# skill-set SPEC

This is the master spec for the skill-set system itself. Each consuming project keeps its own `docs/SPEC.md` for its own work; this file governs the framework.

## Harness scope

The framework is harness-agnostic: a `Harness` abstraction in `bin/skill-chain.py` isolates the choice of agent runtime (which CLI to spawn, what command-line shape, what stream format). Two implementations ship today: `claude-code` (default) and `cursor` (`cursor-agent` CLI; Phase 58 finalized the live stream-json mapping). Additional harnesses (a cheaper Claude tier per Phase 19, a non-Claude binary like Goose per Phase 20, future Codex / Gemini / etc.) drop in by adding a `Harness` subclass. User-facing docs use harness-neutral terms ("agent", "harness", "skills directory"); the current default skills paths (`~/.claude/skills/` for globally-installed transferables, `<project>/.claude/skills/` for proprietary) come from the Claude Code harness and will be parameterized when a second harness lands. The layout is flat under the harness skills dir because Claude Code only discovers direct children; a nested segregation subdir (e.g. `skill-set/`) was tried and reverted after discovery broke.

## Primary concepts

### Skill-chain

A `.yaml` file naming a sequence of skills the chain runner executes in order. Same transferable/proprietary split as skills:

- **Transferable chains** live at `<repo>/chains/<name>.yaml`.
- **Proprietary chains** live at `<project>/.claude/chains/<name>.yaml`.
- A proprietary chain MAY name the transferable chain it instantiates via `transferable: <name>` (informational; no inheritance/override behavior in MVP, proprietary chains list their full skill sequence explicitly).

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
---
```

Transferable skills don't back-link (1:N relationship). Validation: `schema/skill-set.schema.json` + the distinct-name check in `bin/validate-frontmatter.py`.

**Distinct-name rule.** A proprietary skill's `name:` MUST differ from its `transferable:`. Both install under the same harness skills directory (`~/.claude/skills/<name>/` for personal-global, `<project>/.claude/skills/<name>/` for project-scoped), so identical names would collide and `install-skills.sh` would silently clobber hand-edited proprietary content. Enforced by the validator; no opt-out.

**`sst-` / `ssp-` prefix convention.** All skill-set skills carry a framework-identifying prefix:

- Transferable skills (canonical, shipped here under `skills/`) use `sst-<base>`. Examples: `sst-dev-cycle`, `sst-linkedin-easy-apply`, `sst-sanitize-transferable`.
- Proprietary counterparts use `ssp-<base>`. Examples: `ssp-dev-cycle`, `ssp-linkedin-easy-apply`. They declare `transferable: sst-<base>` in frontmatter.

Project-scoped proprietary MAY substitute a project-name prefix when tightly coupled to one codebase (e.g. `myproject-dev-cycle`); that also satisfies the distinct-name rule. The `ssp-` default is preferred for portability. The prefix makes it visible at a glance which skills came from this framework and on which side of the split, and keeps unrelated user-authored skills cleanly separable.

**Scopes.** Two canonical homes for proprietary skills:

1. **Project-scoped** at `<project>/.claude/skills/<name>/` discovered only when the harness runs in that project. For skills specialized to a single codebase.
2. **Personal-global** at `~/.claude/skills/<name>/` discovered from any directory. For skills specialized to the user's identity, tooling, or config (e.g. `ssp-linkedin-easy-apply` carrying a resume path + salary floor). Because `install-skills.sh` only touches names defined in this repo's `skills/`, `ssp-*` skills are never overwritten when the transferable counterpart is bumped.

### Handoff docs

Every project keeps two canonical files (`docs/SPEC.md`, `docs/TODO.md`) read by every skill on start and updated by every skill on close. See `templates/`.

**HUMAN.md invariant (Phase 54).** A third optional handoff file, `docs/HUMAN.md` (the human-only-blocker channel), is owned exclusively by the oversight layer: ONLY `sst-supervisor` and `sst-manager` (plus their proprietary mirrors) may read or write `docs/HUMAN.md`. The execution layer (`sst-dev-cycle`, `sst-dev-review`, `sst-tester`, and their mirrors) neither consults nor appends to it; blocked-item pick-gating is re-homed to the manager and the phase-completion branch-setup handoff to the supervisor.

`SPEC.md` shape: long-lived, phase checklists with `- [ ]`/`- [x]`. Closed phases are compressed to a 1-paragraph context + a tight bulleted change log (one line per item); consuming projects keep them inline until the file grows unwieldy, at which point closed phases are archived to `docs/SPEC-DONE.md`. Phases that drift toward novella-length should be compressed back; git history + TODO `Just shipped` carry the detail.

`TODO.md` shape (three sections):
```markdown
## In flight
- [<skill> @ <utc>] <one-line>

