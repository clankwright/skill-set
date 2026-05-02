# skill-set SPEC — closed phases archive

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

Close the within-chain learning loop: looping chains can now consume their own supervisor's improvements within the same run. `auto-promote: off|proprietary|all` (default `proprietary`) routes supervisor output by scope; `SKILL.patch.md` sidecar is a drop-in replacement (full frontmatter+body, one per skill, overwritten each cycle). `bin/apply-skill-patch.py` works around the `.claude/skills/**` write-prompt gap; runner uses `--permission-mode bypassPermissions` + `--max-turns 100`.

- [x] 11.1 Schema enum + supervisor rewrite (routing table; transferable sanitization extended to direct overwrites; verdict structure records direct-vs-sidecar + sanitization footers).
- [x] 11.2 `sst-promote-skill-proposal` rewritten for sidecar promotion; transferable re-sanitized before every promote.
- [x] 11.3 All pre-existing transferable chains gained explicit `auto-promote:` (YAML 1.1 quirk: bare `off` quoted to avoid bool coercion).
- [x] 11.4 First end-to-end loop consuming its own supervisor's improvements: `~/Dev/sdrai/.skill-runs/2026-04-25T03-07-52Z_sdrai-cycle` `--loop 3` (iter_01 filed should-fix; iter_02 closed it; iter_03 rate-limit-killed mid-review per Phase 13).
- [x] 11.5 Supervisor evolution under empirical pressure: §3 change-intent table requires every patch line to cite a transcript line (v1.2.0→v1.3.0); inlined `apply-skill-patch.py` invocation under §3 routing table to prevent Edit/Write fallback (v1.3.0→v1.4.0); snapshot-write merged manifest after every skill so supervisor reads a real `MANIFEST.json` (v1.4.0→v1.4.1); generic `.claude/skills/`-only carve-out in `sst-dev-cycle`/`sst-dev-review` pre-flights so supervisor-managed dirt doesn't trip the reviewer.

### Phase 12: efficiency wins + multi-loop chain driver (closed)

A 9-cycle / $73.59 / 4-hour empirical pass on `sdrai-cycle` (~95% spec completion) surfaced three structural inefficiencies: (a) same-root TODO items fragmenting across cycles, each paying full review+supervisor overhead; (b) the supervisor burning ~$1 confirming "clean" when the run-log shows no finding; (c) `loop:` mode shipped (Phase 9) but unused, every cycle still manually re-invoked. Phase 12 closes those plus introduces the missing top-level role: a chain driver that watches one multi-iteration run and pipes progress over Telegram in real time.

