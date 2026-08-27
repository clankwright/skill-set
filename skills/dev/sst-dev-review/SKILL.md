---
name: sst-dev-review
description: Post-cycle second-pass review of the last `/sst-dev-cycle` commit on any project. Reads what shipped (code + tests + spec + TODO + docs), evaluates it against the spec item it closed along several axes (spec parity, correctness, coverage, discoverability, production verification, security, style, performance), and appends concrete follow-up items to the project's spec AND the handoff TODO's "Next up" if critical, blocking, or medium-to-major gaps are found. If nothing substantive turns up, leaves both unchanged and reports "clean." Does NOT fix issues — only names them and schedules them as spec work for the next `/sst-dev-cycle`. Pair with `/sst-dev-cycle` (chained via `bin/skill-chain.py sst-dev-cycle sst-dev-review`).
user-invocable: true
version: 1.27.0
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

**Spec sub-item IDs.** Every `- [ ]` item in `docs/SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 3.1 [hard] **description**`). IDs are assigned once and never renumbered — gaps from closed/removed items are valid. When filing follow-ups to `## Next up` in §4, the new ID's `<phase>` MUST be the phase of the work this review is reviewing (the shipped pick), not a different phase's dump. Cite that ID (e.g. `reason: spec 5.2`) rather than "Phase N sub-item" for durability.

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
      1. Run the project's full test suite (`pytest tests/ -q` or equivalent) **in the foreground**: a single blocking command with the tool timeout raised for a slow suite; never launch this recovery gate as a detached/background job and then poll its output file. This mirrors `sst-dev-cycle` §4's foreground-gate rule and exists for the same reason: a single-shot review invocation is not re-invoked after its turn ends, so pausing to poll a backgrounded suite ends the turn with the recovery commit still pending and re-strands the very cycle this step exists to heal. Note that a foreground command left at the default tool timeout can itself be auto-backgrounded by the harness when it overruns, landing you in the same poll trap, so raise the timeout explicitly rather than relying on the default; and if the suite genuinely exceeds even the raised foreground timeout, run it as foreground shards you block on sequentially. If **any** test fails (**tests green** signal absent): print `[incomplete-cycle] tests failing in dirty tree; cannot auto-commit`, surface the failure detail to the user, and **exit**. Do NOT commit or push.
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
4. **Tester findings (back-compat: review proceeds unchanged when files are absent).** Locate the chain run-log dir (most recent `.skill-runs/<*>/` under the current working directory, or the path the chain runner printed as `[log-dir] <path>`). **In a looped run, read the findings from THIS iteration's log subdir, not the run dir.** The run dir of a `--loop N` run is a single slot shared by every iteration, so a `tester-findings.json` sitting directly in it may belong to an EARLIER iteration; the iteration's own findings live beside the iteration's MANIFEST at `<run-dir>/iter_NN/`. Resolve the path the same way §2.10 resolves the MANIFEST: if the run dir contains `iter_NN/` subdirectories, read `<run-dir>/iter_NN/tester-findings.{json,md}` for the highest-numbered iteration (the one whose `MANIFEST.json` `git_sha_before` is an ancestor of HEAD — see §2.10; an exact `HEAD~1` match is NOT required, since a dev that took a preparatory commit starts from `HEAD~2` or earlier); only a flat, non-looped run puts the files directly in the run dir. Never read a run-dir copy without first checking for an `iter_NN/` subdir — and if both exist, the iteration copy wins and the run-dir copy is stale by construction. (Observed: a review `cat`-ed the run-dir copy on iteration 3 of a looped run and got the PREVIOUS iteration's `verdict: green` while the current iteration's tester had graded `verdict: red` with a `fail` on the artifact the product emails to third parties; it recovered only because it happened to re-read the iteration copy moments later. A review that stops at the first read consumes a green verdict, files none of the tester's findings, and drops a runtime blocker silently — the tester stage's entire output lost to a path that resolved to the wrong iteration.) If the tester stage ran for this cycle, `tester-findings.json` and `tester-findings.md` are present at the resolved path. Read both when present; when absent, the tester was either pre-empted (`[skip-tester]`) or not yet inserted into the chain — in both cases the review proceeds exactly as before 41.3 with no gap flagged for tester absence.

   When the findings files ARE present, integrate them:
   - A check with `status: fail` becomes or strengthens a `[blocker]` in §4 (a broken surface at runtime is as serious as a code correctness bug).
   - A check with `status: needs-change` becomes or strengthens a `[should-fix]`.
   - An overall `verdict: degraded` (the tester tried but could not fully exercise the surface — server didn't come up, stale auth, partial reachability) is itself surfaced as a `[should-fix]` noting incomplete runtime coverage.
   - An overall `verdict: skipped` (self-skip no-op, or the dev emitted `[skip-tester]` and the runner never spawned the tester) is a valid non-finding state — do NOT file any finding for it.
   - An overall `verdict: green` is a non-finding state **only when every check has `status: pass`**. Always walk `checks[]` first — the per-check `fail` / `needs-change` rules above win over the overall verdict label. Testers may emit `verdict: green` while still carrying a residual `needs-change` (e.g. a coverage gap the exploratory drive already exercised); that residual MUST still become a `[should-fix]` in §4. Do not treat overall `green` as a blanket skip of `checks[]`.
   - A check with `status: pass` is a non-finding for §4 purposes, with ONE exception that is not a finding but a §5 EDIT: when a `pass` check's recommendation names a correction to the TEXT of an OPEN spec item (a hedge the tester has now measured, an acceptance clause the just-shipped commit made unreachable, a figure the tester confirmed or corrected), apply that correction to the item's own text in §5 alongside the new findings, and say so in the §6 report. Narrating it in §6 alone is not enough: the next cycle picks that item and reads its stale text, so a tester-superseded hedge sends it to re-measure what the tester already measured, and a superseded acceptance clause sends it to write a guard against a state that can no longer be reached. The tester is the only stage that measured the item live, and a `pass` verdict on the measurement does not make the correction optional. Mirror the same correction into the queue file (`docs/TODO.md`) when the item is also queued there — the dev reads the queue entry before the spec item. (Observed: a tester `pass` check reported that an open item's "computed, not yet live-measured" figure was now live-confirmed under both rendering variants; the review acknowledged it in its §6 report and re-ordered the item's queue entry, but left both the spec item and the queue line carrying the "computed" hedge AND the item's own "measure it live before fixing" instruction — with that item grouped into the very next cycle's batch, so the next dev was directed to spend a live drive re-measuring a figure already confirmed.)

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

**A docs-only cycle with no new tests is not a coverage finding.** When every changed file is prose, "shipped without tests" and a flat pass count are the correct outcome — do not file it, and do not propose a guard that reads the document and asserts on its wording. Documentation is not a behavioural contract: a test that greps a `.md` file for a phrase, heading, or checkbox exercises no code path and goes red whenever someone rewords a paragraph. If a documented claim is worth guarding, file the guard against what the document describes (the flag the CLI exposes, the field the endpoint returns), never against the text. Equally, treat an EXISTING prose-asserting test in the diff as a finding in its own right, and propose deleting it rather than repairing it.

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

**File a `[should-fix]` tagged `[batch-coherence]`** when any of: (a) a stated item has no `[x]` flip and no Just-shipped entry; (b) the diff contains `[x]` flips absent from the stated batch; (c) batch items touch disjoint files with no discernible shared relation axis; (d) a **shipped** item — one present in the commit's code diff AND named in a fresh `## Just shipped` entry — has no corresponding SPEC `- [ ]`→`- [x]` flip in the commit, so its checkbox is left `[ ]` though the work landed (SPEC↔TODO drift; in a branch-per-phase project a falsely-open `- [ ]` also blocks the §0/§7 phase-completion bail, which fires only when every `- [ ]` under the phase is `- [x]`). Case (d) most often bites items that live in a SPEC subsection away from the main phase list (e.g. a **Review follow-ups** block): the dev updates `## Just shipped` but overlooks the checkbox in the other block.

Do **not** file (a)–(c) for a single-item batch (trivially coherent) or when the multi-file reach is a uniform mechanical change (e.g. tagging the same frontmatter field in N SKILL.md files = one concept, one axis). **Case (d) is exempt from that exemption:** the shipped-but-unflipped check fires on a single-item commit too, and — because it keys on the code diff + `## Just shipped`, not on the stated batch — it is checked even when the dev emitted no `[batch-pick]` block (the `batch_pick_missing` / Just-shipped-proxy fallback path above). Confirm it directly: `git show HEAD -- docs/SPEC.md | grep '^\+.*\[x\]'` and check every shipped item appears among the flips; a `## Just shipped` entry with a code change but no matching `[x]` flip is drift.

### 2.10 Batch sizing

**Locating the iter MANIFEST is a mandatory first action of this axis — not a precondition you may judge as unmet before looking.** List `.skill-runs/` and locate the MANIFEST at `.skill-runs/<latest-run-dir>/MANIFEST.json` (flat) or `.skill-runs/<latest-run-dir>/iter_NN/MANIFEST.json` (looped run). Only if no MANIFEST file exists *after you have actually run the lookup* may you note "iter MANIFEST absent" in §6 and skip this axis; that §6 note is mandatory whenever the axis is skipped. Never report this axis as "nothing to flag" without having read a MANIFEST — an axis you did not attempt to run is not a clean axis.

**`"in_progress": true` on the iter MANIFEST is the normal mid-chain state, not a receipt gap.** The chain runner snapshot-writes each skill's record as that skill finishes, so by the time this review runs the dev's `skills[]` entry, including the `model_usage` token receipt this axis needs, is already present while the chain-level `in_progress` flag is still true (it stays true until after the auto-supervisor returns). Never skip the band check, or report the dev's receipt as unavailable, because the MANIFEST is `in_progress`: the only legal skip remains a MANIFEST file that does not exist on disk after the lookup actually ran. (Observed: a review that had already read an `in_progress` MANIFEST containing the dev's full `model_usage` reported the axis skipped for "no dev input_tokens receipt available", a fifth receipt form the §6 clause rules do not permit; the correct action was to sum `inputTokens + cacheCreationInputTokens` from the dev record it had already read.) The same snapshot semantics bind chain-state narration anywhere in your report, not just the band check: records for stages that run after this review (the auto-supervisor, and any stage the runner has not reached yet) are legitimately absent from `skills[]` while you read, because the review runs mid-chain. Never report the chain as "interrupted", "truncated", or "the supervisor never ran" from `in_progress` plus a missing later-stage record, including in free-form "worth surfacing" notes -- confine chain-state observations to what the MANIFEST positively records (a `rate_limit_pauses` entry, a `skill_failure` flag). (Observed: a review resuming after a mid-iter rate-limit pause surfaced "chain was interrupted; supervisor never ran" as fact in its report extras while the runner was still mid-flight driving the iteration, and folded a dev-emitted tester skip it had itself validated as legitimate two axes earlier into the same interruption narrative.)

