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

- Phase 12 spec block: efficiency wins + multi-loop orchestrator. After 9 sdrai-cycles ($73.59 / 4h / ~95% spec completion), three structural inefficiencies surfaced (same-root fragmentation, supervisor flat fee on clean runs, unused loop mode) plus one missing role (active orchestrator that drives a multi-iteration run + Telegrams progress live, distinct from cadence-based sst-manager). Six new tail items queued: same-root carveout in sst-dev-cycle §1, same-root tagging in sst-dev-review §5, sst-supervisor fast-path on clean, adopt loop mode on a transferable chain, new sst-orchestrator skill (+ bin/orchestrate-chain.py wrapper), Phase 12 acceptance check (≥25% cost reduction target on multi-iteration runs vs Phase 11 baseline) — by claude-code at 2026-04-25T02:00:00Z
- skill-chain.py: snapshot-write MANIFEST.json after each skill so the auto-supervisor (always last in the chain) actually sees it. Run 25-T00-55-27Z exposed that the supervisor's "MANIFEST.json missing" note was a real chain-runner ordering bug, not an artifact: top-level MANIFEST.json was only written at end-of-main, AFTER all skills (including the supervisor) finished. Fix: run_iteration now takes chain_meta and writes a merged snapshot (chain-level fields + accumulated skill records) to iter_log_dir/MANIFEST.json before any skill runs and after each one completes; in_progress flag tells consumers the file is pre-final. Supervisor §Inputs prose bumped to v1.4.1 to acknowledge its own record won't appear in the snapshot (don't flag self-absence as a defect) — by claude-code at 2026-04-25T01:30:00Z
- sst-supervisor v1.3.0 → v1.4.0: supervisor-tool-discipline patch. Observed run 12-33-37Z had supervisor reach for Edit on .claude/skills/, get denied, then "fall back to sidecar per off-mode treatment" — a silent mode downgrade not in Phase 11's contract. Root cause: §3 routing table described what to write but not how, and the helper-script rule was 100 lines later at §Permissions. Inlined the apply-skill-patch.py invocation directly under §3's routing table; added "A tool-permission denial is NOT a mode downgrade" to Operating principles (auto-promote mode is set by the chain YAML at run start, not by which tool fails mid-run). Also promoted the pending sdrai-dev-review v1.2.0 sidecar into SKILL.md via the helper (the 12-33-37Z finding itself was well-scoped: §2.3 now names the project's canonical `--ignore` invocation, pre-empting the 784-vs-738 test-count gotcha) — by claude-code at 2026-04-24T22:45:00Z
- sst-supervisor v1.2.0 → v1.3.0: anti-scope-creep gate. §3 now requires a change-intent table (kind, section, motivating transcript-line citation) for every line-level change BEFORE drafting; row count must be ≤ finding count. §6 verdict records the table verbatim for audit. Operating principles elevate "every proposed line change cites a transcript line — no citation, no change" to top-level. Closes the Phase 11 tail item that fell out of the first sdrai-cycle's orphan "landing surface" bullet — by claude-code at 2026-04-24T06:15:00Z
- Phase 11 turn-budget + scope-creep remediation: harness now passes --max-turns 100 so supervisor runs doing proprietary + transferable + sanitize + verdict stop terminating cleanly mid-workflow at the undocumented ~31-turn ceiling (claude-code#16963). Trimmed orphan "Public landing surface" scope creep from the first Phase 11 run's proprietary sdrai-dev-review v1.1.0 + transferable sst-dev-review v1.1.0 sidecar, re-applied both via apply-skill-patch.py. Phase 11 SPEC updated with two tail items (supervisor scope-creep gate + framework-wide "stop if dirty" audit for supervisor-managed .claude/skills/) — by claude-code at 2026-04-24T06:00:00Z
- Phase 11 permissions fix round 2: bypassPermissions still prompts on .claude/skills/ Edits in practice. Built bin/apply-skill-patch.py (Python helper that atomically replaces SKILL.md / SKILL.patch.md under approved roots); supervisor now routes every skill write through Bash(apply-skill-patch.py) instead of Edit/Write. Script invocation pre-allowed in ~/.claude/settings.json. sst-supervisor v1.2.0 with rewritten Permissions contract — by claude-code at 2026-04-24T05:45:00Z
- Phase 11 permissions fix: harness switched from --dangerously-skip-permissions to --permission-mode bypassPermissions so the supervisor's direct-overwrite path into .claude/skills/ actually works (skip-permissions empirically still prompts there despite its help text). sst-supervisor v1.1.1 with updated permissions contract; SPEC.md Phase 11 block updated — by claude-code at 2026-04-24T05:15:00Z
- sst-dev-cycle v1.0.2 + framework handoff contract: Just-shipped format drops commit SHA (a commit can't contain its own hash; amend-based workarounds leave dangling references); skill, templates, CLAUDE.md, SPEC.md, sst-dev-review aligned to the new format — by claude-code at 2026-04-24T04:45:00Z
- 93bf49b Phase 11: auto-promote field on chain schema (off | proprietary | all, default proprietary); sst-supervisor rewritten to route direct-overwrite vs SKILL.patch.md sidecar by scope + mode; sst-promote-skill-proposal rewritten to scan sidecars across project/harness/master-repo and promote via atomic rename — by claude-code at 2026-04-24T04:00:00Z
- 2e9e1d3 Phase 10 correction: trimmed the 17 sst-* skills that were installed in adc9ea8 but had no prior bare-name presence. Harness now holds only the 6 sst-* replacements (sst-dev-cycle, sst-dev-review, sst-lead-generation, sst-domain-seo-research, sst-linkedin-networking, sst-sanitize-transferable) + ssp-linkedin-easy-apply + vps-email-setup — by claude-code at 2026-04-24T01:10:00Z

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

- Phase 12 `sst-dev-cycle §1 same-root carveout` — reason: spec Phase 12 efficiency-win 1; same-root multi-surface follow-ups (e.g. 7.7.E.1+E.2) currently fragment into separate cycles, each paying ~$2.50 fixed overhead; bundling under the <300-LoC, disjoint-files guard saves ~$6 per pair without violating small-scope discipline.
- Phase 12 `sst-dev-review §5 same-root tagging` — reason: spec Phase 12; (group with <root>) annotation on review-spawned follow-ups is what makes the §1 carveout above pickable. Pair with the dev-cycle change.
- Phase 12 `sst-supervisor fast-path on clean` — reason: spec Phase 12 efficiency-win 2; ~5 of 9 sdrai cycles produced no findings yet supervisor still spent $0.97–1.45 each. §0.5 keyword-scan pre-check + clean-deploy verification short-circuits to a one-line verdict; never applies when prior verdict says escalate.
- Phase 12 `Adopt loop mode on a transferable chain` — reason: spec Phase 12 efficiency-win 3 + Phase 9 + Phase 11 tail items consolidated. Set loop: 3 on chains/dev-cycle-with-review.yaml, document the YAML field + CLI flag in README.md, validates the convergence test (Phase 11 tail).
- Phase 12 `sst-orchestrator + bin/orchestrate-chain.py` — reason: spec Phase 12; missing top-level role distinct from cadence-based sst-manager. Drives skill-chain.py --loop N, posts Telegram updates per iteration boundary, halts on --max-budget-usd / --max-cycles / supervisor-escalation. Proprietary counterpart supplies watched-chain + chat ID + budget defaults.
- Phase 12 `Acceptance: ≥25% cost reduction on multi-iteration runs vs Phase 11 baseline` — reason: spec Phase 12 close item; a real sdrai-cycle with all four wins live, measured against the $73.59 / 9-cycle baseline.
- Phase 11 `Update transferable chains under chains/ to set auto-promote explicitly + document the field in README.md` — reason: spec Phase 11 tail item; schema + skill routing shipped this cycle but the existing chains all rely on the default and the README still doesn't mention the mode.
- Phase 11 `End-to-end loop convergence test` — reason: spec Phase 11 tail item; verify two consecutive iterations of the same synthetic should-fix finding converge on iteration 2 (improved skill applied) instead of re-filing on iteration 3+.
- Phase 9 `Document the loop flag + YAML field in README.md` — reason: spec Phase 9 tail item; the runner/schema support ships this cycle but the user-facing README still only describes one-shot chains.
- Phase 9 `Add at least one transferable chain that uses loop: N by default` — reason: spec Phase 9 tail item; validates the YAML field against a real consuming flow (likely candidate: an sst-iterative-writer or dev-cycle-with-review loop).
- Phase 8.6 end-to-end smoke: chain `sst-web-research → sst-editorial-pass → sst-social-promoter` against a real consuming project with clean supervisor verdict — reason: spec Phase 8 tail item, Phase 8.1-8.5 lifts already complete.
- Phase 6 `Push to public GitHub repo` — reason: `git remote -v` is empty; blocks open-source release work.
- Phase 2 `User runs bin/install-skills.sh -y to deploy the updated sst-dev-cycle/sst-dev-review into ~/.claude/skills/` — reason: user action, still pending.
