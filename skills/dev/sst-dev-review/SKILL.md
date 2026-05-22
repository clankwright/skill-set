---
name: sst-dev-review
description: Post-cycle second-pass review of the last `/sst-dev-cycle` commit on any project. Reads what shipped (code + tests + spec + TODO + docs), evaluates it against the spec item it closed along several axes (spec parity, correctness, coverage, discoverability, production verification, security, style, performance), and appends concrete follow-up items to the project's spec AND the handoff TODO's "Next up" if critical, blocking, or medium-to-major gaps are found. If nothing substantive turns up, leaves both unchanged and reports "clean." Does NOT fix issues — only names them and schedules them as spec work for the next `/sst-dev-cycle`. Pair with `/sst-dev-cycle` (chained via `bin/skill-chain.py sst-dev-cycle sst-dev-review`).
user-invocable: true
version: 1.5.2
model-floor: sonnet
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

This skill reads `docs/SPEC.md`, `docs/TODO.md`, `docs/FUTURE-WORK.md`, and `docs/HUMAN.md` (all if present) end-to-end on open. It may write to `docs/SPEC.md`, `docs/TODO.md`, `docs/FUTURE-WORK.md`, and `docs/HUMAN.md` on close (under §4). Severity bar and process are unchanged from the rest of this skill; the only addition is that every blocker/should-fix you file in the spec also gets mirrored as a one-line entry in `TODO.md`'s `## Next up` so the next `/sst-dev-cycle` picks it up without re-scanning the spec. Both files commit together in §5 if anything was added.

**Spec sub-item IDs.** Every `- [ ]` item in `docs/SPEC.md` carries a stable ID of the form `<phase>.<n>` before the difficulty bracket (e.g. `- [ ] 3.1 [hard] **description**`). IDs are assigned once and never renumbered — gaps from closed/removed items are valid. When filing follow-ups to `## Next up` in §4, prefer citing the SPEC item by its ID (e.g. `reason: spec 3.1`) over "Phase 3 sub-item" for durability.

## 0. Pre-flight

