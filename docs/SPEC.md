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
- <sha> <one-line> — by <skill> at <utc>

## Next up (queued for next cycle)
- <one-line> — reason / source
```

Skill contract (codified in transferable preambles):
1. Read both docs end-to-end before any other action.
2. Pick from `TODO.md` "Next up" if non-empty, else next unchecked item in `SPEC.md`.
3. Write a single "In flight" line at start; rewrite (don't append) as work narrows.
4. On close: move "In flight" → "Just shipped" with commit SHA; append any new work to "Next up"; trim "Just shipped" to last 10.
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
