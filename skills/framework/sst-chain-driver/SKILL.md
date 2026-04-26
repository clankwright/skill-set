---
name: sst-chain-driver
description: Single-session driver for a multi-iteration skill-chain run. Spawns `bin/skill-chain.py --chain <name> --loop N` as a subprocess via `bin/drive-chain.py`, watches the live event stream, posts Telegram updates at session start, each iteration boundary (commit + per-iter spend + cumulative), every rate-limit pause/resume, supervisor escalation, and session end. Honors a `--max-budget-usd` halt and a `--max-cycles` halt independently of the chain's own loop count. Distinct from sst-manager (cron-based, multi-project, periodic) and from sst-skill-router (in-process planner inside one user request). The proprietary counterpart supplies the watched-chain name, Telegram chat ID, and budget defaults.
user-invocable: true
version: 1.2.0
argument-hint: <chain-name> [--loop N] [--max-budget-usd $X] [--max-cycles N]
---

# Chain driver

The chain driver is the missing top-level role between `sst-manager` (cadence-based, cross-project, reactive) and `bin/skill-chain.py` (the chain runner itself). It is invoked once per multi-iteration session, runs FOR THE WHOLE DURATION of that session, and posts Telegram updates as events fire so the user can supervise a long autonomous run from their phone.

The chain driver NEVER:
- edits a `SKILL.md` (that's the supervisor + `/sst-promote-skill-proposal`).
- makes git commits or deploys (read-only across the working tree; write-only to the chain's own log dir + outbound Telegram).
- decides which work to pick (the chain's skills handle that via the project's `docs/TODO.md`).

## Operating principles

- **One subprocess, one session.** The chain driver wraps exactly one `bin/skill-chain.py` invocation. To watch a different chain, spawn a second chain driver. Don't multiplex multiple chains inside one session.
- **Halt is best-effort, not pre-emptive.** A budget or cycle cap fires SIGINT to the chain runner between iterations (or between skills). The chain runner's `KeyboardInterrupt` path finalizes manifests cleanly and exits with 130. There is no kill-mid-skill: a skill that has already started will run to completion before the halt lands.
- **Telegram is best-effort too.** A failed Telegram send (network, bad token, missing chat ID) prints to stderr but does not abort the driven run. The chain itself is the source of truth; Telegram is a courtesy stream.
- **No retries on the chain runner.** Rate-limit pause-and-resume happens INSIDE `bin/skill-chain.py` (Phase 13). The chain driver just observes and forwards. If the chain exits non-zero, the chain driver exits non-zero.
- **Iteration boundaries are the unit of accountability.** Per-iteration `MANIFEST.json` files are the canonical record of cost, commit SHA, and supervisor verdict. The chain driver reads those: it does not estimate costs from streamed events, and it does not parse skill output for project facts.

## Inputs

The chain driver accepts the user's intent in either form:

- **Direct**: the user invokes `/sst-chain-driver` with a chain name and caps on the command line. Example: *"run dev-cycle-with-review-looped, halt at $30 or 5 iterations, use the manager telegram env at ~/.config/manager-telegram.env"*.
- **Configured**: the proprietary counterpart (e.g. `<project>-chain-driver`) declares the watched-chain + caps + telegram-env path in its frontmatter or body, so the user only types the skill name.

The proprietary counterpart's SKILL.md should declare:

```yaml
watched-chain: <chain-name>          # e.g. dev-cycle-with-review-looped
default-loop: <int>                  # e.g. 3
default-max-budget-usd: <float>      # e.g. 30.00
default-max-cycles: <int>            # e.g. 5  (typically equals default-loop)
telegram-env: ~/.config/<persona>-telegram.env
label: <persona-name>                # human-readable tag for telegram messages
```

(Pattern mirrors `sst-manager`'s configuration block. The proprietary's body declares these as a fenced ```yaml block; this skill greps for them, with CLI overrides winning over the declared defaults.)

## Process

### 0. Pre-flight

1. Resolve the chain name. The proprietary counterpart's `watched-chain:` is the default; user CLI args override.
2. Confirm `bin/drive-chain.py` is present at `~/Dev/skill-set/bin/drive-chain.py` (or `<repo-root>/bin/drive-chain.py` when working inside this repo). If not, the framework is not installed cleanly: bail with a clear error pointing the user at `bin/install-skills.sh`.
3. Confirm the chain definition resolves: `bin/skill-chain.py` will look in `<cwd>/.claude/chains/<name>.yaml` first, then `<repo>/chains/<name>.yaml`. If neither exists, fail loud: there is no point spawning a chain driver over a non-existent chain.
4. If a `telegram-env` path is configured (or passed via `--telegram-env`), confirm the file exists and exports both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Missing either = the run will produce stderr-suppressed warnings; that's a soft fail, not hard.

### 1. Resolve effective caps

Layer (most-specific wins):

1. CLI: `--max-budget-usd`, `--max-cycles`, `--loop`.
2. Proprietary counterpart's `default-*` fields.
3. Defaults: no budget cap, no cycle cap, loop = 1 (degenerate but legal: the chain driver works fine over a single-iteration chain).

Validate: budget > 0 if set, cycles >= 1 if set, loop >= 0.

### 2. Spawn the chain-driver helper

Build the command and invoke via Bash:

```bash
bin/drive-chain.py \
  --chain <name> \
  --loop <N> \
  --max-budget-usd <X> \
  --max-cycles <N> \
  --telegram-env <path> \
  --label <persona-name>
```

Omit any flag whose value resolved to "no cap" (the helper treats absence as no cap). If the user passed `--no-telegram`, forward that and skip the `--telegram-env` flag entirely.

The helper streams stdout from the underlying chain runner verbatim. The skill should NOT post-process or buffer — let it stream so the interactive terminal looks identical to a direct `bin/skill-chain.py` invocation.

### 3. Observe and report

The helper handles every Telegram event automatically:

| Event | Trigger | Telegram text shape |
| :---  | :---    | :---                |
| session-start | chain-driver startup | chain name, iter count, caps, log dir, started_at |
| iter-close    | each `===== iteration N =====` boundary AFTER the first | commit SHA + subject, per-iter cost, cumulative cost, verdict outcome, rate-limit pause count, utc |
| rate-limit-pause | `[rate-limit] ... sleeping ... before retrying /<skill>` | type, skill, sleep seconds, wake utc, current iter |
| rate-limit-resume | `>>` session banner after a pause | resumed skill, utc |
| rate-limit-abort | `[rate-limit] ... aborting chain` / `max-pauses-per-session` / `max-rate-limit-pause-seconds` | reason, raw line |
| halt-request | budget/cycle cap exceeded OR supervisor verdict outcome is `escalate` | reason, SIGINT sent at next safe boundary |
| session-end | subprocess exit | exit code, halt reason if any, completed iterations, cumulative cost, manifest path, finished_at |

The skill itself does not need to parse the stream further. The terminal stays the same as a direct chain invocation; Telegram is the secondary stream the helper drives.

### 4. Halt semantics

Three independent halt sources, OR'd:

- `--max-budget-usd` exceeded: cumulative cost from iter manifests exceeds the cap.
- `--max-cycles` reached: completed iterations meet or exceed the cap.
- Supervisor `Outcome: escalate` (or any `escalate` keyword in `supervisor_verdict.md` body when no `Outcome:` line is present): the helper auto-halts so a human can inspect.

A halt sends SIGINT to the chain runner. The chain runner's `KeyboardInterrupt` path is well-tested for between-iter sleeps; for in-flight skills, the SIGINT terminates the current `claude` subprocess (which exits 130), the iteration manifest records the partial run, and the chain exits.

### 5. Report to the user

After the helper exits, surface a one-line summary on stdout:

```
sst-chain-driver: chain=<name> iters=<completed>/<requested> cost=$<X.XX> exit=<rc>
  log: <run-dir>
  halt: <reason or 'normal'>
```

Telegram has already received the user-facing session-end message; this stdout line is for the calling context (a manager reading the cron log, or the user watching the terminal).

## Hard rules

- **Never run `bin/skill-chain.py` directly.** Always go through `bin/drive-chain.py`. The whole point is the watcher; bypassing it loses the budget gate and the Telegram stream.
- **Never edit a `SKILL.md` from inside the chain driver.** That's `sst-supervisor` + `/sst-promote-skill-proposal`. The chain driver is read-only across `.claude/skills/`.
- **Never spawn a second chain driver from inside one.** Recursion is meaningless here; one session = one chain. If the user asks for two parallel runs, they invoke the skill twice.
- **Never pass project-specific paths or chat IDs in the transferable's prose.** The proprietary counterpart owns those facts. The transferable parses them from the proprietary's frontmatter / body.
- **Never silently drop a Telegram failure.** The helper writes failed sends to stderr with a `[chain-driver]` tag; the skill should leave that visible rather than swallowing it. If the user wants no Telegram at all, they pass `--no-telegram`.
- **Telegram messages capped at 4000 chars** (enforced by `bin/notify-telegram.sh`). The helper formats short multi-line bodies that fit; if a future event class needs longer content, write the long form to the run dir and link from the Telegram body.

## Reference: command-line shape

The full helper signature, for the agent to compose against:

```
bin/drive-chain.py
    --chain <chain-name>           [required]
    --loop <N>                     [forwarded to skill-chain.py]
    --max-budget-usd <X>           [omit for no cap]
    --max-cycles <N>               [omit for no cap]
    --telegram-env <path>          [omit when env vars are already set]
    --no-telegram                  [suppress outbound entirely]
    --harness <name>               [forwarded; default claude-code]
    --log-dir <path>               [forwarded; default .skill-runs/<UTC>_<chain>/]
    --no-log                       [forwarded; degrades iter-close to a no-cost line]
    --label <name>                 [tag in every Telegram body]
    -- <extra-args-for-skill-chain.py>
```

`--label` is the human-readable tag the helper prefixes every Telegram body with. Default is the chain name. The proprietary counterpart usually overrides it to the persona name (`<persona>` rather than `dev-cycle-with-review-looped`).

## Worker lifecycle (Phase 18; in spec, not yet implemented)

Per framework policy, the `bin/manager-bot.py` long-poll Telegram worker only runs while a chain session is active. The chain driver SHOULD:

1. At session-start, after the pre-flight in §0 succeeds and BEFORE spawning `bin/skill-chain.py`: check whether a worker is already running for this `telegram-env` (probe by tmux session name `<persona>-bot` or by a PID file in `~/.claude/state/manager-bot.pid`). If not, start one in a detached tmux session named after the persona.
2. At session-end, after the chain runner exits and BEFORE the final stdout summary: stop the worker IFF this session started it. If the worker was already running before the chain started (externally managed by the user), do NOT touch it.

Until the implementation lands, the chain driver assumes the worker is externally managed (tmux session started by the user via `/sst-setup-telegram` or by hand). The user is responsible for stopping the worker between chain runs to avoid the inbound-noise pattern Phase 18 exists to fix.

The manager skill (`sst-manager`) does NOT depend on the worker being live: when the worker is down, the manager's §1 inbound-command sweep finds an empty queue dir and proceeds with §2 (cross-project status) cleanly.

## Naming history

This skill was originally shipped as `sst-orchestrator` and renamed to `sst-chain-driver` in framework Phase 15 to remove the three-way collision between this skill, `sst-skill-router` (formerly `sst-agent-orchestrator`), and the looser everyday "orchestrator" usage. Behavior is unchanged. Any existing proprietary `<persona>-orchestrator` counterpart should be renamed to `<persona>-chain-driver` and its `transferable:` frontmatter pointed at this skill.
