---
name: sst-outreach-writer-editor
description: Turn a contact-intel brief into a highly motivating plain-text cold email customized to the person and audience class. Drafts, then self-edits through motivation / personalization / spam-risk passes. Consumes sst-contact-researcher output; does not research or send. Pair via the contact-research-and-write chain.
user-invocable: true
version: 1.3.0
model-floor: opus
effort-floor: high
argument-hint: [none — reads data/sst-contact-researcher/latest.md]
---

# Outreach writer-editor

Draft → critique → revise for cold email. Inspired by `sst-iterative-writer` (iteration loop) and `sst-editorial-pass` (structured passes), specialized for short motivating outreach rather than long-form prose. Research stays upstream in `sst-contact-researcher`.

## Project contract

- **Input (programmatic)**: `<project>/data/sst-contact-researcher/latest.md` only. Abort if missing. Do not discover paths by mtime scanning or prior-skill transcript lines.
- **Output dir**: `<project>/data/sst-outreach-writer-editor/`.
  - **Always** write `latest.md` and, when `status=ready`, `latest.json` (overwrite) — the apply driver reads these.
  - Also write dated archives `<utc>_<company-slug>.md` / `.json`.
- **Required from the proprietary counterpart** (when present): product one-liner, proof/demo URL, sender sign-off, audience-specific angles, subject/body bans, CTA options, max word count.
- **Tools required**: `Read`, `Write`. No web research. No claim/apply/seed scripts.
- **Downstream**: project's `apply-intel-draft` / `run-seeded-outreach` driver deposits Drafts. This skill never sends mail and never invokes those scripts.

## Operating principles

- **Motivation > feature list.** Lead with the recipient's pain and the outcome they want. Product mechanics earn one short paragraph max.
- **Honor the intel.** Every personalization line must trace to the brief. If `hook_quality` is `weak`, write a pain-led opener without faking a source cite — or refuse and ask for better research.
- **Audience-specific.** End-buyer, partner-referrer, and advisor emails are different letters. Use the proprietary audience angles.
- **Short.** Default ≤120 words body (proprietary may tighten). Over 200 words is a hard fail on the spam-risk pass.
- **One CTA.** Never dual-ask ("call or watch a video?").
- **Plain text only.** No HTML, images, tracking pixels, or markdown links in the sendable body (URLs as raw https://... lines).
- **No data-plumbing in prompts.** Reading seed/queue, claiming, and applying to Drafts are driver responsibilities.

## 0. Load intel + proprietary facts

1. Read `data/sst-contact-researcher/latest.md` (required).
2. Read the proprietary counterpart (product, bans, CTAs, sign-off).
3. If `send_ready: false` and the proprietary forbids non-email channels, write `latest.md` marked `status: blocked` (no `latest.json`) and exit 0.
4. If `hook_quality: weak` and no usable pain signal, write `latest.md` with `status: need-research` (no JSON) and exit 0.
## 1. Draft iteration 1

Compose:

**Subject rules (defaults — proprietary may add bans):**
- No product name in the subject
- No "free", "private beta", "just following up", "quick question" alone
- Prefer outcome or pain the recipient already feels
- ≤8 words when possible

**Body skeleton:**
1. Greeting (named first name, else role-aware "Hi there,")
2. One-sentence dated hook from intel **only if fresh** (hook_date within last 12 months / `hook_freshness: fresh`). If the hook is stale (>12 months), undated, or `hook_quality: weak`, use a pain-led opener instead — never "Congrats on" a year-old award or old acquisition.
3. One-sentence bridge: their situation → the outcome you enable
4. One short proof paragraph (what the product does in outcomes, not feature dump)
5. Optional proof URL on its own line (demo / case / doc — from proprietary)
6. One CTA
7. Sign-off from proprietary

Save as `..._iter1.md` using the output schema in §4.

## 2. Self-edit passes (mandatory)

Run these passes in order on the current draft. Each pass either revises the draft or records "clean."

### Pass A — Motivation
- Does the first two sentences make *them* feel seen, or pitch *us*?
- Cut any sentence that only advertises the sender.
- Strengthen the outcome verb (save hours, stop chasing, land clean on the day they pick).

### Pass B — Personalization fidelity
- Every firm/person-specific claim appears in the intel brief.
- No invented quotes, dates, or tools.
- If a line can't be sourced, cut it.
- **Stale hook ban:** If `hook_date` is more than 12 months before today (or `hook_freshness: stale`), the body must not open with congratulations or "saw your [old event]". Rewrite opener to pain/outcome. Older facts may appear only as brief firm backdrop if essential — never as the hook.

### Pass C — Audience fit
- End-buyer: their monthly pain and time.
- Partner-referrer: their book / clients / underwriting load — not the end-buyer's feelings.
- Advisor: their team's chase time and deliverable quality.
- Wrong audience voice → rewrite the bridge + CTA.

### Pass D — Spam / ignore risk
- Subject triggers (free, beta, tool, "saw your profile") → rewrite.
- Body > word cap → cut.
- Dual CTA → pick one.
- "I'd love your feedback" / "private beta cohort" begging → rewrite as peer offer.
- Em dashes, HTML, images → strip.
- Congrats on awards / acquisitions / press older than 12 months → rewrite (stale personalization reads like a scraped directory dump).

Stop after Pass D unless a pass introduced a new personalization claim — then re-run Pass B once.

Save intermediates if useful; always write the canonical file.

## 3. Optional second iteration

If Pass A–D still leave a major flaw (wrong audience, no motivation, weak CTA), write `iter2` addressing the flaw list explicitly. Cap at 2 iterations for cold email (more polish usually hurts).

## 4. Output schema

```markdown
# Outreach draft — <Company>

- drafted_at: <utc-iso>
- intel_path: <path>
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
<2-4 bullets: psychological / situational reasons, tied to intel>

## Send checklist
- [ ] Human skimmed subject + first 2 lines
- [ ] Demo/proof URL resolves
- [ ] Recipient not on suppression / recent-contact list
```

Save the markdown to **both** `latest.md` (overwrite) and `<utc>_<slug>.md`.

When `status` is `ready`, also write **`latest.json`** (overwrite) and `<utc>_<slug>.json` for the apply driver:

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

## 5. Report

```
Draft: data/sst-outreach-writer-editor/latest.md
Draft-JSON: data/sst-outreach-writer-editor/latest.json   # or none
status: <ready|blocked|need-research>
word_count: <n>
Subject: <subject>
```

## Hard rules

- **Never invent intel.** No research fetches in this skill.
- **Never send / claim / apply.** No SMTP, no mailbox scripts, no queue mutations.
- **Never skip Pass D.** Spam-shaped subjects are the #1 silent failure mode.
- **Never call yourself recursively.** One writer-editor invocation per contact.
- **Refuse empty personalization.** A mail that could be sent to any firm in the vertical is a failed draft — mark `need-research` or rewrite with a real hook/pain line.
- **Refuse stale openers.** Hooks older than 12 months are not personalization — open on pain instead.
