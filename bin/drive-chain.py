#!/usr/bin/env python3
"""
drive-chain.py — drive a multi-iteration skill-chain run with budget gates
                 and Telegram event notifications.

Usage:
    drive-chain.py --chain <name> [--loop <N>]
                   [--profile <persona>]
                   [--max-budget-usd <X>] [--max-cycles <N>]
                   [--telegram-env <path>]
                   [--no-telegram]
                   [--harness <name>]
                   [--log-dir <path>]
                   [--no-log]
                   [-- <extra-args-forwarded-to-skill-chain.py>]

`--profile <persona>` reads `<cwd>/.claude/skills/<persona>-chain-driver/SKILL.md`
(then `~/.claude/skills/...` as fallback) for a `## Configured defaults` yaml
block exposing `watched-chain`, `default-loop`, `default-max-budget-usd`,
`default-max-cycles`, `telegram-env`, `label`. Each maps to the corresponding
CLI arg as a layer below it (CLI wins). Mirrors the slash-command agent's
own resolution of the same block, so `python3 bin/drive-chain.py --profile X`
behaves the same as `/<X>-chain-driver` would.

Spawns `bin/skill-chain.py --chain <name> --loop N --log-dir <auto>` as a
subprocess. Streams its stdout to the terminal verbatim; in parallel, watches
for iteration-boundary markers, reads the per-iteration MANIFEST.json the
chain runner writes when one completes, and posts Telegram updates at four
event classes:

  1. session start     - chain name, requested iterations, optional caps
  2. iteration close   - commit SHA + subject + per-iter spend + cumulative
  3. rate-limit pause  - forwarded immediately when the chain runner emits
                         a `[rate-limit] ... sleeping ... before retrying`
                         banner; same on the matching resume line
  4. session end       - completed iteration count + total spend +
                         non-zero exit reason if any + supervisor verdict
                         path (latest iter's verdict file)

Halts the subprocess between iterations (via SIGINT to the `time.sleep` in
skill-chain.py's loop) when:
  - cumulative spend exceeds --max-budget-usd, OR
  - completed iterations reach --max-cycles, OR
  - a non-supervisor skill exits non-zero (the chain runner already aborts;
    the chain driver just observes and notifies).

Telegram outbound goes through bin/notify-telegram.sh, which requires
TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in env. --telegram-env points at a
file (sourced into the subprocess env) that exports both. --no-telegram
suppresses outbound entirely (useful for local debugging or a dry-run).

Distinct from sst-manager: the manager runs on a cron and surveys MULTIPLE
projects passively. The chain driver runs ONCE per multi-iteration chain
session and is active the entire time. Output streams to stdout the same
way bin/skill-chain.py does, so an interactive terminal looks identical
whether the chain is invoked directly or via this wrapper.

Originally shipped as orchestrate-chain.py; renamed to drive-chain.py in
framework Phase 15 alongside the sst-orchestrator -> sst-chain-driver
skill rename.
"""

import argparse
import datetime as _dt
import fcntl
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
MANAGER_BOT = REPO_ROOT / "bin" / "manager-bot.py"
TRANSFERABLE_CHAINS_DIR = REPO_ROOT / "chains"

# Persona profile keys consumed from a `<persona>-chain-driver/SKILL.md`
# "Configured defaults" yaml block. Mirrored against the proprietary layer the
# slash-command agent applies on its own; --profile gives the bare CLI helper
# the same resolution path so terminal users see identical behavior.
PROFILE_KEYS = (
    "watched-chain",
    "default-loop",
    "default-max-budget-usd",
    "default-max-cycles",
    "telegram-env",
    "label",
)

# Phase 18 chain-bound worker lifecycle paths.
WORKER_STATE_DIR = Path.home() / ".claude" / "state"
WORKER_PID_FILE = WORKER_STATE_DIR / "manager-bot.pid"
WORKER_LOCK_FILE = WORKER_STATE_DIR / "manager-bot.pid.lock"
# Refcount for simultaneous chain-driver runs sharing the same worker.
# Each driver that "owns" the worker (starter or registered adopter) holds one
# slot; the last to exit stops the session.
WORKER_REFCOUNT_FILE = WORKER_STATE_DIR / "manager-bot.refcount"

