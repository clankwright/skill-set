# Contributing

Two rules above all:

1. **No proprietary content in transferable skills.** No project names, company names, domain names, IPs, ports, OS-specific commands tied to one stack, secret env-var names, table names, or paths from any specific project. The categories of leak are documented in `templates/sanitization-guidance.md`. Sanitization is judgment-based: run the `sanitize-transferable` skill on your draft before opening a PR — it produces a categorized findings file and a fillable checklist footer.
2. **Transferable patches must include a sanitization footer.** Every PR that modifies a `skills/**/SKILL.md` file must include a `Sanitization checklist:` block in the PR description, with each category from `templates/sanitization-guidance.md` explicitly accounted for. Copy the footer the `sanitize-transferable` skill generates; tick each box only after you (the human) re-confirm. Empty footers and "✓ all good" shorthand fail CI.

## What can land here

- New transferable skills (`skills/<category>/<name>/SKILL.md` plus optional `references/`, `scripts/`, `assets/`). Pick the category folder whose existing skills share the most intent with yours; if none fits, propose a new category in the PR description.
- Improvements to existing transferable skills, sourced either from your own work or from a supervisor proposal in `proposals/`.
- New tooling under `bin/` that supports the chain runner, manager bot, or supervisor workflow.
- Schema and template improvements.

## What doesn't

- Anything that names a specific company, domain, or stack.
- Skills that only make sense inside one codebase. Those are proprietary; keep them in your project's `.claude/skills/`.
- Bulk AI-generated skill packs without per-skill review.

## Promoting a supervisor proposal

When a supervisor run produces a transferable proposal under `proposals/`:

1. Read the proposal's rationale block — does the lesson generalize, or is it project-specific?
2. If it generalizes: open a PR moving the proposal into `skills/<category>/<name>/SKILL.md`. Re-do the sanitization checklist yourself (don't trust the supervisor's footer blindly; it's a draft).
3. If it doesn't: delete the proposal. The lesson belongs in the proprietary counterpart only.

## SKILL.md frontmatter (required fields)

```yaml
---
name: <kebab-case>
description: <one-paragraph: what the skill does, when it triggers>
version: 1.0.0
---
```

User-invocable skills add `user-invocable: true`. Skills that only run as part of a chain omit it.

## Style

- Match the prose style of existing skills: imperative voice, short sentences, no marketing language.
- Numbered top-level sections (`## 1. Pre-flight`, `## 2. Decide`, ...) when the skill is a sequential procedure.
- Examples in fenced code blocks. Real commands, not pseudo-code.
