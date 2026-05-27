# skill-set SPEC

This is the master spec for the skill-set system itself. Each consuming project keeps its own `docs/SPEC.md` for its own work; this file governs the framework.

## Harness scope

The framework is harness-agnostic: a `Harness` abstraction in `bin/skill-chain.py` isolates the choice of agent runtime (which CLI to spawn, what command-line shape, what stream format). The MVP shipped with one implementation, `claude-code`, because that's what the prototype runs on; additional harnesses (a cheaper Claude tier per Phase 19, a non-Claude binary like Goose per Phase 20, future Codex / Gemini / etc.) drop in by adding a `Harness` subclass. User-facing docs use harness-neutral terms ("agent", "harness", "skills directory"); the current default skills paths (`~/.claude/skills/` for globally-installed transferables, `<project>/.claude/skills/` for proprietary) come from the Claude Code harness and will be parameterized when a second harness lands. The layout is flat under the harness skills dir because Claude Code only discovers direct children; a nested segregation subdir (e.g. `skill-set/`) was tried and reverted after discovery broke.

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

1. **Project-scoped** at `<project>/.claude/skills/<name>/` discovered only when the harness runs in that project. For skills specialized to a single codebase.
2. **Personal-global** at `~/.claude/skills/<name>/` discovered from any directory. For skills specialized to the user's identity, tooling, or config (e.g. `ssp-linkedin-easy-apply` carrying a resume path + salary floor). Because `install-skills.sh` only touches names defined in this repo's `skills/`, `ssp-*` skills are never overwritten when the transferable counterpart is bumped.

### Handoff docs

Every project keeps two canonical files (`docs/SPEC.md`, `docs/TODO.md`) read by every skill on start and updated by every skill on close. See `templates/`.

`SPEC.md` shape: long-lived, phase checklists with `- [ ]`/`- [x]`. Closed phases are compressed to a 1-paragraph context + a tight bulleted change log (one line per item); consuming projects keep them inline until the file grows unwieldy, at which point closed phases are archived to `docs/SPEC-archive.md`. Phases that drift toward novella-length should be compressed back; git history + TODO `Just shipped` carry the detail.

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

Before writing a transferable proposal, the supervisor invokes the `sst-sanitize-transferable` skill, which scans the draft against `templates/sanitization-guidance.md` (rubric) and the per-project banned-terms list maintained by the proprietary supervisor. Sanitization is judgment-based, an LLM pass, not regex. Any `must-fix` finding aborts the write; the lesson stays in the proprietary proposal only. Every transferable proposal carries a `Sanitization checklist:` footer the sanitize skill generates and the human reviewer fills in; CI rejects PRs without a complete footer.

## Phases

> All closed phases (1–19, 21–36) archived to [docs/SPEC-archive.md](SPEC-archive.md). Active and deferred phases live below.

### Phase 20 (deferred): `goose-cerebras` harness + portability proof

Moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-20-deferred-goose-cerebras-harness--portability-proof). Re-pick conditions are documented there.

### Phase 37: handoff-doc prose alignment

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**
- [x] 37.1 [easy] [should-fix] `docs/SPEC.md:81` — The "SPEC.md shape" description says "Closed phases get a 1-paragraph context + a tight bulleted change log (one line per item, not a paragraph each). Phases that drift toward novella-length should be compressed back" — but commit `77d17de` archived all closed phases to `docs/SPEC-archive.md`. A dev reading line 81 would expect compressed-inline closed phases in SPEC.md, not an archive file. Proposed fix: update the description to say completed phases are archived to `docs/SPEC-archive.md` once closed, with consuming projects keeping closed phases inline (compressed) until the file grows large enough to warrant an archive.

### Phase 38: bounded-item discipline + phase-completion handoff

**Context.** A consuming project (claim_management) burned ~60 commits across three 20-iteration `cm-cycle` runs without ever closing its active phase, because `## Next up` carried an unbounded placeholder (`Phase 2.16 iterative UI/UX polish`) with no falsifiable done-state. Every iter the dev found one more comment/banner to fix, shipped it, and the placeholder survived to win the next pick — defeating the global empty-queue bail (§0 step 6), which only fires when the WHOLE spec is checked. Root cause: the framework permits open-ended items and has no phase-scoped completion handoff. This phase closes both gaps: prevent unbounded items at write time (38.1, 38.2), stop + hand off when a phase genuinely completes (38.3, 38.4), and have the supervisor actively detect-and-mitigate the stuck-item pattern when it recurs (38.5).

