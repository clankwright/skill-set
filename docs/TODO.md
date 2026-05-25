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

- 35.6 [medium] flip dispatcher lifecycle to always-on: retired chain-driver start/stop hooks in drive-chain.py, updated Phase 18 SPEC prose, CLAUDE.md, README worker management — by skill-set-dev at 2026-05-25T17:39:14Z
- 36.3 [easy] templates/SPEC.md contract_violation JSON: corrected "reason"→"kind", added "skill" field, removed "signals" key, updated guidance to "surface the `kind` field" — by skill-set-dev at 2026-05-25T17:18:24Z
- 36.2 [easy] templates/SPEC.md: added "### Incomplete-cycle contract violation" section after "### Blocked-on-human bail" documenting runner signal, manifest shape, and chain-driver reporting guidance — by skill-set-dev at 2026-05-25T17:00:11Z
- 35.2+35.3+35.5 [medium] bin/manager-bot.py reshaped into dispatcher: spawn_manager_for_command (--process-command, cwd from persona), _route_via_dispatcher helper, inline /ping/help/projects only, all project-scoped verbs dispatched; startup log broadened; 60 tests green — by skill-set-dev at 2026-05-25T14:08:33Z
- 35.15 [easy] retroactive /sst-sanitize-transferable on sst-dev-review/SKILL.md (005477c inline bypass): Sanitize: must-fix=0, should-fix=0, nit=0 — by skill-set-dev at 2026-05-25T13:32:53Z
- 36.1 [medium] Phase 36: runner-level incomplete-cycle enforcement in bin/skill-chain.py; _incomplete_cycle_detected helper + run_iteration check + main() terminated_by; 9 new tests (25 total green) — by skill-set-dev at 2026-05-25T12:43:24Z
- 35.16 [easy] close false positive: runner _DIFFICULTY_BRACKET_RE.search() correctly picks [medium] from [supervisor] [medium] lines; no TODO fix needed; SPEC closed without code change — by skill-set-dev at 2026-05-25T12:21:47Z
- 35.14 [easy] retroactive /sst-sanitize-transferable on sst-supervisor/SKILL.md (005477c inline bypass): Sanitize: must-fix=0, should-fix=0, nit=1 (pre-existing /home/rob/ path in examples) — by skill-set-dev at 2026-05-25T10:19:02Z
- 35.10 [easy] retroactive spec block for sst-wiki-curator v1.1.0 (c20ff96): 12 items 23.5–23.16 covering all 13 testbed phases (synthesis page kind, drafts/ layer, domain-schema extension, navigation axis, reading paths, middle lint.py template, Mode D umbrella, variant-boundary lint, source-papers table, contradiction example, adjacent patterns, profile axis) — by skill-set-dev at 2026-05-25T08:44:42Z
- 35.13 [easy] sst-supervisor §0.5.3 fast-path keyword scan: word-boundary anchoring on ERROR/FAIL/Traceback/Exception; v1.13.0→v1.13.1; Inline sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T08:25:12Z
## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- 35.8 [medium] end-to-end integration test under tests/test_manager_bot.py + fixture project: simulate bot → queue → mock manager spawn → mock notify-telegram capture; parameterize over each verb; assert unknown-persona refuse path doesn't spawn. — SPEC Phase 35

