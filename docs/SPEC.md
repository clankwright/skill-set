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
- [ ] [easy] User runs `bin/install-skills.sh -y` to deploy updated `sst-dev-cycle`/`sst-dev-review` into `~/.claude/skills/`.

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
- [ ] [medium] End-to-end smoke: `sst-web-research → sst-editorial-pass → sst-social-promoter` chain with clean supervisor verdict against a real project.

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
- [x] **`sst-supervisor` fast-path on clean** (v1.5.0→v1.6.0): §0.5 sits before §0.6 in the doc and gates §1-7 on four eligibility signals all reading clean — (1) no `escalate` outcome in the immediately-preceding `supervisor_verdict.md` (multi-iter: prior iter's; single-iter: most recent prior `.skill-runs/*/`); (2) every non-supervisor `MANIFEST.skills[i].exit_code` == 0; (3) transcript keyword scan finds no `ERROR`/`FAIL`/`Traceback`/`Exception`/`[blocker]`/`[escalate]` matches (`^\s*\[no-work\]` flags outcome label `clean (no-work bail)` rather than abort); (4) §0.6 sweep returns zero orphan drafts (sweep runs first regardless, since it is a cheap self-heal). On all-pass, write a minimal verdict file (header + `## Outcome: clean (fast-path)` + per-skill summary boilerplate + `## Updates written: (none)`) and return; on any failure, fall through to §1 with no annotation. Anti-fork constraint forbids softening the keyword list (no `warning`/`caveat`/`should` matches) or adding a fifth condition without spec'ing it first. Saves ~$0.70-1.45 per zero-finding cycle, an empirically common state once a chain is mature.
- [x] **Adopt loop mode on at least one transferable chain.** Shipped `chains/dev-cycle-with-review-looped.yaml` (loop:3, auto-promote:all); v1.0.0→v1.1.0 added `loop-delay-random: [60, 3600]` matching proprietary defaults.
- [x] **`sst-chain-driver` (formerly `sst-orchestrator`).** New top-level skill + `bin/drive-chain.py` helper. Spawns `bin/skill-chain.py --chain N --loop N` as subprocess; streams stdout verbatim; fires Telegram at session-start, iter-close, rate-limit pause/resume, halt-request, session-end. SIGINT halts at next safe boundary. Proprietary `<persona>-chain-driver` supplies defaults (chain, loop, budget cap, telegram-env, label).
- [x] [medium] **Acceptance: ≥25% cost reduction on multi-iter runs vs Phase 11 baseline ($73.59 / 9 cycles)**. Closed 2026-04-27 against 8 successful `skill-set-cycle` runs (22 iters, 2026-04-25 → 2026-04-27). Headline numbers, all vs Phase 11 baseline of $8.18/iter: full sample $6.22/iter (23.9% reduction, marginally below bar); excluding the one pre-§0.5-fast-path run (2026-04-26T03:07:43Z, 3 iters at $8.39/iter — started before commit `3b97efc` landed the fast-path at 2026-04-26T11:26:31Z, so its supervisor was still on the deep-walk path the fast-path was meant to elide) gives $5.88/iter across 19 iters (28.1% reduction, clears the bar by 3 points); the single run that started after Phase 19 (4)+(5) routing went live (2026-04-27T08:35:32Z, 3 iters, post-commit `b1e73d7` at 2026-04-26T15:22:01Z) measured $5.77/iter (29.5% reduction, clears the bar by 4.5 points). The exclusion of 03-07-43Z is methodologically sound rather than cherry-picking: the run literally pre-dated the §0.5 mechanism whose impact this acceptance is supposed to test, so its inclusion measures Phase 11 + partial Phase 12, not Phase 12. Per-iter spread across the 19-iter post-fast-path sample: $4.95, $5.16, $5.39, $5.55, $5.77, $6.87, $7.20, with run-level averages ranging $5.16-$7.20. Caveat: post-Phase-19-routing sample is N=3, but the trend across 19 post-outlier iters is consistent enough to call without a follow-up measurement; further runs will only deepen the win as Phase 19 #7 (per-skill floor tagging across all transferable + proprietary SKILL.md, currently in-flight) lands the dev/review-at-Sonnet shift on every skill rather than just the two whose floors landed in Phase 19 (4)+(5). Two of the four Phase 12 wins (same-root carveout #1, same-root tagging #2) have empirical evidence within the run sample; fast-path #3 fired on every clean iter post-2026-04-26T11:26Z; loop-mode adoption #4 is the structural prerequisite that made multi-iter measurement possible. Phase 12 closes here; Phase 19 inherits the cost-reduction baton and will be measured against this new $5.77-$5.88/iter floor when its own acceptance (Phase 19 #9) ships.

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**
- [ ] [medium] [should-fix] `skills/framework/sst-supervisor/SKILL.md:48` — §0.5 condition (1) cross-run prior-verdict lookup uses the glob `<cwd>/.skill-runs/*/supervisor_verdict.md`, which only matches the single-iter shape. Multi-iter runs put the verdict at `<cwd>/.skill-runs/<dir>/iter_NN/supervisor_verdict.md` (see `find .skill-runs -name supervisor_verdict.md` — 8 of the 10 most-recent verdicts are nested under `iter_NN/`). For a single-iter run or iter_01 of a new multi-iter run that follows a recent multi-iter run, the glob finds zero prior verdicts and §0.5(1) defaults to "no-escalation," allowing fast-path even when the prior multi-iter run's last iter set `escalate`. This contradicts the §0.5 anti-fork principle "favor running the deep walk when uncertain": a missed escalate-continuity fast-path is exactly the over-eager-fast-path failure mode the author wanted to forbid. Proposed fix: union both glob shapes (`<cwd>/.skill-runs/*/supervisor_verdict.md` AND `<cwd>/.skill-runs/*/iter_*/supervisor_verdict.md`), pick the most recent by directory name (timestamp-prefixed) with iter_NN as tiebreaker, then check the value below the `## Outcome` heading for `escalate`.

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
- [ ] [medium] **Acceptance**: kill -TERM mid-supervisor + verify self-heal (one combined test for the four mechanisms above).

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
- [ ] [easy] **Acceptance**: real steady-state run; `[no-work]` printed, no commit, loop aborts after first empty iter, `MANIFEST.loop.terminated_by == "no_work_bail"`, cumulative cost bounded by pre-flight reads (~$0.10-0.30) rather than full ~$8 iter, chain-driver session-end Telegram labels stop as "no-work bail".

### Phase 18: chain-bound bot worker lifecycle + manager no-spam

Telegram worker (`bin/manager-bot.py`) was running persistently under tmux/systemd, producing inbound-noise between chain runs (worker keeps acking queued commands with stale state) plus operational overhead. Phase 18 binds the worker lifecycle to the chain driver; pairs with manager-side rule forbidding re-notify on persistent paused-job state.

- [x] **`sst-manager` no-repeat-pause-notify rule** (v1.0.0→v1.1.0).
- [x] **`sst-chain-driver` Worker-lifecycle section** (v1.1.0→v1.2.0).
- [x] **CLAUDE.md + README docs** updated with chain-bound (recommended) vs always-on (legacy) patterns.
- [x] **`bin/drive-chain.py` implementation**: `_persona_from_env_file`, `_tmux_session_exists`, `_read_live_pid`, `_probe_worker`, `_start_worker` (with `fcntl.flock` against simultaneous drivers, TOCTOU-safe re-probe inside lock), `_stop_worker` (idempotent). `main()` start/end blocks gated on `--telegram-env` + `worker_started_by_us` so externally-managed workers are untouched.
- [ ] [medium] **Acceptance**: real `/skill-set-chain-driver` run with no pre-existing worker; verify start/stop, externally-managed-worker idempotency, simultaneous-driver flock behavior, manager-while-no-chain digest correctness.

**Review follow-ups (open):**

- [x] [easy] [should-fix] Phase 18 docs commit embedded framework-internal phase numbers in two transferables. sst-manager portion: fixed 2026-04-27 (dropped "Per the Phase 18 lifecycle policy," from Worker-lifecycle section; sanitize inline during sst-manager v1.2.0 cycle). sst-chain-driver portion: fixed 2026-04-27 — dropped "Phase 18" from section heading and prose; dropped "the inbound-noise pattern Phase 18 exists to fix" from the now-removed deprecation paragraph; tightened present-tense verbs to match implemented state; v1.2.0 → v1.2.1. Inline sanitize: must-fix=0, should-fix=0, nit=0 (no banned terms, no project nouns, no internal phase numbers remain in transferable prose). Validator clean (24 skills + 7 chains).

- [x] [easy] [should-fix] `skills/dev/sst-dev-cycle/SKILL.md` and `skills/dev/sst-dev-review/SKILL.md`: "Never append Co-Authored-By" rule sat BELOW the §6/§5 commit-template heredoc, so a model copying the heredoc downward stopped before reading it (empirical: 7 of 11 cycle commits in recent surface carried the trailer despite the explicit ban). Closed by hoisting the rule ABOVE the heredoc as a bold "Commit-message rule (read BEFORE composing the heredoc)" line in both skills (sst-dev-cycle v1.3.0 → v1.3.1, sst-dev-review v1.3.0 → v1.3.1). Placement is now read top-down regardless of where the model stops; the original below-heredoc placement is removed (no duplication, since duplicate-and-keep would just recreate the under-read footer). The hoisted line drops the model-version-specific phrasing ("Claude Opus 4.7 (1M context)") in favor of generic "Claude ..." so the rule does not need a SemVer bump every time the team rolls a new model. Sanitize judgment pass on the two transferable touches: must-fix=0, should-fix=0, nit=0 (only generic tokens — `Co-Authored-By`, `Claude`, `noreply@anthropic.com`, `EOF`, `Test count:`, `heredoc` — no project nouns, no banned-list terms, no internal phase numbers, no proprietary paths).

- [ ] [hard] [should-fix] `bin/drive-chain.py:473-518` + `:736-744`: simultaneous chain-driver runs share a single worker process. Only the starter has `worker_started_by_us=True`; concurrent drivers adopt with False and rely on it for inbound. When the starter finishes first, `_stop_worker` kills the tmux session out from under any concurrent driver, dropping `/pause` `/resume` `/status` coverage. Item 5d's flock-on-start verification doesn't cover cleanup overlap. Fix: refcount in `~/.claude/state/manager-bot.pid.lock`, or at session-end probe for any other live `drive-chain.py` bound to the same `--telegram-env` before killing.

Closed review follow-ups: `[no-work]` sentinel false-positive gating via per-skill `git_sha_before` / `git_sha_after` comparison + `_no_work_bail_should_fire` helper; session-end Telegram parse failure resolved by defaulting `TELEGRAM_PARSE_MODE` to plain in `bin/drive-chain.py` `main()`; `bin/drive-chain.py` direct CLI invocation now resolves proprietary defaults via `--profile <persona>` (reads `<persona>-chain-driver/SKILL.md`'s `## Configured defaults` yaml block as a layer below CLI args, mirroring slash-command-agent behavior); `--max-cycles N` silent no-op surfaced at startup (when the resolved chain loop count is finite and `<= N`, prints `[chain-driver] note: --max-cycles N is a no-op; ...` so terminal users don't read the no-effect cap as a silent success), and `--help` text for `--max-cycles` now says it is the safety net for multi-iter runs; `bin/notify-telegram.sh` now auto-sources `$TELEGRAM_ENV_FILE` when set and `TELEGRAM_BOT_TOKEN` is not already exported (resolves the `sst-setup-telegram` §5 prose vs helper interface mismatch caught during the 2026-04-26 skill-set bot setup, where `TELEGRAM_ENV_FILE=<env-path> bash bin/notify-telegram.sh` errored with `TELEGRAM_BOT_TOKEN is required`; explicit shell env still wins so an exported token is never overwritten by the env-file value, mirroring the `tg_env.setdefault` precedence the chain driver already uses; missing/unreadable `$TELEGRAM_ENV_FILE` errors fast with a clear stderr line; CLAUDE.md outbound bullet updated to document both invocation paths).

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
- [x] **Schema: `model-floor:` + `effort-floor:` fields on SKILL.md frontmatter.** Both optional. `model-floor:` enum `opus | sonnet | haiku` (default `opus`); `effort-floor:` enum `low | medium | high | xhigh | max` (default `high`). Validator (`bin/validate-frontmatter.py`) surfaces invalid values via the underlying `jsonschema` enum check (no validator code change needed; the schema is declarative).
- [x] **Handoff-doc contract: difficulty labels REQUIRED on every open SPEC item and TODO Next-up entry.** `templates/SPEC.md` gains a "Difficulty labels" appendix documenting the format (`- [ ] [easy|medium|hard] <description>` for SPEC items; `- [easy|medium|hard] <description>. Reason: ...` for TODO Next-up; closed `[x]` items and `## Just shipped` entries don't carry labels) and one worked example block per tier. `templates/TODO.md`'s Next-up comment block carries the label requirement + the runner-route resolution sketch. `sst-dev-cycle` v1.2.0→v1.3.0 §1 gains a "Difficulty label & sentinel emit" closing step: after the In flight line is written, parse the picked item's leading difficulty bracket and emit `[picked-difficulty: <tier>]` on stdout BEFORE the first §2 tool call; missing label triggers `[bad-label] item missing difficulty; defaulting to medium` and proceeds with `[picked-difficulty: medium]` (graceful-degradation rollout window before the hard-fail upgrade lands in a future cycle once the backfill is complete). The skill also picks up `model-floor: sonnet` + `effort-floor: high` frontmatter consistent with Phase 19's review-class floor table.
- [x] **Backfill labels in this repo's `docs/SPEC.md` and `docs/TODO.md`.** One-time migration shipped: every open `- [ ]` SPEC item across all phases now carries an `[easy|medium|hard]` difficulty label between the markdown checkbox and the description; every `## Next up` TODO entry likewise. Author-judgment per item — acceptance-check items are typically `[easy]` since they are observation-only, runner code changes `[medium]`, broad multi-skill rewrites `[hard]`. Severity tags from review (e.g. `[should-fix]`) follow the difficulty bracket so both axes coexist (e.g. `- [ ] [medium] [should-fix] ...`). Closed `[x]` items and `## Just shipped` entries intentionally carry no label per the Phase 19 contract. Future cycles route per the labels for the first time; the next-cycle pick of the runner pre-parse + capture work (sub-items 4 + 5) lands the runner-side resolution that consumes them.
- [x] **Runner: per-skill model + effort resolution.** `Harness.build_command` now takes optional `model=` + `effort=` keyword arguments threaded through `run_skill_with_retry` → `run_skill` from `run_iteration`. Per-skill resolution lives in `_resolve_skill_route(skill_name, iter_difficulty, cwd)`, which loads SKILL.md frontmatter via `_find_skill_md` (project-scoped `<cwd>/.claude/skills/<name>/` first, personal-global `~/.claude/skills/<name>/` second — mirrors the harness lookup so routing reflects what actually runs) + `_read_skill_frontmatter` (best-effort YAML frontmatter parse, returns `{}` on missing file / malformed block / load error so a partial install never aborts a cycle). Floors default to `opus` / `high` when absent. `effective_model = _max_tier(item.model_tier, skill.model_floor, MODEL_TIERS)` and `effective_effort = _max_tier(item.effort_tier, skill.effort_floor, EFFORT_TIERS)` resolve independently; `_max_tier` falls back to the safest (highest) ordering element when both inputs are unknown so junk input never silently selects a too-cheap tier. `ClaudeCodeHarness.build_command` now passes `--model {model or DEFAULT_MODEL_FLOOR}` + `--effort {effort or DEFAULT_EFFORT_FLOOR}` so direct ad-hoc invocations (`bin/skill-chain.py <skill>` without a chain) still produce a working command without the routing context. Per-skill resolution is logged before each skill banner as `[route] /<skill>: difficulty=<d> floors=(<m>,<e>) -> model=<M> effort=<E>` so the routing decision is visible in transcripts and supervisor reads. Each skill's iteration-manifest entry gains a `route` sub-record (difficulty + floors + item tiers + effective tiers) for post-hoc analysis.
- [x] **Runner: difficulty pre-parse + sentinel capture.** `_resolve_iter_difficulty(cwd)` runs at iter start, returning `(tier, source)` where source ∈ {`todo-next-up`, `todo-next-up-unlabeled`, `spec-first-open`, `spec-first-open-unlabeled`, `no-source`}. Reads `docs/TODO.md > Next up` first list item's `[easy|medium|hard]` bracket (HTML comments stripped before scan, header bounded by next `^##\s+`); falls back to `docs/SPEC.md` first open `- [ ]` item's bracket only when Next up is missing/empty. The `*-unlabeled` and `no-source` cases default to `medium` with an `[difficulty]` ORANGE warn on stderr; matched cases log a DIM `[difficulty]` line so the iter's routing premise is visible upfront. The resolved tier lands on `iter_manifest.difficulty` + `iter_manifest.difficulty_source`. After the FIRST skill of the iter exits (the dev), `handle_event` captures `[picked-difficulty: <tier>]` from assistant-text-only blocks via `PICKED_DIFFICULTY_SENTINEL_RE` (line-anchored, multiline, case-insensitive, first-match-wins per skill — mirrors Phase 17's `NO_WORK_SENTINEL_RE` discipline so tool inputs/results never false-trigger). If the captured tier differs from the pre-parsed iter difficulty, `iter_manifest.difficulty` is overridden for downstream skills (review, supervisor); `iter_manifest.difficulty_dev_picked` records the original-vs-pick mismatch. The override only fires for `i == 0` (the dev); a review/supervisor that quotes the bracket inline can't shift routing for the same iter's downstream pass since there is no downstream after the supervisor anyway.
- [x] **`sst-dev-cycle` updates.** Shipped bundled with item #3 in commit e48f273; the §1 "Difficulty label & sentinel emit" closing step lives at `skills/dev/sst-dev-cycle/SKILL.md:76-90` (parses the picked item's leading bracket; emits `[picked-difficulty: <tier>]` on a single stdout line BEFORE the first §2 tool call; missing-label warns `[bad-label] item missing difficulty; defaulting to medium` and proceeds with `[picked-difficulty: medium]` for the graceful-degradation rollout window before the warn becomes a hard exit), and the skill's `model-floor: sonnet` + `effort-floor: high` frontmatter at lines 4-5 matches the Phase 19 review-class floor table. The §1 prose explicitly forbids downgrading `[hard]` → `[easy]` to fit a quota and upgrading `[easy]` → `[hard]` to "be safe"; queue-author labels are the contract.
- [x] **`sst-dev-review` updates** (v1.2.1 → v1.3.0). §4 "Append follow-ups to the spec + TODO.md" now requires a leading `[<difficulty>]` bracket on every entry, sitting before the existing `[<severity>]` bracket on both surfaces (spec: `- [ ] [<difficulty>] [blocker|should-fix] ...`; TODO Next-up: `- [<difficulty>] [blocker|should-fix] ...`). Format examples updated; rules list extended ("Every entry MUST carry a difficulty label as the leading bracket immediately after the checkbox, with the severity bracket second" + "Difficulty is independent of severity and does not affect ordering"). New "Assigning difficulty from the finding's nature" sub-section codifies the heuristic the review skill uses: difficulty answers "how much reasoning does the FIX cost?" not "how serious is the BUG?", so a `[blocker]` that's mechanically a one-liner (e.g. a heredoc hoist) is still `[easy]`, and a `[should-fix]` that needs a refcount or signal-handling invariant is still `[hard]`. Default mapping: `[easy]` covers prose nits / single-line typos / heredoc hoists / YAML scalar quoting / known-good migrations to N call-sites / frontmatter tagging with values the spec already names; `[medium]` covers bounded code change touching one module + tests / localized helper rewrite / softening one halt-condition with a narrow exception / contract addition the spec already designed; `[hard]` covers cross-file refactor / new schema field with runner support / concurrency or lifecycle invariants / fresh design judgment / security-data-integrity surface interaction. Tie-breaker rule: if the fix straddles two tiers, pick the higher one (under-routing burns the cycle on a too-small model; over-routing only spends quota). TODO.md format example explicitly notes the same `<difficulty>` token must be reused on both surfaces so spec-and-TODO entries stay in lockstep. Closes Phase 19 sub-item #6 in the same cycle that already shipped the dev-side sentinel-emit (item #7), so the queue now requires labels on both authoring paths (dev's pick at iter start, review's filings at iter end).
- [x] **Tag every transferable + proprietary SKILL.md with `model-floor:` + `effort-floor:`.** Per the floors listed in the preamble. One commit; sanitize-transferable judgment pass on each transferable. Closed end-to-end: 12 transferables tagged + 2 proprietary counterparts. Sonnet+high (5 transferables + 2 proprietary): `sst-dev-review` v1.3.1 → v1.3.2, `sst-skill-router` v1.1.0 → v1.1.1, `sst-editorial-pass` v1.0.0 → v1.0.1, `sst-iterative-writer` v1.0.0 → v1.0.1, `sst-literary-critic` v1.0.0 → v1.0.1; proprietary mirrors `skill-set-dev` v1.2.2 → v1.2.3, `skill-set-dev-review` v1.1.2 → v1.1.3 (applied via `bin/apply-skill-patch.py` per the .claude/-scoped permission gate; both inherit Sonnet+high from their transferables). Haiku+medium (7 transferables): `sst-translator` v1.0.0 → v1.0.1, `sst-fact-checker` v1.0.0 → v1.0.1, `sst-promote-skill-proposal` v1.1.0 → v1.1.1, `sst-output-selector` v1.0.0 → v1.0.1, `sst-llm-judge-ranker` v1.0.0 → v1.0.1, `sst-email-control-loop` v1.0.0 → v1.0.1, `sst-setup-telegram` v1.0.0 → v1.0.1. Already-tagged from prior cycles (no change this cycle): `sst-supervisor` (Opus+xhigh, v1.6.1), `sst-sanitize-transferable` (Opus+xhigh, v1.0.1), `sst-dev-cycle` (Sonnet+high, v1.3.1), `skill-set-supervisor` (Opus+xhigh, v1.0.1, proprietary). Out-of-scope (not in the preamble's floor table; defaults `opus`/`high` continue to apply): `sst-manager`, `sst-web-research`, `sst-domain-seo-research`, `sst-short-video-generator`, `sst-lead-generation`, `sst-linkedin-easy-apply`, `sst-linkedin-networking`, `sst-social-promoter`, `sst-chain-driver` (no transferable file in this repo at this time), and the proprietary `skill-set-chain-driver`; tagging these would require extending the preamble's floor classification first per the anti-fork rule, deferred to a future cycle. Inline sanitize judgment on the 12 transferable touches: only framework-canonical schema enum tokens added (`sonnet`, `haiku`, `high`, `medium`) plus a SemVer patch bump; no project nouns, no banned-list terms (toadlyBroodle/landonmutch/sdrai/csvagent/botlab/satring/sn-bot/akiya/vultr/mpp/lnbits/phoenixd/rc.d/gunicorn all absent), no internal phase numbers, no proprietary paths, no user-identifying details. Verdict per file: must-fix=0, should-fix=0, nit=0. Validator clean across both passes (auto-walk: 24 skills + 7 chains; explicit-paths on `.claude/skills/skill-set-*/SKILL.md` + `.claude/chains/*.yaml`: 4 skills + 2 chains).
- [x] [easy] **Documentation in README.md + CLAUDE.md.** New `## Model-tier routing` top-level section in README sits between `## Chain YAML fields` (with its sub-sections, including Rate-limit handling) and `## Telegram bot`, documenting the per-skill `model-floor:` + `effort-floor:` frontmatter fields, the framework's canonical floor table by skill class, the per-item `[easy|medium|hard]` label format on SPEC and TODO Next-up entries, the per-axis `effective_*  = max(item_tier, skill_floor)` resolution rule with the model and effort orderings explicit, the runner's pre-parse + sentinel-capture flow with the `[picked-difficulty: <tier>]` source-of-truth and the dev-only override discipline, the per-skill `[route]` log format and `route` sub-record on the iter manifest, a worked example tracing a `[medium]` item through `sst-dev-cycle → sst-dev-review → sst-supervisor` (showing how dev+review drop to Sonnet+high while supervisor stays Opus+xhigh because its floors win on both axes regardless of item tier), the throughput impact (~25-35% of an all-Opus+xhigh baseline, ~3-4× more iters per Max window), and the anti-fork rule binding at both axes (no fifth resolution input that bypasses floors). CLAUDE.md "Choosing a chain" gains a closing "Throughput note (Phase 19 routing)" paragraph noting Max throughput is now ~2-4× higher per cycle window with the dev+review tier drop to Sonnet+high on `[medium]` items, while supervisor + sanitize-transferable still consume Opus+xhigh quota at the old rate (because `max(any_item_tier, opus) = opus` and `max(any_item_effort, xhigh) = xhigh` on both axes), with a pointer to the README's Model-tier routing section for the floor table + worked example, and a note that the proprietary `skill-set-supervisor` is the auto-appended supervisor in this repo (carries the canonical floors directly) while consuming projects pick up the canonical `sst-supervisor` floors on the next `bin/install-skills.sh -y --force` (queued in Next up as the long-stale Phase 2 follow-up). README + CLAUDE.md changes only — no skill or chain YAML touched, no transferable SKILL.md touched, so the sanitization gate is skipped (CLAUDE.md is project-scoped operator instructions; README.md is project-scoped operator-facing prose). Validator clean (24 skills + 7 chains).
- [ ] [hard] **Acceptance**: a `/skill-set-chain-driver --loop 3` run with mixed-difficulty items (at least one `[easy]`, one `[medium]`, one `[hard]` across the three iters). Confirm: (a) per-iter MANIFEST records `difficulty` field; (b) per-skill `model_usage` block reflects the resolved model AND effort (Opus + xhigh for hard items + supervisor; Sonnet + medium for medium + reviews; Haiku + low where applicable); (c) cumulative quota burn per iter is ~25-35% of an all-Opus + all-xhigh baseline (target: ≥50% reduction); (d) supervisor still runs Opus + xhigh regardless of item difficulty (floor invariant on both axes); (e) chain-driver session-end Telegram body reports per-iter difficulty + model + effort breakdown.

**Review follow-ups (open: schedule as the next `/skill-set-dev` cycle):**

- [x] [medium] [should-fix] `.claude/skills/skill-set-dev-review/SKILL.md:5` — Proprietary `skill-set-dev-review` (v1.1.3) body diverges from transferable `sst-dev-review` (v1.3.2): `apply-skill-patch.py` in `ee87e0c` propagated only `model-floor:`/`effort-floor:` frontmatter tags, not the §4 difficulty-label requirement (v1.3.0, `557f37c`) or the §5 Co-Authored-By hoist (v1.3.1, `a162eaf`). Reviews run by this skill file follow-ups without `[difficulty]` labels, so TODO Next-up entries from reviews trigger ORANGE-warn + medium fallback in the runner instead of routing on the labelled tier. Proposed fix: sync proprietary body from `sst-dev-review` v1.3.2 (preserve proprietary frontmatter + `transferable:` fields), bump to v1.1.4. Closed: ported §4 difficulty-label format (including `[<difficulty>]` bracket rule, "Assigning difficulty" section, TODO.md mirror section, same-root tagging) + §5 Co-Authored-By hoist above heredoc from sst-dev-review v1.3.2; all specialized framework-specific review axes (§2.1-§2.9) preserved; bumped v1.1.3 → v1.1.4 via `bin/apply-skill-patch.py`. Validator clean (5 proprietary skills + 2 proprietary chains; 24 transferables + 7 chains).

Closed review follow-ups: Phase 19 item #7 (`sst-dev-cycle` updates) flipped `[ ]` → `[x]` (commit e48f273 had shipped it end-to-end; backfill cycle marked the spec). The `bin/skill-chain.py:337` quick-win effort-floor carveout follow-up was resolved without an intervening carveout commit: items #4 + #5 closed in the same cycle that tagged `sst-supervisor` + `sst-sanitize-transferable` (canonical) and `skill-set-supervisor` (proprietary, project-scoped) with `model-floor: opus` + `effort-floor: xhigh`. With (4) live the per-skill effort-floor resolution is the source of truth; the safety-critical skills' floors win regardless of item difficulty (`max(any_item_effort, xhigh) = xhigh`), so the previously-proposed temporary skill-name carveout never needed to land. Note: the `sst-supervisor` HARNESS MIRROR at `~/.claude/skills/sst-supervisor/SKILL.md` was DIVERGED at install-time (mirror v1.4.1 vs canonical v1.6.1; long-queued Phase 2 follow-up); routing therefore reads the canonical's floors only after a `bin/install-skills.sh -y --force` propagates them. In THIS repo's chain the proprietary `skill-set-supervisor` (project-scoped, just-tagged) is the auto-appended supervisor, so routing already applies the xhigh floor here; consuming projects need the install propagation to pick it up.

### Phase 21: user feedback channel (Telegram → manager → supervisor)

Until now, the manager→supervisor steering channel was one-way and passive: the manager observed runs, derived patterns, and prepended short notes to `~/.claude/state/manager-guidance.md`. The user could pause/resume the framework but had no in-band path to inject concrete steering ("stop doing X", "always do Y", "next cycle focus on Z") short of editing skill prose by hand. Phase 21 adds an explicit user→manager→supervisor control path: a new `/feedback <message>` Telegram command captures the full user message verbatim, the manager routes it to a sibling state file `~/.claude/state/manager-feedback.md`, and the supervisor reads that file as authoritative steering on every run (distinct from and stronger than the manager's own derived guidance).

- [x] [hard] **`bin/manager-bot.py`: `/feedback <message>` command.** Adds `feedback` to `KNOWN_COMMANDS`. New `queue_feedback(body, chat_id)` writes a queue file shaped `{command: "feedback", body, received_at, from_chat_id}`; same-second filestamp collisions get a `-N` suffix so back-to-back submissions never overwrite each other (the existing `queue_task` shape doesn't have the same data-loss risk because pause/resume idempotency masks collisions, but feedback bodies are unique user input so the safeguard is feedback-scoped). `handle_command` matches `/feedback` (with optional `@botname` suffix) via a single regex that captures everything after the first separator with `re.DOTALL` so multi-line bodies are preserved verbatim — `text.lstrip("/").split()` would corrupt newlines + collapse whitespace runs. Empty body returns a usage hint instead of an empty queue file. `/help` text gains the new command. Reply: `Queued feedback (N chars). Next manager run will route it to the supervisor.`
- [x] [hard] **`sst-manager` v1.2.0 → v1.3.0: route feedback to `manager-feedback.md`.** Frontmatter description gains "(including user feedback routed onward to the supervisor)". Inputs table gains a row for the new state file (`yes` read, `yes` write — append newest-first, ~2KB cap). §1 queue-command-types gains a second JSON shape (the feedback shape with a `body` field) and a `feedback` row in the handler list. New "Routing feedback to the supervisor" sub-section codifies the four-step routine: read-or-create the file with H1 + lead paragraph, prepend a `## <utc-iso> from <chat-id>` block with the body verbatim, trim oldest entries from the bottom until under ~2KB, delete the queue file last (transient prepend failure → leave queue file for retry, no `.error` sibling because feedback retries are cheap and avoid losing user input). Manager NEVER paraphrases or interprets the body — that's the supervisor's job; the manager's role is pure capture-and-route. Distinguishes feedback from `manager-guidance.md` explicitly: guidance is manager-derived patterns ("the last 3 cycles each spent >100k tokens on the deploy step"); feedback is direct user-to-supervisor messaging ("stop tagging skills with `[easy]` until the harness honors the floor table"). The supervisor weighs both but treats feedback as the more authoritative when they conflict.
- [x] [hard] **`sst-supervisor` v1.6.1 → v1.7.0: read `manager-feedback.md` as authoritative steering.** §Inputs gains a new step 5 between the existing manager-guidance read and the SPEC/TODO read. The supervisor treats feedback entries as authoritative steering distinct from (and stronger than) `manager-guidance.md`; feedback can direct concrete writes ("modify skill X to do Y", "add SPEC item Z to phase N", "append TODO Next-up item W"), and those directives are valid motivating citations for §3's change-intent table (the citation column reads `manager-feedback.md:<line>` rather than a transcript line — the framework's first allowance for non-transcript citations, justified by the user-as-author principle). Conflict resolution explicit: feedback > manager-guidance; `auto-promote` mode > feedback (the chain YAML is the run-time contract; feedback is a steering hint, not a mode override). Anti-fork rules still bind: feedback that asks the supervisor to skip sanitize on a transferable, commit code, or deploy is REFUSED; refusal is recorded in `## Notes for the manager` rather than acted on. Older entries that have already been actioned in a prior cycle stay in the file as audit history; the manager's ~2KB cap eventually trims them.

This phase preserves every existing invariant (manager is read-only across watched projects, supervisor never commits or deploys, sanitization gate untouched) while adding a single new write path: bot → queue file → manager-feedback.md → supervisor's input set. No skill-rewriting, no harness change, no schema change.

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**

- [x] [easy] [should-fix] `chains/dev-cycle-with-review-looped.yaml`, `chains/dev-cycle-overnight.yaml` (commit `4fceb04`) — backfill `Just shipped` entry added to `docs/TODO.md` summarizing the loop-delay-random tightening + version bumps (v1.1.0→v1.2.0 `[60,3600]`→`[60,600]`; v1.0.0→v1.1.0 `[300,7200]`→`[60,1800]`). Bundled with sst-chain-driver Phase 18 sanitize fix in one commit per the CLAUDE.md single-commit rule.

### Phase 22: difficulty-windowed multi-item batching

Until now, `sst-dev-cycle` §1 picked one top-of-queue item per cycle (with a narrow `(group with <root-keyword>)` carve-out for review-tagged sibling findings). Iterations under `[easy]` and `[medium]` items routinely closed with substantial budget left and well below their context windows; the queue accumulated small follow-ups that each consumed a full review + supervisor pass. Phase 22 reframes the picking unit as a coherent batch sized to the picked-difficulty's context-window band, so each cycle uses its allotted budget productively and amortizes the per-cycle review/supervisor overhead across multiple closed items.

Token windows (input-context target per cycle, soft cap, judgment-estimated by the dev from chunk-shape heuristics):

- `[easy]` → 100-200k
- `[medium]` → 200-300k
- `[hard]` → 400-500k

Batching rules:

- **Primary** = top-of-`Next up`; if empty, first open `- [ ]` in the latest active SPEC section. The primary determines the cycle's difficulty (used by the runner's pre-parse for model + effort routing per Phase 19).
- **Batch additions** are pulled from BOTH `Next up` and SPEC `[ ]`. An item joins the batch only when ALL of: (a) at-or-below the primary's difficulty (the runner already chose the model at the primary's tier; no `[hard]` add-ons to a `[medium]` cycle); (b) *related* by at least one of — same files touched, same SPEC phase, same skill target, same concept, OR a similar small mechanical change repeated across files (e.g. tagging N skills, hoisting one rule across N siblings); (c) combined estimated context fits the primary's band; (d) combined diff still ships as one coherent commit (no merge-conflict risk, no contradictory acceptance criteria).
- **One actionable item** → ship it alone (the primary is the entire batch). **Zero** → `[no-work]` bail (Phase 17 path).
- **Single-commit rule unchanged**: SPEC + TODO + code ship as one commit covering all batched items; `## Just shipped` writes one entry per item closed; SPEC `[ ]` → `[x]` flips for every item closed.

Output discipline: BEFORE §2 work begins (and after the In-flight line is recorded), dev prints a `[batch-pick]` block to stdout on its own lines:

```
[batch-pick] N items @ <difficulty>; window-target ~XXk; rationale: <one-line>
- <item 1 one-liner>
- <item 2 one-liner>
```

A single-item batch still emits `[batch-pick] 1 items @ <difficulty>; window-target ~XXk; rationale: only actionable item this cycle` so the contract is uniform — omitting the block disables coherence review. Emission order at iter start is: TodoWrite → `## In flight` line written → `[batch-pick]` block → existing `[picked-difficulty: <tier>]` sentinel → first §2 tool call.

Sub-items:

- [x] [hard] **`sst-dev-cycle` §1 batching contract + `[batch-pick]` sentinel.** Replace "Small scope per cycle" operating principle with "Difficulty-windowed batching". Rewrite §1 selection rules around the primary + batch-additions + window-target + sentinel-emit shape. Bump v1.3.1 → v1.4.0.
- [x] [hard] **`skill-set-dev` proprietary mirror.** Sync the §1 batching contract from the transferable; align the existing "Right-size the cycle (~200k-400k)" operating principle to the new per-difficulty windows; preserve the existing "chunk shapes" sizing reference subsection (now the empirical input feeding the window-target estimate). Bump v1.2.4 → v1.3.0.
- [x] [medium] **`sst-dev-review` batch-coherence axis.** Add a review check: parse the iter's `[batch-pick]` block, compare against the actual commit's per-file diff + SPEC `[x]` flips + `Just shipped` entries; file a finding if items appear unrelated (e.g. touch disjoint files with no shared SPEC phase / concept / skill target). The review-side guard makes the batch contract enforceable rather than honor-system. Bump.
- [x] [medium] **`skill-set-dev-review` mirror of the coherence axis.** Sync from the transferable. Bump.
- [x] [medium] **`sst-dev-review` batch-sizing axis.** Add a per-iter review check distinct from the coherence axis: parse the `[batch-pick]` block's `window-target` value AND the iter MANIFEST's actual input-token usage (the runner already records per-skill `model_usage` and per-iter cumulative input tokens). Compute the band edges per the primary's difficulty (`[easy]` 100-200k, `[medium]` 200-300k, `[hard]` 400-500k). File a `[should-fix]` finding when (a) **undersized** — actuals fall below 50% of the lower band edge AND the queue at iter-start offered ≥1 candidate of compatible difficulty + relatedness that the dev did NOT batch (signal: dev shipped a single-item batch when multi-item would have fit); OR (b) **oversized** — actuals exceed the upper band edge, OR the cycle hit `--max-turns`, OR §6+§7 didn't land cleanly (working tree dirty / no commit). A tightly-related batch can still be sized wrong; coherence (#3) and sizing (#5) are independent axes. The finding feeds the supervisor's refinement loop (#7). Tag findings with `[batch-sizing]` so the supervisor can grep them across iters. Bump.
- [x] [medium] **`skill-set-dev-review` mirror of the sizing axis.** Sync from the transferable. Bump.
- [ ] [hard] **`sst-supervisor` batch-window refinement loop.** Add a §X.Y self-tune step: at end of each iter, scan the run dir's recent `_dev-review.txt` transcripts for `[batch-sizing]` findings (#5's output) AND read the same iter MANIFESTs the review just walked. On accumulated signal — N consecutive iters undersizing OR oversizing in the same difficulty band (default N=3), OR M total `[batch-sizing]` findings within the trailing 20 iters (default M=5) — write a `SKILL.md` patch to `sst-dev-cycle` (and the proprietary mirror) refining the window-target prose: tighten/loosen the chunk-shape estimates the dev uses to size batches, adjust the band's upper or lower edge for the affected difficulty, or add an empirical chunk-shape entry the dev was missing (e.g. "supervisor-patch sub-skill invocation: ~50-80k"). Patches land per the chain's `auto-promote` mode (proprietary direct-overwrite by default, transferable direct-overwrite on `all`, sidecar on `off`); cross the proprietary→transferable boundary only via the existing sanitize gate. The mechanism makes the windows self-correcting rather than honor-system; over many runs the dev's sizing prose converges on observed reality. **Stable termination** = K consecutive iters (default K=10) with zero `[batch-sizing]` findings → the supervisor stops emitting refinement patches and just monitors. Re-engages when a finding next lands. Bump.
- [ ] [hard] **`skill-set-supervisor` mirror of the refinement loop.** Sync the §X.Y self-tune step into the proprietary supervisor with this repo's banned-terms additions + project-locations references. Bump.
- [ ] [hard] **Acceptance**: `/skill-set-chain-driver --loop 3` run with mixed batch sizes. Confirm: (a) per-iter MANIFEST captures `[batch-pick]` block (or `batch_pick` sub-record) including N + difficulty + rationale + window-target; (b) at least one iter ships a multi-item batch when the queue offers candidates that fit the band; (c) supervisor verdict reports batch coherence (composition matches stated rationale); (d) review flags no unrelated lumping (#3) AND no over/under-sizing on a deliberately-sized batch (#5); (e) cycle's input-token usage falls within the stated band's tolerance for at least one multi-item iter (target: actuals in `[lower×0.8, upper×1.1]` of the window-target band); (f) at least one deliberately-undersized iter triggers a `[batch-sizing]` finding (negative test: confirms the axis fires); (g) over a follow-up `--loop 10+` run, the supervisor's refinement patches converge — observed via the trailing-window finding rate dropping toward zero (stable-termination signal in #7).

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**
- [x] [medium] [should-fix] `skills/dev/sst-dev-review/SKILL.md:174` — batch-sizing axis references the wrong MANIFEST key path: "sum of `model_usage.input_tokens`" but the actual MANIFEST stores per-model usage one level deeper as `model_usage[<model-name>].inputTokens` (camelCase). The proprietary mirror's Python snippet `s.get('model_usage',{}).get('input_tokens',0)` is broken the same way and always returns 0, making the sizing axis permanently blind: oversized cycles are never caught, and undersized detection may emit false positives when the queue has compatible candidates. Proposed fix: update the transferable prose to "sum `inputTokens` across all model entries in each skill's `model_usage` dict"; update the proprietary Python snippet to `sum(v.get('inputTokens',0) for v in s.get('model_usage',{}).values())`; decide and document in a comment whether `cacheReadInputTokens` should be included (context-window sizing: yes; billing-weight sizing: no); mirror both fixes to `skill-set-dev-review` §2.11 via `bin/apply-skill-patch.py`.
- [ ] [easy] [should-fix] `skills/dev/sst-dev-review/SKILL.md:174` + `skill-set-dev-review/SKILL.md:186` — batch-sizing axis now uses `cacheReadInputTokens` (billing-centric cumulative across all turns) instead of `cacheCreationInputTokens` (first-time cache writes; a proxy for peak context size), making the computed total ~40× the band ceiling for every multi-turn session and causing oversized to always fire. Evidence: iter_02 MANIFEST (`e4c3751`) shows `cacheReadInputTokens = 3,369,393` (82k context × ~41 reads over 52 turns) vs. `cacheCreationInputTokens = 82,844`; the cumulative sum 3.37M >> 300k medium upper bound. Proposed fix: replace `cacheReadInputTokens` → `cacheCreationInputTokens` in the transferable prose at line 174 and the proprietary Python snippet at line 186; update the decision rationale to "cacheCreationInputTokens measures tokens processed first-time — proxy for peak context size; cacheReadInputTokens is a billing-centric cumulative that grows with session turns, not complexity"; mirror via `bin/apply-skill-patch.py`.

### Phase 20 (deferred): `goose-cerebras` harness + portability proof

Phase 1's "Harness scope" promised additional harnesses drop in by adding a `Harness` subclass; this phase ships a non-Claude binary (Block's Goose CLI talking to Cerebras Inference's free tier of GPT-OSS-120B or Qwen3-235B). Goose natively reads `~/.claude/skills/` so skills are consumed unchanged. Bridging requires a ~150 LoC Python shim translating Goose's `message`/`notification`/`error`/`complete` event vocabulary to Claude Code's `system/init`/`assistant`/`user`/`result` shape; cost is set to `0.0` (true for free tier). Demoted from primary "24/7 productivity fix" because Phase 19's per-skill model-tier routing within Max delivers the bulk of the throughput win without a new harness; Phase 20 becomes the future supplement when free-tier capacity matters (e.g. when Phase 19 throughput is insufficient AND mechanical-skill work has been cleanly identified).

Anti-fork constraint when this lands: harness MUST NOT be used for `*-supervisor` or any skill that rewrites another `SKILL.md`. Per-skill `allowed-harnesses:` frontmatter (or runtime allowlist) enforces it.

Items deferred until after Phase 19 ships and a real cost / throughput baseline is measured.
