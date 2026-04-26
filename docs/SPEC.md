# skill-set SPEC

This is the master spec for the skill-set system itself. Each consuming project keeps its own `docs/SPEC.md` for its own work; this file governs the framework.

## Harness scope

The framework is harness-agnostic: a `Harness` abstraction in `bin/skill-chain.py` isolates the choice of agent runtime (which CLI to spawn, what command-line shape, what stream format). The MVP shipped with one implementation, `claude-code`, because that's what the prototype runs on; additional harnesses (a cheaper Claude tier per Phase 19, a non-Claude binary like Goose per Phase 20, future Codex / Gemini / etc.) drop in by adding a `Harness` subclass. User-facing docs use harness-neutral terms ("agent", "harness", "skills directory"); the current default skills paths (`~/.claude/skills/` for globally-installed transferables, `<project>/.claude/skills/` for proprietary) come from the Claude Code harness and will be parameterized when a second harness lands. The layout is flat under the harness skills dir because Claude Code only discovers direct children; a nested segregation subdir (e.g. `skill-set/`) was tried and reverted after discovery broke.

## Primary concepts

### Skill-chain

A `.yaml` file naming a sequence of skills the chain runner executes in order. Same transferable/proprietary split as skills:

- **Transferable chains** live at `<repo>/chains/<name>.yaml`.
- **Proprietary chains** live at `<project>/.claude/chains/<name>.yaml`.
- A proprietary chain MAY name the transferable chain it instantiates via `transferable: <name>` (informational; no inheritance/override behavior in MVP, proprietary chains list their full skill sequence explicitly).

Frontmatter shape (validated by `schema/skill-chain.schema.json`):

```yaml
name: dev-cycle-with-review        # must match filename without .yaml
description: ...
version: 1.0.0
user-invocable: true               # default true
auto-supervisor: true              # default true
loop: 1                            # default 1; N>1 runs the sequence N times; 0 = until failure/Ctrl-C
loop-delay: 0                      # default 0; seconds to sleep between iterations
skills:                            # required, ordered
  - sst-dev-cycle
  - sst-dev-review
transferable: dev-cycle-with-review  # proprietary only
transferable-version: ">=1.0.0"      # proprietary only, optional
```

Invocation:

```bash
bin/skill-chain.py --chain <name>                  # resolves cwd/.claude/chains/ then repo/chains/
bin/skill-chain.py --chain <name> --loop 5         # override loop count at runtime
bin/skill-chain.py --chain <name> --loop 0         # loop until failure / Ctrl-C
bin/skill-chain.py <skill> [<skill>]               # ad-hoc, no chain file needed
```

When `loop != 1`, each iteration's artifacts land in a `<log-dir>/iter_NN/` subdir with its own `MANIFEST.json`; the top-level `MANIFEST.json` carries an `iterations: [...]` array summarizing each pass. For `loop == 1` the single-run flat layout is preserved unchanged, so existing tooling is untouched. A non-supervisor skill failure aborts the whole loop; Ctrl-C cleanly breaks out after the current skill finishes.

### Skill-set

A `(transferable, proprietary)` pair of `SKILL.md` files, linked via the `transferable:` field in the proprietary's YAML frontmatter:

```yaml
---
name: ssp-dev-cycle                  # proprietary; MUST differ from `transferable:`
description: ...
user-invocable: true
transferable: sst-dev-cycle          # transferable counterpart
transferable-version: ">=1.0.0"
---
```

Transferable skills don't back-link (1:N relationship). Validation: `schema/skill-set.schema.json` + the distinct-name check in `bin/validate-frontmatter.py`.

**Distinct-name rule.** A proprietary skill's `name:` MUST differ from its `transferable:`. Both install under the same harness skills directory (`~/.claude/skills/<name>/` for personal-global, `<project>/.claude/skills/<name>/` for project-scoped), so identical names would collide and `install-skills.sh` would silently clobber hand-edited proprietary content. Enforced by the validator; no opt-out.

**`sst-` / `ssp-` prefix convention.** All skill-set skills carry a framework-identifying prefix:

- Transferable skills (canonical, shipped here under `skills/`) use `sst-<base>`. Examples: `sst-dev-cycle`, `sst-linkedin-easy-apply`, `sst-sanitize-transferable`.
- Proprietary counterparts use `ssp-<base>`. Examples: `ssp-dev-cycle`, `ssp-linkedin-easy-apply`. They declare `transferable: sst-<base>` in frontmatter.

Project-scoped proprietary MAY substitute a project-name prefix when tightly coupled to one codebase (e.g. `myproject-dev-cycle`); that also satisfies the distinct-name rule. The `ssp-` default is preferred for portability. The prefix makes it visible at a glance which skills came from this framework and on which side of the split, and keeps unrelated user-authored skills cleanly separable.

**Scopes.** Two canonical homes for proprietary skills:

