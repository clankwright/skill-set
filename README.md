# skill-set

Field-agnostic, harness-agnostic **skill-sets** for autonomous LLM agents.

Currently only the [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) harness is implemented; the chain runner, supervisor, and manager are written so a second harness (Codex CLI, Gemini CLI, Cursor headless, etc.) drops in via a single `Harness` subclass.

## What's a skill-set?

A skill-set is a `(transferable, proprietary)` pair of `SKILL.md` files:

- **Transferable** — generalized, project-independent, lives in this repo, shareable.
- **Proprietary** — project- or company-specific, lives in your project's harness skills directory (currently `<project>/.claude/skills/`), never published. The proprietary skill names its transferable parent in frontmatter (`transferable: <name>`).

The pairing is the unit of reuse. The transferable holds the *method* (TDD cycle, lead verification, content-ops loop). The proprietary holds the *facts* the method needs to land in your specific environment (database name, deploy command, scope tags, escalation contacts).

## What ships here

- `skills/` — every transferable skill, grouped into category folders (`framework/`, `dev/`, `research/`, `content/`, `evaluation/`, `orchestration/`, `outreach/`). Each leaf `<category>/<name>/` holds one `SKILL.md` plus optional `references/`, `scripts/`, `assets/`. Categories are organizational for humans only: the harness identifies a skill by its `name:` field, not its path.
- `chains/` — every transferable skill-chain definition, one `.yaml` per chain. Each names a sequence of skills the chain runner executes in order. Projects keep their own proprietary chains under `<project>/.claude/chains/<name>.yaml`.
- `bin/skill-chain.py` — the chain runner. Spawns one harness subprocess per skill, streams pretty output, captures per-job logs. Accepts either an inline skill list or `--chain <name>` (looks up `<cwd>/.claude/chains/<name>.yaml` first, then `<repo>/chains/<name>.yaml`).
- `bin/install-skills.sh` — copies every `skills/**/<name>/` into the harness's user-skills directory (default `~/.claude/skills/<name>/`, flat — categories are dropped on install) so the harness picks them up globally. Claude Code only scans direct children of its skills dir, so the layout must stay flat.
- `bin/manager-bot.py` — long-poll Telegram bot for the manager skill.
- `templates/SPEC.md`, `templates/TODO.md` — the canonical handoff docs every project must keep.
- `templates/sanitization-guidance.md` — the rubric the `sst-sanitize-transferable` skill applies before any transferable promotion.
- `schema/` — JSON Schema specs the validator (and CI) lint against.
- `proposals/` — supervisor-generated transferable-skill patches awaiting human review.

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

auto-promote: proprietary       # "off" | proprietary (default) | all  # NOTE: "off" must be quoted (YAML 1.1 parses bare `off` as boolean false)

on-rate-limit: pause            # fail | pause (default) | pause-with-cap
max-rate-limit-pause-seconds: 28800   # cap on a single pause when on-rate-limit is pause-with-cap
max-pauses-per-session: 3             # hard cap on rate-limit pauses per skill per chain run

