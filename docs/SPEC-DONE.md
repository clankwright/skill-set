# skill-set SPEC — completed phases (DONE)

All phases here have every item complete (`[x]`). Active work lives in `docs/SPEC.md`.

### Phase 1: skeleton + log capture (closed)

- [x] 1.1 Master repo scaffolding: LICENSE, README, `.gitignore`, `templates/SPEC.md`, `templates/TODO.md`.
- [x] 1.2 `bin/skill-chain.py` chain runner with `--log-dir` writing `MANIFEST.json` + per-skill `.jsonl`/`.txt`.
- [x] 1.3 `Harness` abstraction (claude-code MVP) + `--harness` flag + `$AGENT_HARNESS` env.
- [x] 1.4 Smoke-tested via real dev-cycle from a consuming project; consuming `TODO.md` bootstrapped from template.

### Phase 2: linkage + globals lift (closed)

- [x] 2.1 `transferable:` field added to consuming proprietary skills; canonical homes for transferables moved to `skills/`.
- [x] 2.2 Handoff-doc read/update contract baked into transferable preambles.
- [x] 2.3 `schema/skill-set.schema.json` validator written.
- [x] 2.4 User runs `bin/install-skills.sh --force` to deploy all updated transferable skills into `~/.claude/skills/` (24 skills installed; 5 stale-diverged skills force-updated: sst-dev-cycle v1.4.1, sst-dev-review v1.4.5, sst-supervisor v1.8.2, sst-chain-driver v1.2.1, sst-manager; 8 updated, 5 new).

### Phase 3: supervisor (closed)

- [x] 3.1 Transferable `sst-supervisor` + first proprietary supervisor in a consuming project.
- [x] 3.2 Auto-append proprietary supervisor in `bin/skill-chain.py`.
- [x] 3.3 `templates/sanitization-guidance.md` + `sst-sanitize-transferable` skill (LLM-judgment, not regex).

### Phase 4: proposal promotion (closed)

- [x] 4.1 `~/.claude/skills/promote-skill-proposal/SKILL.md` shipped.

### Phase 5: manager + Telegram bot (closed)

- [x] 5.1 `sst-manager` (transferable) + first proprietary manager.
- [x] 5.2 `bin/notify-telegram.sh` (outbound) + `bin/manager-bot.py` (long-poll inbound) + service-unit / rc.d templates.

### Phase 6: open-source (closed)

- [x] 6.1 Public GitHub at `git@github.com:toadlyBroodle/skill-set.git`; `main` tracks `origin/main`.
- [x] 6.2 CI: frontmatter validator + sanitization-footer-on-PR enforcement; CONTRIBUTING.md.

### Phase 7: portability proof (closed)

- [x] 7.1 Built second skill-set in non-dev domain (lead-gen, content-ops, infra) by lifting `sst-lead-generation`, `sst-domain-seo-research`, `sst-linkedin-easy-apply`, `sst-linkedin-networking`.
- [x] 7.2 `sst-supervisor` + `sst-manager` work unmodified across both domains; validator passes uniformly.

### Phase 8: lift long-running agents into transferables (closed)

12-agent framework ported as 12 target skills (11 transferable, 1 proprietary). Each lift converted a Python-agent module into a SKILL.md natural-language procedure; rate-limit / tool helpers mapped to harness primitives. Each lift passed `sst-sanitize-transferable` + validator pre-commit.

- [x] 8.1: `sst-web-research`, `sst-fact-checker`, `sst-output-selector`.
- [x] 8.2: `sst-iterative-writer`, `sst-literary-critic`, `sst-editorial-pass`.
- [x] 8.3: `sst-llm-judge-ranker`, `sst-translator`.
- [x] 8.4: `sst-email-control-loop`, `sst-skill-router` (originally `sst-agent-orchestrator`; renamed in Phase 15).
- [x] 8.5: `sst-short-video-generator`, `sst-social-promoter` + first proprietary counterpart.

Phase 8.6 (end-to-end smoke acceptance) moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-86--end-to-end-smoke).

### Phase 9: optional chain looping (closed)

Opt-in iteration on the chain runner so a single chain definition can repeat its full skill sequence N times (or until non-supervisor failure). Long-running skills tick through several queued items in one sitting; supervisor still runs once per iteration.

- [x] 9.1 `loop` + `loop-delay` schema fields (defaults 1 / 0; backward-compat); `--loop` + `--loop-delay` CLI flags (CLI > YAML); `--loop 0` runs until failure or Ctrl-C.
- [x] 9.2 Iteration-per-subdir log layout (`iter_NN/MANIFEST.json`) when `loop != 1`; flat layout preserved for `loop == 1`. Top-level `MANIFEST` carries `iterations: [...]` + `loop: {requested, delay_seconds, completed}` when looping.
- [x] 9.3 README "Chain YAML fields" + "Loop mode" sections.
- [x] 9.4 `chains/dev-cycle-with-review-looped.yaml` shipped (loop:3, auto-promote:all) as the multi-iter reference; baseline `dev-cycle-with-review` unchanged.

### Phase 10: proprietary-naming enforcement + sst-/ssp- migration (closed)

Distinct-name rule + `sst-<base>` / `ssp-<base>` prefix convention + install-time safety net for hand-edited targets.

- [x] 10.1 Validator rejects proprietary skills where `name == transferable`; transferables in this repo's `skills/` MUST carry `sst-` prefix.
- [x] 10.2 Renamed every transferable bare → sst- (cross-references in SKILL bodies, chain YAMLs, docs, templates).
- [x] 10.3 `bin/install-skills.sh` DIVERGED-target detection: interactive diff prompt; `-y` skips DIVERGED; `--force` overwrites.
- [x] 10.4 Personal global audit: pre-sst- bare names migrated; canonical copies kept outside `~/.claude/skills/` so harness reset is non-destructive.

### Phase 11: auto-promote mode (closed)

Close the within-chain learning loop: looping chains can now consume their own supervisor's improvements within the same run. `auto-promote: off|proprietary|all` (default `proprietary`) routes supervisor output by scope; `SKILL.patch.md` sidecar is a drop-in replacement.

- [x] 11.1 Schema enum + supervisor rewrite (routing table; transferable sanitization extended to direct overwrites; verdict structure records direct-vs-sidecar + sanitization footers).
- [x] 11.2 `sst-promote-skill-proposal` rewritten for sidecar promotion; transferable re-sanitized before every promote.
- [x] 11.3 All pre-existing transferable chains gained explicit `auto-promote:` (YAML 1.1 quirk: bare `off` quoted to avoid bool coercion).
- [x] 11.4 First end-to-end loop consuming its own supervisor's improvements: `~/Dev/sdrai/.skill-runs/2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3`.
- [x] 11.5 Supervisor evolution under empirical pressure: §3 change-intent table requires every patch line to cite a transcript line; inlined `apply-skill-patch.py` invocation; snapshot-write merged manifest; generic `.claude/skills/`-only carve-out.

### Phase 12: efficiency wins + multi-loop chain driver (closed)

A 9-cycle / $73.59 / 4-hour empirical pass on `sdrai-cycle` surfaced three structural inefficiencies: (a) same-root TODO items fragmenting across cycles, (b) the supervisor burning ~$1 confirming "clean", (c) `loop:` mode shipped (Phase 9) but unused. Phase 12 closes those plus introduces a chain driver that watches one multi-iteration run and pipes progress over Telegram in real time.

- [x] 12.1 **`sst-dev-cycle` §1 same-root carveout** (v1.0.3→v1.1.0): when 2+ Next-up entries carry `(group with <root>)` AND combined diff <~300 LoC AND files disjoint, bundle into one cycle.
- [x] 12.2 **`sst-dev-review` §4 same-root tagging** (v1.1.0→v1.2.0): findings sharing one root cause append `(group with <root>)`.
- [x] 12.3 **`sst-supervisor` fast-path on clean** (v1.5.0→v1.6.0): §0.5 gates §1-7 on four eligibility signals all reading clean; on all-pass writes minimal verdict and returns. Saves ~$0.70-1.45 per zero-finding cycle.
- [x] 12.4 **Adopt loop mode on at least one transferable chain.** Shipped `chains/dev-cycle-with-review-looped.yaml`.
- [x] 12.5 **`sst-chain-driver` (formerly `sst-orchestrator`).** New top-level skill + `bin/drive-chain.py` helper.
- [x] 12.6 [medium] **Acceptance: ≥25% cost reduction on multi-iter runs vs Phase 11 baseline ($73.59 / 9 cycles)**. Closed 2026-04-27: $5.88/iter across 19 post-fast-path iters (28.1% reduction); post-Phase-19-routing sample measured $5.77/iter (29.5% reduction).

**Review follow-ups (closed):**
- [x] 12.7 [medium] [should-fix] §0.5 condition (1) cross-run prior-verdict lookup glob only matched single-iter shape; fixed by unioning both glob shapes and picking the most recent.

Closed review follow-up: `bin/orchestrate-chain.py` looping detection only consulted `--loop` CLI override, not the chain YAML's `loop:` field; fixed by deriving `looping = True` from the observed `===== iteration N =====` banner.

### Phase 13: rate-limit pause-and-resume (closed)

