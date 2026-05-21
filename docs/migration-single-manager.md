# Migration: per-project managers → single operator-level manager

This runbook collapses N proprietary `<persona>-manager/` skill dirs (e.g. `cm-manager`, `dahrouge-manager`, `skill-set-manager`) into one operator-level `<operator>-manager/` (e.g. `rob-manager`) that watches every project from a single yaml block. The per-project context moves into each project's `docs/MANAGER.md`; the per-project objectives merge into one file with `## Project:` sections.

The transferable `sst-manager` already walks N watched-projects per invocation, so the only thing the per-project shape was adding was multiplication: N cron entries, N env-file paths, N skill files, N folders to keep in sync as the transferable evolves. Collapse removes that multiplication while preserving every per-project nuance via `docs/MANAGER.md` and `## Project:`-scoped objectives.

The bot's `_discover_manager_personas` already supports both shapes side-by-side (SPEC 30.3): legacy per-project managers keep emitting their folder-derived persona token; operator-level managers (`operator-level: true` in the yaml block) emit one persona per `watched-projects[*].name`. Migrate one persona at a time; the discovery code does not require a flag-day cutover.

---

## Pre-flight

Confirm the inventory of currently-installed per-project managers:

```bash
ls ~/.claude/skills/ | grep -E '\-manager$'
```

You should see something like `cm-manager`, `dahrouge-manager`, `skill-set-manager`. Pick an operator name; it labels the new skill file and is not used as a routable token. (Examples: your given name, your handle, `ops`, `meta`.) The persona tokens the bot routes on continue to be the per-project names (`cm`, `dahrouge`, `skill-set`); they come from the new manager's `watched-projects[*].name`.

If a per-project manager has a corresponding cron entry, locate it first:

```bash
sudo grep -E '<persona>-manager|<persona>-chain-driver' /etc/crontab
```

You will replace those N entries with one `<operator>-manager` entry in step (d) below.

---

## (a) Create the operator-level `<operator>-manager/` skill