user-invocable: true            # default true; false = chain-only, not picked by /<chain-name>
auto-supervisor: true           # default true; false = don't auto-append the project's supervisor
```

CLI flags (`--loop`, `--loop-delay`, `--auto-promote`, `--on-rate-limit`, etc.) override the corresponding YAML field per invocation. Schema reference: `schema/skill-chain.schema.json`.

### Loop mode

`loop: N` makes the chain runner repeat its full skill sequence N times. A non-supervisor failure aborts the loop; Ctrl-C cleanly breaks after the current skill finishes. Each iteration's logs land in `<run-dir>/iter_NN/` with their own `MANIFEST.json`; the top-level `MANIFEST.json` carries an `iterations: [...]` array summarizing each pass. For `loop: 1` (the default) the single-run flat layout is preserved unchanged. `loop: 0` means "until failure / Ctrl-C," intended for `sst-chain-driver`-wrapped overnight runs where the budget cap is the natural stopping criterion.

Loop mode pairs naturally with skills that pick the next item from `TODO.md > Next up` each iteration: dev cycles, content cycles, lead-gen runs. The supervisor still runs once per iteration, so the handoff-doc contract stays intact between cycles.

**Empty-queue bail (steady-state stop).** When the project reaches steady state (`TODO.md > Next up` empty AND every `- [ ]` in `docs/SPEC.md` flipped `[x]`), the dev-cycle skill exits cleanly with the line `[no-work] <reason>` on stdout instead of inventing speculative work. The chain runner recognizes the `[no-work]` sentinel, skips the remaining skills in the iteration (review, supervisor), since there's no commit for them to work against, and aborts the loop entirely. The iter manifest records `no_work_bail: {skill, reason}`; the top-level `manifest["loop"]["terminated_by"] = "no_work_bail"` so a chain driver's session-end summary can label the stop "no-work bail" rather than "max-cycles reached." This is the canonical clean stop, not an error condition: an unattended `dev-cycle-overnight` run terminates as soon as the queue is exhausted instead of looping on speculative work to the budget cap. Sentinel format documented in `templates/SPEC.md`; any consuming project's dev skill opts in simply by emitting it.

### Chains shipped here

| Chain                            | Loop      | Auto-promote   | Use case                                                                                  |
| :---                             | :---      | :---           | :---                                                                                      |
| `dev-cycle-with-review`          | 1         | `proprietary`  | Single-item dev work. Conservative supervisor routing (proprietary edits land; transferable improvements wait for human promotion). |
| `dev-cycle-with-review-looped`   | 3         | `all`          | Three-item dev batch. Aggressive routing so the supervisor's transferable improvements land within the run and later iterations consume them. |
| `dev-cycle-overnight`            | 0         | `all`          | Unattended overnight drain of `TODO.md > Next up`. Auto-stops when the queue is exhausted (dev skill emits `[no-work]`, runner aborts the loop); `sst-chain-driver --max-budget-usd $X` is the secondary safety net. Randomized [5min, 2h] inter-iter delay keeps commit cadence human-shaped. |
| `editorial-with-fact-check`      | 1         | `off`          | Run a draft through an editorial pass with citation verification. No supervisor self-modification. |
| `multi-output-evaluation`        | 1         | `off`          | Compare N candidate outputs on a rubric and pick the best. |
| `research-and-write`             | 1         | `off`          | Research a topic and produce a synthesized written deliverable. |
| `research-write-promote`         | 1         | `off`          | Research → write → social-promote pipeline. |

Pick the dev chain by intent:

- **One specific change** → `dev-cycle-with-review` directly (`bin/skill-chain.py --chain dev-cycle-with-review`).
- **Knock out the next 1-3 items in one sitting** → `dev-cycle-with-review-looped` via `sst-chain-driver` so you get per-iter Telegram bodies.
- **Drain the queue overnight** → `dev-cycle-overnight` via `sst-chain-driver` with `--max-budget-usd $X` as the budget gate.

A proprietary `<persona>-chain-driver` skill (e.g. `skill-set-chain-driver`) carries the chain name + cap defaults so the user types `/<persona>-chain-driver` with no flags. Override `--loop`, `--max-budget-usd`, or `--max-cycles` on the CLI for a one-off shape change.

### Auto-promote

The supervisor (auto-appended to every chain unless `auto-supervisor: false`) writes proposed `SKILL.md` rewrites by routing on this field:

| `auto-promote` | Proprietary skill            | Transferable skill                                                                                |
| :---           | :---                         | :---                                                                                              |
| `off`          | sidecar `SKILL.patch.md`     | sidecar `SKILL.patch.md`                                                                          |
| `proprietary`  | direct overwrite `SKILL.md`  | sidecar `SKILL.patch.md`                                                                          |
| `all`          | direct overwrite `SKILL.md`  | direct overwrite iff `sst-sanitize-transferable` reports `must-fix: 0`; else sidecar `SKILL.patch.md` |

Default is `proprietary`: the supervisor's lessons land immediately on proprietary skills (so a multi-iteration loop converges within the run), but transferable changes still go to a sidecar for human review via `/sst-promote-skill-proposal`. Pick `off` for content / research / evaluation chains where skill self-modification is unwanted; pick `all` on dev loops where you want transferable improvements to land within the same run as well (the sanitize gate blocks proprietary leakage). Rolling back an unwanted direct overwrite is `git checkout <skill-dir>/SKILL.md`.

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
| `sst-dev-cycle`, `sst-dev-review`, `sst-skill-router`, `sst-editorial-pass`, `sst-iterative-writer`, `sst-literary-critic` | `sonnet` | `high` |
| `sst-translator`, `sst-fact-checker`, `sst-promote-skill-proposal`, `sst-output-selector`, `sst-llm-judge-ranker`, `sst-email-control-loop`, `sst-setup-telegram` | `haiku` | `medium` |

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

**Worked example** — a `[medium]` item picked by `sst-dev-cycle`, reviewed by `sst-dev-review`, then supervised by `sst-supervisor`:

| Skill                    | item tier         | skill floor       | resolved          |
| :---                     | :---              | :---              | :---              |
| `sst-dev-cycle`          | sonnet, medium    | sonnet, high      | **sonnet, high**  |
| `sst-dev-review`         | sonnet, medium    | sonnet, high      | **sonnet, high**  |
| `sst-supervisor`         | sonnet, medium    | opus, xhigh       | **opus, xhigh**   |

The dev + review run on Sonnet+high (effort floor wins on the effort axis; model floor matches the item tier on the model axis); the supervisor still runs on Opus+xhigh because its floors win on both axes regardless of item difficulty. A `[hard]` item by the same chain would lift dev + review to Opus+high (item tier wins on both axes); an `[easy]` item by `sst-translator` would run on Haiku+low (floors match the item tier).

**Throughput impact.** Combined with the dev/review tier dropping from Opus+xhigh to Sonnet+high on most items, routing review-class work to Sonnet+medium and mechanical work to Haiku+low cuts quota burn per iter to ~25-35% of an all-Opus+xhigh baseline (~3-4× more iters per Max window). Supervisor + sanitize stay on Opus+xhigh on every cycle since their floors are absolute; auto-promoted transferable rewrites are still authored at the supervisor's Opus+xhigh route.

**Anti-fork rule.** Floors are declared in SKILL.md frontmatter; the runner reads them, never invents them. The `max()` resolution rule binds at both axes — there is no path that lets an item difficulty drop a skill below its floor, and no fifth resolution input that bypasses both axes. If a new skill class needs a different floor pair, add the frontmatter values; don't branch the resolver.

## Telegram bot

The framework ships a small Telegram bot (`bin/manager-bot.py` + `bin/notify-telegram.sh`) so two long-running loops can talk to you directly:

- **`sst-chain-driver`** fires Telegram bodies at session start, every iteration boundary (commit + per-iter spend + cumulative), every rate-limit pause / resume, every halt request, and session end. Lets you walk away from a multi-hour `--loop N` run.
- **`sst-manager`** drains inbound slash-commands (`/status`, `/objectives`, `/proposals`, `/promote <project> <skill>`, `/pause`, `/resume`) into a queue at `~/.claude/state/manager-bot-queue/`, which the next manager run picks up.

### Setup

The user-invocable skill `sst-setup-telegram` provisions a bot end-to-end. Invoke it from any project:

```
/sst-setup-telegram
```

It walks you through the BotFather steps that must happen in your Telegram app (create the bot, send the first message), then automates everything else: `getMe` token verification, chat-id discovery via `getUpdates`, env-file write with mode 600, outbound + inbound round-trip tests, optional service-unit install, and `setMyCommands` registration.

Env-file naming convention: `~/.config/<persona>-telegram.env`, where `<persona>` matches the proprietary chain-driver / manager skill name (e.g. `~/.config/skill-set-telegram.env` for `skill-set-chain-driver`, `~/.config/sdrai-telegram.env` for an `sdrai-manager`). Each file holds two lines:

```
TELEGRAM_BOT_TOKEN=<from-BotFather>
TELEGRAM_CHAT_ID=<numeric-chat-id>
```

Mode 600, never committed. Token revocation: BotFather → `/revoke` → pick the bot → paste the new token into the env file.

### Daily use

Outbound (any script can fire a Telegram body):

```bash
( set -a; . ~/.config/skill-set-telegram.env; set +a; \
  echo "ship report: 3/3 iter clean" | bash bin/notify-telegram.sh )
