# skill-set — project instructions

This repo is the framework that defines how skill-chains, handoff docs, and supervisors work. When working here, **dogfood the framework's own contract on the framework itself.** The rules below are not aspirational; they are the same rules every skill that runs in any consuming project is required to follow.

## Communication style (low-bandwidth mode)

The user has extremely limited attention. Keep every reply exceptionally terse.

- Output ONLY what was explicitly asked for; drop preamble, trivial detail, and narration.
- Do surface, briefly: anything the user likely did not anticipate, anything unexpected that turned up, anything the user must be aware of, and actions ONLY the user can complete (that you cannot do yourself).
- Prefer bullet points; lead each with a **bold topic/action prefix**, then minimal detail.
- Briefly note completed items so the user knows they were not overlooked. ALWAYS report errors, warnings, and problems.

## Handoff docs: read first, update in same commit

Before any non-trivial edit:

1. Read `docs/SPEC.md` end-to-end. This is the canonical plan for the framework itself.
2. Read `docs/TODO.md` end-to-end. Three sections: `In flight`, `Just shipped (last cycle)`, `Next up (queued for next cycle)`.
3. If `docs/FUTURE-WORK.md` exists, read it end-to-end. Do not pick from it — it is the project's parking lot for deferred work and acceptance tests requiring human verification. Only humans move entries from here into `Next up`.
4. If `docs/HUMAN.md` exists, read it end-to-end. Do not pick from it — check for open `## Blocking` entries whose `Blocks:` line covers your intended change before proceeding.

Pick work this way:

- If `TODO.md > Next up` is non-empty, the top item is the next cycle's work unless the user says otherwise.
- Else, pick the next unchecked `- [ ]` item in `SPEC.md`.
- If the user hands you a task directly, that overrides both; still surface any conflict with the queue before starting.

On close of every substantive change:

- Write one `- [<what-you're-doing> @ <utc-iso>]` line under `In flight` when you start. Rewrite (don't append) as focus narrows. Clear it when done.
- Move the finished item to `Just shipped (last cycle)` as `- <one-line> — by <agent-or-skill> at <utc-iso>`. No commit SHA: a commit cannot contain its own hash; find the matching commit via `git log --oneline --grep '<keyword>'`. Trim that section to the most recent 10.
- If you close a SPEC phase item, flip its `- [ ]` → `- [x]` in the same commit.
- Any follow-up work discovered during the cycle goes to `Next up`, not the SPEC directly.
- `SPEC.md`, `TODO.md`, and the code change ship in a **single commit**. Do not split them.

**Sub-item IDs.** Every `- [ ]` and `- [x]` item in `SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 26.1 [medium] **description**`). IDs are assigned once and never renumbered; closed or removed items leave their ID void — gaps are valid. New items append at the end as `<phase>.<n+1>`; inserts between existing items use letter suffixes (`<phase>.<n>a`, …). When filing a `## Next up` entry or commit message, prefer the ID over "Phase N sub-item text." The validator checks for duplicates within each phase block.

## Use the framework's own tools

- Validate any change to a skill or chain YAML with `bin/validate-frontmatter.py`.
- When testing a chain change, run it via `bin/skill-chain.py --chain <name>` (optionally with `--loop N`). Don't reinvent a bespoke runner.
- New chain definitions live in `chains/<name>.yaml` (transferable) and must satisfy `schema/skill-chain.schema.json`.
- New skill definitions live in `skills/<category>/<name>/SKILL.md` and must satisfy `schema/skill-set.schema.json`.
- If a change affects the harness abstraction, keep `bin/skill-chain.py`'s `Harness` base class the single source of truth; don't branch on harness names in the runner.

## Choosing a chain (skill-set's own dev cycles)

The proprietary chains under `.claude/chains/` are skill-set's own dogfooding surface. Pick by intent:

- **`/ssp-chain-driver`** (canonical default; wraps `skill-set-cycle`, loop:3, $30 budget cap) — daily multi-item run that closes 1-3 queued items per session and posts Telegram updates at every iteration boundary, rate-limit pause, and session end. No inter-iter delay by default (back-to-back). This is what the user invokes most days.
- **`/ssp-chain-driver --chain skill-set-overnight --max-budget-usd 80`** (or higher) — unattended overnight drain. Loops until failure / budget / Ctrl-C; randomized [5min, 30min] inter-iter delay keeps commit cadence human-shaped across many hours; the supervisor edits and commits framework skill improvements directly within the run, so later iterations consume them.
- **`bin/skill-chain.py --chain skill-set-cycle`** (no chain-driver wrap) — debug mode, no Telegram, no budget cap. Use when iterating on chain runner behavior or when you want a single quick item without the wrapper overhead.

Both proprietary chains exist locally only (`.claude/` is gitignored as Claude Code runtime state). The transferable parents are `dev-cycle-with-review-looped` and `dev-cycle-overnight` under `chains/` (stage order: `sst-dev-cycle → sst-tester → sst-dev-review`, with `sst-tester` inserted in Phase 41); consuming projects build their own `<persona>-cycle` / `<persona>-overnight` proprietary chains the same way.

