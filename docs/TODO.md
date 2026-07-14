# skill-set TODO (handoff doc)

> Cross-cycle state. Every skill reads this on start and updates it on close. Three sections, in this order. Primary spec: `docs/SPEC.md`.

## In flight

- [ssp-dev @ 2026-07-14T01:19:49Z] 61.3 brave-web credential merge (free-in-env + paid-from-file)

## Just shipped (last cycle)

- Phase 61 (61.1-61.2): Cursor Brave web search/fetch (`bin/brave-web.py`, free→paid key) + `--approve-mcps`/`--trust`; Claude Code untouched (Sanitize: n/a) — by ssp-dev at 2026-07-14T01:15:27Z
- Phase 60.1: estimate Cursor harness $ cost from usage tokens (Grok 4.5 API rates fallback; --max-budget-usd re-enabled; Sanitize: n/a) — by ssp-dev at 2026-07-14T01:09:44Z
- Phase 59.2: ssp-chain-driver Locations retargeted — overnight jitter via `--overnight` / `--loop-delay-random` (v1.0.3; Sanitize: n/a, proprietary) — by ssp-dev at 2026-07-14T00:54:10Z
- Phase 59.1: remove redundant overnight chain YAMLs (`dev-cycle-overnight` + `skill-set-overnight`); overnight = `--overnight` on looped cycle; README/CLAUDE.md/tests updated (Sanitize: n/a) — by ssp-dev at 2026-07-14T00:48:37Z
- Phase 58.7: `Harness.apply_budget_constraints` no-op + `CursorHarness` override (loud-skip `--max-budget-usd`); removed module-level `_maybe_clear_cursor_budget` name-branch — by ssp-dev at 2026-07-14T00:43:52Z
- Default loop-delay is none: runner no longer injects DEFAULT_LOOP_DELAY_RANDOM when unset; `dev-cycle-with-review-looped` uses `loop-delay: 0` (overnight / `--overnight` keep 5-30min jitter) — by manual at 2026-07-14T00:39:51Z
- Phase 58.6: inject proxied `num_turns` when Cursor result emits null (not only when key absent) so summary prints "N turns" not "None turns"; regression test with explicit null key (25→26) — by ssp-dev at 2026-07-14T00:37:35Z
- Phase 58.5: Cursor telemetry gap closed — `usage`→`modelUsage` (cache key rename); `num_turns` proxy from assistant frames; `--max-budget-usd` loud-skipped under `--harness cursor` (prefer `--max-cycles`); overnight/infinite without cycles SystemExits after clear. 8 new tests (17→25); 614→622 green; README Cursor notes updated — by ssp-dev at 2026-07-14T00:30:13Z
- CLAUDE.md low-bandwidth rule: briefly note completed items (was "do not report routine successes") so the user can see work was not overlooked — by manual (stash pop from Phase 58 park) at 2026-07-14T00:23:00Z
- Phase 58 (58.1-58.4): Cursor harness finalization — live stream-json fixture (`tests/fixtures/cursor-stream-sample.jsonl`); `_cursor_tool_call_fields` maps live `editToolCall`/`readToolCall`/`shellToolCall` (path→file_path) so Phase 49 wrote_tester_guidance works; 17 unit tests in `test_cursor_harness.py`; README documents `--harness cursor` + CURSOR_MODEL ids (also lands dirty Phase 57 fable-off-by-default paragraph). Grok default already `cursor-grok-4.5-high` (33ea3f0), confirmed live. Telemetry gap (no cost/num_turns; usage tokens present) left on Next up — by ssp-dev at 2026-07-14T00:13:08Z

<!--
  Append-on-close, newest first. Format:
  - <one-line summary> — by <skill-name> at <utc-iso>
  No commit SHA: a commit cannot contain its own hash, and amend-based
  workarounds produce stale references. Correlate entries to commits via
  `git log --oneline --grep '<keyword>'`. Older entries below retain their
  SHAs from the prior two-commit pattern; leave them alone, they're valid.
  Trim to the most recent 10 entries; older history lives in docs/SPEC.md
  phase blocks and `git log`.
-->

## Next up (queued for next cycle)

<!--
  One line per queued item. The next cycle picks the top item unless the spec says otherwise.
  Format:
  - <one-line description> — <reason/source: spec phase X.Y, supervisor verdict <sha>, manager directive, user message>
  Order: blockers/highest-impact first.
-->

<!-- Priority: Cursor IDE browser is not available to cursor-agent -p; Playwright MCP is the chain browser. Phase 61 only passed --approve-mcps/--trust — tool still not first-class for Cursor harness. -->
- [medium] Cursor-harness web browser tool via Playwright MCP: ensure headless `cursor-agent` can call the project's Playwright browser MCP (config/`mcp.json` discovery, cold-start directive for tester/outreach/research skills that need a real browser, headed when DISPLAY exists); do not use Cursor IDE `cursor-ide-browser` (IDE-only) — source: user request 2026-07-14 (priority)

<!-- From 2026-07-14T01-03-22Z review of Phase 61 (7b96d31) + Phase 60.1 / 59.2 since last Review. -->
- [easy] [should-fix] 61.3 `bin/brave-web.py:_resolve_credentials` — early-return on either key set blocks paid-from-file when free is in env; merge missing keys so free→paid 429 fallback works — review of 7b96d31

<!-- Cursor still prints Claude Phase-19 fiction (opus/fable/xhigh) + fable-cap banner while every skill actually runs on CURSOR_MODEL / Grok. -->
- [medium] Cursor harness routing + stdout: map item difficulty / skill floors onto Grok effort ladder (`cursor-grok-4.5-{low,medium,high}[-fast]`, not Claude haiku/sonnet/opus/fable); print real model id + effort in `[route]` lines and MANIFEST `route` records; pass resolved id to `cursor-agent --model` (stop collapsing every skill to DEFAULT_CURSOR_MODEL) — source: user request 2026-07-14
- [easy] Suppress Claude-only fable toggle stdout under `--harness cursor`: do not print `[model] fable disabled…` / honor `--enable-fable` messaging (fable is not a Cursor tier); leave Claude Code path unchanged — source: user request 2026-07-14

<!-- Cursor capability gaps surfaced by harness dogfood runs 2026-07-14 (00-10-28Z + 00-27-32Z). Highest-impact first. -->
- [hard] Cursor has no Skill tool — nested `/sst-sanitize-transferable` (and other sub-skill) invocations from inlined skill prose cannot run; add a Cursor path (runner-spawned nested skill inline, or harness-aware prose: Read SKILL.md + follow) so transferable-editing cycles under `--harness cursor` still pass the sanitize gate — source: run analysis 2026-07-14 (Phase 58.5 skipped sanitize only because no transferable; next transferable cycle will hit this)
- [medium] Cursor has no `--max-turns` hard backstop (soft wind-down is tester-only / advisory); add a runner-side turn/watchdog (count assistant frames, kill or wind-down after N) under `--harness cursor` — source: run analysis 2026-07-14 (documented gap; runaway risk)

<!-- planner candidate tests-passing-fix (2026-06-25) resolved: the objectives.md pytest-path fix was applied directly in a live session; candidate removed, no dev-cycle pick needed. -->
