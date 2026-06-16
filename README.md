# skill-set

Field-agnostic, harness-agnostic **skill-sets** for autonomous LLM agents.

Currently only the [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) harness is implemented; the chain runner, supervisor, and manager are written so a second harness (Codex CLI, Gemini CLI, Cursor headless, etc.) drops in via a single `Harness` subclass.

## Features

**Framework model.** Every capability ships as a `(transferable, proprietary)` pair. Transferable skills use the `sst-*` prefix (generalized method, lives in this repo, shareable). Proprietary counterparts use `ssp-*` (project facts, live in `<project>/.claude/skills/`, never published). The runner invokes them by name; a consuming project adds only the thin `ssp-*` overlay for its environment.

**Skill catalog** (transferable `sst-*` skills, grouped by category):

| Skill | Category | Purpose |
|---|---|---|
| `sst-dev-cycle` | framework | TDD dev cycle: pick next spec item, write failing tests, implement, commit |
| `sst-dev-review` | framework | Post-cycle review: flag bugs, missing tests, spec drift |
| `sst-tester` | framework | UI/integration tester: Playwright sweep of changed surfaces |
| `sst-supervisor` | framework | Meta-reviewer: edits skill prose directly when a finding requires it |
| `sst-manager` | framework | Telegram-bot dispatcher: `/status`, `/pause`, `/feedback` |
| `sst-chain-driver` | framework | Chain orchestrator: budget cap, per-iter Telegram, rate-limit pause |
| `sst-executor` | framework | One-shot task executor for supervisor-delegated follow-ups |
| `sst-sanitize-transferable` | framework | Hard gate before any transferable SKILL.md edit |
| `sst-web-research` | research | Multi-source web research with citation |
| `sst-editorial-pass` | content | Draft to edited copy using a configurable rubric |
| `sst-social-promoter` | outreach | Research output to social post |

See `skills/` for the full catalog (research, content, evaluation, outreach, orchestration categories).

**Chains** (transferable chain definitions in `chains/`):

| Chain | Loop | Use case |
|---|---|---|
| `dev-cycle-with-review` | 1 | Single item: dev-cycle + tester + review |
| `dev-cycle-with-review-looped` | 3 | 3-item batch with aggressive supervisor routing |
| `dev-cycle-overnight` | 0 | Unattended queue drain; stops when queue is empty |
| `research-and-write` | 1 | Research a topic and produce a written deliverable |
| `editorial-with-fact-check` | 1 | Draft through editorial pass with citation check |
| `research-write-promote` | 1 | Research to write to social-promote pipeline |

**Unified runner CLI** (`bin/skill-chain.py` -- flags for chain scheduling and budget control):

| Flag | Purpose |
|---|---|
| `--chain <name>` | Load a named chain YAML instead of an inline skill list |
| `--loop N` | Repeat the full skill sequence N times (0 = until failure/Ctrl-C) |
| `--overnight` | Preset: loop=0, randomized delay; requires `--max-budget-usd` |
| `--batch '<glob>'` | Run a skill over every file matching the glob |
| `--max-budget-usd X` | Halt the loop when cumulative spend reaches $X |
| `--profile <path>` | Load chain defaults (loop, budget, label) from a YAML profile |
| `--telegram-env <path>` | Override the Telegram env-file for this run |

## Usage

**Run a chain once:**

```bash
bin/skill-chain.py --chain dev-cycle-with-review
```

**Run a looped batch (N iterations, stops on empty queue or Ctrl-C):**

```bash
bin/skill-chain.py --chain dev-cycle-with-review-looped --loop 3
```

**Drain the queue overnight (stops when queue is empty or budget is exhausted):**

```bash
bin/skill-chain.py --chain dev-cycle-overnight --overnight --max-budget-usd 30
```

**Batch mode (run a skill over every matching file):**

```bash
bin/skill-chain.py sst-dev-review --batch 'skills/**/*.md'
```

**Standalone tester sweep (exercise every UI surface a phase or set of shipped items introduced):**

```bash
/sst-tester --phase 47
# or target specific just-shipped items by name:
/sst-tester --todos "47.1+47.2 README"
```

## What's a skill-set?

A skill-set is a `(transferable, proprietary)` pair of `SKILL.md` files:

