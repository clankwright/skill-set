---
name: sst-sanitize-transferable
description: Scan a transferable SKILL.md (or a draft transferable rewrite) for proprietary leakage using LLM judgment, not regex. Reads the sanitization-guidance reference, any per-project banned-terms list maintained by the proprietary supervisor, and the target SKILL.md body. Produces a categorized findings list (must-fix / should-fix / nit) with concrete suggested rewrites for each, and optionally writes a fully-sanitized sibling file for human review. Never silently edits the target. Used as a hard pre-write gate by whoever edits a transferable directly — the supervisor on its automated edits, or a human/manager on a manual edit.
user-invocable: true
version: 1.1.0
model-floor: opus
effort-floor: xhigh
---

# Sanitize transferable

The framework's open-source master repo holds transferable skills. Anything that lands here can't be retracted from clones. Sanitization is judgment-based: regex grep is too brittle (false positives on backticked examples, false negatives on novel project nouns), so this skill applies an LLM pass instead.

This skill **never silently edits** the target. It reports findings and (optionally) writes a sibling `.sanitized.md` file for review before the edit is applied directly to the transferable SKILL.md.

## When to invoke

- Before the supervisor edits a transferable directly: `/sst-sanitize-transferable <draft.md>` — a `must-fix` finding blocks the edit.
- Before any manual edit to a transferable `skills/*/SKILL.md` is committed: run this skill on the proposed body as a hard gate.
- Manually, on any existing `skills/*/SKILL.md` to audit it for accumulated leakage.

## Inputs

1. **Target file**: the SKILL.md (or draft body) to scan.
2. **Sanitization guidance**: `~/Dev/skill-set/templates/sanitization-guidance.md` — the rubric.
3. **Per-project banned-terms list** (when invoked from a project context): the proprietary supervisor's `## Banned terms` section, e.g. `~/Dev/<project>/.claude/skills/<persona>-supervisor/SKILL.md`. Pass via `--project-context <skill-md-path>` or auto-discover from `<cwd>/.claude/skills/*-supervisor/SKILL.md`.
4. **Sibling SKILL.md files** in the master repo at `~/Dev/skill-set/skills/` — for *consistency comparison* (does this skill use the same generalizations as its siblings?).

## Process

### 1. Read the inputs

- Read `templates/sanitization-guidance.md` end-to-end. The categories there ARE the ones you'll classify findings into.
- Read the target file end-to-end.
- Read the project-context banned-terms list (if any) end-to-end. These are project nouns the proprietary supervisor has explicitly forbidden in transferables.

### 2. Walk the target section by section

For each prose section, ask:

1. **Identity / ownership** (category 1 in the guidance): does this paragraph name a specific project, person, company, domain, IP, or port? Real ones, not RFC placeholders.
2. **Stack / OS specifics** (category 2): does it name a specific OS, init system, VPS provider, or service tied to one deployment? If yes, is the mention legitimately teaching ("don't hand-roll a `systemctl` call") or accidentally prescribing?
3. **Secrets / credentials** (category 3): real secrets, project-specific env-var names, test-account creds.
4. **Filesystem / infra** (category 4): paths under `/home/<user>/`, `/opt/<project>/`, project-specific subdirs, db names, daemon names, SSH aliases.
5. **Universalized assumptions** (category 5): is the skill assuming every project deploys via X, runs Y, uses Z? Generalize or qualify.
6. **Hardcoded values masquerading as limits** (category 6): is `timeout=30` because that's what *the original project* used, or because that's a real protocol/RFC limit?
7. **Per-project banned terms**: case-insensitive substring check against the project-context list. Each match is a `must-fix` finding with category 1 (identity).

Inline-backticked code spans get partial leniency: when the prose is *quoting an example to avoid* (`Don't write \`sudo service <projectname> stop\``), the project noun inside the backticks is not a leak per se, because the quote itself is the lesson. Use judgment.

### 3. Produce a findings report

Write a Markdown report to stdout AND to `<target>.findings.md` next to the target file:

```markdown
# Sanitization findings — <target file path>

**Scanned:** <utc-iso>
**Guidance:** ~/Dev/skill-set/templates/sanitization-guidance.md
**Project context:** <path to proprietary supervisor SKILL.md, or "none">

## Summary

- must-fix: <N>
- should-fix: <N>
- nit: <N>

## Findings

### [must-fix] Identity / ownership — line 42
**Quote:** "Deploy to <VPS provider> via `ssh <host-alias>` (<OS> <version>)."
**Why this leaks:** the VPS provider name is a specific vendor; the OS + version pins the deployment environment; `ssh <host-alias>` is a project-local SSH alias. Together these say *this skill is from one specific project*.
**Suggested rewrite:** "Deploy via the project's standard deploy command (look in CLAUDE.md or `deploy/`)."

### [should-fix] Stack specifics — line 88
...

### [nit] Universalized assumption — line 134
...
```

### 4. Optionally write a sanitized sibling

If the user passes `--write-sanitized`, also produce `<target>.sanitized.md` with every must-fix and should-fix finding applied. The nit findings are NOT auto-applied (those are matters of taste). Report:

```
Sanitized version written to <target>.sanitized.md.
Diff: diff -u <target> <target>.sanitized.md
Apply by copying the sanitized body over <target> once the diff is reviewed.
```

If the user passes `--in-place`, refuse — sanitization is never applied silently. The reviewer always reads the diff before the edit is applied.

### 5. Sanitization checklist footer (for proposals)

When invoked on a transferable proposal that will eventually become a PR, also produce a fillable footer the supervisor / proposer copies into the PR description. CI's sanitization-footer job (in `.github/workflows/validate.yml`) checks this is present and complete:

```markdown
## Sanitization checklist

- [ ] Identity / ownership: scanned. Findings: <N>. Resolved: <N>.
- [ ] Stack / OS specifics: scanned. Findings: <N>. Resolved: <N>.
- [ ] Secrets / credentials: scanned. Findings: <N>. Resolved: <N>.
- [ ] Filesystem / infra: scanned. Findings: <N>. Resolved: <N>.
- [ ] Universalized assumptions: scanned. Findings: <N>. Resolved: <N>.
- [ ] Per-project banned terms (<source>): explicitly checked. Hits: <N>. Resolved: <N>.

Scanned at: <utc-iso>  ·  By: sst-sanitize-transferable v<version>
```

The user / reviewer ticks each box AFTER manually re-confirming. The sanitize skill never ticks them itself.

## Hard rules

- **Never edit the target file.** This skill only reports; whoever is editing (the supervisor, or a human/manager) applies the sanitized rewrite after reviewing the diff.
- **Never call git.** No commits, no pushes, no branch creation.
- **Sanitization is per-skill.** Don't bundle scans across multiple skills in one report; each skill gets its own report file.
- **When in doubt, file it as a finding.** False-positives are cheap (the human reviewer overrides); false-negatives are permanent leaks in clones.

## Skipping the scan

There is no `--force` flag. If you want to ship something without scanning, don't call this skill — but then the transferable edit is unsanitized and must not be committed. The supervisor treats a `must-fix` finding (or a missing scan) as a hard block on any direct edit to a transferable.
