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
  - <sha-short> <one-line summary> — by <skill-name> at <utc-iso>
  Trim to the most recent 10 entries; older history lives in docs/SPEC.md phase blocks and `git log`.
-->

- 5fc1223 Phase 10 rename: all 23 transferables to sst- prefix; cross-refs, chain YAMLs, docs, templates updated; sst- prefix enforced by validator — by claude-code at 2026-04-24T00:30:00Z
- 55e6693 Phase 10 start: distinct-name validator rule + sst-/ssp- prefix convention in SPEC — by claude-code at 2026-04-24T00:15:00Z
- b623cf6 Revert install target segregation: harness only discovers direct children under ~/.claude/skills/ — by claude-code at 2026-04-24T00:00:00Z
- bb4fdb8 Rename repo transferable-skills → skill-set; segregate global install path under ~/.claude/skills/skill-set/ — by claude-code at 2026-04-23T23:08:58Z
- 34cb36a Phase 9: optional chain looping + dogfood CLAUDE.md — by claude-code at 2026-04-23T12:31:40Z
- bc3ec9c Phase 8.5: lift short-video-generator + social-promoter; first proprietary counterpart
- 795041d Phase 8.4: lift email-control-loop, agent-orchestrator
- 9c5d5c0 Phase 8.3: lift llm-judge-ranker, translator
- c1bec46 Fix YAML parse failure in editorial-pass frontmatter; harden validator
- 9d98937 Phase 8.2: lift literary-critic, iterative-writer, editorial-pass

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- [Phase 10] Install-time safety net in `bin/install-skills.sh`: when target diverges from source beyond frontmatter, show diff and require per-skill confirmation (skip in `-y` mode unless `--force`) — reason: spec Phase 10; protects hand-edited targets from silent overwrite.
- [Phase 10] Rename user's diverged `~/.claude/skills/linkedin-easy-apply/` to `ssp-linkedin-easy-apply`, update frontmatter (`name: ssp-linkedin-easy-apply` + `transferable: sst-linkedin-easy-apply`), back up canonical copy outside `~/.claude/` — reason: spec Phase 10; first application of the new convention.
- Phase 9 `Document the loop flag + YAML field in README.md` — reason: spec Phase 9 tail item; the runner/schema support ships this cycle but the user-facing README still only describes one-shot chains.
- Phase 9 `Add at least one transferable chain that uses loop: N by default` — reason: spec Phase 9 tail item; validates the YAML field against a real consuming flow (likely candidate: an sst-iterative-writer or dev-cycle-with-review loop).
- Phase 8.6 end-to-end smoke: chain `sst-web-research → sst-editorial-pass → sst-social-promoter` against a real consuming project with clean supervisor verdict — reason: spec Phase 8 tail item, Phase 8.1-8.5 lifts already complete.
- Phase 6 `Push to public GitHub repo` — reason: `git remote -v` is empty; blocks open-source release work.
- Phase 2 `User runs bin/install-skills.sh -y to deploy the updated sst-dev-cycle/sst-dev-review into ~/.claude/skills/` — reason: user action, still pending.
