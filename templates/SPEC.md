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

- [ ] Item 1: <one-liner>
- [ ] Item 2: <one-liner>

### Phase 1: <name>

<1-paragraph context.>

- [ ] Item 1: <one-liner>
- [ ] Item 2: <one-liner>

## Deferred / out of scope

- <Item that was considered and explicitly punted, with the reason. Revisit when the reason no longer applies.>

## Glossary (project-specific terms)

- **<term>**: <one-line definition>

---

### How this file evolves

- A skill closes an item by flipping `- [ ]` → `- [x]` in the same commit as the code change.
- When all items in a phase are checked, append a "completed" block to that phase: 1-paragraph result + bulleted file citations + test-count delta. Don't delete the phase's checklist; it's the historical record.
- New work surfaced mid-cycle goes to `TODO.md`'s "Next up", not directly here. The next cycle decides whether it merits a new spec phase or was actually a follow-up to the current one.
