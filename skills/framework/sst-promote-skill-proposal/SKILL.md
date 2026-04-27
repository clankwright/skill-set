---
name: sst-promote-skill-proposal
description: User-gated promotion of a supervisor-written SKILL.patch.md sidecar into a real SKILL.md. Scans the current project and harness skills dir for pending sidecars, lets the user pick one, shows the diff, and (on confirmation) replaces the target SKILL.md with the sidecar's content. Never auto-promotes; never crosses the proprietary→transferable boundary without re-running the leak check. Used when a chain ran with auto-promote turned off (or for any transferable skill whose auto-promote was blocked by sanitization findings).
user-invocable: true
version: 1.1.1
model-floor: haiku
effort-floor: medium
---

# Promote skill proposal

The supervisor writes proposed rewrites as `SKILL.patch.md` sidecars next to the target `SKILL.md` when auto-promote doesn't apply directly (auto-promote `off`, or a transferable skill under `proprietary` mode, or a transferable skill under `all` mode that sanitization blocked). This skill turns those sidecars into actual `SKILL.md` edits. **Always under user gating** — every promotion requires an explicit confirm. No batch mode, no auto.

When the chain ran with `auto-promote: proprietary` (default) or `all`, proprietary skills were already overwritten in place and this skill is not needed for them; it's still the only sanctioned path for the transferable counterparts.

## When to invoke

After a supervisor run that wrote one or more `SKILL.patch.md` sidecars. The supervisor's verdict file (`<run-dir>/supervisor_verdict.md`) lists each sidecar path explicitly under "Updates written".

## Process

### 1. Find pending sidecars

Scan all three sidecar-capable roots, newest `SKILL.patch.md` mtime first:

- `<cwd>/.claude/skills/*/SKILL.patch.md` — proprietary, project-local.
- `~/.claude/skills/*/SKILL.patch.md` — transferable (and any personal-global proprietary), runtime-effective path.
- `~/Dev/skill-set/skills/**/SKILL.patch.md` — transferable, master-repo staged path.

For each, read the `version:` field from the sidecar frontmatter and from the adjacent `SKILL.md` so the list can show `v<old>→v<new>`. If the most recent `supervisor_verdict.md` in `<cwd>/.skill-runs/*/` names the sidecar, pick up its severity + one-line rationale for the display.

If zero sidecars across all three roots: report "no pending proposals" and exit.

### 2. Let the user pick one

Show a numbered list: `<n>. <severity> <skill-name> v<old>→v<new> [<scope>]  — <rationale>`. Wait for the user's choice. If the user picks a transferable sidecar, also show:

- The sanitization checklist for that sidecar copied from the latest verdict file (every box ticked, every banned term explicitly named with "checked: not present"). If incomplete or absent, refuse the promotion until the supervisor re-runs or the user fills it in.

### 3. Resolve the target file

The target is always the `SKILL.md` next to the sidecar. If that `SKILL.md` does not exist, abort and report — this skill only updates existing skills, never creates new ones (new transferables go through the manual `bin/new-skill-set.sh` flow).

### 4. Re-run sst-sanitize-transferable (transferable only)

Even though the supervisor already scanned, re-run before applying — the sanitization guidance and the per-project banned-terms list may have been updated since the sidecar was drafted:

```bash
/sst-sanitize-transferable <sidecar-path> --project-context <proprietary-supervisor-SKILL.md>
```

(The sidecar is itself a drop-in SKILL.md, so no body-extraction step is needed.) If `<sidecar>.findings.md` reports any `must-fix`: refuse the promotion, print the findings file path, suggest the user either edit the sidecar to resolve the findings or delete it entirely. Should-fix findings are advisory at promotion time — surface them but let the user decide.

### 5. Show the diff

```bash
diff -u <target-SKILL.md> <sidecar-SKILL.patch.md>
```

Print it. Wait for the user's explicit `confirm` (any other reply aborts).

### 6. Apply the patch

```bash
mv <sidecar-SKILL.patch.md> <target-SKILL.md>
```

A single atomic rename: the sidecar becomes the new `SKILL.md`; the prior `SKILL.md` content is discarded (recoverable from git history). The sidecar's frontmatter must already carry the bumped `version:` per SemVer (the supervisor does this when it writes the sidecar). If the version looks wrong (unchanged or un-bumped), warn the user before `mv`-ing.

### 7. Stage (don't commit)

- **Project-local proprietary** target under `<cwd>/.claude/skills/`: if that path is gitignored in the project (common), the change is local-only — no staging needed. Otherwise `git -C <cwd> add .claude/skills/<skill-name>/SKILL.md`.
- **Personal-global** target under `~/.claude/skills/`: not part of any git repo by default; no staging.
- **Master-repo transferable** target under `~/Dev/skill-set/skills/`: `git -C ~/Dev/skill-set add skills/<cat>/<skill-name>/SKILL.md` so the user can craft the PR commit themselves. Print the suggested PR title (`Update <skill-name> v<old>→v<new>: <one-line>`), the suggested PR body (the verdict's rationale + the sanitization footer copied verbatim), and the command to push.

Never commit. Never push. Promotion is the user's hand on the trigger from here on.

### 8. Report

```
Promoted <severity> sidecar for <skill-name> v<old> → v<new>.
Target: <abs-path-to-SKILL.md>.
Next step: <PR command for master-repo transferable | "deployed locally" for proprietary/personal-global>.
```

No follow-up question. No batch offer.

## Hard rules

- **One sidecar per invocation.** If the user wants to promote three, that's three invocations.
- **No silent updates.** Every promotion shows the diff and waits for `confirm`.
- **Transferable promotions never bypass `sst-sanitize-transferable`.** No `--force` flag exists. If the sidecar lacks a fresh findings file (timestamp newer than the sidecar), this skill refuses — re-run the sanitize skill first.
- **Don't touch the supervisor's output logic.** This skill consumes sidecars; it doesn't second-guess them.
- **If the target `SKILL.md` has been edited since the sidecar was drafted** (compare the sidecar's mtime to the target's mtime), warn the user and show both diffs (sidecar vs current, current vs HEAD-at-sidecar-mtime). The user decides whether to abort, manually merge, or override.