1. Working directory is the project root (same repo as the commit you're reviewing). Activate any language environment the project uses.
2. Git state check: **note and proceed**. Run `git status --porcelain` and capture the output verbatim. The review runs against the just-shipped cycle commit (HEAD by default, or the cumulative surface when the cycle shipped >1 commit) regardless of working-tree dirt; the dirt is captured as a "Working-tree state at review start" note in the §6 report and (when §4 fires) in the §5 commit body, then ignored. Rationale: the project's supervisor (when the project runs `sst-supervisor` or a `<project>-supervisor` proprietary counterpart) routinely leaves direct-overwritten edits to peer SKILL.md files uncommitted in `<cwd>/.claude/skills/*/` as its contract; parallel agent sessions and the user's own concurrent edits can also legitimately touch project source while a review runs. Halting on either case wastes the cycle's commit and forces the user to babysit the working tree. Concrete rules:
   - Capture the porcelain output. If non-empty, surface it as the "Working-tree state at review start" note in the §6 report and (when §4 fires) include it in the §5 commit body. Surfacing what wasn't part of the just-shipped commit is the value-add; reviewer-side rather than dev-side because the dev cycle has already committed (and pushed) by the time the review starts.
   - Do NOT stash, checkout, or modify any of the dirty files. They are out-of-scope for the review.
   - The §5 stage-narrowly rule is the structural guard: stage only the spec file (plus `docs/TODO.md` if a Next-up entry was added, plus `docs/FUTURE-WORK.md` if §4 routed findings there), never `git add -A` or `git add .`. Working-tree dirt cannot accidentally ride into the review commit if §5 is followed.
   - One exception still halts: if a dirty file is the spec file itself, `docs/TODO.md`, `docs/FUTURE-WORK.md`, or `docs/HUMAN.md` (the four files this skill writes to in §4), stop. Concurrent writers on the same files is the one collision the note-and-proceed pattern doesn't survive; surface to the user and exit.
3. Read `docs/SPEC.md` and `docs/TODO.md` end-to-end. The spec tells you what the cycle claimed to close; `TODO.md`'s `## Just shipped` confirms the cycle's own self-reported summary (no SHA in that format — a commit cannot contain its own hash; correlate the top Just-shipped line to HEAD, or to the matching commit via `git log --oneline --grep`).
4. Identify the commit under review:
   ```bash
   git log -1 --format='%H %s'
   ```
   If that commit is a skill edit, a docs-only commit, a merge, or otherwise **not** a real dev cycle, walk backward with `git log --format='%H %s' -20` until you find the last real `/sst-dev-cycle` commit. Common scope tags the cycle uses: `Auth:`, `UI:`, `Docs:`, `Tests:`, `Deploy:`, `Infra:`, or a feature-area tag. Review **that** commit — do not review skill/docs-only commits.

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

*(Applies when the dev cycle used the batching protocol — the dev skill emits a `[batch-pick]` block to stdout before its first tool call.)*

**Find the `[batch-pick]` block** in the dev transcript (most recent `.skill-runs/*/iter_NN/00_<dev-skill>.txt` or `.skill-runs/*/00_<dev-skill>.txt`). If no log exists, fall back to the `## Just shipped` top entries in `docs/TODO.md` as a proxy.

Parse the block's stated items and compare against the actual commit:

- `git show HEAD -- docs/SPEC.md | grep '^\+.*\[x\]'` — each `[x]` flip should correspond to a stated batch item (no extra flips, no missing flips).
- `## Just shipped` additions in the diff — each stated item should have a corresponding entry.
- `git show HEAD --stat` — files touched should be explained by the batch items; two or more items that touch disjoint files with no shared SPEC phase, concept, or mechanical pattern signal incoherent bundling.

**File a `[should-fix]` tagged `[batch-coherence]`** when any of: (a) a stated item has no `[x]` flip and no Just-shipped entry; (b) the diff contains `[x]` flips absent from the stated batch; (c) batch items touch disjoint files with no discernible shared relation axis.

Do **not** file for a single-item batch (trivially coherent) or when the multi-file reach is a uniform mechanical change (e.g. tagging the same frontmatter field in N SKILL.md files = one concept, one axis).

### 2.10 Batch sizing

*(Applies when the iter MANIFEST is available. If absent, note it in §6 and skip this axis.)*

Locate the MANIFEST at `.skill-runs/<latest-run-dir>/MANIFEST.json` (flat) or `.skill-runs/<latest-run-dir>/iter_NN/MANIFEST.json` (looped run). Read: `difficulty` (set by the runner's sentinel capture) and the dev skill's input tokens: sum `inputTokens + cacheCreationInputTokens` across all entries in its `model_usage` dict for **the dev skill only** (`skills[0]` — the first skill in the chain, the one that chose how much work to take on; `model_usage` is keyed by model name, not a flat dict; `cacheCreationInputTokens` measures tokens written to cache first-time — a proxy for peak context size; `cacheReadInputTokens` is a billing-centric cumulative that grows with session turns, not context complexity, and would inflate the total ~40× for long sessions). Do NOT sum review + supervisor tokens — those skills consume what they consume regardless of workload sizing; only the dev skill can act on its own window.

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

This line is the supervisor's §3.5.1 extraction target and must appear as a standalone line in the transcript. If no batch-sizing finding fires this iter, do not emit the line.

## 3. Decide on output

Count findings after you've applied the "no nitpicks" bar.

- **Zero findings after the bar**: the cycle was clean. Skip step 4. Go to step 5 and report clean.
- **At least one should-fix or blocker**: go to step 4, append to spec, commit.

A clean report with no findings is a success signal, not a failure to find work. Don't pad.

## 4. Append follow-ups to the spec + TODO.md

**Route first: three destinations.** Before filing any finding, decide the destination:

- **`docs/HUMAN.md`** (human-only blocker findings): findings whose proposed fix requires a human action the cycle cannot perform — writing a secret outside the repo, granting access in a third-party UI, signing a legal agreement, or anything that inherently requires out-of-band credentials. Append under `## Blocking` (cycle-stopping) or `## High` (non-blocking prerequisite) per the schema in `docs/HUMAN.md`. APPEND only; never close an existing entry. Do NOT also mirror to spec or `## Next up`.
- **`docs/FUTURE-WORK.md`** (acceptance and smoke-test findings only): findings whose resolution requires a real chain-driver round-trip, Telegram message exchange, human-verified end-to-end smoke, or any check the dev cycle cannot perform autonomously from inside its own iteration. Append under `## Manual / human verification > ### <Phase context>` (create the sub-section if absent). One line per finding. Do NOT also mirror to spec or `## Next up` — these items sit in FUTURE-WORK.md until a human flips them back when external verification is ready.
- **Spec + `docs/TODO.md`** (all other findings): code corrections, prose edits, schema additions, contract clarifications — work a future dev cycle can execute autonomously. File in the spec and mirror to `## Next up` per the rules below.

Signs a finding belongs in HUMAN.md: the proposed fix is "set a secret", "grant access", "sign an agreement", or anything that requires a human with external credentials. Signs it belongs in FUTURE-WORK.md: the proposed fix is "run an acceptance test", "verify via a Telegram bot", "confirm with a live chain-driver run", "observe in production", or "exercise end-to-end by hand" — any fix the dev cycle cannot self-verify from inside the chain. Signs it belongs in spec + TODO: the proposed fix is a code change, a prose edit, a schema addition, or any other autonomous development task.

**Spec.** Open the project's spec file (same one `/sst-dev-cycle` updates). Under the sub-section the cycle touched, append a **Review follow-ups** subsection. Format:

```markdown
**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [ ] [<difficulty>] [blocker] `<file>:<line>` — <one-sentence description>. Proposed fix: <short hint>.
- [ ] [<difficulty>] [should-fix] `<file>:<function>` — <one-sentence description>. Proposed fix: <short hint>.
```

Rules:

- Every entry MUST carry a difficulty label as the leading bracket immediately after the checkbox, with the severity bracket second. Difficulty is one of `[easy]` / `[medium]` / `[hard]` per the SPEC.md "Difficulty labels" appendix; the project's chain runner pre-parses it to route the next cycle's skills (`effective = max(item_tier, skill_floor)` per axis). Closed `[x]` items don't carry the label (historical).
- Only `[blocker]` and `[should-fix]` severities go here. No nice-to-have / nitpick / cosmetic items — if you can't justify why it causes a real bug, security risk, or major confusion, don't file it.
- One checkbox per finding; do not bundle. A later `/sst-dev-cycle` will pick the top unchecked item (or a bundled chunk, if it uses a chunk-sizing rule).
- Order by severity (blocker → should-fix), then by file/line. Difficulty is independent of severity and does not affect ordering.
- If a finding also affects another sub-section or module, put the follow-up under the **most recent** sub-section (the one this review targets), not the older one. The idea is to work chronologically through the spec.
- Do not move any existing `[x]` box to `[ ]`. If a previously-claimed item turns out to be incomplete, that is a **new** follow-up line, not a regression edit.

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
git add <spec-file> docs/TODO.md docs/FUTURE-WORK.md docs/HUMAN.md  # TODO.md only if you wrote a Next-up entry; FUTURE-WORK.md only if §4 routed findings there; HUMAN.md only if §4 appended a human-only blocker; plus any status-index file you corrected
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

> Reviewed commit `<sha>` (`<scope>: <summary>`). Checked all review axes (parity, correctness, coverage, docs, prod-verify, security, style, performance). No substantive findings at the blocker or should-fix bar. Spec unchanged.

**With findings:**

> Reviewed commit `<sha>` (`<scope>: <summary>`). Found <N> items: <B> blocker, <S> should-fix. Appended a "Review follow-ups" block under `<section>` in the spec and committed as `<review-sha>`. Highest-impact: <one-line description of the worst item>.

## Pitfalls to avoid

- **Re-running the full test suite is fine but not the point.** A green suite doesn't prove the feature is complete, because the tests were written alongside the feature. Your job is to find what the tests forgot to check.
- **Don't grep for generic keywords and call it review.** "I searched for `TODO`" is not review. Read the actual diff line by line.
- **Don't invent requirements not in the spec.** If the spec said "format + MX only" and the code does exactly that, not adding an SMTP probe is a feature, not a gap. If the *spec* missed something obvious, that is a spec-level finding (propose a new spec bullet), not an implementation bug.
- **Don't double-count.** If one root cause surfaces in three places, file one finding.
- **Don't escalate style to blocker.** A magic number in test-only code is not worth flagging at all under the severity bar — skip it.
- **Don't pad the review.** If after honest examination you have zero blocker/should-fix items, report clean and stop. A zero-item or one-item review is a success signal. Nitpicks, stylistic preferences, cosmetic doc polish, minor duplication, and comment wording never go in the follow-ups.
- **Don't review the review.** When you're done with the findings list, stop.
- **Don't touch the working tree to "compare against HEAD~1."** Never `git checkout HEAD~1 -- .`, never chain `git stash` with `git checkout` of the prior commit. Either pattern can clobber the working tree (including a freshly popped stash) and require `git fsck --lost-found` to recover. Any prior-state inspection should use `git show HEAD~1 -- <path>` (read-only, doesn't touch the tree) or a separate worktree (`git worktree add /tmp/review-prev HEAD~1`, then remove when done).
