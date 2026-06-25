# skill-set HUMAN-action backlog (handoff doc)

> Active blockers requiring an out-of-band human action — anything the autonomous dev cycle cannot perform from inside its own iteration. **NOT** for deferred work (use `docs/FUTURE-WORK.md`), and **NOT** for acceptance tests the dev cycle can't self-verify (also `FUTURE-WORK.md > ## Manual / human verification`). HUMAN.md is the "the cycle is stuck right now, waiting on you" list.
>
> Every skill reads this on start. Top of file is highest urgency; within each section, newest-first.

## Item schema

Each entry is a checkbox bullet whose ID has the form `H<phase>.<n>` (e.g. `H3.1`, `H35.1`), followed by a `[easy|medium|hard]` difficulty bracket and a `**short title**`. The body paragraph documents what the human must do, where, and why the cycle can't do it. Open items also carry a `Blocks:` line (comma-separated SPEC IDs, or `none`), an optional `Verify:` shell-check line (passing closes the item), a `Filed by:` line, and a `Source:` line. See the concrete H35.1 entry below for the live shape; consult `templates/HUMAN.md` for the canonical reference.

`<phase>` matches the SPEC.md phase the action is gating; `<n>` is 1-indexed within HUMAN.md per phase, independent of SPEC.md's counter. IDs are stable once assigned; gaps from removed/closed items are valid.

## Blocking

