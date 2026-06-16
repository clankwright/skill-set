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

- 44.1+44.2+44.3+44.4 Phase 44 close: standalone `--phase`/`--todos` mode in sst-tester (SKILL.md v1.0.0→1.1.0; two-modes dispatch D1, scope resolution D2, iterate-all D3, out-of-tree findings D4); test_phase44.py 15 tests + 2 fixtures pin D2 resolution; mirror into ssp-cm-tester (base-version→1.1.0, CM phase->spec map; check-ssp-sync clean); README+CLAUDE invocation docs; relax test_phase41 version pin to major-1 semver; 379→394 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-16T21:55:00Z
- 42.10: move mkdir below dry-run continue in run_batch_mode(), add no-dir-creation test; 378→379 green — by sst-dev-cycle at 2026-06-16T21:10:00Z
- 42.4+42.5+42.6+42.7: --batch mode in skill-chain.py, drive-chain.py shim, caller migration + tests; 364→378 green — by sst-dev-cycle at 2026-06-16T20:30:00Z
- 42.9 add integration test: profile-sourced budget satisfies --overnight cap requirement (no CLI cap + profile fills → no SystemExit, loop=0); 363→364 green — by sst-dev-cycle at 2026-06-16T19:05:00Z
- 42.8+42.3 extract `_apply_profile_defaults` pure helper (5 tests: all-fields/explicit-wins/explicit-loop-suppresses-max-cycles) + add `--overnight`/`--preset overnight` preset (`_apply_preset`, `PRESETS` dict, cap check, `--loop` mutual exclusion, 8 tests); 350→363 green — by sst-dev-cycle at 2026-06-16T18:00:00Z
- 42.1+42.2 unify the chain-run CLI: merge drive-chain.py's wrapper layer natively into bin/skill-chain.py — six inert-when-unset flags (--profile/--max-budget-usd/--max-cycles/--telegram-env/--no-telegram/--label), profile defaults below CLI args, opt-in Telegram (4 event classes incl. real-time pause/resume via a notify callback), pure `_wrapper_halt_reason` budget/cycle/escalation halt, `UNIFIED_CLI_EPILOG` flag-mapping in --help; 23 new tests (tests/test_phase42.py), 327→350 green — by sst-dev-cycle at 2026-06-16T16:45:00Z
- 41.7+41.8 Phase 41 close: 16 hygiene/tooling tests (git-status-porcelain, finally/trap teardown, port-free, out-of-tree artifacts, install-skills lists sst-tester, check-ssp-sync clean); README chain descriptions + floor table + worked example updated for dev→tester→review; CLAUDE.md updated; 311→327 green — by sst-dev-cycle at 2026-06-16T15:30:00Z
- reconcile ssp-cm-supervisor base-version pin (2.1.0→2.2.0): reviewed wrapper against 39.1 finding-aware-abort change (§0.5.3 not overridden, reconcile is mechanical); check-ssp-sync clean for all 6 CM wrappers; 311→311 green — by sst-dev-cycle at 2026-06-16T14:10:00Z
- 41.5+41.6 CM tester rollout: author `ssp-cm-tester` wrapper (CM ports 5003/3000, `web/e2e` spec map, `.auth/state.json` 36h reuse, full teardown, never push/main/test/dev1), insert it into `cm-cycle.yaml` (dev → tester → review, v1.2.0), mirror the tester-findings read into `ssp-cm-dev-review` + the guidance/`[skip-tester]` branch into `ssp-cm-dev`, reconcile both wrappers' base-version pins (dev→1.9.0, review→1.11.0); CM `.claude/` is gitignored runtime state so deliverables persist on disk (no CM commit); validate-frontmatter + schema + check-ssp-sync (3 wrappers in-sync) all clean; skill-set suite 311→311 green; FUTURE-WORK acceptance filed — by sst-dev-cycle at 2026-06-16T13:30:00Z
- 41.11 fix incomplete-cycle recovery message: use first non-tester non-supervisor follower; 1 new test, 310→311 green — by sst-dev-cycle at 2026-06-16T12:00:00Z
## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->


- [medium] 46.1+46.2 remove the Phase 42 deprecation shims — delete `bin/drive-chain.py` + `bin/skill-batch.py`, remove/repoint their tests (`test_drive_chain_telegram.py`, shim cases in `test_phase42.py`), scrub remaining refs from `sst-chain-driver` (sanitize-gated) + `notify-telegram.sh` + `skill-chain.py` (leave SPEC-DONE historical text); unified `skill-chain.py` is the only entrypoint — user request 2026-06-16 (spec Phase 46)
