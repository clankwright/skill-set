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

Before writing a transferable proposal, the supervisor invokes the `sst-sanitize-transferable` skill, which scans the draft against `templates/sanitization-guidance.md` (rubric) and the per-project banned-terms list maintained by the proprietary supervisor. Sanitization is judgment-based, an LLM pass, not regex. Any `must-fix` finding aborts the write; the lesson stays in the proprietary proposal only. Every transferable proposal carries a `Sanitization checklist:` footer the sanitize skill generates and the human reviewer fills in; CI rejects PRs without a complete footer.

## Phases

> Completed phases live in [docs/SPEC-DONE.md](SPEC-DONE.md). Active and deferred phases live below.

### Phase 20 (deferred): `goose-cerebras` harness + portability proof

Moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-20-deferred-goose-cerebras-harness--portability-proof). Re-pick conditions are documented there.

### Phase 39: supervisor fast-path finding-aware abort

**Context.** The `sst-supervisor` §0.5 no-work fast-path keyword scan (§0.5.3) keys only on `\bERROR` / `\bFAIL(ED)?\b` / `\bTraceback` / `\bException`. A `sst-dev-review` pass that finds a real `[blocker]`/`[should-fix]` and reports it in prose ("Found 2 items: 1 blocker, 1 should-fix") trips none of those tokens, so all five fast-path conditions can hold and the supervisor writes a spurious `clean (fast-path)` verdict that silently drops the review's finding. This is the false-negative complement to the false-positive tightening already shipped in 35.13 (word-boundary anchoring). Observed on the 2026-06-02T05-11-26Z lngraph run (iter_02 verdict) and recurring as a standing manager note since 2026-04-30. The supervisor cannot self-modify its own prose from inside a consuming project's chain, so the refinement is filed here as framework work.

- [x] 39.1 [medium] **`sst-supervisor` §0.5.3: abort the fast-path on any review-reported finding.** Extend the §0.5.3 transcript scan in `skills/framework/sst-supervisor/SKILL.md` to match the `sst-dev-review` §6 "With findings" report template — the line `Found <N> items: <B> blocker, <S> should-fix` with N>0, and/or an appended `Review follow-ups` block in the diff — and abort the fast-path (fall through to the §1 deep walk) on a match, so a prose-only finding can no longer pass as `clean (fast-path)`. Keep the existing `^\s*\[no-work\]` sentinel carve-out unchanged. Respect the §0.5.3 Anti-fork constraint: no soft prose matches (`warning`/`caveat`/`should`); anchor strictly to the review skill's fixed §6 report template, not free prose. Acceptance: §0.5.3 documents the new condition with its exact match target; the Anti-fork constraint note is updated to cover it; `/sst-sanitize-transferable` clean on `sst-supervisor`; `sst-supervisor` version bumped.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 39.2 [medium] [should-fix] `skills/dev/sst-dev-review/SKILL.md` §0.2 orphaned-cycle recovery — the auto-commit path does not invoke `/sst-sanitize-transferable` on changed files under `skills/framework/`, bypassing the sanitization gate that both `sst-supervisor`'s own SKILL.md contract and CLAUDE.md require for all transferable edits. The 39.1 changes contain no proprietary leakage, but the structural bypass leaves future orphaned recoveries of transferable edits un-gated. Proposed fix: in §0.2 step 7 (before committing), check whether `git diff --name-only` includes any path under `skills/framework/`; if so, invoke `/sst-sanitize-transferable` on each affected SKILL.md and abort with a user-visible message if any must-fix finding is returned.
- [x] 39.3 [easy] [should-fix] `skills/dev/sst-dev-review/SKILL.md` §0.2 step 7 — the recovery sanitize gate checks only `skills/framework/**`, narrower than the `sst-dev-cycle` §5 gate (`skills/<category>/<sst-*>/SKILL.md`); transferable dev skills in `skills/dev/` (e.g. `sst-dev-cycle`, `sst-dev-review`) are left un-sanitized if an orphaned recovery commits them. Proposed fix: widen the step 7 path check to match the dev-cycle gate: scan staged paths for `skills/**/sst-*/SKILL.md` (not just `skills/framework/`), invoke `/sst-sanitize-transferable` on each match, and update the test to assert the broader pattern; bump version to 1.9.0.