Path: `<chosen-project>/.claude/skills/<operator>-manager/SKILL.md` (project-scoped, in whichever consuming repo you treat as the operator's "home" project). The proprietary stays out of `~/.claude/skills/` so `bin/install-skills.sh` never overwrites it.

Minimal frontmatter + config block:

```markdown
---
name: <operator>-manager
description: Operator-level manager. Wraps sst-manager and watches every project from a single yaml block. ...
user-invocable: true
transferable: sst-manager
version: 1.0.0
model-floor: opus
effort-floor: high
---

# <Operator> Manager

Inherits the full transferable contract at `~/.claude/skills/sst-manager/SKILL.md` (v1.13+).

## Configuration (the transferable greps this fenced block at startup)

```yaml
operator-level: true
watched-projects:
  - path: /home/rob/Dev/claim_management
    name: cm
  - path: /home/rob/Dev/dahrouge.com
    name: dahrouge
  - path: /home/rob/Dev/skill-set
    name: skill-set
objectives-path: <abs-path>/.claude/skills/<operator>-manager/objectives.md
telegram-env: ~/.config/<operator>-telegram.env
```
```

Notes:

- The `operator-level: true` line is what the bot's `_discover_manager_personas` keys on to emit one persona per `watched-projects[*].name` (SPEC 30.3). Without it, the file falls back to folder-derived persona (`<operator>` itself) and the project tokens are NOT registered.
- The `name:` field in each `watched-projects` entry is the persona token the user types as the first arg on `/feedback <token> ...`, `/status <token>`, `/pause <token>`, etc. (per SPEC 28.3). Keep them stable across the migration: a user typing `/feedback cm` before and after must still hit the cm project.
- `objectives-path:` points at the consolidated objectives file (step (c)).
- `telegram-env:` is the operator-level env file. Either symlink `~/.config/<operator>-telegram.env -> ~/.config/skill-set-telegram.env` (or any existing env file you already use), or create a fresh `.env` per `sst-setup-telegram`. The chat-id allowlist and bot token stay the same; only the env-file path is operator-named.

Project-agnostic body sections (hard rules, language preferences) that genuinely apply to every project belong here. Per-project context goes into each project's `docs/MANAGER.md` (step (b)).

---

## (b) Move per-project facts from `<persona>-manager/SKILL.md` to `<project>/docs/MANAGER.md`

Per SPEC 30.1, `sst-manager` reads `<watched-project>/docs/MANAGER.md` at walk time. This is where per-project context lives in the new shape. Use `~/Dev/skill-set/templates/MANAGER.md` as the starting skeleton:

```bash
cp ~/Dev/skill-set/templates/MANAGER.md <project>/docs/MANAGER.md
```

Then port the project-specific content out of the old `<persona>-manager/SKILL.md`:

| Old location in `<persona>-manager/SKILL.md`           | New location in `<project>/docs/MANAGER.md` |
| ------------------------------------------------------ | ------------------------------------------- |
| "Persona token: `<token>`" section                     | `project-token: <token>` line               |
| "Hard rules specific to this project" section          | "Per-project hard rules" section            |
| "Telegram digest language" / "Digest tone" preferences | "Digest tone" section                       |
| Project-specific deadlines, stakeholders, in-flight    | "Notes" section                             |

`docs/MANAGER.md` is **advisory steering only** — its rules cannot override transferable anti-fork constraints (no `main`-push, no sanitize bypass, no commit/deploy from the manager). Frame each rule as something the manager surfaces or routes around, not as a hard contract.

Repeat for every project the old `<persona>-manager/` watched. Commit each `docs/MANAGER.md` in the project's own git tree.

---

## (c) Consolidate objectives into one `<operator>-manager/objectives.md` with `## Project:` sections

Per SPEC 30.2, the `objectives.md` schema accepts `## Project: <name>` level-2 headers. Each scored bullet under a `## Project:` section runs its shell check from that project's path; anti-objectives stay top-level (cross-project).

Start from the template:

```bash
cp ~/Dev/skill-set/templates/objectives.md \
   <chosen-project>/.claude/skills/<operator>-manager/objectives.md
```

For each old `<persona>-manager/objectives.md`:

1. Open the source file.
2. Copy each scored bullet (`- [ ] <slug>: ... check: ... target: ... since: ...`) into the new file under a fresh `## Project: <name>` header. The `<name>` must match the `name:` field in the operator-manager's `watched-projects:` entry.
3. Cross-project anti-objectives (production-cutover bans, test-count bans, streak counter bans) merge into one top-level `## Anti-objectives` section. Deduplicate by intent.
4. Cross-project quality objectives ("test suite green," "no open blockers") can stay top-level (they apply to every watched project) OR be repeated under each `## Project:` section if the check expressions differ per project.

The planner's gap-scoring (Phase 25 §γ) reads `## Project:`-scoped objectives separately and proposes candidates only against the matching project's `## Next up`. Anti-objectives bind globally.

---

## (d) Replace N cron entries with one

Locate the per-persona cron entries:

```bash
sudo grep -E '<persona>-manager' /etc/crontab
```

Replace them with one operator-level entry. Pattern (8am + 3pm local; adjust to your timezone):

```cron
# operator-level manager: walks every watched project per ~/.claude/skills/<operator>-manager/SKILL.md
0 8,15 * * *  rob  cd /home/rob && TELEGRAM_LABEL=<operator> /usr/local/bin/claude --print "/<operator>-manager" >> /home/rob/.claude/state/cron.log 2>&1
```

The `TELEGRAM_LABEL=<operator>` exports the operator name as the outbound digest label (per SPEC 28.1). Per-project digest sections inside the body carry their own `[<project-token>]` prefix; the outer envelope label tells the user "this came from the operator-level manager," not from any one project.

Delete the old `<persona>-manager` and `<persona>-chain-driver` cron entries that the new one supersedes. Keep per-project chain-driver entries separate — chain-drivers are per-codebase (they spawn the per-project dev/review/supervisor pipeline) and do NOT collapse to the operator level.

Verify with `sudo crontab -l -u rob` or `sudo cat /etc/crontab | grep <operator>` after editing.

---

## (e) Archive per-project `<persona>-manager/` skill dirs

Do not delete — archive. The audit trail matters when investigating "where did this old digest format come from" or "what was the cm-specific hard rule that got dropped."

For each old `<persona>-manager/`:

```bash
cd <project>/.claude/skills/
tar -czf .archive/<persona>-manager.$(date -u +%Y-%m-%dT%H-%M-%SZ).tar.gz <persona>-manager/
rm -rf <persona>-manager/
```

(Create `.archive/` if it does not exist; add it to `.gitignore` if you do not want the tarball checked in.)

After archive, `_discover_manager_personas` no longer finds the old folder, so the legacy folder-derived persona drops from `/projects`. The new operator-level persona tokens (registered via `watched-projects[*].name`) cover routing.

---

## Verify

```bash
# 1. /projects via the bot should list every project token (no operator name).
echo "/projects" | TELEGRAM_ENV_FILE=~/.config/<operator>-telegram.env bash bin/notify-telegram.sh

# 2. The manager skill itself should walk every watched-project in one invocation.
claude --print "/<operator>-manager"

# 3. Per-project hard rules from docs/MANAGER.md should surface in the digest.
#    (manual inspection — the digest section for each project will reflect the new steering)

# 4. Inbound: /feedback <token> ... should route to the right project section
#    of manager-notes.md (and trigger on-demand spawn if MANAGER_SKILL_NAME is set).
```

If `/projects` returns the operator name (e.g. `rob`) instead of the project tokens, the `operator-level: true` line is missing from the yaml block — re-check step (a).

---

## Rollback

The migration is reversible at every step because legacy `<persona>-manager/` dirs are archived, not deleted:

```bash
cd <project>/.claude/skills/
tar -xzf .archive/<persona>-manager.<utc>.tar.gz
# restore the per-persona cron entry, remove the operator-level entry
```

The operator-level `<operator>-manager/` can stay installed alongside legacy managers during transition — `_discover_manager_personas` happily emits personas from both shapes (SPEC 30.3 transition tests cover this). Migrate one persona at a time if a single big-bang cutover feels risky.
