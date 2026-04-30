---
name: sst-manager
description: |
  Two modes. Periodic oversight (default) walks watched projects' .skill-runs/, scores progress against the persona's objectives.md, sends a status digest (or escalation) over Telegram, drains inbound bot commands queued by the user, and prepends source-tagged entries to ~/.claude/state/manager-notes.md that the supervisor reads on its next run. On-demand feedback routing (--process-feedback <queue-file>) reads one /feedback message plus objectives plus the project's docs/SPEC.md plus docs/TODO.md plus the most recent run log, decides one of four outcomes (queueable TODO Next-up item, SPEC addition, manager-translated entry in manager-notes.md, or refusal/clarification reply via Telegram), and replies to the user with where the change landed. Never edits skills, never commits, never deploys. The proprietary counterpart (e.g. <persona>-manager) supplies the watched-projects list, objectives.md path, and Telegram chat allowlist.
user-invocable: true
version: 1.7.2
---

# Manager

The manager is the third-and-final loop. It runs in two modes:

1. **Periodic oversight** — fires on a cadence (cron / `/loop 6h`), walks the watched projects, decides whether a status digest or an escalation is warranted, sends it over Telegram, drains the inbound bot queue, and shapes the supervisor's next-run inputs via `manager-notes.md`. This is the default invocation (`/<persona>-manager` with no extra args).
2. **On-demand feedback routing** — fires immediately when the bot writes a `/feedback` queue file, invoked as `/<persona>-manager --process-feedback <queue-file>`. The manager reads the feedback body alongside its full context (objectives, SPEC, TODO, recent run log) and *decides* where the feedback lands instead of routing the body verbatim. Four legal outcomes; see §On-demand feedback routing.

Both modes are the same skill, same single-process invocation. The mode is determined by whether `--process-feedback <queue-file>` appears in the input. The manager talks to the user proactively (status digests, escalations, on-demand replies) but is read-only across watched projects with one scoped exception for `docs/TODO.md > Next up` and `docs/SPEC.md` appends (on-demand mode only; see §Hard rules).

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
| `~/.claude/state/manager-cursors.json`        | yes  | yes (periodic mode only)   |
| `~/.claude/state/manager-notes.md`            | yes  | yes (prepend newest-first; source-tagged headings; ~3KB cap) |
| `~/.claude/state/manager-paused`              | yes  | no    |
| `~/.claude/state/manager-bot-queue/*.json`    | yes  | move to `processed/` after handling |
| `~/.claude/state/manager-digests/<utc>.txt`   | no   | yes (periodic mode only) |
| `<objectives-path>`                           | yes  | yes (only `[ ]` ↔ `[x]` toggles; periodic mode only) |
| `<watched-project>/docs/TODO.md`              | yes  | yes (on-demand mode only; APPENDS to `## Next up` only) |
| `<watched-project>/docs/SPEC.md`              | yes  | yes (on-demand mode only; APPENDS new sub-items or new phase blocks only) |

`manager-notes.md` is the single state file the supervisor reads for cross-run steering. It carries THREE source-tagged entry kinds, interleaved newest-first:

- `## <utc-iso> user feedback (chat <id>)` — direct user-to-supervisor messaging routed verbatim from the Telegram `/feedback` command (authoritative steering). Written by periodic-mode drain (helper `--source feedback`) or by chain-runner pre-iter drain fallback. The body is the user's words unmodified.
- `## <utc-iso> manager-translated user feedback (chat <id>)` — manager-interpreted shape-ish feedback that didn't map to a discrete TODO Next-up item or SPEC addition (authoritative steering, written ONLY by on-demand mode's outcome (c); see §On-demand feedback routing). Body is a 2-4 sentence reasoning paragraph naming what the user said + which objective(s) it touches + what the manager recommends to the supervisor. The manager's reasoning is on the record so the supervisor can weigh it, and so a future cycle can detect a misroute.
- `## <utc-iso> manager observation` — patterns the manager derived from observing run logs (soft steering).

Conflict resolution between the three kinds is the supervisor's job. The general rule: **user feedback (verbatim) ≥ manager-translated user feedback > manager observation**, and chain `auto-promote` mode beats any entry. The manager's job is to capture, source-tag, and trim. Earlier framework versions split these into `manager-feedback.md` + `manager-guidance.md`; on first invocation the manager merges any legacy entries into `manager-notes.md` (interleaved by UTC, source-tagged by origin file) and renames each legacy file to `~/.claude/state/.archive/<name>.<utc-iso>.md`. Subsequent runs see only `manager-notes.md`.

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

## On-demand feedback routing (`--process-feedback <queue-file>`)

