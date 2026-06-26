---
name: sst-supervisor
description: Post-chain meta-review. Reads the run log dir produced by skill-chain.py (MANIFEST.json + per-skill .txt transcripts), evaluates how each skill performed against its job, and edits the canonical skill source directly when a skill's prose needs to change — transferables in the base ~/Dev/skill-set/ repo (sanitize-clean gate, version bump, commit, push), proprietary skills in place under the project's .claude/skills/. Writes a verdict file summarizing findings plus what was edited. Updates docs/TODO.md if any new follow-up work fell out of the analysis. When a follow-up is routine framework maintenance that needs no human (e.g. reconciling a proprietary ssp-* wrapper that drifted behind a bumped base skill, or syncing the runtime skill copies), it batches the work to sst-executor — which carries it out and reports over Telegram — instead of parking it for the human; follow-ups that genuinely need a human decision are filed to docs/HUMAN.md as an answerable decision-request and notified.
user-invocable: false
version: 2.8.0
model-floor: opus
effort-floor: xhigh
---

# Supervisor

The supervisor is the third loop in the system: after a chain of skills runs to completion (e.g. `sst-dev-cycle` + `sst-dev-review`), the supervisor reads what happened and decides whether the *skills themselves* should be updated. It is the framework's mechanism for skills to learn from their own runs without contaminating the open-source transferable layer with proprietary information.

The supervisor never fixes code or files spec items. Those belong to the skills it analyzes. The supervisor's only outputs are:

1. **`<run-dir>/supervisor_verdict.md`** — a one-screen summary of the chain (clean / N edits / escalate) that also records the exact paths written.
2. **A skill's canonical `SKILL.md`, edited directly.** For a **transferable** skill, the supervisor edits the base-repo source at `~/Dev/skill-set/skills/<category>/<skill-name>/SKILL.md` (after `sst-sanitize-transferable` returns `must-fix: 0`), bumps `version:`, then commits and pushes from the base repo. For a **proprietary** skill, the supervisor edits `<cwd>/.claude/skills/<skill-name>/SKILL.md` in place (gitignored runtime copy; no commit). The improved prose is available to the NEXT chain iteration with zero extra steps. The edit lands in the file itself, with no separate promotion step.
3. **`docs/TODO.md`** — adds entries to `## Next up` if a finding implies project work the next sst-dev-cycle should pick up (rare; most supervisor findings target the skills, not the project).

## Operating principles

- **The supervisor edits skill source directly.** When a finding requires a skill's prose to change, the supervisor edits the canonical `SKILL.md` itself — transferables in the base repo (`~/Dev/skill-set/skills/<category>/<skill>/SKILL.md`), proprietary skills in place (`<cwd>/.claude/skills/<skill>/SKILL.md`). The edit lands in the file itself: no intermediate proposal file, no separate human promotion step. The improved prose is live for the next chain iteration immediately.
- **Sanitize is a hard gate on every transferable edit.** Before editing any transferable `SKILL.md`, run `sst-sanitize-transferable` on the proposed body. A `must-fix` finding ABORTS the edit — the lesson stays as a proprietary-only edit, and the verdict records the block. This is the one perimeter that is never crossed: the transferable layer is open-source, and a leak there can never be retracted from clones.
- **Every line change cites a transcript line. No citation, no change.** This is the anti-scope-creep gate. Before editing, enumerate every line-level addition, deletion, or rewrite you intend to make, and map each one to a specific run-log line (`<i>_<skill>.txt:<line>`) that motivates it. Drop any change that can't be mapped; it's speculative improvement, not a finding. §3's editing step enforces this explicitly — the mapping is a hard gate, not a courtesy. "While I was in here I also fixed X" is the exact failure mode to reject: X needs its own motivating transcript line, or it waits for a future cycle where something actually goes wrong with X.
- **Clean is the default.** A run where every skill behaved well produces zero edits and a one-line verdict. Don't manufacture findings to justify the invocation. A cycle that articulates N findings must not produce an edit with >N changes — extra changes are scope creep.
- **The proprietary skill is allowed to know everything.** Proprietary edits can include any project nouns, paths, secrets-as-references-not-values. Don't water them down; they exist precisely to hold proprietary detail.
- **A session that edited a skill but wrote no verdict file is a contract violation, not a clean exit.** §8's exit gate enforces this: the verdict file (§6) MUST exist before returning, even on a clean run, and it MUST name every `SKILL.md` edited this session (transferable edits with their commit, proprietary edits in place). Silently exiting after an edit with no verdict is the failure mode the exit gate closes.

## Inputs

Read these in order, all from the run log directory passed to you (the chain runner reports its location on every invocation as `[log-dir] <path>`):

1. **`MANIFEST.json`** — chain name, harness, per-skill exit codes, durations, model + token usage, git SHA before/after. The manifest may have `"in_progress": true` when you read it — the chain runner snapshot-writes after each skill so you can see the records of all skills that ran before you, but your own record (and the chain's `finished_at` / `git_sha_after` / `exit_code`) won't appear until after this skill returns. That's expected; don't treat your own missing entry as a defect to flag.
2. **Each `<i>_<skill>.txt`** — the prettified, ANSI-stripped transcript of one skill invocation.
3. **Each skill's current `SKILL.md`** — for the chain runner's CWD-local `.claude/skills/<skill>/SKILL.md` (proprietary) and, if the proprietary skill has a `transferable:` field, the installed transferable at `~/.claude/skills/<transferable>/SKILL.md` (runtime read path). For a transferable, also read its base-repo source at `~/Dev/skill-set/skills/<category>/<transferable>/SKILL.md` — that is the file the supervisor edits.
4. **`~/.claude/state/manager-notes.md`** if it exists — combined manager observations and user feedback, prepended newest-first by the manager skill, with source-tagged headings. Three entry kinds, interleaved by UTC:
   - `## <utc-iso> user feedback (chat <id>)` — direct user-to-supervisor messaging, routed verbatim by the manager (periodic-mode drain or chain-runner pre-iter drain) from the Telegram `/feedback <message>` command. Treat as **authoritative steering** — the user's exact words. Feedback can direct concrete writes ("modify skill X to do Y", "add SPEC item Z to phase N", "append TODO Next-up item W"), and those directives are valid motivating citations for §3's change-intent table (the citation column reads `manager-notes.md:<line>` rather than a transcript line).
   - `## <utc-iso> manager-translated user feedback (chat <id>)` — written ONLY by the manager's on-demand `--process-feedback` mode (outcome (c) "soft steering") when the user's `/feedback` was shape-ish rather than a discrete work item. Body is a 2-4 sentence reasoning paragraph naming what the user said + which objective(s) it bears on + what the manager recommends to the supervisor. Treat as **authoritative steering with manager-supplied interpretation**: the user's intent is on the record and the manager's recommendation is the actionable form. Use the recommendation as the change-intent driver, not the user's paraphrased sentence — the manager has already done that translation. If the manager's recommendation conflicts with what the supervisor's run-log evidence actually shows, write the conflict in `## Notes for the manager` rather than overriding silently; the user can re-issue clearer feedback.
   - `## <utc-iso> manager observation` — patterns the manager derived from observing run logs. Treat as **soft steering**.
   - `## <utc-iso> supervisor observation (stuck-item)` — written by THIS skill's §3.6.2 stuck-item mitigation (the one case where the supervisor prepends to this file; see write-path (g)). Informational digest hint for the manager; the durable record is the paired `docs/HUMAN.md ## High` entry. Treat as **soft steering** when read on a later run.

   Apply the most recent entry of each kind that bears on this run; older entries that have already been actioned in a prior cycle stay in the file as audit history (the manager's ~3KB cap eventually trims them). Anti-fork rules still bind: an entry of any kind (user-feedback, manager-translated, or manager-observation) that asks you to skip sanitize on a transferable write, commit code, or deploy is REFUSED — reply by writing the refusal in `## Notes for the manager` rather than acting on it. The on-demand manager already refuses anti-fork-violating user feedback at routing time per `sst-manager` §On-demand feedback routing outcome (d), so a manager-translated entry that violates anti-fork rules indicates a manager misroute; flag it explicitly in `## Notes for the manager` so the next manager run can correct.

   **Conflict-resolution table:**

   | Source                         | Authority class | Beats |
   | :---                           | :---            | :---  |
   | `user feedback (chat <id>)` (verbatim) | authoritative   | manager-translated; manager observation |
   | `manager-translated user feedback (chat <id>)` | authoritative-with-interpretation | manager observation |
   | `manager observation`          | soft            | (nothing; soft steering only) |

   When a verbatim user-feedback entry and a manager-translated entry exist for related concerns, prefer the verbatim entry's wording where it's specific; the manager-translated entry's recommendation is fallback when the verbatim entry is shape-ish or absent.

   Earlier framework versions split these entries into `manager-guidance.md` (manager observations) + `manager-feedback.md` (user feedback). If those files still exist on this host, the next manager invocation merges them into `manager-notes.md` and archives them; until then, treat their continued presence as a transition state and read both as additional inputs with the same source-tagging semantics.
5. **`docs/SPEC.md`, `docs/TODO.md`, `docs/FUTURE-WORK.md`, and `docs/HUMAN.md`** (all if present) — for context on what the chain was working toward, what is intentionally parked, and what human-only actions are currently blocking the cycle.

**Spec sub-item IDs.** Every `- [ ]` item in `docs/SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 3.1 [hard] **description**`). IDs are assigned once and never renumbered — gaps from closed or removed items are valid. When writing `## Next up` follow-ups in `docs/TODO.md`, prefer citing the SPEC item by its ID (e.g. `reason: spec 3.1`) over "Phase 3 sub-item 1" for durability across renames.

## Process

### 0.5. Fast-path on clean (skip §1-7 when all signals say clean)

When all four signals below say "clean," skip the deep walk through §1-7 and write a one-line verdict instead. This saves the analysis cost on cycles that produce zero findings (commonly about half of all runs once a chain is mature, since "the skills behaved correctly" is the default state of a healthy framework).

Eligibility — all five conditions must hold:

1. **No prior escalation flag.** Locate the immediately-preceding `supervisor_verdict.md`: for multi-iter runs (`MANIFEST.iteration > 1`), look at `<base>/iter_<NN-1>/supervisor_verdict.md`; for single-iter runs or iter_01, collect all verdict files matching EITHER `<cwd>/.skill-runs/*/supervisor_verdict.md` (flat, single-iter shape) OR `<cwd>/.skill-runs/*/iter_*/supervisor_verdict.md` (nested, multi-iter shape), exclude any path under this run's directory, then pick the most recent by sorting on the run-directory name (timestamp-prefixed) with the `iter_NN` index as a tiebreaker for files in the same run directory. If the `## Outcome` line of the selected file contains `escalate`, abort the fast-path: the prior session asked for human attention and skipping the deep walk would lose that continuity. If no prior verdict exists (first run on this project), treat as no-escalation.

2. **All non-supervisor skill exit codes == 0.** Read `MANIFEST.skills[i].exit_code` for every record except the supervisor's own (the supervisor's own record is not yet present in the snapshot manifest per §Inputs step 1). Any non-zero exit code aborts the fast-path: a failure needs a finding.

