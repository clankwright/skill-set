---
name: sst-social-promoter
description: |
  Browser-automated social-platform promotion workflow — log in, search for relevant recent posts, draft and submit short tailored replies that recommend a target product/service while respecting platform self-promo rules. Generic across platforms (Reddit, HN, Discord, X, niche forums); the platform-specific search terms, login flow nuances, and brand-specific reply copy live in the project's proprietary counterpart (e.g. <brand>-promoter). Uses the project's browser automation (typically Playwright MCP).
user-invocable: false
version: 1.0.0
argument-hint: [campaign brief — target platform, target subreddits/channels, recency window]
---

# Social promoter

Drive a browser to find relevant conversations and post tailored, non-spammy replies that surface a product/service. The transferable encodes the *method*; brand specifics (which subreddits, which platform, what the product is, the actual reply copy) live in the proprietary counterpart.

## Project contract

- **Required from the proprietary counterpart**:
  - Target platform identifier (e.g. `reddit`, `hackernews`, `discord-server-id`).
  - Login credential source (env vars, secrets file — declared by the proprietary, not stored here).
  - Target communities (subreddits / channels / forum IDs).
  - Search keywords / topic patterns relevant to the campaign.
  - The product / service being promoted, and a short brand description.
  - Reply copy templates (1-3 short variants the proprietary supplies; this skill picks the best fit per thread).
  - Subreddit-specific self-promo rules and disclosure requirements.
- **Tools required**: Playwright MCP (or the harness's browser-automation equivalent); harness's `WebSearch` and `WebFetch` for reconnaissance. No file IO needed unless the proprietary requests run logging.
- **Output dir**: `<project>/data/sst-social-promoter/<utc>_<campaign-slug>/run.jsonl` — append one line per post visited and per reply submitted.
- **Input shape**: a campaign brief from the proprietary counterpart, typically as a paragraph naming target communities + recency window + reply intent.

## Operating principles

- **Non-spammy, period.** Replies are short (1-2 sentences), specific to the OP's question, and only mention the product when it's the actual best answer. If the OP is asking about something else, scroll past — don't reply just to drop a link.
- **Respect platform rules.** If a community requires self-promo disclosure, include it. If a community bans self-promo, don't post there at all (read the sidebar / rules before the first post in any new community).
- **One post, one reply.** Don't reply to the same OP twice. Don't reply to your own previous comments.
- **Recency matters.** Default to threads from the last month. Replies on year-old posts read as bot behavior.
- **Match the tone.** Casual subreddit → casual reply. Professional forum → formal reply. The proprietary's reply templates should already reflect this; pick the right one.

## Process

### 1. Read the proprietary's campaign brief

Confirm you have everything you need:
- Login creds in the configured env vars
- Target communities list
- Search keywords
- Product description
- Reply copy templates (typically 1-3 variants)
- Per-community rules summary

If any of these is missing, abort with a clear error pointing to the proprietary counterpart's SKILL.md.

### 2. Connect to the browser

The Playwright MCP server should already be running (the project starts it on session boot, NOT this skill). Confirm browser tools are available; abort with a clear error if not.

### 3. Log in

Navigate to the platform. Handle cookie banners. Submit credentials. Confirm login succeeded by checking for the post-login UI element the proprietary specified (e.g. the user avatar in the top right).

### 4. For each target community

#### 4a. Read the community rules

Visit the community's rules / about page once per session (cache the result for the rest of the run). Note:
- Self-promo allowed? At what frequency?
- Disclosure required (e.g. flair the comment, mention affiliation)?
- Banned topics or domains?

If self-promo is banned, skip the community entirely.

#### 4b. Search for relevant threads

Run targeted searches using the proprietary's keywords + recency filter (last month). Keywords might include the problem the product solves (e.g. "CSV cleaning", "missing fields", "lead enrichment"), not the product name itself.

#### 4c. Triage the results

For each thread that surfaces:

- Open it. Read the OP and the top 3 comments.
- Decide: is the OP genuinely asking about something the product addresses? (Yes / Maybe / No.)
  - **No**: skip; log to `run.jsonl` as `triage: skip-irrelevant`.
  - **Maybe**: still skip; "maybe" is not a green light. Save engineering effort for clear yes hits.
  - **Yes**: continue to 4d.
- Has the OP already received a satisfactory answer in the existing comments? If yes, skip; the conversation has moved on.

#### 4d. Draft and post the reply

- Pick the best-fit reply template from the proprietary's variants. Tailor 1-2 specific phrases to the OP's situation (use a specific noun from their question; reference their stack if mentioned).
- Apply any disclosure the community requires.
- Submit the reply.
- Wait for the platform's confirmation (either the new comment appearing in the page or a server response).
- Log to `run.jsonl`: `{thread_url, reply_text, posted_at, disclosed: true/false}`.

#### 4e. Pace yourself

Rate-limit: at most 2 posts per community per session, at most 5 posts across all communities per session. Spamming will get the account flagged and the entire campaign loses access.

### 5. Report

```
Campaign: <slug>
Communities visited: <N>
Threads triaged: <N>
Replies posted: <N>
Skipped (irrelevant / already-answered / rules-blocked): <N>
Run log: <path to run.jsonl>
```

## Hard rules

- **Never post the same reply text twice in one session.** Even with subject tailoring, repeating the template body looks like a bot.
- **Never reply on threads older than 90 days.** Cap is 30 days by default.
- **Never DM the OP.** Replies are public; cold DMs cross the spam line.
- **Never argue in the comments.** If someone disagrees with the recommendation, that's their reply; don't escalate.
- **Never bypass a community's "no self-promo" rule.** Skip the community.
- **Never store credentials in this skill or in the run log.** Credentials live in the env vars the proprietary counterpart names; the log records which platform, not which account.
- **Never auto-upvote / auto-downvote anything.** Engagement comes from posting, period.