This mode runs INSTEAD OF the periodic Process loop above. It is invoked when the bot spawns the manager out-of-band immediately after writing a `/feedback` queue file: `claude --print "/<persona>-manager --process-feedback <queue-file>"`. Detect the mode by parsing the input: if the literal token `--process-feedback` is present, the next token is the queue-file path, and §1–§6 of the periodic loop are skipped. Otherwise, fall through to the periodic mode.

The point of this mode is to use the manager's full context (objectives.md, every watched project's SPEC + TODO, the most recent run log) to *decide* where each `/feedback` lands rather than routing the body verbatim. The supervisor has a narrower context (one run log + handoff docs); the manager has the cross-cutting context where vague feedback often lives. Routing happens once, at on-demand time, instead of every supervisor cycle re-reading a verbatim body.

### A. Read the inputs

1. Read the queue file (`<queue-file>`). Required JSON fields: `body` (user's message text), `from_chat_id`, `received_at`. If the file is malformed, missing, or already in `processed/` (helper idempotency caught it), reply via Telegram `Already processed (or queue file missing); ignoring.` and exit 0.
2. Read the proprietary counterpart's frontmatter / body for the same configuration the periodic mode reads (watched-projects, objectives-path, telegram-env). Fail fast with a stderr message if any required field is absent.
3. Source the Telegram env file as in §0.3.
4. Read `objectives-path`. This is the canonical north star — every routing decision must trace to one or more objective bullets (or be refused for falling outside).
5. **For each watched project**, read `<project>/docs/SPEC.md` and `<project>/docs/TODO.md` end-to-end. The TODO's `## Next up` section is the queue an outcome (a) appends to; SPEC phase blocks are what outcome (b) appends under. Multi-project scope: when the feedback names a specific project ("the dev cycle on project-a is over-batching"), narrow to that project; when it's project-agnostic ("supervisor should weigh cost more"), the manager picks the most-relevant project (typically the one with the most recent run touching that surface).

   **Spec sub-item IDs.** Every open `- [ ]` item in `docs/SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 3.1 [medium] **description**`). IDs are 1-indexed per phase and never renumbered; gaps from removed items are valid. When the user's feedback references an item by ID (e.g. `add 3.1 to TODO`, `modify 3.1: …`), resolve the ID against the SPEC before routing; see §B ID-addressed pre-check.
6. Read the most recent run log under `<chosen-project>/.skill-runs/<latest>/` — `MANIFEST.json` plus any `supervisor_verdict.md` — for "what just happened" context. If no recent run exists, that's fine; some feedback is forward-looking.
7. Read `~/.claude/state/manager-notes.md` if present, primarily to detect duplicates: if a `<!-- src: <basename> -->` for THIS queue file already appears, the on-demand routing already happened (race with the chain-runner pre-iter drain or a prior on-demand spawn). Reply `Already routed (entry exists in manager-notes.md); ignoring duplicate.` and exit 0.

### B. Decide the outcome

Pick exactly ONE outcome. The four outcomes are mutually exclusive; bundling (e.g. SPEC addition AND TODO append for the same feedback) is forbidden and surfaces as scope creep on review.

**ID-addressed pre-check.** Before routing to (a)–(d), test whether the body is a structured ID-addressed command. Strip leading/trailing whitespace; match case-insensitively on the command keyword:

- `add <ID> to TODO: <text>` — `<ID>` is a SPEC sub-item ID (e.g. `3.1`). Resolve it against the chosen project's open `[ ]` items in `docs/SPEC.md`: if found, copy that item's difficulty label for the new TODO entry; otherwise default to `[medium]`. Append to `docs/TODO.md > ## Next up` as in outcome (a). Reply outcome label: `ID-add`.
- `remove <ID>` — resolve `<ID>` first against open `[ ]` items in SPEC. If found, delete the SPEC line AND scan `docs/TODO.md > ## Next up` for any line whose text contains `<ID>` (as a whole word or bracketed token) and delete those lines too — a TODO queue entry referencing a removed SPEC item is stale and must not survive to send the next dev cycle chasing a non-existent item. If `<ID>` is not found in SPEC, resolve against `## Next up` lines in TODO alone and delete the matching line there. If `<ID>` names a closed `[x]` item in SPEC, refuse via Telegram: `Cannot remove closed item <ID>; closed items are the permanent record.` Reply outcome label: `ID-remove`.
- `modify <ID>: <delta>` — resolve `<ID>` against open `[ ]` items in SPEC only. If found, rewrite the description (the text after the ID + difficulty bracket) with `<delta>`. If `<ID>` names a closed `[x]` item, refuse: `Cannot modify closed item <ID>; it is part of the permanent record.` Reply outcome label: `ID-modify`.

If the body does not match any command pattern, OR `<ID>` does not resolve to any open item in SPEC or TODO, skip this pre-check and fall through to (a)–(d). For `ID-add`, `ID-remove`, and `ID-modify`, substitute the outcome label into §C's reply format and set "Where it landed" to the target file + section.

