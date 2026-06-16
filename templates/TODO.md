# <Project Name> TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order.

## In flight

<!--
  Exactly one line per currently-running skill, format:
  - [<skill-name> @ <utc-iso>] <one-line: what this skill is currently doing>
  Rewrite (don't append) as the focus narrows. Empty when no skill is running.
-->

## Just shipped (last cycle)

<!--
  Append-on-close, newest first. Format:
  - <one-line summary> — by <skill-name> at <utc-iso>
  No commit SHA: a commit cannot contain its own hash, and the amend-based
  workarounds produce stale/dangling references. Correlate entries to commits
  via `git log --oneline --grep '<keyword-from-summary>'`. Trim to the most
  recent 10 entries; older history lives in the SPEC.md phase blocks and `git log`.
-->

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - [<difficulty>] <one-line description>. Reason: <spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Difficulty (model + effort routing) is one of: easy / medium / hard.
    [easy]   = Haiku tier + low effort. Mechanical, well-bounded.
    [medium] = Sonnet tier + medium effort. Substantial reasoning, multi-step, structured.
    [hard]   = Opus tier + high effort. Novel design, cross-file, architectural decisions.
  The chain runner pre-parses the top entry's label and routes the iter's skills via
  `effective = max(item_tier, skill_floor)` per axis. See SPEC.md "Difficulty labels"
  appendix for the full contract.
  Order: blockers/highest-impact first (label is independent of priority).
-->

## Tester sweep targets

<!--
  Queue of UI/UX surfaces for the looped standalone tester to drain one per
  iteration. The looped-standalone mode of sst-tester (and proprietary *-tester
  wrappers) reads this section to pick the next unexercised target, tracks
  exercised state out-of-tree at
  ~/.claude/state/sst-tester/<project-slug>/queue-<run-utc>.json, and
  self-terminates on [no-test-work] when the queue is empty or the section is
  absent. Run: `bin/skill-chain.py <tester-skill> --loop N`

  Format: - [P1|P2|P3] <surface description> [covered|partial|GAP]
    P1 = high impact / blocking; P2 = normal; P3 = low / polish.
    covered = exercised and green; partial = exercised with gaps; GAP = not yet exercised.
  Example:
  - [P1] Login and auth redirect flow GAP
  - [P2] Allocation page: submit + result table partial
  - [P3] Settings panel: all field types covered
-->