Multi-iter `--loop N` chains crossing the rolling 5h Anthropic quota mid-run now sleep until reset + jitter[15,60]s, then resume the killed skill in place. Three error categories handled (five_hour, primary, extra_usage); each skill invocation is a fresh subprocess so restart is safe.

- [x] 13.1 **Detection in `handle_event`**: captures `rate_limit_event` with `status ∈ {exceeded,blocked,reset_required,throttled,rejected}`. Stderr fallback `RATE_LIMIT_TEXT_RE`.
- [x] 13.2 **Pause loop in `run_skill_with_retry`**: parses reset_time + jitter; falls back to retry_after; finally exponential-backoff `300×2^attempt`.
- [x] 13.3 **Configurability**: schema gained `on-rate-limit` (`fail|pause|pause-with-cap`, default pause), `max-rate-limit-pause-seconds` (default 28800/8h), `max-pauses-per-session` (default 3).
- [x] 13.4 **Manifest**: `iter_manifest["rate_limit_pauses"]` + top-level `manifest["rate_limit_policy"]`.
- [x] 13.5 **Repeat-pause safeguard**: aborts at `retry_count >= max_pauses`.
- [x] 13.6 **Chain-driver hook**: `bin/drive-chain.py` parses `[rate-limit]` banners, fires Telegram on pause + resume + abort variants.
- [x] 13.7 **Acceptance**: verified live on 2026-04-25 in `2026-04-25T13-36-00Z_skill-set-cycle/iter_03` (real five_hour quota crossing; sleep 6811.5s; retry session at wake_at exactly; chain finished all 3 iters).

Live-failure follow-ups closed 2026-04-25 (status-enum gap added `rejected`; text-fallback regex extended for `you're out of (extra )?usage`; localized-clock parser branch; `[FAIL] (success)` label disambiguation). 28 inline scenario tests cover the matrix.

### Phase 14: supervisor completion invariant + run-dir hygiene (closed)

12-cycle / 14-iteration sdrai-cycle pass surfaced three failure modes tied to supervisor's completion contract: early-exit between sub-skill invocation and verdict write, orphaned drafts across iter boundaries, and `apply-skill-patch.py --backup` cruft accumulation.

- [x] 14.1 **Completion invariant** (sst-supervisor §8 Exit gate, v1.4.1→v1.5.0): before return, every file in `<run-dir>/drafts/` is either applied via `apply-skill-patch.py` OR named in verdict's `[deferred]` block; verdict file exists even on clean runs.
- [x] 14.2 **Iter-boundary drafts sweep** (sst-supervisor §0.6): when `MANIFEST.iteration > 1`, scan `<base>/iter_<NN-1>/drafts/`. Each orphan routed per current chain's auto-promote, re-sanitized if transferable, deleted on consumption.
- [x] 14.3 **Drop `--backup` from `apply-skill-patch.py` invocations**; one-shot cleanup of historical `.bak` files.
- [x] 14.4 **`bin/clean-skill-runs.py`**: idempotent housekeeping. Defaults dry-run; `--apply` deletes.
- [x] 14.5 **`loop-delay-random: [min, max]`** on schema + runner: `random.uniform` per iteration boundary; `MANIFEST.loop` records `delay_random_range` + `delay_samples`. Proprietary `skill-set-cycle.yaml` defaults `[60, 3600]`.

Phase 14.6 (kill -TERM acceptance) moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-146--kill--term-mid-supervisor-self-heal).

### Phase 15: rename for clarity (closed)

Three skills shared the "orchestrator"/"manager" naming axis and routinely got confused. Renamed two ambiguous skills; `sst-manager` unchanged.

| Old name | New name | What it does |
|---|---|---|
| `sst-orchestrator` | `sst-chain-driver` | drives ONE multi-iter chain run; spawns `bin/skill-chain.py`, watches stdout, posts Telegram |
| `sst-agent-orchestrator` | `sst-skill-router` | inside ONE user request, decomposes the task, picks sub-skills, sequences them |

- [x] 15.1 Skill renames (1.0.0→1.1.0); body prose + frontmatter updated; "Naming history" footer on both.
- [x] 15.2 Helper rename `bin/orchestrate-chain.py` → `bin/drive-chain.py`; runtime tags `[chain-driver]`; Telegram body prefixes updated.
- [x] 15.3 Cross-references updated; stale deployed copies cleared.
- [x] 15.4 Validator clean (24 skills + 6 chains).

### Phase 16: long-running chain pattern + chain selection docs (closed)

Phase 12/15 shipped chain-driver mechanism + one multi-iter chain. Phase 16 fills two adjacent shapes: unattended overnight drain + missing chain-selection docs.

- [x] 16.1 **`chains/dev-cycle-overnight.yaml`** (transferable; loop:0, loop-delay-random [300,7200], auto-promote:all).
- [x] 16.2 **Proprietary `.claude/chains/skill-set-overnight.yaml`** mirrors the transferable.
- [x] 16.3 **README "Chains shipped here" subsection** + "Pick the dev chain by intent" guide; CLAUDE.md "Choosing a chain" + proprietary chain-driver "Common overrides" extended.
- [x] 16.4 Validator clean (24 skills + 7 chains).

### Phase 17: empty-queue handling (closed)

A mature framework reaches steady state (`Next up` empty AND every SPEC `[ ]` is `[x]`). Without spec'd behavior, dev skills invent speculative work. Phase 17 closes the hole at the dev skill pre-flight AND the chain runner level.

- [x] 17.1 **`sst-dev-cycle` §0 step 6 empty-queue bail** (v1.1.0→v1.2.0): exit 0 cleanly with stdout `[no-work] queue empty and spec fully checked; nothing to do`.
- [x] 17.2 **Chain runner sentinel recognition**: `NO_WORK_SENTINEL_RE` line-anchored regex; `handle_event` scans assistant-text only; first-match-wins per skill. `main()` sets `manifest["loop"]["terminated_by"] = "no_work_bail"` and breaks the outer loop.
- [x] 17.3 **Documentation** in README "Loop mode" + CLAUDE.md "Choosing a chain" + `templates/SPEC.md` "Empty-queue bail" appendix.

Phase 17.4 (empty-queue bail acceptance) removed from FUTURE-WORK.md; superseded by 17.5.

- [x] 17.5 [easy] [should-fix] Bail fired incorrectly when `## Next up` had only `[low]`-priority entries. Fix: explicit "Priority is not a bail criterion" paragraph (bail requires ZERO `- ` entries regardless of priority bracket); added `[low]`-priority mention to §1 step 1.

### Phase 18: chain-bound bot worker lifecycle + manager no-spam (closed)

Telegram worker (`bin/manager-bot.py`) was running persistently under tmux/systemd, producing inbound-noise between chain runs. Phase 18 binds the worker lifecycle to the chain driver. **Note: Phase 35.6 later reversed the chain-bound decision** — since Phase 35 the bot is a pure dispatcher (every command spawns a one-time manager process that re-reads state), so the inbound-noise risk no longer applies and the worker is now recommended to run always-on.

- [x] 18.1 **`sst-manager` no-repeat-pause-notify rule** (v1.0.0→v1.1.0).
- [x] 18.2 **`sst-chain-driver` Worker-lifecycle section** (v1.1.0→v1.2.0).
- [x] 18.3 **CLAUDE.md + README docs** updated with chain-bound (recommended) vs always-on (legacy) patterns.
- [x] 18.4 **`bin/drive-chain.py` implementation**: `_persona_from_env_file`, `_tmux_session_exists`, `_read_live_pid`, `_probe_worker`, `_start_worker` (with `fcntl.flock`, TOCTOU-safe re-probe), `_stop_worker` (idempotent).

Phase 18.5 (chain-bound worker lifecycle acceptance) moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-185--chain-bound-worker-lifecycle-acceptance).

**Review follow-ups (closed):**
- [x] 18.6 [easy] [should-fix] Phase 18 docs commit embedded framework-internal phase numbers in two transferables; fixed inline, validator clean.
- [x] 18.7 [easy] [should-fix] "Never append Co-Authored-By" rule sat BELOW the commit-template heredoc and was being skipped (7 of 11 cycle commits carried the trailer). Closed by hoisting the rule ABOVE the heredoc.
- [x] 18.8 [hard] [should-fix] Simultaneous chain-driver runs share a single worker; only the starter had `worker_started_by_us=True`. Fix: refcount in `~/.claude/state/manager-bot.pid.lock` + session-end probe.
- [x] 18.9 [easy] [should-fix] `_any_other_driver_using_persona` docstring mismatched call-site interpretation; fixed by aligning prose to actual behavior.
- [x] 18.10 [medium] [should-fix] Worker-lifecycle stale-recycle path wiped the refcount of concurrent drivers; fixed by reading refcount under flock before recycling.
- [x] 18.11 [hard] [should-fix] Stale-recycle TOCTOU gap closed by new `_recycle_stale_worker_if_unused(descriptor)` helper holding `WORKER_LOCK_FILE` across the refcount read AND the tmux kill + state-file unlinks.

Closed review follow-ups: `[no-work]` sentinel false-positive gating via per-skill `git_sha_before`/`git_sha_after` comparison; session-end Telegram parse failure resolved by defaulting `TELEGRAM_PARSE_MODE` to plain; `bin/drive-chain.py` `--profile <persona>` resolution; `--max-cycles N` silent no-op surfaced at startup; `bin/notify-telegram.sh` auto-sources `$TELEGRAM_ENV_FILE`.