- **Transferable** — generalized, project-independent, lives in this repo, shareable.
- **Proprietary** — project- or company-specific, lives in your project's harness skills directory (currently `<project>/.claude/skills/`), never published. The proprietary skill names its transferable parent in frontmatter (`transferable: <name>`).

The pairing is the unit of reuse. The transferable holds the *method* (TDD cycle, lead verification, content-ops loop). The proprietary holds the *facts* the method needs to land in your specific environment (database name, deploy command, scope tags, escalation contacts).

## What ships here

- `skills/` — every transferable skill, grouped into category folders (`framework/`, `dev/`, `research/`, `content/`, `evaluation/`, `orchestration/`, `outreach/`). Each leaf `<category>/<name>/` holds one `SKILL.md` plus optional `references/`, `scripts/`, `assets/`. Categories are organizational for humans only: the harness identifies a skill by its `name:` field, not its path.
- `chains/` — every transferable skill-chain definition, one `.yaml` per chain. Each names a sequence of skills the chain runner executes in order. Projects keep their own proprietary chains under `<project>/.claude/chains/<name>.yaml`.
- `bin/skill-chain.py` — the chain runner. Spawns one harness subprocess per skill, streams pretty output, captures per-job logs. Accepts either an inline skill list or `--chain <name>` (looks up `<cwd>/.claude/chains/<name>.yaml` first, then `<repo>/chains/<name>.yaml`).
- `bin/install-skills.sh` — deploys transferable skills into the harness's user-skills directory (default `~/.claude/skills/<name>/`, flat — categories are dropped on install). Update-only by default: only skills already installed are refreshed; new ones are skipped. Use `--install <name>` to add a skill for the first time, or `--list-new` to see what's available. Claude Code only scans direct children of its skills dir, so the layout must stay flat.
- `bin/manager-bot.py` — long-poll Telegram bot for the manager skill.
- `templates/SPEC.md`, `templates/TODO.md` — the canonical handoff docs every project must keep.
- `templates/sanitization-guidance.md` — the rubric the `sst-sanitize-transferable` skill applies as a hard gate before any direct edit to a transferable skill.
- `schema/` — JSON Schema specs the validator (and CI) lint against.

## What's *not* shipped: the `ssp-*` proprietary skills

The repo ships only the `sst-*` transferables. Each one's proprietary counterpart is named `ssp-*` and lives under `<project>/.claude/skills/`, which is **gitignored** — so these skills are **never committed to or pushed from this repo**. They are local, per-machine runtime state, and exist so each checkout can carry its own custom modifications (banned-terms list, project paths, config, private wording) without publishing them.

In this repo (skill-set dogfooding itself) the proprietary set is:

| Proprietary (`ssp-*`, local only) | Transferable parent (`sst-*`, shipped) |
|---|---|
| `ssp-dev`          | `sst-dev-cycle`    |
| `ssp-dev-review`   | `sst-dev-review`   |
| `ssp-supervisor`   | `sst-supervisor`   |
| `ssp-manager`      | `sst-manager`      |
| `ssp-chain-driver` | `sst-chain-driver` |

Consuming projects name theirs `ssp-<project>-<role>` (e.g. `ssp-sdrai-supervisor`) so several projects' skills can coexist in one harness without colliding; skill-set's own use the bare `ssp-<role>` form since this repo is a single project.

Each `ssp-*` skill is a thin overlay: it `transferable:`-declares its `sst-*` parent, inherits that parent's full process at runtime, and adds only the local facts the method can't know. **They are NOT in the repo** — a fresh clone or a second machine has none of them. Set them up locally (create `.claude/skills/ssp-<role>/SKILL.md` plus the proprietary chains under `.claude/chains/`, or copy them from a machine that already has them, then `bin/install-skills.sh -y` to deploy the `sst-*` parents they inherit). Keeping them gitignored is intentional: each environment customizes freely without leaking private config into the public repo. The dogfooding chains (`skill-set-cycle` / `skill-set-overnight`) invoke them by name (`ssp-dev` → `ssp-dev-review` → auto-appended `ssp-supervisor`), so running the loop needs them present; hand-editing the `sst-*` transferables needs only what's in the repo.

## Three loops

| Loop       | Cadence              | Owner                     |
|------------|----------------------|---------------------------|
| Job        | per chain invocation | `bin/skill-chain.py`      |
| Supervisor | end of every chain   | `skills/framework/sst-supervisor/` |
| Manager    | periodic / on demand | `skills/framework/sst-manager/` + bot |

