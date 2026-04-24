---
name: sst-editorial-pass
description: |
  Run a draft through a structured multi-pass editorial review — high-level scope check, citation verification (via sst-fact-checker sub-skill), claim segmentation, fact-correction application, then a final clarity/conciseness pass. Produces a polished, publish-ready draft plus a summary of edits made and any remaining open questions. Designed to consume the output of sst-iterative-writer or any human draft.
user-invocable: true
version: 1.0.0
argument-hint: [path to draft file or raw draft text]
---

# Editorial pass

A serious editor reads a draft in passes, each handling one concern. This skill encodes that procedure: scope first, then facts, then prose. The `sst-fact-checker` sub-skill handles the verification work.

## Project contract

- **Output dir**: `<project>/data/sst-editorial-pass/` for the edited draft. Files as `<utc>_<draft-slug>.md`.
- **Required skills**: `sst-fact-checker` (called as a sub-skill).
- **Tools required**: harness's `Read`, `Skill` (for invoking sst-fact-checker), `Write`. Web access only as needed for sst-fact-checker's downstream search.
- **Input shape**: a draft as raw text or a file path.

## Operating principles

- **Cheap passes first.** A scope problem invalidates all the later work; check it first and bail early if the draft is fundamentally off-target.
- **Don't fix what isn't broken.** If a section is clean, leave it alone. The point of an editorial pass is to surface and fix real problems, not to demonstrate that you read carefully.
- **Cite the corrections.** When you fix a fact, name the source from the sst-fact-checker that backs the correction. If the sst-fact-checker came back unverified, mark the claim as `[unverified]` in the edited draft — don't quietly delete it.
- **Track what you did.** The output isn't just the edited draft; it's the edited draft + a summary of what changed and why.
- **No safety/ethics expansion.** Don't add safety/ethics caveats the original draft didn't have. If anything, remove generic ones the writer padded in.

## Pass 0: high-level scope review

Read the draft once, top to bottom. Ask:
- Scope much too broad or too narrow for the brief?
- Length way off (10x too long, 10x too short)?
- Tone mismatched with the audience?
- Missing major sections the brief implied?
- Padded with generic safety/ethics framing the brief didn't ask for?

If the answer to any of these is YES with high impact, **stop here**. Return the draft to the writer with a one-paragraph scathing-but-specific critique and clear required improvements. Do NOT spend the time on later passes against fundamentally wrong content.

If the draft is in the right ballpark, continue.

## Pass 1: claim extraction and fact-checking

Walk the draft and extract every claim that's a factual assertion (something verifiable, not opinion or stylistic flourish). Indicators that a sentence carries a factual claim:

- Specific dates, numbers, percentages, years.
- Named studies, institutions, authorities.
- Phrases like "according to," "research shows," "X is the largest/oldest/most/...".
- Citations or footnotes already in the draft (re-verify them).

Group related claims that share a search angle. Send the batch to the `sst-fact-checker` sub-skill:

```
Skill: sst-fact-checker
  input: <newline-separated claims, with provided source URLs in (claim, url) form when available>
```

Wait for the sst-fact-checker's report. It will return three buckets: verified / corrected / unverified.

## Pass 2: apply corrections

For each corrected claim: rewrite the sentence in the draft to use the sst-fact-checker's corrected statement. Keep the surrounding prose; just swap the wrong fact for the right one. Add the source URL inline if the draft uses citations.

For each unverified claim: mark the sentence in the draft with `[unverified]` (inline) and add a footnote or end-of-doc list entry naming what couldn't be verified. Don't silently drop unverified claims — that would change the draft's meaning without a record.

For each verified claim: no change needed. (You may add the cite if the draft is missing one.)

## Pass 3: clarity, conciseness, completeness

After all factual corrections are in, do ONE prose pass focused on:

- **Clarity**: Sentences that are hard to parse on first read get rewritten. No "gotcha" syntax.
- **Conciseness**: Cut filler words ("very," "really," "in order to," etc.). Cut redundant sentences. Cut padding paragraphs.
- **Completeness**: If a section the brief implied is missing AND the writer's drafts didn't cover it, add a short note `[missing: <topic>]` rather than filling it in yourself — that's outside this pass's scope.

Maintain the draft's voice. Don't rewrite it in a different tone.

## 4. Save the edited draft

Save to `<project>/data/sst-editorial-pass/<utc>_<slug>.md` with this structure:

```markdown
# <Draft title>

## Edit summary
- Verified claims: <N>
- Corrections applied: <N> (from sst-fact-checker report at <path>)
- Unverified claims marked: <N>
- Sections rewrote for clarity: <list>
- Sections cut: <list>
- Sections that need more research: <list of `[missing: ...]` markers>

## Remaining open questions
- <one-line each, anything the writer / editor / next reviewer still needs to settle>

## Edited draft
<the full, polished content here, with [unverified] inline markers
where they apply>
```

Report the file path as the final line of your response.

## Hard rules

- **Never silently delete content.** Cuts go in the "Sections cut" list with one-line reason.
- **Never apply a "correction" without a sst-fact-checker source.** If the sst-fact-checker said unverified, the inline marker stays — it doesn't get rewritten in either direction.
- **Don't escalate scope.** If you find an issue that's outside an editorial pass (e.g. the architecture of the argument is broken), flag it in "Remaining open questions" — don't restructure the piece.
- **Don't bypass sst-fact-checker.** Even when the draft is short, every factual claim goes through the sub-skill. The whole point is the audit trail.
