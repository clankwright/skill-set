# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight


## Just shipped (last cycle)

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

- 42.4+42.5+42.6+42.7: --batch mode in skill-chain.py, drive-chain.py shim, caller migration + tests; 364→378 green — by sst-dev-cycle at 2026-06-16T20:30:00Z
- 42.9 add integration test: profile-sourced budget satisfies --overnight cap requirement (no CLI cap + profile fills → no SystemExit, loop=0); 363→364 green — by sst-dev-cycle at 2026-06-16T19:05:00Z
- 42.8+42.3 extract `_apply_profile_defaults` pure helper (5 tests: all-fields/explicit-wins/explicit-loop-suppresses-max-cycles) + add `--overnight`/`--preset overnight` preset (`_apply_preset`, `PRESETS` dict, cap check, `--loop` mutual exclusion, 8 tests); 350→363 green — by sst-dev-cycle at 2026-06-16T18:00:00Z
- 42.1+42.2 unify the chain-run CLI: merge drive-chain.py's wrapper layer natively into bin/skill-chain.py — six inert-when-unset flags (--profile/--max-budget-usd/--max-cycles/--telegram-env/--no-telegram/--label), profile defaults below CLI args, opt-in Telegram (4 event classes incl. real-time pause/resume via a notify callback), pure `_wrapper_halt_reason` budget/cycle/escalation halt, `UNIFIED_CLI_EPILOG` flag-mapping in --help; 23 new tests (tests/test_phase42.py), 327→350 green — by sst-dev-cycle at 2026-06-16T16:45:00Z
- 41.7+41.8 Phase 41 close: 16 hygiene/tooling tests (git-status-porcelain, finally/trap teardown, port-free, out-of-tree artifacts, install-skills lists sst-tester, check-ssp-sync clean); README chain descriptions + floor table + worked example updated for dev→tester→review; CLAUDE.md updated; 311→327 green — by sst-dev-cycle at 2026-06-16T15:30:00Z
- reconcile ssp-cm-supervisor base-version pin (2.1.0→2.2.0): reviewed wrapper against 39.1 finding-aware-abort change (§0.5.3 not overridden, reconcile is mechanical); check-ssp-sync clean for all 6 CM wrappers; 311→311 green — by sst-dev-cycle at 2026-06-16T14:10:00Z
- 41.5+41.6 CM tester rollout: author `ssp-cm-tester` wrapper (CM ports 5003/3000, `web/e2e` spec map, `.auth/state.json` 36h reuse, full teardown, never push/main/test/dev1), insert it into `cm-cycle.yaml` (dev → tester → review, v1.2.0), mirror the tester-findings read into `ssp-cm-dev-review` + the guidance/`[skip-tester]` branch into `ssp-cm-dev`, reconcile both wrappers' base-version pins (dev→1.9.0, review→1.11.0); CM `.claude/` is gitignored runtime state so deliverables persist on disk (no CM commit); validate-frontmatter + schema + check-ssp-sync (3 wrappers in-sync) all clean; skill-set suite 311→311 green; FUTURE-WORK acceptance filed — by sst-dev-cycle at 2026-06-16T13:30:00Z
- 41.11 fix incomplete-cycle recovery message: use first non-tester non-supervisor follower; 1 new test, 310→311 green — by sst-dev-cycle at 2026-06-16T12:00:00Z
- 41.3+41.4+41.9+41.10 reviewer consumes tester findings, insert sst-tester into framework chains, dev writes tester-guidance.md / [skip-tester], runner honors skip; 24 new tests, 286→310 green; sanitize must-fix=0 on both transferables — by sst-dev-cycle at 2026-06-16T11:00:00Z
- 41.1+41.2 author the `sst-tester` transferable (`skills/framework/sst-tester/SKILL.md`, v1.0.0, model-floor sonnet / effort-floor high) — chain position (dev → tester → review), authority envelope (D5: never commit/deploy/edit-tree), run lifecycle (read `tester-guidance.md` + derive what-changed from `git show HEAD` / `## Just shipped` / flipped SPEC `[x]` → self-skip → start stack → poll readiness w/ timeout → drive surfaces → collect → teardown → write findings), degrade-don't-hang (D2) + self-skip (D4/D7 `verdict: skipped`), headed/headless (D2), out-of-tree artifacts (D3, `~/.claude/state/sst-tester/<utc>/`); + the tester→reviewer findings contract (`tester-findings.{md,json}` schema: per-check `{area, change_ref, status: pass|fail|needs-change, evidence, recommendation}` + overall `verdict: green|red|degraded|skipped` + one-line summary), sample fixture `tests/fixtures/tester-findings.json`, 19 new tests (`tests/test_phase41.py`); 267→286 green; sanitize must-fix=0; validator clean — by sst-dev-cycle at 2026-06-16T08:20:00Z
## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->


- [easy] [should-fix] 42.10 `bin/skill-chain.py:2301` — mkdir before dry-run check in run_batch_mode() creates output dirs as side effect; move mkdir below dry-run continue, add test — review of 22a19c5
- [hard] 44.1+44.2 add a standalone terminal-invocable `sst-tester` mode (`--phase <id>` / `--todos <ref...>`) that resolves + iteratively exercises ALL UI/UX a phase or set of completed todos introduced (iterate-all/collect-all, out-of-tree findings) — distinct from the in-chain last-diff mode; user request 2026-06-16 (spec Phase 44)
- [medium] 44.3+44.4 mirror the standalone mode into `ssp-cm-tester` (CM phase->`web/e2e` spec map) + document the terminal invocation in `README.md`/`CLAUDE.md` — spec Phase 44; depends on 44.1/44.2