### Phase 41: interactive UI/UX test stage between dev and review (`sst-tester` + `ssp-cm-tester`)

**Context.** UI/UX changes are currently verified only by the dev cycle's own inline checks plus static Playwright specs (in consuming projects, e.g. claim_management's `web/e2e/*.spec.js`) that nothing runs in-loop; no stage actually spins up the running app and drives the changed surfaces in a real browser between implement (`sst-dev-cycle`) and review (`sst-dev-review`), so the reviewer judges UI work from a diff alone and never sees runtime behavior. This phase adds a new chain stage that, after the dev cycle commits, resolves what changed, starts the project's local front+back-end stack, drives the affected surfaces in a browser (headed when a display exists, headless fallback), writes a structured findings artifact for the reviewer, then tears the stack down and exits cleanly — never persisting screenshots/traces or any test-time artifact inside the repo tree. Split per the transferable/proprietary model: a project-agnostic `sst-tester` (contract, lifecycle discipline, findings format, degrade/clean-exit guarantees) wrapped by `ssp-cm-tester` (the consuming project's exact ports, start/stop commands, auth-state path, and e2e specs).

**Design decisions (codified in the SKILL bodies; revisit before implementing if any is wrong):**
- D1 — Coverage: the tester RUNS the project's existing e2e specs mapped to the changed surfaces AND does exploratory browser checks of net-new functionality not yet covered; it does NOT author committed spec files (that stays the dev cycle's "failing tests first" job) and instead files any coverage gap as a finding.
- D2 — Headed/auth: headed when a display (WSLg/`DISPLAY`) is available, headless fallback otherwise; it NEVER blocks on interactive login — a stale/missing saved session degrades to a finding and it runs only the reachable surface.
- D3 — Artifacts: zero files written under any repo working tree; binary artifacts (screenshots/traces/video) go to a non-repo state dir (`~/.claude/state/sst-tester/<utc>/`), referenced by path; the reviewer-facing findings doc goes to the chain run-log dir (`<project>/.skill-runs/<run>/`, already gitignored).
- D4 — Self-skip: on a project with no documented local-run/browser path, the tester emits a one-line "no local-run path; nothing to exercise" and exits 0, so adding it to a non-UI chain is harmless.
- D5 — Read-only on the tree: the tester never commits, deploys, or edits repo source; it only starts/stops local servers, drives a browser, and writes the (out-of-tree / run-log) findings.
- D6 — Dev-authored guidance: the dev stage writes a brief `tester-guidance.md` to the run-log dir naming the most meaningful surfaces/flows to exercise for this cycle's changes (each tied to a changed file/feature); the tester reads it to prioritize the highest-value checks rather than re-deriving everything from the diff.
- D7 — Two skip paths so the tester only runs when it adds value: (a) **dev pre-empt** — when the cycle has no front-end/UI surface, the dev emits a `[skip-tester] <reason>` sentinel and the chain runner skips the tester stage entirely (never spawned), going straight to review; (b) **tester self-skip** — if spawned but it finds legitimately nothing FE/UI exercisable against the dev's work, it exits 0 as a no-op with a `verdict: skipped` record. A pre-empted or self-skipped tester is a valid, non-finding state for the reviewer (distinct from `degraded`).