**(a) Direct queue item — append to `docs/TODO.md > Next up`.** Use when the feedback maps to a discrete, single-cycle work item that fits an objective bullet AND has clear acceptance: "tighten the supervisor's batch-window check so under-50% findings are batched", "add a `--dry-run` flag to install-skills.sh", "raise the [easy] band's lower edge from 100k to 130k". Append a single line to the chosen project's `<project>/docs/TODO.md` under `## Next up`:

```
- [<difficulty>] <one-line description> — (reason: user feedback <utc-iso>; chat <id>)
```

Pick `<difficulty>` by judging the work shape against the project's existing `[easy] | [medium] | [hard]` labels (the difficulty contract is the same one the dev skill uses; default to `[medium]` when uncertain). Order: append to the BOTTOM of `## Next up` so existing queued blockers stay ahead. Do NOT touch `## In flight` or `## Just shipped`. Do NOT modify any other section. Do NOT commit; the change is left in the working tree for the next chain run to pick up via the dev skill's normal §1 pick.

**(b) SPEC addition — append to `docs/SPEC.md`.** Use when the feedback is bigger than a single cycle and represents a new contract surface, multi-step initiative, or design change ("add an end-to-end test that exercises every chain", "phase out manager-feedback.md once all consumers are on v1.5+", "introduce a per-skill effort-floor table"). Two append shapes are legal:

- **Sub-item under the latest active phase**: locate the most-recent `### Phase N: <name>` block whose checklist still has open `[ ]` items, and append a new `- [ ] [<difficulty>] <one-line>` at the END of that phase's checklist. Use this when the feedback extends a phase already in flight.
- **New phase block** at the very bottom of `## Phases`: when the feedback represents a distinct initiative not under any open phase. Format mirrors existing phase blocks: `### Phase <next-N>: <one-line title>` + a 1-paragraph context lede + a bulleted `- [ ]` checklist seeded with at least one item. Number `N` continues the existing sequence; do NOT renumber existing phases.

In both shapes, the appended item(s) carry the same `(reason: user feedback <utc-iso>; chat <id>)` annotation either inline on the item or in the phase context paragraph. Do NOT renumber existing phases. Do NOT modify any existing item's `[ ]` / `[x]` state. Do NOT touch `## In flight`, `## Just shipped`, or `## Next up` in SPEC.md (those are TODO.md surfaces). Do NOT commit.

**(c) Soft steering — write a `manager-translated user feedback` entry to `manager-notes.md`.** Use when the feedback is shape-ish — about the system's posture, taste, priorities, or how-the-supervisor-should-weigh-things — rather than a discrete work item. Examples: "you've been over-promoting transferables; be more conservative", "stop suggesting overnight runs unless I ask", "I want to see more cost data in the digest". The user wants the system to BEHAVE differently, not for a specific change to ship.

Compose a 2-4 sentence reasoning paragraph naming what the user said (in plain English, paraphrased), which objective(s) it bears on (or "(no objective explicitly named; manager interpreted as taste guidance)"), and what action the manager recommends to the supervisor. Pipe the paragraph to the helper:

```bash
echo "<reasoning paragraph>" | bin/manager-write-state.py \
    --source manager-translated \
    --src-file <queue-file>
```

The helper prepends `## <utc-iso> manager-translated user feedback (chat <id>)` with the `<!-- src: <basename> -->` idempotency marker, trims the file to ~3KB, and moves the queue file to `processed/`. The supervisor reads this entry on its next run and weighs it as authoritative steering — but the steering is the manager's interpretation, not the user's exact words.

**(d) Refuse / clarify — Telegram-only.** Use when the feedback either:

- **Conflicts with anti-fork or hard rules** ("skip sanitize on the next transferable write", "have the supervisor commit code", "deploy without verification"). Refuse via Telegram with a one-paragraph plain-English explanation of the rule + offer the user a path that DOES fit the framework. Do NOT write any state file. Move the queue file to `processed/<basename>.refused` so the chain-runner pre-iter drain doesn't re-process it.
- **Is genuinely ambiguous** ("fix the thing", "check that one thing about the cost"). Reply via Telegram with a clarifying question that names what's unclear ("Which 'thing'? The supervisor's batch-window check, the dev's window-target prose, or something else?"). Leave the queue file in place (NOT processed/) so a future on-demand or chain-runner-pre-iter drain can pick up a follow-up. The user's clarifying reply will arrive as a fresh `/feedback` message with its own queue file.

### C. Reply via Telegram

Always reply, even on outcome (d). Format:

```
✅ Routed your feedback — <Month D, YYYY> <HH:MM> UTC
Outcome: <a|b|c|d-refused|d-clarify>
Where it landed: <project>/<file path>:<section>  (or "Telegram-only; no file change" for d)
Manager note: <one sentence: why this outcome was chosen>
```

