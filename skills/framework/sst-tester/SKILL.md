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
version: 1.6.1
model-floor: sonnet
effort-floor: high
---

# Interactive UI/UX Tester

One invocation = one runtime pass over the front-end surfaces a dev cycle just changed. This skill sits **after the dev skill and before the review skill** in a dev chain: the dev cycle ships a commit, the tester spins up the running app and drives the changed surfaces in a browser, and the reviewer then reads the tester's findings alongside the diff instead of judging UI work from the diff alone.

This is the project-agnostic transferable. It owns the **contract** — chain position, authority envelope, run lifecycle, degrade/self-skip discipline, headed/headless policy, the out-of-tree artifact rule, and the findings format. A proprietary wrapper (e.g. an `ssp-*-tester`) supplies the concrete facts this skill deliberately does not hardcode: the exact ports, the start/stop commands, the saved-auth-state path, and the mapping from changed surfaces to the project's e2e specs. Nothing in this file names a port, a path, or a project.

## Operating principles

- **Observe, never mutate the tree.** The tester is read-only on the repo. It starts and stops local servers, drives a browser, and writes findings — it never commits, never deploys, never edits repo source, and never pushes. (See **Authority envelope** below.)
- **Degrade, don't hang.** Every external dependency (a server that won't come up, a stale login session, a surface that 404s) becomes a *finding*, not a blocked run. The tester never blocks on an interactive prompt and never waits without a timeout. A run that can reach only half the surfaces reports on that half and records the rest as degraded.
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
7. **Collect findings + compute the verdict.** Aggregate the per-check records into the overall verdict (see **Findings contract** for the green/red/degraded/skipped rule) and a one-line summary.
8. **Tear down.** See **Teardown** — stop both servers and close the browser (unless the wrapper opts into browser reuse); assert the documented ports are free and no orphan server processes remain.
9. **Write findings + exit.** Write `tester-findings.md` and `tester-findings.json` to the run-log dir, then exit. The reviewer reads them on its next turn.

### Headed vs headless (D2)

Run **headed** when a display is available (e.g. a live `DISPLAY` session), so a human watching the run sees the real interaction; fall back to **headless** when no display exists (CI, a detached cron run, an overnight drain). The headed/headless choice never changes which surfaces are exercised — only whether a window is shown. Headless is the safe default when detection is ambiguous.

### Teardown (guaranteed)

All server-starting and browser-driving steps run inside a `finally`/trap path so teardown ALWAYS fires — on success, on a thrown exception, on a readiness timeout, or on Ctrl-C. Teardown:

- gracefully stops the back-end and front-end servers (never `kill -9` a server that has a graceful stop);
- closes the browser context — UNLESS the wrapper defines a browser-reuse policy (one long-lived browser kept open across runs, so iterative or local-headed runs reattach to it instead of cold-launching each time). When the wrapper opts in, the browser is deliberately LEFT OPEN; only the servers are torn down. Server teardown is never optional;
- confirms the documented ports have no remaining listener and no orphan server processes survive (a wrapper's deliberately-kept-open reuse browser is expected, NOT an orphan — do not kill it).

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
  - `fail` — the surface is broken (console error, failed assertion, broken interaction); becomes a review `[blocker]`.
  - `needs-change` — the surface works but something should change (a missing committed spec for a changed surface, a UX rough edge, a coverage gap); becomes (or strengthens) a review `[should-fix]`.
- **`checks[].evidence`** — a path under the out-of-tree state dir, never a repo path. Empty is allowed only for a `pass` with nothing worth capturing.
- **`checks[].change_ref`** — ties the check back to a changed file or the SPEC id the dev cycle flipped, so the reviewer can correlate runtime behavior with the diff.

The reviewer's contract for consuming these files (read on its open, escalate `fail`→`blocker` / `needs-change`→`should-fix`, surface `degraded`, treat `skipped` as a non-finding, and proceed unchanged when the files are absent) lives in the review skill, not here.

## When invoked with no run-log dir argument

Default to the most recent `.skill-runs/<*>/` directory under the current working directory. If none exists, there is no dev cycle to test against — exit 0 with a one-line `verdict: skipped` reason and write nothing further.
