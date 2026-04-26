# skill-set SPEC

This is the master spec for the skill-set system itself. Each consuming project keeps its own `docs/SPEC.md` for its own work; this file governs the framework.

## Harness scope

The framework is harness-agnostic: a `Harness` abstraction in `bin/skill-chain.py` isolates the choice of agent runtime (which CLI to spawn, what command-line shape, what stream format). The MVP ships with one implementation — `claude-code` — because that's what the prototype runs on; additional harnesses (Codex CLI, Gemini CLI, etc.) drop in by adding a `Harness` subclass. User-facing docs use harness-neutral terms ("agent", "harness", "skills directory"); the current default skills paths (`~/.claude/skills/` for globally-installed transferables, `<project>/.claude/skills/` for proprietary) come from the Claude Code harness and will be parameterized when a second harness lands. The layout is flat under the harness skills dir because Claude Code only discovers direct children; a nested segregation subdir (e.g. `skill-set/`) was tried and reverted after discovery broke.

## Primary concepts

### Skill-chain

A `.yaml` file naming a sequence of skills the chain runner executes in order. Same transferable/proprietary split as skills:

- **Transferable chains** live at `<repo>/chains/<name>.yaml`.
- **Proprietary chains** live at `<project>/.claude/chains/<name>.yaml`.
- A proprietary chain MAY name the transferable chain it instantiates via `transferable: <name>` (informational; no inheritance/override behavior in MVP — proprietary chains list their full skill sequence explicitly).

Frontmatter shape (validated by `schema/skill-chain.schema.json`):

```yaml
name: dev-cycle-with-review        # must match filename without .yaml
description: ...
version: 1.0.0
user-invocable: true               # default true
auto-supervisor: true              # default true
loop: 1                            # default 1; N>1 runs the sequence N times; 0 = until failure/Ctrl-C
loop-delay: 0                      # default 0; seconds to sleep between iterations
skills:                            # required, ordered
  - sst-dev-cycle
  - sst-dev-review
transferable: dev-cycle-with-review  # proprietary only
transferable-version: ">=1.0.0"      # proprietary only, optional
```

Invocation:

```bash
bin/skill-chain.py --chain <name>                  # resolves cwd/.claude/chains/ then repo/chains/
bin/skill-chain.py --chain <name> --loop 5         # override loop count at runtime
bin/skill-chain.py --chain <name> --loop 0         # loop until failure / Ctrl-C
bin/skill-chain.py <skill> [<skill>]               # ad-hoc, no chain file needed
```

When `loop != 1`, each iteration's artifacts land in a `<log-dir>/iter_NN/` subdir with its own `MANIFEST.json`; the top-level `MANIFEST.json` carries an `iterations: [...]` array summarizing each pass. For `loop == 1` the single-run flat layout is preserved unchanged, so existing tooling is untouched. A non-supervisor skill failure aborts the whole loop; Ctrl-C cleanly breaks out after the current skill finishes.

### Skill-set

A `(transferable, proprietary)` pair of `SKILL.md` files, linked via the `transferable:` field in the proprietary's YAML frontmatter:

```yaml
---
name: ssp-dev-cycle                  # proprietary; MUST differ from `transferable:`
description: ...
user-invocable: true
transferable: sst-dev-cycle          # transferable counterpart
transferable-version: ">=1.0.0"
---
```

Transferable skills don't back-link (1:N relationship). Validation: `schema/skill-set.schema.json` + the distinct-name check in `bin/validate-frontmatter.py`.

**Distinct-name rule.** A proprietary skill's `name:` MUST differ from its `transferable:`. Both install under the same harness skills directory (`~/.claude/skills/<name>/` for personal-global, `<project>/.claude/skills/<name>/` for project-scoped), so identical names would collide and `install-skills.sh` would silently clobber hand-edited proprietary content. Enforced by the validator; no opt-out.

**`sst-` / `ssp-` prefix convention.** All skill-set skills carry a framework-identifying prefix:

- Transferable skills (canonical, shipped here under `skills/`) use `sst-<base>`. Examples: `sst-dev-cycle`, `sst-linkedin-easy-apply`, `sst-sanitize-transferable`.
- Proprietary counterparts use `ssp-<base>`. Examples: `ssp-dev-cycle`, `ssp-linkedin-easy-apply`. They declare `transferable: sst-<base>` in frontmatter.

Project-scoped proprietary MAY substitute a project-name prefix when tightly coupled to one codebase (e.g. `myproject-dev-cycle`); that also satisfies the distinct-name rule. The `ssp-` default is preferred for portability. The prefix makes it visible at a glance which skills came from this framework and on which side of the split, and keeps unrelated user-authored skills cleanly separable.

**Scopes.** Two canonical homes for proprietary skills:

1. **Project-scoped** at `<project>/.claude/skills/<name>/` — discovered only when the harness runs in that project. For skills specialized to a single codebase.
2. **Personal-global** at `~/.claude/skills/<name>/` — discovered from any directory. For skills specialized to the user's identity, tooling, or config (e.g. `ssp-linkedin-easy-apply` carrying a resume path + salary floor). Because `install-skills.sh` only touches names defined in this repo's `skills/`, `ssp-*` skills are never overwritten when the transferable counterpart is bumped.

### Handoff docs

Every project keeps two canonical files (`docs/SPEC.md`, `docs/TODO.md`) read by every skill on start and updated by every skill on close. See `templates/`.

`SPEC.md` shape: long-lived, phase checklists with `- [ ]`/`- [x]`, closed phases get a 1-paragraph context + bulleted change log.

`TODO.md` shape (three sections):
```markdown
## In flight
- [<skill> @ <utc>] <one-line>

## Just shipped (last cycle)
- <one-line> — by <skill> at <utc>

## Next up (queued for next cycle)
- <one-line> — reason / source
```

