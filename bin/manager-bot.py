#!/usr/bin/env python3
"""manager-bot.py — long-poll Telegram bot for the manager skill.

Sits between the user (on Telegram) and the manager skill. Pulls updates via
getUpdates (no webhook needed — works behind NAT / on a laptop), filters by
TELEGRAM_CHAT_ID, and translates inbound commands into queue files under
~/.claude/state/manager-bot-queue/. The next manager-skill invocation drains
the queue.

Critical separation: this bot NEVER spawns the agent harness or runs Claude.
It only writes JSON files. The user (or cron) triggers /<persona>-manager
and the manager processes the queue.

Setup: see ~/Dev/docs/telegram_bot_setup.md (BotFather, chat-id discovery,
service unit / rc.d wiring).

Required env (typically from a .env file):
  TELEGRAM_BOT_TOKEN  — from BotFather
  TELEGRAM_CHAT_ID    — your numeric chat id (allowlist)

Optional env:
  MANAGER_STATE_DIR   — default ~/.claude/state
"""

import datetime as _dt
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("manager-bot requires `requests` (pip install requests)", file=sys.stderr)
    sys.exit(1)

# Optionally load .env from a file pointed at by $TELEGRAM_ENV_FILE.
env_file = os.environ.get("TELEGRAM_ENV_FILE")
if env_file and Path(env_file).exists():
    for line in Path(env_file).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'").strip('"'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("manager-bot")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID_ALLOW = os.environ.get("TELEGRAM_CHAT_ID")  # numeric, as string
STATE_DIR = Path(os.environ.get("MANAGER_STATE_DIR", str(Path.home() / ".claude" / "state")))
QUEUE_DIR = STATE_DIR / "manager-bot-queue"
DIGESTS_DIR = STATE_DIR / "manager-digests"

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is required")
    sys.exit(1)
if not CHAT_ID_ALLOW:
    logger.warning("TELEGRAM_CHAT_ID not set; bot will reply to any chat (NOT RECOMMENDED)")

API = f"https://api.telegram.org/bot{TOKEN}"

KNOWN_COMMANDS = {"status", "objectives", "proposals", "promote", "pause", "resume", "ping", "help", "feedback"}


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_filestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def get_updates(offset: int = 0) -> list:
    try:
        r = requests.get(
            f"{API}/getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35,
        )
        if r.status_code == 200 and r.json().get("ok"):
            return r.json()["result"]
    except requests.Timeout:
        pass
    except Exception as e:
        logger.error(f"Poll error: {e}")
    return []


def send_reply(chat_id: int, text: str, parse_mode: str | None = "Markdown") -> None:
    try:
        payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        requests.post(f"{API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Reply failed: {e}")


def queue_task(command: str, args: list[str], from_chat_id: int) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = QUEUE_DIR / f"{_utc_filestamp()}_{command}.json"
    payload = {
        "command": command,
        "args": args,
        "received_at": _utc_iso(),
        "from_chat_id": from_chat_id,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def queue_feedback(body: str, from_chat_id: int) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _utc_filestamp()
    path = QUEUE_DIR / f"{stamp}_feedback.json"
    # The shared 1-second filestamp resolution would silently overwrite a
    # second feedback submitted in the same second, dropping user input.
    suffix = 2
    while path.exists():
        path = QUEUE_DIR / f"{stamp}_feedback-{suffix}.json"
        suffix += 1
    payload = {
        "command": "feedback",
        "body": body,
        "received_at": _utc_iso(),
        "from_chat_id": from_chat_id,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def latest_digest() -> str | None:
    if not DIGESTS_DIR.is_dir():
        return None
    files = sorted(DIGESTS_DIR.glob("*.txt"), reverse=True)
    if not files:
        return None
    return files[0].read_text(encoding="utf-8")


def handle_command(text: str, chat_id: int) -> str:
    """Parse one command line and return the reply text. Side-effect: queues a task when appropriate."""
    # Feedback captures the full message body verbatim (preserving whitespace
    # and newlines), so split-by-whitespace would corrupt multi-line input.
    # Match the leading `/feedback` token (optional @botname) and take
    # everything after the first separator as the body.
    fb_match = re.match(r"^/feedback(?:@\S+)?(?:\s+(.*))?$", text, flags=re.DOTALL)
    if fb_match:
        body = (fb_match.group(1) or "").strip()
        if not body:
            return "Usage: /feedback <message>\n(give the supervisor steering input or course corrections)"
        path = queue_feedback(body, chat_id)
        return (
            f"Queued feedback ({len(body)} chars). "
            "Next manager run will route it to the supervisor."
        )

    parts = text.lstrip("/").split()
    if not parts:
        return "Empty command. Try /help."
    cmd = parts[0].lower()
    # Strip @botname suffix (e.g. /status@my_manager_bot)
    if "@" in cmd:
        cmd = cmd.split("@", 1)[0]
    args = parts[1:]

    if cmd not in KNOWN_COMMANDS:
        return f"Unknown command: `{cmd}`\nKnown: {', '.join(sorted(KNOWN_COMMANDS))}"

    if cmd == "ping":
        return "pong"

    if cmd == "help":
        return (
            "Manager bot commands:\n"
            "/status — most recent manager digest\n"
            "/objectives — current objectives.md\n"
            "/proposals — list pending skill-patch proposals\n"
            "/promote <project> <skill> — queue a /promote-skill-proposal run\n"
            "/feedback <message> — steer the supervisor (course corrections, focus, do/don't)\n"
            "/pause — manager skips its next scheduled run\n"
            "/resume — manager runs again at next schedule\n"
            "/ping — bot liveness check\n\n"
            "All commands except /ping and /help write a queue file at "
            f"`{QUEUE_DIR}` for the next manager-skill invocation to process."
        )

    if cmd == "status":
        digest = latest_digest()
        if not digest:
            return "No digest yet. Run the manager skill at least once."
        if len(digest) > 3500:
            digest = digest[:3450] + "\n\n... [truncated]"
        return digest

    if cmd in {"objectives", "proposals", "promote", "pause", "resume"}:
        if cmd == "promote" and len(args) < 2:
            return "Usage: /promote <project> <skill>"
        path = queue_task(cmd, args, chat_id)
        return f"Queued `/{cmd}` (file: `{path.name}`). Next manager run will process it."

    return f"Unknown command: `{cmd}`"


def main() -> int:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("manager-bot starting; state=%s", STATE_DIR)
    logger.info("allowlisted chat: %s", CHAT_ID_ALLOW or "<any (insecure)>")
    offset = 0
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = (msg.get("text") or "").strip()
            if not text or not chat_id:
                continue
            if CHAT_ID_ALLOW and str(chat_id) != str(CHAT_ID_ALLOW):
                logger.warning("Ignored message from unauthorized chat %s: %r", chat_id, text[:80])
                continue
            logger.info("Received from %s: %r", chat_id, text[:120])
            if not text.startswith("/"):
                send_reply(chat_id, "I only understand commands. Try /help.")
                continue
            try:
                reply = handle_command(text, chat_id)
            except Exception as exc:
                logger.exception("handle_command failed")
                reply = f"Error: {exc}"
            if reply:
                send_reply(chat_id, reply)
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main() or 0)