`sst-tester` also runs standalone from the terminal (Phase 44): `/sst-tester --phase <id>` or `/sst-tester --todos <ref...>` sweeps every UI surface a whole phase (closed `[x]` front-end items) or named `## Just shipped` todos introduced, iterating all of them (not just the last diff), writing `tester-findings.{md,json}` to `~/.claude/state/sst-tester/<utc>/`. The in-chain mode (no scope args) is unchanged. Proprietary wrappers (`ssp-cm-tester`) supply the per-project phase->spec map, e.g. `/ssp-cm-tester --phase 3`.

It is safe to invoke any of these even when `TODO.md > Next up` is empty AND every SPEC `[ ]` is `[x]`: the dev skill's pre-flight emits `[no-work]` and the chain runner aborts the loop cleanly without picking speculative work, running review/supervisor, or burning further iterations. The bail surfaces a single short iteration log + a "no-work bail" session-end Telegram body, no commit.

**Throughput note (Phase 19 routing).** With per-skill `model-floor:` + `effort-floor:` and per-item `[easy|medium|hard]` labels live, the chain runner now resolves each skill's `--model` + `--effort` independently via `max(item_tier, skill_floor)` on each axis. The dev, tester, and review skills drop from Opus+xhigh to Sonnet+high on `[medium]` items and to Haiku+low / Sonnet+medium where labels permit, lifting Max-quota throughput per cycle window to roughly 2-4× the prior all-Opus+xhigh baseline. The supervisor (and `sst-sanitize-transferable`, where it runs) still consumes Opus+xhigh quota at the old rate because its floors are absolute — `max(any_item_tier, opus) = opus` and `max(any_item_effort, xhigh) = xhigh` — so any cycle that authors a transferable rewrite via the supervisor still pays the Opus+xhigh tariff for that skill. See `README.md` → "Model-tier routing" for the floor table + worked example. The proprietary `ssp-supervisor` (project-scoped) is the auto-appended supervisor in this repo and carries the canonical Opus+xhigh floors directly; consuming projects pick up the canonical `sst-supervisor` floors on the next `bin/install-skills.sh -y --force` (queued in `Next up` as the long-stale Phase 2 follow-up).

## Never bypass the sanitization path

Any change that promotes a proprietary skill into a transferable one (or drafts a transferable proposal) must go through `skills/framework/sst-sanitize-transferable/` and include the sanitization-checklist footer. CI rejects PRs that skip this.

## Don't fork the contract

If you find yourself wanting to add a side-channel (a non-SPEC plan doc, a second TODO section, a bespoke log format), stop. The point of the framework is one contract across all projects. Change the contract in `docs/SPEC.md` + `templates/` first, then update every consuming surface.

## Telegram bot

User-facing setup, daily commands, and worker management live in `README.md` → "Telegram bot". When you touch this surface in code, honor these constraints:

- **Don't read `~/.config/*-telegram.env`.** Token is secret; the same rule the global `CLAUDE.md` applies to `.env` files under `~/Dev/**` extends here. If you need a value, ask the user to paste it.
- **Outbound: pipe to `bin/notify-telegram.sh` with credentials in env.** Credential resolution order (first match wins): (1) caller-exported `TELEGRAM_BOT_TOKEN`; (2) `TELEGRAM_ENV_FILE` env var pointing at a `.env` file; (3) base-dir fallback `~/Dev/skill-set/telegram.env` — the shared channel for all projects using skill-set when no per-persona env is configured; (4) graceful skip (exit 0 with stderr note) when nothing is configured. Two explicit ways to invoke: (a) `TELEGRAM_ENV_FILE=<env-path> bash bin/notify-telegram.sh` — auto-sourced when `TELEGRAM_BOT_TOKEN` is not already exported; (b) pre-source in a subshell (`( set -a; . <env-path>; set +a; echo "..." | bash bin/notify-telegram.sh )`). Explicit shell env always wins (auto-source skipped when the caller already set the token). `bin/skill-chain.py` (Phase 42) and `sst-manager §0.4` follow the same resolution chain. `telegram.env` is gitignored — never commit it.
- **The worker is a single `getUpdates` consumer.** Stop the tmux session before any inline `getUpdates` call, or your debug poll will steal updates from the worker.
- **Inbound state is queue files** under `~/.claude/state/manager-bot-queue/`. The manager skill drains them on its next run. Don't introduce a side-channel; the queue dir is the contract.
- **Env-file path is `~/.config/<persona>-telegram.env`**, where `<persona>` matches the proprietary chain-driver / manager skill name. New proprietary skills must match the convention so `bin/skill-chain.py --telegram-env` resolves without an explicit override.
- **Worker is always-on.** Since Phase 35 the bot is a pure dispatcher — every project-scoped command spawns a one-time manager process that re-reads project state on each invocation, eliminating the stale-reply risk that motivated Phase 18's chain-bound lifecycle. Run `bin/manager-bot.py` persistently (tmux / systemd / rc.d); commands work whether a chain is active or not. The chain driver no longer starts or stops the worker.
- **No re-notify on persistent paused-job state.** Rate-limit pause and resume each fire ONE Telegram body (the chain driver handles this). The manager's periodic digest may MENTION currently-paused jobs in the consolidated status block, but MUST NOT fire a separate Telegram body per tick for the same paused job. Persistent paused state is steady state, not a new event.
