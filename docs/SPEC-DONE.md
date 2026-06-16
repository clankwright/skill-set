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

### Phase 39: supervisor fast-path finding-aware abort

**Context.** The `sst-supervisor` §0.5 no-work fast-path keyword scan (§0.5.3) keys only on `\bERROR` / `\bFAIL(ED)?\b` / `\bTraceback` / `\bException`. A `sst-dev-review` pass that finds a real `[blocker]`/`[should-fix]` and reports it in prose ("Found 2 items: 1 blocker, 1 should-fix") trips none of those tokens, so all five fast-path conditions can hold and the supervisor writes a spurious `clean (fast-path)` verdict that silently drops the review's finding. This is the false-negative complement to the false-positive tightening already shipped in 35.13 (word-boundary anchoring). Observed on the 2026-06-02T05-11-26Z lngraph run (iter_02 verdict) and recurring as a standing manager note since 2026-04-30. The supervisor cannot self-modify its own prose from inside a consuming project's chain, so the refinement is filed here as framework work.

- [x] 39.1 [medium] **`sst-supervisor` §0.5.3: abort the fast-path on any review-reported finding.** Extend the §0.5.3 transcript scan in `skills/framework/sst-supervisor/SKILL.md` to match the `sst-dev-review` §6 "With findings" report template — the line `Found <N> items: <B> blocker, <S> should-fix` with N>0, and/or an appended `Review follow-ups` block in the diff — and abort the fast-path (fall through to the §1 deep walk) on a match, so a prose-only finding can no longer pass as `clean (fast-path)`. Keep the existing `^\s*\[no-work\]` sentinel carve-out unchanged. Respect the §0.5.3 Anti-fork constraint: no soft prose matches (`warning`/`caveat`/`should`); anchor strictly to the review skill's fixed §6 report template, not free prose. Acceptance: §0.5.3 documents the new condition with its exact match target; the Anti-fork constraint note is updated to cover it; `/sst-sanitize-transferable` clean on `sst-supervisor`; `sst-supervisor` version bumped.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 39.2 [medium] [should-fix] `skills/dev/sst-dev-review/SKILL.md` §0.2 orphaned-cycle recovery — the auto-commit path does not invoke `/sst-sanitize-transferable` on changed files under `skills/framework/`, bypassing the sanitization gate that both `sst-supervisor`'s own SKILL.md contract and CLAUDE.md require for all transferable edits. The 39.1 changes contain no proprietary leakage, but the structural bypass leaves future orphaned recoveries of transferable edits un-gated. Proposed fix: in §0.2 step 7 (before committing), check whether `git diff --name-only` includes any path under `skills/framework/`; if so, invoke `/sst-sanitize-transferable` on each affected SKILL.md and abort with a user-visible message if any must-fix finding is returned.
- [x] 39.3 [easy] [should-fix] `skills/dev/sst-dev-review/SKILL.md` §0.2 step 7 — the recovery sanitize gate checks only `skills/framework/**`, narrower than the `sst-dev-cycle` §5 gate (`skills/<category>/<sst-*>/SKILL.md`); transferable dev skills in `skills/dev/` (e.g. `sst-dev-cycle`, `sst-dev-review`) are left un-sanitized if an orphaned recovery commits them. Proposed fix: widen the step 7 path check to match the dev-cycle gate: scan staged paths for `skills/**/sst-*/SKILL.md` (not just `skills/framework/`), invoke `/sst-sanitize-transferable` on each match, and update the test to assert the broader pattern; bump version to 1.9.0.

### Phase 41: interactive UI/UX test stage between dev and review (`sst-tester` + `ssp-cm-tester`)

**Context.** UI/UX changes are currently verified only by the dev cycle's own inline checks plus static Playwright specs (in consuming projects, e.g. claim_management's `web/e2e/*.spec.js`) that nothing runs in-loop; no stage actually spins up the running app and drives the changed surfaces in a real browser between implement (`sst-dev-cycle`) and review (`sst-dev-review`), so the reviewer judges UI work from a diff alone and never sees runtime behavior. This phase adds a new chain stage that, after the dev cycle commits, resolves what changed, starts the project's local front+back-end stack, drives the affected surfaces in a browser (headed when a display exists, headless fallback), writes a structured findings artifact for the reviewer, then tears the stack down and exits cleanly — never persisting screenshots/traces or any test-time artifact inside the repo tree. Split per the transferable/proprietary model: a project-agnostic `sst-tester` (contract, lifecycle discipline, findings format, degrade/clean-exit guarantees) wrapped by `ssp-cm-tester` (the consuming project's exact ports, start/stop commands, auth-state path, and e2e specs).

