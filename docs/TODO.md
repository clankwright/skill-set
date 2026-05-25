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

- 35.14 [easy] retroactive /sst-sanitize-transferable on sst-supervisor/SKILL.md (005477c inline bypass): Sanitize: must-fix=0, should-fix=0, nit=1 (pre-existing /home/rob/ path in examples) — by skill-set-dev at 2026-05-25T10:19:02Z
- 35.10 [easy] retroactive spec block for sst-wiki-curator v1.1.0 (c20ff96): 12 items 23.5–23.16 covering all 13 testbed phases (synthesis page kind, drafts/ layer, domain-schema extension, navigation axis, reading paths, middle lint.py template, Mode D umbrella, variant-boundary lint, source-papers table, contradiction example, adjacent patterns, profile axis) — by skill-set-dev at 2026-05-25T08:44:42Z
- 35.13 [easy] sst-supervisor §0.5.3 fast-path keyword scan: word-boundary anchoring on ERROR/FAIL/Traceback/Exception; v1.13.0→v1.13.1; Inline sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.12 [easy] sst-dev-review template retroactive spec item (415ac81): <phase>.<n> ID before difficulty bracket; inline sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.11 [easy] retroactive sst-sanitize-transferable on sst-dev-review/SKILL.md (415ac81); inline sanitize: must-fix=0 + retroactive spec item 35.12 added — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.9 [easy] Phase 29 spec item 29.3 added for post-pause jitter (3f1d716); handoff-doc omission resolved — by skill-set-dev at 2026-05-25T08:25:12Z
- 35.1 [medium] sst-manager --process-command mode: new §On-demand command routing section with 7 verb handlers (status/objectives/proposals/promote/pause/resume/ping); v1.14.2→v1.15.0; Sanitize: must-fix=0 — by skill-set-dev at 2026-05-25T07:44:34Z
- 35.7 [easy] bin/notify-telegram.sh: chunk-split bodies >4000 chars at newline boundaries with code-fence rebalancing; +3 tests (130→133 green) — by skill-set-dev at 2026-05-25T07:44:34Z
- 35.4 [easy] skill-set-manager: document --process-command mode in proprietary template description + on-demand command section; v1.5.1→v1.5.2; transferable-version >=1.15.0 — by skill-set-dev at 2026-05-25T07:44:34Z
- 32.3 [easy] sst-promote-skill-proposal §6b: replace "absolute path" with "sidecar path in the same form used when discovering it — do not expand ~ before comparing"; v1.1.2→v1.1.3; +1 test (126→127 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-23T20:30:00Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [supervisor] [medium] Phase 36 (proposed): code-level enforcement of "dev exits with incomplete cycle" in `bin/skill-chain.py`. After the dev skill exits with `[ok]`, the runner checks (a) `git_sha_before == git_sha_after` AND (b) `## In flight` is non-empty OR `Sanitize: must-fix=PENDING` appears anywhere in `docs/TODO.md`. If either trigger fires, emit `[contract-violation: incomplete-cycle]` to the iter transcript so dev-review can flag it deterministically, and abort the chain loop. Five consecutive recurrences of "sub-skill returns, parent doesn't close" (2026-04-27 iter_02, 2026-05-02, 2026-05-25 iter_04, iter_05, iter_06) with FOUR prose defenses (Defenses 2+3+4 in skill-set-dev §5 + v1.4.0 Single-sub-skill cap in §1) all failing to prevent the pattern. Prose-level fix is exhausted; the model treats sub-skill returning as cycle terminus regardless of what the prose says. Source: 2026-05-25T07-22-35Z_skill-set-cycle/iter_06/supervisor_verdict.md — supervisor verdict iter_06.
- [easy] [should-fix] 35.15 `skills/dev/sst-dev-review/SKILL.md` inline sanitize bypass in 35.11 closure (005477c): retroactive `/sst-sanitize-transferable` + "Sanitize: must-fix=N" record — review of 005477c (group with inline-sanitize-bypass)
- 35.2 [medium] bin/manager-bot.py reshape into dispatcher: lift spawn_on_demand_manager to general spawn_manager_for_command, drop inline /ping-/status-/projects fulfillment, route every project-scoped verb through a one-time manager spawn in the project cwd. — SPEC Phase 35
- 35.3 [easy] dispatcher project-cwd resolution via `_discover_manager_personas`; spawn manager with `cwd=project_cwd`. — SPEC Phase 35
- 35.5 [easy] bot startup log broadens to "on-demand command routing enabled (verbs: ...)"; queue-only fallback when MANAGER_SKILL_NAME is unset. — SPEC Phase 35
- 35.6 [medium] dispatcher-lifecycle decision (always-on vs chain-bound); Phase 35 removes the Phase 18 inbound-noise rationale because every spawn re-reads project state — recommend flipping to always-on, update Phase 18 follow-ups + drive-chain.py + CLAUDE.md + README accordingly. — SPEC Phase 35
- 35.8 [medium] end-to-end integration test under tests/test_manager_bot.py + fixture project: simulate bot → queue → mock manager spawn → mock notify-telegram capture; parameterize over each verb; assert unknown-persona refuse path doesn't spawn. — SPEC Phase 35

