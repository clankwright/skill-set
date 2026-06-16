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

- 39.3 sst-dev-review §0.2: widen recovery sanitize gate to sst-*/SKILL.md; version 1.8.0→1.9.0; 2 new tests, 250→252 green — by sst-dev-cycle at 2026-06-16T00:00:00Z
- 39.2 sst-dev-review §0.2 recovery: add sanitize gate — check staged `skills/framework/` paths, invoke `/sst-sanitize-transferable`, abort on must-fix; version 1.7.0→1.8.0; 4 new tests, 246→250 green; sanitize must-fix=0 — by sst-dev-cycle at 2026-06-15T00:35:00Z
- 39.1 sst-supervisor §0.5.3 fast-path: abort on review-reported findings; added `Found \d+ items:` and `Review follow-ups` abort conditions to §0.5.3 keyword list; Anti-fork constraint updated; version 2.1.0→2.2.0; 5 new tests, 241→246 green — by sst-dev-cycle at 2026-06-15T00:00:00Z
- Phase 40 [hard batch, 40.1-40.6] remove sidecar/auto-promote mechanism wholesale: `sst-supervisor` 2.0.0 + `sst-manager` 2.0.0 rewritten to a direct-edit-and-commit model (no `SKILL.patch`/`auto-promote`/`proposals`/`promote` machinery; manager authorized to edit base-repo skills directly on user-request OR own judgment); dropped `auto-promote` from all 7 chains + schema + skill-chain.py comment; deleted `sst-promote-skill-proposal/` and `bin/apply-skill-patch.py`; scrubbed `sst-sanitize-transferable` 1.1.0, `sst-chain-driver` 1.2.2, README, CLAUDE.md, templates, manager-bot.py `/promote` verb; retired `tests/test_phase32.py`, added `tests/test_phase40.py` (19 cases incl. active-surface grep-guard); 218 green, validator clean. Implemented by sst-dev-cycle; closed manually after the cycle hit error_max_turns post-validator without committing, at 2026-06-03T01:00:00Z
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

- [hard] 43.1+43.2+43.3 close the sanitize→commit seam in `sst-dev-cycle` §5 + `sst-dev-review §0.2` (sanitize no longer the last `/skill` before commit; `git commit` is the final action) + recovery-first reviewer (commit a healthy-but-uncommitted cycle at the START of its turn) — fixes the recurring `contract_violation` halt that blocks reliable looping; user request + 2026-06-15 run-log diagnosis (spec Phase 43, highest priority)
- [medium] 43.4+43.5 relax `bin/skill-chain.py` `contract_violation` kill (don't abort when the reviewer recovers the cycle) + regression guard/tests (no sanitize `/skill` immediately before commit; recovery-first + relaxed-kill) — spec Phase 43; depends on 43.1-43.3
- [hard] 41.1+41.2 author the `sst-tester` transferable (`skills/framework/sst-tester/SKILL.md`) + the tester→reviewer findings contract (run-log `tester-findings.{md,json}` schema + a `tests/fixtures` sample) — new `dev → tester → review` chain stage that drives the running app in a browser between implement and review; user request 2026-06-15 (spec Phase 41, root dependency)
- [medium] 41.3+41.4+41.9+41.10 reviewer consumes run-log tester findings + insert `sst-tester` into the framework dev chains + dev writes `tester-guidance.md` (else `[skip-tester]` pre-empt) + `bin/skill-chain.py` honors the pre-empt (skip tester → straight to review) — spec Phase 41; depends on 41.1/41.2
- [hard] 41.5+41.6 author the `ssp-cm-tester` wrapper (CM ports 5003/3000, `web/e2e` specs, `web/e2e/.auth/state.json` reuse) + insert into `claim_management/.claude/chains/cm-cycle.yaml` + mirror the findings-read in `ssp-cm-dev-review` — spec Phase 41; CM rollout, depends on 41.1-41.4
- [medium] 41.7+41.8 clean-exit + artifact-hygiene enforcement (zero in-tree artifacts, guaranteed teardown, no orphan procs/ports) + tooling/install/docs wiring (`bin/install-skills.sh`, `bin/check-ssp-sync.py`, `README.md`, `CLAUDE.md`) — spec Phase 41; closes the phase
- [hard] 42.1+42.2 spec the unified chain-run CLI + merge `drive-chain.py`'s wrapper (budget/`--max-cycles`/telegram/profile/label) natively into `bin/skill-chain.py` so all flags live in one parser (no more `-- ` forwarding) — collapse skill-chain/drive-chain/overnight/skill-batch into one entrypoint; user request 2026-06-15 (spec Phase 42)
- [medium] 42.3+42.4+42.5+42.6+42.7 `--overnight` preset + fold `skill-batch.py` into a `--batch` mode + `drive-chain.py`/`skill-batch.py` deprecation shims + migrate `*-chain-driver` skills/cron/docs to the single runner + unified-flag-matrix tests — spec Phase 42; depends on 42.1/42.2

