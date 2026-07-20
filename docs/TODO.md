# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

<!-- nothing in flight -->

## Just shipped (last cycle)

- Phase 68 (68.1-68.3): [log-dir]/[iter-dir]/[iteration] injected into every skill prompt; --skill-args passthrough; executor spawns via skill-chain wrapper w/ rate-limit pause-resume (manager-bot spawn_executor, sst-supervisor 2.10.0 §5c); sst-executor 1.1.0 archives queue file at close-out only (Sanitize: must-fix=0) — by owner request at 2026-07-20T01:30:00Z
- docs: archive completed SPEC phases 46-67 to SPEC-DONE.md (SPEC.md has no active phases); move HUMAN.md H43.1 + H44.1 to ## Done (Sanitize: n/a) — by owner request at 2026-07-17T01:14:12Z
- 67.1: inline sanitize gate into sst-dev-cycle in-session (H43.1 option 1; Phase 66 catch reframed as generic backstop; mirrors reconciled to base 1.21.0; Sanitize: must-fix=0) — by owner request at 2026-07-17T01:02:25Z
- 66.1: runner commit re-prompt on incomplete-cycle before review handoff (H43.1 option 2; Sanitize: n/a) — by owner request at 2026-07-17T00:40:07Z
- 50.4: Widen OVERLOAD_TEXT_RE for resource_exhausted + Server error mid-response (Phase 50 backoff before supervisor) — by owner request at 2026-07-16T07:32:31Z
- Phase 65.2: gate post-iter `[totals after iter N]` behind `if looping:` (Sanitize: n/a) — by ssp-dev at 2026-07-14T02:28:24Z
- Phase 65.1: cumulative run totals in MANIFEST `totals:` + `[totals]` stdout (Sanitize: n/a) — by ssp-dev at 2026-07-14T02:22:33Z
- Phase 63.2: comment out CURSOR_MODEL in `.env.example` (opt-in pin; copy no longer disables Grok ladder) (Sanitize: n/a) — by ssp-dev at 2026-07-14T02:06:08Z
- Phase 64.3: exclude normalize-synthesized tool_call frames from Cursor `_turn_proxy` / max-turns (tag `_synthetic_from_tool_call`; Phase-49 gates unchanged) (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:58:59Z
- Phase 64 (64.1-64.2): Cursor nested-skill Read+follow cold-start directive + runner max-turns watchdog via assistant-frame proxy (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:52:46Z

<!--
  Append-on-close, newest first. Format:
  - <one-line summary> — by <skill-name> at <utc-iso>
  No commit SHA: a commit cannot contain its own hash, and amend-based
  workarounds produce stale references. Correlate entries to commits via
  `git log --oneline --grep '<keyword>'`. Older entries below retain their
  SHAs from the prior two-commit pattern; leave them alone, they're valid.
  Trim to the most recent 10 entries; older history lives in docs/SPEC.md
  phase blocks and `git log`.
-->

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

<!-- From 2026-07-14T01-55Z review of Phases 61.3–64 since last Review (89f218b, 7b10693, 9b1e01d, 87c0ed7). -->

<!-- planner candidate tests-passing-fix (2026-06-25) resolved: the objectives.md pytest-path fix was applied directly in a live session; candidate removed, no dev-cycle pick needed. -->
