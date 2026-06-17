# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

## Just shipped (last cycle)

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