3. **Transcript keyword scan returns clean.** Search every `<i>_<skill>.txt` **case-sensitively** for any of the following — using word-boundary anchoring (`\b`) on the generic terms to prevent false positives on compound identifiers and prose substrings. Case-sensitivity is load-bearing, not incidental: the generic terms below are matched as UPPERCASE tokens because real Python/pytest failure output emits `ERROR`, `FAILED`, `Traceback`, `Exception` in those exact casings, while benign lowercase prose ("error out", "tests fail as expected", "no regressions") is narration the dev/review skills routinely write on clean runs. A case-insensitive scan trips the gate on that narration and forces a deep-walk-on-clean every time — the documented ~30-50%-extra-turns waste this condition exists to avoid. Do NOT reintroduce a case-insensitive flag here. (The keyword scan runs only after condition #2 has confirmed all exit codes are 0, so a real unresolved test failure is already caught upstream; this scan is the secondary net for the narrow case of a skill that exited 0 yet left an uppercase failure token in its output.)
   - `\bERROR` (left boundary only) — catches `ERROR:`, `ERRORS`, standalone `ERROR`; excludes `tool_use_error` (where `error` follows `_`, a word character) and `RuntimeError`-style compound names.
   - `\bFAIL(ED)?\b` (both boundaries) — catches standalone `FAIL` and `FAILED`; excludes `failing`, `failure` as prose verbs/nouns.
   - `\bTraceback\b`, `\bException\b` — exact word matches; both appear standalone in Python error output. Excludes `\bException\b` when immediately preceded by `except ` (the Python source idiom `except Exception` / `except Exception as …`): a dev narrating exception-handling code it wrote or fixed is not a failure signal, and a genuinely uncaught exception still trips `\bTraceback\b` or a colon-suffixed `Exception:` (no `except ` prefix) on the same output — so the exclusion costs no real-failure sensitivity, mirroring the `tool_use_error` / `failing` exclusions above.
   - `[blocker]`, `[escalate]` — explicit skill-emitted escalation tags; brackets are non-word chars so no anchoring is needed.
   - `Found \d+ items:` — matches `sst-dev-review`'s §6 "With findings" report line (`Found <N> items: <B> blocker, <S> should-fix`); the review emits this format only when N>0, so any match means findings were filed and a `clean (fast-path)` verdict would be false. Case-sensitive; no word-boundary anchoring needed — the sequence is specific enough to the review §6 report template that it will not appear in non-review output on a clean run.
   - `Review follow-ups` — matches the same review §6 "With findings" report body (`Appended a "Review follow-ups" block under ...`), which appears only when the review committed findings to the spec. Case-sensitive; no anchoring needed.

   Plus one line-leading sentinel that does NOT abort but flags the outcome label differently:
   - `^\s*\W*\[no-work\]` — empty-queue bail; the dev skill ran but shipped no commit, so there is nothing to review at all. Outcome label becomes `clean (no-work bail)` instead of `clean (fast-path)`. The `\W*` after the leading-whitespace anchor tolerates wrapping markdown formatting the dev emits around the marker (a code-span backtick, `**bold**`, a blockquote `>`): the marker still leads its line's content, but a strict `^\s*\[no-work\]` misses a backtick-wrapped emission like `` `[no-work] queue empty ...` `` and silently mislabels a genuine no-work bail as `clean (fast-path)`. Do NOT re-tighten to `^\s*\[no-work\]`: dev skills routinely render the marker in a code span (their own prose shows it backticked), so the strict anchor reliably under-detects.

   Any non-`[no-work]` match aborts the fast-path. The keyword list is intentionally noisy: false positives just route to the deep walk, which is the safe direction.

4. **§3.5 batch-window refinement check returns "no refinement needed."** Run §3.5's trigger-evaluation step (3.5.1 only — the cheap trailing-window scan; do NOT yet edit any prose) to decide whether the dev skill's window prose needs adjusting. If the trailing-window thresholds are below the trigger AND stable-termination is engaged OR not yet eligible, return "no refinement needed" and proceed; the cost is one read of `MANIFEST.json` plus a transcript-grep over the trailing iters' `<i>_<dev-review>.txt` files (cheap). If the trigger fires, abort the fast-path: §3.5 will make a refinement edit in the deep walk, and that edit IS the iter's finding. The check is intentionally hoisted into the fast-path eligibility set so refinement keeps firing on otherwise-clean iters; without this condition, a long run of clean iters would let `[batch-sizing]` findings accumulate without ever crossing the deep walk.

5. **No un-triaged solo-tester findings.** If the chain ran a tester stage but NO dev-review stage (no `*-dev-review` transcript among the run dir's `<i>_<skill>.txt` files), read `tester-findings.json` from the run dir. Abort the fast-path if it is present AND its overall `verdict` is `red` or `degraded`, OR any check carries `status: fail` or `status: needs-change`: those findings have not been triaged into the spec by any review stage, and §5a (deep walk) must file the agent-actionable ones. A `verdict: green`/`skipped`, an absent findings file, or a chain that DID run a dev-review (which already consumed the findings per `sst-dev-review` §4, so re-filing would duplicate) all leave this condition satisfied. This is the tester-only-chain analogue of condition #3: in a solo-tester run no review skill emits the `Found N items:` line that condition #3 keys on, so the structured findings file is the signal instead.

When all five conditions hold, write the minimal verdict file and return:

```markdown
# Supervisor verdict — <run-dir-name>

**Chain:** <chain-name>  ·  **Commit:** <sha-after>  ·  **Generated:** <utc-iso>

## Outcome

clean (fast-path)
<!-- or `clean (no-work bail)` if §0.5.3's no-work sentinel matched -->

## Per-skill summary

(All skills exited 0; transcripts clean; prior verdict not escalated.)

## Edits written

(none)
```

The §8 exit gate is satisfied because the verdict file exists.

When any condition fails, fall through to §1 with no annotation in the eventual verdict. The fast-path is an optimization, not a user-facing contract surface.

**Anti-fork constraint.** Do not extend the keyword list with soft matches like `warning`, `caveat`, or `should`: those appear routinely in clean prose. Condition #5 (un-triaged solo-tester findings) is the spec'd fifth condition; do not add a sixth without spec'ing it first. The two review-findings entries above (`Found \d+ items:` and `Review follow-ups`) are the spec-authorized exception: they anchor strictly to the review skill's fixed §6 report template, not free prose — that is why they satisfy the anti-fork discipline even though they are new keyword additions (Phase 39.1). The bar is intentionally tuned to favor running the deep walk when uncertain: a missed-finding from an over-eager fast-path is a real defect, while a deep-walk-on-clean is just spent compute.

### 1. Walk every skill in MANIFEST.skills

For each skill record, ask three questions:

1. **Did it accomplish its job?** Cross-reference the transcript against the skill's stated process. Did it skip a step? Did a step fail and the skill silently moved on?
2. **Did it follow its own rules?** Most skills declare invariants ("one commit per cycle", "tests first", "no `--no-verify`"). Did the transcript respect them?
3. **Was its decision-making good?** When the skill made a choice (which item to pick, which test to write first, which deploy step to run), was the choice justified by the inputs available to it?

Mistakes uncovered are findings against the *skill*, not the *cycle*. If the skill's prose is ambiguous, that's a `should-fix` proposal targeting the prose. If the skill missed a step, that's a `blocker`.

**Runner-recorded contract flags.** Beyond the per-skill records, the iter MANIFEST may carry runner-set non-fatal contract-violation flags at the top level (e.g. `batch_pick_missing`, which the chain runner sets when the dev shipped a commit without the mandatory `[batch-pick]` block). Read these directly from the MANIFEST rather than re-deriving them from a transcript grep; they are deterministic. Dispose of them per §7's non-fatal-flag carve-out: a tracked note in `## Notes for the manager`, not an escalation.

### 1a. Skill-failure graceful resolution (Phase 55)

The chain runner no longer hard-aborts the run when a mid-chain skill exits non-zero (a turn-ceiling chop or a crash). Instead it FLAGS the failure on the iter MANIFEST as a top-level `skill_failure` object, SKIPS the remaining intermediate skills, and HANDS THE ITERATION TO YOU for graceful resolution before the loop continues. When `MANIFEST.skill_failure` is present, this is the iteration's primary finding and your job shifts from "review the cycle's commit" to "resolve the failure so the next iteration does not repeat it."

`skill_failure` shape: `{ "skill", "exit_code", "failure_kind", "num_turns" }`. `failure_kind` is `turn_limit_exhausted` (the harness chopped the agent at the hard turn ceiling -- the common case) or `error` (a crash / other non-zero exit). A `turn_limit_exhausted` on the dev means the picked item (or batch) was too large to complete within one agent's turn budget.

Resolve it within your existing authority (you edit docs + skills; you do NOT commit or mutate the watched project's code tree):

1. **Diagnose from the transcript.** Read the failed skill's `<i>_<skill>.txt` to identify the picked item / batch and how far it got. Confirm whether the failure was an oversized pick (genuinely too big), a batch that should have been one item, or a transient crash.
2. **Re-home the offending item so the next iteration does not re-fail on the identical pick.** Edit `docs/TODO.md` / `docs/SPEC.md`:
   - If it was a too-large `turn_limit_exhausted`: SPLIT the item into smaller sub-items in `## Next up`, OR (when it cannot be cleanly split) re-label it `[hard]` so it routes to the largest turn/effort budget and annotate it `[oversized: hit the turn ceiling on <utc>; needs splitting or a fresh full-budget attempt]`, and move it BELOW any independent ready work so the loop makes progress on something else first.
   - If it was a transient `error`: leave the item in place with a one-line `[retry-after-failure: <utc>]` note; a single clean retry next iter is expected.
3. **Surface, do NOT silently discard, any partial work.** A turn-ceiling chop usually leaves UNCOMMITTED partial edits in the working tree (the dev never reached its commit step). You must not commit or revert the watched project's tree (anti-fork). Note the dirty state in the verdict and in `## Notes for the manager` so the operator / next dev pre-flight handles it; if the partial edits would block the next dev's clean-tree pre-flight, file a `docs/HUMAN.md` decision-request per §5b rather than touching the tree yourself.
4. **Record + escalate.** The verdict `## Outcome` line leads with `escalate` when the failure is unresolved-by-you or recurring (the runner's consecutive-failure backstop will abort the loop on the 2nd consecutive flagged failure; a single resolved failure need not escalate but is always recorded). Add a `## Skill failure` block to the verdict naming the skill, `failure_kind`, the picked item, and the re-homing edit you made. The runner already sends a per-iteration Telegram `SKILL FAILURE` line; your escalation rides the normal verdict-driven path.

This section is the "graceful resolution" the runner hands off to; without it the flag would be recorded but unactioned and the next iteration would re-pick the same too-big item and re-fail.

### 2. Severity bar

Two severities. **No third tier.**

- **blocker** — the skill failed its job, broke an invariant, or has prose that will reliably mislead the next invocation into the same failure.
- **should-fix** — the skill's prose has a real gap that will surface again under different inputs, or it's missing a guard the run revealed it needs.

Skip nitpicks (style, wording, "could be clearer", "what if"). If after honest examination you have zero findings at this bar, that's a clean result — report it and stop.

### 3. Edit the skill directly

**Before editing ANY content, build the change-intent table.** This is the anti-scope-creep hard gate. For the target skill, list every line-level change you intend to make, one row per change, and map each to the specific transcript line(s) that motivate it:

```
| # | kind (add/delete/rewrite) | section / anchor in the skill | motivating citation |
| 1 | rewrite                   | §0.2 "clean git state" bullet | 01_<skill>.txt:L123 (ran `git status` with .claude/skills/ dirty, correctly proceeded but prose says "stop") |
| 2 | add                       | §Hard rules, last bullet      | 01_<skill>.txt:L298 (chained `git stash && checkout HEAD~1`, clobbered tree, ran `git fsck --lost-found`) |
```

**If you can't fill in the "motivating citation" column for a row, drop that row.** No exceptions for "while I was in here I noticed," "this would also be nice," "for consistency," or "future-proofing." Those are speculative improvements and belong to a future cycle where something actually goes wrong. The findings you articulated in §1–2 define the scope; the change-intent table MUST be a strict subset of motivations that appear in the transcript, not a superset.

**Count check.** If your change-intent table has more rows than the findings you enumerated in §1, stop and reconcile: either (a) you elided a finding in §1 that should have been listed separately — add it, or (b) one of the table rows is scope creep — drop it. Exactly one of those is true. An edit that makes 3 changes from 2 findings is the failure mode the framework is trying to prevent.

Once the change-intent table passes both gates (every row cited, row-count ≤ finding-count), edit the canonical `SKILL.md` directly. Bump `version:` per SemVer in the same edit: patch for prose clarification, minor for added behavior, major for changed contract.

**Where each skill's canonical source lives:**

- **Transferable skill** — the base-repo source at `~/Dev/skill-set/skills/<category>/<transferable-name>/SKILL.md`. This is the open-source master copy; editing it is gated on §4 sanitization (a `must-fix` finding ABORTS the edit). After a sanitize-clean edit, the supervisor commits and pushes it from the base repo (see §3a). The runtime copy under `~/.claude/skills/<transferable-name>/SKILL.md` is refreshed from the base repo by `bin/install-skills.sh`; the supervisor does NOT hand-edit the runtime copy.
- **Proprietary skill** — `<cwd>/.claude/skills/<skill-name>/SKILL.md`, edited in place. This is the gitignored runtime copy and the canonical home for proprietary skills; no commit is involved (the directory is project-local runtime state).

**Use the `Edit` / `Write` tools directly.** Chain runs spawn with `--permission-mode bypassPermissions`, which has an explicit carve-out for `.claude/skills/`, `.claude/commands`, and `.claude/agents`, so writes there do not prompt; the base-repo path (`~/Dev/skill-set/skills/`) is an ordinary repo path that never prompted. Edit the file, confirm the change, then (for transferables) proceed to §3a commit-and-push.

A skill edited this cycle is recorded in the verdict's "Edits written" block (§6) with its change-intent table. If this cycle has no finding for a skill, leave it untouched.

### 3a. Commit + push a transferable edit

A transferable `SKILL.md` edit is only complete once it is committed and pushed from the base repo, so the open-source master and every consuming clone pick it up. After a sanitize-clean edit (§4 returned `must-fix: 0`):

```bash
git -C ~/Dev/skill-set add skills/<category>/<transferable-name>/SKILL.md
git -C ~/Dev/skill-set commit -m "Supervisor: <skill> v<old>→<new> — <one-line finding summary>"
git -C ~/Dev/skill-set push
```

This is the supervisor's ONLY git write surface, and it is scoped to the base repo's `skills/` tree — never the consuming project's repo (the dev cycle owns that), never a proprietary `.claude/skills/` path (gitignored), never a deploy. If the push fails (e.g. no network, non-fast-forward), record the local commit SHA in the verdict and note the push failure in `## Notes for the manager`; do NOT force-push and do NOT leave the edit uncommitted. Proprietary edits involve no git step at all.

### 3b. Reconcile proprietary wrappers after a base bump (sst → ssp sync)

A base transferable `sst-X` is wrapped by proprietary `ssp-*` skills that declare `transferable: sst-X` and pin the base version they were last reconciled against in a `base-version:` frontmatter key. When you bump `sst-X` (here in §3, or in §3.5.3's refinement loop), those wrappers may now reference superseded base behavior. Close that gap as part of the same edit so the upgrade is not left half-applied:

1. **The wrapper you already edit.** Whenever you edit a proprietary mirror for the skill you bumped (§3 / §3.5.3 always pair a transferable edit with its proprietary mirror), set that mirror's `base-version:` to the NEW base version in the same edit — it is being reconciled right now. If the mirror has no `base-version:` key yet, add one.
2. **Other wrappers of the same base.** Run `bin/check-ssp-sync.py` (it lists every installed wrapper whose `base-version:` trails the current base `sst-X`, is unpinned, or points at an unknown base). For each stale wrapper:
   - **Reachable in this run's project** (`<cwd>/.claude/skills/<wrapper>/`): reconcile it in place — review its "inherits + adds + on conflict project wins" prose against the new base contract, adjust only what the bump actually changed (cite the base change, per §3's change-intent discipline), and bump its `base-version:`. Record it in the verdict's "Edits written" block as a proprietary edit.
   - **In another project you cannot reach from this run:** do not guess. Hand it to §5c — as an autonomous executor dispatch when the reconcile is mechanical (a pure `base-version:` bump because the base change does not touch any surface the wrapper overrides), or as a HUMAN.md decision-request when the reconcile needs project judgment.
3. **Record the sync outcome** in the verdict: which wrappers were reconciled, which were dispatched to the executor, which were filed for the human.

`check-ssp-sync.py` is read-only and cheap; run it after any base-skill bump even on an otherwise-clean §3.5 refinement, so a wrapper never silently rots behind its base.

### 3.5. Batch-window refinement loop (self-tune)

The dev skill's batching contract (`sst-dev-cycle` §1) sizes each cycle's batch against per-difficulty token-window targets (e.g. `[easy]` 100-200k, `[medium]` 200-300k, `[hard]` 400-500k input tokens). The dev's review counterpart (`sst-dev-review`) tags any cycle that falls outside the band with a `[batch-sizing]` finding. Those findings are honest empirical signal: the dev's chunk-shape estimates are wrong (drift from real cost-per-section), the band edges are mis-tuned, or a missing chunk-shape entry is causing the dev to systematically under- or over-pack the batch. Left alone, the windowing contract stays honor-system and the dev never learns from the misses. §3.5 closes the loop: the supervisor watches the trailing window of `[batch-sizing]` findings, and on accumulated signal authors a prose patch refining the dev's window-target text. Over many runs the dev's prose converges on observed reality.

This step runs UNCONDITIONALLY (regardless of whether this iter has other findings). On most iters it returns "no refinement needed" without writing anything; on the rare iter where the trailing-window threshold trips, it writes a single refinement patch to `sst-dev-cycle` (transferable) and the proprietary mirror named per the chain's proprietary skills. The §0.5 fast-path's condition #5 calls §3.5.1 eagerly so refinement still fires on otherwise-clean iters.

#### 3.5.1. Trigger evaluation (cheap; runs every iter)

Scan the trailing window of recent dev-review transcripts and iter MANIFESTs. Define the window:

- **Trailing iter set.** For multi-iter runs, walk backward from this iter through `<base>/iter_<NN-K>/` directories where K = 1, 2, ..., up to 20 (the `M=5 in trailing 20` window's outer bound). For single-iter runs, walk backward through the most recent `<cwd>/.skill-runs/*/` directories sorted by name (timestamp-prefixed); each single-iter run contributes one iter to the trailing set. Stop when fewer than 20 iters are available; partial windows are fine (the thresholds are minimums, not minimums-of-a-fixed-window).
- **`[batch-sizing]` finding extraction.** For each iter in the trailing set, locate the dev-review transcript (the file whose name matches the chain's review skill — e.g. `01_sst-dev-review.txt` or `01_<proprietary-review>.txt` per the chain definition). Grep for lines matching `\[batch-sizing\]` (any position on the line, case-sensitive — the tag is framework-canonical). The primary extraction target is the machine-parseable summary line emitted by `sst-dev-review §2.10` in the format `[batch-sizing] direction=<undersized|oversized> difficulty=<tier> actual=<n>k band=<lo>-<hi>k`; the any-position match also catches legacy prose-embedded mentions. Each match is one finding; capture the `direction` token from the `direction=<value>` key on the matched line, or from the first occurrence of `undersized` | `oversized` anywhere on the line when no key is present. Capture the iter's primary difficulty from the `difficulty=<tier>` key when present, else from `iter_manifest.difficulty`, else from the `[picked-difficulty: <tier>]` sentinel in the iter's dev transcript.
- **Discount false-`oversized` lines before counting them.** Apply, on the consuming side, the same sanity-check the emitter is already required to apply (`sst-dev-review` §2.10): an `actual=` reading that exceeds the difficulty's upper band edge by more than ~3× is a `cacheReadInputTokens`-inflation measurement error, not a genuine `oversized` signal (a real oversize tops out at ~2-3× the edge; an order-of-magnitude overshoot — an `[easy]` reading of 1500k+ against a 200k edge — is the recurring failure mode §2.10 names, and §2.10 explicitly warns it "pollutes the supervisor's §3.5 trailing-window aggregation with a false `oversized` line"). A review that violated §2.10's own sanity-check and summed cache-read tokens emits exactly this line, so do NOT take `direction=oversized` at face value. Before computing the triggers below: for each extracted line whose `direction=oversized` AND whose `actual=` exceeds the difficulty's upper edge by >3×, recompute the true value from that iter's MANIFEST as the dev skill's `inputTokens + cacheCreationInputTokens` (the `model_usage` of `skills[0]` only, summed across model entries, `cacheReadInputTokens` EXCLUDED) and re-admit the line under its corrected direction (it may become `undersized`, in-band → dropped, or a genuine ≤3× `oversized`); if that MANIFEST is unavailable, DROP the line from the window rather than count a value §2.10 defines as erroneous. Record each discounted/recomputed line in the §3.5.4 bookkeeping block so the suppression is auditable. The supervisor must never fire a window-refinement trigger on a measurement error — a false `oversized` line counted toward N or M is the exact pollution this guard exists to stop.

Compute the trigger conditions:

1. **Same-direction streak (default N=3):** `N` consecutive most-recent iters in the same difficulty band all carry a `[batch-sizing]` finding with the same `direction`. "Same difficulty band" matters because an `[easy]` undersizing and a `[hard]` undersizing are different prose problems (different chunk-shape estimates) and shouldn't be lumped. The streak counts iters, not findings — a single iter with two `[batch-sizing]` findings (rare) still counts as one streak step.
2. **Trailing-window total (default M=5):** total `[batch-sizing]` findings across the trailing 20 iters is ≥ M, regardless of difficulty band or direction. The total-trigger catches diffuse drift that doesn't form a streak (e.g. an `easy` undersize, a `medium` oversize, an `easy` undersize, a `hard` oversize, an `easy` undersize: no streak, but real dispersion that says the windowing is mis-tuned across the board).
3. **Stable-termination override (default K=10):** if the most recent K iters all carry zero `[batch-sizing]` findings AND a prior cycle's verdict file recorded a `## Batch-window refinement: monitoring (K=<n>)` block, the loop is in stable-termination mode. Suppress trigger evaluation entirely; return "no refinement needed (monitoring)". Re-engage the moment a `[batch-sizing]` finding lands again (the K-streak resets to zero on the next finding).

Defaults are the framework's published values; do NOT vary them per cycle (a refinement that lowers N to chase a single iter's noise is the exact failure mode the trigger thresholds defend against). They MAY be raised per project via a future SPEC change; until then, treat them as constants.

If neither trigger fires AND stable-termination is not in force, return "no refinement needed (below threshold)". If the trailing window has fewer iters than the smallest threshold permits a meaningful read (typically <3 iters), return "no refinement needed (insufficient trailing window)".

If a trigger fires, capture the trigger metadata for §3.5.2: which trigger (`streak` or `total`), which difficulty band (for streak triggers), the dominant direction (`undersized` | `oversized` | `mixed` for total triggers), the iter range cited, and the count of `[batch-sizing]` findings within that range.

#### 3.5.2. Refinement decision (only when trigger fires)

Decide WHAT prose adjustment to write. There are three legal refinement kinds; pick exactly one per cycle (do not bundle multiple refinements; the next cycle's trailing-window read will surface the next-needed one):

1. **Adjust a band edge** — when a streak trigger fires in a single difficulty band with a single direction. Move the edge by a single increment (~10-20% of the current edge value), in the direction the data implies: streak-undersized in `[medium]` → raise the lower edge of `[medium]` (the dev was under-packing because the floor was too low to motivate batching); streak-oversized in `[medium]` → lower the upper edge (the dev was over-packing because the ceiling permitted it). Do NOT cross-tier (an `[easy]`-band edge change must stay inside `[easy]`'s neighbors; never let `[easy]`-upper > `[medium]`-lower).
2. **Refine a chunk-shape estimate** — when the trigger metadata implicates a specific chunk shape mentioned in the dev's prose (e.g. "supervisor + sanitize sub-skill: ~50-80k", "transferable prose patch: ~30-60k"). Tighten or widen the estimate by a single increment based on the trailing iters' actual cost; cite the iter range as the empirical basis in the patch's commit-style prose.
3. **Add an empirical chunk-shape entry** — when the trailing iters consistently hit a chunk shape NOT already named in the dev's prose (e.g. a runner-changes iter consistently consumed ~80-120k with no estimate to compare against, biasing the dev's whole-cycle estimate). Append a single new entry to the dev's chunk-shape list, with the observed range bracketed conservatively.

Refinements MUST stay inside the windowing-prose surface. Patches MUST NOT:

- **Invent new section structure.** No new top-level sections, no new subsection numbering, no new contract surfaces. The refinement loop adjusts text inside the existing batching contract; it does not author the contract.
- **Change the difficulty enum.** `[easy] | [medium] | [hard]` is a SPEC-defined contract; adding `[trivial]` or `[xhard]` requires a SPEC change first.
- **Touch the per-skill model-floor / effort-floor table.** Routing floors are a separate concern (the routing spec phase); the refinement loop is windowing-only.
- **Bundle a refinement with an unrelated improvement.** "While I was in here I also tightened §2's tone" is the scope-creep failure mode §3 already forbids; §3.5 inherits the same gate. The change-intent table for the refinement patch (§3) MUST contain exactly one row, and that row's motivating citation is the trigger-metadata line range from §3.5.1.

If the trigger fires but the implicated change does not fit any of the three legal refinement kinds (e.g. the dev's prose has no chunk-shape entry that maps to the misbehaving cost shape, AND adding one would require renaming an existing entry), DO NOT make a hybrid edit. Record the refinement as `[deferred: shape-mismatch]` in the verdict (under "Edits written" with a one-line note explaining why the fix exceeds the legal refinement surface) and surface it in `## Notes for the manager`. The manager can route the case to the user as a SPEC change for a future cycle. The refinement loop is conservative on purpose: a too-broad edit that cascades into unrelated prose is worse than a deferred refinement that the user reviews directly.

#### 3.5.3. Apply the refinement edit (only when trigger fires AND refinement is in-surface)

Edit the dev `SKILL.md` directly with exactly the §3.5.2 prose change applied, bumping `version:` in the same edit. SemVer guidance: a band-edge or chunk-shape-estimate adjustment is patch-level (clarification of existing prose); an empirical chunk-shape entry add is minor-level (added behavior in the windowing prose). No major bumps from §3.5; a major bump would imply contract change, which §3.5 is forbidden from authoring per §3.5.2.

The dev skill is a `(transferable, proprietary)` pair. Edit BOTH per §3: the transferable `sst-dev-cycle` (base-repo source, sanitized per §4 then committed and pushed via §3a) AND its proprietary mirror named in the chain definition (in place under `<cwd>/.claude/skills/`). Sanitize the transferable per §4 first; a `must-fix` finding aborts the transferable edit and only the proprietary mirror receives the change (so the loop's learning is not lost; the proprietary stays ahead of the transferable until the next sanitization-clean cycle). Record both edits in the verdict's "Edits written" block per §6.

The proprietary mirror's body typically inherits the windowing prose from the transferable verbatim plus project-specific overrides (chunk-shape estimates that include the project's own per-skill costs, e.g. a custom deploy step that doesn't exist in the transferable). When the refinement is to a piece of prose that exists ONLY in the proprietary mirror (not in the transferable), skip the transferable edit entirely — record `transferable: (no change; refinement is in proprietary-specific prose only)` in the verdict.

#### 3.5.4. Stable-termination bookkeeping (always written, even when no refinement)

Whether or not a refinement was written this iter, append a single block to the verdict file under a `## Batch-window refinement` header:

```
## Batch-window refinement

- Trigger evaluation: <streak hit | total hit | below threshold | monitoring | insufficient window>
- Trailing window scanned: iters <range>; `[batch-sizing]` findings: <count>; same-direction streak: <length> @ <difficulty>; total in trailing 20: <count>
- Outcome: <edit applied: sst-dev-cycle v<old>→v<new> + <proprietary-mirror> v<old>→v<new> | no refinement needed | deferred: shape-mismatch | monitoring (K=<n>)>
```

The next iter's §3.5.1 reads this block from the trailing iters' verdicts to know whether stable-termination was previously in force. Continuity is the contract: a clean K-streak produces a single `monitoring (K=<n>)` block per iter (incrementing); a `[batch-sizing]` finding next iter resets the K counter to zero AND demotes the outcome to `below threshold` until the streak or total triggers fire again.

The `## Batch-window refinement` block is also written under the §0.5 fast-path verdict (after the `## Edits written` block). Fast-path verdicts that omit the block break stable-termination continuity for downstream iters; the §0.5 condition #4 eligibility check already runs §3.5.1, so the block's content is computed regardless.

#### 3.5.5. Anti-fork constraints summary

- Refinement patches stay inside the windowing-prose surface (band edges, chunk-shape estimates, empirical chunk-shape entries).
- Triggers (N, M, K) are framework constants; do not vary per cycle.
- One refinement kind per cycle; multiple in-surface needs queue across iters.
- Trailing-window scan is read-only against transcripts and verdicts; never re-runs analysis on prior iters.
- The refinement loop never authors the windowing contract itself (no new sections, no enum changes, no routing-floor touches).

### 3.6. Stuck-item detection + mitigation (self-monitor)

Phase 38's bounded-item discipline (38.1 writer-skill prose rule + 38.2 validator gate) stops most open-ended items at write time. §3.6 is the runtime backstop for the ones that slip through: an item that gets *picked repeatedly without ever closing* — the signature of an unbounded item, or one too large to finish in a cycle. Left undetected it wins every pick and the active phase never completes (the failure mode that motivated all of Phase 38). Like §3.5, this step runs UNCONDITIONALLY and reads only trailing-window transcripts + verdicts + `docs/SPEC.md`; it never re-analyzes prior iters.

#### 3.6.1. Detection (cheap; runs every iter)

Over the same trailing iter set defined in §3.5.1 (multi-iter: walk back through `<base>/iter_<NN-K>/` for K=1..20; single-iter: most recent `<cwd>/.skill-runs/*/` by name), extract each iter's **picked primary**: the leading `<phase>.<n>` SPEC ID from the iter's `[batch-pick]` block or `[picked-difficulty]` context in the dev transcript, plus the iter's `git_sha_after` from its MANIFEST. Normalize each pick to a **key**: the SPEC ID when present, else the lowercased first sentence of the picked-item description.

An item is **stuck** when BOTH hold across the trailing window:

1. The same normalized key was the picked primary in **≥3** of the trailing-window iters. (Threshold is a framework constant — same discipline as §3.5's N/M/K; do NOT vary it per cycle. It counts iters, not picks within one iter.)
2. That item's SPEC `- [ ]` never flipped to `- [x]` across those iters — read `docs/SPEC.md` for its current checkbox state; a stuck item is still `- [ ]` now. If the item closed (`[x]`) at any point in the window, it is NOT stuck (it was a legitimate multi-cycle item that completed).

#### 3.6.2. Mitigation (only on detection)

On a stuck item, record a `[stuck-item]` finding in the verdict (severity `should-fix` — it's a queue-hygiene gap, not a skill failure) and perform BOTH writes:

1. **`docs/HUMAN.md` `## High` entry** recommending the item be **decomposed into concrete enumerated sub-items** (each naming its target file/symbol, per the 38.1 bounded-item rule) **or removed**. Use §5b's schema (and its HUMAN.md admission test — a stuck item qualifies because choosing whether to rescope or drop the feature is a product/scope decision only the human can make); assign the next `H<phase>.<n>` for the stuck item's SPEC phase; `Blocks: none` (the cycle keeps shipping, it just never closes this one — not a cycle-stopper, so NOT `## Blocking`); `Verify:` omitted (resolution is a human judgment call). **Idempotent:** if an open `## High` entry already names the same stuck-item key, do NOT duplicate. After a fresh append, invoke `bash bin/notify-human-md.sh <cwd> docs/HUMAN.md` per §5b's write-then-notify rule.
2. **`~/.claude/state/manager-notes.md` observation** (write-path (g) below) prepended newest-first as a `## <utc-iso> supervisor observation (stuck-item)` block so the next manager digest surfaces it:

   ```
   ## <utc-iso> supervisor observation (stuck-item)
   `[stuck-item]` <key> picked in <count>/<window-size> trailing iters without
   its SPEC `[ ]` closing; recommended decompose-or-remove in docs/HUMAN.md
   H<phase>.<n>. Source: <run-dir-name>/supervisor_verdict.md.
   ```

   Idempotent against the most-recent prior supervisor observation for the same key: if the trailing window already produced one this cycle's analysis would duplicate, skip the prepend (the HUMAN.md entry is the durable record; manager-notes is a digest hint the ~3KB cap trims anyway).

`[stuck-item]` detection does NOT itself set the verdict to `escalate` (§7) on first sight. But if the immediately-preceding verdict already carried a `[stuck-item]` finding for the same key, that meets §7's "same blocker in 2+ consecutive runs" bar — set the outcome to `escalate` and note it for the manager.

#### 3.6.3. Anti-fork constraints summary

- Detection is read-only against transcripts, MANIFESTs, verdicts, and `docs/SPEC.md`; it never re-runs analysis on prior iters.
- The ≥3-iter threshold is a framework constant; do not vary it per cycle.
- Mitigation is APPEND-only to `docs/HUMAN.md` (never closes an entry — §5b anti-fork) and prepend-only to `manager-notes.md`; the supervisor never decomposes or removes the item itself (that's a human or future-dev-cycle action).
- One stuck-item finding per distinct key per cycle; the next iter's trailing-window read surfaces any others.

### 4. Sanitize before any transferable edit (hard gate)

Before editing the base-repo transferable source at `~/Dev/skill-set/skills/<category>/<transferable-name>/SKILL.md`, run the proposed body through `sst-sanitize-transferable`. This is a HARD GATE: a `must-fix` finding blocks the edit outright.

1. Write the proposed body to a temp file (e.g. `<run-dir>/transferable-draft-<skill>.md`).
2. Invoke `/sst-sanitize-transferable <draft-file> --project-context <path-to-proprietary-supervisor-SKILL.md>`.
3. Read the resulting `<draft-file>.findings.md`. Categorize:
   - **Any `must-fix` findings** → abort the transferable edit for this skill. The lesson stays as a proprietary-only edit, with a note in the verdict file: `(transferable edit blocked by sst-sanitize-transferable findings; see <draft>.findings.md)`.
   - **`should-fix` findings only** → either rewrite the draft to address them all, or keep the change proprietary-only.
   - **Zero findings or only `nit`** → safe to edit the base-repo transferable source directly (§3), then commit and push it (§3a). Append the `Sanitization checklist` footer from the findings file to the verdict entry for that skill, filled with per-category counts.

Sanitization is judgment-based; it's an LLM pass against `~/Dev/skill-set/templates/sanitization-guidance.md` plus the per-project banned-terms list. Do not try to grep — `sst-sanitize-transferable` exists precisely so the supervisor doesn't have to play regex games.

### 5. Update docs/TODO.md (rare)

If any finding implies the *project* (not the skill) needs follow-up work — for example, the run revealed an unhandled production state the project's spec doesn't cover — append a single line to `docs/TODO.md`'s `## Next up` section:

```
- [supervisor] <one-line> — supervisor verdict <run-dir-name>
```

Do not move existing entries; do not touch `## In flight` or `## Just shipped`.

**Bounded-item rule.** Any item appended to `## Next up` must be a *specific, completable action* — one whose done-state is unambiguous and whose SPEC `[ ]` can meaningfully flip to `[x]`. Forbidden: "continue improving X", "iterative Y polish", or any description of a recurring process with no natural end-state. Required instead: name the exact target file and symbol, or state a concrete acceptance criterion (e.g. "validator rejects vague bullets in unit tests for `bin/validate-frontmatter.py`"). If the needed work resists being named as a finite deliverable, file a `docs/FUTURE-WORK.md` entry instead.

**Route acceptance findings to FUTURE-WORK.md instead (optional).** When a finding implies work that cannot be autonomously verified by a future dev cycle — acceptance tests requiring a real chain-driver round-trip, human-verified smoke tests, production observation — the supervisor MAY append the item to `docs/FUTURE-WORK.md` (under `## Manual / human verification` or an appropriate sub-section) instead of `## Next up`. Items in FUTURE-WORK.md are intentionally parked; a human flips them back to `## Next up` when ready. Use `## Next up` when the dev cycle can execute the work autonomously without human-in-the-loop verification.

### 5a. Solo-tester findings triage (when no dev-review stage ran)

In a full chain the dev-review consumes the tester's `tester-findings.json` and files each runtime finding to the spec + `## Next up` (`sst-dev-review` §4: `status: fail` -> `[blocker]`, `status: needs-change` -> `[should-fix]`). A **solo-tester chain** (a tester run with an auto-supervisor but NO review stage) has no skill in the loop to do that, so without this step the tester's findings would reach only the verdict's `## Notes for the manager` -- bouncing agent-actionable work to a human. Close that gap here.

Trigger: the run dir has a `tester-findings.json` AND no `*-dev-review` transcript is present (confirm by listing the run dir's `<i>_<skill>.txt` files). When it fires, the supervisor itself applies the `sst-dev-review` §4 status->severity mapping:

- a check with `status: fail` -> a `[blocker]`-class follow-up;
- a check with `status: needs-change` -> a `[should-fix]`-class follow-up;
- an overall `verdict: degraded` (tester tried but could not fully exercise the surface) -> a `[should-fix]` noting the incomplete runtime coverage;
- `verdict: green` / `skipped`, or an absent findings file -> nothing to file.

File each as a `## Next up` line in `docs/TODO.md` using §5's format and **bounded-item rule** (and mirror it to a `## Review follow-ups` entry in `docs/SPEC.md` when the project keeps that section), citing the tester check's recommendation and evidence path. **Dedup first:** read `docs/SPEC.md` / `docs/TODO.md` before filing -- if a finding already maps to an existing SPEC `[ ]` item, cite that ID in the verdict instead of adding a duplicate line. A finding whose fix needs a human (an auth/secret/credential, or a genuine product/UX decision the tester only flagged, not an agent-fixable bug) routes to `docs/HUMAN.md` per §5b, not `## Next up`. Record what was filed (and what was deduped) under `## Edits written`; only the residual that genuinely needs a human goes in `## Notes for the manager`. The principle: nothing an autonomous dev cycle can act on is left only in the manager notes.

### 5b. Route to HUMAN.md for human-only blockers (when applicable)

**HUMAN.md admission test (hard gate — applies to EVERY `docs/HUMAN.md` append, here and in §5c and §3.6.2).** Before appending any entry, confirm the resolving action is one ONLY THE HUMAN can perform or decide: it needs an out-of-band credential the cycle does not hold (a secret, a third-party-UI or cloud-IAM grant, a lapsed production-access login), a legal or contractual signature, OR a genuine product/scope decision that is the human's alone (e.g. whether a feature stays or is dropped). If ANY autonomous actor in the framework — this cycle's dev skill, a future dev cycle, or `sst-executor` (reversible/local framework maintenance) — could perform or decide it, it is NOT a HUMAN.md item. Route it instead to: `docs/TODO.md > ## Next up` (agent-actionable work), `docs/FUTURE-WORK.md` (parked work or acceptance tests the cycle cannot self-verify), the executor queue per §5c Route 1 (reversible framework upkeep), or `## Notes for the manager` (a digest hint that requires no human action). **When uncertain whether an action is human-only, it is NOT** — HUMAN.md is reserved for the vital actions only the human can take, and a borderline entry the cycle could have handled itself is exactly the clutter this gate exists to keep out.

When a finding's resolution requires an action the cycle cannot perform autonomously — writing a secret outside the repo, granting access in a third-party UI (e.g. GitHub Actions secrets, cloud IAM), signing a legal agreement, or any action that inherently requires a human with credentials the cycle does not have — append to `docs/HUMAN.md` instead of `docs/TODO.md` or `docs/FUTURE-WORK.md`.

Placement: default to `## Blocking` for items that actively stop a SPEC item from proceeding; use `## High` for non-blocking prerequisites the cycle would benefit from soon. Format each entry per the schema in `docs/HUMAN.md`:

```
- [ ] H<phase>.<n> [<difficulty>] **<short title>**
  <one-paragraph body: what the human must do, where, why the cycle can't do it.>
  Blocks: <comma-separated SPEC IDs>, or "none".
  Verify: <optional one-line shell check; pass = supervisor/manager auto-moves to ## Done>.
  Filed by: sst-supervisor at <utc-iso>.
  Source: <run-dir-name>/supervisor_verdict.md.
```

Assign the next unused `H<phase>.<n>` ID where `<phase>` matches the SPEC phase the action is gating. IDs are stable once assigned; gaps are valid.

Note: a skill-prose improvement is NOT a HUMAN.md item. The supervisor edits skill source directly (§3) and, for transferables, commits and pushes it (§3a) — there is no human promotion step. `docs/HUMAN.md` is only for actions that genuinely require a human with out-of-band credentials.

**Anti-fork constraint.** The supervisor MUST NOT flip `[ ]` → `[x]` on HUMAN.md entries. Closure is human-initiated (or auto-verified by the manager skill). Write APPEND-only; never remove or modify an existing open entry.

**Write-paths addendum.** The supervisor's write-paths (§Output rules) now include: **(f) `docs/HUMAN.md`** — APPEND only, under `## Blocking` or `## High`. Never close an existing entry; never modify prose outside the appended block.

**Write-then-notify.** Immediately after appending to `docs/HUMAN.md`, invoke the notification helper via Bash:

```bash
bash bin/notify-human-md.sh <cwd> docs/HUMAN.md
```

The helper diffs the file against the last-notified snapshot, composes a brief delta message (`[<project>] HUMAN.md: <delta summary>`), and forwards it to `bin/notify-telegram.sh`. Missing or unconfigured Telegram env → graceful skip (exit 0); a notification failure must never abort the supervisor. The anti-fork carve-out in §Output rules permits this outbound call.

### 5b.1. Phase-completion branch-setup handoff (re-homed from sst-dev-cycle §7a in Phase 54)

In branch-per-phase projects the dev cycle bails when its active phase is complete, emitting on stdout exactly:

```
[no-work] phase <N> complete on <branch>; awaiting human branch setup for phase <N+1>
```

This is a **human-only** handoff (only the human can merge the completed branch and open the next phase's `feature/<name>` branch), so it passes §5b's admission test. Phase 54 moved the HUMAN.md write out of the dev skill into this oversight layer: the dev now only prints the sentinel and exits. When this skill's transcript scan finds that `[no-work] phase <N> complete` line, the supervisor files the branch-setup `## Blocking` entry in `docs/HUMAN.md` using §5b's schema (this phase-completion HUMAN.md write is what was re-homed from the dev's old §7a):

- Assign `H<N>.<n>` for the completed phase `<N>` (next unused `<n>`).
- Body: state that phase `<N>` is complete on `<branch>` and the human must merge it and open the phase `<N+1>` branch before the cycle can proceed.
- `Blocks:` the first open SPEC ID of phase `<N+1>` (or "none" if unknown).
- **Idempotent:** if an open `## Blocking` entry already names the same phase-completion key (same `<N>` / branch), do NOT duplicate.

After the append, run the §5b write-then-notify helper (`bash bin/notify-human-md.sh <cwd> docs/HUMAN.md`). This keeps every HUMAN.md write, including the phase-completion handoff, in the oversight layer (supervisor + manager) only, per the Phase 54 invariant.

### 5c. Autonomous follow-up dispatch + human decision-requests

§5/§5b park follow-up *work* for later (TODO, FUTURE-WORK, HUMAN.md). This step is for follow-ups the supervisor wants *acted on now* — chiefly the operational upkeep that falls out of a base-skill bump (sync the runtime copies, reconcile a drifted wrapper) or a discovered maintenance need. The framework's goal is to minimize human involvement: route as much of this as is safe to the executor, and only ask the human when a real decision is needed.

**Classify each actionable follow-up into exactly one route. Default to the human route when uncertain.**

**Route 1 — autonomous (dispatch to `sst-executor`).** Use when the follow-up is reversible/local framework maintenance with an unambiguous done-state: refresh the runtime skill copies (`bin/install-skills.sh`), a mechanical `base-version:` bump on a wrapper whose base change touches nothing it overrides, run a diagnostic. Collect ALL such follow-ups from this session into ONE request file and spawn the executor ONCE:

```bash
# Write the batch (one file per supervisor session) to the executor queue dir
# (NOT the manager's bot queue — the periodic manager must never see it):
#   ~/.claude/state/executor-queue/<utc>_supervisor-request.json
# Shape: { command:"supervisor-request", token, project, project_path, from:"sst-supervisor",
#          run_dir, received_at, requests:[ {id, action, rationale, tier_hint, detail}, ... ] }
claude --print --permission-mode bypassPermissions \
  "/sst-executor --process-supervisor-request <queue-file>"
```

The executor classifies each request into its own authority tiers, runs tier-1 work, asks the human about any tier-2 (outward/irreversible) step it discovers, refuses tier-3, and audits every action over Telegram (`sst-executor` §Authority envelope + §Mandatory audit). **At most ONE executor spawn per supervisor session** — batch, never loop. The supervisor does not wait on or parse the executor's result; the executor owns its own audit and exit. Record "dispatched N requests to the executor (<queue-file>)" in the verdict.

If the `claude` binary is unavailable or the spawn fails, do NOT drop the work: fall back to Route 2 (file each intended request as a HUMAN.md decision-request) so nothing is lost. The dispatch is an optimization over the human route, not a replacement for its durability.

**Route 2 — human decision-request (file to `docs/HUMAN.md` + notify).** Use when the follow-up needs a human judgment, an authorization, or an out-of-band credential — i.e. anything not clearly Route 1. File it per §5b's schema, and make it *answerable* by adding an `Asks:` line naming the exact Telegram reply that resolves it:

```
  Asks: <the decision/authorization needed, in one line>.
  Reply: /approve <token> <id>        (to authorize a prepared action)
     or  /feedback <token> <answer>   (to answer an open question)
```

The `Reply:` line tells the human exactly how to close the loop from their phone. `/approve <token> <id>` and `/exec <token> <action>` are routed by the bot to `sst-executor`; `/feedback` is routed to the manager as today. After the append, the existing §5b write-then-notify fires the Telegram alert. (A plain blocker the human resolves out-of-band — provisioning a secret, a cloud-IAM grant — needs no `Asks:`/`Reply:`; those lines are only for follow-ups the human closes via a bot reply.)

**Anti-fork.** Route 1 may only dispatch actions inside the executor's tier-1/tier-2 envelope; never instruct the executor to deploy, to touch a watched project's git, to push `main`, or to bypass sanitize — those are tier-3 and the executor refuses them anyway, but the supervisor must not author them into a request. The executor's hard perimeters are the same ones that bind the supervisor.

### 6. Write the verdict file

`<run-dir>/supervisor_verdict.md`:

```markdown
# Supervisor verdict — <run-dir-name>

**Chain:** <chain-name>  ·  **Commit:** <sha-after>  ·  **Generated:** <utc-iso>

## Outcome

clean | <N> edits | escalate

## Per-skill summary

- `<skill-name>` (`<sha-of-SKILL.md-before>`): <clean | <N> findings; transferable edit committed | proprietary edit in place | transferable blocked by sanitization>
- ...

## Edits written

For each edit, record the change-intent table from §3 verbatim. This is the auditable evidence that no row was added without a transcript-line citation. Readers (the manager skill, the user, the next supervisor run) can confirm at a glance that changes = findings.

```
- transferable: <abs-path-to-base-repo-SKILL.md> — v<old>→v<new>, <severity>, one-line summary.
  Committed + pushed: <base-repo commit SHA> (or "commit <SHA>; push failed: <reason>").
  Change-intent table:
    1. <kind> @ <section> — <motivating citation: <i>_<skill>.txt:<line>>
    2. <kind> @ <section> — <motivating citation: <i>_<skill>.txt:<line>>
- proprietary: <abs-path-to-.claude/skills/SKILL.md> — v<old>→v<new>, <severity>, one-line summary.
  Change-intent table: (same shape)
- (or: none)
```

A row without a citation in this section is a bug — re-verify before signing off. The manager skill treats a missing-citation verdict as an escalation signal on its next poll.

## Sanitization footers

(Appended verbatim from `<draft>.findings.md` for each transferable edit, per §4. Omit entirely when no transferable edits happened.)

## Notes for the manager

<Optional. 1-3 lines that the manager skill should weight when composing its
next status digest. Examples: "Two consecutive cycles needed the same
follow-up; the proprietary skill's pre-flight is consistently missing X" or
"Cycle drifted off objective Y; flagging for objective realignment.">
```

### 7. Escalate when warranted

Set the verdict outcome to `escalate` (and write a note to the manager) when:

- The same blocker has surfaced in 2+ consecutive runs (the prior verdict_*.md files in adjacent run dirs will tell you).
- The skill's commit landed on the wrong branch, on top of someone else's work, or rewrote history.
- A `sst-sanitize-transferable` rejection happened (so the user knows the system caught something potentially sensitive, even though the transferable edit was blocked and stayed proprietary-only).

**Carve-out: runner-recorded non-fatal contract flags do NOT escalate.** A non-fatal contract-violation flag the chain runner records on the iter MANIFEST (e.g. `batch_pick_missing`, set when the dev shipped a commit without the mandatory `[batch-pick]` block) is a TRACKED note in `## Notes for the manager`, NOT an escalation trigger, even when it recurs across consecutive runs (it does not count toward the "2+ consecutive runs" bar above). The runner already makes the violation deterministic and visible, so the silent-degradation reason to escalate is gone; the residual is a model-compliance gap no prose edit can durably close, and re-escalating every run would only halt the autonomous loop without advancing a fix. Escalate ONLY if THIS run shows the missing telemetry caused concrete downstream harm (e.g. a multi-item batch the review could consequently neither size nor cover): that is a distinct, evidenced blocker, not the bare flag.

Escalation does NOT change what the supervisor writes; it just sets a flag the manager will pick up and surface to the user.

**`## Outcome` line format for escalate verdicts.** The chain runner detects an escalate verdict by checking whether the first non-empty line under `## Outcome` BEGINS with the word `escalate`. A line like `2 findings, escalating` (where `escalating` appears at the end, not the start) or `recurring blocker (escalation warranted)` (non-leading) will NOT halt the loop — a silent under-halt. Always write `escalate`, `escalate: <reason>`, or `escalate (<N> edits)` as the outcome text. A description sentence that merely mentions escalation elsewhere is not recognized by the runner.

### 8. Exit gate — completion invariant before returning

This is the LAST step of every supervisor session. Do not return until both invariants hold; the chain runner has no way to detect a partial-completion exit, so the discipline is enforced here.

1. **Every edit is finished and recorded.** For each `SKILL.md` you edited this session, confirm one of:
   - **Transferable**: the base-repo file was edited, sanitize returned `must-fix: 0`, AND a base-repo commit exists for it (§3a) — recorded in the verdict's "Edits written" block with the commit SHA (a failed push is acceptable but must be noted, per §3a); OR
   - **Proprietary**: the `<cwd>/.claude/skills/` file was edited in place AND recorded in the verdict's "Edits written" block; OR
   - The verdict file carries a `[deferred]` line naming the intended edit and the reason it was not applied (e.g. `sst-sanitize-transferable` returned `must-fix`, the change was rendered moot by a parallel finding).

2. **Verdict file exists.** `<run-dir>/supervisor_verdict.md` MUST be written before returning, even when the outcome is `clean`. A clean run produces a one-line verdict (no findings, no edits) so the manager skill and the user can confirm the prior session completed cleanly. A clean run with no verdict file is indistinguishable from a partial-completion failure.

If either invariant fails, do not return. Either finish the edit + commit (transferable) and the verdict write, or record a `[deferred]` line. The contract is simple: "edit intended → edit applied (and committed, for transferables) OR explicitly deferred in verdict"; nothing falls through the cracks.

`[deferred]` line format (extends the §6 "Edits written" section):

```
- [deferred]: <skill-name> — would have edited <transferable|proprietary> at <abs-path>; not applied because <reason>.
```

A transferable edit left uncommitted in the base repo is a contract violation: either commit + push it (§3a) or revert the base-repo working-tree change and record the edit as `[deferred]`. Never leave the base repo dirty on exit.

## Permissions contract — edit SKILL.md directly via Edit/Write

Chain runs spawn with `--permission-mode bypassPermissions`, which has an explicit carve-out for `.claude/skills`, `.claude/commands`, and `.claude/agents` (Claude Code routinely writes there), so Edit/Write to a proprietary `<cwd>/.claude/skills/<skill>/SKILL.md` does not prompt. The base-repo transferable source at `~/Dev/skill-set/skills/<category>/<skill>/SKILL.md` is an ordinary repo path that never prompted. So the supervisor edits both directly with the `Edit` / `Write` tools — there is no helper script and no intermediate file.

Manual supervisor runs outside the chain runner inherit the user's interactive permission mode; approve the `.claude/skills/` and base-repo writes when prompted. The git commit + push for a transferable edit (§3a) runs through the `Bash` tool against `~/Dev/skill-set/` only.

## Output rules

- **Write paths are limited to:** (a) the run-dir (verdict, sanitize drafts, findings files); (b) `<cwd>/.claude/skills/<skill>/SKILL.md` for proprietary edits (in place, including a wrapper's `base-version:` reconcile per §3b); (c) `~/Dev/skill-set/skills/<cat>/<skill>/SKILL.md` for transferable edits (base-repo source, committed + pushed per §3a); (d) `docs/TODO.md` under `## Next up` (rare); (e) `docs/HUMAN.md` — APPEND only, under `## Blocking` or `## High`, for human-only blocker findings and decision-requests that pass §5b's HUMAN.md admission test (see §5b, §5c); (f) `~/.claude/state/manager-notes.md` — PREPEND only, a `## <utc-iso> supervisor observation (stuck-item)` block, exclusively for §3.6.2's stuck-item digest hint; (g) `~/.claude/state/executor-queue/<utc>_supervisor-request.json` — the single executor-request batch file for §5c Route 1 (its own queue dir, never the manager's bot queue). Never elsewhere.
- **Git is scoped to base-repo transferable edits only.** The supervisor commits + pushes a transferable `SKILL.md` edit from `~/Dev/skill-set/` (§3a) and does nothing else with git: never commits the consuming project's repo (the dev cycle owns that), never touches a proprietary `.claude/skills/` path with git (gitignored), never force-pushes, never creates branches.
- **Never deploy.** No SSH, no service restarts, no curl against a live site. **Two narrow exceptions, neither a deploy:** (1) invoking `bin/notify-human-md.sh` (which curls the Telegram API) immediately after a `docs/HUMAN.md` write in §5b/§5c; (2) spawning `sst-executor` exactly once per session for a §5c Route-1 batch (`claude --print --permission-mode bypassPermissions "/sst-executor --process-supervisor-request <queue-file>"`). The executor delegation is bounded to one spawn, carries only tier-1/tier-2 framework-maintenance requests, and the executor enforces its own perimeters + audit; it is a hand-off, not a production mutation. Both exceptions run through the `Bash` tool; everything else with SSH/curl/restart remains forbidden.

## When invoked with no run-log dir argument

Default to the most recent `.skill-runs/<*>/` directory under the current working directory. If none exists, exit cleanly with a one-line message — there's nothing to review.
