# transferable-skills TODO (handoff doc)

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

- bc3ec9c Phase 8.5: lift short-video-generator + social-promoter; first proprietary counterpart
- 795041d Phase 8.4: lift email-control-loop, agent-orchestrator
- 9c5d5c0 Phase 8.3: lift llm-judge-ranker, translator
- c1bec46 Fix YAML parse failure in editorial-pass frontmatter; harden validator
- 9d98937 Phase 8.2: lift literary-critic, iterative-writer, editorial-pass
- 1d61ac5 Phase 8.1: lift web-research, fact-checker, output-selector
- 21ea214 Add skill-chain definitions as a first-class concept
- 5b6a064 Phase 7 + sanitize pivot: lift non-dev transferables; replace regex leak-check with skill-based sanitization
- 9ccd6ba Phase 6: CI workflow + frontmatter validator + leak-check refinements
- 7363463 Phase 5: manager skill + Telegram bot + service units

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- Phase 9 `Document the loop flag + YAML field in README.md` — reason: spec Phase 9 tail item; the runner/schema support ships this cycle but the user-facing README still only describes one-shot chains.
- Phase 9 `Add at least one transferable chain that uses loop: N by default` — reason: spec Phase 9 tail item; validates the YAML field against a real consuming flow (likely candidate: an iterative-writer or dev-cycle-with-review loop).
- Phase 8.6 end-to-end smoke: chain `web-research → editorial-pass → social-promoter` against a real consuming project with clean supervisor verdict — reason: spec Phase 8 tail item, Phase 8.1-8.5 lifts already complete.
- Phase 6 `Push to public GitHub repo` — reason: `git remote -v` is empty; blocks open-source release work.
- Phase 2 `User runs bin/install-skills.sh -y to deploy the updated dev-cycle/dev-review into ~/.claude/skills/` — reason: user action, still pending.
