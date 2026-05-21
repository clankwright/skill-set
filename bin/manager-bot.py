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
import shutil
import subprocess
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
# Persona-specific manager skill name (e.g. "skill-set-manager", "sdrai-manager").
# When set, the bot spawns `claude --print "/<skill> --process-feedback <queue-file>"`
# out-of-band on each /feedback so on-demand routing happens within seconds rather
# than waiting for the next cron tick. When unset, /feedback queues only and the
# next periodic-mode tick (or chain-runner pre-iter drain) does verbatim routing.
MANAGER_SKILL_NAME = os.environ.get("MANAGER_SKILL_NAME")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"
ON_DEMAND_LOG_DIR = STATE_DIR / "manager-bot-spawn-log"

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is required")
    sys.exit(1)
if not CHAT_ID_ALLOW:
    logger.warning("TELEGRAM_CHAT_ID not set; bot will reply to any chat (NOT RECOMMENDED)")

API = f"https://api.telegram.org/bot{TOKEN}"

KNOWN_COMMANDS = {"status", "objectives", "proposals", "promote", "pause", "resume", "ping", "help", "feedback", "projects"}

# Commands that operate at the bot level and never target a specific persona.
# They are always processed regardless of project token.
PROJECT_AGNOSTIC_COMMANDS = {"ping", "help", "projects"}


def route_queue_payload(
    payload: dict,
    my_persona: str,
    known_personas: list[str],
) -> tuple[str, str]:
    """Route a queue file payload to this manager (or another) by project token.

    For non-agnostic commands the project token is the FIRST whitespace-delimited
    arg (`args[0]` for command payloads; `body.split()[0]` for feedback). The
    project-token convention is anti-fork: this function never defaults to
    `my_persona` when the token is missing — silently assuming would let a
    skill-set-intended message corrupt cm's state file (and vice versa).

    Returns (action, detail) where action is one of:
      - "act": this manager should process the command.
      - "skip": another known persona owns it; leave the queue file alone.
      - "refuse-missing": no project token; refuse with usage detail.
      - "refuse-unknown": token is not a known persona; refuse with usage detail.

    `detail` is a one-line human-readable string for the refuse-* cases that
    names the discovery surface (`/projects`) and lists known personas; empty
    for act/skip.
    """
    command = (payload.get("command") or "").lower()
    if command in PROJECT_AGNOSTIC_COMMANDS:
        return ("act", "")

    if command == "feedback":
        body = payload.get("body") or ""
        if not body.strip():
            return ("refuse-missing", _refusal_detail(known_personas))
        token = body.split()[0]
    else:
        args = payload.get("args") or []
        if not args:
            return ("refuse-missing", _refusal_detail(known_personas))
        token = args[0]

    if token == my_persona:
        return ("act", "")
    if token in known_personas:
        return ("skip", "")
    return ("refuse-unknown", _refusal_detail(known_personas))


def _refusal_detail(known_personas: list[str]) -> str:
    listing = ", ".join(sorted(known_personas)) if known_personas else "(none discovered)"
    return (
        f"Project token required as the first arg. "
        f"Use /<command> <token> ... — known: {listing}. "
        f"Send /projects for the live registry."
    )

# Default root for persona discovery; override in tests.
SKILLS_ROOT = Path.home() / ".claude" / "skills"


def _discover_manager_personas(skills_root: Path | None = None) -> list[dict]:
    """Scan skills_root/*-manager/SKILL.md and return persona + project info.

    Each entry: {'persona': str, 'projects': [{'path': str, 'name': str}, ...]}.
    Persona is derived by stripping the '-manager' suffix from the folder name.
    The watched-projects block is parsed from a fenced yaml block in the body;
    if absent, 'projects' is an empty list.

    Files without a `transferable:` key in their YAML frontmatter are skipped —
    they are transferable template files (e.g. sst-manager), not real deployed
    persona instances. Proprietary persona instances always declare
    `transferable: sst-manager` (or similar) in their frontmatter.
    """
    import re as _re
    root = skills_root if skills_root is not None else SKILLS_ROOT
    results = []
    for skill_md in sorted(root.glob("*-manager/SKILL.md")):
        folder = skill_md.parent.name  # e.g. "cm-manager"
        if not folder.endswith("-manager"):
            continue
        body = skill_md.read_text(encoding="utf-8", errors="replace")
        # Extract the YAML frontmatter block (content between the first pair of ---).
        fm_match = _re.match(r"^---\s*\n(.*?)\n---", body, _re.DOTALL)
        if not fm_match:
            continue  # no frontmatter at all; skip
        frontmatter = fm_match.group(1)
        # Skip transferable template files — they lack a transferable: key.
        if not _re.search(r"^transferable\s*:", frontmatter, _re.MULTILINE):
            continue
        persona = folder[: -len("-manager")]
        projects: list[dict] = []
        # Find a fenced yaml block containing watched-projects:.
        block_match = _re.search(
            r"```yaml\s*\n(.*?)```", body, _re.DOTALL
        )
        if block_match:
            block = block_match.group(1)
            if "watched-projects:" in block:
                # Parse path: / name: pairs under watched-projects:.
                for m in _re.finditer(
                    r"^\s+-\s+path:\s*(.+?)\s*$.*?(?:^\s+name:\s*(.+?)\s*$)?",
                    block, _re.MULTILINE | _re.DOTALL
                ):
                    path_val = m.group(1).strip()
                    name_val = (m.group(2) or "").strip() or Path(path_val).name
                    projects.append({"path": path_val, "name": name_val})
        results.append({"persona": persona, "projects": projects})
    return results


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


