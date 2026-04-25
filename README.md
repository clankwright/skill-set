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

`loop: N` makes the chain runner repeat its full skill sequence N times. A non-supervisor failure aborts the loop; Ctrl-C cleanly breaks after the current skill finishes. Each iteration's logs land in `<run-dir>/iter_NN/` with their own `MANIFEST.json`; the top-level `MANIFEST.json` carries an `iterations: [...]` array summarizing each pass. For `loop: 1` (the default) the single-run flat layout is preserved unchanged.

Loop mode pairs naturally with skills that pick the next item from `TODO.md > Next up` each iteration: dev cycles, content cycles, lead-gen runs. The supervisor still runs once per iteration, so the handoff-doc contract stays intact between cycles. `chains/dev-cycle-with-review-looped.yaml` ships a 3-iteration variant of `dev-cycle-with-review` for exactly this use.

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
