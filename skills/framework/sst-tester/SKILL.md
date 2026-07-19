---
name: sst-tester
description: |
  Interactive UI/UX test stage that runs between the dev cycle and the review.
  After the dev skill commits, the tester resolves what changed, starts the
  project's local front+back-end stack, drives the affected surfaces in a real
  browser (headed when a display exists, headless fallback), writes a structured
  findings artifact for the reviewer, then tears the stack down and exits cleanly
  — never persisting screenshots, traces, or any test-time artifact inside the
  repo tree. Self-skips to a no-op when the project has no local-run/browser path
  or the cycle touched no front-end surface. Never commits, deploys, or edits repo
  source. Wrapped by a proprietary per-project skill that supplies the exact ports,
  start/stop commands, auth-state path, and e2e specs. Also runs standalone from the
  terminal (`--phase <id>` / `--todos <ref...>`) to sweep every UI surface a whole
  phase or set of completed todos introduced. Runs in looped-standalone drain mode
  (`bin/skill-chain.py <tester> --loop N`) to drain a `## Tester sweep targets`
  queue one target per iteration, self-terminating on `[no-test-work]` when the
  queue is exhausted.
user-invocable: true
version: 1.11.0
model-floor: opus
effort-floor: high
---

# Interactive UI/UX Tester

One invocation = one runtime pass over the front-end surfaces a dev cycle just changed. This skill sits **after the dev skill and before the review skill** in a dev chain: the dev cycle ships a commit, the tester spins up the running app and drives the changed surfaces in a browser, and the reviewer then reads the tester's findings alongside the diff instead of judging UI work from the diff alone.

This is the project-agnostic transferable. It owns the **contract** — chain position, authority envelope, run lifecycle, degrade/self-skip discipline, headed/headless policy, the out-of-tree artifact rule, and the findings format. A proprietary wrapper (e.g. an `ssp-*-tester`) supplies the concrete facts this skill deliberately does not hardcode: the exact ports, the start/stop commands, the saved-auth-state path, and the mapping from changed surfaces to the project's e2e specs. Nothing in this file names a port, a path, or a project.

## Operating principles

- **Observe, never mutate the tree.** The tester is read-only on the repo. It starts and stops local servers, drives a browser, and writes findings — it never commits, never deploys, never edits repo source, and never pushes. (See **Authority envelope** below.)
- **Degrade, don't hang.** Every external dependency (a server that won't come up, a stale login session, a surface that 404s) becomes a *finding*, not a blocked run. The tester never blocks on an interactive prompt and never waits without a timeout. A run that can reach only half the surfaces reports on that half and records the rest as degraded. This includes the browser ITSELF hanging: a surface that freezes or crashes the page's main thread must become a hang *finding* and a browser recovery, never a hung tester (see **Browser hang / unresponsive page** below).
- **Add value or get out of the way.** If there is nothing front-end to exercise — no local-run path, or a cycle that touched no UI surface — the tester exits 0 as a clean no-op (`verdict: skipped`). Adding this stage to a non-UI chain is harmless.
- **Leave no trace.** Zero files under any repo working tree. Binary artifacts (screenshots, traces, video) go to an out-of-tree state dir; the reviewer-facing findings doc goes to the chain run-log dir (already gitignored). The servers are always torn down even on exception or timeout. The browser is closed too by default — UNLESS the wrapper defines a browser-reuse policy that keeps one long-lived browser open across runs (see **Teardown**); a deliberately-reused browser is the one sanctioned exception to full teardown and is not an orphan.
- **Author no committed specs.** The tester RUNS the project's existing e2e specs mapped to the changed surfaces and does exploratory checks of net-new functionality, but it does NOT write committed spec files — authoring "failing tests first" stays the dev cycle's job. A coverage gap is filed as a finding, not closed by writing a spec.
- **Wind down before the turn cap — or the soft budget, regardless.** Of all the chain's agents the tester is the one most likely to approach the harness's per-agent turn ceiling (long browser / tool-call sweeps). The chain runner injects a soft turn-budget directive into the tester's prompt naming a working budget below the hard cap. When invoked standalone (manual `/sst-tester`, a Skill-tool invocation, or a looped-standalone drain) the same directive may reach you WITHOUT a real hard cut behind it — honor the soft budget as self-pacing whether or not a hard ceiling will actually arrive; do not wait to feel the ceiling. As you approach the budget, stop opening new surfaces: write the findings you already have to a clean state, run teardown, and exit so the reviewer (or the next looped iteration) gets a usable handoff instead of a mid-sweep chop. A partial-but-clean findings record beats being cut off.

## Chain position

The tester is inserted immediately between the dev skill and the review skill:

```
<dev-skill> → sst-tester → <review-skill>
```

It runs only after the dev cycle has committed (so the changed surfaces are on disk and HEAD reflects them) and before the reviewer forms its verdict (so the reviewer can read the findings). Two skip paths keep it from running when it adds nothing:

