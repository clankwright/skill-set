#!/usr/bin/env bash
# notify-human-md.sh — diff docs/HUMAN.md against the last-notified snapshot
# and send a brief Telegram summary of any delta (new entries, section moves,
# [ ]↔[x] flips). Idempotent: no change since snapshot → no send.
#
# Usage:
#   bin/notify-human-md.sh <project-root> [<human-md-path>] [--telegram-env <path>]
#
# Arguments:
#   project-root     Path to the watched project root (derives the snapshot key).
#   human-md-path    Path to HUMAN.md (default: <project-root>/docs/HUMAN.md).
#   --telegram-env   Explicit .env file; forwarded as TELEGRAM_ENV_FILE to
#                    notify-telegram.sh, overriding the automatic resolution chain.
#
# Telegram env is resolved via the same chain as bin/notify-telegram.sh:
#   1. Caller-exported TELEGRAM_BOT_TOKEN.
#   2. TELEGRAM_ENV_FILE env var (path to a .env file with TOKEN + CHAT_ID).
#   3. ~/Dev/skill-set/telegram.env base-dir fallback.
#   4. Graceful skip (exit 0 + stderr note) when nothing is configured.
#
# Optional env overrides (used by tests):
#   HUMAN_MD_SNAPSHOT_DIR   Override the snapshot storage directory.
#                           Default: ~/.claude/state/human-md-snapshots/
#   NOTIFY_TELEGRAM_BIN     Override the path to notify-telegram.sh.
#                           Default: <this-script's-dir>/notify-telegram.sh
#   TELEGRAM_LABEL          Forwarded to notify-telegram.sh for multi-persona
#                           labeling (prepends "[<label>]\n\n" to the body).
#
# Snapshot files (per project):
#   <snapshot-dir>/<slug>.sha    SHA256 of the last-notified HUMAN.md content.
#   <snapshot-dir>/<slug>.cache  Full content of the last-notified snapshot.
#
# Message format: "[<project>] HUMAN.md: <delta summary>"
#   delta items: "+H3.2 ##High \"<title>\"", "H3.1 [ ]→[x]", "H3.1 ##Blocking→##Done"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- arg parsing ---
PROJECT_ROOT=""
HUMAN_MD_PATH_ARG=""
TELEGRAM_ENV_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --telegram-env)
            if [[ $# -lt 2 ]]; then
                echo "notify-human-md: --telegram-env requires a path argument" >&2
                exit 1
            fi
            TELEGRAM_ENV_OVERRIDE="$2"
            shift 2
            ;;
        -*)
            echo "notify-human-md: unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$PROJECT_ROOT" ]]; then
                PROJECT_ROOT="$1"
            elif [[ -z "$HUMAN_MD_PATH_ARG" ]]; then
                HUMAN_MD_PATH_ARG="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$PROJECT_ROOT" ]]; then
    echo "notify-human-md: usage: notify-human-md.sh <project-root> [<human-md-path>] [--telegram-env <path>]" >&2
    exit 1
fi

# Resolve HUMAN.md path
HUMAN_MD="${HUMAN_MD_PATH_ARG:-${PROJECT_ROOT}/docs/HUMAN.md}"

# If HUMAN.md does not exist, nothing to do
if [[ ! -f "$HUMAN_MD" ]]; then
    echo "notify-human-md: HUMAN.md not found at $HUMAN_MD; skipping" >&2
    exit 0
fi

# Notify-telegram binary (overridable in tests)
NOTIFY_TG_BIN="${NOTIFY_TELEGRAM_BIN:-${SCRIPT_DIR}/notify-telegram.sh}"

# Snapshot directory
SNAPSHOT_DIR="${HUMAN_MD_SNAPSHOT_DIR:-${HOME}/.claude/state/human-md-snapshots}"
mkdir -p "$SNAPSHOT_DIR"

# Snapshot key: absolute project root with / replaced by _
PROJECT_ROOT_ABS="$(cd "$PROJECT_ROOT" && pwd)"
SNAPSHOT_KEY="$(printf '%s' "$PROJECT_ROOT_ABS" | tr '/' '_' | sed 's/^_//')"
SNAPSHOT_SHA_FILE="${SNAPSHOT_DIR}/${SNAPSHOT_KEY}.sha"
SNAPSHOT_CACHE_FILE="${SNAPSHOT_DIR}/${SNAPSHOT_KEY}.cache"

# Current SHA
CURRENT_SHA="$(sha256sum "$HUMAN_MD" | awk '{print $1}')"

# Idempotency check
PRIOR_SHA=""
if [[ -f "$SNAPSHOT_SHA_FILE" ]]; then
    PRIOR_SHA="$(cat "$SNAPSHOT_SHA_FILE")"
fi

if [[ "$CURRENT_SHA" == "$PRIOR_SHA" ]]; then
    # No change — silent exit
    exit 0
fi

# --- compute delta via Python ---
TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT

cp "$HUMAN_MD" "${TMPDIR_WORK}/current.md"
if [[ -f "$SNAPSHOT_CACHE_FILE" ]]; then
    cp "$SNAPSHOT_CACHE_FILE" "${TMPDIR_WORK}/prior.md"
