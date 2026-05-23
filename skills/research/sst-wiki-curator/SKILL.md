---
name: sst-wiki-curator
description: "Build and maintain LLM-curated knowledge wikis for prose domains (legal/regulatory tracking, scientific literature, market intelligence, product taxonomies, personal research notes, etc.). Two modes. (a) Scaffold — create a new wiki at a chosen path, picking one of three variants (minimal — hand-curated markdown only; middle — raw dumps plus curated subdirs plus lint report, no scripts; scripted — full sources.json plus download/convert/index/lint/licenses pipeline with YAML front matter). Writes the schema spec (AGENTS.md or CLAUDE.md), README, append-only log, root index.md, plus the variant's standard subdirs and any scripts. (b) Ingest/maintain — read an existing wiki's schema spec, add a new source (or run a lint pass), generate or update the relevant pages with proper YAML front matter and cross-references in the wiki's chosen wikilink convention, refresh the root index.md catalog, append to log.md, and (for scripted variants) re-run the index/lint pipeline. Not for code repos, tabular data, or single-document summarization — those have better tools."
user-invocable: true
version: 1.1.0
argument-hint: "scaffold <wiki-root> [--variant minimal|middle|scripted] | ingest <wiki-root> <source-url-or-file> | maintain <wiki-root> [--lint] | umbrella <parent-dir>"
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

Every wiki has three required layers:

1. **`raw/` or `sources/`** — immutable source documents (articles, PDFs, HTML dumps, converted markdown). Never edit. Typically gitignored once it grows past a few MB.
2. **`wiki/`** (the working layer) — LLM-generated markdown pages. Papers, topics, entities, events, analyses. This is what humans read and what the agent maintains.
3. **Schema spec** (`AGENTS.md` or `CLAUDE.md`) — the operational contract the LLM reads before doing work. Page types, ingest workflow, wikilink convention, front-matter fields, contradiction handling, lint expectations.

An optional fourth layer sits between `raw/` and `wiki/`:

**`drafts/`** (optional) — LLM scratchpad for long-form synthesis in progress. Use it when a topic needs multiple passes before it is stable enough to live in `wiki/`. Rules:

- Never cross-referenced from `wiki/`; never treated as an authoritative claim source.
- **Promotion** (draft → wiki page): when the draft is stable, all claims trace to a source in `raw/`, and at least one other wiki page would cross-reference it.
- **Prune signal**: drafts unedited across 3 consecutive maintain passes are flagged `[stale-draft]` in `LINT-REPORT.md` for human review. Never auto-deleted.

Worked example: `<wiki-root>/drafts/<slug>.md` — a long-form synthesis drafted across multiple passes before the content stabilized enough to promote to `wiki/`.

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
├── drafts/                # optional scratchpad (never cross-referenced from wiki/)
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

| Variant   | Sources                  | Scripts | Lint              | Profile default | Use when                                                        |
|-----------|--------------------------|---------|-------------------|-----------------|-----------------------------------------------------------------|
| Minimal   | Plain markdown in `raw/` | None    | LLM judgment only | personal        | Bootstrapping, small domain, hand-curated prose. Cleanest start.|
| Middle    | Raw dumps in `raw/<src>/`| None    | LLM-written report| personal        | Bigger corpus, lots of source material, but no need for automation yet. |
| Scripted  | `sources.json` manifest  | Full    | Automated checks  | publishable     | Defined corpus of primary sources, automated ingest desired.    |

### Lint output spectrum

Quick-reference summary of which lint path each variant uses. Full details in §Mode C.

| Variant  | Lint method                        | Report artifact                  |
|----------|------------------------------------|----------------------------------|
| Minimal  | LLM judgment (Mode C.2 checklist)  | `LINT-REPORT.md` in `wiki/`      |
| Middle   | `scripts/lint.py` (stdlib) + LLM judgment (stale claims, contradictions, gaps) | `LINT-REPORT.md` in `wiki/` |
| Scripted | `scripts/lint.py` exit code        | Entry in `log.md` only           |

Pick one path per wiki and keep it. Writing both `LINT-REPORT.md` and a `log.md` entry for the same lint run creates two sources of truth that drift apart across passes.

## The profile axis

`profile:` is a second dimension orthogonal to `variant:`. Where `variant:` describes the automation level, `profile:` describes the publication intent and the defaults the agent applies during scaffold and ingest passes.

| Profile        | Link style      | Front matter        | Lint path               | License tracking          |
|---------------|-----------------|--------------------|-----------------------|--------------------------|
| `personal`    | Relative links  | Optional           | LLM judgment            | Not required             |
| `publishable` | Wikilinks       | Required, full     | Scripted or strict LLM  | Required (`LICENSES.md`) |

Declare the profile in the schema spec alongside `variant:`:

```yaml
variant: middle
profile: personal
```

**Defaults:** `personal` for minimal and middle wikis; `publishable` for scripted wikis. Changeable at scaffold time.

Profile affects defaults, not hard constraints. A `personal` wiki may choose wikilinks; a `publishable` wiki in active development may defer `LICENSES.md`. The profile signals intent so the agent doesn't ask about link style, front-matter requirements, and license tracking on every ingest.

### Profile × variant interactions

| Combo                  | Typical use                                  | Notes                                                                             |
|------------------------|---------------------------------------------|-----------------------------------------------------------------------------------|
| minimal + personal     | Quick bootstrap, private research notes      | Most common starting point for solo research. Front matter optional.              |
| minimal + publishable  | Tiny public corpus                           | Unusual; consider moving to middle if the corpus will grow.                       |
| middle + personal      | Growing personal wiki                        | Good for wikis accumulating raw material without publish pressure.                |
| middle + publishable   | Team wiki, no CI yet                         | Move to scripted when automated lint and license tracking become load-bearing.    |
| scripted + personal    | Personal research with defined paper corpus  | Common shape for deep-dive personal research. `LICENSES.md` optional.            |
| scripted + publishable | Production knowledge base                    | Full pipeline: scripted ingest, automated lint, wikilinks, full license tracking. |