**Do not infer MANIFEST absence from the run-directory name.** A `.skill-runs/<run-dir>` name carries the chain's *start* timestamp, not the commit time. In a `--loop N` run the iteration that produced HEAD commits minutes-to-hours after the chain started, so a run dir whose name predates the commit by hours is normal — it is **not** evidence that "the commit came from a wiped or manual run with no `.skill-runs/` entry." Never reason from run-dir-name-vs-commit-time at all. Identify the run positively instead: list the most recent `<run-dir>/` for `iter_NN/` subdirectories, then read the highest-numbered `iter_NN/MANIFEST.json`. **Treat `git_sha_before` as a confirmation, not a filter.** It records the commit the iteration STARTED from, which equals `git rev-parse HEAD~1` only when the dev produced exactly one commit — and the dev cycle is permitted a separate preparatory commit ahead of its cycle commit (its §0 dirty-tree carve-out), in which case `git_sha_before` matches `HEAD~2` or further back. So accept the highest-numbered `iter_NN/MANIFEST.json` whose `git_sha_before` is an ANCESTOR of HEAD (`git merge-base --is-ancestor <sha> HEAD`); if not even that matches, still use the highest-numbered `iter_NN/MANIFEST.json` and note the imprecise match in §6 rather than skipping the axis. Declare the MANIFEST absent only when no `MANIFEST.json` file exists on disk after the lookup ran — NEVER because a lookup found files but none matched `HEAD~1` exactly. (Observed: a dev committed a supervisor-left docs entry on its own before its cycle commit; the review enumerated every `iter_*/MANIFEST.json`, found none whose `git_sha_before` equalled `HEAD~1`, and reported `axis skipped: iter MANIFEST absent` for a file sitting on disk — silently dropping that iteration's batch-sizing datapoint from the supervisor's trailing-window aggregation.)