**Design decisions (codified in the SKILL bodies; revisit before implementing if any is wrong):**
- D1 — Coverage: the tester RUNS the project's existing e2e specs mapped to the changed surfaces AND does exploratory browser checks of net-new functionality not yet covered; it does NOT author committed spec files (that stays the dev cycle's "failing tests first" job) and instead files any coverage gap as a finding.
- D2 — Headed/auth: headed when a display (WSLg/`DISPLAY`) is available, headless fallback otherwise; it NEVER blocks on interactive login — a stale/missing saved session degrades to a finding and it runs only the reachable surface.
- D3 — Artifacts: zero files written under any repo working tree; binary artifacts (screenshots/traces/video) go to a non-repo state dir (`~/.claude/state/sst-tester/<utc>/`), referenced by path; the reviewer-facing findings doc goes to the chain run-log dir (`<project>/.skill-runs/<run>/`, already gitignored).
- D4 — Self-skip: on a project with no documented local-run/browser path, the tester emits a one-line "no local-run path; nothing to exercise" and exits 0, so adding it to a non-UI chain is harmless.
- D5 — Read-only on the tree: the tester never commits, deploys, or edits repo source; it only starts/stops local servers, drives a browser, and writes the (out-of-tree / run-log) findings.
- D6 — Dev-authored guidance: the dev stage writes a brief `tester-guidance.md` to the run-log dir naming the most meaningful surfaces/flows to exercise for this cycle's changes (each tied to a changed file/feature); the tester reads it to prioritize the highest-value checks rather than re-deriving everything from the diff.
- D7 — Two skip paths so the tester only runs when it adds value: (a) **dev pre-empt** — when the cycle has no front-end/UI surface, the dev emits a `[skip-tester] <reason>` sentinel and the chain runner skips the tester stage entirely (never spawned), going straight to review; (b) **tester self-skip** — if spawned but it finds legitimately nothing FE/UI exercisable against the dev's work, it exits 0 as a no-op with a `verdict: skipped` record. A pre-empted or self-skipped tester is a valid, non-finding state for the reviewer (distinct from `degraded`).

