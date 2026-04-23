---
name: dev-cycle
description: Autonomous test-driven development cycle. Reads the project's spec + handoff TODO, picks the next queued or unchecked item, writes failing tests first, implements until the full test suite is green, commits (code + tests + spec + TODO update in one commit), pushes, deploys if the project has a deploy path, and verifies production. Runs end-to-end without pausing for confirmation.
user-invocable: true
version: 1.0.0
---

# Autonomous TDD Cycle

One invocation = one shipped change. Read the spec, decide, write failing tests, implement, deploy, verify, commit + push. **No approval prompts between steps.** This skill is the user's standing authorization for the whole cycle.

## Operating principles

- **Run to 100% completion. Never stop to ask.** If a step fails, diagnose and fix the root cause and retry. Only escalate to the user if you've exhausted reasonable attempts on an external blocker (server unreachable, missing credential, ambiguous spec wording that can't be resolved by reading the code).
- **Tests define done.** Write the failing test first. If the test would require a mock that contradicts the real architecture, fix the test design — don't write implementation-first to "see what shape makes sense."
- **Small scope per cycle.** One unchecked spec item (or one bug). Don't bundle unrelated changes. If you notice an adjacent issue, note it in the spec's deferred list or a follow-ups file rather than fixing it inline.
- **One commit.** Implementation + tests + spec + TODO update in a single commit. Push once. No separate spec-only or TODO-only push.
- **Fix root causes, never mask failures.** No `@pytest.mark.skip`, no `xfail`, no `-k` to exclude failing tests, no deleting assertions "temporarily." If a test is wrong, fix the test with a clear rationale; if the code is wrong, fix the code.

## Handoff docs (read on open, update on close — every cycle)

Two canonical files per project carry cross-cycle state. Default location `<project>/docs/`; the project's harness-instructions file (e.g. `CLAUDE.md`) overrides if it points elsewhere via a `Handoff docs:` line.

