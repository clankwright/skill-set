---
name: sst-dev-review
description: Post-cycle second-pass review of the last `/sst-dev-cycle` commit on any project. Reads what shipped (code + tests + spec + TODO + docs), evaluates it against the spec item it closed along several axes (spec parity, correctness, coverage, discoverability, production verification, security, style, performance), and appends concrete follow-up items to the project's spec AND the handoff TODO's "Next up" if critical, blocking, or medium-to-major gaps are found. If nothing substantive turns up, leaves both unchanged and reports "clean." Does NOT fix issues — only names them and schedules them as spec work for the next `/sst-dev-cycle`. Pair with `/sst-dev-cycle` (chained via `bin/skill-chain.py sst-dev-cycle sst-dev-review`).
user-invocable: true
version: 1.14.12
model-floor: opus
effort-floor: high
---

# Autonomous Dev-Cycle Review

One invocation = a critical second pass over the last shipped `/sst-dev-cycle` commit. This skill's only output is either (a) a concise `Review follow-ups` block appended to the project's spec as the next cycle's work, or (b) an explicit "clean" report. **Do not fix code here** — except for plainly wrong doc typos that fit in the same commit. Fixes run through `/sst-dev-cycle` on a later invocation.

## Operating principles

- **Be critical.** The author of the last cycle was you, and you are biased toward seeing it as complete. Deliberately hunt for what was glossed over: edge cases not tested, happy-path bias in prod verification, stale docs, missing constants, mocks that contradict the real architecture.
- **Cite, don't paraphrase.** Every finding names a file + line or function + symbol. "Looks wrong" with no reference is not a finding.
- **No silent rewrites.** If you see a bug, propose it as a spec follow-up line. Do not edit the bug out — even a trivial one — because that bypasses the TDD cycle. The only exception: plainly wrong docs (typo in a comment, stale test-count number) may be corrected in the same commit as the review.
- **Clean is a valid outcome.** If the cycle was tight, say so. Don't manufacture findings to justify the invocation.
- **One commit or none.** Either append follow-ups and commit once (scope tag `Review:`), or commit nothing.

## Severity bar — critical / blocking / medium-to-major only

Two severities. **No third tier.**

- **blocker** — breaks a user flow, opens a security vulnerability, creates a clear economic or data-integrity bug, or leaves the system in a state where the next release can't ship safely.
- **should-fix** — bug or gap of medium-to-major impact that isn't hurting yet but will: missing coverage on a paid/auth-critical path, a guard that's dead code, an input without a bound that becomes a DoS vector under load, a migration that wasn't run in prod, a discovery surface (OpenAPI / manifest / README) that lies about the endpoint.

**Do NOT flag nitpicky, inconsequential, or trivial items.** Style nits, cosmetic doc polish, minor duplication, off-by-one in log messages, comment wording, magic numbers in test-only code, personal-taste refactors — skip them all. If you're tempted to write "nice-to-have" / "bikeshed" / "could be clearer" / "would be nicer if," that's the signal to delete the finding, not file it. A shorter review with only real problems is the goal; padding with trivia dilutes signal and wastes the next `/sst-dev-cycle` cycle.

Before filing any finding, ask: *would this actually hurt a user, cause a real bug, create a real security/economic risk, or mislead the next engineer into a mistake?* If the honest answer is no, drop it.

## Handoff docs

This skill reads `docs/SPEC.md`, `docs/TODO.md`, and `docs/FUTURE-WORK.md` (all if present) end-to-end on open. It may write to `docs/SPEC.md`, `docs/TODO.md`, and `docs/FUTURE-WORK.md` on close (under §4). Severity bar and process are unchanged from the rest of this skill; the only addition is that every blocker/should-fix you file in the spec also gets mirrored as a one-line entry in `TODO.md`'s `## Next up` so the next `/sst-dev-cycle` picks it up without re-scanning the spec. Both files commit together in §5 if anything was added.

**Spec sub-item IDs.** Every `- [ ]` item in `docs/SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 3.1 [hard] **description**`). IDs are assigned once and never renumbered — gaps from closed/removed items are valid. When filing follow-ups to `## Next up` in §4, prefer citing the SPEC item by its ID (e.g. `reason: spec 3.1`) over "Phase 3 sub-item" for durability.

## 0. Pre-flight