- [x] 41.1 [hard] **Author the `sst-tester` transferable.** Create `skills/framework/sst-tester/SKILL.md`: chain position (immediately after the dev skill, before the review skill), authority envelope (D5), the run lifecycle (read the dev's run-log `tester-guidance.md` + resolve changes from the dev handoff → self-skip to `verdict: skipped` if nothing FE/UI is exercisable → start the project's local stack → poll readiness with a timeout → drive the changed surfaces → collect findings → tear the stack down → exit), degrade-don't-hang (D2) and self-skip (D4), headed/headless policy (D2), artifact-out-of-tree rule (D3), and the "what changed" derivation (read `git show HEAD`, `docs/TODO.md` `## Just shipped`, and the SPEC items the dev cycle flipped to `[x]`). Frontmatter: `description: |` block scalar, `version: 1.0.0`, `model-floor: sonnet`, `effort-floor: high`, `user-invocable: true`. Acceptance: file exists and `bin/validate-frontmatter.py` passes; `/sst-sanitize-transferable skills/framework/sst-tester/SKILL.md` returns must-fix 0; body contains no port literal and no project-specific path or noun.
- [x] 41.2 [medium] **Define the tester→reviewer findings contract.** Specify, in `sst-tester`, the findings artifact: a `tester-findings.md` (reviewer-facing) + `tester-findings.json` (machine-readable) written to the chain run-log dir `<project>/.skill-runs/<run>/`, with per-check records `{area, change_ref, status: pass|fail|needs-change, evidence (out-of-tree artifact path), recommendation}` plus an overall `verdict: green|red|degraded` and a one-line summary. Add a sample `tester-findings.json` under `tests/fixtures/`. Acceptance: the schema is documented in `sst-tester/SKILL.md` and matched by the fixture; a unit test in `tests/` parses the fixture and asserts the required keys; `bin/validate-frontmatter.py` clean.
- [x] 41.3 [medium] **Teach `sst-dev-review` to consume tester findings.** In `skills/dev/sst-dev-review/SKILL.md` §0 (Inputs), add reading the run-log `tester-findings.{md,json}` when present; a tester `fail`/`needs-change` becomes (or strengthens) a review `[blocker]`/`[should-fix]`; a `degraded`/aborted tester run is itself surfaced; the §6 report template gains a `Tester: <green|red|degraded|skipped> (<n> checks)` line, and a `skipped`/pre-empted tester is treated as a valid non-finding state (distinct from `degraded`). Preserve back-compat: when no findings file exists, review proceeds exactly as today. Acceptance: SKILL.md documents the read + escalation + absent-file back-compat path; `/sst-sanitize-transferable` must-fix 0; `version` bumped.
- [x] 41.4 [medium] **Insert `sst-tester` into the framework dev chains.** In `chains/dev-cycle-with-review.yaml`, `chains/dev-cycle-with-review-looped.yaml`, and `chains/dev-cycle-overnight.yaml`, change the `skills:` list to `sst-dev-cycle` → `sst-tester` → `sst-dev-review`; bump each chain `version`. Acceptance: the three YAMLs list `sst-tester` between the dev and review skills and validate against `schema/`; a test in `tests/` asserts the tester's index is exactly between dev and review in each chain.
- [x] 41.5 [hard] **Author the `ssp-cm-tester` proprietary wrapper.** Create `<claim_management>/.claude/skills/ssp-cm-tester/SKILL.md` wrapping `sst-tester` with CM facts: backend `source ./.venv/bin/activate && unset APP_ENV && python web/server/cm_flask_api.py` (port 5003), frontend `cd web/client && npm start` (webpack dev, port 3000), readiness polls on both ports with a timeout, auth reuse of `web/e2e/.auth/state.json` (36h; stale → D2 finding), the changed-surface→`web/e2e/*.spec.js` mapping (run via `npx playwright test --config=web/e2e/playwright.config.js <spec>` with `--output` redirected out of tree) plus exploratory checks for net-new UI, full teardown (kill the :5003 and :3000 processes, close the browser), and the standing CM rule never to push/commit/deploy or touch `main`/`test`/`dev1`. Frontmatter: `transferable: sst-tester`, `base-version: 1.0.0`, `transferable-version: ">=1.0.0"`, `version: 1.0.0`, `model-floor: sonnet`. Acceptance: file exists; `bin/check-ssp-sync.py` reports it in-sync; `bin/validate-frontmatter.py` passes; body documents the exact start/stop commands, both ports, and the auth-state path.
- [x] 41.6 [medium] **Insert `ssp-cm-tester` into `cm-cycle` + teach the CM reviewer.** In `<claim_management>/.claude/chains/cm-cycle.yaml`, set the `skills:` list to `ssp-cm-dev` → `ssp-cm-tester` → `ssp-cm-dev-review` and bump `version`; in `ssp-cm-dev-review/SKILL.md` mirror 41.3 (read the run-log tester findings, escalate fail/needs-change, surface degraded), and in `ssp-cm-dev/SKILL.md` mirror 41.9 (write `tester-guidance.md` for CM's changed UI surfaces, else emit `[skip-tester]`). Acceptance: `cm-cycle.yaml` lists the tester in position and validates; `ssp-cm-dev-review` references the tester findings; `bin/check-ssp-sync.py` clean for both CM wrappers.
- [x] 41.7 [medium] **Clean-exit + artifact-hygiene enforcement.** Codify in `sst-tester` (general) and `ssp-cm-tester` (concrete) that the stage (a) writes zero files under any repo working tree, (b) tears down both servers and closes the browser even on exception/timeout (a `finally`/trap path), and (c) leaves no orphan `node`/`python`/`chromium` processes and no listener on the documented ports. Acceptance: both SKILL bodies document the guaranteed-teardown path and the out-of-tree artifact dir; a test/fixture walkthrough asserts `git status --porcelain` is empty after a run and the documented ports are free.
- [x] 41.8 [medium] **Wire tooling, install, and docs.** Ensure `bin/install-skills.sh --list-new` surfaces `sst-tester` and installs it; add the `ssp-cm-tester` `base-version` pin so `bin/check-ssp-sync.py` exits 0; update `README.md`'s skill inventory + `CLAUDE.md` (and `templates/` if they enumerate the dev chain) to describe the new `dev → tester → review` order. Acceptance: `bin/install-skills.sh --list-new` lists `sst-tester`; `bin/check-ssp-sync.py` exit 0; `bin/validate-frontmatter.py` clean across all skills; full `tests/` suite green; README/CLAUDE.md describe the inserted stage.
- [x] 41.9 [medium] **Dev stage writes tester guidance + the pre-empt sentinel.** In `skills/dev/sst-dev-cycle/SKILL.md`, after the commit step (§6/§7), add the branch: if the cycle touched a front-end/UI surface, write a brief `tester-guidance.md` to the run-log dir `<project>/.skill-runs/<run>/` naming the most meaningful flows/surfaces to exercise (each tied to a changed file/feature); otherwise emit a `[skip-tester] <reason>` sentinel on its final line and write no guidance. Acceptance: SKILL.md documents both branches with the guidance template and the exact `[skip-tester]` token; `/sst-sanitize-transferable` must-fix 0; `version` bumped.
- [x] 41.10 [medium] **Chain runner honors the `[skip-tester]` pre-empt.** In `bin/skill-chain.py`, recognize a `[skip-tester]` sentinel emitted by the stage immediately preceding a tester stage and, when present, skip the tester (do not spawn it) and proceed to the next stage, recording the skip + reason in `MANIFEST.json`; never skip a non-tester follower. Mirror the existing sentinel-recognition machinery (`[no-work]` / Phase 36 guard). Acceptance: a `tests/` unit test asserts a `sst-dev-cycle → sst-tester → sst-dev-review` chain skips the tester and still runs review when the dev output carries `[skip-tester]`, runs the tester normally otherwise, and records the skip reason in the manifest; full suite green.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 41.11 [medium] [should-fix] `bin/skill-chain.py:1626` — Phase 36 incomplete-cycle check assumes `skills_to_run[i+1]` is the recovery-capable follower, but after 41.4 inserts sst-tester at position 1, when the dev exits incomplete without emitting `[skip-tester]` (e.g., a UI cycle that fails to commit before §7a executes), the message incorrectly says "passing to /sst-tester for orphaned-cycle recovery" — the tester has no recovery contract. Recovery still occurs (tester exits 0, reviewer runs §0.2 next), but the message actively misleads debugging of the overnight-drain incomplete-cycle scenario Phase 43 addressed; also untested: no test covers incomplete-cycle + tester-in-chain without `[skip-tester]`. Proposed fix: in the Phase 36 block, find the first non-`*-tester`, non-supervisor skill in `skills_to_run[i+1:]` for the print message and the `!= auto_supervisor` guard; add a unit test for the incomplete-cycle + tester-in-chain + no-`[skip-tester]` case.

### Phase 42: unify the chain-run entrypoints into one CLI

**Context.** Launching a chain currently spans multiple scripts with overlapping, awkwardly-split options: `bin/skill-chain.py` (core — chain resolution, `--loop`, delay/jitter, harness, logging, rate-limit pause/resume, sentinels, `MANIFEST.json`); `bin/drive-chain.py` (a supervisory wrapper that re-spawns `skill-chain.py` to add `--max-budget-usd`/`--max-cycles`/Telegram event posts/`--profile`/`--label`, and forces every skill-chain flag to be passed after a `-- ` separator); the "overnight" pattern (`chains/dev-cycle-overnight.yaml` = `loop: 0` + jitter `[300,1800]`, paired with a remembered `drive-chain --max-budget-usd`); and `bin/skill-batch.py` (sister runner — one skill × N glob inputs, sharing `run_skill_with_retry`). The result is "which script do I use, and which flags go where?" friction — the `-- <forwarded-args>` split most of all. This phase collapses them into ONE canonical runner that owns every flag natively: wrapper features become first-class options, the overnight pattern becomes a preset, and batch-over-inputs becomes a mode — with thin deprecation shims so existing callers (the `*-chain-driver` skills, cron, docs) keep working through the migration.

**Design decisions (codified during 42.1; revisit if any is wrong):**
- D1 — One canonical entrypoint absorbs the others. Default: `bin/skill-chain.py` becomes the single script; `drive-chain.py` and `skill-batch.py` reduce to thin deprecation shims that forward to it. (Alternative: a freshly-named `bin/run.py` with all three as shims — chosen in 42.1; the default minimizes caller churn.)
- D2 — All flags in one parser; the `-- <forwarded>` separator is gone. `--max-budget-usd`, `--max-cycles`, `--telegram-env`/`--no-telegram`, `--profile`, `--label` become native optional flags that are inert when unset, so today's bare `skill-chain.py` behavior is unchanged.
- D3 — `--overnight` preset collapses the overnight pattern: expands to `--loop 0` + jitter `[300,1800]` and REQUIRES a budget/cycle cap (errors without one). An extensible `--preset` mechanism may bundle other common combos; full flags always remain available.
- D4 — Batch mode: one-skill-over-a-glob becomes a `--batch <glob>` mode (or `batch` subcommand) of the unified runner, reusing the shared retry/harness code `skill-batch.py` already imports.
- D5 — Back-compat: the shims emit a one-line deprecation notice and forward; all in-repo callers (the two `*-chain-driver` skills, cron, README, CLAUDE.md, templates) are migrated within this phase, so nothing depends on the split once it closes.

- [x] 42.1 [hard] **Spec the unified CLI surface + entrypoint choice.** Enumerate every flag across `bin/skill-chain.py` + `bin/drive-chain.py` + `bin/skill-batch.py` + the overnight chain YAML; define the single merged argument set, the `--overnight`/`--preset` shorthand, the `--batch` mode, and decide the canonical entrypoint name (default: keep `skill-chain.py`; record rationale if renaming). Acceptance: a `docs/` section (or the runner `--help` epilog) lists the full flag set with each legacy flag mapped to its unified form and notes which scripts become shims; no flag requires `-- `-forwarding. **Done:** canonical entrypoint stays `bin/skill-chain.py` (D1 default — minimizes caller churn); the `UNIFIED_CLI_EPILOG` constant (surfaced in `--help`) maps each legacy `drive-chain.py`/`skill-batch.py` flag to its native unified form, states the `-- `-forwarding split is gone, and names the two scripts that reduce to shims (42.4/42.5). `--overnight`/`--batch` remain spec'd in D3/D4 for 42.3/42.4.
- [x] 42.2 [hard] **Merge the `drive-chain.py` wrapper layer into the canonical runner.** Move budget gates (`--max-budget-usd`), `--max-cycles`, Telegram event posts (`--telegram-env`/`--no-telegram`, the four event classes), `--profile` resolution, and `--label` into `bin/skill-chain.py` as native optional flags that are inert when unset. Acceptance: a single `skill-chain.py` invocation runs a chain with budget caps + Telegram + profile natively (no second process, no `-- `); `tests/test_skill_chain.py` stays green; the budget/telegram/profile paths get tests (port the relevant `tests/test_drive_chain_telegram.py` cases). **Done:** the six flags are native + inert-when-unset; profile defaults resolve as a layer below CLI args (explicit `--loop` suppresses profile `default-max-cycles`); Telegram is opt-in (`_wrapper_telegram_enabled`: only `--telegram-env`/`--profile`/`--label`, never the bare runner) and fires all four event classes natively — session-start, iter-close (commit + per-iter + cumulative cost + verdict), real-time rate-limit pause/resume (via a `notify` callback threaded through `run_iteration`→`run_skill_with_retry`), session-end; budget/cycle/escalation halt is the pure `_wrapper_halt_reason` (`terminated_by: "wrapper_halt"`), accumulating cost whether or not Telegram is on. 23 tests in `tests/test_phase42.py`; full suite 327→350. `drive-chain.py` retains its own copy until the 42.5 shim lands.
- [x] 42.3 [medium] **`--overnight` preset.** Add `--overnight` (and an extensible `--preset`) that expands to `--loop 0` + `--loop-delay-random 300,1800` and errors unless a `--max-budget-usd` or `--max-cycles` cap is set. Acceptance: `--overnight` with a cap expands to the documented defaults; without a cap it exits non-zero with a clear message; a unit test asserts both. **Done:** `--overnight` and `--preset overnight` added to `parse_args()`; `_apply_preset(args, explicit_loop)` handles expansion + cap check + mutual exclusion with `--loop`; `PRESETS` dict makes the mechanism extensible; 8 new tests in `tests/test_phase42.py`.
- [x] 42.4 [medium] **Fold `skill-batch.py` into a `--batch` mode.** Expose one-skill-over-a-glob as `--batch <glob>` (or a `batch` subcommand) on the unified runner, reusing the shared retry/harness code; reduce `bin/skill-batch.py` to a deprecation shim. Acceptance: the unified runner runs a skill once per glob input; `skill-batch.py` still works + prints a deprecation notice; batch tests green. **Done:** `--batch GLOB` added to `parse_args()`; `render_output_template`/`expand_inputs` helpers added; `run_batch_mode()` dispatched from `main()` when `--batch` is set; `bin/skill-batch.py` reduced to a forwarding shim with deprecation notice; 10 new tests (render/expand helpers, flag parsing, dry-run, flag matrix).
- [x] 42.5 [medium] **Deprecation shim for `drive-chain.py`.** Reduce `bin/drive-chain.py` to a thin wrapper that maps its args onto the unified CLI and forwards, printing a one-line deprecation notice; remove the duplicated wrapper logic. Acceptance: existing `drive-chain.py --chain ... --max-budget-usd ...` invocations still work via the shim; the wrapper logic now lives only in the canonical runner; `tests/test_drive_chain_telegram.py` passes (or is repointed). **Done:** `bin/drive-chain.py` reduced to a 40-line subprocess shim (strips `--` separator, forwards to `skill-chain.py`, prints deprecation); `test_drive_chain_telegram.py` repointed to `skill-chain.py`'s `_resolve_tg_env`.
- [x] 42.6 [medium] **Migrate all in-repo callers + docs.** Update `skills/framework/sst-chain-driver/SKILL.md`, the proprietary `ssp-cm-chain-driver/SKILL.md`, cron entries (`CM_MANAGER_*` / chain-driver), `README.md`, `CLAUDE.md`, and `templates/SPEC.md` to the unified CLI and drop every `-- <forwarded-args>` / two-script example. Acceptance: a grep shows no in-repo caller depends on the two-script split or `-- `-forwarding; the `*-chain-driver` skills invoke the single runner; docs describe one entrypoint. **Done:** `sst-chain-driver/SKILL.md` v1.3.0 — §0 pre-flight, §2 command block, §hard-rules, §reference shape all updated to `bin/skill-chain.py`; `README.md` + `CLAUDE.md` Telegram-section references updated; grep confirms no remaining two-script-split dependency in skills/chains/templates.
- [x] 42.7 [easy] **Tests + validation green.** A test exercises the unified flag matrix (core + budget + telegram + `--overnight` preset + `--batch`) and confirms each shim forwards correctly. Acceptance: full `tests/` suite green; `bin/validate-frontmatter.py` clean; the validator CI entrypoint passes. **Done:** 14 new tests in `test_phase42.py`; `test_drive_chain_telegram.py` repointed; full suite 364→378 green; validator clean; sanitize must-fix=0 on `sst-chain-driver`.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 42.8 [medium] [should-fix] `bin/skill-chain.py` — extracted profile default-application block into `_apply_profile_defaults(args, profile, explicit_loop)` with 5 tests covering: all-fields-filled-when-unset, explicit-CLI-wins-per-field, explicit-loop-suppresses-max-cycles, no-explicit-loop-fills-max-cycles, empty-profile-is-noop. `main()` now delegates to the pure helper; profile loading path unchanged; 350→363 green.
- [x] 42.9 [easy] [should-fix] `tests/test_phase42.py` — no test covers the documented guarantee that a profile-sourced cap satisfies `--overnight`'s cap requirement; 42.3's commit message states "Applied after profile defaults so a profile-sourced cap satisfies the cap requirement" but every existing test provides the cap via CLI. A future reorder of the `_apply_profile_defaults` / `_apply_preset` calls in `main()` would silently break this guarantee and give users a false "requires cap" error on profile-configured overnight runs. Proposed fix: add one integration test that calls `_apply_profile_defaults(args, {"default-max-budget-usd": "25.0"}, explicit_loop=False)` then `_apply_preset(args, explicit_loop=False)` on `parse_args(["--chain", "x", "--overnight"])` (no CLI cap), asserting no SystemExit and `args.loop == 0`.
- [x] 42.10 [easy] [should-fix] `bin/skill-chain.py:2301` — `out_path.parent.mkdir(parents=True, exist_ok=True)` runs before the `if args.dry_run:` check in `run_batch_mode()`, creating output directory trees on disk even when `--dry-run` is set. The flag is documented as "print planned invocations and exit without running" but leaves filesystem mutations as a side effect over every matched input. Proposed fix: move the `mkdir` call below the dry-run early-continue (i.e. immediately before the `run_skill_with_retry` call), and add a test asserting no directories are created under a tmp path when `--dry-run` is set.

### Phase 43: review follow-ups (sanitize-seam fix + recovery-first reviewer)

Phase 43 (43.1-43.5) closed and migrated to `docs/SPEC-DONE.md`. The follow-up below was found in post-cycle review of commit `a98e902` and is open work for a later `/sst-dev-cycle`.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 43.6 [medium] [should-fix] `bin/skill-chain.py:417` (`_contract_violation_aborts`) — the relaxed abort decides "cycle recovered" from `git_sha_after != head_at_violation`, but `git_sha_after` (set at `skill-chain.py:1604`) is captured AFTER the auto-appended supervisor runs as the last skill in `skills_to_run`, and the supervisor commits findings-driven base-repo edits as its normal contract (advancing HEAD). So when the dev exits dirty without committing AND `sst-dev-review §0.2` fails to recover (e.g. tests failing in the dirty tree → it prints `[incomplete-cycle] tests failing` and exits without committing) AND the supervisor then makes any commit, the HEAD-advance proxy is satisfied → `_contract_violation_aborts` returns `False` → the loop continues against a still-incomplete, still-dirty cycle, defeating the Phase 36 guard in exactly the overnight-drain scenario Phase 43 targets. The HEAD-advance proxy is satisfied by any committing skill, not only by a genuine recovery. Proposed fix: decide recovery on the actual condition rather than the proxy — re-evaluate `_incomplete_cycle_detected(cwd)` (and/or `git status --porcelain` non-empty) at the loop-level abort check in `main()`, OR compare against a HEAD snapshot captured immediately after the recovery follower (review) instead of the post-supervisor `git_sha_after`; add a regression test where dev exits dirty + review fails to recover + supervisor commits → loop still aborts with `terminated_by: contract_violation`.
- [x] 43.7 [easy] [should-fix] `bin/skill-chain.py:1874` (`main()` contract-violation comment) — the three-line comment at lines 1874-1876 still describes the Phase 43.4 SHA-proxy mechanism ("abort only when HEAD did not advance ... A cycle the follower recovered (HEAD advanced)") that 43.6 replaced; the actual recovery signal is now "In-flight cleared by the recovery follower," not "HEAD advanced." A future engineer reading `main()` is directed to the wrong signal when debugging cycle-recovery behavior. Proposed fix: rewrite the comment to reference the Phase 43.6 mechanism: abort only when `_incomplete_cycle_detected` returns True (In-flight still set); the recovery follower clearing the In-flight line is the genuine recovery signal, not HEAD advancement.

### Phase 44: standalone terminal-invocable tester mode (phase / completed-todo UI-UX sweep)

**Context.** The `sst-tester` stage (Phase 41) runs only in-chain, scoped to what the LAST dev cycle changed. There is no way to deliberately exercise all UI/UX a whole phase (or a set of completed todos) introduced, from the terminal. This phase adds an OPTIONAL standalone mode to `sst-tester` (and `ssp-cm-tester`) the user invokes directly — `--phase <id>` and/or `--todos <ref...>` — that resolves every UI/UX surface those closed items introduced, iterates over ALL of them (not just the latest diff) in a headed (headless-fallback) browser, and accumulates findings into the same `tester-findings.{md,json}` contract. Same guarantees as the in-chain mode: read-only on the tree, out-of-tree artifacts, full teardown, degrade-don't-hang, never commits/deploys.

**Design decisions:**
- D1 — Mode dispatch on one skill: existing in-chain mode (no scope args -> test the last dev cycle's diff) vs new standalone mode (explicit `--phase`/`--todos` -> phase/todo-scoped sweep). The skill detects mode from its args.
- D2 — Scope resolution: `--phase <id>` -> every `[x]` SPEC item under `### Phase <id>` whose change touched a front-end surface; `--todos <ref...>` -> the named `## Just shipped` / closed entries. Map each to its UI surface + existing e2e spec(s); the proprietary wrapper supplies the per-phase->spec map.
- D3 — Iterate-all, collect-all: unlike the single-diff in-chain pass, standalone exercises every resolved surface and does NOT stop at the first failure; it accumulates a per-surface findings section + an overall verdict.
- D4 — Standalone output: writes `tester-findings.{md,json}` (the Phase 41.2 contract) to `~/.claude/state/sst-tester/<utc>/` (no chain run-log dir) and prints a terminal summary; it does NOT file spec follow-ups (it tests + reports; the human or a review consumes the findings).

- [x] 44.1 [hard] **Standalone mode in `sst-tester`.** In `skills/framework/sst-tester/SKILL.md`, add the user-invocable standalone mode triggered by `--phase <id>` and/or `--todos <ref...>` (distinct from the in-chain mode): resolve target -> enumerate the UI/UX surfaces those closed items introduced -> iterate, exercising each (run the mapped e2e spec(s) + exploratory checks), accumulating findings. Document the arg surface, mode dispatch (D1), scope resolution (D2), iterate-all/collect-all (D3), and the standalone artifact/findings location (D4). Keep the in-chain mode unchanged; standalone stays read-only / out-of-tree / full-teardown. Acceptance: SKILL.md documents both modes + `--phase`/`--todos` + scope resolution + the read-only/out-of-tree/teardown guarantees; `/sst-sanitize-transferable` must-fix 0; version bumped.
- [x] 44.2 [medium] **Phase/todo scope resolution + tests.** Specify and test how the surface set is derived: `--phase <id>` -> all `[x]` items under `### Phase <id>` touching a front-end path; `--todos <ref...>` -> matching `## Just shipped` entries (by id or text); define how a UI surface is identified from a closed item (its changed files / named surface). Acceptance: documented resolution with an example for each input; a `tests/` test derives the surface set from a sample phase + a sample todo list.
- [x] 44.3 [medium] **Standalone mode in `ssp-cm-tester` + CM phase->spec map.** Mirror 44.1 in the CM wrapper: expose the `--phase`/`--todos` standalone mode with CM's phase->`web/e2e/*.spec.js` map (e.g. Phase 3 custom-claims -> custom-claims.spec.js + submitted-claims.spec.js + the report specs), local-stack start/stop, auth reuse. Acceptance: `ssp-cm-tester/SKILL.md` documents the standalone invocation + the CM phase->spec map; `bin/check-ssp-sync.py` clean; `/ssp-cm-tester --phase 3` documented.
- [x] 44.4 [easy] **Docs + invocation.** Document the terminal invocation (`/sst-tester --phase <id>` / `/ssp-cm-tester --phase 3`, and via the unified runner once Phase 42 lands) in `README.md` + `CLAUDE.md`. Acceptance: README/CLAUDE.md show the standalone invocation; full `tests/` suite green; `bin/validate-frontmatter.py` clean.

**Phase 44 closed (44.1-44.4).** `sst-tester` gained an optional standalone terminal mode dispatched on `--phase`/`--todos` (the in-chain mode is unchanged): `skills/framework/sst-tester/SKILL.md` v1.0.0 → v1.1.0 adds a `## Two modes` dispatch note (D1) and a `## Standalone mode` section documenting the arg surface, scope resolution (D2: closed `[x]` front-end items under a phase / matched `## Just shipped` entries by id or substring), iterate-all/collect-all (D3), and the out-of-tree findings location `~/.claude/state/sst-tester/<utc>/` (D4); standalone keeps the read-only / out-of-tree / full-teardown guarantees. `tests/test_phase44.py` (15 tests) pins the documented D2 resolution against two new fixtures (`tests/fixtures/sample-phase-spec.md`, `sample-just-shipped.md`) and the doc-presence + transferable-hygiene assertions; `tests/test_phase41.py` version pin relaxed to a major-1 semver. The proprietary `ssp-cm-tester` wrapper mirrored the mode (base-version 1.0.0 → 1.1.0, version → 1.1.0, a CM phase->`web/e2e/*.spec.js` map; `bin/check-ssp-sync.py` clean for the tester wrapper). Standalone invocation documented in `README.md` + `CLAUDE.md`. Suite 379 → 394 green; sanitize must-fix=0; validator clean.