Read: `difficulty` (set by the runner's sentinel capture) and the dev skill's input tokens: sum `inputTokens + cacheCreationInputTokens` across all entries in its `model_usage` dict for **the dev skill only** (`skills[0]` — the first skill in the chain, the one that chose how much work to take on; `model_usage` is keyed by model name, not a flat dict; `cacheCreationInputTokens` measures tokens written to cache first-time — a proxy for peak context size; `cacheReadInputTokens` is a billing-centric cumulative that grows with session turns, not context complexity, and would inflate the total ~40× for long sessions). Do NOT sum review + supervisor tokens — those skills consume what they consume regardless of workload sizing; only the dev skill can act on its own window.

**A runner-fallback `difficulty` is not the pick: re-band on the commit's own items when the dev never declared a tier.** The MANIFEST `difficulty` field is authoritative for band selection only when it was captured from the dev's own emission (the `[picked-difficulty]` sentinel / `[batch-pick]` block). When the iter MANIFEST carries a `batch_pick_missing` flag, or its `difficulty_source` records a queue-top pre-parse (e.g. `todo-next-up`), the runner's value was parsed from the top of the queue BEFORE the dev picked, and an undeclared pick or batch can land on a different tier entirely; banding on the pre-parse then feeds a false-direction machine line into the supervisor's §3.5 aggregation (observed: a pre-parsed `[easy]` iter whose undeclared two-item batch had a `[hard]` primary; the ~254k actual reads `oversized` against the 100-200k easy band but is a legal below-band no-line state against the 400-500k hard band). In that case derive the tier from the commit itself: read the difficulty brackets of the SPEC IDs the commit closed (the same bracket-parsing fallback the batch-coherence axis uses), take the PRIMARY item's bracket (the leading SPEC ID in the commit subject, else the highest-tier item closed), band on that, and name the divergence in the §6 receipt (e.g. `manifest difficulty=easy (todo pre-parse), banded on primary=hard`). Tier ambiguity is never grounds to omit the receipt or skip the axis: resolve it by this rule and emit whatever the fire-rules produce.

**A retried or resumed dev record measures only its final attempt — add the earlier attempts back.** When the dev skill's MANIFEST record carries `retry_count > 0` (a rate-limit pause-and-resume, an overload retry, or a turn-ceiling chop), its `model_usage` holds the tokens of the LAST attempt alone, while the attempt that did most of the work survives only in its own transcript, `<i>_<dev-skill>.retry-<n>.txt`. Reading `skills[0]` by itself then under-measures the cycle by roughly the size of the discarded attempt. So whenever the DEV record's own `retry_count > 0`, read each retry transcript's closing per-model usage line, take `inputTokens + cacheCreationInputTokens` (the `in` and `cache-write` figures — never `cache-read`) from each, and add them to the MANIFEST figure before comparing against the band. **The gate is that record's own `retry_count`, NOT the bare presence of `.retry-<n>.txt` files in the iteration directory; those two conditions are not equivalent.** Every skill in the chain writes its retry siblings into the SAME directory, and the reviewer is the likeliest one to own them: a rate-limit pause on the review itself leaves `<i>_<review-skill>.retry-<n>.txt` on disk before the resumed attempt reaches this step, so an unscoped listing of the directory finds retry files on an iteration where the dev ran exactly once. Match on the dev's own transcript index (`<i>_<dev-skill>.retry-<n>.txt`), ignore every other skill's, and when the dev's record shows no retry, say `single-attempt` on the strength of that record rather than on a directory listing. Summing a sibling that is not the dev's charges another skill's cost to the dev's `actual=`, inflating it on the OVERSIZED side and feeding the supervisor's §3.5 aggregation the same false-`oversized` reading the sanity-check below exists to stop. Say in the §6 `Batch-sizing:` receipt that the number is a multi-attempt sum, so the supervisor's §3.5 aggregation can tell a summed reading from a single-attempt one. (Observed: a resumed cycle recorded 95k in `skills[0]` for a four-item `[medium]` batch whose working attempt cost a further 93k; the MANIFEST figure alone sits below the `[medium]` 100k undersize threshold and would have fired a false `undersized` line against a cycle that batched correctly and shipped all four items in one commit. Separately: a review resumed after a multi-hour pause listed the iteration directory's `*retry*` files unscoped, captioned the output "no retry files above = single attempt" on an iteration whose only retry siblings were its own, and happened to reach the correct single-attempt figure anyway; the probe it ran could not have established that, and the same probe on a genuinely retried dev cannot say which skill's siblings it found.)

**Sanity-check the computed `actual` against the band before you use it.** `cacheReadInputTokens` is the largest number in `model_usage` and summing it by reflex is the recurring failure mode here — it inflates `actual` roughly 40×, far past any real workload. So if your computed `actual` exceeds the difficulty's upper band edge by more than ~3× (e.g. an `[easy]` reading of 1500k or 2600k against a 200k edge), you almost certainly included `cacheReadInputTokens`; recompute as `inputTokens + cacheCreationInputTokens` only before deciding the finding or emitting the machine line. A genuine oversize is at most ~2-3× the edge; an order-of-magnitude overshoot is a measurement error, not a batch-sizing signal, and emitting it pollutes the supervisor's §3.5 trailing-window aggregation with a false `oversized` line.

Band edges by difficulty (dev-skill input-token targets — same values the dev skill uses for its own batch window-sizing; the `[batch-sizing]` finding fires on the dev's number, not the full-chain sum):
- `[easy]` → 100–200k; undersize threshold 50k (50% of lower edge)
- `[medium]` → 200–300k; undersize threshold 100k
- `[hard]` → 400–500k; undersize threshold 200k

Also read the `[batch-pick]` block's `window-target ~XXk`. **Verify the declaration is LICENSED, not that it sits inside the band.** The dev-cycle contract explicitly permits an out-of-band `window-target` in both directions, so a bare inside-the-band test reports compliant cycles as mismatches: a solo-forced pick declares the honest estimate for its one item even when that estimate falls below the tier's lower edge (naming which batch-eligibility bullet excluded the remaining candidates), and a work-shape carve-out documented in the dev skill's own batching prose may license a budget ABOVE the tier's upper edge, for a shape whose own floor consumes the whole band so that the honest number for a single item of it lands past the ceiling. So the check is: does the block cite an applicable clause, and does it satisfy that clause's conditions? A carve-out whose parts are inseparable (one that licenses the wider budget only for a SOLO pick) is not satisfied by an `N items` block where N > 1, and citing it there is a compliance finding in its own right. But a licensed out-of-band declaration is COMPLIANT: do not report it as a target-versus-band mismatch, and do not treat the tier band as evidence against it.

**When a carve-out is validly invoked, band the fire-rules below against the CARVE-OUT's declared budget rather than the tier table.** The tier band no longer describes what that cycle was authorized to spend, so comparing against it fires an `oversized` line at exactly the cost the carve-out predicts, and that line reaches the supervisor's §3.5 aggregation indistinguishable from genuine drift, where it can provoke a band-edge refinement against the very shape the carve-out was written to accommodate (the carve-out then reads as the cause of the drift it was authored to remove). Name the substituted band in the §6 receipt, e.g. `actual=<n>k vs carve-out budget <lo>-<hi>k (cited and satisfied; tier band <lo>-<hi>k) -> in-band, no line`, so the substitution is auditable and the supervisor can see which band the reading was taken against; the machine line, when one fires, still carries `band=` for whichever band the comparison actually used. A carve-out cited but NOT satisfied does not move the band: band on the tier, emit whatever the fire-rules then produce, and report the unmet condition separately. (Observed: a cycle validly invoked a lowest-tier carve-out that licenses a budget above that tier's ceiling for live-drive verification work, then came in under both the carve-out budget and the tier ceiling, and the review had to assert both "in-band against the tier band" and "the above-band declaration is licensed" in one report to reconcile this section against the dev's own contract; had that cycle instead landed where its carve-out predicts, this section as written would have emitted an `oversized` line against a fully compliant pick.)

**The substitution moves the CEILING only: the `undersized` side stays keyed on the tier band and its published threshold.** A carve-out licenses a cycle to spend more than its tier permits; it never obliges it to, so a reading that lands BELOW the carve-out budget is not an undershoot to be measured against that budget. Deriving the undersize threshold from the substituted band's lower edge (50% of it, as the tier table derives its own) raises the threshold along with the ceiling and fires `undersized` at a cycle sitting comfortably inside its tier band: the same false line reaching the supervisor's §3.5 aggregation that this paragraph exists to prevent, arriving from the other direction. So compare against the carve-out budget for the `oversized` rule, and against the tier band and its published undersize threshold for the `undersized` rule. A reading below the carve-out budget but inside the tier band fires nothing, and its receipt is the below-carve-out-in-tier-band form in §6. (Observed: a cycle validly invoked a carve-out licensing 220-250k against an `[easy]` 100-200k band and measured 171k. The review banded against the carve-out budget as instructed yet cited the TIER's 50k undersize threshold, which is the right answer and is not what this paragraph as written authorizes; the literal reading gives 110k, and the same carve-out with a 105k reading would then have fired `undersized` against a pick sitting inside its own tier band.)

**File a `[should-fix]` tagged `[batch-sizing]`** when:
- **Undersized**: actual input tokens < the undersize threshold AND the pre-commit queue (read from `git show HEAD -- docs/TODO.md | grep '^\-.*\[' | head -20`) offered ≥1 item of compatible difficulty + related concept that the dev did not batch.
- **Oversized**: actual input tokens exceed the upper band edge, OR MANIFEST records `terminated_by == "max_turns"`, OR the diff shows no SPEC `[x]` flips despite a stated batch pick (§6+§7 of the dev cycle did not land cleanly). **"Exceed" is judged at whole-`k` granularity, and an exact tie with an edge is INSIDE the band:** round the computed total to the nearest `k` and fire only when the rounded value lands strictly outside the rounded band. The machine line states both `actual` and the band edges in whole `k`, so that is the granularity the comparison is defined at; a raw total a few hundred tokens past an edge rounds ONTO it and is not an oversize. Firing there emits a line whose own numbers show no overshoot (`actual=200k band=100-200k`), which is the same self-contradictory receipt this section already rejects in the other direction, and it hands the supervisor's hard-counted M-total trigger a sub-0.1% measurement artifact as if it were signal. (Observed: a two-item `[easy]` batch that hit its declared ~180k window-target summed to 200,164 against the 200k upper edge; the review called it in-band, which was right, but nothing in this rule said it could.)

Include the actual token count, difficulty, and band edges in the finding text. The `[batch-sizing]` tag allows the supervisor to aggregate findings across iters and trigger window-target refinement.

Also emit a **machine-parseable summary line** to stdout immediately after deciding the finding (before §3), one line per direction found:

```
[batch-sizing] direction=<undersized|oversized> difficulty=<tier> actual=<n>k band=<lo>-<hi>k
```

This line is the supervisor's §3.5.1 extraction target and must appear as a standalone line in the transcript. If no batch-sizing finding fires this iter, do not emit the line -- and do NOT emit a tag-bearing substitute for it either. The literal `[batch-sizing]` token is the supervisor's grep key, so a no-fire receipt written as its own tagged transcript line registers as a phantom finding in the §3.5.1 trailing-window count and pushes the M-total trigger toward a refinement no measurement asked for (observed: a below-band no-fire iter emitted `[batch-sizing] no line: actual=177k vs medium band 200-300k, above the 100k undersize threshold` as a standalone line, so a mechanical any-position grep reads four findings in a window where three fired; that line's `undersize` prose also sits one character away from being mistaken for an `undersized` direction by the extraction's substring fallback). The receipt's only home is the tag-free §6 `Batch-sizing:` clause -- an in-band conclusion is still a COMPUTED conclusion: state the computed metric in your §6 report anyway (e.g. `batch-sizing: actual=245k vs band 200-300k -> in-band, no line`) so the number is auditable. A "within band" claim is compliant ONLY when it states BOTH the computed `actual=` value AND the band edges it was compared against, AND `actual` falls numerically inside that band: a receipt that quotes the actual but names no band has skipped the comparison (observed: a receipt quoting `actual=384k` declared a 200-300k-band iter "in-band"), one whose own `actual=` lies outside the band it names is self-contradictory, and a receipt with NO numbers at all -- a purely qualitative judgment ("single focused item -- in-band") -- is the same skipped comparison even when the review fetched the dev's token totals moments earlier (observed: a review pulled the dev's token footer expressly "for the batch-sizing receipt", then wrote "in-band" with neither `actual=` nor band edges on an iter whose true ~141k actual sat below its 200-300k band; fetching the numbers is not comparing them -- the receipt is compliant only when the computed `actual=` appears in it) -- in all three cases re-run the comparison and emit whatever the fire-rules above actually produce: an `oversized` machine line when `actual` exceeds the upper edge; an `undersized` machine line ONLY when the undersized rule holds (`actual` below the undersize threshold, plus the unbatched-queue condition); and NO machine line when `actual` lies below the lower edge but at-or-above the undersize threshold -- that below-band gap is a legal no-line state (the band table's undersize thresholds define it) and takes the below-band receipt form in §6, NOT the `in-band` wording and NOT a fabricated `undersized` line (a machine line emitted outside the fire-rules feeds a false direction into the supervisor's §3.5 trailing-window aggregation). Eyeballing the diff's apparent size instead of comparing the summed MANIFEST metric against the band edges produces a silent false-negative (a missing `oversized` line breaks the supervisor's §3.5 same-direction streak) exactly as damaging as the false-`oversized` inflation the sanity-check above guards against.

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

**"I cannot verify this from here" is a FUTURE-WORK trigger, not a reason to withhold the finding.** The signs above are all shapes of the FIX; a reviewer's own epistemic position is the other admission route into FUTURE-WORK.md, and it is the one that gets misread. When you have MEASURED a real, newly-introduced hazard but the fact that would settle it lives outside anything you can read from here (a target environment's installed packages, a runtime the cycle never boots, a service or machine you have no access to), filing a *fix* would indeed presume the answer, so file the *check*: one FUTURE-WORK line naming the measurement you did make, the unknown that decides it, and what breaks in each branch of that unknown. Withholding it is not the conservative option. Your §6 report is consumed once by whoever reads it next and is not a queue anyone can return to, so an evidenced hazard recorded only there has no address; the same sentences under `## Manual / human verification` persist until someone can answer them. Then check separately whether the hazard has a half that needs no unknown resolved, typically a guard the changed file already applies to an adjacent case, and route that half to spec + `## Next up` as ordinary autonomous work. (Observed: a review measured that two tests its cycle had just promoted onto a merge-blocking CI gate import a package that gate's environment never installs, declined to file on the grounds that "I cannot inspect that environment, so filing it would invent a requirement", and left the entire hazard in its close note, including the half that was a missing import-error skip guard the same file already used for the adjacent optional dependency.)

**Spec.** Open the project's spec file (same one `/sst-dev-cycle` updates). Under the phase this review is reviewing (the shipped pick's phase), append a **Review follow-ups** subsection. Format:

```markdown
**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [ ] <phase>.<n> [<difficulty>] [blocker] `<file>:<line>` — <one-sentence description>. Proposed fix: <short hint>.
- [ ] <phase>.<n> [<difficulty>] [should-fix] `<file>:<function>` — <one-sentence description>. Proposed fix: <short hint>.
```

Rules:

- Every entry MUST start with a stable `<phase>.<n>` sub-item ID immediately after the checkbox, then the difficulty bracket, then the severity bracket. **`<phase>` is the phase being reviewed** — the shipped pick's `<phase>.<n>` from `## Just shipped`, the `[batch-pick]` block, or the SPEC `[x]` flips in the cycle commit. File the follow-up under that phase's section. Pick the next unused `<n>` in THAT phase only (gaps from closed items are valid — do not renumber). Do NOT allocate IDs from a different phase's sequence just because a global Review follow-ups dump historically used it, and do NOT re-home this review's leftovers onto another phase. A same-phase batch stays that phase. If the cycle shipped mixed-phase IDs, file each finding under the phase of the item it relates to; default to the primary pick. If the pick has no `<phase>.<n>` ID, file free-form (no new ID) rather than guessing another phase's next-n. `bin/validate-frontmatter.py` rejects any checkbox bullet in `docs/SPEC.md` that lacks this ID in the correct position, so a missing or mis-ordered ID is a CI failure. Run the validator **bare** to exercise that check: `python bin/validate-frontmatter.py` with no path arguments scans `docs/SPEC.md` (plus `docs/TODO.md`) on fixed repo paths. If `bin/validate-frontmatter.py` is absent (not every consuming project vendors the script), skip the validator step instead of re-probing interpreters or paths: a missing-file exit (127 from a missing interpreter, 2 from a missing script) means the project has no CI frontmatter gate to satisfy, not that your spec edit broke validation. Do NOT pass `docs/SPEC.md` or `docs/TODO.md` as path arguments; positional args are validated as `SKILL.md` frontmatter, so a doc path there fails the SKILL schema and exits 2. That is a spurious failure that looks like your spec edit broke validation when only the invocation was wrong. Difficulty is one of `[easy]` / `[medium]` / `[hard]` per the SPEC.md "Difficulty labels" appendix; the project's chain runner pre-parses it to route the next cycle's skills (`effective = max(item_tier, skill_floor)` per axis). Closed `[x]` items don't carry the label (historical).
- Only `[blocker]` and `[should-fix]` severities go here. No nice-to-have / nitpick / cosmetic items — if you can't justify why it causes a real bug, security risk, or major confusion, don't file it.
- One checkbox per finding; do not bundle. A later `/sst-dev-cycle` will pick the top unchecked item (or a bundled chunk, if it uses a chunk-sizing rule).
- Order by severity (blocker → should-fix), then by file/line. Difficulty is independent of severity and does not affect ordering.
- If a finding also affects another sub-section or module, still file it under the **phase being reviewed** (the one this review targets), not an older or catch-all phase. Chronological work through the spec does not license dumping leftovers onto a different phase's ID sequence.
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

**Commit-message rule (read BEFORE composing the heredoc):** never append a `Co-Authored-By: Claude ... <noreply@anthropic.com>` trailer (or any AI-coauthor trailer variant — Cursor, Claude Code, or any other agent identity). Do NOT pass `git commit --trailer ...` either: the `--trailer` flag is the same ban, not a loophole around the heredoc. The heredoc body below ends at `EOF` — nothing else goes after the closing paragraph. Empirical: placement-below-heredoc was being skipped by models reading top-down, so the rule lives ABOVE the template now; a later Cursor-harness cycle then reintroduced the trailer via `--trailer "Co-authored-by: Cursor ..."` while keeping the heredoc clean. The `git commit` invocation is exactly the template below — no extra flags.

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

> Reviewed commit `<sha>` (`<scope>: <summary>`). Checked all review axes (parity, correctness, coverage, docs, prod-verify, security, style, performance). No substantive findings at the blocker or should-fix bar. Spec unchanged. Tester: <green|skipped|degraded|red> (<n> checks). Batch-sizing: <actual=<n>k vs band <lo>-<hi>k -> in-band, no line | actual=<n>k vs band <lo>-<hi>k -> below band, above undersize threshold (<t>k), no line | actual=<n>k vs band <lo>-<hi>k -> below undersize threshold (<t>k), unbatched-queue condition not met, no line | line emitted: direction=<dir> actual=<n>k band=<lo>-<hi>k | axis skipped: iter MANIFEST absent>.

**With findings:**

> Reviewed commit `<sha>` (`<scope>: <summary>`). Found <N> items: <B> blocker, <S> should-fix. Appended a "Review follow-ups" block under `<section>` in the spec and committed as `<review-sha>`. Highest-impact: <one-line description of the worst item>. Tester: <green|skipped|degraded|red> (<n> checks). Batch-sizing: <actual=<n>k vs band <lo>-<hi>k -> in-band, no line | actual=<n>k vs band <lo>-<hi>k -> below band, above undersize threshold (<t>k), no line | actual=<n>k vs band <lo>-<hi>k -> below undersize threshold (<t>k), unbatched-queue condition not met, no line | line emitted: direction=<dir> actual=<n>k band=<lo>-<hi>k | axis skipped: iter MANIFEST absent>.

The `Found <N> items: <B> blocker, <S> should-fix.` clause is machine-parsed, not prose: the supervisor's fast-path (`sst-supervisor` §0.5 condition #3) anchors on the exact string `Found <N> items:` to detect a findings-filing review. Emit it verbatim: plural `items:` even when N=1, digits not words, and no markdown emphasis inside the clause (bold like `Found **1 item: ...**` breaks the anchor). When another clause of the template does not apply (e.g. the spec docs are untracked, so there is no `<review-sha>` to cite), adapt THAT clause ("filed on disk; no commit needed") and keep this one intact. A findings-filing review that paraphrases the clause (`Found 1 blocker.`, `Verdict: 3 should-fix filed`) can be mislabeled `clean (fast-path)` by the supervisor, silently dropping its findings from oversight. The clause belongs to the **With findings** form ONLY: a clean review (zero items after the bar) uses the Clean form and MUST NOT emit a zero-count variant (`Found 0 items: 0 blocker, 0 should-fix`), because the supervisor treats a `Found <N> items:` match as a findings-filing signal and a zero-count emission forces a needless deep walk on exactly the clean iterations its fast-path exists to skip.

`Tester:` line rules: use `skipped` when findings are absent or `verdict: skipped`; `green` when `verdict: green`; `degraded` when `verdict: degraded`; `red` when `verdict: red`. Include the check count from `checks[]` when the file is present (`0` when skipped/absent). When tester files are absent, emit `Tester: skipped (0 checks)` so the supervisor can track tester coverage across iterations.

`Batch-sizing:` clause rules: this clause is the §2.10 axis's mandatory receipt and appears in EVERY report, both forms. Exactly one of: the computed in-band statement (`actual=<n>k vs band <lo>-<hi>k -> in-band, no line`), the below-band no-line statement (`actual=<n>k vs band <lo>-<hi>k -> below band, above undersize threshold (<t>k), no line`) for the legal gap state where `actual` sits below the band's lower edge but at-or-above the difficulty's undersize threshold (§2.10's undersized finding does not fire there, so there is no machine line to repeat -- and the `in-band` wording would be self-contradictory), the below-threshold-no-fire statement (`actual=<n>k vs band <lo>-<hi>k -> below undersize threshold (<t>k), unbatched-queue condition not met, no line`), the carve-out statement in one of three shapes, for a cycle whose `[batch-pick]` cited a work-shape carve-out this review found SATISFIED (§2.10): `actual=<n>k vs carve-out budget <lo>-<hi>k (cited and satisfied; tier band <lo>-<hi>k) -> in-band, no line` when the reading sits inside the substituted budget, `actual=<n>k vs carve-out budget <lo>-<hi>k (cited and satisfied; tier band <lo>-<hi>k) -> below carve-out budget, inside tier band, no line` when it came in under that budget while still inside its tier band (§2.10's substitution moves the ceiling only, so the undersized rule reads the tier band and nothing fires), or `actual=<n>k vs carve-out budget <lo>-<hi>k (cited and satisfied; tier band <lo>-<hi>k) -> below carve-out budget, below tier band, above undersize threshold (<t>k), no line` when it came in under BOTH the budget and the tier band's lower edge while still at-or-above the tier's undersize threshold -- a carve-out whose budget sits ABOVE the tier band makes this the shape an under-delivery takes, and the two alternatives are both wrong: the `inside tier band` shape asserts a relation that is false, and the plain below-band form states the numbers exactly while silently discarding the fact that a carve-out was cited and found satisfied, which is the one thing the carve-out shapes exist to record (observed: a `[medium]` cycle cited a work-shape carve-out this review found satisfied, then measured 179k against a 200-300k tier band whose undersize threshold is 100k and a 220-250k carve-out budget -- below BOTH the budget and the band's lower edge -- and the review had to hand-write a receipt outside the enumeration, flagging in its own report extras that it had done so), a repeat of the machine line's values when a finding fired this run (`line emitted: direction=<dir> actual=<n>k band=<lo>-<hi>k`), or `axis skipped: iter MANIFEST absent` (legal only after the §2.10 MANIFEST lookup actually ran and found no file).

The below-threshold-no-fire form covers the state §2.10's undersized rule creates by being a CONJUNCTION: `actual` sits below the difficulty's undersize threshold, but the pre-commit queue offered no item of compatible difficulty AND related concept to batch, so the `undersized` line must not fire. Neither of the other no-line forms is available there (`in-band` is false, and the below-band-above-threshold form asserts a threshold relation that is also false), so this is the form to use rather than inventing one or forcing a wrong one. A pick that ships alone because nothing was batch-eligible is a legitimate cycle even when it lands under its tier's floor, and pushing it into the `in-band` slot is the silent false-negative that starves the supervisor's §3.5 trailing window (the same class of receipt error §2.10 rejects in the other direction). When the dev's `[batch-pick]` rationale names which eligibility bullet excluded the remaining candidates, repeat that reason here in a few words so the undershoot reads as forced rather than as under-packing; when the dev emitted no `[batch-pick]` block at all (the `batch_pick_missing` fallback path), say the reason was unavailable rather than inferring one. (Observed: a `[hard]` cycle measured 176k against a 400-500k band with a 200k undersize threshold, and its only compatible queue item was blocked by a stated dependency on the shipped one, so no `undersized` line could fire; the review had to hand-write a receipt outside the four then-permitted forms, having correctly refused to force it into either of the two no-line ones.)

A report with no `Batch-sizing:` clause means the axis was silently skipped — the exact false-negative §2.10 warns about: the missing `undersized`/`oversized` machine line breaks the supervisor's §3.5 trailing-window aggregation, and without this receipt slot the omission is invisible because the rest of the report reads complete.

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