Each loop reads the project's handoff docs (`docs/SPEC.md`, `docs/TODO.md`) and writes back to them. Cross-cycle state lives in those files, not in any agent's context window.

## Chain YAML fields

A chain definition is a small YAML file under `chains/<name>.yaml` (transferable, lives in this repo) or `<project>/.claude/chains/<name>.yaml` (proprietary, lives in a consuming project). Beyond the four required fields (`name`, `description`, `version`, `skills`) the runner accepts a handful of optional fields that change scheduling, supervisor routing, and rate-limit handling:

```yaml
name: my-cycle                  # required, kebab-case, must match filename without .yaml
description: ...                # required, ≥20 chars
version: 1.0.0                  # required, semver
skills:                         # required, ordered; runner invokes each in sequence
  - skill-a
  - skill-b

loop: 3                         # default 1; N>1 runs the sequence N times; 0 = until failure / Ctrl-C
loop-delay: 0                   # seconds to sleep between iterations (default 0)
loop-delay-random: [60, 3600]   # OR sample uniform-random delay per boundary; mutually exclusive with loop-delay

on-rate-limit: pause            # fail | pause (default) | pause-with-cap
max-rate-limit-pause-seconds: 28800   # cap on a single pause when on-rate-limit is pause-with-cap
max-pauses-per-session: 3             # hard cap on rate-limit pauses per skill per chain run

user-invocable: true            # default true; false = chain-only, not picked by /<chain-name>
auto-supervisor: true           # default true; false = don't auto-append the project's supervisor
```

CLI flags (`--loop`, `--loop-delay`, `--on-rate-limit`, etc.) override the corresponding YAML field per invocation. Schema reference: `schema/skill-chain.schema.json`.

### Loop mode

`loop: N` makes the chain runner repeat its full skill sequence N times. A non-supervisor failure aborts the loop; Ctrl-C cleanly breaks after the current skill finishes. Each iteration's logs land in `<run-dir>/iter_NN/` with their own `MANIFEST.json`; the top-level `MANIFEST.json` carries an `iterations: [...]` array summarizing each pass. For `loop: 1` (the default) the single-run flat layout is preserved unchanged. `loop: 0` means "until failure / Ctrl-C," intended for `sst-chain-driver`-wrapped overnight runs where the budget cap is the natural stopping criterion.

Loop mode pairs naturally with skills that pick the next item from `TODO.md > Next up` each iteration: dev cycles, content cycles, lead-gen runs. The supervisor still runs once per iteration, so the handoff-doc contract stays intact between cycles.

**Empty-queue bail (steady-state stop).** When the project reaches steady state (`TODO.md > Next up` empty AND every `- [ ]` in `docs/SPEC.md` flipped `[x]`), the dev-cycle skill exits cleanly with the line `[no-work] <reason>` on stdout instead of inventing speculative work. The chain runner recognizes the `[no-work]` sentinel, skips the remaining skills in the iteration (review, supervisor), since there's no commit for them to work against, and aborts the loop entirely. The iter manifest records `no_work_bail: {skill, reason}`; the top-level `manifest["loop"]["terminated_by"] = "no_work_bail"` so a chain driver's session-end summary can label the stop "no-work bail" rather than "max-cycles reached." This is the canonical clean stop, not an error condition: an unattended `dev-cycle-overnight` run terminates as soon as the queue is exhausted instead of looping on speculative work to the budget cap. Sentinel format documented in `templates/SPEC.md`; any consuming project's dev skill opts in simply by emitting it.

### Chains shipped here

| Chain                            | Loop      | Auto-promote   | Use case                                                                                  |
| :---                             | :---      | :---           | :---                                                                                      |
| `dev-cycle-with-review`          | 1         | `proprietary`  | Single-item dev work; stage order: `dev → tester → review`. Conservative supervisor routing (proprietary edits land; transferable improvements wait for human promotion). |
| `dev-cycle-with-review-looped`   | 3         | `all`          | Three-item dev batch; stage order: `dev → tester → review`. Aggressive routing so the supervisor's transferable improvements land within the run and later iterations consume them. |
| `dev-cycle-overnight`            | 0         | `all`          | Unattended overnight drain of `TODO.md > Next up`; stage order: `dev → tester → review`. Auto-stops when the queue is exhausted (dev skill emits `[no-work]`, runner aborts the loop); `sst-chain-driver --max-budget-usd $X` is the secondary safety net. Randomized [5min, 2h] inter-iter delay keeps commit cadence human-shaped. |
| `editorial-with-fact-check`      | 1         | `off`          | Run a draft through an editorial pass with citation verification. No supervisor self-modification. |
| `multi-output-evaluation`        | 1         | `off`          | Compare N candidate outputs on a rubric and pick the best. |
| `research-and-write`             | 1         | `off`          | Research a topic and produce a synthesized written deliverable. |
| `research-write-promote`         | 1         | `off`          | Research → write → social-promote pipeline. |

