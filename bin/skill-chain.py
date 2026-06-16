#!/usr/bin/env python3
"""
Run one or more agent skills in sequence, streaming prettified output.

Usage:
    skill-chain.py [--log-dir <dir>] [--chain-name <name>] [--harness <name>]
                   [--loop <N>] [--loop-delay <seconds>]
                   [--on-rate-limit <fail|pause|pause-with-cap>]
                   [--max-rate-limit-pause-seconds <N>]
                   [--max-pauses-per-session <N>]
                   <skill> [<skill> ...]

Each skill runs as its own subprocess of the configured agent harness.
Skills are chained with shell-style && semantics: non-zero exit aborts
the chain.

Designed for autonomous long-running skills (e.g. /dev-cycle, /dev-review).
Renders assistant text, tool calls, and session summaries so you can follow
progress at a glance.

Looping: --loop N (or the chain YAML's `loop:` field) runs the full skill
sequence N times. --loop 0 loops until a non-supervisor skill fails or the
user interrupts with Ctrl-C. --loop-delay inserts a sleep between iterations.
When looping, each iteration's logs land in its own <log-dir>/iter_NN/
subdir with its own MANIFEST.json; the top-level MANIFEST.json records the
iteration summaries.

Rate-limit pause-and-resume: a multi-iteration run can cross the rolling
5h Anthropic quota window mid-flight. When the harness emits a
`rate_limit_event` with `status=exceeded` (or the subprocess dies with a
recognizable rate-limit error), --on-rate-limit (default `pause`) sleeps
until the parsed reset_time + jitter and re-invokes the killed skill from
scratch. Each retry archives the prior attempt's .txt/.jsonl with a
`.retry-N` suffix so the audit trail is preserved. `pause-with-cap` falls
back to `fail` when a single pause would exceed
--max-rate-limit-pause-seconds. --max-pauses-per-session aborts the chain
after N pauses on the same skill (repeated pauses suggest a quota-burning
loop, not a genuine window crossing).

When --log-dir is set (or omitted, in which case the script auto-creates
./.skill-runs/<UTC>_<chain-name>/), the chain also writes:
  - <i>_<skill>.jsonl  raw stream events from the harness
  - <i>_<skill>.txt    ANSI-stripped prettified transcript (what you saw)
  - MANIFEST.json      chain metadata + per-skill exit/duration/usage + git SHAs
                       (for --loop != 1: top-level manifest carries an
                       `iterations` array; per-iteration details are in
                       iter_NN/MANIFEST.json)

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
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTIFY_TELEGRAM = REPO_ROOT / "bin" / "notify-telegram.sh"
TRANSFERABLE_CHAINS_DIR = REPO_ROOT / "chains"

# Persona profile keys consumed from a `<persona>-chain-driver/SKILL.md`
# "Configured defaults" yaml block. Each maps to the corresponding native CLI
# arg as a layer BELOW it (explicit CLI flag wins). --profile gives the
# unified runner the same defaults resolution the slash-command chain-driver
# agent applies on its own. (Merged natively from the former drive-chain.py
# wrapper in Phase 42.)
PROFILE_KEYS = (
    "watched-chain",
    "default-loop",
    "default-max-budget-usd",
    "default-max-cycles",
    "telegram-env",
    "label",
)

# Named presets (extensible). Each entry maps to the flag values it expands to
# and an optional `requires_cap` sentinel. `--overnight` is the initial preset;
# additional presets can be registered here without changing the dispatch logic.
PRESETS: dict = {
    "overnight": {
        "loop": 0,
        "loop_delay_random": "300,1800",
        "requires_cap": True,
    },
}

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


# ---- Rate-limit pause-and-resume -------------------------------------------
# Phase 13: when the harness emits a `rate_limit_event` with one of these
# statuses, the run_skill_with_retry wrapper pauses until the parsed reset
# time and re-invokes the killed skill from scratch. The text-based fallback
# regex catches the case where the subprocess died from a rate-limit error
# before emitting a clean event (the patterns appear in the merged stderr
# stream, which the runner already tees through stdout).

RATE_LIMIT_FATAL_STATUSES = frozenset({
    "exceeded", "blocked", "reset_required", "throttled", "rejected",
})

RATE_LIMIT_TEXT_RE = re.compile(
    r"\b(?:rate[\s-]*limit(?:ed|s|ing)?\b.{0,40}\b(?:exceeded|reached|reset)\b"
    r"|you'?ve hit your\s+\w+\s+rate limit"
    r"|hit your.{0,20}usage limit"
    r"|you'?re out of (?:extra )?usage)",
    re.IGNORECASE,
)

RATE_LIMIT_RESET_RE = re.compile(
    r"(\d{1,2}:\d{2}\s*(?:am|pm)\s*\([^)]+\))",
    re.IGNORECASE,
)

DEFAULT_ON_RATE_LIMIT = "pause"
DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS = 28800   # 8h, covers 5h rolling + headroom
DEFAULT_MAX_PAUSES_PER_SESSION = 3
# Inter-iteration human-like delay applied when neither CLI nor chain YAML
# specifies loop-delay or loop-delay-random. 5-30min jitter keeps commit
# cadence indistinguishable from a human workflow. Opt out per-run with
# `--loop-delay 0` or per-chain with `loop-delay: 0` in YAML.
DEFAULT_LOOP_DELAY_RANDOM = (300.0, 1800.0)
RATE_LIMIT_JITTER_RANGE = (15, 60)              # extra seconds after parsed reset
RATE_LIMIT_FALLBACK_BACKOFF_SECONDS = 300       # initial backoff when no reset_time


# ---- No-work sentinel (Phase 17) -------------------------------------------
# When a skill (typically a dev cycle in steady state) finds nothing to do and
# prints `[no-work] <one-line reason>` as its own assistant-text line before
# exiting 0, the chain runner aborts the loop entirely (skipping the remaining
# skills in the iteration AND any further iterations). Saves the per-iter
# overhead of running review/supervisor against an empty commit, and stops an
# unattended overnight `loop: 0` run from burning the budget cap on
# speculative work in steady state. The bail is correct framework behavior,
# not a defect; sentinel format is documented in templates/SPEC.md so any
# consuming project's dev skill can opt into the contract by emitting it.

NO_WORK_SENTINEL_RE = re.compile(r"^\s*\[no-work\](?:\s+(.*\S))?\s*$", re.MULTILINE)

# ---- Blocked-on-human sentinel (Phase 31.8) ---------------------------------
# When a dev-cycle skill scans docs/HUMAN.md and finds that its picked SPEC
# item is listed in a Blocking entry's `Blocks:` line, it prints
# `[blocked-on-human] <H-ID> <title>` and exits 0. The chain runner aborts
# the iteration (skipping review/supervisor) and terminates the loop, recording
# `terminated_by: "blocked_on_human"` in the top-level loop manifest so the
# chain driver's session-end report can surface the reason clearly.
BLOCKED_ON_HUMAN_SENTINEL_RE = re.compile(
    r"^\s*\[blocked-on-human\](?:\s+(.*\S))?\s*$", re.MULTILINE
)

# ---- Skip-tester sentinel (Phase 41.10) -------------------------------------
# When a dev-cycle skill's work has no front-end/UI surface it prints
# `[skip-tester] <reason>` as its final line and exits. The chain runner
# checks whether the immediately-following skill's name ends in `-tester`; if
# so it skips that skill (never spawns it) and proceeds to the next skill in
# the list (typically sst-dev-review). The skip + reason are recorded in the
# iter manifest under `tester_skipped`. A non-tester immediate follower is
# never skipped, even if the sentinel was emitted.
SKIP_TESTER_SENTINEL_RE = re.compile(
    r"^\s*\[skip-tester\](?:\s+(.*\S))?\s*$", re.MULTILINE
)

# ---- Per-skill model + effort routing (Phase 19) ---------------------------
# Each iter pre-parses the picked item's difficulty bracket from
# docs/TODO.md > Next up (or docs/SPEC.md first open `[ ]` if Next up is empty),
# mapping `[easy]` -> (haiku, low), `[medium]` -> (sonnet, medium),
# `[hard]` -> (opus, high). Each skill's frontmatter declares a model-floor
# and effort-floor; effective tier = max(item_tier, skill_floor) over the
# orderings below. After the FIRST skill of an iter (typically the dev) exits,
# the runner scans its assistant text for `[picked-difficulty: <tier>]`; a
# match overrides the iter difficulty for any subsequent skill in the same
# iter, so review/supervisor route on what the dev actually picked rather
# than the queue head.

MODEL_TIERS  = ["haiku", "sonnet", "opus"]
EFFORT_TIERS = ["low", "medium", "high", "xhigh", "max"]

DIFFICULTY_TO_MODEL  = {"easy": "haiku",  "medium": "sonnet", "hard": "opus"}
DIFFICULTY_TO_EFFORT = {"easy": "low",    "medium": "medium", "hard": "high"}

DEFAULT_MODEL_FLOOR  = "opus"
DEFAULT_EFFORT_FLOOR = "high"
DEFAULT_DIFFICULTY   = "medium"

PICKED_DIFFICULTY_SENTINEL_RE = re.compile(
    r"^\s*\[picked-difficulty:\s*(easy|medium|hard)\]\s*$",
    re.MULTILINE | re.IGNORECASE,
)

_NEXT_UP_HEADER_RE = re.compile(r"^##\s+Next up\b", re.MULTILINE)
_HEADING_RE        = re.compile(r"^##\s+", re.MULTILINE)
_HTML_COMMENT_RE   = re.compile(r"<!--.*?-->", re.DOTALL)
_DIFFICULTY_BRACKET_RE = re.compile(r"\[(easy|medium|hard)\]", re.IGNORECASE)


def _max_tier(item_tier: str, floor_tier: str, ordering: list[str]) -> str:
    """Return whichever of item_tier / floor_tier has the higher index in ordering.

    Unknown tiers (typo, future value) sort as -1 so a known floor still wins.
    Falls back to the floor when both are unknown so the framework defaults
    apply rather than passing junk to the harness.
    """
    a = ordering.index(item_tier)  if item_tier  in ordering else -1
    b = ordering.index(floor_tier) if floor_tier in ordering else -1
    if a < 0 and b < 0:
        return ordering[-1]  # safest: highest tier
    return ordering[max(a, b)]


def _find_skill_md(skill_name: str, cwd: str) -> Path | None:
    """Locate the SKILL.md the harness will load for this skill.

    Mirrors Claude Code's resolution order: project-scoped first
    (<cwd>/.claude/skills/<name>/SKILL.md), then personal-global
    (~/.claude/skills/<name>/SKILL.md). Returns None when neither exists; the
    caller treats that as "no frontmatter" and falls back to defaults rather
    than failing — a missing SKILL.md will surface as a harness error on the
    actual skill invocation a moment later.
    """
    candidates = [
        Path(cwd) / ".claude" / "skills" / skill_name / "SKILL.md",
        Path.home() / ".claude" / "skills" / skill_name / "SKILL.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _read_skill_frontmatter(path: Path | None) -> dict:
    """Parse the YAML frontmatter block at the top of a SKILL.md. Returns {}
    when the file is missing, lacks a `---\\n…\\n---\\n` block, or YAML can't
    be loaded. Best-effort by design: routing falls back to defaults rather
    than failing the chain on a malformed skill file.
    """
    if path is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    try:
        import yaml
        data = yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_iter_difficulty(cwd: str) -> tuple[str, str]:
    """Pre-parse the next item's difficulty for routing. Returns (tier, source).

    Source codes (for stderr reporting + manifest forensics):
      - 'todo-next-up'             — first item in `## Next up` carried a label
      - 'todo-next-up-unlabeled'   — first item lacked a label; defaulted
      - 'spec-first-open'          — Next up empty; first SPEC `[ ]` had a label
      - 'spec-first-open-unlabeled'— first open SPEC item lacked a label; defaulted
      - 'no-source'                — neither file resolvable; defaulted

    The `*-unlabeled` and `no-source` cases return DEFAULT_DIFFICULTY ('medium')
    so the chain proceeds rather than failing on missing labels — same
    graceful-degradation rollout window the dev skill's `[bad-label]` warn
    operates in.
    """
    todo = Path(cwd) / "docs" / "TODO.md"
    if todo.exists():
        try:
            text = todo.read_text(encoding="utf-8")
        except OSError:
            text = ""
        m = _NEXT_UP_HEADER_RE.search(text)
        if m:
            section = text[m.end():]
            end_m = _HEADING_RE.search(section)
            if end_m:
                section = section[:end_m.start()]
            section = _HTML_COMMENT_RE.sub("", section)
            for line in section.splitlines():
                s = line.strip()
                if not s.startswith("- "):
                    continue
                lm = _DIFFICULTY_BRACKET_RE.search(s)
                if lm:
                    return lm.group(1).lower(), "todo-next-up"
                return DEFAULT_DIFFICULTY, "todo-next-up-unlabeled"
    spec = Path(cwd) / "docs" / "SPEC.md"
    if spec.exists():
        try:
            text = spec.read_text(encoding="utf-8")
        except OSError:
            text = ""
        for line in text.splitlines():
            m = re.match(r"^\s*-\s+\[ \]\s+\[(easy|medium|hard)\]", line, re.IGNORECASE)
            if m:
                return m.group(1).lower(), "spec-first-open"
            if re.match(r"^\s*-\s+\[ \]", line):
                return DEFAULT_DIFFICULTY, "spec-first-open-unlabeled"
    return DEFAULT_DIFFICULTY, "no-source"


def _resolve_skill_route(
    skill_name: str,
    iter_difficulty: str,
    cwd: str,
) -> tuple[str, str, dict]:
    """Compute (effective_model, effective_effort, route_record) for a skill.

    route_record is a small dict suitable for stashing on the skill_record /
    iter_manifest so post-hoc analysis (supervisor, chain driver) can see how
    the routing decision was made for each skill in the iter.
    """
    fm = _read_skill_frontmatter(_find_skill_md(skill_name, cwd))
    model_floor  = fm.get("model-floor")  or DEFAULT_MODEL_FLOOR
    effort_floor = fm.get("effort-floor") or DEFAULT_EFFORT_FLOOR
    item_model   = DIFFICULTY_TO_MODEL.get(iter_difficulty,  DIFFICULTY_TO_MODEL[DEFAULT_DIFFICULTY])
    item_effort  = DIFFICULTY_TO_EFFORT.get(iter_difficulty, DIFFICULTY_TO_EFFORT[DEFAULT_DIFFICULTY])
    eff_model    = _max_tier(item_model,  model_floor,  MODEL_TIERS)
    eff_effort   = _max_tier(item_effort, effort_floor, EFFORT_TIERS)
    record = {
        "difficulty":     iter_difficulty,
        "model_floor":    model_floor,
        "effort_floor":   effort_floor,
        "item_model":     item_model,
        "item_effort":    item_effort,
        "effective_model":  eff_model,
        "effective_effort": eff_effort,
    }
    return eff_model, eff_effort, record


def _no_work_bail_should_fire(
    record: dict,
    sha_before: str | None,
    sha_after: str | None,
) -> bool:
    """Return True iff the skill's `[no-work]` sentinel should abort the loop.

    A commit landing during the skill (sha_before != sha_after, both known)
    means real work shipped: the sentinel was a false-positive (e.g. the dev
    skill quoting its own bail prose mid-reasoning, or a code block with an
    example sentinel line). When git SHAs are unavailable (non-git harness or
    `git rev-parse` failure on either side), trust the sentinel: the dev
    skill is the authority on its own steady-state, and gating bails on a
    SHA-comparison we can't perform would silently break the contract on
    consumers that don't run under git.
    """
    if not record.get("no_work_bail"):
        return False
    if sha_before is not None and sha_after is not None and sha_before != sha_after:
        return False
    return True


def _incomplete_cycle_detected(cwd: str) -> bool:
    """Phase 36: return True when docs/TODO.md indicates an incomplete dev cycle.

    Two signals:
    - 'Sanitize: must-fix=PENDING' anywhere in the file (Defense 4 reorder
      left the placeholder unfilled).
    - '## In flight' section contains a '- [' bullet (the dev wrote an
      In-flight line but never cleared it before exiting).

    Only called when git SHA is available and shows no commit (sha_before ==
    sha_after), so the cost of reading one file is always justified.
    """
    todo_path = Path(cwd) / "docs" / "TODO.md"
    if not todo_path.exists():
        return False
    text = todo_path.read_text(encoding="utf-8")
    if "Sanitize: must-fix=PENDING" in text:
        return True
    # Parse ## In flight section; a live entry starts with '- ['
    m = re.search(
        r"^##\s+In flight\s*\n(.*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if m:
        # Strip HTML comments so template prose inside <!-- --> doesn't match
        body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.DOTALL)
        if re.search(r"^\s*-\s+\[", body, re.MULTILINE):
            return True
    return False


def _contract_violation_aborts(iter_manifest: dict, cwd: str) -> bool:
    """Phase 43 (D3/43.4) + 43.6: decide whether a recorded incomplete-cycle
    contract violation should abort the loop.

    Phase 43.4 used a HEAD-advance proxy: if git_sha_after != head_at_violation,
    some follower committed, so recovery was assumed. This was flawed: the
    auto-appended supervisor's normal commits advance HEAD even when the recovery
    follower (sst-dev-review §0.2) failed to commit, so the proxy could be satisfied
    by a supervisor-only commit, masking an unrecovered cycle.

    Fix (43.6): re-evaluate _incomplete_cycle_detected(cwd) at the loop-level abort.
    A recovery follower that succeeds MUST clear the In-flight line as part of its
    commit; the supervisor never touches In-flight state. So the actual In-flight
    state is the correct, supervisor-immune recovery signal.

    Conservative default: if docs/TODO.md is absent (non-standard setup),
    _incomplete_cycle_detected returns False, treating the cycle as recovered
    (fail-open, same as the prior missing-SHA path).
    """
    cv = iter_manifest.get("contract_violation")
    if not cv:
        return False
    # Phase 43.6: use the actual incomplete-cycle state, not the post-supervisor
    # SHA proxy from Phase 43.4.
    return _incomplete_cycle_detected(cwd)


def _parse_reset_time(value: Any) -> float | None:
    """Parse a rate-limit reset time into epoch seconds. Returns None on failure.

    Accepts ISO 8601 strings (with or without trailing Z), unix timestamps as
    int/float, numeric strings, or localized 12-hour wall-clock strings of the
    form `HH:MMam/pm (TZ-name)` (e.g. `7:50pm (Asia/Tokyo)`) — the latter is
    what the live "out of extra usage" stderr banner emits. For the wall-clock
    branch, the next occurrence of that local time is returned (today if still
    in the future, tomorrow otherwise). The harness's `rate_limit_info` payload
    uses different field names across schema versions (`resetsAt`, `reset_time`,
    `resetTime`, `resets_at`); the caller is responsible for plucking the
    candidate value before handing it here.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    # ISO 8601 with optional trailing Z
    iso = s[:-1] if s.endswith("Z") else s
    try:
        dt = _dt.datetime.fromisoformat(iso)
    except ValueError:
        dt = None
    if dt is not None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt.timestamp()
    # Localized 12-hour clock with TZ name in parens, e.g. `7:50pm (Asia/Tokyo)`.
    m = re.match(r"^(\d{1,2}):(\d{2})\s*([ap]m)\s*\(([^)]+)\)$", s, re.IGNORECASE)
    if m:
        hour = int(m.group(1)) % 12
        if m.group(3).lower() == "pm":
            hour += 12
        minute = int(m.group(2))
        tz_name = m.group(4).strip()
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tz_name)
        except Exception:
            return None
        now_local = _dt.datetime.now(tz)
        candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now_local:
            candidate += _dt.timedelta(days=1)
        return candidate.timestamp()
    # Numeric string fallback (unix epoch)
    try:
        return float(s)
    except ValueError:
        return None


