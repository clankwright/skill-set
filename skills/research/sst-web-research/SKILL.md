---
name: sst-web-research
description: Research a topic from scratch using web search, page fetches, and academic sources (arXiv). Produces a structured markdown report with a clear title, introduction, findings organized into logical sections, conclusion, and a complete list of source URLs. For technical/scientific topics, leads with arXiv before falling back to general web. Synthesizes — never plagiarizes — and always cites every source it uses.
user-invocable: true
version: 1.0.0
argument-hint: [topic or research question]
---

# Web research

A multi-step research loop: search → visit → extract → synthesize. The goal is one publishable markdown report with every claim cited.

## Project contract

- **Output dir**: `<project>/data/sst-web-research/` by default. Override via the project's harness-instructions file. Reports are written as `<utc>_<query-hash>.md`.
- **Tools required**: harness's `WebSearch` and `WebFetch` (or an equivalent page-fetcher; Playwright MCP for JS-heavy sites).
- **No state across runs**: each invocation is self-contained. Loading prior research happens only if the user explicitly references a prior report path.

## Operating principles

- **Synthesize, never plagiarize.** Use sources to inform your own writing. Quote sparingly and only with attribution.
- **Cite every claim.** Every factual statement in the report carries a source URL. The "Sources" section at the end lists them all.
- **Authoritative > popular.** Prefer primary sources (the original paper, the official docs, the original announcement) over commentary about them.
- **Stop when satisfied.** Aim for ~10 high-quality sources for a typical topic. More is overkill; fewer is usually weak coverage.
- **Stay technical.** Don't bend the report toward safety/ethics caveats unless the user asked for that angle. Surface them if they're directly relevant; otherwise focus on the technical and factual substance.

## 1. Frame the query

If the user's input is vague, restate the question in your own words at the top of your scratch notes. Decide:

- **Topic class**: technical/scientific (use arXiv-first), commercial (use vendor docs + comparison sites), news (use recent results + multiple outlets), how-to (use official docs + community write-ups).
- **Depth target**: a one-page brief vs. a comprehensive report. Default to comprehensive unless the user signals otherwise.

## 2. Search

For technical / scientific queries, lead with arXiv:

```
WebSearch: site:arxiv.org "<your terms>"           # find papers
WebSearch: "<your terms>" site:arxiv.org cat:cs.AI  # category-scoped
```

For everything else, start with broad web search:

```
WebSearch: <your specific terms>
```

Use search operators when refining:
- quotes for exact phrases (`"chain of thought prompting"`)
- `-` to exclude (`-reddit`)
- `site:` to scope (`site:openai.com`)
- `inurl:` / `intitle:` for targeted hits

If results are thin, refine: more specific terms, narrower scope, different operator. Don't accept a weak first batch.

## 3. Visit and extract

For each promising hit:

```
WebFetch: <url>  // Extract the parts relevant to: <your specific question>
```

For PDFs (typical on arXiv): fetch the PDF directly with `WebFetch`; the harness's PDF reader handles extraction. For JS-rendered pages where `WebFetch` returns empty content, fall back to Playwright MCP.

While reading, keep two scratch lists:
- **Facts found** (with source URL each).
- **Open questions** (with the search term you'd try next).

Iterate steps 2-3 until the open-questions list is empty or saturated.

## 4. Synthesize

Compose the report. Required structure:

```markdown
# <Clear, specific title — not the user's raw query>

## Introduction
<1-3 paragraphs: what's the topic, what's its scope in this report, what
does the reader walk away knowing.>

## <Section 1 — first major finding cluster>
<2-5 paragraphs of findings with inline citations like ([Source](url)).>

## <Section 2>
...

## <Section N>
...

## Conclusion
<1-2 paragraphs: what the research showed, what's still open or contested,
what the natural next step is.>

## Sources
- [<page title>](<url>) — <one-line note on what this source contributed>
- ...
```

**Inline citation style**: every paragraph that asserts a fact ends with at least one `([Source N](url))` reference. The Sources list at the end is the authoritative roll-call; inline links point into it.

## 5. Write the file

Save the report to `<project>/data/sst-web-research/<utc>_<short-slug>.md`. The slug is a 3-5-word kebab-case version of the topic. If the dir doesn't exist, create it.

Report path back to the user as the final line of your response.

## Hard rules

- **No fabricated URLs.** Every source URL was actually fetched. If you couldn't fetch it, it doesn't go in the report.
- **No fabricated facts.** If a search found a claim but no source backs it up, drop the claim.
- **No `<URL_HERE>` placeholders.** Either fill them in or remove the surrounding sentence.
- **No safety/ethics editorializing.** Surface real safety considerations only when they're directly part of the topic; don't append a generic disclaimer.
- **No "I think"/"I believe"** in the report body. The report is a synthesis, not your opinion.
