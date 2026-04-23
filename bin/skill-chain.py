#!/usr/bin/env python3
"""
Run one or more agent skills in sequence, streaming prettified output.

Usage:
    skill-chain.py [--log-dir <dir>] [--chain-name <name>] [--harness <name>] <skill> [<skill> ...]

Each skill runs as its own subprocess of the configured agent harness.
Skills are chained with shell-style && semantics: non-zero exit aborts
the chain.

Designed for autonomous long-running skills (e.g. /dev-cycle, /dev-review).
Renders assistant text, tool calls, and session summaries so you can follow
progress at a glance.

When --log-dir is set (or omitted, in which case the script auto-creates
./.skill-runs/<UTC>_<chain-name>/), the chain also writes:
  - <i>_<skill>.jsonl  raw stream events from the harness
  - <i>_<skill>.txt    ANSI-stripped prettified transcript (what you saw)
  - MANIFEST.json      chain metadata + per-skill exit/duration/usage + git SHAs

Harness abstraction
-------------------
The MVP ships with a single harness implementation ("claude-code"), but the
chain is structured so dropping in another harness (Codex CLI, Gemini CLI,
Cursor headless, etc.) is a matter of adding a class and registering it in
HARNESSES. Select with --harness or the AGENT_HARNESS env var.

The event renderer below currently assumes the harness emits
Anthropic-stream-json-shaped events (one JSON object per line, with type
fields like "system", "assistant", "user", "result"). When adding a new
harness with a different event shape, give it a `parse_event` method that
maps its native format to the same internal event dict, or replace the
renderer with a harness-specific one.
"""

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ---- ANSI styling -----------------------------------------------------------
RESET   = "\033[0m"
DIM     = "\033[2m"
BOLD    = "\033[1m"
MAGENTA = "\033[1;35m"   # assistant text (thinking/speech)
GREEN   = "\033[1;32m"   # Bash
CYAN    = "\033[1;36m"   # Read/Grep/Glob
YELLOW  = "\033[1;33m"   # Edit/Write/NotebookEdit
BLUE    = "\033[1;34m"   # Task/sub-agent
PURPLE  = "\033[1;95m"   # Skill invocation
RED     = "\033[1;31m"   # errors
ORANGE  = "\033[33m"    # warnings
GRAY    = "\033[38;5;244m"

TOOL_COLORS = {
    "Bash":         GREEN,
    "Read":         CYAN,
    "Grep":         CYAN,
    "Glob":         CYAN,
    "WebFetch":     CYAN,
    "WebSearch":    CYAN,
    "Edit":         YELLOW,
    "Write":        YELLOW,
    "NotebookEdit": YELLOW,
    "Task":         BLUE,
    "Agent":        BLUE,
    "Skill":        PURPLE,
    "TodoWrite":    GRAY,
    "ToolSearch":   GRAY,
    "ScheduleWakeup": GRAY,
}

INPUT_MAX = 500  # per-tool-call input truncation


# ---- Harness abstraction ---------------------------------------------------

class Harness:
    """Spawns one skill invocation as a subprocess that emits one event per stdout line.

    Subclasses must set `name` and implement `build_command(skill_name)`.
    """

    name: str = "abstract"

    def build_command(self, skill_name: str) -> list[str]:
        raise NotImplementedError


class ClaudeCodeHarness(Harness):
    """Anthropic Claude Code CLI as the agent harness."""

    name = "claude-code"

    def build_command(self, skill_name: str) -> list[str]:
        prompt = (
            f"Use the Skill tool to invoke the '{skill_name}' skill and run it "
            f"to completion. Do not respond with anything else first; invoke the "
            f"skill immediately."
        )
        return [
            "claude",
            "--dangerously-skip-permissions",
            "--model", "opus",
            "-p",
            "--verbose",
            "--output-format", "stream-json",
            prompt,
        ]


HARNESSES: dict[str, type[Harness]] = {
    "claude-code": ClaudeCodeHarness,
}