### Phase 19: per-skill model-tier + effort + item-difficulty-aware routing (closed)

Maximize productive throughput within the Claude Max subscription by routing each chain iteration to the cheapest model AND lowest effort tier that can handle the picked item, while preserving Opus + xhigh for items that need them. Two parallel knobs (model and effort), each with two architectural layers, applied in `max()`.

Per-skill floors by skill class:
- **Opus floor + xhigh effort-floor**: `sst-supervisor`, `sst-sanitize-transferable`.
- **Sonnet floor + high effort-floor**: `sst-dev-cycle`, `sst-dev-review`, `sst-skill-router`, `sst-editorial-pass`, `sst-iterative-writer`, `sst-literary-critic`.
- **Haiku floor + medium effort-floor**: `sst-translator`, `sst-fact-checker`, `sst-promote-skill-proposal`, `sst-output-selector`, `sst-llm-judge-ranker`, `sst-email-control-loop`, `sst-setup-telegram`.

Per-item difficulty label: `[easy]` → Haiku+low; `[medium]` → Sonnet+medium; `[hard]` → Opus+high. Resolution rule: `effective_model = max(item.model_tier, skill.model_floor)` and `effective_effort = max(item.effort_tier, skill.effort_floor)`.

- [x] 19.1 **Quick-win: pin `--effort high` as harness explicit default.** Downshifts Opus 4.7 from `xhigh` implicit default to API-standard `high`.
- [x] 19.2 **Schema: `model-floor:` + `effort-floor:` fields on SKILL.md frontmatter.**
- [x] 19.3 **Handoff-doc contract: difficulty labels REQUIRED on every open SPEC item and TODO Next-up entry.**
- [x] 19.4 **Backfill labels in this repo's `docs/SPEC.md` and `docs/TODO.md`.**
- [x] 19.5 **Runner: per-skill model + effort resolution.** `Harness.build_command` now takes optional `model=` + `effort=` keyword arguments. Per-skill resolution in `_resolve_skill_route(skill_name, iter_difficulty, cwd)`.
- [x] 19.6 **Runner: difficulty pre-parse + sentinel capture.** `_resolve_iter_difficulty(cwd)` runs at iter start; `[picked-difficulty: <tier>]` captured from dev skill's output as authoritative tier.
- [x] 19.7 **`sst-dev-cycle` updates.** §1 "Difficulty label & sentinel emit" closing step; `model-floor: sonnet` + `effort-floor: high` frontmatter.
- [x] 19.8 **`sst-dev-review` updates** (v1.2.1 → v1.3.0). §4 requires `[<difficulty>]` bracket on every entry; new "Assigning difficulty from the finding's nature" sub-section.
- [x] 19.9 **Tag every transferable + proprietary SKILL.md with `model-floor:` + `effort-floor:`.** 12 transferables + 2 proprietary counterparts tagged.
- [x] 19.10 [easy] **Documentation in README.md + CLAUDE.md.** New `## Model-tier routing` top-level section; CLAUDE.md "Choosing a chain" gains a closing "Throughput note (Phase 19 routing)" paragraph.

Phase 19.11 (model-tier routing acceptance) moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-1911--model-tier-routing-acceptance).

**Review follow-ups (closed):**
- [x] 19.12 [medium] [should-fix] `.claude/skills/skill-set-dev-review/SKILL.md:5` — Proprietary body diverged from transferable; synced via `bin/apply-skill-patch.py`, bumped to v1.1.4.

### Phase 21: user feedback channel (Telegram → manager → supervisor) (closed)

Until now, the manager→supervisor steering channel was one-way and passive. Phase 21 adds an explicit user→manager→supervisor control path: a new `/feedback <message>` Telegram command captures the full user message verbatim, the manager routes it to `~/.claude/state/manager-feedback.md`, and the supervisor reads that file as authoritative steering.

- [x] 21.1 [hard] **`bin/manager-bot.py`: `/feedback <message>` command.** Adds `feedback` to `KNOWN_COMMANDS`. `queue_feedback(body, chat_id)` writes a queue file with same-second collision protection. `/help` text gains the new command.
- [x] 21.2 [hard] **`sst-manager` v1.2.0 → v1.3.0: route feedback to `manager-feedback.md`.** Manager NEVER paraphrases — pure capture-and-route. Feedback distinguished from `manager-guidance.md`.
- [x] 21.3 [hard] **`sst-supervisor` v1.6.1 → v1.7.0: read `manager-feedback.md` as authoritative steering.** Conflict resolution explicit: feedback > manager-guidance; `auto-promote` mode > feedback. Anti-fork rules still bind.

**Review follow-ups (closed):**
- [x] 21.4 [easy] [should-fix] Backfill `Just shipped` entry for `chains/dev-cycle-with-review-looped.yaml` + `chains/dev-cycle-overnight.yaml` loop-delay-random tightening.

### Phase 22: difficulty-windowed multi-item batching (closed)

Until now, `sst-dev-cycle` §1 picked one top-of-queue item per cycle. Iterations under `[easy]` and `[medium]` items routinely closed with substantial budget left. Phase 22 reframes the picking unit as a coherent batch sized to the picked-difficulty's context-window band.

Token windows: `[easy]` → 100-200k; `[medium]` → 200-300k; `[hard]` → 400-500k. Batching rules: primary = top-of-`Next up`; batch additions pulled from BOTH `Next up` and SPEC `[ ]` when at-or-below the primary's difficulty, related, fits the band, and ships as one coherent commit.

- [x] 22.1 [hard] **`sst-dev-cycle` §1 batching contract + `[batch-pick]` sentinel.** v1.3.1 → v1.4.0.
- [x] 22.2 [hard] **`skill-set-dev` proprietary mirror.** v1.2.4 → v1.3.0.
- [x] 22.3 [medium] **`sst-dev-review` batch-coherence axis.**
- [x] 22.4 [medium] **`skill-set-dev-review` mirror of the coherence axis.**
- [x] 22.5 [medium] **`sst-dev-review` batch-sizing axis.** Per-iter check distinct from coherence; tags findings with `[batch-sizing]`.
- [x] 22.6 [medium] **`skill-set-dev-review` mirror of the sizing axis.**
- [x] 22.7 [hard] **`sst-supervisor` batch-window refinement loop.** §3.5 self-tune section (trigger evaluation, refinement decision, write the refinement patch, stable-termination bookkeeping, anti-fork constraints) + §0.5 fast-path eligibility condition #5. v1.7.0 → v1.8.0.
- [x] 22.8 [hard] **`skill-set-supervisor` mirror of the refinement loop.** v1.0.1 → v1.1.0; `transferable-version` bumped to `>=1.8.0`.

Phase 22.9 (batch-window acceptance) moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-229--batch-window-acceptance).

**Review follow-ups (closed):**
- [x] 22.10 [medium] [should-fix] Batch-sizing axis referenced wrong MANIFEST key path (`model_usage.input_tokens` instead of `model_usage[<model>].inputTokens`); fixed in both surfaces.
- [x] 22.11 [easy] [should-fix] Batch-sizing axis used `cacheReadInputTokens` (cumulative across all turns) instead of `cacheCreationInputTokens` (peak proxy); fixed.
- [x] 22.12 [easy] [should-fix] §3.5.1's `[batch-sizing]` finding-extraction grep never matched in practice; loosened regex and added discoverable summary line in dev-review §6 transcript output.
- [x] 22.13 [easy] [should-fix] `[easy]` band upper edge (200k) below observed full-chain consumption; raised to 250k for review-side full-chain.
- [x] 22.14 [easy] [should-fix] Dev-only vs total-chain calibration trap: dev-cycle window targets calibrated for dev skill alone but review measures full chain; reconciled via prose note + band adjustments.
- [x] 22.15 [easy] [should-fix] `[medium]` and `[hard]` band edges still carried dev-only numbers after [easy] fix; raised medium upper to 430k, hard upper to 630k.
- [x] 22.16 [medium] [should-fix] Flat (loop=1) session MANIFEST omitted `difficulty`, `difficulty_source`, `rate_limit_pauses`; promoted these from `iterations_collected[0]` into session manifest.

### Phase 23: `sst-wiki-curator` transferable skill (closed)

A new transferable skill under `skills/research/sst-wiki-curator/` that builds and maintains LLM-curated knowledge wikis for prose domains. Two modes: scaffold (create a new wiki; pick variant minimal | middle | scripted) and ingest/maintain.

- [x] 23.1 [hard] **Author `skills/research/sst-wiki-curator/SKILL.md`.** v1.0.0. Inline sanitize: must-fix=0.
- [x] 23.2 [medium] **Acceptance**: scaffold + ingest validated on a throwaway dir.
- [x] 23.3 [easy] **Install via `bin/install-skills.sh -y`** so the skill becomes harness-discoverable.

**Review follow-ups (closed):**
- [x] 23.4 [easy] [should-fix] B.9 prose fix used inline sanitize evaluation; closed by retroactive `sst-sanitize-transferable` run on current working-tree state (must-fix=0, should-fix=0, nit=1 — Karpathy citation retained as public technical citation).

