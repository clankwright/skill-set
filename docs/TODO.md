# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

<!-- nothing in flight -->

## Just shipped (last cycle)

- Phase 55 (55.1-55.4): a skill failure no longer kills the chain. (1) dev-cycle model floor sonnet->opus so the lead agent finishes in-budget (sst-dev-cycle v1.15.0 + rationale note; ssp-cm-dev base 1.15.0/ver 1.14.0; ssp-dahrouge-dev base 1.15.0/ver 1.3.5). (2) bin/skill-chain.py run_iteration FLAGS a non-zero non-supervisor exit as a top-level skill_failure {skill,exit_code,failure_kind,num_turns}, skips the remaining intermediate skills, and hands off to the auto-supervisor for graceful resolution; rc stays 0 so the loop continues; rate-limit/overload aborts stay HARD stops; new _classify_skill_failure (error_max_turns->turn_limit_exhausted). (3) main() consecutive-failure backstop SKILL_FAILURE_BACKSTOP=2 -> terminated_by skill_failure_backstop + per-iter Telegram SKILL FAILURE line. (4) sst-supervisor §1a "Skill-failure graceful resolution" (v2.8.0): diagnose, re-home/split the offending item, surface (never mutate) partial work, escalate; mirrored into ssp-cm-supervisor (base 2.8.0/ver 2.2.7) + ssp-dahrouge-supervisor (base 2.8.0/ver 2.1.7). (5) [55.5] fixed the skill-set-validator-clean objective: validate-frontmatter.py now WALKS a directory arg (was crashing IsADirectoryError on `skills/ chains/`, swallowed by the objective's grep -> spuriously green), and objectives.md switched to the exit-code form. 5 new tests in test_skill_chain.py + 2 in test_validate.py; 590->597 green; validate-frontmatter clean; check-ssp-sync OK all 3 roots; sanitize must-fix 0 pending at push -- by manual completion (live session) at 2026-06-26T05:28:45Z
- Post-Phase-54 ssp reconcile + objectives fix: reconciled ALL ssp-* wrappers across ~/Dev to current base versions (cm + dahrouge dev/dev-review/manager/supervisor + ssp-manager) and refreshed the stale ~/.claude/skills runtime copies (4 transferables reinstalled, 2 installed manager wrappers synced); bumped the two pre-existing stale wrappers ssp-cm-chain-driver (base 1.3.0->1.4.0) and ssp-dahrouge-tester (base 1.6.0->1.8.0), both config-only re their base changes; fixed ssp-manager objectives.md skill-set-tests-passing check to call ~/.local/bin/pytest (was python3 -m pytest, a false-fail since system python3 is 3.10 but pytest is 3.11 at ~/.local/bin); check-ssp-sync clean from all 3 roots -- by manual completion (live session) at 2026-06-25T23:46:46Z
- Phase 54 (54.1+54.2+54.3+54.4): consolidate HUMAN.md to the oversight layer -- revoke read/write from sst-dev-cycle (v1.14.0) + sst-dev-review (v1.13.0); RE-HOME the phase-completion branch-setup handoff to sst-supervisor (§5b.1, v2.7.0) and the blocked-item pick-gating to sst-manager (§3b, v2.4.0); mirror into ssp-cm-dev (base 1.14.0) + ssp-cm-dev-review (base 1.13.0); SPEC "Handoff docs" + README carry the invariant; reconciled ssp-manager base-version 2.3.0->2.4.0; 26 new tests in test_phase54.py; 564->590 green; validate-frontmatter clean; transferables sanitize-clean -- by manual completion (live session) at 2026-06-25T12:11:54Z (orphaned cycle 2026-06-25T09-17-14Z continued from its failing test file)
- Phase 53 (53.1+53.2): sst-manager always-reply hard rule (v2.2.0->v2.3.0) + manager-bot.py deadlock-watcher; 17 new tests; 547->564 green — by sst-dev-cycle at 2026-06-25T05:00:00Z
- Runner markdown-wrapped sentinel fix: relax PICKED_DIFFICULTY_SENTINEL_RE + BATCH_PICK_SENTINEL_RE with \W* tolerance; 5 new guard tests in test_skill_chain.py; 542->547 green — by sst-dev-cycle at 2026-06-25T03:30:00Z
- 52.1+52.2: add four anti-pattern RED-FLAGS to sst-tester + ssp-cm-tester mirror; add synthetic-data-masking note to sst-dev-cycle e2e guard — by sst-dev-cycle at 2026-06-25T02:00:00Z
- 51.4 fix sst-tester standalone blast-radius diff source (git show HEAD -> git log -p per file): SKILL.md step 6a mode-conditional note; 3 new tests; 527->530 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-25T01:00:00Z
- 51.1+51.2+51.3 Phase 51 close: sst-tester blast-radius mandate (FLOOR-not-ceiling, derive-from-diff, adjacent/integrated surfaces, All/none/many, record-gaps, budget reconciliation) v1.6.1->v1.7.0; ssp-cm-tester base-version 1.6.1->1.7.0 + §4b CM heuristics (merged-table scroll/virtualization, select-all partitions, all-clients aggregate, legend swatch match, report/credit sanity); README in-chain broadened coverage prose; 18 new tests; 509->527 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-25T00:15:00Z
- enforce escalate outcome-line leading-word convention in sst-supervisor §7 (v2.4.0->v2.4.1) + 2 guard tests in test_skill_chain.py; 507->509 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-24T11:10:00Z
- Items 1+3 from Next up: e2e blind-ship guard in sst-dev-cycle §6 (E2e-only guard prose + [needs-live-stack] path) + batch-pick non-emission formally accepted (Known model-behavior gap prose + batch_pick_missing documented); v1.11.0->v1.12.0; 6 new tests in test_dev_cycle_contracts.py; 501->507 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-24T10:00:00Z

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

<!-- Cursor harness finalization (source: user request 2026-07-14; initial CursorHarness landed on branch worktree-cursor-harness). Highest-impact/blocking first. -->
- [medium] Verify the Cursor live stream-json event shape against a real `cursor-agent -p --output-format stream-json` run (needs CURSOR_API_KEY) and confirm `CursorHarness.normalize_event` maps system/init, assistant/text, tool_call, and result correctly; save a sample run as a tests/fixtures/*.jsonl — source: harness shipped without a live capture (headless auth blocked)
- [medium] Confirm `_cursor_tool_call_fields` arg-key mapping (writeToolCall/readToolCall/function inner shapes, esp. the file-path key) against captured events; fix the `wrote_tester_guidance` "never both" detection if Cursor's path key differs from path/file_path/filePath — source: mapping is best-effort against partly-documented schema
- [medium] Close the Cursor telemetry gap: its result frame carries no cost/num_turns/usage, so manifest fields stay zero and `sst-chain-driver --max-budget-usd` can't meter a Cursor run — either derive from a usage frame if Cursor exposes one, or make the budget gate detect harness=="cursor" and skip/estimate with a loud note — source: known gap in initial harness
- [easy] Confirm the exact Grok model id `cursor-agent -m` accepts and set the CURSOR_MODEL default accordingly (currently "grok"); document the supported ids — source: default picked without live confirmation
- [easy] Add CursorHarness unit tests (build_command cold/resume/tester-winddown + normalize_event tool_call→tool_use + claude-code identity) to tests/ — source: only a manual smoke test ran at ship time
- [easy] Update README lines ~5/385 to reflect that the cursor harness is implemented (they still say only claude-code ships) — source: left untouched to avoid clobbering an in-flight uncommitted README edit

<!-- planner candidate tests-passing-fix (2026-06-25) resolved: the objectives.md pytest-path fix was applied directly in a live session; candidate removed, no dev-cycle pick needed. -->

