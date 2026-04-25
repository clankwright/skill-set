#!/usr/bin/env python3
"""
orchestrate-chain.py — drive a multi-iteration skill-chain run with budget gates
                       and Telegram event notifications.

Usage:
    orchestrate-chain.py --chain <name> [--loop <N>]
                         [--max-budget-usd <X>] [--max-cycles <N>]
                         [--telegram-env <path>]
                         [--no-telegram]
                         [--harness <name>]
                         [--log-dir <path>]
                         [--no-log]
                         [-- <extra-args-forwarded-to-skill-chain.py>]

Spawns `bin/skill-chain.py --chain <name> --loop N --log-dir <auto>` as a
subprocess. Streams its stdout to the terminal verbatim; in parallel, watches
for iteration-boundary markers, reads the per-iteration MANIFEST.json the
chain runner writes when one completes, and posts Telegram updates at four
event classes:

  1. session start     — chain name, requested iterations, optional caps
  2. iteration close   — commit SHA + subject + per-iter spend + cumulative
  3. rate-limit pause  — forwarded immediately when the chain runner emits
                         a `[rate-limit] ... sleeping ... before retrying`
                         banner; same on the matching resume line
  4. session end       — completed iteration count + total spend +
                         non-zero exit reason if any + supervisor verdict
                         path (latest iter's verdict file)

Halts the subprocess between iterations (via SIGINT to the `time.sleep` in
skill-chain.py's loop) when:
  - cumulative spend exceeds --max-budget-usd, OR
  - completed iterations reach --max-cycles, OR
  - a non-supervisor skill exits non-zero (the chain runner already aborts;
    the orchestrator just observes and notifies).

Telegram outbound goes through bin/notify-telegram.sh, which requires
TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in env. --telegram-env points at a
file (sourced into the subprocess env) that exports both. --no-telegram
suppresses outbound entirely (useful for local debugging or a dry-run).

Distinct from sst-manager: the manager runs on a cron and surveys MULTIPLE
projects passively. The orchestrator runs ONCE per multi-iteration chain
session and is active the entire time. Output streams to stdout the same
way bin/skill-chain.py does, so an interactive terminal looks identical
whether the chain is invoked directly or via this wrapper.
"""

import argparse
import datetime as _dt
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_CHAIN = REPO_ROOT / "bin" / "skill-chain.py"
NOTIFY_TELEGRAM = REPO_ROOT / "bin" / "notify-telegram.sh"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# ===== iteration N/M =====   or   ===== iteration N (looping until failure) =====
ITER_BANNER_RE = re.compile(
    r"=====\s+iteration\s+(\d+)(?:/(\d+))?(?:\s+\(([^)]*)\))?\s+====="
)

# [rate-limit] <type> exceeded; sleeping <Ns> until <ISO> before retrying /<skill>
RATE_LIMIT_PAUSE_RE = re.compile(
    r"\[rate-limit\]\s+(\S+)\s+exceeded;\s+sleeping\s+(\S+)\s+until\s+(\S+)\s+before\s+retrying\s+/(\S+)"
)

# RED-banner abort variants
RATE_LIMIT_ABORT_RE = re.compile(
    r"\[rate-limit\]\s+(.+?)(aborting chain|max-pauses-per-session|max-rate-limit-pause-seconds|falling back to fail)"
)


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_dirname() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def _git_subject(cwd: str, sha: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "log", "-1", "--pretty=%s", sha],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip() or "(no subject)"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "(unknown)"


def _read_telegram_env(path: Path) -> dict[str, str]:
    """Parse a shell-style env file (KEY=VALUE per line, # comments, optional `export `).
    Returns the dict to merge into the orchestrator's env. Quoted values are
    stripped of one matching pair of single or double quotes.
    """
    out: dict[str, str] = {}
    if not path.exists():
        raise SystemExit(f"--telegram-env: file does not exist: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[len("export "):].lstrip()
        if "=" not in s:
            continue
        key, _, value = s.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key] = value
    return out


class TelegramSink:
    """Sends a message via bin/notify-telegram.sh. No-op when --no-telegram."""

    def __init__(self, *, enabled: bool, env: dict[str, str]):
        self.enabled = enabled
        self.env = env
        self._warned_missing = False

    def send(self, message: str, *, label: str = "telegram") -> None:
        if not self.enabled:
            print(f"[orchestrator] {label} (suppressed): {message.splitlines()[0][:200]}",
                  file=sys.stderr, flush=True)
            return
        if "TELEGRAM_BOT_TOKEN" not in self.env or "TELEGRAM_CHAT_ID" not in self.env:
            if not self._warned_missing:
                print("[orchestrator] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not in env; "
                      "skipping outbound. Pass --telegram-env <file> or set them, "
                      "or use --no-telegram to suppress this warning.",
                      file=sys.stderr, flush=True)
                self._warned_missing = True
            return
        try:
            r = subprocess.run(
                ["bash", str(NOTIFY_TELEGRAM)],
                input=message,
                env={**os.environ, **self.env},
                capture_output=True, text=True, timeout=20,
            )
            if r.returncode != 0:
                print(f"[orchestrator] {label}: notify-telegram exited {r.returncode}: "
                      f"{r.stderr.strip()[:300]}", file=sys.stderr, flush=True)
        except subprocess.TimeoutExpired:
            print(f"[orchestrator] {label}: notify-telegram timed out", file=sys.stderr, flush=True)


