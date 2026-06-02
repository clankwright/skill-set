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

- Removed orphaned `~/.claude/skills/sst-dev-review/SKILL.patch.md` (v1.5.7, dated 2026-05-25) from the install dir. The 1.5.8 record (below) and HUMAN.md H35.3 only cleared the repo `.claude/skills/` copy; the globally-installed sidecar persisted and the supervisor re-flagged it across the last three lngraph verdicts. Canonical `SKILL.md` is v1.6.0 (verified strict superset — the patch's only unique content, the parser anti-pattern bullet, is already at SKILL.md:329), so discard not promote; a stale-version sidecar left in place would downgrade the skill if `apply-skill-patch.py` ran — by manual (direct change) at 2026-06-02T07:12:03Z
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

- [hard] 40.1 `sst-supervisor` direct-edit rewrite: replace the whole sidecar/auto-promote machinery (§3 routing table, §4 sidecar fallback, §5b HUMAN.md promotion entries, §6 sidecar verdict fields, §Permissions apply-skill-patch clauses, §0.6 drafts→sidecar) with a direct-edit model — edit `~/Dev/skill-set/skills/<cat>/<skill>/SKILL.md` directly (sanitize-clean gate), bump version, commit, push. No `SKILL.patch.md`/`auto-promote` strings left. — spec 40.1 (user directive 2026-06-02: "sidecars are a pain, supervisors edit skills directly in base repo, commit+push")
- [medium] 40.2 `sst-manager` direct-edit authorization: add instruction that the manager MAY edit base-repo (`~/Dev/skill-set/`) skills directly + commit + push when the user requests OR it deems necessary on its own; remove §3b.2 proposals/promote handlers, discard-sidecar auto-close, and all `/sst-promote-skill-proposal`/sidecar references. — spec 40.2 (user directive 2026-06-02)
- [medium] 40.3 Drop `auto-promote` from all 7 `chains/*.yaml` + the overnight description line; grep `bin/{skill-chain,drive-chain,manager-bot}.py` for any reader and neutralize so its absence isn't an error. — spec 40.3 (user directive 2026-06-02)
- [medium] 40.4 Delete `skills/framework/sst-promote-skill-proposal/` + `bin/apply-skill-patch.py`; update `sst-sanitize-transferable` (drop "apply via /sst-promote-skill-proposal"), `templates/HUMAN.md` (sidecar example), `templates/sanitization-guidance.md`, `bin/manager-bot.py` /promote help, `bin/clean-skill-runs.py` docstring. No `/sst-promote-skill-proposal` or `apply-skill-patch.py` ref outside SPEC-archive. — spec 40.4 (user directive 2026-06-02)
- [easy] 40.5 README + CLAUDE.md: rewrite the auto-promote routing table, `proposals/` line, promote-skill tier row, and overnight-chain note to the direct-edit-and-commit model. — spec 40.5 (user directive 2026-06-02)
- [medium] 40.6 Retire `tests/test_phase32.py` sidecar tests; add direct-edit contract tests + a grep-guard that fails if any sidecar/`auto-promote`/`sst-promote-skill-proposal` term reappears on the active skill/chain surface. — spec 40.6 (user directive 2026-06-02)
- [medium] 39.1 `sst-supervisor` §0.5.3 fast-path: abort on any `sst-dev-review`-reported finding (the §6 `Found <N> items: <B> blocker, <S> should-fix` template with N>0, and/or an appended `Review follow-ups` block), not just `ERROR`/`FAIL`/`Traceback`/`Exception` keyword hits — so a prose-only finding can no longer pass as `clean (fast-path)`. — spec Phase 39.1; lngraph supervisor verdict 2026-06-02T05-11-26Z iter_02 (recurring standing note since 2026-04-30)