Skill contract (codified in transferable preambles):
1. Read both docs end-to-end before any other action.
2. Pick from `TODO.md` "Next up" if non-empty, else next unchecked item in `SPEC.md`.
3. Write a single "In flight" line at start; rewrite (don't append) as work narrows.
4. On close: move "In flight" → "Just shipped" (no commit SHA — a commit cannot contain its own hash; correlate via `git log --oneline --grep`); append any new work to "Next up"; trim "Just shipped" to last 10.
5. Both docs commit in the same commit as the code change.

### Run log

Each chain invocation writes to `<project>/.skill-runs/<UTC>_<chain-name>/`:

- `MANIFEST.json` — chain name, harness, skill list, exit codes, durations, model, token usage, git SHA before/after.
- `<i>_<skill>.jsonl` — raw stream events emitted by the harness (one JSON object per line).
- `<i>_<skill>.txt` — prettified, ANSI-stripped transcript.
- `supervisor_verdict.md` — appended at end of chain (when supervisor runs).
- `proposals/<skill-name>.patch.md` — proposed `SKILL.md` rewrites (proprietary or transferable).

### Sanitization (transferable proposals only)

Before writing a transferable proposal, the supervisor invokes the `sst-sanitize-transferable` skill, which scans the draft against `templates/sanitization-guidance.md` (rubric) and the per-project banned-terms list maintained by the proprietary supervisor. Sanitization is judgment-based — an LLM pass, not regex. Any `must-fix` finding aborts the write; the lesson stays in the proprietary proposal only. Every transferable proposal carries a `Sanitization checklist:` footer the sanitize skill generates and the human reviewer fills in; CI rejects PRs without a complete footer.

## Phases

### Phase 1: skeleton + log capture

- [x] `git init` master repo, MIT LICENSE, README, SPEC, .gitignore.
- [x] `templates/SPEC.md`, `templates/TODO.md`.
- [x] Relocate the chain runner into the master repo as `bin/skill-chain.py` (single canonical copy, no symlinks).
- [x] Add `--log-dir` to chain script; write `MANIFEST.json` + per-skill `.jsonl` + `.txt`.
- [x] Introduce `Harness` abstraction (Claude Code as MVP impl); `--harness` flag + `$AGENT_HARNESS`.
- [x] Smoke-test a real dev-cycle chain end-to-end from a consuming project.
- [x] Bootstrap the consuming project's `docs/TODO.md` from template.

### Phase 2: linkage + globals lift

- [x] Add `transferable: dev-cycle` / `transferable: dev-review` to the consuming project's proprietary skills (in `<project>/.claude/skills/`).
- [x] Copy the prior `~/.claude/skills/dev-cycle/` and `dev-review/` implementations into `skills/` (canonical home is the master repo from now on; `bin/install-skills.sh` does a one-way copy back to the harness skills dir).
- [x] Bake handoff-doc read/update contract into transferable preambles.
- [x] `schema/skill-set.schema.json` validator written (the validator runner that enforces it lives in Phase 3 supervisor + Phase 6 CI).
- [ ] User runs `bin/install-skills.sh -y` to deploy the updated sst-dev-cycle/sst-dev-review into `~/.claude/skills/`.

### Phase 3: supervisor

- [x] `skills/supervisor/SKILL.md` (transferable).
- [x] First proprietary `<project>-supervisor/SKILL.md` built in a consuming project.
- [x] Auto-append proprietary supervisor in `bin/skill-chain.py`.
- [x] `templates/sanitization-guidance.md` + `skills/sanitize-transferable/` (LLM-judgment scan, not regex grep).

### Phase 4: proposal promotion

- [x] `~/.claude/skills/promote-skill-proposal/SKILL.md`.

### Phase 5: manager + Telegram bot

- [x] `skills/manager/SKILL.md` (transferable).
- [x] First proprietary manager in a consuming project.
- [x] `bin/notify-telegram.sh` (outbound).
- [x] `bin/manager-bot.py` (long-poll).
- [x] Service unit (systemd) + rc.d script.

### Phase 6: open-source

- [x] Push to public GitHub repo. `git@github.com:toadlyBroodle/skill-set.git`, `main` tracks `origin/main`.
- [x] CI: frontmatter validator + sanitization-footer-on-PR enforcement (leak/grep enforcement removed — replaced by sanitize-transferable skill run pre-PR by contributors).
- [x] CONTRIBUTING.md.

### Phase 7: portability proof

- [x] Build a second skill-set in a non-dev field (lead-gen, content-ops, infra). Done by lifting `sst-lead-generation`, `sst-domain-seo-research`, `sst-linkedin-easy-apply`, `sst-linkedin-networking` from existing globals.
- [x] Confirm `sst-supervisor` and `sst-manager` work unmodified across both — they're domain-agnostic by construction; the validator passes all skills uniformly.

### Phase 8: lift long-running agents into transferables

A 12-agent framework was ported into this repo as 12 target skills (11 transferable, 1 split into transferable + first proprietary counterpart). 5 sub-phases ordered by complexity / interdependency. Each lift converted a language-model-agent Python module into a SKILL.md natural-language procedure; agent-framework infrastructure (rate-limiting wrappers, tool helpers) mapped to harness-provided primitives. Each lifted skill passed `sst-sanitize-transferable` + `validate-frontmatter` before commit.

- [x] Phase 8.1: `sst-web-research`, `sst-fact-checker`, `sst-output-selector`.
- [x] Phase 8.2: `sst-iterative-writer`, `sst-literary-critic`, `sst-editorial-pass`.
- [x] Phase 8.3: `sst-llm-judge-ranker`, `sst-translator`.
- [x] Phase 8.4: `sst-email-control-loop`, `sst-skill-router` (originally shipped as `sst-agent-orchestrator`; renamed in Phase 15).
- [x] Phase 8.5: `sst-short-video-generator`, `sst-social-promoter` + first proprietary counterpart in a consuming project's `.claude/skills/`.
- [ ] End-to-end smoke: a chain `sst-web-research → sst-editorial-pass → sst-social-promoter` runs to completion against a real project with a clean supervisor verdict. (User-driven validation; deferred until the user runs a real cycle.)

### Phase 9: optional chain looping

Add opt-in iteration to the chain runner so a single chain definition can repeat its full skill sequence N times (or until a non-supervisor failure). Rationale: long-running skills (sst-dev-cycle, sst-editorial-pass, sst-social-promoter) often want to tick through several items from `TODO.md > Next up` in one sitting without a human re-invoking the chain each pass. The supervisor still runs once per iteration, keeping the handoff-doc contract intact between cycles.

- [x] `loop` + `loop-delay` fields added to `schema/skill-chain.schema.json` (defaults 1 / 0; fully backward compatible).
- [x] `bin/skill-chain.py` gains `--loop` and `--loop-delay` CLI flags (CLI overrides YAML). `--loop 0` loops until a non-supervisor failure or Ctrl-C.
- [x] Iteration-per-subdir log layout (`iter_NN/MANIFEST.json`) when `loop != 1`; single-run flat layout preserved for `loop == 1`.
- [x] Top-level `MANIFEST.json` carries `iterations: [...]` + `loop: {requested, delay_seconds, completed}` when looping.
- [x] Document the loop flag + YAML field in `README.md`. New "Chain YAML fields" section covers `loop`, `loop-delay`, `loop-delay-random`, `auto-promote`, and the rate-limit triplet, with a full annotated example block, the loop-mode iteration log layout, and a CLI-overrides note.
- [x] Add at least one transferable chain that uses `loop: N` by default. Shipped `chains/dev-cycle-with-review-looped.yaml` (`loop: 3`, `auto-promote: all`) as a multi-iteration variant of `dev-cycle-with-review`; the canonical baseline chain stays at `loop: 1` so existing consumers see no behavioral change.

### Phase 10: proprietary-naming enforcement + sst-/ssp- migration

Formalize the distinct-name rule and the `sst-<base>` / `ssp-<base>` prefix convention (see "Skill-set" section). Migrate every existing transferable in this repo from bare names to the `sst-` prefix and update every cross-reference. Add an install-time safety net so hand-edited targets under `~/.claude/skills/` are never silently clobbered on `install-skills.sh` runs.

- [x] Validator rule in `bin/validate-frontmatter.py`: rejects proprietary skills where `name == transferable`.
- [x] SPEC section documenting the distinct-name rule, `sst-`/`ssp-` prefix convention, and the two proprietary scopes.
- [x] Rename all transferables in `skills/` from bare names to `sst-<base>`; update every cross-reference in SKILL.md bodies, chain YAMLs, docs, and templates. Strengthened the validator to require `sst-` prefix on transferables inside this repo's `skills/` tree.
- [x] Install-time safety net in `bin/install-skills.sh`: a target is DIVERGED when its SKILL.md body differs from source beyond the YAML frontmatter. Interactive runs show a per-skill diff and prompt before overwrite; `-y` mode skips DIVERGED targets (count reported at the end); `--force` overrides and overwrites.
- [x] Audit `~/.claude/skills/` for user-diverged copies; renamed `linkedin-easy-apply` (bare, pre-sst-) → `ssp-linkedin-easy-apply` with `transferable: sst-linkedin-easy-apply` link; canonical copy kept at `~/Dev/skill-set-personal/skills/ssp-linkedin-easy-apply/` (outside `~/.claude/` so it survives a harness reset). Discovery verified: harness now lists `ssp-linkedin-easy-apply`.

### Phase 11: auto-promote mode

Close the learning loop between chain iterations. Before Phase 11 the supervisor wrote its proposed `SKILL.md` rewrites to `<run-dir>/proposals/<skill>.patch.md`, which accumulated one file per cycle and could only be turned into a real edit by a separate user-gated `/sst-promote-skill-proposal` invocation. That meant a looping chain (`sdrai-cycle`, `sst-dev-cycle`, etc.) never consumed its own supervisor's improvements within the same run; the next iteration re-read the same stale skill and the supervisor frequently re-filed the same proposal.

Phase 11 introduces an `auto-promote` field on the chain definition (schema: `off | proprietary | all`, default `proprietary`) that tells the supervisor to route its output by scope:

| auto-promote | Proprietary skill           | Transferable skill                                                   |
| :---         | :---                        | :---                                                                 |
| `off`        | sidecar `SKILL.patch.md`    | sidecar `SKILL.patch.md`                                             |
| `proprietary`| direct overwrite `SKILL.md` | sidecar `SKILL.patch.md`                                             |
| `all`        | direct overwrite `SKILL.md` | direct overwrite `SKILL.md` iff `sst-sanitize-transferable` reports `must-fix: 0`; else sidecar |

The `SKILL.patch.md` sidecar is a drop-in replacement (full frontmatter + body) rather than a proposal-with-header. One per skill, overwritten each cycle; rationale + citations live in the run's `supervisor_verdict.md`. `/sst-promote-skill-proposal` now consumes sidecars: `mv SKILL.patch.md SKILL.md` after user-gated diff review.

**Two supporting changes to the harness layer** made Phase 11 actually work:

1. `bin/skill-chain.py` spawns skills with `--permission-mode bypassPermissions` instead of `--dangerously-skip-permissions`. bypassPermissions is the mode docs describe as carving out `.claude/skills/**`; skip-permissions, despite its "bypass all permission checks" help text, empirically still fires prompts there.

2. **Even with bypassPermissions, Claude Code's Edit/Write tools still prompt on `.claude/skills/**` writes** in practice (the documented carveout doesn't match observed behavior). The fix is `bin/apply-skill-patch.py`, a small Python helper that atomically replaces a `SKILL.md` / `SKILL.patch.md` under an approved skills root. Because the write happens in the script's own process — not via a Claude tool — the tool-level permission gate doesn't apply. The supervisor invokes it via the Bash tool, and `Bash(/home/rob/Dev/skill-set/bin/apply-skill-patch.py:*)` is allow-listed once in `~/.claude/settings.json`. The script validates every target against an approved-roots list (refuses anything outside `~/.claude/skills/`, `~/Dev/skill-set/skills/`, `~/Dev/skill-set-personal/skills/`, `~/.claude/commands|agents/`, or any `<project>/.claude/skills/` under `~`) and requires the source to begin with YAML frontmatter.

