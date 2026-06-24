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

`SPEC.md` shape: long-lived, phase checklists with `- [ ]`/`- [x]`. Closed phases are compressed to a 1-paragraph context + a tight bulleted change log (one line per item); consuming projects keep them inline until the file grows unwieldy, at which point closed phases are archived to `docs/SPEC-DONE.md`. Phases that drift toward novella-length should be compressed back; git history + TODO `Just shipped` carry the detail.

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

> Completed phases live in [docs/SPEC-DONE.md](SPEC-DONE.md); deferred phases live in [docs/FUTURE-WORK.md](FUTURE-WORK.md). Active phases live below.

### Phase 46: remove the Phase 42 deprecation shims

**Context.** Phase 42.4/42.5 reduced `bin/drive-chain.py` and `bin/skill-batch.py` to thin deprecation shims that forward to the unified `bin/skill-chain.py`. Per user request, remove them entirely — the unified runner is the only entrypoint. Phase 42.6 already migrated every in-repo caller to `skill-chain.py`, so this is a clean deletion plus a scrub of the remaining shim-specific tests and references. Historical mentions in `docs/SPEC-DONE.md` (the Phase 42 record) are a changelog and stay.

- [x] 46.1 [medium] **Delete the shim scripts + their tests.** Remove `bin/drive-chain.py` and `bin/skill-batch.py`; remove or repoint their tests — `tests/test_drive_chain_telegram.py` (repoint to `skill-chain.py`'s native telegram path if it still covers live behavior, else delete) and the shim-forwarding cases in `tests/test_phase42.py`. Acceptance: both `bin/` files are gone; no test imports or invokes the deleted shims; full `tests/` suite green.
- [x] 46.2 [medium] **Scrub remaining shim references.** Ensure `skills/framework/sst-chain-driver/SKILL.md` (transferable — run `/sst-sanitize-transferable` before committing), `bin/notify-telegram.sh`, and `bin/skill-chain.py` reference only `skill-chain.py` (no functional `drive-chain.py`/`skill-batch.py` mention); leave the historical Phase 42 text in `docs/SPEC-DONE.md` intact. Acceptance: a `grep -rn "drive-chain.py\|skill-batch.py"` across `bin/`, `skills/`, `tests/` returns nothing (only `docs/SPEC-DONE.md` historical text remains); `/sst-sanitize-transferable` must-fix 0 on `sst-chain-driver`; `bin/validate-frontmatter.py` clean.

### Phase 47: README feature + usage overview

**Context.** The README has grown alongside the framework but lacks a concise top-level outline of what the skill-set provides — the transferable/proprietary model, the skill catalog, the chains, the unified runner CLI, and common usage examples — so a new user cannot orient quickly. This phase gives `README.md` a brief Features/Functionality section + a Usage-examples section. Do AFTER Phase 46 so every example uses the unified `bin/skill-chain.py` entrypoint and never the removed shims.

- [x] 47.1 [medium] **Features + functionality overview in `README.md`.** Add/refresh a concise section outlining: (a) what the framework is + the transferable/proprietary `sst-`/`ssp-` model; (b) the skill catalog (one line each — dev-cycle, dev-review, tester, supervisor, manager, executor, chain-driver, sanitize-transferable, plus the research/content/outreach families); (c) the chains (`dev-cycle-with-review`, `-looped`, `-overnight`, etc.); (d) the unified runner CLI flags (`--chain`/`--loop`/`--overnight`/`--batch`/`--max-budget-usd`/`--telegram-env`/`--profile`). Keep it an outline, not exhaustive prose. Acceptance: `README.md` has the Features/Functionality section covering (a)-(d); content matches the current code (skills present, flags exist); `bin/validate-frontmatter.py` clean.
- [x] 47.2 [easy] **Common usage examples in `README.md`.** Add a Usage section with copy-pasteable examples: run a chain (`bin/skill-chain.py --chain dev-cycle-with-review --loop N`), an overnight drain (`--overnight --max-budget-usd X`), batch mode (`<skill> --batch '<glob>'`), and the standalone tester sweep (`/sst-tester --phase <id>`). Use ONLY the post-Phase-46 unified entrypoint (no `drive-chain.py`/`skill-batch.py`). Acceptance: `README.md` has a Usage-examples section with the four examples above, all via `skill-chain.py`; no example references a removed shim.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 47.3 [easy] [should-fix] `README.md:75` — the batch mode usage example omits the required `--output-template` flag; running it as written exits with `--batch requires --output-template`. Proposed fix: append `--output-template 'reviewed/{stem}.md'` (or a clearer placeholder template) to the example command, and update `test_usage_batch_example` in `tests/test_phase47.py` to assert `--output-template` also appears in the README.

### Phase 48: looped standalone tester that drains a test-target queue and self-terminates

**Context.** Phase 44 gave `sst-tester` a one-shot standalone sweep (`--phase`/`--todos`). Users want to loop JUST the tester from the terminal so it drains a queue of UI/UX test targets one per iteration and self-terminates when none remain -- the tester analog of the dev cycle's `## Next up` drain + `[no-work]` loop-abort. Two gaps block this today: (a) `bin/skill-chain.py <skill> --loop N` cannot thread the tester's `--phase`/`--todos` scope into a looped ad-hoc run (strict `parse_args` rejects unknown flags), and more fundamentally a fixed `--phase` would re-run the identical full sweep every iteration with no notion of "done"; (b) there is no tester-side "no test work left" sentinel the loop runner recognizes, so a looped tester never bails. The CM project already maintains the queue shape this builds on: a `## Tester sweep targets` section in `docs/TODO.md` (one line per UI/UX target, tagged P1-P3 and covered|partial|GAP). This phase keeps the tester's existing guarantees intact: read-only on the tree, all artifacts out of tree, no handoff-doc edits, guaranteed teardown.

- [x] 48.1 [medium] **Canonical tester-target queue + a draining selector.** Adopt `## Tester sweep targets` in `docs/TODO.md` as the framework-standard tester queue and add it (with the one-line item format + P/coverage tags) to `templates/TODO.md`. Add to `skills/framework/sst-tester/SKILL.md` a "looped-standalone" scope resolver that, per iteration, selects the next target NOT yet recorded as exercised this run; the exercised-state is tracked OUT OF TREE at `~/.claude/state/sst-tester/<project-slug>/queue-<run-utc>.json` so the tester never edits the handoff doc or the tree. Acceptance: a unit test feeds a `## Tester sweep targets` block of K items plus an out-of-tree state with J<K already recorded and asserts the selector returns the first of the K-J unrecorded targets (and `None` when all K are recorded); `templates/TODO.md` contains the `## Tester sweep targets` section; `bin/validate-frontmatter.py` clean.
- [x] 48.2 [medium] **`[no-test-work]` bail recognized by the loop runner.** When the looped-standalone resolver finds no unrecorded target (queue drained, or the doc has no `## Tester sweep targets` section / no front-end targets), `sst-tester` prints a `[no-test-work]` sentinel and exits 0 WITHOUT starting a browser or the local stack. Extend `bin/skill-chain.py`'s loop-abort predicate (today keyed on `[no-work]` / `[blocked-on-human]`) to also break the loop on `[no-test-work]`. Acceptance: a test asserts `skill-chain.py`'s loop-abort triggers on a `[no-test-work]` skill result (the loop stops before reaching `--loop N`); the existing `[no-work]` dev-cycle bail and its test are unchanged; a `sst-tester` unit/contract test asserts the empty/absent-queue path emits `[no-test-work]` and spawns no stack/browser.
- [x] 48.3 [medium] **One-command looped terminal entrypoint + docs.** Make a single unified-runner command drive the drain: `bin/skill-chain.py <tester-skill> --loop N` enters looped-standalone mode when the positional skill is a tester and no `--chain` is set (no `--phase`/`--todos` needed -- the queue is the scope), draining one target per iteration and stopping early on `[no-test-work]`. Document it in `skills/framework/sst-tester/SKILL.md` (a "Looped standalone drain" subsection), the `README.md` Usage section (one copy-pasteable example, unified runner only), and mirror the CM example into `.claude/skills/ssp-cm-tester` (the CM `docs/TODO.md` already carries the queue). Acceptance: `README.md` Usage shows `bin/skill-chain.py <tester> --loop N` looping the standalone tester to queue-exhaustion; `sst-tester` SKILL.md documents the looped-standalone drain + the `[no-test-work]` bail; `bin/validate-frontmatter.py` clean; no example references a removed shim or a per-iter `--phase`.

**Phase 48 shipped — 2026-06-17**

- `templates/TODO.md`: added `## Tester sweep targets` section with queue format (P1/P2/P3 priority tags, covered/partial/GAP coverage tags, run hint).
- `skills/framework/sst-tester/SKILL.md` (v1.1.0 → v1.2.0): Three modes D1 dispatch updated; new `## Looped standalone drain` section (queue format, draining selector algorithm, `[no-test-work]` bail, exercised-state file contract, authority/guarantees); description frontmatter extended.
- `bin/skill-chain.py`: added `NO_TEST_WORK_SENTINEL_RE`, sentinel scanning in assistant-text handler, loop-abort in `run_iteration`, loop-abort in outer `main()` loop (`terminated_by: "no_test_work_bail"`).
- `README.md`: added looped tester drain example to `## Usage`.
- `tests/test_phase48.py`: 23 tests (4 selector unit, 3 template/SKILL prose, 7 sentinel RE + integration, 2 SKILL prose, 7 SKILL/README prose + version).
- Test count: 414 → 437. Sanitize: must-fix=0.

**Review follow-ups (open — schedule as the next `/sst-dev-cycle` cycle):**
- [x] 48.4 [easy] [should-fix] `skills/framework/sst-tester/SKILL.md:62` — D1 dispatch summary rule says "their absence with a `## Tester sweep targets` queue present selects looped-standalone mode" with no in-chain discriminator; a project that populates the queue AND runs the tester in-chain (dev+tester+review chain) would incorrectly enter looped-standalone mode instead of testing the dev cycle's changes. `SKILL.md:132` in the Standalone-mode D1 paragraph also says "With neither flag the skill runs in-chain (default) exactly as before" — stale now that looped-standalone is a third mode. Proposed fix: update line 62 to add the in-chain discriminator ("... AND no `tester-guidance.md` from the preceding dev skill, i.e. not invoked in-chain"); update line 132 to acknowledge looped-standalone as the other non-standalone path when a queue is present.

### Phase 49: sst-tester wind-down false-claim fix + looped-standalone session contract

**Context.** Phase 48's live looped-standalone assessment (2026-06-17) revealed two contract gaps: (a) `WIND_DOWN_DIRECTIVE_TEMPLATE` in `bin/skill-chain.py` falsely claims "the harness enforces a hard ceiling of {hard} agent turns" — untrue when the tester is launched via the Skill tool or a manual invocation where no `--max-turns` is in force; (b) the looped-standalone section's flush, per-session budget, and canonical-drain contract were implicit rather than explicit; a live T7-T15 drain ran 471 turns by draining 9 targets in one session instead of one target per separately-budgeted subprocess.

- [x] 49.1 [medium] **Soften `WIND_DOWN_DIRECTIVE_TEMPLATE` false enforcement claim.** Change "the harness enforces a hard ceiling of {hard} agent turns for this skill" to conditional language ("if a hard ceiling is in force it is {hard} agent turns") so the text is accurate both in-chain (where `--max-turns` is enforced) and standalone (where no chop is in force). Update the Operating Principles "Wind down before the turn cap" bullet in `sst-tester SKILL.md` to acknowledge standalone launches where the hard cap may be absent. Acceptance: test asserts template does NOT contain "the harness enforces a hard ceiling"; test asserts template DOES use conditional language; wind-down bullet mentions "standalone" or "whether or not a hard ceiling will actually arrive".
- [x] 49.2 [medium] **Harden looped-standalone per-target flush + session budget contract.** Add `### Per-target flush and session budget` to `sst-tester SKILL.md` explicitly requiring: (a) write each target's verdict to the out-of-tree state as soon as it is verdicted; (b) do not drain a multi-target range past the soft budget in one session; (c) `bin/skill-chain.py <tester> --loop N` is the canonical (separately-budgeted) approach. Bump version to 1.5.0; update `ssp-cm-tester base-version` to 1.5.0. Acceptance: tests assert flush, session limit, and "canonical"/"separately-budgeted" in SKILL.md; version >= 1.5.0; sanitize must-fix=0.
- [x] 49.3 [medium] **Runner-level "never both" enforcement: void `[skip-tester]` when the dev wrote `tester-guidance.md` the same run.** A dev skill that writes a `tester-guidance.md` this run has, by writing it, committed the cycle to a tester RUN; emitting `[skip-tester]` in the same run is a self-contradiction the prose-level "pick exactly one" rule did not converge on over repeated iters. Detect the guidance-file write in `handle_event` (sets `skill_record["wrote_tester_guidance"]`, keyed on the skill's own tool-use this run, not a stale on-disk file); in `run_iteration`, when the dev emits `[skip-tester]` AND wrote guidance, VOID the skip (run the tester anyway, the safe direction, and record `tester_skip_voided` in the manifest) instead of popping the tester; honor `[skip-tester]` unchanged when no guidance was written. Mirrors the Phase 36 incomplete-cycle block: runner enforcement of a contract prose-level defenses could not uphold. Acceptance: tests assert (a) `handle_event` sets the flag on a `tester-guidance.md` write and ignores other file writes; (b) `run_iteration` voids the skip when guidance was written and honors it otherwise; full suite green.

**Phase 49 shipped — 2026-06-17**

- `bin/skill-chain.py`: `WIND_DOWN_DIRECTIVE_TEMPLATE` reworded from unconditional "the harness enforces a hard ceiling" to conditional "if a hard ceiling is in force it is {hard} agent turns"; comment updated.
- `skills/framework/sst-tester/SKILL.md` (v1.4.0 → v1.5.0): Operating Principles wind-down bullet extended to acknowledge standalone launches; new `### Per-target flush and session budget` subsection in Looped standalone drain.
- `Dev/claim_management/.claude/skills/ssp-cm-tester/SKILL.md`: `base-version` updated 1.4.0 → 1.5.0.
- `tests/test_phase49.py`: 8 new tests (3 template conditional-language, 4 SKILL.md prose, 1 version).
- Test count: 446 → 454. Sanitize: must-fix=0.
- 49.3: runner-level never-both enforcement -- `handle_event` sets `wrote_tester_guidance` on a `tester-guidance.md` tool-use; `run_iteration` voids a same-run `[skip-tester]` (records `tester_skip_voided`) instead of popping the tester. 4 new tests in `tests/test_skill_chain.py`; 454 → 458 green.

### Phase 50: transient server-error (529 Overloaded / 5xx) exponential-backoff retry in the runner

**Context.** The 2026-06-23 `cm-cycle` run (`.skill-runs/2026-06-23T01-54-21Z_cm-cycle/`) was requested for 30 iterations but died at iteration 17: the `ssp-cm-dev` subprocess returned `API Error: 529 Overloaded` (`iter_17/00_ssp-cm-dev.{txt,jsonl}`) and the loop aborted on the non-zero exit (per SPEC "A non-supervisor skill failure aborts the whole loop"). A 529 is a transient, self-clearing server overload, not a quota event; the correct response is a short exponential-backoff retry, not termination. Two retry layers are relevant and must NOT be conflated: (a) the Claude Code harness ALREADY retries internally (the run shows `{"type":"system","subtype":"api_retry","attempt":N,"max_retries":10,"error_status":529,"error":"overloaded"}` events) and the 529 outlasted all 10 of those internal retries; (b) the runner `bin/skill-chain.py` has NO outer retry for this case. Today `run_skill_with_retry` retries ONLY rate-limit signals: it reads `rate_limit_signal` (structured `rate_limit_event` matching `RATE_LIMIT_FATAL_STATUSES`) or `rate_limit_text_match` (`RATE_LIMIT_TEXT_RE`), and at the "Ordinary failure, not a rate-limit. Pass through." branch it returns any other non-zero exit immediately. A 529 carries neither rate-limit marker, so it falls straight through and aborts the loop. The fix is a SECOND, outer retry layer in the runner: on a transient 5xx, re-invoke the killed skill via `--resume <session_id>` after an exponential backoff (with jitter), capped at 10 runner-level retries, then give up. This is independent of `--on-rate-limit` / `--max-pauses-per-session` (those are tuned for quota resets, up to 8h) and independent of the harness's own internal `max_retries`.

- [ ] 50.1 [medium] **Capture a transient-server-error signal distinct from the rate-limit signal.** In `bin/skill-chain.py`, recognize transient 5xx server errors from the harness stream and store them on the skill record analogous to `rate_limit_signal` / `rate_limit_text_match`. Detection sources (claude-code harness fields, kept behind the same event-handling path the `rate_limit_event` capture already uses, so a future `Harness` subclass can normalize them): (a) the final `result` frame's `api_error_status` field in `OVERLOAD_HTTP_STATUSES = {500, 502, 503, 504, 529}` with `is_error: true`; (b) `{"type":"system","subtype":"api_retry","error_status":<5xx>}` system events (informational, count them onto the record); (c) a text fallback `OVERLOAD_TEXT_RE` matching `API Error: 5\d\d` and/or `overloaded` in the `result` text or merged stderr, for the case the structured field is absent. Store `skill_record["overload_signal"] = {"status": <int>, "source": ...}` (and an `overload_retry_events` count) WITHOUT colliding with the rate-limit fields; a failure that is BOTH (should not happen) prefers the rate-limit path. Acceptance: unit tests assert (a) a `result` frame with `api_error_status: 529, is_error: true` sets `overload_signal` and NOT `rate_limit_signal`; (b) an `api_retry` system event increments the event count; (c) the text fallback fires when only the `API Error: 529` result text is present; (d) a clean rate-limit event still sets `rate_limit_signal` and NOT `overload_signal`.
- [ ] 50.2 [medium] **Exponential-backoff retry path for transient server errors in `run_skill_with_retry`.** When `run_skill` returns a non-zero exit whose record carries an `overload_signal` (and no rate-limit signal), retry with exponential backoff instead of passing through: sleep `min(OVERLOAD_BACKOFF_CAP_SECONDS, OVERLOAD_BACKOFF_BASE_SECONDS * 2**attempt)` plus random jitter (reuse the `RATE_LIMIT_JITTER_RANGE` style), then re-invoke the skill via `--resume <session_id>` (same resume mechanism the rate-limit path uses so the agent picks up mid-skill), archiving each failed attempt via `_archive_attempt`. Cap at `OVERLOAD_MAX_RETRIES = 10` runner-level retries (NOT the harness's internal `max_retries`); on exhaustion, give up and return the failure with `record["overload_aborted"] = "overload_retries_exhausted"` (mirrors the `max_pauses_reached` abort), letting the loop terminate as it does today. Keep this separate from the rate-limit pause budget: `--max-pauses-per-session` must NOT be consumed by overload retries, and an overload retry must not trigger the 8h pause logic. Add an `--max-overload-retries N` CLI flag (default 10) mirroring the rate-limit knobs; record per-retry entries (an `overload_retry_records` list folded into the iteration manifest like `pause_records`) and fire the `notify` callback (`overload-retry` / `overload-resume`) so the chain-driver reports it like rate-limit pauses. Suggested defaults: `OVERLOAD_BACKOFF_BASE_SECONDS = 10`, `OVERLOAD_BACKOFF_CAP_SECONDS = 300`. Acceptance: tests assert (a) a 529-failing-then-succeeding skill is retried and returns rc 0 with `retry_count` recorded; (b) backoff grows exponentially and is capped (assert the computed sleep sequence, jitter stubbed/seedable); (c) after 10 consecutive overload failures the wrapper gives up with `overload_aborted = "overload_retries_exhausted"` and does NOT loop forever; (d) an ordinary (non-5xx, non-rate-limit) failure still passes through immediately with zero overload retries; (e) the rate-limit pause path and its `max_pauses` accounting are unchanged; (f) overload retries do not decrement the rate-limit pause budget.
- [ ] 50.3 [easy] **Document the new retry layer + flag.** Update `bin/skill-chain.py`'s module docstring/epilog, `README.md` (the rate-limit / resilience prose and the CLI flags list), and `skills/framework/sst-chain-driver/SKILL.md` (transferable -- run `/sst-sanitize-transferable` before committing) to document: the transient-5xx exponential-backoff retry, the `--max-overload-retries` flag (default 10), that it is distinct from `--on-rate-limit` / `--max-pauses-per-session`, and that it sits OUTSIDE the harness's own internal `api_retry` (so "10 retries" is the runner layer, not the harness layer). Note the new manifest fields (`overload_signal`, `overload_retry_records`, `overload_aborted`). Acceptance: README CLI table lists `--max-overload-retries`; the resilience prose distinguishes overload-retry from rate-limit pause; `bin/validate-frontmatter.py` clean; `/sst-sanitize-transferable` must-fix 0 on `sst-chain-driver`.

**Acceptance (phase):** new `tests/test_phase50.py` covering 50.1 + 50.2 detection/backoff/cap/give-up/passthrough cases; full `tests/` suite green; `bin/validate-frontmatter.py` clean; sanitize must-fix 0 on any transferable touched.
