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

- 35.1 [medium] sst-manager --process-command mode: new §On-demand command routing section with 7 verb handlers (status/objectives/proposals/promote/pause/resume/ping); v1.14.2→v1.15.0; Sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T07:44:34Z
- 35.7 [easy] bin/notify-telegram.sh: chunk-split bodies >4000 chars at newline boundaries with code-fence rebalancing; +3 tests (130→133 green) — by skill-set-dev at 2026-05-25T07:44:34Z
- 35.4 [easy] skill-set-manager: document --process-command mode in proprietary template description + on-demand command section; v1.5.1→v1.5.2; transferable-version >=1.15.0 — by skill-set-dev at 2026-05-25T07:44:34Z
- 32.3 [easy] sst-promote-skill-proposal §6b: replace "absolute path" with "sidecar path in the same form used when discovering it — do not expand ~ before comparing"; v1.1.2→v1.1.3; +1 test (126→127 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-23T20:30:00Z
- 32.2 [medium] sst-promote-skill-proposal §6b: scan docs/HUMAN.md for open Verify:test!-e entries matching the promoted sidecar, flip to [x], call bin/notify-human-md.sh; v1.1.1→v1.1.2; +4 tests (122→126 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-23T18:10:00Z
- 32.1 [medium] sst-supervisor §5b sidecar-promotion routing to HUMAN.md ##High (Blocks: none, Verify: test ! -e, auto-clear path) + sst-manager §3b discarded-sidecar auto-close rule + templates/HUMAN.md pending-sidecar entry shape; sst-supervisor v1.12.0→v1.13.0, sst-manager v1.14.1→v1.14.2; +9 tests (113→122 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-23T16:20:00Z
- 33.1-33.5+34.3 [medium] Phase 33: bin/notify-human-md.sh (snapshot-diff, delta, send) + write-then-notify contract on sst-supervisor/sst-dev-review/sst-manager + anti-fork carve-outs + templates/HUMAN.md format note; +12 tests (101→113 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-23T15:30:00Z
- 34.6 [easy] extract _resolve_tg_env helper from drive-chain.py main() + tests/test_drive_chain_telegram.py (3 tests: base-dir fires, --telegram-env beats, BOT_TOKEN beats); +3 tests (98→101 green) — by sst-dev-cycle at 2026-05-23T14:15:00Z
- 34.1+34.2+34.4+34.5 [easy] Telegram base-dir fallback: notify-telegram.sh (graceful skip + ~/Dev/skill-set/telegram.env fallback), drive-chain.py (REPO_ROOT fallback), sst-manager §0.4 optional telegram-env + fallback chain, .gitignore + README.md + CLAUDE.md docs; +4 tests (94→98 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-23T00:15:00Z
- 31.11+31.12 [medium] integration test for run_iteration blocked_on_human bail + CLAUDE.md step 4 for HUMAN.md; +1 test (93→94 green) — by sst-dev-cycle at 2026-05-22T20:15:00Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- 35.2 [medium] bin/manager-bot.py reshape into dispatcher: lift spawn_on_demand_manager to general spawn_manager_for_command, drop inline /ping-/status-/projects fulfillment, route every project-scoped verb through a one-time manager spawn in the project cwd. — SPEC Phase 35
- 35.3 [easy] dispatcher project-cwd resolution via `_discover_manager_personas`; spawn manager with `cwd=project_cwd`. — SPEC Phase 35
- 35.5 [easy] bot startup log broadens to "on-demand command routing enabled (verbs: ...)"; queue-only fallback when MANAGER_SKILL_NAME is unset. — SPEC Phase 35
- 35.6 [medium] dispatcher-lifecycle decision (always-on vs chain-bound); Phase 35 removes the Phase 18 inbound-noise rationale because every spawn re-reads project state — recommend flipping to always-on, update Phase 18 follow-ups + drive-chain.py + CLAUDE.md + README accordingly. — SPEC Phase 35
- 35.8 [medium] end-to-end integration test under tests/test_manager_bot.py + fixture project: simulate bot → queue → mock manager spawn → mock notify-telegram capture; parameterize over each verb; assert unknown-persona refuse path doesn't spawn. — SPEC Phase 35

