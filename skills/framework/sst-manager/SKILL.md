---
name: sst-manager
description: |
  Three modes. Periodic oversight (default) walks watched projects' .skill-runs/, scores progress against the persona's objectives.md, reads docs/HUMAN.md for active blockers (fires immediate Telegram alerts for new Blocking entries and auto-verifies Verify: lines on closed items), sends a status digest (or escalation) over Telegram, drains inbound bot commands queued by the user, and prepends source-tagged entries to ~/.claude/state/manager-notes.md that the supervisor reads on its next run. On-demand feedback routing (--process-feedback <queue-file>) reads one /feedback message plus objectives plus the project's docs/SPEC.md plus docs/TODO.md plus docs/HUMAN.md plus the most recent run log, decides one of five outcomes (queueable TODO Next-up item, SPEC addition, manager-translated entry in manager-notes.md, HUMAN.md blocker entry, or refusal/clarification reply via Telegram), and replies to the user with where the change landed. Planner mode (--plan, or auto-triggered by periodic mode when Next up is empty AND every SPEC [ ] is [x] for ≥1 prior tick) scores gap on each measurable objective, picks the 1-3 highest-gap criteria, and drafts [unconfirmed:<id>] candidate items into Next up that the user clears manually before the dev cycle picks them. Never edits skills, never commits, never deploys. The proprietary counterpart (e.g. <persona>-manager) supplies the watched-projects list, objectives.md path, and Telegram chat allowlist.
user-invocable: true
version: 1.14.2
---

# Manager

The manager is the third-and-final loop. It runs in three modes:

1. **Periodic oversight** — fires on a cadence (cron / `/loop 6h`), walks the watched projects, decides whether a status digest or an escalation is warranted, sends it over Telegram, drains the inbound bot queue, and shapes the supervisor's next-run inputs via `manager-notes.md`. This is the default invocation (`/<persona>-manager` with no extra args).
2. **On-demand feedback routing** — fires immediately when the bot writes a `/feedback` queue file, invoked as `/<persona>-manager --process-feedback <queue-file>`. The manager reads the feedback body alongside its full context (objectives, SPEC, TODO, HUMAN.md, recent run log) and *decides* where the feedback lands instead of routing the body verbatim. Five legal outcomes; see §On-demand feedback routing.
3. **Planner** — invoked as `/<persona>-manager --plan`, OR auto-triggered in-process at the end of periodic mode §3 when the chosen project's `Next up` is empty AND every SPEC `[ ]` is `[x]` AND those conditions held for ≥1 prior tick (cursor-tracked). The manager scores gap on each measurable objective in `objectives-path`, picks the 1-3 highest-gap criteria, and drafts `[unconfirmed:<id>]` candidate items into `docs/TODO.md > Next up`. The user clears the `[unconfirmed:`-prefix manually before the dev cycle picks the item. See §Planner mode.

All three modes are the same skill, same single-process invocation. Mode is determined by parsing the input: `--process-feedback <queue-file>` → on-demand; else `--plan` → planner; else periodic. Periodic mode may transition into planner-mode in-process when its auto-trigger fires (the digest §4 then reports the planner output as part of the same tick). The manager talks to the user proactively (status digests, escalations, on-demand replies, planner announcements) but is read-only across watched projects with two scoped exceptions: `docs/TODO.md > Next up` and `docs/SPEC.md` appends in on-demand mode, and `docs/TODO.md > Next up` appends of `[unconfirmed:*]` lines in planner mode (see §Hard rules).

