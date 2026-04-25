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

- [ ] Push to public GitHub repo.
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
- [x] Phase 8.4: `sst-email-control-loop`, `sst-agent-orchestrator`.
- [x] Phase 8.5: `sst-short-video-generator`, `sst-social-promoter` + first proprietary counterpart in a consuming project's `.claude/skills/`.
- [ ] End-to-end smoke: a chain `sst-web-research → sst-editorial-pass → sst-social-promoter` runs to completion against a real project with a clean supervisor verdict. (User-driven validation; deferred until the user runs a real cycle.)

### Phase 9: optional chain looping

Add opt-in iteration to the chain runner so a single chain definition can repeat its full skill sequence N times (or until a non-supervisor failure). Rationale: long-running skills (sst-dev-cycle, sst-editorial-pass, sst-social-promoter) often want to tick through several items from `TODO.md > Next up` in one sitting without a human re-invoking the chain each pass. The supervisor still runs once per iteration, keeping the handoff-doc contract intact between cycles.

- [x] `loop` + `loop-delay` fields added to `schema/skill-chain.schema.json` (defaults 1 / 0; fully backward compatible).
- [x] `bin/skill-chain.py` gains `--loop` and `--loop-delay` CLI flags (CLI overrides YAML). `--loop 0` loops until a non-supervisor failure or Ctrl-C.
- [x] Iteration-per-subdir log layout (`iter_NN/MANIFEST.json`) when `loop != 1`; single-run flat layout preserved for `loop == 1`.
- [x] Top-level `MANIFEST.json` carries `iterations: [...]` + `loop: {requested, delay_seconds, completed}` when looping.
- [ ] Document the loop flag + YAML field in `README.md`.
- [ ] Add at least one transferable chain that uses `loop: N` by default (candidate: an sst-iterative-writer or dev-cycle-with-review loop).

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
- [ ] Update every transferable chain YAML under `chains/` to set `auto-promote:` explicitly (all three modes exercised across the set), then document the field in `README.md`.
- [x] First end-to-end loop that actually consumes its own supervisor's improvements: closed empirically by the `~/Dev/sdrai/.skill-runs/2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` run (iter_01 review filed one `[should-fix]` on `SIGNALS_VALID_TYPES` dedup; iter_02 picked and closed it in `40f1243`; iter_02 review reported clean, no re-file). See Phase 14 preamble for context.
- [x] Harness `--max-turns 100` set explicitly in `bin/skill-chain.py`. `claude -p` has an undocumented turn ceiling (~31 observed; github.com/anthropics/claude-code/issues/16963) that otherwise makes the supervisor terminate `[ok]` mid-workflow between the "sanitization clean, safe to proceed" step and the actual transferable-sidecar write. 100 is headroom for a supervisor doing proprietary overwrite + transferable sanitize + transferable sidecar + verdict.
- [x] Supervisor over-expands patches. First Phase 11 sdrai-cycle run articulated 2 findings but wrote a patch with 3 changes (the third — "Public landing surface" bullet — was orphan scope creep not grounded in the transcript). sst-supervisor v1.2.0 → v1.3.0: §3 now requires a change-intent table mapping every line-level change to a motivating transcript-line citation before drafting; row count must be ≤ finding count. §6 verdict records the table verbatim for auditability. Operating principles elevate "every proposed line change cites a transcript line — no citation, no change" to a top-level rule.
- [x] Supervisor reaches for Edit/Write on `.claude/skills/` and, on denial, "falls back to sidecar per `off`-mode treatment" instead of routing through `apply-skill-patch.py`. Observed in run `2026-04-24T12-33-37Z_sdrai-cycle`: the helper-script rule lived at §173 (Permissions contract, deep in the file), but §3 (drafting) ended before describing *how* to write and the agent defaulted to Edit. sst-supervisor v1.3.0 → v1.4.0: (a) inlined the `apply-skill-patch.py` Bash invocation directly under §3's routing table so agents reach the rule while drafting, not 100 lines later; (b) added "A tool-permission denial is NOT a mode downgrade" to Operating principles — auto-promote mode is set by the chain YAML at run start, not by which tool happens to fail mid-run.
- [x] Supervisor reads `MANIFEST.json` but the chain runner only writes it after the iteration loop completes — so the supervisor (always last skill in the chain) saw no manifest at all when it ran. Observed in run `2026-04-25T00-55-27Z_sdrai-cycle`: supervisor noted *"MANIFEST.json was missing from this run dir (chain-runner artifact)"* and fell back to defaults silently. Fixed in `bin/skill-chain.py` `run_iteration()`: now snapshot-writes a merged manifest (chain-level fields + per-skill records of skills that ran before this one) to `iter_log_dir/MANIFEST.json` after every skill, with `"in_progress": true` set so consumers know it's pre-final. The end-of-main full write supersedes the snapshots. sst-supervisor §Inputs prose updated (v1.4.0 → v1.4.1) so the supervisor doesn't flag its own absent record as a defect.
- [x] Supervisor-managed `.claude/skills/` dirt interacts badly with the reviewer's pre-flight "stop if dirty" rule. Audited every transferable doing a `git status`-clean check (`sst-dev-cycle`, `sst-dev-review`, `sst-supervisor` — only the first two have a pre-flight gate; `sst-supervisor` already operates on `.claude/skills/` as its turf). Patched both: `sst-dev-cycle` v1.0.2 → v1.0.3 §0.3 and `sst-dev-review` v1.0.0 → v1.1.0 §0.2 now carry the same generic carve-out the proprietary `sdrai-dev-review` and `skill-set-dev-review` use ("if `git status --porcelain` shows ONLY paths under `.claude/skills/`, proceed"). `sst-dev-review` v1.1.0 also picks up the destructive-state HEAD~1 rule (Pitfalls + §2.3 test-count): never `git checkout HEAD~1 -- .` or chain `git stash` with `git checkout` of the prior commit; use `git show HEAD~1 -- <path>` or a separate `git worktree` instead.

