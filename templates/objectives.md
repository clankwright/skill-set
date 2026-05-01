# <project-name> — outcome objectives

The bar the manager scores progress against. Higher-level than SPEC phases — these are the project's reasons to exist, not its in-flight todo list. Manager flips `[ ]` → `[x]` ONLY when a measurable check passes; never rewrites the prose. SPEC phases close one-by-one in the dev cycle, but these are evaluated holistically once per manager tick.

Each objective is a bullet plus a 3-line continuation block:

```
- [ ] <slug>: <one-line description>
      check: <shell expr OR count(<glob>) <op> <value>>
      target: <value-or-bound, e.g. "== 0", "<= 0.50", ">= 30">
      since: <utc-iso when this criterion was added>
```

The `check:` line runs via the manager's `--plan` mode (a follow-up extension of `sst-manager`, invoked as `--plan`). Two forms:
- **shell check** — anything else; the manager runs the expression in `/bin/bash -c` from this project's root and compares stdout (numeric) OR exit code to `target:`.
- **metric check** — starts with `count(<glob>)`; the manager expands the glob from this project's root and counts matches, then compares to `target:`.

`<slug>` is a kebab-case identifier the planner uses to reference the criterion in `Next up` rationale lines. Slugs are unique within this file and never renumbered. The `since:` field starts the gap timer the planner uses to prioritize: an open criterion open for 90 days outranks one opened yesterday when picking the 1–3 highest-gap items to draft.

Prose-only bullets without a `check:` block are still legal — the planner treats them as untracked goals (visible but unscored). Use the prose form for objectives whose completion criterion is qualitative (cannot be reduced to a one-line shell or metric expression) and where you'd rather track progress by hand than write a flaky check.

## <Primary outcome heading — what success looks like for this project>

Replace this paragraph with one paragraph naming the project's reason to exist and how the listed criteria together define "done."

- [ ] <slug-1>: <one-line measurable outcome>
      check: <shell-or-metric-expr>
      target: <bound>
      since: <utc-iso>
- [ ] <slug-2>: <one-line measurable outcome>
      check: <shell-or-metric-expr>
      target: <bound>
      since: <utc-iso>

## <Supporting outcomes (optional sub-section)>

Use a second heading for outcomes that support the primary goal but aren't themselves the project's reason to exist (quality, recoverability, observability, etc.). Mix scored and prose-only items as appropriate.

- [ ] <slug-3>: <description>
      check: <expr>
      target: <bound>
      since: <utc-iso>
- [ ] <prose-only objective the planner cannot easily score; remains visible but unscored>

## Anti-objectives (the manager should NOT push toward these)

List things the manager should explicitly NOT escalate or plan toward. Without this section, planner-mode tends to drift into chasing easy-but-wrong metrics (e.g. raw line counts, file counts, surface area). One bullet per anti-objective; no `check:` block (these are hard rules, not measurable criteria).

- **<Anti-objective 1>**: <one-paragraph rationale for why this is NOT a goal>
- **<Anti-objective 2>**: <one-paragraph rationale>

<!--
Example anti-objectives a typical project might list:
  - **Skill count / file count.** The library is whatever the spec needs; counting is not a goal.
  - **Streak counters.** "N clean cycles in a row" is a statistic, not an outcome.
  - **Adoption metrics.** Stars, downloads, external contributors — out of scope until v1.0.
-->