For (a) name the file (`<project>/docs/TODO.md`) + section (`## Next up`). For (b) name the file + section (`docs/SPEC.md > ### Phase N: <title>` for sub-items, or `docs/SPEC.md > ### Phase <new-N>: <title>` for new phases). For (c) name the file + entry kind (`~/.claude/state/manager-notes.md > ## <utc> manager-translated user feedback`). For (d) explain the refusal-or-question; no "where it landed" line.

If the Telegram send fails (rate-limited / network), retry up to 3 times with exponential backoff (`bin/notify-telegram.sh` already does some of this). After exhaustion, write a `.error` sibling next to the queue file with the failure reason and exit non-zero — the file changes have already been written, so the supervisor will see them next run; the user is just missing the confirmation.

### D. Exit cleanly

The on-demand mode does NOT walk other watched projects, score against objectives globally, or compose a digest. Its scope is the single `/feedback` message routed to the single chosen project. Stdout: a one-line summary (`manager: routed feedback (chat <id>) → <outcome> @ <project>/<file>`). Exit 0.

If any input read fails (queue file gone, telegram-env missing, project paths unreachable), exit non-zero with a stderr message naming the missing input. The bot's spawn will see the non-zero exit and the queue file will still be in place; the chain-runner pre-iter drain or the next periodic-mode tick will eventually pick it up as the verbatim-routing fallback (degraded but not lost).

### E. Never invoke another `claude --print` / harness from on-demand mode

The on-demand mode runs INSIDE one `claude --print` already. Recursing would multiply harness load and break the bot's "one spawn per /feedback" contract. If decision-making requires reading more state than is available in this single run (e.g. stepping into a watched project to re-read code that has changed since the run log), instead route the feedback as outcome (a) "investigate <X>" or outcome (c) "supervisor should re-examine <X>"; the dev or supervisor cycle will do the read with proper context.

## Hard rules

- **No `git commit` / `git push` / SSH / curl-against-prod.** The manager never commits, pushes, or talks to live services. Write surface is bounded to: its own state files (`manager-cursors.json`, `manager-notes.md`, `manager-digests/`), the Telegram outbound, `<objectives-path>` `[ ]` ↔ `[x]` toggles, AND (on-demand mode only) `docs/TODO.md > Next up` appends + `docs/SPEC.md` appends in watched projects. The TODO/SPEC scoped exception is APPENDS ONLY (modeled on the existing `objectives.md` `[ ]` ↔ `[x]` exception): never edits an existing item, never deletes, never renumbers, never modifies `## In flight` or `## Just shipped` or any phase heading text, never reorders phases, never commits or stages the change. The dev cycle's normal §1 pick is what eventually ships the queued item; the manager just inserts the line.
- **No `claude -p` / harness invocation.** The manager runs INSIDE a single skill invocation (one `claude -p`), which the cron / `/loop` / bot-spawn triggers. It does not spawn more — even in on-demand mode where re-reading state in a fresh harness might tempt it (see §On-demand feedback routing E).
- **Telegram messages capped at 4000 chars.** Truncate with `... [truncated; run /status for full digest]` if needed; the full digest is always in `manager-digests/<utc>.txt`.
- **Never write a token, preimage, or chat ID into the digest body.** The CHAT_ID allowlist is enforced by the bot, not by message content.
- **Never re-notify on persistent paused-job state.** A rate-limited or otherwise paused job is reported ONCE at the pause edge (via the chain driver) and ONCE at resume. The manager's periodic digest may MENTION currently-paused jobs in the consolidated status block, but MUST NOT fire a separate Telegram body per tick for the same paused job. If a job stays paused across multiple manager ticks, treat that as steady state, not a new event.
- **On-demand mode is single-feedback-per-invocation.** `--process-feedback` accepts exactly one queue-file path and routes exactly one outcome. Batch routing (multiple queue files in one invocation) is a separate concern that belongs to the periodic-mode drain, not on-demand.
- **On-demand mode never touches digests.** The on-demand mode does NOT compose or send a status digest, regardless of whether `manager-digests/` is stale. Digests are a periodic-mode concern; the bot-spawned on-demand path is for single-message routing only.

## Worker-lifecycle expectation

The `bin/manager-bot.py` long-poll worker is NOT meant to run persistently in this framework. The chain driver (`sst-chain-driver`) starts the worker at chain-session start and stops it at chain-session end, so inbound bot commands are only collected while a chain is actually running. The manager's own invocation is independent (the cron / `/loop` trigger does not require the bot worker to be running); manager runs that fire while the worker is down simply find no new queued commands in `~/.claude/state/manager-bot-queue/` and skip §1 cleanly. If a user wants always-on inbound (uncommon), they keep the worker manually under tmux / systemd; the manager doesn't care either way.