# Legacy default tmux session name from README "Worker management" (always-on
# pattern). Probed alongside the persona-derived name so an externally-managed
# legacy worker is recognized as pre-existing and left untouched.
LEGACY_WORKER_TMUX_NAME = "manager-bot"

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
    Returns the dict to merge into the chain driver's env. Quoted values are
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
            print(f"[chain-driver] {label} (suppressed): {message.splitlines()[0][:200]}",
                  file=sys.stderr, flush=True)
            return
        if "TELEGRAM_BOT_TOKEN" not in self.env or "TELEGRAM_CHAT_ID" not in self.env:
            if not self._warned_missing:
                print("[chain-driver] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not in env; "
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
                print(f"[chain-driver] {label}: notify-telegram exited {r.returncode}: "
                      f"{r.stderr.strip()[:300]}", file=sys.stderr, flush=True)
        except subprocess.TimeoutExpired:
            print(f"[chain-driver] {label}: notify-telegram timed out", file=sys.stderr, flush=True)


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

    Checks two patterns for an explicit outcome declaration (markdown-header
    form first, legacy colon form second); failing both, scans the body for
    `escalate` / `ESCALATE` with code spans stripped so a supervisor
    enumerating grep patterns it did NOT find (e.g. ``"`[escalate]`"`` in a
    "no matches" sentence) does not false-trigger.

    Returns 'unknown' when the file is absent (caller decides whether that's
    an error vs just a no-supervisor chain).
    """
    if not verdict_path.exists():
        return "unknown"
    try:
        body = verdict_path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    # Primary: markdown-header form `## Outcome\n\n<word ...>` (what supervisors
    # actually write — the first non-empty word on the line after the heading).
    m = re.search(r"^##\s+Outcome\s*\n+\s*([A-Za-z_-]+)", body, re.MULTILINE)
    if m:
        return m.group(1).strip().lower()
    # Secondary: inline colon form `Outcome: <word>` (legacy / alternative).
    m = re.search(r"^\s*\*?\*?Outcome\*?\*?\s*:\s*([A-Za-z_-]+)", body, re.MULTILINE)
    if m:
        return m.group(1).strip().lower()
    # Fallback: strip fenced blocks and inline code spans before scanning so
    # "`[escalate]`" in a "no matches" enumeration doesn't match \bescalate\b.
    stripped = re.sub(r"```[\s\S]*?```", "", body)
    stripped = re.sub(r"`[^`\n]+`", "", stripped)
    if re.search(r"\bescalate\b", stripped, re.IGNORECASE):
        return "escalate"
    return "clean"


def _persona_from_env_file(env_path: Path | None) -> str | None:
    """Derive the persona from a `<persona>-telegram.env` path.

    Convention from CLAUDE.md and sst-setup-telegram: the env file lives at
    `~/.config/<persona>-telegram.env`. The persona is also the tmux session
    suffix (`<persona>-bot`) the chain-bound worker runs under. Returns None
    when the path is missing or doesn't follow the convention; the caller
    then skips worker management rather than guessing a name.
    """
    if env_path is None:
        return None
    name = env_path.name
    suffix = "-telegram.env"
    if not name.endswith(suffix):
        return None
    persona = name[: -len(suffix)]
    return persona or None


def _tmux_session_exists(name: str) -> bool:
    try:
        r = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def _read_live_pid(pid_file: Path) -> int | None:
    """Read pid_file; return the PID iff the process is alive. Stale files
    (process exited but PID file remained) return None so the probe falls
    through to a fresh start."""
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        # Process exists but is owned by another user; still counts as live.
        return pid
    return pid


def _probe_worker(persona_session: str) -> dict | None:
    """Look for an existing manager-bot worker. Returns a descriptor dict
    when found, else None. Probes (in order): the persona-suffixed tmux
    session, the legacy `manager-bot` tmux session, and a live PID at the
    well-known PID file.
    """
    for name in (persona_session, LEGACY_WORKER_TMUX_NAME):
        if _tmux_session_exists(name):
            return {"kind": "tmux", "name": name, "ours": False}
    pid = _read_live_pid(WORKER_PID_FILE)
    if pid is not None:
        return {"kind": "pid", "pid": pid, "ours": False}
    return None


def _is_worker_stale(descriptor: dict) -> bool:
    """Return True when bin/manager-bot.py was modified *after* the worker
    process started, meaning the worker is serving old code and should be
    recycled. Only meaningful for tmux-kind descriptors on Linux (/proc).
    Conservatively returns False on any read failure so a live worker is
    never incorrectly killed."""
    if not MANAGER_BOT.exists():
        return False
    try:
        bot_mtime = MANAGER_BOT.stat().st_mtime
    except OSError:
        return False
    if descriptor.get("kind") != "tmux":
        return False
    session = descriptor.get("name")
    if not session:
        return False
    # Get the PID of the pane running in the tmux session.
    try:
        pinfo = subprocess.run(
            ["tmux", "list-panes", "-t", session, "-F", "#{pane_pid}"],
            capture_output=True, text=True, timeout=5,
        )
        line = pinfo.stdout.strip().splitlines()[0] if pinfo.stdout.strip() else ""
        if not line:
            return False
        pid = int(line)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError):
        return False
    # /proc/<pid>/stat field 22 (0-indexed 21) is jiffies since boot.
    try:
        stat_fields = Path(f"/proc/{pid}/stat").read_text().split()
        start_jiffies = int(stat_fields[21])
        uptime_seconds = float(Path("/proc/uptime").read_text().split()[0])
        sc_clk_tck = os.sysconf("SC_CLK_TCK")
        process_start_real = time.time() - uptime_seconds + start_jiffies / sc_clk_tck
    except (OSError, ValueError, AttributeError, IndexError):
        return False
    return bot_mtime > process_start_real


def _start_worker(*, persona: str, env_file: Path) -> dict | None:
    """Start a detached tmux session running bin/manager-bot.py with
    TELEGRAM_ENV_FILE pointing at env_file. Holds an exclusive flock on
    WORKER_LOCK_FILE during the start so two simultaneous chain drivers
    serialize. Re-probes inside the lock to handle the TOCTOU window;
    returns None if another driver won the race or tmux is unavailable.
    """
    if not MANAGER_BOT.exists():
        return None
    WORKER_STATE_DIR.mkdir(parents=True, exist_ok=True)
    WORKER_LOCK_FILE.touch(exist_ok=True)

    session = f"{persona}-bot"
    shell_cmd = (
        f"TELEGRAM_ENV_FILE={shlex.quote(str(env_file))} "
        f"{shlex.quote(sys.executable)} {shlex.quote(str(MANAGER_BOT))}"
    )

    try:
        lock_fd = os.open(str(WORKER_LOCK_FILE), os.O_RDWR)
    except OSError:
        return None
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Another chain driver is mid-start; assume it will succeed and
            # let the caller treat the resulting worker as externally-managed
            # (we won't kill it on session-end since worker_started_by_us
            # stays False).
            return None

        if _probe_worker(session) is not None:
            return None

        try:
            r = subprocess.run(
                ["tmux", "new-session", "-d", "-s", session, shell_cmd],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if r.returncode != 0:
            return None

        pid = -1
        try:
            pinfo = subprocess.run(
                ["tmux", "list-panes", "-t", session, "-F", "#{pane_pid}"],
                capture_output=True, text=True, timeout=5,
            )
            line = pinfo.stdout.strip().splitlines()[0] if pinfo.stdout.strip() else ""
            if line:
                pid = int(line)
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        if pid > 0:
            try:
                WORKER_PID_FILE.write_text(f"{pid}\n", encoding="utf-8")
            except OSError:
                pass

        # Initialize refcount to 1 for the starting driver.  Written inside
        # the existing flock so _refcount_op (which acquires the same lock)
        # never races with this initialization.
        try:
            WORKER_REFCOUNT_FILE.write_text("1\n", encoding="utf-8")
        except OSError:
            pass

        return {"kind": "tmux", "name": session, "pid": pid, "ours": True}
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(lock_fd)


def _stop_worker(descriptor: dict) -> None:
    """Stop a worker started by this chain driver. Idempotent: safe to call
    even if the tmux session has already exited. Cleans up the PID and
    refcount state files."""
    if descriptor.get("kind") == "tmux":
        name = descriptor.get("name")
        if name:
            try:
                subprocess.run(
                    ["tmux", "kill-session", "-t", name],
                    capture_output=True, text=True, timeout=5,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
    for state_file in (WORKER_PID_FILE, WORKER_REFCOUNT_FILE):
        if state_file.exists():
            try:
                state_file.unlink()
            except OSError:
                pass


def _refcount_op(delta: int) -> int:
    """Atomically increment or decrement the worker refcount under
    WORKER_LOCK_FILE.  Returns the new count (clamped to >= 0).

    NOTE: do NOT call this from inside _start_worker's flock block — the same
    process opening the lock file twice causes a deadlock on Linux.  _start_worker
    writes the initial count=1 directly before releasing its lock.
    """
    WORKER_STATE_DIR.mkdir(parents=True, exist_ok=True)
    WORKER_LOCK_FILE.touch(exist_ok=True)
    try:
        lock_fd = os.open(str(WORKER_LOCK_FILE), os.O_RDWR)
    except OSError:
        return max(0, delta)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        count = 0
        if WORKER_REFCOUNT_FILE.exists():
            try:
                count = int(WORKER_REFCOUNT_FILE.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                count = 0
        new_count = max(0, count + delta)
        try:
            WORKER_REFCOUNT_FILE.write_text(f"{new_count}\n", encoding="utf-8")
        except OSError:
            pass
        return new_count
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(lock_fd)


def _any_other_driver_using_persona(persona: str, my_pid: int) -> bool:
    """Return True if another live drive-chain.py process is using the same
    persona's telegram-env file.  Used to detect stale refcounts left by
    crashed drivers so the last live driver still cleans up.

    Linux-only (/proc scan).  Returns True conservatively on non-Linux or
    on any read error, which means: assume other drivers might still be
    running (don't stop the worker prematurely).
    """
    proc_dir = Path("/proc")
    if not proc_dir.exists():
        return True
    env_pattern = f"{persona}-telegram.env"
    for entry in proc_dir.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == my_pid:
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().decode("utf-8", errors="replace")
            parts = cmdline.split("\x00")
            if not any("drive-chain.py" in p for p in parts):
                continue
            if any(env_pattern in p for p in parts):
                return True
        except (OSError, PermissionError):
            continue
    return False


def _find_profile_skill(persona: str, cwd: str) -> Path | None:
    """Resolve a `<persona>-chain-driver/SKILL.md` in the same priority order
    the harness uses for proprietary skills: project-scoped first, then
    personal-global. Returns None on miss."""
    candidates = [
        Path(cwd) / ".claude" / "skills" / f"{persona}-chain-driver" / "SKILL.md",
        Path.home() / ".claude" / "skills" / f"{persona}-chain-driver" / "SKILL.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _load_profile_defaults(persona: str, cwd: str) -> dict | None:
    """Parse the first ```yaml fenced block under the `## Configured defaults`
    header of a `<persona>-chain-driver/SKILL.md`. Returns the parsed dict or
    None if no skill / no block found. Unknown keys are ignored; PROFILE_KEYS
    is the contract surface the chain driver consumes.
    """
    path = _find_profile_skill(persona, cwd)
    if path is None:
        return None
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # Find `## Configured defaults` then the first ```yaml ... ``` block after it.
    m = re.search(
        r"^##\s+Configured defaults\s*\n(.*?)(?=^##\s+|\Z)",
        body, re.MULTILINE | re.DOTALL,
    )
    if not m:
        return None
    section = m.group(1)
    code = re.search(r"```yaml\s*\n(.*?)\n```", section, re.DOTALL)
    if not code:
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        data = yaml.safe_load(code.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return {k: v for k, v in data.items() if k in PROFILE_KEYS}


def _resolve_chain_yaml_loop(chain_name: str, cwd: str) -> int | None:
    """Mirror skill-chain.py's chain lookup, return the YAML's `loop:` field
    (default 1 when present-but-unspecified). Returns None if the chain isn't
    found or PyYAML isn't available — the no-op-cap note is a UX nicety, not
    correctness, so any failure is a silent no-op (the chain runner will
    produce its own clearer error if --chain itself is bogus)."""
    candidates = [
        Path(cwd) / ".claude" / "chains" / f"{chain_name}.yaml",
        TRANSFERABLE_CHAINS_DIR / f"{chain_name}.yaml",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    loop = data.get("loop", 1)
    try:
        return int(loop)
    except (TypeError, ValueError):
        return None


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(
        prog="drive-chain.py",
        description="Drive a multi-iteration skill-chain run with budget gates "
                    "and Telegram event notifications. Wraps bin/skill-chain.py.",
    )
    p.add_argument("--chain", default=None,
                   help="Chain name to run (resolves the same way bin/skill-chain.py "
                        "does). Required unless --profile resolves a `watched-chain:`.")
    p.add_argument("--profile", default=None,
                   help="Persona name; loads `<persona>-chain-driver/SKILL.md`'s "
                        "`## Configured defaults` yaml block (project-scoped first, "
                        "then ~/.claude/skills/) as a layer below CLI args. Mirrors "
                        "what /<persona>-chain-driver does for its slash-command "
                        "agent, so terminal users get identical defaults.")
    p.add_argument("--loop", type=int, default=None,
                   help="Iteration count (forwarded to skill-chain.py --loop). "
                        "0 means until failure / Ctrl-C; the chain driver's --max-cycles "
                        "still applies independently.")
    p.add_argument("--max-budget-usd", type=float, default=None,
                   help="Send SIGINT to the chain runner between iterations once "
                        "cumulative cost exceeds this amount. Cost is summed from "
                        "iter_NN/MANIFEST.json skills[].total_cost_usd.")
    p.add_argument("--max-cycles", type=int, default=None,
                   help="Send SIGINT to the chain runner between iterations once "
                        "this many iterations have completed. Independent of "
                        "--loop (whichever fires first wins). Only meaningful when "
                        "the resolved chain loop count is greater than --max-cycles "
                        "(or 0/unlimited); single-iter chains finish naturally before "
                        "the cap can fire and a no-op note is printed at startup. "
                        "Precedence: when --loop N is passed explicitly without "
                        "--max-cycles, any profile default-max-cycles is skipped "
                        "(--loop is the only ceiling for that run). To impose a "
                        "lower cap on an explicit --loop N run, pass --max-cycles M "
                        "alongside it.")
    p.add_argument("--telegram-env", type=Path, default=None,
                   help="Path to a shell-style env file exporting TELEGRAM_BOT_TOKEN "
                        "and TELEGRAM_CHAT_ID. Sourced into the chain driver's "
                        "subprocess env when invoking bin/notify-telegram.sh.")
    p.add_argument("--no-telegram", action="store_true",
                   help="Suppress all Telegram outbound (events are still printed to "
                        "stderr with a [suppressed] tag).")
    p.add_argument("--harness", default=None,
                   help="Forwarded to skill-chain.py --harness if set.")
    p.add_argument("--log-dir", type=Path, default=None,
                   help="Forwarded to skill-chain.py --log-dir if set; otherwise the "
                        "chain driver computes the same default path skill-chain.py "
                        "would so it knows where to read iter_NN/MANIFEST.json.")
    p.add_argument("--no-log", action="store_true",
                   help="Forwarded to skill-chain.py --no-log. Implies the chain driver "
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

    # Snapshot before profile loading so the precedence gate below can
    # distinguish "user said --loop N" from "profile filled in default-loop."
    # When --loop N is explicit, default-max-cycles is skipped so the user's
    # loop count is the only ceiling (no silent profile cap).
    explicit_loop = args.loop is not None

    # Resolve profile defaults as a layer BELOW CLI args. Each CLI arg keeps
    # its current "explicit > profile > None/builtin" semantics; we only fill
    # in fields the user didn't pass. Unknown profile keys are dropped by
    # _load_profile_defaults; missing profile is a silent no-op so users who
    # don't pass --profile see no behavior change.
    if args.profile:
        profile = _load_profile_defaults(args.profile, cwd)
        if profile is None:
            print(
                f"[chain-driver] --profile {args.profile!r}: no "
                f"'<persona>-chain-driver/SKILL.md' found under "
                f"<cwd>/.claude/skills/ or ~/.claude/skills/, or its "
                f"'## Configured defaults' yaml block is missing/malformed; "
                f"continuing with CLI args + builtin defaults only.",
                file=sys.stderr, flush=True,
            )
        else:
            if args.chain is None and profile.get("watched-chain"):
                args.chain = str(profile["watched-chain"])
            if args.loop is None and profile.get("default-loop") is not None:
                try:
                    args.loop = int(profile["default-loop"])
                except (TypeError, ValueError):
                    pass
            if args.max_budget_usd is None and profile.get("default-max-budget-usd") is not None:
                try:
                    args.max_budget_usd = float(profile["default-max-budget-usd"])
                except (TypeError, ValueError):
                    pass
            if (args.max_cycles is None
                    and not explicit_loop
                    and profile.get("default-max-cycles") is not None):
                try:
                    args.max_cycles = int(profile["default-max-cycles"])
                except (TypeError, ValueError):
                    pass
            if args.telegram_env is None and profile.get("telegram-env"):
                args.telegram_env = Path(
                    os.path.expanduser(str(profile["telegram-env"]))
                )
            if args.label is None and profile.get("label"):
                args.label = str(profile["label"])

    if args.chain is None:
        raise SystemExit(
            "--chain is required (or pass --profile <persona> resolving to a "
            "'<persona>-chain-driver/SKILL.md' with `watched-chain:` set)."
        )

    print(
        f"[chain-driver] resolved: chain={args.chain!r} loop={args.loop} "
        f"max_cycles={args.max_cycles} max_budget_usd={args.max_budget_usd}",
        file=sys.stderr, flush=True,
    )

    if args.log_dir is not None:
        log_dir = args.log_dir.resolve()
    elif args.no_log:
        log_dir = None
    else:
        log_dir = (Path(cwd) / ".skill-runs" / f"{_utc_dirname()}_{args.chain}").resolve()

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)

    # --max-cycles no-op note: when the resolved chain loop count is finite and
    # <= the cap, the cap can never fire (the chain finishes naturally first).
    # Surface this at startup so terminal users don't read a silent no-op as
    # "the cap silently worked." `loop: 0` (until-failure) keeps the cap
    # meaningful, so we don't warn there.
    if args.max_cycles is not None:
        effective_loop = (
            args.loop if args.loop is not None
            else _resolve_chain_yaml_loop(args.chain, cwd)
        )
        if effective_loop is not None and 0 < effective_loop <= args.max_cycles:
            print(
                f"[chain-driver] note: --max-cycles {args.max_cycles} is a no-op; "
                f"chain '{args.chain}' will run {effective_loop} iter(s) naturally "
                f"and exit before the cap can fire. The cap is the safety net for "
                f"multi-iter runs (--loop N>{args.max_cycles}, or chain `loop: 0`).",
                file=sys.stderr, flush=True,
            )

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
    # Default to plain text. Chain-driver bodies (session-start / iter-close /
    # rate-limit / supervisor / session-end) interpolate raw run-dir paths,
    # ISO timestamps, and commit subjects that frequently contain `_` `*` `[`;
    # under notify-telegram.sh's `Markdown` fallback those parse as
    # unterminated entities and the API returns 400. Explicit user config
    # (env file or shell) still wins via setdefault.
    tg_env.setdefault("TELEGRAM_PARSE_MODE", "")

    telegram = TelegramSink(enabled=not args.no_telegram, env=tg_env)
    label = args.label or args.chain

    # Phase 18: chain-bound worker lifecycle. Start the manager-bot worker iff
    # Telegram is enabled, an env file was provided (so we have a chat-id to
    # ack), and no existing worker is running.
    #
    # Simultaneous-driver refcount (Phase 18.8 fix): every driver that "owns"
    # the worker holds one slot in WORKER_REFCOUNT_FILE.  The starter writes
    # count=1 inside _start_worker's flock.  A concurrent driver that finds the
    # persona-bot session already running increments to count=2 (or higher) via
    # _refcount_op.  At session-end each driver decrements; only the last
    # (count→0) kills the session.  Truly external workers (legacy tmux name,
    # PID-only, or non-persona-prefixed) are never registered and never stopped.
    worker_registered = False     # True when we hold a refcount slot
    worker_descriptor: dict | None = None
    persona: str | None = None    # promoted to outer scope for session-end use
    if not args.no_telegram and args.telegram_env is not None:
        persona = _persona_from_env_file(args.telegram_env)
        if persona:
            session = f"{persona}-bot"
            existing = _probe_worker(session)
            if existing is not None and _is_worker_stale(existing):
                # Read refcount under WORKER_LOCK_FILE before recycling.
                # _stop_worker wipes WORKER_REFCOUNT_FILE, which drops
                # concurrent drivers' slots and causes them to kill the
                # freshly-started worker when they finish.  If count > 0,
                # defer the recycle; all current drivers share the stale
                # worker until the last one exits naturally.
                current_count = _refcount_op(0)
                if current_count > 0:
                    print(
                        f"[chain-driver] stale worker detected "
                        f"({existing.get('kind')}: "
                        f"{existing.get('name') or existing.get('pid')}) "
                        f"but {current_count} driver(s) registered — "
                        f"deferring recycle until refcount clears.",
                        file=sys.stderr, flush=True,
                    )
                    # Don't clear existing; fall through to adopt the worker.
                else:
                    print(
                        f"[chain-driver] stale worker detected "
                        f"({existing.get('kind')}: "
                        f"{existing.get('name') or existing.get('pid')}); "
                        f"manager-bot.py was updated since the worker started — "
                        f"recycling session.",
                        file=sys.stderr, flush=True,
                    )
                    _stop_worker(existing)  # also resets WORKER_REFCOUNT_FILE
                    existing = None
            if existing is None:
                worker_descriptor = _start_worker(
                    persona=persona, env_file=args.telegram_env.resolve(),
                )
                if worker_descriptor is not None:
                    worker_registered = True  # _start_worker wrote refcount=1
                    print(
                        f"[chain-driver] worker started: tmux session "
                        f"'{worker_descriptor.get('name')}' "
                        f"(pid {worker_descriptor.get('pid', '?')})",
                        file=sys.stderr, flush=True,
                    )
                else:
                    print(
                        "[chain-driver] worker start skipped (raced with "
                        "another driver, tmux unavailable, or manager-bot.py "
                        "not found); chain will run without an inbound worker.",
                        file=sys.stderr, flush=True,
                    )
            elif existing.get("kind") == "tmux" and existing.get("name") == session:
                # Our persona's worker is already up — register so we hold a
                # refcount slot.  This prevents a concurrent driver that started
                # the session from killing it when it finishes first.
                new_count = _refcount_op(+1)
                worker_registered = True
                worker_descriptor = existing
                print(
                    f"[chain-driver] worker already running "
                    f"(tmux: {session}); registered (refcount now {new_count}); "
                    f"will release on session-end.",
                    file=sys.stderr, flush=True,
                )
            else:
                # Legacy session name, PID-only, or different persona: truly
                # external — leave untouched, no refcount slot taken.
                print(
                    f"[chain-driver] worker already running "
                    f"({existing.get('kind')}: "
                    f"{existing.get('name') or existing.get('pid')}); "
                    f"externally-managed — leaving untouched.",
                    file=sys.stderr, flush=True,
                )
        else:
            print(
                f"[chain-driver] --telegram-env path "
                f"'{args.telegram_env}' does not match the "
                f"<persona>-telegram.env convention; skipping worker management.",
                file=sys.stderr, flush=True,
            )

    # Provisional `looping` from the CLI override; the chain runner may still
    # resolve loop_count != 1 from the chain YAML's `loop:` field even when
    # --loop wasn't passed. We promote `looping` to True on the first iter
    # banner we observe (the chain runner only prints that banner when its
    # resolved loop_count != 1), so YAML-defined loops are detected
    # transparently without re-resolving the chain definition here.
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
        f"chain-driver: session START — {label}\n"
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
                f"chain-driver [{label}]: iteration {n} closed "
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
                f"chain-driver [{label}]: iteration {n} closed but MANIFEST.json "
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
            f"chain-driver [{label}]: iter {n} CLOSE\n"
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
                    f"chain-driver [{label}]: HALT requested — {halt_reason}\n"
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
                # Banner presence is authoritative: the chain runner only
                # prints `===== iteration N =====` when its resolved
                # loop_count != 1. Set BEFORE _finalize_iteration so the
                # iter_NN/MANIFEST.json path + per-iter verdict path are
                # used instead of the flat top-level layout.
                looping = True
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
                    f"chain-driver [{label}]: RATE-LIMIT pause\n"
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
                        f"chain-driver [{label}]: RATE-LIMIT abort\n"
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
                    f"chain-driver [{label}]: rate-limit RESUME\n"
                    f"skill resumed: /{pause_active.get('skill')}\n"
                    f"at: {_utc_iso()}"
                )
                telegram.send(resume_msg, label="rate-limit-resume")
                pause_active = None
                continue
    except KeyboardInterrupt:
        # User Ctrl-C on the chain driver - propagate cleanly to the child.
        halt_reason = halt_reason or "chain driver received SIGINT"
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

    # Phase 18 + 18.8 fix: release our refcount slot; stop the worker only when
    # this is the last registered driver (refcount drops to 0).  Belt-and-
    # suspenders: if the count is still >0 but no other drive-chain.py for this
    # persona is alive in /proc, the previous owner crashed and left a stale
    # count — we stop anyway and log the anomaly.
    if worker_registered and worker_descriptor is not None:
        remaining = _refcount_op(-1)
        should_stop = remaining <= 0
        if not should_stop and persona is not None:
            if not _any_other_driver_using_persona(persona, os.getpid()):
                should_stop = True
                print(
                    f"[chain-driver] stale refcount ({remaining}); "
                    f"no other drive-chain.py for persona '{persona}' alive — "
                    f"stopping worker.",
                    file=sys.stderr, flush=True,
                )
        if should_stop:
            _stop_worker(worker_descriptor)
            print(
                f"[chain-driver] worker stopped: tmux session "
                f"'{worker_descriptor.get('name')}'",
                file=sys.stderr, flush=True,
            )
        else:
            print(
                f"[chain-driver] worker left running: "
                f"{remaining} other registered driver(s) still active.",
                file=sys.stderr, flush=True,
            )

    # Read top-level manifest for the session-end summary.
    top_manifest_path = log_dir / "MANIFEST.json" if log_dir else None
    top_manifest = _read_manifest(top_manifest_path) if top_manifest_path else None

    completed = (top_manifest or {}).get("loop", {}).get("completed") if top_manifest else None
    if completed is None:
        completed = iters_finalized

    final_lines = [
        f"chain-driver: session END - {label}",
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