def _compute_rate_limit_sleep(signal: dict, *, max_pause: int | None) -> tuple[float | None, str | None]:
    """Decide how long to sleep on a rate-limit signal. Returns (seconds, wake_iso).

    Priority: parsed reset_time > retry_after_seconds > exponential backoff.
    Adds a random jitter (15-60s) on top of the parsed reset to spread retries.
    Returns (None, None) when the computed pause exceeds max_pause; the caller
    treats that as a `fail` outcome under the `pause-with-cap` policy.
    """
    now = time.time()
    sleep_seconds: float | None = None
    if signal.get("reset_time") is not None:
        reset_epoch = _parse_reset_time(signal.get("reset_time"))
        if reset_epoch is not None:
            sleep_seconds = max(0.0, reset_epoch - now) + random.randint(*RATE_LIMIT_JITTER_RANGE)
    if sleep_seconds is None and signal.get("retry_after_seconds") is not None:
        try:
            sleep_seconds = max(0.0, float(signal["retry_after_seconds"])) + random.randint(*RATE_LIMIT_JITTER_RANGE)
        except (TypeError, ValueError):
            sleep_seconds = None
    if sleep_seconds is None:
        # Exponential-ish: caller sets the prior wait via `signal['_attempt']`.
        attempt = int(signal.get("_attempt", 0))
        sleep_seconds = float(RATE_LIMIT_FALLBACK_BACKOFF_SECONDS * (2 ** min(attempt, 4)))
    if max_pause is not None and sleep_seconds > max_pause:
        return None, None
    wake_dt = _dt.datetime.fromtimestamp(now + sleep_seconds, _dt.timezone.utc)
    return sleep_seconds, wake_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _archive_attempt(log_dir: Path | None, index: int, skill_name: str, retry_count: int) -> None:
    """Rename the prior attempt's transcript files to `.retry-N.{txt,jsonl}` so
    the canonical names are clear for the upcoming retry. Idempotent: if the
    source files don't exist (no log_dir or first attempt), this is a no-op.
    """
    if log_dir is None:
        return
    stem = f"{index:02d}_{skill_name}"
    for ext in (".txt", ".jsonl"):
        src = log_dir / f"{stem}{ext}"
        if src.exists():
            dst = log_dir / f"{stem}.retry-{retry_count}{ext}"
            try:
                src.rename(dst)
            except OSError:
                pass


# ---- Harness abstraction ---------------------------------------------------

class Harness:
    """Spawns one skill invocation as a subprocess that emits one event per stdout line.

    Subclasses must set `name` and implement `build_command(skill_name, *,
    model, effort)`. `model` and `effort` are the per-skill resolved tiers
    from Phase 19 routing; harnesses that don't honor either may ignore them.
    """

    name: str = "abstract"

    def build_command(
        self,
        skill_name: str,
        *,
        model: str | None = None,
        effort: str | None = None,
        extra_prompt: str = "",
        resume_session_id: str | None = None,
    ) -> list[str]:
        raise NotImplementedError


