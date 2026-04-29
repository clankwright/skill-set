---
name: sst-manager
description: Periodic high-level oversight loop. Walks the watched projects' .skill-runs/, reads MANIFEST.json + supervisor_verdict.md + handoff docs, scores progress against the persona's objectives.md, sends a status digest (or an escalation) over Telegram, processes any inbound bot commands queued by the user (including user feedback routed onward to the supervisor), and prepends source-tagged entries to ~/.claude/state/manager-notes.md that the supervisor reads on its next run. Never edits skills, never commits, never deploys. The proprietary counterpart (e.g. <persona>-manager) supplies the watched-projects list, objectives.md path, and Telegram chat allowlist.
user-invocable: true
version: 1.6.2
---

# Manager

The manager is the third-and-final loop. It runs on a cadence (cron / `/loop 6h`) and is the only loop that talks to the user proactively. It holds the long-lived org/persona objectives, watches the projects, and steers the supervisor by prepending source-tagged entries to a single notes file the supervisor reads on its next run.

The manager NEVER:
- edits a `SKILL.md` (that's `/sst-promote-skill-proposal`).
- runs the agent harness on its own (that's the user, or the chain runner triggered by user/cron).
- makes git commits or deploys (read-only across the projects it watches; write-only to its own state files and the Telegram outbound).

## Operating principles

- **Objectives are sacrosanct.** The proprietary counterpart holds an `objectives.md`. The manager only flips `- [ ]` → `- [x]` when a measurable milestone is hit; it never rewrites the prose. If objectives are wrong, that's a user-level edit.
- **Cursors prevent re-processing.** `~/.claude/state/manager-cursors.json` records the latest seen run dir per watched project. Only newer runs get analyzed.
- **One digest per invocation.** Either a status digest (default) or an escalation. Never both. Escalations skip batching and fire immediately.
- **Bounded shaping, not editing.** Updates to `~/.claude/state/manager-notes.md` are prepend-and-trim, capped at ~3KB. Each entry carries a source-tagged heading (`## <utc-iso> user feedback (chat <id>)` for verbatim user feedback routed from the bot, `## <utc-iso> manager observation` for manager-derived patterns). The supervisor reads the file as a preamble, never the manager's full history.
- **Pause respect.** If `~/.claude/state/manager-paused` exists, the cycle is a no-op (no walk, no digest, no notes update). Reply silently to keep the cron quiet.

## Inputs

The proprietary counterpart's SKILL.md must declare:

```yaml
watched-projects:
  - path: ~/Dev/project-a
    name: project-a
  - path: ~/Dev/project-b
    name: project-b
objectives-path: ~/.claude/skills/<persona>-manager/objectives.md
telegram-env: ~/.config/manager-telegram.env  # exports TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
```

(The proprietary's body lists these as a fenced ```yaml block; this skill greps for them.)

State files this skill reads / writes:

| Path                                          | Read | Write |
|-----------------------------------------------|------|-------|
| `~/.claude/state/manager-cursors.json`        | yes  | yes   |
| `~/.claude/state/manager-notes.md`            | yes  | yes (prepend newest-first; source-tagged headings; ~3KB cap) |
| `~/.claude/state/manager-paused`              | yes  | no    |
| `~/.claude/state/manager-bot-queue/*.json`    | yes  | delete after processing |
| `~/.claude/state/manager-digests/<utc>.txt`   | no   | yes   |
| `<objectives-path>`                           | yes  | yes (only `[ ]` ↔ `[x]` toggles) |

`manager-notes.md` is the single state file the supervisor reads for cross-run steering. It carries TWO source-tagged entry kinds, interleaved newest-first:

- `## <utc-iso> user feedback (chat <id>)` — direct user-to-supervisor messaging routed verbatim from the Telegram `/feedback` command (authoritative steering).
- `## <utc-iso> manager observation` — patterns the manager derived from observing run logs (soft steering).

Conflict resolution between the two kinds is the supervisor's job (user feedback wins). The manager's job is to capture, source-tag, and trim. Earlier framework versions split these into `manager-feedback.md` + `manager-guidance.md`; on first invocation the manager merges any legacy entries into `manager-notes.md` (interleaved by UTC, source-tagged by origin file) and renames each legacy file to `~/.claude/state/.archive/<name>.<utc-iso>.md`. Subsequent runs see only `manager-notes.md`.

## Process

### 0. Pre-flight

1. If `~/.claude/state/manager-paused` exists, exit silently (no log, no message). The user toggles this via the bot's `/pause` and `/resume`.
2. Read the proprietary counterpart's frontmatter / body for the configuration above. If anything required is missing, write to stderr and exit non-zero — the manager cannot run without knowing what to watch.
3. Source the Telegram env file: `set -a; . "$telegram_env"; set +a`. The `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` exports are now available for `bin/notify-telegram.sh`.
4. Read or create `~/.claude/state/manager-cursors.json` (default: `{}`).

### 1. Process inbound bot commands first

`~/.claude/state/manager-bot-queue/*.json` holds tasks the user fired from Telegram (the bot writes these but never executes anything). Two file shapes:

```json
{
  "command": "promote" | "status" | "objectives" | "proposals" | "pause" | "resume",
  "args": ["<project-name>", "<skill-name>"],
  "received_at": "<utc-iso>",
  "from_chat_id": <int>
}
```

```json
{
  "command": "feedback",
  "body": "<full message text, may contain whitespace and newlines>",
  "received_at": "<utc-iso>",
  "from_chat_id": <int>
}
```

Handle in received-at order:

- `pause` / `resume` → toggle `~/.claude/state/manager-paused` accordingly. Reply `paused` / `resumed` to the chat.
- `status` → reply with the most recent digest from `manager-digests/`.
- `objectives` → reply with the current `objectives.md` (truncate to 3500 chars to fit Telegram).
- `proposals` → list pending proposals across all watched projects' `.skill-runs/*/proposals/` and the master repo's `proposals/`. Format: one line per proposal with severity, source, target.
- `promote <project> <skill>` → write `~/.claude/state/manager-bot-queue/promote-task.txt` for the next user-driven `/sst-promote-skill-proposal` invocation (this skill does NOT execute Claude itself; it just queues). Reply `queued`.
- `feedback` → route the user's body verbatim to the supervisor via `~/.claude/state/manager-notes.md` under a `user feedback (chat <id>)` source-tagged heading. See "Routing feedback to the supervisor" below. Reply confirming the body was routed onward (e.g. `Routed feedback (N chars) to the supervisor; it will read it on the next chain run.`).

After processing, delete each task file. If a task fails, leave it and add a `.error` sibling with the failure reason.

**Routing feedback to the supervisor.** When a `feedback` queue file is processed:

Check whether `bin/manager-write-state.py` is present before invoking it (`test -f bin/manager-write-state.py`).

**If the helper is present:** Invoke `bin/manager-write-state.py --source feedback --src-file <queue-file>` via Bash. The helper handles all atomic-write, source-tagging, trim, and processed/-rename steps. If the invocation fails (non-zero exit), leave the queue file in place so the next manager run retries; do not write a `.error` sibling — feedback retries are cheap and avoid losing user input on a transient failure.

`bin/manager-write-state.py` initializes `manager-notes.md` with the correct H1 + lead paragraph if the file does not yet exist; prepends the entry just under the lead paragraph in the format `## <utc-iso> user feedback (chat <id>)` with a `<!-- src: <basename> -->` idempotency marker; trims total file length to ~3KB by deleting the oldest entries from the bottom; and renames the queue file to `manager-bot-queue/processed/<basename>`.

**If the helper is absent** (consuming project installed `sst-manager` without the companion binary — copy it with `cp bin/manager-write-state.py <project>/bin/` from the skill-set repo): fall back to these manual steps via Bash:
1. Read the queue file's `body` field.
2. Prepend `## <utc-iso> user feedback (chat <id>)\n<body>\n\n` to `~/.claude/state/manager-notes.md` (create the file with the standard H1 + lead paragraph if absent).
3. Trim `manager-notes.md` to ~3KB by removing the oldest `## ...` blocks from the bottom.
4. Move the queue file to `~/.claude/state/manager-bot-queue/processed/<basename>`.

This is the only path the user has to inject concrete steering into the supervisor's loop without editing skill prose by hand. The manager does NOT interpret or paraphrase the body — that's the supervisor's job. The manager's only role is to (a) capture the body when it arrives, (b) source-tag the entry, (c) trim the file when it gets too long, and (d) route. The supervisor weighs user-feedback entries as authoritative steering and manager-observation entries as soft steering; user feedback wins on conflict.

### 2. Walk watched projects

For each `watched-projects[].path`:

```bash
ls -dt "$path"/.skill-runs/*/  2>/dev/null
```

Filter to dirs whose timestamp is strictly newer than `manager-cursors.json[path]`. For each new run, in chronological order:

1. Read `MANIFEST.json` (chain name, harness, exit code, per-skill records, git SHA before/after).
2. Read `supervisor_verdict.md` if present.
3. Read the project's `docs/SPEC.md` (or the path the project's `CLAUDE.md` declares) and `docs/TODO.md` to see what state the project is in NOW.
4. Score the run against `objectives-path`:
   - **Advance**: this run's commit closes a spec item that maps to an objective bullet.
   - **Drift**: the run shipped to an area not on the objectives list (acceptable, common — most cycles do).
   - **Regression**: the run reverted earlier work, broke an objective-tagged path, or supervisor flagged escalate.

Update `manager-cursors.json[path]` to the latest processed run dir name.

### 3. Toggle objectives when warranted

Only flip `[ ]` → `[x]` for an objective bullet when:

- A run's `supervisor_verdict.md` is `clean`, AND
- The shipped commit's diff touches files the bullet names, AND
- The bullet's text is unambiguous about completion criteria (no "ongoing" / "until further notice" wording).

When in doubt, don't flip. The user always wins.

### 4. Compose the digest

State facts. The user is technical and wants commit subjects, spend figures, and concrete status — not narrative or mood. Every status digest MUST contain all five sections below; write "nothing" or "none" rather than omitting a section.

**Language rules (apply to every digest):**
- Translate tool names to role words: "the dev cycle" not `sst-dev-cycle`; "the reviewer" not `sst-dev-review`; "the supervisor" not `sst-supervisor`; "the manager" for this skill.
- Replace internal numbering (e.g. "Phase 19 #7") with what the work actually is ("the per-skill cost-routing rollout").
- Drop framework terms: "run dir", "MANIFEST", "exit_code", "sanitize gate", "auto-promote", "anti-fork", "supervisor verdict", "sidecar". Use plain equivalents: "a recent run", "a check failed", "a proposed improvement".
- Keep technical specifics: quote commit subjects verbatim (backticks); round spend to nearest cent; keep difficulty labels (`[easy]`/`[medium]`/`[hard]`) as-is.
- Timestamps become human-readable dates ("April 27, 2026"), not ISO strings.

**Default (status digest) — five required sections:**

```
Progress update — <Month D, YYYY>

What shipped:
  <project-name>: <N> commit(s), ≈$<X.XX> spend
    • `<commit subject verbatim>` — <one sentence: what problem this closed, in plain English>
    • `<commit subject verbatim>` — <one sentence>
  <project-name>: nothing since last check

What stalled or failed:
  <one specific line per issue, or "nothing">

Goals:
  ✓ <objective text> — <evidence, e.g. "all 12 spec items closed">
  → <objective text> — <concrete status: "N of M items closed", "no movement", "blocked on <X>">

Open queue: <N> item(s); top: [<difficulty>] <top Next-up item one-liner>
Pending review: <N> proposal(s), or "none"
```

Two representative examples:

*Active run with one issue:*
```
Progress update — April 28, 2026

What shipped:
  project-a: 2 commits, ≈$6.20 spend
    • `fix: batch-sizing check now reads correct token field` — fixed a bug where the reviewer was always measuring batch sizes as zero, making the oversizing detection permanently blind
    • `feat: add user feedback routing via Telegram bot` — new /feedback command lets you steer the auto-reviewer directly from your phone without editing files
  project-b: nothing since last check

What stalled or failed:
  project-a: iter 3 hit a rate limit mid-run; auto-resumed after ~2h pause

Goals:
  ✓ Reduce per-cycle cost by 25% — all 12 spec items closed; $4.50/iter vs $7.20 baseline
  → Add user feedback channel — 3 of 3 spec items closed; acceptance test pending

Open queue: 7 items; top: [medium] manager digest format rewrite
Pending review: 1 proposal (dev-review patch)
```

*Clean tick — nothing new:*
```
Progress update — April 27, 2026

What shipped:
  project-a: nothing since last check
  project-b: nothing since last check

What stalled or failed:
  nothing

Goals:
  → Reduce per-cycle cost by 25% — 9 of 12 items closed
  → Add user feedback channel — 2 of 3 items closed

Open queue: 5 items; top: [easy] acceptance check for empty-queue handling
Pending review: none
```

Save to `~/.claude/state/manager-digests/<utc>.txt`. Send via `bin/notify-telegram.sh` (prepend a leading newline so Telegram renders cleanly).

**Escalation (immediate, no batching):**

Trigger when ANY of:

- A run's review determined something needs the user's attention (outcome was `escalate`).
- More than 2 consecutive runs in one project failed to complete.
- A completed goal was un-marked (possibly a manual edit — worth surfacing).
- An automated quality check blocked a proposed improvement from shipping.

```
⚠ Something needs your attention — <project-name>, <Month D, YYYY>

<one paragraph in plain English: what happened, what it affects, and what
the user should consider doing. No internal paths or jargon. The user can
reply /status for more detail if needed.>
```

### 5. Update notes for the supervisor

`~/.claude/state/manager-notes.md` (the same file feedback routing writes to in §1; manager-observation entries interleave with user-feedback entries by UTC):

If a pattern is worth shaping the supervisor's behavior, check whether `bin/manager-write-state.py` is present (`test -f bin/manager-write-state.py`).

**If present:** write the observation body (2-4 sentences) to stdin and invoke `bin/manager-write-state.py --source observation` via Bash. The helper handles all atomic-write, source-tagging, and trim steps — it prepends a `## <utc-iso> manager observation` entry and trims the total file to ~3KB.

**If absent:** prepend `## <utc-iso> manager observation\n<body>\n\n` directly to `~/.claude/state/manager-notes.md` (create with standard H1 + lead paragraph if absent), then trim to ~3KB.

Examples of useful observations:
- "The last 3 cycles each spent >100k tokens on the deploy step. If you see another such run, file a should-fix to break the long step into pre-flight checks."
- "Stop flagging the EMAIL_VERIFICATION_REQUIRED bypass; it's intentional through 2026-05-03."

If no pattern was worth shaping, do NOT invoke the helper. Empty updates pollute the supervisor's preamble.

**Legacy migration (one-time, idempotent).** On first invocation, if `~/.claude/state/manager-feedback.md` and/or `~/.claude/state/manager-guidance.md` exist alongside (or in place of) `manager-notes.md`, merge their entries into `manager-notes.md`: read each legacy file's `## <heading>` blocks, re-tag the heading per origin (`manager-feedback.md` entries become `## <utc> user feedback (chat <id>)` if a chat-id is recoverable from the heading, else `## <utc> user feedback`; `manager-guidance.md` entries become `## <utc> manager observation`), interleave by UTC newest-first under the new H1 + lead paragraph, then move each legacy file to `~/.claude/state/.archive/<name>.<utc-iso>.md`. Subsequent invocations see only `manager-notes.md` and skip the migration check.

### 6. Report

Stdout: a one-line summary (`manager: 2 watched projects, 1 escalation, sent digest, supervisor notes updated`). Telegram already received the user-facing message; stdout is for the cron log.

## Hard rules

- **No `git commit` / `git push` / SSH / curl-against-prod.** The manager is read-only across watched projects, write-only to its own state files, and outbound-only to Telegram.
- **No `claude -p` / harness invocation.** The manager runs INSIDE a single skill invocation (one `claude -p`), which the cron / `/loop` triggers. It does not spawn more.
- **Telegram messages capped at 4000 chars.** Truncate with `... [truncated; run /status for full digest]` if needed; the full digest is always in `manager-digests/<utc>.txt`.
- **Never write a token, preimage, or chat ID into the digest body.** The CHAT_ID allowlist is enforced by the bot, not by message content.
- **Never re-notify on persistent paused-job state.** A rate-limited or otherwise paused job is reported ONCE at the pause edge (via the chain driver) and ONCE at resume. The manager's periodic digest may MENTION currently-paused jobs in the consolidated status block, but MUST NOT fire a separate Telegram body per tick for the same paused job. If a job stays paused across multiple manager ticks, treat that as steady state, not a new event.

## Worker-lifecycle expectation

The `bin/manager-bot.py` long-poll worker is NOT meant to run persistently in this framework. The chain driver (`sst-chain-driver`) starts the worker at chain-session start and stops it at chain-session end, so inbound bot commands are only collected while a chain is actually running. The manager's own invocation is independent (the cron / `/loop` trigger does not require the bot worker to be running); manager runs that fire while the worker is down simply find no new queued commands in `~/.claude/state/manager-bot-queue/` and skip §1 cleanly. If a user wants always-on inbound (uncommon), they keep the worker manually under tmux / systemd; the manager doesn't care either way.