### Phase 12: efficiency wins + multi-loop orchestrator

A 9-cycle / $73.59 / 4-hour empirical pass on `sdrai-cycle` (2026-04-23 → 2026-04-25, ~95% spec completion) surfaced three structural inefficiencies: (a) same-root TODO items getting fragmented across cycles each paying full review+supervisor overhead, (b) the supervisor burning ~$1 to confirm "clean" when nothing in the run-log shows a finding, and (c) `loop:` mode (Phase 9) shipped but unused — every cycle is still manually re-invoked. Phase 12 closes those plus introduces the missing top-level role: an orchestrator that drives a multi-iteration chain run autonomously and pipes progress to the user over Telegram in real time (the existing `sst-manager` is cadence-based and reactive; the orchestrator is event-driven and active for the duration of one multi-iteration run).

- [ ] **`sst-dev-cycle` §1 same-root carveout.** Add to the selection-priority section: when `TODO.md > Next up` has multiple queued items sharing a root cause (e.g. "propagate constant X to all public surfaces"), AND the combined diff is <300 LoC, AND they touch disjoint files, bundle them into one cycle. Rationale: empirically `7.7.E.1` ($9.90) + `7.7.E.2` ($5.75) split one conceptual change ("propagate Bearer min-fee floor across public pricing surfaces") into two cycles, each paying ~$2.50 fixed review+supervisor overhead. Bundling would have saved ~$6 per such pair without violating the small-scope discipline (the work is cohesive, just files-disjoint).

- [ ] **`sst-dev-review` §5 same-root tagging.** When the reviewer files multiple Next-up follow-ups that share a root cause, tag each entry with `(group with <root-keyword>)`. The next `sst-dev-cycle`'s pick step (above) keys on this tag to bundle. Avoids the upstream/downstream coordination problem where the reviewer correctly observes a multi-surface gap but each follow-up gets picked atomically.

