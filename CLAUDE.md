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
- Move the finished item to `Just shipped (last cycle)` as `- <sha-short> <one-line> — by <agent-or-skill> at <utc-iso>`. Trim that section to the most recent 10.
- If you close a SPEC phase item, flip its `- [ ]` → `- [x]` in the same commit.
- Any follow-up work discovered during the cycle goes to `Next up`, not the SPEC directly.
- `SPEC.md`, `TODO.md`, and the code change ship in a **single commit**. Do not split them.

## Use the framework's own tools

- Validate any change to a skill or chain YAML with `bin/validate-frontmatter.py`.
- When testing a chain change, run it via `bin/skill-chain.py --chain <name>` (optionally with `--loop N`). Don't reinvent a bespoke runner.
- New chain definitions live in `chains/<name>.yaml` (transferable) and must satisfy `schema/skill-chain.schema.json`.
- New skill definitions live in `skills/<category>/<name>/SKILL.md` and must satisfy `schema/skill-set.schema.json`.
- If a change affects the harness abstraction, keep `bin/skill-chain.py`'s `Harness` base class the single source of truth; don't branch on harness names in the runner.

## Never bypass the sanitization path

Any change that promotes a proprietary skill into a transferable one (or drafts a transferable proposal) must go through `skills/framework/sst-sanitize-transferable/` and include the sanitization-checklist footer. CI rejects PRs that skip this.

## Don't fork the contract

If you find yourself wanting to add a side-channel (a non-SPEC plan doc, a second TODO section, a bespoke log format), stop. The point of the framework is one contract across all projects. Change the contract in `docs/SPEC.md` + `templates/` first, then update every consuming surface.
