#!/usr/bin/env python3
"""Stub 'claude --print' binary for integration tests (SPEC 35.8).

Invoked by spawn_manager_for_command as:
  python3 stub_claude.py --print --permission-mode bypassPermissions
      "/<persona>-manager --process-command <queue-file>"

Reads the queue file, writes a JSON capture file for the test to assert, and
writes a simulated "telegram" capture representing what a real manager would
send via notify-telegram.sh.

Environment variables:
  STUB_CAPTURE_FILE      — path where invocation details + queue content are written
  STUB_TELEGRAM_CAPTURE  — path where simulated Telegram payload is written
"""
import json
import os
import sys
from pathlib import Path

capture_file = Path(os.environ.get("STUB_CAPTURE_FILE", "/tmp/stub_claude_capture.json"))
telegram_capture = Path(os.environ.get("STUB_TELEGRAM_CAPTURE", "/tmp/stub_claude_telegram.json"))

last_arg = sys.argv[-1] if len(sys.argv) > 1 else ""

if "--process-command" not in last_arg:
    capture_file.write_text(json.dumps({"args": sys.argv[1:], "no_queue": True}))
    sys.exit(0)

qfile_str = last_arg.split("--process-command", 1)[1].strip()
try:
    qdata = json.loads(Path(qfile_str).read_text())
except Exception as exc:
    qdata = {"error": str(exc)}

# Write invocation details: args, cwd, and the parsed queue file content.
capture_file.write_text(json.dumps({
    "args": sys.argv[1:],
    "cwd": os.getcwd(),
    "queue_file": qfile_str,
    "queue_content": qdata,
}, indent=2))

# Simulate the manager's Telegram reply (what a real manager would send via
# notify-telegram.sh after processing the command).
telegram_capture.write_text(json.dumps({
    "command": qdata.get("command"),
    "from_chat_id": qdata.get("from_chat_id"),
    "persona": "stub-manager",
    "reply": f"[stub] processed command: {qdata.get('command')}",
}, indent=2))