def _read_manifest(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _iteration_cost(iter_manifest: dict) -> float:
    return sum(float(s.get("total_cost_usd") or 0) for s in iter_manifest.get("skills", []))


def _supervisor_verdict_path(log_dir: Path, iter_num: int, looping: bool) -> Path:
    if looping:
        return log_dir / f"iter_{iter_num:02d}" / "supervisor_verdict.md"
    return log_dir / "supervisor_verdict.md"


def _verdict_outcome(verdict_path: Path) -> str:
    """Inspect a supervisor_verdict.md and return a one-word outcome label.

    Looks for an explicit `Outcome: <word>` line first; failing that, scans
    for `escalate` / `ESCALATE` markers anywhere in the body. Returns
    'unknown' when the file is absent (caller decides whether that's an
    error vs just a no-supervisor chain).
    """
    if not verdict_path.exists():
        return "unknown"
    try:
        body = verdict_path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    m = re.search(r"^\s*\*?\*?Outcome\*?\*?\s*:\s*([A-Za-z_-]+)", body, re.MULTILINE)
    if m:
        return m.group(1).strip().lower()
    if re.search(r"\bescalate\b", body, re.IGNORECASE):
        return "escalate"
    return "clean"


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(
        prog="orchestrate-chain.py",
        description="Drive a multi-iteration skill-chain run with budget gates "
                    "and Telegram event notifications. Wraps bin/skill-chain.py.",
    )
    p.add_argument("--chain", required=True,
                   help="Chain name to run (resolves the same way bin/skill-chain.py does).")
    p.add_argument("--loop", type=int, default=None,
                   help="Iteration count (forwarded to skill-chain.py --loop). "
                        "0 means until failure / Ctrl-C; the orchestrator's --max-cycles "
                        "still applies independently.")
    p.add_argument("--max-budget-usd", type=float, default=None,
                   help="Send SIGINT to the chain runner between iterations once "
                        "cumulative cost exceeds this amount. Cost is summed from "
                        "iter_NN/MANIFEST.json skills[].total_cost_usd.")
    p.add_argument("--max-cycles", type=int, default=None,
                   help="Send SIGINT to the chain runner between iterations once "
                        "this many iterations have completed. Independent of "
                        "--loop (whichever fires first wins).")
    p.add_argument("--telegram-env", type=Path, default=None,
                   help="Path to a shell-style env file exporting TELEGRAM_BOT_TOKEN "
                        "and TELEGRAM_CHAT_ID. Sourced into the orchestrator's "
                        "subprocess env when invoking bin/notify-telegram.sh.")
    p.add_argument("--no-telegram", action="store_true",
                   help="Suppress all Telegram outbound (events are still printed to "
                        "stderr with a [suppressed] tag).")
    p.add_argument("--harness", default=None,
                   help="Forwarded to skill-chain.py --harness if set.")
    p.add_argument("--log-dir", type=Path, default=None,
                   help="Forwarded to skill-chain.py --log-dir if set; otherwise the "
                        "orchestrator computes the same default path skill-chain.py "
                        "would so it knows where to read iter_NN/MANIFEST.json.")
    p.add_argument("--no-log", action="store_true",
                   help="Forwarded to skill-chain.py --no-log. Implies the orchestrator "
                        "cannot read per-iteration manifests, so iteration-boundary "
                        "Telegrams will report only the cycle index (no commit/cost).")
    p.add_argument("--label", default=None,
                   help="Optional human-readable label included in each Telegram "
                        "(e.g. the project name or the persona). Defaults to the "
                        "chain name.")
    args, rest = p.parse_known_args(argv)
    # Forwarded args appear after `--`; argparse leaves them in `rest`.
    if rest and rest[0] == "--":
        rest = rest[1:]
    return args, rest


def main() -> int:
    args, forwarded = parse_args(sys.argv[1:])

    cwd = os.getcwd()

    if args.log_dir is not None:
        log_dir = args.log_dir.resolve()
    elif args.no_log:
        log_dir = None
    else:
        log_dir = (Path(cwd) / ".skill-runs" / f"{_utc_dirname()}_{args.chain}").resolve()

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)

    # Build the skill-chain.py command.
    cmd: list[str] = [sys.executable, str(SKILL_CHAIN), "--chain", args.chain]
    if args.loop is not None:
        cmd += ["--loop", str(args.loop)]
    if args.harness is not None:
        cmd += ["--harness", args.harness]
    if args.no_log:
        cmd += ["--no-log"]
    elif log_dir is not None:
        cmd += ["--log-dir", str(log_dir)]
    cmd += list(forwarded)

    # Telegram env merge.
    tg_env: dict[str, str] = {}
    if args.telegram_env:
        tg_env.update(_read_telegram_env(args.telegram_env))
    # Allow caller-set env vars to win when no --telegram-env was passed.
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_PARSE_MODE"):
        if k not in tg_env and k in os.environ:
            tg_env[k] = os.environ[k]

    telegram = TelegramSink(enabled=not args.no_telegram, env=tg_env)
    label = args.label or args.chain

    looping = (args.loop is not None and args.loop != 1)
    loop_desc = (
        f"--loop {args.loop}" if args.loop is not None
        else "(YAML-defined loop)"
    )

    cap_lines: list[str] = []
    if args.max_budget_usd is not None:
        cap_lines.append(f"budget cap ${args.max_budget_usd:.2f}")
    if args.max_cycles is not None:
        cap_lines.append(f"cycle cap {args.max_cycles}")
    cap_text = " | ".join(cap_lines) if cap_lines else "no caps"

    start_msg = (
        f"orchestrator: session START — {label}\n"
        f"chain: {args.chain} {loop_desc}\n"
        f"cwd: {cwd}\n"
        f"caps: {cap_text}\n"
        f"log: {log_dir if log_dir else '(none)'}\n"
        f"started_at: {_utc_iso()}"
    )
    telegram.send(start_msg, label="session-start")

    # Spawn the chain runner. line-buffered so we can stream banners as they fire.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    last_iter_seen = 0           # most recent iteration banner we've observed
    iters_finalized = 0          # how many per-iter MANIFESTs we've consumed
    cumulative_cost_usd = 0.0
    halt_requested = False
    halt_reason: str | None = None
    pause_active: dict[str, str] | None = None  # tracked across pause/resume lines

    def _finalize_iteration(n: int) -> None:
        """Read iter_N/MANIFEST.json (or top-level for non-loop), update budget,
        send Telegram. Idempotent: tracks `iters_finalized` and only fires once
        per iteration. Safe to call after subprocess exit."""
        nonlocal iters_finalized, cumulative_cost_usd, halt_requested, halt_reason
        if n <= iters_finalized:
            return
        if log_dir is None:
            iters_finalized = n
            telegram.send(
                f"orchestrator [{label}]: iteration {n} closed "
                f"(no log dir; cost/commit unavailable)",
                label="iter-close-nolog",
            )
            return

        # Single-iter chain (no loop) writes flat; multi-iter writes iter_NN/.
        iter_manifest_path = (
            log_dir / f"iter_{n:02d}" / "MANIFEST.json"
            if looping else log_dir / "MANIFEST.json"
        )
        iter_manifest = _read_manifest(iter_manifest_path)
        if iter_manifest is None:
            iters_finalized = n
            telegram.send(
                f"orchestrator [{label}]: iteration {n} closed but MANIFEST.json "
                f"not found at {iter_manifest_path}",
                label="iter-close-missing",
            )
            return

        cost = _iteration_cost(iter_manifest)
        cumulative_cost_usd += cost
        iters_finalized = n

        sha_before = iter_manifest.get("git_sha_before")
        sha_after = iter_manifest.get("git_sha_after")
        commit_line = "no commit"
        if sha_before and sha_after and sha_before != sha_after:
            subject = _git_subject(cwd, sha_after)
            commit_line = f"{sha_after[:8]} {subject}"

        verdict = _verdict_outcome(_supervisor_verdict_path(log_dir, n, looping))
        rl_pauses = iter_manifest.get("rate_limit_pauses") or []
        pause_note = f" | {len(rl_pauses)} rate-limit pause(s)" if rl_pauses else ""

        msg = (
            f"orchestrator [{label}]: iter {n} CLOSE\n"
            f"commit: {commit_line}\n"
            f"cost: ${cost:.4f} (cumulative ${cumulative_cost_usd:.4f})\n"
            f"verdict: {verdict}{pause_note}\n"
            f"at: {_utc_iso()}"
        )
        telegram.send(msg, label="iter-close")

        # Check halt thresholds. Halt is best-effort: SIGINT lands during
        # skill-chain.py's between-iter sleep or during a skill mid-run; either
        # way the chain runner has a KeyboardInterrupt path that finalizes
        # manifests cleanly with exit 130.
        if not halt_requested:
            if args.max_budget_usd is not None and cumulative_cost_usd > args.max_budget_usd:
                halt_requested = True
                halt_reason = (
                    f"max-budget-usd exceeded "
                    f"(${cumulative_cost_usd:.4f} > ${args.max_budget_usd:.2f})"
                )
            elif args.max_cycles is not None and iters_finalized >= args.max_cycles:
                halt_requested = True
                halt_reason = f"max-cycles reached ({iters_finalized} >= {args.max_cycles})"
            elif verdict == "escalate":
                halt_requested = True
                halt_reason = f"supervisor escalation in iter {n}"

            if halt_requested:
                telegram.send(
                    f"orchestrator [{label}]: HALT requested — {halt_reason}\n"
                    f"sending SIGINT to chain runner (will exit at next "
                    f"between-iter boundary or end of current skill).",
                    label="halt-request",
                )
                try:
                    proc.send_signal(signal.SIGINT)
                except ProcessLookupError:
                    pass

    try:
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            sys.stdout.write(raw_line)
            sys.stdout.flush()

            stripped = _strip_ansi(raw_line.rstrip())

            m = ITER_BANNER_RE.search(stripped)
            if m:
                n = int(m.group(1))
                if n > 1:
                    # The PRIOR iteration completed before this banner printed.
                    _finalize_iteration(n - 1)
                last_iter_seen = max(last_iter_seen, n)
                continue

            m = RATE_LIMIT_PAUSE_RE.search(stripped)
            if m:
                rtype, secs, wake_iso, skill = m.groups()
                pause_active = {
                    "type": rtype, "skill": skill, "wake": wake_iso, "sleep_s": secs,
                    "started_at": _utc_iso(),
                }
                telegram.send(
                    f"orchestrator [{label}]: RATE-LIMIT pause\n"
                    f"type: {rtype} | skill: /{skill}\n"
                    f"sleeping {secs}s until {wake_iso}\n"
                    f"iter: {last_iter_seen} | at: {_utc_iso()}",
                    label="rate-limit-pause",
                )
                continue

            if "[rate-limit]" in stripped and pause_active and ("retrying" not in stripped):
                # Any subsequent [rate-limit] line that isn't another pause is
                # most likely an abort banner; surface it so the user sees why
                # the chain didn't resume.
                am = RATE_LIMIT_ABORT_RE.search(stripped)
                if am:
                    telegram.send(
                        f"orchestrator [{label}]: RATE-LIMIT abort\n"
                        f"reason: {am.group(2)}\n"
                        f"detail: {stripped[:300]}",
                        label="rate-limit-abort",
                    )
                    pause_active = None
                continue

            # Heuristic resume signal: the next iteration banner OR the next
            # `>>> session ...` line from a fresh subprocess invocation
            # implicitly tells us the pause cleared. We don't try to detect
            # the EXACT resume moment because the chain runner's RESUME log
            # is only the next skill banner; instead the iter-close summary
            # carries the pause count at iteration boundary.
            if pause_active and ">>" in stripped and "session" in stripped:
                resume_msg = (
                    f"orchestrator [{label}]: rate-limit RESUME\n"
                    f"skill resumed: /{pause_active.get('skill')}\n"
                    f"at: {_utc_iso()}"
                )
                telegram.send(resume_msg, label="rate-limit-resume")
                pause_active = None
                continue
    except KeyboardInterrupt:
        # User Ctrl-C on the orchestrator — propagate cleanly to the child.
        halt_reason = halt_reason or "orchestrator received SIGINT"
        try:
            proc.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass

    rc = proc.wait()

    # Finalize the last iteration if its banner was the most recent thing we
    # saw and the subprocess has exited (the chain runner doesn't print a
    # closing banner for the last iter, only for the next one that would have
    # come).
    if last_iter_seen > iters_finalized:
        _finalize_iteration(last_iter_seen)

    # Read top-level manifest for the session-end summary.
    top_manifest_path = log_dir / "MANIFEST.json" if log_dir else None
    top_manifest = _read_manifest(top_manifest_path) if top_manifest_path else None

    completed = (top_manifest or {}).get("loop", {}).get("completed") if top_manifest else None
    if completed is None:
        completed = iters_finalized

    final_lines = [
        f"orchestrator: session END — {label}",
        f"exit_code: {rc}{' (HALT: ' + halt_reason + ')' if halt_reason else ''}",
        f"iterations completed: {completed}",
        f"cumulative cost: ${cumulative_cost_usd:.4f}",
    ]
    if top_manifest_path and top_manifest_path.exists():
        final_lines.append(f"manifest: {top_manifest_path}")
    final_lines.append(f"finished_at: {_utc_iso()}")
    telegram.send("\n".join(final_lines), label="session-end")

    return rc


if __name__ == "__main__":
    sys.exit(main())
