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

- 38.12: Phase 36 pass-through guard excludes auto-supervisor: `skills_to_run[i+1] != auto_supervisor` prevents orphaned dev work reaching supervisor; 1 new test, 215 green — by sst-dev-cycle at 2026-05-28T19:15:00Z
- sst-dev-review 1.6.0 orphaned-cycle recovery + Phase 36 guard passthrough: review skill now recovers incomplete dev cycles (dirty tree + In-flight line) by verifying tests and committing; runner passes to review instead of aborting when a follower skill exists; 2 new tests (passes_to_review, aborts_without_next_skill), 214 green, sanitize must-fix=0 — by sst-dev-cycle at 2026-05-28T18:10:00Z
- [medium batch] manager rate-limit fixes: manager-idle-check.py cursor-field fix (reads `latest_run` with `last_run` fallback; idle-gate now skips idle projects, dahrouge confirmed IDLE) + 5 tests; sst-manager 1.17.0 model-floor opus to sonnet + README guidance; README manager cron-tick-spreading note; 213 green, sanitize clean. Proprietary cm/dahrouge/skill-set wrapper model-floors flipped to sonnet locally (gitignored). Implemented by sst-dev-cycle; closed manually after an incomplete-cycle abort, 2026-05-27T22:26:16Z
- sst-dev-review 1.5.8 [easy]: hand-merge parser-behavior anti-pattern bullet from stale SKILL.patch.md sidecar (May 25, pre-38.1/38.11); discard sidecar; validator clean. Filed retroactively per direct-change convention — by manual (direct change) at 2026-05-27T13:30:00Z
- [medium batch] manager idle pre-check + sst-setup-telegram symlink: bin/manager-idle-check.py (7 logic tests) + sst-manager 1.16.0 §Caller-side-idle-gate + sst-setup-telegram 1.1.0 §4 base-dir symlink; 13 new tests, 208 green; sanitize must-fix=0 on both transferables — by sst-dev-cycle at 2026-05-27T09:15:00Z
- 38.11 + sst-dev-review 1.5.7: --force DIVERGED overwrite test + validator-invocation clarification; 1 new test, 195 green — by sst-dev-cycle at 2026-05-27T07:35:00Z
- install-skills.sh .installed-body marker: distinguish upstream source UPDATE from hand-edit DIVERGED; 7 new tests, 194 green — by sst-dev-cycle at 2026-05-27T06:15:00Z
- 38.10 [easy]: fix manager-bot.service ReadWritePaths comment: replace "outside %h/Dev/" with "outside any already-listed ReadWritePaths entry" + explicit sibling example; 2 new tests, 187 green — by sst-dev-cycle at 2026-05-27T05:05:00Z
- 38.8+38.9 [easy batch]: close batch-sizing meta note; widen manager-bot.service ReadWritePaths from %h/.claude/state to %h/.claude %h/Dev/skill-set + clarifying comment; 3 new tests, 185 green — by sst-dev-cycle at 2026-05-27T04:10:00Z
- manager-bot.service [medium batch + 38.7]: user-mode unit (WantedBy=default.target, %h paths, no User=), MANAGER_SKILL_NAME=1, CLAUDE_BIN + MANAGER_SKILLS_EXTRA_ROOTS commented hints; manager-bot.py MANAGER_SKILLS_EXTRA_ROOTS env var + extra_roots param + cross-root dedup; README systemd install block with WSL linger note; 8 new tests, 182 green — by sst-dev-cycle at 2026-05-27T03:30:00Z
- 38.3+38.4+38.5 [hard batch] Phase 38 close-out: sst-dev-cycle §0-7 phase-completion bail (derive active phase from SPEC `## Operational scope` branch map → phase-scoped `[no-work]` sentinel) + §0-7a idempotent HUMAN.md `## Blocking` handoff with notify-human-md.sh; sst-supervisor §3.6 stuck-item detection (same item picked ≥3 trailing iters without `[ ]`→`[x]` → `[stuck-item]` finding + HUMAN.md `## High` + manager-notes write-path (g)); 7 runner no-work-bail regression tests (174 green); sanitize must-fix=0 on both transferables — by sst-dev-cycle at 2026-05-27T00:42:00Z
- 38.2 [medium] validate_spec_item_quality in bin/validate-frontmatter.py: open-ended-marker check on SPEC.md open items + TODO Next-up bullets; backtick/quote exemption; concrete-target pass-through; 8 new tests, 167 green — by sst-dev-cycle at 2026-05-27T00:00:00Z
## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->