1. Working directory is the project root (same repo as the commit you're reviewing). Activate any language environment the project uses.
2. **Recovery-first: orphaned-dev-cycle recovery (recover, THEN review).** As the FIRST action of this skill's turn — **before the review pass** (§1 onward) — detect and recover any dev cycle that exited without committing. A missed commit is healed at the top of this stage rather than left to abort the loop. This fires when the chain runner's Phase 36 guard detected an incomplete dev cycle and routed this skill to attempt recovery instead of aborting.

   **Recovery-first health predicate (Phase 43/43.3).** Recover the orphaned cycle ONLY when all five signals hold — an incomplete-but-*healthy* cycle, i.e. the dev "just missed" its own commit:
   - **dirty tree** — `git status --porcelain` is non-empty; AND
   - **In-flight line** — `docs/TODO.md`'s `## In flight` section carries a live `- [` bullet; AND
   - **HEAD unchanged** — HEAD did not advance during the dev skill's run (the runner routed here precisely because `sha_before == sha_after`); AND
   - **tests green** — the project's full test suite passes in the dirty tree; AND
   - **sanitize clean** — any staged transferable `SKILL.md` returns zero `must-fix` findings.

   When all five hold, commit the dev's work now (the recovery commit), then continue to the review pass. If any signal fails, do not recover — fall through to the §0.3 note-and-proceed pass. Steps:
   a. Run `git status --porcelain`. If empty (clean tree → no **dirty tree**), skip to step 3 (nothing to recover).
   b. Read `docs/TODO.md`'s `## In flight` section (strip HTML comments). If it contains no `- [` bullet (no **In-flight line**), skip to step 3 (dirty tree is unrelated noise — see step 3).
   c. **Both signals present (dirty tree + live In-flight line); HEAD unchanged is established by the runner's routing.** Recovery path — note the **sanitize clean** gate (sub-step 4) runs BEFORE staging + commit so it is never the step immediately before the commit (Phase 43/D2 seam fix):
      1. Run the project's full test suite (`pytest tests/ -q` or equivalent). If **any** test fails (**tests green** signal absent): print `[incomplete-cycle] tests failing in dirty tree; cannot auto-commit`, surface the failure detail to the user, and **exit**. Do NOT commit or push.
      2. Tests pass. Extract the scope + description from the In-flight line (format: `- [<skill> @ <utc>] <description>`).
      3. Inspect changed files: `git diff --name-only` and `git ls-files --others --exclude-standard`.
      4. **Sanitize gate for transferable edits (runs BEFORE staging — the seam fix).** From the changed-file list in step 3, check for any transferable skill path matching `skills/**/sst-*/SKILL.md`. If any match, invoke `/sst-sanitize-transferable` on each affected `SKILL.md` now — before the spec-flip, the TODO finalize, the staging, and the commit:
         ```
         /sst-sanitize-transferable <path-to-affected-SKILL.md>
         ```
         Read the resulting findings. If any `must-fix` finding is returned (**sanitize clean** signal absent): print `[incomplete-cycle] must-fix sanitize finding in recovery commit; cannot auto-commit — rewrite the banned token or confine the change to a proprietary skill`, surface the finding detail, and **abort** (do NOT commit or push). A must-fix finding means auto-committing would ship proprietary-leakage into a transferable skill — the same gate `sst-dev-cycle` §3/§5 enforces and that `sst-supervisor` and the project `CLAUDE.md` require. If no `skills/**/sst-*/SKILL.md` paths changed, or if the sanitize check returns zero must-fix findings, proceed to step 5. Running this gate here, not as the step immediately before the commit, mirrors `sst-dev-cycle` §3: the spec-flip + TODO finalize + staging + commit all still follow it, so its clean return is never mistaken for the end of recovery.
      5. If `docs/SPEC.md` has any `- [ ]` items covered by the In-flight scope that appear modified in the diff, flip them to `- [x]` now.
      6. Finalize `docs/TODO.md`: delete the In-flight bullet from step (b); prepend to `## Just shipped`: `- <description from In-flight line> — by sst-dev-cycle at <utc from In-flight timestamp>`.
      7. Stage all changed files by name: `git add <code-files> <test-files> docs/SPEC.md docs/TODO.md`. Never `git add -A`.
      8. Commit (this is the recovery's final action — no `/skill` sub-invocation sits between the sanitize gate in step 4 and this commit):
         ```bash
         git commit -m "$(cat <<'EOF'
         <Scope>: <description from the In-flight line>

         Auto-committed by sst-dev-review orphaned-cycle recovery (Phase 36):
         dev exited without staging. Full test suite green at recovery time.

         Test count: <old> → <new>.
         EOF
         )"
         ```
      9. `git push origin <branch>`.
   d. After a successful recovery commit, continue to step 3 (the review pass follows: recover, THEN review). The working tree may still carry supervisor-side `.claude/skills/*/` dirt — that is normal and handled by step 3.
3. Git state check: **note and proceed**. Run `git status --porcelain` and capture the output verbatim. The review runs against the just-shipped cycle commit (HEAD by default, or the cumulative surface when the cycle shipped >1 commit) regardless of working-tree dirt; the dirt is captured as a "Working-tree state at review start" note in the §6 report and (when §4 fires) in the §5 commit body, then ignored. Rationale: the project's supervisor (when the project runs `sst-supervisor` or a `<project>-supervisor` proprietary counterpart) routinely leaves direct-overwritten edits to peer SKILL.md files uncommitted in `<cwd>/.claude/skills/*/` as its contract; parallel agent sessions and the user's own concurrent edits can also legitimately touch project source while a review runs. Halting on either case wastes the cycle's commit and forces the user to babysit the working tree. Concrete rules:
   - Capture the porcelain output. If non-empty, surface it as the "Working-tree state at review start" note in the §6 report and (when §4 fires) include it in the §5 commit body. Surfacing what wasn't part of the just-shipped commit is the value-add; reviewer-side rather than dev-side because the dev cycle has already committed (and pushed) by the time the review starts.
   - Do NOT stash, checkout, or modify any of the dirty files. They are out-of-scope for the review.
   - The §5 stage-narrowly rule is the structural guard: stage only the spec file (plus `docs/TODO.md` if a Next-up entry was added, plus `docs/FUTURE-WORK.md` if §4 routed findings there), never `git add -A` or `git add .`. Working-tree dirt cannot accidentally ride into the review commit if §5 is followed.
   - One exception still halts: if a dirty file is the spec file itself, `docs/TODO.md`, or `docs/FUTURE-WORK.md` (the three files this skill writes to in §4), stop. Concurrent writers on the same files is the one collision the note-and-proceed pattern doesn't survive; surface to the user and exit.
4. **Tester findings (back-compat: review proceeds unchanged when files are absent).** Locate the chain run-log dir (most recent `.skill-runs/<*>/` under the current working directory, or the path the chain runner printed as `[log-dir] <path>`). **In a looped run, read the findings from THIS iteration's log subdir, not the run dir.** The run dir of a `--loop N` run is a single slot shared by every iteration, so a `tester-findings.json` sitting directly in it may belong to an EARLIER iteration; the iteration's own findings live beside the iteration's MANIFEST at `<run-dir>/iter_NN/`. Resolve the path the same way §2.10 resolves the MANIFEST: if the run dir contains `iter_NN/` subdirectories, read `<run-dir>/iter_NN/tester-findings.{json,md}` for the highest-numbered iteration (the one whose `MANIFEST.json` `git_sha_before` equals `git rev-parse HEAD~1`); only a flat, non-looped run puts the files directly in the run dir. Never read a run-dir copy without first checking for an `iter_NN/` subdir — and if both exist, the iteration copy wins and the run-dir copy is stale by construction. (Observed: a review `cat`-ed the run-dir copy on iteration 3 of a looped run and got the PREVIOUS iteration's `verdict: green` while the current iteration's tester had graded `verdict: red` with a `fail` on the artifact the product emails to third parties; it recovered only because it happened to re-read the iteration copy moments later. A review that stops at the first read consumes a green verdict, files none of the tester's findings, and drops a runtime blocker silently — the tester stage's entire output lost to a path that resolved to the wrong iteration.) If the tester stage ran for this cycle, `tester-findings.json` and `tester-findings.md` are present at the resolved path. Read both when present; when absent, the tester was either pre-empted (`[skip-tester]`) or not yet inserted into the chain — in both cases the review proceeds exactly as before 41.3 with no gap flagged for tester absence.

   When the findings files ARE present, integrate them:
   - A check with `status: fail` becomes or strengthens a `[blocker]` in §4 (a broken surface at runtime is as serious as a code correctness bug).
   - A check with `status: needs-change` becomes or strengthens a `[should-fix]`.
   - An overall `verdict: degraded` (the tester tried but could not fully exercise the surface — server didn't come up, stale auth, partial reachability) is itself surfaced as a `[should-fix]` noting incomplete runtime coverage.
   - An overall `verdict: skipped` (self-skip no-op, or the dev emitted `[skip-tester]` and the runner never spawned the tester) is a valid non-finding state — do NOT file any finding for it.
   - An overall `verdict: green` is a non-finding state **only when every check has `status: pass`**. Always walk `checks[]` first — the per-check `fail` / `needs-change` rules above win over the overall verdict label. Testers may emit `verdict: green` while still carrying a residual `needs-change` (e.g. a coverage gap the exploratory drive already exercised); that residual MUST still become a `[should-fix]` in §4. Do not treat overall `green` as a blanket skip of `checks[]`.

   **Tester-check disposal (hard gate).** Before emitting ANY §6 report form (Clean or With findings), enumerate every `checks[]` entry with `status: fail` or `status: needs-change`. For each, either (a) file/strengthen a §4 finding, **or** (b) record an explicit one-line dismissal in the §6 report as `Tester dismissals: <area> — <one-line reason>` (allowed when the residual does not clear the severity bar — e.g. feed-independent coverage already owned by an open e2e item, or a duplicate of a prior-cycle dismissal). Silent omission is forbidden: a §6 report that never mentions a residual `fail`/`needs-change` is a contract violation even when the dismissal would have been correct. Observed failure modes: (1) overall-`green` reviews skip walking `checks[]` and emit Clean without disposing the residual; (2) With-findings reviews file some residuals and silently drop others below the bar without a `Tester dismissals:` line.

   Include the tester verdict in the §6 report regardless of whether findings were escalated (see §6 template below).

5. Read `docs/SPEC.md` and `docs/TODO.md` end-to-end. The spec tells you what the cycle claimed to close; `TODO.md`'s `## Just shipped` confirms the cycle's own self-reported summary (no SHA in that format — a commit cannot contain its own hash; correlate the top Just-shipped line to HEAD, or to the matching commit via `git log --oneline --grep`).
6. Identify the commit under review:
   ```bash
   git log -1 --format='%H %s'
   ```
   If that commit does **not** correspond to the `## Just shipped` self-report (a skill edit under `.claude/skills/`, a merge, or some other commit the cycle did not produce), walk backward with `git log --format='%H %s' -20` until you find the commit that self-report names. Common scope tags the cycle uses: `Auth:`, `UI:`, `Docs:`, `Tests:`, `Deploy:`, `Infra:`, or a feature-area tag — a `Docs:`-tagged commit is real dev work when it matches `## Just shipped` (the cycle ships docs-only items under `Docs:`), so review it. Review **that** commit — do not review skill-edit or merge commits.

## 1. Gather review surfaces

Run these in parallel:

- `git show HEAD --stat` → files touched.
- `git show HEAD` → full diff of code + tests + spec + docs.
- `git log HEAD -1 --format='%B'` → full commit body (scope tag, claim, test-count delta).
- Locate the project's spec (same file `/sst-dev-cycle` updates — common locations: `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/<project>_SPEC.md`, `TODO.md`, `README.md`). Grep for the section the cycle's commit message references.
- Read the full spec section for that phase/area end-to-end.

Write down (mentally, not to a file): what spec item was closed, what bullets the spec claims are done, what the commit message claims, which files changed.

## 2. Review axes — work through each

For every axis, produce zero or more findings. Each finding has the form:

```
[severity] <file>:<line> — <what's wrong>. <why it matters>. <proposed fix>.
```

Severity = **blocker** or **should-fix** only (see the severity bar above).

### 2.1 Spec ↔ implementation parity

- Does each bullet the spec marks `[x]` actually exist in the diff? Grep for the symbol, function, or behavior the bullet claims.
- Did the commit claim "N new tests" and does `git show HEAD -- <test-dir>` actually add N tests?
- Is the project's status index (e.g. `CLAUDE.md`, `README.md` status table, top-of-spec summary) updated to reflect the new state?

### 2.2 Code correctness

For every new or modified public function, endpoint, handler, or exported symbol:

- **Auth:** new auth-gated paths use the project's canonical auth helper, not a hand-rolled check. If the project has separate helpers for different auth modes (e.g. account-scoped vs. anonymous-paid), the right one is used.
- **Auth-before-body:** on paid or auth-gated endpoints, credentials are checked **before** parsing the request body, so unauthenticated scanners get the project's standard auth-error response and not a body-validation error.
- **Rate limiting:** the path is rate-limited along every axis that makes sense for it (per-user AND per-IP if both are real surfaces).
- **Pre-flight checks:** any expensive operation is gated by a cheap pre-check (balance / quota / size cap) that fails fast with a useful error.
- **State mutations:** `commit` / `save` / equivalent is called after the mutation; no bare add-without-commit; no commit inside a hot loop.
- **Error handling:** exceptions are mapped to safe user-facing errors. Internal detail (`str(e)`, stack frames, payment hashes, token prefixes) is never in user-visible error fields.
- **Input validation:** every string has an upper length bound; every list has a length bound; every enum-like field has an allowlist validator. No unchecked user input flows into shell commands, SQL, a search query, or file paths.
- **Architectural gotchas:** any rule the project's CLAUDE.md / README calls out (e.g. "never import X at module scope in Y", "new columns need an ALTER in migrate()", "service restart uses Z not Y") — did the cycle honor them? Grep for the specific symbol/pattern the rule names.

### 2.3 Test coverage

For each new test file or modified test file:

- **Happy path.** Yes, obvious — is it actually there?
- **Adversarial input:** malformed body, missing required field, over-limit batch, wrong types.
- **Auth failures:** no credential, invalid credential, wrong-scope credential. If the project distinguishes between "invalid credential" and "needs payment," a test proves the right status code fires for each.
- **Boundary conditions:** min and max of every range. Empty list if allowed. One item. Exactly the cap.
- **Dedup / caching:** if the code adds a cache, a test proves the cache is hit (call counter, mock observed once).
- **Ordering / idempotency:** if order or idempotency is claimed, a test asserts it.
- **Cross-user / cross-tenant isolation:** if the endpoint reads scoped data, a test proves user A cannot see user B's rows.
- **Branch coverage of the endpoint itself, not just its helpers.** A very common gap: the cycle adds a helper + helper tests, but every test that hits the endpoint lands in an early error path (e.g. the auth 401/402) and never exercises the happy branch — meaning regressions inside the handler (balance accounting, cache-header writing, id formatting) won't trip any test.
- **Test count:** the commit message claims `old → new`. Run the project's collect-only equivalent (`pytest --collect-only -q | tail -3`, `jest --listTests`, `go test -list '.*'`) and confirm the current total matches the `new` number. If the absolute is off but the delta is right, it's cosmetic — don't file unless it's misleading. **Do not** try to compare against HEAD~1's count by checking out the prior commit (`git checkout HEAD~1 -- .`, `git stash && git checkout HEAD~1 -- .`, or any variant that mutates the working tree). That pattern has previously destroyed working-tree state — including a freshly-popped stash — and required `git fsck --lost-found` to recover. The commit message's claimed `old` is the source of truth; if you don't trust the claim, read the prior commit's diff with `git show HEAD~1 -- <test-dir>/ | grep -c '^+def test_'` (or the project's language-equivalent) instead of touching the tree. If you genuinely need a true HEAD~1 collection (rare), use `git worktree add /tmp/review-prev HEAD~1` against an isolated path, run the collect command there, then `git worktree remove /tmp/review-prev` — never the live working tree.

### 2.4 Discovery / documentation surfaces

If the cycle added or changed a public-facing API or capability, every surface the project advertises should reflect it:

- **OpenAPI / schema files** if the project publishes them.
- **Agent / MCP / `.well-known/` manifests** if the project exposes them to external agents.
- **README / quickstart / example curl-block** if the project documents the API there.
- **Index / status table** in the project's CLAUDE.md or top-level docs.

Missing a surface is a should-fix, not a nit: discovery drift is what makes APIs look broken to outside callers even when they work.

### 2.5 Production verification

Walk the `/sst-dev-cycle` transcript (or reconstruct from the diff):

- Was the change actually hit against the **production** URL, not just localhost?
- Were both happy path AND at least one adversarial input exercised live?
- Did the production process count / health check show what the project's operational docs say it should?
- If the cycle added a schema migration, was `\d <table>` (or equivalent) actually run in prod to confirm the column exists?
- If the cycle changed a background worker, was a real job submitted and observed to completion?

A missing prod-verify of a migration, auth path, or billing path is **blocker**. A missing prod-verify of a pure UI change is should-fix.

### 2.6 Security

- **Injection:** new user-controlled string flowing into a search query, SQL, shell, subprocess arg, CSV — is it sanitized / parameterized?
- **Authorization bypass:** new endpoint reading by id — is it scoped by user/tenant, or can anyone with an id read anyone's row?
- **Replay:** payment / signed-request flows use the project's canonical consume-once helper (not a hand-rolled hash check).
- **Secrets in logs / errors:** new log lines / debug prints / error messages — do any of them include a token, preimage, payment hash, or API key in full?
- **Rate-limit coverage on the new path:** both axes (user AND IP, or equivalent for the project).

### 2.7 Programming style

**Flag only if the style issue has real, medium-to-major consequences** — otherwise skip. Magic numbers, minor duplication, comment wording, and most style nits should NOT be filed. Only file when the defect will cause a real bug, real confusion for the next engineer, or reflects an architectural mismatch that will bite later:

- `TODO` / `FIXME` / `XXX` committed to main on a load-bearing code path (not on cosmetic code).
- Placeholder values in production code (`<YOUR_KEY>`, `0x...`, `foo@bar.com`) that will ship as-is.
- New mocks that contradict the real architecture (e.g. mocking a real DB when the whole point was an integration test) — this is a correctness gap, not style.
- Duplicate logic where the two copies will silently diverge and cause a real bug (e.g. two pricing formulas, two URL-builder functions).

### 2.8 Performance

- DNS / HTTP / external API call without an explicit timeout argument?
- Unbounded loop over user-supplied list without a cap?
- Per-row DB query inside a loop that could be one batched query (`IN (...)`, `ANY(...)`, join)?
- Synchronous blocking call inside an async handler that holds the event loop?

### 2.9 Batch coherence

**Locating the dev transcript is a mandatory first action of this axis — not a precondition to judge as unmet before looking.** List `.skill-runs/` and open the most recent dev transcript (`.skill-runs/*/iter_NN/00_<dev-skill>.txt` or `.skill-runs/*/00_<dev-skill>.txt`). This axis applies whenever the dev cycle used the batching protocol — i.e. the dev emitted a `[batch-pick]` block to stdout before its first tool call — and you confirm that by reading the transcript, not by assuming. If you genuinely cannot find a dev transcript after running the lookup, fall back to the `## Just shipped` top entries in `docs/TODO.md` as a proxy and note the fallback in §6. Never report this axis as "nothing to flag" without having opened the transcript (or recorded the fallback) — an axis you did not attempt to run is not a clean axis.

**Find the `[batch-pick]` block** in the dev transcript located above.

Parse the block's stated items and compare against the actual commit:

- `git show HEAD -- docs/SPEC.md | grep '^\+.*\[x\]'` — each `[x]` flip should correspond to a stated batch item (no extra flips, no missing flips).
- `## Just shipped` additions in the diff — each stated item should have a corresponding entry.
- `git show HEAD --stat` — files touched should be explained by the batch items; two or more items that touch disjoint files with no shared SPEC phase, concept, or mechanical pattern signal incoherent bundling.

**File a `[should-fix]` tagged `[batch-coherence]`** when any of: (a) a stated item has no `[x]` flip and no Just-shipped entry; (b) the diff contains `[x]` flips absent from the stated batch; (c) batch items touch disjoint files with no discernible shared relation axis.

Do **not** file for a single-item batch (trivially coherent) or when the multi-file reach is a uniform mechanical change (e.g. tagging the same frontmatter field in N SKILL.md files = one concept, one axis).

### 2.10 Batch sizing

**Locating the iter MANIFEST is a mandatory first action of this axis — not a precondition you may judge as unmet before looking.** List `.skill-runs/` and locate the MANIFEST at `.skill-runs/<latest-run-dir>/MANIFEST.json` (flat) or `.skill-runs/<latest-run-dir>/iter_NN/MANIFEST.json` (looped run). Only if no MANIFEST file exists *after you have actually run the lookup* may you note "iter MANIFEST absent" in §6 and skip this axis; that §6 note is mandatory whenever the axis is skipped. Never report this axis as "nothing to flag" without having read a MANIFEST — an axis you did not attempt to run is not a clean axis.

**`"in_progress": true` on the iter MANIFEST is the normal mid-chain state, not a receipt gap.** The chain runner snapshot-writes each skill's record as that skill finishes, so by the time this review runs the dev's `skills[]` entry, including the `model_usage` token receipt this axis needs, is already present while the chain-level `in_progress` flag is still true (it stays true until after the auto-supervisor returns). Never skip the band check, or report the dev's receipt as unavailable, because the MANIFEST is `in_progress`: the only legal skip remains a MANIFEST file that does not exist on disk after the lookup actually ran. (Observed: a review that had already read an `in_progress` MANIFEST containing the dev's full `model_usage` reported the axis skipped for "no dev input_tokens receipt available", a fifth receipt form the §6 clause rules do not permit; the correct action was to sum `inputTokens + cacheCreationInputTokens` from the dev record it had already read.) The same snapshot semantics bind chain-state narration anywhere in your report, not just the band check: records for stages that run after this review (the auto-supervisor, and any stage the runner has not reached yet) are legitimately absent from `skills[]` while you read, because the review runs mid-chain. Never report the chain as "interrupted", "truncated", or "the supervisor never ran" from `in_progress` plus a missing later-stage record, including in free-form "worth surfacing" notes -- confine chain-state observations to what the MANIFEST positively records (a `rate_limit_pauses` entry, a `skill_failure` flag). (Observed: a review resuming after a mid-iter rate-limit pause surfaced "chain was interrupted; supervisor never ran" as fact in its report extras while the runner was still mid-flight driving the iteration, and folded a dev-emitted tester skip it had itself validated as legitimate two axes earlier into the same interruption narrative.)

**Do not infer MANIFEST absence from the run-directory name.** A `.skill-runs/<run-dir>` name carries the chain's *start* timestamp, not the commit time. In a `--loop N` run the iteration that produced HEAD commits minutes-to-hours after the chain started, so a run dir whose name predates the commit by hours is normal — it is **not** evidence that "the commit came from a wiped or manual run with no `.skill-runs/` entry." Never reason from run-dir-name-vs-commit-time at all. Identify the run positively instead: list the most recent `<run-dir>/` for `iter_NN/` subdirectories, then read the highest-numbered `iter_NN/MANIFEST.json` — its `git_sha_before` equals the commit's parent (`git rev-parse HEAD~1`) when you have the right iteration. Declare the MANIFEST absent only when that file genuinely does not exist on disk.

Read: `difficulty` (set by the runner's sentinel capture) and the dev skill's input tokens: sum `inputTokens + cacheCreationInputTokens` across all entries in its `model_usage` dict for **the dev skill only** (`skills[0]` — the first skill in the chain, the one that chose how much work to take on; `model_usage` is keyed by model name, not a flat dict; `cacheCreationInputTokens` measures tokens written to cache first-time — a proxy for peak context size; `cacheReadInputTokens` is a billing-centric cumulative that grows with session turns, not context complexity, and would inflate the total ~40× for long sessions). Do NOT sum review + supervisor tokens — those skills consume what they consume regardless of workload sizing; only the dev skill can act on its own window.

**Sanity-check the computed `actual` against the band before you use it.** `cacheReadInputTokens` is the largest number in `model_usage` and summing it by reflex is the recurring failure mode here — it inflates `actual` roughly 40×, far past any real workload. So if your computed `actual` exceeds the difficulty's upper band edge by more than ~3× (e.g. an `[easy]` reading of 1500k or 2600k against a 200k edge), you almost certainly included `cacheReadInputTokens`; recompute as `inputTokens + cacheCreationInputTokens` only before deciding the finding or emitting the machine line. A genuine oversize is at most ~2-3× the edge; an order-of-magnitude overshoot is a measurement error, not a batch-sizing signal, and emitting it pollutes the supervisor's §3.5 trailing-window aggregation with a false `oversized` line.

Band edges by difficulty (dev-skill input-token targets — same values the dev skill uses for its own batch window-sizing; the `[batch-sizing]` finding fires on the dev's number, not the full-chain sum):
- `[easy]` → 100–200k; undersize threshold 50k (50% of lower edge)
- `[medium]` → 200–300k; undersize threshold 100k
- `[hard]` → 400–500k; undersize threshold 200k

Also read the `[batch-pick]` block's `window-target ~XXk` and verify it falls within the band for the stated difficulty.

**File a `[should-fix]` tagged `[batch-sizing]`** when:
- **Undersized**: actual input tokens < the undersize threshold AND the pre-commit queue (read from `git show HEAD -- docs/TODO.md | grep '^\-.*\[' | head -20`) offered ≥1 item of compatible difficulty + related concept that the dev did not batch.
- **Oversized**: actual input tokens exceed the upper band edge, OR MANIFEST records `terminated_by == "max_turns"`, OR the diff shows no SPEC `[x]` flips despite a stated batch pick (§6+§7 of the dev cycle did not land cleanly).

Include the actual token count, difficulty, and band edges in the finding text. The `[batch-sizing]` tag allows the supervisor to aggregate findings across iters and trigger window-target refinement.

Also emit a **machine-parseable summary line** to stdout immediately after deciding the finding (before §3), one line per direction found:

```
[batch-sizing] direction=<undersized|oversized> difficulty=<tier> actual=<n>k band=<lo>-<hi>k
```

This line is the supervisor's §3.5.1 extraction target and must appear as a standalone line in the transcript. If no batch-sizing finding fires this iter, do not emit the line -- but an in-band conclusion is still a COMPUTED conclusion: state the computed metric in your §6 report anyway (e.g. `batch-sizing: actual=245k vs band 200-300k -> in-band, no line`) so the number is auditable. A "within band" claim is compliant ONLY when it states BOTH the computed `actual=` value AND the band edges it was compared against, AND `actual` falls numerically inside that band: a receipt that quotes the actual but names no band has skipped the comparison (observed: a receipt quoting `actual=384k` declared a 200-300k-band iter "in-band"), one whose own `actual=` lies outside the band it names is self-contradictory, and a receipt with NO numbers at all -- a purely qualitative judgment ("single focused item -- in-band") -- is the same skipped comparison even when the review fetched the dev's token totals moments earlier (observed: a review pulled the dev's token footer expressly "for the batch-sizing receipt", then wrote "in-band" with neither `actual=` nor band edges on an iter whose true ~141k actual sat below its 200-300k band; fetching the numbers is not comparing them -- the receipt is compliant only when the computed `actual=` appears in it) -- in all three cases re-run the comparison and emit whatever the fire-rules above actually produce: an `oversized` machine line when `actual` exceeds the upper edge; an `undersized` machine line ONLY when the undersized rule holds (`actual` below the undersize threshold, plus the unbatched-queue condition); and NO machine line when `actual` lies below the lower edge but at-or-above the undersize threshold -- that below-band gap is a legal no-line state (the band table's undersize thresholds define it) and takes the below-band receipt form in §6, NOT the `in-band` wording and NOT a fabricated `undersized` line (a machine line emitted outside the fire-rules feeds a false direction into the supervisor's §3.5 trailing-window aggregation). Eyeballing the diff's apparent size instead of comparing the summed MANIFEST metric against the band edges produces a silent false-negative (a missing `oversized` line breaks the supervisor's §3.5 same-direction streak) exactly as damaging as the false-`oversized` inflation the sanity-check above guards against.

**The machine-parseable line is the SOLE handoff of a batch-sizing finding; do NOT also route it through §4.** A batch-sizing finding's resolution is the supervisor's window-target refinement (`sst-supervisor` §3.5), which aggregates these machine lines across many iters and is threshold-gated; it is not autonomous dev-cycle work. So a `[batch-sizing]` finding does NOT get filed to the spec, `## Next up`, or `FUTURE-WORK.md`, and does NOT count toward the §3 routed-finding total that decides whether to commit; emit the machine line and stop there. Filing it as a per-iter spec/TODO item injects skill-prose-editing work into the dev cycle's own pick queue (work the dev neither owns nor should pick, since the window-target prose lives in the dev SKILL.md the supervisor governs), displaces genuine feature items at the top of the queue, and can provoke a premature single-iter window change that §3.5's cross-iter thresholds exist to prevent.

## 3. Decide on output

Count findings after you've applied the "no nitpicks" bar.

- **Zero findings after the bar**: the cycle was clean. Skip step 4. Go to step 5 and report clean.
- **At least one should-fix or blocker**: go to step 4, append to spec, commit.

A clean report with no findings is a success signal, not a failure to find work. Don't pad.

## 4. Append follow-ups to the spec + TODO.md

**Route first: two destinations.** Before filing any finding, decide the destination:

- **`docs/FUTURE-WORK.md`** (acceptance/smoke-test findings AND human-only blocker findings): route here when the resolving action requires (a) a real chain-driver round-trip, Telegram message exchange, human-verified end-to-end smoke, or any check the dev cycle cannot perform autonomously from inside its own iteration; OR (b) an out-of-band human action — setting a secret, granting third-party-UI/cloud-IAM access, signing a legal agreement, or any fix that inherently requires credentials the cycle does not hold. For human-only findings, prefix the entry with `human-only:` so the oversight layer (`sst-supervisor`, `sst-manager`) can detect and escalate them. Append under `## Manual / human verification > ### <Phase context>` (create the sub-section if absent). One line per finding. Do NOT also mirror to spec or `## Next up` — these items sit in FUTURE-WORK.md until a human (or the oversight layer) decides to act on them.
- **Spec + `docs/TODO.md`** (all other findings): code corrections, prose edits, schema additions, contract clarifications — work a future dev cycle can execute autonomously. File in the spec and mirror to `## Next up` per the rules below.

Signs it belongs in FUTURE-WORK.md: the proposed fix is "set a secret", "grant access", "sign an agreement", "run an acceptance test", "verify via a Telegram bot", "confirm with a live chain-driver run", "observe in production", or "exercise end-to-end by hand" — any fix the dev cycle cannot self-verify from inside the chain. For purely human fixes, prefix with `human-only:`. Signs it belongs in spec + TODO: the proposed fix is a code change, a prose edit, a schema addition, or any other autonomous development task.

**Spec.** Open the project's spec file (same one `/sst-dev-cycle` updates). Under the sub-section the cycle touched, append a **Review follow-ups** subsection. Format:

```markdown
**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [ ] <phase>.<n> [<difficulty>] [blocker] `<file>:<line>` — <one-sentence description>. Proposed fix: <short hint>.
- [ ] <phase>.<n> [<difficulty>] [should-fix] `<file>:<function>` — <one-sentence description>. Proposed fix: <short hint>.
```

Rules:

- Every entry MUST start with a stable `<phase>.<n>` sub-item ID immediately after the checkbox, then the difficulty bracket, then the severity bracket. The ID belongs to the same Phase header the **Review follow-ups** subsection lives under; pick the next unused `<n>` in that phase (gaps from closed items are valid — do not renumber). `bin/validate-frontmatter.py` rejects any checkbox bullet in `docs/SPEC.md` that lacks this ID in the correct position, so a missing or mis-ordered ID is a CI failure. Run the validator **bare** to exercise that check: `python bin/validate-frontmatter.py` with no path arguments scans `docs/SPEC.md` (plus `docs/TODO.md`) on fixed repo paths. If `bin/validate-frontmatter.py` is absent (not every consuming project vendors the script), skip the validator step instead of re-probing interpreters or paths: a missing-file exit (127 from a missing interpreter, 2 from a missing script) means the project has no CI frontmatter gate to satisfy, not that your spec edit broke validation. Do NOT pass `docs/SPEC.md` or `docs/TODO.md` as path arguments; positional args are validated as `SKILL.md` frontmatter, so a doc path there fails the SKILL schema and exits 2. That is a spurious failure that looks like your spec edit broke validation when only the invocation was wrong. Difficulty is one of `[easy]` / `[medium]` / `[hard]` per the SPEC.md "Difficulty labels" appendix; the project's chain runner pre-parses it to route the next cycle's skills (`effective = max(item_tier, skill_floor)` per axis). Closed `[x]` items don't carry the label (historical).
- Only `[blocker]` and `[should-fix]` severities go here. No nice-to-have / nitpick / cosmetic items — if you can't justify why it causes a real bug, security risk, or major confusion, don't file it.
- One checkbox per finding; do not bundle. A later `/sst-dev-cycle` will pick the top unchecked item (or a bundled chunk, if it uses a chunk-sizing rule).
- Order by severity (blocker → should-fix), then by file/line. Difficulty is independent of severity and does not affect ordering.
- If a finding also affects another sub-section or module, put the follow-up under the **most recent** sub-section (the one this review targets), not the older one. The idea is to work chronologically through the spec.
- Do not move any existing `[x]` box to `[ ]`. If a previously-claimed item turns out to be incomplete, that is a **new** follow-up line, not a regression edit.

**Bounded-item rule.** Every spec item filed must name a *specific feature with a falsifiable acceptance criterion*, not a standing activity. Every corresponding `## Next up` entry must be a *specific, completable action* whose done-state is unambiguous. Open-ended / recurring / catch-all items are forbidden.

*Forbidden shape:* "address remaining edge cases in the X module", "continue improving Y", "iterative Z polish" — no natural end-state, will never flip to `[x]`.

*Required instead:* decompose into concrete enumerated items, each naming a target file/symbol and a done-condition: "add adversarial test for `X.validate()` with empty-list input in `tests/test_x.py`"; "cap loop in `y.py:do_thing()` at 1000 iterations". A real but unbounded cleanup that resists this decomposition should not be filed.

**Assigning difficulty from the finding's nature.** Difficulty answers "how much reasoning does the FIX cost?", not "how serious is the BUG?" — severity already covers seriousness. Default mapping:

- `[easy]` — prose nit in a SKILL.md or doc, a single-line typo / stale number, hoisting a one-liner inside a heredoc, quoting a YAML scalar, applying a known-good migration to N call-sites, tagging frontmatter with a value the spec already names.
- `[medium]` — a bounded code change touching one module + its tests, a localized helper rewrite, softening one halt-condition to note-and-proceed with a narrow exception, a contract addition the spec has already designed (no new schema decisions).
- `[hard]` — cross-file refactor, a new schema field with runner support, a concurrency / lifecycle invariant (refcount, flock, signal handling), anything that requires a fresh design judgment or interacts with a security/data-integrity surface.

If the finding's fix straddles two tiers, pick the higher one — under-routing burns the cycle on a too-small model; over-routing only spends quota. A `[blocker]` that's mechanically a one-liner (e.g. a hoist) is still `[easy]`; a `[should-fix]` that needs a refcount is still `[hard]`.

**TODO.md.** Open `docs/TODO.md`. For each finding you just filed in the spec, append a corresponding line to `## Next up`:

```markdown
- [<difficulty>] [blocker] <spec-ID> <one-line restating the spec entry, with file:line> — review of <commit-sha-short>
- [<difficulty>] [should-fix] <spec-ID> <one-line restating the spec entry, with file:line> — review of <commit-sha-short>
```

Use the same `<difficulty>` token you assigned in the spec entry; the two surfaces stay in lockstep. Include the spec item's `<phase>.<n>` ID as the first token after the severity bracket so that `remove <ID>` commands in the manager's ID-addressed pre-check can match and purge the entry atomically.

**Same-root tagging.** If two or more findings share a single root cause (the same constant needs propagating to multiple surfaces; the same missing guard appears across sibling modules; the same discovery surface is stale in both a manifest AND a README), append `(group with <root-keyword>)` to each TODO.md line, where `<root-keyword>` is a short token that names the shared cause. Pick a token that's specific enough to disambiguate from unrelated work (e.g. `(group with input-bound-propagation)`, `(group with manifest-readme-sync)`, `(group with auth-helper-migration)`) and reuse the exact same token across every entry in the group — `sst-dev-cycle` §1's same-root bundling rule keys on string-equality of the tag. Tag only when the bundling is real: disjoint files, cohesive change, plausibly under ~300 LoC combined. Spec entries do NOT get the tag — the spec is a longer-lived record and bundling is a TODO-level scheduling concern; the spec's filing rule of "one checkbox per finding, do not bundle" is unchanged. If only one finding is on the shared root, do not tag (a `(group with X)` of size 1 is just noise).

Order: blockers first, then should-fix, then any pre-existing entries (push pre-existing entries down — review-spawned items get priority). When a group share is involved, keep the tagged entries adjacent within their severity band so the next cycle sees them as a contiguous run. Don't touch `## In flight` or `## Just shipped`; those belong to `sst-dev-cycle`.

## 5. Commit + push (only if step 4 actually added items)

**Commit-message rule (read BEFORE composing the heredoc):** never append a `Co-Authored-By: Claude ... <noreply@anthropic.com>` trailer (or any AI-coauthor trailer variant). The heredoc body below ends at `EOF` — nothing else goes after the closing paragraph. Empirical placement-below-heredoc was being skipped by models reading top-down, so the rule lives ABOVE the template now.

```bash
git add <spec-file> docs/TODO.md docs/FUTURE-WORK.md  # TODO.md only if you wrote a Next-up entry; FUTURE-WORK.md only if §4 routed findings there; plus any status-index file you corrected
git commit -m "$(cat <<'EOF'
Review: follow-ups from <scope>: <one-line reference to cycle>

<Paragraph: what was reviewed, findings count by severity, and the
single highest-impact item. Point the reader at the new "Review
follow-ups" block in the spec.>

EOF
)"
git push origin <branch>
```

**Never deploy.** This skill does not touch production. The follow-ups are spec-only; actual fixes go through `/sst-dev-cycle`.

## 6. Report to user

Two forms — pick one, no follow-up question, no offer to fix.

**Clean:**

> Reviewed commit `<sha>` (`<scope>: <summary>`). Checked all review axes (parity, correctness, coverage, docs, prod-verify, security, style, performance). No substantive findings at the blocker or should-fix bar. Spec unchanged. Tester: <green|skipped|degraded|red> (<n> checks). Batch-sizing: <actual=<n>k vs band <lo>-<hi>k -> in-band, no line | actual=<n>k vs band <lo>-<hi>k -> below band, above undersize threshold (<t>k), no line | line emitted: direction=<dir> actual=<n>k band=<lo>-<hi>k | axis skipped: iter MANIFEST absent>.

**With findings:**

> Reviewed commit `<sha>` (`<scope>: <summary>`). Found <N> items: <B> blocker, <S> should-fix. Appended a "Review follow-ups" block under `<section>` in the spec and committed as `<review-sha>`. Highest-impact: <one-line description of the worst item>. Tester: <green|skipped|degraded|red> (<n> checks). Batch-sizing: <actual=<n>k vs band <lo>-<hi>k -> in-band, no line | actual=<n>k vs band <lo>-<hi>k -> below band, above undersize threshold (<t>k), no line | line emitted: direction=<dir> actual=<n>k band=<lo>-<hi>k | axis skipped: iter MANIFEST absent>.

The `Found <N> items: <B> blocker, <S> should-fix.` clause is machine-parsed, not prose: the supervisor's fast-path (`sst-supervisor` §0.5 condition #3) anchors on the exact string `Found <N> items:` to detect a findings-filing review. Emit it verbatim: plural `items:` even when N=1, digits not words, and no markdown emphasis inside the clause (bold like `Found **1 item: ...**` breaks the anchor). When another clause of the template does not apply (e.g. the spec docs are untracked, so there is no `<review-sha>` to cite), adapt THAT clause ("filed on disk; no commit needed") and keep this one intact. A findings-filing review that paraphrases the clause (`Found 1 blocker.`, `Verdict: 3 should-fix filed`) can be mislabeled `clean (fast-path)` by the supervisor, silently dropping its findings from oversight. The clause belongs to the **With findings** form ONLY: a clean review (zero items after the bar) uses the Clean form and MUST NOT emit a zero-count variant (`Found 0 items: 0 blocker, 0 should-fix`), because the supervisor treats a `Found <N> items:` match as a findings-filing signal and a zero-count emission forces a needless deep walk on exactly the clean iterations its fast-path exists to skip.

`Tester:` line rules: use `skipped` when findings are absent or `verdict: skipped`; `green` when `verdict: green`; `degraded` when `verdict: degraded`; `red` when `verdict: red`. Include the check count from `checks[]` when the file is present (`0` when skipped/absent). When tester files are absent, emit `Tester: skipped (0 checks)` so the supervisor can track tester coverage across iterations.

`Batch-sizing:` clause rules: this clause is the §2.10 axis's mandatory receipt and appears in EVERY report, both forms. Exactly one of: the computed in-band statement (`actual=<n>k vs band <lo>-<hi>k -> in-band, no line`), the below-band no-line statement (`actual=<n>k vs band <lo>-<hi>k -> below band, above undersize threshold (<t>k), no line`) for the legal gap state where `actual` sits below the band's lower edge but at-or-above the difficulty's undersize threshold (§2.10's undersized finding does not fire there, so there is no machine line to repeat -- and the `in-band` wording would be self-contradictory), a repeat of the machine line's values when a finding fired this run (`line emitted: direction=<dir> actual=<n>k band=<lo>-<hi>k`), or `axis skipped: iter MANIFEST absent` (legal only after the §2.10 MANIFEST lookup actually ran and found no file). A report with no `Batch-sizing:` clause means the axis was silently skipped — the exact false-negative §2.10 warns about: the missing `undersized`/`oversized` machine line breaks the supervisor's §3.5 trailing-window aggregation, and without this receipt slot the omission is invisible because the rest of the report reads complete.

## Pitfalls to avoid

- **Re-running the full test suite is fine but not the point.** A green suite doesn't prove the feature is complete, because the tests were written alongside the feature. Your job is to find what the tests forgot to check.
- **Don't grep for generic keywords and call it review.** "I searched for `TODO`" is not review. Read the actual diff line by line.
- **Don't invent requirements not in the spec.** If the spec said "format + MX only" and the code does exactly that, not adding an SMTP probe is a feature, not a gap. If the *spec* missed something obvious, that is a spec-level finding (propose a new spec bullet), not an implementation bug.
- **Don't double-count.** If one root cause surfaces in three places, file one finding.
- **Don't escalate style to blocker.** A magic number in test-only code is not worth flagging at all under the severity bar — skip it.
- **Don't pad the review.** If after honest examination you have zero blocker/should-fix items, report clean and stop. A zero-item or one-item review is a success signal. Nitpicks, stylistic preferences, cosmetic doc polish, minor duplication, and comment wording never go in the follow-ups.
- **Don't review the review.** When you're done with the findings list, stop.
- **Don't claim parser or runner behavior without reading the code.** If a finding hinges on how the chain runner (or any `bin/` script the project ships) parses a line — a difficulty bracket, a sentinel match, a header anchor — open the function and verify against its actual regex/logic before filing. A `re.search()` on `\[(easy|medium|hard)\]` scans the whole line and is robust to a leading source-tag bracket; a `re.match()` anchored to start is not. Don't assume which one is in use. A factually-incorrect parser claim creates a false-positive finding that wastes the next cycle and may motivate a "fix" that breaks behavior working as designed.
- **Don't touch the working tree to "compare against HEAD~1."** Never `git checkout HEAD~1 -- .`, never chain `git stash` with `git checkout` of the prior commit. Either pattern can clobber the working tree (including a freshly popped stash) and require `git fsck --lost-found` to recover. Any prior-state inspection should use `git show HEAD~1 -- <path>` (read-only, doesn't touch the tree) or a separate worktree (`git worktree add /tmp/review-prev HEAD~1`, then remove when done).
