---
name: sst-wiki-curator
description: "Build and maintain LLM-curated knowledge wikis for prose domains (legal/regulatory tracking, scientific literature, market intelligence, product taxonomies, personal research notes, etc.). Two modes. (a) Scaffold — create a new wiki at a chosen path, picking one of three variants (minimal — hand-curated markdown only; middle — raw dumps plus curated subdirs plus lint report, no scripts; scripted — full sources.json plus download/convert/index/lint/licenses pipeline with YAML front matter). Writes the schema spec (AGENTS.md or CLAUDE.md), README, append-only log, root index.md, plus the variant's standard subdirs and any scripts. (b) Ingest/maintain — read an existing wiki's schema spec, add a new source (or run a lint pass), generate or update the relevant pages with proper YAML front matter and cross-references in the wiki's chosen wikilink convention, refresh the root index.md catalog, append to log.md, and (for scripted variants) re-run the index/lint pipeline. Not for code repos, tabular data, or single-document summarization — those have better tools."
user-invocable: true
version: 1.0.0
argument-hint: "scaffold <wiki-root> [--variant minimal|middle|scripted] | ingest <wiki-root> <source-url-or-file> | maintain <wiki-root> [--lint]"
---

# Wiki curator

Build and maintain plain-markdown knowledge wikis for prose domains, following the three-layer pattern (raw sources → curated wiki → schema spec) popularized by Karpathy's [LLM-managed wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The wiki is greppable, diffable, portable, and accumulates knowledge across many sources instead of re-deriving it every query — no embeddings, no vector DB, no vendor lock-in.

## When to use this pattern

A domain where you want to:

- Accumulate prose knowledge across many sources (papers, articles, reports, regulations, product docs).
- Keep the corpus greppable, diffable, version-controllable, and portable.
- Have an LLM agent do the maintenance (summaries, cross-references, filing, index upkeep).
- Stay under ~200 pages without needing extra retrieval infrastructure.

If the domain is code, use a code repo. If it's tabular data, use a spreadsheet or database. This skill is for prose knowledge.

## Project contract

- **Wiki root**: any directory the user picks. The skill operates only inside that directory and any user-named subdirs (e.g. `raw/`, `wiki/`, `scripts/`). Never write outside the wiki root.
- **Schema spec**: each wiki has one canonical operational spec the LLM reads before doing work. By default named `AGENTS.md`; pick `CLAUDE.md` instead if the project's harness auto-loads it (Claude Code does). The skill respects whichever name is already present; only when scaffolding from scratch does it pick a default.
- **No state across runs**: each invocation is self-contained. Loading prior context comes from reading the wiki's own files (`AGENTS.md` / `CLAUDE.md`, `index.md`, `log.md`).
- **Tools required**: file system access; for the scripted variant's optional ingest, an HTTP fetcher (the harness's `WebFetch` or equivalent) and a markdown converter.

## Operating principles

- **Plain markdown in git is the source of truth.** No Obsidian plugins, no Notion, no Roam. Obsidian is fine as a viewer; do not write to it.
- **Synthesize, never plagiarize.** The LLM's job is to summarize, cross-reference, and file. Quote sparingly and only with attribution. Preserve the source's claim; never invent.
- **Cite every claim.** Each factual statement on a wiki page must trace back to a source in `raw/` (or `sources/`) or to another wiki page. Front matter and inline citations both count.
- **The index is agent-maintained.** Do not hand-edit `index.md` or wikilinks once the wiki is past the seed stage. The agent updates them on every ingest.
- **Append-only log.** `log.md` records what happened, in chronological order. Never rewrite past entries. Date-prefixed lines so unix tools can parse them.
- **Pick the minimal variant unless you already know you need the scripted one.** Adding scripts later is cheap; removing them is not. The middle variant exists for wikis that ingest a lot of raw material but don't yet need automated lint/index.

## Three-layer architecture

Every wiki has three logical layers:

1. **`raw/` or `sources/`** — immutable source documents (articles, PDFs, HTML dumps, converted markdown). Never edit. Typically gitignored once it grows past a few MB.
2. **`wiki/`** (the working layer) — LLM-generated markdown pages. Papers, topics, entities, events, analyses. This is what humans read and what the agent maintains.
3. **Schema spec** (`AGENTS.md` or `CLAUDE.md`) — the operational contract the LLM reads before doing work. Page types, ingest workflow, wikilink convention, front-matter fields, contradiction handling, lint expectations.

