#!/usr/bin/env python3
"""manager-write-state.py — atomic writes to manager-notes.md.

Three modes:
  --source feedback --src-file <queue.json>
      Read one feedback queue JSON file, prepend a user-feedback entry to
      manager-notes.md, move the queue file to manager-bot-queue/processed/.

  --source observation
      Read from stdin, prepend a manager-observation entry to manager-notes.md.

  --drain-feedback-queue
      Process all pending *_feedback*.json queue files under manager-bot-queue/,
      sorted by filename (chronological). Holds an exclusive flock on
      manager-bot-queue/.drain.lock for the full glob+process+rename sequence.
      Idempotent: skips any file whose basename already appears in manager-notes.md
      via a '<!-- src: <basename> -->' marker.

MANAGER_STATE_DIR env var overrides the default ~/.claude/state path.
"""

import argparse
import datetime
import fcntl
import json
import os
import re
import sys
import tempfile
from pathlib import Path

STATE_DIR = Path(os.environ.get("MANAGER_STATE_DIR", Path.home() / ".claude" / "state"))
NOTES_PATH = STATE_DIR / "manager-notes.md"
QUEUE_DIR = STATE_DIR / "manager-bot-queue"
PROCESSED_DIR = QUEUE_DIR / "processed"
LOCK_PATH = QUEUE_DIR / ".drain.lock"

# ~3KB total file cap (preamble + entries)
CAP_BYTES = 3072

NOTES_HEADER = (
    "# Manager notes for the supervisor\n"
    "\n"
    "Newest first. The supervisor reads this as steering input on every run."
    " Two source-tagged entry kinds, interleaved by UTC:\n"
    "- `## <utc-iso> user feedback (chat <id>)` — verbatim user message from"
    " the Telegram `/feedback` command (authoritative).\n"
    "- `## <utc-iso> manager observation` — manager-derived patterns from"
    " observed runs (soft steering).\n"
)


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_notes() -> str:
    if NOTES_PATH.exists():
        return NOTES_PATH.read_text(encoding="utf-8")
    return NOTES_HEADER


def _split_preamble(content: str) -> tuple[str, str]:
    """Return (preamble, entries). Preamble = H1 + lead paragraph; entries start at first ## heading."""
    m = re.search(r"^## ", content, re.MULTILINE)
    if m:
        return content[: m.start()], content[m.start() :]
    return content, ""


def _trim_entries(entries: str, budget_bytes: int) -> str:
    """Remove oldest (bottom) entries until the entries section fits in budget_bytes."""
    if len(entries.encode("utf-8")) <= budget_bytes:
        return entries
    # Split into blocks; each block starts with "## "
    blocks = re.split(r"(?=^## )", entries, flags=re.MULTILINE)
    while blocks and len("".join(blocks).encode("utf-8")) > budget_bytes:
        blocks.pop()
    return "".join(blocks)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".notes-tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    os.replace(tmp, path)


def _already_seen(basename: str, content: str) -> bool:
    return f"<!-- src: {basename} -->" in content


def _prepend(content: str, entry: str) -> str:
    preamble, entries = _split_preamble(content)
    new_entries = entry + "\n" + entries
    # Budget for entries = total cap minus preamble size
    preamble_bytes = len(preamble.encode("utf-8"))
    entry_budget = max(CAP_BYTES - preamble_bytes, len(entry.encode("utf-8")) + 64)
    trimmed = _trim_entries(new_entries, entry_budget)
    if preamble and not preamble.endswith("\n"):
        preamble += "\n"
    return preamble + trimmed


def process_feedback(src_file: Path) -> None:
    """Prepend user-feedback entry from a queue JSON file; move file to processed/."""
    data = json.loads(src_file.read_text(encoding="utf-8"))
    body = data.get("body", "").strip()
    chat_id = data.get("from_chat_id", "unknown")
    utc = data.get("received_at") or _utc_now()
    basename = src_file.name

    content = _read_notes()
    if _already_seen(basename, content):
        print(f"skip (already seen): {basename}")
        return

    entry = (
        f"## {utc} user feedback (chat {chat_id})\n"
        f"<!-- src: {basename} -->\n"
        f"\n"
        f"{body}\n"
    )
    _atomic_write(NOTES_PATH, _prepend(content, entry))

    # Move to processed/ — atomically rename if possible
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / basename
    if not dest.exists():
        src_file.rename(dest)
    else:
        # Already in processed (rename failed and then retried), just remove
        src_file.unlink()
    print(f"processed: {basename}")


def process_observation() -> None:
    """Prepend a manager-observation entry read from stdin."""
    body = sys.stdin.read().strip()
    if not body:
        print("error: empty stdin for observation", file=sys.stderr)
        sys.exit(1)
    utc = _utc_now()
    entry = f"## {utc} manager observation\n\n{body}\n"
    content = _read_notes()
    _atomic_write(NOTES_PATH, _prepend(content, entry))
    print(f"wrote observation at {utc}")


def drain_feedback_queue() -> None:
    """Process all pending *_feedback*.json files, flock-guarded."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            files = sorted(
                list(QUEUE_DIR.glob("*_feedback.json"))
                + list(QUEUE_DIR.glob("*_feedback-*.json")),
                key=lambda p: p.name,
            )
            if not files:
                print("drain: no feedback queue files")
                return
            for src_file in files:
                try:
                    process_feedback(src_file)
                except Exception as exc:
                    print(f"error processing {src_file.name}: {exc}", file=sys.stderr)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--source",
        choices=["feedback", "observation"],
        help="feedback: needs --src-file; observation: reads stdin",
    )
    group.add_argument(
        "--drain-feedback-queue",
        action="store_true",
        help="process all pending *_feedback*.json queue files (flock-guarded)",
    )
    parser.add_argument("--src-file", type=Path, help="queue JSON file (required for --source feedback)")
    args = parser.parse_args()

    if args.drain_feedback_queue:
        drain_feedback_queue()
    elif args.source == "feedback":
        if not args.src_file:
            parser.error("--source feedback requires --src-file <path>")
        process_feedback(args.src_file)
    elif args.source == "observation":
        process_observation()


if __name__ == "__main__":
    main()
