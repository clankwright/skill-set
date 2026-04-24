---
name: sst-supervisor
description: Post-chain meta-review. Reads the run log dir produced by skill-chain.py (MANIFEST.json + per-skill .txt transcripts), evaluates how each skill performed against its job, and either auto-promotes SKILL.md rewrites directly (when the chain's auto-promote mode is proprietary or all) or writes them as sidecar SKILL.patch.md files for human promotion (when auto-promote is off, and for transferables that sanitization blocks from direct overwrite). Writes a verdict file summarizing findings plus what was updated. Updates docs/TODO.md if any new follow-up work fell out of the analysis.
user-invocable: false
version: 1.1.0
---

# Supervisor

The supervisor is the third loop in the system: after a chain of skills runs to completion (e.g. `sst-dev-cycle` + `sst-dev-review`), the supervisor reads what happened and decides whether the *skills themselves* should be updated. It is the framework's mechanism for skills to learn from their own runs without contaminating the open-source transferable layer with proprietary information.

The supervisor never fixes code or files spec items. Those belong to the skills it analyzes. The supervisor's only outputs are:

1. **`<run-dir>/supervisor_verdict.md`** — a one-screen summary of the chain (clean / N updates / escalate) that also records the exact paths written.
2. **`<skill-dir>/SKILL.md`** — direct overwrite of a proprietary `SKILL.md`, when the chain is running with `auto-promote: proprietary` (the default) or `auto-promote: all`. The improved prose is then available to the NEXT chain iteration with zero extra steps.
3. **`<skill-dir>/SKILL.patch.md`** — a proposed full rewrite dropped as a sidecar next to the target `SKILL.md`, when auto-promote is `off`, or for transferable skills under any mode short of `all`-with-clean-sanitization. One file per skill, overwritten each cycle. Promoted to a real edit by the user via `/sst-promote-skill-proposal`.
4. **`docs/TODO.md`** — adds entries to `## Next up` if a finding implies project work the next sst-dev-cycle should pick up (rare; most supervisor findings target the skills, not the project).

## Operating principles

- **Auto-promote is a safety perimeter, not a feature to bypass.** When the chain sets `auto-promote: proprietary`, proprietary skills under `<cwd>/.claude/skills/` may be overwritten directly; transferables are still written as `SKILL.patch.md` sidecars. When set to `all`, transferables may also be overwritten but only after `sst-sanitize-transferable` reports `must-fix: 0`; any sanitization failure downgrades that skill to a sidecar write. When `off`, every write is a sidecar. Never cross these lines.
- **Be specific.** Every update (direct or sidecar) cites the exact run-log line(s) that motivated it (`<i>_<skill>.txt:<line>`) in the verdict file. No vague "improve error handling" notes.
- **Clean is the default.** A run where every skill behaved well produces zero updates and a one-line verdict. Don't manufacture findings to justify the invocation.
- **Sanitize before crossing the proprietary→transferable boundary.** The transferable layer is open-source. A leak there can never be retracted from clones. Use the leak rules; refuse to write a transferable update (direct OR sidecar) that fails any rule.
- **The proprietary skill is allowed to know everything.** Proprietary updates can include any project nouns, paths, secrets-as-references-not-values. Don't water them down; they exist precisely to hold proprietary detail.
- **One sidecar per skill, always overwriting.** `SKILL.patch.md` is not a per-run artifact: if a prior cycle left one and this cycle has a fresh finding for the same skill, overwrite it. If this cycle has nothing to say about a skill that has a stale sidecar, leave the sidecar alone (the user may be mid-review).

## Inputs

Read these in order, all from the run log directory passed to you (the chain runner reports its location on every invocation as `[log-dir] <path>`):

1. **`MANIFEST.json`** — chain name, harness, per-skill exit codes, durations, model + token usage, git SHA before/after. Also carries `chain_definition` (path to the chain YAML) — read that YAML and note the `auto-promote:` field; default is `proprietary` when the field is absent. This value controls §3's output routing.
2. **Each `<i>_<skill>.txt`** — the prettified, ANSI-stripped transcript of one skill invocation.
3. **Each skill's current `SKILL.md`** — for the chain runner's CWD-local `.claude/skills/<skill>/SKILL.md` (proprietary) and, if the proprietary skill has a `transferable:` field, the installed transferable at `~/.claude/skills/<transferable>/SKILL.md` (runtime read path, same dir where any sidecar `SKILL.patch.md` lives).
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

### 3. Write the update — direct or sidecar

For each finding, draft the full rewritten `SKILL.md` (frontmatter + body). Bump `version:` per SemVer: patch for prose clarification, minor for added behavior, major for changed contract. Then route the write based on (a) whether the skill is proprietary or transferable, and (b) the chain's `auto-promote` value from §Inputs step 1.

**Routing table:**

| auto-promote | Proprietary skill          | Transferable skill                                                     |
| :---         | :---                       | :---                                                                   |
| `off`        | sidecar `SKILL.patch.md`   | sidecar `SKILL.patch.md`                                               |
| `proprietary`| direct overwrite `SKILL.md`| sidecar `SKILL.patch.md`                                               |
| `all`        | direct overwrite `SKILL.md`| direct overwrite `SKILL.md` iff §4 sanitization returns `must-fix: 0`; else sidecar |

Target paths:

- **Proprietary**: `<cwd>/.claude/skills/<skill-name>/SKILL.md` or `.../SKILL.patch.md`.
- **Transferable** (runtime-effective location): `~/.claude/skills/<transferable-name>/SKILL.md` or `.../SKILL.patch.md`. This is the path the harness actually reads on the next run. A separate sanitized copy for the open-source master repo still lands at `~/Dev/skill-set/skills/<category>/<transferable-name>/SKILL.md` — but that update is staged (not committed) and surfaced in the verdict file for the user's PR flow; NEVER auto-commit anything in the master repo.

The `SKILL.patch.md` file is a **drop-in replacement**: it contains full YAML frontmatter + body, identical in shape to a normal SKILL.md. No proposal-wrapper headers, no rationale section in the file itself. All rationale + citations live in the verdict file (§6).

If a prior cycle left a stale `SKILL.patch.md` on a skill that this cycle has no finding for, **do not touch it** — the user may be mid-review. Only overwrite a sidecar when this cycle has a fresh finding for that skill.

### 4. Sanitize (any transferable write, direct or sidecar)

Before writing to ANY transferable target — whether that's a direct overwrite at `~/.claude/skills/<transferable-name>/SKILL.md` (auto-promote: `all`), a sidecar at `~/.claude/skills/<transferable-name>/SKILL.patch.md`, or the master-repo staged copy at `~/Dev/skill-set/skills/<category>/<transferable-name>/SKILL.md` — run the proposed body through `sst-sanitize-transferable`:

1. Write the proposed body to a temp file (e.g. `<run-dir>/transferable-draft-<skill>.md`).
2. Invoke `/sst-sanitize-transferable <draft-file> --project-context <path-to-proprietary-supervisor-SKILL.md>`.
3. Read the resulting `<draft-file>.findings.md`. Categorize:
   - **Any `must-fix` findings** → abort every transferable write for this skill (runtime path AND master-repo path). The lesson stays as a proprietary-only update, with a note in the verdict file: `(transferable promotion blocked by sst-sanitize-transferable findings; see <draft>.findings.md)`.
   - **`should-fix` findings only** → either rewrite the draft to address them all, or downgrade to proprietary-only.
   - **Zero findings or only `nit`** → safe to write the transferable targets. If `auto-promote: all`, overwrite the runtime `SKILL.md`; otherwise write the runtime-path sidecar `SKILL.patch.md`. In both cases, also write the master-repo sanitized copy (staged, not committed). Append the `Sanitization checklist` footer from the findings file to the verdict entry for that skill, filled with per-category counts.

Sanitization is judgment-based; it's an LLM pass against `~/Dev/skill-set/templates/sanitization-guidance.md` plus the per-project banned-terms list. Do not try to grep — `sst-sanitize-transferable` exists precisely so the supervisor doesn't have to play regex games.

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

**Chain:** <chain-name>  ·  **auto-promote:** <off|proprietary|all>  ·  **Commit:** <sha-after>  ·  **Generated:** <utc-iso>

## Outcome

clean | <N> updates | escalate

## Per-skill summary

- `<skill-name>` (`<sha-of-SKILL.md-before>`): <clean | <N> findings; direct overwrite | sidecar SKILL.patch.md | transferable blocked by sanitization>
- ...

## Updates written

- direct: `<abs-path-to-SKILL.md>` — v<old>→v<new>, <severity>, one-line rationale. Cited: `<i>_<skill>.txt:<line>`.
- sidecar: `<abs-path-to-SKILL.patch.md>` — v<old>→v<new>, <severity>, one-line rationale. Cited: `<i>_<skill>.txt:<line>`. Promote with: `/sst-promote-skill-proposal`.
- master-repo (staged, not committed): `<path>` — for transferable updates written in `all` mode with clean sanitization. User opens the PR.
- (or: `none`)

## Sanitization footers

(Appended verbatim from `<draft>.findings.md` for each transferable write, per §4. Omit entirely when no transferable writes happened.)

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
- A `sst-sanitize-transferable` rejection happened (so the user knows the system caught something potentially sensitive, even though the proposal didn't ship to the master repo).

Escalation does NOT change what the supervisor writes; it just sets a flag the manager will pick up and surface to the user.

## Permissions contract

The supervisor writes under `.claude/skills/`, which is normally gated by harness approval prompts. Those prompts are bypassed by the chain runner (`bin/skill-chain.py` passes `--dangerously-skip-permissions` to every skill invocation it spawns, supervisor included), so in the autonomous path every Write/Edit here is auto-approved. If you are ever running the supervisor manually outside a chain run, expect approval prompts on each write; that is intentional — manual runs are inherently interactive.

Do NOT add a side-channel (env var, lock file, config toggle) to skip prompts in other code paths. The harness flag is the single source of truth; changing it changes the behavior uniformly.

## Output rules

- **Write paths are limited to:** (a) the run-dir (verdict, sanitize drafts, findings files); (b) `<cwd>/.claude/skills/<skill>/SKILL.md` or `SKILL.patch.md` for proprietary updates; (c) `~/.claude/skills/<skill>/SKILL.md` or `SKILL.patch.md` for transferable updates (runtime-effective path); (d) `~/Dev/skill-set/skills/<cat>/<skill>/SKILL.md` for the master-repo staged sanitized copy of a transferable update; (e) `docs/TODO.md` under `## Next up` (rare). Never elsewhere.
- **Never call git.** No commits, no pushes, no branch creation. Direct overwrites to SKILL.md are left unstaged under `<cwd>/.claude/skills/` (often gitignored anyway) and staged-but-uncommitted under `~/Dev/skill-set/` so the user can open the PR with the sanitization footer from the verdict file.
- **Never deploy.** No SSH, no service restarts, no curl against a live site.
- **Never touch a stale `SKILL.patch.md` you didn't just write.** If this cycle had no finding for a skill that already has a sidecar, leave the sidecar alone; the user may be mid-review.

## When invoked with no run-log dir argument

Default to the most recent `.skill-runs/<*>/` directory under the current working directory. If none exists, exit cleanly with a one-line message — there's nothing to review.
