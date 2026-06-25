---
name: sst-dev-cycle
description: Autonomous test-driven development cycle. Reads the project's spec + handoff TODO, picks the next queued or unchecked item, writes failing tests first, implements until the full test suite is green, commits (code + tests + spec + TODO update in one commit), pushes, deploys if the project has a deploy path, and verifies production. Runs end-to-end without pausing for confirmation.
user-invocable: true
version: 1.14.0
model-floor: sonnet
effort-floor: high
---

# Autonomous TDD Cycle

One invocation = one shipped change. Read the spec, decide, write failing tests, implement, deploy, verify, commit + push. **No approval prompts between steps.** This skill is the user's standing authorization for the whole cycle.

## Operating principles

- **Run to 100% completion. Never stop to ask.** If a step fails, diagnose and fix the root cause and retry. Only escalate to the user if you've exhausted reasonable attempts on an external blocker (server unreachable, missing credential, ambiguous spec wording that can't be resolved by reading the code).
- **Tests define done.** Write the failing test first. If the test would require a mock that contradicts the real architecture, fix the test design — don't write implementation-first to "see what shape makes sense."
- **Difficulty-windowed batching per cycle.** The primary item's difficulty (`[easy]` / `[medium]` / `[hard]`) determines a target context-window band for **this skill's own input tokens**: easy 100-200k, medium 200-300k, hard 400-500k. These targets are the lead-agent window: this is the only skill in the chain whose context size is a function of a workload-sizing decision; review and supervisor consume what they consume regardless. The review's §2.10 batch-sizing check fires on this skill's number too — not the full-chain sum. Pick a coherent batch of related items (same files, same phase, same skill target, same concept, or a similar small mechanical change repeated across files) sized to fit the band. If the queue offers only one actionable item, ship it alone; if zero, fire the `[no-work]` bail in §0. Bundling *unrelated* items remains forbidden — the batch must be cohesive, not just adjacent. See §1 for the full picking + batching protocol and the `[batch-pick]` declaration format.
- **One commit, one push, then the invocation is over.** Implementation + tests + spec + TODO update (including the new Just-shipped line) ship as exactly one commit, pushed exactly once. No separate spec-only commit, no separate TODO-only commit, and no *second feature commit*: a single invocation produces at most one pick→implement→commit→push pass. When the batch holds several related items (§1), they all land in that one commit, declared up front in the `[batch-pick]` block; you do NOT pick the primary, commit it, then return to §1 for the next queue item and commit it separately. After §7's push completes, the cycle proceeds through §7a/§8/§9/§10 and then ENDS; finding more actionable items still sitting in `## Next up` or the spec does NOT license another commit in this invocation; those are the next invocation's work (or, if they were genuinely batch-eligible, they belonged in the up-front `[batch-pick]` and the single commit). A run that emits N commits + N pushes for N separately-picked queue items (a pick-commit-pick-commit loop) has broken this invariant, even when each individual commit is clean: it defeats per-cycle review (downstream review keys on one cycle commit), inflates the cycle past its difficulty-window band undetected, and turns one authorized cycle into N. The Just-shipped line format does NOT include the commit's own SHA — that's provably impossible (a commit cannot contain its own hash). Correlate Just-shipped entries to commits by the one-line summary + utc-iso + `git log --oneline --grep`.
- **Fix root causes, never mask failures.** No `@pytest.mark.skip`, no `xfail`, no `-k` to exclude failing tests, no deleting assertions "temporarily." If a test is wrong, fix the test with a clear rationale; if the code is wrong, fix the code.

## Handoff docs (read on open, update on close — every cycle)

Two canonical files per project carry cross-cycle state. Default location `<project>/docs/`; the project's harness-instructions file (e.g. `CLAUDE.md`) overrides if it points elsewhere via a `Handoff docs:` line.

