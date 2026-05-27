# skill-set FUTURE-WORK

Parking lot for items the framework is not actively working on this cycle:

- **Manual / human verification** — acceptance tests that need a real chain-driver round-trip with eyes on the output (Telegram, terminal, MANIFEST). The dev cycle skills cannot self-verify these from inside their own iteration.
- **Deferred work** — phases or sub-items consciously parked behind a prerequisite (e.g. a real cost baseline must land before the work is worth picking up).
- **Future items** — work the user wants to keep visible but not queued for the next cycle. A human flips entries back into `docs/TODO.md > Next up` (with the appropriate `[easy|medium|hard]` label) when ready to execute.

This file is **not picked from automatically.** The dev cycle's pick order is unchanged: `TODO.md > Next up` first, then the next unchecked item in `SPEC.md`. Entries here are surfaced only by humans (or by a human-invoked planner pass).

## Format

Mirror the SPEC item ID where one exists (the items below were moved out of `SPEC.md`; their phase numbers stay so the link is obvious). Group by section. One line per item; copy the original prose verbatim so it can be flipped back into `Next up` without re-authoring.

## Manual / human verification

### Phase 8.6 — end-to-end smoke

- [medium] End-to-end smoke: `sst-web-research → sst-editorial-pass → sst-social-promoter` chain with clean supervisor verdict against a real project.

### Phase 14.6 — kill -TERM mid-supervisor self-heal

- [medium] **Acceptance**: kill -TERM mid-supervisor + verify self-heal (one combined test for the four mechanisms shipped under Phase 14.1–14.5).

### Phase 18.5 — chain-bound worker lifecycle acceptance

- [medium] **Acceptance**: real `/skill-set-chain-driver` round-trip with Telegram. Confirm: (a) chain driver starts the `skill-set-bot` tmux session at session-start and the user can `/ping → pong` during the run; (b) chain driver kills the tmux session at session-end; (c) re-run with the worker pre-started by hand (e.g. `tmux new-session -d -s skill-set-bot ...`): chain driver detects the pre-existing worker, does NOT start a second one, does NOT kill it at session-end; (d) two simultaneous chain-driver runs against different chains: only one tries to start the worker (flock); (e) manager invocation while no chain is running succeeds with an empty inbound queue and a digest body that does NOT re-notify any currently-paused job.

### Phase 19.11 — model-tier routing acceptance

- [hard] **Acceptance**: a `/skill-set-chain-driver --loop 3` run with mixed-difficulty items (at least one `[easy]`, one `[medium]`, one `[hard]` across the three iters). Confirm: (a) per-iter MANIFEST records `difficulty` field; (b) per-skill `model_usage` block reflects the resolved model AND effort (Opus + xhigh for hard items + supervisor; Sonnet + medium for medium + reviews; Haiku + low where applicable); (c) cumulative quota burn per iter is ~25–35% of an all-Opus + all-xhigh baseline (target: ≥50% reduction); (d) supervisor still runs Opus + xhigh regardless of item difficulty (floor invariant on both axes); (e) chain-driver session-end Telegram body reports per-iter difficulty + model + effort breakdown.

### Phase 22.9 — batch-window acceptance