class ClaudeCodeHarness(Harness):
    """Anthropic Claude Code CLI as the agent harness."""

    name = "claude-code"

    def build_command(
        self,
        skill_name: str,
        *,
        model: str | None = None,
        effort: str | None = None,
        extra_prompt: str = "",
        resume_session_id: str | None = None,
    ) -> list[str]:
        if resume_session_id:
            # Resume a prior session after a rate-limit pause: send a short
            # no-op prompt so the in-flight context is restored without
            # re-triggering the skill from scratch.
            prompt = "continue"
        else:
            prompt = (
                f"Use the Skill tool to invoke the '{skill_name}' skill and run it "
                f"to completion. Do not respond with anything else first; invoke the "
                f"skill immediately."
            )
        if extra_prompt:
            prompt = prompt + "\n\n" + extra_prompt
        # Phase 19 (4): model and effort are resolved by the runner from
        # max(item_difficulty_tier, skill_floor) and passed in. Fall back to
        # the conservative framework defaults (opus / high) when either is
        # absent so direct callers (`bin/skill-chain.py <skill>` ad-hoc form)
        # still produce a working command without the routing context.
        cmd = [
            "claude",
            # bypassPermissions, not --dangerously-skip-permissions. The latter
            # empirically still prompts on writes under `.claude/skills/**` even
            # though its help text claims it bypasses all checks — which breaks
            # Phase 11's direct-overwrite path (sst-supervisor rewriting peer
            # SKILL.md files). bypassPermissions has an explicit carveout for
            # .claude/skills, .claude/commands, .claude/agents because claude
            # routinely writes there. See Claude Code permissions docs.
            "--permission-mode", "bypassPermissions",
            # --max-turns is undocumented in --help but is a real flag that
            # raises the per-invocation turn/tool-call ceiling for `-p` mode.
            # Without it, supervisor runs that do a proprietary edit +
            # transferable sanitize + transferable edit + verdict have
            # terminated cleanly at ~31 turns with `[ok]` status mid-workflow
            # (server-side pause_turn). 150 buys headroom for multi-write
            # cycles without burning cache on runaway agents. See
            # github.com/anthropics/claude-code/issues/16963.
            "--max-turns", "150",
            "--model",  model  or DEFAULT_MODEL_FLOOR,
            "--effort", effort or DEFAULT_EFFORT_FLOOR,
        ]
        if resume_session_id:
            cmd += ["--resume", resume_session_id]
        cmd += ["-p", "--verbose", "--output-format", "stream-json", prompt]
        return cmd


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
    # The harness sometimes emits subtype="success" alongside is_error=True
    # (e.g. when the subprocess died with a rate-limit but the result frame
    # still claimed lifecycle success). Tag the parenthetical so the label and
    # the subtype don't visibly contradict each other.
    sub_label = sub if (not err or sub.lower().startswith("error")) else f"error: {sub}"
    meta = c(f"{dur_ms/1000:.1f}s * {turns} turns * ${cost:.4f}  ({sub_label})", DIM)
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
                text = block.get("text", "")
                print_assistant_text(sink, text)
                # Phase 17: scan for the [no-work] sentinel. Stash on the
                # skill_record so run_iteration can abort the chain after
                # the skill exits cleanly. First match wins; later text
                # within the same skill doesn't overwrite it.
                if "no_work_bail" not in skill_record:
                    m = NO_WORK_SENTINEL_RE.search(text)
                    if m:
                        reason = (m.group(1) or "").strip() or "no reason given"
                        skill_record["no_work_bail"] = reason
                # Phase 31.8: [blocked-on-human] sentinel — dev skill found a
                # docs/HUMAN.md Blocking entry whose Blocks: line covers the
                # picked item. Abort the iteration and loop (parallel to the
                # no-work bail). First match wins; no commit expected.
                if "blocked_on_human" not in skill_record:
                    bm = BLOCKED_ON_HUMAN_SENTINEL_RE.search(text)
                    if bm:
                        reason = (bm.group(1) or "").strip() or "no reason given"
                        skill_record["blocked_on_human"] = reason
                # Phase 41.10: [skip-tester] sentinel — dev skill found no
                # front-end/UI surface, so the tester stage should be skipped.
                # First match wins; run_iteration checks this after the skill
                # exits and skips the immediately-following *-tester skill.
                if "skip_tester" not in skill_record:
                    stm = SKIP_TESTER_SENTINEL_RE.search(text)
                    if stm:
                        reason = (stm.group(1) or "").strip() or "no reason given"
                        skill_record["skip_tester"] = reason
                # Phase 19 (5): capture the dev skill's `[picked-difficulty:
                # <tier>]` sentinel so run_iteration can override the iter's
                # pre-parsed difficulty for any skill that runs after the dev.
                # First match wins; later text within the same skill doesn't
                # overwrite it. Tool inputs / results are not scanned (only
                # `block.type == "text"` reaches here), mirroring the
                # no-work sentinel's discipline.
                if "picked_difficulty" not in skill_record:
                    pm = PICKED_DIFFICULTY_SENTINEL_RE.search(text)
                    if pm:
                        skill_record["picked_difficulty"] = pm.group(1).lower()
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
        stat_raw = info.get("status", "?")
        stat = (stat_raw or "").lower()
        sink.write(f"     {c(f'! rate-limit {rtype}: {util:.0f}% ({stat_raw})', ORANGE)}")
        if stat in RATE_LIMIT_FATAL_STATUSES:
            # Capture the fatal signal so the run_skill_with_retry wrapper can
            # decide whether to pause-and-resume. Field names for the reset
            # timestamp vary across harness/schema versions; try the common ones.
            reset_raw = (
                info.get("resetsAt")
                or info.get("reset_time")
                or info.get("resetTime")
                or info.get("resets_at")
            )
            retry_after = (
                info.get("retryAfterSeconds")
                or info.get("retry_after_seconds")
                or info.get("retryAfter")
            )
            # First fatal wins: a later overlapping signal of a different tier
            # shouldn't overwrite the one that actually killed the skill.
            if "rate_limit_signal" not in skill_record:
                skill_record["rate_limit_signal"] = {
                    "type": rtype,
                    "status": stat,
                    "reset_time": reset_raw,
                    "retry_after_seconds": retry_after,
                    "observed_at": _utc_iso(),
                }
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


def run_skill(
    harness: Harness,
    skill_name: str,
    index: int,
    log_dir: Path | None,
    *,
    model: str | None = None,
    effort: str | None = None,
    extra_prompt: str = "",
    log_stem_override: str | None = None,
    resume_session_id: str | None = None,
) -> tuple[int, dict]:
    """Run one skill via the configured harness. Returns (exit_code, manifest_record).

    `model` and `effort` are the per-skill resolved tiers (Phase 19 routing);
    when omitted the harness applies its conservative defaults so direct
    `bin/skill-chain.py <skill>` invocations remain harness-shaped.

    `extra_prompt` is appended to the harness's stock skill-invocation prompt
    so callers can pass per-iteration context (e.g. an input file path in
    --inputs batch mode).

    `log_stem_override` lets the caller name the per-skill log files (default
    is `<index:02d>_<skill_name>`). Useful in batch mode where the input
    filename is more meaningful than the iteration index.

    `resume_session_id` is the Claude Code session id from a prior aborted run.
    When set, the harness uses `--resume <id>` so the agent picks up mid-skill
    instead of restarting from scratch (used by run_skill_with_retry after a
    rate-limit pause).
    """
    cmd = harness.build_command(skill_name, model=model, effort=effort,
                                 extra_prompt=extra_prompt,
                                 resume_session_id=resume_session_id)

    txt_path: Path | None = None
    jsonl_path: Path | None = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        stem = log_stem_override or f"{index:02d}_{skill_name}"
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
                # Non-JSON lines (typically stderr merged into stdout). Scan for
                # a rate-limit pattern so the wrapper can pause-and-resume even
                # when the subprocess died before emitting a clean
                # rate_limit_event. Captured as a fallback only — the structured
                # signal from handle_event takes precedence.
                if RATE_LIMIT_TEXT_RE.search(line):
                    skill_record.setdefault("rate_limit_text_match", line[:300])
                    if "rate_limit_text_reset" not in skill_record:
                        reset_match = RATE_LIMIT_RESET_RE.search(line)
                        if reset_match:
                            skill_record["rate_limit_text_reset"] = reset_match.group(1).strip()
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


def run_skill_with_retry(
    harness: Harness,
    skill_name: str,
    index: int,
    log_dir: Path | None,
    *,
    on_rate_limit: str,
    max_pause_seconds: int,
    max_pauses: int,
    pause_records: list[dict],
    model: str | None = None,
    effort: str | None = None,
    extra_prompt: str = "",
    log_stem_override: str | None = None,
    loop_delay: float = 0.0,
    loop_delay_random: tuple[float, float] | None = None,
    notify=None,
) -> tuple[int, dict]:
    """Run a skill with rate-limit pause-and-resume.

    On non-zero exit, inspect the skill_record for a structured rate-limit
    signal (preferred) or a text-fallback match (subprocess died before clean
    event). Under `pause` / `pause-with-cap`, sleep until the parsed reset
    + jitter, archive the failed attempt, and re-invoke the skill via
    `--resume <session_id>` so the agent picks up mid-skill instead of
    restarting from scratch. Aborts after `max_pauses` retries on the same
    skill or when `pause-with-cap` exceeds `max_pause_seconds`.

    After the rate-limit sleep ends and before retrying the skill, an
    additional human-like delay drawn from `loop_delay_random` (or a flat
    `loop_delay`) is applied so the post-pause retry doesn't fire on a
    machine-perfect schedule. Reuses the same knobs as the inter-iter sleep
    so a chain configured with `loop-delay-random: [a, b]` gets matching
    cadence on both inter-iter boundaries and post-pause resumes. The
    sampled value is recorded as `pause_record["post_pause_delay"]`.

    pause_records is mutated in place with one entry per executed pause so
    run_iteration can fold them into the iteration manifest.
    """
    retry_count = 0
    resume_session_id: str | None = None
    while True:
        rc, record = run_skill(
            harness, skill_name, index, log_dir, model=model, effort=effort,
            extra_prompt=extra_prompt, log_stem_override=log_stem_override,
            resume_session_id=resume_session_id,
        )
        if retry_count > 0:
            record["retry_count"] = retry_count

        if rc == 0:
            return rc, record
        if on_rate_limit == "fail":
            return rc, record

        signal = record.get("rate_limit_signal")
        text_fallback = record.get("rate_limit_text_match")
        if signal is None and text_fallback is None:
            # Ordinary failure, not a rate-limit. Pass through.
            return rc, record

        if retry_count >= max_pauses:
            print(c(
                f"[rate-limit] {skill_name} hit max-pauses-per-session ({max_pauses}); "
                f"aborting chain instead of retrying further (likely a quota-burning loop)",
                RED,
            ), flush=True)
            record["rate_limit_aborted"] = "max_pauses_reached"
            return rc, record

        # Construct the signal for sleep computation. Use the structured
        # signal when available; fall back to a synthetic one with attempt
        # count so the exponential backoff in _compute_rate_limit_sleep applies.
        # If the text-fallback extracted a wall-clock reset stamp from the
        # stderr line (e.g. `7:50pm (Asia/Tokyo)`), thread it through as the
        # signal's reset_time whenever the structured signal lacks one, so
        # _parse_reset_time's localized branch turns it into a real wake
        # epoch instead of falling to exponential backoff. Joint-fire case
        # (structured `rejected` + stderr "out of extra usage … resets …")
        # is the live failure mode Phase 13's BUG fix exists to cover; the
        # condition keys on `eff_signal.get("reset_time")` rather than `signal
        # is None` so the wall-clock fills in whenever the structured payload
        # carries no reset under any of the four aliased field names.
        eff_signal: dict[str, Any] = dict(signal) if signal else {"type": "unknown", "status": "fallback"}
        text_reset_used = False
        if not eff_signal.get("reset_time"):
            text_reset = record.get("rate_limit_text_reset")
            if text_reset:
                eff_signal["reset_time"] = text_reset
                text_reset_used = True
        eff_signal["_attempt"] = retry_count
        cap = max_pause_seconds if on_rate_limit == "pause-with-cap" else None
        sleep_seconds, wake_iso = _compute_rate_limit_sleep(eff_signal, max_pause=cap)
        if sleep_seconds is None:
            print(c(
                f"[rate-limit] computed pause exceeds --max-rate-limit-pause-seconds "
                f"({max_pause_seconds}s) under pause-with-cap; falling back to fail",
                RED,
            ), flush=True)
            record["rate_limit_aborted"] = "max_pause_seconds_exceeded"
            return rc, record

        kind = eff_signal.get("type", "?")
        banner = (f"[rate-limit] {kind} exceeded; sleeping {sleep_seconds:.0f}s "
                  f"until {wake_iso} before retrying /{skill_name}")
        print(c(banner, ORANGE), flush=True)

        if signal and text_reset_used:
            source = "rate_limit_event+text_reset"
        elif signal:
            source = "rate_limit_event"
        else:
            source = "text_fallback"
        pause_record = {
            "at": _utc_iso(),
            "type": kind,
            "status": eff_signal.get("status"),
            "sleep_seconds": round(sleep_seconds, 1),
            "reset_time": eff_signal.get("reset_time"),
            "wake_at": wake_iso,
            "skill": skill_name,
            "retry_count": retry_count + 1,
            "source": source,
        }
        pause_records.append(pause_record)

        # Phase 42: real-time rate-limit pause notification (native; was a
        # stdout-banner watch in the former drive-chain.py wrapper). Inert when
        # no notify callback is wired (bare runs / Telegram opt-out).
        if notify is not None:
            notify("rate-limit-pause", pause_record)

        # KeyboardInterrupt during the sleep propagates up to run_iteration's
        # caller, which finalizes the manifest cleanly via main()'s outer
        # try/except. No special handling needed here.
        time.sleep(sleep_seconds)

        pause_record["resumed_at"] = _utc_iso()
        if notify is not None:
            notify("rate-limit-resume", pause_record)
        retry_count += 1
        # Capture the session id from the interrupted run so the next
        # attempt can use --resume to pick up mid-skill context.
        resume_session_id = record.get("session_id") or None
        # Archive the failed attempt's transcript files before the retry
        # overwrites the canonical names. Uses retry_count - 1 so the first
        # failure becomes .retry-0, the second .retry-1, etc.
        _archive_attempt(log_dir, index, skill_name, retry_count - 1)

        # Post-pause human-like delay before retrying. Same knobs as the
        # inter-iter sleep: a configured loop_delay_random samples from
        # [min, max]; a flat loop_delay applies as a fixed wait; zero on
        # both is a no-op. KeyboardInterrupt during this sleep propagates
        # up the same way the rate-limit sleep above does.
        post_pause_sleep = 0.0
        if loop_delay_random is not None:
            post_pause_sleep = random.uniform(loop_delay_random[0], loop_delay_random[1])
        elif loop_delay > 0:
            post_pause_sleep = loop_delay
        if post_pause_sleep > 0:
            if loop_delay_random is not None:
                print(c(
                    f"[rate-limit] post-pause delay {post_pause_sleep:.1f}s "
                    f"(sampled from [{loop_delay_random[0]:g}, {loop_delay_random[1]:g}]) "
                    f"before retrying /{skill_name}",
                    DIM,
                ), flush=True)
            else:
                print(c(
                    f"[rate-limit] post-pause delay {post_pause_sleep:.1f}s "
                    f"before retrying /{skill_name}",
                    DIM,
                ), flush=True)
            pause_record["post_pause_delay"] = round(post_pause_sleep, 1)
            time.sleep(post_pause_sleep)


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
    """Discover a supervisor skill to auto-append.

    Preference order:
      1. A project-local proprietary supervisor at `<cwd>/.claude/skills/*-supervisor/SKILL.md`.
         Exactly one match → use it. More than one → warn and return None (ambiguous;
         the user must pick explicitly, and we do NOT silently fall back).
      2. Fallback: the transferable `sst-supervisor` at
         `~/.claude/skills/sst-supervisor/SKILL.md`, used when the project ships no
         proprietary supervisor of its own (e.g. the skill-set repo itself). This lets
         every project get meta-review + auto-promotion without authoring a wrapper.

    Returns the skill name (folder name) or None when neither exists.
    """
    skills_dir = Path(cwd) / ".claude" / "skills"
    if skills_dir.is_dir():
        candidates = [
            d for d in skills_dir.iterdir()
            if d.is_dir() and d.name.endswith("-supervisor") and (d / "SKILL.md").exists()
        ]
        if len(candidates) > 1:
            names = ", ".join(sorted(d.name for d in candidates))
            print(c(f"[supervisor] multiple supervisor skills found ({names}); "
                    f"auto-append disabled, pass one explicitly.", ORANGE), flush=True)
            return None
        if candidates:
            return candidates[0].name
    # No proprietary supervisor in cwd → fall back to the transferable.
    if (Path.home() / ".claude" / "skills" / "sst-supervisor" / "SKILL.md").exists():
        return "sst-supervisor"
    return None


