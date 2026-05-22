# <Project Name> HUMAN-action backlog (handoff doc)

> Active blockers requiring an out-of-band human action — anything the autonomous dev cycle cannot perform from inside its own iteration. **NOT** for deferred work (use `docs/FUTURE-WORK.md`), and **NOT** for acceptance tests the dev cycle can't self-verify (also `FUTURE-WORK.md > ## Manual / human verification`). HUMAN.md is the "the cycle is stuck right now, waiting on you" list.
>
> Every skill reads this on start. Top of file is highest urgency; within each section, newest-first.

## Item schema

Each entry uses the form:

```
- [ ] H<phase>.<n> [easy|medium|hard] **<short title>**
  <one-paragraph body: what the human must do, where, why the cycle can't do it.>
  Blocks: <comma-separated SPEC IDs the human action is gating, or "none" if orthogonal>.
  Verify: <optional one-line shell check the supervisor/manager auto-runs on next tick; pass = move to ## Done, fail = reopen>.
  Filed by: <skill-name> at <utc-iso>.
  Source: <verdict path, transcript path, "/feedback chat <id>", or "review of <sha>">.
```

`<phase>` matches the SPEC.md phase the action is gating; `<n>` is 1-indexed within HUMAN.md per phase, independent of SPEC.md's counter. IDs are stable once assigned; gaps from removed/closed items are valid.

## Blocking

(Highest-urgency items — open `## Blocking` entries block the dev cycle from picking dependent SPEC items. The cycle emits `[blocked-on-human]` and bails if its picked item's SPEC ID appears in any `Blocks:` line here.)

<!-- example, delete on instantiation
- [ ] H3.1 [easy] **Set 7 STRAPI_* GitHub Actions secrets**
  The dahrouge.com deploy workflow (`.github/workflows/deploy_backup_to_vm.yml:56-62`) passes 7 `secrets.X` values to the VM-side provision script. None of the 7 are currently set at github.com/dahrouge-geological/dahrouge.com -> Settings -> Secrets and variables -> Actions, so every deploy aborts at `vm/provision-strapi-postgres.sh:13` (or now, after Phase 3.18, at the workflow's pre-flight step). Required values: `STRAPI_DB_PASSWORD`, `STRAPI_APP_KEYS`, `STRAPI_API_TOKEN_SALT`, `STRAPI_ADMIN_JWT_SECRET`, `STRAPI_TRANSFER_TOKEN_SALT`, `STRAPI_JWT_SECRET`, `STRAPI_ENCRYPTION_KEY`. Generation guidance lives in `cms/README.md > Required GitHub Actions secrets`. Until set, Phase 3.1-3.5 cannot be runtime-validated and Strapi is not live on staging.
  Blocks: 3.1, 3.2, 3.3, 3.4, 3.5 (Phase 3 deploys + runtime validation), 4.2, 4.3 (Editor workflow needs a live admin), 5.1 (soak gate cannot start).
  Verify: gh secret list --repo dahrouge-geological/dahrouge.com 2>/dev/null | awk '{print $1}' | grep -c '^STRAPI_' | grep -qx 7
  Filed by: sst-supervisor at 2026-05-22T<utc>.
  Source: docs/TODO.md 3.10, 3.18 + chat with user 2026-05-22.
-->

## High

(Important but not actively blocking the cycle. The dev cycle continues past these unless picked-item gating exists.)

## Medium

## Low

## Done

(Audit trail of closed entries — newest-first. The supervisor/manager moves items here after `[x]` is set AND the `Verify:` check passes. Entries keep their original H-ID and pick up a `(verified <utc>)` suffix.)

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