**v1.1.0 features (retroactive — all shipped in c20ff96):**
- [x] 23.5 [easy] **Synthesis page kind (`kind: synthesis`).** Three promotion criteria; A.5b synthesis-page template added to Mode A scaffold.
- [x] 23.6 [easy] **`drafts/` working layer.** Optional fourth layer added for in-progress synthesis.
- [x] 23.7 [easy] **Domain-schema extension pattern.** Five-step pattern; longevity `evidence_tier` worked example.
- [x] 23.8 [easy] **Navigation axis: aggregating by domain field.** Three reference examples (longevity, edge-llm, ai-empowerment).
- [x] 23.9 [easy] **Reading paths in `index.md` and schema spec.** Optional `## Reading paths` section (3–7 steps).
- [x] 23.10 [easy] **Middle-variant `lint.py` template (`A.6.5`).** ~80-LoC stdlib-only `scripts/lint.py`.
- [x] 23.11 [easy] **Mode D: umbrella parent-dir index.** Walks sibling wikis, writes `<parent-dir>/index.md` with auto-generated table.
- [x] 23.12 [easy] **Variant-boundary lint check + conditional `LINT-REPORT.md`.**
- [x] 23.13 [easy] **Optional source-papers table (`A.5a`).** When to add: 5+ paper pages.
- [x] 23.14 [easy] **Contradiction handling worked example.** NAD⁺ precursors: preclinical vs. 2025 long-COVID RCT.
- [x] 23.15 [easy] **Adjacent patterns section + Mode A pre-scaffold gate.** Four anti-patterns named with worked examples.
- [x] 23.16 [easy] **`profile:` axis (personal/publishable) orthogonal to `variant:`.** Profile × variant interactions table covers all 6 combos.

### Phase 24: smart-manager feedback routing (Telegram → on-demand manager → supervisor) (closed)

Today's feedback path is mechanical: bot writes a queue file, manager drains the queue and prepends the user body verbatim. Phase 24 moves interpretation upstream into the manager and lets the manager decide where each piece of user feedback lands. Bot spawns the manager out-of-band on each `/feedback` so routing happens within seconds.

- [x] 24.1 [easy] **Two-file collapse: `manager-feedback.md` + `manager-guidance.md` → `manager-notes.md` with source-tagged headings.** `sst-manager` v1.4.0 → v1.5.0, `sst-supervisor` v1.8.2 → v1.9.0.
- [x] 24.2 [medium] **`bin/manager-write-state.py` helper.** Pure-Python stdlib-only; three modes covering tempfile+fsync+rename atomicity and idempotency markers.
- [x] 24.3 [hard] **Smart manager on-demand routing.** Four legal outcomes: direct queue item, SPEC addition, soft steering (manager-translated), refuse/clarify. `sst-manager` v1.6.2 → v1.7.0; `sst-supervisor` v1.9.0 → v1.10.0.
- [x] 24.4 [medium] **Bot subprocess spawn on `/feedback`.** `MANAGER_SKILL_NAME` env var picks the persona. Spawn uses `start_new_session=True` + `subprocess.Popen` (non-blocking).
- [x] 24.5 [medium] **Chain-runner pre-iter drain fallback.** `bin/skill-chain.py` calls `bin/manager-write-state.py --drain-feedback-queue` at the start of every iter.