- [ ] **`sst-supervisor` fast-path on clean.** Add a §0.5 pre-check that scans each skill's `<i>_<skill>.txt` for finding-bearing keywords (`failed`, `denied`, `aborted`, `stash`, `--no-verify`, `pkill`, `must-fix`, contradiction patterns) AND verifies the cycle's commit deployed cleanly. If all transcripts are clean by that scan AND no escalation flags exist, write a one-line "clean" verdict and exit before walking §1–6. Estimated saves ~$0.70 × ~50% of cycles (currently ~5 of 9 sdrai cycles produced no findings; supervisor still spent $0.97–1.45 each). Fast-path must NEVER apply when any prior verdict in the run-dir's `.skill-runs/` chain says `escalate` — escalation tail still goes through the full walk.

- [ ] **Adopt loop mode on at least one transferable chain.** Set `loop: 3` on `chains/dev-cycle-with-review.yaml` (or a new `chains/dev-cycle-with-review-looped.yaml` if backwards compatibility matters), so a single `bin/skill-chain.py --chain dev-cycle-with-review` knocks out the next three queued items autonomously. Validates Phase 9's looping infra against a real consuming flow and unblocks the Phase 11 tail item ("verify two consecutive iterations of a synthetic should-fix finding converge"). Document the loop flag + YAML field in `README.md` (still a Phase 9 tail item).

- [ ] **`sst-orchestrator` (new top-level skill).** Distinct from `sst-manager` (which is cadence-based, cross-project, reactive). The orchestrator is invoked once per multi-iteration session, drives `bin/skill-chain.py --chain <name> --loop N` as a subprocess, watches the live event stream, and posts Telegram updates at: (1) session start (chain name + iteration count + estimated budget), (2) each iteration boundary (commit SHA + one-line summary + cumulative spend), (3) supervisor escalation or non-zero exit (immediate alert with run-dir path), (4) session end (commits-shipped count + total spend + per-iteration breakdown). Uses `bin/notify-telegram.sh` for outbound and respects a `--max-budget-usd` halt + a `--max-cycles` halt. Separate proprietary counterpart (`<persona>-orchestrator`) supplies the watched-chain name, Telegram chat ID, and budget defaults — same split convention as `sst-manager` / `<persona>-manager`. Implementation: most of the orchestration is mechanical (parse jsonl, send Telegram on threshold events), so `bin/orchestrate-chain.py` does the heavy lifting; the SKILL is a thin natural-language wrapper that lets the user say *"run sdrai-cycle until budget hits $30 or 5 iterations finish, whichever first"*.

