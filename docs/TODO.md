# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

<!-- nothing in flight -->

## Just shipped (last cycle)

- Phase 64 (64.1-64.2): Cursor nested-skill Read+follow cold-start directive + runner max-turns watchdog via assistant-frame proxy (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:52:46Z
- Phase 63.1: Cursor Grok ladder routing — map Phase-19 floors → cursor-grok-4.5-{low,medium,high}; real ids in [route]/MANIFEST/--model (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:45:58Z
- Phase 62 (62.1-62.2): Cursor Playwright MCP cold-start + mcp.json discovery (never cursor-ide-browser); suppress Claude fable stdout under `--harness cursor` (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:29:09Z
- Phase 61.3: brave-web `_resolve_credentials` merges missing keys from env-file (free-in-env + paid-from-file); 3 regression tests (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:20:18Z
- Phase 61 (61.1-61.2): Cursor Brave web search/fetch (`bin/brave-web.py`, free→paid key) + `--approve-mcps`/`--trust`; Claude Code untouched (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:15:27Z
- Phase 60.1: estimate Cursor harness $ cost from usage tokens (Grok 4.5 API rates fallback; --max-budget-usd re-enabled; Sanitize: n/a) — by ssp-dev at 2026-07-14T01:09:44Z
- Phase 59.2: ssp-chain-driver Locations retargeted — overnight jitter via `--overnight` / `--loop-delay-random` (v1.0.3; Sanitize: n/a, proprietary) — by ssp-dev at 2026-07-14T00:54:10Z
- Phase 59.1: remove redundant overnight chain YAMLs (`dev-cycle-overnight` + `skill-set-overnight`); overnight = `--overnight` on looped cycle; README/CLAUDE.md/tests updated (Sanitize: n/a) — by ssp-dev at 2026-07-14T00:48:37Z
- Phase 58.7: `Harness.apply_budget_constraints` no-op + `CursorHarness` override (loud-skip `--max-budget-usd`); removed module-level `_maybe_clear_cursor_budget` name-branch — by ssp-dev at 2026-07-14T00:43:52Z
- Default loop-delay is none: runner no longer injects DEFAULT_LOOP_DELAY_RANDOM when unset; `dev-cycle-with-review-looped` uses `loop-delay: 0` (overnight / `--overnight` keep 5-30min jitter) — by manual at 2026-07-14T00:39:51Z

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
- [medium] [should-fix] 64.3 `bin/skill-chain.py:normalize_event`+`_turn_proxy` — tool_call→assistant inflation makes Phase-64 max-turns fire ~10× early on tool-heavy Cursor runs — review of 87c0ed7
- [easy] [should-fix] 63.2 `.env.example:13` — filled `CURSOR_MODEL=` pin disables Phase-63 Grok ladder when copied to `.env` — review of 9b1e01d

<!-- planner candidate tests-passing-fix (2026-06-25) resolved: the objectives.md pytest-path fix was applied directly in a live session; candidate removed, no dev-cycle pick needed. -->