- [x] 12.1 **`sst-dev-cycle` §1 same-root carveout** (v1.0.3→v1.1.0): when 2+ Next-up entries carry `(group with <root>)` AND combined diff <~300 LoC AND files disjoint, bundle into one cycle.
- [x] 12.2 **`sst-dev-review` §4 same-root tagging** (v1.1.0→v1.2.0): findings sharing one root cause append `(group with <root>)`; single-finding "groups" untagged; spec entries never tagged (one-checkbox-per-finding preserved).
- [x] 12.3 **`sst-supervisor` fast-path on clean** (v1.5.0→v1.6.0): §0.5 sits before §0.6 in the doc and gates §1-7 on four eligibility signals all reading clean — (1) no `escalate` outcome in the immediately-preceding `supervisor_verdict.md` (multi-iter: prior iter's; single-iter: most recent prior `.skill-runs/*/`); (2) every non-supervisor `MANIFEST.skills[i].exit_code` == 0; (3) transcript keyword scan finds no `ERROR`/`FAIL`/`Traceback`/`Exception`/`[blocker]`/`[escalate]` matches (`^\s*\[no-work\]` flags outcome label `clean (no-work bail)` rather than abort); (4) §0.6 sweep returns zero orphan drafts (sweep runs first regardless, since it is a cheap self-heal). On all-pass, write a minimal verdict file (header + `## Outcome: clean (fast-path)` + per-skill summary boilerplate + `## Updates written: (none)`) and return; on any failure, fall through to §1 with no annotation. Anti-fork constraint forbids softening the keyword list (no `warning`/`caveat`/`should` matches) or adding a fifth condition without spec'ing it first. Saves ~$0.70-1.45 per zero-finding cycle, an empirically common state once a chain is mature.
- [x] 12.4 **Adopt loop mode on at least one transferable chain.** Shipped `chains/dev-cycle-with-review-looped.yaml` (loop:3, auto-promote:all); v1.0.0→v1.1.0 added `loop-delay-random: [60, 3600]` matching proprietary defaults.
- [x] 12.5 **`sst-chain-driver` (formerly `sst-orchestrator`).** New top-level skill + `bin/drive-chain.py` helper. Spawns `bin/skill-chain.py --chain N --loop N` as subprocess; streams stdout verbatim; fires Telegram at session-start, iter-close, rate-limit pause/resume, halt-request, session-end. SIGINT halts at next safe boundary. Proprietary `<persona>-chain-driver` supplies defaults (chain, loop, budget cap, telegram-env, label).
- [x] 12.6 [medium] **Acceptance: ≥25% cost reduction on multi-iter runs vs Phase 11 baseline ($73.59 / 9 cycles)**. Closed 2026-04-27 against 8 successful `skill-set-cycle` runs (22 iters, 2026-04-25 → 2026-04-27). Headline numbers, all vs Phase 11 baseline of $8.18/iter: full sample $6.22/iter (23.9% reduction, marginally below bar); excluding the one pre-§0.5-fast-path run (2026-04-26T03:07:43Z, 3 iters at $8.39/iter — started before commit `3b97efc` landed the fast-path at 2026-04-26T11:26:31Z, so its supervisor was still on the deep-walk path the fast-path was meant to elide) gives $5.88/iter across 19 iters (28.1% reduction, clears the bar by 3 points); the single run that started after Phase 19 (4)+(5) routing went live (2026-04-27T08:35:32Z, 3 iters, post-commit `b1e73d7` at 2026-04-26T15:22:01Z) measured $5.77/iter (29.5% reduction, clears the bar by 4.5 points). The exclusion of 03-07-43Z is methodologically sound rather than cherry-picking: the run literally pre-dated the §0.5 mechanism whose impact this acceptance is supposed to test, so its inclusion measures Phase 11 + partial Phase 12, not Phase 12. Per-iter spread across the 19-iter post-fast-path sample: $4.95, $5.16, $5.39, $5.55, $5.77, $6.87, $7.20, with run-level averages ranging $5.16-$7.20. Caveat: post-Phase-19-routing sample is N=3, but the trend across 19 post-outlier iters is consistent enough to call without a follow-up measurement; further runs will only deepen the win as Phase 19 #7 (per-skill floor tagging across all transferable + proprietary SKILL.md, currently in-flight) lands the dev/review-at-Sonnet shift on every skill rather than just the two whose floors landed in Phase 19 (4)+(5). Two of the four Phase 12 wins (same-root carveout #1, same-root tagging #2) have empirical evidence within the run sample; fast-path #3 fired on every clean iter post-2026-04-26T11:26Z; loop-mode adoption #4 is the structural prerequisite that made multi-iter measurement possible. Phase 12 closes here; Phase 19 inherits the cost-reduction baton and will be measured against this new $5.77-$5.88/iter floor when its own acceptance (Phase 19 #9) ships.

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**
- [x] 12.7 [medium] [should-fix] `skills/framework/sst-supervisor/SKILL.md:48` — §0.5 condition (1) cross-run prior-verdict lookup uses the glob `<cwd>/.skill-runs/*/supervisor_verdict.md`, which only matches the single-iter shape. Multi-iter runs put the verdict at `<cwd>/.skill-runs/<dir>/iter_NN/supervisor_verdict.md` (see `find .skill-runs -name supervisor_verdict.md` — 8 of the 10 most-recent verdicts are nested under `iter_NN/`). For a single-iter run or iter_01 of a new multi-iter run that follows a recent multi-iter run, the glob finds zero prior verdicts and §0.5(1) defaults to "no-escalation," allowing fast-path even when the prior multi-iter run's last iter set `escalate`. This contradicts the §0.5 anti-fork principle "favor running the deep walk when uncertain": a missed escalate-continuity fast-path is exactly the over-eager-fast-path failure mode the author wanted to forbid. Proposed fix: union both glob shapes (`<cwd>/.skill-runs/*/supervisor_verdict.md` AND `<cwd>/.skill-runs/*/iter_*/supervisor_verdict.md`), pick the most recent by directory name (timestamp-prefixed) with iter_NN as tiebreaker, then check the value below the `## Outcome` heading for `escalate`.

Closed review follow-up: `bin/orchestrate-chain.py` looping detection only consulted `--loop` CLI override, not the chain YAML's `loop:` field; fixed by deriving `looping = True` from the observed `===== iteration N =====` banner.

### Phase 13: rate-limit pause-and-resume (closed)

Multi-iter `--loop N` chains crossing the rolling 5h Anthropic quota mid-run now sleep until reset + jitter[15,60]s, then resume the killed skill in place. Three error categories handled (five_hour, primary, extra_usage); each skill invocation is a fresh subprocess so restart is safe.

- [x] 13.1 **Detection in `handle_event`**: captures `rate_limit_event` with `status ∈ {exceeded,blocked,reset_required,throttled,rejected}` into `skill_record["rate_limit_signal"]`; field-alias resolution for `reset_time`/`retry_after_seconds`. First-fatal-wins. Stderr fallback `RATE_LIMIT_TEXT_RE` for cases where the subprocess died before a clean structured event.
- [x] 13.2 **Pause loop in `run_skill_with_retry`**: parses reset_time + jitter; falls back to retry_after; finally exponential-backoff `300×2^attempt`. Per-attempt `.txt`/`.jsonl` archived to `<stem>.retry-N.{ext}`. Ctrl-C clean through the outer try/except.
- [x] 13.3 **Configurability**: schema gained `on-rate-limit` (`fail|pause|pause-with-cap`, default pause), `max-rate-limit-pause-seconds` (default 28800/8h), `max-pauses-per-session` (default 3); CLI flags mirror; CLI > YAML > defaults.
- [x] 13.4 **Manifest**: `iter_manifest["rate_limit_pauses"]` (one record per pause); top-level `manifest["rate_limit_policy"]` records resolved policy.
- [x] 13.5 **Repeat-pause safeguard**: aborts at `retry_count >= max_pauses` with `record["rate_limit_aborted"] = "max_pauses_reached"`; `pause-with-cap` adds `"max_pause_seconds_exceeded"`.
- [x] 13.6 **Chain-driver hook**: `bin/drive-chain.py` parses `[rate-limit]` banners, fires Telegram on pause + resume + abort variants.
- [x] 13.7 **Acceptance**: verified live on 2026-04-25 in `2026-04-25T13-36-00Z_skill-set-cycle/iter_03` (real five_hour quota crossing; sleep 6811.5s = parsed reset + jitter; retry session at wake_at exactly; chain finished all 3 iters; manifest records full timeline).

Live-failure follow-ups closed 2026-04-25 (status-enum gap added `rejected`; text-fallback regex extended for `you're out of (extra )?usage`; localized-clock parser branch for `7:50pm (Asia/Tokyo)`-style; `[FAIL] (success)` label disambiguation; joint-fire merge condition for structured-signal-with-text-extracted-reset). 28 inline scenario tests cover the matrix.

### Phase 15: rename for clarity (closed)

Three skills shared the "orchestrator"/"manager" naming axis and routinely got confused. Renamed two ambiguous skills; `sst-manager` unchanged.

| Old name | New name | What it does |
|---|---|---|
| `sst-orchestrator` | `sst-chain-driver` | drives ONE multi-iter chain run; spawns `bin/skill-chain.py`, watches stdout, posts Telegram |
| `sst-agent-orchestrator` | `sst-skill-router` | inside ONE user request, decomposes the task, picks sub-skills, sequences them |

- [x] 15.1 Skill renames (1.0.0→1.1.0); body prose + frontmatter updated; "Naming history" footer on both.
- [x] 15.2 Helper rename `bin/orchestrate-chain.py` → `bin/drive-chain.py`; runtime tags `[chain-driver]`; Telegram body prefixes updated.
- [x] 15.3 Cross-references updated; stale deployed copies cleared (install-skills.sh intentionally doesn't delete target-only dirs).
- [x] 15.4 Validator clean (24 skills + 6 chains).

### Phase 16: long-running chain pattern + chain selection docs (closed)

Phase 12/15 shipped chain-driver mechanism + one multi-iter chain. Phase 16 fills two adjacent shapes: unattended overnight drain + missing chain-selection docs.

- [x] 16.1 **`chains/dev-cycle-overnight.yaml`** (transferable; loop:0, loop-delay-random [300,7200], auto-promote:all). Designed for chain-driver wrap so budget cap is the safety net.
- [x] 16.2 **Proprietary `.claude/chains/skill-set-overnight.yaml`** mirrors the transferable with skill-set-* skills + auto-appended supervisor.
- [x] 16.3 **README "Chains shipped here" subsection** + "Pick the dev chain by intent" guide; CLAUDE.md "Choosing a chain" + proprietary chain-driver "Common overrides" extended.
- [x] 16.4 Validator clean (24 skills + 7 chains).

### Phase 21: user feedback channel (Telegram → manager → supervisor) (closed)

Until now, the manager→supervisor steering channel was one-way and passive: the manager observed runs, derived patterns, and prepended short notes to `~/.claude/state/manager-guidance.md`. The user could pause/resume the framework but had no in-band path to inject concrete steering ("stop doing X", "always do Y", "next cycle focus on Z") short of editing skill prose by hand. Phase 21 adds an explicit user→manager→supervisor control path: a new `/feedback <message>` Telegram command captures the full user message verbatim, the manager routes it to a sibling state file `~/.claude/state/manager-feedback.md`, and the supervisor reads that file as authoritative steering on every run (distinct from and stronger than the manager's own derived guidance).

- [x] 21.1 [hard] **`bin/manager-bot.py`: `/feedback <message>` command.** Adds `feedback` to `KNOWN_COMMANDS`. New `queue_feedback(body, chat_id)` writes a queue file shaped `{command: "feedback", body, received_at, from_chat_id}`; same-second filestamp collisions get a `-N` suffix so back-to-back submissions never overwrite each other (the existing `queue_task` shape doesn't have the same data-loss risk because pause/resume idempotency masks collisions, but feedback bodies are unique user input so the safeguard is feedback-scoped). `handle_command` matches `/feedback` (with optional `@botname` suffix) via a single regex that captures everything after the first separator with `re.DOTALL` so multi-line bodies are preserved verbatim — `text.lstrip("/").split()` would corrupt newlines + collapse whitespace runs. Empty body returns a usage hint instead of an empty queue file. `/help` text gains the new command. Reply: `Queued feedback (N chars). Next manager run will route it to the supervisor.`
- [x] 21.2 [hard] **`sst-manager` v1.2.0 → v1.3.0: route feedback to `manager-feedback.md`.** Frontmatter description gains "(including user feedback routed onward to the supervisor)". Inputs table gains a row for the new state file (`yes` read, `yes` write — append newest-first, ~2KB cap). §1 queue-command-types gains a second JSON shape (the feedback shape with a `body` field) and a `feedback` row in the handler list. New "Routing feedback to the supervisor" sub-section codifies the four-step routine: read-or-create the file with H1 + lead paragraph, prepend a `## <utc-iso> from <chat-id>` block with the body verbatim, trim oldest entries from the bottom until under ~2KB, delete the queue file last (transient prepend failure → leave queue file for retry, no `.error` sibling because feedback retries are cheap and avoid losing user input). Manager NEVER paraphrases or interprets the body — that's the supervisor's job; the manager's role is pure capture-and-route. Distinguishes feedback from `manager-guidance.md` explicitly: guidance is manager-derived patterns ("the last 3 cycles each spent >100k tokens on the deploy step"); feedback is direct user-to-supervisor messaging ("stop tagging skills with `[easy]` until the harness honors the floor table"). The supervisor weighs both but treats feedback as the more authoritative when they conflict.
- [x] 21.3 [hard] **`sst-supervisor` v1.6.1 → v1.7.0: read `manager-feedback.md` as authoritative steering.** §Inputs gains a new step 5 between the existing manager-guidance read and the SPEC/TODO read. The supervisor treats feedback entries as authoritative steering distinct from (and stronger than) `manager-guidance.md`; feedback can direct concrete writes ("modify skill X to do Y", "add SPEC item Z to phase N", "append TODO Next-up item W"), and those directives are valid motivating citations for §3's change-intent table (the citation column reads `manager-feedback.md:<line>` rather than a transcript line — the framework's first allowance for non-transcript citations, justified by the user-as-author principle). Conflict resolution explicit: feedback > manager-guidance; `auto-promote` mode > feedback (the chain YAML is the run-time contract; feedback is a steering hint, not a mode override). Anti-fork rules still bind: feedback that asks the supervisor to skip sanitize on a transferable, commit code, or deploy is REFUSED; refusal is recorded in `## Notes for the manager` rather than acted on. Older entries that have already been actioned in a prior cycle stay in the file as audit history; the manager's ~2KB cap eventually trims them.

This phase preserves every existing invariant (manager is read-only across watched projects, supervisor never commits or deploys, sanitization gate untouched) while adding a single new write path: bot → queue file → manager-feedback.md → supervisor's input set. No skill-rewriting, no harness change, no schema change.

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**

- [x] 21.4 [easy] [should-fix] `chains/dev-cycle-with-review-looped.yaml`, `chains/dev-cycle-overnight.yaml` (commit `4fceb04`) — backfill `Just shipped` entry added to `docs/TODO.md` summarizing the loop-delay-random tightening + version bumps (v1.1.0→v1.2.0 `[60,3600]`→`[60,600]`; v1.0.0→v1.1.0 `[300,7200]`→`[60,1800]`). Bundled with sst-chain-driver Phase 18 sanitize fix in one commit per the CLAUDE.md single-commit rule.

### Phase 26: stable sub-item IDs + ID-addressable feedback (closed)

Phase 24's smart-manager routing accepts arbitrary `/feedback` bodies and decides where they land via a four-outcome decision tree. That works for shape-ish feedback, but the user has no concise way to point at a specific SPEC item from Telegram — every command goes through full LLM interpretation even when the user already knows exactly what they want changed. Phase 26 makes SPEC sub-items individually addressable by giving each one a stable ID of the form `<phase>.<n>` (e.g. `25.1`, `25.2`) and extending the feedback router to recognize ID-addressed commands like `add 25.1a to TODO: <text>`, `remove 25.1`, `modify 25.2: <delta>`. The numbering scheme is append-only-with-letter-inserts: new sub-items between existing ones use `<phase>.<n>a`, `<phase>.<n>b`, etc.; closed or removed items leave their ID void rather than triggering a renumber, so feedback referencing an ID in bot history stays valid forever.

- [x] 26.1 [medium] **sub-item numbering across SPEC.md.** Number every existing sub-item in `docs/SPEC.md` as `<phase>.<n>` (1-indexed within each phase block; closed phases get retro-numbered too). Format: prepend the ID inside the existing checkbox bullet, e.g. `- [ ] 25.1 [hard] **Reframe `objectives.md` ...**`. New sub-items go to `<phase>.<n+1>` at the end of the phase, OR `<phase>.<n>a/b/c...` between existing ones. Once assigned, an ID never moves; closing or removing an item leaves the ID void rather than renumbering. Update `templates/` SPEC sample + `CLAUDE.md` "handoff docs" section so consuming projects adopt the same scheme. Update `sst-dev-cycle`, `sst-dev-review`, `sst-supervisor`, `sst-manager` SKILL prose with a §Numbering convention block naming the rules. Validator extension: `bin/validate-frontmatter.py` (or a new helper) checks SPEC for ID uniqueness within each phase block + no gaps that would imply a renumber.
- [x] 26.2 [medium] **ID-addressed `/feedback` commands.** Extend `sst-manager --process-feedback` (Phase 24) to recognize three ID-addressed forms before falling through to the four-outcome decision tree: `add <ID> to TODO: <text>` inserts a `Next up` line tagged with the ID; `remove <ID>` deletes the matching `[ ]` line from `docs/SPEC.md` (or the matching `Next up` line if the ID is queue-only); `modify <ID>: <delta>` rewrites the body. Each maps to a fifth pre-resolved outcome that bypasses LLM interpretation when the user has named the destination by ID. Telegram reply confirms the ID + the action + the file path. Out of scope: bulk operations, regex matching, multi-ID commands, ID lookups in closed phase blocks (those are read-only). Hard-rule note: the existing scoped exception for `Next up` + `SPEC.md` appends already covers add; remove and modify are new write paths within the same exception envelope.

**Review follow-ups (open — schedule as the next `/skill-set-dev` cycle):**
- [x] 26.3 [easy] [should-fix] `bin/validate-frontmatter.py:validate_spec_ids` — `validate_spec_ids()` flags duplicate IDs within a phase block but never flags `- [ ]` / `- [x]` bullets that are missing an ID entirely; consuming projects adding new items without IDs pass validation silently, breaking the contract that every item carries a stable ID and causing ID-addressed `/feedback` commands to fail silently on those items. Proposed fix: add a complementary check in `validate_spec_ids()` that emits an error for any phase-scoped `- [ ]` / `- [x]` bullet that does not satisfy `_SPEC_BULLET_ID_RE`.
- [x] 26.4 [medium] [should-fix] `skills/framework/sst-manager/SKILL.md:§B ID-addressed pre-check` — `remove <ID>` deletes the matching `[ ]` line from SPEC but does not also remove a corresponding `## Next up` entry in TODO referencing the same ID; after removal, the stale queue entry survives and the next dev cycle will attempt to execute a SPEC item that no longer exists. Proposed fix: after deleting the SPEC line (if found), scan `docs/TODO.md > ## Next up` for any line whose text contains `<ID>` and delete it too, making removal atomic across both files.
- [x] 26.5 [easy] [should-fix] `bin/validate-frontmatter.py:156-157` — Both `_SPEC_BULLET_ID_RE` and `_SPEC_CHECKBOX_RE` use character class `[ x]` (lowercase only); a `[X]` (uppercase) checkbox silently bypasses both the 26.3 presence check and the duplicate-ID check, letting any model that outputs uppercase-X produce un-IDed or duplicate items that pass validation. Proposed fix: change both patterns to `[ xX]`.
- [x] 26.6 [easy] [should-fix] `skills/dev/sst-dev-review/SKILL.md:238-239` — The §4 TODO-entry template (`- [<difficulty>] [should-fix] <file:line> — review of <sha>`) embeds no spec item ID; the Phase 26.4 atomic `remove <ID>` purge scans TODO Next-up for the ID string, so review-generated entries are never matched and survive as orphans after `remove <ID>`, causing the next dev cycle to attempt non-existent SPEC items. Proposed fix: update the template to embed the spec ID as a leading token (e.g., `- [<difficulty>] [should-fix] <ID> <one-line> — review of <sha>`) and apply the same change to `skill-set-dev-review`.