# ---- Unified chain-run CLI (Phase 42) --------------------------------------
# bin/skill-chain.py is the single canonical chain-run entrypoint. The former
# bin/drive-chain.py wrapper layer (budget gates, Telegram event posts, persona
# profile resolution, run label) is now native here as inert-when-unset flags,
# so nothing requires the old `-- <forwarded-args>` two-script split. The epilog
# below is the spec'd flag-mapping surface (42.1): it lists the merged wrapper
# flags and records which scripts reduce to deprecation shims.
UNIFIED_CLI_EPILOG = """\
Unified chain-run CLI (Phase 42)
--------------------------------
This is the single canonical entrypoint for running a chain OR for running a
single skill once per glob-matched input (--batch mode). The wrapper layer that
used to live in bin/drive-chain.py is now native here; you no longer pass
skill-chain flags after a `-- ` separator.

Legacy flag -> unified form (all native on this runner now):
  drive-chain.py --max-budget-usd X      -> skill-chain.py --max-budget-usd X
  drive-chain.py --max-cycles N          -> skill-chain.py --max-cycles N
  drive-chain.py --telegram-env FILE     -> skill-chain.py --telegram-env FILE
  drive-chain.py --no-telegram           -> skill-chain.py --no-telegram
  drive-chain.py --profile PERSONA       -> skill-chain.py --profile PERSONA
  drive-chain.py --label LABEL           -> skill-chain.py --label LABEL
  drive-chain.py --chain C -- --loop N   -> skill-chain.py --chain C --loop N
  skill-batch.py SKILL --inputs GLOB ... -> skill-chain.py SKILL --batch GLOB ...

Batch mode (one skill over many inputs):
  skill-chain.py SKILL --batch "*.csv" --output-template "reviewed/{stem}.txt"
  (add --dry-run to preview; --skip-if-exists to resume; --on-failure continue)

Telegram event posts are inert unless you opt in with --telegram-env, --profile,
or --label (and not --no-telegram); a bare `skill-chain.py --chain X` never
touches Telegram. Budget/cycle caps (--max-budget-usd / --max-cycles) work with
or without Telegram.

Shims: bin/drive-chain.py and bin/skill-batch.py reduce to thin deprecation
shims that forward onto this runner (drive-chain shim: 42.5; batch mode: 42.4).
"""


# ---- Batch-mode helpers (Phase 42.4) ---------------------------------------

def render_output_template(template: str, input_path: Path, base: Path) -> Path:
    """Render a per-input output path from a template.

    Tokens: {stem} (filename without ext), {name} (full filename), {parent}
    (parent dir, relative to base when possible), {ext} (extension without dot).
    Absolute results are used as-is; relative results are joined to base.
    """
    rel = input_path
    if input_path.is_absolute():
        try:
            rel = input_path.relative_to(base)
        except ValueError:
            rel = input_path
    out = template.format(
        stem=input_path.stem,
        name=input_path.name,
        parent=str(rel.parent),
        ext=input_path.suffix.lstrip("."),
    )
    p = Path(out)
    return p if p.is_absolute() else (base / p)


def expand_inputs(glob: str, base: Path,
                  include: "str | None", exclude: "str | None",
                  start_at: "str | None") -> "list[Path]":
    """Return sorted list of files matching `glob` under `base`, after filters."""
    matches = sorted(base.glob(glob))
    inc = re.compile(include) if include else None
    exc = re.compile(exclude) if exclude else None
    out: list[Path] = []
    for p in matches:
        if not p.is_file():
            continue
        if start_at and p.stem < start_at:
            continue
        if inc and not inc.search(p.stem):
            continue
        if exc and exc.search(p.stem):
            continue
        out.append(p)
    return out


def _git_subject(cwd: str, sha: str) -> str:
    """One-line commit subject for `sha`, or a placeholder on any failure."""
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
    """Parse a shell-style env file (KEY=VALUE per line, # comments, optional
    `export `). One matching pair of surrounding quotes is stripped from values.
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


def _resolve_tg_env(
    telegram_env_path: "Path | None",
    os_env: "dict[str, str]",
    repo_root: "Path",
) -> "dict[str, str]":
    """Merge Telegram credentials from up to three sources (first match wins per
    key): (1) --telegram-env explicit file; (2) caller-exported env vars;
    (3) base-dir fallback `repo_root/telegram.env`. TELEGRAM_PARSE_MODE defaults
    to "" (plain text) so bodies with markdown-ish characters aren't mangled.
    """
    tg: dict[str, str] = {}
    if telegram_env_path:
        tg.update(_read_telegram_env(telegram_env_path))
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_PARSE_MODE"):
        if k not in tg and k in os_env:
            tg[k] = os_env[k]
    if "TELEGRAM_BOT_TOKEN" not in tg:
        _base_fallback = repo_root / "telegram.env"
        if _base_fallback.exists():
            try:
                tg.update(_read_telegram_env(_base_fallback))
            except Exception:  # noqa: BLE001 — best-effort; malformed fallback never aborts
                pass
    tg.setdefault("TELEGRAM_PARSE_MODE", "")
    return tg


class TelegramSink:
    """Sends a message via bin/notify-telegram.sh. No-op when disabled."""

    def __init__(self, *, enabled: bool, env: dict[str, str]):
        self.enabled = enabled
        self.env = env
        self._warned_missing = False

    def send(self, message: str, *, label: str = "telegram") -> None:
        if not self.enabled:
            return
        if "TELEGRAM_BOT_TOKEN" not in self.env or "TELEGRAM_CHAT_ID" not in self.env:
            if not self._warned_missing:
                print("[chain] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not in env; "
                      "skipping outbound. Pass --telegram-env <file>/--profile, set "
                      "them, or use --no-telegram to suppress this warning.",
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
                print(f"[chain] {label}: notify-telegram exited {r.returncode}: "
                      f"{r.stderr.strip()[:300]}", file=sys.stderr, flush=True)
        except subprocess.TimeoutExpired:
            print(f"[chain] {label}: notify-telegram timed out", file=sys.stderr, flush=True)


def _iteration_cost(iter_manifest: dict) -> float:
    """Sum total_cost_usd across an iteration manifest's skill records."""
    return sum(float(s.get("total_cost_usd") or 0) for s in iter_manifest.get("skills", []))


def _supervisor_verdict_path(log_dir: Path, iter_num: int, looping: bool) -> Path:
    if looping:
        return log_dir / f"iter_{iter_num:02d}" / "supervisor_verdict.md"
    return log_dir / "supervisor_verdict.md"


def _verdict_outcome(verdict_path: Path) -> str:
    """One-word outcome label from a supervisor_verdict.md. Checks the
    `## Outcome` markdown-header form first, the inline `Outcome:` form second,
    then a code-span-stripped \\bescalate\\b scan. 'unknown' when absent.
    """
    if not verdict_path.exists():
        return "unknown"
    try:
        body = verdict_path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    m = re.search(r"^##\s+Outcome\s*\n+\s*([A-Za-z_-]+)", body, re.MULTILINE)
    if m:
        return m.group(1).strip().lower()
    m = re.search(r"^\s*\*?\*?Outcome\*?\*?\s*:\s*([A-Za-z_-]+)", body, re.MULTILINE)
    if m:
        return m.group(1).strip().lower()
    stripped = re.sub(r"```[\s\S]*?```", "", body)
    stripped = re.sub(r"`[^`\n]+`", "", stripped)
    if re.search(r"\bescalate\b", stripped, re.IGNORECASE):
        return "escalate"
    return "clean"


