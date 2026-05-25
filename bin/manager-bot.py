#!/usr/bin/env python3
"""manager-bot.py — Telegram dispatcher for manager skills.

Receives commands from Telegram, resolves the project token to a persona,
writes a queue file, and spawns the matching `<persona>-manager` skill in
the project's cwd. The manager fulfills the command and replies via
notify-telegram.sh — the bot never reads project state itself.

Project-agnostic commands (/help, /projects, bare /ping with no token) are
handled inline. All project-scoped commands are dispatched.

Setup: see ~/Dev/docs/telegram_bot_setup.md (BotFather, chat-id discovery,
service unit / rc.d wiring).

Required env (typically from a .env file):
  TELEGRAM_BOT_TOKEN   — from BotFather
  TELEGRAM_CHAT_ID     — your numeric chat id (allowlist)

Optional env:
  MANAGER_STATE_DIR    — default ~/.claude/state
  MANAGER_SKILL_NAME   — any truthy value enables on-demand command routing;
                         the actual skill name is derived from the project token
                         (e.g. token "cm" -> /cm-manager). When unset, every
                         project-scoped command queues for the next periodic tick.
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
# When set, enables on-demand command routing: every project-scoped command
# spawns `/<persona>-manager --process-command <queue-file>` in the project's
# cwd immediately, and the manager replies via Telegram. The value itself is
# not the skill name; the skill name is derived from the project token
# (e.g. token "skill-set" -> skill "skill-set-manager"). When unset, commands
# queue for the next periodic manager tick or chain-runner pre-iter drain.
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
# They are always processed inline regardless of project token.
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

    Two emission shapes (SPEC 30.3):

    1. **Legacy per-project manager** (no `operator-level: true` in the yaml
       block). The folder name minus `-manager` is the persona token; all
       watched-projects are attached to that single persona. This preserves
       cm-manager and similar pre-collapse instances.
    2. **Operator-level manager** (`operator-level: true` in the yaml block).
       Each watched-project's `name:` field is a separate persona token; one
       record is emitted per watched-project, scoped to that single project.
       The folder name (e.g. `rob`) is treated as an operator label, not a
       routable token, and is NOT emitted as a persona. This is the
       post-migration shape documented in docs/migration-single-manager.md.

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
        fm_match = _re.match(r"^---\s*\n(.*?)\n---", body, _re.DOTALL)
        if not fm_match:
            continue
        frontmatter = fm_match.group(1)
        if not _re.search(r"^transferable\s*:", frontmatter, _re.MULTILINE):
            continue
        folder_persona = folder[: -len("-manager")]
        projects: list[dict] = []
        operator_level = False
        block_match = _re.search(r"```yaml\s*\n(.*?)```", body, _re.DOTALL)
        if block_match:
            block = block_match.group(1)
            if _re.search(r"^operator-level\s*:\s*true\s*$", block, _re.MULTILINE):
                operator_level = True
            if "watched-projects:" in block:
                # Walk the block line-by-line: each `- path: <val>` starts a
                # project record; an immediately-following `  name: <val>`
                # (any deeper-indented continuation lines, in practice) sets
                # the explicit name. Falls back to the path's basename when
                # name: is omitted.
                in_wp = False
                cur: dict | None = None
                for raw in block.splitlines():
                    line = raw.rstrip()
                    if not line:
                        continue
                    if _re.match(r"^watched-projects\s*:", line):
                        in_wp = True
                        continue
                    if in_wp and _re.match(r"^\S", line):
                        # Left the watched-projects block (next top-level key).
                        if cur is not None:
                            projects.append(cur)
                            cur = None
                        in_wp = False
                        continue
                    if not in_wp:
                        continue
                    m_path = _re.match(r"^\s+-\s+path\s*:\s*(.+?)\s*$", line)
                    if m_path:
                        if cur is not None:
                            projects.append(cur)
                        path_val = m_path.group(1).strip()
                        cur = {"path": path_val, "name": Path(path_val).name}
                        continue
                    m_name = _re.match(r"^\s+name\s*:\s*(.+?)\s*$", line)
                    if m_name and cur is not None:
                        cur["name"] = m_name.group(1).strip()
                        continue
                if cur is not None:
                    projects.append(cur)
        if operator_level and projects:
            for proj in projects:
                results.append({"persona": proj["name"], "projects": [proj]})
        else:
            results.append({"persona": folder_persona, "projects": projects})
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


def spawn_manager_for_command(
    persona: str,
    project_cwd: str | None,
    queue_file: Path,
) -> bool:
    """Spawn `/<persona>-manager --process-command <queue-file>` in project_cwd.

    Returns True if the spawn was launched successfully. The manager runs
    asynchronously and owns the Telegram reply. Returns False when
    MANAGER_SKILL_NAME is unset (dispatching disabled) or the spawn fails;
    in either case the queue file remains for the next periodic tick or
    chain-runner pre-iter drain to pick up.
    """
    if not MANAGER_SKILL_NAME:
        return False
    ON_DEMAND_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = ON_DEMAND_LOG_DIR / f"{queue_file.stem}.log"
    skill_name = f"{persona}-manager"
    cwd_str = str(Path(project_cwd).expanduser()) if project_cwd else None
    cmd = [
        CLAUDE_BIN,
        "--print",
        "--permission-mode",
        "bypassPermissions",
        f"/{skill_name} --process-command {queue_file}",
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
                cwd=cwd_str,
            )
    except Exception as exc:
        logger.error("on-demand manager spawn failed: %s", exc)
        return False
    logger.info(
        "spawned %s --process-command for %s (cwd=%s, log=%s)",
        skill_name, queue_file.name, cwd_str, log_path,
    )
    return True


def _route_via_dispatcher(cmd: str, token: str, queue_file: Path) -> str:
    """Route a queued command through the on-demand manager spawn, or fall back to queue-only.

    When MANAGER_SKILL_NAME is unset, always queues. When set, resolves the
    token against discovered personas; unknown token returns an error message
    with the known token list; on successful spawn returns a routing ack.
    """
    if not MANAGER_SKILL_NAME:
        return f"Queued `/{cmd}`. Next manager run will process it."

    all_personas = _discover_manager_personas()
    persona_entry = next((p for p in all_personas if p["persona"] == token), None)
    if persona_entry is None:
        known = sorted(p["persona"] for p in all_personas)
        listing = ", ".join(known) if known else "(none discovered)"
        return (
            f"Unknown project token: `{token}`. Known: {listing}. "
            "Run /projects to see the live registry."
        )

    cwd = persona_entry["projects"][0]["path"] if persona_entry["projects"] else None
    spawned = spawn_manager_for_command(token, cwd, queue_file)
    if spawned:
        return f"Routing /{cmd} to {token} — reply incoming when it lands."
    return f"Queued `/{cmd}` (file: `{queue_file.name}`). Next manager run will process it."


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
            return "Usage: /feedback <project> <message>\n(give the supervisor steering input or course corrections)"
        token = body.split()[0]
        path = queue_feedback(body, chat_id)
        return _route_via_dispatcher("feedback", token, path)

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

    # Project-agnostic commands — always handled inline.
    if cmd == "ping" and not args:
        return "pong from dispatcher"

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
            f"`{QUEUE_DIR}` and spawn the matching manager skill when routing is enabled.\n\n"
            "When on-demand routing is enabled (MANAGER_SKILL_NAME set), replies arrive via "
            "Telegram from the manager. Otherwise commands queue for the next periodic tick."
        )

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

    # All project-scoped commands (including /ping <persona>) go through the dispatcher.
    if cmd == "promote" and len(args) < 2:
        return "Usage: /promote <project> <skill>"

    if not args:
        return f"Usage: /{cmd} <project>\n(project token required — run /projects to see known tokens)"

    token = args[0]
    path = queue_task(cmd, args, chat_id)
    return _route_via_dispatcher(cmd, token, path)


def main() -> int:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("manager-bot starting; state=%s", STATE_DIR)
    logger.info("allowlisted chat: %s", CHAT_ID_ALLOW or "<any (insecure)>")
    if MANAGER_SKILL_NAME:
        logger.info(
            "on-demand command routing enabled (verbs: status, objectives, proposals, "
            "promote, pause, resume, feedback, ping): claude=%s",
            CLAUDE_BIN,
        )
    else:
        logger.info(
            "on-demand command routing disabled (MANAGER_SKILL_NAME unset); "
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
