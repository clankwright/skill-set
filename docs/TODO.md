# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

## Just shipped (last cycle)

- 51.1+51.2+51.3 Phase 51 close: sst-tester blast-radius mandate (FLOOR-not-ceiling, derive-from-diff, adjacent/integrated surfaces, All/none/many, record-gaps, budget reconciliation) v1.6.1->v1.7.0; ssp-cm-tester base-version 1.6.1->1.7.0 + §4b CM heuristics (merged-table scroll/virtualization, select-all partitions, all-clients aggregate, legend swatch match, report/credit sanity); README in-chain broadened coverage prose; 18 new tests; 509->527 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-25T00:15:00Z
- enforce escalate outcome-line leading-word convention in sst-supervisor §7 (v2.4.0->v2.4.1) + 2 guard tests in test_skill_chain.py; 507->509 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-24T11:10:00Z
- Items 1+3 from Next up: e2e blind-ship guard in sst-dev-cycle §6 (E2e-only guard prose + [needs-live-stack] path) + batch-pick non-emission formally accepted (Known model-behavior gap prose + batch_pick_missing documented); v1.11.0->v1.12.0; 6 new tests in test_dev_cycle_contracts.py; 501->507 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-24T10:00:00Z
- gate wrote_tester_guidance in handle_event on Write/Edit only (not Read); add Read-does-not-trip + Edit-sets-flag tests; 499->501 green — by sst-dev-cycle at 2026-06-24T08:30:00Z
- 50.1+50.2+50.3 Phase 50 close: transient 5xx overload signal capture (result-frame api_error_status, api_retry events, OVERLOAD_TEXT_RE text fallback) + exponential-backoff retry in run_skill_with_retry (independent of rate-limit path, OVERLOAD_MAX_RETRIES=10/BASE=10/CAP=300) + --max-overload-retries CLI flag + overload_retry_records manifest + Telegram overload-retry/resume events + README + sst-chain-driver SKILL.md v1.3.0->1.4.0; 25 new tests; 474->499 green; sanitize must-fix=0 -- by sst-dev-cycle at 2026-06-24T00:00:00Z
- 49.3: runner-level never-both enforcement in bin/skill-chain.py -- handle_event sets wrote_tester_guidance on a tester-guidance.md tool-use; run_iteration voids a same-run [skip-tester] (records tester_skip_voided) instead of popping the tester, so a dev that wrote guidance always gets its touched surface exercised; 4 new tests in test_skill_chain.py; 454→458 green -- integrated from a CM-agent fix by the user at 2026-06-18
- 49.1+49.2 Phase 49 close: soften WIND_DOWN_DIRECTIVE_TEMPLATE false enforcement claim (conditional "if a hard ceiling is in force it is {hard} turns"); update sst-tester SKILL.md wind-down principle + new Per-target flush and session budget subsection (v1.4.0→1.5.0); update ssp-cm-tester base-version to 1.5.0; 8 new tests; 446→454 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-17T06:40:00Z

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

- 48.4: fix D1 dispatch discriminator in sst-tester SKILL.md (add tester-guidance.md in-chain guard at line 62; update stale line 132 to name looped-standalone as third mode); 2 new tests; 437→439 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-17T02:10:00Z
- 48.1+48.2+48.3 Phase 48 close: tester-target queue (templates/TODO.md), looped-standalone drain + [no-test-work] bail (sst-tester v1.1.0→v1.2.0), NO_TEST_WORK_SENTINEL_RE + loop-abort in skill-chain.py, README looped tester example, CM tester mirror (base-version→1.2.0); 23 new tests; 414→437 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-17T00:50:00Z
- 47.3: fix batch mode usage example (add --output-template 'reviewed/{stem}.md') + strengthen test_usage_batch_example assertion; 414→414 green — by sst-dev-cycle at 2026-06-16T23:55:00Z
- 47.1+47.2 Phase 47 close: add ## Features (sst-/ssp- model, skill catalog table, chains table, CLI flags table) + ## Usage (4 copy-pasteable examples) to README.md; test_phase47.py 23 tests; 391→414 green — by sst-dev-cycle at 2026-06-16T23:15:00Z
- 46.1+46.2 Phase 46 close: delete bin/drive-chain.py + bin/skill-batch.py, remove test_drive_chain_telegram.py, strip 5 shim tests from test_phase42.py + add test_epilog_documents_wrapper_flags, add test_phase46.py (4 tests), scrub all shim .py references from skill-chain.py (epilog + 6 comments), notify-telegram.sh, sst-chain-driver SKILL.md (v1.3.0); sanitize must-fix=0; validate-frontmatter clean; 394→391 green — by sst-dev-cycle at 2026-06-16T22:40:00Z
- 44.1+44.2+44.3+44.4 Phase 44 close: standalone `--phase`/`--todos` mode in sst-tester (SKILL.md v1.0.0→1.1.0; two-modes dispatch D1, scope resolution D2, iterate-all D3, out-of-tree findings D4); test_phase44.py 15 tests + 2 fixtures pin D2 resolution; mirror into ssp-cm-tester (base-version→1.1.0, CM phase->spec map; check-ssp-sync clean); README+CLAUDE invocation docs; relax test_phase41 version pin to major-1 semver; 379→394 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-16T21:55:00Z
- 42.10: move mkdir below dry-run continue in run_batch_mode(), add no-dir-creation test; 378→379 green — by sst-dev-cycle at 2026-06-16T21:10:00Z
- 42.4+42.5+42.6+42.7: --batch mode in skill-chain.py, drive-chain.py shim, caller migration + tests; 364→378 green — by sst-dev-cycle at 2026-06-16T20:30:00Z
- 42.9 add integration test: profile-sourced budget satisfies --overnight cap requirement (no CLI cap + profile fills → no SystemExit, loop=0); 363→364 green — by sst-dev-cycle at 2026-06-16T19:05:00Z
## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [easy] [should-fix] 51.4 standalone-mode blast-radius uses wrong diff source: step 6a "Use `git show HEAD` hunks" misses earlier phase commits in standalone mode (skills/framework/sst-tester/SKILL.md:103) — review of 42235b1
- [medium] Test-design anti-pattern guards: make `sst-tester` (+ `ssp-cm-tester`) flag tests whose DESIGN cannot fail on the real bug -- synthetic-data masking (pre-populating the data the code fails to fetch), jsdom-can't-test-layout (virtualization/map/color need a real browser), All/none/many cardinality gaps, and assert-request-not-result. -- SPEC Phase 52; user question 2026-06-25 ("how are all these regressions getting through the test suites?") + post-mortem of CM SPEC 3.70-3.77 / 10.5.
- [supervisor] [easy] Runner false-flags `batch_pick_missing` on markdown-wrapped markers: relax `PICKED_DIFFICULTY_RE` (`bin/skill-chain.py:313`) and `BATCH_PICK_SENTINEL_RE` (`bin/skill-chain.py:325`) to tolerate leading/trailing markdown (`**bold**`, backticks) around the `[picked-difficulty: <tier>]` / `[batch-pick]` markers, mirroring the `\W*` tolerance §0.5.3 already applies to the `[no-work]` sentinel; add a guard test in `tests/test_skill_chain.py` asserting a `**[batch-pick]**` + `**[picked-difficulty: medium]**` emission sets `emitted_batch_pick` and `picked_difficulty` (no `batch_pick_missing`). — supervisor verdict 2026-06-24T23-57-40Z_dev-cycle-with-review-looped (iter_01 dev emitted both markers bold-wrapped at 00_sst-dev-cycle.txt:30/35; runner falsely set batch_pick_missing)