Pick the dev chain by intent:

- **One specific change** → `dev-cycle-with-review` directly (`bin/skill-chain.py --chain dev-cycle-with-review`).
- **Knock out the next 1-3 items in one sitting** → `dev-cycle-with-review-looped` via `sst-chain-driver` so you get per-iter Telegram bodies.
- **Drain the queue overnight** → `dev-cycle-overnight` via `sst-chain-driver` with `--max-budget-usd $X` as the budget gate.

A proprietary `ssp-<persona>-chain-driver` skill (e.g. `ssp-chain-driver` in this repo, `ssp-sdrai-chain-driver` in a consumer) carries the chain name + cap defaults so the user types `/<persona>-chain-driver` with no flags. Override `--loop`, `--max-budget-usd`, or `--max-cycles` on the CLI for a one-off shape change.

**Standalone tester sweep (`sst-tester --phase` / `--todos`).** Besides its in-chain stage, `sst-tester` (and its proprietary wrappers) runs directly from the terminal to deliberately exercise EVERY UI surface a whole phase or set of completed todos introduced, not just the last diff: `/sst-tester --phase <id>` resolves every closed `[x]` front-end item under `### Phase <id>`; `/sst-tester --todos <ref...>` resolves the named `## Just shipped` entries; pass both to union the surface sets. The standalone sweep iterates all resolved surfaces (does not stop at the first failure), writes `tester-findings.{md,json}` to the out-of-tree state dir `~/.claude/state/sst-tester/<utc>/`, and prints a one-line verdict. It stays read-only on the tree and never commits or deploys, same as the in-chain mode. A proprietary wrapper supplies the project's phase->spec map (e.g. `/ssp-cm-tester --phase 3`).

### Skill self-improvement (direct edit + commit)

The supervisor (auto-appended to every chain unless `auto-supervisor: false`) edits skill source directly when a finding requires a skill's prose to change — there is no proposal file and no separate promotion step:

| Skill kind   | What the supervisor does                                                                                                  |
| :---         | :---                                                                                                                      |
| Proprietary  | edits `<cwd>/.claude/skills/<skill>/SKILL.md` in place (gitignored runtime copy; no commit). Live for the next iteration. |
| Transferable | edits the base-repo source `~/Dev/skill-set/skills/<cat>/<skill>/SKILL.md`, gated on `sst-sanitize-transferable` returning `must-fix: 0`, then bumps `version:`, commits, and pushes from the base repo. |

The supervisor's lessons land immediately: proprietary edits are live for the next iteration of a multi-iteration loop, and a sanitize-clean transferable edit is committed and pushed within the same run so the open-source master and every clone pick it up. A `must-fix` sanitization finding blocks the transferable edit and keeps the lesson proprietary-only. Rolling back an unwanted edit is `git checkout <skill-dir>/SKILL.md` (or `git revert` on the base-repo commit). The manager has the same base-repo edit authorization when the user requests it or it deems an edit necessary; see `sst-manager`.

### Rate-limit handling

When the active model run hits the rolling 5h Anthropic quota (or weekly / extra usage cap), `on-rate-limit: pause` (default) makes the runner sleep until the reset timestamp + jitter and re-invoke the killed skill from scratch. Each retry archives the prior attempt's `.txt`/`.jsonl` to `<stem>.retry-N.{ext}` so the audit trail is preserved. `pause-with-cap` falls back to `fail` when a single computed pause would exceed `max-rate-limit-pause-seconds`. `fail` (legacy) treats a rate-limit hit like any other non-zero exit. `max-pauses-per-session` aborts the chain when the same skill needs more than N pauses in one invocation, on the assumption that repeated pauses signal a quota-burning loop, not a genuine quota crossing.

## Model-tier routing

