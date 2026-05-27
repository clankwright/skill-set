#!/usr/bin/env python3
"""manager-idle-check.py — cheap idle pre-check for sst-manager periodic ticks.

Invoke BEFORE spawning the sst-manager LLM to avoid burning Opus quota when
none of the watched projects have new activity.

Exit codes:
  0  — idle (nothing to do; safe to skip the manager invocation)
  1  — work found (at least one condition indicates the manager should run)
  2  — configuration or runtime error (missing config, unreadable files, etc.)

Idle conditions (ALL must hold for the project to be considered idle):
  1. No new .skill-runs/ directory whose name sorts after the cursor's
     last-seen run dir name (run dir names are UTC ISO timestamps, so
     lexicographic order == chronological order).
  2. No unprocessed files in the bot-queue directory (files in the
     processed/ subdirectory are excluded — they have already been handled).
  3. docs/HUMAN.md has no new open Blocking entries that were absent from the
     cursor's human_md_snapshot (a dict of H-ID -> title).

If the cursor file has no entry for the project (first-ever run), the check
returns NOT idle so the manager runs unconditionally on first invocation.

Usage:
  bin/manager-idle-check.py --project <path> [--cursors <path>] [--queue-dir <path>]

Where:
  --project    Path to the watched project root (required).
  --cursors    Path to manager-cursors.json
               (default: ~/.claude/state/manager-cursors.json).
  --queue-dir  Path to the bot-queue directory
               (default: ~/.claude/state/manager-bot-queue/).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ── Public API (used by tests directly) ─────────────────────────────────────

def is_manager_idle(
    project_path: str,
    *,
    cursors_path: str | None = None,
    queue_dir: str | None = None,
) -> bool:
    """Return True if the manager has nothing to do for *project_path*.

    Parameters
    ----------
    project_path:
        Absolute (or ``~``-prefixed) path to the watched project root.
    cursors_path:
        Path to manager-cursors.json.  Defaults to
        ``~/.claude/state/manager-cursors.json``.
    queue_dir:
        Path to the bot-queue directory.  Defaults to
        ``~/.claude/state/manager-bot-queue/``.

    Returns
    -------
    True  -- idle; skip the manager invocation.
    False -- work found; invoke the manager.
    """
    project_path = str(Path(project_path).expanduser().resolve())
    state_dir = Path("~/.claude/state").expanduser()

    if cursors_path is None:
        cursors_path = str(state_dir / "manager-cursors.json")
    if queue_dir is None:
        queue_dir = str(state_dir / "manager-bot-queue")

    cursors_file = Path(cursors_path)
    queue_dir_path = Path(queue_dir)
    project_root = Path(project_path)

    # ── 1. Load cursor ───────────────────────────────────────────────────────
    cursors: dict = {}
    if cursors_file.exists():
        try:
            cursors = json.loads(cursors_file.read_text())
        except (json.JSONDecodeError, OSError):
            # Unreadable cursor: run the manager so it can rebuild state.
            return False

    cursor_entry = cursors.get(project_path)
    if cursor_entry is None:
        # First run: no cursor entry yet.
        return False

    # Normalise: cursor_entry may be a bare string (legacy) or a dict (extended).
    if isinstance(cursor_entry, str):
        last_run_name: str | None = cursor_entry
        human_snapshot: dict | None = None
    else:
        last_run_name = cursor_entry.get("latest_run") or cursor_entry.get("last_run")
        raw_snapshot = cursor_entry.get("human_md_snapshot")
        human_snapshot = raw_snapshot if isinstance(raw_snapshot, dict) else None

    # ── 2. New .skill-runs/ directory? ──────────────────────────────────────
    runs_dir = project_root / ".skill-runs"
    if _has_new_run_dir(runs_dir, last_run_name):
        return False

    # ── 3. Unprocessed bot-queue files? ─────────────────────────────────────
    if _has_pending_queue_files(queue_dir_path):
        return False

    # ── 4. New HUMAN.md Blocking entries? ────────────────────────────────────
    if _human_md_blocking_changed(
        project_root / "docs" / "HUMAN.md",
        human_snapshot,
    ):
        return False

    return True


# ── Internal helpers ─────────────────────────────────────────────────────────

def _has_new_run_dir(runs_dir: Path, last_run_name: str | None) -> bool:
    """True if there is a .skill-runs/ entry with a name that sorts after
    *last_run_name*.

    Run-dir names are UTC ISO timestamps (``2026-05-27T00-00-42Z_chain``), so
    lexicographic order equals chronological order.
    """
    if not runs_dir.is_dir():
        return False

    run_names = sorted(d.name for d in runs_dir.iterdir() if d.is_dir())
    if not run_names:
        return False
    if last_run_name is None:
        # Runs exist but no cursor yet: manager has never processed any.
        return True

    return any(name > last_run_name for name in run_names)


def _has_pending_queue_files(queue_dir: Path) -> bool:
    """True if queue_dir contains any *.json files outside the processed/ subdir."""
    if not queue_dir.is_dir():
        return False
    processed = queue_dir / "processed"
    for f in queue_dir.glob("*.json"):
        # Exclude the processed/ subdirectory (already handled files live there).
        if f.parent != processed:
            return True
    return False


def _parse_blocking_snapshot(human_md_path: Path) -> dict:
    """Return a dict of open Blocking H-IDs -> titles from docs/HUMAN.md.

    Only entries in the ``## Blocking`` section that are open (``[ ]``) are
    included.  Closed (``[x]``) entries are ignored.
    """
    if not human_md_path.exists():
        return {}

    text = human_md_path.read_text()
    in_blocking = False
    snapshot: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^## Blocking", stripped):
            in_blocking = True
            continue
        if re.match(r"^## ", stripped) and in_blocking:
            break  # Moved past ## Blocking section.
        if in_blocking:
            m = re.match(
                r"^- \[ \] (H\d+\.\d+[a-z]?)\s+\[(?:easy|medium|hard)\]\s+\*\*(.+?)\*\*",
                stripped,
            )
            if m:
                snapshot[m.group(1)] = m.group(2)
    return snapshot


def _human_md_blocking_changed(
    human_md_path: Path,
    stored_snapshot: dict | None,
) -> bool:
    """True if the current HUMAN.md Blocking section differs from *stored_snapshot*.

    Parameters
    ----------
    human_md_path:
        Path to docs/HUMAN.md (may not exist).
    stored_snapshot:
        The H-ID -> title dict stored in the cursor (from manager's §3b write).
        ``None`` means the manager has never captured a snapshot.

    Returns True (changed) when:
    - The file exists but no snapshot was stored (manager needs a first snapshot).
    - The current set of open Blocking H-IDs differs from the snapshot.
    """
    current_snapshot = _parse_blocking_snapshot(human_md_path)

    if stored_snapshot is None:
        # No snapshot yet: changed only if the file has blocking entries.
        return bool(current_snapshot)

    return current_snapshot != stored_snapshot


# ── CLI entry-point ──────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cheap idle pre-check for sst-manager periodic ticks.",
        epilog=(
            "Exit 0: idle (skip manager). "
            "Exit 1: work found (invoke manager). "
            "Exit 2: config/runtime error."
        ),
    )
    parser.add_argument("--project", required=True, help="Watched project root path.")
    parser.add_argument(
        "--cursors",
        default=None,
        help="Path to manager-cursors.json "
        "(default: ~/.claude/state/manager-cursors.json).",
    )
    parser.add_argument(
        "--queue-dir",
        default=None,
        dest="queue_dir",
        help="Bot-queue directory "
        "(default: ~/.claude/state/manager-bot-queue/).",
    )
    args = parser.parse_args(argv)

    try:
        idle = is_manager_idle(
            args.project,
            cursors_path=args.cursors,
            queue_dir=args.queue_dir,
        )
    except Exception as exc:
        print(f"manager-idle-check: error: {exc}", file=sys.stderr)
        return 2

    if idle:
        print("manager-idle-check: idle -- skipping manager invocation.")
        return 0
    else:
        print("manager-idle-check: work found -- invoking manager.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