- [ ] 41.1 [hard] **Author the `sst-tester` transferable.** Create `skills/framework/sst-tester/SKILL.md`: chain position (immediately after the dev skill, before the review skill), authority envelope (D5), the run lifecycle (read the dev's run-log `tester-guidance.md` + resolve changes from the dev handoff → self-skip to `verdict: skipped` if nothing FE/UI is exercisable → start the project's local stack → poll readiness with a timeout → drive the changed surfaces → collect findings → tear the stack down → exit), degrade-don't-hang (D2) and self-skip (D4), headed/headless policy (D2), artifact-out-of-tree rule (D3), and the "what changed" derivation (read `git show HEAD`, `docs/TODO.md` `## Just shipped`, and the SPEC items the dev cycle flipped to `[x]`). Frontmatter: `description: |` block scalar, `version: 1.0.0`, `model-floor: sonnet`, `effort-floor: high`, `user-invocable: true`. Acceptance: file exists and `bin/validate-frontmatter.py` passes; `/sst-sanitize-transferable skills/framework/sst-tester/SKILL.md` returns must-fix 0; body contains no port literal and no project-specific path or noun.
- [ ] 41.2 [medium] **Define the tester→reviewer findings contract.** Specify, in `sst-tester`, the findings artifact: a `tester-findings.md` (reviewer-facing) + `tester-findings.json` (machine-readable) written to the chain run-log dir `<project>/.skill-runs/<run>/`, with per-check records `{area, change_ref, status: pass|fail|needs-change, evidence (out-of-tree artifact path), recommendation}` plus an overall `verdict: green|red|degraded` and a one-line summary. Add a sample `tester-findings.json` under `tests/fixtures/`. Acceptance: the schema is documented in `sst-tester/SKILL.md` and matched by the fixture; a unit test in `tests/` parses the fixture and asserts the required keys; `bin/validate-frontmatter.py` clean.
- [ ] 41.3 [medium] **Teach `sst-dev-review` to consume tester findings.** In `skills/dev/sst-dev-review/SKILL.md` §0 (Inputs), add reading the run-log `tester-findings.{md,json}` when present; a tester `fail`/`needs-change` becomes (or strengthens) a review `[blocker]`/`[should-fix]`; a `degraded`/aborted tester run is itself surfaced; the §6 report template gains a `Tester: <green|red|degraded|skipped> (<n> checks)` line, and a `skipped`/pre-empted tester is treated as a valid non-finding state (distinct from `degraded`). Preserve back-compat: when no findings file exists, review proceeds exactly as today. Acceptance: SKILL.md documents the read + escalation + absent-file back-compat path; `/sst-sanitize-transferable` must-fix 0; `version` bumped.
- [ ] 41.4 [medium] **Insert `sst-tester` into the framework dev chains.** In `chains/dev-cycle-with-review.yaml`, `chains/dev-cycle-with-review-looped.yaml`, and `chains/dev-cycle-overnight.yaml`, change the `skills:` list to `sst-dev-cycle` → `sst-tester` → `sst-dev-review`; bump each chain `version`. Acceptance: the three YAMLs list `sst-tester` between the dev and review skills and validate against `schema/`; a test in `tests/` asserts the tester's index is exactly between dev and review in each chain.
- [ ] 41.5 [hard] **Author the `ssp-cm-tester` proprietary wrapper.** Create `<claim_management>/.claude/skills/ssp-cm-tester/SKILL.md` wrapping `sst-tester` with CM facts: backend `source ./.venv/bin/activate && unset APP_ENV && python web/server/cm_flask_api.py` (port 5003), frontend `cd web/client && npm start` (webpack dev, port 3000), readiness polls on both ports with a timeout, auth reuse of `web/e2e/.auth/state.json` (36h; stale → D2 finding), the changed-surface→`web/e2e/*.spec.js` mapping (run via `npx playwright test --config=web/e2e/playwright.config.js <spec>` with `--output` redirected out of tree) plus exploratory checks for net-new UI, full teardown (kill the :5003 and :3000 processes, close the browser), and the standing CM rule never to push/commit/deploy or touch `main`/`test`/`dev1`. Frontmatter: `transferable: sst-tester`, `base-version: 1.0.0`, `transferable-version: ">=1.0.0"`, `version: 1.0.0`, `model-floor: sonnet`. Acceptance: file exists; `bin/check-ssp-sync.py` reports it in-sync; `bin/validate-frontmatter.py` passes; body documents the exact start/stop commands, both ports, and the auth-state path.
- [ ] 41.6 [medium] **Insert `ssp-cm-tester` into `cm-cycle` + teach the CM reviewer.** In `<claim_management>/.claude/chains/cm-cycle.yaml`, set the `skills:` list to `ssp-cm-dev` → `ssp-cm-tester` → `ssp-cm-dev-review` and bump `version`; in `ssp-cm-dev-review/SKILL.md` mirror 41.3 (read the run-log tester findings, escalate fail/needs-change, surface degraded), and in `ssp-cm-dev/SKILL.md` mirror 41.9 (write `tester-guidance.md` for CM's changed UI surfaces, else emit `[skip-tester]`). Acceptance: `cm-cycle.yaml` lists the tester in position and validates; `ssp-cm-dev-review` references the tester findings; `bin/check-ssp-sync.py` clean for both CM wrappers.
- [ ] 41.7 [medium] **Clean-exit + artifact-hygiene enforcement.** Codify in `sst-tester` (general) and `ssp-cm-tester` (concrete) that the stage (a) writes zero files under any repo working tree, (b) tears down both servers and closes the browser even on exception/timeout (a `finally`/trap path), and (c) leaves no orphan `node`/`python`/`chromium` processes and no listener on the documented ports. Acceptance: both SKILL bodies document the guaranteed-teardown path and the out-of-tree artifact dir; a test/fixture walkthrough asserts `git status --porcelain` is empty after a run and the documented ports are free.
- [ ] 41.8 [medium] **Wire tooling, install, and docs.** Ensure `bin/install-skills.sh --list-new` surfaces `sst-tester` and installs it; add the `ssp-cm-tester` `base-version` pin so `bin/check-ssp-sync.py` exits 0; update `README.md`'s skill inventory + `CLAUDE.md` (and `templates/` if they enumerate the dev chain) to describe the new `dev → tester → review` order. Acceptance: `bin/install-skills.sh --list-new` lists `sst-tester`; `bin/check-ssp-sync.py` exit 0; `bin/validate-frontmatter.py` clean across all skills; full `tests/` suite green; README/CLAUDE.md describe the inserted stage.
- [ ] 41.9 [medium] **Dev stage writes tester guidance + the pre-empt sentinel.** In `skills/dev/sst-dev-cycle/SKILL.md`, after the commit step (§6/§7), add the branch: if the cycle touched a front-end/UI surface, write a brief `tester-guidance.md` to the run-log dir `<project>/.skill-runs/<run>/` naming the most meaningful flows/surfaces to exercise (each tied to a changed file/feature); otherwise emit a `[skip-tester] <reason>` sentinel on its final line and write no guidance. Acceptance: SKILL.md documents both branches with the guidance template and the exact `[skip-tester]` token; `/sst-sanitize-transferable` must-fix 0; `version` bumped.
- [ ] 41.10 [medium] **Chain runner honors the `[skip-tester]` pre-empt.** In `bin/skill-chain.py`, recognize a `[skip-tester]` sentinel emitted by the stage immediately preceding a tester stage and, when present, skip the tester (do not spawn it) and proceed to the next stage, recording the skip + reason in `MANIFEST.json`; never skip a non-tester follower. Mirror the existing sentinel-recognition machinery (`[no-work]` / Phase 36 guard). Acceptance: a `tests/` unit test asserts a `sst-dev-cycle → sst-tester → sst-dev-review` chain skips the tester and still runs review when the dev output carries `[skip-tester]`, runs the tester normally otherwise, and records the skip reason in the manifest; full suite green.

### Phase 42: unify the chain-run entrypoints into one CLI

**Context.** Launching a chain currently spans multiple scripts with overlapping, awkwardly-split options: `bin/skill-chain.py` (core — chain resolution, `--loop`, delay/jitter, harness, logging, rate-limit pause/resume, sentinels, `MANIFEST.json`); `bin/drive-chain.py` (a supervisory wrapper that re-spawns `skill-chain.py` to add `--max-budget-usd`/`--max-cycles`/Telegram event posts/`--profile`/`--label`, and forces every skill-chain flag to be passed after a `-- ` separator); the "overnight" pattern (`chains/dev-cycle-overnight.yaml` = `loop: 0` + jitter `[300,1800]`, paired with a remembered `drive-chain --max-budget-usd`); and `bin/skill-batch.py` (sister runner — one skill × N glob inputs, sharing `run_skill_with_retry`). The result is "which script do I use, and which flags go where?" friction — the `-- <forwarded-args>` split most of all. This phase collapses them into ONE canonical runner that owns every flag natively: wrapper features become first-class options, the overnight pattern becomes a preset, and batch-over-inputs becomes a mode — with thin deprecation shims so existing callers (the `*-chain-driver` skills, cron, docs) keep working through the migration.

**Design decisions (codified during 42.1; revisit if any is wrong):**
- D1 — One canonical entrypoint absorbs the others. Default: `bin/skill-chain.py` becomes the single script; `drive-chain.py` and `skill-batch.py` reduce to thin deprecation shims that forward to it. (Alternative: a freshly-named `bin/run.py` with all three as shims — chosen in 42.1; the default minimizes caller churn.)
- D2 — All flags in one parser; the `-- <forwarded>` separator is gone. `--max-budget-usd`, `--max-cycles`, `--telegram-env`/`--no-telegram`, `--profile`, `--label` become native optional flags that are inert when unset, so today's bare `skill-chain.py` behavior is unchanged.
- D3 — `--overnight` preset collapses the overnight pattern: expands to `--loop 0` + jitter `[300,1800]` and REQUIRES a budget/cycle cap (errors without one). An extensible `--preset` mechanism may bundle other common combos; full flags always remain available.
- D4 — Batch mode: one-skill-over-a-glob becomes a `--batch <glob>` mode (or `batch` subcommand) of the unified runner, reusing the shared retry/harness code `skill-batch.py` already imports.
- D5 — Back-compat: the shims emit a one-line deprecation notice and forward; all in-repo callers (the two `*-chain-driver` skills, cron, README, CLAUDE.md, templates) are migrated within this phase, so nothing depends on the split once it closes.

- [ ] 42.1 [hard] **Spec the unified CLI surface + entrypoint choice.** Enumerate every flag across `bin/skill-chain.py` + `bin/drive-chain.py` + `bin/skill-batch.py` + the overnight chain YAML; define the single merged argument set, the `--overnight`/`--preset` shorthand, the `--batch` mode, and decide the canonical entrypoint name (default: keep `skill-chain.py`; record rationale if renaming). Acceptance: a `docs/` section (or the runner `--help` epilog) lists the full flag set with each legacy flag mapped to its unified form and notes which scripts become shims; no flag requires `-- `-forwarding.
- [ ] 42.2 [hard] **Merge the `drive-chain.py` wrapper layer into the canonical runner.** Move budget gates (`--max-budget-usd`), `--max-cycles`, Telegram event posts (`--telegram-env`/`--no-telegram`, the four event classes), `--profile` resolution, and `--label` into `bin/skill-chain.py` as native optional flags that are inert when unset. Acceptance: a single `skill-chain.py` invocation runs a chain with budget caps + Telegram + profile natively (no second process, no `-- `); `tests/test_skill_chain.py` stays green; the budget/telegram/profile paths get tests (port the relevant `tests/test_drive_chain_telegram.py` cases).
- [ ] 42.3 [medium] **`--overnight` preset.** Add `--overnight` (and an extensible `--preset`) that expands to `--loop 0` + `--loop-delay-random 300,1800` and errors unless a `--max-budget-usd` or `--max-cycles` cap is set. Acceptance: `--overnight` with a cap expands to the documented defaults; without a cap it exits non-zero with a clear message; a unit test asserts both.
- [ ] 42.4 [medium] **Fold `skill-batch.py` into a `--batch` mode.** Expose one-skill-over-a-glob as `--batch <glob>` (or a `batch` subcommand) on the unified runner, reusing the shared retry/harness code; reduce `bin/skill-batch.py` to a deprecation shim. Acceptance: the unified runner runs a skill once per glob input; `skill-batch.py` still works + prints a deprecation notice; batch tests green.
- [ ] 42.5 [medium] **Deprecation shim for `drive-chain.py`.** Reduce `bin/drive-chain.py` to a thin wrapper that maps its args onto the unified CLI and forwards, printing a one-line deprecation notice; remove the duplicated wrapper logic. Acceptance: existing `drive-chain.py --chain ... --max-budget-usd ...` invocations still work via the shim; the wrapper logic now lives only in the canonical runner; `tests/test_drive_chain_telegram.py` passes (or is repointed).
- [ ] 42.6 [medium] **Migrate all in-repo callers + docs.** Update `skills/framework/sst-chain-driver/SKILL.md`, the proprietary `ssp-cm-chain-driver/SKILL.md`, cron entries (`CM_MANAGER_*` / chain-driver), `README.md`, `CLAUDE.md`, and `templates/SPEC.md` to the unified CLI and drop every `-- <forwarded-args>` / two-script example. Acceptance: a grep shows no in-repo caller depends on the two-script split or `-- `-forwarding; the `*-chain-driver` skills invoke the single runner; docs describe one entrypoint.
- [ ] 42.7 [easy] **Tests + validation green.** A test exercises the unified flag matrix (core + budget + telegram + `--overnight` preset + `--batch`) and confirms each shim forwards correctly. Acceptance: full `tests/` suite green; `bin/validate-frontmatter.py` clean; the validator CI entrypoint passes.

### Phase 43: review follow-ups (sanitize-seam fix + recovery-first reviewer)

Phase 43 (43.1-43.5) closed and migrated to `docs/SPEC-DONE.md`. The follow-up below was found in post-cycle review of commit `a98e902` and is open work for a later `/sst-dev-cycle`.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 43.6 [medium] [should-fix] `bin/skill-chain.py:417` (`_contract_violation_aborts`) — the relaxed abort decides "cycle recovered" from `git_sha_after != head_at_violation`, but `git_sha_after` (set at `skill-chain.py:1604`) is captured AFTER the auto-appended supervisor runs as the last skill in `skills_to_run`, and the supervisor commits findings-driven base-repo edits as its normal contract (advancing HEAD). So when the dev exits dirty without committing AND `sst-dev-review §0.2` fails to recover (e.g. tests failing in the dirty tree → it prints `[incomplete-cycle] tests failing` and exits without committing) AND the supervisor then makes any commit, the HEAD-advance proxy is satisfied → `_contract_violation_aborts` returns `False` → the loop continues against a still-incomplete, still-dirty cycle, defeating the Phase 36 guard in exactly the overnight-drain scenario Phase 43 targets. The HEAD-advance proxy is satisfied by any committing skill, not only by a genuine recovery. Proposed fix: decide recovery on the actual condition rather than the proxy — re-evaluate `_incomplete_cycle_detected(cwd)` (and/or `git status --porcelain` non-empty) at the loop-level abort check in `main()`, OR compare against a HEAD snapshot captured immediately after the recovery follower (review) instead of the post-supervisor `git_sha_after`; add a regression test where dev exits dirty + review fails to recover + supervisor commits → loop still aborts with `terminated_by: contract_violation`.
- [x] 43.7 [easy] [should-fix] `bin/skill-chain.py:1874` (`main()` contract-violation comment) — the three-line comment at lines 1874-1876 still describes the Phase 43.4 SHA-proxy mechanism ("abort only when HEAD did not advance ... A cycle the follower recovered (HEAD advanced)") that 43.6 replaced; the actual recovery signal is now "In-flight cleared by the recovery follower," not "HEAD advanced." A future engineer reading `main()` is directed to the wrong signal when debugging cycle-recovery behavior. Proposed fix: rewrite the comment to reference the Phase 43.6 mechanism: abort only when `_incomplete_cycle_detected` returns True (In-flight still set); the recovery follower clearing the In-flight line is the genuine recovery signal, not HEAD advancement.