## Just shipped (last cycle)
- <one-line> by <skill> at <utc>

## Next up (queued for next cycle)
- <one-line> reason / source
```

Skill contract (codified in transferable preambles):
1. Read both docs end-to-end before any other action.
2. Pick from `TODO.md` "Next up" if non-empty, else next unchecked item in `SPEC.md`.
3. Write a single "In flight" line at start; rewrite (don't append) as work narrows.
4. On close: move "In flight" → "Just shipped" (no commit SHA, a commit cannot contain its own hash; correlate via `git log --oneline --grep`); append any new work to "Next up"; trim "Just shipped" to last 10.
5. Both docs commit in the same commit as the code change.

### Run log

Each chain invocation writes to `<project>/.skill-runs/<UTC>_<chain-name>/`:

- `MANIFEST.json` chain name, harness, skill list, exit codes, durations, model, token usage, git SHA before/after.
- `<i>_<skill>.jsonl` raw stream events emitted by the harness (one JSON object per line).
- `<i>_<skill>.txt` prettified, ANSI-stripped transcript.
- `supervisor_verdict.md` appended at end of chain (when supervisor runs).
- `proposals/<skill-name>.patch.md` proposed `SKILL.md` rewrites (proprietary or transferable).

### Sanitization (transferable proposals only)

Before writing a transferable proposal, the supervisor invokes the `sst-sanitize-transferable` skill, which scans the draft against `templates/sanitization-guidance.md` (rubric) and the per-project banned-terms list maintained by the proprietary supervisor. Sanitization is judgment-based, an LLM pass, not regex. Any `must-fix` finding aborts the write; the lesson stays in the proprietary proposal only. Every transferable proposal carries a `Sanitization checklist:` footer the sanitize skill generates and the human reviewer fills in; CI rejects PRs without a complete footer. Invocation mechanics are caller-specific (Phase 67): the supervisor invokes the skill via the Skill tool; `sst-dev-cycle` §3 reads the same SKILL.md and follows its Process in-session (no sub-invocation, per H43.1 option 1). The gate is the rubric walk + the findings artifact, not the Skill-tool call.

## Phases

> Completed phases live in [docs/SPEC-DONE.md](SPEC-DONE.md); deferred phases live in [docs/FUTURE-WORK.md](FUTURE-WORK.md). Active phases live below.

### Phase 69 -- backlog-growth control: filing budget, phase freeze, queue-delta telemetry (2026-09-08, owner-directed)

A consuming project measured its own queue and found the review stage filing items faster than the
dev stage closed them: 46 new IDs across 21 iterations against ~1.9 closed per iteration, an active
phase parked at ~60 open for a week, a quarter of it polish at a third severity tier, and a third of
it prose corrections to earlier items' own notes. No individual review was wrong; the severity bar
gates whether a finding is REAL and nothing gated how many became QUEUE ITEMS, so the backlog tracked
the loop's observation rate instead of its defect count and the phase could never be finished or merged.

- [x] 69.1 [medium] `sst-dev-review` (1.36.0): filing budget (`filed_non_blocker <= max(1, closed)`,
  ceiling 3, blockers exempt and uncapped), overflow routed to `docs/FUTURE-WORK.md` with evidence
  intact, mandatory dedup receipt, and the two-severity bar restated as binding every writer of the
  queue rather than only this stage.
- [x] 69.2 [medium] `sst-dev-review` (1.36.0): phase freeze. At `phase_open <= 10` (or on a human
  declaration) a phase accepts only `[blocker]` items; the banner is written into the phase's
  `## Next up` subsection so later stages read state instead of re-deriving it. Inert, with a
  `phase=none` path, in a project whose spec has no phase structure.