Real-world examples: a `scripted + personal` wiki might be a deep-dive research corpus (full scripted pipeline, personal research notes, not yet published for redistribution); `minimal + personal` wikis are lightweight personal-research folders (flat `raw/`, relative links, LLM lint, front matter absent on most pages).

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
kind: paper | topic | analysis | entity | event | concept | synthesis
---
```

Paper pages add: `url`, `year`, `venue`, `access` (open | paywall | preprint), `license` (CC-BY-4.0 | public-domain | proprietary | …), `topics:` (list of topic slugs).

Topic pages add: `topic: <slug>` (matches the file's id).

Synthesis pages add: `covers:` (list of topic slugs this page synthesizes). See §Synthesis page kind below.

The minimal variant MAY skip front matter on paper pages and let the source filename + a top-of-page summary block carry the metadata; topic pages still benefit from front matter as soon as a linter exists.

### Synthesis page kind

`synthesis` names the most-read pages in a mature wiki: high-level orientation docs, ranked recommendation lists, evidence rubrics, and master corpus indexes. They sit above the per-subdir taxonomy — typically at `wiki/<slug>.md` or at the wiki root — and are linked prominently from the top of `wiki/index.md`.

What a synthesis page holds (pick what fits your domain):

- **Ranked recommendations** — ordered list of interventions, tools, or strategies with one-line rationale each. Worked example: a `longevity/` wiki's `recommendations.md` — ordered intervention list with per-item evidence tier.
- **Evidence rubric** — a scoring ladder applied uniformly across pages (T0-T7 tiers, maturity grades). Worked example: a `longevity/` wiki's `wiki/analysis/evidence-tiers.md` — T0-T7 scoring ladder applied uniformly across pages.
- **Master corpus index** — links to every page in a topic cluster with one-line summaries, for a reader new to the domain. Worked example: a topic-cluster reference page linking 20+ individual topic pages.

**Promotion criteria** — create a synthesis page when any of these fire:

1. A topic or analysis page is cited more than the catalog (`index.md`) in cross-references: it has become the de-facto entry point.
2. An analysis page answers "where do I start?" for a newcomer and has outgrown its analysis subdir.
3. The same orientation paragraph appears in three or more places: consolidate into one synthesis page.

Once created, link the synthesis page from the `## If you're new here` section at the top of `wiki/index.md` (above the per-subdir catalog).

### Cross-references

Two styles work; pick one per wiki and be consistent:

- **Wikilinks**: `[[slug]]` or `[[dir/slug]]`. Parsable by an indexer script. Good when a linter enforces them.
- **Relative markdown links**: `[Title](../topics/foo.md)`. No tooling required. Better for the minimal variant.

External links are always normal markdown `[text](url)`.

### Page length

