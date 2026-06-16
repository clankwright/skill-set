# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

<!--
  Exactly one line per currently-running skill, format:
  - [<skill-name> @ <utc-iso>] <one-line: what this skill is currently doing>
  Rewrite (don't append) as the focus narrows. Empty when no skill is running.
-->
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

- 41.7+41.8 Phase 41 close: 16 hygiene/tooling tests (git-status-porcelain, finally/trap teardown, port-free, out-of-tree artifacts, install-skills lists sst-tester, check-ssp-sync clean); README chain descriptions + floor table + worked example updated for dev→tester→review; CLAUDE.md updated; 311→327 green — by sst-dev-cycle at 2026-06-16T15:30:00Z
- reconcile ssp-cm-supervisor base-version pin (2.1.0→2.2.0): reviewed wrapper against 39.1 finding-aware-abort change (§0.5.3 not overridden, reconcile is mechanical); check-ssp-sync clean for all 6 CM wrappers; 311→311 green — by sst-dev-cycle at 2026-06-16T14:10:00Z
- 41.5+41.6 CM tester rollout: author `ssp-cm-tester` wrapper (CM ports 5003/3000, `web/e2e` spec map, `.auth/state.json` 36h reuse, full teardown, never push/main/test/dev1), insert it into `cm-cycle.yaml` (dev → tester → review, v1.2.0), mirror the tester-findings read into `ssp-cm-dev-review` + the guidance/`[skip-tester]` branch into `ssp-cm-dev`, reconcile both wrappers' base-version pins (dev→1.9.0, review→1.11.0); CM `.claude/` is gitignored runtime state so deliverables persist on disk (no CM commit); validate-frontmatter + schema + check-ssp-sync (3 wrappers in-sync) all clean; skill-set suite 311→311 green; FUTURE-WORK acceptance filed — by sst-dev-cycle at 2026-06-16T13:30:00Z
- 41.11 fix incomplete-cycle recovery message: use first non-tester non-supervisor follower; 1 new test, 310→311 green — by sst-dev-cycle at 2026-06-16T12:00:00Z
- 41.3+41.4+41.9+41.10 reviewer consumes tester findings, insert sst-tester into framework chains, dev writes tester-guidance.md / [skip-tester], runner honors skip; 24 new tests, 286→310 green; sanitize must-fix=0 on both transferables — by sst-dev-cycle at 2026-06-16T11:00:00Z
- 41.1+41.2 author the `sst-tester` transferable (`skills/framework/sst-tester/SKILL.md`, v1.0.0, model-floor sonnet / effort-floor high) — chain position (dev → tester → review), authority envelope (D5: never commit/deploy/edit-tree), run lifecycle (read `tester-guidance.md` + derive what-changed from `git show HEAD` / `## Just shipped` / flipped SPEC `[x]` → self-skip → start stack → poll readiness w/ timeout → drive surfaces → collect → teardown → write findings), degrade-don't-hang (D2) + self-skip (D4/D7 `verdict: skipped`), headed/headless (D2), out-of-tree artifacts (D3, `~/.claude/state/sst-tester/<utc>/`); + the tester→reviewer findings contract (`tester-findings.{md,json}` schema: per-check `{area, change_ref, status: pass|fail|needs-change, evidence, recommendation}` + overall `verdict: green|red|degraded|skipped` + one-line summary), sample fixture `tests/fixtures/tester-findings.json`, 19 new tests (`tests/test_phase41.py`); 267→286 green; sanitize must-fix=0; validator clean — by sst-dev-cycle at 2026-06-16T08:20:00Z
- 43.7 rewrite stale `main()` contract-violation comment to reference `_incomplete_cycle_detected` (not HEAD-advance proxy); 267→267 green — by sst-dev-cycle at 2026-06-16T07:15:00Z
- 43.6 `_contract_violation_aborts` fix: replace SHA proxy with `_incomplete_cycle_detected(cwd)`; supervisor-only HEAD advance no longer masks failed review recovery; 2 new tests (masking regression + genuine recovery), 265→267 green — by sst-dev-cycle at 2026-06-16T06:30:00Z
- Phase 43 [hard batch, 43.1-43.5] close the sanitize→commit seam: relocate `sst-dev-cycle` sanitize gate into §3 step 5 (before §4 verify), rewrite §5 as "runs in §3" pointer + §7 "final action" framing (1.7.1→1.8.0); reorder `sst-dev-review §0.2` recovery so sanitize runs before staging + document the 5-signal recovery-first health predicate + recover-then-review order (1.9.0→1.10.0); relax `bin/skill-chain.py` `contract_violation` kill via `_contract_violation_aborts()` (follower-recovered HEAD-advance continues the loop); `tests/test_phase43.py` grep-guard + recovery-predicate + relaxed-kill (13 new, 252→265 green); sanitize must-fix=0 on both transferables; validator clean; Phase 43 migrated to SPEC-DONE.md — by sst-dev-cycle at 2026-06-16T01:15:00Z
- 39.3 sst-dev-review §0.2: widen recovery sanitize gate to sst-*/SKILL.md; version 1.8.0→1.9.0; 2 new tests, 250→252 green — by sst-dev-cycle at 2026-06-16T00:00:00Z
## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [hard] 42.1+42.2 spec the unified chain-run CLI + merge `drive-chain.py`'s wrapper (budget/`--max-cycles`/telegram/profile/label) natively into `bin/skill-chain.py` so all flags live in one parser (no more `-- ` forwarding) — collapse skill-chain/drive-chain/overnight/skill-batch into one entrypoint; user request 2026-06-15 (spec Phase 42)
- [medium] 42.3+42.4+42.5+42.6+42.7 `--overnight` preset + fold `skill-batch.py` into a `--batch` mode + `drive-chain.py`/`skill-batch.py` deprecation shims + migrate `*-chain-driver` skills/cron/docs to the single runner + unified-flag-matrix tests — spec Phase 42; depends on 42.1/42.2

- [hard] 44.1+44.2 add a standalone terminal-invocable `sst-tester` mode (`--phase <id>` / `--todos <ref...>`) that resolves + iteratively exercises ALL UI/UX a phase or set of completed todos introduced (iterate-all/collect-all, out-of-tree findings) — distinct from the in-chain last-diff mode; user request 2026-06-16 (spec Phase 44)
- [medium] 44.3+44.4 mirror the standalone mode into `ssp-cm-tester` (CM phase->`web/e2e` spec map) + document the terminal invocation in `README.md`/`CLAUDE.md` — spec Phase 44; depends on 44.1/44.2
