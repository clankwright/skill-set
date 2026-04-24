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

- sst-dev-cycle v1.0.2 + framework handoff contract: Just-shipped format drops commit SHA (a commit can't contain its own hash; amend-based workarounds leave dangling references); skill, templates, CLAUDE.md, SPEC.md, sst-dev-review aligned to the new format — by claude-code at 2026-04-24T04:45:00Z
- 93bf49b Phase 11: auto-promote field on chain schema (off | proprietary | all, default proprietary); sst-supervisor rewritten to route direct-overwrite vs SKILL.patch.md sidecar by scope + mode; sst-promote-skill-proposal rewritten to scan sidecars across project/harness/master-repo and promote via atomic rename — by claude-code at 2026-04-24T04:00:00Z
- 2e9e1d3 Phase 10 correction: trimmed the 17 sst-* skills that were installed in adc9ea8 but had no prior bare-name presence. Harness now holds only the 6 sst-* replacements (sst-dev-cycle, sst-dev-review, sst-lead-generation, sst-domain-seo-research, sst-linkedin-networking, sst-sanitize-transferable) + ssp-linkedin-easy-apply + vps-email-setup — by claude-code at 2026-04-24T01:10:00Z
- adc9ea8 Phase 10 final: installed all 23 sst-* skills into ~/.claude/skills/ and removed 6 stale bare-name dirs (dev-cycle, dev-review, lead-generation, domain-seo-research, linkedin-networking, sanitize-transferable) after diff-audit confirmed no user edits. Harness now shows sst-*/ssp- only — by claude-code at 2026-04-24T01:00:00Z
- 8a32abd Phase 10 install safety net: bin/install-skills.sh now detects DIVERGED targets (body differs beyond frontmatter), skips them in -y mode, prompts interactively, and overrides via --force — by claude-code at 2026-04-24T00:45:00Z
- 5fc1223 Phase 10 rename: all 23 transferables to sst- prefix; cross-refs, chain YAMLs, docs, templates updated; sst- prefix enforced by validator — by claude-code at 2026-04-24T00:30:00Z
- 55e6693 Phase 10 start: distinct-name validator rule + sst-/ssp- prefix convention in SPEC — by claude-code at 2026-04-24T00:15:00Z
- b623cf6 Revert install target segregation: harness only discovers direct children under ~/.claude/skills/ — by claude-code at 2026-04-24T00:00:00Z
- bb4fdb8 Rename repo transferable-skills → skill-set; segregate global install path under ~/.claude/skills/skill-set/ — by claude-code at 2026-04-23T23:08:58Z
- 34cb36a Phase 9: optional chain looping + dogfood CLAUDE.md — by claude-code at 2026-04-23T12:31:40Z
- bc3ec9c Phase 8.5: lift short-video-generator + social-promoter; first proprietary counterpart

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- Phase 11 `Update transferable chains under chains/ to set auto-promote explicitly + document the field in README.md` — reason: spec Phase 11 tail item; schema + skill routing shipped this cycle but the existing chains all rely on the default and the README still doesn't mention the mode.
- Phase 11 `End-to-end loop convergence test` — reason: spec Phase 11 tail item; verify two consecutive iterations of the same synthetic should-fix finding converge on iteration 2 (improved skill applied) instead of re-filing on iteration 3+.
- Phase 9 `Document the loop flag + YAML field in README.md` — reason: spec Phase 9 tail item; the runner/schema support ships this cycle but the user-facing README still only describes one-shot chains.
- Phase 9 `Add at least one transferable chain that uses loop: N by default` — reason: spec Phase 9 tail item; validates the YAML field against a real consuming flow (likely candidate: an sst-iterative-writer or dev-cycle-with-review loop).
- Phase 8.6 end-to-end smoke: chain `sst-web-research → sst-editorial-pass → sst-social-promoter` against a real consuming project with clean supervisor verdict — reason: spec Phase 8 tail item, Phase 8.1-8.5 lifts already complete.
- Phase 6 `Push to public GitHub repo` — reason: `git remote -v` is empty; blocks open-source release work.
- Phase 2 `User runs bin/install-skills.sh -y to deploy the updated sst-dev-cycle/sst-dev-review into ~/.claude/skills/` — reason: user action, still pending.
