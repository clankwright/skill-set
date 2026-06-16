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
#   TELEGRAM_ENV_FILE    — path to a .env file with TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID;
#                          auto-sourced ONLY when TELEGRAM_BOT_TOKEN is not already exported.
#                          Lets `TELEGRAM_ENV_FILE=<env-path> bash notify-telegram.sh` work
#                          directly without a manual subshell pre-source. Explicit shell env
#                          wins (auto-source is skipped if the caller already set the token).
#
# Credential resolution order (first match wins):
#   1. Caller-exported TELEGRAM_BOT_TOKEN (already in env).
#   2. TELEGRAM_ENV_FILE (sourced when TELEGRAM_BOT_TOKEN is not yet set).
#   3. ~/Dev/skill-set/telegram.env (base-dir fallback; shared channel for all skill-set
#      projects; only tried when neither of the above is available).
#   4. No credentials found — logs "skipping send" to stderr and exits 0 (graceful skip).
#   TELEGRAM_PARSE_MODE  — "Markdown" (default), "MarkdownV2", "HTML", or empty for plain.
#   TELEGRAM_LABEL       — when set non-empty, prepends "[<label>]\n\n" to the body so the
#                          recipient can distinguish messages from different personas sharing
#                          the same chat. Empty / unset = legacy behavior unchanged.
#                          bin/skill-chain.py sets this via the --label flag automatically.
#
# Behavior:
#   - Reads stdin, splits into ≤4000-char chunks at newline boundaries. Code fences (```)
#     spanning a split boundary are closed at the end of the first chunk and reopened at the
#     start of the next so every chunk is valid Markdown.
#   - POSTs each chunk to https://api.telegram.org/bot<TOKEN>/sendMessage with a 100ms delay
#     between chunks to preserve message ordering on the client.
#   - Exit 0 when all chunks succeed; non-zero on any Telegram API error.

set -euo pipefail

if [ -n "${TELEGRAM_ENV_FILE:-}" ] && [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    if [ ! -r "$TELEGRAM_ENV_FILE" ]; then
        echo "notify-telegram: TELEGRAM_ENV_FILE=$TELEGRAM_ENV_FILE not readable" >&2
        exit 1
    fi
    set -a; . "$TELEGRAM_ENV_FILE"; set +a
fi

# Base-dir fallback: ~/Dev/skill-set/telegram.env is the shared Telegram channel for all
# projects using skill-set. Fires only when no more-specific env is already configured
# (explicit TELEGRAM_BOT_TOKEN or TELEGRAM_ENV_FILE always wins).
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] && [ -z "${TELEGRAM_ENV_FILE:-}" ]; then
    _SST_BASE_ENV="${HOME}/Dev/skill-set/telegram.env"
    if [ -r "$_SST_BASE_ENV" ]; then
        set -a; . "$_SST_BASE_ENV"; set +a
    fi
    unset _SST_BASE_ENV
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "notify-telegram: no credentials configured; skipping send" >&2
    exit 0
fi
PARSE_MODE="${TELEGRAM_PARSE_MODE-Markdown}"

text="$(cat)"
if [ -z "$text" ]; then
    echo "notify-telegram: empty stdin; nothing to send" >&2
    exit 1
fi

if [ -n "${TELEGRAM_LABEL:-}" ]; then
    text="[${TELEGRAM_LABEL}]"$'\n\n'"${text}"
fi

# POST one chunk via curl; build the JSON payload using python's json.dumps for safe escaping.
_send_chunk() {
    local body="$1"
    local payload
    payload=$(TEXT="$body" CID="$TELEGRAM_CHAT_ID" MODE="$PARSE_MODE" python3 - <<'PY'
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
    local response ok
    response=$(
        curl -sS -X POST \
            -H 'Content-Type: application/json' \
            --max-time 15 \
            --data "$payload" \
            "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
    )
    ok=$(printf '%s' "$response" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("yes" if d.get("ok") else "no")' 2>/dev/null || echo no)
    if [ "$ok" != "yes" ]; then
        echo "notify-telegram: API returned non-ok response:" >&2
        printf '%s\n' "$response" >&2
        return 1
    fi
}

if [ "${#text}" -le 4000 ]; then
    _send_chunk "$text"
else
    # Split at newline boundaries; close any open code fence (```) that spans the split
    # point so every chunk is valid Markdown, then reopen it at the start of the next chunk.
    _first_chunk=true
    while IFS= read -r -d '' _chunk; do
        [ -n "$_chunk" ] || continue
        if [ "$_first_chunk" = true ]; then
            _first_chunk=false
        else
            sleep 0.1
        fi
        _send_chunk "$_chunk"
    done < <(TEXT="$text" python3 - <<'PY'
import os, sys

text = os.environ["TEXT"]
MAX = 4000


def split_chunks(text, max_len, min_chunk=200):
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        candidate = text[:max_len]
        last_nl = candidate.rfind('\n')
        # Prefer the last newline, but require a minimum chunk size to avoid
        # near-empty chunks that trigger infinite rebalancing loops.
        split_at = last_nl + 1 if last_nl > 0 else max_len
        if split_at < min_chunk:
            split_at = max_len
        chunk = text[:split_at]
        # If the chunk ends with an open code fence, close it so the chunk is valid Markdown.
        if chunk.count('```') % 2 == 1:
            chunk = chunk.rstrip('\n') + '\n```'
            text = '```\n' + text[split_at:]
        else:
            text = text[split_at:]
        chunks.append(chunk)
    return chunks


for part in split_chunks(text, MAX):
    sys.stdout.buffer.write(part.encode('utf-8') + b'\x00')
PY
)
fi
