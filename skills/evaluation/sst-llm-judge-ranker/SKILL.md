---
name: sst-llm-judge-ranker
description: Maintain a ranked list of N artifacts (drafts, designs, code variants, research reports, ...) by comparing each new candidate against the current top and bottom of the list, using LLM judgment as the comparator. Supports both batch ranking (compare every artifact against every other) and incremental insertion (place a new artifact into an existing ranked list with O(log N) comparisons via binary search). Persists the ranklist as JSON; safe to call repeatedly as new candidates land.
user-invocable: true
version: 1.0.0
argument-hint: [path to candidates dir | two file paths to compare directly]
---

# LLM-judge ranker

Order N artifacts by quality on a stated dimension. The comparator is "the LLM judges A vs B against this goal," done pairwise.

## Project contract

- **Output dir**: `<project>/data/sst-llm-judge-ranker/<run-id>/` where `<run-id>` is either user-supplied or auto-generated as `<utc>_<short-uuid>`. Inside:
  - `metadata.jsonl` — append-only log of every artifact registered.
  - `ranking_state/<artifact-set>.ranklist.json` — the current ranked list (just IDs, ordered best→worst).
- **Tools required**: harness's `Read` (for candidate files). No web access; ranking is pure analysis.
- **Input shapes**:
  - **Direct compare**: two file paths + an optional goal → returns winner + rationale.
  - **Batch rank**: a directory of candidate files + a goal → produces an initial ranklist.
  - **Incremental insert**: a new candidate path + the existing ranklist file → places the new candidate at its correct position with binary-search comparisons.

## Operating principles

- **One comparator function.** Every comparison answers the same question in the same form: "Given goal G, which of A vs B better accomplishes it? Reply A | B | Equal, then a one-paragraph justification." Don't drift the rubric mid-run.
- **Goal-anchored.** Every comparison cites the same `goal`. If the goal changes between runs, the ranklist needs to be rebuilt from scratch — don't mix.
- **Cap the list.** `max_ranklist_size` (default 10) caps how many artifacts the list retains. After insertion, prune the worst.
- **Atomic writes.** Update the ranklist file via temp + rename so partial writes never corrupt it.
- **Don't re-rank what's already in the list.** Each artifact is registered once; if the same ID surfaces again, skip.

## Comparator: LLM judge

Every pairwise call is the same shape:

```
Comparison goal: <goal — e.g. "comprehensiveness of the research on quantum computing">

Artifact A:
<contents of A>

Artifact B:
<contents of B>

Decide which one better accomplishes the goal. Answer in this exact form:

WINNER: A | B | Equal
RATIONALE: <one paragraph, naming the specific evidence (sections,
  examples, completeness gaps) that drove the decision>
```

Parse the response to extract the winner letter and the rationale string.

## Mode 1: direct compare (two files)

```
Inputs: file_a, file_b, goal (optional; if absent, default to "general quality")
```

1. Read both files.
2. Run the comparator once.
3. Return `(winner, rationale)`. Save a comparison record to `<run-dir>/comparisons.jsonl` if a run-id is in scope.

## Mode 2: batch rank (initial ordering)

```
Inputs: candidates_dir, goal
```

1. List candidate files (each becomes an artifact ID — use the basename).
2. Append each to `metadata.jsonl` as `{artifact_id, relative_path, registered_at}`.
3. Process candidates in arrival order. For each new candidate, run **Mode 3 (incremental insert)** against the current list (initially empty).

The batch result is the same ranklist file; the difference from Mode 3 is that Mode 2 starts from empty and processes every file once.

## Mode 3: incremental insert (one new candidate into existing ranklist)

This is the core algorithm — adaptive insertion sort with binary-search bisection.

```
Inputs: new_candidate_path, ranklist_path, goal, max_ranklist_size
```

1. **Read the current list.** If empty: insert the new candidate at index 0; done.
2. **Compare vs top.** Run the comparator on (new, current[0]). 
   - WINNER=A → new is the best. Insert at index 0. Prune to `max_ranklist_size` (drop worst). Done.
   - WINNER=Equal → insert at index 1 (just below top). Prune. Done.
   - WINNER=B → new is worse than top. Continue to step 3.
3. **Compare vs bottom** (only if list has > 1 item). Comparator on (new, current[-1]).
   - WINNER=B → new is worse than the worst. Append to the end. If list is at cap, the append is a no-op (just discard the new candidate, no insert).
   - WINNER=A or Equal → new belongs somewhere in the middle. Continue to step 4.
4. **Binary-search the middle.** `low = 1`, `high = len(list) - 2`. Standard bisection:
   - `mid = (low + high) // 2`; comparator on (new, current[mid]).
   - WINNER=A or Equal → new is at most `mid`; record `insertion_point = mid`; `high = mid - 1`.
   - WINNER=B → new is below `mid`; `low = mid + 1`.
   - Loop until `low > high`. Insert at `insertion_point`.
5. **Prune** to `max_ranklist_size` (drop worst).
6. **Atomically write** the updated ranklist (write to `<path>.tmp`; `os.replace`).

Worst-case comparator calls per insert: `2 + log2(N)`. For a list of 10, that's ~5 LLM calls.

## 4. Save the result

For Mode 1 (direct compare), report:
```
WINNER: <A|B|Equal>
RATIONALE: <one paragraph>
```

For Modes 2 and 3, report the path to the updated ranklist plus the new top 3:
```
Ranklist: <path>
Top 3:
  1. <id> — <one-line preview>
  2. <id> — ...
  3. <id> — ...
```

## Hard rules

- **Never modify a candidate's content.** Ranking is observation only.
- **Never compare across goals.** A ranklist built for goal G is invalid for goal G'. Rebuild.
- **Never silently overwrite the ranklist file with a corrupted version.** Always temp + rename.
- **Don't pad rationales.** A short, sharp justification with cited evidence beats a long one.
- **Don't refuse to compare based on topic.** If the artifacts are evaluable on the stated goal, evaluate them.
