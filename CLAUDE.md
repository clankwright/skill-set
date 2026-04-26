# skill-set — project instructions

This repo is the framework that defines how skill-chains, handoff docs, and supervisors work. When working here, **dogfood the framework's own contract on the framework itself.** The rules below are not aspirational; they are the same rules every skill that runs in any consuming project is required to follow.

## Handoff docs: read first, update in same commit

Before any non-trivial edit:

1. Read `docs/SPEC.md` end-to-end. This is the canonical plan for the framework itself.
2. Read `docs/TODO.md` end-to-end. Three sections: `In flight`, `Just shipped (last cycle)`, `Next up (queued for next cycle)`.

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

## Use the framework's own tools

- Validate any change to a skill or chain YAML with `bin/validate-frontmatter.py`.
- When testing a chain change, run it via `bin/skill-chain.py --chain <name>` (optionally with `--loop N`). Don't reinvent a bespoke runner.
- New chain definitions live in `chains/<name>.yaml` (transferable) and must satisfy `schema/skill-chain.schema.json`.
- New skill definitions live in `skills/<category>/<name>/SKILL.md` and must satisfy `schema/skill-set.schema.json`.
- If a change affects the harness abstraction, keep `bin/skill-chain.py`'s `Harness` base class the single source of truth; don't branch on harness names in the runner.

## Choosing a chain (skill-set's own dev cycles)

The proprietary chains under `.claude/chains/` are skill-set's own dogfooding surface. Pick by intent:

- **`/skill-set-chain-driver`** (canonical default; wraps `skill-set-cycle`, loop:3, $30 budget cap) — daily multi-item run that closes 1-3 queued items per session and posts Telegram updates at every iteration boundary, rate-limit pause, and session end. This is what the user invokes most days.
- **`/skill-set-chain-driver --chain skill-set-overnight --max-budget-usd 80`** (or higher) — unattended overnight drain. Loops until failure / budget / Ctrl-C; randomized [5min, 2h] inter-iter delay keeps commit cadence human-shaped across many hours; auto-promote `all` so the supervisor's framework improvements land within the run.
- **`bin/skill-chain.py --chain skill-set-cycle`** (no chain-driver wrap) — debug mode, no Telegram, no budget cap. Use when iterating on chain runner behavior or when you want a single quick item without the wrapper overhead.

Both proprietary chains exist locally only (`.claude/` is gitignored as Claude Code runtime state). The transferable parents are `dev-cycle-with-review-looped` and `dev-cycle-overnight` under `chains/`; consuming projects build their own `<persona>-cycle` / `<persona>-overnight` proprietary chains the same way.

## Never bypass the sanitization path

Any change that promotes a proprietary skill into a transferable one (or drafts a transferable proposal) must go through `skills/framework/sst-sanitize-transferable/` and include the sanitization-checklist footer. CI rejects PRs that skip this.

## Don't fork the contract

If you find yourself wanting to add a side-channel (a non-SPEC plan doc, a second TODO section, a bespoke log format), stop. The point of the framework is one contract across all projects. Change the contract in `docs/SPEC.md` + `templates/` first, then update every consuming surface.

## Telegram bot

User-facing setup, daily commands, and worker management live in `README.md` → "Telegram bot". When you touch this surface in code, honor these constraints:

- **Don't read `~/.config/*-telegram.env`.** Token is secret; the same rule the global `CLAUDE.md` applies to `.env` files under `~/Dev/**` extends here. If you need a value, ask the user to paste it.
- **Outbound: source the env file in a subshell, then pipe to `bin/notify-telegram.sh`.** That helper expects `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in the environment; it does NOT auto-source `TELEGRAM_ENV_FILE`.
- **The worker is a single `getUpdates` consumer.** Stop the tmux session before any inline `getUpdates` call, or your debug poll will steal updates from the worker.
- **Inbound state is queue files** under `~/.claude/state/manager-bot-queue/`. The manager skill drains them on its next run. Don't introduce a side-channel; the queue dir is the contract.
- **Env-file path is `~/.config/<persona>-telegram.env`**, where `<persona>` matches the proprietary chain-driver / manager skill name. New proprietary skills must match the convention so `bin/drive-chain.py --telegram-env` resolves without an explicit override.
- **Worker is chain-bound, not persistent.** `bin/manager-bot.py` only runs while a chain session is actively running (started by the chain driver at session-start, stopped at session-end per Phase 18). Don't leave the worker tmux session up between chain runs: it produces inbound-noise (the worker keeps acking the user's queued commands and replying) without any active chain whose state to report. The manager's periodic ticks work fine without the worker live; `~/.claude/state/manager-bot-queue/` is just empty between chain runs.
- **No re-notify on persistent paused-job state.** Rate-limit pause and resume each fire ONE Telegram body (the chain driver handles this). The manager's periodic digest may MENTION currently-paused jobs in the consolidated status block, but MUST NOT fire a separate Telegram body per tick for the same paused job. Persistent paused state is steady state, not a new event.