Top-level files outside the three layers:

- `README.md` — human-facing intro.
- `log.md` — append-only operational log.
- `sources.json` (scripted variant only) — manifest of every source with id, URL, license, topics.
- `LICENSES.md` (scripted variant only) — generated license summary.

Example layout:

```
<wiki-root>/
├── AGENTS.md              # or CLAUDE.md; the schema for the LLM
├── README.md              # human-facing docs
├── log.md                 # append-only operational log
├── sources.json           # source manifest (scripted variant)
├── sources/               # raw downloads (scripted; gitignored once large)
│   ├── html/
│   ├── pdf/
│   └── md/                # converted-to-markdown
├── raw/                   # source markdown (minimal/middle variants)
├── wiki/
│   ├── index.md           # catalog with one-line summaries, by section
│   ├── papers/            # one page per source (or per topic in minimal)
│   ├── topics/            # one page per concept
│   ├── analysis/          # syntheses, rankings, open questions
│   └── build/             # generated index artifacts (scripted; gitignored)
└── scripts/               # scripted variant only
    ├── _wiki.py           # shared front-matter + wikilink parsing
    ├── download.py        # fetch sources listed in sources.json
    ├── convert.py         # HTML/PDF → markdown
    ├── index.py           # build TF-IDF + wikilink graph + keyword index
    ├── lint.py            # link/metadata/parity/license checks
    └── licenses.py        # apply license fields + regenerate LICENSES.md
```

Subdir names under `wiki/` are domain-specific. Common choices: `papers/`, `topics/`, `analysis/`; or `concepts/`, `entities/`, `events/`, `culture/`; or `cases/`, `statutes/`, `commentary/` for a legal wiki. Pick names that match the domain's natural taxonomy, document them in the schema spec, and stick with them. Two levels under `wiki/` is plenty; deeper nesting hurts greppability.

## The three variants

| Variant   | Sources                  | Scripts | Lint              | Use when                                                        |
|-----------|--------------------------|---------|-------------------|-----------------------------------------------------------------|
| Minimal   | Plain markdown in `raw/` | None    | LLM judgment only | Bootstrapping, small domain, hand-curated prose. Cleanest start.|
| Middle    | Raw dumps in `raw/<src>/`| None    | LLM-written report| Bigger corpus, lots of source material, but no need for automation yet. |
| Scripted  | `sources.json` manifest  | Full    | Automated checks  | Defined corpus of primary sources, automated ingest desired.    |

## File conventions

### Naming

- Paper pages: `<slug>.md` where slug matches the `id` in `sources.json` (scripted) or the source filename (minimal/middle). Keep slugs short, lowercase, hyphenated, version-agnostic.
- Topic pages: `<topic-slug>.md`, stable English names.
- No numeric prefixes on filenames. No dates in filenames.

### YAML front matter

Every wiki page starts with front matter the linter and indexer can parse. Required fields differ by page type. Minimum:

```yaml
---
id: <slug>
title: "<human title>"
kind: paper | topic | analysis | entity | event | concept
---
```

Paper pages add: `url`, `year`, `venue`, `access` (open | paywall | preprint), `license` (CC-BY-4.0 | public-domain | proprietary | …), `topics:` (list of topic slugs).

