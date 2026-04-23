---
name: agent-orchestrator
description: |
  Per-task orchestrator that picks which sub-skills to invoke for a complex multi-step request, sequences them, passes outputs between them, and synthesizes a final result. Discovers available skills via the harness's skill registry; chooses by description, not by hardcoded names. Always ends with an editorial pass on the synthesized output. Distinct from the framework's manager skill (which is the periodic ops-loop with Telegram digests); this one runs INSIDE a single user request.
user-invocable: true
version: 1.0.0
argument-hint: [high-level task or objective]
---

# Agent orchestrator

Given a complex task, this skill plans the sub-tasks, picks skills to handle each, runs them in sequence, and synthesizes the results. The user calls this once; the skill drives everything to completion.

## Project contract

- **Output dir**: `<project>/data/agent-orchestrator/` for the synthesized final result. Files as `<utc>_<task-slug>.md`.
- **Required skills**: discovered dynamically from the harness's skill registry. The orchestrator picks based on each skill's `description` field. The chain ALWAYS ends with `editorial-pass` (or the project's proprietary editorial counterpart) for the final synthesis pass.
- **Tools required**: harness's `Skill` tool (to invoke sub-skills); `Read` (to load intermediate outputs); `Write` (to save the final synthesis).

## Operating principles

- **Plan before invoking.** Before calling any sub-skill, write a plan: what's the task, what sub-tasks does it decompose into, which skill handles each, in what order, with what inputs/outputs. The plan is your contract with yourself; deviations from it require a re-plan, not a quiet ad-hoc detour.
- **Pick by description, not by name.** Don't hardcode skill names. Walk the harness's available skills, read each description, choose by fit. This keeps the orchestrator portable across projects with different proprietary skill sets.
- **Pass concrete inputs.** When you call a sub-skill, give it the actual data it needs (text, file paths, structured inputs), not "the previous result." Keep the contract explicit.
- **Always close with editorial-pass.** The final user-facing output goes through `editorial-pass` (or its proprietary counterpart). No exceptions — even short answers benefit from the scope/clarity check.
- **Iterate when results are weak.** If a sub-skill returned a thin or off-target result, revise your instructions and re-invoke. Don't accept "close enough" on the first pass and let it propagate downstream.

## Process

### 1. Read the task

Restate the task in your own words. Identify:

- **Top-level deliverable** (a research report, an edited draft, a published post, a ranked shortlist, ...).
- **Implicit sub-deliverables** (does the report require new research, or does it work from existing inputs? does the post need fact-checking? does the shortlist need new candidates first?).
- **Constraints** (length target, audience, tone, must-include / must-not-include, deadlines).

If anything is genuinely ambiguous and would produce wildly different plans, ask once before planning.

### 2. Plan the chain

Write a plan in this shape (in your scratchpad; save to `<project>/data/agent-orchestrator/<utc>_<slug>.plan.md`):

```markdown
# Plan — <task slug>

**Task**: <restated>
**Final deliverable**: <what the user gets>

## Sub-tasks
1. <sub-task> — skill: `<skill-name>` — input: <description> — expected output: <description>
2. <sub-task> — skill: `<skill-name>` — input: <output of step 1, transformed how?> — expected output: <description>
3. ...
N. Synthesis + editorial-pass — input: <all prior outputs> — expected output: <final deliverable>
```

### 3. Discover available skills

Read the harness's skill registry (the list it surfaces to you on every invocation). Match each sub-task to the best-fit skill by description. Prefer:

- **Proprietary counterparts** when present in the project's `.claude/skills/` (they hold project-specific facts).
- **Transferable skills** otherwise.

If the project has both `<project>-X` and `X` available, use `<project>-X`. The proprietary's `transferable: X` frontmatter signals which transferable it inherits, but you don't need to chase that — just pick the most-specific available implementation.

### 4. Execute the chain

For each step in your plan:

1. Invoke the chosen skill with the prepared input.
2. Read the skill's output (most skills report a file path as the final line; `Read` it).
3. Verify the output meets the "expected output" you wrote in the plan. If it doesn't:
   - For minor shortfalls: revise the instructions and re-invoke the same skill (max 2 retries).
   - For fundamental shortfalls: re-plan from this step. Don't pretend the bad output is fine.
4. Pass the verified output as input to the next step.

If a step fails twice in a row, surface the failure to the user with the plan's current state. Don't loop indefinitely.

### 5. Final synthesis + editorial pass

After all sub-skills have completed:

1. Synthesize the outputs into the final deliverable's shape (report, draft, list, etc.). This is your direct work, not a sub-skill call.
2. Invoke `editorial-pass` (or the proprietary editorial counterpart) on the synthesis.
3. Save the editorial-pass result to `<project>/data/agent-orchestrator/<utc>_<slug>.md`.

### 6. Report

```
Final deliverable: <path>
Plan: <path to .plan.md>
Sub-skills run: <list with one-line outcomes>
Total sub-skill invocations: <N>
```

## Hard rules

- **Never invoke yourself recursively.** This skill is the orchestrator; it doesn't call other agent-orchestrator instances.
- **Never invoke `manager` (the ops-loop skill).** Different concept; the ops manager runs on a cron, not inside a user request.
- **Never skip the editorial-pass at the end.** Even when the synthesis feels solid, the pass catches scope drift and unverified claims.
- **Never pad the final deliverable to look thorough.** Match the user's request, not your sense of completeness.
- **If a sub-skill is missing for a sub-task, ask the user how to proceed.** Don't fake it by inlining the work — that defeats the orchestration pattern.
