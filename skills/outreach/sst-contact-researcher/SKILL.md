---
name: sst-contact-researcher
description: Deep-research one cold-outreach contact (person + firm) into a structured intel brief. Fetches source pages, extracts a dated personalization hook, verifies the published email, and maps audience/pain — does not draft or send email. Upstream of sst-outreach-writer-editor in the contact-research-and-write chain.
user-invocable: true
version: 1.2.0
argument-hint: [ignored when seed.json present — prefer bin/prepare-intel-seed.py]
---

# Contact researcher

One invocation = one contact. Search → fetch → verify → synthesize an intel brief the writer can turn into a personalized cold email. Inspired by `sst-web-research` (cite what you fetch) and `sst-lead-generation` (no-guessing verification). This skill stops at intel; drafting belongs downstream.

## Project contract

- **Input (programmatic)**: `<project>/data/sst-contact-researcher/seed.json` written by the project's prepare/claim driver **before** this skill runs. Required keys: `company`, `audience`; preferred: `to`, `first_name`, `source_url`, `template`, `source`. Do **not** claim queue rows, write seed files, or invoke apply scripts from this skill — that is driver work.
- **Output dir**: `<project>/data/sst-contact-researcher/`.
  - **Always** write `latest.md` (overwrite) — this is the only handoff the writer reads.
  - Also write a dated archive `<utc>_<company-slug>.md`.
- **Tools required**: `WebSearch`, `WebFetch` (Playwright MCP for JS-heavy pages). No SMTP send. No queue/claim/apply scripts.
- **Downstream**: `sst-outreach-writer-editor` reads `latest.md` only (no path-passing in prompts).

## Operating principles

- **One contact, real depth.** Prefer one richly researched lead over five thin ones.
- **Never guess emails.** Same bar as `sst-lead-generation`: published on the firm's own site / byline / press, or a published generic mailbox (`info@`, `contact@`, …). Drop ZoomInfo / RocketReach / Hunter / Apollo / Buzzfile / pattern guesses.
- **Dated hook or drop.** If you cannot find a specific, dated, public fact to open an email with, mark `hook_quality: weak` and say why — do not invent one.
- **Freshness (>12 months = stale).** Prefer hooks dated within the last **12 months** relative to today. A fact older than 12 months (or clearly "ancient history" awards/press from prior calendar years with no newer signal) is **stale**: do not promote it as the opener hook. Keep searching for something newer; if nothing fresher exists, set `hook_quality: weak` (or `adequate` only if pain signals are strong) and record the old fact under Firm context — never as `## Dated hook` for the writer to congratulate. Undated website boilerplate is not a dated hook.
- **Bias search toward recent.** Include the current year (and prior year only as fallback) in queries; prefer news/press/awards pages with explicit dates over evergreen About pages.
- **Synthesize for the writer, not the reader.** The intel brief is an internal artifact; plain facts + URLs, not marketing copy.
- **Cite every claim.** Every factual line carries the URL you fetched.
- **No data-plumbing in prompts.** Queue claim, seed.json write, Drafts apply, and path handoff are owned by `bin/` drivers. This skill only researches and writes `latest.md`.

## 1. Resolve the target

Read `data/sst-contact-researcher/seed.json`. If missing, abort with a clear error (driver must prepare it). Lock:

| Field | Required |
|---|---|
| Company name | yes (`company`) |
| Audience class | yes (`audience`) |
| Source URL | preferred (`source_url`) |
| Named person + title | if in seed / published |
| Candidate email | if in seed (`to`) |

If the proprietary ICP filter rejects the firm (wrong vertical), print `[skip] <reason>` and exit 0 **without** writing `latest.md` (leave any prior latest untouched).

## 2. Search and fetch

Minimum fetches (skip only if the proprietary already supplied a verified equivalent):

1. **Source page** that put them on the list (case study, spotlight, testimonial, directory profile).
2. **Firm website** — About / Team / Contact.
3. **One corroborating page** (press, association profile, LinkedIn company About if public).

Scratch lists while reading:

- **Facts** (with URL each)
- **Pain signals** (quotes or paraphrases tied to the product category)
- **Open questions** (next search term)

Iterate until you have a dated hook OR you can honestly mark the hook weak.

## 3. Verify the email

Apply the lead-gen verification bar. Record in the brief:

- `email` — the address you will recommend
- `email_kind` — `named` | `generic` | `none`
- `email_verification_url` — page where it is published
- If `none`: still write the intel (writer may produce a LinkedIn/InMail variant) but set `send_ready: false`

## 4. Write the intel brief

Write the brief body using the schema below to **both**:

1. `<project>/data/sst-contact-researcher/latest.md` (overwrite — writer handoff)
2. `<project>/data/sst-contact-researcher/<utc>_<company-slug>.md` (archive)

```markdown
# Contact intel — <Company>

- researched_at: <utc-iso>
- audience: <audience class from proprietary>
- send_ready: <true|false>
- hook_quality: <strong|adequate|weak>

## Contact
- company: ...
- person: <First Last | unknown>
- title: ...
- email: ...
- email_kind: named|generic|none
- email_verification_url: ...
- company_domain: ...
- company_url: ...

## Dated hook (for email opener)
- hook: <one sentence the writer can paste almost verbatim — MUST be ≤12 months old>
- hook_date: <YYYY-MM or YYYY-MM-DD or "undated">
- hook_freshness: <fresh|stale|undated>  # fresh = within last 12 months; stale = older
- hook_source_url: ...
- hook_quote: <optional short quote from the source>

If the best public fact is stale, omit a strong Dated hook (leave hook_quality weak/adequate via pain only) and optionally note the old fact under Firm context as `stale_context`, not as the opener.

## Audience & pain
- audience_notes: <what this person cares about day-to-day>
- pain_signals:
  - <signal> ([source](url))
- why_us_fit: <1-3 sentences tying pain to the product category — no feature dump>

## Firm context
- size_proxy: <revenue band / headcount / bonded / other observable>
- stack_signals: <accounting/PM tools mentioned, if any>
- geography: ...

## Do not say
- <landmines: competitors they love, wrong product assumptions, banned claims>

## Sources
- [title](url) — <one-line contribution>
```

## 5. Report

Human-readable summary only (not a data handoff — the writer reads `latest.md`):

```
Intel: data/sst-contact-researcher/latest.md
send_ready: <true|false>
hook_quality: <strong|adequate|weak>
```

## Hard rules

- **No fabricated URLs or quotes.** If you didn't fetch it, it is not in the brief.
- **No email pattern guesses.** Unverifiable → `email_kind: none`, `send_ready: false`.
- **No email draft in this skill.** Subject/body belong to `sst-outreach-writer-editor`.
- **No send / claim / apply / seed writes.** Research + `latest.md` only.
- **Weak hook is honest.** Prefer `hook_quality: weak` over a fake "Saw your website" opener.
- **No stale openers.** Never set `hook_quality: strong` for a hook_date older than 12 months.