Favor long, self-contained pages over many stubs. If a topic page is a paragraph plus three wikilinks, merge it into a sibling. Orphan-topic and low-inbound-link signals (from the linter or the LLM's lint pass) surface these.

### Contradiction handling

When two sources disagree on the same claim, the topic page records the disagreement explicitly, names both sources, and either picks the better-supported claim with a one-line rationale or marks the topic `unresolved`. Never silently average or paraphrase away the conflict.

If your domain has no contested claims — a factual catalog with a single authoritative source, or a topic space where sources reinforce rather than contradict — omit this section from your schema spec. The guidance applies only when a domain genuinely produces competing interpretations of the same evidence.

**Worked example — NAD⁺ precursors in a longevity wiki**

Two bodies of evidence pull in opposite directions on the same question: does supplementing NR (nicotinamide riboside) improve health outcomes in humans?

- *Preclinical literature*: NAD⁺ levels decline ~50% by midlife; restoring them via NR or NMN supplementation extends healthspan in mice and worms. The mechanism is established; the translation expectation was that higher NAD⁺ should improve downstream health endpoints in humans.
- *`papers/nr-longcovid-2025`* (eClinicalMedicine, 2025): double-blind RCT, n=58 long-COVID patients, NR 2 g/day for 24 weeks. Blood NAD⁺ rose substantially. Primary endpoints — cognition and symptom recovery — did not change.

**Resolution in `wiki/topics/nad-mitophagy.md`:** The topic page picks the RCT result as the higher-quality evidence class and states the contradiction explicitly: "NAD⁺ precursors (negative on clinical endpoints): Blood NAD⁺ rose reliably; cardiovascular, metabolic, and muscle endpoints are largely null. Recommendation: do not supplement NR/NMN on current evidence." The mechanistic prediction is not discarded — it explains why the hypothesis was plausible — but the clinical endpoint takes precedence over the mechanism. The topic is not marked `unresolved` because the evidence hierarchy makes the decision: RCT > mechanistic prediction.

Apply the same pattern in any domain: name both sources, state why one outranks the other, record the decision, leave the reasoning visible. A future paper that does show clinical benefit can update the resolution in one place.

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

## Extending the schema for your domain

Every wiki past the bootstrap stage benefits from one to three categorical YAML front-matter fields specific to its domain. These extensions turn front matter from passive metadata into a navigation primitive: once a field exists in front matter, `index.md` and synthesis pages can aggregate by it, lint can enforce its presence, and topic pages can sort or filter by its value.

Three examples drawn from real wikis, each invented ad-hoc:

- A `longevity/` wiki — `evidence_tier: T0..T7` (mouse-only to RCT meta-analysis) plus `endpoint: primary_met | primary_not_met | secondary_only | observational | n/a`. Tags every paper with the maturity of its evidence and whether the headline finding was pre-specified.
- An `edge-llm/` wiki — model context length and VRAM-at-context tier, so the index can rank model+quant combinations by what actually fits on a given device.
- An `ai-empowerment/` wiki — maturity, cost, and access tier per tool, so a beginner can filter to free + ready-to-use options.

Each was invented ad-hoc. The pattern below codifies the steps so the next wiki doesn't reinvent it.

### The five-step pattern

1. **Pick 1-3 fields.** Categorical (an enum or a small ordered ladder), not free-text. A field worth adding is one that (a) you would otherwise re-derive on every query, (b) sorts or filters the corpus into useful subsets, and (c) every page in scope can be assigned a value (or `n/a`) without speculative judgement.
2. **Define the values.** Enumerate every value the field can take. Avoid open-ended scales; a 4-7 value ladder is usually right. Write a one-line gloss per value.
3. **Write a rubric synthesis page** at `wiki/<field>-tiers.md` or `wiki/analysis/<field>-tiers.md`, kind `synthesis`. The rubric is the canonical reference: definitions, worked examples per value, within-tier caveats, how the field is assigned during ingest. Cross-reference from every page that uses the field. See §Synthesis page kind.
4. **Document the field in the schema spec** in a `## Domain fields` section using the `domain-fields:` block format below. The block makes the extension visible to the LLM on every read so it doesn't re-derive the convention from scattered paper pages.
5. **Add a lint check** so a missing field on an in-scope page becomes a finding. Minimal/middle: append the check to the Mode C.2 LLM-judgment checklist. Scripted: add a per-field required-when-kind rule to `scripts/lint.py`. Lint surfaces drift; without it, the field rots within a few ingest cycles.

### Anatomy of a good domain field

- **Stable values.** Once a value is published in front matter, renaming it churns every page. Pick names you can live with for the life of the wiki.
- **Assignable from the source alone.** A reviewer should be able to assign the value reading only the source, not the rest of the corpus. Otherwise the field is a synthesis output, not a metadata field.
- **Orthogonal.** Two fields should not be derivable from each other. If `endpoint: primary_met` always implies `evidence_tier >= T6`, drop one.
- **Within-tier quality lives outside the field.** The rubric documents quality dimensions (replication, dose-response, effect size); the front-matter field captures only the tier, not the within-tier verdict.

### Worked example: longevity's `evidence_tier`

The longevity wiki at `longevity/` adds two domain fields. `evidence_tier` is the canonical illustration; `endpoint` follows the same pattern at smaller scope.

**Step 1-2: pick the field and enumerate the values.** An eight-rung ladder from in-vitro to hard-endpoint RCT meta-analysis:

```
T0 — in vitro / cell culture only
T1 — invertebrate lifespan (C. elegans, Drosophila)
T2 — single mouse study, lifespan or healthspan endpoint
T3 — replicated mouse studies; ITP-grade or independent labs
T4 — non-human primate or large mammal
T5 — small human trial (n < 100), surrogate endpoint
T6 — Phase 2/3 human RCT, surrogate endpoint, or large prospective cohort (n>10k) with hard endpoint
T7 — Phase 3 RCT or meta-analysis with hard endpoint (mortality, MACE)
```

**Step 3: rubric synthesis page.** `longevity/wiki/analysis/evidence-tiers.md` is the rubric. It carries the value definitions, worked examples per tier, the "within-tier quality" dimensions (endpoint clarity, effect size, replication, population, confounding, design, dose-response), and the editorial rule for when T2-T3 evidence is accepted vs. rejected. Every paper page links to it.

**Step 4: in paper front matter.** Every paper page in the wiki carries the field:

```yaml
---
id: pearl-rapamycin-2025
title: "PEARL: rapamycin in healthy adults"
kind: paper
url: <url>
year: 2025
venue: Aging
access: open
license: CC-BY-4.0
topics: [rapamycin, clinical-trials]
evidence_tier: T6
endpoint: primary_not_met
---
```

**Step 5: in synthesis-page aggregation.** `longevity/wiki/analysis/evidence-tiers.md` aggregates every intervention's maximum tier reached. The rubric definition (the tier ladder) and the cross-corpus aggregation (which intervention sits where) usually share one synthesis page — `evidence-tiers.md` does both in a single file rather than splitting them across a topic page and a separate rubric.

```markdown
### Tier 7 (mortality/hard-endpoint RCT or meta-analysis)
- **Smoking cessation.** [[papers/jha-2013-smoking-mortality]].
- **Blood pressure control to <120 SBP.** [[papers/sprint-2015-intensive-bp]].
- **Statin therapy.** [[papers/ctt-2012-statins-low-risk]].

### Tier 6 (Phase 2/3 RCT, surrogate endpoint)
- **Vitamin D supplementation.** [[papers/vital-2019-vitd-omega3]]. **Negative result.**
- **Rapamycin (PEARL).** [[papers/pearl-rapamycin-2025]]. **Primary endpoint negative.**
```

The same field also drives the recommendations synthesis page (`longevity/recommendations.md`), which tags every recommended intervention with `(Tier N)` inline, so a reader sees the evidence weight without leaving the page.

**Step 6: in lint.** The longevity `scripts/lint.py` requires `evidence_tier` on every page with `kind: paper`; missing the field is an error. Topic pages without an `evidence_tier` summary that aggregates their linked papers' tiers are a `[review]` finding for human attention.

### Declaring fields in the schema spec

Every wiki declares its domain fields in one block at the top of its schema spec (`AGENTS.md` or `CLAUDE.md`), under a `## Domain fields` heading. The block is YAML-shaped for parsing by future tooling and human-readable today. See the `domain-fields:` template inserted by Mode A.3 below.

## Aggregating by domain field

Once a domain field exists in front matter, it becomes a **navigation axis**: a way to sort, filter, or group pages beyond alphabetical order. This is where the field earns its weight. Without aggregation, a domain field is just metadata; with aggregation, `index.md` and synthesis pages become the structured interface that makes the corpus readable as a body of evidence, not just a list of summaries.

### The feedback loop

```
domain field  →  navigation axis  →  reading path
```

1. **Domain field** (defined per §Extending the schema for your domain): a categorical front-matter field every in-scope page carries (e.g., `evidence_tier: T6`).
2. **Navigation axis**: one or more aggregation views built from that field — grouped listings in `index.md`, tier-sorted sections in a synthesis page, or a filtered table showing only pages that meet a threshold.
3. **Reading path**: when the aggregation consistently guides newcomers ("start at Tier 5+, skip Tier 2"), promote it to a named reading path in the `## If you're new here` section of `index.md`.

The loop closes when a maintain pass detects that a reading path recommendation is stale (the field values on the cited pages have changed) and rewrites the aggregation. The field, the aggregation, and the reading path stay in sync through lint signals: a field missing on a new paper page is a lint error; a reading path citing a retracted tier-assignment is a `[review]` finding.

### Three reference examples

**Example 1 — longevity `evidence_tier` (tier-weighted reading path)**

`longevity/wiki/analysis/evidence-tiers.md` aggregates every intervention by its maximum tier reached. The aggregation is tier-ordered (T7 down to T1), not alphabetical. The recommendations synthesis page (`longevity/recommendations.md`) uses the same axis to sort interventions by evidence weight. The reading path in `index.md` uses the tier as a filter: "If you want only well-powered human evidence, start with Tier 6+ pages."

How the aggregation looks in `index.md` (snippet, commented out in the scaffold template — see §Mode A.5):

```markdown
<!-- domain-field-aggregation: evidence_tier -->
<!--
## By evidence tier (T7 = strongest)

### Tier 7 — hard-endpoint RCT or meta-analysis
- [Smoking cessation](wiki/papers/jha-2013-smoking-mortality.md) — T7; mortality endpoint.
- [Blood pressure control](wiki/papers/sprint-2015-intensive-bp.md) — T7; cardiovascular mortality.

### Tier 6 — Phase 2/3 RCT or large prospective cohort
- [Rapamycin (PEARL)](wiki/papers/pearl-rapamycin-2025.md) — T6; primary endpoint negative.
-->
```

**Example 2 — edge-llm benchmark maturity (maturity-sorted model table)**

An `edge-llm/` wiki could add a `benchmark_maturity` field (enum: `provisional | established | replicated`) to model pages (prospective illustration; the field does not currently exist in the wiki). The aggregation view in `index.md` would be a table sorted by maturity descending, then by VRAM tier ascending — so a reader can find the smallest model with replicated benchmark performance for a given device class. No reading path is warranted here; the maturity axis is a power-user filter, not a newcomer tour.

```markdown
<!-- domain-field-aggregation: benchmark_maturity -->
<!--
## By benchmark maturity

| Model | Maturity | VRAM tier | Notes |
|-------|----------|-----------|-------|
| ... | replicated | 8 GB | |
| ... | established | 4 GB | |
| ... | provisional | 2 GB | |
-->
```

**Example 3 — ai-empowerment cost/access (cost-friction-filtered tool table)**

An `ai-empowerment/` wiki uses a `cost_tier` field on tool pages (prospective illustration; actual wiki values are freeform strings such as `low ($0-20/mo)`, `mid ($499/yr)`, `usage-based ($0.10-0.40/sec)` — a categorical enum like `free | freemium | paid` would be a template suggestion for a new wiki, not the declared enum for an existing wiki). It could also add an `access_tier` field (enum: `no-signup | email | account | waitlist`; prospective illustration — no page in the wiki currently uses this field). The aggregation would be a cross-filtered view: tools that are `free` + `no-signup` or `email` are the lowest-friction entry points. This becomes a reading path: "Start with free, no-signup tools before evaluating paid options."

```markdown
<!-- domain-field-aggregation: cost_tier + access_tier -->
<!--
## By cost and access friction

### Free + immediate access
- [Tool A](wiki/tools/tool-a.md) — free; no signup.
- [Tool B](wiki/tools/tool-b.md) — free; email only.

### Free + friction (account or waitlist)
- [Tool C](wiki/tools/tool-c.md) — free; waitlist.
-->
```

### When to add aggregation

Add an aggregation view the first time you answer a query by mentally sorting the corpus by the domain field. That is the signal that the field has value as a navigation axis. If you never sort by the field, it is passive metadata — useful for lint enforcement, not for navigation.

Promote aggregation to a reading path when the aggregation view is the right "first pass" for a newcomer (not just a power-user filter). Name it and link it from the `## If you're new here` section of `index.md`.

## Adjacent patterns, not wikis

Some artifacts look like wikis but aren't. Scaffolding wiki structure on top of them creates friction with no payoff. Four common patterns that trigger the confusion:

**Comparative-prose set** — a small folder of flat markdown files comparing two or three versions of the same text. Example: a `<comparison-folder>/` containing a handful of files, each a different lens on the same source text. There is no accumulation across sources, no taxonomy, no agent-maintained index. Use instead: a single comparison document or a shared-notes folder. A wiki adds no value when every file is a standalone unit with no cross-references.

**Research-output folder** — a project directory containing notebooks, figures, a draft paper, and submission materials. Example: a `<research-project>/` holding Jupyter notebooks, a published research note, figure outputs, and a `submissions/` directory. The knowledge lives in the notebooks and the paper, not in a curated wiki. Use instead: a code repository or research workspace. Adding `wiki/` and `index.md` would duplicate the paper's narrative without adding anything.

**Project tracker** — a directory of PR drafts, TODO lists, and reference docs tied to active contribution work on external projects. Example: a `<tracker-folder>/` containing `TODO.md`, draft notes, architecture gap analyses, and one-off reference docs per issue. The content is ephemeral and action-oriented, not accumulating. Use instead: a task tracker (plain TODO, Linear, GitHub Issues). A wiki's append-only, cross-referenced structure is wrong for content that gets discarded when the task closes.

**Single-document deep dive** — one long markdown file synthesizing a topic from scratch. The depth is real, but the source set is one document or one sitting. Use instead: write the document. A wiki earns its overhead when there are 5+ sources and future ingests are expected; a solo synthesis page is just a document.

**Quick test:** "Will this artifact accumulate knowledge across many sources over time, maintained by an agent?" If the honest answer is no, don't scaffold a wiki. If the user insists, explain the mismatch and scaffold the minimal variant if they still want to proceed.

## Mode A: scaffold a new wiki

**Before scaffolding, answer one question: "Is this prose knowledge accumulated from many sources that an agent will maintain over time?"** If no — it's a research-project folder, a text-comparison set, a project tracker, or a one-time synthesis — redirect to §Adjacent patterns, not wikis instead of scaffolding.

The user passes `scaffold <wiki-root> [--variant minimal|middle|scripted]`. If `--variant` is omitted, default to **minimal** and tell the user; prompt to switch only if the user explicitly mentions a defined corpus or automated lint.

### A.1 — confirm the variant + subdir taxonomy

Before writing anything, restate the plan back to the user in 3-4 lines:

```
About to scaffold <variant> wiki at <wiki-root> with subdirs:
  - wiki/<sub-1>/  (<purpose>)
  - wiki/<sub-2>/  (<purpose>)
Schema spec: <AGENTS.md|CLAUDE.md>
Profile: <personal|publishable>
Wikilink style: <wikilinks|relative>
Confirm or correct.
```

Pick the schema name based on the harness: `CLAUDE.md` if the user is on the Claude Code harness (auto-loaded), `AGENTS.md` otherwise. Pick the subdir taxonomy by asking the user one question: "What kinds of pages will this wiki hold?" Map common answers:

- "Papers and concepts" → `papers/`, `topics/`, `analysis/`
- "Things, people, events" → `entities/`, `events/`, `concepts/`, `culture/`
- "Cases and statutes" → `cases/`, `statutes/`, `commentary/`
- "Products and companies" → `products/`, `companies/`, `categories/`

If unclear, default to `papers/`, `topics/`, `analysis/` and explain the user can rename later.

Confirm the profile before writing the schema spec. Default is `personal` for minimal and middle wikis (relative links, front matter optional, LLM lint, no `LICENSES.md`) and `publishable` for scripted wikis (wikilinks, full front matter, scripted lint, `LICENSES.md`). Let the user override. Record the chosen profile as `profile: <personal|publishable>` in the schema spec alongside `variant:`, at the top of the spec before any section headings. See §The profile axis for the full interaction matrix.

### A.2 — create the directory tree

```bash
mkdir -p <wiki-root>/{raw,wiki/<sub-1>,wiki/<sub-2>,wiki/<sub-3>}
# scripted variant only:
mkdir -p <wiki-root>/{sources/html,sources/pdf,sources/md,wiki/build,scripts}
```

Create a `drafts/` directory with a one-line README (all variants):

```bash
mkdir -p <wiki-root>/drafts
echo "# Drafts\n\nLLM scratchpad for in-progress synthesis. Never cross-referenced from wiki/. Promote to wiki/ when stable and fully sourced." > <wiki-root>/drafts/README.md
```

### A.3 — write the schema spec

The schema spec is the contract the LLM reads on every future invocation. Keep it short — everything the LLM needs, nothing it can infer from examples. Required sections:

1. **Structure** — the directory tree and what each subdir holds.
2. **Page format** — the YAML front-matter block + the body sections each page kind requires.
3. **Naming conventions** — slug rules.
4. **Wikilink convention** — wikilinks vs relative links; one or the other, not both.
5. **Workflows** — `Ingest`, `Query`, `Lint` (each with numbered steps).
6. **Writing style** — concrete rules. Examples: "no em dashes; use colons or commas instead", "no hedging language (`I believe`, `perhaps`, `it seems`)", "every claim cites a file in `raw/`".
7. **Domain fields** (optional, add when the wiki has one or more domain-specific categorical fields) — declares the extensions in one place so every future invocation sees them. See §Extending the schema for your domain for the full pattern and worked example. The block format:

   ````markdown
   ## Domain fields

   This wiki extends the standard schema with these YAML front-matter fields:

   ```yaml
   domain-fields:
     <field-name>:
       type: enum
       values: [<v1>, <v2>, ...]
       applies-to: [paper, topic, synthesis]   # which page kinds carry the field
       required-when: [paper]                   # which page kinds error if missing
       rubric: wiki/analysis/<field>-tiers.md   # synthesis page documenting the values
       gloss: "<one-line description of what the field captures>"
   ```

   Example (longevity):

   ```yaml
   domain-fields:
     evidence_tier:
       type: enum
       values: [T0, T1, T2, T3, T4, T5, T6, T7]
       applies-to: [paper, topic, synthesis]
       required-when: [paper]
       rubric: wiki/analysis/evidence-tiers.md
       gloss: "Maturity ladder: in vitro (T0) through hard-endpoint RCT meta-analysis (T7)."
     endpoint:
       type: enum
       values: [primary_met, primary_not_met, secondary_only, observational, n/a]
       applies-to: [paper]
       required-when: [paper]
       rubric: wiki/analysis/evidence-tiers.md
       gloss: "Whether the paper's primary endpoint was pre-specified and met."
   ```
   ````

   Skip this section entirely if the wiki uses only the standard fields. Add it the first time you introduce a domain field; update it when you add another.

A starting template (adapt per domain):

```markdown
variant: <minimal|middle|scripted>
profile: <personal|publishable>

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

If the wiki will grow beyond a few dozen pages, add a `## Reading paths` section to the schema spec (after the Workflows block). Document one or more ordered tours for newcomers — 3 to 7 steps, one line of rationale each. Example:

```markdown
## Reading paths

### Grok the field
A suggested reading order for someone starting from scratch.
1. [[topics/<orientation-topic>]] — big picture
2. [[topics/<methods-topic>]] — how the work is done
3. [[analysis/<key-synthesis>]] — what the evidence shows
```

The agent updates tours during maintain passes as the wiki matures. A wiki with no reading path is still valid; add this only when you have 10+ pages and a clear newcomer journey.

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

## If you're new here, read in this order

_(add 3-7 steps with one-line rationale each after your first few pages land)_

## <Sub-1>

_(no entries yet)_

## <Sub-2>

_(no entries yet)_

<!-- domain-field-aggregation — uncomment after adding a domain field per §Extending the schema for your domain -->
<!--
## By <field-name> (<value-1> = <meaning>)

### <value-1>
- [<Page title>](wiki/<subdir>/<slug>.md) — <one-line context>.

### <value-2>
- [<Page title>](wiki/<subdir>/<slug>.md) — <one-line context>.
-->
```

### A.5a — optional: source-papers table

For wikis where provenance at a glance matters, close `wiki/index.md` with a `## Source papers` table listing every ingested source. The agent appends one row per ingest; the human can scan the full corpus without opening individual paper pages.

Columns: **Paper | Authors | Venue | Year**

```markdown
## Source papers

| Paper | Authors | Venue | Year |
|-------|---------|-------|------|
| <Title> | <First author> et al. | <Venue> | <Year> |
```

See the worked example in §A.5b for the table shape. A wiki with 30+ paper pages benefits immediately from this table — the corpus is scannable without navigating into subdirs.

Add this table when: the wiki has 5+ paper pages and readers benefit from seeing the full source set without navigating into subdirs. Skip for topic-only wikis with few or no paper pages.

### A.5b — optional: synthesis-page template

For wikis where a high-level orientation page, ranked list, or rubric would be the most useful starting point, drop a synthesis-page template into the wiki root (not inside a subdir). Add this during scaffold if you already know the shape of the synthesis; add it later when the promotion criteria in §Synthesis page kind fire.

Template:

```markdown
---
id: <slug>
title: "<human title>"
kind: synthesis
covers: [<topic-1>, <topic-2>]
---

# <Title>

> **TL;DR:** One to three sentences. What this page answers, who it's for, and the key takeaway.

## Ranked recommendations (or: rubric / master index)

1. **<Item>** — <one-line rationale>. Source: [[analysis/<slug>]].
2. **<Item>** — <one-line rationale>. Source: [[papers/<slug>]].

## How to read this page

<Optional: explain the ranking or scoring system in two to four sentences.>

## Sources

- [[papers/<slug>]] — <one-line context>
- [[analysis/<slug>]] — <one-line context>
```

Worked examples: `longevity/recommendations.md` (ranked interventions with T0-T7 evidence tier tags), `longevity/wiki/analysis/evidence-tiers.md` (uniform evidence rubric), a topic-cluster reference page (master corpus index linking 20+ topic pages).

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

### A.6.5 — middle variant only: drop the lint.py template

For the middle variant, create `scripts/lint.py` from the template below. This gives the wiki fast, deterministic link-checking and front-matter enforcement without the full scripted-variant infrastructure (no `sources.json`, no download/convert/index pipeline). Skip for minimal wikis (use LLM judgment only). Skip for scripted wikis (they already have a fuller `lint.py` per §Scripts reference).

```bash
mkdir -p <wiki-root>/scripts
```

Template (stdlib only, no pip installs required):

```python
#!/usr/bin/env python3
"""Middle-variant wiki lint — stdlib only.
Usage: python3 scripts/lint.py [wiki-root]  (default: .)
Checks: broken relative links, missing index entries, orphan pages,
        unlinked paper pages, front-matter fields, empty pages.
Exit 0 on clean, 1 on errors.
"""
import re, sys
from pathlib import Path

WIKI_DIR = "wiki"
INDEX = "wiki/index.md"
REQUIRED_FIELDS = {"id", "title", "kind"}
KINDS = {"paper", "topic", "analysis", "entity", "event", "concept", "synthesis"}

def parse_front_matter(text):
    if not text.startswith("---"): return {}
    end = text.find("\n---", 3)
    if end == -1: return {}
    fields = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m: fields[m.group(1)] = m.group(2).strip()
    return fields

def wiki_pages(root):
    skip = {"index.md", "LINT-REPORT.md"}
    return {str(p.relative_to(root)): p
            for p in (root / WIKI_DIR).rglob("*.md") if p.name not in skip}

def rel_links(text):
    return [m.split("#")[0].strip()
            for m in re.findall(r"\[[^\]]*\]\(([^)#]+\.md[^)]*)\)", text)]

def check_broken_links(root, pages):
    errs = []
    for rel, absp in pages.items():
        for link in rel_links(absp.read_text(errors="replace")):
            if not (absp.parent / link).resolve().exists():
                errs.append(f"[broken-link] {rel}: '{link}'")
    return errs

def check_index(root, pages):
    idx = root / INDEX
    if not idx.exists():
        return [f"[missing-index] {INDEX} not found"]
    body = idx.read_text(errors="replace")
    return [f"[missing-index-entry] {r}"
            for r in pages if Path(r).stem not in body and Path(r).name not in body]

def check_orphans(root, pages):
    linked = set()
    for p in list(pages.values()) + [root / INDEX]:
        if p.exists():
            for link in rel_links(p.read_text(errors="replace")):
                t = (p.parent / link).resolve()
                for rel, absp in pages.items():
                    if absp.resolve() == t: linked.add(rel)
    return [f"[orphan] {r}: no inbound links" for r in pages
            if r not in linked
            and parse_front_matter(pages[r].read_text(errors="replace")).get("kind") == "topic"]

def check_front_matter(root, pages):
    errs = []
    for rel, absp in pages.items():
        fm = parse_front_matter(absp.read_text(errors="replace"))
        for f in REQUIRED_FIELDS:
            if f not in fm: errs.append(f"[missing-front-matter] {rel}: '{f}'")
        if "kind" in fm and fm["kind"] not in KINDS:
            errs.append(f"[bad-kind] {rel}: '{fm['kind']}'")
    return errs

def check_empty(root, pages):
    errs = []
    for rel, absp in pages.items():
        text = absp.read_text(errors="replace")
        body = text[text.find("\n---", 3) + 4:] if text.startswith("---") else text
        if len(body.strip()) < 50:
            errs.append(f"[empty-page] {rel}")
    return errs

def check_unlinked_papers(root, pages):
    """Paper pages (kind:paper) that no topic page links to."""
    paper_pages = {rel: absp for rel, absp in pages.items()
                   if parse_front_matter(absp.read_text(errors="replace")).get("kind") == "paper"}
    if not paper_pages:
        return []
    topic_pages = [absp for rel, absp in pages.items()
                   if parse_front_matter(absp.read_text(errors="replace")).get("kind") == "topic"]
    linked = set()
    for tp in topic_pages:
        if tp.exists():
            for link in rel_links(tp.read_text(errors="replace")):
                t = (tp.parent / link).resolve()
                for rel, absp in paper_pages.items():
                    if absp.resolve() == t:
                        linked.add(rel)
    return [f"[unlinked-paper] {r}: no topic page links here" for r in paper_pages if r not in linked]

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not (root / WIKI_DIR).exists():
        sys.exit(f"error: no {WIKI_DIR}/ at {root}")
    pages = wiki_pages(root)
    errs = (check_broken_links(root, pages) + check_index(root, pages) +
            check_orphans(root, pages) + check_unlinked_papers(root, pages) +
            check_front_matter(root, pages) + check_empty(root, pages))
    for e in errs: print(e)
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
```

After dropping the template, verify it exits 0 against the empty scaffold:

```bash
cd <wiki-root> && python3 scripts/lint.py
```

An empty wiki (no pages yet) has nothing to check and should exit 0. If it errors, the template has a path bug — fix before declaring scaffold done.

During **maintain passes** on a middle-variant wiki: run `python3 scripts/lint.py` first to get the deterministic findings (broken links, missing front matter, orphans, unlinked papers, index drift, empty pages), then apply LLM judgment for the fuzzy checks that the script cannot perform (stale claims, contradiction handling, gaps in coverage). Incorporate all findings into `LINT-REPORT.md`.

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
# drafts/ — uncomment to exclude from version control (default: committed)
# drafts/
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

Before touching any wiki page, read `<wiki-root>/AGENTS.md` (or `CLAUDE.md`) end-to-end. Note: page kinds, subdir taxonomy, wikilink style, required front-matter fields, contradiction handling, writing style, profile: (if present, apply §The profile axis defaults for link style and front-matter requirements). The schema is authoritative; if your defaults conflict with it, the schema wins.

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

### B.9 — commit (mandatory; do not skip or defer)

**The ingest is not complete until this commit lands. Do not output "ingest complete" before running this step.**

Stage and commit everything that changed:

```bash
cd <wiki-root>
git add raw/<slug>.md wiki/papers/<slug>.md wiki/topics/ wiki/index.md log.md
# scripted variant also: git add sources.json wiki/build/ LICENSES.md
git commit -m "<wiki-name>: ingest <slug> — <one-line of what it adds>"
```

Verify with `git log --oneline | head -1` that a new commit exists before declaring done. If not, diagnose and retry.

## Mode C: maintain (lint pass)

The user passes `maintain <wiki-root> [--lint]`. Lint surfaces drift the agent should fix.

### C.1 — read the schema spec

Same as B.1.

### C.2 — run the lint checks

**Minimal variant** — LLM walks the wiki and checks:

1. **Broken cross-references.** Walk every relative link or wikilink; flag targets that don't exist.
2. **Orphan topic pages.** Topics with no inbound links from any paper or analysis page.
3. **Papers nothing links to.** Paper pages that no topic mentions.
4. **Missing front matter.** Pages without the required fields per the schema.
5. **Index drift.** Pages in `wiki/` not listed in `index.md`, or vice versa.
6. **Stale claims.** Claims contradicted by a newer source. (LLM judgment; flag for human review rather than auto-fix.)
7. **Contradiction handling.** Topics with multiple sources making incompatible claims that the topic page hasn't surfaced.
8. **Gaps.** Topics referenced repeatedly across paper pages with no dedicated topic page.
9. **Variant boundary.** If the schema spec declares a `variant:` field (or describes itself as scripted / middle / minimal), check that the directory structure matches the claim: scripted requires `sources.json`; middle requires `raw/` with per-source subdirectories (not a flat `raw/`); minimal has flat `raw/` or no `raw/`. A mismatch — e.g., `variant: middle` in a wiki without `raw/` subdirs, or `variant: scripted` without `sources.json` — is a `[review]` finding. Do not auto-fix; flag for the human to clarify whether the variant label or the directory structure should change.

**Middle variant** — run `scripts/lint.py` first (if present) for the deterministic subset of checks (items 1-5 above), then apply LLM judgment for the fuzzy checks (items 6-8). Incorporate all findings into `LINT-REPORT.md`.

```bash
python3 scripts/lint.py
```

**Scripted variant** — additionally:

```bash
python3 scripts/lint.py
```

…which exits non-zero on broken wikilinks, missing front-matter fields, orphan topics, parity mismatches between `sources.json` and `wiki/papers/`, malformed URLs, and missing licenses.

### C.3 — produce a lint report

**Minimal and middle variants**: write `<wiki-root>/wiki/LINT-REPORT.md` (or append with a date header). Group findings by category. For each finding: file path, line if applicable, one-line description, suggested fix. Mark each finding `[auto]` (safe to apply automatically) or `[review]` (needs human judgment).

**Scripted variant**: the `lint.py` exit code is the report. Record the result in `log.md` only (`YYYY-MM-DD LINT: <N> errors, <M> warnings`). Do not write `LINT-REPORT.md` for scripted wikis.

Pick one path per wiki and keep it. Writing both creates two sources of truth that drift apart across passes.

### C.4 — apply auto-safe fixes

Apply only `[auto]` findings (broken-link slug typos, missing front-matter scaffolding, index entries for already-existing pages). Leave `[review]` findings in the report for the human.

### C.5 — append to log.md

```
YYYY-MM-DD LINT: <N> findings; <M> auto-applied; <K> for review. See LINT-REPORT.md.
```

### C.6 — commit

One commit: `<wiki-name>: lint pass — <one-line summary>`.

## Mode D: umbrella (parent-dir index)

The user passes `umbrella <parent-dir>`. Mode D is for three or more sibling wikis under a shared parent directory; it writes a single master index at the parent level without merging the individual wikis.

Worked example: a `research/` directory holds five wikis (`longevity/`, `bpu/`, `aliens/`, `edge-llm/`, `ai-empowerment/`). Running `umbrella research/` produces `research/index.md` with one row per detected wiki.

### D.1 — walk sibling wikis

Walk `<parent-dir>` up to two levels deep. A directory qualifies as a wiki when it contains both:
- a `wiki/index.md` (or `wiki/` subdir with `index.md`), AND
- at least one schema spec (`AGENTS.md` or `CLAUDE.md`).

Skip directories that don't meet both criteria. For each qualifying directory, collect:

- **Name**: the path relative to `<parent-dir>` (e.g., `aliens`, `comsci/edge-llm`).
- **Variant**: infer from directory structure — `scripts/lint.py` + `sources.json` both present → scripted; `scripts/lint.py` present alone → middle; `raw/` with subdirectories → middle; otherwise minimal.
- **Page count**: count `*.md` files under `wiki/`, excluding `index.md`, `LINT-REPORT.md`, and anything under `wiki/build/`.
- **Last-ingest date**: the most recent `YYYY-MM-DD INGEST:` line in `log.md`, or the most recent file modification date under `wiki/` if `log.md` is absent or has no INGEST line.
- **One-line description**: the first non-blank, non-heading paragraph of `README.md`, trimmed to 80 characters. Fall back to the first sentence of the schema spec's opening paragraph if no README exists.

### D.2 — write the umbrella index

Write or refresh `<parent-dir>/index.md` using the template in §D.3. If the file already exists, locate the `<!-- umbrella-index: auto-generated, do not hand-edit below -->` sentinel and overwrite everything from that line through the end of the table (the last `|` row). Preserve any human-written prose above the sentinel.

### D.3 — umbrella-index template

```markdown
# <parent-dirname> wikis

_Last refreshed: YYYY-MM-DD._

<!-- umbrella-index: auto-generated, do not hand-edit below -->
| Wiki | Variant | Pages | Last ingest | Description |
|------|---------|-------|-------------|-------------|
| [<name>](./<name>/wiki/index.md) | <variant> | <n> | <YYYY-MM-DD> | <one-line> |
```

Each row's **Wiki** column links directly to the wiki's `wiki/index.md`. Sort rows alphabetically by name. For nested wikis (e.g., `comsci/edge-llm`), the link path is `./comsci/edge-llm/wiki/index.md`.

### D.4 — append to parent log.md (if present)

If `<parent-dir>/log.md` exists, append one line:

```
YYYY-MM-DD UMBRELLA: refreshed index.md; N wikis indexed (<name-1>, <name-2>, ...).
```

If no parent `log.md` exists, skip this step — Mode D does not create a parent `log.md`.

### D.5 — commit

One commit from `<parent-dir>`:

```bash
git add index.md log.md
git commit -m "<parent-dirname>: umbrella index refresh — N wikis"
```

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
- `lint.py` — exit 0 on success, 1 on errors. Checks: front-matter required-fields, slug ↔ filename match, wikilink target exists, `sources.json` ↔ `wiki/papers/` parity, `topics:` references existing topic pages, license-required-when-committed-source, declared-variant ↔ directory-structure match (`sources.json` required for scripted; `raw/<src>/` subdirs for middle; flat `raw/` for minimal).
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

- Minimal/middle: `LINT-REPORT.md` is written with all findings categorized.
- Scripted: lint result recorded in `log.md` only; no `LINT-REPORT.md`.
- All `[auto]` findings are applied.
- `log.md` has the new LINT entry.
- The change is committed in one commit.
