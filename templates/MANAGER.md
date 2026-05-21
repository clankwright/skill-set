# <project-name> — per-project manager guidance

This file carries per-project steering for the operator-level manager. It is read at walk time alongside `docs/SPEC.md`, `docs/TODO.md`, and `docs/FUTURE-WORK.md`. Every rule here is **advisory steering** — the manager uses it to shape digests and on-demand routing for this project, but nothing in this file can override the transferable anti-fork constraints (no `main`-push, no sanitize bypass, no commit/deploy from the manager).

## Project token

The value here must match the `name:` field in the operator-manager's `watched-projects:` entry. The manager cross-checks on each walk; a mismatch is surfaced as a warning in the digest.

```
project-token: <project-name>
```

## Digest tone

Vocabulary preferences and surface choices that shape how this project's section reads in the manager digest. Examples:

- **Feature-name lookups** — map internal code names to plain-English names (e.g. "`sst-dev-cycle`" → "the dev cycle").
- **What to surface** — specific areas worth calling out: "always mention open rate-limit pauses", "include spend-per-iter if > $5".
- **What to suppress** — noise the user does not want in digests: "skip the validator clean count", "do not mention passing tests in stable phases".

If no preferences apply, leave this section empty or delete it.

## Per-project hard rules

Rules that apply specifically to this project. The manager enforces these when composing digests and when routing on-demand feedback. These are advisory steering: violating them is surfaced as a warning, not a blocker; the transferable anti-fork rules still take precedence.

Examples:

- "Never propose production-cutover candidates — deployment is owned by `/<persona>-deploy`."
- "Test-branch deploys are owned by `/<persona>-deploy-test`; do not draft TODO items about them."
- "If the most recent supervisor verdict is `escalate`, always escalate (not status-digest) regardless of the digest frequency setting."

List one rule per bullet. Leave this section empty if no project-specific rules apply.

## Notes

Free-form context the manager can reference when routing feedback or composing digests: stakeholder names, upcoming deadlines (use ISO dates), in-flight decisions that aren't in the SPEC yet, or anything that helps the manager avoid confusing this project with another. This section is read-only for the manager; only the human operator edits it.
