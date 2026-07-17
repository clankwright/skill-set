# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

<!-- nothing in flight -->

## Just shipped (last cycle)

- 66.1: runner commit re-prompt on incomplete-cycle before review handoff (H43.1 option 2; Sanitize: n/a) — by owner request at 2026-07-17T00:40:07Z
- 50.4: Widen OVERLOAD_TEXT_RE for resource_exhausted + Server error mid-response (Phase 50 backoff before supervisor) — by owner request at 2026-07-16T07:32:31Z
- Phase 65.2: gate post-iter `[totals after iter N]` behind `if looping:` (Sanitize: n/a) — by ssp-dev at 2026-07-14T02:28:24Z
- Phase 65.1: cumulative run totals in MANIFEST `totals:` + `[totals]` stdout (Sanitize: n/a) — by ssp-dev at 2026-07-14T02:22:33Z
- Phase 63.2: comment out CURSOR_MODEL in `.env.example` (opt-in pin; copy no longer disables Grok ladder) (Sanitize: n/a) — by ssp-dev at 2026-07-14T02:06:08Z
- Phase 64.3: exclude normalize-synthesized tool_call frames from Cursor `_turn_proxy` / max-turns (tag `_synthetic_from_tool_call`; Phase-49 gates unchanged) (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:58:59Z
- Phase 64 (64.1-64.2): Cursor nested-skill Read+follow cold-start directive + runner max-turns watchdog via assistant-frame proxy (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:52:46Z
- Phase 63.1: Cursor Grok ladder routing — map Phase-19 floors → cursor-grok-4.5-{low,medium,high}; real ids in [route]/MANIFEST/--model (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:45:58Z
- Phase 62 (62.1-62.2): Cursor Playwright MCP cold-start + mcp.json discovery (never cursor-ide-browser); suppress Claude fable stdout under `--harness cursor` (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:29:09Z
- Phase 61.3: brave-web `_resolve_credentials` merges missing keys from env-file (free-in-env + paid-from-file); 3 regression tests (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:20:18Z
- Phase 61 (61.1-61.2): Cursor Brave web search/fetch (`bin/brave-web.py`, free→paid key) + `--approve-mcps`/`--trust`; Claude Code untouched (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:15:27Z

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
