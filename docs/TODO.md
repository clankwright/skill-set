# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

## Just shipped (last cycle)

- Runner markdown-wrapped sentinel fix: relax PICKED_DIFFICULTY_SENTINEL_RE + BATCH_PICK_SENTINEL_RE with \W* tolerance; 5 new guard tests in test_skill_chain.py; 542->547 green — by sst-dev-cycle at 2026-06-25T03:30:00Z
- 52.1+52.2: add four anti-pattern RED-FLAGS to sst-tester + ssp-cm-tester mirror; add synthetic-data-masking note to sst-dev-cycle e2e guard — by sst-dev-cycle at 2026-06-25T02:00:00Z
- 51.4 fix sst-tester standalone blast-radius diff source (git show HEAD -> git log -p per file): SKILL.md step 6a mode-conditional note; 3 new tests; 527->530 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-25T01:00:00Z
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

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [medium] Manager/bot must never silently deadlock a command: `sst-manager` (+ `ssp-*` mirrors) must end every `--process-feedback`/`--process-command` run with exactly one outbound Telegram message -- a result OR a decision-request sent BEFORE ending (never deferred to "once you answer"), leaving the queue file pending for the reply; mirror `sst-executor` tier-2. Plus a `manager-bot.py` warning when a run exits 0 but left its queue file undrained with no send. -- SPEC Phase 53; user report 2026-06-25 (a `/feedback ssp-cm` did the work + prepared a push/extend decision but sent NO Telegram message and parked the questions, so the user was never asked).


