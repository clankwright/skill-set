# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

<!-- nothing in flight -->

## Just shipped (last cycle)

- Phase 58.7: `Harness.apply_budget_constraints` no-op + `CursorHarness` override (loud-skip `--max-budget-usd`); removed module-level `_maybe_clear_cursor_budget` name-branch — by ssp-dev at 2026-07-14T00:43:52Z
- Default loop-delay is none: runner no longer injects DEFAULT_LOOP_DELAY_RANDOM when unset; `dev-cycle-with-review-looped` uses `loop-delay: 0` (overnight / `--overnight` keep 5-30min jitter) — by manual at 2026-07-14T00:39:51Z
- Phase 58.6: inject proxied `num_turns` when Cursor result emits null (not only when key absent) so summary prints "N turns" not "None turns"; regression test with explicit null key (25→26) — by ssp-dev at 2026-07-14T00:37:35Z
- Phase 58.5: Cursor telemetry gap closed — `usage`→`modelUsage` (cache key rename); `num_turns` proxy from assistant frames; `--max-budget-usd` loud-skipped under `--harness cursor` (prefer `--max-cycles`); overnight/infinite without cycles SystemExits after clear. 8 new tests (17→25); 614→622 green; README Cursor notes updated — by ssp-dev at 2026-07-14T00:30:13Z
- CLAUDE.md low-bandwidth rule: briefly note completed items (was "do not report routine successes") so the user can see work was not overlooked — by manual (stash pop from Phase 58 park) at 2026-07-14T00:23:00Z
- Phase 58 (58.1-58.4): Cursor harness finalization — live stream-json fixture (`tests/fixtures/cursor-stream-sample.jsonl`); `_cursor_tool_call_fields` maps live `editToolCall`/`readToolCall`/`shellToolCall` (path→file_path) so Phase 49 wrote_tester_guidance works; 17 unit tests in `test_cursor_harness.py`; README documents `--harness cursor` + CURSOR_MODEL ids (also lands dirty Phase 57 fable-off-by-default paragraph). Grok default already `cursor-grok-4.5-high` (33ea3f0), confirmed live. Telemetry gap (no cost/num_turns; usage tokens present) left on Next up — by ssp-dev at 2026-07-14T00:13:08Z
- Phase 55 (55.1-55.4): a skill failure no longer kills the chain. (1) dev-cycle model floor sonnet->opus so the lead agent finishes in-budget (sst-dev-cycle v1.15.0 + rationale note; ssp-cm-dev base 1.15.0/ver 1.14.0; ssp-dahrouge-dev base 1.15.0/ver 1.3.5). (2) bin/skill-chain.py run_iteration FLAGS a non-zero non-supervisor exit as a top-level skill_failure {skill,exit_code,failure_kind,num_turns}, skips the remaining intermediate skills, and hands off to the auto-supervisor for graceful resolution; rc stays 0 so the loop continues; rate-limit/overload aborts stay HARD stops; new _classify_skill_failure (error_max_turns->turn_limit_exhausted). (3) main() consecutive-failure backstop SKILL_FAILURE_BACKSTOP=2 -> terminated_by skill_failure_backstop + per-iter Telegram SKILL FAILURE line. (4) sst-supervisor §1a "Skill-failure graceful resolution" (v2.8.0): diagnose, re-home/split the offending item, surface (never mutate) partial work, escalate; mirrored into ssp-cm-supervisor (base 2.8.0/ver 2.2.7) + ssp-dahrouge-supervisor (base 2.8.0/ver 2.1.7). (5) [55.5] fixed the skill-set-validator-clean objective: validate-frontmatter.py now WALKS a directory arg (was crashing IsADirectoryError on `skills/ chains/`, swallowed by the objective's grep -> spuriously green), and objectives.md switched to the exit-code form. 5 new tests in test_skill_chain.py + 2 in test_validate.py; 590->597 green; validate-frontmatter clean; check-ssp-sync OK all 3 roots; sanitize must-fix 0 pending at push -- by manual completion (live session) at 2026-06-26T05:28:45Z
- Post-Phase-54 ssp reconcile + objectives fix: reconciled ALL ssp-* wrappers across ~/Dev to current base versions (cm + dahrouge dev/dev-review/manager/supervisor + ssp-manager) and refreshed the stale ~/.claude/skills runtime copies (4 transferables reinstalled, 2 installed manager wrappers synced); bumped the two pre-existing stale wrappers ssp-cm-chain-driver (base 1.3.0->1.4.0) and ssp-dahrouge-tester (base 1.6.0->1.8.0), both config-only re their base changes; fixed ssp-manager objectives.md skill-set-tests-passing check to call ~/.local/bin/pytest (was python3 -m pytest, a false-fail since system python3 is 3.10 but pytest is 3.11 at ~/.local/bin); check-ssp-sync clean from all 3 roots -- by manual completion (live session) at 2026-06-25T23:46:46Z
- Phase 54 (54.1+54.2+54.3+54.4): consolidate HUMAN.md to the oversight layer -- revoke read/write from sst-dev-cycle (v1.14.0) + sst-dev-review (v1.13.0); RE-HOME the phase-completion branch-setup handoff to sst-supervisor (§5b.1, v2.7.0) and the blocked-item pick-gating to sst-manager (§3b, v2.4.0); mirror into ssp-cm-dev (base 1.14.0) + ssp-cm-dev-review (base 1.13.0); SPEC "Handoff docs" + README carry the invariant; reconciled ssp-manager base-version 2.3.0->2.4.0; 26 new tests in test_phase54.py; 564->590 green; validate-frontmatter clean; transferables sanitize-clean -- by manual completion (live session) at 2026-06-25T12:11:54Z (orphaned cycle 2026-06-25T09-17-14Z continued from its failing test file)
- Phase 53 (53.1+53.2): sst-manager always-reply hard rule (v2.2.0->v2.3.0) + manager-bot.py deadlock-watcher; 17 new tests; 547->564 green — by sst-dev-cycle at 2026-06-25T05:00:00Z

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

<!-- Phase 42 `--overnight` preset (loop:0 + loop-delay-random + cap) makes dedicated overnight chain YAMLs redundant. -->
- [easy] Remove redundant overnight chain YAMLs (`chains/dev-cycle-overnight.yaml` + proprietary `.claude/chains/skill-set-overnight.yaml`); use `--overnight` / `--preset overnight` on the looped (or single) cycle chain instead; update README/CLAUDE.md/tests that reference the overnight YAML — source: user request 2026-07-14

<!-- Cursor capability gaps surfaced by harness dogfood runs 2026-07-14 (00-10-28Z + 00-27-32Z). Highest-impact first. -->
- [medium] Build a Cursor-harness-only Brave web-search + page-fetch tool: free Brave API key first, on rate-limit fall back to paid key; cover both WebSearch and WebFetch substitutes; wire under `--harness cursor` only (Claude Code keeps native tools) — source: user request 2026-07-14 + run analysis (research skills need fetch too)
- [hard] Cursor has no Skill tool — nested `/sst-sanitize-transferable` (and other sub-skill) invocations from inlined skill prose cannot run; add a Cursor path (runner-spawned nested skill inline, or harness-aware prose: Read SKILL.md + follow) so transferable-editing cycles under `--harness cursor` still pass the sanitize gate — source: run analysis 2026-07-14 (Phase 58.5 skipped sanitize only because no transferable; next transferable cycle will hit this)
- [medium] CursorHarness.build_command: pass `--approve-mcps` and `--trust` (cursor-agent headless flags) alongside `--force` so Playwright/MCP skills do not stall on approval prompts in `-p` mode — source: run analysis 2026-07-14 (`cursor-agent --help`; harness currently only passes `--force`)
- [medium] Cursor has no `--max-turns` hard backstop (soft wind-down is tester-only / advisory); add a runner-side turn/watchdog (count assistant frames, kill or wind-down after N) under `--harness cursor` — source: run analysis 2026-07-14 (documented gap; runaway risk)

<!-- planner candidate tests-passing-fix (2026-06-25) resolved: the objectives.md pytest-path fix was applied directly in a live session; candidate removed, no dev-cycle pick needed. -->