Topic pages add: `topic: <slug>` (matches the file's id).

The minimal variant MAY skip front matter on paper pages and let the source filename + a top-of-page summary block carry the metadata; topic pages still benefit from front matter as soon as a linter exists.

### Cross-references

Two styles work; pick one per wiki and be consistent:

- **Wikilinks**: `[[slug]]` or `[[dir/slug]]`. Parsable by an indexer script. Good when a linter enforces them.
- **Relative markdown links**: `[Title](../topics/foo.md)`. No tooling required. Better for the minimal variant.

External links are always normal markdown `[text](url)`.

### Page length

Favor long, self-contained pages over many stubs. If a topic page is a paragraph plus three wikilinks, merge it into a sibling. Orphan-topic and low-inbound-link signals (from the linter or the LLM's lint pass) surface these.

### Contradiction handling

When two sources disagree on the same claim, the topic page records the disagreement explicitly, names both sources, and either picks the better-supported claim with a one-line rationale or marks the topic `unresolved`. Never silently average or paraphrase away the conflict.

### Append-only log

`log.md` records every ingest, query, and lint pass. Two formats both grep cleanly; pick one and stick with it:

```
# single-line per event
2026-04-21 INGEST: <slug> added; linked into <topic-1>, <topic-2>
2026-04-21 LINT: 0 warnings, 0 errors across <N> pages
```

```
# section per event
## [2026-04-21] ingest | <slug>
Added paper page; linked into topics/<t1>, topics/<t2>.
License = CC-BY-4.0, full-text redistributable.
```

## Mode A: scaffold a new wiki

The user passes `scaffold <wiki-root> [--variant minimal|middle|scripted]`. If `--variant` is omitted, default to **minimal** and tell the user; prompt to switch only if the user explicitly mentions a defined corpus or automated lint.

### A.1 — confirm the variant + subdir taxonomy

Before writing anything, restate the plan back to the user in 3-4 lines:

```
About to scaffold <variant> wiki at <wiki-root> with subdirs:
  - wiki/<sub-1>/  (<purpose>)
  - wiki/<sub-2>/  (<purpose>)
Schema spec: <AGENTS.md|CLAUDE.md>
Wikilink style: <wikilinks|relative>
Confirm or correct.
```

Pick the schema name based on the harness: `CLAUDE.md` if the user is on the Claude Code harness (auto-loaded), `AGENTS.md` otherwise. Pick the subdir taxonomy by asking the user one question: "What kinds of pages will this wiki hold?" Map common answers:

- "Papers and concepts" → `papers/`, `topics/`, `analysis/`
- "Things, people, events" → `entities/`, `events/`, `concepts/`, `culture/`
- "Cases and statutes" → `cases/`, `statutes/`, `commentary/`
- "Products and companies" → `products/`, `companies/`, `categories/`

If unclear, default to `papers/`, `topics/`, `analysis/` and explain the user can rename later.

### A.2 — create the directory tree

```bash
mkdir -p <wiki-root>/{raw,wiki/<sub-1>,wiki/<sub-2>,wiki/<sub-3>}
# scripted variant only:
mkdir -p <wiki-root>/{sources/html,sources/pdf,sources/md,wiki/build,scripts}
```

### A.3 — write the schema spec

The schema spec is the contract the LLM reads on every future invocation. Keep it short — everything the LLM needs, nothing it can infer from examples. Required sections:

1. **Structure** — the directory tree and what each subdir holds.
2. **Page format** — the YAML front-matter block + the body sections each page kind requires.
3. **Naming conventions** — slug rules.
4. **Wikilink convention** — wikilinks vs relative links; one or the other, not both.
5. **Workflows** — `Ingest`, `Query`, `Lint` (each with numbered steps).
6. **Writing style** — concrete rules. Examples: "no em dashes; use colons or commas instead", "no hedging language (`I believe`, `perhaps`, `it seems`)", "every claim cites a file in `raw/`".

A starting template (adapt per domain):

```markdown
# <Domain> Knowledge Base

## Structure

\`\`\`
raw/          # Source documents. Never edit.
wiki/         # LLM-compiled knowledge base.
  index.md    # Catalog: every wiki page with one-line summary, by section.
  <sub-1>/    # <purpose>
  <sub-2>/    # <purpose>
log.md        # Append-only operation log
\`\`\`

## Wiki article format

Every wiki article follows this template:

\`\`\`markdown
---
id: <slug>
title: "<human title>"
kind: <kind>
---

# Article Title

> **Summary:** One-paragraph overview.

**Sources:** [[raw/<source>.md]], …

## <Section heading>

Body text with cross-references: [<title>](../<sub>/<slug>.md).

## See also

- [<related>](../<sub>/<related>.md)
\`\`\`

## Workflows

### Ingest
1. Place source(s) in `raw/`.
2. Read each source.
3. Extract methods, entities, concepts, claims.
4. Create or update wiki articles in the appropriate subdir.
5. Add cross-references.
6. Update `wiki/index.md`.
7. Append to `log.md`: `YYYY-MM-DD INGEST: <description>`.

### Query
1. Search relevant wiki pages.
2. Synthesize a response citing specific articles.
3. If the synthesis is durable, file it as a new wiki page.
4. Append to `log.md`: `YYYY-MM-DD QUERY: <summary>`.

### Lint
1. Scan all wiki articles for: contradictions, missing cross-references, orphan pages, broken links, gaps (raw topics without wiki coverage), stale claims.
2. Produce a lint report.
3. Append to `log.md`: `YYYY-MM-DD LINT: <summary>`.

## Writing style

- Concise, technically confident. No fluff or hedging.
- No em dashes. Use colons, semicolons, commas, or restructure.
- No "I believe", "perhaps", "it seems", "in order to", "utilize".
- Cross-reference liberally; isolated articles are less useful.
- Every claim must trace to a file in `raw/`.
- Raw sources are immutable; all curation happens in `wiki/`.
```

### A.4 — write README.md and log.md

`README.md` is human-facing: 3-5 paragraphs covering what the wiki is, who maintains it, how to add a source, how to query. Reference the schema spec for the operational contract.

`log.md` starts with one seed line:

```
YYYY-MM-DD INIT: <one-line description of the domain and intent>
```

### A.5 — write wiki/index.md

A skeleton catalog grouped by section, with placeholder lines under each section. The agent fills it in on first ingest:

```markdown
# <Domain> Wiki — Index

## <Sub-1>

_(no entries yet)_

## <Sub-2>

_(no entries yet)_
```

### A.6 — scripted variant only: copy and customize the script kit

For the scripted variant, write or copy these files into `scripts/` (full versions in §Scripts reference below):

- `scripts/_wiki.py` — shared front-matter parser + wikilink walker.
- `scripts/download.py` — reads `sources.json`, fetches each `url` to `sources/html/<id>.html` (or `pdf`).
- `scripts/convert.py` — HTML/PDF → clean markdown in `sources/md/<id>.md`.
- `scripts/index.py` — walks `wiki/`, writes `wiki/build/{index,graph,keywords,pages}.json` plus `tfidf.npz` + `tfidf_vocab.json`.
- `scripts/lint.py` — exits non-zero on broken wikilinks, missing required front-matter fields, orphan topic pages, papers nothing links to, `sources.json` ↔ `wiki/papers/` id parity mismatch, malformed URLs, missing licenses.
- `scripts/licenses.py` — treats `sources.json` as the source of truth for per-source licenses; regenerates `LICENSES.md`.

Also write `sources.json` with one or two seed entries:

```json
{
  "sources": [
    {
      "id": "<slug>",
      "title": "<title>",
      "url": "<url>",
      "year": 2026,
      "venue": "<venue>",
      "access": "open",
      "license": "CC-BY-4.0",
      "topics": ["<topic-1>"]
    }
  ]
}
```

### A.7 — write `.gitignore`

Track scripts, manifests, schema, and the curated wiki. Ignore:

```
sources/html/
sources/pdf/
sources/md/
sources/download_log.json
wiki/build/
__pycache__/
*.pyc
```

Commit the full text of a source only when its `license` permits redistribution (CC-BY-*, public-domain, the source is the user's own work). Keep `license` and `url` in the page's YAML front matter when committed.

### A.8 — verify scaffold

Smoke-test:

- For all variants: re-read the schema spec end-to-end. Confirm it answers: "If a new agent picks this up tomorrow, can it ingest the next source without asking?" Tighten anywhere it can't.
- For scripted: from `<wiki-root>`, run `python3 scripts/lint.py`. Expect zero errors against the empty wiki + seed `sources.json`. If it fails, fix the script before declaring scaffold done.

### A.9 — append to log.md and commit

```
YYYY-MM-DD INIT: scaffolded <variant> wiki at <wiki-root>; subdirs: <sub-1>, <sub-2>, <sub-3>; schema spec: <AGENTS.md|CLAUDE.md>; wikilink style: <wikilinks|relative>.
```

Then `git init` (if the wiki root isn't already a repo) and commit everything in one commit: `<scope>: scaffold <domain> wiki (<variant>)`.

## Mode B: ingest a new source

The user passes `ingest <wiki-root> <source-url-or-file>`. The skill walks the variant's workflow.

### B.1 — read the schema spec FIRST

Before touching any wiki page, read `<wiki-root>/AGENTS.md` (or `CLAUDE.md`) end-to-end. Note: page kinds, subdir taxonomy, wikilink style, required front-matter fields, contradiction handling, writing style. The schema is authoritative; if your defaults conflict with it, the schema wins.

Also read `<wiki-root>/wiki/index.md` to know what already exists. A new ingest should never duplicate an existing page; it links to the existing one and extends it.

### B.2 — fetch and convert (variant-dependent)

**Minimal variant.** Drop the source markdown directly into `<wiki-root>/raw/<slug>.md`. If given a URL, fetch it (harness `WebFetch`) and save the raw text. If given a PDF, convert to markdown (`pymupdf4llm` or equivalent) before saving.

**Middle variant.** Same as minimal, but raw dumps may be organized into subdirs by source: `raw/<source-org>/<slug>.md`.

**Scripted variant.**

1. Add a new entry to `sources.json` with `id`, `url`, `year`, `venue`, `access`, `topics:`. Pick a slug consistent with existing slugs.
2. Add a `LICENSE_MAP` entry in `scripts/licenses.py` if the license isn't already mapped from URL prefix.
3. Run `python3 scripts/licenses.py all` to fill the `license` field and regenerate `LICENSES.md`.
4. Run `python3 scripts/download.py` to fetch HTML/PDF into `sources/`.
5. Run `python3 scripts/convert.py` to turn HTML/PDF into clean markdown at `sources/md/<id>.md`.

### B.3 — read the source

Read the converted source end-to-end. Note: key methods, entities, concepts, claims, and which claims are novel vs. already-covered by existing wiki pages. If the source is large, summarize each section in scratch notes before writing any wiki page.

### B.4 — write the paper page

Create `<wiki-root>/wiki/papers/<slug>.md` (or the scripted variant's equivalent path).

Structure:

```markdown
---
id: <slug>
title: "<human title>"
kind: paper
url: <url>
year: <year>
venue: <venue>
access: <open|paywall|preprint>
license: <license>
topics: [<topic-1>, <topic-2>]
---

# <human title>

> **Summary:** Two to four sentences. What the source is, what it claims, why it matters. No fluff.

**Sources:** [[raw/<slug>]]

## Key claims

- Claim 1: <one sentence>. Source: §<section> of [[raw/<slug>]].
- Claim 2: …

## Methods (or: Approach / Argument / Evidence)

<2-5 paragraphs.>

## Findings (or: Results / Conclusions)

<2-5 paragraphs.>

## Limitations and open questions

<1-3 paragraphs. What the source doesn't address. Where claims are uncertain.>

## Connections to other wiki pages

- [[topics/<related>]] — <one-line of how this paper relates>
- [[topics/<another>]] — <…>

## See also

- [<related paper>](../papers/<slug>.md)
```

Adapt section names to the domain. A legal wiki's paper page might use `Holding`, `Reasoning`, `Citations`. A market-intel wiki's might use `Market`, `Position`, `Risks`. Whatever the domain's natural shape is.

### B.5 — link the new paper into existing topic pages

For every topic in the new paper's `topics:` field:

1. Open `<wiki-root>/wiki/topics/<topic>.md` (or the variant's path).
2. If it doesn't exist, create it (front matter `kind: topic`, the standard summary + sections + see-also).
3. Add a wikilink (or relative link) to the new paper under the topic page's "Sources" or "Key papers" section, with one line of context.
4. If the new paper changes a topic's overall claim, update the topic page's body — never just append, restructure if needed. Resolve contradictions per the schema spec's contradiction-handling rule.

### B.6 — update wiki/index.md

Add the new paper page to its section's catalog with a one-line summary. If a new topic page was created, add it to the topics section. Keep entries alphabetized within each section.

### B.7 — scripted variant: rebuild index + lint

```bash
python3 scripts/index.py
python3 scripts/lint.py
```

Fix every error before declaring the ingest done. Common fixes: add a missing topic link, fill a missing front-matter field, rename a slug to match `sources.json`.

### B.8 — append to log.md

```
YYYY-MM-DD INGEST: <slug> added; linked into <topic-1>, <topic-2>; license=<license>.
```

### B.9 — commit

One commit covering: `sources.json` (scripted), the new raw source (minimal/middle, if license permits), the new paper page, every modified topic page, `wiki/index.md`, `log.md`, and any regenerated build artifacts (scripted, if you commit them — most don't).

Commit message: `<wiki-name>: ingest <slug> — <one-line of what it adds>`.

## Mode C: maintain (lint pass)

The user passes `maintain <wiki-root> [--lint]`. Lint surfaces drift the agent should fix.

### C.1 — read the schema spec

Same as B.1.

### C.2 — run the lint checks

**Minimal/middle variants** (no scripts) — LLM walks the wiki and checks:

1. **Broken cross-references.** Walk every relative link or wikilink; flag targets that don't exist.
2. **Orphan topic pages.** Topics with no inbound links from any paper or analysis page.
3. **Papers nothing links to.** Paper pages that no topic mentions.
4. **Missing front matter.** Pages without the required fields per the schema.
5. **Index drift.** Pages in `wiki/` not listed in `index.md`, or vice versa.
6. **Stale claims.** Claims contradicted by a newer source. (LLM judgment; flag for human review rather than auto-fix.)
7. **Contradiction handling.** Topics with multiple sources making incompatible claims that the topic page hasn't surfaced.
8. **Gaps.** Topics referenced repeatedly across paper pages with no dedicated topic page.

**Scripted variant** — additionally:

```bash
python3 scripts/lint.py
```

…which exits non-zero on broken wikilinks, missing front-matter fields, orphan topics, parity mismatches between `sources.json` and `wiki/papers/`, malformed URLs, and missing licenses.

### C.3 — produce a lint report

Write `<wiki-root>/wiki/LINT-REPORT.md` (or append to it if it exists with a date header). Group findings by category. For each finding: file path, line if applicable, one-line description, suggested fix. Mark each finding `[auto]` (safe to apply automatically) or `[review]` (needs human judgment).

### C.4 — apply auto-safe fixes

Apply only `[auto]` findings (broken-link slug typos, missing front-matter scaffolding, index entries for already-existing pages). Leave `[review]` findings in the report for the human.

### C.5 — append to log.md

```
YYYY-MM-DD LINT: <N> findings; <M> auto-applied; <K> for review. See LINT-REPORT.md.
```

### C.6 — commit

One commit: `<wiki-name>: lint pass — <one-line summary>`.

## Wikilinks vs. relative links

A wiki picks one and sticks with it. The schema spec records the choice.

- **Wikilinks** `[[slug]]` or `[[dir/slug]]` — terse, parsable by an indexer, but require tooling (linter or Obsidian-style preview) to navigate. Good for the scripted variant.
- **Relative markdown links** `[Title](../topics/foo.md)` — render natively in any markdown viewer (GitHub, VS Code, plain editor), no tooling required. Good for the minimal/middle variants.

Mixing the two within one wiki creates index-drift bugs. Don't.

External links (URLs to non-wiki targets) are always normal markdown `[text](url)` regardless of the wiki's internal style.

## License tracking

A wiki that ingests external sources tracks the license of each source. The minimum:

- **Per-source `license` field** in YAML front matter (paper pages) or in `sources.json` (scripted).
- **Common values**: `public-domain`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC-BY-NC-4.0`, `proprietary`, `unknown`.
- **Redistribution rule**: commit the source's full text only when the license permits. `public-domain` and `CC-BY-*` permit; `proprietary` and `unknown` do not — store these only in the LLM's working layer (paper-page summary + key-claim citations) and let the user fetch the original via `url` if they need full text.
- **`LICENSES.md`** (scripted variant) is regenerated from `sources.json` and lists every source's license alongside its title and `url`.

Never commit a source whose license is `proprietary` or `unknown`. The paper page's summary + cited claims are derivative work and generally fall under fair-use; the full text is not.

## Anti-patterns

- **Embedding-based RAG over a personal corpus.** Vector-DB RAG makes the LLM rediscover knowledge every query — no accumulation, no diff, no portability. Use plain markdown + wikilinks + (optionally) a TF-IDF index instead.
- **Tool lock-in.** Plain markdown in git is the source of truth. Obsidian / Notion / Roam are viewers, not stores.
- **Fragmenting a topic into many stubs.** Prefer one dense page over five empty ones. Linter's orphan-topic and low-inbound-link signals surface this.
- **Hand-curated cross-references.** The agent maintains them; humans review the diff. A human who wikilinks by hand will fall behind within a week.
- **Deep nesting.** Two levels under `wiki/` is plenty. Deeper trees hurt greppability and `index.md` upkeep.
- **Numeric prefixes or dates in filenames.** Slug must be stable across edits. Dates live in front matter.
- **Silently averaging contradictions.** When two sources disagree, the topic page surfaces the disagreement, names both sources, and either picks the better-supported claim with a rationale or marks the topic `unresolved`.
- **Editing past `log.md` entries.** Append-only. If a past entry is wrong, append a correction with the same date.

## Scale guidance

- **Under 50 pages**: a single `index.md` with one-line summaries is all the retrieval you need. No scripts.
- **50 to 200 pages**: `index.md` + wikilinks + `scripts/index.py`'s TF-IDF output is still comfortable in one prompt.
- **Over 200 pages**: split `index.md` by section, each linking to a section index. Add a local TF-IDF / BM25 query CLI if needed. Still no embeddings.

## Human vs LLM roles

The human curates sources, directs analysis, decides what matters, and reviews the diff. The LLM does summarizing, cross-referencing, filing, index upkeep, and lint. A single new source typically touches 10-15 wiki pages — that fan-out is why LLM maintenance is load-bearing. Hand-maintaining wikilinks doesn't scale.

## Scripts reference (scripted variant)

When scaffolding the scripted variant, the script kit is small and follows conventions. Each script is ≤200 LoC; copy from any existing scripted wiki when bootstrapping a new one and adapt the constants (paths, license map, source-fetch headers).

- `_wiki.py` — front-matter parser (`parse_yaml_frontmatter(text) → (frontmatter_dict, body_str)`) plus a wikilink walker (`extract_wikilinks(body) → list[str]`).
- `download.py` — reads `sources.json`, for each entry fetches `url` to `sources/html/<id>.html` (or `pdf`); records timestamps and HTTP status to `sources/download_log.json`. Skip on file-exists unless `--refresh`.
- `convert.py` — for each `sources/html/<id>.html` or `sources/pdf/<id>.pdf`, produces `sources/md/<id>.md`. HTML via `markdownify`; PDF via `pymupdf4llm`.
- `index.py` — walks `wiki/`, parses every page's front matter and wikilinks, writes:
  - `wiki/build/index.json` — page-id → file-path + title + kind + topics
  - `wiki/build/graph.json` — adjacency list of wikilinks
  - `wiki/build/keywords.json` — top-N keywords per page (TF-IDF rank)
  - `wiki/build/pages.json` — full text of every page (for downstream tools)
  - `wiki/build/tfidf.npz` + `tfidf_vocab.json` — sparse matrix for similarity queries
- `lint.py` — exit 0 on success, 1 on errors. Checks: front-matter required-fields, slug ↔ filename match, wikilink target exists, `sources.json` ↔ `wiki/papers/` parity, `topics:` references existing topic pages, license-required-when-committed-source.
- `licenses.py` — `licenses.py all` walks `sources.json`, fills missing `license` from `LICENSE_MAP` (URL-prefix-keyed), regenerates `LICENSES.md` at `<wiki-root>/LICENSES.md` and `<wiki-root>/wiki/LICENSES.md`.

These scripts assume the directory shape in §Three-layer architecture. Don't reorganize without updating every script's path constants.

## Acceptance

A scaffold pass is done when:

- The directory tree exists with all required subdirs.
- The schema spec is written, complete, and self-contained (a fresh agent can ingest the next source from it alone).
- `README.md`, `log.md` (with INIT entry), and `wiki/index.md` (skeleton) are written.
- For scripted: `sources.json` has at least one seed entry, every script is present and `lint.py` exits 0.
- The scaffold is committed.

An ingest pass is done when:

- The new source is in `raw/` (minimal/middle) or `sources/md/` + `sources.json` (scripted).
- The new paper page is written with full front matter and body.
- Every topic page in the paper's `topics:` is updated (or created) with a link to the new paper.
- `wiki/index.md` lists the new page.
- For scripted: `lint.py` exits 0.
- `log.md` has the new INGEST entry.
- The change is committed in one commit.

A maintain pass is done when:

- `LINT-REPORT.md` is written with all findings categorized.
- All `[auto]` findings are applied.
- `log.md` has the new LINT entry.
- The change is committed in one commit.