def spawn_on_demand_manager(queue_file: Path) -> bool:
    """Spawn `claude --print "/<persona>-manager --process-feedback <queue-file>"`
    out-of-band so on-demand routing happens within seconds. Returns True if the
    spawn was launched successfully (the manager runs asynchronously; we don't
    wait for the result — Telegram reply-on-routing-completion is the manager's
    own responsibility). Returns False if MANAGER_SKILL_NAME is unset or the
    spawn fails to launch; in either case the queue file remains in place and
    the next periodic-mode tick or chain-runner pre-iter drain will catch up.
    """
    if not MANAGER_SKILL_NAME:
        return False
    ON_DEMAND_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = ON_DEMAND_LOG_DIR / f"{queue_file.stem}.log"
    cmd = [
        CLAUDE_BIN,
        "--print",
        "--permission-mode",
        "bypassPermissions",
        f"/{MANAGER_SKILL_NAME} --process-feedback {queue_file}",
    ]
    try:
        with open(log_path, "ab", buffering=0) as log_fd:
            subprocess.Popen(
                cmd,
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
    except Exception as exc:
        logger.error("on-demand manager spawn failed: %s", exc)
        return False
    logger.info("spawned on-demand manager for %s (log=%s)", queue_file.name, log_path)
    return True


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
        spawned = spawn_on_demand_manager(path)
        if spawned:
            return (
                f"Routing feedback ({len(body)} chars) through the manager — "
                "Telegram update incoming when it lands."
            )
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
            "/status <project> — most recent manager digest\n"
            "/objectives <project> — current objectives.md\n"
            "/proposals <project> — list pending skill-patch proposals\n"
            "/promote <project> <skill> — queue a /promote-skill-proposal run\n"
            "/feedback <project> <message> — steer the supervisor; on-demand manager spawns if configured, otherwise queues for next periodic run\n"
            "/pause <project> — pause this persona's scheduled runs\n"
            "/resume <project> — resume this persona's scheduled runs\n"
            "/projects — list known personas, project roots, and their tokens\n"
            "/ping — bot liveness check\n"
            "/help — this message\n\n"
            "Project token is REQUIRED for all commands except /ping, /help, and /projects\n"
            "(e.g. `/status cm`, `/feedback cm <text>`). Run `/projects` to see the live\n"
            "token-to-project registry.\n\n"
            "Token-required commands write a queue file at "
            f"`{QUEUE_DIR}` for the next manager-skill invocation to process.\n\n"
            "Replies are live only during chain runs; commands sent between runs "
            "queue and ack on the next session start."
        )

    if cmd == "status":
        digest = latest_digest()
        if not digest:
            return "No digest yet. Run the manager skill at least once."
        if len(digest) > 3500:
            digest = digest[:3450] + "\n\n... [truncated]"
        return digest

    if cmd == "projects":
        personas = _discover_manager_personas()
        if not personas:
            return (
                "No manager personas found.\n"
                f"Install a `*-manager/SKILL.md` under `{SKILLS_ROOT}` to register one."
            )
        lines = []
        for entry in sorted(personas, key=lambda x: x["persona"]):
            persona = entry["persona"]
            projs = entry["projects"]
            if projs:
                for p in projs:
                    lines.append(f"`{persona}` -> {p['path']} (token: `{persona}`)")
            else:
                lines.append(f"`{persona}` -> (no watched-projects configured)")
        return "Registered personas:\n" + "\n".join(lines)

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
    if MANAGER_SKILL_NAME:
        logger.info(
            "on-demand /feedback routing enabled: claude=%s skill=/%s",
            CLAUDE_BIN, MANAGER_SKILL_NAME,
        )
    else:
        logger.info(
            "on-demand /feedback routing disabled (MANAGER_SKILL_NAME unset); "
            "queue-only fallback active"
        )
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