- **Dev pre-empt.** When the dev cycle's work has no front-end/UI surface, the dev skill emits a `[skip-tester] <reason>` sentinel on its final line and the chain runner skips this stage entirely (the tester is never spawned) and proceeds straight to review.
- **Tester self-skip.** If the tester IS spawned but finds legitimately nothing FE/UI exercisable against the dev's work, it exits 0 as a no-op and writes a findings record with `verdict: skipped`.

A pre-empted or self-skipped tester is a valid, non-finding state for the reviewer — distinct from `degraded` (which means the tester tried to exercise a surface and couldn't reach part of it).

## Three modes: in-chain vs standalone vs looped-standalone (D1)

This skill detects its mode from its args and environment; there is no separate skill:

- **In-chain mode (default; no scope args).** Spawned by the dev chain between the dev skill and the review skill, scoped to what the LAST dev cycle changed (the `git show HEAD` diff + the dev's `tester-guidance.md`). This is everything **Run lifecycle** below describes. Findings go to the chain run-log dir for the reviewer.
- **Standalone mode (`--phase <id>` and/or `--todos <ref...>`).** Invoked directly by the user from the terminal to deliberately exercise EVERY UI/UX surface a whole phase, or a named set of completed todos, introduced (not just the latest diff). Resolves a surface set from the scope args (D2), iterates over all of them accumulating findings (D3), and writes the findings out-of-tree (D4). See **Standalone mode** below.
- **Looped-standalone mode (no scope args; `## Tester sweep targets` queue present).** Invoked via `bin/skill-chain.py <tester-skill> --loop N` with no `--phase`/`--todos`. Selects the next unexercised target from the `## Tester sweep targets` section of `docs/TODO.md`, exercises it, and exits. Each iteration drains one target; the out-of-tree exercised-state file at `~/.claude/state/sst-tester/<project-slug>/queue-<run-utc>.json` accumulates across iterations so each pass picks a fresh target. When the queue is exhausted (or absent), emits `[no-test-work]` and exits 0 WITHOUT starting the browser or local stack; the chain runner aborts the loop on this sentinel. See **Looped standalone drain** below.

The presence of `--phase` or `--todos` selects standalone mode; their absence with a `## Tester sweep targets` queue present AND no `tester-guidance.md` from the preceding dev skill (i.e. not invoked in-chain) selects looped-standalone mode; their absence with no queue, or when `tester-guidance.md` is present (in-chain invocation), runs in-chain. All three modes share the same authority envelope, the same headed/headless policy, the same guaranteed teardown, the same out-of-tree artifact rule, and the same findings contract. Mode changes only *what* is in scope and *where* the findings land, never the read-only / no-commit / no-deploy guarantees.

## Authority envelope (D5)

The tester's authority is strictly bounded. It MAY:

- start and stop the project's local front-end and back-end servers;
- drive a browser against `localhost` surfaces;
- read the repo (git history, the diff, the handoff docs, the project's e2e spec files);
- write the findings artifact to the run-log dir and binary artifacts to the out-of-tree state dir.

It MUST NOT, under any circumstance:

- commit, amend, or push — the tester **never commits**;
- deploy or restart any non-local / managed service — the tester **never deploys**;
- edit, create, or delete any file under the repo working tree (the e2e specs it runs are read and executed, never modified);
- spawn another harness or chain;
- invoke another skill via the Skill tool, or file follow-up items into the project's handoff docs. The tester writes `tester-findings.{md,json}` and **exits**; the chain runner spawns the next stage (e.g. the review skill). The tester never hands off by *calling* the next skill itself, and never escalates its own findings into a SPEC/TODO backlog or any review-owned doc (turning a `fail` into a backlog item is the review stage's job, per the **Findings contract**). The leave-no-trace check does NOT cover this: handoff docs are typically gitignored, so editing them leaves `git status --porcelain` clean, and an empty git status does NOT license a handoff-doc write or a skill invocation.

A wrapper inherits this envelope unchanged and may only *narrow* it (e.g. an explicit "never touch this project's protected branches" rule).

## Run lifecycle

The chain runner reports the run-log directory on every invocation as `[log-dir] <path>`. Resolve it from there (or, when invoked standalone, default to the most recent `.skill-runs/<*>/` directory under the current working directory). All steps below run inside a guaranteed-teardown wrapper (see **Teardown** — the teardown fires even if an early step throws or times out).

1. **Read the dev's guidance + derive what changed.** Read the dev-authored `tester-guidance.md` from the run-log dir if present (D6): it names the most meaningful surfaces/flows to exercise this cycle, each tied to a changed file or feature. Use it to prioritize the highest-value checks rather than re-deriving everything. Independently derive the change set as a cross-check and as a fallback when no guidance exists:
   - `git show HEAD --stat` and `git show HEAD` — the files and hunks the dev cycle committed;
   - `docs/TODO.md`'s `## Just shipped (last cycle)` top entry — the human-readable summary of what shipped;
   - the SPEC items the dev cycle flipped to `[x]` (diff `docs/SPEC.md` against the prior commit) — the intended behavior.
   Map the changed files to front-end surfaces (routes, components, views). If none of the changed surfaces is front-end/UI, go to step 2's self-skip.
2. **Self-skip decision (D4 / D7).** If the project documents no local-run/browser path, OR the change set touches no exercisable front-end surface, write a findings record with `verdict: skipped` and a one-line reason (`no local-run path; nothing to exercise`, or `cycle touched no front-end surface`) and exit 0. Do not start any server.
3. **Start the local stack.** Start the project's back-end and front-end servers (the wrapper supplies the exact commands). Capture each server's stdout/stderr to the out-of-tree state dir so a crash is diagnosable without polluting the repo.
4. **Poll readiness with a timeout.** Poll each server's readiness endpoint/port until ready or a bounded timeout elapses. If a server never becomes ready, record a `degraded` finding naming which server and its captured log tail, and continue with whatever surface IS reachable (or self-skip to `degraded` if nothing is reachable).
5. **Establish session, degrade if stale (D2).** If the changed surfaces require authentication, reuse the project's saved browser session/auth state (the wrapper supplies the path and freshness window). A missing or stale session degrades to a finding and the tester exercises only the reachable (unauthenticated) surface — it **never blocks** on an interactive login prompt.
6. **Drive the changed surfaces.** For each changed surface, in priority order from the guidance:
   - RUN the project's existing e2e spec(s) mapped to that surface **in the foreground, so the run blocks until the spec process exits**, redirecting any spec-runner output to the out-of-tree state dir (never the repo tree). Do NOT launch the spec as a background/detached job and then end your turn while it is still running: a backgrounded command does not block the agent loop, so ending the turn on a "waiting for the spec to finish" note silently skips steps 7-9 (collect findings, tear down servers, write findings), leaving NO findings artifact and the servers still bound. If a spec genuinely must be backgrounded, you MUST poll it to completion before proceeding; steps 8 (teardown) and 9 (write findings) are mandatory terminal steps you execute explicitly, not a trap that fires on its own;
   - do exploratory browser checks of net-new functionality not yet covered by a committed spec;
   - watch for console errors, failed network requests, and broken interactions.
   Each surface produces one or more per-check records (see **Findings contract**). A missing spec for a changed surface is itself a finding (coverage gap), recorded as `needs-change`, not silently skipped.
6a. **Broaden beyond the dev's named guidance: blast-radius / adjacent-surface probing.** After running the dev's named surfaces, treat `tester-guidance.md` as a **FLOOR, not a ceiling**. Derive and exercise your OWN additional test cases from the actual change before collecting findings:
   - **Read the diff for blast radius.** Enumerate what ELSE consumes each touched component, shared context/state, CSS variable, endpoint, or data-fetch path. The diff source is mode-dependent: in in-chain mode, use `git show HEAD` hunks (the dev cycle committed exactly one commit before the tester runs, so HEAD is the full change); in standalone mode (`--phase` / `--todos`), use `git log -p -- <file>` for each resolved surface file — `git show HEAD` shows only the most recent commit and silently misses components changed by earlier phase items, while per-file log history covers the full phase. In both modes, the dev's guidance may have omitted side-channel dependents. Ask: "what other page/component/feature reads the same state or calls the same endpoint I just changed?"
   - **Exercise adjacent + integrated surfaces, prioritized by risk.** Examples: a change to a shared or virtualized list → also test scroll/virtualization behavior, select-all across every data partition, and every other consumer of that list; a change to a shared loading/context state → also test every page that reads it (including aggregate views and pages the dev did not name); a styling or legend change → verify the legend swatch matches the actually-rendered element in the browser; a data-fetch / lazy-load change → also test the empty, aggregate ("All"), and switch-back paths.
   - **Probe "All / none / many" cardinalities explicitly.** Single-item happy paths routinely hide failures in aggregate views, zero-row states, and large data sets. Always exercise the all-items/all-regions/all-clients aggregate, the zero-rows case, and a multi-item set alongside the single-item case the dev named.
   - **Count virtualized/windowed lists by their TRUE total, never the rendered DOM.** With windowed rendering, the row elements present in the DOM are only the visible window plus overscan, never the real total. To assert "all N rows are present" or "column X is populated for every row," read the list's own absolute row index (e.g. the max value of the rows' index attribute, plus 1) while scrolling to the end, and spot-check cells across the scroll range. Counting rendered `<tr>`s produces false "rows missing"/"rows present" conclusions in both directions.
   - **Reach state through the app's REAL widgets, and let the framework commit between dependent interactions.** A custom dropdown/select component and its hidden native fallback (or a URL query param) are DIFFERENT code paths: drive the one a user actually clicks, or the bug will not reproduce. And when one interaction's state feeds the next (pick an option, then click the submit/generate button), perform them as separate steps with a short settle in between: selecting and submitting in the same synchronous tick can send the PRE-change value, producing a false result that looks like the feature ignored the setting.
   - **Record self-derived cases AND uncovered gaps.** For each self-derived adjacent case you run, add a per-check record to the findings (same `{area, change_ref, status, evidence, recommendation}` schema as step 6). For any high-risk adjacent surface you identified but could NOT cover this run (server unreachable, auth stale, budget exhausted), record it explicitly as `needs-change` with a one-line note naming the gap — the reviewer needs visibility into uncovered gaps even when you could not exercise them.
   - **Stay within the session budget: coverage-thinking, not unbounded testing.** Rank adjacent surfaces by risk and exercise the highest-risk ones first. Stop at the soft budget (per **Operating principles**): do not defer teardown to squeeze in one more surface. A partial-but-clean run beats being chopped mid-surface. Broadening is a PRIORITIZED extension of the existing budget, not a license to multiply sessions or skip teardown.
6b. **Flag test-design anti-patterns (RED-FLAGS).** After exercising the surfaces (steps 6 and 6a), assess the automated tests the dev wrote for the change. Flag any of the following four anti-patterns as a `needs-change` finding — each pattern guarantees the test suite can pass while the real bug is present:

   **(a) Synthetic-data masking.** A unit test that pre-populates (injects) the exact data the change is meant to FETCH or merge, bypassing the fetch seam entirely. The test passes because it feeds the component what it would normally fetch — the fetch bug is invisible. Flag it and demand a test that drives the real fetch path, or at least asserts the fetch/merge is invoked with the correct arguments, not one that pre-populates the result the fetch is supposed to produce.

   **(b) jsdom-can't-test-layout.** A layout, virtualization, map rendering, or color/style behavior assertion made only in jsdom (Jest). jsdom does not perform actual layout, measure element sizes, or render to pixels — so any test relying on scroll position, virtual row presence, element measurements, color, or CSS-rendered appearance is structurally incapable of catching the real bug. **A green Jest test DOES NOT count as coverage for layout/virtualization/map/color behavior.** Flag it and require a real-browser (Playwright) check against the running app for that behavior.

   **(c) Cardinality gaps.** Tests that exercise only the single-item happy path and never test All/none/many variants: the all-items/all-clients aggregate, the zero-row empty state, and a multi-item or large set alongside the single case the dev named. Single-item happy paths routinely hide failures in aggregate views, empty states, and large data sets. Flag any test whose coverage leaves these cardinalities unexercised.

   **(d) Request-not-result.** A test that asserts the REQUEST/intent (e.g. the correct POST body was sent, the right endpoint was called, the right function was invoked with the right arguments) but NOT the downstream RESULT — the actual content of the generated artifact, rendered report, or returned data structure. Flag it and require a test that also asserts the result's content, not just that the right request was made.

   Record each flagged anti-pattern as a `needs-change` check in the findings (same `{area, change_ref, status, evidence, recommendation}` schema), naming the specific test file/function and the anti-pattern it represents. A flagged anti-pattern is `needs-change`, never `fail` — the suite may be green, but its DESIGN guarantees it cannot fail on the real bug class it is meant to catch.

6c. **Inspect rendered OUTPUT artifacts, not just that they were produced.** When a changed surface emits a file or rendered artifact (a generated document/PDF, an export, a server-produced image or map), "it downloaded" and "the numbers inside are right" are NOT sufficient: layout defects live only in the rendered pixels and are invisible to both a download assertion and a content/text extraction. For each such artifact:
   - **Capture and rasterize it.** Trigger the generation through the real UI, capture the download to the out-of-tree state dir, unpack if needed, render the visual page(s) to an image (e.g. rasterize the PDF page), and actually LOOK at the image.
   - **Assert the layout, not just the content.** Positioned elements must land where their setting says (a "position: bottom-right" option must move the element there); titles, legends, labels, logos, and decorations must not overlap, clip, or wrap into each other; text must not spill outside its frame.
   - **Sweep the settings that change the artifact's LAYOUT, not just the default.** Position/corner/orientation/size options interact, and these defects are usually position-specific: a top-corner pass misses a bottom-corner bug and vice-versa. Render at least every position choice of any placement option the change touches.
   - **Verify render-sensitive layout on the deploy target, not only locally.** Output produced by server-side or native rendering (fonts, native graphics libraries, headless-vs-desktop differences) can lay out DIFFERENTLY on the deployment environment than on the local stack; e.g. a title that fits on one line locally can wrap on the server and collide with an adjacent element. When a layout defect would be font- or measurement-sensitive, confirm the artifact on the environment that actually ships it (the wrapper names the reachable deployed/staging origin, if any); a local-only pass is recorded as partial coverage, not proof.

6d. **Idle render-loop probe on heavy surfaces.** A runaway re-render loop shows no visible error, logs no framework warning, and still "works" at small scale, but it pins the CPU at rest and, once the data set is large enough that one loop iteration exceeds the browser's hang threshold, kills the tab outright. After a heavy or newly-changed view has finished loading and settled, profile a few seconds of NO interaction (e.g. a CDP `Profiler` sample, or repeated frame-gap timing): the main thread must be predominantly idle. A surface that is continuously busy at rest (cells re-rendering, layout being re-measured in a cycle) is a render loop: record it as a finding (with the profile evidence) even when every functional check on that surface passed. This is cheap, needs no user interaction, and catches the freeze class that only manifests for users with larger data than the test fixture.

7. **Collect findings + compute the verdict.** Aggregate all per-check records (the dev's named surfaces from step 6, the self-derived adjacent-surface cases from step 6a, the anti-pattern flags from step 6b, the rendered-artifact inspections from step 6c, AND the idle render-loop probes from step 6d) into the overall verdict (see **Findings contract** for the green/red/degraded/skipped rule) and a one-line summary.
8. **Tear down.** See **Teardown** — stop both servers and close the browser (unless the wrapper opts into browser reuse); assert the documented ports are free and no orphan server processes remain.
9. **Write findings + exit.** Write `tester-findings.md` and `tester-findings.json` to the run-log dir, then exit. The reviewer reads them on its next turn.

### Headed vs headless (D2)

Run **headed** when a display is available (e.g. a live `DISPLAY` session), so a human watching the run sees the real interaction; fall back to **headless** when no display exists (CI, a detached cron run, an overnight drain). The headed/headless choice never changes which surfaces are exercised — only whether a window is shown. Headless is the safe default when detection is ambiguous.

### Browser hang / unresponsive page (guaranteed recovery)

A driven surface can hang or crash the BROWSER itself, not just fail a check. An infinite render/update loop, an unbounded synchronous computation, or a memory blowup pegs the page's main thread so it stops responding, and a severe case crashes/closes the renderer outright. This is the failure that most easily takes the tester down WITH the page: a browser action that never returns, or a retry loop against a frozen surface, hangs the whole run. Handle it so the hang becomes the run's headline finding, never a hung tester:

- **Bound every browser interaction.** Every navigate, click, fill, evaluate, snapshot, and wait carries an EXPLICIT short per-action timeout (a few seconds, not the tool's minutes-long default). Never issue an unbounded browser action. The default timeout is the single most common reason a tester hangs on a frozen page.
- **A timed-out or unresponsive interaction is a bounded FINDING, not a retry.** Treat any of these as a stop condition: a browser action exceeds its timeout mid-action; a liveness probe (a trivial `evaluate`, or timing two consecutive `requestAnimationFrame` callbacks) does not return within a second or two; or the tool reports the target / context / page was closed or the debugger/CDP disconnected (a renderer crash). When it happens, STOP driving that surface. Do NOT re-issue the same action, and do NOT reload-and-retry the same flow: a surface that hangs will hang again, and that retry is exactly how the tester itself hangs.
- **Reproduce with a REAL click, and distinguish a true freeze from a merely BUSY page.** A click/action that times out is NOT automatically an app freeze: the common benign cause is ACTIONABILITY (the tool waited for the element to stabilize and it never did because the page was re-rendering, e.g. a large data set streaming in or a virtualized list settling), not a blocked main thread. CRITICAL: never confirm or clear a suspected freeze with a synthetic/programmatic click. An injected `element.click()` fires only an untrusted `click` event and SKIPS the real pointer + focus path, so a freeze that path triggers (a real click that moves focus into a modal whose open traverses a huge DOM, a trusted-event handler, etc.) will NOT reproduce under a synthetic click and will FALSELY read as responsive (this exact trap turned a real, reproducible freeze into a "cannot reproduce"). To decide: (1) reproduce with a REAL click (the tool's actual click, e.g. `browser_click` / `page.click`, bounded by a short timeout); (2) SEPARATELY and right after, probe main-thread liveness with a trivial `evaluate` (or a frame-gap / longtask measure) that must return within ~2-3s. If the real click times out AND the liveness probe does not return (or shows a multi-second frame gap / longtask) then it is a true freeze: `fail` "<surface> freezes the browser on <action>". If the real click times out but the liveness probe returns promptly (~30-120ms) then it is an actionability / busy page: `needs-change` "<surface> not interactable within Ns (continuous re-render / slow load)". Never assert "renderer crashed / OOM" when the renderer is alive but busy. Include the minimal repro (the exact REAL interaction + data scale) and, when captured, the last console output and whether a framework render-loop warning was logged.
- **Recover the browser, then continue or exit cleanly.** After a hang the current page/context is poisoned. Discard it: close the page/context; if the graceful close ALSO hangs, force-kill the browser process and clear any leftover user-data-dir / singleton profile lock so a fresh browser can launch. Then either open a fresh context for the REMAINING surfaces, or, if the browser cannot be recovered, go straight to teardown. Under NO circumstance does one hung surface stall the run: it MUST still reach teardown and write findings, with the hang recorded and the other surfaces reported.
- **Per-surface watchdog.** Give each surface a bounded wall-clock budget for its interactions; if it elapses with the surface still not settling, treat it as a hang finding and move on. This is the surface-level analog of the run-level soft budget.
- **The hang is the highest-value finding of the run.** A surface that freezes or crashes a real user's browser is a `fail` (a review blocker), so capture it precisely even though the rest of that surface's checks could not complete. A partial findings record naming the hang beats a run that never returns.

### Teardown (guaranteed)

All server-starting and browser-driving steps run inside a `finally`/trap path so teardown ALWAYS fires — on success, on a thrown exception, on a readiness timeout, on a browser hang, or on Ctrl-C. Teardown:

- gracefully stops the back-end and front-end servers (never `kill -9` a server that has a graceful stop);
- closes the browser context — UNLESS the wrapper defines a browser-reuse policy (one long-lived browser kept open across runs, so iterative or local-headed runs reattach to it instead of cold-launching each time). When the wrapper opts in, the browser is deliberately LEFT OPEN; only the servers are torn down. Server teardown is never optional. EXCEPTION: a browser that hung or crashed (per **Browser hang / unresponsive page**) is force-killed and its profile lock cleared even under a reuse policy — a poisoned browser is discarded, not reattached to;
- confirms the documented ports have no remaining listener and no orphan server processes survive (a wrapper's deliberately-kept-open reuse browser is expected, NOT an orphan — do not kill it; a hung browser that was force-killed for recovery is likewise expected, not a teardown failure).

A run that cannot guarantee a clean teardown records that as a `degraded` finding so the reviewer knows the environment may be dirty.

### Artifacts — out of tree (D3)

- **Zero files under any repo working tree.** After a run, `git status --porcelain` must be empty (modulo files the dev cycle already committed). The tester writes nothing the repo would track.
- **Binary artifacts** (screenshots, traces, video, server logs) go to a non-repo state dir: `~/.claude/state/sst-tester/<utc>/`. The findings records reference these by path; they are never copied into the repo.
- **Write each artifact directly to the out-of-tree dir; never rely on a post-hoc move.** When a tool accepts an output-path argument (for example the browser screenshot tool's `filename`), pass the ABSOLUTE out-of-tree path, not a bare filename. A bare filename is resolved relative to the process working directory (the repo root), so it deposits a binary artifact inside the tree and forces a detect-and-move that leaves the tree dirty if anything fails between the write and the move. Passing the absolute path keeps the leave-no-trace invariant true by construction rather than by recovery.
- **The reviewer-facing findings doc** (`tester-findings.{md,json}`) goes to the chain run-log dir (`<project>/.skill-runs/<run>/`), which is already gitignored, so it is visible to the reviewer without ever entering version control.

## Standalone mode (`--phase <id>` / `--todos <ref...>`)

Invoked from the terminal to sweep all UI/UX a phase or a set of completed todos introduced. The in-chain mode above is unchanged; this section adds only the standalone path. Standalone stays **read-only on the tree, out-of-tree for all artifacts, and full-teardown**, identical guarantees to in-chain.

### Arg surface + dispatch (D1)

- `--phase <id>`: resolve every closed UI surface under `### Phase <id>` of `docs/SPEC.md`.
- `--todos <ref...>`: resolve the UI surfaces of one or more named `## Just shipped` entries in `docs/TODO.md`.
- Either flag (or both together) selects standalone mode; the two are additive (pass both to union their resolved surface sets). With neither flag: if `tester-guidance.md` is absent AND a `## Tester sweep targets` queue exists in `docs/TODO.md`, the skill runs in looped-standalone drain mode; otherwise it runs in-chain (default).

### Scope resolution (D2)

A closed item resolves to a **UI surface** when any file path it cites is a front-end path. The default front-end predicate (a wrapper may extend it for project-specific dirs) is: a path whose extension is one of `.tsx .jsx .ts .js .vue .svelte .html .css .scss`, or a path under a front-end directory the wrapper names. Items that cite only back-end paths (e.g. `.py` handlers, `.sql` migrations), docs (`.md`), or config resolve to **no** surface and are excluded from the sweep.

- **`--phase <id>`**: under `### Phase <id>`, collect every `- [x]` item (closed only; open `- [ ]` items are NOT swept, since they were never shipped). For each closed item, extract its cited paths and keep the front-end ones; map each surface to its route/component and to the project's mapped e2e spec(s) via the wrapper's phase->spec map. The resolved set is the union over all closed front-end items in that phase.
  - *Example.* `--phase 7` over a phase whose `[x]` items cite `web/src/routes/checkout.tsx`, `web/src/components/LeadForm.jsx` (both front-end), `api/webhooks/stripe.py` (back-end), and `docs/STOREFRONT.md` (docs) resolves to `{checkout.tsx, CartSummary.tsx, LeadForm.jsx}` and excludes the back-end and docs items; a still-open `- [ ]` inventory-dashboard item in the same phase is excluded because it was never shipped.
- **`--todos <ref...>`**: for each ref, match a `## Just shipped` entry by its leading SPEC-id token (e.g. `7.2`) OR a case-insensitive substring of the entry text (e.g. `settings`); apply the same front-end predicate to the matched entry's cited paths. A ref that matches no entry, or matches an entry with no front-end path, contributes nothing.
  - *Example.* `--todos 7.2 settings` matches the `7.2 ... web/src/components/LeadForm.jsx` entry by id and the `6.9 settings page web/src/routes/settings.tsx` entry by substring, resolving to `{LeadForm.jsx, settings.tsx}`. A `--todos 7.3` naming a back-end-only entry resolves to nothing.

If the union of resolved surfaces is empty (no closed front-end items in scope), standalone self-skips exactly like the in-chain path: write a `verdict: skipped` findings record with the reason and exit 0.

### Iterate-all, collect-all (D3)

Unlike the in-chain single-diff pass (which prioritizes the dev's guidance and one cycle's surfaces), standalone exercises **every** resolved surface and **does not stop at the first failure**. It runs the mapped e2e spec(s) plus exploratory checks for each surface, accumulating one or more per-check records per surface, then computes the overall verdict from the full set (green/red/degraded/skipped per the **Findings contract** rule). A broken surface becomes a `fail` check and the sweep continues to the remaining surfaces.

The lifecycle is otherwise the in-chain lifecycle: start the local stack, poll readiness with a timeout, establish/degrade the session, drive each surface, then guaranteed teardown. A surface that can't be reached degrades to a finding and the sweep moves on.

### Standalone output location (D4)

Standalone has no chain run-log dir. It writes both `tester-findings.md` and `tester-findings.json` (the same contract as in-chain) to the out-of-tree state dir `~/.claude/state/sst-tester/<utc>/`, alongside the binary artifacts, and prints a one-line terminal summary (the overall verdict + summary) plus that artifact path. Standalone **does not** file SPEC follow-ups or edit any handoff doc; it tests and reports, and a human or a later review consumes the findings.

## Looped standalone drain

Drain a `## Tester sweep targets` queue one target per iteration using the unified runner:

```bash
bin/skill-chain.py <tester-skill> --loop N
```

The queue in `docs/TODO.md` is the scope; pass the loop count and no other scope args. The runner loops up to N times; the tester exits early on `[no-test-work]` when the queue is exhausted, so the actual iteration count is `min(N, queue_length)`.

### Queue format (`## Tester sweep targets` in `docs/TODO.md`)

Each entry is a bullet line under the `## Tester sweep targets` section:

```
## Tester sweep targets
- [P1] <surface description> [covered|partial|GAP]
- [P2] <surface description> GAP
- [P3] <surface description> partial
```

Priority tags: `P1` = high-impact / blocking; `P2` = normal; `P3` = low / polish. Coverage tags: `covered` = exercised green; `partial` = exercised with gaps; `GAP` = not yet exercised.

### Draining selector

Per iteration the tester:

1. Reads `## Tester sweep targets` from `docs/TODO.md`. If the section is absent or empty, skips to the `[no-test-work]` bail.
2. Loads the out-of-tree exercised-state file `~/.claude/state/sst-tester/<project-slug>/queue-<run-utc>.json`. The `<run-utc>` is stamped once at the start of the loop run; all iterations within the same `--loop N` invocation share the same file so the state accumulates across iterations.
3. Returns the first item whose key (the item text stripped of the leading `- `) is NOT present in the already-exercised set.
4. If no such item exists (all entries are recorded), returns `None` and the tester emits `[no-test-work]`.

### `[no-test-work]` bail

When the draining selector returns `None` (queue drained, or the section is absent / has no front-end targets), the tester:

- Prints exactly one line on stdout: `[no-test-work] <reason>` (e.g. `[no-test-work] queue drained; 3/3 targets exercised this run`)
- Exits 0 WITHOUT starting the browser or the local stack

The chain runner recognizes the `[no-test-work]` sentinel, records `terminated_by: "no_test_work_bail"` in the loop manifest, and breaks the outer loop so the run self-terminates cleanly. This is the tester analog of the dev cycle's `[no-work]` sentinel.

### Exercised-state file

The exercised-state file is written and updated by the tester out-of-tree at `~/.claude/state/sst-tester/<project-slug>/queue-<run-utc>.json`. It is a JSON object mapping exercised item keys to their run timestamp. The file is NEVER written under the repo working tree; after any looped drain `git status --porcelain` must be empty.

The `<project-slug>` is derived from the project's root directory name (the basename of `cwd`). The `<run-utc>` is fixed for the lifetime of one `--loop N` invocation so all iterations share a single state file.

### Per-target flush and session budget

**Write each target's findings immediately, not only at run end.** As soon as a target is verdicted, write its record to the exercised-state file (`queue-<run-utc>.json`) AND flush any per-target findings output. Writing incrementally means a context compaction or a turn chop can never lose an in-flight verdict: the cursor always reflects which targets have been exercised so far.

**Do not drain a multi-target range past the soft budget in one session.** As you approach the soft turn budget, stop before opening a new target: finish the current target cleanly, run teardown, and exit. The next invocation resumes from the queue cursor (already-exercised targets are recorded in the exercised-state file). Opening a fresh target when only a few turns remain risks a mid-exercise chop that leaves the servers still bound.

**The canonical drain is runner-looped.** `bin/skill-chain.py <tester-skill> --loop N` is the canonical approach: it spawns a fresh, separately-budgeted subprocess per target so each invocation starts with a full turn budget. Manual invocations (direct `/sst-tester` or Skill-tool calls) should also exercise one target per invocation — prefer the runner-looped form over packing many targets into one session.

### Authority and guarantees

Looped-standalone mode inherits all guarantees of in-chain and standalone modes unchanged:

- Read-only on the tree; never commits, deploys, or edits repo source.
- All artifacts (screenshots, traces, findings) go out-of-tree.
- Guaranteed teardown fires even on exception or timeout.
- `git status --porcelain` is empty after every iteration.

## Findings contract (tester → reviewer)

The tester writes two files to the run-log dir on every run that is not a dev pre-empt:

- **`tester-findings.md`** — reviewer-facing. A short human-readable summary: the overall verdict, the one-line summary, and a table/list of per-check records with their evidence paths and recommendations.
- **`tester-findings.json`** — machine-readable. The reviewer parses this to escalate findings into its own review.

### `tester-findings.json` schema

```json
{
  "verdict": "green | red | degraded | skipped",
  "summary": "one-line human summary of the run",
  "checks": [
    {
      "area": "the surface/route/component exercised",
      "change_ref": "the changed file or SPEC id this check covers",
      "status": "pass | fail | needs-change",
      "evidence": "out-of-tree artifact path (e.g. ~/.claude/state/sst-tester/<utc>/checkout.png)",
      "recommendation": "what the reviewer/next cycle should do, or empty on pass"
    }
  ]
}
```

Field rules:

- **`verdict`** — one of:
  - `green` — every check passed; the changed surfaces work at runtime.
  - `red` — at least one check is `fail` (a changed surface is broken at runtime).
  - `degraded` — the tester could not fully exercise the intended surface (server didn't come up, stale auth session, partial reachability); the reviewer should treat coverage as incomplete, not as "passed."
  - `skipped` — self-skip no-op (no local-run path, or no front-end surface in the change set); a valid non-finding state, distinct from `degraded`. A `skipped` record carries an empty or single explanatory `checks` entry and the reason in `summary`.
- **`summary`** — a single line; the reviewer surfaces it verbatim in its `Tester:` report line.
- **`checks[].status`** — one of:
  - `pass` — the surface behaved correctly.
  - `fail` — the surface is broken (console error, failed assertion, broken interaction), **or it completes mechanically but produces materially wrong output** — a page, export, or rendered artifact whose content misstates the underlying data (a zero-row period rendered as a populated all-zeros table, a stale or wrong total, a document stamped with a status its contents contradict); becomes a review `[blocker]`. "It rendered without an error" is NOT the bar: judge the OUTPUT against what the data says it should be, and weigh where that output GOES — an artifact that leaves the app for a third party (an emailed report, an invoice, a statement an auditor or lender reads) is `fail` when it is wrong, never a `needs-change` polish item. A correct-but-improvable surface is the only `needs-change`.
  - `needs-change` — the surface works AND its output is correct, but something should still change (a missing committed spec for a changed surface, a UX rough edge, a coverage gap); becomes (or strengthens) a review `[should-fix]`.

  The enum above is CLOSED, and the array key is `checks`, never `findings`. Do not invent per-check statuses: `skipped`, `partial`, `info`, `not-exercisable`, and `known-preexisting` have all been observed in real runs, and every off-enum status (or a renamed array key) silently drops its record from the reviewer's escalation path, because the reviewer machine-parses `checks[]` and acts only on `fail` / `needs-change`. Map the tempting cases back into the enum: a mapped spec you could NOT run this session (an environment or data restriction, a missing fixture, stale auth) is `needs-change` with the can't-run reason and the unlock named in `recommendation` (step 6a's uncovered-gaps rule: the reviewer needs visibility precisely because you could not exercise it); a known, already-filed issue reproduced in passing is a `pass` whose `recommendation` cites the existing backlog item ("already filed as <id>; do not re-file"); a pure FYI belongs in `summary`. Only the top-level `verdict` may be `skipped`; a per-check `skipped` is not a legal value.
- **`checks[].evidence`** — a path under the out-of-tree state dir, never a repo path. Empty is allowed only for a `pass` with nothing worth capturing.
- **`checks[].change_ref`** — ties the check back to a changed file or the SPEC id the dev cycle flipped, so the reviewer can correlate runtime behavior with the diff.

The reviewer's contract for consuming these files (read on its open, escalate `fail`→`blocker` / `needs-change`→`should-fix`, surface `degraded`, treat `skipped` as a non-finding, and proceed unchanged when the files are absent) lives in the review skill, not here.

## When invoked with no run-log dir argument

Default to the most recent `.skill-runs/<*>/` directory under the current working directory. If none exists, there is no dev cycle to test against — exit 0 with a one-line `verdict: skipped` reason and write nothing further.
