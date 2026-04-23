# transferable-skills

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
- `bin/install-skills.sh` — copies every `skills/**/<name>/` into the harness's user-skills directory (default `~/.claude/skills/<name>/`, flat — categories are dropped on install) so the harness picks them up globally.
- `bin/manager-bot.py` — long-poll Telegram bot for the manager skill.
- `templates/SPEC.md`, `templates/TODO.md` — the canonical handoff docs every project must keep.
- `templates/sanitization-guidance.md` — the rubric the `sanitize-transferable` skill applies before any transferable promotion.
- `schema/` — JSON Schema specs the validator (and CI) lint against.
- `proposals/` — supervisor-generated transferable-skill patches awaiting human review.

## Three loops

| Loop       | Cadence              | Owner                     |
|------------|----------------------|---------------------------|
| Job        | per chain invocation | `bin/skill-chain.py`      |
| Supervisor | end of every chain   | `skills/framework/supervisor/` |
| Manager    | periodic / on demand | `skills/framework/manager/` + bot |

Each loop reads the project's handoff docs (`docs/SPEC.md`, `docs/TODO.md`) and writes back to them. Cross-cycle state lives in those files, not in any agent's context window.

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
