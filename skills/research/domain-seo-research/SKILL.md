---
name: domain-seo-research
description: SEO keyword research via Google Keyword Planner + reliable bulk domain availability checking (whois + DNS + HTTP). Finds high-visibility available domains for new projects.
user-invocable: true
version: 1.0.0
argument-hint: [niche description or seed keywords]
---

# Domain SEO Research Skill

Research SEO keyword trends and find available domain names for a new project. Combines Google Keyword Planner data with triple-verified bulk availability checks to surface the best domain that matches high-volume, high-growth keywords.

## Workflow

### Phase 1: Gather Seed Keywords

From the user's niche description or seed keywords, generate 5-10 seed keyword phrases that cover:
- The core product/service (e.g. "ai security audit")
- Verb forms (e.g. "ai red teaming", "ai pentesting")
- Tool/product framing (e.g. "ai vulnerability scanner")
- Adjacent concepts (e.g. "prompt injection", "llm security")

### Phase 2: Google Keyword Planner Research

Use Playwright to query Google Keyword Planner. The account may already be logged in.

1. Navigate to `https://ads.google.com/aw/keywordplanner/home`
2. If login is required, ask the user to enter credentials manually and wait
3. Click "Discover new keywords"
4. Enter all seed keywords (type each, press Enter to add as a chip)
5. **Change location to United States** (click location button, remove existing location, search "United States", click Include, Save). The default is often Canada; US data is more useful for SEO.
6. Click "Get results"
7. Wait 3-4 seconds for results to load
8. Read the snapshot to extract the keyword results table

**Data to capture for each keyword:**
- Keyword text
- Avg. monthly searches (range like "1K - 10K")
- YoY change (percentage)
- Competition level (Low/Medium/High)

**Run 2-3 searches** with different keyword clusters to maximize coverage. Go back to the Keyword Planner home between searches.

**Present results** to the user as a ranked markdown table sorted by volume, highlighting keywords with +900% YoY growth.

### Phase 3: Generate Domain Candidates

From the keyword data, programmatically generate 150-200+ domain candidates across .com AND alternative TLDs using these patterns:

```
Patterns (where KW = top keywords like "redteam", "pentest", "llm"):
- {kw1}{kw2}.com          (e.g. redteamai.com)
- {kw2}{kw1}.com          (e.g. airedteam.com)
- get{kw}.com             (e.g. getredteam.com)
- {kw}hq.com / {kw}lab.com / {kw}labs.com / {kw}ops.com
- {kw}pro.com / {kw}kit.com / {kw}hub.com
- {kw}io.com / {kw}iq.com / {kw}bot.com / {kw}agent.com
- {kw}er.com / {kw}ly.com / {kw}up.com / {kw}zen.com
- my/the/try/run/go/just/auto/smart/deep/fast/easy/super/open/full + {kw}.com
- {kw}scan.com / {kw}test.com / {kw}check.com / {kw}guard.com
- Short forms: first letters, dropped vowels

Also generate alt-TLD variants for the best brand names:
- .dev (Google-owned, HTTPS enforced, dev-credible, ~$12/yr)
- .app (Google-owned, HTTPS enforced, ~$14/yr)
- .io  (popular startup TLD, ~$30/yr)
- .co  (popular startup TLD, ~$25/yr)
- .ai  (AI-relevant but premium pricing, ~$80-100/yr)
- .security / .tech / .tools / .run (niche TLDs)
- .net / .org (classic fallbacks)
```

### Phase 4: Bulk Availability Check (Triple Verification)

**CRITICAL: whois parsing must be precise.** The .com whois response includes boilerplate
TERMS OF USE text containing phrases like "domain name registration" and "Domain Name".
Naive grep for `Domain Name:` or `Registrant` matches this boilerplate and reports EVERY
domain as taken. This is the #1 source of false "TAKEN" results.

**The correct approach:**
1. Check the FIRST FEW LINES of whois output for "No match" (definitive available signal)
2. Only if no "No match", look for the EXACT domain name in a `Domain Name: DOMAIN.COM` line
3. Use DNS + HTTP as secondary checks for premium/parked domains

**Always use this function (copy-paste exactly):**

