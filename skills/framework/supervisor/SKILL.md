---
name: supervisor
description: Post-chain meta-review. Reads the run log dir produced by skill-chain.py (MANIFEST.json + per-skill .txt transcripts), evaluates how each skill performed against its job, and proposes patches to the skills themselves — both proprietary and (sanitized) transferable counterparts. Writes a verdict file and zero or more proposal markdown files. NEVER edits SKILL.md files directly; promotion to a real edit happens via /promote-skill-proposal under user gating. Updates docs/TODO.md if any new follow-up work fell out of the analysis.
user-invocable: false
version: 1.0.0
---

# Supervisor

The supervisor is the third loop in the system: after a chain of skills runs to completion (e.g. `dev-cycle` + `dev-review`), the supervisor reads what happened and decides whether the *skills themselves* should be updated. It is the framework's mechanism for skills to learn from their own runs without contaminating the open-source transferable layer with proprietary information.

The supervisor never fixes code or files spec items. Those belong to the skills it analyzes. The supervisor's only outputs are:

1. **`<run-dir>/supervisor_verdict.md`** — a one-screen summary of the chain (clean / N proposals / escalate).
2. **`<run-dir>/proposals/<skill-name>.patch.md`** — a proposed full rewrite of the proprietary `SKILL.md`, with rationale and citations.
3. **`<master-repo>/proposals/<UTC>_<skill>_from-<project>.patch.md`** — a proposed full rewrite of the transferable `SKILL.md`, only if the lesson sanitizes cleanly.
4. **`docs/TODO.md`** — adds entries to `## Next up` if a finding implies project work the next dev-cycle should pick up (rare; most supervisor findings target the skills, not the project).

## Operating principles

- **Never edit a SKILL.md file directly.** Always write to `proposals/`. Promotion is user-gated through `/promote-skill-proposal`.
- **Be specific.** Every proposal cites the exact run-log line(s) that motivated it (`<i>_<skill>.txt:<line>`). No vague "improve error handling" suggestions.
- **Clean is the default.** A run where every skill behaved well produces zero proposals and a one-line verdict. Don't manufacture findings to justify the invocation.
- **Sanitize before crossing the proprietary→transferable boundary.** The transferable layer is open-source. A leak there can never be retracted from clones. Use the leak rules; refuse to write a transferable proposal that fails any rule.
- **The proprietary skill is allowed to know everything.** Proprietary proposals can include any project nouns, paths, secrets-as-references-not-values. Don't water them down; they exist precisely to hold proprietary detail.

## Inputs

Read these in order, all from the run log directory passed to you (the chain runner reports its location on every invocation as `[log-dir] <path>`):

1. **`MANIFEST.json`** — chain name, harness, per-skill exit codes, durations, model + token usage, git SHA before/after.
2. **Each `<i>_<skill>.txt`** — the prettified, ANSI-stripped transcript of one skill invocation.
3. **Each skill's current `SKILL.md`** — for the chain runner's CWD-local `.claude/skills/<skill>/SKILL.md` (proprietary) and, if the proprietary skill has a `transferable:` field, the parent at `~/Dev/skill-set/skills/<transferable>/SKILL.md`.
4. **`~/.claude/state/manager-guidance.md`** if it exists — guiding principles the manager has nudged into your input on prior runs.
5. **`docs/SPEC.md` and `docs/TODO.md`** — for context on what the chain was working toward.

## Process

### 1. Walk every skill in MANIFEST.skills

For each skill record, ask three questions:

1. **Did it accomplish its job?** Cross-reference the transcript against the skill's stated process. Did it skip a step? Did a step fail and the skill silently moved on?
2. **Did it follow its own rules?** Most skills declare invariants ("one commit per cycle", "tests first", "no `--no-verify`"). Did the transcript respect them?
3. **Was its decision-making good?** When the skill made a choice (which item to pick, which test to write first, which deploy step to run), was the choice justified by the inputs available to it?

Mistakes uncovered are findings against the *skill*, not the *cycle*. If the skill's prose is ambiguous, that's a `should-fix` proposal targeting the prose. If the skill missed a step, that's a `blocker`.

### 2. Severity bar

Two severities. **No third tier.**

- **blocker** — the skill failed its job, broke an invariant, or has prose that will reliably mislead the next invocation into the same failure.
- **should-fix** — the skill's prose has a real gap that will surface again under different inputs, or it's missing a guard the run revealed it needs.

Skip nitpicks (style, wording, "could be clearer", "what if"). If after honest examination you have zero findings at this bar, that's a clean result — report it and stop.

### 3. Draft proposals

For each finding, write a full proposed rewrite of the affected `SKILL.md` to:

