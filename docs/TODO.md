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

- 27 [medium] FUTURE-WORK.md contract: 4 transferables (sst-dev-cycle v1.4.4, sst-dev-review v1.5.0, sst-supervisor v1.11.0, sst-manager v1.10.0) + 4 proprietary mirrors + templates/FUTURE-WORK.md (new) + templates/SPEC.md + CLAUDE.md updated; inline sanitize verdict must-fix=0 — by skill-set-dev at 2026-05-02T14:31:10Z
- 23.4 [easy] [should-fix] `sst-wiki-curator/SKILL.md` retroactive `sst-sanitize-transferable` run: must-fix=0, should-fix=0, nit=1 (Karpathy citation retained); audit trail closed — by skill-set-dev at 2026-05-02T13:03:36Z
- 18.11 [hard] [should-fix] `bin/drive-chain.py` stale-recycle TOCTOU closed: new `_recycle_stale_worker_if_unused(descriptor)` helper holds `WORKER_LOCK_FILE` across refcount-read + tmux-kill + state-file unlinks; `main()` stale-recycle branch calls it in place of the prior `_refcount_op(0)` + `_stop_worker` pair (which released the lock between check and stop, letting a concurrent `_start_worker` write count=1 and launch a fresh persona-named session that the deferred kill would destroy). Returns `(True, 0)` when recycled, `(False, count)` when deferred. Smoke-tested four refcount states (no file, count=0 explicit, count=1, count=2) against a tmp state dir. Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-02T07:45:55Z
- 23.2 [medium] sst-wiki-curator acceptance passed: scaffold (a–d) + ingest (e–j) all confirmed against a throwaway dir; B.9 commit-gate prose fixed (v1.0.0→v1.0.1) after first ingest run skipped the commit step. — by skill-set-dev at 2026-05-02T07:22:27Z
- 18.10 [medium] [should-fix] `bin/drive-chain.py` stale-recycle path now reads refcount via `_refcount_op(0)` under lock before calling `_stop_worker`; defers recycle with a stderr notice when count > 0, protecting concurrent drivers' refcount slots. — by skill-set-dev at 2026-05-02T06:45:12Z
- 18.9 [easy] [should-fix] `bin/drive-chain.py:_any_other_driver_using_persona` non-Linux guard changed `return False` → `return True` so the docstring's "don't stop the worker prematurely" intent matches the `if not ...` call site; docstring updated to "Returns True conservatively". — by skill-set-dev at 2026-05-02T06:45:12Z
- 18.8 [hard] [should-fix] `bin/drive-chain.py` simultaneous-driver refcount fix: `WORKER_REFCOUNT_FILE` (`manager-bot.refcount`) tracks active driver count; `_refcount_op` atomically ±1 under `WORKER_LOCK_FILE`; `_start_worker` writes count=1 inside its existing flock to avoid re-entrancy deadlock; adopting drivers increment via `_refcount_op(+1)`; session-end decrements and stops only when count→0; `_any_other_driver_using_persona` /proc scan catches stale counts from crashed drivers; `_stop_worker` now cleans both PID and refcount files. Validator clean. — by skill-set-dev at 2026-05-02T03:24:16Z
- 25.2 [hard] **`sst-manager --plan` mode**: added §Planner mode (α–θ) to `sst-manager` (v1.8.0→v1.9.0) — explicit `--plan` invocation OR auto-trigger from periodic mode §3 when `Next up` empty + SPEC fully checked across ≥1 prior tick (cursor-tracked via `manager-cursors.json[<project>].planner.queue_empty_since_tick`); β re-entry guard (one outstanding `[unconfirmed:*]` batch at a time, discoverable via `<!-- planner-id: -->` marker); γ ranking by gap-magnitude × gap-age across open `[ ]` measurable bullets; δ candidate format `- [unconfirmed:<id>] [<tier>] ... <!-- planner: <utc> --> <!-- planner-id: <id> -->`; ε cursor persistence; ζ Telegram announcement (consolidated with periodic digest on auto-trigger); §Hard rules tightened with two new bullets (never propose while batch outstanding, never invent prose-only objective candidates). Mode dispatch hoisted to §0.1 covering all three modes; §Score-against-objectives §4 enriched with gap-magnitude/gap-age axes; forward-references to "the planner extension" replaced with concrete `§Planner mode` cross-refs. Proprietary mirror `skill-set-manager` v1.4.0→v1.5.0 with `transferable-version: ">=1.9.0"` adds a Cadence paragraph naming the auto-trigger conditions against this single-project repo. Inline sanitize judgment on the transferable touch: must-fix=0, should-fix=0, nit=0 (two `Phase NN` internal-number leaks stripped from new prose during the cycle; banned-terms scan zero hits). Validator clean (25 skills + 7 chains; 5 proprietary skills + 2 proprietary chains). — by skill-set-dev at 2026-05-02T03:03:36Z
- [supervisor] [medium] archived fully-closed SPEC phases (1–7, 9–13, 15–16, 21, 26) to docs/SPEC-archive.md; SPEC.md reduced from 31,844 tokens to ~23,900 tokens (fits single Read call). Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-02T02:34:19Z
- 25.5 [easy] [should-fix] `objectives.md:cycles-clean check` glob extended to cover root-level `supervisor_verdict.md` (single-iter runs write verdict at run root, not `iter_*/`); both glob forms now unioned in the `ls -dt` call. SPEC 25.5 `[ ]` → `[x]`. Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-02T02:08:55Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [easy] [should-fix] 27.8 `skills/dev/sst-dev-review/SKILL.md:§5` — §5 git add not updated for FUTURE-WORK.md; findings routed there by §4 are silently unstaged — review of f915596
- [medium] [should-fix] 27.9 `skills/dev/sst-dev-cycle/SKILL.md` — inline sanitize reused in Phase 27 despite 23.4 proposing formal requirement; sanitize-gate rule never added to dev contract — review of f915596

