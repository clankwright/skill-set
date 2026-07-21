---
name: sst-outreach-research-and-write
description: Deep-research one cold-outreach contact and draft a motivating plain-text email in a single agent session. Replaces the former sst-contact-researcher + sst-outreach-writer-editor handoff. Does not claim queue rows, write seed.json, or apply Drafts — project drivers own that.
user-invocable: true
version: 1.0.0
model-floor: opus
effort-floor: high
argument-hint: [ignored when seed.json present — prefer project bin/prepare-intel-seed.py]
---

# Outreach research-and-write

One invocation = one contact. Search → fetch → verify → intel brief → draft → self-edit → sendable JSON. Inspired by `sst-web-research` (cite what you fetch), `sst-lead-generation` (no-guessing verification), `sst-iterative-writer` (iteration), and `sst-editorial-pass` (structured passes).

**No agent handoff.** Do not stop after intel and wait for another skill. Research and writing happen in this same session.

## Project contract

- **Input (programmatic)**: `<project>/data/sst-contact-researcher/seed.json` written by the project's prepare/claim driver **before** this skill runs. Required keys: `company`, `audience`; preferred: `to`, `first_name`, `source_url`, `template`, `source`. Do **not** claim queue rows, write seed files, or invoke apply scripts from this skill — that is driver work.
- **Intel dir** (audit / debug): `<project>/data/sst-contact-researcher/`.
  - Always write `latest.md` (overwrite) after research, plus dated archive `<utc>_<company-slug>.md`.
- **Draft dir** (driver reads this): `<project>/data/sst-outreach-writer-editor/`.
  - Always write `latest.md`; when `status=ready`, also `latest.json` (overwrite) plus dated archives.
- **Required from the proprietary counterpart** (when present): ICP filter, audience classes, product one-liner, proof/demo URL, sender sign-off, audience angles, subject/body bans, CTA options, max word count, preferred source channels.
- **Tools**: `WebSearch`, `WebFetch` (Playwright MCP for JS-heavy pages), `Read`, `Write`. No SMTP. No claim/apply/seed scripts.

## Operating principles

- **One contact, real depth.** Prefer one richly researched lead over five thin ones.
- **Never guess emails.** Published on the firm's own site / byline / press, or a published generic mailbox (`info@`, `contact@`, …). Drop ZoomInfo / RocketReach / Hunter / Apollo / Buzzfile / pattern guesses.
- **Dated hook or pain.** Prefer a specific, dated, public fact ≤12 months old. If none, mark `hook_quality: weak` and open on current pain — do not invent a hook or congratulate stale awards.
- **Bias search toward recent.** Include the current year (prior year only as fallback); prefer news/press/awards with explicit dates over evergreen About pages.
- **Cite every claim.** Every factual intel line carries the URL you fetched.
- **Motivation > feature list.** Lead with their pain and the outcome they want. Product mechanics earn one short paragraph max.
- **Short.** Default ≤120 words body (proprietary may tighten). Over 200 words is a hard fail.
- **One CTA.** Never dual-ask. Plain text only — no HTML, images, tracking pixels, or markdown links in the sendable body.
- **No data-plumbing.** Queue claim, seed.json, Drafts apply are driver responsibilities.

---

## Part A — Research

### A1. Resolve the target

Read `data/sst-contact-researcher/seed.json`. If missing, abort with a clear error. Lock:

| Field | Required |
|---|---|
| Company name | yes (`company`) |
| Audience class | yes (`audience`) |
| Source URL | preferred (`source_url`) |
| Named person + title | if in seed / published |
| Candidate email | if in seed (`to`) |

If the proprietary ICP filter rejects the firm, print `[skip] <reason>` and exit 0 **without** writing `latest.md` / draft artifacts (leave prior files untouched).

### A2. Search and fetch

Minimum fetches (skip only if proprietary already supplied a verified equivalent):

1. **Source page** that put them on the list.
2. **Firm website** — About / Team / Contact.
3. **One corroborating page** (press, association, public LinkedIn company About).

Scratch: Facts (URL each), Pain signals, Open questions. Iterate until you have a fresh dated hook OR can honestly mark the hook weak.

### A3. Verify the email

- `email` — address you will recommend
- `email_kind` — `named` | `generic` | `none`
- `email_verification_url` — page where published
- If `none`: still write intel; set `send_ready: false` (draft may be blocked per proprietary)

### A4. Write the intel brief

Write to **both** `data/sst-contact-researcher/latest.md` and `data/sst-contact-researcher/<utc>_<company-slug>.md`:

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
- hook: <one sentence — MUST be ≤12 months old>
- hook_date: <YYYY-MM or YYYY-MM-DD or "undated">
- hook_freshness: <fresh|stale|undated>
- hook_source_url: ...
- hook_quote: <optional>

If the best public fact is stale, omit a strong Dated hook and note the old fact under Firm context as `stale_context`.