The runner picks `--model` and `--effort` per skill, per iteration, by combining two inputs: a **per-skill floor** declared in SKILL.md frontmatter, and a **per-item difficulty label** read from the dev's pick. Each axis (model, effort) resolves independently via `max()` so neither input can drop a safety-critical skill below its declared floor.

**Per-skill floors** sit in SKILL.md frontmatter as two optional fields:

```yaml
model-floor: opus      # opus | sonnet | haiku  (default opus)
effort-floor: xhigh    # low | medium | high | xhigh | max  (default high)
```

The framework's canonical floor table:

| Skill class                                                                 | `model-floor` | `effort-floor` |
| :---                                                                        | :---          | :---           |
| `sst-supervisor`, `sst-sanitize-transferable`                               | `opus`        | `xhigh`        |
| `sst-dev-cycle`, `sst-tester`, `sst-dev-review`, `sst-skill-router`, `sst-editorial-pass`, `sst-iterative-writer`, `sst-literary-critic` | `sonnet` | `high` |
| `sst-manager`                                                               | `sonnet`      | `high`         |
| `sst-translator`, `sst-fact-checker`, `sst-output-selector`, `sst-llm-judge-ranker`, `sst-email-control-loop`, `sst-setup-telegram` | `haiku` | `medium` |

**Per-item difficulty labels** sit on every open SPEC item and TODO Next-up entry:

- `[easy]` → Haiku tier + `low` effort (mechanical, well-bounded, no judgment-bleeding-edge).
- `[medium]` → Sonnet tier + `medium` effort (substantial reasoning, multi-step, structured).
- `[hard]` → Opus tier + `high` effort (novel design, cross-file reasoning, architectural decisions).

Format: SPEC items use `- [ ] [<difficulty>] <description>`; TODO Next-up uses `- [<difficulty>] <description>. Reason: ...`. Closed `[x]` items and `## Just shipped` entries don't carry labels (historical).

**Resolution rule (per skill, per iter):**

```
effective_model  = max(item.model_tier,  skill.model_floor)   over {haiku < sonnet < opus}
effective_effort = max(item.effort_tier, skill.effort_floor)  over {low < medium < high < xhigh < max}
```

Routing flow: the runner pre-parses the next item's difficulty BEFORE invoking the iter's first skill (the dev). The dev skill emits `[picked-difficulty: <tier>]` on stdout before its first tool call as the source of truth; if the actual pick differs from the pre-parse, the runner overrides the iter's difficulty for downstream skills (review, supervisor) only. Each skill's resolved route logs as `[route] /<skill>: difficulty=<d> floors=(<m>,<e>) -> model=<M> effort=<E>` and lands on the iter manifest's `route` sub-record for post-hoc analysis.

**Worked example** — a `[medium]` item picked by `sst-dev-cycle`, tested by `sst-tester`, reviewed by `sst-dev-review`, then supervised by `sst-supervisor`:

| Skill                    | item tier         | skill floor       | resolved          |
| :---                     | :---              | :---              | :---              |
| `sst-dev-cycle`          | sonnet, medium    | sonnet, high      | **sonnet, high**  |
| `sst-tester`             | sonnet, medium    | sonnet, high      | **sonnet, high**  |
| `sst-dev-review`         | sonnet, medium    | sonnet, high      | **sonnet, high**  |
| `sst-supervisor`         | sonnet, medium    | opus, xhigh       | **opus, xhigh**   |

The dev, tester, and review run on Sonnet+high (effort floor wins on the effort axis; model floor matches the item tier on the model axis); the supervisor still runs on Opus+xhigh because its floors win on both axes regardless of item difficulty. A `[hard]` item by the same chain would lift dev, tester, and review to Opus+high (item tier wins on both axes); an `[easy]` item by `sst-translator` would run on Haiku+low (floors match the item tier).

**Throughput impact.** Combined with the dev/tester/review tier dropping from Opus+xhigh to Sonnet+high on most items, routing review-class work to Sonnet+medium and mechanical work to Haiku+low cuts quota burn per iter to ~25-35% of an all-Opus+xhigh baseline (~3-4× more iters per Max window). Supervisor + sanitize stay on Opus+xhigh on every cycle since their floors are absolute; transferable skill edits committed by the supervisor are still authored at the supervisor's Opus+xhigh route.