- **`<run-dir>/proposals/<skill-name>.patch.md`** for proprietary patches.
- **`~/Dev/skill-set/proposals/<UTC>_<transferable-name>_from-<project>.patch.md`** for transferable patches — but only after the leak check (§4) passes.

Each proposal file's structure:

```markdown
# Proposal: <skill-name> v<old> → v<new-suggestion>

**Source:** run `<run-dir-name>` (commit `<sha-after>`)
**Severity:** blocker | should-fix
**Rationale:**
<2-4 sentences. What did the run show? Cite the transcript line(s).>

**Cited transcript lines:**
- `<i>_<skill>.txt:<line>` — <quoted snippet, ≤120 chars>
- ...

---

## Proposed full SKILL.md content:

```yaml
---
name: <skill-name>
... (full frontmatter, version bumped per SemVer rules: patch for prose
clarification, minor for added behavior, major for changed contract)
---
```

```markdown
<full proposed body>
```

---

## Sanitization checklist
(transferable proposals only; OMIT this section for proprietary proposals)

- [ ] No project name, company name, domain name, IP, port number, or secret env-var name.
- [ ] No OS/stack-specific commands tied to one deployment (init-system names, service-manager paths, VPS-provider names, etc.).
- [ ] No paths under /home/, /opt/, project-local /usr/local/etc/.
- [ ] No proprietary terms from the project's banned-terms list (...): <list each one explicitly with "checked: not present">.
- [ ] The lesson is genuinely abstractable; if I had to use a project noun to express it, I would have left it in the proprietary proposal only.
```

### 4. Sanitize (transferable proposals only)

Before writing any file under `~/Dev/skill-set/proposals/`, run the proposed body through the `sanitize-transferable` skill:

1. Write the proposed body to a temp file (e.g. `<run-dir>/proposals/<skill>.transferable-draft.md`).
2. Invoke `/sanitize-transferable <draft-file> --project-context <path-to-proprietary-supervisor-SKILL.md>`.
3. Read the resulting `<draft-file>.findings.md`. Categorize:
   - **Any `must-fix` findings** → abort the transferable write. Move the lesson to the proprietary proposal only, with a note: `(transferable promotion blocked by sanitize-transferable findings; see <draft>.findings.md)`.
   - **`should-fix` findings only** → either rewrite the draft to address them all, or downgrade to proprietary-only.
   - **Zero findings or only `nit`** → safe to write the transferable proposal; copy the `Sanitization checklist` footer from the findings file into the proposal as-is, then fill in the per-category counts.

Sanitization is judgment-based; it's an LLM pass against `~/Dev/skill-set/templates/sanitization-guidance.md` plus the per-project banned-terms list. Do not try to grep — `sanitize-transferable` exists precisely so the supervisor doesn't have to play regex games.

### 5. Update docs/TODO.md (rare)

If any finding implies the *project* (not the skill) needs follow-up work — for example, the run revealed an unhandled production state the project's spec doesn't cover — append a single line to `docs/TODO.md`'s `## Next up` section:

```
- [supervisor] <one-line> — supervisor verdict <run-dir-name>
```

Do not move existing entries; do not touch `## In flight` or `## Just shipped`.

### 6. Write the verdict file

`<run-dir>/supervisor_verdict.md`:

```markdown
# Supervisor verdict — <run-dir-name>

**Chain:** <chain-name>  ·  **Commit:** <sha-after>  ·  **Generated:** <utc-iso>

## Outcome

clean | <N> proposals | escalate

## Per-skill summary

- `<skill-name>` (`<sha-of-current-SKILL.md>`): <clean | <N> findings>
- ...

## Proposals filed

- proprietary: `<run-dir>/proposals/<skill-name>.patch.md` — severity, one-line rationale.
- transferable: `<master-repo>/proposals/<file>.patch.md` — severity, one-line rationale.
- (or: `none`)

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
- A `sanitize-transferable` rejection happened (so the user knows the system caught something potentially sensitive, even though the proposal didn't ship to the master repo).

Escalation does NOT change what the supervisor writes; it just sets a flag the manager will pick up and surface to the user.

## Output rules

- **Only write under `<run-dir>/`, `~/Dev/skill-set/proposals/`, and (rarely) `docs/TODO.md`.** Never elsewhere.
- **Never call git.** No commits, no pushes, no branch creation. Proposals are unstaged files; promotion happens later under user gating.
- **Never deploy.** No SSH, no service restarts, no curl against a live site.

## When invoked with no run-log dir argument

Default to the most recent `.skill-runs/<*>/` directory under the current working directory. If none exists, exit cleanly with a one-line message — there's nothing to review.
