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

- 34.1+34.2+34.4+34.5 [easy] Telegram base-dir fallback: notify-telegram.sh (graceful skip + ~/Dev/skill-set/telegram.env fallback), drive-chain.py (REPO_ROOT fallback), sst-manager §0.4 optional telegram-env + fallback chain, .gitignore + README.md + CLAUDE.md docs; +4 tests (94→98 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-23T00:15:00Z
- 31.11+31.12 [medium] integration test for run_iteration blocked_on_human bail + CLAUDE.md step 4 for HUMAN.md; +1 test (93→94 green) — by sst-dev-cycle at 2026-05-22T20:15:00Z
- 31.1-31.10 [medium] Phase 31 HUMAN.md framework wiring: templates/HUMAN.md skeleton, sst-supervisor §5b, sst-dev-review 4th routing bucket, sst-manager HUMAN.md read+write+digest+alerts+auto-verify, sst-dev-cycle [blocked-on-human] sentinel, bin/skill-chain.py runner, bin/validate-frontmatter.py validator, dahrouge.com cross-refs; sst-manager v1.13.0→v1.14.0; +15 tests (78→93 green); Sanitize: must-fix=1 (self-fixed inline → final must-fix=0) — by sst-dev-cycle at 2026-05-22T19:30:00Z
- 30.3 [hard] framework portion: operator-level manager support — `_discover_manager_personas` honors `operator-level: true` (emits one persona per `watched-projects[*].name`); `docs/migration-single-manager.md` operator runbook; sst-manager v1.12.0→v1.13.0 documents both shapes; +8 tests (70→78 green); Sanitize: must-fix=3 (self-fixed inline → final must-fix=0) — by sst-dev-cycle at 2026-05-21T23:50:00Z
- 30.1+30.2 [medium] MANAGER.md preamble + sst-manager walk-time read + multi-project objectives.md ## Project: sections; sst-manager v1.11.2→v1.12.0; +13 tests (57→70 green); Sanitize: must-fix=0, should-fix=1 (self-fixed) — by sst-dev-cycle at 2026-05-21T23:15:00Z
- 29.2 [medium] add run_skill_with_retry integration tests for session-id threading (rate-limit retry loop); +2 tests (55→57 green) — by sst-dev-cycle at 2026-05-21T22:15:00Z
- 29.1 [medium] rate-limit retry now uses --resume <session_id> to restore prior session; continuation prompt "continue" replaces bootstrap; +6 tests (49→55 green) — by sst-dev-cycle at 2026-05-21T21:30:00Z
- 28.8 [easy] fix sst-manager truncation hint to say "run /status <persona> for full digest"; also fix notify-telegram.sh; +2 tests (42→44 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-21T20:10:00Z
- [easy] strip "Multi-project bot conventions" from cm-manager/SKILL.md; generic routing now lives in transferable sst-manager §1; v1.0.0→v1.0.1 — by sst-dev-cycle at 2026-05-21T18:10:00Z
- 28.7 [medium] make /status persona-aware: latest_digest(persona) filters <persona>_*.txt, sst-manager digest naming updated to <persona>_<utc>.txt, /status handler requires token; +5 tests (37→42 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-21T17:00:00Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [medium] Phase 33: Telegram notification on every HUMAN.md change — add `bin/notify-human-md.sh` (snapshot-diff → brief descriptive Telegram message) plus a write-then-notify contract on every HUMAN.md writer (`sst-supervisor` §5b, `sst-dev-review` §4, `sst-manager`). Start at SPEC 33.1. — reason: user message 2026-05-22 (operator wants every HUMAN.md change surfaced immediately, not just the manager's periodic `## Blocking` delta). Phase 32 (supervisor routes unpromoted sidecars into HUMAN.md `## High`) is SPEC-only, lower priority — not queued here.