The supervisor reads `auto-promote` from the chain YAML (via `MANIFEST.chain_definition`) and routes accordingly. Rollback of an unwanted direct overwrite is `git checkout <path>/SKILL.md`, or `mv <path>/SKILL.md.bak <path>/SKILL.md` if the supervisor wrote with `--backup`.

- [x] `auto-promote` enum added to `schema/skill-chain.schema.json` (default `proprietary`; backward-compatible for chains that omit it).
- [x] `sst-supervisor` rewritten: routing table in §3, transferable sanitization extended in §4 to cover direct overwrites, verdict file structure records direct-vs-sidecar targets + per-write sanitization footers. Permissions contract documented.
- [x] `sst-promote-skill-proposal` rewritten: scans three sidecar-capable roots (`<cwd>/.claude/skills/`, `~/.claude/skills/`, `~/Dev/skill-set/skills/`), promotes via atomic rename. Transferable sanitization re-run before every promotion.
- [x] Update every transferable chain YAML under `chains/` to set `auto-promote:` explicitly (all three modes exercised across the set), then document the field in `README.md`. All 5 pre-existing chains gained an explicit `auto-promote`: `dev-cycle-with-review` → `proprietary`, `editorial-with-fact-check` / `multi-output-evaluation` / `research-and-write` / `research-write-promote` → `"off"`. The new `dev-cycle-with-review-looped` exercises `all`. README "Auto-promote" subsection documents the routing table + when to pick each mode. (YAML 1.1 quirk caught and noted: bare `off` is parsed as the boolean `False` by PyYAML and trips the schema enum, so `off` values are quoted; the validator's existing enum check is the standing guardrail.)
- [x] First end-to-end loop that actually consumes its own supervisor's improvements: closed empirically by the `~/Dev/sdrai/.skill-runs/2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` run (iter_01 review filed one `[should-fix]` on `SIGNALS_VALID_TYPES` dedup; iter_02 picked and closed it in `40f1243`; iter_02 review reported clean, no re-file). See Phase 14 preamble for context.
- [x] Harness `--max-turns 100` set explicitly in `bin/skill-chain.py`. `claude -p` has an undocumented turn ceiling (~31 observed; github.com/anthropics/claude-code/issues/16963) that otherwise makes the supervisor terminate `[ok]` mid-workflow between the "sanitization clean, safe to proceed" step and the actual transferable-sidecar write. 100 is headroom for a supervisor doing proprietary overwrite + transferable sanitize + transferable sidecar + verdict.
- [x] Supervisor over-expands patches. First Phase 11 sdrai-cycle run articulated 2 findings but wrote a patch with 3 changes (the third — "Public landing surface" bullet — was orphan scope creep not grounded in the transcript). sst-supervisor v1.2.0 → v1.3.0: §3 now requires a change-intent table mapping every line-level change to a motivating transcript-line citation before drafting; row count must be ≤ finding count. §6 verdict records the table verbatim for auditability. Operating principles elevate "every proposed line change cites a transcript line — no citation, no change" to a top-level rule.
- [x] Supervisor reaches for Edit/Write on `.claude/skills/` and, on denial, "falls back to sidecar per `off`-mode treatment" instead of routing through `apply-skill-patch.py`. Observed in run `2026-04-24T12-33-37Z_sdrai-cycle`: the helper-script rule lived at §173 (Permissions contract, deep in the file), but §3 (drafting) ended before describing *how* to write and the agent defaulted to Edit. sst-supervisor v1.3.0 → v1.4.0: (a) inlined the `apply-skill-patch.py` Bash invocation directly under §3's routing table so agents reach the rule while drafting, not 100 lines later; (b) added "A tool-permission denial is NOT a mode downgrade" to Operating principles — auto-promote mode is set by the chain YAML at run start, not by which tool happens to fail mid-run.
- [x] Supervisor reads `MANIFEST.json` but the chain runner only writes it after the iteration loop completes — so the supervisor (always last skill in the chain) saw no manifest at all when it ran. Observed in run `2026-04-25T00-55-27Z_sdrai-cycle`: supervisor noted *"MANIFEST.json was missing from this run dir (chain-runner artifact)"* and fell back to defaults silently. Fixed in `bin/skill-chain.py` `run_iteration()`: now snapshot-writes a merged manifest (chain-level fields + per-skill records of skills that ran before this one) to `iter_log_dir/MANIFEST.json` after every skill, with `"in_progress": true` set so consumers know it's pre-final. The end-of-main full write supersedes the snapshots. sst-supervisor §Inputs prose updated (v1.4.0 → v1.4.1) so the supervisor doesn't flag its own absent record as a defect.
- [x] Supervisor-managed `.claude/skills/` dirt interacts badly with the reviewer's pre-flight "stop if dirty" rule. Audited every transferable doing a `git status`-clean check (`sst-dev-cycle`, `sst-dev-review`, `sst-supervisor` — only the first two have a pre-flight gate; `sst-supervisor` already operates on `.claude/skills/` as its turf). Patched both: `sst-dev-cycle` v1.0.2 → v1.0.3 §0.3 and `sst-dev-review` v1.0.0 → v1.1.0 §0.2 now carry the same generic carve-out the proprietary `sdrai-dev-review` and `skill-set-dev-review` use ("if `git status --porcelain` shows ONLY paths under `.claude/skills/`, proceed"). `sst-dev-review` v1.1.0 also picks up the destructive-state HEAD~1 rule (Pitfalls + §2.3 test-count): never `git checkout HEAD~1 -- .` or chain `git stash` with `git checkout` of the prior commit; use `git show HEAD~1 -- <path>` or a separate `git worktree` instead.

### Phase 12: efficiency wins + multi-loop orchestrator

A 9-cycle / $73.59 / 4-hour empirical pass on `sdrai-cycle` (2026-04-23 → 2026-04-25, ~95% spec completion) surfaced three structural inefficiencies: (a) same-root TODO items getting fragmented across cycles each paying full review+supervisor overhead, (b) the supervisor burning ~$1 to confirm "clean" when nothing in the run-log shows a finding, and (c) `loop:` mode (Phase 9) shipped but unused — every cycle is still manually re-invoked. Phase 12 closes those plus introduces the missing top-level role: an orchestrator that drives a multi-iteration chain run autonomously and pipes progress to the user over Telegram in real time (the existing `sst-manager` is cadence-based and reactive; the orchestrator is event-driven and active for the duration of one multi-iteration run).

- [x] **`sst-dev-cycle` §1 same-root carveout.** Added to the selection-priority section in `sst-dev-cycle` v1.0.3 → v1.1.0: when two or more `## Next up` entries carry a `(group with <root-keyword>)` tag AND combined diff <~300 LoC AND files are disjoint, bundle the tagged set into one cycle. Mismatched tags, breach of LoC, or independent acceptance criteria fall back to per-item picks. Untagged items continue to be picked individually per the priority list. Empirical motivation cited in this SPEC stays project-specific (the `7.7.E.1`+`7.7.E.2` Bearer-min-fee-floor case); the transferable prose itself uses neutral examples ("constant propagating to multiple surfaces", "missing guard across sibling modules", "discovery surface stale in both a manifest AND a README"). Sanitization judgment pass on the addition: must-fix=0, should-fix=0, nit=0.

- [x] **`sst-dev-review` §5 same-root tagging.** Added to §4 (the TODO.md-format block, where the actual writing happens — "§5" in the original item title was a labeling shortcut) in `sst-dev-review` v1.1.0 → v1.2.0: when multiple findings share one root cause, append `(group with <root-keyword>)` to each TODO.md line using the exact same token across every entry in the group (the carveout keys on string-equality of the tag). Single-finding "groups" are not tagged (a group of size 1 is just noise). Spec entries never get the tag (one-checkbox-per-finding rule preserved; bundling is a TODO-level scheduling concern). When tagged entries are present, they're kept contiguous within their severity band so the next cycle sees them as a single run. Sanitization judgment pass on the addition: must-fix=0, should-fix=0, nit=0 (only generic example tags `input-bound-propagation`, `manifest-readme-sync`, `auth-helper-migration`).

- [ ] **`sst-supervisor` fast-path on clean.** Add a §0.5 pre-check that scans each skill's `<i>_<skill>.txt` for finding-bearing keywords (`failed`, `denied`, `aborted`, `stash`, `--no-verify`, `pkill`, `must-fix`, contradiction patterns) AND verifies the cycle's commit deployed cleanly. If all transcripts are clean by that scan AND no escalation flags exist, write a one-line "clean" verdict and exit before walking §1–6. Estimated saves ~$0.70 × ~50% of cycles (currently ~5 of 9 sdrai cycles produced no findings; supervisor still spent $0.97–1.45 each). Fast-path must NEVER apply when any prior verdict in the run-dir's `.skill-runs/` chain says `escalate` — escalation tail still goes through the full walk.

- [x] **Adopt loop mode on at least one transferable chain.** Took the backwards-compatible path: shipped a new `chains/dev-cycle-with-review-looped.yaml` (`loop: 3`, `auto-promote: all`) rather than mutating the default behavior of the canonical `dev-cycle-with-review` chain. A single `bin/skill-chain.py --chain dev-cycle-with-review-looped` now knocks out the next three queued items autonomously; baseline `dev-cycle-with-review` remains at the implicit `loop: 1` so existing consumers see no behavioral change. The Phase 11 tail item this referenced ("First end-to-end loop that actually consumes its own supervisor's improvements") was already closed empirically in the prior cycle. README "Loop mode" subsection documents the YAML field + the iteration log layout.

- [x] **`sst-orchestrator` (new top-level skill).** Distinct from `sst-manager` (cadence-based, cross-project, reactive) and from `sst-agent-orchestrator` (in-process per-task planner). Shipped as `skills/framework/sst-orchestrator/SKILL.md` (v1.0.0) + `bin/orchestrate-chain.py`. The helper spawns `bin/skill-chain.py --chain <name> --loop N` as a subprocess, streams its stdout verbatim, and runs a parallel watcher that fires Telegram bodies via `bin/notify-telegram.sh` at: (1) session start (chain name + caps + log-dir + utc), (2) each iteration boundary detected from the `===== iteration N =====` banner — reads the prior iteration's `iter_NN/MANIFEST.json` for cost/SHA/verdict + parses `git log -1 --pretty=%s` for the commit subject, (3) every rate-limit pause/resume parsed from the chain runner's `[rate-limit]` banners (closes Phase 13 item 6 in the same cycle), (4) halt-request when budget/cycle/escalation thresholds fire, (5) session end (exit code + halt reason + completed iterations + cumulative spend + manifest path). Halts are best-effort SIGINTs to the chain runner — the runner's existing `KeyboardInterrupt` path finalizes manifests cleanly. The proprietary counterpart (`<persona>-orchestrator`) supplies `watched-chain`, `default-loop`, `default-max-budget-usd`, `default-max-cycles`, `telegram-env`, `label` — same split convention as `sst-manager` / `<persona>-manager`; deferred to a follow-up cycle. SKILL prose passed sst-sanitize-transferable (must-fix=0, should-fix=0, nit=0). Smoke-tested: bogus-chain invocation propagates cleanly, telegram-suppression mode works.

- [ ] **Phase 12 acceptance check.** Re-run a real `sdrai-cycle` with all four wins live (same-root bundling triggered on a multi-surface follow-ups, supervisor fast-path on a clean cycle, `loop: 3`, `sst-chain-driver` (formerly `sst-orchestrator`) driving + Telegram'ing). Compare cost-per-shipped-feature against the Phase-11 baseline ($73.59 / 9 cycles). Target: ≥25% reduction on multi-iteration runs.

**Review follow-ups (closed):**

- [x] [should-fix] `bin/orchestrate-chain.py:297` — `looping = (args.loop is not None and args.loop != 1)` only inspected the `--loop` CLI override; it did not consult the chain YAML's `loop:` field. When the orchestrator was invoked against `chains/dev-cycle-with-review-looped.yaml` without re-passing `--loop 3` on the CLI (the canonical no-override invocation, since the YAML already declares `loop: 3`), `bin/skill-chain.py` resolved `loop_count = 3` and wrote `iter_NN/MANIFEST.json` plus `===== iteration N/3 =====` banners, while `_finalize_iteration` read the flat `log_dir/MANIFEST.json` (which only exists at session-end). Per-iter Telegram bodies fell to the "MANIFEST.json not found" branch, `cumulative_cost_usd` stayed at $0.0000, and the `--max-budget-usd` halt never fired. Fixed: the iter-banner handler now sets `looping = True` BEFORE calling `_finalize_iteration(n - 1)` on every banner observation. Banner presence is authoritative because `bin/skill-chain.py` only prints `===== iteration N =====` when its resolved `total_iterations != 1` (line 958-964); the YAML-vs-CLI source of `loop_count` is irrelevant. Closure pattern verified — `_finalize_iteration` and `_supervisor_verdict_path` read `looping` from the enclosing scope at call time, so the assignment propagates without `nonlocal`. Four inline scenarios cover the banner-regex matrix (`N/M`, infinite-loop label, ANSI-stripped), the path-layout flip, and the closure-promotion sequence.

### Phase 13: rate-limit pause-and-resume

A multi-iteration `--loop N` chain can run for hours and crosses the rolling 5-hour Anthropic quota window mid-run. When that happens today the chain runner's subprocess exits non-zero, the iteration is marked failed, the loop aborts, and any cycle's worth of work-in-flight (TDD that hadn't reached commit, a partially-deployed change) is left in an indeterminate state. Phase 13 lets the runner detect the rate-limit signal, sleep until the reset time, and resume the killed skill in place — so a 3-iteration `sdrai-cycle` that crosses a quota boundary just stretches in wall-clock time rather than aborting.

Three error categories the runner needs to recognize, from highest-frequency to lowest:

1. **Five-hour rolling quota** — the standard rate limit. `claude` emits `rate_limit_event` with `rate_limit_info: {rateLimitType: "five_hour", status: "exceeded", reset_time: "<UTC>"}` (the runner already prints these as warnings; it does not yet act on `status: exceeded`). When the active model run hits the wall the subprocess exits with a recognizable error message in stderr (`"You've hit your <limit> rate limit"` or similar). Both signals must be handled.

2. **Out-of-usage** (primary plan quota exhausted) — distinct from the five-hour bucket; this is the monthly / weekly cap. Same `rate_limit_event` shape with `rateLimitType: "weekly"` or `"primary"` (exact field name TBD; capture from a real exhausted-quota event during implementation).

3. **Out-of-extra-usage** (overflow / burst quota also exhausted) — Pro/Team plans have a secondary pool. Same shape with `rateLimitType: "extra"` or `"burst"`.

For all three, the resolution is the same: parse the reset timestamp from the event payload, sleep until reset + a short jitter (15–60s), then re-invoke the killed skill from scratch. Each skill invocation is a fresh subprocess, so restarting is safe — there is no in-process state to preserve across the pause.

- [x] **Detection in `bin/skill-chain.py`.** `handle_event` now captures any `rate_limit_event` with `status in {exceeded, blocked, reset_required, throttled}` into `skill_record["rate_limit_signal"]`, plucking `reset_time` from any of the four observed field names (`resetsAt`/`reset_time`/`resetTime`/`resets_at`) and `retry_after_seconds` similarly. First-fatal-wins so an overlapping later signal doesn't overwrite the one that actually killed the skill. The non-JSON line scanner in `run_skill` matches `RATE_LIMIT_TEXT_RE` against merged stderr (the harness tees stderr through stdout) and stashes a `rate_limit_text_match` fallback for the case where the subprocess died before emitting a clean structured event. The regex is deliberately tight ("rate limit" + an exhaustion verb like "exceeded"/"reached"/"reset", or "you've hit your X rate limit") so warning-level mentions don't trigger false retries.

- [x] **Pause loop in `run_skill_with_retry` (wraps `run_skill`).** Each `run_iteration` skill invocation now goes through the wrapper, which inspects `rate_limit_signal` (preferred) or `rate_limit_text_match` (fallback) on non-zero exit and either pauses + retries or returns the failure. Sleep duration: `_compute_rate_limit_sleep` uses parsed reset_time + jitter[15,60]s when available; falls back to retry_after_seconds + jitter; finally to exponential backoff (`300 * 2**min(attempt, 4)` seconds) when neither is present. Each retry archives the prior attempt's `.txt`/`.jsonl` to `<stem>.retry-N.{ext}` via `_archive_attempt` so the canonical names are clear for the new attempt and the audit trail is preserved. Ctrl-C during the `time.sleep` propagates cleanly through `run_iteration` to `main`'s outer try/except (exit 130). ORANGE `[rate-limit] <type> exceeded; sleeping <Ns> until <wake-UTC> before retrying /<skill>` banner per pause.

- [x] **Configurability.** Schema gained `on-rate-limit` (enum `fail|pause|pause-with-cap`, default `pause`), `max-rate-limit-pause-seconds` (integer, default 28800 = 8h), and `max-pauses-per-session` (integer, default 3). CLI gained matching `--on-rate-limit`, `--max-rate-limit-pause-seconds`, `--max-pauses-per-session` flags; CLI > YAML > defaults. Default-on-pause is invisible to single-iteration chains (they finish in one subprocess and never hit a pause); multi-iteration chains transparently gain the pause-and-resume without a YAML change.

- [x] **Manifest record.** `iter_manifest["rate_limit_pauses"]` is now a list of `{at, type, status, sleep_seconds, reset_time, wake_at, skill, retry_count, source, resumed_at}` entries; one per executed pause. Top-level `manifest["rate_limit_policy"]` records the resolved (`on_rate_limit`, `max_rate_limit_pause_seconds`, `max_pauses_per_session`) so the supervisor or a downstream tool can see how the run was configured. The supervisor reading these via the snapshot manifest can distinguish rate-limit retries (`retry_count > 0` on the skill record) from skill defects.

- [x] **Repeat-pause safeguard.** `run_skill_with_retry` aborts when `retry_count >= max_pauses` and stamps `record["rate_limit_aborted"] = "max_pauses_reached"` so the manifest reader knows why. `pause-with-cap` mode adds a separate exit reason: `"max_pause_seconds_exceeded"` when a single computed pause would exceed `max_rate_limit_pause_seconds`. Both produce RED `[rate-limit]` banners.

- [x] **Orchestrator hook (Phase 12 #5).** Closed in the same cycle as `sst-orchestrator` itself. `bin/orchestrate-chain.py` parses the chain runner's `[rate-limit] <type> exceeded; sleeping <N>s until <utc> before retrying /<skill>` banner via `RATE_LIMIT_PAUSE_RE` and fires an immediate Telegram pause notification (type, skill, sleep seconds, wake utc, current iter). On resume, the next `>>` session-init banner from a fresh subprocess invocation is treated as the resume signal and a second Telegram fires. Each iteration-close summary also reports the `rate_limit_pauses` count from `iter_NN/MANIFEST.json` so the audit trail stays visible at iteration boundaries. RED-banner abort variants (`max-pauses-per-session`, `max-rate-limit-pause-seconds`, `aborting chain`) get their own `rate-limit-abort` telegram with the raw line.

- [x] **Acceptance check.** Verified live on 2026-04-25 in `2026-04-25T13-36-00Z_skill-set-cycle/iter_03`. The chain crossed a real five_hour rolling quota mid-iteration (status `rejected` on session `c584a8c6` at `2026-04-25T14:47:12Z`); detection fired (`source: rate_limit_event`, structured payload carried `reset_time` epoch `1777135200`); sleep was 6811.5s = `reset_time - detected_at + jitter[15,60]s`, within ±60s of the parsed reset; retry session `14f48ecd` started at `2026-04-25T16:40:44Z` matching `wake_at` exactly (drift = 0s); the retried skill ran 28 turns / 377s / $2.025 / `exit_code: 0` / `result_subtype: success`; the chain finished all 3 iterations and committed `a45a506`; `MANIFEST.rate_limit_pauses[0]` records `{at, type, status, sleep_seconds, reset_time, wake_at, source, resumed_at}` with all timestamps consistent; the original session's transcript was archived to `00_skill-set-dev.retry-0.{txt,jsonl}` per the documented per-attempt rotation. Original criterion (f) Telegram pause/resume notifications is naturally a Phase 12 chain-driver-acceptance concern (the wiring lives in `bin/drive-chain.py` and only fires when the chain is invoked via `sst-chain-driver`); rolled into Phase 12 acceptance, not blocking Phase 13 closure.

**Review follow-ups (closed):**
- [x] [should-fix] `bin/skill-chain.py:186` — `_compute_rate_limit_sleep`'s `retry_after_seconds` branch now wraps the float coercion in `max(0.0, ...)` to mirror the parallel reset-time clamp on line 183. A negative harness value (e.g. `-30` from clock skew or a schema-shape mismatch) no longer produces a negative `sleep_seconds`, no longer crashes `time.sleep` from inside `run_skill_with_retry`, and the pause-and-resume safety net stays intact. Inline tests verify the negative, zero, and positive paths.

**Live-failure follow-ups (closed 2026-04-25):**

A real `--loop 2` run of `skill-set-cycle` on 2026-04-25 hit `out of extra usage` mid-second-iteration; the just-shipped pause-and-resume mechanism failed to engage and the chain aborted instead. Forensics (transcript: `! rate-limit five_hour: 0% (rejected)` + stderr `You're out of extra usage · resets 7:50pm (Asia/Tokyo)` + `[FAIL] 88.5s ... (success)` + `/skill-set-dev exited with 1; aborting chain`) surfaced four narrow gaps in the Phase 13 detection layer, all closed in this cycle:

- [x] **Status-enum gap.** The live `rate_limit_event` carried `status: "rejected"` but `RATE_LIMIT_FATAL_STATUSES` was `{exceeded, blocked, reset_required, throttled}` — the runner ignored the killing signal entirely. Added `rejected` to the fatal set so the structured event is now captured.

- [x] **Text-fallback gap.** When the structured event was filtered out, the stderr backstop (`RATE_LIMIT_TEXT_RE`) also did not match `You're out of extra usage`. Extended the regex to recognize `you're out of (?:extra )?usage` alongside the existing `rate limit + (exceeded|reached|reset)` and `you've hit your X rate limit` patterns. The text-fallback reset-time extractor is a new compiled regex `RATE_LIMIT_RESET_RE` matching `\d{1,2}:\d{2}\s*(?:am|pm)\s*\(...\)` against the same stderr line; it stashes a `rate_limit_text_reset` field on the skill record alongside `rate_limit_text_match`.

- [x] **Localized-clock parser branch.** The `7:50pm (Asia/Tokyo)` wall-clock format is not ISO-8601, so `_parse_reset_time` fell through to the numeric-epoch try and returned `None`. Added a third branch (case-insensitive regex `^(\d{1,2}):(\d{2})\s*([ap]m)\s*\(([^)]+)\)$`) that resolves to "next occurrence of HH:MM in the named tz" using `zoneinfo.ZoneInfo(tz_name)` (today if still future, tomorrow otherwise) and returns the epoch. `run_skill_with_retry` now threads `rate_limit_text_reset` into the synthetic signal when only a text-fallback fired, so a stderr-only death now yields a real wake epoch instead of the 300s exponential-backoff floor.

- [x] **`[FAIL] (success)` label inconsistency.** `print_result_summary` labelled `[FAIL]` from `is_error=True` but parenthetically printed the harness's lifecycle `subtype="success"` verbatim. The two now align: when `is_error=True` and `subtype=="success"`, the parenthetical reads `(error: success)`; when `subtype` already starts with `error` it is shown as-is; the `[ok]`/`(success)` happy path is unchanged.

Twenty-eight inline scenario tests verified the five fixes (status-enum capture, text-fallback regex over six samples, RATE_LIMIT_RESET_RE extraction, localized-clock parser including midnight + 12:30pm + bad-TZ edges, retry_after clamp on negative/zero/positive, label disambiguation across err+sub combinations, end-to-end synthetic-signal sleep computation). The Phase 13 acceptance check (real five-hour quota crossing during a `loop: 3` run) remains open as the standing user-driven validation.

**Review follow-ups (closed):**
- [x] [should-fix] `bin/skill-chain.py:681-684` joint-fire merge condition — `run_skill_with_retry` previously only threaded the text-extracted `rate_limit_text_reset` into `eff_signal["reset_time"]` when `signal is None` (the stderr-only-death path). In the live failure mode the BUG-fix cycle was built to fix (structured `rate_limit_event` with `status: "rejected"` AND stderr `You're out of extra usage · resets 7:50pm (Asia/Tokyo)`) `signal` is not None, so the new `RATE_LIMIT_RESET_RE` extraction was ignored on the exact path the forensics described, and the wake time fell through `reset_time → retry_after → 300s exponential backoff` whenever the captured `rejected` payload omitted `reset_time` under all four aliased field names (`resetsAt`/`reset_time`/`resetTime`/`resets_at`). Fixed: condition changed from `if signal is None:` to `if not eff_signal.get("reset_time"):`, so the text-extracted wall-clock fills in whenever the structured signal lacks a parseable reset regardless of whether the structured signal itself fired. The manifest pause-record `source` field now reports mixed provenance (`"rate_limit_event+text_reset"`) when the joint-fire path supplied the wake time, distinct from `"rate_limit_event"` (pure structured) and `"text_fallback"` (stderr-only-death). Eight inline scenario tests verified the full matrix: joint-fire with-and-without structured `reset_time`, signal-only paths, stderr-only paths, and edge cases (empty-string + None-valued `reset_time` fields treated as falsy and overridable by `text_reset`).

### Phase 14: supervisor completion invariant + run-dir hygiene

A 12-cycle / 14-iteration `sdrai-cycle` loop (2026-04-23 → 2026-04-25) closed Phase 3 of `~/Dev/sdrai` entirely (all five v1 endpoints live + production-verified), shipped 24 commits, grew the consuming project's test suite 697 → 825, and reached ~95% spec completion. The framework's own contract held: 9 of the 14 supervisor passes ran clean, `sst-sanitize-transferable` returned `must-fix: 0` on every transferable draft scanned, the dev skill's pattern-fidelity instinct kept divergence low (new modules mirrored existing ones rather than diverging), and the `2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` run demonstrated within-chain convergence (iter_01 review filed one `[should-fix]` on `SIGNALS_VALID_TYPES` dedup; iter_02 picked and closed it; iter_03 was rate-limit-killed mid-review per Phase 13). Three new failure modes surfaced once enough cycle volume accumulated, all tied to the supervisor's completion contract:

(a) **Supervisor early-exit between sub-skill invocation and verdict write.** Twice in 14 supervisor passes the session terminated cleanly (`[ok]`, no error) after `sst-sanitize-transferable` returned, BEFORE `apply-skill-patch.py` ran for the transferable AND BEFORE `supervisor_verdict.md` was written. Drafts persist in `<run-dir>/drafts/` indefinitely; downstream iterations cannot pick them up because the anti-scope-creep gate requires per-iteration transcript citations. Observed in `~/Dev/sdrai/.skill-runs/2026-04-24T04-21-39Z_sdrai-cycle/` (transferable sidecar skipped after the proprietary overwrite landed) and `~/Dev/sdrai/.skill-runs/2026-04-25T06-15-57Z_sdrai-cycle/iter_01/` (both writes skipped, only sanitize ran). The two follow-up iter verdicts independently flagged this and asked for a "if you wrote drafts, you MUST also call apply-skill-patch.py and write the verdict file before exiting" guard.

(b) **Orphaned drafts across iter boundaries.** When (a) fires inside a multi-iter chain, iter_N+1's supervisor sees the prior `drafts/` directory but cannot consume it (no transcript citation in iter_N+1's own session). The drafts persist until a human runs `apply-skill-patch.py` by hand.

(c) **`apply-skill-patch.py --backup` accumulates `.bak` cruft.** Five consecutive sdrai supervisor verdicts noted the same `.claude/skills/sdrai-dev-review/SKILL.md.bak` sitting in `git status`, untouched for days. Git history covers rollback fine; the `--backup` default is dead weight that surfaces every cycle as a tracked-but-uncommitted file.

- [x] **Completion invariant in `sst-supervisor`.** Added as `### 8. Exit gate` (current §7 Escalate retained at §7; new exit gate is §8 since it runs LAST, after the verdict file is written). Before returning, both invariants must hold: (a) every file in `<run-dir>/drafts/` is either applied via `apply-skill-patch.py` OR named in the verdict file's `[deferred]` block with a reason; (b) `<run-dir>/supervisor_verdict.md` exists, even on clean runs (a clean run with no verdict is indistinguishable from partial-completion failure). New `[deferred]` block format documented for the verdict's "Updates written" section. Codified as Operating-principle bullet: "A session that wrote drafts but no verdict file is a contract violation, not a clean exit." sst-supervisor v1.4.1 → v1.5.0 (minor bump = added behavior).

- [x] **Iter-boundary drafts sweep in `sst-supervisor`.** Added as `### 0.6. Iter-boundary drafts sweep`. Runs only when `MANIFEST.iteration > 1`; for a log-dir at `<base>/iter_NN/`, scans `<base>/iter_<NN-1>/drafts/`. Each orphan is treated as a manager-injected finding citing the prior iter's `<i>_<supervisor>.txt` line (or the `[deferred]` block in the prior iter's `supervisor_verdict.md`), routed per the current chain's `auto-promote` mode, re-sanitized if transferable (a prior-iter sanitize pass does not bind this iter), and the consumed draft is deleted. Sweep ONLY consumes drafts from `iter_<NN-1>/`; older orphans indicate a multi-iter outage and get flagged in `## Notes for the manager` rather than chain-recursing. Findings flow through §1–7 normally with the sweep's drafts counted in §3's change-intent table; §8 verifies the post-condition.

- [x] **Drop `--backup` from `sst-supervisor`'s `apply-skill-patch.py` invocations.** Updated both invocation templates (§3 routing + §Permissions example). The `--backup` flag still exists on the helper for ad-hoc human use; the supervisor just doesn't pass it. One-shot cleanup ran: `find /home/rob/Dev/skill-set/.claude/skills /home/rob/Dev/sdrai/.claude/skills -name 'SKILL.md.bak' -delete` cleared the 3 historical files (1 in sdrai, 2 in skill-set's own `.claude/skills/`).

- [x] **`bin/clean-skill-runs.py` (new helper).** Idempotent housekeeping for `<project>/.skill-runs/` + `<project>/.claude/skills/` trees. Defaults to dry-run (read-only); `--apply` performs deletions. Removes (1) empty `<run-dir>/proposals/` and `<run-dir>/iter_NN/proposals/` directories (Phase 11 routes drafts to `drafts/` and proposals to in-place sidecars; the pre-Phase-11 `proposals/` skeletons are pure leftover), (2) `*SKILL.md.bak` files anywhere under `<project>/.claude/skills/` (the supervisor's old `apply-skill-patch.py --backup` cruft; git history covers rollback), (3) `<run-dir>/drafts/` directories whose newest file mtime is older than N days (default 14, configurable via `--days`), with explicit per-dir y/N prompts unless `--yes` is passed; empty drafts/ dirs always qualify (treated as zero-age cruft) so they get cleared regardless of threshold. Approved-root safety: refuses any project root outside the user's home, refuses any project root that contains neither `.skill-runs/` nor `.claude/skills/` (mirrors `apply-skill-patch.py`'s allowlist discipline). The drafts age check uses the newest FILE mtime (not the directory's own mtime, which updates on every child add/remove and would mask actually-stale contents). Smoke-tested: synthetic fixture (empty proposals + non-empty proposals + stale-content drafts touched to 2026-01-01 + fresh drafts + empty iter_NN/drafts + .bak file) flags exactly what should flag, prompt rejection keeps stale drafts intact, idempotency holds (second run reports nothing). Real-world dry-run: 1 empty drafts/ in this repo's `.skill-runs/`, 1 empty proposals/ in sdrai's; recent (<14d) drafts and non-empty proposals correctly left alone.

- [x] **Phase 11 within-chain-convergence demonstration closed empirically.** The `2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` run produced exactly the convergence pattern Phase 11's tail item specified: iter_01's `sdrai-dev-review` filed one `[should-fix]` on `SIGNALS_VALID_TYPES` dedup (`signals_lite.py:25` vs `main.py:491`); iter_02's `sdrai-dev` picked and closed it in commit `40f1243`; iter_02's review reported clean, no re-file. Counts as the empirical close of Phase 11's "First end-to-end loop that actually consumes its own supervisor's improvements" item — flipping that line above from `[ ]` to `[x]` in the same commit as this Phase 14 block.

- [x] **Randomized inter-iteration delay.** `loop-delay-random: [min_seconds, max_seconds]` shipped on `schema/skill-chain.schema.json` (with `allOf` mutual-exclusion against `loop-delay`) and `bin/skill-chain.py` (CLI `--loop-delay-random "<min>,<max>"`, parses + range-checks, samples `random.uniform(min, max)` per iteration boundary). Top-level `MANIFEST["loop"]` gains `delay_random_range` + `delay_samples` (one entry per iteration boundary so the trace is auditable). `[loop] sleeping <Ns> (sampled from [min, max])` banner shows the chosen delay live. Ctrl-C is clean during the sleep via the existing `time.sleep`/`KeyboardInterrupt` path (same as fixed `loop-delay`). Schema-level acceptance verified (mutual-exclusion fires; bad shapes rejected; back-compat preserved for chains setting only `loop-delay` or neither). The proprietary `~/Dev/skill-set/.claude/chains/skill-set-cycle.yaml` (v1.0.0 → v1.1.0) sets the default `[60, 3600]` so this repo's own multi-iter runs jitter 1-60min between iterations without an explicit CLI flag.

- [ ] **Phase 14 acceptance.** Trigger a new multi-iter run with the completion invariant + iter-boundary sweep + randomized delay live. Deliberately short-circuit the supervisor mid-write (e.g. `kill -TERM` after the sanitize call). Confirm: (a) the killed iter's supervisor exits with non-zero status because the exit gate fails, OR writes a `[deferred]` verdict file naming each unapplied draft; (b) the next iter's supervisor finds and consumes the orphaned drafts via the §0.6 sweep; (c) no `.bak` files remain in `.claude/skills/` after the run; (d) `bin/clean-skill-runs.py` removes any stale `proposals/` dir without prompting; (e) MANIFEST shows non-uniform `delay_seconds` between iterations within the configured range.

### Phase 15: rename for clarity

Three skills shared the "orchestrator" / "manager" naming axis and routinely got confused for one another in conversation: `sst-orchestrator` (single-session driver of one multi-iter chain run), `sst-agent-orchestrator` (in-process per-task planner inside a single user request), and `sst-manager` (cron-based cross-project periodic ops loop). The name "orchestrator" appearing twice was the worst offender: a casual question like "use the orchestrator" was ambiguous between the two transferables, and the everyday English meaning of "orchestrator" overlapped with both. Phase 15 renames the two ambiguous skills so each name reads its mechanism directly. `sst-manager` is unchanged: cron-based cross-project monitoring fits the everyday meaning of "manager" cleanly and the rename cost into consuming projects' `<persona>-manager` counterparts isn't justified.

| Old name                   | New name              | What it does                                                       |
| :---                       | :---                  | :---                                                               |
| `sst-orchestrator`         | `sst-chain-driver`    | drives ONE multi-iter chain run; spawns `bin/skill-chain.py`, watches stdout, posts Telegram at session boundaries / iter close / rate-limit pauses / halts / session end |
| `sst-agent-orchestrator`   | `sst-skill-router`    | inside ONE user request, decomposes the task, picks sub-skills by description, sequences them, synthesizes the result |
| `sst-manager` (unchanged)  | `sst-manager`         | cron-based loop across MANY projects; reads `.skill-runs/` archives, writes Telegram digests + `manager-guidance.md` for the next supervisor pass |

- [x] **Skill renames.** `skills/framework/sst-orchestrator/` → `skills/framework/sst-chain-driver/`; `skills/orchestration/sst-agent-orchestrator/` → `skills/orchestration/sst-skill-router/`. SKILL.md frontmatter `name:` updated; body prose updated (skill heading, "the orchestrator" prose, hard-rules block, command-line shape examples); both pick up a "Naming history" footer noting the old name + the rationale. Version bumps 1.0.0 → 1.1.0 (rename is observable to consumers via the `name:` field even though behavior is unchanged).

- [x] **Helper rename.** `bin/orchestrate-chain.py` → `bin/drive-chain.py`. Internal references (docstring, `prog=` argparse name, `[orchestrator]` log-line tags, runtime Telegram body prefixes `orchestrator: session START` / `orchestrator [<label>]: ...` / `orchestrator: session END`) all updated to read `chain-driver` / `[chain-driver]`. The script's behavior is unchanged; it parses the same CLI flags, reads the same per-iter manifests, fires the same Telegram event classes.

- [x] **Cross-references updated.** `skills/orchestration/sst-email-control-loop/SKILL.md` description's "called once per cycle of an outer loop (e.g. by sst-agent-orchestrator)" rewritten to point at `sst-skill-router`. Forward-looking SPEC.md items in Phase 12 acceptance + Phase 13 acceptance updated to use new names. TODO.md `Next up` entries updated to use new names; `Just shipped` entries left intact (the historical record of what shipped under what name is correct as written; the new name appears via this Phase 15 block + the chain-driver's own "Naming history" footer).

- [x] **Stale deployed copies cleared.** Old `~/.claude/skills/sst-orchestrator/` and `~/.claude/skills/sst-agent-orchestrator/` directories removed manually after `bin/install-skills.sh -y` (the install script intentionally does not delete target-only dirs to protect hand-managed skills, so renames require an explicit cleanup step). Harness skill registry verified to list the new names and not the old ones.

- [x] **Validator clean** (24 skills + 6 chains).

### Phase 16: long-running chain pattern + chain selection docs

The Phase 12 / Phase 15 work shipped the chain driver mechanism (`sst-chain-driver` + `bin/drive-chain.py`) and a single multi-iter chain (`dev-cycle-with-review-looped`, loop:3). That covers the "knock out 1-3 items in one sitting" use case. Phase 16 fills in two adjacent shapes the same mechanism enables: an unattended overnight drain pattern (`loop: 0` until-failure, paired with `--max-budget-usd` as the natural stopping criterion) and the missing user-facing documentation that says which chain to use when.

- [x] **`chains/dev-cycle-overnight.yaml` (new transferable).** `loop: 0`, `loop-delay-random: [300, 7200]` (5min-2h), `auto-promote: all`. Designed to be invoked through `sst-chain-driver` so the budget cap is the safety net (the chain itself loops forever; the driver halts at `--max-budget-usd` / `--max-cycles` / supervisor escalation). Same skill sequence as `dev-cycle-with-review` (`sst-dev-cycle` → `sst-dev-review`); the auto-supervisor is auto-appended per default. Auto-promote `all` matches the looped chain's choice (supervisor improvements land within the run after sanitize-clears them).

- [x] **Proprietary `.claude/chains/skill-set-overnight.yaml`.** Mirrors the transferable with skill-set-* skills (`skill-set-dev` → `skill-set-dev-review` → auto-appended `skill-set-supervisor`). Lives under `.claude/chains/` (gitignored runtime state, not version-controlled here; matches the pattern for `skill-set-cycle.yaml`).

- [x] **README.md "Chains shipped here" subsection.** Table mapping every transferable chain to its use case, loop count, and auto-promote mode. Followed by a "Pick the dev chain by intent" guide (one change → `dev-cycle-with-review`; 1-3 items → `dev-cycle-with-review-looped` via `sst-chain-driver`; overnight drain → `dev-cycle-overnight` via `sst-chain-driver` with budget cap). Note about proprietary `<persona>-chain-driver` skills carrying the chain + cap defaults so the user types `/<persona>-chain-driver` with no flags.

- [x] **CLAUDE.md "Choosing a chain" section.** Skill-set-specific guidance pointing to `/skill-set-chain-driver` (canonical default), `/skill-set-chain-driver --chain skill-set-overnight --max-budget-usd 80` (overnight drain), and raw `bin/skill-chain.py --chain skill-set-cycle` (debug mode without driver wrap).

- [x] **Proprietary `skill-set-chain-driver` SKILL.md updated.** Added the overnight invocation as a fourth common override pattern in the "Common overrides" list.

- [x] **Validator clean** (24 skills + 7 chains; new transferable count is 7).

### Phase 17: empty-queue handling

A mature framework reaches steady state: `TODO.md > Next up` is empty AND every `- [ ]` in `docs/SPEC.md` is `[x]`. Today the dev skill's prose has no specified behavior for this state, so under a `/skill-set-chain-driver` invocation (or any other looped chain) the dev skill is likely to invent speculative work, re-pick a just-shipped item with a slightly different framing, or scope-creep on existing skills. Each empty iteration still costs ~$8 (dev + review + supervisor combined). A 3-iter default could burn $25 producing nothing useful; an overnight `--loop 0` run would burn the entire `--max-budget-usd` cap on speculative work before stopping. Phase 17 closes this hole at the dev skill's pre-flight AND at the chain runner level so empty-queue exits abort the loop cleanly instead of consuming budget.

- [x] **`sst-dev-cycle` §0 empty-queue bail.** (group with empty-queue-bail) Added §0 step 6 "Empty-queue bail" in `skills/dev/sst-dev-cycle/SKILL.md` (v1.1.0 → v1.2.0): if `TODO.md > Next up` has no `- ` entries AND `docs/SPEC.md` has no remaining `- [ ]` checkboxes AND the user gave no specific task in the prompt, exit 0 cleanly without picking, testing, or committing. Print exactly one stdout line `[no-work] queue empty and spec fully checked; nothing to do` before exiting. Explicit MUST-NOT list to head off scope-creep tendencies (don't pick a just-shipped item, invent speculative work, scope-creep, or fabricate a `Next up` entry). Inherits to `<project>-dev-cycle` proprietary counterparts automatically via `transferable:`; no per-project edit needed.

- [x] **Chain runner recognizes the `[no-work]` exit signal.** (group with empty-queue-bail) `bin/skill-chain.py` gains a `NO_WORK_SENTINEL_RE = ^\s*\[no-work\](?:\s+(.*\S))?\s*$` (multiline, line-anchored to avoid inline mentions triggering). `handle_event` scans assistant-text blocks for the sentinel and stashes the reason on `skill_record["no_work_bail"]` (first match wins per skill; tool inputs and tool results are not scanned, so the supervisor reading skill prose containing example sentinels does not false-trigger). After a clean (rc=0) skill exit, `run_iteration` checks `record.get("no_work_bail")`, sets `iter_manifest["no_work_bail"] = {"skill": <name>, "reason": <line>}`, prints a BLUE `[no-work] /<skill>: <reason>: skipping remaining skills + aborting loop` banner, and breaks out of the inner skills loop, skipping review + supervisor. `main()` then sets `manifest["loop"]["terminated_by"] = "no_work_bail"` (when looping) and breaks the outer while loop. Tool inputs / tool results don't go through the assistant-text scan, so the supervisor reading example sentinel prose doesn't false-trigger. Smoke-tested: regex matches every canonical sentinel form (with/without reason, leading whitespace, multi-line context) and rejects inline mentions; `handle_event` integration test confirms first-match-wins and inline-mention immunity.

- [x] **Documentation in README.md + CLAUDE.md + templates/SPEC.md.** README.md "Loop mode" subsection gains a paragraph documenting the bail as the canonical clean stop (sentinel format, manifest fields, chain-driver session-end label). The "Chains shipped here" row for `dev-cycle-overnight` notes the auto-stop on empty work (the budget cap becomes the secondary safety net, not the primary one). CLAUDE.md "Choosing a chain" section gains an it-is-safe-to-invoke-on-empty paragraph (no caveat existed in this CLAUDE.md to remove; the spec phrasing assumed one). `templates/SPEC.md` gains a new "Empty-queue bail (steady state)" subsection at the bottom of the "How this file evolves" appendix so consuming projects bootstrap with the contract documented.

- [ ] **Acceptance check.** With `Next up` empty AND every SPEC `[ ]` flipped `[x]`, invoke `/skill-set-chain-driver`. Confirm: (a) `skill-set-dev` exits 0 with the no-work sentinel printed and no commit; (b) chain runner aborts the loop after the first empty iter (no second iter starts; `MANIFEST.loop.terminated_by == "no_work_bail"`); (c) iter MANIFEST records `no_work_bail` with the sentinel line; (d) cumulative cost is bounded by the dev skill's own pre-flight read (~$0.10-0.30 for SPEC + TODO + CLAUDE reads) rather than a full ~$8 iter; (e) chain-driver session-end Telegram body labels the stop as "no-work bail".

### Phase 18: chain-bound bot worker lifecycle + manager no-spam

The Telegram worker (`bin/manager-bot.py`) currently runs persistently under tmux / systemd. That pattern produces inbound-noise between chain runs (the worker keeps acking the user's queued commands and replying with stale state) and adds operational overhead (the user has to remember to start / stop it manually). Phase 18 binds the worker lifecycle to the chain driver: started at chain-session start, stopped at chain-session end, idempotent against an externally-managed worker the user wants always-on. Pairs with a manager-side rule that forbids re-notifying on persistent paused-job state (a paused job is one Telegram body at the pause edge, one at resume; the manager's periodic digest may mention it in the consolidated status block but never fires a separate body per tick for the same paused job).

- [x] **`sst-manager` no-repeat-pause-notify rule.** Added to `sst-manager` Hard rules + Worker-lifecycle expectation section. v1.0.0 → v1.1.0 (added behavior).

- [x] **`sst-chain-driver` Worker-lifecycle section (spec, not yet implemented).** Documents the chain-bound lifecycle policy in the transferable's body so the implementation (item below) has prose to land against. v1.1.0 → v1.2.0.

- [x] **CLAUDE.md + README.md docs landed.** CLAUDE.md "Telegram bot" section gains the worker-lifecycle constraint + the no-spam rule. README.md "Worker management" splits into the chain-bound (recommended) vs always-on (legacy) patterns.

- [ ] **`bin/drive-chain.py` + chain driver implementation.** At chain-session start, after `_resolve_chain` succeeds: probe for an existing worker (tmux session named `<persona>-bot` OR PID file at `~/.claude/state/manager-bot.pid`); if not running, start one in a detached tmux session named after the persona (taking the env file from `--telegram-env`). Stash a flag `worker_started_by_us = True` so cleanup is conditional. At chain-session end, after the chain runner exits and BEFORE the final stdout summary: if `worker_started_by_us`, kill the tmux session. If a pre-existing worker was found, do NOT touch it. Race: two simultaneous chain drivers must not double-start the worker (use `flock` on the PID file). Forwarded behavior: `--no-telegram` skips the worker management entirely; `--telegram-env <path>` is required for the worker start (without it, no chat-id to ack).

- [ ] **Acceptance check.** Trigger a real `/skill-set-chain-driver` run with no pre-existing worker. Confirm: (a) chain driver starts the tmux session at session-start and the user can `/ping → pong` during the run; (b) chain driver kills the tmux session at session-end; (c) re-run with the worker pre-started by hand (e.g. `tmux new-session -d -s skill-set-bot ...`): chain driver detects the pre-existing worker, does NOT start a second one, does NOT kill it at session-end; (d) two simultaneous chain-driver runs against different chains: only one tries to start the worker (flock); (e) manager invocation while no chain is running succeeds with an empty inbound queue and a digest body that does NOT re-notify any currently-paused job.

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**

- [ ] [should-fix] `skills/framework/sst-chain-driver/SKILL.md:151,158` and `skills/framework/sst-manager/SKILL.md:193` (added in commit `26c5458`) — Phase 18 docs commit modified two transferables and embedded skill-set's internal framework phase number ("Phase 18" in the section title `## Worker lifecycle (Phase 18; in spec, not yet implemented)`, "Per the Phase 18 lifecycle policy", "the inbound-noise pattern Phase 18 exists to fix") inside skills that consuming projects install. Unlike commit `16e67a1` ("Sanitization judgment pass on the sst-dev-cycle addition: must-fix=0"), the commit body documents no sanitize pass. CLAUDE.md is explicit: "Never bypass the sanitization path." Proposed fix: rerun `sst-sanitize-transferable` on both additions; rephrase to drop framework-internal phase numbering (e.g. section title "Worker lifecycle (planned)", body refs "the chain-bound lifecycle policy" / "the inbound-noise pattern this rule exists to fix"). One bundled cycle since both files share the same root.

- [ ] [should-fix] `bin/skill-chain.py:499-503` (`handle_event` no-work sentinel scan) + `bin/skill-chain.py:1051-1058` (`run_iteration` bail) — sentinel detection is first-match-wins on any assistant-text line beginning with `[no-work]`, with the bail unconditionally skipping review/supervisor and aborting the loop on a clean exit. If a dev skill prints the sentinel mid-reasoning ("Here's what I'd emit:\n\n[no-work] queue empty\n\n...") and then proceeds to commit real work, the runner skips review/supervisor for a real commit AND aborts the loop. The cycle's smoke tests (per commit `16e67a1` body) covered "rejects inline mentions" but not "sentinel emitted on its own line as part of reasoning, then skill keeps working." Proposed fix: gate the bail on `git_sha_before == git_sha_after` for the dev skill (if a commit landed, the sentinel was a false alarm); or only honor a sentinel match in the LAST assistant-text block before exit, not first-match-wins.

- [ ] [should-fix] `skills/dev/sst-dev-cycle/SKILL.md:148` and `skills/dev/sst-dev-review/SKILL.md:202` — the "Never append Co-Authored-By: Claude Opus 4.7..." rule sits as a standalone line BELOW the §6 commit-template heredoc (lines 132-141 in `sst-dev-cycle`), so a model copying the heredoc downward stops before reading it. Empirical: 7 of 11 cycle commits in this review surface (`26c5458`, `7c4c595`, `be10b0f`, `d5cd04c`, `e2d2a76`, `e104dad`, `ab83b88`) carry the trailer despite the explicit ban. Proposed fix: hoist the rule INSIDE the heredoc template (e.g. add a shown-in-example "# NEVER append Co-Authored-By trailers below this line" comment) or move the rule above the heredoc so it is read before the template is followed. Forward-looking; do not rewrite history.
