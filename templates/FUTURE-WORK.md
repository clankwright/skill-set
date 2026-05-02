# <Project Name> FUTURE-WORK

Parking lot for items the project is not actively working on this cycle:

- **Manual / human verification** — acceptance tests that need real-world observation, end-to-end smoke tests with live external dependencies, or any check the dev cycle cannot self-verify from inside its own iteration.
- **Deferred work** — phases or sub-items consciously parked behind a prerequisite. State the re-pick condition explicitly so the work can be scheduled when ready.
- **Future items** — work the user wants to keep visible but not queued for the next cycle.

This file is **not picked from automatically.** The dev cycle's pick order is unchanged: `TODO.md > Next up` first, then the next unchecked item in `SPEC.md`. Entries here are surfaced only by humans (or by a human-invoked planner pass).

## Format

Mirror the SPEC item ID where one exists. Group by section. One line per item; copy the original prose verbatim so it can be flipped back into `Next up` without re-authoring.

## Manual / human verification

(Add entries here for acceptance tests that require human observation, live chain runs, Telegram verification, production smoke tests, etc.)

## Deferred work

(Add entries here for phases or sub-items blocked on a prerequisite. State the re-pick condition when you add the entry.)

## Future / human-handled

(Add entries here for work the user wants visible but not queued yet.)

## Flipping an item back into `Next up`

1. Pick the entry. Copy its one-line description.
2. Append to `docs/TODO.md > Next up` as `- [<difficulty>] <description>. Reason: flipped from FUTURE-WORK <utc-iso>`.
3. Delete the entry from this file (or leave it under `## Just flipped` if you want a paper trail; not required).
4. The next dev cycle picks it per the normal pick order.