- [ ] **Phase 12 acceptance check.** Re-run a real `sdrai-cycle` with all four wins live (same-root bundling triggered on a multi-surface follow-ups, supervisor fast-path on a clean cycle, `loop: 3`, orchestrator driving + Telegram'ing). Compare cost-per-shipped-feature against the Phase-11 baseline ($73.59 / 9 cycles). Target: ≥25% reduction on multi-iteration runs.

### Phase 13: rate-limit pause-and-resume

A multi-iteration `--loop N` chain can run for hours and crosses the rolling 5-hour Anthropic quota window mid-run. When that happens today the chain runner's subprocess exits non-zero, the iteration is marked failed, the loop aborts, and any cycle's worth of work-in-flight (TDD that hadn't reached commit, a partially-deployed change) is left in an indeterminate state. Phase 13 lets the runner detect the rate-limit signal, sleep until the reset time, and resume the killed skill in place — so a 3-iteration `sdrai-cycle` that crosses a quota boundary just stretches in wall-clock time rather than aborting.

Three error categories the runner needs to recognize, from highest-frequency to lowest:

1. **Five-hour rolling quota** — the standard rate limit. `claude` emits `rate_limit_event` with `rate_limit_info: {rateLimitType: "five_hour", status: "exceeded", reset_time: "<UTC>"}` (the runner already prints these as warnings; it does not yet act on `status: exceeded`). When the active model run hits the wall the subprocess exits with a recognizable error message in stderr (`"You've hit your <limit> rate limit"` or similar). Both signals must be handled.

2. **Out-of-usage** (primary plan quota exhausted) — distinct from the five-hour bucket; this is the monthly / weekly cap. Same `rate_limit_event` shape with `rateLimitType: "weekly"` or `"primary"` (exact field name TBD; capture from a real exhausted-quota event during implementation).

3. **Out-of-extra-usage** (overflow / burst quota also exhausted) — Pro/Team plans have a secondary pool. Same shape with `rateLimitType: "extra"` or `"burst"`.

For all three, the resolution is the same: parse the reset timestamp from the event payload, sleep until reset + a short jitter (15–60s), then re-invoke the killed skill from scratch. Each skill invocation is a fresh subprocess, so restarting is safe — there is no in-process state to preserve across the pause.

- [ ] **Detection in `bin/skill-chain.py`.** Extend `handle_event` to flag any `rate_limit_event` with `status` matching `exceeded`/`blocked`/`reset_required`. Parse `reset_time` (ISO 8601), `retry_after_seconds`, or whatever the actual payload field is — capture the real shape from a live triggered event, not a guess. Also add a stderr/exit-code detector for the case where the subprocess died from a rate-limit error before emitting a clean event (a regex against the prettified transcript's tail, or a check on the `result` event's `subtype` and error message).

- [ ] **Pause loop in `run_skill` (or wrapping it).** When a rate-limit signal fires:
  - If `reset_time` parsed: sleep until `reset_time + jitter(15–60s)`. Print a single ORANGE banner `[rate-limit] <type> exceeded; sleeping <Ns> until <UTC-iso>` and (if the orchestrator is wired) emit a Telegram notification.
  - If only `retry_after_seconds`: sleep that long.
  - If neither: exponential backoff starting at 5min, capped at the configured max-pause.
  - Honor Ctrl-C cleanly during the sleep (interrupt the loop, finalize the manifest, exit 130).
  - On wake: re-invoke `run_skill(harness, skill_name, index, log_dir)` for the same skill. The retry overwrites the previous attempt's transcript files (or appends with a `.retry-N` suffix — TBD).

- [ ] **Configurability.**
  - Chain YAML: `on-rate-limit: fail | pause | pause-with-cap` (default `pause`). `pause-with-cap` honors `max-rate-limit-pause-seconds` (default 28800 = 8h) and falls back to `fail` if a single pause would exceed it.
  - CLI: `--on-rate-limit <fail|pause|pause-with-cap>` and `--max-rate-limit-pause-seconds <N>`. CLI overrides YAML.
  - Schema additions to `schema/skill-chain.schema.json`.

- [ ] **Manifest record.** `MANIFEST.json` (top-level + per-iteration) gains `rate_limit_pauses: [{at, type, sleep_seconds, reset_time, resumed_at, skill, retry_count}]`. The supervisor's §1 walk recognizes `retry_count > 0` records and does not mistake the pause for a skill defect.

- [ ] **Repeat-pause safeguard.** If the same skill triggers a rate-limit pause more than `max-pauses-per-session` times (default 3), abort the chain — repeated pauses on the same skill suggest a quota-burning loop, not a genuine hourly-window crossing. Log the abort reason.

- [ ] **Orchestrator hook (Phase 12 #5).** `sst-orchestrator` / `bin/orchestrate-chain.py` recognizes `rate_limit_pauses` events and Telegrams: "Chain paused at <UTC>, resuming at <UTC>; reason: <type>; iteration <N>/<total>." A second Telegram fires on resume.

- [ ] **Acceptance check.** Trigger a real five-hour rate-limit during a `loop: 3` run (likely by deliberately bursting a heavy skill run before the chain). Confirm: (a) detection fired, (b) sleep duration matched the reset time within ±60s, (c) the killed skill re-ran cleanly on resume, (d) the chain finished all three iterations, (e) MANIFEST records the pause with accurate timestamps, (f) Telegram fired both pause and resume notifications.

### Phase 14: supervisor completion invariant + run-dir hygiene

A 12-cycle / 14-iteration `sdrai-cycle` loop (2026-04-23 → 2026-04-25) closed Phase 3 of `~/Dev/sdrai` entirely (all five v1 endpoints live + production-verified), shipped 24 commits, grew the consuming project's test suite 697 → 825, and reached ~95% spec completion. The framework's own contract held: 9 of the 14 supervisor passes ran clean, `sst-sanitize-transferable` returned `must-fix: 0` on every transferable draft scanned, the dev skill's pattern-fidelity instinct kept divergence low (new modules mirrored existing ones rather than diverging), and the `2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` run demonstrated within-chain convergence (iter_01 review filed one `[should-fix]` on `SIGNALS_VALID_TYPES` dedup; iter_02 picked and closed it; iter_03 was rate-limit-killed mid-review per Phase 13). Three new failure modes surfaced once enough cycle volume accumulated, all tied to the supervisor's completion contract:

(a) **Supervisor early-exit between sub-skill invocation and verdict write.** Twice in 14 supervisor passes the session terminated cleanly (`[ok]`, no error) after `sst-sanitize-transferable` returned, BEFORE `apply-skill-patch.py` ran for the transferable AND BEFORE `supervisor_verdict.md` was written. Drafts persist in `<run-dir>/drafts/` indefinitely; downstream iterations cannot pick them up because the anti-scope-creep gate requires per-iteration transcript citations. Observed in `~/Dev/sdrai/.skill-runs/2026-04-24T04-21-39Z_sdrai-cycle/` (transferable sidecar skipped after the proprietary overwrite landed) and `~/Dev/sdrai/.skill-runs/2026-04-25T06-15-57Z_sdrai-cycle/iter_01/` (both writes skipped, only sanitize ran). The two follow-up iter verdicts independently flagged this and asked for a "if you wrote drafts, you MUST also call apply-skill-patch.py and write the verdict file before exiting" guard.

(b) **Orphaned drafts across iter boundaries.** When (a) fires inside a multi-iter chain, iter_N+1's supervisor sees the prior `drafts/` directory but cannot consume it (no transcript citation in iter_N+1's own session). The drafts persist until a human runs `apply-skill-patch.py` by hand.

(c) **`apply-skill-patch.py --backup` accumulates `.bak` cruft.** Five consecutive sdrai supervisor verdicts noted the same `.claude/skills/sdrai-dev-review/SKILL.md.bak` sitting in `git status`, untouched for days. Git history covers rollback fine; the `--backup` default is dead weight that surfaces every cycle as a tracked-but-uncommitted file.

- [ ] **Completion invariant in `sst-supervisor`.** Add to the parent-skill prose a final §7 "exit gate": before returning, the supervisor MUST verify that `<run-dir>/drafts/` is empty OR that every file in it has a corresponding `apply-skill-patch.py` invocation in this session's transcript. If neither holds, the supervisor MUST either apply the remaining drafts or write the verdict file with an explicit `[deferred]` block per draft (citing why it was not applied; e.g. sanitize returned `must-fix`). The verdict file MUST exist before the supervisor returns. Codify the rule as a top-level Operating principle ("a supervisor session that wrote drafts but no verdict file is a contract violation, not a clean exit").

- [ ] **Iter-boundary drafts sweep in `sst-supervisor`.** Add a §0.6 prelude step (runs only when `iter > 1`, detected via `MANIFEST.iteration > 1`): `ls <run-dir>/iter_NN-1/drafts/` (or `<run-dir>/drafts/` for non-iter chains where the prior session ran in the same dir). For each unconsumed file, treat it as a manager-injected finding: cite the prior iter's `02_<supervisor>.txt:<line>` as the motivating source (this satisfies anti-scope-creep without inventing a citation), then route per the current `auto-promote` mode. Drop the consumed file after applying. Outcome: a partial-completion supervisor failure in iter_N self-heals at the start of iter_N+1 instead of orphaning learning across the chain.

- [ ] **Drop `--backup` from `sst-supervisor`'s `apply-skill-patch.py` invocations.** Update the §3 helper-script template + the §Permissions invocation example to omit `--backup`. Keep the flag in `bin/apply-skill-patch.py` (still useful for ad-hoc human use) but stop defaulting to it in the supervisor's automated pathway. One-shot cleanup: `find ~/Dev -path '*/.claude/skills/*' -name 'SKILL.md.bak' -delete` to clear historical cruft.

- [ ] **`bin/clean-skill-runs.py` (new helper).** Idempotent housekeeping for `<project>/.skill-runs/` trees. Removes (1) empty `<run-dir>/proposals/` directories left over from pre-Phase 11 contracts (still present in `~/Dev/sdrai/.skill-runs/2026-04-23T10-42-54Z_sdrai-cycle/proposals/` and similar), (2) `*.SKILL.md.bak` cruft per the bullet above, (3) optionally orphaned `<run-dir>/drafts/` directories older than N days (default 14) with explicit user confirmation per file. Safe to re-run; never deletes a draft whose mtime is younger than the threshold without prompting.

- [x] **Phase 11 within-chain-convergence demonstration closed empirically.** The `2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` run produced exactly the convergence pattern Phase 11's tail item specified: iter_01's `sdrai-dev-review` filed one `[should-fix]` on `SIGNALS_VALID_TYPES` dedup (`signals_lite.py:25` vs `main.py:491`); iter_02's `sdrai-dev` picked and closed it in commit `40f1243`; iter_02's review reported clean, no re-file. Counts as the empirical close of Phase 11's "First end-to-end loop that actually consumes its own supervisor's improvements" item — flipping that line above from `[ ]` to `[x]` in the same commit as this Phase 14 block.

- [ ] **Randomized inter-iteration delay.** Add `loop-delay-random: [min_seconds, max_seconds]` to `schema/skill-chain.schema.json` and `bin/skill-chain.py`. When set, the runner sleeps `random.randint(min, max)` between iterations of a `--loop N` chain instead of the fixed `loop-delay` value (mutually exclusive with `loop-delay`; setting both is a YAML validation error). CLI: `--loop-delay-random "<min>,<max>"` overrides YAML. Honors Ctrl-C cleanly during the sleep using the same pattern Phase 13 introduces for rate-limit pauses. `MANIFEST.iterations[]` records the actual sampled `delay_seconds` per iteration boundary so the trace is auditable. Rationale: a fixed cadence makes the commit-timing trail of an autonomous loop obvious to outside observers (e.g. GitHub activity feeds, on-call dashboards). A 1-60min uniform jitter (`[60, 3600]`) makes the cadence indistinguishable from a human-driven workflow without meaningfully extending wall-clock for a 3-iter run.

- [ ] **Phase 14 acceptance.** Trigger a new multi-iter run with the completion invariant + iter-boundary sweep + randomized delay live. Deliberately short-circuit the supervisor mid-write (e.g. `kill -TERM` after the sanitize call). Confirm: (a) the killed iter's supervisor exits with non-zero status because the exit gate fails, OR writes a `[deferred]` verdict file naming each unapplied draft; (b) the next iter's supervisor finds and consumes the orphaned drafts via the §0.6 sweep; (c) no `.bak` files remain in `.claude/skills/` after the run; (d) `bin/clean-skill-runs.py` removes any stale `proposals/` dir without prompting; (e) MANIFEST shows non-uniform `delay_seconds` between iterations within the configured range.
