# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

<!-- nothing in flight -->

## Just shipped (last cycle)

- Phase 54 (54.1+54.2+54.3+54.4): consolidate HUMAN.md to the oversight layer -- revoke read/write from sst-dev-cycle (v1.14.0) + sst-dev-review (v1.13.0); RE-HOME the phase-completion branch-setup handoff to sst-supervisor (§5b.1, v2.7.0) and the blocked-item pick-gating to sst-manager (§3b, v2.4.0); mirror into ssp-cm-dev (base 1.14.0) + ssp-cm-dev-review (base 1.13.0); SPEC "Handoff docs" + README carry the invariant; reconciled ssp-manager base-version 2.3.0->2.4.0; 26 new tests in test_phase54.py; 564->590 green; validate-frontmatter clean; transferables sanitize-clean -- by manual completion (live session) at 2026-06-25T12:11:54Z (orphaned cycle 2026-06-25T09-17-14Z continued from its failing test file)
- Phase 53 (53.1+53.2): sst-manager always-reply hard rule (v2.2.0->v2.3.0) + manager-bot.py deadlock-watcher; 17 new tests; 547->564 green — by sst-dev-cycle at 2026-06-25T05:00:00Z
- Runner markdown-wrapped sentinel fix: relax PICKED_DIFFICULTY_SENTINEL_RE + BATCH_PICK_SENTINEL_RE with \W* tolerance; 5 new guard tests in test_skill_chain.py; 542->547 green — by sst-dev-cycle at 2026-06-25T03:30:00Z
- 52.1+52.2: add four anti-pattern RED-FLAGS to sst-tester + ssp-cm-tester mirror; add synthetic-data-masking note to sst-dev-cycle e2e guard — by sst-dev-cycle at 2026-06-25T02:00:00Z
- 51.4 fix sst-tester standalone blast-radius diff source (git show HEAD -> git log -p per file): SKILL.md step 6a mode-conditional note; 3 new tests; 527->530 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-25T01:00:00Z
- 51.1+51.2+51.3 Phase 51 close: sst-tester blast-radius mandate (FLOOR-not-ceiling, derive-from-diff, adjacent/integrated surfaces, All/none/many, record-gaps, budget reconciliation) v1.6.1->v1.7.0; ssp-cm-tester base-version 1.6.1->1.7.0 + §4b CM heuristics (merged-table scroll/virtualization, select-all partitions, all-clients aggregate, legend swatch match, report/credit sanity); README in-chain broadened coverage prose; 18 new tests; 509->527 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-25T00:15:00Z
- enforce escalate outcome-line leading-word convention in sst-supervisor §7 (v2.4.0->v2.4.1) + 2 guard tests in test_skill_chain.py; 507->509 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-24T11:10:00Z
- Items 1+3 from Next up: e2e blind-ship guard in sst-dev-cycle §6 (E2e-only guard prose + [needs-live-stack] path) + batch-pick non-emission formally accepted (Known model-behavior gap prose + batch_pick_missing documented); v1.11.0->v1.12.0; 6 new tests in test_dev_cycle_contracts.py; 501->507 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-24T10:00:00Z
- gate wrote_tester_guidance in handle_event on Write/Edit only (not Read); add Read-does-not-trip + Edit-sets-flag tests; 499->501 green — by sst-dev-cycle at 2026-06-24T08:30:00Z
- 50.1+50.2+50.3 Phase 50 close: transient 5xx overload signal capture (result-frame api_error_status, api_retry events, OVERLOAD_TEXT_RE text fallback) + exponential-backoff retry in run_skill_with_retry (independent of rate-limit path, OVERLOAD_MAX_RETRIES=10/BASE=10/CAP=300) + --max-overload-retries CLI flag + overload_retry_records manifest + Telegram overload-retry/resume events + README + sst-chain-driver SKILL.md v1.3.0->1.4.0; 25 new tests; 474->499 green; sanitize must-fix=0 -- by sst-dev-cycle at 2026-06-24T00:00:00Z

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

<!-- queue empty: Phase 54 shipped 2026-06-25; no item queued for the next cycle -->

- [unconfirmed:tests-passing-fix-20260625] [easy] Fix the tests-passing objective check to call `~/.local/bin/pytest` instead of `python3 -m pytest` in ssp-manager's objectives.md — planner: targets objective skill-set-tests-passing; gap: 1 != 0, age 35d; reason: system `python3` is 3.10 but pytest is installed for Python 3.11 at `~/.local/bin/pytest`, causing a false fail even when all 590 tests pass. <!-- planner: 2026-06-25T23:16:32Z --> <!-- planner-id: tests-passing-fix-20260625 -->