```

`notify-telegram.sh` reads stdin, truncates to 4000 chars, POSTs to `sendMessage`, and exits non-zero if Telegram does not ack. `TELEGRAM_PARSE_MODE=Markdown` (default) lets you bold / link / code-format the body.

Inbound (you talk to the bot in Telegram):

```
/help    list commands
/ping    liveness check (worker replies "pong")
/status  paste back the most recent manager digest
```

The other commands (`/objectives`, `/proposals`, `/promote`, `/pause`, `/resume`) write a queue file to `~/.claude/state/manager-bot-queue/`; the next `<persona>-manager` invocation drains the queue.

**Replies are live only during chain runs.** The bot worker starts when a chain session begins and stops when it ends (chain-bound lifecycle). Commands you send between runs are queued to disk and acknowledged on the next session start — the bot going silent doesn't mean it's broken, it means no chain is currently running. Run `/ping` at the start of a chain session to confirm liveness before relying on inbound commands.

### Worker management

The long-poll worker (`bin/manager-bot.py`) holds the open connection to `api.telegram.org`. Two patterns:

**Chain-bound (recommended; Phase 18 in spec)**: the chain driver (`sst-chain-driver`) starts the worker at chain-session start and stops it at chain-session end. Worker only runs while there's an active chain whose state it can report on. Avoids the inbound-noise pattern where a persistent worker keeps acking queued user commands without an active chain. Until Phase 18 lands, this is operationally a manual pattern: the user starts the worker before invoking `/skill-set-chain-driver` (or whichever proprietary chain driver) and stops it after the run completes.

**Always-on (legacy / always-available bot)**: the worker runs persistently under one of three hosts, surfacing inbound commands even between chain runs. Keep this if you want manager-bot commands available 24/7 (the user can `/status` at any time and the next manager tick consumes the queued command). Three host options:

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
- **systemd user-unit** (auto-restart, survives host reboot when lingering is enabled): `bin/manager-bot.service` is shipped as a template; edit the four `<...>` placeholders, drop it at `~/.config/systemd/user/manager-bot.service`, then `systemctl --user daemon-reload && systemctl --user enable --now manager-bot.service && loginctl enable-linger <user>`.
- **rc.d** (FreeBSD and similar): `bin/manager-bot.rc.d` is the template. Copy to `/usr/local/etc/rc.d/manager-bot`, `chmod 755`, add `manager-bot_enable="YES"` to `/etc/rc.conf`, then `sudo service manager-bot start`.

### Caveats

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

Phase 1 in progress. See `docs/SPEC.md` for the full plan and current phase.

## License

MIT. See `LICENSE`.