def get_harness(name: str | None = None) -> Harness:
    """Resolve a harness by name. Defaults to $AGENT_HARNESS or 'claude-code'."""
    if name is None:
        name = os.environ.get("AGENT_HARNESS", "claude-code")
    if name not in HARNESSES:
        supported = ", ".join(sorted(HARNESSES))
        raise SystemExit(f"unknown harness '{name}'; supported: {supported}")
    return HARNESSES[name]()


# ---- ANSI stripping (for log files) ----------------------------------------
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# ---- Output sink: tees to terminal (with color) and file (stripped) --------
class _Sink:
    """Writes prettified output to stdout (with ANSI) and to a per-skill txt file (stripped)."""

    def __init__(self, txt_path: Path | None = None):
        self.txt_path = txt_path
        self._fh = txt_path.open("w", encoding="utf-8") if txt_path else None

    def write(self, line: str) -> None:
        print(line, flush=True)
        if self._fh is not None:
            self._fh.write(_strip_ansi(line) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


def c(text: str, col: str) -> str:
    return f"{col}{text}{RESET}"


def summarize_input(name: str, inp: dict) -> str:
    """One-line human summary of the tool call's input."""
    if name == "Bash":
        return _truncate(inp.get("command", ""))
    if name == "Read":
        fp = inp.get("file_path", "")
        off = inp.get("offset")
        lim = inp.get("limit")
        if off is not None or lim is not None:
            return f"{fp}  [offset={off} limit={lim}]"
        return fp
    if name == "Grep":
        path = inp.get("path", ".")
        return f"{inp.get('pattern', '')}  in {path}"
    if name == "Glob":
        return inp.get("pattern", "")
    if name == "WebFetch":
        return f"{inp.get('url', '')}  // {_truncate(inp.get('prompt', ''), 120)}"
    if name == "WebSearch":
        return inp.get("query", "")
    if name in ("Edit", "Write", "NotebookEdit"):
        return inp.get("file_path", "")
    if name == "Skill":
        return inp.get("skill", "")
    if name in ("Task", "Agent"):
        sub = inp.get("subagent_type") or "default"
        desc = inp.get("description", "")
        return f"[{sub}] {desc}"
    if name == "TodoWrite":
        todos = inp.get("todos", [])
        if not todos:
            return "(empty)"
        first = todos[0].get("content", "")
        return f"{len(todos)} todos -- first: {_truncate(first, 160)}"
    if name == "ToolSearch":
        return inp.get("query", "")
    if name == "ScheduleWakeup":
        return f"{inp.get('delaySeconds', '?')}s -- {inp.get('reason', '')}"
    return _truncate(json.dumps(inp, separators=(",", ":")))


def _truncate(s: str, maximum: int = INPUT_MAX) -> str:
    if len(s) > maximum:
        return s[:maximum] + "..."
    return s


def print_assistant_text(sink: _Sink, text: str) -> None:
    body = text.rstrip()
    if not body:
        return
    sink.write("")
    sink.write(c(body, MAGENTA))
    sink.write("")


def print_tool_use(sink: _Sink, name: str, inp: dict) -> None:
    col = TOOL_COLORS.get(name, GRAY)
    summary = summarize_input(name, inp)
    arrow = c("->", DIM)
    name_fmt = c(name, col)

    if "\n" in summary:
        first, rest = summary.split("\n", 1)
        sink.write(f"{arrow} {name_fmt}  {c(first, DIM)}")
        for line in rest.splitlines():
            sink.write(f"     {c(line, DIM)}")
    else:
        sink.write(f"{arrow} {name_fmt}  {c(summary, DIM)}")


def print_tool_result(sink: _Sink, content: Any, is_error: bool) -> None:
    if not is_error:
        return
    text = content if isinstance(content, str) else json.dumps(content)
    first_line = text.splitlines()[0] if text else ""
    sink.write(f"     {c('X ' + _truncate(first_line, 300), RED)}")


def print_result_summary(sink: _Sink, event: dict) -> None:
    dur_ms = event.get("duration_ms") or 0
    cost   = event.get("total_cost_usd") or 0
    turns  = event.get("num_turns", 0)
    sub    = event.get("subtype", "")
    err    = event.get("is_error", False)
    usage  = event.get("modelUsage", {}) or {}

    status = c("[FAIL]", RED) if err else c("[ok]", GREEN)
    meta = c(f"{dur_ms/1000:.1f}s * {turns} turns * ${cost:.4f}  ({sub})", DIM)
    sink.write("")
    sink.write(f"{status}  {meta}")
    for model, u in usage.items():
        inp      = u.get("inputTokens", 0)
        cache_r  = u.get("cacheReadInputTokens", 0)
        cache_c  = u.get("cacheCreationInputTokens", 0)
        out      = u.get("outputTokens", 0)
        cost_m   = u.get("costUSD", 0)
        sink.write(
            f"  {c(model, DIM)}: "
            f"{c(f'{inp:,} in', DIM)} * "
            f"{c(f'{cache_r:,} cache-read', DIM)} * "
            f"{c(f'{cache_c:,} cache-write', DIM)} * "
            f"{c(f'{out:,} out', DIM)} * "
            f"{c(f'${cost_m:.4f}', DIM)}"
        )


def handle_event(sink: _Sink, event: dict, skill_record: dict) -> None:
    t = event.get("type")

    if t == "system" and event.get("subtype") == "init":
        sid   = (event.get("session_id", "") or "")[:8]
        cwd   = event.get("cwd", "")
        model = event.get("model", "")
        skill_record["session_id"] = event.get("session_id", "")
        skill_record["model"] = model
        sink.write(
            f"{c('>>', BLUE)} "
            f"{c(f'session {sid}', DIM)} * "
            f"{c(model, DIM)} * "
            f"{c(cwd, DIM)}"
        )
        return

    if t == "assistant":
        for block in event.get("message", {}).get("content", []):
            bt = block.get("type")
            if bt == "text":
                print_assistant_text(sink, block.get("text", ""))
            elif bt == "tool_use":
                print_tool_use(sink, block.get("name", "?"), block.get("input", {}))
        return

    if t == "user":
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_result":
                print_tool_result(sink, block.get("content"), block.get("is_error", False))
        return

    if t == "rate_limit_event":
        info = event.get("rate_limit_info", {})
        util = info.get("utilization", 0) * 100
        rtype = info.get("rateLimitType", "?")
        stat = info.get("status", "?")
        sink.write(f"     {c(f'! rate-limit {rtype}: {util:.0f}% ({stat})', ORANGE)}")
        return

    if t == "result":
        print_result_summary(sink, event)
        skill_record["result_subtype"]   = event.get("subtype", "")
        skill_record["is_error"]         = bool(event.get("is_error", False))
        skill_record["total_cost_usd"]   = event.get("total_cost_usd") or 0
        skill_record["num_turns"]        = event.get("num_turns", 0)
        skill_record["duration_ms"]      = event.get("duration_ms") or 0
        skill_record["model_usage"]      = event.get("modelUsage", {}) or {}
        return


def run_skill(harness: Harness, skill_name: str, index: int, log_dir: Path | None) -> tuple[int, dict]:
    """Run one skill via the configured harness. Returns (exit_code, manifest_record)."""
    cmd = harness.build_command(skill_name)

    txt_path: Path | None = None
    jsonl_path: Path | None = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{index:02d}_{skill_name}"
        txt_path = log_dir / f"{stem}.txt"
        jsonl_path = log_dir / f"{stem}.jsonl"

    sink = _Sink(txt_path)
    jsonl_fh = jsonl_path.open("w", encoding="utf-8") if jsonl_path else None

    skill_record: dict = {
        "index": index,
        "name": skill_name,
        "harness": harness.name,
        "started_at": _utc_iso(),
        "log_jsonl": jsonl_path.name if jsonl_path else None,
        "log_txt": txt_path.name if txt_path else None,
    }

    banner = c(f"===== /{skill_name} =====", BOLD + MAGENTA)
    sink.write("")
    sink.write(banner)
    sink.write("")

    started = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if jsonl_fh is not None:
                jsonl_fh.write(line + "\n")
                jsonl_fh.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                sink.write(c(line, GRAY))
                continue
            try:
                handle_event(sink, event, skill_record)
            except Exception as exc:
                sink.write(f"{c(f'[render error: {exc}]', RED)}  {_truncate(line, 300)}")
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        sink.write("")
        sink.write(c("[interrupted]", ORANGE))
        rc = 130
    else:
        rc = proc.wait()

    elapsed = time.monotonic() - started
    skill_record["finished_at"] = _utc_iso()
    skill_record["wall_seconds"] = round(elapsed, 1)
    skill_record["exit_code"] = rc

    sink.close()
    if jsonl_fh is not None:
        jsonl_fh.close()

    return rc, skill_record


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_dirname() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _git_sha(cwd: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSFERABLE_CHAINS_DIR = REPO_ROOT / "chains"


def load_chain(name: str, cwd: str) -> dict:
    """Resolve a chain definition by name.

    Lookup order:
      1. <cwd>/.claude/chains/<name>.yaml  (proprietary)
      2. <repo>/chains/<name>.yaml         (transferable)

    Returns the parsed dict. Raises SystemExit on miss or invalid shape.
    """
    candidates = [
        Path(cwd) / ".claude" / "chains" / f"{name}.yaml",
        TRANSFERABLE_CHAINS_DIR / f"{name}.yaml",
    ]
    for path in candidates:
        if path.exists():
            try:
                import yaml
            except ImportError:
                raise SystemExit("--chain requires PyYAML (`pip install pyyaml`)")
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict) or "skills" not in data:
                raise SystemExit(f"chain {path} is missing required 'skills' field")
            data["_source"] = str(path)
            return data
    raise SystemExit(
        f"chain {name!r} not found. Looked in:\n  " +
        "\n  ".join(str(p) for p in candidates)
    )


def find_local_supervisor(cwd: str) -> str | None:
    """Discover a project-local supervisor skill: <cwd>/.claude/skills/*-supervisor/SKILL.md.

    Returns the skill name (folder name) if exactly one is found; None otherwise.
    Multiple matches: prints a warning and returns None (the chain runs without
    auto-supervisor; the user can still pass it explicitly).
    """
    skills_dir = Path(cwd) / ".claude" / "skills"
    if not skills_dir.is_dir():
        return None
    candidates = [
        d for d in skills_dir.iterdir()
        if d.is_dir() and d.name.endswith("-supervisor") and (d / "SKILL.md").exists()
    ]
    if not candidates:
        return None
    if len(candidates) > 1:
        names = ", ".join(sorted(d.name for d in candidates))
        print(c(f"[supervisor] multiple supervisor skills found ({names}); "
                f"auto-append disabled, pass one explicitly.", ORANGE), flush=True)
        return None
    return candidates[0].name


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="skill-chain.py",
        description="Run agent skills in sequence with prettified output and per-job log capture.",
    )
    p.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Directory to write run logs (MANIFEST.json + per-skill .jsonl/.txt). "
             "Defaults to ./.skill-runs/<UTC>_<chain-name>/ unless --no-log is set.",
    )
    p.add_argument(
        "--no-log",
        action="store_true",
        help="Disable log capture entirely (terminal output only).",
    )
    p.add_argument(
        "--chain-name",
        default=None,
        help="Label for the chain (used in default log dir name). "
             "Defaults to the first skill's name.",
    )
    p.add_argument(
        "--harness",
        default=None,
        help="Agent harness to use. Default: $AGENT_HARNESS, else 'claude-code'. "
             f"Supported: {', '.join(sorted(HARNESSES))}.",
    )
    p.add_argument(
        "--no-supervisor",
        action="store_true",
        help="Skip the auto-appended project-local supervisor skill "
             "(<cwd>/.claude/skills/*-supervisor/). On by default when a supervisor exists.",
    )
    p.add_argument(
        "--chain",
        default=None,
        help="Run a named chain definition instead of an inline skill list. "
             "Looks in <cwd>/.claude/chains/<name>.yaml first, then "
             "<repo>/chains/<name>.yaml. Mutually exclusive with positional "
             "skills argument.",
    )
    p.add_argument(
        "skills",
        nargs="*",
        help="One or more skill names to run in sequence. Omit when --chain is set.",
    )
    return p.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    harness = get_harness(args.harness)

    cwd = os.getcwd()

    # Resolve skills + chain name from either --chain or the positional list.
    chain_def: dict | None = None
    if args.chain and args.skills:
        raise SystemExit("--chain and positional skills are mutually exclusive")
    if args.chain:
        chain_def = load_chain(args.chain, cwd)
        skills_arg = list(chain_def["skills"])
        chain_name = args.chain_name or chain_def.get("name") or args.chain
        if not args.no_supervisor and chain_def.get("auto-supervisor") is False:
            args.no_supervisor = True
    else:
        if not args.skills:
            raise SystemExit("provide either --chain <name> or one or more skill names")
        skills_arg = list(args.skills)
        chain_name = args.chain_name or skills_arg[0]
    args.skills = skills_arg  # for downstream code that references args.skills

    log_dir: Path | None
    if args.no_log:
        log_dir = None
    elif args.log_dir is not None:
        log_dir = args.log_dir.resolve()
    else:
        log_dir = (Path(cwd) / ".skill-runs" / f"{_utc_dirname()}_{chain_name}").resolve()

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        print(c(f"[log-dir] {log_dir}", DIM), flush=True)
    print(c(f"[harness] {harness.name}", DIM), flush=True)
    if chain_def is not None:
        print(c(f"[chain]   {chain_def.get('name', args.chain)}  "
                f"(from {chain_def.get('_source', '?')})", DIM), flush=True)

    # Auto-append a project-local supervisor (e.g. <cwd>/.claude/skills/<project>-supervisor/)
    # if one exists and the user didn't already include it in the chain.
    skills_to_run = list(args.skills)
    auto_supervisor: str | None = None
    if not args.no_supervisor:
        auto_supervisor = find_local_supervisor(cwd)
        if auto_supervisor and auto_supervisor not in skills_to_run:
            skills_to_run.append(auto_supervisor)
            print(c(f"[supervisor] auto-appended '{auto_supervisor}' "
                    f"(disable with --no-supervisor)", DIM), flush=True)

    manifest: dict = {
        "chain_name": chain_name,
        "chain_definition": chain_def.get("_source") if chain_def else None,
        "chain_transferable_parent": chain_def.get("transferable") if chain_def else None,
        "harness": harness.name,
        "skills_requested": list(args.skills),
        "skills_run": skills_to_run,
        "auto_supervisor": auto_supervisor,
        "started_at": _utc_iso(),
        "cwd": cwd,
        "git_sha_before": _git_sha(cwd),
        "skills": [],
    }

    final_rc = 0
    for i, skill in enumerate(skills_to_run):
        rc, record = run_skill(harness, skill, i, log_dir)
        # Mark whether this slot is the supervisor (informational; helps the manager).
        if skill == auto_supervisor:
            record["role"] = "supervisor"
        manifest["skills"].append(record)
        if rc != 0:
            # Supervisor failure should NOT abort downstream work or surface as the
            # chain's exit code, since the cycle's real work already shipped. Surface
            # it but keep the chain green.
            if skill == auto_supervisor:
                print(c(f"\n[supervisor] {skill} exited with {rc}; "
                        f"continuing (chain remains successful)", ORANGE), flush=True)
                continue
            print(f"\n{c(f'/{skill} exited with {rc}; aborting chain', RED)}", flush=True)
            final_rc = rc
            break

    manifest["finished_at"] = _utc_iso()
    manifest["git_sha_after"] = _git_sha(cwd)
    manifest["exit_code"] = final_rc

    if log_dir is not None:
        (log_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    return final_rc


if __name__ == "__main__":
    sys.exit(main())
