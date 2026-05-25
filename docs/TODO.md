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

- 36.1 [medium] Phase 36: runner-level incomplete-cycle enforcement in bin/skill-chain.py; _incomplete_cycle_detected helper + run_iteration check + main() terminated_by; 9 new tests (25 total green) — by skill-set-dev at 2026-05-25T12:43:24Z
- 35.16 [easy] close false positive: runner _DIFFICULTY_BRACKET_RE.search() correctly picks [medium] from [supervisor] [medium] lines; no TODO fix needed; SPEC closed without code change — by skill-set-dev at 2026-05-25T12:21:47Z
- 35.14 [easy] retroactive /sst-sanitize-transferable on sst-supervisor/SKILL.md (005477c inline bypass): Sanitize: must-fix=0, should-fix=0, nit=1 (pre-existing /home/rob/ path in examples) — by skill-set-dev at 2026-05-25T10:19:02Z
- 35.10 [easy] retroactive spec block for sst-wiki-curator v1.1.0 (c20ff96): 12 items 23.5–23.16 covering all 13 testbed phases (synthesis page kind, drafts/ layer, domain-schema extension, navigation axis, reading paths, middle lint.py template, Mode D umbrella, variant-boundary lint, source-papers table, contradiction example, adjacent patterns, profile axis) — by skill-set-dev at 2026-05-25T08:44:42Z
- 35.13 [easy] sst-supervisor §0.5.3 fast-path keyword scan: word-boundary anchoring on ERROR/FAIL/Traceback/Exception; v1.13.0→v1.13.1; Inline sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.12 [easy] sst-dev-review template retroactive spec item (415ac81): <phase>.<n> ID before difficulty bracket; inline sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.11 [easy] retroactive sst-sanitize-transferable on sst-dev-review/SKILL.md (415ac81); inline sanitize: must-fix=0 + retroactive spec item 35.12 added — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.9 [easy] Phase 29 spec item 29.3 added for post-pause jitter (3f1d716); handoff-doc omission resolved — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.1 [medium] sst-manager --process-command mode: new §On-demand command routing section with 7 verb handlers (status/objectives/proposals/promote/pause/resume/ping); v1.14.2→v1.15.0; Sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T07:44:34Z
- 35.7 [easy] bin/notify-telegram.sh: chunk-split bodies >4000 chars at newline boundaries with code-fence rebalancing; +3 tests (130→133 green) — by skill-set-dev at 2026-05-25T07:44:34Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [easy] [should-fix] 35.15 `skills/dev/sst-dev-review/SKILL.md` inline sanitize bypass in 35.11 closure (005477c): retroactive `/sst-sanitize-transferable` + "Sanitize: must-fix=N" record — review of 005477c (group with inline-sanitize-bypass)
- 35.2 [medium] bin/manager-bot.py reshape into dispatcher: lift spawn_on_demand_manager to general spawn_manager_for_command, drop inline /ping-/status-/projects fulfillment, route every project-scoped verb through a one-time manager spawn in the project cwd. — SPEC Phase 35
- 35.3 [easy] dispatcher project-cwd resolution via `_discover_manager_personas`; spawn manager with `cwd=project_cwd`. — SPEC Phase 35
- 35.5 [easy] bot startup log broadens to "on-demand command routing enabled (verbs: ...)"; queue-only fallback when MANAGER_SKILL_NAME is unset. — SPEC Phase 35
- 35.6 [medium] dispatcher-lifecycle decision (always-on vs chain-bound); Phase 35 removes the Phase 18 inbound-noise rationale because every spawn re-reads project state — recommend flipping to always-on, update Phase 18 follow-ups + drive-chain.py + CLAUDE.md + README accordingly. — SPEC Phase 35
- 35.8 [medium] end-to-end integration test under tests/test_manager_bot.py + fixture project: simulate bot → queue → mock manager spawn → mock notify-telegram capture; parameterize over each verb; assert unknown-persona refuse path doesn't spawn. — SPEC Phase 35

