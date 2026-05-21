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

- 28.3 [hard] hoist multi-project routing from proprietary cm-manager into transferable sst-manager: project-token-as-first-arg routing table in §1, per-persona pause file `manager-paused-<persona>` honored in §0.2 + §Operating principles, refusal reply references `/projects` dynamic list; new `route_queue_payload` helper in `bin/manager-bot.py` with 15 tests (28→43 green); sst-manager v1.10.0→v1.11.0; Sanitize: must-fix=0 — by sst-dev-cycle at 2026-05-21T08:55:00Z
- 28.4 [medium] fix _discover_manager_personas to skip transferable sst-manager (no transferable: in frontmatter); +4 tests; 15→18 tests green — by sst-dev-cycle at 2026-05-21T01:10:00Z
- 28.1+28.2 [medium] TELEGRAM_LABEL env var on notify-telegram.sh + drive-chain.py coordination + /projects bot command + /help extension; 15 tests green — by skill-set-dev at 2026-05-21T00:10:00Z
- 27.14 [easy] retroactive sst-sanitize-transferable on sst-dev-cycle/SKILL.md (7d7eb87): must-fix=0, should-fix=0, nit=0; findings file updated; audit trail closed — by skill-set-dev at 2026-05-04T00:22:15Z
- 27.13 [easy] sst-dev-cycle/SKILL.md §5 "inline not sufficient" clause added + proprietary mirror v1.3.6→v1.3.7; transferable v1.4.6→v1.4.7; Sanitize: must-fix=0 (inline, single framework-canonical sentence) — by skill-set-dev at 2026-05-03T23:58:45Z
- 27.12 [easy] retroactive sst-sanitize-transferable on sst-dev-review/SKILL.md (d1a3a7e gate bypass): must-fix=0, should-fix=0, nit=0; findings file written; audit trail closed — by skill-set-dev at 2026-05-03T23:58:45Z
- 27.11 [easy] retroactive sst-sanitize-transferable on sst-dev-cycle/SKILL.md (f90e930 Phase 17.5): must-fix=0, should-fix=0, nit=0; findings file written; audit trail closed — by skill-set-dev at 2026-05-03T14:46:20Z
- 27.10 [easy] sst-dev-review halt guard "two files" → "three files" + FUTURE-WORK.md added to halt condition; v1.5.1→v1.5.2; proprietary mirror v1.2.10→v1.2.11; inline sanitize must-fix=0 — by skill-set-dev at 2026-05-03T14:46:20Z
- 17.5 [easy] sst-dev-cycle §0 step 6 bail hardening: [low]-priority non-criterion clause + §1 step 1 paired statement; skill-set-dev mirror v1.3.5→v1.3.6; sst-dev-cycle v1.4.5→v1.4.6; inline sanitize must-fix=0 — by skill-set-dev at 2026-05-03T14:16:31Z
- 27.9 [medium] sst-dev-cycle §5 sanitize-gate added (new section, §5–§9 renumbered to §6–§10); skill-set-dev v1.3.4→v1.3.5 transferable-version bumped; inline sanitize must-fix=0 — by skill-set-dev at 2026-05-03T01:39:42Z
- 27.8 [easy] sst-dev-review §5 git add updated to include docs/FUTURE-WORK.md; §0 stage-narrowly reference updated; proprietary mirror v1.2.9→v1.2.10; transferable v1.5.0→v1.5.1; inline sanitize must-fix=0 — by skill-set-dev at 2026-05-03T01:15:16Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [easy] [should-fix] 28.5 `bin/manager-bot.py:345-364` /help text + `README.md:165,208,210` — three discovery surfaces still describe `/status`, `/objectives`, `/proposals`, `/pause`, `/resume`, `/feedback` without the now-required project token and frame the token as a conditional multi-persona "tip"; `route_queue_payload` refuses every untagged non-agnostic command regardless of persona count. Update per-command usage lines to show `<project>` and reword the tip/README paragraphs to say "required" (not "accepted"), with `/ping`/`/help`/`/projects` as the exception set. — review of 9b898d9
- [easy] Strip the proprietary "Multi-project bot conventions" section (the project-token routing convention + outbound `[cm]` label rule) from `~/Dev/claim_management/.claude/skills/cm-manager/SKILL.md`; what remains is cm-specific overrides only (anything generic now lives in the transferable `sst-manager` §1 routing table). Commit in the claim_management repo, not skill-set. — Reason: SPEC 28.3 explicit follow-up; the generic routing convention has been hoisted to the transferable so the proprietary cm-manager section is redundant.
- [medium] `bin/skill-chain.py` rate-limit pause-and-resume should resume the prior Claude Code session via `--resume <session_id>` instead of spawning a fresh subprocess. Today `run_skill_with_retry` (lines 885-1010) loops back into `run_skill` → `ClaudeCodeHarness.build_command` (lines 482-524), which always builds a cold `claude -p ...` invocation; the prior `session_id` (already captured into `skill_record["session_id"]` at line 693) is dropped. Symptom: a rate-limit hit mid-skill (e.g. 717s / 46 turns into a `/sst-dev-cycle` iteration before any commit) abandons all in-flight context — the retry starts the same item over from a cold context, re-reading spec + TODO from disk. Looks like "started a new agent session" instead of resuming. Was masked previously because most rate-limit hits land between iterations (after a commit/push), where a cold start picks up correctly via on-disk state and looks like resumption. Fix shape: thread `session_id` through `run_skill_with_retry` → `run_skill` → `Harness.build_command(skill_name, *, model, effort, resume_session_id=None)`; `ClaudeCodeHarness` prepends `--resume <id>` when set and replaces the bootstrap prompt with a no-op continuation prompt (e.g. `"continue"`) so the resumed session doesn't re-trigger the skill from scratch. Add a smoke test that the second attempt's command contains `--resume`. — Reason: user report 2026-05-03 — rate-limit during long sst-dev-cycle iteration on redaiteam repo wasted ~$3.32 of cache + 46 turns of work that didn't survive the retry.