- **`SPEC.md`** (or the project's existing primary spec — `docs/<project>_SPEC.md` is common) — long-lived phase checklists, closed-phase change logs.
- **`TODO.md`** — three sections: `## In flight` (one line per running skill), `## Just shipped (last cycle)` (newest-first, max 10), `## Next up (queued for next cycle)` (one line per item, ordered by impact).
- **`FUTURE-WORK.md`** (optional, at `docs/FUTURE-WORK.md` if the project uses it) — parking lot for deferred work, acceptance tests requiring human or chain-level verification, and items the user wants visible but not queued. **Read on open; never pick from.** The pick order is unchanged: `TODO.md > Next up` first, then the spec's next unchecked item.

Contract for every cycle:

1. **Open**: read both end-to-end before any other action. If `TODO.md` is missing, create it from `~/Dev/skill-set/templates/TODO.md` as the very first action; commit that creation as part of this cycle's single commit. Do not invent a different shape.
2. **Decide** (see §1 below): pick from `TODO.md`'s "Next up" if non-empty, else from the spec's next unchecked item.
3. **Mid-cycle**: append a single `## In flight` line at the start of work in this format: `- [<skill-name> @ <utc-iso>] <one-line>`. Rewrite (don't append again) as the work narrows. Do not commit mid-cycle "In flight" updates; they live unstaged until the close commit.
4. **Close** (see §6–7 below): clear the in-flight line; write the new Just-shipped line (`- <one-line summary> — by <skill-name> at <utc-iso>`, no SHA); if the cycle uncovered new work that doesn't belong in the spec, append it to "Next up"; trim "Just shipped" to the most recent 10 entries. Then commit everything in one commit.
5. `SPEC.md`, `TODO.md`, and the code change ship as one commit — never as multiple commits. The Just-shipped line does NOT include the commit's own SHA (impossible without an amend-then-rewrite hack that produces stale SHAs); readers correlate entries to commits by the one-line summary, not by hash.

**Spec sub-item IDs.** Every `- [ ]` item in `docs/SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 3.1 [hard] **description**`). IDs are assigned once per phase in 1-indexed order and never renumbered — closed or removed items leave their ID void (gaps are valid). Inserts between existing items use letter suffixes (`<phase>.<n>a`, …). When filing a `## Next up` entry or writing a commit message, prefer the ID (e.g. `3.1`) over "Phase 3 sub-item 1" for concision.

## 0. Pre-flight

1. Confirm the working directory is the project root (check for `.git`, the project's config/manifest file).
2. Activate any language-specific environment the project uses (venv, node_modules, etc.).
3. Confirm `git status` is clean. If there are pre-existing staged, modified, or untracked files — whether left by a prior aborted run OR produced outside any cycle (notebook/REPL execution outputs, regenerated lockfiles, build artifacts, formatter sweeps) — inspect each and dispose of it BEFORE starting: if a change is unrelated finished work worth keeping, commit it in its OWN separate commit first, so this cycle's commit stays scoped to the work you pick; otherwise stash or discard it. Do NOT carry a pre-existing change into this cycle's feature commit — **documenting it in the commit message does not make this OK** ("not *silently*" is not the bar; "not at all" is). Folding unrelated churn (a regenerated notebook, a lockfile bump) into a feature commit breaks per-commit review, `git bisect`, and `git revert`, and contradicts §7's "stage only the files you changed." **Exception:** the project's supervisor (when the project runs `sst-supervisor` or a `<project>-supervisor` proprietary counterpart) routinely leaves direct-overwritten edits to peer SKILL.md files uncommitted in `<cwd>/.claude/skills/*/`. Per the supervisor's contract, those files are NOT part of any dev cycle and must NOT trigger a stop. Concretely: if `git status --porcelain` shows ONLY paths under `.claude/skills/`, proceed without stashing or checking out. Any other modified or untracked files (project code, tests, docs, configs, generated artifacts) — apply the rule above.
4. Read `docs/SPEC.md` (or the project's primary spec — see §1) end-to-end.
5. Read `docs/TODO.md` end-to-end. If missing, create it from `~/Dev/skill-set/templates/TODO.md` and stage it for inclusion in this cycle's single commit; do NOT make a separate "create TODO" commit.

   If `docs/FUTURE-WORK.md` exists, also read it end-to-end. **Do not pick from it** — it is the project's parking lot for deferred work and acceptance tests requiring human verification; the pick order is unchanged.

6. **Empty-queue bail.** If ALL three conditions hold, exit 0 immediately without picking any item, writing any test, or making any commit:
   - `TODO.md`'s `## Next up (queued for next cycle)` section contains no `- ` entries (only the `<!-- ... -->` template comment, or empty); AND
   - `docs/SPEC.md` (or the project's primary spec) contains no remaining `- [ ]` checkboxes (every checkable item is `[x]`); AND
   - The user's prompt to this skill carries no specific task or item to work on (no override).

   **Priority is not a bail criterion.** If `## Next up` contains any `- ` line — including entries tagged `[low]` — the first condition above is false and the bail MUST NOT fire. `[low]`-priority items are work in the queue, not steady state. Priority affects the order in which items are picked, not whether the queue is non-empty. Do not bail when only `[low]` entries remain.

   Print exactly one line on stdout BEFORE exiting:

   ```
   [no-work] queue empty and spec fully checked; nothing to do
   ```

   The chain runner recognizes this `[no-work] <one-line reason>` sentinel and aborts the loop entirely (no review, no supervisor, no further iterations), saving the per-iter overhead of running downstream skills against an empty commit. The bail is the correct response in steady state, not a defect. **Do NOT** pick a just-shipped item, invent speculative work, scope-creep on existing skills, or fabricate a `Next up` entry to consume. A user-provided override (a specific item or task in the prompt) suppresses the bail; queue-empty + spec-clean alone, with no override, fires it.

   Inherits to proprietary `<project>-dev-cycle` skills automatically via `transferable:`; no per-project change needed to opt in.

7. **Phase-completion bail (branch-per-phase projects only).** Some consuming projects map each SPEC phase to its own `feature/<name>` branch and record the mapping in a `## Operational scope` section of `docs/SPEC.md` (one line per phase: HEAD branch → phase number). When that section exists, derive the **active phase** from the current branch BEFORE picking in §1:

   - Read the SPEC's `## Operational scope` branch map and match `git branch --show-current` to its phase entry. **If the project has no `## Operational scope` section** (skill-set itself, and any project not using branch-per-phase), this bail cannot fire — skip it entirely and continue to §1, picking normally.
   - When a match resolves an active phase `<N>`: that phase is **complete** iff every `- [ ]` item under phase `<N>`'s SPEC section is `- [x]` AND no `## Next up (queued for next cycle)` entry is scoped to phase `<N>` (an entry is "scoped to phase `<N>`" when its leading `<phase>.<n>` ID has `<phase> == N`, or its prose explicitly names that phase). In a branch-per-phase project only active-phase work is actionable on the current branch, so `## Next up` / SPEC items scoped to a *different* phase do NOT count and do NOT suppress this bail.
   - **On a complete active phase:** print exactly one line on stdout and exit 0:

     ```
     [no-work] phase <N> complete on <branch>; awaiting human branch setup for phase <N+1>
     ```

   This is a **phase-scoped variant** of the §0-6 empty-queue bail, not a replacement. The global bail fires only when the WHOLE spec is `[x]`; this one fires when the *active* phase is done even though later phases still carry open `- [ ]` items. The chain runner recognizes any `[no-work] <reason>` line as a loop-aborting sentinel (same `terminated_by: "no_work_bail"` manifest path — confirmed by the `NO_WORK_SENTINEL_RE` regression tests in `tests/test_skill_chain.py`), so no runner change is needed. **Do NOT scope-creep onto a later phase's open items just because they exist:** the human owns the decision to merge the completed branch and open the next phase's branch. A later phase having open `- [ ]` items (in SPEC or `## Next up`) does NOT suppress this bail.

   **Note:** the post-completion branch-setup handoff (recording the human-blocker entry and notifying the human) is handled by `sst-supervisor` (post-chain), not by this skill. The dev prints the sentinel and exits; the supervisor detects the `[no-work] phase <N> complete` line in its transcript scan and files the idempotent handoff entry. Phase-completion handoff writes live in the oversight layer only.

## 1. Decide what to work on

Find the project's spec or roadmap. Common locations: `docs/SPEC.md`, `docs/ROADMAP.md`, `TODO.md`, `README.md`, the top-level docstring of a main module, or a `docs/<project-name>_SPEC.md` variant. If multiple exist, prefer the most-recently-edited one and scan for a "primary spec" pointer.

### Pick the primary

1. **`TODO.md`'s `## Next up`** — top entry first, including `[low]`-priority entries when nothing higher is queued. Priority controls ordering within the queue, not actionability. These are queued items already vetted by the previous cycle, supervisor, manager, or user. Treat the source/reason annotation on the entry as the authority for *why* you're doing it.
2. If `## Next up` is empty: first open `- [ ]` in the latest active SPEC section. If the spec uses non-checkbox flagging conventions ("V1 Status", "Known Issues", "Open"), pick the next listed item there.
3. If everything checkable is `[x]`: look at any "Deferred / Out of scope" list for items whose blocking reason no longer applies.
4. **User directive** — if the user handed you a specific request, that overrides the above; still append it to `## Next up` first so the audit trail is intact.

The primary's difficulty (`[easy]` / `[medium]` / `[hard]`) is the cycle's difficulty for both routing (the `[picked-difficulty]` sentinel below) and window-sizing (the `[batch-pick]` band declared next).

### Batch related items into the cycle

Don't ship just the primary if related siblings fit. Walk the rest of `Next up` AND the SPEC's open `[ ]` items. Add an item to the batch only when ALL of:

- **At-or-below the primary's difficulty.** The runner already chose the model + effort at the primary's tier; no `[hard]` add-ons to a `[medium]` cycle.
- **Related** by at least one of: same files touched, same SPEC phase, same skill target, same concept, OR a similar small mechanical change repeated across files (e.g. tagging N skills, hoisting one rule across N siblings, fixing the same typo across N spec entries).
- **Combined estimated context fits the primary's band.** Target input-token windows by difficulty (judgment-estimated from chunk shapes you know; these are this skill's own tokens — the review's §2.10 check fires on the same number, not the full-chain sum): `[easy]` 100-200k, `[medium]` 200-300k, `[hard]` 400-500k. Reference chunk-shape sizes — prose patch ~30-60k, schema field + runner support + spec entry ~50-100k, new bin/ helper ~60-120k, full new transferable skill ~150-250k.
- **One coherent commit.** No merge-conflict risk between batched items; no contradictory acceptance criteria; the change-set still tells one story in the commit message.

If only the primary is actionable across both surfaces, ship it alone (the primary IS the entire batch). If zero items are actionable across both surfaces, exit via the `[no-work]` bail in §0 step 6 — do NOT pad the batch with speculative work or invent a `Next up` entry to consume.

Bundling *unrelated* items remains forbidden. The batch must be cohesive (sharing files / phase / concept / mechanical pattern), not just adjacent in the queue.

### Declare the batch BEFORE §2

After the In flight line is written and BEFORE the `[picked-difficulty]` sentinel below, print one block to stdout on its own lines:

```
[batch-pick] N items @ <difficulty>; window-target ~XXk; rationale: <one-line>
- <item 1 one-liner>
- <item 2 one-liner>
```

Single-item picks still emit the block: `[batch-pick] 1 items @ <difficulty>; window-target ~XXk; rationale: only actionable item this cycle` (or whatever brief rationale fits). The block is uniform across batch sizes — omitting it on single-item picks would disable downstream batch-coherence review and break the contract. The chain runner captures this for the iter MANIFEST; downstream skills (review, supervisor) read it to validate that the actual commit's diff + SPEC `[x]` flips + `Just shipped` entries match the stated batch composition + rationale.

### Tie-break + record

If multiple equally-related groupings exist: prefer the grouping that closes a higher-impact item first → smallest combined surface → most-independent items.

Record the pick: TodoWrite entry covering the batch (one TodoWrite item per batched SPEC/TODO item, or a single rolled-up entry referencing the `[batch-pick]` block — your call). Then write one `## In flight` line in `TODO.md` covering the whole batch: `- [<this-skill-name> @ <utc-iso>] <one-line summarizing the batch>`. Single line even for multi-item batches; rewrite (don't append) as the work narrows.

Don't commit yet; this gets committed alongside the code change at the end of the cycle.

### Difficulty label & sentinel emit (model + effort routing)

After the `[batch-pick]` block, read the primary's leading difficulty bracket. Item shape: `- [ ] [hard] <description>` in `SPEC.md` and `- [hard] <description>. Reason: ...` in `TODO.md`'s `## Next up`. Three valid values — `easy` / `medium` / `hard` — mapping to `(model, effort)` tiers `(haiku, low)` / `(sonnet, medium)` / `(opus, high)`; see `~/Dev/skill-set/templates/SPEC.md` "Difficulty labels" appendix for the full contract and per-tier guidance. If the primary has no parseable label (expected during the contract-bump rollout window when many existing items are still unlabeled, including any user-provided override that didn't carry a tag), print exactly one line on stdout:

```
[bad-label] item missing difficulty; defaulting to medium
```

and treat the tier as `medium`. Then print exactly one line on stdout BEFORE the first §2 tool call:

```
[picked-difficulty: <tier>]
```

The chain runner captures this sentinel as the authoritative tier for any skill that runs after this one (review, supervisor, etc.); the runner resolves `effective_model = max(<tier-model>, skill.model_floor)` and `effective_effort = max(<tier-effort>, skill.effort_floor)` independently per axis, so a skill's floor wins on either axis when it is stricter than the item's tier.

Do NOT downgrade `[hard]` to `[easy]` to fit a quota; if the budget feels tight, queue a follow-up `Next up` entry asking the user to confirm the route AND ship the picked item at the labeled tier (or skip this cycle if the user-confirmation is needed first). Do NOT upgrade `[easy]` to `[hard]` either; the labels are the queue author's contract with the runner. The graceful-degradation `[bad-label]` warn becomes a hard exit in a future framework cycle once the migration backfill is complete; treat unlabeled items as a queue-hygiene gap to fix opportunistically (label them in `## Next up` when you touch them for any other reason).

Emission order at iter start, top to bottom: TodoWrite → `## In flight` line → `[batch-pick]` block → `[picked-difficulty: <tier>]` → first §2 tool call.

**Known model-behavior gap.** Despite these instructions, models occasionally skip the `[batch-pick]` / `[picked-difficulty]` emission. The runner records `batch_pick_missing = True` in the iteration manifest when the block is absent; downstream review + supervisor fall back gracefully. This is a formally-accepted degradation (root-cause decision 2026-06-18): the emission contract above remains canonical and `batch_pick_missing` is the mitigation.

## 2. Write failing tests

**Before writing any implementation code, write the tests that define the new functionality.**

1. Identify the right test file. Mirror the naming and style of adjacent tests.
2. Write tests that describe the desired behavior at the right level:
   - For user-facing changes: an end-to-end test that exercises the actual user journey (Playwright / browser automation for web; CLI invocation + output check for command-line tools; API call + response-shape assertion for backends).
   - For library/internal changes: unit tests on the public interface.
   - Always include at least one adversarial case (bad input, unauthenticated caller, boundary condition) and any invariant the change must preserve.
3. Run just the new tests to confirm they fail for the expected reason (missing feature, not broken test setup):
   ```bash
   <test-runner> <new-test-file> -v
   ```
4. If a new test passes immediately, strengthen it until it fails or delete it — a passing new test either doesn't test the new behavior or is redundant.
5. Confirm existing tests still pass at this point. You should not have broken anything yet.

## 3. Implement

1. Write only the code required to make the failing tests pass. Reuse existing helpers and patterns; don't invent parallel abstractions.
2. After each change, re-run the failing tests. As each goes green, move on.
3. Always read the target file before editing. Use precise string matches.
4. For web projects: if you change backend code, restart the local dev server before re-running browser tests.
5. **Sanitize transferable edits NOW — right after the edit, before §4 (the seam fix, Phase 43/D1).** If this implementation edited any transferable `SKILL.md` (any path matching `skills/<category>/<sst-*>/SKILL.md`), run the sanitize gate at this point — immediately after the edit and BEFORE you run the §4 verification:

   ```
   /sst-sanitize-transferable <path-to-SKILL.md>
   ```

   Inline assessment of the change does not satisfy this requirement; the sub-skill must be invoked even if the change appears obviously safe. Read the resulting findings file. Any `must-fix` finding blocks the cycle: rewrite the prose to remove the banned token (or confine the change to a proprietary skill only), then re-run the gate before continuing to §4. Record the verdict for the commit message body as `Sanitize: must-fix=N` (e.g. `Sanitize: must-fix=0`); you will write it in §7. Running the gate **here**, not as the last step before the commit, is the whole point of Phase 43: when the sub-skill returns clean you still have §4 (verify), §6 (spec + TODO), and §7 (commit) ahead of you, so its return can never be mistaken for the end of the cycle. See §5 for the rationale. If no transferable `SKILL.md` was edited, skip this step.

## 4. Verify — fail-loop until green

```bash
<test-runner> <relevant-tests> -v     # fast iteration
<test-runner> <full-suite>            # final gate
```

Record the full-suite pass count before your change. After, it must be `old_count + <new_tests>` (or higher, if you incidentally fixed a flake). If it drops, you broke something — fix before continuing.

**A default-filtered suite can hide a broken deliverable.** Many projects exclude slow or environment-dependent tests from the default runner invocation — opt-in markers (`notebook`, `integration`, `e2e`, `slow`, `live`) or a separate suite directory; check the test config (`pytest.ini` / `addopts`, the `Makefile`'s test targets, `package.json` scripts) so you know what the default run actually executes. The default "full suite" then reports green without ever running those tests. When the change you shipped is an **executable artifact** (a notebook, a script, a migration, a generated config) OR touches a code path that only a default-excluded test exercises, run those excluded tests explicitly before the gate counts as passed — e.g. `<test-runner> -m <marker> <your-test-file>`. A green default run that skipped your deliverable's own execution test is a false green: it proves the code you did not exercise still imports, not that the artifact you shipped actually runs. Do not flip the SPEC item to `[x]` on a false green — that ships a broken deliverable that the next reviewer has to catch.

On failure:
- Read the actual assertion. Don't guess.
- Fix the root cause. If a test is incorrectly asserting, fix the test with a clear rationale noted in the commit message; if the code is wrong, fix the code.
- Re-run. Repeat until green.
- **Never skip, xfail, or `-k`-exclude failing tests to move on.**

If the project has known-flaky test files that are separately tracked, explicitly list them in the command (ignoring a known-flaky file is fine; ignoring a file because YOUR change made it fail is not).

For UI changes, also verify in a real browser (Playwright MCP against a local dev server). Target zero console errors. Stop the local dev server when you're done verifying.

## 5. Sanitize transferable edits — runs in §3, never here (the seam fix)

The transferable sanitize gate is invoked in **§3 step 5**, immediately after the edit and before §4 verification. It is deliberately NOT a step of its own wedged between test-green and the commit. This is the Phase 43 seam fix.

**Why the relocation matters.** The sanitize sub-skill runs via the Skill tool and returns control to THIS cycle; its findings file is a checkpoint, not the cycle's deliverable. When the sub-invocation was the LAST `/skill` step before the commit, models repeatedly treated its clean `must-fix=0` return as task-completion and stopped their turn before the SPEC-flip / `git commit` + push — leaving a dirty tree that tripped the chain runner's `incomplete-cycle` contract violation and aborted the loop. Running the gate back in §3, with §4 (verify) + §6 (spec + TODO) + §7 (commit) all still ahead of it, removes that seam: no sub-skill return ever sits immediately before the commit.

By the time you reach this point the gate has already run (or was skipped because no transferable `SKILL.md` was edited). Do not invoke `/sst-sanitize-transferable` here. Carry the `Sanitize: must-fix=N` verdict you recorded in §3 forward into the §7 commit message, then proceed: §6 (flip `SPEC.md`, finalize `TODO.md`) → §7 (single commit + push). The commit is the skill's final action; the cycle is not done until §7 has pushed.

## 6. Update the spec + TODO.md (all updates in a single pass, no SHA in Just-shipped)

**`SPEC.md`**: flip `- [ ]` to `- [x]` for what you shipped. If this closes a sub-phase or milestone, add a section mirroring the format of the most recent completed one: 1-paragraph context, bulleted checklist of changes with file citations, test-count delta. Update any index / status summary file that the project keeps (e.g. a `CLAUDE.md` phase list). **This section asserts only what is verified by §6 time** — code and test facts known now. Do NOT state a deploy or runtime fact you only check later in §8/§9 (e.g. "deployed and healthy", "the external key is present", "the cron is live"): §6 runs before deploy and verify, so any such claim is unverified the moment you write it. Record deploy/verify outcomes after §9, and if §9 contradicts a line you already wrote here, correct this section before §10. A result block that contradicts the same cycle's own verify outcome is a ship-blocking defect, not a cosmetic nit.

**E2e-only guard.** Before flipping `- [ ]` to `- [x]` for any item whose acceptance criteria require running against a live stack (an e2e spec, an integration test that only passes against a real service, or any test the suite runs in parse-only mode such as `playwright --list`): you MUST have actually run that test against the live stack this cycle. A green test suite from a parse-only or mock-only runner does not close a live-stack requirement. If the live stack is not available this cycle, do NOT mark the item `[x]`. Instead, leave the item open and append a `[needs-live-stack] <one-line>` follow-up to `## Next up` naming the specific test and target service. Do not summarize the item as closed in Just-shipped — the item is not done.

**Synthetic-data-masking guard.** A test that injects the data a NEW fetch/merge is meant to produce does NOT satisfy that change's coverage — it pre-populates the result the fetch would normally return, so the fetch bug is invisible to the suite. If a changed fetch or merge path has no test that drives the real fetch or asserts the fetch is invoked with the correct arguments, the item's coverage is incomplete even when the suite is green.

**`TODO.md`** — four updates, all applied before committing:

1. Clear the `## In flight` line you wrote in §1 (delete it entirely; the "Just shipped" entry replaces it).
2. Prepend a new entry at the top of `## Just shipped (last cycle)` in format: `- <one-line summary> — by <this-skill-name> at <utc-iso>`. **No SHA.** A commit cannot contain its own hash — any SHA you write would either be a placeholder requiring amend-rewrite (the SHA goes stale the instant you amend) or a fake/dangling reference. Downstream consumers (sst-dev-review, sst-supervisor, sst-manager, human readers) correlate Just-shipped entries to commits via the one-line summary and `git log --oneline --grep`; git log is the ledger, TODO is the summary.
3. If you uncovered new work that doesn't merit a spec edit (small follow-ups, adjacent fixes, deferred polish), append each to `## Next up (queued for next cycle)` with format `- <one-line> — <reason/source>`.
4. Trim `## Just shipped (last cycle)` to the most recent 10 entries; older entries are reflected in `SPEC.md` checkboxes and `git log` already.

## 7. Commit + push (single commit, no extras)

Stage only the files you changed (by name — no `git add -A`, which sweeps up secrets and noise). Bundle implementation + tests + spec update + TODO.md update + any index-file update in ONE commit. **The `git commit` + `git push` below is the skill's final action** — by Phase 43's seam fix there is no `/skill` sub-invocation (the sanitize gate already ran in §3) between the §4 test-green point and this commit, so nothing here should make you stop short of pushing:

**Commit-message rule (read BEFORE composing the heredoc):** never append a `Co-Authored-By: Claude ... <noreply@anthropic.com>` trailer (or any AI-coauthor trailer variant). Empirical: the prior placement of this rule BELOW the heredoc was being skipped by models that copied the template top-down, and the trailer leaked into the majority of recent cycle commits despite the explicit ban. The heredoc body below ends at `EOF` — nothing else goes after `Test count:`.

```bash
git add <code-files> <test-files> <spec-file> docs/TODO.md <index-file>
git commit -m "$(cat <<'EOF'
<Scope>: <one-line imperative summary>

<Paragraph on why this change, what it does, and any non-obvious
decisions. Reference the failing-test evidence or the issue it closes.>

Test count: <old> → <new>.
EOF
)"

git push origin <branch>
```

**Never make a separate "docs: record <sha> in TODO" commit, and never `git commit --amend` to rewrite a Just-shipped SHA**. The Just-shipped line intentionally omits the SHA for exactly this reason — a commit cannot contain its own hash, and amend-based workarounds produce dangling references that confuse forensic work. The one-line summary + utc-iso is sufficient to locate the commit in `git log`.

Scope tags match the project's convention (examples: `Auth:`, `UI:`, `Docs:`, `Tests:`, `Deploy:`, `Infra:`, or a feature area like `Leads:`). **Never use `Review:` as the scope tag for a dev-cycle commit** — that prefix is reserved for the `sst-dev-review` skill's own follow-up commits, which the review skill emits to add SPEC/TODO entries (`Review: follow-ups from <scope>: ...`) on top of a finished dev cycle. When the dev-cycle picks a review-follow-up item out of `## Next up` (the item itself originated from a `Review:` commit), the dev's own commit still uses a scope tag reflecting **what the dev-cycle changed**, not the source of the work — e.g. `Tests:` for a test-strengthening cycle, `<phase>.<n>:` for a cycle continuing a SPEC phase, the original feature-area tag for an implementation change. The `sst-dev-review` walk-back rule (§0.4 there) treats `Review:`-prefixed commits as non-dev-cycle commits and walks past them to find the next reviewable commit; a misnamed prefix causes the cycle's actual dev work to be silently skipped by the next review.

Never commit `.env` files, credentials, or local scratch files. If the project gitignores config dirs (e.g. `deploy/`, `docs/` in some layouts), those changes won't reach the remote — you'll need the project's separate sync mechanism (scp, rsync, a sync script) for those.

## 7a. Tester handoff (immediately after §7 push)

After `git push origin <branch>` completes, write the tester guidance or pre-empt the tester. This step is the dev skill's contribution to the `dev → tester → review` chain: the tester reads the guidance to prioritize the highest-value checks rather than re-deriving everything from the diff; a pre-empt saves the tester from being spawned at all for non-UI cycles.

**If the cycle touched a front-end/UI surface** (any changed file under a front-end directory, a changed route, a changed component, a changed e2e spec, or new UI-visible behavior from the SPEC item): write a brief `tester-guidance.md` to the chain run-log dir. Find the run-log dir by scanning `.skill-runs/` for the most recently-created directory, or by reading the `[log-dir] <path>` line printed by the chain runner before any skill started. Template:

```
# Tester guidance for <scope-tag>: <description>

Surfaces to exercise (in priority order):
- <route/component/view>: <what to check, tied to <changed-file or SPEC-id>>
- ...
```

Keep the list short (3-5 items max), ordered by user-facing impact. Each entry ties a changed file or SPEC item to the specific browser interaction worth exercising. Do NOT write committed spec files — that is the dev cycle's TDD job, not the tester's.

**If the cycle touched NO front-end/UI surface** (a pure backend, CLI, schema, prose, or framework-internal change with no visible browser surface): emit exactly one line as the final line of this skill's output:

```
[skip-tester] <reason>
```

Where `<reason>` briefly names why the tester stage should be skipped (e.g. `no front-end surface in this cycle`, `backend-only change: bin/skill-chain.py`, `prose-only: docs/SPEC.md`). Write no `tester-guidance.md`. The chain runner recognizes `[skip-tester]` from the preceding skill and skips the tester stage when the immediately-following skill's name ends in `-tester`, proceeding straight to review.

**Mutually exclusive: write guidance XOR emit `[skip-tester]`, never both (hard terminal rule).** The two branches above are ONE terminal decision, not two independent emissions:

- **Mixed change sets are guidance cycles.** If ANY changed file is a front-end/UI surface (a component, route, view, style, or a changed/new e2e spec), write `tester-guidance.md` and do NOT emit `[skip-tester]`, even when the change set ALSO touches backend, CLI, schema, or docs files. The presence of non-UI files alongside a UI surface never licenses a skip. `backend-only` / `docs-only` is a valid skip reason ONLY when EVERY changed file is non-UI.
- **Terminal self-check before this skill exits.** Confirm you did exactly one of the two. If you wrote `tester-guidance.md` at any point this run, you MUST NOT also emit a `[skip-tester]` final line; if you emitted `[skip-tester]`, you MUST NOT have written `tester-guidance.md`.
- **Runner backstop (do not rely on it).** If the runner sees a skill BOTH write `tester-guidance.md` AND emit `[skip-tester]` in one run, it VOIDS the skip and runs the tester anyway (recorded as `tester_skip_voided` in the iter manifest), choosing the safe direction so a touched surface gets exercised. That backstop exists because prose-level "pick exactly one" did not converge on its own; it is a safety net, not a license. Emitting both is still a contract violation that signals muddled scope reasoning even when the outcome is harmless. Decide once.

## 8. Deploy

If the project has a deploy path (SSH to a VPS, CI workflow, `deploy/` script, container rebuild), run it. The specific command is project-specific and should be documented in the project's `CLAUDE.md`, `README.md`, or a deploy script — read it there, don't guess.

If the change involves a schema migration or new config, run that first before restarting the service. Never use `kill -9` / `pkill -9` on a managed service; use the service's own stop/start or graceful-reload command.

After the deploy completes, confirm:
- The service health check returns OK.
- The expected number of worker processes is running (if the project uses a worker model).
- No stack traces in the most recent log entries.

## 9. Verify — the deployed artifact AND the external contracts it depends on

"Verify" means exercising the change against the **real systems it touches**. There are two independent surfaces, and a cycle must cover whichever ones apply:

1. **The environment you deployed to** (§8). Skip this when the project has no deploy path — a local-only artifact correctly has nothing to verify here.
2. **Any external service or API your code consumes.** This surface is independent of deployment: a project can have no deploy path of its own yet rest its entire correctness on an external API contract. **"No deployment" never implies "no live verification."** Whenever the change's correctness depends on an external contract, you MUST make at least one real call to that service and assert that the actual response shape matches what your code — and the test mocks — assume. Tests that pass only against mocks you authored prove the code is self-consistent, not that it matches reality: a mock encoding a wrong schema produces green tests over broken code. Do NOT collapse this into "deployment is N/A, so verification is N/A" — that conflation ships code that cannot work against the real service.

Exercise the specific thing you changed against the live environment:
- API/external-service consumer: a real HTTP call (with real credentials if the endpoint needs them), assert the response shape — keys, nesting, required params. If the endpoint rejects the request your code builds, that is a defect found, not a reason to skip.
- API change (a service you own): real HTTP call with real credentials, assert the response shape.
- UI change: Playwright MCP against the production URL, navigate to the changed page, 0 console errors.
- Background-job change: submit a real small job and confirm it completes.

Reuse the project's permanent test account or staging credentials — never create ad-hoc accounts.

If verification fails:
- Minor issue (copy, layout nit): fix forward in a new cycle.
- Regression that breaks existing users: revert the deploy (`git revert HEAD; git push`, then re-run the deploy command) and file the proper fix as the next cycle's work.
- External-contract mismatch (the real API doesn't match what the code/tests assume): the code is non-functional against reality — fix the code and the mocks to match the real contract before closing the cycle. If the fix is out of scope for the picked batch, file it as the next cycle's top `## Next up` item rather than closing a cycle that shipped code that can't run against the live service.

## 10. Done

The cycle is complete when:
- All new and existing tests pass locally.
- The commit is pushed.
- The deploy completed and the service is healthy (or the project has no deploy path).
- The changed behavior is verified live — against the deployed environment and/or the external contracts the change depends on.
- The spec reflects the new state.

Report a terse summary to the user: commit SHA, one-line description, test-count delta, production verification result. No follow-up question.
