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

- 18.10 [medium] [should-fix] `bin/drive-chain.py` stale-recycle path now reads refcount via `_refcount_op(0)` under lock before calling `_stop_worker`; defers recycle with a stderr notice when count > 0, protecting concurrent drivers' refcount slots. — by skill-set-dev at 2026-05-02T06:45:12Z
- 18.9 [easy] [should-fix] `bin/drive-chain.py:_any_other_driver_using_persona` non-Linux guard changed `return False` → `return True` so the docstring's "don't stop the worker prematurely" intent matches the `if not ...` call site; docstring updated to "Returns True conservatively". — by skill-set-dev at 2026-05-02T06:45:12Z
- 18.8 [hard] [should-fix] `bin/drive-chain.py` simultaneous-driver refcount fix: `WORKER_REFCOUNT_FILE` (`manager-bot.refcount`) tracks active driver count; `_refcount_op` atomically ±1 under `WORKER_LOCK_FILE`; `_start_worker` writes count=1 inside its existing flock to avoid re-entrancy deadlock; adopting drivers increment via `_refcount_op(+1)`; session-end decrements and stops only when count→0; `_any_other_driver_using_persona` /proc scan catches stale counts from crashed drivers; `_stop_worker` now cleans both PID and refcount files. Validator clean. — by skill-set-dev at 2026-05-02T03:24:16Z
- 25.2 [hard] **`sst-manager --plan` mode**: added §Planner mode (α–θ) to `sst-manager` (v1.8.0→v1.9.0) — explicit `--plan` invocation OR auto-trigger from periodic mode §3 when `Next up` empty + SPEC fully checked across ≥1 prior tick (cursor-tracked via `manager-cursors.json[<project>].planner.queue_empty_since_tick`); β re-entry guard (one outstanding `[unconfirmed:*]` batch at a time, discoverable via `<!-- planner-id: -->` marker); γ ranking by gap-magnitude × gap-age across open `[ ]` measurable bullets; δ candidate format `- [unconfirmed:<id>] [<tier>] ... <!-- planner: <utc> --> <!-- planner-id: <id> -->`; ε cursor persistence; ζ Telegram announcement (consolidated with periodic digest on auto-trigger); §Hard rules tightened with two new bullets (never propose while batch outstanding, never invent prose-only objective candidates). Mode dispatch hoisted to §0.1 covering all three modes; §Score-against-objectives §4 enriched with gap-magnitude/gap-age axes; forward-references to "the planner extension" replaced with concrete `§Planner mode` cross-refs. Proprietary mirror `skill-set-manager` v1.4.0→v1.5.0 with `transferable-version: ">=1.9.0"` adds a Cadence paragraph naming the auto-trigger conditions against this single-project repo. Inline sanitize judgment on the transferable touch: must-fix=0, should-fix=0, nit=0 (two `Phase NN` internal-number leaks stripped from new prose during the cycle; banned-terms scan zero hits). Validator clean (25 skills + 7 chains; 5 proprietary skills + 2 proprietary chains). — by skill-set-dev at 2026-05-02T03:03:36Z
- [supervisor] [medium] archived fully-closed SPEC phases (1–7, 9–13, 15–16, 21, 26) to docs/SPEC-archive.md; SPEC.md reduced from 31,844 tokens to ~23,900 tokens (fits single Read call). Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-02T02:34:19Z
- 25.5 [easy] [should-fix] `objectives.md:cycles-clean check` glob extended to cover root-level `supervisor_verdict.md` (single-iter runs write verdict at run root, not `iter_*/`); both glob forms now unioned in the `ls -dt` call. SPEC 25.5 `[ ]` → `[x]`. Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-02T02:08:55Z
- 25.4 [medium] [should-fix] `objectives.md:cycles-clean check` rewritten from broken `grep -c '^Outcome.*escalate'` (always returns 0) to self-contained awk that skips the `## Outcome` header + blank line and prints 1/0 for escalate/clean; no-file edge handled via `${f:-/dev/null}`; SPEC 25.4 `[ ]` → `[x]`. Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-02T01:39:56Z
- 25.3 [easy] [should-fix] `sst-manager` SKILL.md:81 dangling §Planner mode reference replaced with capability prose; inline sanitize must-fix=0. Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-01T06:29:15Z
- 25.1 [hard] **measurable objectives schema**: rewrote `.claude/skills/skill-set-manager/objectives.md` "single goal" criteria as scored bullets (`slug:` + `check:` + `target:` + `since:` continuation block); shell-check + `count(<glob>) <op> <value>` metric-check forms; added `templates/objectives.md` sample for consuming projects; `sst-manager` v1.7.2→v1.8.0 added §Score-against-objectives explaining schema parsing + check evaluation + gap computation, plus updated §3 Toggle-objectives to branch on scored-vs-prose-only bullets; `skill-set-manager` v1.3.1→v1.4.0 with `transferable-version: ">=1.8.0"`. Phase 25.2 `--plan` mode is now unblocked and stays the next pick. Inline sanitize: must-fix=0 (two phase-number citations stripped from new transferable prose during the cycle). Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-01T05:49:56Z
- 26.5+26.6 [easy] `bin/validate-frontmatter.py` uppercase-`[X]` bypass fixed (`[ x]` → `[ xX]` in both `_SPEC_BULLET_ID_RE` + `_SPEC_CHECKBOX_RE`); `sst-dev-review` v1.4.8→v1.4.9 + `skill-set-dev-review` v1.2.7→v1.2.8 §4 TODO template now embeds `<spec-ID>` leading token so `remove <ID>` purge can match review-generated Next-up entries. Inline sanitize: must-fix=0. Validator clean (25 skills + 7 chains). — by skill-set-dev at 2026-05-01T05:30:53Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [easy] Phase 24 sub-item: end-to-end acceptance test of the four `/feedback` outcomes (concrete change → TODO Next-up; shape-ish → manager-notes.md; refuse → Telegram explanation; ambiguous → clarifying question) plus crash-recovery via the chain-runner pre-iter drain fallback. Reason: spec Phase 24 acceptance item; sub-items 3+4 shipped this cycle, so the acceptance test is now unblocked.
- [medium] Phase 23 acceptance: invoke `/sst-wiki-curator scaffold <test-path> --variant minimal` against a throwaway dir and confirm directory tree, schema-spec self-containment, `INIT` log line, git-init + first commit; then `/sst-wiki-curator ingest <test-path> <test-source-md>` and confirm raw drop, paper page with full front matter, topic page(s) created/updated, `index.md` updated, `INGEST` log line, one-commit close. Reason: spec Phase 23 acceptance item.
- [medium] Phase 18 `acceptance check on chain-bound worker lifecycle`. Reason: spec Phase 18 item 5; the implementation landed this cycle (item 4 `[x]`) but acceptance requires a real `/skill-set-chain-driver` round-trip with Telegram. Confirm: (a) chain driver starts the `skill-set-bot` tmux session at session-start and the user can `/ping → pong` during the run; (b) chain driver kills the tmux session at session-end; (c) re-run with the worker pre-started by hand (e.g. `tmux new-session -d -s skill-set-bot ...`): chain driver detects the pre-existing worker, does NOT start a second one, does NOT kill it at session-end; (d) two simultaneous chain-driver runs against different chains: only one tries to start the worker (flock); (e) manager invocation while no chain is running succeeds with an empty inbound queue and a digest body that does NOT re-notify any currently-paused job.
- [easy] Phase 17 `acceptance check on empty-queue bail`. Reason: spec Phase 17 item 4; the steady-state run requires `Next up` empty AND every SPEC `[ ]` flipped `[x]` (this cycle didn't reach that state, so item 4 stayed `[ ]`). When the queue eventually empties, invoke `/skill-set-chain-driver` and confirm: (a) `skill-set-dev` exits 0 with `[no-work] ...` printed and no commit; (b) chain runner aborts the loop after the first empty iter (no second iter starts; `MANIFEST.loop.terminated_by == "no_work_bail"`); (c) iter MANIFEST records `no_work_bail` with the sentinel line; (d) cumulative cost is bounded by the dev skill's pre-flight reads (~$0.10-0.30) rather than a full ~$8 iter; (e) chain-driver session-end Telegram body labels the stop "no-work bail".
- [medium] Phase 14 `Acceptance check: kill -TERM mid-supervisor + verify self-heal`. Reason: spec Phase 14 close item; one combined acceptance test for the four Phase 14 mechanisms above.
- [medium] Phase 20 `goose-cerebras harness` (deferred). Reason: spec Phase 20 (deferred behind Phase 19); the per-skill model-tier work in Phase 19 delivers the bulk of the 24/7-productivity throughput win within the existing Max subscription, so this becomes a future supplement for free-tier capacity rather than the primary fix. Re-pick when Phase 19 acceptance ships and a real cost / throughput baseline shows Phase 19's win is insufficient AND mechanical-skill work has been cleanly identified for offload to Cerebras. Architecture as in spec: `GooseCerebrasHarness` subclass + `bin/goose-shim.py` translating Goose's stream-json event vocabulary to Claude Code's shape + per-skill `allowed-harnesses:` anti-fork guard.
- [medium] Phase 8.6 end-to-end smoke: chain `sst-web-research → sst-editorial-pass → sst-social-promoter` against a real consuming project with clean supervisor verdict. Reason: spec Phase 8 tail item, Phase 8.1-8.5 lifts already complete.
