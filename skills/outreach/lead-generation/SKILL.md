---
name: lead-generation
description: Research and verify cold-outreach leads in any field. Selects high-yield source channels, enforces a no-guessing verification bar, delegates research to sub-agents with strict rules, and produces send-ready lead lists with verified contact emails. Works for B2B sales, recruiting, partnership outreach, PR, investor research, or any "find the right person to email" task.
user-invocable: true
version: 1.0.0
---

# Lead Generation

Research and verify cold-outreach leads. The skill is channel-agnostic and vertical-agnostic; it is the *process* that matters. It is equally useful for finding B2B software buyers, recruiting engineers, sourcing podcast guests, or building investor lists.

## When to use this skill

- User says "find me 10 [company type] to email about X"
- User wants to build a cold-outreach list for any purpose (sales, hiring, PR, partnerships)
- User asks to research named prospects and their contact info
- User asks to expand an existing outreach list to more targets

## What makes this hard (and why it needs a system)

Two failure modes ruin cold outreach:

1. **Research produces unverifiable leads.** Anonymous forum posts, ZoomInfo/RocketReach pattern matches, "inferred" emails. You send; it bounces; domain reputation craters; future sends land in spam.

2. **Research scales faster than verification.** Agents happily return 50 "leads" that are 80% garbage. Triaging the list costs more than starting over with a smaller strict list.

The fix: one rule above all others — **Never guess. Verify every email against the firm's own published content.**

## The verification bar

An email is considered verified for cold outreach ONLY if it meets one of these standards:

1. **Published on the firm's own contact page, About page, team directory, or footer** (the highest standard; this is the email the firm wants the public to use).
2. **Published in a byline, press release, or case study the firm authored or participated in** (e.g., `jane.doe@firm.com` quoted as the author of a company blog post).
3. **Published on the firm's LinkedIn company page "Contact Info" section** (when public).

The following are **NOT acceptable** and must be explicitly rejected:

- Pattern-guess emails from ZoomInfo, RocketReach, Hunter.io, Buzzfile, Apollo, or any aggregator that reports a "likely" email based on firm domain patterns. These are guesses, not publications.
- "Firm uses `firstname.lastname@` pattern, confirmed via multiple employees, so target's email is probably X." This is also a guess.
- Email from a third-party data broker that the firm didn't publish.

When no individual email is verifiable, **generic published mailboxes are acceptable**: `info@`, `contact@`, `office@`, `hello@`, function-specific `accounting@` / `estimating@`, etc., provided they appear on the firm's own site. Address the body to the named individual anyway.

When neither an individual nor a generic mailbox is publicly published, **drop the lead** or flag for a non-email channel (LinkedIn InMail, contact form, phone).

## Channel selection — where real names are publicly attached to signal

### High-yield channels (prioritize these)

Signal-rich channels where real company names and roles are publicly attached:

1. **Vendor case studies / customer testimonials.** Vendors obtain explicit permission from customers to publish names and quotes. Case studies are a verified naming event. Look at testimonial pages on niche vertical-software vendor sites, not horizontal review aggregators.
2. **Industry association member spotlights.** Trade associations (AGC, ABC, NAHB, ABA, AMA, SHRM, etc.) profile members by name in newsletters and spotlight pages. Real names, real roles, real companies.
3. **Certification/designation directories.** LEED, CCIFP, CFP, CCIM, ACM Fellows, etc. Named professionals at named companies. Some include public email fields.
4. **Press releases and news announcements.** Byline + company header + usually a named quote. Freshness is a bonus.
5. **Conference speaker bios.** Named speaker + firm + topic + often direct email for session follow-up.
6. **Published case studies by service firms** (law firms, CPA firms, consulting firms). When a service provider publishes a client success story, the client is named and usually quoted.
7. **"Top N" industry lists** (trade publications, regional business journals, Forbes, Inc.). Named company + often named contact.
8. **Regulatory filings** (SEC EDGAR for public companies, state contractor licenses, municipal bid awards). Public record; names included.
9. **LinkedIn public content from company execs.** Posts where a named executive at a named company writes about a problem you solve.

### Low-yield channels (deprioritize)

Signal-poor channels where identity is hidden by design:

1. **Reddit and most forums.** Pseudonymous by design. Profile bios rarely list companies. Even rich pain posts rarely convert to named-lead emails.
2. **Software review aggregators** (Capterra, G2, Software Advice, TrustRadius). Reviews are anonymized to first name + last initial, no company. They publish named reviewers *only when the vendor asks them to*.
3. **Quora / community Q&A platforms.** Mostly pseudonymous; contact info stripped.
4. **Twitter / X threads on pain points.** Usernames exist but corporate identities are inconsistent; people post from personal accounts about company problems without naming the company.
5. **State license databases** (for public-licensee fields like contractors). Named companies, but the database contains no contact email. Cross-referencing to email is a high-effort pattern-matching exercise prone to the no-guessing rule violation.

If a user insists on low-yield channels, report the structural limitation, capture any good pain posts as "monitor only," and suggest swapping to a high-yield channel instead.

## Workflow

### Step 1: Define the ICP precisely

Before any research, confirm with the user:

- **Company size band.** "Small to mid" is insufficient. Specify revenue, headcount, or a proxy (e.g., "$1M-$50M revenue" or "5-50 employees").
- **Industry / vertical.** Be narrow. "Construction" is too broad; "bonded construction subcontractors" is actionable.
- **Role to reach.** Founder/owner, controller, CFO, ops manager, etc.
- **Pain signal you're matching against.** "Uses QBO and needs WIP reporting" is concrete; "needs better financial tools" is not.
- **Geographic scope.** Nationwide, regional, or single-state.

Without a sharp ICP, agents return noise. With one, the verification bar does its own filtering.

### Step 2: Select 2-3 channels

Pick 2-3 channels from the high-yield list above, matched to the ICP. Spawning parallel research agents, one per channel, is strictly better than one agent trying to cover all channels. Agents work in parallel; user waits for the slowest one instead of the sum.

Explicitly tell each agent **not to duplicate leads from prior batches** by passing the list of already-contacted company names.

### Step 3: Brief research agents with the strict rules

Every research agent gets these rules verbatim:

> **Rules for each lead (strict):**
> 1. Real reference URL (not a search-results page).
> 2. One-line excerpt showing the pain point or context.
> 3. Company name identified explicitly in the reference.
> 4. Company domain (their real business website).
> 5. Contact email verified via one of:
>    - Company Contact/About/Team page listing the email
>    - Generic `info@` / `contact@` / `office@` if no individual published (flag as generic)
>    - **DO NOT guess email patterns. No `firstname.lastname@domain.com` guesses.**
>    - DO NOT source from ZoomInfo, RocketReach, Hunter.io, Buzzfile, Apollo, or any pattern-matching aggregator.
> 6. Contact verification source URL (distinct from the finding URL).
> 7. Named person from the reference (if any) — title + first/last name.
> 8. Skip unverifiable leads entirely. It is OK to return fewer than asked. It is NOT OK to pad with unverifiable entries.

Always ask for a structured markdown output format that can be pasted directly into a lead-tracking doc. Include `**Status:** [ ] Sent` at the bottom of each entry so you can mark as sent later.

Target 5-12 leads per agent. Quality over quantity.

### Step 4: Post-agent verification pass

Before trusting an agent's output, run a verification pass on any lead where the agent cited:
- ZoomInfo / RocketReach / Hunter.io / Buzzfile / Apollo / any aggregator
- "Pattern confirmed via multiple employees on same domain"
- "MX record suggests `info@` exists"
- Any verification URL that doesn't resolve or is unreachable

For these, fetch the firm's actual contact page and confirm the specific email is published. Swap to the verified generic mailbox if the individual pattern fails. Drop the lead if neither resolves.

### Step 5: Email infrastructure sanity check (once per new sender domain)

Before sending, confirm the sender infrastructure:

- **SPF**: `dig +short TXT yourdomain.com` — must authorize the sending IP.
- **DKIM**: verify signer is configured for the domain; check `dig +short TXT <selector>._domainkey.yourdomain.com`.
- **DMARC**: `dig +short TXT _dmarc.yourdomain.com` — at least `p=none` for monitoring; stricter once you have deliverability signal.
- **HELO/PTR alignment**: If sending from a VPS, the reverse DNS should match the domain, or at minimum look consistent.

Missing SPF or DKIM → recipients will silently drop. Fix before sending.

### Step 6: SMTP RCPT-TO probe (optional, for uncertain addresses)

When you have a pattern-guessed or unverified address and can't find a better one, you can probe the recipient's mail gateway via SMTP RCPT-TO. This is sparingly useful; many gateways are accept-all.