- [x] 69.3 [easy] `sst-dev-review` (1.36.0): a finding whose entire remedy is prose in the three
  handoff docs is an in-place §5 edit, never a queue item; tracked-source prose stays on the wrong
  side of that line and is judged against the severity bar as before.
- [x] 69.4 [medium] `sst-dev-review` (1.36.0) §2.11: `[queue-delta]` machine line, emitted
  unconditionally every iteration, plus its mandatory §6 receipt clause.
- [x] 69.5 [medium] `sst-dev-cycle` (1.73.0): the dev's own filing rules reconciled to the same
  contract (two severities, at most 2 new IDs, freeze honored), because a queue two stages write and
  only one is rationed on is not rationed at all. A FROZEN phase stays fully pickable.
- [x] 69.6 [hard] `sst-supervisor` (2.25.0) §3.7: backlog-growth detection. Aggregates
  `[queue-delta]` samples over §3.5.1's trailing window; net-growth streak (N=5), flat-backlog
  window (M=8), freeze-eligibility, and a draining override (K=10); responds with one prose
  refinement, a freeze routed to manager-notes, or escalation to HUMAN.md when the growth survived a
  prior response. A missing sample is a finding, never an imputed zero. Hoisted into the §0.5
  fast-path so it keeps firing on clean iters.
- [x] 69.7 [easy] `sst-manager` (2.5.0): per-project backlog reading in §2 and a mandatory
  `Backlog:` line in the digest's STANDING section, promoted to `NEEDS YOU` after two consecutive
  growing ticks (the point at which no autonomous stage can fix it).
- [x] 69.8 [easy] `templates/SPEC.md` + `templates/FUTURE-WORK.md`: two-severity rule and bounded filing rate documented in the spec template; new `## Deferred review findings` section defined in the FUTURE-WORK template as the overflow destination the review writes to.

Wrappers reconciled in the same pass: `ssp-cm-dev-review` 1.39.0, `ssp-cm-dev` 1.109.0,
`ssp-cm-supervisor` 2.7.0, `ssp-cm-manager` 1.5.0, `ssp-dahrouge-manager` 1.2.0 (the last two were
also behind their base before this change). Sanitize gate: 0 must-fix across all four transferables;
3 should-fix found and applied (undeclared caps, phase-structure assumption).

Tests: none added. Every change is skill prose; `bin/validate-frontmatter.py` and
`bin/check-ssp-sync.py` both clean.

### Phase 68 — log-dir prompt handoff + rate-limit-safe executor spawns (2026-07-20, owner-directed)

Root cause of three consecutive supervisor escalations: the runner's `[log-dir]` startup print goes
to its own stdout, which no skill subprocess can see, so every skill guessed its run dir via
`ls -dt .skill-runs/*/` (iter-4 dev fabricated a standalone run dir; tester followed; review lost
the MANIFEST). Separately, executor spawns were bare `claude --print` — a session-limit hit killed
the batch instantly and an early queue-file archive reported it falsely processed.

- [x] 68.1 `run_iteration` injects `[log-dir]` / `[iter-dir]` / `[iteration]` into every skill's
  invocation prompt via `extra_prompt` (prompt is the only channel into a skill).
- [x] 68.2 `--skill-args` passthrough (single-skill runs): argument-taking skills run under the
  wrapper's rate-limit pause-and-resume. `manager-bot.py spawn_executor` and `sst-supervisor` §5c
  (2.10.0) both spawn the executor via `skill-chain.py … --skill-args … --on-rate-limit pause`
  (supervisor detached with `nohup … &`).
- [x] 68.3 `sst-executor` (1.1.0) archives its queue file at close-out only, both modes — the
  un-archived file is the crash-safety marker that keeps a dead batch re-dispatchable.

Tests: `tests/test_phase68.py` (8).