- **`SPEC.md`** (or the project's existing primary spec — `docs/<project>_SPEC.md` is common) — long-lived phase checklists, closed-phase change logs.
- **`TODO.md`** — three sections: `## In flight` (one line per running skill), `## Just shipped (last cycle)` (newest-first, max 10), `## Next up (queued for next cycle)` (one line per item, ordered by impact).

Contract for every cycle:

1. **Open**: read both end-to-end before any other action. If `TODO.md` is missing, create it from `~/Dev/skill-set/templates/TODO.md` as the very first action; commit that creation as part of this cycle's single commit. Do not invent a different shape.
2. **Decide** (see §1 below): pick from `TODO.md`'s "Next up" if non-empty, else from the spec's next unchecked item.
3. **Mid-cycle**: append a single `## In flight` line at the start of work in this format: `- [<skill-name> @ <utc-iso>] <one-line>`. Rewrite (don't append again) as the work narrows. Do not commit mid-cycle "In flight" updates; they live unstaged until the close commit.
4. **Close** (see §5–6 below): move the in-flight line to "Just shipped" with the commit SHA-short; if the cycle uncovered new work that doesn't belong in the spec, append it to "Next up." Trim "Just shipped" to the most recent 10 entries.
5. Both `SPEC.md` and `TODO.md` ship in the same commit as the code change (see §6).

## 0. Pre-flight

1. Confirm the working directory is the project root (check for `.git`, the project's config/manifest file).
2. Activate any language-specific environment the project uses (venv, node_modules, etc.).
3. Confirm `git status` is clean. If there are staged or modified files from a prior aborted run, inspect them and either commit them (if they represent finished work) or stash/discard them before starting — do not silently include them in this cycle's commit.
4. Read `docs/SPEC.md` (or the project's primary spec — see §1) end-to-end.
5. Read `docs/TODO.md` end-to-end. If missing, create it from `~/Dev/skill-set/templates/TODO.md` and stage it for inclusion in this cycle's single commit; do NOT make a separate "create TODO" commit.

## 1. Decide what to work on

Find the project's spec or roadmap. Common locations: `docs/SPEC.md`, `docs/ROADMAP.md`, `TODO.md`, `README.md`, the top-level docstring of a main module, or a `docs/<project-name>_SPEC.md` variant. If multiple exist, prefer the most-recently-edited one and scan for a "primary spec" pointer.

Selection priority:
1. **`TODO.md`'s "Next up"** — top entry first. These are queued items already vetted by the previous cycle, supervisor, manager, or user. Treat the source/reason annotation on the entry as the authority for *why* you're doing it.
2. If "Next up" is empty: items in the spec explicitly flagged as open gaps / blockers (labels vary: "V1 Status", "Known Issues", "TODO", "Open", `- [ ]`).
3. The next unchecked `- [ ]` in the spec's newest active section.
4. If everything checkable is checked, look at any "Deferred / Out of scope" list for items whose blocking reason no longer applies.

Tie-break by: smallest surface area → most independent → highest user impact. If the user gave a specific request, that overrides everything above (also: append the request to "Next up" first, so the audit trail is intact).

Record the pick by writing the `## In flight` line in `TODO.md` now: `- [<this-skill-name> @ <utc-iso>] <one-line description of the picked item>`. Don't commit yet; this gets committed alongside the code change at the end of the cycle.

## 2. Write failing tests

**Before writing any implementation code, write the tests that define the new functionality.**

1. Identify the right test file. Mirror the naming and style of adjacent tests.
2. Write tests that describe the desired behavior at the right level:
   - For user-facing changes: an end-to-end test that exercises the actual user journey (Playwright / browser automation for web; CLI invocation + output check for command-line tools; API call + response-shape assertion for backends).
   - For library/internal changes: unit tests on the public interface.
   - Always include at least one adversarial case (bad input, unauthenticated caller, boundary condition) and any invariant the change must preserve.
3. Run just the new tests to confirm they fail for the expected reason (missing feature, not broken test setup):
   ```bash
   <test-runner> <new-test-file> -v
   ```
4. If a new test passes immediately, strengthen it until it fails or delete it — a passing new test either doesn't test the new behavior or is redundant.
5. Confirm existing tests still pass at this point. You should not have broken anything yet.

## 3. Implement

1. Write only the code required to make the failing tests pass. Reuse existing helpers and patterns; don't invent parallel abstractions.
2. After each change, re-run the failing tests. As each goes green, move on.
3. Always read the target file before editing. Use precise string matches.
4. For web projects: if you change backend code, restart the local dev server before re-running browser tests.

## 4. Verify — fail-loop until green

```bash
<test-runner> <relevant-tests> -v     # fast iteration
<test-runner> <full-suite>            # final gate
```

Record the full-suite pass count before your change. After, it must be `old_count + <new_tests>` (or higher, if you incidentally fixed a flake). If it drops, you broke something — fix before continuing.

On failure:
- Read the actual assertion. Don't guess.
- Fix the root cause. If a test is incorrectly asserting, fix the test with a clear rationale noted in the commit message; if the code is wrong, fix the code.
- Re-run. Repeat until green.
- **Never skip, xfail, or `-k`-exclude failing tests to move on.**

If the project has known-flaky test files that are separately tracked, explicitly list them in the command (ignoring a known-flaky file is fine; ignoring a file because YOUR change made it fail is not).

For UI changes, also verify in a real browser (Playwright MCP against a local dev server). Target zero console errors. Stop the local dev server when you're done verifying.

## 5. Update the spec + TODO.md

**`SPEC.md`**: flip `- [ ]` to `- [x]` for what you shipped. If this closes a sub-phase or milestone, add a section mirroring the format of the most recent completed one: 1-paragraph context, bulleted checklist of changes with file citations, test-count delta. Update any index / status summary file that the project keeps (e.g. a `CLAUDE.md` phase list).

**`TODO.md`** — three updates, in order:

1. Move the line you wrote to `## In flight` in §1 over to `## Just shipped (last cycle)` at the top: `- <sha-short> <one-line summary> — by <this-skill-name> at <utc-iso>`. Use the SHA-short from the commit you're about to make (you'll know it after the commit lands; do this update in §6 after the first `git commit`, or pre-write a placeholder and amend — placeholder + amend is cleaner since the commit body is one atomic unit).
2. If you uncovered new work that doesn't merit a spec edit (small follow-ups, adjacent fixes, deferred polish), append each to `## Next up (queued for next cycle)` with format `- <one-line> — <reason/source>`.
3. Trim `## Just shipped (last cycle)` to the most recent 10 entries; older entries are reflected in `SPEC.md` checkboxes and `git log` already.

## 6. Commit + push

Stage only the files you changed (by name — no `git add -A`, which sweeps up secrets and noise). Bundle implementation + tests + spec update + TODO.md update + any index-file update in ONE commit:

```bash
git add <code-files> <test-files> <spec-file> docs/TODO.md <index-file>
git commit -m "$(cat <<'EOF'
<Scope>: <one-line imperative summary>

<Paragraph on why this change, what it does, and any non-obvious
decisions. Reference the failing-test evidence or the issue it closes.>

Test count: <old> → <new>.

EOF
)"
git push origin <branch>
```

(If you pre-wrote a placeholder SHA in `TODO.md`, run a `git commit --amend --no-edit` after editing the SHA in, then push.)

Never append "Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>", or similar, to commit messages!
Scope tags match the project's convention (examples: `Auth:`, `UI:`, `Docs:`, `Tests:`, `Deploy:`, `Infra:`, or a feature area like `Leads:`).

Never commit `.env` files, credentials, or local scratch files. If the project gitignores config dirs (e.g. `deploy/`, `docs/` in some layouts), those changes won't reach the remote — you'll need the project's separate sync mechanism (scp, rsync, a sync script) for those.

## 7. Deploy

If the project has a deploy path (SSH to a VPS, CI workflow, `deploy/` script, container rebuild), run it. The specific command is project-specific and should be documented in the project's `CLAUDE.md`, `README.md`, or a deploy script — read it there, don't guess.

If the change involves a schema migration or new config, run that first before restarting the service. Never use `kill -9` / `pkill -9` on a managed service; use the service's own stop/start or graceful-reload command.

After the deploy completes, confirm:
- The service health check returns OK.
- The expected number of worker processes is running (if the project uses a worker model).
- No stack traces in the most recent log entries.

## 8. Verify production

Exercise the specific thing you changed against the live environment:
- API change: real HTTP call with real credentials, assert the response shape.
- UI change: Playwright MCP against the production URL, navigate to the changed page, 0 console errors.
- Background-job change: submit a real small job and confirm it completes.

Reuse the project's permanent test account or staging credentials — never create ad-hoc accounts.

If verification fails:
- Minor issue (copy, layout nit): fix forward in a new cycle.
- Regression that breaks existing users: revert the deploy (`git revert HEAD; git push`, then re-run the deploy command) and file the proper fix as the next cycle's work.

## 9. Done

The cycle is complete when:
- All new and existing tests pass locally.
- The commit is pushed.
- The deploy completed and the service is healthy.
- The changed behavior is verified live.
- The spec reflects the new state.

Report a terse summary to the user: commit SHA, one-line description, test-count delta, production verification result. No follow-up question.
