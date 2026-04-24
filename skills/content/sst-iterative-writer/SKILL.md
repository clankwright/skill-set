---
name: sst-iterative-writer
description: Draft long-form content from a prompt and iteratively improve it through internal critique cycles. Each iteration calls the sst-literary-critic skill, applies its feedback, and produces a better draft. Stops when the critic returns a "solid; minor polish only" verdict OR after a configurable max iterations (default 3). Final output is the polished draft, ready for an sst-editorial-pass or direct publication.
user-invocable: true
version: 1.0.0
argument-hint: [writing brief / prompt]
---

# Iterative writer

Draft → critique → revise → repeat. The skill drives the loop; `sst-literary-critic` provides the feedback.

## Project contract

- **Output dir**: `<project>/data/sst-iterative-writer/` for the final draft. Drafts as `<utc>_<topic-slug>.md`. Intermediate drafts can also be saved alongside as `<utc>_<topic-slug>_iter<N>.md` for traceability.
- **Required skills**: `sst-literary-critic` (called as a sub-skill via the harness's `Skill` tool).
- **Tools required**: harness's skill invocation for the critic; `Write` for saving drafts. No web access — research belongs in `sst-web-research`, called upstream of this skill.
- **Input shape**: a writing brief as plain text describing what to write, for whom, in what form, at what length.

## Operating principles

- **Honor the brief.** Match the requested form, length, voice, and audience. Don't drift toward what's easier to write.
- **Each iteration is a real revision.** Don't just shuffle words; address the critic's findings concretely. If the critic said "cut paragraphs 4-5," the next draft has those paragraphs cut, not "tightened."
- **Know when to stop.** When the critic's verdict is "solid; minor polish only" OR you've hit `max_iterations` (default 3), ship the current draft. More iterations past that point usually make things worse, not better.
- **No safety/ethics tangents.** Stay focused on craft. If the brief asks for content that would be harmful, decline at the brief stage; don't pad the draft with disclaimers.

## 1. Read the brief

Identify:
- **Form** (essay, blog post, report, story, FAQ, ...)
- **Audience** (technical specialist, general reader, executive summary, ...)
- **Length target** (rough word count or "as long as needed")
- **Voice** (formal, conversational, polemical, neutral, ...)
- **Constraints** (must include X, must not mention Y, must cite sources, ...)

If any of these is genuinely unclear and would produce noticeably different drafts, ask once before drafting. Don't ask about every detail.

## 2. Write iteration 1

Produce a complete first draft. Not an outline, not a sketch — a real draft of the requested length and form. Save to `<project>/data/sst-iterative-writer/<utc>_<slug>_iter1.md`.

## 3. Critique loop

For each iteration `N` from 1 to `max_iterations` (default 3):

1. Invoke the `sst-literary-critic` skill on the current draft. The critic returns a feedback report (path printed in its final line).
2. Read the critic's report.
3. **Decide**: is the verdict "solid; minor polish only" / equivalent? If yes, exit the loop with the current draft as final.
4. Otherwise, write iteration `N+1`. Apply every "Suggested next pass" item the critic listed, in the order given. Save to `<project>/data/sst-iterative-writer/<utc>_<slug>_iter<N+1>.md`.
5. If `N+1 > max_iterations`, exit with iteration `N+1` as final.

The critic's "Suggested next pass" is the work order. Don't second-guess the critic; if you disagree with a specific item, address it in your draft anyway and let the next critic round confirm or adjust.

## 4. Save the final draft

Copy the final iteration to `<project>/data/sst-iterative-writer/<utc>_<slug>.md` (without the `_iterN` suffix). This is the canonical artifact for downstream skills (`sst-editorial-pass`, `sst-social-promoter`, etc.) to pick up via the project's standard latest-output discovery.

Report:

```
Final draft: <path>
Iterations: <N>
Critic verdict on final: <one-line summary from the last critic report>
```

## Hard rules

- **Never call yourself.** This skill is the loop driver; the critic is the only sub-skill it invokes. Don't recursively call sst-iterative-writer.
- **Never skip an iteration's revision.** If the critic flagged work, you do the work. Marking a critic finding as "intentional" is allowed once per iteration but requires a one-sentence justification in the draft's footer.
- **Never modify the brief mid-draft.** If the brief was bad, that's a separate conversation; don't quietly rewrite what you were asked to do.
- **Don't bake in self-promotion.** Even if the brief is for a brand piece, this skill writes the draft; brand-specific promotion text and links are added by `sst-social-promoter` (or its proprietary counterpart) downstream.