def _find_profile_skill(persona: str, cwd: str) -> Path | None:
    """Resolve `<persona>-chain-driver/SKILL.md` (project-scoped first, then
    personal-global). Returns None on miss."""
    candidates = [
        Path(cwd) / ".claude" / "skills" / f"{persona}-chain-driver" / "SKILL.md",
        Path.home() / ".claude" / "skills" / f"{persona}-chain-driver" / "SKILL.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _load_profile_defaults(persona: str, cwd: str) -> dict | None:
    """Parse the first ```yaml block under `## Configured defaults` in a
    `<persona>-chain-driver/SKILL.md`. Returns the PROFILE_KEYS subset, or None
    when no skill / no block / no PyYAML."""
    path = _find_profile_skill(persona, cwd)
    if path is None:
        return None
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return None
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


def _apply_profile_defaults(
    args: argparse.Namespace,
    profile: dict,
    explicit_loop: bool,
) -> None:
    """Apply profile-sourced defaults to `args` in-place. Explicit CLI flags win.

    `explicit_loop` is captured BEFORE profile loading (args.loop is not None at
    that point) so an explicit --loop N suppresses the profile's default-max-cycles
    — the operator's loop is the only ceiling for that run.
    """
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


def _apply_preset(args: argparse.Namespace, explicit_loop: bool) -> None:
    """Expand --overnight / --preset into their canonical flag values.

    Must be called AFTER profile defaults so a profile-sourced cap satisfies
    the --overnight cap requirement. `explicit_loop` mirrors the same flag
    captured before profile loading: True when the operator passed --loop
    explicitly on the CLI.
    """
    # Normalize --overnight shorthand to --preset overnight.
    if getattr(args, "overnight", False):
        if getattr(args, "preset", None) not in (None, "overnight"):
            raise SystemExit("--overnight and --preset are mutually exclusive")
        args.preset = "overnight"

    preset_name = getattr(args, "preset", None)
    if not preset_name:
        return

    if preset_name == "overnight":
        if explicit_loop:
            raise SystemExit(
                "--overnight / --preset overnight and --loop are mutually exclusive; "
                "--overnight implies --loop 0"
            )
        if args.max_budget_usd is None and args.max_cycles is None:
            raise SystemExit(
                "--overnight / --preset overnight requires a budget or cycle cap "
                "to prevent unguarded infinite runs; "
                "add --max-budget-usd <N> or --max-cycles <N>"
            )
        args.loop = 0
        if args.loop_delay_random is None:
            args.loop_delay_random = PRESETS["overnight"]["loop_delay_random"]


def _wrapper_telegram_enabled(args: argparse.Namespace) -> bool:
    """Telegram event posting is opt-in: enabled only when the user supplied
    --telegram-env, --profile, or --label (and did not pass --no-telegram). A
    bare `skill-chain.py --chain X` never touches Telegram (inert-when-unset)."""
    if getattr(args, "no_telegram", False):
        return False
    return any([
        getattr(args, "telegram_env", None) is not None,
        getattr(args, "profile", None) is not None,
        getattr(args, "label", None) is not None,
    ])


def _wrapper_halt_reason(
    *,
    cumulative_cost_usd: float,
    completed_iterations: int,
    max_budget_usd: "float | None",
    max_cycles: "int | None",
    verdict: "str | None" = None,
) -> "str | None":
    """Decide whether a between-iteration halt should fire, returning a one-line
    reason or None. Pure (no I/O) so it is unit-testable. Mirrors the former
    drive-chain.py halt thresholds: budget first, then cycle cap, then a
    supervisor escalation verdict."""
    if max_budget_usd is not None and cumulative_cost_usd > max_budget_usd:
        return (f"max-budget-usd exceeded "
                f"(${cumulative_cost_usd:.4f} > ${max_budget_usd:.2f})")
    if max_cycles is not None and completed_iterations >= max_cycles:
        return f"max-cycles reached ({completed_iterations} >= {max_cycles})"
    if verdict == "escalate":
        return "supervisor escalation"
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="skill-chain.py",
        description="Run agent skills in sequence with prettified output and per-job log capture.",
        epilog=UNIFIED_CLI_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        "--loop",
        type=int,
        default=None,
        help="Run the full skill sequence this many times (default 1 = no loop). "
             "0 = loop until a non-supervisor skill fails or the user interrupts. "
             "Overrides the chain YAML's `loop:` field when both are set.",
    )
    p.add_argument(
        "--loop-delay",
        type=float,
        default=None,
        help="Seconds to sleep between iterations when --loop != 1. "
             "Overrides the chain YAML's `loop-delay:` field when both are set. "
             "Mutually exclusive with --loop-delay-random.",
    )
    p.add_argument(
        "--loop-delay-random",
        type=str,
        default=None,
        metavar="MIN,MAX",
        help=f"Per-iteration randomized delay; sampled uniformly from [MIN, MAX] "
             f"seconds (inclusive) after each iteration boundary. Format: "
             f"'<min>,<max>' (e.g. '300,1800' for 5-30min jitter). Overrides the "
             f"chain YAML's `loop-delay-random:` field. Mutually exclusive with "
             f"--loop-delay; setting both is an error. Makes a multi-iter run's "
             f"cadence look human-driven instead of clockwork-automated. When "
             f"neither this nor --loop-delay nor any YAML delay field is set, "
             f"the runner defaults to "
             f"[{int(DEFAULT_LOOP_DELAY_RANDOM[0])},{int(DEFAULT_LOOP_DELAY_RANDOM[1])}] "
             f"(5-30min). Opt out with --loop-delay 0.",
    )
    p.add_argument(
        "--on-rate-limit",
        choices=["fail", "pause", "pause-with-cap"],
        default=None,
        help=f"How to handle rate-limit signals from the harness. 'fail' (legacy) "
             f"aborts the chain on a rate-limit like any other non-zero exit. "
             f"'pause' (default {DEFAULT_ON_RATE_LIMIT}) sleeps until the parsed "
             f"reset_time + jitter and re-invokes the killed skill. "
             f"'pause-with-cap' falls back to 'fail' if a single pause would "
             f"exceed --max-rate-limit-pause-seconds. Overrides the chain YAML's "
             f"`on-rate-limit:` field when both are set.",
    )
    p.add_argument(
        "--max-rate-limit-pause-seconds",
        type=int,
        default=None,
        help=f"Upper bound on a single rate-limit pause when --on-rate-limit is "
             f"pause-with-cap. Default {DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS}s "
             f"(8h). Overrides the chain YAML's `max-rate-limit-pause-seconds:` "
             f"field when both are set.",
    )
    p.add_argument(
        "--max-pauses-per-session",
        type=int,
        default=None,
        help=f"Hard cap on rate-limit pauses per skill within one chain "
             f"invocation. Default {DEFAULT_MAX_PAUSES_PER_SESSION}. Repeated "
             f"pauses on the same skill suggest a quota-burning loop, not a "
             f"genuine window crossing — abort the chain after this many. "
             f"Overrides the chain YAML's `max-pauses-per-session:` field when "
             f"both are set.",
    )
    # ---- Native wrapper flags (Phase 42; inert when unset) ------------------
    p.add_argument(
        "--profile",
        default=None,
        help="Persona name; loads `<persona>-chain-driver/SKILL.md`'s "
             "`## Configured defaults` yaml block (project-scoped first, then "
             "~/.claude/skills/) as a layer BELOW CLI args (explicit flag wins). "
             "Fills --chain (watched-chain), --loop (default-loop), "
             "--max-budget-usd, --max-cycles, --telegram-env, and --label. Also "
             "opts into Telegram event posts.",
    )
    p.add_argument(
        "--max-budget-usd",
        type=float,
        default=None,
        help="Halt the loop at the next between-iteration boundary once "
             "cumulative cost (summed from each iteration manifest's "
             "skills[].total_cost_usd) exceeds this amount. Inert when unset.",
    )
    p.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Halt the loop once this many iterations have completed. "
             "Independent of --loop (whichever fires first wins). A no-op when "
             "the resolved loop count is finite and <= this cap (the chain "
             "finishes naturally first); a startup note is printed in that case. "
             "Precedence: an explicit --loop N skips any profile default-max-cycles.",
    )
    p.add_argument(
        "--telegram-env",
        type=Path,
        default=None,
        help="Path to a shell-style env file exporting TELEGRAM_BOT_TOKEN and "
             "TELEGRAM_CHAT_ID. Opts into Telegram event posts (session start, "
             "iteration close, rate-limit pause/resume, session end).",
    )
    p.add_argument(
        "--no-telegram",
        action="store_true",
        help="Suppress all Telegram outbound even when --telegram-env/--profile/"
             "--label is set (events still print to the terminal).",
    )
    p.add_argument(
        "--label",
        default=None,
        help="Human-readable label prepended (as [label]) to each Telegram body "
             "and used in event messages. Defaults to the chain name. Opts into "
             "Telegram event posts.",
    )
    p.add_argument(
        "--overnight",
        action="store_true",
        help="Shorthand for --preset overnight. Expands to --loop 0 + "
             "--loop-delay-random 300,1800 (5-30min human-like jitter). "
             "Requires --max-budget-usd or --max-cycles (errors without a cap). "
             "Mutually exclusive with --loop. Applied after --profile defaults "
             "so a profile-sourced cap satisfies the cap requirement.",
    )
    p.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        default=None,
        help="Apply a named preset. Presets are extensible via the PRESETS dict; "
             "current presets: " + ", ".join(sorted(PRESETS)) + ". "
             "--overnight is a convenient alias for --preset overnight.",
    )
    # ---- Batch mode (Phase 42.4; replaces bin/skill-batch.py) -----------------
    p.add_argument(
        "--batch",
        metavar="GLOB",
        default=None,
        help="Run a single skill once per file matching GLOB (relative to "
             "--inputs-cwd, default cwd). Triggers batch mode; the skill name "
             "must be the first positional argument. Replaces skill-batch.py.",
    )
    p.add_argument(
        "--output-template",
        metavar="TMPL",
        default=None,
        help="Per-input output path template. Supports {stem}, {name}, {parent}, "
             "{ext}. e.g. 'reviewed/{stem}.csv'. Required when --batch is set.",
    )
    p.add_argument(
        "--inputs-cwd",
        type=Path,
        default=None,
        help="Resolve --batch glob relative to this dir (default: cwd).",
    )
    p.add_argument(
        "--output-cwd",
        type=Path,
        default=None,
        help="Resolve --output-template relative to this dir (default: --inputs-cwd).",
    )
    p.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Skip batch iterations whose output path already exists.",
    )
    p.add_argument(
        "--include",
        metavar="REGEX",
        default=None,
        help="Only process inputs whose stem matches this regex.",
    )
    p.add_argument(
        "--exclude",
        metavar="REGEX",
        default=None,
        help="Skip inputs whose stem matches this regex.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after N successful batch iterations (0 = no limit).",
    )
    p.add_argument(
        "--start-at",
        metavar="STEM",
        default=None,
        help="Skip inputs alphabetically before this stem.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="In batch mode: print planned invocations and exit without running.",
    )
    p.add_argument(
        "--on-failure",
        choices=["fail", "continue"],
        default="fail",
        help="How to handle a batch-iteration failure. 'fail' (default) aborts; "
             "'continue' processes remaining inputs.",
    )
    p.add_argument(
        "skills",
        nargs="*",
        help="One or more skill names to run in sequence. Omit when --chain is set. "
             "In batch mode, exactly one skill name.",
    )
    return p.parse_args(argv)