**Anti-fork rule.** Floors are declared in SKILL.md frontmatter; the runner reads them, never invents them. The `max()` resolution rule binds at both axes — there is no path that lets an item difficulty drop a skill below its floor, and no fifth resolution input that bypasses both axes. If a new skill class needs a different floor pair, add the frontmatter values; don't branch the resolver.

## Telegram bot

The framework ships a small Telegram bot (`bin/manager-bot.py` + `bin/notify-telegram.sh`) so two long-running loops can talk to you directly:

- **`sst-chain-driver`** fires Telegram bodies at session start, every iteration boundary (commit + per-iter spend + cumulative), every rate-limit pause / resume, every halt request, and session end. Lets you walk away from a multi-hour `--loop N` run.
- **`sst-manager`** drains inbound slash-commands (`/status <project>`, `/objectives <project>`, `/pause <project>`, `/resume <project>`, `/feedback <project> <message>`) into a queue at `~/.claude/state/manager-bot-queue/`, which the next manager run picks up. A project token is required for all inbound commands except `/ping`, `/help`, and `/projects`.

### Setup

The user-invocable skill `sst-setup-telegram` provisions a bot end-to-end. Invoke it from any project:

```
/sst-setup-telegram
```

It walks you through the BotFather steps that must happen in your Telegram app (create the bot, send the first message), then automates everything else: `getMe` token verification, chat-id discovery via `getUpdates`, env-file write with mode 600, outbound + inbound round-trip tests, optional service-unit install, and `setMyCommands` registration.

Env-file naming convention: `~/.config/<persona>-telegram.env`, where `<persona>` matches the proprietary chain-driver / manager skill name (e.g. `~/.config/skill-set-telegram.env` for `ssp-chain-driver`, `~/.config/sdrai-telegram.env` for an `ssp-sdrai-manager`). Each file holds two lines:

```
TELEGRAM_BOT_TOKEN=<from-BotFather>
TELEGRAM_CHAT_ID=<numeric-chat-id>
```

Mode 600, never committed. Token revocation: BotFather → `/revoke` → pick the bot → paste the new token into the env file.

**Base-dir fallback (simplest single-bot setup).** If you run multiple projects from one skill-set installation and want all of them to share one Telegram channel without per-project env files, create `~/Dev/skill-set/telegram.env` with the same two lines (mode 600, already gitignored). `bin/notify-telegram.sh`, `bin/skill-chain.py`, and `sst-manager §0.4` all check this file last in their resolution chain — it fires only when no more-specific per-persona env is configured. Per-persona env files always win when present.

### Daily use

Outbound (any script can fire a Telegram body):

```bash
( set -a; . ~/.config/skill-set-telegram.env; set +a; \
  echo "ship report: 3/3 iter clean" | bash bin/notify-telegram.sh )
```

`notify-telegram.sh` reads stdin, truncates to 4000 chars, POSTs to `sendMessage`, and exits non-zero if Telegram does not ack. `TELEGRAM_PARSE_MODE=Markdown` (default) lets you bold / link / code-format the body.

**Multi-project labeling:** when multiple personas share the same bot, set `TELEGRAM_LABEL=<persona>` before calling `notify-telegram.sh` and every outbound body will be prefixed with `[<persona>]` on its own line. `bin/skill-chain.py` sets this automatically from `--label` (or the chain name as fallback), so chain-driver bodies are already labeled when you run a named chain. Consuming projects whose proprietary `*-notify-telegram.sh` wrapper currently hard-codes a label prefix can collapse to a one-line passthrough that exports `TELEGRAM_LABEL=<persona>` and execs `bin/notify-telegram.sh`.

Inbound (you talk to the bot in Telegram):

```
/help      list commands
/ping      liveness check (worker replies "pong")
/status    paste back the most recent manager digest
/projects  list registered personas, their project roots, and their tokens
```

All commands except `/ping`, `/help`, and `/projects` REQUIRE a project token as the first argument (e.g. `/status cm`, `/feedback cm <text>`). Run `/projects` to see the live token-to-project registry; discovery is filesystem-driven from `~/.claude/skills/*-manager/SKILL.md`.

The token-required commands (`/status`, `/objectives`, `/pause`, `/resume`, `/feedback`) write a queue file to `~/.claude/state/manager-bot-queue/`; the next `<persona>-manager` invocation drains the queue. The three agnostic commands (`/ping`, `/help`, `/projects`) take no token and are answered by the bot directly, without a queue file.