- [x] 38.1 [medium] **Writer-skill prose rule: no unbounded items.** In `sst-dev-review` (§4 follow-up filing), `sst-supervisor` (follow-up + TODO writes), and `sst-manager` (planner + feedback routing), add a rule: every SPEC item must name a *specific feature with a falsifiable acceptance criterion*; every TODO item must be a *specific, completable action*. Open-ended / recurring / catch-all items (a task whose description is a standing activity rather than a finite deliverable) are forbidden — a real but unbounded cleanup must be decomposed into concrete enumerated items (each naming its target file/symbol) or not filed. Acceptance: each of the three SKILL.md bodies contains the rule with an explicit forbidden-shape example and a decompose-instead example; `/sst-sanitize-transferable` clean on all three.
- [x] 38.2 [medium] **Validator gate `validate_spec_item_quality`.** Add a check in `bin/validate-frontmatter.py` that fails on any `docs/SPEC.md` or `docs/TODO.md` checkbox bullet whose task text matches an open-ended marker (denylist: the standing-activity words, matched only in the task-description span, NOT inside backticks/quotes — so an item that *mentions* a denylisted word as data, like this very item, does not trip) unless the bullet also enumerates ≥1 concrete target (a file path, symbol, or `<phase>.<n>` reference). Acceptance: new unit tests in `tests/` cover (a) a vague bullet → fail, (b) a vague-word-in-backticks bullet → pass, (c) a concrete bullet → pass; full suite green; the check runs in the existing validator CI entrypoint.
- [x] 38.3 [hard] **`sst-dev-cycle` phase-completion bail.** Before picking (§0/§1), derive the active phase from the SPEC `## Operational scope` branch map (current HEAD branch → phase number). If every SPEC `- [ ]` for that phase is `- [x]` AND no `## Next up` entry is scoped to that phase, fire a new phase-scoped sentinel `[no-work] phase <N> complete on <branch>; awaiting human branch setup for phase <N+1>` and exit 0 without picking/manufacturing work. Distinct from the global empty-queue bail. Acceptance: SKILL.md documents the derivation + sentinel; the chain runner recognizes it as a loop-aborting `[no-work]` variant (confirm `bin/skill-chain.py` sentinel match covers it, add a test if not); a fixture where one phase is fully `[x]` but a later phase has open items still bails on the completed phase rather than scope-creeping.
- [x] 38.4 [medium] **`sst-dev-cycle` HUMAN.md handoff on phase completion.** When the 38.3 bail fires, first append a `docs/HUMAN.md` `## Blocking` entry instructing the human to (1) merge/PR the completed feature branch, (2) create the next phase's `feature/<name>` branch from `origin/test`, (3) add its `## Operational scope` mapping; include a `Verify:` line and a `Blocks:` of the next phase's first SPEC ID; then call `bash bin/notify-human-md.sh <cwd> docs/HUMAN.md`. Idempotent: do not append a duplicate if an open entry for the same completed phase already exists. Acceptance: SKILL.md documents the entry template + idempotency rule; a test (or fixture walkthrough) shows the entry is written once and re-running the bail does not duplicate it.
- [x] 38.5 [medium] **`sst-supervisor` stuck-item detection + mitigation.** Extend the supervisor's existing trailing-window analysis to flag a *stuck unbounded item*: the same `## Next up` / SPEC item (by ID or by normalized description) was picked in ≥3 of the trailing-window iters without its SPEC `- [ ]` flipping to `- [x]`. On detection, the verdict records a `[stuck-item]` finding, and the supervisor (a) appends a `docs/HUMAN.md` `## High` entry recommending the item be decomposed into concrete sub-items or removed, and (b) prepends a manager-notes.md observation so the next manager digest surfaces it. Acceptance: SKILL.md documents the detection threshold + both mitigation writes; a fixture with the same item across 3 iters produces the `[stuck-item]` finding; `/sst-sanitize-transferable` clean.
- [x] 38.6 [medium] **`find_local_supervisor` transferable fallback.** `bin/skill-chain.py`'s supervisor auto-append discovered only a project-local `<cwd>/.claude/skills/*-supervisor/`; projects without a proprietary wrapper (e.g. skill-set itself) silently ran with no supervisor, making the chain YAML's `auto-promote` inert. `find_local_supervisor` now falls back to the transferable `~/.claude/skills/sst-supervisor/` when no proprietary supervisor exists in cwd (proprietary still wins; ambiguous multi-match still returns None with no fallback). 4 new unit tests in `tests/test_skill_chain.py` (prefers-proprietary, falls-back-to-transferable, none-when-neither, multiple-returns-none); full suite 159 green. Filed retroactively per the direct-change convention (implemented outside the dev-cycle in response to a user request).

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 38.7 [easy] [should-fix] [batch-sizing] `docs/TODO.md` Next-up co-batching missed in iter_01 of 2026-05-27T00-00-42Z run — dev used 71k input tokens against the medium band of 200-300k (undersize threshold: 100k); 38.5 [medium] (`sst-supervisor` stuck-item detection) and the manager-bot.service [medium] item in `docs/TODO.md` have no hard dependency on 38.3 and were co-batchable alongside 38.2. Proposed fix: in the next medium-difficulty batch, include 38.5 or a manager-bot medium item as a co-pick when their dependency graph permits.
- [x] 38.8 [easy] [should-fix] [batch-sizing] `bin/manager-bot.py` iter_03 batch undersized — dev used 72k input tokens against the medium band of 200-300k (undersize threshold 100k); window-target was ~220k; the 3rd stated batch item (38.7-close) was a trivial meta flip contributing near-zero tokens, leaving effective 2-item coverage at ~72k. `install-skills.sh` [medium] was available in `docs/TODO.md` as a genuine 3rd item and was not co-batched. Proposed fix: in the next medium batch, co-pick `install-skills.sh` from `docs/TODO.md` alongside the top queued item to bring total context into the 100k+ range; trivial meta/close items do not count toward window-fill.
- [x] 38.9 [easy] [should-fix] `bin/manager-bot.service:35` `ReadWritePaths=%h/.claude/state` too narrow for dispatcher mode — `ProtectSystem=strict` makes all paths outside `ReadWritePaths` read-only, including `~/.claude/projects/` (claude session cache) and project working dirs; the spawned `claude` subprocess in `spawn_manager_for_command` (bin/manager-bot.py:373) inherits this mount namespace and will fail to write session state or skill-run output. `MANAGER_SKILL_NAME=1` is now the default so dispatcher mode is on for any user who follows the "edit only two values" README instructions. Proposed fix: widen `ReadWritePaths` to `%h/.claude %h/Dev/skill-set` (at minimum) or `%h` (broadest, preserves /usr /etc protection), and update the service comment to note that dispatcher mode requires all project-root paths to be listed.
- [x] 38.10 [easy] [should-fix] `bin/manager-bot.service:39` comment says "if those projects live outside %h/Dev/" but the actual covered ancestor is `%h/Dev/skill-set`, not `%h/Dev/` — a user with `MANAGER_SKILLS_EXTRA_ROOTS` pointing to `%h/Dev/claim_management/.claude/skills` would follow the comment literally, not add `%h/Dev/claim_management` to `ReadWritePaths`, and the spawned `claude` subprocess would get silent write failures for run logs and skill state. Proposed fix: replace "outside %h/Dev/" with "outside any already-listed ReadWritePaths entry (e.g. a sibling of %h/Dev/skill-set like %h/Dev/claim_management must be listed explicitly)".
- [x] 38.11 [easy] [should-fix] `tests/test_install_skills.py` — No test covers `--force` overwriting a DIVERGED skill and verifying the `.installed-body` marker is updated to the new source body. If the unconditional marker-write at `bin/install-skills.sh:389` were accidentally moved inside a non-DIVERGED branch, `--force` would silently stop seeding the marker, causing subsequent source bumps to re-appear as DIVERGED and re-breaking the exact regression the feature fixed. Proposed fix: add a `TestMarkerFileManagement` test that sets up a hand-edited target + v1 marker + v2 source, runs with `--force`, then asserts `.installed-body` == v2 body.
- [ ] 38.12 [easy] [should-fix] `bin/skill-chain.py:1551` — Phase 36 pass-through condition `i + 1 < len(skills_to_run)` fires when the immediate follower is the auto-supervisor (appended by `main()` when no review skill is explicit in the chain), silently changing the old abort behavior: orphaned dev work stays uncommitted while the supervisor re-reviews the previous HEAD. `test_run_iteration_contract_violation_aborts_without_next_skill` passes `auto_supervisor=None` and covers only `["sst-dev-cycle"]`, missing the `["sst-dev-cycle", "sst-supervisor"]` case. Proposed fix: change `if i + 1 < len(skills_to_run):` to `if i + 1 < len(skills_to_run) and skills_to_run[i + 1] != auto_supervisor:` in `run_iteration`; add a test with `auto_supervisor="sst-supervisor"` and `skills_to_run=["sst-dev-cycle", "sst-supervisor"]` confirming the abort path is taken.
