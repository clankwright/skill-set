---
name: sst-manager
description: Periodic high-level oversight loop. Walks the watched projects' .skill-runs/, reads MANIFEST.json + supervisor_verdict.md + handoff docs, scores progress against the persona's objectives.md, sends a status digest (or an escalation) over Telegram, processes any inbound bot commands queued by the user, and writes a short guiding-principles preamble to ~/.claude/state/manager-guidance.md that the supervisor reads on its next run. Never edits skills, never commits, never deploys. The proprietary counterpart (e.g. <persona>-manager) supplies the watched-projects list, objectives.md path, and Telegram chat allowlist.
user-invocable: true
version: 1.2.0
---

# Manager

The manager is the third-and-final loop. It runs on a cadence (cron / `/loop 6h`) and is the only loop that talks to the user proactively. It holds the long-lived org/persona objectives, watches the projects, and steers the supervisor by writing guiding principles the supervisor reads on its next run.

The manager NEVER:
- edits a `SKILL.md` (that's `/sst-promote-skill-proposal`).
- runs the agent harness on its own (that's the user, or the chain runner triggered by user/cron).
- makes git commits or deploys (read-only across the projects it watches; write-only to its own state files and the Telegram outbound).

## Operating principles

- **Objectives are sacrosanct.** The proprietary counterpart holds an `objectives.md`. The manager only flips `- [ ]` → `- [x]` when a measurable milestone is hit; it never rewrites the prose. If objectives are wrong, that's a user-level edit.
- **Cursors prevent re-processing.** `~/.claude/state/manager-cursors.json` records the latest seen run dir per watched project. Only newer runs get analyzed.
- **One digest per invocation.** Either a status digest (default) or an escalation. Never both. Escalations skip batching and fire immediately.
- **Bounded shaping, not editing.** Updates to `~/.claude/state/manager-guidance.md` are append-and-trim, capped at ~1KB. The supervisor reads the file as a preamble, never the manager's full history.
- **Pause respect.** If `~/.claude/state/manager-paused` exists, the cycle is a no-op (no walk, no digest, no guidance update). Reply silently to keep the cron quiet.

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
| `~/.claude/state/manager-guidance.md`         | yes  | yes   |
| `~/.claude/state/manager-paused`              | yes  | no    |
| `~/.claude/state/manager-bot-queue/*.json`    | yes  | delete after processing |
| `~/.claude/state/manager-digests/<utc>.txt`   | no   | yes   |
| `<objectives-path>`                           | yes  | yes (only `[ ]` ↔ `[x]` toggles) |

## Process

### 0. Pre-flight

1. If `~/.claude/state/manager-paused` exists, exit silently (no log, no message). The user toggles this via the bot's `/pause` and `/resume`.
2. Read the proprietary counterpart's frontmatter / body for the configuration above. If anything required is missing, write to stderr and exit non-zero — the manager cannot run without knowing what to watch.
3. Source the Telegram env file: `set -a; . "$telegram_env"; set +a`. The `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` exports are now available for `bin/notify-telegram.sh`.
4. Read or create `~/.claude/state/manager-cursors.json` (default: `{}`).

### 1. Process inbound bot commands first

`~/.claude/state/manager-bot-queue/*.json` holds tasks the user fired from Telegram (the bot writes these but never executes anything). Each file:

```json
{
  "command": "promote" | "status" | "objectives" | "proposals" | "pause" | "resume",
  "args": ["<project-name>", "<skill-name>"],
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

After processing, delete each task file. If a task fails, leave it and add a `.error` sibling with the failure reason.

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

Write for the user reading on a phone. Organize around what matters to them — what moved forward, what broke, what got fixed — not what the framework did internally.

**Language rules (apply to every digest):**
- Use role words instead of tool names: "the dev cycle" not `sst-dev-cycle`; "the reviewer" not `sst-supervisor`; "the manager" for this skill. Drop names that add no meaning to a non-technical reader.
- Replace internal numbering (e.g. "Phase 19 #7") with what the work actually is ("the per-skill cost-routing rollout").
- Drop framework terms: "run dir", "MANIFEST", "exit_code", "sanitize gate", "auto-promote", "anti-fork", "supervisor verdict", "sidecar". Use plain equivalents: "a recent run", "a check failed", "a proposed improvement".
- Status in plain English: "on track" / "stuck on X" / "needs your input on Y" / "all quiet, nothing happened".
- Timestamps in digest bodies become human-readable dates ("April 27, 2026"), not ISO strings.

**Default (status digest):**

```
Progress update — <Month D, YYYY>

What moved forward:
  <project-name>: <plain-English summary of what shipped, or "quiet since last check">

Goals:
  ✓ <completed objective>
  → <active objective> — <status: on track / no movement / needs your input>

Suggested improvements waiting for review: <N, or "none">
Issues: <one line, or "none">
Fixes: <one line, or "none">
```

Three representative examples (calibrate tone against these):

*Objective progress + issue + fix:*
```
Progress update — April 27, 2026

What moved forward:
  project-a: finished the per-skill cost-routing rollout — dev and review work now
    use a cheaper model when the task is routine (2 changes shipped)
  project-b: quiet since last check

Goals:
  ✓ Reduce per-cycle cost by 25% — done
  → Add user feedback channel — no movement this period

Suggested improvements waiting for review: 1
Issues: the reviewer flagged a missed step in an older commit; a follow-up is queued
Fixes: fixed a bug where the bot worker wasn't stopping at end of session
```

*Clean tick (nothing new):*
```
Progress update — April 27, 2026

project-a: nothing new since last check
project-b: nothing new since last check

Goals:
  → Reduce per-cycle cost by 25% — on track
  → Add user feedback channel — on track

Suggested improvements waiting for review: none
No issues or fixes to report.
```

*All work done (empty queue):*
```
Progress update — April 27, 2026

All queued work is complete — nothing in the pipeline.

Goals:
  ✓ All current goals achieved

Suggested improvements waiting for review: none
No issues or fixes to report. Reply /objectives to review or add goals.
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

### 5. Update guidance for the supervisor

`~/.claude/state/manager-guidance.md`:

- Read existing content. If empty, start with:
  ```markdown
  # Manager guidance to supervisor

  Newest first. The supervisor reads this as a preamble on every run.
  ```
- Prepend (NOT append) a new dated entry IF the manager noticed a pattern worth shaping the supervisor's behavior:
  ```markdown
  ## <utc-iso>
  <2-4 sentences. Examples:
    "The last 3 cycles each spent >100k tokens on the deploy step.
     If you see another such run, file a should-fix on sst-dev-cycle's
     deploy section to break the long step into pre-flight checks."
    "Stop flagging the EMAIL_VERIFICATION_REQUIRED bypass; it's
     intentional through 2026-05-03."
  >
  ```
- Trim total file length to ~1KB by deleting the oldest entries until under threshold. Keep the leading H1.

If no pattern was worth shaping, do NOT touch the file. Empty updates pollute the supervisor's preamble.

### 6. Report

Stdout: a one-line summary (`manager: 2 watched projects, 1 escalation, sent digest, supervisor guidance updated`). Telegram already received the user-facing message; stdout is for the cron log.

## Hard rules

- **No `git commit` / `git push` / SSH / curl-against-prod.** The manager is read-only across watched projects, write-only to its own state files, and outbound-only to Telegram.
- **No `claude -p` / harness invocation.** The manager runs INSIDE a single skill invocation (one `claude -p`), which the cron / `/loop` triggers. It does not spawn more.
- **Telegram messages capped at 4000 chars.** Truncate with `... [truncated; run /status for full digest]` if needed; the full digest is always in `manager-digests/<utc>.txt`.
- **Never write a token, preimage, or chat ID into the digest body.** The CHAT_ID allowlist is enforced by the bot, not by message content.
- **Never re-notify on persistent paused-job state.** A rate-limited or otherwise paused job is reported ONCE at the pause edge (via the chain driver) and ONCE at resume. The manager's periodic digest may MENTION currently-paused jobs in the consolidated status block, but MUST NOT fire a separate Telegram body per tick for the same paused job. If a job stays paused across multiple manager ticks, treat that as steady state, not a new event.

## Worker-lifecycle expectation

The `bin/manager-bot.py` long-poll worker is NOT meant to run persistently in this framework. The chain driver (`sst-chain-driver`) starts the worker at chain-session start and stops it at chain-session end, so inbound bot commands are only collected while a chain is actually running. The manager's own invocation is independent (the cron / `/loop` trigger does not require the bot worker to be running); manager runs that fire while the worker is down simply find no new queued commands in `~/.claude/state/manager-bot-queue/` and skip §1 cleanly. If a user wants always-on inbound (uncommon), they keep the worker manually under tmux / systemd; the manager doesn't care either way.
