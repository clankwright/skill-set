---
name: sst-fact-checker
description: Verify a list of factual claims via web search. For each claim, runs targeted searches, visits the most relevant pages, and decides verified / corrected / unverified with cited sources. Produces a structured Fact Checking Report grouped by outcome. Designed to be called by a higher-level editorial loop OR run standalone on a list of claims a human or upstream agent supplies.
user-invocable: true
version: 1.0.1
model-floor: haiku
effort-floor: medium
argument-hint: [list of claims (one per line) or path to a claims file]
---

# Fact checker

Given a batch of claims, decide which are supported, which need correction, and which can't be verified — with citations for every decision.

## Project contract

- **Output dir**: `<project>/data/sst-fact-checker/` by default. Reports as `<utc>_<batch-hash>.md`.
- **Tools required**: harness's `WebSearch` and `WebFetch`.
- **Input shape**: either a newline-separated list of claims, or a structured list of `(claim, source-url)` pairs when the upstream agent already proposed sources.

## Operating principles

- **Be neutral.** Your job is to verify, not to advocate. A claim that turns out to be wrong gets reported as wrong; a claim that's hard to verify gets reported as unverified — don't tilt either way.
- **Multi-source for "verified".** A single hit on a low-trust page is not enough to call something verified. Aim for two independent authoritative sources before stamping "verified."
- **Quote the correction.** When you mark a claim as needing correction, write the corrected statement in the report. Don't just say "this is wrong."
- **404 / irrelevant url = unverified.** If the upstream agent provided a source URL but the page is missing or off-topic, the claim is unverified (even if the claim itself sounds plausible).

## 1. Read the input

Parse the input into a list of claims. If the input is a file path, read the file. If it's a paragraph of prose, extract individual factual sentences first.

For each claim, decide whether it's:
- A **standalone fact** (e.g. "Python 3.12 was released in October 2023").
- A **claim with provided source** (e.g. `("X happened", "https://example.com/article")`).
- A **compound claim** that should be split into atoms before verifying (split it).

## 2. Plan the searches

Group related claims that can share search terms (e.g. multiple stats from the same study). For each group, devise the search query most likely to surface authoritative sources:

```
WebSearch: "<exact phrase from the claim>"
WebSearch: <topic terms> site:<authoritative domain>
WebSearch: <topic> filetype:pdf      # for studies, reports
```

Useful operators:
- `"..."` exact phrase
- `-` exclude
- `site:` scope to a domain
- `-site:` exclude a domain (drop low-trust sources)
- `intitle:` / `inurl:` for targeted hits

## 3. Verify each claim

For each claim, fetch the top results until you have enough to decide:

```
WebFetch: <url>  // Find evidence about: <the claim>
```

Decision rules:
- **Verified**: ≥2 independent authoritative sources support it. (For a claim with a provided source URL, that source counts as one; you still need one independent corroboration unless the source IS the primary record — e.g. an official announcement.)
- **Corrected**: Authoritative sources contradict the claim or show it's misstated. Write the corrected statement.
- **Unverified**: You can't find authoritative support OR sources are contradictory. Be explicit about which.

Don't grade claims more harshly than the evidence justifies. A claim that's "mostly right but with a date off by a year" is `corrected`, not `unverified`.

## 4. Produce the report

Write to `<project>/data/sst-fact-checker/<utc>_<batch-hash>.md`:

```markdown
# Fact Checking Report — <utc>

**Batch**: <N> claims  ·  **Verified**: <V>  ·  **Corrected**: <C>  ·  **Unverified**: <U>

## Verified Claims

- **Claim**: <the original claim, quoted verbatim>
  - Sources: [url1], [url2]
  - Notes: <optional one-line context, e.g. "primary source + 1 independent corroboration">

- ...

## Corrected Claims

- **Claim**: <the original claim>
  - Correction: <the corrected statement, written precisely>
  - Sources: [url1], [url2]
  - Notes: <optional, e.g. "off by 1 year; the actual date is X per the official release notes">

- ...

## Unverified Claims

- **Claim**: <the original claim>
  - Reason: <one of: "no authoritative source found"; "sources contradict each other"; "provided URL was 404 / off-topic"; "topic too recent / too obscure for available sources">
  - What I tried: <2-3 search terms attempted>

- ...
```

Report the file path as the final line of your response.

## Hard rules

- **No fabricated sources.** Every URL in the report was actually fetched.
- **No fabricated corrections.** A "correction" needs a source backing the new statement.
- **Don't add safety/ethics commentary.** The sst-fact-checker reports facts; editorial framing belongs to the calling skill.
- **Don't refuse claims based on topic.** If the claim is checkable, check it. If it's a value judgment ("X is the best Y"), mark it unverified with a "this is opinion, not fact" note — don't refuse.
