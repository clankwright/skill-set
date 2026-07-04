---
name: sst-setup-telegram
description: End-to-end Telegram bot provisioning, guided-plus-automated. Walks the user through the BotFather steps that only they can do (those touch the user's Telegram app), and automates everything else — chat-id discovery via getUpdates, credentials written to a protected .env file, outbound + inbound round-trip test, optional service-unit install for a long-poll worker, and optional /setcommands push so command suggestions show up in the client. Works for any project that wants a Telegram channel for alerts, chatops, or bot-driven human-in-loop steering.
user-invocable: true
version: 1.1.1
model-floor: sonnet
effort-floor: medium
argument-hint: "[bot display name]  [--host systemd|rc.d|tmux|none]  [--env-path <path>]"
---

# Setup Telegram

Provision a Telegram bot from zero. The skill **guides** the user through any step that requires their Telegram app (talking to BotFather, adding the bot to a group) and **automates** every step that can be done with the API + the user's shell (chat-id discovery, credentials file, send/receive test, service install).

## Operating principle

**Never fabricate credentials. Never guess the token or chat-id.** If the user hasn't done the manual step, pause and wait — don't invent plausible-looking values. Every value that lands in the `.env` file must come from an API round-trip the skill just performed.

## 0. Gather intent

Ask the user (in this order, skipping any they pre-answered in the invocation args):

1. **Purpose of the bot** in one sentence (e.g. "alerts from the nightly build", "chatops for a deploy pipeline", "steer a long-running agent"). Used to suggest a display name.
2. **Display name** of the bot (shows in the chat header). 3-64 chars, any text.
3. **Username** of the bot (must end in `bot`, must be globally unique across Telegram, 5-32 chars, letters + digits + underscores). Suggest `<project>_<purpose>_bot` if they don't have one.
4. **Target**: one-to-one DM with the user, or a group chat? (Determines the chat-id discovery flow in step 3.)
5. **Host for the long-poll worker**, if they want one. Options:
   - `systemd` (most Linux distros)
   - `rc.d` (FreeBSD and similar)
   - `tmux` (a detached shell session, laptop-friendly)
   - `none` (outbound only — they'll call `sendMessage` directly; no inbound commands)
6. **Env-file path**. Default: `~/.config/telegram-<project>.env`. Must be readable only by the user running the worker.

Record the answers as a short config summary before proceeding.

## 1. Create the bot (manual — guide the user)

Claude cannot reach BotFather; the user must. Output the following to the user, verbatim, and then **wait** for them to say "done" or paste the token:

```
Open Telegram on any device you're logged in on, then:

  1. Search for the account `@BotFather` and start a chat.
  2. Send:    /newbot
  3. When prompted, send your display name:     <display-name>
  4. When prompted, send your username:         <username>
     (must end in 'bot'; BotFather will tell you if it's taken)
  5. BotFather replies with a message that includes a line like:
     `HTTP API: 1234567890:ABCdefGhIjKlMnOpQrStUvWxYz0123456789`
     That string after 'HTTP API:' is the bot token.

Paste the token back here (or say 'cancel' to abort).
```

When the user pastes a token, do NOT echo it back. Verify it by calling `getMe`:

```bash
curl -sS --max-time 10 "https://api.telegram.org/bot<TOKEN>/getMe"
```

The response should be JSON with `"ok": true` and a `result` block containing `username` and `first_name`. If `ok: false` or the request errors, the token is wrong — ask the user to recheck (usually they copied an extra character) and retry.

If `ok: true`, print only `Bot verified: @<username> (id <id>).` No token echo.

## 2. Initiate the chat (manual — guide the user)

For chat-id discovery via `getUpdates` to work, the bot must have at least one message in its history — which means the user has to send it one.

**If 1:1 DM:**

```
Open the chat with your new bot (in Telegram, tap the username BotFather showed
you, or search for it).  Send any message — "/start" is conventional.  Say 'done'
when sent.
```

**If group chat:**

```
  1. Open the target group in Telegram.
  2. Group info -> Add members -> search for @<bot-username> -> Add.
  3. Send any message in the group (tag the bot with '@<bot-username> hi' so
     Telegram forwards it even if privacy mode is on).
  4. Say 'done' when sent.
```

Wait for "done" before continuing.

## 3. Discover the chat-id (automated)

Call `getUpdates` and extract the chat id from the most-recent message:

```bash
curl -sS --max-time 10 "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

From the response, walk `result[*].message.chat` (and `result[*].channel_post.chat`, `result[*].my_chat_member.chat`) and collect distinct `id` values with their `type` (`private` / `group` / `supergroup` / `channel`) and `title` or `username`.

- **Zero matches**: the user's message hasn't arrived yet (or the bot's privacy mode is on and it's a group; have them either promote the bot to admin OR disable privacy via BotFather's `/setprivacy`). Wait 5 seconds and retry once. If still empty, surface the exact BotFather sub-step.
- **One match**: use it.
- **Multiple matches**: show the list (type + title/username, id redacted as `…<last-4>`) and ask the user which one is the target. Never pick silently.

**Privacy-mode caveat for groups:** by default, bots only see messages that either mention them (`@bot_username`) or are replies to their own messages. If the user wants the bot to see every message in a group, instruct them to message BotFather:

```
/setprivacy  ->  pick your bot  ->  Disable
```

## 4. Write the credentials file (automated)

Create the env file at the agreed path with mode 600. Content:

```bash
# Telegram bot credentials for <project> / <purpose>.
# Generated by sst-setup-telegram on <utc-iso>.
# Bot: @<bot-username>  (id <bot-id>)
# Chat: <type> "<title-or-username>"  (id <chat-id>)
# DO NOT commit this file. Regenerate via BotFather's /revoke if it leaks.
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<chat-id>
```

Then:

```bash
chmod 600 <env-path>
```

Verify: `stat -c '%a %U' <env-path>` (Linux) or `stat -f '%Lp %Su' <env-path>` (BSD/mac) should print `600 <username>`. If the parent dir doesn't exist, create it first with `mkdir -p -m 700`.

**Create the base-dir fallback symlink (idempotent).** The skill-set framework
resolves Telegram credentials in this order: (1) caller-exported
`TELEGRAM_BOT_TOKEN`; (2) `TELEGRAM_ENV_FILE` env var; (3) base-dir fallback
`~/Dev/skill-set/telegram.env`. To make every project's `bin/notify-telegram.sh`
call work without per-caller configuration, create this fallback symlink after
writing the credentials file:

```bash
SYMLINK=~/Dev/skill-set/telegram.env
if [ ! -e "$SYMLINK" ]; then
    ln -s <env-path> "$SYMLINK"
    echo "Created base-dir fallback symlink: $SYMLINK -> <env-path>"
else
    echo "Base-dir fallback symlink already exists at $SYMLINK (skipping)"
fi
```

This step is idempotent: skip if the symlink (or a file) already exists at
`~/Dev/skill-set/telegram.env`. If `~/Dev/skill-set/` does not exist (e.g. a
non-skill-set project), print a note and skip gracefully — the fallback is only
relevant when the skill-set framework is present.

**Never print the token or chat-id after this point.** Reference them by pointing at the env-file path.

## 5. Outbound round-trip test (automated)

With the env file just written, source it in a subshell and send a test message:

```bash
(
  set -a; . <env-path>; set +a
  curl -sS --max-time 10 \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,os; print(json.dumps({"chat_id": int(os.environ["TELEGRAM_CHAT_ID"]), "text": "sst-setup-telegram: outbound OK", "disable_web_page_preview": True}))')" \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("sent" if d.get("ok") else ("fail: " + json.dumps(d)))'
)
```

On `sent`: ask the user to confirm they see the "sst-setup-telegram: outbound OK" message in their target chat. On `fail`: the response JSON names the reason (`chat not found` → wrong chat-id; `bot was blocked by the user` → user blocked the bot; `Forbidden: bot is not a member of the group` → re-add bot). Fix and retry. **Never commit the env file to diagnose this.**

If the repo ships `bin/notify-telegram.sh`, prefer that for the test instead of the inline curl — one round-trip, same result, matches what production code will use:

```bash
echo "sst-setup-telegram: outbound OK (via notify-telegram.sh)" | \
    TELEGRAM_ENV_FILE=<env-path> bash <repo>/bin/notify-telegram.sh
```

(Both paths are valid; pick the shorter one. If the repo-shipped script is present, use it so the user sees the exact command their future code will run.)

## 6. Inbound test (automated, optional)

If the user requested a long-poll worker (`--host` != `none`), prove inbound works before installing the service:

1. Prompt the user: `Send "/ping" to @<bot-username> from the target chat, then say 'done'.`
2. Wait for "done".
3. Call `getUpdates` and look for a `message` with `text == "/ping"` and `chat.id == <stored-chat-id>`.
4. If present: report `Inbound OK.` and move on.
5. If absent after 5s: say the message didn't arrive from the allowlisted chat. Common cause: privacy mode on a group — see §3 caveat.

Skip this section entirely if `--host none`.

## 7. Install the long-poll worker (automated where the host allows)

Only run this if the user chose a `--host` other than `none`. This section assumes they have a bot implementation already — typically a script that reads the env file and long-polls `getUpdates`. If the repo ships `bin/manager-bot.py`, use it; otherwise point the user at their own worker path.

**`--host systemd`:**

Write a unit file to `/etc/systemd/system/<name>.service` (or `~/.config/systemd/user/<name>.service` for a user-unit). Template (edit the 4 `<...>` placeholders):

```ini
[Unit]
Description=<purpose> Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<username>
WorkingDirectory=<worker-working-dir>
Environment="TELEGRAM_ENV_FILE=<env-path>"
ExecStart=/usr/bin/python3 <worker-script>
Restart=always
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=<state-dir>
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

Then:

```bash
# System-wide:
sudo systemctl daemon-reload
sudo systemctl enable --now <name>.service
sudo systemctl status <name>.service --no-pager

# User-scoped (no sudo):
systemctl --user daemon-reload
systemctl --user enable --now <name>.service
systemctl --user status <name>.service --no-pager
loginctl enable-linger <username>   # so the user unit keeps running after logout
```

Watch the logs for 10 seconds:

```bash
journalctl -u <name>.service -f --since '10 seconds ago'
```

Expect a startup line + no tracebacks. If the unit flaps (`Restart=always` hides a crash loop), fix before declaring victory.

**`--host rc.d`** (FreeBSD and similar):

Copy an rc.d script to `/usr/local/etc/rc.d/<name>`, `chmod 755` it, then add `<name>_enable="YES"` plus any overrides to `/etc/rc.conf`. Start with `sudo service <name> start`; confirm with `sudo service <name> status`. (If the repo ships `bin/manager-bot.rc.d`, copy that as the starting template and edit the 4 placeholder variables at the top.)

**`--host tmux`**:

No service unit; run the worker in a detached tmux session so the user can reattach and watch:

```bash
tmux new-session -d -s <name> "TELEGRAM_ENV_FILE=<env-path> python3 <worker-script>"
tmux list-sessions           # confirm the session is alive
tmux attach -t <name>        # optional: watch (Ctrl-b d to detach)
```

Warn the user: tmux sessions die on host reboot; if they want persistence, switch to systemd/rc.d.

## 8. Push command suggestions to the client (automated, optional)

Telegram shows autocompletion for bot commands if you register them via BotFather's `/setcommands`. Ask the user for the command list (or, if the worker exposes a `/help` that lists them, parse that). Then POST to the Bot API's `setMyCommands`:

```bash
(
  set -a; . <env-path>; set +a
  curl -sS --max-time 10 \
    -H 'Content-Type: application/json' \
    -d '{"commands":[
          {"command":"ping","description":"bot liveness check"},
          {"command":"help","description":"list available commands"}
        ]}' \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setMyCommands" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("set" if d.get("ok") else ("fail: " + json.dumps(d)))'
)
```

On `set`: the commands appear in the user's Telegram client within a few seconds (after the chat is re-opened). On `fail`: the API response names the reason.

## 9. Hand-off

Produce a short summary to the user:

```
Telegram setup complete.

  Bot:        @<username>   (id <bot-id>)
  Chat:       <type> "<title-or-username>"   (id stored in env file)
  Env file:   <env-path>   (mode 600)
  Worker:     <systemd unit | rc.d service | tmux session | "outbound only">
  Commands:   <registered | skipped>

Outbound send:      echo "hi" | TELEGRAM_ENV_FILE=<env-path> bash <notify-script>
Inbound queue:      <state-dir>/<worker>-queue/*.json   (only if the worker is installed)

To revoke: BotFather -> /revoke -> pick @<username> -> paste the new token into <env-path>.
To tear down a bot entirely: BotFather -> /deletebot.
```

Never include the token in the summary.

## Hard rules

- **Never write the token to stdout, stderr, logs, or any file other than the agreed env file.** After step 1 verifies it, reference it only as `<TOKEN>` or via `$TELEGRAM_BOT_TOKEN` sourced from the env file.
- **Never commit the env file.** If the working directory is a git repo, verify the env-path is outside it OR that the filename/parent is in `.gitignore`; offer to add it if not.
- **Never pick among multiple chat-ids silently.** Always show the options and ask.
- **Never skip §5 (outbound test).** "The env file exists" isn't the same as "the credentials work."
- **Pause at every manual step.** Do not proceed until the user confirms the step is complete; do not assume.

## Common failure modes

- **`Unauthorized`** on any call: token wrong or revoked. Re-check step 1.
- **`chat not found`** on sendMessage: wrong chat-id, OR the bot was removed from the group. Re-run step 3.
- **Empty `getUpdates`** after the user sent a message: either the user hasn't actually sent it yet, OR privacy mode is on in a group (see §3 caveat), OR a previous process is already polling with a newer offset (the Bot API only lets one getUpdates consumer exist at a time; stop the other worker first).
- **`Forbidden: bot was blocked by the user`**: the user blocked the bot. They unblock via the chat's info pane.
- **`429 Too Many Requests`**: rate-limited; back off per the `retry_after` field in the response.
