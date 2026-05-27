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

- 38.8+38.9 [easy batch]: close batch-sizing meta note; widen manager-bot.service ReadWritePaths from %h/.claude/state to %h/.claude %h/Dev/skill-set + clarifying comment; 3 new tests, 185 green — by sst-dev-cycle at 2026-05-27T04:10:00Z
- manager-bot.service [medium batch + 38.7]: user-mode unit (WantedBy=default.target, %h paths, no User=), MANAGER_SKILL_NAME=1, CLAUDE_BIN + MANAGER_SKILLS_EXTRA_ROOTS commented hints; manager-bot.py MANAGER_SKILLS_EXTRA_ROOTS env var + extra_roots param + cross-root dedup; README systemd install block with WSL linger note; 8 new tests, 182 green — by sst-dev-cycle at 2026-05-27T03:30:00Z
- 38.3+38.4+38.5 [hard batch] Phase 38 close-out: sst-dev-cycle §0-7 phase-completion bail (derive active phase from SPEC `## Operational scope` branch map → phase-scoped `[no-work]` sentinel) + §0-7a idempotent HUMAN.md `## Blocking` handoff with notify-human-md.sh; sst-supervisor §3.6 stuck-item detection (same item picked ≥3 trailing iters without `[ ]`→`[x]` → `[stuck-item]` finding + HUMAN.md `## High` + manager-notes write-path (g)); 7 runner no-work-bail regression tests (174 green); sanitize must-fix=0 on both transferables — by sst-dev-cycle at 2026-05-27T00:42:00Z
- 38.2 [medium] validate_spec_item_quality in bin/validate-frontmatter.py: open-ended-marker check on SPEC.md open items + TODO Next-up bullets; backtick/quote exemption; concrete-target pass-through; 8 new tests, 167 green — by sst-dev-cycle at 2026-05-27T00:00:00Z
- 38.6 [medium] find_local_supervisor transferable fallback in bin/skill-chain.py: falls back to ~/.claude/skills/sst-supervisor when no project-local *-supervisor; proprietary still wins, multi-match still None; 4 new tests, 159 green — by manual (direct change) at 2026-05-26T23:55:57Z
- 38.1 [medium] bounded-item rule added to sst-dev-review + sst-supervisor + sst-manager (3 write surfaces): forbid open-ended/recurring items, require falsifiable acceptance criterion / concrete target; sanitize must-fix=0 — by skill-set-dev at 2026-05-26T23:55:57Z
- sst-manager SKILL.md worker-lifecycle paragraph rewritten to always-on dispatcher model (fixes stale Phase 35.6 contradiction at old line ~665) — by skill-set-dev at 2026-05-26T23:55:57Z
- bin/manager-bot.py docstring: added Discovery note that project-local *-manager skills must be symlinked into ~/.claude/skills/ to be found by _discover_manager_personas — by skill-set-dev at 2026-05-26T23:55:57Z
- 37.1 [easy] update SPEC.md:81 "Closed phases" prose to reflect archive-to-COMPLETED.md convention — by skill-set-dev at 2026-05-25T23:41:30Z
- docs: archive all closed phases (1–19, 21–36) to docs/COMPLETED.md; SPEC.md now only holds active preamble + deferred Phase 20; docs/SPEC-archive.md removed — by skill-set-dev at 2026-05-25T22:51:29Z
- 35.8 [medium] round-trip integration tests for dispatcher: tests/fixtures/stub_claude.py + fixture_project fixture + test_dispatcher_round_trip parameterized over 6 verbs + test_dispatcher_refuses_unknown_persona_without_spawning; 67/67 tests green — by skill-set-dev at 2026-05-25T22:34:04Z
## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [medium] install-skills.sh flags every source-newer skill as DIVERGED, conflating "upstream got bumped" with "target was hand-edited"; the `-y` path then SKIPS those updates unless `--force` is passed, breaking the routine "pull canonical then re-deploy" workflow; distinguish UPDATE-from-source vs hand-edit DIVERGED via a `.installed-from-rev` marker file per target, OR by diffing against the git rev that last touched the source body — reason: user message 2026-05-26 (every refresh in this session required `--force`).

