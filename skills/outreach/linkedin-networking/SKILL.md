---
name: linkedin-networking
description: Build LinkedIn presence for a product account. Search for relevant posts, follow accounts, like posts, leave thoughtful comments, send connection requests, and create company pages. Uses Playwright MCP.
user-invocable: true
version: 1.0.0
---

# LinkedIn Networking Agent

Build and maintain LinkedIn presence for a product/brand account. Handles searching for relevant content, following industry accounts, liking posts, commenting with value-first replies, and sending connection requests.

## Prerequisites

- LinkedIn account credentials in project `.env` (LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
- Playwright MCP tools available
- Account must be logged in (or login using stored credentials)

## Login Flow

1. Navigate to `https://www.linkedin.com/feed/`
2. If redirected to login/authwall: navigate to `https://www.linkedin.com/login`
3. Fill email and password from `.env`, click "Sign In"
4. If security verification appears: ask user to complete it manually

## Key Constraints Learned

### New Account Limitations
- **Company page creation requires connections.** LinkedIn blocks "Create a LinkedIn Page" until the personal account has accepted connections. Send 10+ requests first, wait for accepts, then create the page.
- **Don't spam connection requests.** LinkedIn limits to ~100/week for new accounts. Send 10-20 per session.
- **Send without a note** is faster for bulk connection building. "Add a note" gets higher accept rates but takes longer. Use notes only for high-value targets (CPAs, influencers).

### Content Strategy
- **Week 1-2:** Educational posts only. No product mentions. Build credibility.
- **Week 3+:** Start mentioning product naturally in context.
- **Comments > Posts** for new accounts. Commenting on established accounts' posts gets more visibility than posting to zero followers.
- **Always use relevant hashtags:** #ConstructionAccounting, #WIPReport, #JobCosting, #ConstructionManagement, #CFMA, #QBOchat

### Engagement Priority Order
1. **Comment on recent posts** from accounts with 500+ followers (highest visibility)
2. **Like posts** from relevant accounts (low effort, signals engagement)
3. **Follow accounts/pages** in the niche (builds feed relevance)
4. **Send connection requests** to individuals in target roles
5. **Post original content** (educational, value-first)

## Workflow

### Step 1: Login and Check Notifications

```
Navigate: https://www.linkedin.com/feed/
Check notifications for: accepted connections, post engagement, profile views
```

If connection requests were accepted, check if company page can now be created:
```
Navigate: https://www.linkedin.com/company/setup/new/
Click "Company" button
If "Feature not available" -> need more connections, continue networking
If form appears -> fill in company details and create page
```

### Step 2: Search for Relevant Posts

Run 3-5 searches sorted by "Latest" to find fresh content to engage with:

```
https://www.linkedin.com/search/results/content/?keywords=SEARCH_TERM&sortBy=%22date_posted%22
```

**High-value search terms** (adapt per niche):
- `construction WIP report`
- `WIP schedule construction`
- `"over under billing" construction`
- `#ConstructionAccounting WIP`
- `construction accounting job costing`
- `QuickBooks construction`
- `construction bookkeeping`
- `percentage of completion construction`
- `surety bond WIP`

### Step 3: Engage with Posts

For each search result page:

1. **Take screenshot** to see what's visible
2. **Snapshot** to get element refs
3. For each relevant post:
   - **Like it** (click "React Like" button)
   - **Follow the author** if not already following (click "Follow [Name]" button)
   - **Comment** on the best 1-2 posts per search (see commenting guidelines below)

**Interaction pattern for each post** (the refs change every snapshot, always re-snapshot):
```
1. grep for "Follow.*ref=" and "React Like.*ref=" in snapshot
2. Click Follow button ref
3. Click Like button ref
4. For comments: click "Comment" button ref -> snapshot again -> find textbox ref -> type comment -> snapshot -> find comment submit button -> click
```

**Important:** LinkedIn's snapshot refs are ephemeral. After any click, refs may change. Always take a new snapshot before the next interaction.

### Step 4: Comment Guidelines

Comments should be **value-first, no product pitch** (especially in weeks 1-2):

- Respond to the specific point made in the post
- Add a complementary insight, not a contradiction
- Keep it 2-4 sentences
- Show domain expertise
- No links, no product mentions until account is established (week 3+)

**Good comment patterns:**
- "That stat about X is consistent with what I've seen. The root cause is usually Y, which most firms don't address until Z happens."
- "This is the part most people miss. The formula is simple; the hard part is getting [specific operational challenge]."
- "Agree on [their point]. I'd add that [complementary insight] makes a bigger difference than most firms realize."

**Bad patterns (avoid):**
- "Great post!" (empty engagement)
- "Check out my tool at..." (spam)
- Anything longer than a short paragraph

### Step 5: Send Connection Requests

Search for people in target roles:
```
https://www.linkedin.com/search/results/people/?keywords=SEARCH_TERM&origin=GLOBAL_SEARCH_HEADER
```

**High-value search terms for people:**
- `construction accountant QuickBooks`
- `construction CPA`
- `construction bookkeeper`
- `construction controller`
- `CFMA construction`
- `QuickBooks ProAdvisor construction`

**Connection request flow:**
1. Snapshot the search results
2. `grep "Invite.*to connect" snapshot.yml` to find all Connect buttons
3. Click each Connect button -> snapshot -> find "Send without a note" -> click
4. Repeat for all visible results (typically 8-10 per page)
5. Do NOT go to page 2+. One page per session per search is enough.

### Step 6: Follow Key Pages

These are high-value pages to follow in the construction accounting niche:

| Page | Followers | Why |
|------|-----------|-----|
| CFMA | 13,400 | Main construction financial management association |
| CICPAC | 570 | CPAs Who Know Construction |
| The Construction CPA | 1,390 | Construction accounting content |
| BuildBase | 802 | Construction ERP/tech |

Follow via: `https://www.linkedin.com/company/PAGE_SLUG/`
Click the Follow button on the company page.

Also follow CFMA chapter pages (Sacramento, Chicago, Philadelphia, etc.) for local construction accounting content.

### Step 7: Post Original Content

Post 1-2 educational posts per week. No product pitch in weeks 1-2.

**Post flow:**
1. Navigate to `https://www.linkedin.com/feed/`
2. Click "Start a post" button
3. Snapshot -> find "Text editor for creating content" textbox ref
4. Type post content
5. Click "Post" button

**Content ideas (construction WIP niche):**
- Common WIP mistakes (stale estimates, gut-feel percentages, quarterly instead of monthly)
- WIP formula explained simply
- Over/under billing: what your surety actually looks at
- Why PMs hate filling out cost-to-complete (and how to make it easier)
- The gap between QBO and construction-specific reporting
- Real examples of how WIP caught a problem early

**Post format that works:**
```
[Hook line with a surprising stat or bold claim]

[3-5 numbered points or short paragraphs with specific insights]

[Closing thought]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4
```

## Session Tracking

After each networking session, update the promotion plan (`docs/promotion-plan.md`) with:
- Number of connection requests sent (and current total pending/accepted)
- Number of posts liked
- Number of comments left
- Number of accounts followed
- Any notable engagement received (profile views, post impressions, connection accepts)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Redirected to authwall | Navigate to /login, fill credentials from .env |
| "Feature not available" on company page | Need more accepted connections, keep networking |
| Rate limited on connections | Stop for the day, resume tomorrow |
| Post editor refs not found | The editor is in an iframe or dynamic element; take a fresh snapshot after clicking "Start a post" |
| Page went blank / about:blank | Browser crashed; navigate back to linkedin.com/feed |
| File chooser modals stacking | Call `browser_file_upload` with no paths to dismiss each one |