**Replies are live whenever the worker is running.** Since Phase 35 the bot is a pure dispatcher: every project-scoped command spawns a one-time manager process that re-reads project state, so there is no stale-reply risk from a persistent worker. Run the worker always-on (recommended) so commands work between chain runs.

### Worker management

The long-poll worker (`bin/manager-bot.py`) holds the open connection to `api.telegram.org`. Run it always-on so commands work at any time, not just during active chain sessions.

**Always-on (recommended)**: run the worker persistently under one of three hosts. Commands fire the matching manager skill on demand; replies arrive within seconds regardless of whether a chain is running.

Three host options:

- **tmux** (laptop-friendly; default for `sst-setup-telegram`): one detached session per worker. Survives terminal close, not host reboot.
  ```bash
  # Start:
  tmux new-session -d -s manager-bot \
      "TELEGRAM_ENV_FILE=$HOME/.config/skill-set-telegram.env /usr/bin/python3 $PWD/bin/manager-bot.py 2>&1"
  # Watch:
  tmux attach -t manager-bot          # Ctrl-b d to detach
  # Restart (kill + relaunch):
  tmux kill-session -t manager-bot
  tmux new-session -d -s manager-bot "..."   # same command as above
  ```
- **systemd user-unit** (auto-restart, survives host reboot when lingering is enabled): `bin/manager-bot.service` is a ready-to-use template that already enables dispatcher mode (`MANAGER_SKILL_NAME=1`) and uses `%h` (systemd home specifier) for all paths. Edit only two values: `WorkingDirectory` and `TELEGRAM_ENV_FILE`. Then:
  ```bash
  cp bin/manager-bot.service ~/.config/systemd/user/manager-bot.service
  # edit WorkingDirectory= and TELEGRAM_ENV_FILE= to match your paths
  systemctl --user daemon-reload
  systemctl --user enable --now manager-bot.service
  # WSL and other headless hosts: enable linger so the user slice
  # stays alive without an active login session
  loginctl enable-linger "$USER"
  ```
  If `claude` is not on the service's PATH (common for pipx/uv installs), uncomment and set `CLAUDE_BIN` in the service file. For project-local proprietary managers not symlinked into `~/.claude/skills/`, uncomment and set `MANAGER_SKILLS_EXTRA_ROOTS`.
- **rc.d** (FreeBSD and similar): `bin/manager-bot.rc.d` is the template. Copy to `/usr/local/etc/rc.d/manager-bot`, `chmod 755`, add `manager-bot_enable="YES"` to `/etc/rc.conf`, then `sudo service manager-bot start`.

### Caveats

- **Spread cron ticks when multiple personas share one Anthropic account.** Back-to-back manager ticks (e.g. `:00`/`:05`/`:10`) all run on the same rolling 5-hour quota window; if the first tick consumes most of the window, the second and third are rejected mid-run. Stagger ticks across hours instead: e.g. `:00`, `:20`, `:40` within the same hour, or spread across different hours altogether. The idle pre-check (`bin/manager-idle-check.py`) reduces quota burn when projects have no new activity, but cannot help when all ticks fire simultaneously.
- **Single `getUpdates` consumer.** Telegram allows only one process polling `getUpdates` per bot. While the worker is running, an inline `curl .../getUpdates` for debugging will steal updates from it: stop the worker first.
- **Sleep is fine; hibernate / `wsl --shutdown` is not.** Host sleep just freezes the worker; on wake the long-poll is re-established and Telegram replays any queued inbound (24h server-side queue). Hibernate or full shutdown requires manual relaunch (or a systemd unit with `Restart=always`).
- **No webhook mode.** `manager-bot.py` is long-poll only; no public hostname or TLS cert needed. Webhook would be a separate worker.

## Selecting a harness

```bash
# Default (Claude Code):
./bin/skill-chain.py my-cycle

# Explicit:
./bin/skill-chain.py --harness claude-code my-cycle

# Or via env:
AGENT_HARNESS=claude-code ./bin/skill-chain.py my-cycle
```

To add another harness, subclass `Harness` in `bin/skill-chain.py`, register it in `HARNESSES`, and (if it emits a different stream format) supply an event parser.

## Status

Phase 47 complete. See `docs/SPEC.md` for the full plan and phase history.

## License

MIT. See `LICENSE`.
