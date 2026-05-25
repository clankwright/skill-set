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

- [ ] H35.3 [easy] **Promote sst-dev-review sidecar to transferable**
  A supervisor-authored transferable improvement is waiting as a sidecar at
  `/home/rob/Dev/skill-set/skills/dev/sst-dev-review/SKILL.patch.md`. Run
  `/sst-promote-skill-proposal` to review and apply it. The patch adds one
  Pitfalls bullet about verifying parser/runner claims by reading the code
  before filing a finding (motivated by iter_07's false-positive parser claim
  on `docs/TODO.md:47`).
  Blocks: none
  Verify: test ! -e /home/rob/Dev/skill-set/skills/dev/sst-dev-review/SKILL.patch.md
  Filed by: skill-set-supervisor at 2026-05-25T10:30:00Z.
  Source: 2026-05-25T07-22-35Z_skill-set-cycle/iter_07/supervisor_verdict.md.

## Medium

## Low

## Done

(Audit trail of closed entries — newest-first. The supervisor/manager moves items here after `[x]` is set AND the `Verify:` check passes. Entries keep their original H-ID and pick up a `(verified <utc>)` suffix.)

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