The manager NEVER:
- edits a `SKILL.md` (that's `/sst-promote-skill-proposal`).
- runs the agent harness on its own (that's the user, or the chain runner triggered by user/cron).
- makes git commits or deploys (read-only across the projects it watches; write-only to its own state files and the Telegram outbound).

## Operating principles

- **Objectives are sacrosanct.** The proprietary counterpart holds an `objectives.md`. The manager only flips `- [ ]` → `- [x]` when a measurable milestone is hit; it never rewrites the prose. If objectives are wrong, that's a user-level edit.
- **Cursors prevent re-processing.** `~/.claude/state/manager-cursors.json` records the latest seen run dir per watched project. Only newer runs get analyzed.
- **One digest per invocation.** Either a status digest (default) or an escalation. Never both. Escalations skip batching and fire immediately.
- **Bounded shaping, not editing.** Updates to `~/.claude/state/manager-notes.md` are prepend-and-trim, capped at ~3KB. Each entry carries a source-tagged heading (`## <utc-iso> user feedback (chat <id>)` for verbatim user feedback routed from the bot, `## <utc-iso> manager observation` for manager-derived patterns). The supervisor reads the file as a preamble, never the manager's full history.
- **Pause respect.** If `~/.claude/state/manager-paused` exists (global) OR `~/.claude/state/manager-paused-<persona>` exists (scoped to THIS persona, derived from the proprietary counterpart's name minus the `-manager` suffix), the cycle is a no-op (no walk, no digest, no notes update). Reply silently to keep the cron quiet. The global file is human-managed; the scoped file is toggled by `/pause <persona>` / `/resume <persona>` per §1 below.
- **Project-token routing.** A shared Telegram bot may serve multiple personas in the same chat. Every non-agnostic inbound command MUST carry the target persona as its first whitespace-delimited token (`args[0]` for command payloads; `body.split()[0]` for `/feedback`). The manager only acts on queue files whose token matches this persona, leaves files for other known personas alone, and refuses files with missing or unknown tokens. **Never default the token to this persona when it is missing** — silently assuming would let one persona's message corrupt another persona's state file. The discovery surface for known tokens is the bot's `/projects` command. See §1 Project-token routing for the full rule.

## Inputs

The proprietary counterpart's SKILL.md must declare:

```yaml
watched-projects:
  - path: ~/Dev/project-a
    name: project-a
  - path: ~/Dev/project-b
    name: project-b
objectives-path: ~/.claude/skills/<persona>-manager/objectives.md
telegram-env: ~/.config/manager-telegram.env  # optional; exports TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
```

`telegram-env` is optional when a base-dir fallback is available (see §0.4). `watched-projects` and `objectives-path` are required.

(The proprietary's body lists these as a fenced ```yaml block; this skill greps for them.)

**Deployment shape (legacy vs operator-level).** Two shapes are supported in parallel:

1. **Legacy per-project manager.** One `<persona>-manager/` folder per project; the folder name (minus `-manager`) is the persona token; `watched-projects:` has one entry whose `name:` is conventionally the project's directory basename. Persona tokens for inbound bot routing come from the folder name.
2. **Operator-level manager** (preferred for multi-project deployments). One `<operator>-manager/` folder (e.g. `ops-manager` or `<your-handle>-manager`) lists every project in `watched-projects:`. The yaml block carries an explicit `operator-level: true` line; with that flag, the bot's `_discover_manager_personas` emits one persona per `watched-projects[*].name`. The folder name (`<operator>`) is an operator label, not a routable token. Inbound `/feedback <project-a> <text>`, `/status <project-b>`, etc. resolve to the matching project.

Both shapes coexist during transition; the discovery code does not require a flag-day cutover. To migrate, see [`docs/migration-single-manager.md`](../../../docs/migration-single-manager.md) for the runbook (operator-level skill creation, per-project `docs/MANAGER.md` adoption, consolidated `objectives.md` with `## Project:` sections, cron consolidation, legacy archive).

State files this skill reads / writes:

| Path                                          | Read | Write |
|-----------------------------------------------|------|-------|
| `~/.claude/state/manager-cursors.json`        | yes  | yes (periodic mode only)   |
| `~/.claude/state/manager-notes.md`            | yes  | yes (prepend newest-first; source-tagged headings; ~3KB cap) |
| `~/.claude/state/manager-paused`              | yes  | no    |
| `~/.claude/state/manager-bot-queue/*.json`    | yes  | move to `processed/` after handling |
| `~/.claude/state/manager-digests/<persona>_<utc>.txt` | no   | yes (periodic mode only) |
| `<objectives-path>`                           | yes  | yes (only `[ ]` ↔ `[x]` toggles; periodic mode only) |
| `<watched-project>/docs/TODO.md`              | yes  | yes (on-demand mode only; APPENDS to `## Next up` only) |
| `<watched-project>/docs/SPEC.md`              | yes  | yes (on-demand mode only; APPENDS new sub-items or new phase blocks only) |
| `<watched-project>/docs/FUTURE-WORK.md`       | yes (read-only, if present) | no |
| `<watched-project>/docs/HUMAN.md`             | yes (read-only in periodic; read+append in on-demand, if present) | yes (on-demand mode only; APPENDS under `## Blocking` or `## High`) |
| `<watched-project>/docs/MANAGER.md`           | yes (read-only, if present) | no |

`manager-notes.md` is the single state file the supervisor reads for cross-run steering. It carries THREE source-tagged entry kinds, interleaved newest-first:

- `## <utc-iso> user feedback (chat <id>)` — direct user-to-supervisor messaging routed verbatim from the Telegram `/feedback` command (authoritative steering). Written by periodic-mode drain (helper `--source feedback`) or by chain-runner pre-iter drain fallback. The body is the user's words unmodified.
- `## <utc-iso> manager-translated user feedback (chat <id>)` — manager-interpreted shape-ish feedback that didn't map to a discrete TODO Next-up item or SPEC addition (authoritative steering, written ONLY by on-demand mode's outcome (c); see §On-demand feedback routing). Body is a 2-4 sentence reasoning paragraph naming what the user said + which objective(s) it touches + what the manager recommends to the supervisor. The manager's reasoning is on the record so the supervisor can weigh it, and so a future cycle can detect a misroute.
- `## <utc-iso> manager observation` — patterns the manager derived from observing run logs (soft steering).

Conflict resolution between the three kinds is the supervisor's job. The general rule: **user feedback (verbatim) ≥ manager-translated user feedback > manager observation**, and chain `auto-promote` mode beats any entry. The manager's job is to capture, source-tag, and trim. Earlier framework versions split these into `manager-feedback.md` + `manager-guidance.md`; on first invocation the manager merges any legacy entries into `manager-notes.md` (interleaved by UTC, source-tagged by origin file) and renames each legacy file to `~/.claude/state/.archive/<name>.<utc-iso>.md`. Subsequent runs see only `manager-notes.md`.

## Score-against-objectives

The proprietary counterpart's `objectives-path` file holds the bar this manager scores progress against. It is higher-level than the project's SPEC phases — these are reasons-to-exist, not in-flight todos. The schema is two-tier: scored bullets carry a 3-line continuation block; prose-only bullets remain legal as untracked goals.

**Multi-project mode (optional `## Project: <name>` headers).** When the `objectives-path` file contains `## Project: <name>` level-2 headers, each scored bullet under that header is scoped to the watched-project whose `name:` matches `<name>` in the operator-manager's `watched-projects:` list. The manager runs each scoped bullet's `check:` expression with that project's root as `cwd`. Objectives not nested under any `## Project:` header are cross-project and run from the first watched-project's root (or the single watched-project in single-project deployments). **Anti-objectives are always top-level (cross-project):** they must not be nested under a `## Project:` header. When no `## Project:` headers appear in the file, the entire file scopes to the single watched-project — backward-compatible with single-project `objectives.md` files that predate multi-project support.

**Schema for a scored objective:**

```
- [ ] <slug>: <one-line description>
      check: <shell-expr OR count(<glob>) <op> <value>>
      target: <value-or-bound, e.g. "== 0", "<= 0.50", ">= 30">
      since: <utc-iso when this criterion was added>
```

`<slug>` is kebab-case, unique within the file, and never renumbered (§Planner mode uses the slug to identify the criterion in `Next up` rationale lines + idempotency markers). The 3-line block is recognized by 6-space indentation under the bullet line; any other indentation is treated as ordinary continuation text.

**Two `check:` forms:**

1. **shell check** — anything not starting with `count(`. The manager runs the expression in `/bin/bash -c` from the watched project's root (`cwd = <watched-project>/path`). Either stdout (parsed as a number, leading/trailing whitespace stripped) OR exit code is compared to `target:`; if stdout is non-numeric the exit code is used. Examples:
   - `check: grep -c '^- \[ \]' docs/SPEC.md` + `target: == 0` — the SPEC has zero open items.
   - `check: ls -dt .skill-runs/*/iter_*/supervisor_verdict.md 2>/dev/null | head -1 | xargs -I{} grep -c '^Outcome.*escalate' {} 2>/dev/null` + `target: == 0` — the most recent supervisor verdict is not an escalate.
2. **metric check** — `count(<glob>) <op> <value>`. The manager expands `<glob>` from the watched project's root using Python's `pathlib.Path.glob` (or shell `compgen -G` equivalent), counts matches, and compares to `target:`. Example: `check: count(skills/**/SKILL.md) >= 30`. The metric form is preferred for file-shape assertions because it sidesteps shell-quoting subtleties.

**`target:` operators:** `==`, `!=`, `<`, `<=`, `>`, `>=`. The right-hand side is a literal numeric value (integer or float). For boolean-shaped checks where exit code 0 = pass, use `target: == 0`.

**`since:`** is the UTC ISO timestamp when this criterion was added. Used by `--plan` mode to compute a gap-age — an open criterion older than another outranks it when picking the highest-gap items to draft. Set `since:` once on creation and never rewrite it.

**Reading + scoring (called by both periodic mode §3 and on-demand §B):**

1. Parse `objectives-path` block-by-block: a bullet with no continuation block is prose-only (untracked); a bullet followed by 6-space-indented `check:` + `target:` + `since:` lines is scored.
2. For each scored criterion that is still `[ ]`, run the check. Treat any non-zero exit code from a shell check as "criterion not met" without failing the manager run; log the failure to stderr and continue. (A check expression that crashes shouldn't take the whole tick down.)
3. Compare the result to `target:` per the operator. If the comparison passes, the criterion is "met-this-tick"; the periodic mode §3 may flip `[ ]` → `[x]` (only when the conditions in §3 also hold: clean supervisor verdict, diff touches files the criterion names, unambiguous wording).
4. For criteria still unmet, gap-age = `(now - since)` in days; gap-magnitude is the numeric distance between the check result and the target boundary (zero if the target is satisfied; for `target: == 0` with a positive count, magnitude is the count itself; for `target: <= X` magnitude is `max(0, current - X)`; for `target: >= X` magnitude is `max(0, X - current)`). §Planner mode uses both axes for prioritization.

**Prose-only bullets** are visible in digests under "Goals" but appear without the `✓ / →` evidence cell — instead a `?` or "(unscored)" marker. They never auto-flip; only the user edits them by hand. Use this form when a criterion is genuinely qualitative.

**Anti-objectives section** (a level-2 heading typically named `## Anti-objectives` near the bottom) is read for steering only — the manager must NOT propose work that pushes toward an anti-objective in §Planner mode, and must NOT escalate progress against one in a digest. Anti-objective bullets are prose-only by construction (they have no `check:` block).

## Process

### 0. Pre-flight

1. **Mode dispatch.** Parse the input for mode tokens. If `--process-feedback <queue-file>` is present, jump to §On-demand feedback routing and skip §1–§6. Else if `--plan` is present (with no `--process-feedback`), jump to §Planner mode and skip §1–§6. Else continue with periodic mode below; periodic mode's §3 may auto-transition into planner-mode in-process when conditions hold.
2. If `~/.claude/state/manager-paused` exists (global pause) OR `~/.claude/state/manager-paused-<persona>` exists (where `<persona>` is the proprietary counterpart's name with the trailing `-manager` stripped), exit silently (no log, no message). The user toggles the scoped file via the bot's `/pause <persona>` and `/resume <persona>`; the global file is touched by hand for emergency multi-persona stops.
3. Read the proprietary counterpart's frontmatter / body for the configuration above. If `watched-projects` or `objectives-path` is missing, write to stderr and exit non-zero — the manager cannot run without knowing what to watch. `telegram-env` is optional; see step 4.
4. Source the Telegram env file using the resolution chain below. `bin/notify-telegram.sh` applies the same chain internally, so a successful source here is optional but makes credentials available for any inline checks. Resolution order (first match wins): (a) if `telegram_env` is set in the proprietary config and the file is readable, `set -a; . "$telegram_env"; set +a`; (b) else if the skill-set base-dir fallback `~/Dev/skill-set/telegram.env` is readable, source it; (c) else log a warning to stderr ("no Telegram credentials configured") and continue — Telegram sends will be skipped gracefully by `bin/notify-telegram.sh` (exit 0 with a stderr note), but all file writes (digest, HUMAN.md, manager-notes.md) still happen normally.
5. Read or create `~/.claude/state/manager-cursors.json` (default: `{}`).

### 1. Process inbound bot commands first

`~/.claude/state/manager-bot-queue/*.json` holds tasks the user fired from Telegram (the bot writes these but never executes anything). A single bot may serve multiple personas, so every queue file is routed by project token before its command is acted on (see "Project-token routing" below). Two file shapes:

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

**Project-token routing (applies to every queue file before any command handler runs).**

The proprietary counterpart's `<persona>` is its skill folder name with the trailing `-manager` stripped (e.g. `<project>-manager` → persona `<project>`). Resolve once at §0.3 and keep it for the rest of the run.

The set of `<known-personas>` is the live list of installed proprietary managers, discovered by scanning `~/.claude/skills/*-manager/SKILL.md` for files whose YAML frontmatter contains a `transferable:` key (transferable templates lack this key and are excluded; the bot's `_discover_manager_personas` helper applies the same rule). This is the same registry the bot exposes via `/projects`. Refresh on each tick.

For each queue file, parse its payload and decide one of four routes:

| Command class | Token source | Match rule | Action |
| :--- | :--- | :--- | :--- |
| Project-agnostic (`ping`, `help`, `projects`) | n/a | always | act (no token stripping) |
| Feedback (`feedback`) | `body.split()[0]` | token == `<persona>` | strip token, route remainder per §1 feedback handler |
| Feedback (`feedback`) | `body.split()[0]` | token in `<known-personas>` (and ≠ `<persona>`) | leave the queue file alone — another manager owns it |
| Feedback (`feedback`) | `body.split()[0]` | body is empty | refuse-missing (see below) |
| Feedback (`feedback`) | `body.split()[0]` | token is not a known persona | refuse-unknown (see below) |
| All other commands | `args[0]` | token == `<persona>` | strip `args[0]`, route remainder per the handler list below |
| All other commands | `args[0]` | token in `<known-personas>` (and ≠ `<persona>`) | leave the queue file alone — another manager owns it |
| All other commands | `args[0]` | `args` is empty | refuse-missing |
| All other commands | `args[0]` | token is not a known persona | refuse-unknown |

**Anti-fork constraint.** Never default the token to `<persona>` when it is missing. Two personas sharing one chat is the failure mode this rule prevents; silently routing an ambiguous message would corrupt the other persona's `manager-notes.md`.

**Refusal-reply format.** For `refuse-missing` and `refuse-unknown`, reply via Telegram with one line naming the discovery surface AND the live persona list, then move the queue file to `~/.claude/state/manager-bot-queue/processed/<basename>.no-project`:

```
[<persona>] Project token required as the first arg. Use /<command> <token> ... — known: <comma-separated known-personas>. Send /projects for the live registry.
```

Reuse the bot helper `route_queue_payload(payload, my_persona, known_personas)` (in `bin/manager-bot.py`) to compute the routing decision; it returns one of `("act", "")`, `("skip", "")`, `("refuse-missing", <detail>)`, `("refuse-unknown", <detail>)`. The `detail` already carries the refusal text in the canonical format; the manager just prepends the `[<persona>]` outbound label per its own outbound convention.

After routing, handle the per-command behaviors in received-at order:

- `pause <persona>` / `resume <persona>` → toggle `~/.claude/state/manager-paused-<persona>` accordingly (the scoped file; the global `manager-paused` is human-only). Reply `paused` / `resumed` to the chat. Bare `/pause` and `/resume` (no persona token) route to refuse-missing per the routing table above.
- `status <persona>` → reply with the most recent digest from `manager-digests/<persona>_*.txt`. Falls back to the newest file in `manager-digests/` when no persona-prefixed files exist (backward-compatible with pre-28.7 flat naming).
- `objectives` → reply with the current `objectives.md` (truncate to 3500 chars to fit Telegram).
- `proposals` → list pending proposals across all watched projects' `.skill-runs/*/proposals/` and the master repo's `proposals/`. Format: one line per proposal with severity, source, target.
- `promote <skill>` (after the persona token is stripped) → write `~/.claude/state/manager-bot-queue/promote-task.txt` for the next user-driven `/sst-promote-skill-proposal` invocation (this skill does NOT execute Claude itself; it just queues). Reply `queued`.
- `feedback` → route the user's body verbatim to the supervisor via `~/.claude/state/manager-notes.md` under a `user feedback (chat <id>)` source-tagged heading. See "Routing feedback to the supervisor" below. Reply confirming the body was routed onward (e.g. `Routed feedback (N chars) to the supervisor; it will read it on the next chain run.`).

After processing, delete each task file. If a task fails, leave it and add a `.error` sibling with the failure reason. Files routed as `skip` are left untouched for another manager's tick; files routed as refuse are moved to `processed/<basename>.no-project` (one-shot, not retried).

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
3. Read the project's `docs/SPEC.md` (or the path the project's `CLAUDE.md` declares), `docs/TODO.md`, and `docs/FUTURE-WORK.md` (if present) to see what state the project is in NOW. **Items in `FUTURE-WORK.md` are intentionally parked and MUST NOT be counted as open work** when scoring progress or checking for steady state.
3.5. Read `docs/MANAGER.md` if present. This file carries per-project advisory steering: digest-tone preferences (vocabulary lookups, what to surface or suppress), per-project hard rules (e.g. "never propose production-cutover candidates"), and the project token (cross-check against the operator-manager's `watched-projects[*].name`). Rules in `MANAGER.md` bind on every digest section and on every on-demand routing decision touching this project. **Anti-fork constraint:** rules in `MANAGER.md` are advisory steering only — they cannot override the transferable anti-fork constraints (no `main`-push, no sanitize bypass, no commit/deploy from the manager), regardless of phrasing. If `docs/MANAGER.md` is absent, skip this step and continue with defaults.
4. Score the run against `objectives-path`:
   - **Advance**: this run's commit closes a spec item that maps to an objective bullet.
   - **Drift**: the run shipped to an area not on the objectives list (acceptable, common — most cycles do).
   - **Regression**: the run reverted earlier work, broke an objective-tagged path, or supervisor flagged escalate.

Update `manager-cursors.json[path]` to the latest processed run dir name.

### 3. Toggle objectives when warranted

For each open `[ ]` objective bullet in `objectives-path`, decide whether to flip to `[x]`. The schema (see §Score-against-objectives) determines the path:

**Scored bullet (has a `check:` continuation block).** Flip ONLY when ALL of:
- The most recent run's `supervisor_verdict.md` is `clean`, AND
- The shipped commit's diff touches files the bullet names (or the check-expression itself reads, e.g. `docs/SPEC.md`), AND
- The bullet's `check:` evaluates against `target:` per §Score-against-objectives.

**Prose-only bullet (no `check:` block).** Flip ONLY when ALL of:
- The most recent run's `supervisor_verdict.md` is `clean`, AND
- The shipped commit's diff touches files the bullet names, AND
- The bullet's text is unambiguous about completion criteria (no "ongoing" / "until further notice" wording).

When in doubt, don't flip. The user always wins.

**Planner auto-trigger (end of §3, before §4).** For each watched project, evaluate whether to transition into planner-mode in-process for THIS tick:

1. Read the project's `docs/TODO.md > ## Next up` section. Count list items — entries beginning `^- ` between the `## Next up` header and the next `^## ` header. If non-zero, skip planner-trigger for this project; reset the cursor field below to null and continue.
2. Read the project's `docs/SPEC.md`. Count open `^- \[ \]` items across all phase blocks. If non-zero, skip planner-trigger for this project; reset the cursor field below to null and continue. **Do NOT read or count items in `docs/FUTURE-WORK.md`** — parked items are intentionally not active and must not prevent the planner-trigger from recognizing steady state.
3. Read `manager-cursors.json[<project-path>].planner.queue_empty_since_tick` (extending the cursors file with a `planner` sub-object per project). If absent or null, set it to the current `<utc-iso>` and skip planner-trigger this tick (planner needs ≥1 prior tick of empty-state to confirm steady state, not a transient empty between dev cycles). Persist the cursor change.
4. If the cursor is already set (a prior tick observed empty-state) AND the current tick still observes empty-state, the auto-trigger fires: scan `## Next up` for any line containing `[unconfirmed:` AND a `<!-- planner-id: ` marker; if any such line exists, skip planner-trigger silently (one outstanding batch at a time per §Planner mode re-entry rule). Otherwise transition into §Planner mode in-process for THIS project, then resume periodic mode at §4 with the planner output included in the digest.

The cursor field stays set across ticks until the queue or SPEC re-fills, at which point step 1 or 2 resets it to null. This guarantees one auto-trigger per empty-state stretch, not one per tick.

### 3b. HUMAN.md delta-detection and auto-verify

**Run this sub-step for each watched project before §4, after the §3 planner-trigger check.**

**Delta-detection (new Blocking entries → immediate Telegram alert):**

1. Read the project's `docs/HUMAN.md`. If absent, skip delta-detection for this project.
2. Collect the set of H-IDs in `## Blocking` that are open (`[ ]`). Call this `current_blocking`.
3. Read `manager-cursors.json[<project-path>].human_md_snapshot` (a JSON object mapping H-ID strings to their titles, or absent/null). Call this `prior_snapshot`.
4. For each H-ID in `current_blocking` that is NOT in `prior_snapshot`, fire an immediate Telegram alert (separate from the §4 digest) with `TELEGRAM_LABEL=<persona>` set:
   ```
   [<persona>] New HUMAN.md blocker: <H-ID> — <title>. Blocks: <Blocks-value>. See <project-path>/docs/HUMAN.md
   ```
5. Update `manager-cursors.json[<project-path>].human_md_snapshot` to the current `current_blocking` set (H-ID → title mapping). Persist.

**No re-alert on persistent state.** If an H-ID was in the prior snapshot, do NOT fire a separate alert body for it; the §4 digest already lists all open Blocking entries as a recap. Persistent paused-job state is steady state, not a new event.

**Auto-verify (move closed `[x]` items with a passing `Verify:` check to `## Done`):**

1. For each item across `## Blocking` / `## High` / `## Medium` / `## Low` in `docs/HUMAN.md` that is closed (`[x]`) AND carries a `Verify:` line:
   a. Run the `Verify:` shell command from the watched-project's root (`/bin/bash -c "<cmd>"`) with a 60-second timeout.
   b. **Pass (exit 0):** Move the entire entry block to the top of `## Done` and append `(verified <utc-iso>)` to the title line. Update `manager-cursors.json[<project-path>].human_md_snapshot` to remove the H-ID.
   c. **Fail (non-zero or timeout):** Flip the entry back to `[ ]`. Prepend `  Verify-fail at <utc-iso>: <stderr-tail (max 80 chars)>` as the first continuation line. Move the entry to the top of its section (so it's visible). Do NOT fire an immediate alert; the next §4 digest will include it in the Blocking list.
2. If any entries were moved to `## Done`, write the modified `docs/HUMAN.md` back (the whole file, preserving all other content). After writing back, invoke the notification helper: `bash bin/notify-human-md.sh <project-path> <project-path>/docs/HUMAN.md`. Missing Telegram env → graceful skip (exit 0); never block the manager for a notification failure.

Anti-fork: auto-verify is the ONLY path that moves entries to `## Done`. The human's `[ ]` → `[x]` flip is a prerequisite; the manager only runs the `Verify:` check after the human has closed the item. Never auto-move an entry that the human has not yet closed.

**Discarded-sidecar auto-close (exception to the human-flip prerequisite).** For open `[ ]` entries in `## High`, `## Medium`, or `## Low` (NOT `## Blocking`) whose `Verify:` line is a sidecar-absence check (i.e., `test ! -e <path>` or equivalent), if the verify passes (the sidecar file is gone), the manager MAY auto-flip the entry to `[x]` and then run the standard auto-verify path to move it to `## Done`. This covers the case where a sidecar was deleted or discarded without promotion: the sidecar is gone (the blocker resolved itself), so the HUMAN entry is stale. Rationale: a sidecar-absence check is unambiguous evidence of resolution; no other interpretation is possible. `## Blocking` entries are excluded from this auto-close because cycle-stopping items should always involve a human acknowledgment, not a silent auto-close. After auto-closing, invoke `bash bin/notify-human-md.sh <project-path> <project-path>/docs/HUMAN.md` to notify.

### 4. Compose the digest

State facts. The user is technical and wants commit subjects, spend figures, and concrete status — not narrative or mood. Every status digest MUST contain all five sections below; write "nothing" or "none" rather than omitting a section.

**Language rules (apply to every digest):**
- Translate tool names to role words: "the dev cycle" not `sst-dev-cycle`; "the reviewer" not `sst-dev-review`; "the supervisor" not `sst-supervisor`; "the manager" for this skill.
- Replace internal numbering (e.g. "Phase 19 #7") with what the work actually is ("the per-skill cost-routing rollout").
- Drop framework terms: "run dir", "MANIFEST", "exit_code", "sanitize gate", "auto-promote", "anti-fork", "supervisor verdict", "sidecar". Use plain equivalents: "a recent run", "a check failed", "a proposed improvement".
- Keep technical specifics: quote commit subjects verbatim (backticks); round spend to nearest cent; keep difficulty labels (`[easy]`/`[medium]`/`[hard]`) as-is.
- Timestamps become human-readable dates ("April 27, 2026"), not ISO strings.

**Default (status digest) — six required sections (Human-action blockers first):**

```
Progress update — <Month D, YYYY>

Human-action blockers:
  [<persona>] H<phase>.<n> — <title> (blocks <SPEC-IDs>)
  (or "none")

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

The "Human-action blockers" section lists every open `## Blocking` entry across all watched projects' `docs/HUMAN.md`. One line per entry; `<persona>` is the project's persona token; `<SPEC-IDs>` is the `Blocks:` value verbatim. Place this section **above** "What shipped" so it is visible regardless of digest length or truncation in Telegram. If `docs/HUMAN.md` is absent or has no open `## Blocking` entries, write "none".

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

Save to `~/.claude/state/manager-digests/<persona>_<utc>.txt` where `<persona>` is the proprietary manager's persona name (e.g. `my-project`, `other-project`). This prefix lets the bot's `/status <token>` filter to the correct persona's digest in multi-persona deployments. Send via `bin/notify-telegram.sh` (prepend a leading newline so Telegram renders cleanly).

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
2. Read the proprietary counterpart's frontmatter / body for the same configuration the periodic mode reads (watched-projects, objectives-path, telegram-env). Fail fast with a stderr message if `watched-projects` or `objectives-path` is absent; `telegram-env` is optional (see §0.4 fallback chain).
3. Source the Telegram env file as in §0.4.
4. Read `objectives-path`. This is the canonical north star — every routing decision must trace to one or more objective bullets (or be refused for falling outside).
5. **For each watched project**, read `<project>/docs/SPEC.md`, `<project>/docs/TODO.md`, `<project>/docs/FUTURE-WORK.md`, and `<project>/docs/HUMAN.md` (all if present) end-to-end. The TODO's `## Next up` section is the queue an outcome (a) appends to; SPEC phase blocks are what outcome (b) appends under. FUTURE-WORK.md is read for context only; on-demand routing never writes to it. HUMAN.md is where outcome (e) appends. Multi-project scope: when the feedback names a specific project ("the dev cycle on project-a is over-batching"), narrow to that project; when it's project-agnostic ("supervisor should weigh cost more"), the manager picks the most-relevant project (typically the one with the most recent run touching that surface).

   **Spec sub-item IDs.** Every open `- [ ]` item in `docs/SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 3.1 [medium] **description**`). IDs are 1-indexed per phase and never renumbered; gaps from removed items are valid. When the user's feedback references an item by ID (e.g. `add 3.1 to TODO`, `modify 3.1: …`), resolve the ID against the SPEC before routing; see §B ID-addressed pre-check.
6. Read the most recent run log under `<chosen-project>/.skill-runs/<latest>/` — `MANIFEST.json` plus any `supervisor_verdict.md` — for "what just happened" context. If no recent run exists, that's fine; some feedback is forward-looking.
7. Read `~/.claude/state/manager-notes.md` if present, primarily to detect duplicates: if a `<!-- src: <basename> -->` for THIS queue file already appears, the on-demand routing already happened (race with the chain-runner pre-iter drain or a prior on-demand spawn). Reply `Already routed (entry exists in manager-notes.md); ignoring duplicate.` and exit 0.

### B. Decide the outcome

Pick exactly ONE outcome. The five outcomes are mutually exclusive; bundling (e.g. SPEC addition AND TODO append for the same feedback) is forbidden and surfaces as scope creep on review.

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

**(e) HUMAN.md blocker entry — append to `docs/HUMAN.md`.** Use when the feedback body maps to a human-only action the cycle cannot perform: "I can't provision the required secrets yet", "waiting on legal approval", "need to grant access in the cloud console". Examples: the user is telling the manager they cannot do something a pending SPEC item requires, or they want to record that a specific action is blocked on an external dependency. Append to the chosen project's `docs/HUMAN.md` under `## Blocking` (if the action actively stops a SPEC item) or `## High` (non-blocking prerequisite):

```
- [ ] H<phase>.<n> [<difficulty>] **<short title>**
  <one-paragraph body: what the human must do, where, why the cycle can't do it.>
  Blocks: <comma-separated SPEC IDs, or "none">.
  Filed by: sst-manager at <utc-iso> (on-demand, chat <id>).
  Source: /feedback chat <id>.
```

Assign the next unused H-ID where `<phase>` is the SPEC phase being gated (or `0` if orthogonal to any open phase). Anti-fork: NEVER flip `[ ]` → `[x]` here; closure is human-initiated. After appending, invoke the notification helper: `bash bin/notify-human-md.sh <project-path> <project-path>/docs/HUMAN.md`. Missing Telegram env → graceful skip (exit 0).

### C. Reply via Telegram

Always reply, even on outcome (d). Format:

```
✅ Routed your feedback — <Month D, YYYY> <HH:MM> UTC
Outcome: <a|b|c|d-refused|d-clarify|e>
Where it landed: <project>/<file path>:<section>  (or "Telegram-only; no file change" for d)
Manager note: <one sentence: why this outcome was chosen>
```

For (a) name the file (`<project>/docs/TODO.md`) + section (`## Next up`). For (b) name the file + section (`docs/SPEC.md > ### Phase N: <title>` for sub-items, or `docs/SPEC.md > ### Phase <new-N>: <title>` for new phases). For (c) name the file + entry kind (`~/.claude/state/manager-notes.md > ## <utc> manager-translated user feedback`). For (d) explain the refusal-or-question; no "where it landed" line. For (e) name the file + section (`<project>/docs/HUMAN.md > ## Blocking` or `## High`).

If the Telegram send fails (rate-limited / network), retry up to 3 times with exponential backoff (`bin/notify-telegram.sh` already does some of this). After exhaustion, write a `.error` sibling next to the queue file with the failure reason and exit non-zero — the file changes have already been written, so the supervisor will see them next run; the user is just missing the confirmation.

### D. Exit cleanly

The on-demand mode does NOT walk other watched projects, score against objectives globally, or compose a digest. Its scope is the single `/feedback` message routed to the single chosen project. Stdout: a one-line summary (`manager: routed feedback (chat <id>) → <outcome> @ <project>/<file>`). Exit 0.

If any input read fails (queue file gone, project paths unreachable), exit non-zero with a stderr message naming the missing input. Missing Telegram credentials (no `telegram-env` and no base-dir fallback) is NOT a fatal error — Telegram sends are gracefully skipped, file changes still land. The bot's spawn will see the non-zero exit on other failures and the queue file will still be in place; the chain-runner pre-iter drain or the next periodic-mode tick will eventually pick it up as the verbatim-routing fallback (degraded but not lost).

### E. Never invoke another `claude --print` / harness from on-demand mode

The on-demand mode runs INSIDE one `claude --print` already. Recursing would multiply harness load and break the bot's "one spawn per /feedback" contract. If decision-making requires reading more state than is available in this single run (e.g. stepping into a watched project to re-read code that has changed since the run log), instead route the feedback as outcome (a) "investigate <X>" or outcome (c) "supervisor should re-examine <X>"; the dev or supervisor cycle will do the read with proper context.

## Planner mode (`--plan`)

This mode runs INSTEAD OF the periodic Process loop §1–§6 when invoked explicitly as `/<persona>-manager --plan`. It also runs IN-PROCESS as part of a periodic-mode tick when the §3 auto-trigger fires; in that case, periodic mode resumes at §4 (digest) once the planner output is recorded so the user gets one consolidated message rather than two.

The point of this mode is to keep the dev loop making progress when the user has not authored a queued item recently. Without it, a chain run started against an empty `Next up` + fully-checked SPEC produces a `[no-work]` bail and burns no further compute, but also makes no progress toward the user's stated objectives. Planner mode reads `objectives-path`, scores gap on each measurable criterion, and drafts 1-3 candidate `Next up` items targeting the highest-gap criteria. The candidates carry an `[unconfirmed:<id>]` prefix the user clears manually before the dev cycle picks the item, so the planner cannot silently broaden the agenda.

### α. Read the inputs

1. Read the proprietary counterpart's frontmatter / body for the same configuration the periodic mode reads (watched-projects, objectives-path, telegram-env). Fail fast with a stderr message if `watched-projects` or `objectives-path` is absent; `telegram-env` is optional (see §0.4 fallback chain).
2. Source the Telegram env file as in §0.4.
3. Read or create `~/.claude/state/manager-cursors.json` (extending it with a `planner` sub-object per project; see §3 auto-trigger).
4. **For each watched project**, read `<project>/docs/TODO.md` and `<project>/docs/SPEC.md`. The TODO's `## Next up` section is what planner mode appends to; SPEC is read only to confirm fully-checked state and to gather context for tier judgment. When the watched-projects list contains more than one project, planner mode picks the project with the most-recent `.skill-runs/<utc>_<chain>/` activity AND a fully-checked SPEC AND an empty `## Next up` — that is the project most likely to benefit from a fresh batch. If multiple projects qualify, pick the one with the oldest `since:` on its top-gap objective; if none qualify, exit cleanly with stdout `planner: no project in steady state; nothing to draft`.
5. Read `objectives-path`. This is the canonical north star — every candidate draft must trace to one or more open `[ ]` measurable bullet (see §Score-against-objectives for the schema).
6. Read the chosen project's `<project>/.skill-runs/<latest>/MANIFEST.json` plus any `supervisor_verdict.md` for "what just happened" context. The planner uses this to bias rationale wording (e.g. note when a recent supervisor verdict already escalated something the planner is about to draft).

### β. Re-entry guard

Scan the chosen project's `docs/TODO.md > ## Next up` for any line containing `[unconfirmed:` AND a `<!-- planner-id: ` marker. If at least one such line exists, exit cleanly without drafting: stdout `planner: <K> outstanding [unconfirmed:*] item(s); no new batch this tick`, send a single Telegram body `Planner skipped — <K> [unconfirmed:*] item(s) still in queue; clear or convert them before the next batch.`, and return. **One outstanding batch at a time** is a hard invariant — proposing fresh candidates while prior ones await user confirmation is the failure mode the `[unconfirmed:*]` prefix exists to prevent.

The `<!-- planner-id: <id> -->` marker is the discoverable token (the visible `[unconfirmed:<id>]` prefix may be edited by the user during conversion to a non-planner item; the comment marker survives prose edits as long as the line itself survives, and disappears with the line on `remove`).

### γ. Score gaps + pick the top 1-3

Run §Score-against-objectives §1–§4 against `objectives-path`. When the objectives file uses `## Project: <name>` headers (multi-project mode), score only the bullets scoped to the chosen project (i.e. under the matching `## Project:` header, plus any cross-project bullets not nested under any header). Each project-scoped bullet's `check:` runs with the chosen project's root as `cwd`. The planner proposes candidates only against the chosen watched-project's `## Next up`. For each open `[ ]` scored bullet that is currently unmet, record:

- `slug` — the bullet's kebab-case slug.
- `description` — the bullet's one-line description (after the slug + colon).
- `check_result` — the numeric value (or exit code) the check produced.
- `target_op` + `target_value` — the operator + RHS from `target:`.
- `gap_magnitude` — per §Score-against-objectives §4 (numeric distance to target boundary).
- `gap_age_days` — `(now - since) / 86400` rounded to whole days.

Rank candidates by composite gap, lexicographically: (a) `gap_magnitude > 0` outranks `gap_magnitude == 0`; (b) within each magnitude tier, larger `gap_age_days` wins; (c) ties broken by slug alphabetical for determinism. Pick the top **K = min(3, candidate_count)**.

Prose-only bullets (no `check:` block) are NOT eligible for planner drafting — the planner can only score what `check:` makes measurable. They remain visible in periodic-mode digests under "Goals" with the unscored marker but never produce a candidate.

**`docs/FUTURE-WORK.md` items are excluded from gap scoring.** Parked items are intentionally not active; counting them as open work would misrepresent the project's actual gap against its objectives. The planner's gap calculation operates against `docs/TODO.md > Next up` and `docs/SPEC.md` open items only.

Anti-objective bullets (under `## Anti-objectives`, prose-only by construction) are read for steering only — when drafting a candidate, the planner MUST verify the candidate description does not push toward any anti-objective; if it does, skip that candidate and pick the next-ranked one.

### δ. Draft each candidate

For each picked criterion, compose ONE candidate line in this exact format:

```
- [unconfirmed:<id>] [<tier>] <one-line description> — planner: targets objective <slug>; gap: <gap-summary>; reason: <one-sentence rationale> <!-- planner: <utc-iso> --> <!-- planner-id: <id> -->
```

Field rules:

- `<id>` — `<slug>-<YYYYMMDD>` where `<YYYYMMDD>` is today's UTC date with no separators (e.g. `spec-empty-20260502`). Stable for the lifetime of this draft; the `<!-- planner-id: -->` marker carries the same value for re-entry detection.
- `<tier>` — judgment-based: `[easy]` for mechanical / single-file / well-bounded work, `[medium]` for substantial multi-step reasoning, `[hard]` for cross-file or architectural design. Default `[medium]` when uncertain. The user's manual confirmation step (clearing the `[unconfirmed:`-prefix) is the safety net for tier mistakes; the dev cycle's normal pick-and-route then runs against the chosen tier.
- `<one-line description>` — actionable verb-led phrasing, e.g. "Author end-to-end smoke test exercising the full chain", "Compress oversized closed-phase blocks to ≤30 lines per anti-bloat objective". Avoid bare reformulation of the objective text (the rationale field carries the link); name a concrete shippable change.
- `<gap-summary>` — terse: `<check_result> <target_op> <target_value>, age <gap_age_days>d` (e.g. `7 != 0, age 12d`).
- `<one-sentence rationale>` — why THIS candidate moves THIS objective forward. One sentence; saving the longer "what does the user need to know" reasoning for the Telegram announcement below.

Append all K candidates to the END of `<project>/docs/TODO.md > ## Next up` (after any pre-existing user-authored entries; existing queued items keep their order). Do NOT touch any other section. Do NOT commit; the change is left in the working tree, the dev cycle's normal §1 pick will see the candidates only after the user clears at least one `[unconfirmed:`-prefix.

### ε. Persist planner state

Update `~/.claude/state/manager-cursors.json[<project-path>].planner`:

- `last_proposed_at` — current `<utc-iso>`.
- `last_proposed_ids` — list of the K `<id>` values just drafted.
- `queue_empty_since_tick` — leave as-is (the appended `[unconfirmed:*]` items now occupy `Next up`, so the next periodic tick will see non-empty-state and reset this field to null via §3 step 1).

Atomicity: read-modify-write the cursors file via tempfile + fsync + rename to keep state consistent across crash points.

### ζ. Announce via Telegram

Send ONE Telegram body summarizing the batch. Format:

```
🧠 Planner update — <Month D, YYYY>

Queue empty + spec fully checked across <N> tick(s); drafted <K> candidate(s) targeting highest-gap objectives:

  • [unconfirmed:<id>] [<tier>] <description>
    targets: <slug> (<gap-summary>)
    rationale: <one-sentence rationale>

Clear the `[unconfirmed:`-prefix in <project>/docs/TODO.md > Next up to release a candidate for the next dev cycle. Refuse a candidate by deleting its line. The planner will not draft a new batch until every [unconfirmed:*] item is cleared, converted, or deleted.
```

Apply the periodic-mode digest's language rules (translate tool names to role words, drop framework jargon, keep concrete specifics — see §4).

When auto-triggered from periodic mode §3, the planner output is appended to the §4 digest body under a new "Planner update" section rather than sent as a separate Telegram body, so the user receives one consolidated message per tick.

### η. Exit cleanly

Stdout: `planner: drafted <K> candidate(s) for <project> targeting <slug-list>` for explicit `--plan` invocation; auto-triggered runs continue to §4 (digest) and report there. Exit 0.

If any input read fails (objectives-path missing, project paths unreachable), exit non-zero with a stderr message naming the missing input. Missing Telegram credentials is not a fatal error — sends are gracefully skipped. The cursor field is left untouched on failure so the next tick retries.

### θ. Never invoke another `claude --print` / harness from planner mode

Same constraint as §On-demand E. Planner mode runs inside one harness invocation; recursing would multiply load and confuse downstream tooling. If picking a candidate would benefit from reading more code than the run log + TODO + SPEC + objectives expose, draft the candidate as a `[medium]` "investigate <X>" entry rather than reading the code itself; the dev cycle will do the read with proper context.

## Hard rules

- **No `git commit` / `git push` / SSH / curl-against-prod.** The manager never commits, pushes, or talks to live services. Write surface is bounded to: its own state files (`manager-cursors.json`, `manager-notes.md`, `manager-digests/`), the Telegram outbound, `<objectives-path>` `[ ]` ↔ `[x]` toggles, on-demand mode's `docs/TODO.md > Next up` appends + `docs/SPEC.md` appends in watched projects, AND planner-mode's `docs/TODO.md > Next up` appends of `[unconfirmed:*]` lines (with a `<!-- planner-id: <id> -->` marker) only. All TODO/SPEC scoped exceptions are APPENDS ONLY (modeled on the existing `objectives.md` `[ ]` ↔ `[x]` exception): never edits an existing item, never deletes, never renumbers, never modifies `## In flight` or `## Just shipped` or any phase heading text, never reorders phases, never commits or stages the change. The dev cycle's normal §1 pick is what eventually ships the queued item; the manager just inserts the line. **Planner-mode appends** are further bounded by §Planner mode β re-entry guard (one outstanding `[unconfirmed:*]` batch at a time per project) and by the `[unconfirmed:`-prefix that the user must clear manually before the dev cycle picks the item — the planner cannot silently broaden the agenda.
- **No `claude -p` / harness invocation.** The manager runs INSIDE a single skill invocation (one `claude -p`), which the cron / `/loop` / bot-spawn triggers. It does not spawn more — even in on-demand mode where re-reading state in a fresh harness might tempt it (see §On-demand feedback routing E).
- **Telegram messages capped at 4000 chars.** Truncate with `... [truncated; run /status <persona> for full digest]` if needed; the full digest is always in `manager-digests/<persona>_<utc>.txt`.
- **Never write a token, preimage, or chat ID into the digest body.** The CHAT_ID allowlist is enforced by the bot, not by message content.
- **Never re-notify on persistent paused-job state.** A rate-limited or otherwise paused job is reported ONCE at the pause edge (via the chain driver) and ONCE at resume. The manager's periodic digest may MENTION currently-paused jobs in the consolidated status block, but MUST NOT fire a separate Telegram body per tick for the same paused job. If a job stays paused across multiple manager ticks, treat that as steady state, not a new event.
- **On-demand mode is single-feedback-per-invocation.** `--process-feedback` accepts exactly one queue-file path and routes exactly one outcome. Batch routing (multiple queue files in one invocation) is a separate concern that belongs to the periodic-mode drain, not on-demand.
- **On-demand mode never touches digests.** The on-demand mode does NOT compose or send a status digest, regardless of whether `manager-digests/` is stale. Digests are a periodic-mode concern; the bot-spawned on-demand path is for single-message routing only.
- **Planner mode never proposes while a prior batch is outstanding.** §Planner mode β's re-entry guard is a hard invariant: any line under `## Next up` containing `[unconfirmed:` AND a `<!-- planner-id: -->` marker blocks new drafts for that project, including auto-trigger transitions from periodic mode. The user converts a candidate by clearing the `[unconfirmed:`-prefix (releasing it for the dev cycle), or refuses it by deleting the line.
- **Planner mode never invents prose-only objectives.** Candidates may only target open `[ ]` measurable bullets (with a `check:` continuation block). Prose-only and anti-objective bullets are never the source of a planner draft.

## Worker-lifecycle expectation

The `bin/manager-bot.py` long-poll worker is NOT meant to run persistently in this framework. The chain driver (`sst-chain-driver`) starts the worker at chain-session start and stops it at chain-session end, so inbound bot commands are only collected while a chain is actually running. The manager's own invocation is independent (the cron / `/loop` trigger does not require the bot worker to be running); manager runs that fire while the worker is down simply find no new queued commands in `~/.claude/state/manager-bot-queue/` and skip §1 cleanly. If a user wants always-on inbound (uncommon), they keep the worker manually under tmux / systemd; the manager doesn't care either way.