## Audience & pain
- audience_notes: ...
- pain_signals:
  - <signal> ([source](url))
- why_us_fit: <1-3 sentences — no feature dump>

## Firm context
- size_proxy: ...
- stack_signals: ...
- geography: ...

## Do not say
- <landmines>

## Sources
- [title](url) — <one-line contribution>
```

Then continue immediately to Part B in the same session. Do not exit after intel.

---

## Part B — Draft and edit

### B0. Gate

Using the intel just written (and proprietary facts):

1. If `send_ready: false` and proprietary forbids non-email channels → write draft `latest.md` with `status: blocked` (no JSON) and exit 0.
2. If `hook_quality: weak` and no usable pain signal → write `latest.md` with `status: need-research` (no JSON) and exit 0.

### B1. Draft iteration 1

**Subject rules (defaults — proprietary may add bans):**
- No product name in the subject
- No "free", "private beta", "just following up", "quick question" alone
- Prefer outcome or pain they already feel
- ≤8 words when possible

**Body skeleton:**
1. Greeting (named first name, else role-aware "Hi there,")
2. One-sentence dated hook **only if fresh** (`hook_freshness: fresh` / ≤12 months). If stale, undated, or weak → pain-led opener — never "Congrats on" a year-old award.
3. One-sentence bridge: their situation → outcome you enable
4. One short proof paragraph (outcomes, not feature dump)
5. Optional proof URL on its own line (from proprietary)
6. One CTA
7. Sign-off from proprietary

### B2. Self-edit passes (mandatory)

Run in order; each revises or records "clean."

**Pass A — Motivation:** First two sentences see *them*, not pitch *us*. Strengthen outcome verbs.

**Pass B — Personalization fidelity:** Every firm/person claim is in the intel. No invented quotes/dates/tools. Stale hook ban: no congrats / "saw your [old event]" openers.

**Pass C — Audience fit:** End-buyer vs partner-referrer vs advisor voice. Wrong voice → rewrite bridge + CTA.

**Pass D — Spam / ignore risk:** Subject triggers → rewrite. Body over word cap → cut. Dual CTA → pick one. Begging ("I'd love your feedback") → peer offer. Strip em dashes / HTML / images. Stale congrats → rewrite.

Stop after Pass D unless a pass introduced a new personalization claim — then re-run Pass B once.

### B3. Optional second iteration

If Pass A–D still leave a major flaw, write `iter2` addressing the flaw list. Cap at 2 iterations.

### B4. Output schema

```markdown
# Outreach draft — <Company>

- drafted_at: <utc-iso>
- intel_path: data/sst-contact-researcher/latest.md
- audience: <class>
- status: ready|blocked|need-research
- word_count: <n>

## Edit summary
- Motivation: <one line>
- Personalization: <one line>
- Audience: <one line>
- Spam-risk: <one line>
- Iterations: <n>

## Subject
<subject line only>

## Body
<plain-text body exactly as it should send, including sign-off>

## Why this should get a reply
<2-4 bullets tied to intel>

## Send checklist
- [ ] Human skimmed subject + first 2 lines
- [ ] Demo/proof URL resolves
- [ ] Recipient not on suppression / recent-contact list
```

Save to **both** `data/sst-outreach-writer-editor/latest.md` and `<utc>_<slug>.md`.

When `status` is `ready`, also write **`latest.json`** and `<utc>_<slug>.json`:

```json
{
  "to": "<recipient email from intel>",
  "subject": "<subject>",
  "body": "<plain-text body including sign-off>",
  "company": "<company>",
  "audience": "<audience class>",
  "intel_path": "data/sst-contact-researcher/latest.md",
  "status": "ready",
  "word_count": 0,
  "drafted_at": "<utc-iso>"
}
```

Do not emit JSON for `blocked` / `need-research`. Do not run apply scripts.

### B5. Report

```
Intel: data/sst-contact-researcher/latest.md
Draft: data/sst-outreach-writer-editor/latest.md
Draft-JSON: data/sst-outreach-writer-editor/latest.json   # or none
send_ready: <true|false>
hook_quality: <strong|adequate|weak>
status: <ready|blocked|need-research>
word_count: <n>
Subject: <subject>
```

## Hard rules

- **No fabricated URLs or quotes.** If you didn't fetch it, it is not in the brief or email.
- **No email pattern guesses.** Unverifiable → `email_kind: none`, `send_ready: false`.
- **No send / claim / apply / seed writes.** Research + draft artifacts only.
- **Weak hook is honest.** Prefer `hook_quality: weak` over a fake opener.
- **No stale openers.** Never `hook_quality: strong` for hook_date older than 12 months; never congratulate stale events in the email.
- **Never skip Pass D.** Spam-shaped subjects are the #1 silent failure mode.
- **Refuse empty personalization.** Mail that could go to any firm in the vertical → `need-research` or rewrite with a real hook/pain line.
- **One session.** Do not invoke other outreach skills or wait for a second agent.