Phase 24.6 (`/feedback` four-outcome acceptance) moved to [docs/FUTURE-WORK.md](FUTURE-WORK.md#phase-246--feedback-four-outcome-acceptance).

**Review follow-ups (closed):**
- [x] 24.7 [medium] [should-fix] `sst-manager` v1.6.0 prose directed the manager to call `bin/manager-write-state.py` but `bin/install-skills.sh` delivers only SKILL.md files; added fallback blocks detecting helper absence.
- [x] 24.8 [easy] [should-fix] [batch-sizing] undersized cycle that didn't batch a compatible queue item; resolved by bundling.
- [x] 24.9 [easy] [should-fix] `sst-manager §1` fallback instructed `bin/install-skills.sh --install sst-manager` which doesn't copy bin/ companions; replaced with explicit `cp bin/manager-write-state.py <project>/bin/`.
- [x] 24.10 [easy] [should-fix] `README.md` `install-skills.sh` description updated for update-only semantics.
- [x] 24.11 [easy] [should-fix] Phase 24 chain-runner drain fallback `Next up` entry not removed after SPEC `[x]` flip; deleted.
- [x] 24.12 [easy] [should-fix] `spawn_on_demand_manager` leaked fd in long-running bot; wrapped `open` in `with` block.

### Phase 25: planner-mode manager + measurable objectives (closed)

The dev loop only progresses when a human (or a review/supervisor follow-up) writes a concrete `[ ]` SPEC item. There is no path from "high-level objective" → "queued work item" without that authoring step. Phase 25 closes that gap by promoting `sst-manager` from observer to *planner* when the queue is dry.

- [x] 25.1 [hard] **Reframe `objectives.md` to measurable criteria with executable checks.** Each objective becomes a numbered criterion with a one-line description AND a check expression (shell or file/metric).
- [x] 25.2 [hard] **`sst-manager --plan` mode.** Picks 1–3 highest-gap criteria and drafts candidate `Next up` items as `[unconfirmed:<id>]`. Planner re-entry rule: one outstanding batch at a time.

**Review follow-ups (closed):**
- [x] 25.3 [easy] [should-fix] §Score-against-objectives's dangling cross-reference to "§Planner mode"; rewrote to reference capability instead of section.
- [x] 25.4 [medium] [should-fix] `cycles-clean check` shell-check never matched actual verdict format; rewrote to extract line after `## Outcome`.
- [x] 25.5 [easy] [should-fix] `cycles-clean check` glob missed root-level verdicts; extended to cover both `iter_*/` and root paths.

### Phase 26: stable sub-item IDs + ID-addressable feedback (closed)

Phase 24's smart-manager routing accepts arbitrary `/feedback` bodies. Phase 26 makes SPEC sub-items individually addressable by giving each one a stable ID of the form `<phase>.<n>`. Numbering is append-only-with-letter-inserts.

- [x] 26.1 [medium] **sub-item numbering across SPEC.md.** Number every existing sub-item as `<phase>.<n>` (1-indexed within each phase block). Once assigned, an ID never moves. Validator extension checks SPEC for ID uniqueness within each phase block.
- [x] 26.2 [medium] **ID-addressed `/feedback` commands.** Three forms: `add <ID> to TODO: <text>`, `remove <ID>`, `modify <ID>: <delta>`. Each maps to a fifth pre-resolved outcome bypassing LLM interpretation.

**Review follow-ups (closed):**
- [x] 26.3 [easy] [should-fix] `validate_spec_ids()` flagged duplicates but never flagged bullets missing an ID entirely; added complementary check.
- [x] 26.4 [medium] [should-fix] `remove <ID>` did not also remove a corresponding `## Next up` entry; made removal atomic across both files.
- [x] 26.5 [easy] [should-fix] Validator regex patterns used `[ x]` (lowercase only); changed to `[ xX]`.
- [x] 26.6 [easy] [should-fix] `sst-dev-review` TODO-entry template embedded no spec item ID; updated to embed ID as leading token.

### Phase 27: `FUTURE-WORK.md` contract integration (closed)

Phase 27 wires `docs/FUTURE-WORK.md` into the four core skills and their proprietary mirrors. Contract: dev-cycle reads but never picks from it; review MUST route acceptance/smoke-test findings there instead of `Next up`; supervisor MAY suggest items belong there; manager planner mode excludes it from gap scoring.

- [x] 27.1 [medium] **`sst-dev-cycle` FUTURE-WORK.md read.** v1.4.3→v1.4.4.
- [x] 27.2 [medium] **`sst-dev-review` FUTURE-WORK.md routing.** v1.4.9→v1.5.0.
- [x] 27.3 [medium] **`sst-supervisor` FUTURE-WORK.md awareness.** v1.10.1→v1.11.0.
- [x] 27.4 [medium] **`sst-manager` FUTURE-WORK.md exclusion.** v1.9.0→v1.10.0.
- [x] 27.5 [medium] **Proprietary mirrors updated.** skill-set-dev v1.3.3→v1.3.4, skill-set-dev-review v1.2.8→v1.2.9, skill-set-supervisor v1.3.0→v1.3.1, skill-set-manager v1.5.0→v1.5.1.
- [x] 27.6 [easy] **`templates/FUTURE-WORK.md` template added.**
- [x] 27.7 [easy] **`CLAUDE.md` "Handoff docs" section updated** to list `docs/FUTURE-WORK.md` as step 3.

**Review follow-ups (closed):**
- [x] 27.8 [easy] [should-fix] `sst-dev-review §5` `git add` not updated for FUTURE-WORK.md; fixed in both transferable and proprietary mirror.
- [x] 27.9 [medium] [should-fix] Phase 27 used "Inline sanitize verdict" on 4 transferable SKILL.md edits; added explicit "Sanitize gate" rule to `sst-dev-cycle`.
- [x] 27.10 [easy] [should-fix] `sst-dev-review` halt guard said "two files" but §4 routes to three; extended to three including FUTURE-WORK.md.
- [x] 27.11 [easy] [should-fix] Retroactive `/sst-sanitize-transferable` run on f90e930 bypass.
- [x] 27.12 [easy] [should-fix] Retroactive `/sst-sanitize-transferable` run on d1a3a7e bypass.
- [x] 27.13 [easy] [should-fix] Added explicit "Inline assessment does not satisfy this requirement" prohibition.
- [x] 27.14 [easy] [should-fix] Retroactive `/sst-sanitize-transferable` run on 7d7eb87 (the commit that introduced the prohibition itself).

### Phase 28: multi-project bot conventions (single shared bot serving multiple personas) (closed)

A shared Telegram bot serving multiple personas needs every outbound message to carry an unambiguous persona label and every inbound command to disambiguate which persona it targets.

- [x] 28.1 [medium] **`TELEGRAM_LABEL` env var on `bin/notify-telegram.sh`**: when set non-empty, prepend `[<label>]\n\n` to the body. `bin/drive-chain.py` sets `TELEGRAM_LABEL=$args.label` in subprocess env.
- [x] 28.2 [medium] **`/projects` bot command on `bin/manager-bot.py`**: list known personas + their project tokens + their watched-projects roots. Filesystem-driven discovery.
- [x] 28.3 [hard] **Hoist multi-project routing convention from proprietary `cm-manager` into transferable `sst-manager`**: project-token-as-first-arg rule + per-project pause files + refusal-reply format references dynamic list from 28.2's `/projects`.

**Review follow-ups (closed):**
- [x] 28.4 [medium] [should-fix] `_discover_manager_personas` didn't filter out transferable skill files; fixed by parsing frontmatter and skipping files without `transferable:` key.
- [x] 28.5 [easy] [should-fix] `/help` and README documented non-agnostic commands without project token; updated to show `<project>` where required.
- [x] 28.6 [easy] [should-fix] empty-body `/feedback` error missing project token; updated string.
- [x] 28.7 [medium] [should-fix] `/status` ignored project token; made persona-aware by filtering `DIGESTS_DIR` for `<persona>_*.txt` files.
- [x] 28.8 [easy] [should-fix] `sst-manager` truncation hint said "run /status for full digest" but `/status` requires a token; updated to `run /status <persona> for full digest`.

### Phase 29: rate-limit session resume (closed)

When `run_skill_with_retry` retried a skill after a rate-limit pause, it was always starting a cold subprocess, silently abandoning the prior session's in-flight context. The `session_id` was available but never threaded back into the retry invocation.

- [x] 29.1 [medium] **Session resume on rate-limit retry.** `Harness.build_command` + `ClaudeCodeHarness.build_command` gain `resume_session_id`; when set, harness prepends `--resume <id>` and uses `"continue"` as the prompt. 49→55 tests green.

**Review follow-ups (closed):**
- [x] 29.2 [medium] [should-fix] Session-id threading had no integration test; added test patching `run_skill` to return rate-limit + assert resume id pass-through.
- [x] 29.3 [easy] **Retroactive spec item: post-pause jitter in `run_skill_with_retry` (commit 3f1d716).** Threads `loop_delay`/`loop_delay_random` through `run_iteration` into `run_skill_with_retry`; samples human-shaped post-resume delay before the next `run_skill` call.

### Phase 30: collapse per-project managers into a single operator-level manager (closed)

The proprietary `<persona>-manager` pattern treats each project as its own management surface. In practice the proprietary is a thin config-only wrapper — the transferable `sst-manager` does all the actual work. Phase 30 collapses the pattern: one operator-level `<operator>-manager` listing every watched project.

- [x] 30.1 [medium] **`docs/MANAGER.md` preamble + sst-manager walk-time read**: optional `<watched-project>/docs/MANAGER.md` carrying per-project manager guidance.
- [x] 30.2 [medium] **Multi-project `objectives.md` schema (`## Project: <name>` sections)**: each scored bullet under a project section uses that project's path as the `cwd` for the shell check.
- [x] 30.3 [hard] **Migration guide + framework support for operator-level manager collapse**: `docs/migration-single-manager.md` operator runbook; `_discover_manager_personas` gained operator-level support via `operator-level: true` key; legacy per-project managers continue to work. +8 tests.

### Phase 31: HUMAN.md handoff doc for active human-only blockers (closed)

The framework has SPEC.md, TODO.md, and FUTURE-WORK.md. None is the right home for prerequisite human actions the cycle is waiting on. Phase 31 introduces `docs/HUMAN.md`, with its own ID space (`H<phase>.<n>`), urgency-ordered sections (`## Blocking` / `## High` / `## Medium` / `## Low` / `## Done`), and write contracts on supervisor + dev-review + manager.

- [x] 31.1 [easy] **`templates/HUMAN.md` skeleton.**
- [x] 31.2 [medium] **`sst-supervisor` HUMAN.md write contract**: §5b "Route to HUMAN.md for human-only blockers". APPEND only, never close.
- [x] 31.3 [medium] **`sst-dev-review` HUMAN.md routing**: §4 "Route first" decision tree gains third bucket. Halt guard bumped from "three files" to "four files".
- [x] 31.4 [medium] **`sst-manager` HUMAN.md read + on-demand write**: added as fourth outcome to on-demand routing.
- [x] 31.5 [medium] **`sst-manager` periodic oversight HUMAN.md digest section**: "Human-action blockers" section above "Per-project progress".
- [x] 31.6 [medium] **`sst-manager` HUMAN.md delta-detection + Telegram alerts**: immediate alert via `bin/notify-telegram.sh` with `TELEGRAM_LABEL=<persona>` for new H-IDs.
- [x] 31.7 [easy] **`sst-manager` auto-verify pass on `[x]` items**: run `Verify:` check; on pass move to `## Done`, on fail flip back to `[ ]`.
- [x] 31.8 [medium] **`sst-dev-cycle` `[blocked-on-human]` sentinel**: scan HUMAN.md open `## Blocking` entries; emit sentinel and bail if picked SPEC ID is blocked.
- [x] 31.9 [easy] **Validator + format check**: ID format `^H\d+\.\d+$`, mandatory five sections, each open `[ ]` has `Blocks:` line.
- [x] 31.10 [easy] **Cross-reference dahrouge.com SPEC items to H3.1**.

Anti-fork: the four-doc convention (SPEC + TODO + FUTURE-WORK + HUMAN) is the framework default but not mandatory — a project with no human-only blockers may omit HUMAN.md; skills must treat its absence as "no blockers", not "error".

**Review follow-ups (closed):**
- [x] 31.11 [medium] [should-fix] `blocked_on_human` bail path had no integration test; added test patching `run_skill` to return record with `blocked_on_human` set.
- [x] 31.12 [easy] [should-fix] `CLAUDE.md` "Handoff docs" section listed only three steps; added step 4 for HUMAN.md.

### Phase 32: route unpromoted transferable sidecars into HUMAN.md (closed)

Phase 31 gave the supervisor a write contract for project-level human-only blockers. One human-only action it still did not route there is its own output: under `auto-promote: proprietary` (default) a supervisor-authored transferable improvement lands as a `SKILL.patch.md` sidecar that only a human can promote.

- [x] 32.1 [medium] **Supervisor routes unpromoted transferable sidecars into HUMAN.md (`## High`, not `## Blocking`).** Auto-clears when `/sst-promote-skill-proposal` flips it `[x]` on promotion.

**Review follow-ups (closed):**
- [x] 32.2 [medium] [should-fix] `/sst-promote-skill-proposal` not updated for HUMAN.md auto-clear; added scan after promotion for matching `Verify: test ! -e` entries and call `bin/notify-human-md.sh`.
- [x] 32.3 [easy] [should-fix] `§6b` match criterion said "absolute path of the sidecar before the rename" but supervisor writes tilde notation; replaced with "the sidecar path in the same form used when discovering it (do not expand `~` before comparing)".

### Phase 33: Telegram notification on every HUMAN.md change (closed)

Phase 31.6 fires a Telegram alert for new `## Blocking` HUMAN.md entries — but only on the manager's periodic cron tick, and only for that one section. Phase 33 adds a shared notification helper and a write-then-notify contract on every HUMAN.md writer.

- [x] 33.1 [medium] **`bin/notify-human-md.sh` helper.** Thin wrapper over `bin/notify-telegram.sh`: diffs against last-notified snapshot, composes brief delta message, sends, updates snapshot. Idempotent.
- [x] 33.2 [medium] **Write-then-notify contract on HUMAN.md writers.** `sst-supervisor §5b`, `sst-dev-review §4`, `sst-manager` on-demand §1 and §31.7 auto-verify pass.
- [x] 33.3 [easy] **Anti-fork carve-out for the notification call.** Narrow explicit exception to the no-curl rule.
- [x] 33.4 [easy] **Message format + template note.** `[<project>] HUMAN.md: <delta summary>` documented in `templates/HUMAN.md`'s "How this file evolves" appendix.
- [x] 33.5 [medium] **Tests.** Delta detection (add / move / flip), idempotent no-op, graceful skip on missing env, snapshot update. Stub `notify-telegram.sh` so tests never hit the network.

### Phase 34: Telegram env fallback to skill-set base dir for consuming projects (closed)

`bin/notify-telegram.sh`, the chain-driver, the manager's Telegram-env resolution, and the Phase 33 helper all resolve the Telegram env via the per-persona convention. Consuming projects without their own persona env got nothing. Phase 34 adds a base-dir fallback: `~/Dev/skill-set/telegram.env` (gitignored).

- [x] 34.1 [easy] **Resolution chain in `bin/notify-telegram.sh`.**
- [x] 34.2 [easy] **Resolution chain in `bin/drive-chain.py` and `sst-manager`.** Documented in `skill-set/CLAUDE.md`.
- [x] 34.3 [easy] **`bin/notify-human-md.sh` inherits the same chain.**
- [x] 34.4 [easy] **Gitignore + README note.**
- [x] 34.5 [easy] **Tests.** Each helper's resolution chain.

**Review follow-ups (closed):**
- [x] 34.6 [easy] [should-fix] `bin/drive-chain.py`:872-878 base-dir fallback had no test coverage; added tests covering (a) base-dir fires, (b) `--telegram-env` beats base-dir, (c) caller-exported `TELEGRAM_BOT_TOKEN` beats base-dir.

### Phase 35: Telegram bot as thin dispatcher; commands fulfilled by one-time manager spawns (closed)

`bin/manager-bot.py` mixed two roles: Telegram long-poll receiver and command fulfiller. Only `/feedback` already spawned a one-time manager via `spawn_on_demand_manager` (Phase 24); other commands were answered inline by the bot, which had no project cwd / no per-project filesystem context / no per-persona env. Phase 35 collapses fulfillment into the manager skill: every project-scoped command (`/status`, `/objectives`, `/proposals`, `/promote`, `/pause`, `/resume`, `/feedback`, `/ping` when targeted at a persona) becomes a one-time `claude --print "/<persona>-manager --process-command <queue-file>"` spawn scoped to the target project's cwd. The manager fulfills the command and replies through that project's own `notify-telegram.sh`. The bot shrinks to: validate chat allowlist, parse command, resolve project token → persona → manager skill name + project cwd, write a queue file, spawn the manager, ack the user.

Project-agnostic commands (`/help`, `/projects`, bare `/ping` with no persona token) stay inline in the bot because they require no project context.

- [x] 35.1 [medium] **`sst-manager --process-command <queue-file>` mode.** New invocation mirroring `--process-feedback`. Per-verb handlers: `status`, `objectives`, `proposals`, `promote`, `pause`, `resume`, `ping`. Each handler appends a one-line outcome to `manager-notes.md` and sends Telegram reply.
- [x] 35.2 [medium] **`bin/manager-bot.py` reshape into dispatcher.** Lifted `spawn_on_demand_manager` to general `spawn_manager_for_command`; dropped inline /status, /ping (persona-targeted), /objectives, /proposals, /promote, /pause, /resume implementations. Kept inline only `/help`, `/projects`, bare `/ping`.
- [x] 35.3 [easy] **Project cwd resolution in the dispatcher.** `_discover_manager_personas` returns `{"persona": ..., "projects": [{"path": ..., "name": ...}]}`; dispatcher uses `projects[0]["path"]` as cwd for `spawn_manager_for_command`.
- [x] 35.4 [easy] **`<persona>-manager` proprietary template updated.** Inherits via `transferable: sst-manager`. skill-set-manager v1.5.1→v1.5.2; transferable-version `>=1.15.0`.
- [x] 35.5 [easy] **Bot startup logs surface the new mode.** "on-demand command routing enabled (verbs: status, objectives, proposals, promote, pause, resume, feedback, ping)" when `MANAGER_SKILL_NAME` is set; queue-only fallback when unset.
- [x] 35.6 [medium] **Dispatcher lifecycle: flip to always-on.** Phase 18's inbound-noise objection no longer applies since every spawn re-reads project state. Chain-driver start/stop hooks in `bin/drive-chain.py` retired; CLAUDE.md + README Worker management sections updated to recommend always-on.
- [x] 35.7 [easy] **`bin/notify-telegram.sh` chunk-splits long bodies instead of truncating.** ≤4000-char chunks at newline boundaries, code-fence-safe rebalancing. Removed 3500-char trim in `bin/manager-bot.py handle_command`. +3 tests.
- [x] 35.8 [medium] **Acceptance: round-trip integration test.** `tests/test_manager_bot.py` + `tests/fixtures/stub_claude.py` mock the `claude --print` spawn; parameterized over each verb; assertions on queue file shape, spawn cwd, mock manager content, mock notify-telegram payloads.

**Review follow-ups (closed):**
- [x] 35.9 [easy] [should-fix] commit `3f1d716` added post-pause jitter to `run_skill_with_retry` without a spec item; closed by adding retroactive spec item `29.3`.
- [x] 35.10 [medium] [should-fix] commit `c20ff96` promoted `sst-wiki-curator` v1.1.0 (13 testbed feature phases) without spec items; closed by adding 12 retroactive spec items 23.5–23.16.
- [x] 35.11 [easy] [should-fix] commit `415ac81` touched `sst-dev-review` without "Sanitize: must-fix=0" attestation; closed via retroactive sanitize and spec item 35.12.
- [x] 35.12 [easy] **Retroactive spec item: sst-dev-review template requires `<phase>.<n>` ID before difficulty bracket (commit 415ac81).** v1.5.5→v1.5.6.
- [x] 35.13 [easy] **Tighten `sst-supervisor §0.5.3` transcript keyword scan with word-boundary anchoring.** `\bERROR`, `\bFAIL(ED)?\b`, `\bTraceback\b`, `\bException\b`. v1.13.0→v1.13.1.
- [x] 35.14 [easy] [should-fix] `sst-supervisor` 35.13 change used "Inline sanitize" instead of formal `/sst-sanitize-transferable`; closed via retroactive invocation.
- [x] 35.15 [easy] [should-fix] Closure of 35.11 used "inline sanitize on current body" instead of formal invocation; closed via retroactive `/sst-sanitize-transferable` run.
- [x] 35.16 [easy] [should-fix] `docs/TODO.md:47` — **false positive, no fix needed.** `_DIFFICULTY_BRACKET_RE.search(s)` correctly picks `[medium]` from `- [supervisor] [medium] Phase 36 ...`. Closed without changing the TODO entry.

### Phase 36: runner-level enforcement of dev incomplete-cycle detection (closed)

Five consecutive recurrences of the "sub-skill returns, parent doesn't close" failure pattern exhausted prose-level mitigations. The model treats sub-skill return as cycle terminus regardless of what the prose requires. Phase 36 moves enforcement into the runner: after the dev skill exits with `[ok]` and no commit landed, `run_iteration` checks `docs/TODO.md` for evidence of incomplete work and emits `[contract-violation: incomplete-cycle]`.

- [x] 36.1 [medium] **Incomplete-cycle detection in `bin/skill-chain.py`.** New `_incomplete_cycle_detected(cwd)` helper; check fires after `i==0` (dev) exits with rc==0, sha unchanged, and no no-work/blocked-on-human bail. `main()` sets `manifest["loop"]["terminated_by"] = "contract_violation"`. 7 new tests.

**Review follow-ups (closed):**
- [x] 36.2 [easy] [should-fix] `templates/SPEC.md:117` — added "Incomplete-cycle contract violation" section alongside `no_work_bail` and `blocked_on_human`.
- [x] 36.3 [easy] [should-fix] `templates/SPEC.md:126-133` — corrected JSON example to match runner emission (`"kind": "incomplete-cycle"` not `"reason"`; no `signals` key).


### Phase 37: handoff-doc prose alignment

**Review follow-ups (open — schedule as the next `/ssp-dev` cycle):**
- [x] 37.1 [easy] [should-fix] `docs/SPEC.md:81` — The "SPEC.md shape" description says "Closed phases get a 1-paragraph context + a tight bulleted change log (one line per item, not a paragraph each). Phases that drift toward novella-length should be compressed back" — but commit `77d17de` archived all closed phases to `docs/SPEC-archive.md`. A dev reading line 81 would expect compressed-inline closed phases in SPEC.md, not an archive file. Proposed fix: update the description to say completed phases are archived to `docs/SPEC-archive.md` once closed, with consuming projects keeping closed phases inline (compressed) until the file grows large enough to warrant an archive.

### Phase 38: bounded-item discipline + phase-completion handoff

**Context.** A consuming project (claim_management) burned ~60 commits across three 20-iteration `cm-cycle` runs without ever closing its active phase, because `## Next up` carried an unbounded placeholder (`Phase 2.16 iterative UI/UX polish`) with no falsifiable done-state. Every iter the dev found one more comment/banner to fix, shipped it, and the placeholder survived to win the next pick — defeating the global empty-queue bail (§0 step 6), which only fires when the WHOLE spec is checked. Root cause: the framework permits open-ended items and has no phase-scoped completion handoff. This phase closes both gaps: prevent unbounded items at write time (38.1, 38.2), stop + hand off when a phase genuinely completes (38.3, 38.4), and have the supervisor actively detect-and-mitigate the stuck-item pattern when it recurs (38.5).

- [x] 38.1 [medium] **Writer-skill prose rule: no unbounded items.** In `sst-dev-review` (§4 follow-up filing), `sst-supervisor` (follow-up + TODO writes), and `sst-manager` (planner + feedback routing), add a rule: every SPEC item must name a *specific feature with a falsifiable acceptance criterion*; every TODO item must be a *specific, completable action*. Open-ended / recurring / catch-all items (a task whose description is a standing activity rather than a finite deliverable) are forbidden — a real but unbounded cleanup must be decomposed into concrete enumerated items (each naming its target file/symbol) or not filed. Acceptance: each of the three SKILL.md bodies contains the rule with an explicit forbidden-shape example and a decompose-instead example; `/sst-sanitize-transferable` clean on all three.
- [x] 38.2 [medium] **Validator gate `validate_spec_item_quality`.** Add a check in `bin/validate-frontmatter.py` that fails on any `docs/SPEC.md` or `docs/TODO.md` checkbox bullet whose task text matches an open-ended marker (denylist: the standing-activity words, matched only in the task-description span, NOT inside backticks/quotes — so an item that *mentions* a denylisted word as data, like this very item, does not trip) unless the bullet also enumerates ≥1 concrete target (a file path, symbol, or `<phase>.<n>` reference). Acceptance: new unit tests in `tests/` cover (a) a vague bullet → fail, (b) a vague-word-in-backticks bullet → pass, (c) a concrete bullet → pass; full suite green; the check runs in the existing validator CI entrypoint.
- [x] 38.3 [hard] **`sst-dev-cycle` phase-completion bail.** Before picking (§0/§1), derive the active phase from the SPEC `## Operational scope` branch map (current HEAD branch → phase number). If every SPEC `- [ ]` for that phase is `- [x]` AND no `## Next up` entry is scoped to that phase, fire a new phase-scoped sentinel `[no-work] phase <N> complete on <branch>; awaiting human branch setup for phase <N+1>` and exit 0 without picking/manufacturing work. Distinct from the global empty-queue bail. Acceptance: SKILL.md documents the derivation + sentinel; the chain runner recognizes it as a loop-aborting `[no-work]` variant (confirm `bin/skill-chain.py` sentinel match covers it, add a test if not); a fixture where one phase is fully `[x]` but a later phase has open items still bails on the completed phase rather than scope-creeping.
- [x] 38.4 [medium] **`sst-dev-cycle` HUMAN.md handoff on phase completion.** When the 38.3 bail fires, first append a `docs/HUMAN.md` `## Blocking` entry instructing the human to (1) merge/PR the completed feature branch, (2) create the next phase's `feature/<name>` branch from `origin/test`, (3) add its `## Operational scope` mapping; include a `Verify:` line and a `Blocks:` of the next phase's first SPEC ID; then call `bash bin/notify-human-md.sh <cwd> docs/HUMAN.md`. Idempotent: do not append a duplicate if an open entry for the same completed phase already exists. Acceptance: SKILL.md documents the entry template + idempotency rule; a test (or fixture walkthrough) shows the entry is written once and re-running the bail does not duplicate it.
- [x] 38.5 [medium] **`sst-supervisor` stuck-item detection + mitigation.** Extend the supervisor's existing trailing-window analysis to flag a *stuck unbounded item*: the same `## Next up` / SPEC item (by ID or by normalized description) was picked in ≥3 of the trailing-window iters without its SPEC `- [ ]` flipping to `- [x]`. On detection, the verdict records a `[stuck-item]` finding, and the supervisor (a) appends a `docs/HUMAN.md` `## High` entry recommending the item be decomposed into concrete sub-items or removed, and (b) prepends a manager-notes.md observation so the next manager digest surfaces it. Acceptance: SKILL.md documents the detection threshold + both mitigation writes; a fixture with the same item across 3 iters produces the `[stuck-item]` finding; `/sst-sanitize-transferable` clean.
- [x] 38.6 [medium] **`find_local_supervisor` transferable fallback.** `bin/skill-chain.py`'s supervisor auto-append discovered only a project-local `<cwd>/.claude/skills/*-supervisor/`; projects without a proprietary wrapper (e.g. skill-set itself) silently ran with no supervisor, making the chain YAML's `auto-promote` inert. `find_local_supervisor` now falls back to the transferable `~/.claude/skills/sst-supervisor/` when no proprietary supervisor exists in cwd (proprietary still wins; ambiguous multi-match still returns None with no fallback). 4 new unit tests in `tests/test_skill_chain.py` (prefers-proprietary, falls-back-to-transferable, none-when-neither, multiple-returns-none); full suite 159 green. Filed retroactively per the direct-change convention (implemented outside the dev-cycle in response to a user request).

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 38.7 [easy] [should-fix] [batch-sizing] `docs/TODO.md` Next-up co-batching missed in iter_01 of 2026-05-27T00-00-42Z run — dev used 71k input tokens against the medium band of 200-300k (undersize threshold: 100k); 38.5 [medium] (`sst-supervisor` stuck-item detection) and the manager-bot.service [medium] item in `docs/TODO.md` have no hard dependency on 38.3 and were co-batchable alongside 38.2. Proposed fix: in the next medium-difficulty batch, include 38.5 or a manager-bot medium item as a co-pick when their dependency graph permits.
- [x] 38.8 [easy] [should-fix] [batch-sizing] `bin/manager-bot.py` iter_03 batch undersized — dev used 72k input tokens against the medium band of 200-300k (undersize threshold 100k); window-target was ~220k; the 3rd stated batch item (38.7-close) was a trivial meta flip contributing near-zero tokens, leaving effective 2-item coverage at ~72k. `install-skills.sh` [medium] was available in `docs/TODO.md` as a genuine 3rd item and was not co-batched. Proposed fix: in the next medium batch, co-pick `install-skills.sh` from `docs/TODO.md` alongside the top queued item to bring total context into the 100k+ range; trivial meta/close items do not count toward window-fill.
- [x] 38.9 [easy] [should-fix] `bin/manager-bot.service:35` `ReadWritePaths=%h/.claude/state` too narrow for dispatcher mode — `ProtectSystem=strict` makes all paths outside `ReadWritePaths` read-only, including `~/.claude/projects/` (claude session cache) and project working dirs; the spawned `claude` subprocess in `spawn_manager_for_command` (bin/manager-bot.py:373) inherits this mount namespace and will fail to write session state or skill-run output. `MANAGER_SKILL_NAME=1` is now the default so dispatcher mode is on for any user who follows the "edit only two values" README instructions. Proposed fix: widen `ReadWritePaths` to `%h/.claude %h/Dev/skill-set` (at minimum) or `%h` (broadest, preserves /usr /etc protection), and update the service comment to note that dispatcher mode requires all project-root paths to be listed.
- [x] 38.10 [easy] [should-fix] `bin/manager-bot.service:39` comment says "if those projects live outside %h/Dev/" but the actual covered ancestor is `%h/Dev/skill-set`, not `%h/Dev/` — a user with `MANAGER_SKILLS_EXTRA_ROOTS` pointing to `%h/Dev/claim_management/.claude/skills` would follow the comment literally, not add `%h/Dev/claim_management` to `ReadWritePaths`, and the spawned `claude` subprocess would get silent write failures for run logs and skill state. Proposed fix: replace "outside %h/Dev/" with "outside any already-listed ReadWritePaths entry (e.g. a sibling of %h/Dev/skill-set like %h/Dev/claim_management must be listed explicitly)".
- [x] 38.11 [easy] [should-fix] `tests/test_install_skills.py` — No test covers `--force` overwriting a DIVERGED skill and verifying the `.installed-body` marker is updated to the new source body. If the unconditional marker-write at `bin/install-skills.sh:389` were accidentally moved inside a non-DIVERGED branch, `--force` would silently stop seeding the marker, causing subsequent source bumps to re-appear as DIVERGED and re-breaking the exact regression the feature fixed. Proposed fix: add a `TestMarkerFileManagement` test that sets up a hand-edited target + v1 marker + v2 source, runs with `--force`, then asserts `.installed-body` == v2 body.
- [x] 38.12 [easy] [should-fix] `bin/skill-chain.py:1551` — Phase 36 pass-through condition `i + 1 < len(skills_to_run)` fires when the immediate follower is the auto-supervisor (appended by `main()` when no review skill is explicit in the chain), silently changing the old abort behavior: orphaned dev work stays uncommitted while the supervisor re-reviews the previous HEAD. `test_run_iteration_contract_violation_aborts_without_next_skill` passes `auto_supervisor=None` and covers only `["sst-dev-cycle"]`, missing the `["sst-dev-cycle", "sst-supervisor"]` case. Proposed fix: change `if i + 1 < len(skills_to_run):` to `if i + 1 < len(skills_to_run) and skills_to_run[i + 1] != auto_supervisor:` in `run_iteration`; add a test with `auto_supervisor="sst-supervisor"` and `skills_to_run=["sst-dev-cycle", "sst-supervisor"]` confirming the abort path is taken.

### Phase 40: Remove the sidecar promotion mechanism — supervisors and managers edit base-repo skills directly

**Context.** The `auto-promote` / `SKILL.patch.md` sidecar mechanism — a supervisor writes a transferable improvement as a sidecar plus a `docs/HUMAN.md` `## High` "promote this" entry, which a human later applies via `/sst-promote-skill-proposal` — is high-friction and a recurring source of stale, orphaned, and version-skewed artifacts (e.g. the lngraph H0.1/H0.2/H0.3 churn on a single sidecar; an orphaned `sst-dev-review` sidecar carried untouched across three verdicts). Per user decision (2026-06-02), remove it entirely. New model: `sst-supervisor` and `sst-manager` edit the canonical skill source in the base `~/Dev/skill-set/` repo **directly**, then commit and push — the manager doing so when the user requests it OR it deems it necessary on its own. No sidecars, no `auto-promote` modes, no human promotion step. `/sst-sanitize-transferable` stays as a hard pre-write gate on transferable edits. Historical phase records in `docs/SPEC-archive.md` are a changelog and are left intact; this phase only removes the *active* mechanism. (Inventory of every touch point compiled 2026-06-02; cited per item.)

- [x] 40.1 [hard] **`sst-supervisor` direct-edit rewrite.** In `skills/framework/sst-supervisor/SKILL.md` replace the entire sidecar/auto-promote machinery with a direct-edit-and-commit model targeting the base repo. Remove: the §Inputs `auto-promote` read (step 1); the §3 "direct or sidecar" routing table (lines ~172–197); §4's abort-transferable-write→sidecar fallback (keep `/sst-sanitize-transferable` as a hard gate on the edit itself); §5b HUMAN.md `## High` promotion-entry routing (lines ~355–372); the §6 verdict `sidecar:` fields (line ~413); the §Operating-principles sidecar lines (~23–29) and the §Permissions `apply-skill-patch.py`/`SKILL.patch.md` clauses (~468–502); and the §0.6 drafts→sidecar routing (drafts may still stage a rewrite, but it is applied directly). New contract: to change a SKILL.md the supervisor edits `~/Dev/skill-set/skills/<cat>/<skill>/SKILL.md` directly (sanitize-clean required for transferables), bumps the version, commits, and pushes; proprietary `<cwd>/.claude/skills/*` edits stay direct as today. Acceptance: SKILL.md contains no `sidecar`/`SKILL.patch.md`/`auto-promote`/`apply-skill-patch` string; the direct-edit+commit+push contract is documented with the exact base-repo path; `/sst-sanitize-transferable` clean on `sst-supervisor`; version bumped.
- [x] 40.2 [medium] **`sst-manager` direct-edit authorization + sidecar removal.** In `skills/framework/sst-manager/SKILL.md`: (a) add an explicit instruction that the manager MAY edit skills in the base `~/Dev/skill-set/` repo directly (commit + push) when the user requests it OR the manager deems it necessary on its own; (b) remove the §3b.2 `proposals`/`promote` handlers (lines ~685–703), the §3b discard-sidecar auto-close rule (~333), and every `sidecar`/`/sst-promote-skill-proposal` reference (~23, ~239). Acceptance: no sidecar references remain; the direct-edit authorization is documented with both trigger conditions (user request OR manager judgment); `/sst-sanitize-transferable` clean; version bumped.
- [x] 40.3 [medium] **Drop `auto-promote` from chains + any reader.** Remove the `auto-promote:` field from all 7 `chains/*.yaml` and the explanatory line in `chains/dev-cycle-overnight.yaml`'s description. Grep `bin/skill-chain.py`, `bin/drive-chain.py`, `bin/manager-bot.py`, and any manifest-writing code for `auto-promote`/`auto_promote` and remove/neutralize so the field's absence is never an error. Acceptance: no `chains/*.yaml` carries `auto-promote`; no code references it; a chain run parses cleanly without it.
- [x] 40.4 [medium] **Delete the promotion tooling.** Remove the `skills/framework/sst-promote-skill-proposal/` skill directory and `bin/apply-skill-patch.py`. Update dependents: `skills/framework/sst-sanitize-transferable/SKILL.md` (drop the "apply via `/sst-promote-skill-proposal`" framing at lines ~3, ~14, ~19, ~89, ~115, ~122 — sanitize is now a gate on a direct edit by whoever edits); `templates/HUMAN.md` (delete the example pending-sidecar entry, lines ~39–49); `templates/sanitization-guidance.md` (~74); `bin/manager-bot.py` `/promote` help (~456); `bin/clean-skill-runs.py` sidecar docstring (~9, ~107). Acceptance: the skill dir and script are gone; no reference to `/sst-promote-skill-proposal` or `apply-skill-patch.py` remains outside `docs/SPEC-archive.md`; `install-skills.sh --list-new` does not error.
- [x] 40.5 [easy] **Docs: README + CLAUDE.md.** Rewrite `README.md`'s auto-promote routing table (~98–104), the `proposals/` line (~26), and the `sst-promote-skill-proposal` tier-table row (~128) to describe the direct-edit-and-commit model; update `CLAUDE.md`'s overnight-chain `auto-promote all` note (~43) to "supervisor edits + commits framework improvements directly within the run." Acceptance: neither file documents sidecars/auto-promote; both describe the direct-edit model.
- [x] 40.6 [medium] **Tests: retire Phase 32 sidecar tests, add direct-edit contract tests.** `tests/test_phase32.py` (14 cases) asserts the sidecar→HUMAN.md routing + promote-skill flow; delete or rewrite it. Add tests asserting the new contract: `sst-supervisor`/`sst-manager` SKILL.md contain no `SKILL.patch.md`/`auto-promote`/`sst-promote-skill-proposal` string, document the base-repo direct-edit+commit path, and (manager) the user-request-or-self-judgment trigger; `chains/*.yaml` carry no `auto-promote`. Acceptance: full suite green; a grep-guard test fails if any sidecar term reappears on the active skill/chain surface.

### Phase 43: stop the dev cycle halting before commit (sanitize-seam fix + recovery-first reviewer) (closed)

**Context.** The autonomous dev cycle (and its `sst-dev-review §0.2` recovery) repeatedly finished the work + tests + sanitize but exited WITHOUT committing, leaving a dirty tree and tripping the Phase 36 incomplete-cycle guard (`terminated_by: contract_violation`), which aborted the loop. Root cause, proven across three 2026-06-15 transcripts: the cycle invoked `/sst-sanitize-transferable` as the LAST step before commit, and the agent treated that sub-skill's clean `must-fix: 0` return as task-completion, stopping its turn before the SPEC-flip / `git commit` + push. The recovery path had the identical defect. **Closed** by: (1) relocating the `sst-dev-cycle` sanitize gate into §3 step 5 (right after the transferable edit, before §4 verify) and rewriting §5 as a "runs in §3, never here" pointer + §7 "final action" framing; (2) reordering `sst-dev-review §0.2` recovery so the sanitize gate runs before staging, plus documenting the five-signal recovery-first health predicate (dirty tree + In-flight line + HEAD unchanged + tests green + sanitize clean) and the recover-then-review order; (3) relaxing `bin/skill-chain.py`'s `contract_violation` abort via `_contract_violation_aborts()` so a follower-recovered cycle (HEAD advanced) continues the loop and only a genuinely-unrecovered miss aborts; (4) a `tests/test_phase43.py` regression grep-guard (sanitize before §4 / before staging) + recovery-predicate + relaxed-kill tests. `sst-dev-cycle` 1.7.1→1.8.0, `sst-dev-review` 1.9.0→1.10.0; 13 new tests (252→265 green); sanitize must-fix=0 on both transferables; validator clean.

- [x] 43.1 [hard] **Close the sanitize→commit seam in `sst-dev-cycle`.** In `skills/dev/sst-dev-cycle/SKILL.md` §5, restructure so the transferable sanitize gate is not the last `/skill` invocation before commit: either run the scan right after the transferable edit (before tests) or inline the must-fix judgment against `templates/sanitization-guidance.md`; ensure `git commit` + push is the final action with no `/skill` call between test-green and commit. Acceptance: §5 has no `/sst-sanitize-transferable` sub-invocation as the step immediately before commit; the commit is documented as the skill's final action; `/sst-sanitize-transferable` clean on `sst-dev-cycle`; version bumped.
- [x] 43.2 [hard] **Close the same seam in `sst-dev-review §0.2` recovery.** Apply the identical restructure in `skills/dev/sst-dev-review/SKILL.md` §0.2 so its recovery commit is not preceded by a sanitize sub-skill invocation. Acceptance: §0.2 recovery has no sanitize `/skill` call immediately before its commit; commit is the final action; `/sst-sanitize-transferable` clean; version bumped.
- [x] 43.3 [hard] **Recovery-first commit in `sst-dev-review`.** At the very start of its turn, before the review pass, `sst-dev-review` detects an incomplete-but-healthy dev cycle (dirty tree + In-flight line + HEAD unchanged + tests green + sanitize clean) and commits the dev's work then (the recovery commit), then reviews the now-committed change. Document the health predicate and the order (recover, then review). Acceptance: §0 documents the recovery-first step with the exact health predicate; a test/fixture shows an orphaned-but-healthy cycle is committed at the start of review; `/sst-sanitize-transferable` clean; version bumped.
- [x] 43.4 [medium] **Relax the runner's `contract_violation` kill.** In `bin/skill-chain.py`, the incomplete-cycle abort fires only when HEAD is STILL unchanged after the review/recovery follower has run (a reviewer-recovered cycle continues the loop); keep the abort when there is no follower or the follower also left HEAD unchanged. Acceptance: a unit test where dev exits dirty + review commits → loop continues (no `contract_violation`); where dev exits dirty + no follower (or follower also fails to commit) → loop aborts as today; existing incomplete-cycle tests updated.
- [x] 43.5 [medium] **Regression guard + tests.** Add a `tests/` grep-guard that fails if either `sst-dev-cycle` §5 or `sst-dev-review §0.2` re-introduces a `/skill` (sanitize) sub-invocation as the step immediately before commit; add tests for the recovery-first predicate and the relaxed kill. Acceptance: the guard fails on the old pattern, passes on the new; full `tests/` suite green; `bin/validate-frontmatter.py` clean.