```python
import smtplib
s = smtplib.SMTP(MX_HOST, 25, timeout=15)
s.ehlo("yourdomain.com")
s.mail("sender@yourdomain.com")
code, msg = s.rcpt("target@firm.com")
print(code, msg)
s.quit()
```

**Always pair with a negative control** — probe a known-bogus mailbox at the same domain (e.g., `thispersondoesnotexist9999@firm.com`). Interpretation:

- Target 250 AND bogus 5xx → per-mailbox validation; target is valid.
- Target 250 AND bogus 250 → accept-all gateway (common for AppRiver / some Proofpoint setups). Inconclusive.
- Target 5xx → mailbox doesn't exist. Don't send.

Known behaviors (update as you learn more):

- **Microsoft Outlook / Exchange Online**: per-mailbox, probes reliable.
- **Proofpoint (ppe-hosted.com MX)**: varies by tenant.
- **AppRiver (arsmtp.com MX)**: accept-all; probes useless.
- **Google Workspace**: per-mailbox but rate-limited; don't probe aggressively.

### Step 7: Personalize every draft

Cold emails without personalization read as spam. The bar is:

- **Open with a dated, specific reference** to something the target wrote, said, or was featured in. "Your May 2025 piece on X" beats "your recent article on X" because dated beats vague.
- **Tie the reference to the offer** in one sentence. Don't lecture the target; show you understood the reference.
- **Keep the body under 200 words.** Cold emails over 200 words get deleted.
- **One clear ask.** "Worth a 15-minute call?" or "Worth a 3-minute demo?" — not both.
- **Sign with a consistent human name** (not the company name or "Sales Team"). A first name with a legitimate title converts better.
- **Plain text, no HTML, no images, no tracking pixels.** Tracking pixels get flagged by corporate mail gateways; HTML emails land in promotions tabs.

### Step 8: Batch send mechanics

Default parameters for a well-behaved batch:

- **Spacing**: 60 seconds between sends. Slower is always safer; faster triggers spam classifiers and per-IP rate limits.
- **Batch size**: 10-20 per batch maximum from a new sender domain. Larger batches from a young domain look like spam blasts.
- **Timing**: send during recipient business hours when possible. Microsoft Outlook inboxes penalize after-hours cold mail less than Gmail does.
- **From address alignment**: `<Sender Name> <support@yourdomain.com>` with matching SPF/DKIM. Don't send as `noreply@` — it signals broadcast.
- **Reply-To**: either the From address or a monitored inbox. Never a deadletter address.
- **Per-send logging**: capture queue ID, recipient gateway, and downstream `status=sent` acknowledgement. You need these to diagnose non-delivery or bounces later.

A reference Python send loop that matches these defaults:

```python
import subprocess, time

FROM = "<Sender Name> <support@yourdomain.com>"
ENVELOPE_FROM = "support@yourdomain.com"

emails = [
    {"id": "01-acme", "to": "info@acme.com", "subject": "...", "body": "..."},
    # ...
]

for i, e in enumerate(emails):
    msg = (
        f"From: {FROM}\r\n"
        f"To: {e['to']}\r\n"
        f"Reply-To: {ENVELOPE_FROM}\r\n"
        f"Subject: {e['subject']}\r\n"
        f"Content-Type: text/plain; charset=UTF-8\r\n"
        f"MIME-Version: 1.0\r\n"
        f"\r\n"
        f"{e['body']}"
    )
    proc = subprocess.run(
        ["/usr/sbin/sendmail", "-t", "-f", ENVELOPE_FROM, "-i"],
        input=msg.encode("utf-8"),
        capture_output=True,
    )
    t = time.strftime("%H:%M:%S")
    if proc.returncode == 0:
        print(f"[{t}] SENT #{i+1:02d} {e['id']} -> {e['to']}", flush=True)
    else:
        print(f"[{t}] FAIL #{i+1:02d} {e['id']} -> {e['to']}: rc={proc.returncode}", flush=True)
    if i < len(emails) - 1:
        time.sleep(60)
```

After the loop, verify delivery by searching mail logs for each queue ID:

```bash
grep -E "recipient1|recipient2|..." /var/log/mail.log | grep "status=sent"
```

### Step 9: Track in a persistent doc

Every lead belongs in a persistent outreach document (e.g., `docs/outreach.md`). Structure per entry:

```
### NN. [Company name]
- **Reference:** [URL] — "[one-line excerpt]"
- **Company domain:** [domain.com]
- **Contact:** [email (named person if known)] or [generic: info@domain.com]
- **Contact verification:** [URL where the email was sourced + brief note]
- **Named in reference:** [Full Name, Title] or [no person named]
- **Context:** [any notable hook: bonded work, scaling, specific pain quote]
- **Status:** [ ] Sent
```

After a send, flip to `[x] Sent YYYY-MM-DD (gateway, queue-id)`. At the bottom of the doc, a delivery log table with Postfix queue IDs makes downstream debugging trivial.

Also record **channel productivity** — which sources yielded leads, which were thin, which should be re-scanned next round. Don't lose this metadata; it saves hours next time.

### Step 10: Monitor replies and bounces (24-48h window)

After a batch:

- Watch the reply inbox. Triage replies (interested / decline / questions) and act.
- Watch for bounces. A bounce means either the mailbox doesn't exist (bad lead; update doc) or the domain rejected for spam (sender reputation problem; investigate before next batch).
- Track response rate by lead source. Over time this tells you which channels produce replying leads, not just sendable leads.

## Anti-patterns to avoid

- **Agent inflation.** Do not let a research agent pad their list to hit a number. Tell them explicitly "OK to return fewer if thin; NOT OK to pad."
- **Multi-step forwarding chains.** "Here's a name at a company, I guessed the email pattern based on another employee" — no. Drop it.
- **Reddit-scale cold DMs.** Platforms with pseudonymous users punish DM volume fast. Use Reddit only for in-thread engagement, not direct outreach.
- **Generic mailboxes with generic bodies.** If you must send to `info@`, personalize anyway by addressing the body to a specific named person and referencing a specific item they authored.
- **Sending in bursts without spacing.** 10 emails in 10 seconds is a spam signal. 10 emails in 10 minutes reads as human.
- **Not checking SPF/DKIM/DMARC.** One undeliverable batch to a major domain (Gmail, Outlook) and your sender reputation takes weeks to recover.
- **Lumping research and send in one step.** Separate research (produces a doc) from send (acts on the doc). Research is idempotent; send is not.
- **Silently mutating the doc.** When batch 1 is sent, don't delete entries — flip status. You need the history to diagnose later.
- **Building the list without a rule doc.** Every platform has rules (LinkedIn ToS, forum spam rules, CAN-SPAM, GDPR). Read them before sending.

## Cross-cutting considerations

### Compliance

- **CAN-SPAM (US)**: cold B2B email is legal if the message includes a physical mailing address, an unsubscribe mechanism, and a truthful From/Subject line. The physical address and unsubscribe are non-negotiable; include both even in short pitches.
- **GDPR (EU)**: cold email to EU-based recipients requires legitimate interest balancing, including a clear unsubscribe and data-retention respect. If your ICP is EU-heavy, talk to counsel before a bulk send.
- **CASL (Canada)**: stricter than CAN-SPAM; requires express or implied consent. Don't blast Canadian lists without due diligence.

### Deliverability hygiene

- Warm up new sender domains gradually. First week: 10-20 sends/day. Build volume over several weeks.
- Don't buy or scrape lists. Every lead must be individually researched.
- Avoid spam trigger words in subject lines: "free," "act now," "limited time," "no risk." Write like a human writing to another human.
- Monitor your domain's reputation on tools like Google Postmaster, Microsoft SNDS, Talos.

### When to hand off to a human

Some decisions should be the user's, not the agent's:

- Final send approval for the first 3-5 emails from a new sender domain (sanity check).
- Any outreach to a target where the agent is uncertain about the email verification.
- Choosing between two verified emails (e.g., named partner vs. generic inbox) when the named option involves risk.
- Batch sends over 20.

Present the draft payload with a clear summary (From, To, Subject, Body) and wait for explicit approval.

## Output contract

When invoked for a research task, the skill's final deliverable to the user is:

1. An updated outreach doc at `docs/outreach.md` (or wherever the user specifies) with new leads appended.
2. A summary block listing: how many leads found, how many verified, how many rejected and why, which channels were productive, which were thin.
3. A proposal for the next action: send all, send strongest subset, hold for review, expand to more channels.

The user decides what to do next. Never auto-send without explicit approval on the first batch from a new sender domain.