```bash
check_domain() {
    local domain="$1"
    whois_result=$(timeout 5 whois "$domain" 2>/dev/null)

    # Step 1: Check for definitive "not found" in first 5 lines
    # This is the most reliable signal for .com domains
    if echo "$whois_result" | head -5 | grep -qiE "^No match|^NOT FOUND|^No Data Found|^No entries found"; then
        # Whois says not registered. Verify with DNS + HTTP to catch premium/parked.
        if timeout 3 dig +short "$domain" A 2>/dev/null | grep -qE '^[0-9]'; then
            echo "PREMIUM    $domain"; return
        fi
        if timeout 3 dig +short "$domain" NS 2>/dev/null | grep -q '\.'; then
            echo "PREMIUM    $domain"; return
        fi
        http_code=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" "http://$domain" 2>/dev/null)
        if [ "$http_code" != "000" ] && [ "$http_code" != "" ]; then
            echo "PREMIUM    $domain"; return
        fi
        echo "AVAILABLE  $domain"
        return
    fi

    # Step 2: No "no match" found - check for exact domain registration
    # Match "Domain Name: EXACTDOMAIN.COM" to avoid boilerplate false positives
    upper_domain=$(echo "$domain" | tr '[:lower:]' '[:upper:]')
    if echo "$whois_result" | grep -q "Domain Name: ${upper_domain}"; then
        echo "TAKEN      $domain"; return
    fi

    # Step 3: Whois was ambiguous - fall back to DNS + HTTP
    if timeout 3 dig +short "$domain" A 2>/dev/null | grep -qE '^[0-9]'; then
        echo "TAKEN      $domain"; return
    fi
    if timeout 3 dig +short "$domain" NS 2>/dev/null | grep -q '\.'; then
        echo "TAKEN      $domain"; return
    fi
    http_code=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" "http://$domain" 2>/dev/null)
    if [ "$http_code" != "000" ] && [ "$http_code" != "" ]; then
        echo "TAKEN      $domain"; return
    fi

    echo "AVAILABLE  $domain"
}
export -f check_domain
printf '%s\n' "${domains[@]}" | sort -u | xargs -P 15 -I{} bash -c 'check_domain "$@"' _ {}
```

**Execution notes:**
- Use `xargs -P 15` (not 20) to avoid rate limiting on whois + dig + curl combined
- Run in batches of ~80-100 domains per batch
- Sort output so AVAILABLE domains appear first
- The triple-check is slower (~5-8s per domain worst case) but eliminates false positives
- Domains marked AVAILABLE by this function are genuinely purchasable at standard registrar prices

### Phase 5: Expect .com to be Saturated

**Reality check:** For any commercially viable keyword niche, nearly ALL .com domains are taken or premium-priced. Domain squatters use automated tools to register every combination of dictionary words + common suffixes.

When .com results come back 100% taken (which is likely):

1. **Check alt-TLDs for the best brand names.** Run the triple-check against .dev, .app, .io, .co, .ai, .net, .security, .tech variants
2. **Try increasingly creative/obscure .com names** that squatters wouldn't predict (unique portmanteaus, nonsense words, uncommon adjective + noun combos)
3. **Consider premium .com purchase** if the user has budget ($1K-$30K typical for good security domains)

**TLD recommendation hierarchy for tech/SaaS:**
1. .com (if available at standard price, always #1)
2. .dev or .app (Google-owned, HTTPS enforced, credible for tech products)
3. .io (startup-credible, but note: this is the British Indian Ocean Territory ccTLD)
4. .co (startup-friendly, but can be confused with .com)
5. .ai (great for AI products, but expensive and Anguilla ccTLD)
6. .security / .tools / .tech (descriptive but less mainstream)
7. .net / .org (dated for commercial products)

### Phase 6: Rank and Present Results

Present available domains in a tiered ranking table:

**Tier 1: Best SEO + Brand Match**
- Exact or near-exact match to highest-volume keywords
- Short, memorable, professional
- .com strongly preferred, .dev/.app acceptable

**Tier 2: Strong Brand + Good SEO**
- Contains top keyword fragments
- Modern naming conventions
- Good alt-TLD

**Tier 3: Niche/Creative**
- Longer or more specific
- Creative mashups
- Less common TLDs

Provide a top 3 recommendation with reasoning for each. Be honest about .com availability.

### Phase 7: Optional Deep Dive

If the user wants to explore further:
- Verify top picks on Namecheap via Playwright to confirm exact pricing (catches premium pricing the CLI check can't detect)
- Check if any taken .com domains are on auction (Namecheap Auctions tab)
- Verify the top pick isn't a trademarked term (search USPTO via web)
- Check social media handle availability (@username on X/Twitter)

## Important Notes

- **whois boilerplate causes false TAKEN results.** The .com registry whois response includes TERMS OF USE text containing "domain name registration", "Registrant", etc. A naive `grep -i "Domain Name:"` matches this boilerplate on EVERY query, reporting all domains as taken. The fix: always check the first 5 lines for "No match" FIRST, then only look for `Domain Name: EXACT.DOMAIN` (uppercased). This is the #1 lesson from real-world testing.
- **Three result categories:** AVAILABLE (buy at standard price), PREMIUM (whois says free but DNS/HTTP resolves, meaning registrar-held at inflated price), TAKEN (registered by someone).
- .com has more availability than you'd expect once the whois parsing is correct. Many good keyword+suffix combos are genuinely available.
- The Google Ads account location resets to default (Canada) on each new search; always change it to US.
- Prefer domains under 15 characters for memorability.
- Avoid hyphens in domain names.
- For .ai TLD, whois is especially unreliable; verify on a registrar.
- Always verify the user's final pick on an actual registrar (Namecheap via Playwright) before confirming. Even the fixed script can miss edge cases like premium registry pricing that only shows on the registrar site.