1. **Project-scoped** at `<project>/.claude/skills/<name>/` discovered only when the harness runs in that project. For skills specialized to a single codebase.
2. **Personal-global** at `~/.claude/skills/<name>/` discovered from any directory. For skills specialized to the user's identity, tooling, or config (e.g. `ssp-linkedin-easy-apply` carrying a resume path + salary floor). Because `install-skills.sh` only touches names defined in this repo's `skills/`, `ssp-*` skills are never overwritten when the transferable counterpart is bumped.

### Handoff docs

Every project keeps two canonical files (`docs/SPEC.md`, `docs/TODO.md`) read by every skill on start and updated by every skill on close. See `templates/`.

`SPEC.md` shape: long-lived, phase checklists with `- [ ]`/`- [x]`. Closed phases get a 1-paragraph context + a tight bulleted change log (one line per item, not a paragraph each). Phases that drift toward novella-length should be compressed back; git history + TODO `Just shipped` carry the detail.

`TODO.md` shape (three sections):
```markdown
## In flight
- [<skill> @ <utc>] <one-line>

## Just shipped (last cycle)
- <one-line> by <skill> at <utc>

## Next up (queued for next cycle)
- <one-line> reason / source
```

Skill contract (codified in transferable preambles):
1. Read both docs end-to-end before any other action.
2. Pick from `TODO.md` "Next up" if non-empty, else next unchecked item in `SPEC.md`.
3. Write a single "In flight" line at start; rewrite (don't append) as work narrows.
4. On close: move "In flight" → "Just shipped" (no commit SHA, a commit cannot contain its own hash; correlate via `git log --oneline --grep`); append any new work to "Next up"; trim "Just shipped" to last 10.
5. Both docs commit in the same commit as the code change.

### Run log

Each chain invocation writes to `<project>/.skill-runs/<UTC>_<chain-name>/`:

- `MANIFEST.json` chain name, harness, skill list, exit codes, durations, model, token usage, git SHA before/after.
- `<i>_<skill>.jsonl` raw stream events emitted by the harness (one JSON object per line).
- `<i>_<skill>.txt` prettified, ANSI-stripped transcript.
- `supervisor_verdict.md` appended at end of chain (when supervisor runs).
- `proposals/<skill-name>.patch.md` proposed `SKILL.md` rewrites (proprietary or transferable).

### Sanitization (transferable proposals only)

Before writing a transferable proposal, the supervisor invokes the `sst-sanitize-transferable` skill, which scans the draft against `templates/sanitization-guidance.md` (rubric) and the per-project banned-terms list maintained by the proprietary supervisor. Sanitization is judgment-based, an LLM pass, not regex. Any `must-fix` finding aborts the write; the lesson stays in the proprietary proposal only. Every transferable proposal carries a `Sanitization checklist:` footer the sanitize skill generates and the human reviewer fills in; CI rejects PRs without a complete footer.

## Phases

### Phase 1: skeleton + log capture (closed)

- [x] Master repo scaffolding: LICENSE, README, `.gitignore`, `templates/SPEC.md`, `templates/TODO.md`.
- [x] `bin/skill-chain.py` chain runner with `--log-dir` writing `MANIFEST.json` + per-skill `.jsonl`/`.txt`.
- [x] `Harness` abstraction (claude-code MVP) + `--harness` flag + `$AGENT_HARNESS` env.
- [x] Smoke-tested via real dev-cycle from a consuming project; consuming `TODO.md` bootstrapped from template.

### Phase 2: linkage + globals lift

- [x] `transferable:` field added to consuming proprietary skills; canonical homes for transferables moved to `skills/`.
- [x] Handoff-doc read/update contract baked into transferable preambles.
- [x] `schema/skill-set.schema.json` validator written.
- [ ] User runs `bin/install-skills.sh -y` to deploy updated `sst-dev-cycle`/`sst-dev-review` into `~/.claude/skills/`.

### Phase 3: supervisor (closed)

- [x] Transferable `sst-supervisor` + first proprietary supervisor in a consuming project.
- [x] Auto-append proprietary supervisor in `bin/skill-chain.py`.
- [x] `templates/sanitization-guidance.md` + `sst-sanitize-transferable` skill (LLM-judgment, not regex).

### Phase 4: proposal promotion (closed)

- [x] `~/.claude/skills/promote-skill-proposal/SKILL.md` shipped.

### Phase 5: manager + Telegram bot (closed)

- [x] `sst-manager` (transferable) + first proprietary manager.
- [x] `bin/notify-telegram.sh` (outbound) + `bin/manager-bot.py` (long-poll inbound) + service-unit / rc.d templates.

### Phase 6: open-source (closed)

- [x] Public GitHub at `git@github.com:toadlyBroodle/skill-set.git`; `main` tracks `origin/main`.
- [x] CI: frontmatter validator + sanitization-footer-on-PR enforcement; CONTRIBUTING.md.

### Phase 7: portability proof (closed)

- [x] Built second skill-set in non-dev domain (lead-gen, content-ops, infra) by lifting `sst-lead-generation`, `sst-domain-seo-research`, `sst-linkedin-easy-apply`, `sst-linkedin-networking`.
- [x] `sst-supervisor` + `sst-manager` work unmodified across both domains; validator passes uniformly.

### Phase 8: lift long-running agents into transferables

12-agent framework ported as 12 target skills (11 transferable, 1 proprietary). Each lift converted a Python-agent module into a SKILL.md natural-language procedure; rate-limit / tool helpers mapped to harness primitives. Each lift passed `sst-sanitize-transferable` + validator pre-commit.

- [x] 8.1: `sst-web-research`, `sst-fact-checker`, `sst-output-selector`.
- [x] 8.2: `sst-iterative-writer`, `sst-literary-critic`, `sst-editorial-pass`.
- [x] 8.3: `sst-llm-judge-ranker`, `sst-translator`.
- [x] 8.4: `sst-email-control-loop`, `sst-skill-router` (originally `sst-agent-orchestrator`; renamed in Phase 15).
- [x] 8.5: `sst-short-video-generator`, `sst-social-promoter` + first proprietary counterpart.
- [ ] End-to-end smoke: `sst-web-research → sst-editorial-pass → sst-social-promoter` chain with clean supervisor verdict against a real project.

### Phase 9: optional chain looping (closed)

Opt-in iteration on the chain runner so a single chain definition can repeat its full skill sequence N times (or until non-supervisor failure). Long-running skills tick through several queued items in one sitting; supervisor still runs once per iteration.

- [x] `loop` + `loop-delay` schema fields (defaults 1 / 0; backward-compat); `--loop` + `--loop-delay` CLI flags (CLI > YAML); `--loop 0` runs until failure or Ctrl-C.
- [x] Iteration-per-subdir log layout (`iter_NN/MANIFEST.json`) when `loop != 1`; flat layout preserved for `loop == 1`. Top-level `MANIFEST` carries `iterations: [...]` + `loop: {requested, delay_seconds, completed}` when looping.
- [x] README "Chain YAML fields" + "Loop mode" sections.
- [x] `chains/dev-cycle-with-review-looped.yaml` shipped (loop:3, auto-promote:all) as the multi-iter reference; baseline `dev-cycle-with-review` unchanged.

### Phase 10: proprietary-naming enforcement + sst-/ssp- migration (closed)

Distinct-name rule + `sst-<base>` / `ssp-<base>` prefix convention + install-time safety net for hand-edited targets.

- [x] Validator rejects proprietary skills where `name == transferable`; transferables in this repo's `skills/` MUST carry `sst-` prefix.
- [x] Renamed every transferable bare → sst- (cross-references in SKILL bodies, chain YAMLs, docs, templates).
- [x] `bin/install-skills.sh` DIVERGED-target detection: interactive diff prompt; `-y` skips DIVERGED; `--force` overwrites.
- [x] Personal global audit: pre-sst- bare names migrated; canonical copies kept outside `~/.claude/skills/` so harness reset is non-destructive.

### Phase 11: auto-promote mode (closed)

Close the within-chain learning loop: looping chains can now consume their own supervisor's improvements within the same run. `auto-promote: off|proprietary|all` (default `proprietary`) routes supervisor output by scope; `SKILL.patch.md` sidecar is a drop-in replacement (full frontmatter+body, one per skill, overwritten each cycle). `bin/apply-skill-patch.py` works around the `.claude/skills/**` write-prompt gap; runner uses `--permission-mode bypassPermissions` + `--max-turns 100`.

- [x] Schema enum + supervisor rewrite (routing table; transferable sanitization extended to direct overwrites; verdict structure records direct-vs-sidecar + sanitization footers).
- [x] `sst-promote-skill-proposal` rewritten for sidecar promotion; transferable re-sanitized before every promote.
- [x] All pre-existing transferable chains gained explicit `auto-promote:` (YAML 1.1 quirk: bare `off` quoted to avoid bool coercion).
- [x] First end-to-end loop consuming its own supervisor's improvements: `~/Dev/sdrai/.skill-runs/2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` (iter_01 filed should-fix; iter_02 closed it; iter_03 rate-limit-killed mid-review per Phase 13).
- [x] Supervisor evolution under empirical pressure: §3 change-intent table requires every patch line to cite a transcript line (v1.2.0→v1.3.0); inlined `apply-skill-patch.py` invocation under §3 routing table to prevent Edit/Write fallback (v1.3.0→v1.4.0); snapshot-write merged manifest after every skill so supervisor reads a real `MANIFEST.json` (v1.4.0→v1.4.1); generic `.claude/skills/`-only carve-out in `sst-dev-cycle`/`sst-dev-review` pre-flights so supervisor-managed dirt doesn't trip the reviewer.

### Phase 12: efficiency wins + multi-loop chain driver

A 9-cycle / $73.59 / 4-hour empirical pass on `sdrai-cycle` (~95% spec completion) surfaced three structural inefficiencies: (a) same-root TODO items fragmenting across cycles, each paying full review+supervisor overhead; (b) the supervisor burning ~$1 confirming "clean" when the run-log shows no finding; (c) `loop:` mode shipped (Phase 9) but unused, every cycle still manually re-invoked. Phase 12 closes those plus introduces the missing top-level role: a chain driver that watches one multi-iteration run and pipes progress over Telegram in real time.

- [x] **`sst-dev-cycle` §1 same-root carveout** (v1.0.3→v1.1.0): when 2+ Next-up entries carry `(group with <root>)` AND combined diff <~300 LoC AND files disjoint, bundle into one cycle.
- [x] **`sst-dev-review` §4 same-root tagging** (v1.1.0→v1.2.0): findings sharing one root cause append `(group with <root>)`; single-finding "groups" untagged; spec entries never tagged (one-checkbox-per-finding preserved).
- [ ] **`sst-supervisor` fast-path on clean.** §0.5 keyword-scan pre-check + clean-deploy verification short-circuits to a one-line verdict when transcripts are clean and no escalation flag exists. Saves ~$0.70 × 50% of cycles. Never fast-paths when prior verdict says escalate.
- [x] **Adopt loop mode on at least one transferable chain.** Shipped `chains/dev-cycle-with-review-looped.yaml` (loop:3, auto-promote:all); v1.0.0→v1.1.0 added `loop-delay-random: [60, 3600]` matching proprietary defaults.
- [x] **`sst-chain-driver` (formerly `sst-orchestrator`).** New top-level skill + `bin/drive-chain.py` helper. Spawns `bin/skill-chain.py --chain N --loop N` as subprocess; streams stdout verbatim; fires Telegram at session-start, iter-close, rate-limit pause/resume, halt-request, session-end. SIGINT halts at next safe boundary. Proprietary `<persona>-chain-driver` supplies defaults (chain, loop, budget cap, telegram-env, label).
- [ ] **Acceptance: ≥25% cost reduction on multi-iter runs vs Phase 11 baseline ($73.59 / 9 cycles)**.

Closed review follow-up: `bin/orchestrate-chain.py` looping detection only consulted `--loop` CLI override, not the chain YAML's `loop:` field; fixed by deriving `looping = True` from the observed `===== iteration N =====` banner.

### Phase 13: rate-limit pause-and-resume (closed)

Multi-iter `--loop N` chains crossing the rolling 5h Anthropic quota mid-run now sleep until reset + jitter[15,60]s, then resume the killed skill in place. Three error categories handled (five_hour, primary, extra_usage); each skill invocation is a fresh subprocess so restart is safe.

- [x] **Detection in `handle_event`**: captures `rate_limit_event` with `status ∈ {exceeded,blocked,reset_required,throttled,rejected}` into `skill_record["rate_limit_signal"]`; field-alias resolution for `reset_time`/`retry_after_seconds`. First-fatal-wins. Stderr fallback `RATE_LIMIT_TEXT_RE` for cases where the subprocess died before a clean structured event.
- [x] **Pause loop in `run_skill_with_retry`**: parses reset_time + jitter; falls back to retry_after; finally exponential-backoff `300×2^attempt`. Per-attempt `.txt`/`.jsonl` archived to `<stem>.retry-N.{ext}`. Ctrl-C clean through the outer try/except.
- [x] **Configurability**: schema gained `on-rate-limit` (`fail|pause|pause-with-cap`, default pause), `max-rate-limit-pause-seconds` (default 28800/8h), `max-pauses-per-session` (default 3); CLI flags mirror; CLI > YAML > defaults.
- [x] **Manifest**: `iter_manifest["rate_limit_pauses"]` (one record per pause); top-level `manifest["rate_limit_policy"]` records resolved policy.
- [x] **Repeat-pause safeguard**: aborts at `retry_count >= max_pauses` with `record["rate_limit_aborted"] = "max_pauses_reached"`; `pause-with-cap` adds `"max_pause_seconds_exceeded"`.
- [x] **Chain-driver hook**: `bin/drive-chain.py` parses `[rate-limit]` banners, fires Telegram on pause + resume + abort variants.
- [x] **Acceptance**: verified live on 2026-04-25 in `2026-04-25T13-36-00Z_skill-set-cycle/iter_03` (real five_hour quota crossing; sleep 6811.5s = parsed reset + jitter; retry session at wake_at exactly; chain finished all 3 iters; manifest records full timeline).

Live-failure follow-ups closed 2026-04-25 (status-enum gap added `rejected`; text-fallback regex extended for `you're out of (extra )?usage`; localized-clock parser branch for `7:50pm (Asia/Tokyo)`-style; `[FAIL] (success)` label disambiguation; joint-fire merge condition for structured-signal-with-text-extracted-reset). 28 inline scenario tests cover the matrix.

### Phase 14: supervisor completion invariant + run-dir hygiene

12-cycle / 14-iteration sdrai-cycle pass surfaced three failure modes tied to supervisor's completion contract: early-exit between sub-skill invocation and verdict write, orphaned drafts across iter boundaries, and `apply-skill-patch.py --backup` cruft accumulation.

- [x] **Completion invariant** (sst-supervisor §8 Exit gate, v1.4.1→v1.5.0): before return, every file in `<run-dir>/drafts/` is either applied via `apply-skill-patch.py` OR named in verdict's `[deferred]` block; verdict file exists even on clean runs (a clean-but-no-verdict run is indistinguishable from partial-completion failure).
- [x] **Iter-boundary drafts sweep** (sst-supervisor §0.6): when `MANIFEST.iteration > 1`, scan `<base>/iter_<NN-1>/drafts/`. Each orphan = manager-injected finding citing prior iter's transcript line; routed per current chain's auto-promote, re-sanitized if transferable, deleted on consumption. Older orphans flagged in `## Notes for the manager`.
- [x] **Drop `--backup` from `apply-skill-patch.py` invocations** (supervisor templates); one-shot cleanup of historical `.bak` files.
- [x] **`bin/clean-skill-runs.py`**: idempotent housekeeping. Defaults dry-run; `--apply` deletes. Removes empty pre-Phase-11 `proposals/` skeletons, `*SKILL.md.bak` files, stale `drafts/` (default 14d, configurable). Approved-root safety; drafts-age-by-newest-file-mtime.
- [x] **`loop-delay-random: [min, max]`** on schema + runner: `random.uniform` per iteration boundary; `MANIFEST.loop` records `delay_random_range` + `delay_samples`. Mutual-exclusion against `loop-delay`. Proprietary `skill-set-cycle.yaml` defaults `[60, 3600]`.
- [ ] **Acceptance**: kill -TERM mid-supervisor + verify self-heal (one combined test for the four mechanisms above).

### Phase 15: rename for clarity (closed)

Three skills shared the "orchestrator"/"manager" naming axis and routinely got confused. Renamed two ambiguous skills; `sst-manager` unchanged.

| Old name | New name | What it does |
|---|---|---|
| `sst-orchestrator` | `sst-chain-driver` | drives ONE multi-iter chain run; spawns `bin/skill-chain.py`, watches stdout, posts Telegram |
| `sst-agent-orchestrator` | `sst-skill-router` | inside ONE user request, decomposes the task, picks sub-skills, sequences them |

- [x] Skill renames (1.0.0→1.1.0); body prose + frontmatter updated; "Naming history" footer on both.
- [x] Helper rename `bin/orchestrate-chain.py` → `bin/drive-chain.py`; runtime tags `[chain-driver]`; Telegram body prefixes updated.
- [x] Cross-references updated; stale deployed copies cleared (install-skills.sh intentionally doesn't delete target-only dirs).
- [x] Validator clean (24 skills + 6 chains).

### Phase 16: long-running chain pattern + chain selection docs (closed)

Phase 12/15 shipped chain-driver mechanism + one multi-iter chain. Phase 16 fills two adjacent shapes: unattended overnight drain + missing chain-selection docs.

- [x] **`chains/dev-cycle-overnight.yaml`** (transferable; loop:0, loop-delay-random [300,7200], auto-promote:all). Designed for chain-driver wrap so budget cap is the safety net.
- [x] **Proprietary `.claude/chains/skill-set-overnight.yaml`** mirrors the transferable with skill-set-* skills + auto-appended supervisor.
- [x] **README "Chains shipped here" subsection** + "Pick the dev chain by intent" guide; CLAUDE.md "Choosing a chain" + proprietary chain-driver "Common overrides" extended.
- [x] Validator clean (24 skills + 7 chains).

### Phase 17: empty-queue handling

A mature framework reaches steady state (`Next up` empty AND every SPEC `[ ]` is `[x]`). Without spec'd behavior, dev skills invent speculative work, re-pick with new framing, or scope-creep, each empty iter still costs ~$8. An overnight `--loop 0` would burn the full budget cap on speculative work. Phase 17 closes the hole at the dev skill pre-flight AND the chain runner level.

- [x] **`sst-dev-cycle` §0 step 6 empty-queue bail** (v1.1.0→v1.2.0): exit 0 cleanly with stdout `[no-work] queue empty and spec fully checked; nothing to do`. Explicit MUST-NOT list against scope-creep.
- [x] **Chain runner sentinel recognition**: `NO_WORK_SENTINEL_RE` line-anchored regex; `handle_event` scans assistant-text only; first-match-wins per skill; tool inputs/results bypassed (supervisor reading example sentinels does not false-trigger). `run_iteration` skips remaining skills, `main()` sets `manifest["loop"]["terminated_by"] = "no_work_bail"` and breaks the outer loop.
- [x] **Documentation** in README "Loop mode" + CLAUDE.md "Choosing a chain" + `templates/SPEC.md` "Empty-queue bail" appendix.
- [ ] **Acceptance**: real steady-state run; `[no-work]` printed, no commit, loop aborts after first empty iter, `MANIFEST.loop.terminated_by == "no_work_bail"`, cumulative cost bounded by pre-flight reads (~$0.10-0.30) rather than full ~$8 iter, chain-driver session-end Telegram labels stop as "no-work bail".

### Phase 18: chain-bound bot worker lifecycle + manager no-spam

Telegram worker (`bin/manager-bot.py`) was running persistently under tmux/systemd, producing inbound-noise between chain runs (worker keeps acking queued commands with stale state) plus operational overhead. Phase 18 binds the worker lifecycle to the chain driver; pairs with manager-side rule forbidding re-notify on persistent paused-job state.

- [x] **`sst-manager` no-repeat-pause-notify rule** (v1.0.0→v1.1.0).
- [x] **`sst-chain-driver` Worker-lifecycle section** (v1.1.0→v1.2.0).
- [x] **CLAUDE.md + README docs** updated with chain-bound (recommended) vs always-on (legacy) patterns.
- [x] **`bin/drive-chain.py` implementation**: `_persona_from_env_file`, `_tmux_session_exists`, `_read_live_pid`, `_probe_worker`, `_start_worker` (with `fcntl.flock` against simultaneous drivers, TOCTOU-safe re-probe inside lock), `_stop_worker` (idempotent). `main()` start/end blocks gated on `--telegram-env` + `worker_started_by_us` so externally-managed workers are untouched.
- [ ] **Acceptance**: real `/skill-set-chain-driver` run with no pre-existing worker; verify start/stop, externally-managed-worker idempotency, simultaneous-driver flock behavior, manager-while-no-chain digest correctness.

**Review follow-ups (open):**

- [ ] [should-fix] Phase 18 docs commit modified two transferables (`skills/framework/sst-chain-driver/SKILL.md:151,158`, `skills/framework/sst-manager/SKILL.md:193`) and embedded skill-set's internal phase number ("Phase 18", "the inbound-noise pattern Phase 18 exists to fix") inside prose that consuming projects install. Commit body documents no sanitize pass; CLAUDE.md is explicit about never bypassing sanitization. Fix: rerun `sst-sanitize-transferable`; rephrase to drop framework-internal phase numbering.

- [ ] [should-fix] `skills/dev/sst-dev-cycle/SKILL.md:148` and `skills/dev/sst-dev-review/SKILL.md:202`: "Never append Co-Authored-By" rule sits BELOW the §6 commit-template heredoc, so a model copying the heredoc downward stops before reading it. Empirical: 7 of 11 cycle commits in recent surface carry the trailer despite explicit ban. Fix: hoist the rule INSIDE the heredoc template (e.g. `# NEVER append Co-Authored-By trailers below this line`) or move it above the heredoc.

- [ ] [should-fix] `bin/drive-chain.py:473-518` + `:736-744`: simultaneous chain-driver runs share a single worker process. Only the starter has `worker_started_by_us=True`; concurrent drivers adopt with False and rely on it for inbound. When the starter finishes first, `_stop_worker` kills the tmux session out from under any concurrent driver, dropping `/pause` `/resume` `/status` coverage. Item 5d's flock-on-start verification doesn't cover cleanup overlap. Fix: refcount in `~/.claude/state/manager-bot.pid.lock`, or at session-end probe for any other live `drive-chain.py` bound to the same `--telegram-env` before killing.

Closed review follow-ups: `[no-work]` sentinel false-positive gating via per-skill `git_sha_before` / `git_sha_after` comparison + `_no_work_bail_should_fire` helper; session-end Telegram parse failure resolved by defaulting `TELEGRAM_PARSE_MODE` to plain in `bin/drive-chain.py` `main()`; `bin/drive-chain.py` direct CLI invocation now resolves proprietary defaults via `--profile <persona>` (reads `<persona>-chain-driver/SKILL.md`'s `## Configured defaults` yaml block as a layer below CLI args, mirroring slash-command-agent behavior); `--max-cycles N` silent no-op surfaced at startup (when the resolved chain loop count is finite and `<= N`, prints `[chain-driver] note: --max-cycles N is a no-op; ...` so terminal users don't read the no-effect cap as a silent success), and `--help` text for `--max-cycles` now says it is the safety net for multi-iter runs.

### Phase 19: per-skill model-tier + effort + item-difficulty-aware routing

Goal: maximize productive throughput within the user's existing Claude Max subscription by routing each chain iteration to the cheapest model AND lowest effort tier that can handle the picked item, while preserving Opus + xhigh effort for items that genuinely need them. Today the `claude-code` harness hardcoded `--model opus` and passed no `--effort`, so every skill in every cycle burned Max quota at Opus rates AND xhigh adaptive-thinking depth (Opus 4.7's implicit CLI default), regardless of whether the work needed either. The Max quota is denominated in compute-equivalents that roughly mirror API pricing: Sonnet ~5× cheaper per token than Opus, Haiku ~15× cheaper; effort scales response-token output (text + tool calls + extended thinking) so dropping `xhigh` → `high` saves ~30%, `high` → `medium` another ~30%, `medium` → `low` another ~50% on bounded mechanical tasks. Combined: routing review-class work to Sonnet+medium and mechanical work to Haiku+low roughly cuts quota burn per iter to ~25-35% of an all-Opus+xhigh baseline (~3-4× more iters in the same Max window). No paid API spillover; this is purely sharper use of the existing subscription.

Two parallel knobs (model and effort), each with two architectural layers, applied in `max()`:

1. **Per-skill `model-floor:` and `effort-floor:`** in SKILL.md frontmatter. The lowest tier this skill is ever allowed to run on, regardless of item difficulty. Defaults by skill class:
   - **Opus floor + xhigh effort-floor**: `sst-supervisor`, `sst-sanitize-transferable` (framework-level routing / leak detection; floors never drop).
   - **Sonnet floor + high effort-floor**: `sst-dev-cycle`, `sst-dev-review`, `sst-skill-router`, `sst-editorial-pass`, `sst-iterative-writer`, `sst-literary-critic` (substantial reasoning; structured tasks).
   - **Haiku floor + medium effort-floor**: `sst-translator`, `sst-fact-checker`, `sst-promote-skill-proposal`, `sst-output-selector`, `sst-llm-judge-ranker`, `sst-email-control-loop`, `sst-setup-telegram` (mechanical / well-bounded; Haiku doesn't support effort but the floor is recorded for clarity and forward-compat with future-tier Haiku models that may).
   Proprietary counterparts mirror their transferable's floors unless they have a stricter need.

2. **Per-item difficulty label** on every SPEC `[ ]` and TODO `Next up` entry. Required (validated). Three values mapping to BOTH model and effort:
   - `[easy]` → Haiku tier + `low` effort (mechanical, well-bounded, no judgment-bleeding-edge).
   - `[medium]` → Sonnet tier + `medium` effort (substantial reasoning, multi-step, structured).
   - `[hard]` → Opus tier + `high` effort (novel design, cross-file reasoning, architectural decisions, anything spec-closing on a complex phase).

Resolution rule (per skill, per iter): `effective_model = max(item.model_tier, skill.model_floor)` and `effective_effort = max(item.effort_tier, skill.effort_floor)` where the `max` is over `{haiku < sonnet < opus}` and `{low < medium < high < xhigh < max}` respectively. Each axis resolves independently; both pass to the harness as separate `--model` and `--effort` flags. So `[easy]` item picked by `sst-supervisor` runs Opus + xhigh (both floors win); `[hard]` item picked by `sst-translator` runs Opus + high (item overrides both); `[easy]` item picked by `sst-dev-cycle` runs Sonnet + high (floors win for both axes since dev-cycle is Sonnet/high). Anti-fork rule still binds at both axes.

Routing flow: chain runner pre-parses the next item's difficulty BEFORE invoking the iter's first skill (the dev), so all skills in the iter inherit the same difficulty tier (clamped by their respective floors). The dev skill's actual pick is the source of truth; if the dev skill picks something different than the pre-parse expected (rare; only happens when the item-priority rule diverges from the literal Next-up top), the runner logs the mismatch but does not retroactively re-invoke at a different tier. The picked-difficulty sentinel format mirrors Phase 17's `[no-work]`: dev skill prints `[picked-difficulty: hard]` (or easy/medium) on a single line; the runner captures this as the authoritative tier for any skill that runs AFTER the dev.

Item label format:
- SPEC: `- [ ] [hard] <description>` (the leading `- [ ]` is the markdown checkbox; the second bracket is the difficulty).
- TODO `Next up`: `- [hard] <description>. Reason: ...` (no checkbox; difficulty is the leading bracket).
- Closed SPEC items (`- [x]`) and `Just shipped` entries don't need labels (historical).

- [x] **Quick-win: pin `--effort high` as harness explicit default.** `ClaudeCodeHarness.build_command` in `bin/skill-chain.py` now passes `--effort high` so Opus 4.7 (whose CLI implicit default is `xhigh`) downshifts to the API-standard default. Neutral on Opus 4.6 / Sonnet 4.6 (where `high` is already the implicit default). Saves Max-quota on routine cycles without quality risk; per-item difficulty-aware override layers on top once Phase 19's runner work lands. ~5 LoC + an inline comment explaining the rationale.
- [ ] **Schema: `model-floor:` + `effort-floor:` fields on SKILL.md frontmatter.** Both optional. `model-floor:` enum `opus | sonnet | haiku` (default `opus`); `effort-floor:` enum `low | medium | high | xhigh | max` (default `high`). Validator (`bin/validate-frontmatter.py`) surfaces invalid values.
- [ ] **Handoff-doc contract: difficulty labels REQUIRED on every open SPEC item and TODO Next-up entry.** Update `templates/SPEC.md` + `templates/TODO.md` with the label format and one example per tier. Update `sst-dev-cycle` §0 pre-flight to fail with `[bad-label] item missing difficulty` if it picks an unlabeled item (graceful degradation: warn-and-default-to-`[medium]` for the first cycle after the contract bump, then upgrade to hard fail).
- [ ] **Backfill labels in this repo's `docs/SPEC.md` and `docs/TODO.md`.** Tag every existing open `- [ ]` SPEC item with `[easy|medium|hard]` based on user judgment; tag every Next-up entry. One-time migration; commit alongside the contract bump.
- [ ] **Runner: per-skill model + effort resolution.** `Harness.build_command(skill_name, model=None, effort=None)` accepts optional model and effort arguments; each defaults to the skill's `model-floor:` / `effort-floor:`. `bin/skill-chain.py`'s `run_skill` reads SKILL.md frontmatter, resolves `effective_model = max(iter_difficulty_tier, skill.model_floor)` and `effective_effort = max(iter_difficulty_tier, skill.effort_floor)`, passes both to `build_command`. The hardcoded `--model opus` + `--effort high` in `ClaudeCodeHarness.build_command` become `--model <effective_model>` + `--effort <effective_effort>`.
- [ ] **Runner: difficulty pre-parse + sentinel capture.** At iter start, runner reads `docs/TODO.md > Next up` first entry's `[difficulty]` bracket (or `docs/SPEC.md` first `[ ]` item if Next up is empty), stores as `iter_manifest["difficulty"]`. If absent, defaults to `medium` with a warning. After dev skill exits, runner scans assistant-text for `\[picked-difficulty:\s*(easy|medium|hard)\]` (mirror of Phase 17's `NO_WORK_SENTINEL_RE`); if present, overrides `iter_manifest["difficulty"]` for subsequent skills in the iter.
- [ ] **`sst-dev-cycle` updates.** §0 pre-flight reads picked item's difficulty label; emits `[picked-difficulty: <tier>]` to stdout once before any tool call. §1 selection-priority guidance documents how to interpret labels (don't downgrade hard to easy to fit a quota; if budget tight, escalate to user via TODO comment instead).
- [ ] **`sst-dev-review` updates.** §4 review-output documents that follow-up items appended to TODO Next up MUST carry a difficulty label (review skill assigns it based on the finding's nature; should-fix on prose nit = `[easy]`, blocker on architecture = `[hard]`).
- [ ] **Tag every transferable + proprietary SKILL.md with `model-floor:` + `effort-floor:`.** Per the floors listed in the preamble. One commit; sanitize-transferable judgment pass on each transferable.
- [ ] **Documentation in README.md + CLAUDE.md.** New "Model-tier routing" section in README explaining the floor + difficulty + max() rule with a worked example. CLAUDE.md "Choosing a chain" gains a one-paragraph note that Max throughput is now ~2-4× higher per cycle window; supervisor / transferable rewrites still consume Opus quota at the old rate.
- [ ] **Acceptance**: a `/skill-set-chain-driver --loop 3` run with mixed-difficulty items (at least one `[easy]`, one `[medium]`, one `[hard]` across the three iters). Confirm: (a) per-iter MANIFEST records `difficulty` field; (b) per-skill `model_usage` block reflects the resolved model AND effort (Opus + xhigh for hard items + supervisor; Sonnet + medium for medium + reviews; Haiku + low where applicable); (c) cumulative quota burn per iter is ~25-35% of an all-Opus + all-xhigh baseline (target: ≥50% reduction); (d) supervisor still runs Opus + xhigh regardless of item difficulty (floor invariant on both axes); (e) chain-driver session-end Telegram body reports per-iter difficulty + model + effort breakdown.

**Review follow-ups (open: schedule as the next `/skill-set-dev` cycle):**
- [ ] [should-fix] `bin/skill-chain.py:337` (commit 869232b): quick-win pinned `--effort high` for ALL skills. Phase 19 declares `sst-supervisor` and `sst-sanitize-transferable` have `effort-floor: xhigh` (preamble line 293, acceptance item d at line 322), and the resolution-rule paragraph at line 303 explicitly says "supervisor stays opus + xhigh regardless of item label". Pre-quick-win these two skills ran at xhigh (Opus 4.7 CLI implicit default); post-quick-win they run at high. Items #1, #4, #7 of this Phase land sequentially via the dev cycle's one-item-per-cycle picker, so the gap window where the framework's two safety-critical skills run below their declared floor is indeterminate (multiple cycles). Proposed fix: temporary skill-name carveout in `ClaudeCodeHarness.build_command` keeping `--effort xhigh` for skills whose name matches `sst-supervisor`, `sst-sanitize-transferable`, or `*-supervisor` (proprietary counterparts), until items #4 + #7 land and the per-skill effort-floor resolution becomes the source of truth; remove the carveout in the same commit that closes #4 to avoid two competing precedence rules.

### Phase 20 (deferred): `goose-cerebras` harness + portability proof

Phase 1's "Harness scope" promised additional harnesses drop in by adding a `Harness` subclass; this phase ships a non-Claude binary (Block's Goose CLI talking to Cerebras Inference's free tier of GPT-OSS-120B or Qwen3-235B). Goose natively reads `~/.claude/skills/` so skills are consumed unchanged. Bridging requires a ~150 LoC Python shim translating Goose's `message`/`notification`/`error`/`complete` event vocabulary to Claude Code's `system/init`/`assistant`/`user`/`result` shape; cost is set to `0.0` (true for free tier). Demoted from primary "24/7 productivity fix" because Phase 19's per-skill model-tier routing within Max delivers the bulk of the throughput win without a new harness; Phase 20 becomes the future supplement when free-tier capacity matters (e.g. when Phase 19 throughput is insufficient AND mechanical-skill work has been cleanly identified).

Anti-fork constraint when this lands: harness MUST NOT be used for `*-supervisor` or any skill that rewrites another `SKILL.md`. Per-skill `allowed-harnesses:` frontmatter (or runtime allowlist) enforces it.

Items deferred until after Phase 19 ships and a real cost / throughput baseline is measured.