def run_iteration(
    harness: Harness,
    skills_to_run: list[str],
    iter_log_dir: Path | None,
    auto_supervisor: str | None,
    iteration: int,
    total_iterations: int | None,
    cwd: str,
    chain_meta: dict | None = None,
    *,
    on_rate_limit: str = DEFAULT_ON_RATE_LIMIT,
    max_pause_seconds: int = DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS,
    max_pauses: int = DEFAULT_MAX_PAUSES_PER_SESSION,
    loop_delay: float = 0.0,
    loop_delay_random: tuple[float, float] | None = None,
    notify=None,
) -> tuple[int, dict]:
    """Run one pass of the chain. Returns (exit_code, iteration_manifest).

    `chain_meta` carries chain-level fields (chain_name, chain_definition,
    harness, etc.) that the iteration manifest doesn't own. After every skill
    completes, this function writes a snapshot of (chain_meta + iter_manifest)
    to iter_log_dir/MANIFEST.json so downstream skills — notably the auto-
    supervisor, which is the last entry in skills_to_run and reads
    MANIFEST.json at start — can see who ran before them. Without the
    snapshot, the supervisor sees no manifest at all (the final write happens
    in main() AFTER the iteration loop completes, which is AFTER the
    supervisor itself has finished).
    """
    if total_iterations != 1:
        if total_iterations is None:
            label = f"iteration {iteration} (looping until failure)"
        else:
            label = f"iteration {iteration}/{total_iterations}"
        print("", flush=True)
        print(c(f"===== {label} =====", BOLD + BLUE), flush=True)
        print("", flush=True)

    # Phase 19 (5): pre-parse the iter's difficulty from docs/TODO.md > Next up
    # (or docs/SPEC.md first open `[ ]` if Next up is empty), with default
    # 'medium' on a missing label. The dev skill (first in the iter) inherits
    # this for its OWN routing; if it later picks a different item and emits
    # `[picked-difficulty: <tier>]`, that overrides the iter difficulty for
    # any skill that runs AFTER the dev (review, supervisor, etc.). The dev's
    # own model/effort is decided BEFORE it runs, so a mismatch can only
    # affect downstream skills — same one-way contract Phase 17's no-work
    # sentinel established.
    iter_difficulty, difficulty_source = _resolve_iter_difficulty(cwd)
    if difficulty_source.endswith("-unlabeled") or difficulty_source == "no-source":
        print(c(f"[difficulty] {difficulty_source}; defaulting to "
                f"{iter_difficulty} for iter routing", ORANGE), flush=True)
    else:
        print(c(f"[difficulty] iter pre-parsed as {iter_difficulty} "
                f"(source: {difficulty_source})", DIM), flush=True)

    iter_manifest: dict = {
        "iteration": iteration,
        "log_subdir": iter_log_dir.name if iter_log_dir else None,
        "started_at": _utc_iso(),
        "git_sha_before": _git_sha(cwd),
        "difficulty": iter_difficulty,
        "difficulty_source": difficulty_source,
        "skills": [],
        "rate_limit_pauses": [],
    }

    def _snapshot_manifest() -> None:
        if iter_log_dir is None:
            return
        # Pre-iteration snapshot can fire before run_skill has created the
        # per-iteration dir (loop>1 puts each iteration under iter_NN/).
        # Ensure the parent exists ourselves.
        iter_log_dir.mkdir(parents=True, exist_ok=True)
        snap = {**(chain_meta or {}), **iter_manifest}
        snap["in_progress"] = True
        (iter_log_dir / "MANIFEST.json").write_text(
            json.dumps(snap, indent=2) + "\n", encoding="utf-8"
        )

    # Empty snapshot up front so the very first skill (or anything that scans
    # for MANIFEST.json before any skill has finished) at least sees the
    # chain metadata + an empty skills list.
    _snapshot_manifest()

    rc = 0
    for i, skill in enumerate(skills_to_run):
        sha_before_skill = _git_sha(cwd)
        # Phase 19 (4): resolve per-skill effective model + effort from the
        # current iter difficulty (which may have been overridden post-dev by
        # the previous iteration of this loop) and the skill's frontmatter
        # floors. Logged before the skill banner so the routing decision is
        # visible alongside the [supervisor] / [chain-driver] markers in the
        # transcript.
        eff_model, eff_effort, route_record = _resolve_skill_route(
            skill, iter_manifest["difficulty"], cwd,
        )
        print(c(f"[route] /{skill}: difficulty={route_record['difficulty']} "
                f"floors=({route_record['model_floor']},{route_record['effort_floor']}) "
                f"-> model={eff_model} effort={eff_effort}", DIM), flush=True)
        skill_rc, record = run_skill_with_retry(
            harness,
            skill,
            i,
            iter_log_dir,
            on_rate_limit=on_rate_limit,
            max_pause_seconds=max_pause_seconds,
            max_pauses=max_pauses,
            pause_records=iter_manifest["rate_limit_pauses"],
            model=eff_model,
            effort=eff_effort,
            loop_delay=loop_delay,
            loop_delay_random=loop_delay_random,
            notify=notify,
        )
        record["route"] = route_record
        if skill == auto_supervisor:
            record["role"] = "supervisor"
        iter_manifest["skills"].append(record)

        # Phase 19 (5): if the dev skill emitted [picked-difficulty: <tier>]
        # and it differs from the pre-parsed iter difficulty, override for
        # subsequent skills. Only the FIRST skill of the iter is treated as
        # the authoritative dev (i == 0); later skills' picked-difficulty
        # captures are recorded but do not re-override (review/supervisor
        # echoing the bracket in their own prose mustn't shift routing for
        # the same iter's downstream pass — there is no downstream after
        # supervisor anyway).
        picked = record.get("picked_difficulty")
        if i == 0 and picked and picked != iter_manifest["difficulty"]:
            print(c(f"[difficulty] dev /{skill} picked '{picked}' "
                    f"(was '{iter_manifest['difficulty']}'); "
                    f"overriding for downstream skills", DIM), flush=True)
            iter_manifest["difficulty_dev_picked"] = picked
            iter_manifest["difficulty"] = picked
        _snapshot_manifest()
        if skill_rc != 0:
            # Supervisor failure should NOT abort downstream work or surface as the
            # chain's exit code, since the cycle's real work already shipped.
            if skill == auto_supervisor:
                print(c(f"\n[supervisor] {skill} exited with {skill_rc}; "
                        f"continuing (chain remains successful)", ORANGE), flush=True)
                continue
            print(f"\n{c(f'/{skill} exited with {skill_rc}; aborting chain', RED)}", flush=True)
            rc = skill_rc
            break
        # Phase 17 empty-queue bail: a skill that prints `[no-work] <reason>`
        # and exits clean signals steady state. Skip the remaining skills in
        # this iteration (review, supervisor) since there's no commit for them
        # to work against, and let main() abort the loop. Recorded on the iter
        # manifest so a chain driver / supervisor / reader can distinguish a
        # bail from a clean run with real work. Phase 18 review follow-up:
        # if the skill ALSO committed (sha changed), the sentinel was a false
        # positive (e.g. dev skill quoting its own bail prose mid-reasoning,
        # then proceeding to commit real work). Suppress in that case so
        # review + supervisor still run on the real commit and the loop
        # continues.
        sha_after_skill = _git_sha(cwd)
        if _no_work_bail_should_fire(record, sha_before_skill, sha_after_skill):
            iter_manifest["no_work_bail"] = {
                "skill": skill,
                "reason": record["no_work_bail"],
            }
            print(c(f"\n[no-work] /{skill}: {record['no_work_bail']}: "
                    f"skipping remaining skills + aborting loop", BLUE), flush=True)
            break
        if record.get("no_work_bail"):
            sentinel_reason = record.pop("no_work_bail")
            record["no_work_bail_suppressed"] = {
                "reason": "commit shipped during skill",
                "sha_before": sha_before_skill,
                "sha_after": sha_after_skill,
                "sentinel_reason": sentinel_reason,
            }
            _snapshot_manifest()
            print(c(f"\n[no-work] /{skill}: sentinel detected but commit shipped "
                    f"({(sha_before_skill or '?')[:7]} -> {(sha_after_skill or '?')[:7]}); "
                    f"treating as false-positive, continuing", DIM), flush=True)
        # Phase 31.8: [blocked-on-human] sentinel — bail immediately (no
        # false-positive suppression: a commit during a blocked-on-human exit
        # is unexpected; treat as-is and surface the block).
        if record.get("blocked_on_human"):
            iter_manifest["blocked_on_human"] = {
                "skill": skill,
                "reason": record["blocked_on_human"],
            }
            print(c(f"\n[blocked-on-human] /{skill}: {record['blocked_on_human']}: "
                    f"skipping remaining skills + aborting loop", BLUE), flush=True)
            break
        # Phase 41.10: [skip-tester] sentinel — the preceding skill signalled
        # no front-end/UI surface. Check whether the immediately-following
        # skill is a *-tester; if so, remove it from skills_to_run so the
        # outer loop skips it and continues to the next skill naturally.
        # Only the direct follower is eligible; a non-tester immediate follower
        # is never skipped even when the sentinel was emitted.
        if record.get("skip_tester") and i + 1 < len(skills_to_run):
            next_skill = skills_to_run[i + 1]
            if next_skill.endswith("-tester"):
                skip_reason = record["skip_tester"]
                iter_manifest["tester_skipped"] = {
                    "skill": next_skill,
                    "reason": skip_reason,
                    "skipped_by": skill,
                }
                # Pop the tester from the list. The list iterator advances by
                # index position, so after the pop the next index (i+1) now
                # holds what was skills_to_run[i+2] — exactly the follower we
                # want to run next (typically sst-dev-review).
                skills_to_run.pop(i + 1)
                _snapshot_manifest()
                print(c(f"\n[skip-tester] /{skill}: {skip_reason}: "
                        f"skipping /{next_skill}, proceeding to next skill", BLUE),
                      flush=True)
        # Phase 36: incomplete-cycle detection — fires only on the dev skill
        # (i==0), when it exits clean with no commit but docs/TODO.md still
        # shows an In-flight line or a Sanitize: must-fix=PENDING placeholder.
        # This is the runner-level enforcement of the "dev skill done = git push
        # succeeded" contract that prose-level Defenses 1-4 could not uphold.
        # Skipped when git SHA is unavailable (non-git harness).
        #
        # When a downstream skill follows (typically sst-dev-review), don't
        # abort — record the violation and let the next skill attempt recovery
        # (commit the orphaned work after verifying tests pass). Only abort
        # immediately when the dev ran alone with no follower skill.
        if (
            i == 0
            and sha_before_skill is not None
            and sha_after_skill is not None
            and sha_before_skill == sha_after_skill
            and _incomplete_cycle_detected(cwd)
        ):
            iter_manifest["contract_violation"] = {
                "skill": skill,
                "kind": "incomplete-cycle",
                # Phase 43 (D3/43.4): stamp the dev skill's post-run HEAD so the
                # loop-level abort can tell whether a follower (sst-dev-review
                # recovery) later advanced HEAD and healed the cycle.
                "head_at_violation": sha_after_skill,
            }
            # Find the first non-tester, non-supervisor skill after the dev:
            # that's the recovery-capable follower. A *-tester has no recovery
            # contract; naming it in the message misleads debugging.
            recovery_follower = next(
                (s for s in skills_to_run[i + 1:]
                 if not s.endswith("-tester") and s != auto_supervisor),
                None,
            )
            if recovery_follower is not None:
                print(c(
                    f"\n[contract-violation: incomplete-cycle] /{skill}: "
                    f"exited [ok] with no commit but docs/TODO.md indicates "
                    f"incomplete work; passing to /{recovery_follower} "
                    f"for orphaned-cycle recovery",
                    ORANGE,
                ), flush=True)
            else:
                print(c(
                    f"\n[contract-violation: incomplete-cycle] /{skill}: "
                    f"exited [ok] with no commit but docs/TODO.md indicates "
                    f"incomplete work (In-flight non-empty or "
                    f"Sanitize: must-fix=PENDING); aborting chain",
                    RED,
                ), flush=True)
                break

    iter_manifest["finished_at"] = _utc_iso()
    iter_manifest["git_sha_after"] = _git_sha(cwd)
    iter_manifest["exit_code"] = rc
    return rc, iter_manifest


