#!/usr/bin/env bash
# notify-telegram.sh — POST stdin to Telegram sendMessage.
#
# Usage:
#   echo "hello" | notify-telegram.sh
#   notify-telegram.sh < message.txt
#
# Required env (typically sourced from a .env file the proprietary manager points at):
#   TELEGRAM_BOT_TOKEN  — from BotFather
#   TELEGRAM_CHAT_ID    — your numeric chat id (from @userinfobot or the bot's getUpdates)
#
# Optional env:
#   TELEGRAM_PARSE_MODE  — "Markdown" (default), "MarkdownV2", "HTML", or empty for plain.
#
# Behavior:
#   - Reads stdin, truncates to 4000 chars (Telegram cap is 4096; a small margin).
#   - POSTs to https://api.telegram.org/bot<TOKEN>/sendMessage.
#   - Exit 0 on Telegram "ok": true; non-zero otherwise (and prints the body to stderr).

set -euo pipefail

: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is required}"
: "${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID is required}"
PARSE_MODE="${TELEGRAM_PARSE_MODE-Markdown}"

text="$(cat)"
if [ -z "$text" ]; then
    echo "notify-telegram: empty stdin; nothing to send" >&2
    exit 1
fi

# Truncate at 4000 chars to leave headroom for parse-mode escapes.
if [ "${#text}" -gt 4000 ]; then
    text="${text:0:3950}"$'\n... [truncated; run /status for the full digest]'
fi

# Build JSON payload safely (using python's json.dumps to handle escaping).
payload=$(
    TEXT="$text" CID="$TELEGRAM_CHAT_ID" MODE="$PARSE_MODE" python3 - <<'PY'
import json, os
data = {
    "chat_id": int(os.environ["CID"]),
    "text": os.environ["TEXT"],
    "disable_web_page_preview": True,
}
mode = os.environ.get("MODE", "")
if mode:
    data["parse_mode"] = mode
print(json.dumps(data))
PY
)

response=$(
    curl -sS -X POST \
        -H 'Content-Type: application/json' \
        --max-time 15 \
        --data "$payload" \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
)

# Verify Telegram acknowledged.
ok=$(printf '%s' "$response" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("yes" if d.get("ok") else "no")' 2>/dev/null || echo no)

if [ "$ok" != "yes" ]; then
    echo "notify-telegram: API returned non-ok response:" >&2
    printf '%s\n' "$response" >&2
    exit 1
fi