(Highest-urgency items — open `## Blocking` entries block the dev cycle from picking dependent SPEC items. The cycle emits `[blocked-on-human]` and bails if its picked item's SPEC ID appears in any `Blocks:` line here.)



## High

(Important but not actively blocking the cycle. The dev cycle continues past these unless picked-item gating exists.)

- [ ] H43.1 [medium] **Durable fix for recurring `incomplete-cycle`: dev stops after the sanitize sub-skill, before the commit**
  Two consecutive `dev-cycle-with-review-looped` runs have now ended an iteration with the dev (`sst-dev-cycle`) doing all of its work — pick, failing tests, implementation, `/sst-sanitize-transferable` (must-fix=0) — then exiting WITHOUT staging or committing, so the chain runner records `contract_violation: incomplete-cycle` (run `2026-06-24T01-31-10Z`/iter_03, head 192dca5; run `2026-06-24T23-57-40Z`/iter_03, head 0599e56). Same root cause both times: the model treats the sanitize `/skill` sub-invocation's clean return as task-completion and stops its turn. The Phase 43 "seam fix" (run sanitize in §3, before §4, so no sub-skill return sits immediately before the commit) is being IGNORED — the model runs sanitize as its last action anyway, re-creating the exact seam the relocation was meant to remove. The Phase 36 orphaned-cycle recovery in `sst-dev-review` catches it cleanly each time (no work lost; both cycles shipped correctly), but at a real cost: ~$1.7 (dev) + ~$1.1 (review) per recovered cycle, and the review ends up authoring the commit it then reviews, diluting the independent second-pass. This is NOT durably prose-fixable: the dev's prose already mandates the §3 placement emphatically and the model has ignored it twice, so piling on more prose is unlikely to help. A structural change is needed — pick one: (1) inline the sanitize check into the dev skill instead of a `/skill` sub-invocation, so no sub-skill return ever precedes the commit; (2) add a runner-level guard that, on detecting `incomplete-cycle`, re-prompts the dev to commit before handing off to review; or (3) accept the recovery as the intended design and close this won't-fix (the loop already self-heals). The supervisor cannot make this call — it is a contract/structural decision.
  Blocks: none.
  Asks: choose a durable approach for the recurring `incomplete-cycle` (inline sanitize / runner re-prompt / accept recovery as design).
  Reply: /feedback <token> <your choice + any direction>
  Filed by: sst-supervisor at 2026-06-25T02:23:16Z.
  Source: 2026-06-24T23-57-40Z_dev-cycle-with-review-looped/iter_03/supervisor_verdict.md.

- [ ] H44.1 [easy] **Install `sst-tester` into `~/.claude/skills/` so the chain can invoke it**
  The `dev-cycle-with-review-looped` chain runs `sst-tester` as a stage, but the skill is not present in `~/.claude/skills/` (the Skill tool returns `Unknown skill: sst-tester`). In both iter_01 and iter_02 of run `2026-06-16T06-40-57Z` the tester worker only succeeded by improvising: it read `skills/framework/sst-tester/SKILL.md` from the repo and followed it directly. On a weaker model or a stricter harness that fallback may not happen and the stage would hard-fail. The supervisor cannot run installers (its action surface is verdicts/skill-edits/doc-appends plus one executor dispatch); the canonical fix is to refresh the runtime skill copies. Normally this would be an autonomous `sst-executor` dispatch (Route 1), but this run's retry-0 supervisor attempt was rejected on the org monthly spend limit, so a fresh billable `claude --print` executor spawn is being avoided this cycle in favour of this human-closable request.
  Blocks: none.
  Verify: test -f ~/.claude/skills/sst-tester/SKILL.md
  Asks: run the skill installer so `sst-tester` is registered with the harness.
  Reply: /exec <token> bash bin/install-skills.sh -y --force
  Filed by: sst-supervisor at 2026-06-16T08:06:28Z.
  Source: 2026-06-16T06-40-57Z_dev-cycle-with-review-looped/iter_02/supervisor_verdict.md.

## Medium

## Low

## Done

(Audit trail of closed entries — newest-first. The supervisor/manager moves items here after `[x]` is set AND the `Verify:` check passes. Entries keep their original H-ID and pick up a `(verified <utc>)` suffix.)

- [x] H35.3 [easy] **Promote sst-dev-review sidecar to transferable** — sidecar discarded/applied without a separate promotion (SKILL.patch.md no longer present); discarded-sidecar auto-close on absence check. (verified 2026-05-27T03:43:22Z)
- [x] H35.4 [easy] **Recover dirty working tree from iter_10 incomplete cycle (35.15 retroactive sanitize)** — skill-set-dev executed forward-complete option: swap PENDING→0 in Just-shipped (findings confirmed must-fix=0, should-fix=0, nit=0), commit SPEC.md + TODO.md + HUMAN.md. (verified 2026-05-25T13:32:53Z)
- [x] H35.2 [easy] **Recover dirty working tree from iter_06 incomplete cycle (35.14 retroactive sanitize, single-item batch)** — skill-set-dev executed option (b): forward-complete via PENDING→0 swap; findings file confirmed must-fix=0, should-fix=0, nit=1 (pre-existing /home/rob/ path in examples). 35.14 fully committed. (verified 2026-05-25T10:19:02Z)
- [x] H35.1 [easy] **Recover dirty working tree from iter_05 incomplete cycle (35.14 + 35.15 retroactive batch)** — skill-set-dev chose option (a): `git checkout -- docs/SPEC.md docs/TODO.md`, allowing 35.14 and 35.15 to be re-picked serially under the single-sub-skill cap. (verified 2026-05-25T10:00:00Z)

---

## How this file evolves

- **Who writes:** `sst-supervisor` (primary, post-chain), `sst-dev-review` (when a review finding's fix is human-only), `sst-manager` (on-demand `/feedback` routing).
- **Who closes:** the human user (manual `[ ]` -> `[x]`). The supervisor/manager auto-verifies on the next tick via the optional `Verify:` shell line.
- **Who reads:** every skill on cycle start. `sst-dev-cycle` especially uses `Blocks:` lines to decide whether to emit `[blocked-on-human]` and bail.
- **Ordering:** newest-first within each section; sections themselves are ordered top-to-bottom from most-urgent to least.
- **Cross-reference convention:** SPEC.md items blocked on a HUMAN entry carry a `(blocked-on H<phase>.<n>)` annotation on the item line (added by the same skill that filed the HUMAN entry).
- **ID gaps are valid.** Removed entries leave their ID slot empty; never renumber.
- **Telegram bridge.** Every skill that writes to this file invokes `bin/notify-human-md.sh <project-root> docs/HUMAN.md` immediately after the write. The helper diffs the file against the last-notified snapshot and sends a brief delta message for any addition, section move, or `[ ]`↔`[x]` flip. Additionally, `sst-manager` (operator-level or per-project) fires an immediate alert on new `## Blocking` entries during its periodic tick, and includes all open `## Blocking` items in every digest.
- **Notification format.** `[<project>] HUMAN.md: <delta>`. Delta items: `+H3.2 ##High [ ] "<title>"` for new entries, `H3.1 [ ]→[x]` for state flips, `H3.1 ##Blocking→##High "<title>"` for section moves. Multiple deltas are comma-separated; long lists are truncated with `(+N more)`. The `[<project>]` label follows the Phase 28 multi-persona labeling convention.
- **Distinction from `FUTURE-WORK.md`.** FUTURE-WORK.md is the parking lot for *deferred* work and acceptance tests the cycle cannot self-verify; HUMAN.md is for *actively-blocking* human-only actions the cycle is waiting on right now. A future-work item is "we will look at this later"; a HUMAN.md item is "the cycle cannot proceed until you do this."