def _drain_feedback_queue() -> None:
    """Phase 24 (5): pre-iter drain of the feedback queue via manager-write-state.py.

    Best-effort: if the helper is absent (older install) or exits non-zero,
    print a warning and continue. The helper's idempotency marker means a file
    already processed by the on-demand bot spawn is safely skipped here.
    """
    helper = Path(__file__).parent / "manager-write-state.py"
    if not helper.exists():
        return
    try:
        result = subprocess.run(
            [sys.executable, str(helper), "--drain-feedback-queue"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(c(f"[drain-feedback] helper exited {result.returncode}: "
                    f"{result.stderr.strip()[:200]}", ORANGE), flush=True)
    except subprocess.TimeoutExpired:
        print(c("[drain-feedback] helper timed out (30s); continuing", ORANGE), flush=True)
    except Exception as exc:
        print(c(f"[drain-feedback] {exc}; continuing", ORANGE), flush=True)


def run_batch_mode(args: "argparse.Namespace", harness: Harness, cwd: str) -> int:
    """Phase 42.4: run one skill once per glob-matched input (--batch mode).

    Mirrors the behavior of the old bin/skill-batch.py, now folded into the
    canonical runner. Accepts the batch-specific namespace fields that parse_args
    adds when --batch is set (batch, output_template, inputs_cwd, output_cwd,
    skip_if_exists, include, exclude, limit, start_at, dry_run, on_failure) and
    the shared flags (log_dir, no_log, on_rate_limit, max_rate_limit_pause_seconds,
    max_pauses_per_session, harness).
    """
    if not args.skills or len(args.skills) != 1:
        raise SystemExit(
            "--batch mode requires exactly one skill name as a positional argument"
        )
    if not args.output_template:
        raise SystemExit("--batch requires --output-template")

    skill = args.skills[0]
    in_base = (args.inputs_cwd or Path(cwd)).resolve()
    out_base = (args.output_cwd or args.inputs_cwd or Path(cwd)).resolve()
    inputs = expand_inputs(args.batch, in_base, args.include, args.exclude, args.start_at)
    if not inputs:
        print(f"[skill-batch] no inputs matched {args.batch!r} under {in_base}",
              file=sys.stderr)
        return 2

    on_rate_limit = args.on_rate_limit or DEFAULT_ON_RATE_LIMIT
    max_pause_seconds = args.max_rate_limit_pause_seconds or DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS
    max_pauses = args.max_pauses_per_session or DEFAULT_MAX_PAUSES_PER_SESSION

    if args.no_log:
        log_dir: "Path | None" = None
    elif args.log_dir is not None:
        log_dir = args.log_dir.resolve()
    else:
        log_dir = (Path(cwd) / ".skill-batch-runs" / f"{_utc_dirname()}_{skill}").resolve()

    eff_model, eff_effort, _route = _resolve_skill_route(skill, "medium", cwd)

    print(f"[skill-batch] skill={skill} matched={len(inputs)} "
          f"on_rate_limit={on_rate_limit} log_dir={log_dir}")

    manifest: dict = {
        "mode": "batch",
        "skill": skill,
        "started_at": _utc_iso(),
        "matched_inputs": len(inputs),
        "items": [],
        "rate_limit_pauses": [],
    }

    completed = skipped = failed = 0
    overall_rc = 0
    for i, inp in enumerate(inputs, 1):
        out_path = render_output_template(args.output_template, inp, out_base)
        if args.skip_if_exists and out_path.exists():
            print(f"[{i}/{len(inputs)}] [skip] {inp.stem} (output exists)")
            skipped += 1
            manifest["items"].append({
                "index": i, "input": str(inp), "output": str(out_path),
                "status": "skipped", "reason": "output_exists",
            })
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        extra_prompt = (
            f"Apply the skill to this single input/output pair, then exit:\n"
            f"  input:  {inp}\n"
            f"  output: {out_path}"
        )
        print(f"[{i}/{len(inputs)}] [run ] {inp.stem} -> {out_path}")

        if args.dry_run:
            cmd = harness.build_command(skill, model=eff_model, effort=eff_effort,
                                        extra_prompt=extra_prompt)
            print("  DRY-RUN:", " ".join(repr(c_) for c_ in cmd))
            completed += 1
            manifest["items"].append({
                "index": i, "input": str(inp), "output": str(out_path),
                "status": "dry_run",
            })
            continue

        rc, record = run_skill_with_retry(
            harness, skill, i, log_dir,
            on_rate_limit=on_rate_limit,
            max_pause_seconds=max_pause_seconds,
            max_pauses=max_pauses,
            pause_records=manifest["rate_limit_pauses"],
            model=eff_model, effort=eff_effort,
            extra_prompt=extra_prompt,
            log_stem_override=f"{i:03d}_{inp.stem}",
        )
        record["input"] = str(inp)
        record["output"] = str(out_path)
        record["status"] = "ok" if rc == 0 else "fail"
        manifest["items"].append(record)

        if rc == 0:
            completed += 1
        else:
            failed += 1
            print(f"[{i}/{len(inputs)}] [fail] {inp.stem} (rc={rc})", file=sys.stderr)
            if args.on_failure == "fail":
                overall_rc = rc
                break
            overall_rc = rc

        if args.limit and completed >= args.limit:
            print(f"[skill-batch] hit --limit {args.limit}, stopping")
            break

    manifest["finished_at"] = _utc_iso()
    manifest["completed"] = completed
    manifest["skipped"] = skipped
    manifest["failed"] = failed
    print(f"[skill-batch] done. completed={completed} skipped={skipped} failed={failed}")

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    return overall_rc


def main() -> int:
    args = parse_args(sys.argv[1:])
    harness = get_harness(args.harness)

    cwd = os.getcwd()

    # Phase 42.4: batch mode dispatch — one skill over many inputs.
    if args.batch is not None:
        return run_batch_mode(args, harness, cwd)

    # Phase 42: resolve persona profile defaults as a layer BELOW CLI args.
    # Snapshot explicit --loop BEFORE profile loading so an explicit loop count
    # suppresses a profile default-max-cycles (the user's loop is the only
    # ceiling for that run). A missing/malformed profile is a silent no-op.
    explicit_loop = args.loop is not None
    if args.profile:
        profile = _load_profile_defaults(args.profile, cwd)
        if profile is None:
            print(
                f"[chain] --profile {args.profile!r}: no "
                f"'<persona>-chain-driver/SKILL.md' found under "
                f"<cwd>/.claude/skills/ or ~/.claude/skills/, or its "
                f"'## Configured defaults' yaml block is missing/malformed; "
                f"continuing with CLI args + builtin defaults only.",
                file=sys.stderr, flush=True,
            )
        else:
            _apply_profile_defaults(args, profile, explicit_loop)

    # Expand --overnight / --preset after profile defaults so a profile-sourced
    # cap satisfies the --overnight cap requirement.
    _apply_preset(args, explicit_loop)

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

    # Resolve loop parameters (CLI wins over chain YAML).
    if args.loop is not None:
        loop_count = args.loop
    elif chain_def is not None and "loop" in chain_def:
        loop_count = int(chain_def["loop"])
    else:
        loop_count = 1
    if loop_count < 0:
        raise SystemExit("--loop must be >= 0 (0 = until failure / Ctrl-C)")

    # loop-delay-random takes precedence over loop-delay when set.
    # Mutual-exclusion: setting both via the same source (CLI or YAML) is an
    # error; a CLI random override of a YAML fixed delay (or vice versa) is
    # explicitly allowed (CLI is the override layer).
    loop_delay_random: tuple[float, float] | None = None
    if args.loop_delay_random is not None:
        if args.loop_delay is not None:
            raise SystemExit("--loop-delay and --loop-delay-random are mutually exclusive")
        try:
            parts = [float(x.strip()) for x in args.loop_delay_random.split(",")]
        except ValueError:
            raise SystemExit(f"--loop-delay-random must be 'MIN,MAX' numeric "
                             f"(got {args.loop_delay_random!r})")
        if len(parts) != 2:
            raise SystemExit(f"--loop-delay-random must be 'MIN,MAX' (got "
                             f"{args.loop_delay_random!r})")
        if parts[0] < 0 or parts[1] < 0:
            raise SystemExit("--loop-delay-random values must be >= 0")
        if parts[0] > parts[1]:
            raise SystemExit(f"--loop-delay-random MIN ({parts[0]}) must be "
                             f"<= MAX ({parts[1]})")
        loop_delay_random = (parts[0], parts[1])
    elif chain_def is not None and "loop-delay-random" in chain_def:
        if "loop-delay" in chain_def:
            raise SystemExit(f"chain {chain_def.get('name','?')!r}: loop-delay "
                             f"and loop-delay-random are mutually exclusive")
        rng = chain_def["loop-delay-random"]
        if not (isinstance(rng, list) and len(rng) == 2):
            raise SystemExit(f"chain {chain_def.get('name','?')!r}: "
                             f"loop-delay-random must be [min, max]")
        lo, hi = float(rng[0]), float(rng[1])
        if lo < 0 or hi < 0:
            raise SystemExit("loop-delay-random values must be >= 0")
        if lo > hi:
            raise SystemExit(f"loop-delay-random min ({lo}) must be <= max ({hi})")
        loop_delay_random = (lo, hi)

    if loop_delay_random is not None:
        loop_delay = 0.0  # unused when random is active; recorded as the floor for clarity
    elif args.loop_delay is not None:
        loop_delay = args.loop_delay
    elif chain_def is not None and "loop-delay" in chain_def:
        loop_delay = float(chain_def["loop-delay"])
    else:
        # No CLI override, no YAML setting — fall back to the human-like
        # default jitter so multi-iter runs never accidentally fire iterations
        # back-to-back. Opt out with `--loop-delay 0` or YAML `loop-delay: 0`.
        loop_delay = 0.0
        loop_delay_random = DEFAULT_LOOP_DELAY_RANDOM
    if loop_delay < 0:
        raise SystemExit("--loop-delay must be >= 0")

    # Rate-limit config: CLI > YAML > defaults.
    if args.on_rate_limit is not None:
        on_rate_limit = args.on_rate_limit
    elif chain_def is not None and "on-rate-limit" in chain_def:
        on_rate_limit = chain_def["on-rate-limit"]
    else:
        on_rate_limit = DEFAULT_ON_RATE_LIMIT
    if on_rate_limit not in {"fail", "pause", "pause-with-cap"}:
        raise SystemExit(f"invalid on-rate-limit {on_rate_limit!r}; "
                         f"must be one of fail|pause|pause-with-cap")

    if args.max_rate_limit_pause_seconds is not None:
        max_pause_seconds = args.max_rate_limit_pause_seconds
    elif chain_def is not None and "max-rate-limit-pause-seconds" in chain_def:
        max_pause_seconds = int(chain_def["max-rate-limit-pause-seconds"])
    else:
        max_pause_seconds = DEFAULT_MAX_RATE_LIMIT_PAUSE_SECONDS
    if max_pause_seconds < 0:
        raise SystemExit("--max-rate-limit-pause-seconds must be >= 0")

    if args.max_pauses_per_session is not None:
        max_pauses = args.max_pauses_per_session
    elif chain_def is not None and "max-pauses-per-session" in chain_def:
        max_pauses = int(chain_def["max-pauses-per-session"])
    else:
        max_pauses = DEFAULT_MAX_PAUSES_PER_SESSION
    if max_pauses < 1:
        raise SystemExit("--max-pauses-per-session must be >= 1")

    # Phase 42: native budget / cycle caps (inert when unset).
    if args.max_budget_usd is not None and args.max_budget_usd <= 0:
        raise SystemExit("--max-budget-usd must be > 0")
    if args.max_cycles is not None and args.max_cycles < 1:
        raise SystemExit("--max-cycles must be >= 1")

    looping = (loop_count != 1)
    infinite = (loop_count == 0)

    # --max-cycles no-op note: when the resolved loop count is finite and <= the
    # cap, the cap can never fire (the chain finishes naturally first). Surface
    # this at startup so a silent no-op isn't read as "the cap worked." A
    # `loop: 0` (until-failure) run keeps the cap meaningful, so don't warn there.
    if args.max_cycles is not None and 0 < loop_count <= args.max_cycles:
        print(c(
            f"[note] --max-cycles {args.max_cycles} is a no-op: this run loops "
            f"{loop_count} time(s) and exits naturally before the cap can fire. "
            f"The cap is the safety net for multi-iter runs (--loop N>"
            f"{args.max_cycles}, or chain `loop: 0`).", ORANGE,
        ), flush=True)

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
    if looping:
        loop_desc = "until failure / Ctrl-C" if infinite else f"{loop_count} iterations"
        if loop_delay_random is not None:
            delay_desc = f", random delay [{loop_delay_random[0]:g}-{loop_delay_random[1]:g}]s between"
        elif loop_delay > 0:
            delay_desc = f", {loop_delay}s delay between"
        else:
            delay_desc = ""
        print(c(f"[loop]    {loop_desc}{delay_desc}", DIM), flush=True)
    if on_rate_limit != "fail":
        cap_desc = f", cap {max_pause_seconds}s" if on_rate_limit == "pause-with-cap" else ""
        print(c(f"[on-rate-limit] {on_rate_limit}{cap_desc}, max-pauses-per-session={max_pauses}", DIM), flush=True)

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
        "rate_limit_policy": {
            "on_rate_limit": on_rate_limit,
            "max_rate_limit_pause_seconds": max_pause_seconds,
            "max_pauses_per_session": max_pauses,
        },
    }
    if looping:
        manifest["loop"] = {
            "requested": loop_count,      # 0 means infinite
            "delay_seconds": loop_delay,
            "delay_random_range": list(loop_delay_random) if loop_delay_random else None,
            "delay_samples": [],          # actual sampled delays per iteration boundary
            "completed": 0,
        }
        manifest["iterations"] = []

    # Phase 42: native Telegram event posts (opt-in via --telegram-env /
    # --profile / --label; inert otherwise). Credential resolution reuses the
    # full fallback chain (explicit file -> env -> base-dir telegram.env).
    telegram_enabled = _wrapper_telegram_enabled(args)
    label = args.label or chain_name
    tg_env = _resolve_tg_env(args.telegram_env, dict(os.environ), REPO_ROOT) \
        if telegram_enabled else {}
    if telegram_enabled and label:
        # Threaded into the env so notify-telegram.sh prepends "[label]" to
        # every outbound body automatically (SPEC 28.1).
        tg_env["TELEGRAM_LABEL"] = label
    telegram = TelegramSink(enabled=telegram_enabled, env=tg_env)

    def _notify(event: str, payload: dict) -> None:
        """Format + send one Telegram event. No-op when Telegram is disabled."""
        if not telegram_enabled:
            return
        if event == "rate-limit-pause":
            telegram.send(
                f"chain [{label}]: RATE-LIMIT pause\n"
                f"type: {payload.get('type')} | skill: /{payload.get('skill')}\n"
                f"sleeping {payload.get('sleep_seconds')}s until {payload.get('wake_at')}\n"
                f"at: {payload.get('at')}",
                label="rate-limit-pause",
            )
        elif event == "rate-limit-resume":
            telegram.send(
                f"chain [{label}]: rate-limit RESUME\n"
                f"skill resumed: /{payload.get('skill')}\n"
                f"at: {payload.get('resumed_at')}",
                label="rate-limit-resume",
            )

    if telegram_enabled:
        cap_lines: list[str] = []
        if args.max_budget_usd is not None:
            cap_lines.append(f"budget cap ${args.max_budget_usd:.2f}")
        if args.max_cycles is not None:
            cap_lines.append(f"cycle cap {args.max_cycles}")
        cap_text = " | ".join(cap_lines) if cap_lines else "no caps"
        loop_desc_tg = (
            "until failure / Ctrl-C" if infinite
            else (f"{loop_count} iterations" if looping else "single run")
        )
        telegram.send(
            f"chain: session START — {label}\n"
            f"chain: {chain_name} ({loop_desc_tg})\n"
            f"cwd: {cwd}\n"
            f"caps: {cap_text}\n"
            f"log: {log_dir if log_dir else '(none)'}\n"
            f"started_at: {_utc_iso()}",
            label="session-start",
        )

    cumulative_cost_usd = 0.0
    halt_reason: str | None = None

    final_rc = 0
    iteration = 0
    iterations_collected: list[dict] = []
    try:
        while True:
            iteration += 1
            if looping and log_dir is not None:
                iter_log_dir: Path | None = log_dir / f"iter_{iteration:02d}"
            else:
                iter_log_dir = log_dir

            # Phase 24 (5): drain any feedback queued since the last iter so
            # the supervisor's upcoming pass sees it even if the on-demand
            # bot spawn failed (crash / rate-limit / network).
            _drain_feedback_queue()

            rc, iter_manifest = run_iteration(
                harness,
                skills_to_run,
                iter_log_dir,
                auto_supervisor,
                iteration,
                None if infinite else loop_count,
                cwd,
                chain_meta=manifest,
                on_rate_limit=on_rate_limit,
                max_pause_seconds=max_pause_seconds,
                max_pauses=max_pauses,
                loop_delay=loop_delay,
                loop_delay_random=loop_delay_random,
                notify=_notify,
            )
            iterations_collected.append(iter_manifest)

            # Per-iteration MANIFEST.json only when looping (flat layout for loop=1
            # preserves the pre-loop shape for any tooling reading these files).
            if looping and iter_log_dir is not None:
                (iter_log_dir / "MANIFEST.json").write_text(
                    json.dumps(iter_manifest, indent=2) + "\n", encoding="utf-8"
                )

            # Phase 42: iteration-close Telegram + budget/cycle halt (native;
            # was a subprocess-stdout watch in the former drive-chain.py). Cost
            # accumulates whether or not Telegram is enabled so the cap fires
            # in headless runs too.
            iter_cost = _iteration_cost(iter_manifest)
            cumulative_cost_usd += iter_cost
            iter_verdict = "unknown"
            if log_dir is not None:
                iter_verdict = _verdict_outcome(
                    _supervisor_verdict_path(log_dir, iteration, looping)
                )
            if telegram_enabled:
                sha_b = iter_manifest.get("git_sha_before")
                sha_a = iter_manifest.get("git_sha_after")
                commit_line = "no commit"
                if sha_b and sha_a and sha_b != sha_a:
                    commit_line = f"{sha_a[:8]} {_git_subject(cwd, sha_a)}"
                rl_pauses = iter_manifest.get("rate_limit_pauses") or []
                pause_note = f" | {len(rl_pauses)} rate-limit pause(s)" if rl_pauses else ""
                telegram.send(
                    f"chain [{label}]: iter {iteration} CLOSE\n"
                    f"commit: {commit_line}\n"
                    f"cost: ${iter_cost:.4f} (cumulative ${cumulative_cost_usd:.4f})\n"
                    f"verdict: {iter_verdict}{pause_note}\n"
                    f"at: {_utc_iso()}",
                    label="iter-close",
                )

            if rc != 0:
                final_rc = rc
                break

            # Phase 42: between-iteration halt on budget / cycle cap / escalation.
            halt_reason = _wrapper_halt_reason(
                cumulative_cost_usd=cumulative_cost_usd,
                completed_iterations=iteration,
                max_budget_usd=args.max_budget_usd,
                max_cycles=args.max_cycles,
                verdict=iter_verdict,
            )
            if halt_reason is not None:
                if "loop" in manifest:
                    manifest["loop"]["terminated_by"] = "wrapper_halt"
                    manifest["loop"]["halt_reason"] = halt_reason
                print(c(f"[halt] {halt_reason}; ending run after "
                        f"{iteration} iteration(s)", ORANGE), flush=True)
                if telegram_enabled:
                    telegram.send(
                        f"chain [{label}]: HALT — {halt_reason}\n"
                        f"after {iteration} iteration(s) | "
                        f"cumulative ${cumulative_cost_usd:.4f}",
                        label="halt",
                    )
                break
            # Phase 17: empty-queue bail aborts the loop entirely (no further
            # iterations). Recorded on the top-level loop manifest so a chain
            # driver's session-end summary can distinguish "no-work bail" from
            # "max-cycles reached" / "failure".
            if iter_manifest.get("no_work_bail"):
                if "loop" in manifest:
                    manifest["loop"]["terminated_by"] = "no_work_bail"
                break
            # Phase 31.8: blocked-on-human bail — terminate the loop so the
            # chain driver can surface the block reason to the user.
            if iter_manifest.get("blocked_on_human"):
                if "loop" in manifest:
                    manifest["loop"]["terminated_by"] = "blocked_on_human"
                break
            # Phase 36: incomplete-cycle contract violation — abort the loop
            # so a stuck "sub-skill returns, parent doesn't close" cycle
            # doesn't silently re-iterate against the same In-flight state.
            # Phase 43.6: relaxed — abort only when _incomplete_cycle_detected
            # returns True (In-flight still set). The recovery follower clears
            # the In-flight line as part of its commit; that is the genuine
            # recovery signal, not HEAD advancement (which a supervisor commit
            # can satisfy without the cycle actually having recovered).
            if iter_manifest.get("contract_violation"):
                if _contract_violation_aborts(iter_manifest, cwd):
                    if "loop" in manifest:
                        manifest["loop"]["terminated_by"] = "contract_violation"
                    break
                cv = iter_manifest["contract_violation"]
                print(c(
                    f"[contract-violation: recovered] /{cv.get('skill')}: "
                    f"recovery follower cleared In-flight; loop continues",
                    GREEN,
                ), flush=True)
            if not infinite and iteration >= loop_count:
                break
            sleep_seconds = 0.0
            if loop_delay_random is not None:
                sleep_seconds = random.uniform(loop_delay_random[0], loop_delay_random[1])
            elif loop_delay > 0:
                sleep_seconds = loop_delay
            if sleep_seconds > 0:
                if loop_delay_random is not None:
                    print(c(f"[loop] sleeping {sleep_seconds:.1f}s "
                            f"(sampled from [{loop_delay_random[0]:g}, {loop_delay_random[1]:g}]) "
                            f"before iteration {iteration + 1}", DIM), flush=True)
                else:
                    print(c(f"[loop] sleeping {sleep_seconds}s before iteration {iteration + 1}", DIM), flush=True)
                manifest["loop"]["delay_samples"].append(round(sleep_seconds, 2))
                time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        print(c(f"\n[loop] interrupted after {iteration} iteration(s)", ORANGE), flush=True)
        if final_rc == 0:
            final_rc = 130

    manifest["finished_at"] = _utc_iso()
    manifest["exit_code"] = final_rc

    if iterations_collected:
        manifest["git_sha_before"] = iterations_collected[0]["git_sha_before"]
        manifest["git_sha_after"]  = iterations_collected[-1]["git_sha_after"]
    else:
        manifest["git_sha_before"] = _git_sha(cwd)
        manifest["git_sha_after"]  = manifest["git_sha_before"]

    if looping:
        manifest["loop"]["completed"] = iteration
        manifest["iterations"] = iterations_collected
    else:
        # Preserve the original flat shape for single-run manifests.
        # Also promote iter-level routing fields so §2.11 batch-sizing and
        # supervisor §3.5.1 refinement work on debug-mode runs.
        if iterations_collected:
            iter0 = iterations_collected[0]
            manifest["skills"] = iter0["skills"]
            manifest["difficulty"] = iter0.get("difficulty")
            manifest["difficulty_source"] = iter0.get("difficulty_source")
            manifest["rate_limit_pauses"] = iter0.get("rate_limit_pauses", [])
        else:
            manifest["skills"] = []

    if log_dir is not None:
        (log_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    # Phase 42: session-end Telegram (native; was drive-chain.py's final post).
    if telegram_enabled:
        completed = manifest.get("loop", {}).get("completed", iteration) \
            if "loop" in manifest else iteration
        end_lines = [
            f"chain: session END — {label}",
            f"exit_code: {final_rc}"
            + (f" (HALT: {halt_reason})" if halt_reason else ""),
            f"iterations completed: {completed}",
            f"cumulative cost: ${cumulative_cost_usd:.4f}",
        ]
        if log_dir is not None:
            end_lines.append(f"manifest: {log_dir / 'MANIFEST.json'}")
        end_lines.append(f"finished_at: {_utc_iso()}")
        telegram.send("\n".join(end_lines), label="session-end")

    return final_rc


if __name__ == "__main__":
    sys.exit(main())
