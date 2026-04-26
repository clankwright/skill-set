# <Project Name> SPEC

> Canonical project spec. Every skill that runs in this project reads this file end-to-end before deciding what to do, and updates it (along with `TODO.md`) in the same commit as any code change.

## Goal

<One paragraph: what are we building, for whom, and why. This shouldn't change cycle-to-cycle; if it does, that's a Manager-level decision, not a skill-level one.>

## Architecture / stack (one-liner each)

- Backend: <e.g. FastAPI + PostgreSQL>
- Frontend: <e.g. SPA in static/>
- Deployment: <e.g. the project's deploy command — cloud VM, container platform, serverless, etc.>

## Phases

### Phase 0: <name>

<1-paragraph context — what this phase accomplishes and why it's grouped together.>

- [ ] [easy] Item 1: <one-liner — mechanical, well-bounded, no judgment-bleeding-edge>
- [ ] [medium] Item 2: <one-liner — substantial reasoning, multi-step, structured>

### Phase 1: <name>

<1-paragraph context.>

- [ ] [hard] Item 1: <one-liner — novel design, cross-file reasoning, architectural decisions, anything spec-closing on a complex phase>
- [ ] [medium] Item 2: <one-liner>

## Deferred / out of scope

- <Item that was considered and explicitly punted, with the reason. Revisit when the reason no longer applies.>

## Glossary (project-specific terms)

- **<term>**: <one-line definition>

---

### How this file evolves

- A skill closes an item by flipping `- [ ]` → `- [x]` in the same commit as the code change.
- When all items in a phase are checked, append a "completed" block to that phase: 1-paragraph result + bulleted file citations + test-count delta. Don't delete the phase's checklist; it's the historical record.
- New work surfaced mid-cycle goes to `TODO.md`'s "Next up", not directly here. The next cycle decides whether it merits a new spec phase or was actually a follow-up to the current one.

### Difficulty labels (model + effort routing)

Every open `- [ ]` SPEC item AND every `## Next up` TODO entry MUST carry a difficulty label as the leading bracket immediately after the `- [ ]` checkbox (or the leading `- ` for TODO entries). Three values, mapping to BOTH a model tier and a reasoning-effort tier:

- `[easy]` → Haiku tier + `low` effort. Mechanical, well-bounded, no judgment-bleeding-edge (e.g. backfilling a new field across files, renaming an identifier, fixing a typo, applying an approved migration to N call-sites).
- `[medium]` → Sonnet tier + `medium` effort. Substantial reasoning, multi-step, structured (e.g. a bounded bug fix touching one module + its tests, a small new endpoint following an existing pattern, a documented refactor).
- `[hard]` → Opus tier + `high` effort. Novel design, cross-file reasoning, architectural decisions, anything spec-closing on a complex phase (e.g. introducing a new contract surface, designing a new schema, debugging an underspecified failure mode).

The chain runner pre-parses the picked item's label and routes the iteration's skills accordingly. Each skill's own SKILL.md carries `model-floor:` + `effort-floor:` frontmatter fields setting the lowest tier that skill is ever allowed to run on; the resolution rule is `effective = max(item_tier, skill_floor)` per axis (model and effort resolved independently). So a `[easy]` item picked by a Sonnet-floored skill still runs Sonnet (floor wins); a `[hard]` item picked by a Haiku-floored skill runs Opus (item wins).

Closed items (`- [x]`) and `## Just shipped` entries don't carry labels (historical). Closed-phase result paragraphs don't either.

Format examples:

```markdown
# In SPEC.md
- [ ] [easy] Backfill `model-floor:` on every shipped SKILL.md.
- [ ] [medium] Wire the runner's difficulty pre-parse + `[picked-difficulty:]` sentinel capture.
- [ ] [hard] Introduce an `allowed-harnesses:` frontmatter field with anti-fork guards across supervisor / sanitization paths.
```

```markdown
# In TODO.md > Next up
- [easy] Quote the bare `argument-hint:` value in <skill>/SKILL.md so it parses as a string. Reason: validator caught it.
- [medium] Soften `sst-dev-review` §0.2 from halt-on-dirty-tree to note-and-proceed. Reason: review verdict <date>.
- [hard] Phase 19 per-skill model-tier + effort routing. Reason: spec Phase 19.
```

A consuming project's dev skill (`sst-dev-cycle` or any `<project>-dev-cycle` proprietary counterpart) reads the label of the picked item before any tool call and emits `[picked-difficulty: <tier>]` on a single stdout line; the chain runner captures that as the authoritative tier for any skill that runs after the dev. If the picked item is missing a label, the dev skill warns with `[bad-label] item missing difficulty; defaulting to medium` and proceeds with `[picked-difficulty: medium]` (graceful degradation during the contract-bump rollout window). When the framework upgrades to hard-fail, that warn becomes a non-zero exit; in the meantime, treat unlabeled items as a queue-hygiene gap to fix opportunistically.

### Empty-queue bail (steady state)

When `TODO.md`'s "Next up" is empty AND every `- [ ]` in this spec has been flipped to `[x]` AND the user gave no specific task, a dev-cycle skill (`sst-dev-cycle` or any `<project>-dev-cycle` proprietary counterpart) MUST exit 0 cleanly without picking an item, writing tests, or committing. Before exiting it prints exactly one line on stdout:

```
[no-work] <one-line reason>
```

The chain runner (`bin/skill-chain.py`) recognizes this sentinel and aborts the loop entirely (no review skill, no supervisor, no further iterations). The iteration's manifest records `iter_manifest["no_work_bail"] = {"skill": "<name>", "reason": "<sentinel-line>"}`; the top-level `manifest["loop"]["terminated_by"] = "no_work_bail"` distinguishes a bail from natural max-cycles completion or a real failure. A chain driver's session-end report should label the stop "no-work bail," not "max-cycles reached."

Any consuming project's dev skill can opt into the contract simply by emitting the sentinel in the same situation; no chain-runner change is required per project.