- [hard] **Acceptance**: `/skill-set-chain-driver --loop 3` run with mixed batch sizes. Confirm: (a) per-iter MANIFEST captures `[batch-pick]` block (or `batch_pick` sub-record) including N + difficulty + rationale + window-target; (b) at least one iter ships a multi-item batch when the queue offers candidates that fit the band; (c) supervisor verdict reports batch coherence (composition matches stated rationale); (d) review flags no unrelated lumping (#3) AND no over/under-sizing on a deliberately-sized batch (#5); (e) cycle's input-token usage falls within the stated band's tolerance for at least one multi-item iter (target: actuals in `[lower×0.8, upper×1.1]` of the window-target band); (f) at least one deliberately-undersized iter triggers a `[batch-sizing]` finding (negative test: confirms the axis fires); (g) over a follow-up `--loop 10+` run, the supervisor's refinement patches converge — observed via the trailing-window finding rate dropping toward zero (stable-termination signal in #7).

### Phase 24.6 — `/feedback` four-outcome acceptance

- [easy] **Acceptance**: `/feedback <concrete change>` mid-run → new `Next up` item in `docs/TODO.md` within ~60s + Telegram reply names file/section; `/feedback <shape-ish>` → entry in `manager-notes.md` with manager reasoning paragraph; `/feedback "skip sanitize on next transferable write"` → refuse-with-explanation Telegram reply, no file changes; `/feedback <ambiguous>` → clarifying question Telegram reply, queue file stays unprocessed; crash on-demand spawn → next manager cron tick or chain-runner pre-hook processes queue file as fallback, idempotent via `<!-- src: <basename> -->` marker.

### Phase 38.3+38.4+38.5 — phase-completion bail + handoff + stuck-item detection acceptance

- [hard] **Acceptance**: a `/skill-set-chain-driver --loop 3+` run against a branch-per-phase fixture project whose active phase is fully `[x]` with no Next-up item scoped to it. Confirm: (a) sst-dev-cycle §0-7 emits `[no-work] phase <N> complete on <branch>; awaiting human branch setup for phase <N+1>` and the runner aborts the loop with MANIFEST `terminated_by: "no_work_bail"`; (b) §0-7a writes exactly ONE `docs/HUMAN.md ## Blocking` entry on the first iter and re-running the bail leaves the file byte-identical (idempotency — the gap that risks HUMAN.md/Telegram spam on a looped run); (c) `notify-human-md.sh` fires once on the fresh append and not on the idempotent skip; (d) a separate fixture where the same SPEC item is the picked primary across ≥3 trailing iters without its `[ ]`→`[x]` flip produces a sst-supervisor `[stuck-item]` finding plus one `docs/HUMAN.md ## High` decompose-or-remove entry plus one `manager-notes.md` observation (write-path (g)), all idempotent. Reason: 38.4 and 38.5 shipped as SKILL.md prose only (no unit test possible for LLM-driven skills); their acceptance criteria demand behavioral verification that only a live round-trip can supply.

## Deferred phases

### Phase 20 (deferred): `goose-cerebras` harness + portability proof

Phase 1's "Harness scope" promised additional harnesses drop in by adding a `Harness` subclass; this phase ships a non-Claude binary (Block's Goose CLI talking to Cerebras Inference's free tier of GPT-OSS-120B or Qwen3-235B). Goose natively reads `~/.claude/skills/` so skills are consumed unchanged. Bridging requires a ~150 LoC Python shim translating Goose's `message`/`notification`/`error`/`complete` event vocabulary to Claude Code's `system/init`/`assistant`/`user`/`result` shape; cost is set to `0.0` (true for free tier). Demoted from primary "24/7 productivity fix" because Phase 19's per-skill model-tier routing within Max delivers the bulk of the throughput win without a new harness; Phase 20 becomes the future supplement when free-tier capacity matters (e.g. when Phase 19 throughput is insufficient AND mechanical-skill work has been cleanly identified).

Anti-fork constraint when this lands: harness MUST NOT be used for `*-supervisor` or any skill that rewrites another `SKILL.md`. Per-skill `allowed-harnesses:` frontmatter (or runtime allowlist) enforces it.

Re-pick when: Phase 19 acceptance ships AND a real cost / throughput baseline shows Phase 19's win is insufficient AND mechanical-skill work has been cleanly identified for offload to Cerebras. Architecture as in the original spec: `GooseCerebrasHarness` subclass + `bin/goose-shim.py` translating Goose's stream-json event vocabulary to Claude Code's shape + per-skill `allowed-harnesses:` anti-fork guard.

## Future / human-handled

(empty — add entries here when the user wants to keep work visible but not queued)

## Flipping an item back into `Next up`

1. Pick the entry. Copy its one-line description.
2. Append to `docs/TODO.md > Next up` as `- [<difficulty>] <description>. Reason: flipped from FUTURE-WORK <utc-iso>`.
3. Delete the entry from this file (or leave it under `## Just flipped` if you want a paper trail; not required).
4. The next dev cycle picks it per the normal pick order.
