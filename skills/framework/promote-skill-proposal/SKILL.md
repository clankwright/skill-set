---
name: promote-skill-proposal
description: User-gated promotion of a supervisor proposal into a real SKILL.md edit. Lists pending proposals across the current project and the master repo, lets the user pick one, shows the diff, and (on confirmation) overwrites the target SKILL.md with the proposal's body, bumps the version per SemVer, and stages the change. Never auto-promotes; never crosses the proprietary→transferable boundary without re-running the leak check. For transferable promotions, leaves the change unstaged in the master repo so the user can open a PR with the supervisor's sanitization footer in the description.
user-invocable: true
version: 1.0.0
---

# Promote skill proposal

The supervisor writes proposals as `.md` files; this skill turns them into actual `SKILL.md` edits. **Always under user gating** — every promotion requires an explicit confirm. No batch mode, no auto.

## When to invoke

After a supervisor run produces one or more proposals. The supervisor's verdict file (`<run-dir>/supervisor_verdict.md`) lists what was filed.

## Process

### 1. Find pending proposals

Two locations:

- **Proprietary**: `<cwd>/.skill-runs/*/proposals/*.patch.md` — newest dirs first.
- **Transferable**: `~/Dev/skill-set/proposals/*.patch.md`.

List both, newest first, with: severity, target skill name, source run dir, one-line rationale (read from each proposal's header).

If zero proposals across both: report "no pending proposals" and exit.

### 2. Let the user pick one

Show a numbered list. Wait for the user's choice. If the user picks a transferable proposal, also show:

- The proposal's `Sanitization checklist` footer status (every box ticked, every banned term explicitly named with "checked: not present"). If incomplete, refuse the promotion until the supervisor (or the user) fills it in.

### 3. Resolve the target file

- Proprietary proposal `<run-dir>/proposals/<skill-name>.patch.md` → target is `<cwd>/.claude/skills/<skill-name>/SKILL.md` (if `<skill-name>` is the proprietary's name) or whatever skill the proposal's header names.
- Transferable proposal `~/Dev/skill-set/proposals/<UTC>_<skill-name>_from-<project>.patch.md` → target is `~/Dev/skill-set/skills/<skill-name>/SKILL.md`.

If the target doesn't exist, abort and report — proposals can only update existing skills, not create new ones (creating a new transferable goes through the manual `bin/new-skill-set.sh` flow).

### 4. Re-run sanitize-transferable (transferable only)

Even though the supervisor already scanned, re-run before applying — the sanitization guidance and the per-project banned-terms list may have been updated since the proposal was drafted:

```bash
# Extract the proposal body to a temp file (the proposal contains a header + the proposed body).
extract-proposal-body <proposal-file> > /tmp/<skill>.draft.md

# Run the sanitize skill on the draft.
/sanitize-transferable /tmp/<skill>.draft.md --project-context <proprietary-supervisor-SKILL.md>
```

If `<draft>.findings.md` reports any `must-fix`: refuse the promotion, print the findings file path, suggest the user move the lesson to a proprietary-only proposal. Should-fix findings are advisory at promotion time — surface them but let the user decide.

### 5. Show the diff

```bash
diff -u <target-SKILL.md> <(extract_body_from_proposal.py <proposal-file>)
```

Print it. Wait for the user's explicit `confirm` (any other reply aborts).

### 6. Apply the patch

Overwrite the target `SKILL.md` with the proposal's body. The proposal's body is the markdown that follows the `## Proposed full SKILL.md content:` heading and lives between fenced ```yaml frontmatter ``` and ```markdown body ``` blocks.

Bump the `version:` per SemVer:

- prose-only clarification → patch
- added behavior, frontmatter additions → minor
- changed contract, removed behavior, breaking frontmatter changes → major

If the proposal already includes a bumped version, honor it; otherwise infer from the diff.

### 7. Move (don't delete) the proposal

Mark the proposal as applied:

- Proprietary: rename `<proposal>.patch.md` → `<proposal>.applied.md` in place.
- Transferable: rename `<proposal>.patch.md` → `applied/<proposal>.applied.md` (create the `applied/` dir if missing).

Renaming preserves the audit trail (you can always see what was promoted, by whom, when) without cluttering the active proposals list.

### 8. Stage (don't commit)

- **Proprietary** target lives under `<project>/.claude/skills/`. If that path is gitignored in the project (common), the change is local-only — no staging needed; just confirm to the user that the new file is in place.
- **Transferable** target lives in the master repo. Stage with `git -C ~/Dev/skill-set add skills/<skill-name>/SKILL.md proposals/` so the user can craft the PR commit themselves. Print the suggested PR title (`Update <skill-name> v<old>→v<new>: <one-line>`), the suggested PR body (the proposal's rationale + the full sanitization footer copied verbatim), and the command to push.

Never commit. Never push. Promotion is the user's hand on the trigger from here on.

### 9. Report

```
Promoted <severity> proposal for <skill-name> v<old> → v<new>.
Source: <run-dir-name> (<sha-after>).
Target: <abs-path-to-SKILL.md>.
Next step: <PR command for transferable | "deployed locally" for proprietary>.
```

No follow-up question. No batch offer.

## Hard rules

- **One proposal per invocation.** If the user wants to promote three, that's three invocations.
- **No silent updates.** Every promotion shows the diff and waits for `confirm`.
- **Transferable promotions never bypass `sanitize-transferable`.** No `--force` flag exists. If the proposal lacks a fresh findings file (timestamp newer than the target), this skill refuses — re-run the sanitize skill first.
- **Don't touch the supervisor's proposal-generation logic.** This skill consumes proposals; it doesn't second-guess them.
- **If the proposal target file has been edited since the proposal was drafted** (compare the proposal's `Source: <sha-after>` to current HEAD), warn the user and show both diffs (proposal vs current, current vs HEAD-at-proposal-time). The user decides whether to abort, manually merge, or override.
