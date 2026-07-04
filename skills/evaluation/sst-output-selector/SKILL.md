---
name: sst-output-selector
description: Compare N candidate outputs (drafts, designs, code variants, research reports, ...) on a stated rubric and pick the best, with cited justification. The candidates already exist on disk in the project's standard output dir; this skill does not generate them. Produces a comparison table, a clear winner, and (when no candidate is clearly best) a recommendation for combining strengths.
user-invocable: true
version: 1.0.2
model-floor: sonnet
effort-floor: medium
argument-hint: [paths to candidate files | dir containing candidates]
---

# Output selector

QA/QC: given N candidate outputs that an upstream skill produced, pick the best one objectively and explain why.

## Project contract

- **Output dir**: `<project>/data/sst-output-selector/` for the selection report; the candidates themselves are read from wherever the user / upstream skill points (often `<project>/data/<source-skill>/<utc>*.md`).
- **Tools required**: harness's `Read` (for candidate files). No web access needed; selection is purely analytical.
- **Input shape**: a list of file paths, OR a directory + glob, OR raw text blocks pasted into the input.

## Operating principles

- **Objective rubric, not preference.** Pick on measurable quality factors (accuracy, completeness, clarity, structure, citation quality, fitness for the original task). Personal taste doesn't decide.
- **Cite specifics.** "Output 2 is better" is not a justification. "Output 2 cites 8 sources to Output 1's 3, and includes the missing comparison-with-X section the original brief asked for" is.
- **Don't modify the candidates.** Your job is to compare and pick, not to rewrite. If you think the winner needs polish, flag it for the next skill in the chain (e.g. `sst-editorial-pass`).
- **Combination is a real outcome.** When no candidate is clearly best, propose a combination: "use Output 1's structure with Output 2's evidence section." Don't force a choice that doesn't fit.

## 1. Read the inputs

- The N candidate files (use `Read` for each).
- The original query / task / prompt that produced them, if available. Without it, you can still compare on intrinsic quality, but the "fitness for purpose" axis won't have weight.

## 2. Build the rubric

Default axes (override / extend if the user supplies their own):

| Axis                | What to look for |
|---------------------|------------------|
| Accuracy            | Are the facts right? Any unsupported claims? |
| Completeness        | Does it cover what the original task asked for, end to end? |
| Clarity             | Is it readable? Tight sentences, unambiguous terms? |
| Structure           | Logical flow, useful section headings, scannable? |
| Citation quality    | Sources present, authoritative, actually back the claims? |
| Fitness for purpose | Does the output match the form the original task expected (report vs. brief vs. one-liner)? |

## 3. Score each candidate per axis

Walk each axis, score each candidate qualitatively (better / worse / equivalent), and capture the one or two most concrete pieces of evidence.

```
| Axis           | Output 1                         | Output 2                         |
|----------------|----------------------------------|----------------------------------|
| Accuracy       | 1 unsupported claim (line 12)   | All claims cited                  |
| Completeness   | Missing comparison-with-X       | All sections present              |
| Clarity        | Slightly verbose; long ¶s       | Tight; section breaks help        |
| ...            | ...                              | ...                               |
```

## 4. Pick

Tally the axes. The clear winner is the one that wins (or ties) on every axis OR wins decisively on the most-weighted axes (accuracy and fitness for purpose are the heaviest by default).

If no candidate is clearly best, identify the strongest section/aspect of each and propose a combination.

## 5. Write the report

Save to `<project>/data/sst-output-selector/<utc>_<batch-slug>.md`:

```markdown
# Output Selection — <utc>

**Inputs**:
- Output 1: <path>
- Output 2: <path>
- ...

**Original task**: <one-line restatement, or "not provided">

## Comparison table

<the table from §3>

## Winner

**<Output N>** — <one paragraph explaining why, citing the specific
evidence from the comparison table>.

## (If no clear winner) Combination recommendation

- Use Output X's <component>: <reason>
- Augment with Output Y's <component>: <reason>
- Drop / rework Output Z's <component>: <reason>

## Selected output

<paste the full text of the chosen output, OR — if a combination — the
recombined draft>
```

Report the file path as the final line of your response.

## Hard rules

- **Never silently rewrite.** The "Selected output" section is either a direct paste or an explicit recombination; never a copyedit.
- **Never claim a winner without naming the deciding axes.** A choice with no cited evidence is worse than no choice.
- **Don't pick by length.** Longer is not better. Comprehensive coverage IS better, but only when the task demands it.
- **Don't add new content.** If the candidates all miss something the original task asked for, flag it as a gap — but don't fill it. Filling gaps is an upstream / next-skill concern.
