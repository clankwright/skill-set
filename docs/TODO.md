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

- 29.1 [medium] rate-limit retry now uses --resume <session_id> to restore prior session; continuation prompt "continue" replaces bootstrap; +6 tests (49→55 green) — by sst-dev-cycle at 2026-05-21T21:30:00Z
- 28.8 [easy] fix sst-manager truncation hint to say "run /status <persona> for full digest"; also fix notify-telegram.sh; +2 tests (42→44 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-21T20:10:00Z
- [easy] strip "Multi-project bot conventions" from cm-manager/SKILL.md; generic routing now lives in transferable sst-manager §1; v1.0.0→v1.0.1 — by sst-dev-cycle at 2026-05-21T18:10:00Z
- 28.7 [medium] make /status persona-aware: latest_digest(persona) filters <persona>_*.txt, sst-manager digest naming updated to <persona>_<utc>.txt, /status handler requires token; +5 tests (37→42 green); Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-21T17:00:00Z
- 28.6 [easy] fix /feedback empty-body error to include required <project> token; +1 test (36→37 green) — by sst-dev-cycle at 2026-05-21T15:45:00Z
- 28.5 [easy] /help text + README.md updated: per-command `<project>` token shown as required, "Multi-project tip" replaced with "REQUIRED...except /ping, /help, /projects"; +8 tests (28→36 green) — by sst-dev-cycle at 2026-05-21T14:10:00Z
- 28.3 [hard] hoist multi-project routing from proprietary cm-manager into transferable sst-manager: project-token-as-first-arg routing table in §1, per-persona pause file `manager-paused-<persona>` honored in §0.2 + §Operating principles, refusal reply references `/projects` dynamic list; new `route_queue_payload` helper in `bin/manager-bot.py` with 15 tests (28→43 green); sst-manager v1.10.0→v1.11.0; Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-21T08:55:00Z
- 28.4 [medium] fix _discover_manager_personas to skip transferable sst-manager (no transferable: in frontmatter); +4 tests; 15→18 tests green — by sst-dev-cycle at 2026-05-21T01:10:00Z
- 28.1+28.2 [medium] TELEGRAM_LABEL env var on notify-telegram.sh + drive-chain.py coordination + /projects bot command + /help extension; 15 tests green — by skill-set-dev at 2026-05-21T00:10:00Z
- 27.14 [easy] retroactive sst-sanitize-transferable on sst-dev-cycle/SKILL.md (7d7eb87): must-fix=0, should-fix=0, nit=0; findings file updated; audit trail closed — by skill-set-dev at 2026-05-04T00:22:15Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [medium] [should-fix] 29.2 `bin/skill-chain.py:run_skill_with_retry` session-id threading untested at retry-loop level; add integration test patching `run_skill` to simulate rate-limit hit and assert second call gets `resume_session_id` — review of e5350be