else
    touch "${TMPDIR_WORK}/prior.md"
fi

PROJECT_NAME="$(basename "$PROJECT_ROOT_ABS")"

MESSAGE="$(python3 - "$PROJECT_NAME" "${TMPDIR_WORK}/current.md" "${TMPDIR_WORK}/prior.md" <<'PY'
import sys
import re

project = sys.argv[1]
new_path = sys.argv[2]
old_path = sys.argv[3]

SECTIONS = ["Blocking", "High", "Medium", "Low", "Done"]


def parse_entries(text):
    """Return dict: H-ID -> {"section": str, "state": " " or "x", "title": str}"""
    entries = {}
    current_section = None
    for line in text.splitlines():
        m = re.match(r'^## (Blocking|High|Medium|Low|Done)\b', line)
        if m:
            current_section = m.group(1)
            continue
        if current_section is None:
            continue
        # Match entry lines: - [ ] H3.1 [easy] **Title** or - [x] H3.1 ...
        m = re.match(r'^\s*- \[( |x)\] (H\d+\.\d+)\s+(?:\[.*?\]\s+)?\*\*(.+?)\*\*', line)
        if m:
            state = m.group(1)
            hid = m.group(2)
            title = m.group(3)
            entries[hid] = {"section": current_section, "state": state, "title": title}
    return entries


with open(new_path, encoding="utf-8") as f:
    new_text = f.read()
with open(old_path, encoding="utf-8") as f:
    old_text = f.read()

old_entries = parse_entries(old_text)
new_entries = parse_entries(new_text)

deltas = []
all_ids = sorted(
    set(list(old_entries.keys()) + list(new_entries.keys())),
    key=lambda hid: [int(x) for x in re.findall(r'\d+', hid)],
)

for hid in all_ids:
    old = old_entries.get(hid)
    new = new_entries.get(hid)

    if old is None and new is not None:
        # New entry
        sec = new["section"]
        state = "[x]" if new["state"] == "x" else "[ ]"
        title = new["title"]
        deltas.append(f"+{hid} ##{sec} {state} \"{title}\"")
    elif old is not None and new is None:
        # Removed
        deltas.append(f"-{hid} (removed from ##{old['section']})")
    elif old is not None and new is not None:
        old_sec = old["section"]
        new_sec = new["section"]
        old_st = old["state"]
        new_st = new["state"]
        title = new["title"]
        sec_moved = old_sec != new_sec
        flipped = old_st != new_st
        if sec_moved and flipped:
            flip_str = "[ ]→[x]" if new_st == "x" else "[x]→[ ]"
            deltas.append(f"{hid} ##{old_sec}→##{new_sec} + {flip_str} \"{title}\"")
        elif sec_moved:
            deltas.append(f"{hid} ##{old_sec}→##{new_sec} \"{title}\"")
        elif flipped:
            flip_str = "[ ]→[x]" if new_st == "x" else "[x]→[ ]"
            deltas.append(f"{hid} {flip_str} \"{title}\"")
        # else: identical, skip

if not deltas:
    # No structured-entry delta found (e.g. only prose/whitespace changes)
    sys.exit(0)

# Format: "[project] HUMAN.md: delta1, delta2 (+N more)"
summary_items = deltas[:3]
trailer = f" (+{len(deltas) - 3} more)" if len(deltas) > 3 else ""
body = "[{}] HUMAN.md: {}{}".format(project, ", ".join(summary_items), trailer)
print(body, end="")
PY
)"

# If Python exited non-zero or returned empty message, update snapshot and exit
if [[ $? -ne 0 ]] || [[ -z "$MESSAGE" ]]; then
    printf '%s' "$CURRENT_SHA" > "$SNAPSHOT_SHA_FILE"
    cp "$HUMAN_MD" "$SNAPSHOT_CACHE_FILE"
    exit 0
fi

# --- send via notify-telegram.sh ---
# The delta summary embeds HUMAN.md entry titles verbatim, which routinely contain backticks,
# [ ]/[x] brackets, and ** that are literal content, NOT Telegram markdown. Send with
# parse_mode disabled (TELEGRAM_PARSE_MODE="") so the API never rejects it as "can't parse
# entities". (notify-telegram.sh also retries plain-text on that error as a backstop.)
if [[ -n "$TELEGRAM_ENV_OVERRIDE" ]]; then
    printf '%s' "$MESSAGE" | TELEGRAM_PARSE_MODE="" TELEGRAM_ENV_FILE="$TELEGRAM_ENV_OVERRIDE" bash "$NOTIFY_TG_BIN"
else
    printf '%s' "$MESSAGE" | TELEGRAM_PARSE_MODE="" bash "$NOTIFY_TG_BIN"
fi
# notify-telegram.sh exits 0 on graceful skip, 0 on success; propagate non-zero
TG_RC=$?

# Update snapshot regardless of send outcome (prevent retry-spam on transient failures
# is acceptable trade-off; the manager's periodic delta serves as backstop).
printf '%s' "$CURRENT_SHA" > "$SNAPSHOT_SHA_FILE"
cp "$HUMAN_MD" "$SNAPSHOT_CACHE_FILE"

exit $TG_RC
