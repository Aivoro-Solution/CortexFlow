---
title: "Fix Fresh Self-Hosted n8n Flagged as Phishing by Google Safe Browsing (False Positive, 4 Fixes)"
description: "Clean self-hosted n8n flagged 'Deceptive site ahead'? It's a known false positive (GH #41280). Clear it in 24-72h with these 4 fixes."
date: 2026-10-22
category: automation
tags: ["n8n", "self-hosting", "google safe browsing", "docker", "troubleshooting"]
draft: false
featured: false
image: "/og/fix-n8n-selfhosted-phishing-flag.webp"
---

You deploy a clean n8n on a brand-new subdomain — `https://n8n.example.com/` — official Docker image, HTTPS, nothing shady. Hours later, Chrome hits you with a red full-page warning: **"Deceptive site ahead."** Google Search Console says your property has a **Social Engineering** security issue and names your `/signin` page as the offender.

You didn't get hacked. This is a documented false positive — [n8n-io/n8n issue #41280](https://github.com/n8n-io/n8n/issues/41280). Googlebot spots your new certificate via Certificate Transparency logs, crawls a fresh auth screen on a domain with zero reputation, and pattern-matches a private login form as a phishing kit. Here's exactly how to clear the flag and stop it coming back.

## The symptom

Within hours to a few days of first deploy, all three of these appear:

- Chrome/Edge/Firefox show **"Deceptive site ahead"** on every page of your n8n instance.
- Google Search Console → **Security issues** lists **Social Engineering content** (sometimes "Phishing"), with sample URLs like `https://n8n.example.com/signin?redirect=/settings/usage`.
- The [Safe Browsing site status check](https://transparencyreport.google.com/safe-browsing/search) shows your domain as **dangerous/deceptive**.

## Root cause: a new auth screen looks like a phish to a bot

The #41280 thread nails it:

1. You create a new subdomain → its certificate appears in **Certificate Transparency logs**, which Googlebot watches.
2. Googlebot crawls the fresh domain and lands on n8n's `/signin` — a bare authentication screen on a domain with **zero history and zero authority**.
3. Automated classifiers see a credential-collection form with no reputation and file it as **Social Engineering / Phishing**.

Two extra tripwires the community has confirmed ([forum thread t/55142](https://community.n8n.io/t/issues-accessing-self-hosted-n8n-n8n-b2bclientsystems-info-in-chrome-works-in-incognito-and-other-browsers/55142)):

- **The word "n8n" in the subdomain** itself appears to make the flag more likely — an n8n team member in that thread suggested trying a different subdomain name.
- n8n ships **no anti-indexing headers** on `/signin` (no `X-Robots-Tag: noindex`), so nothing tells crawlers "this is a private app, not a public login lure."

The warning does **not** mean your instance is compromised. But rule out a real compromise first (Fix 1), then clear the flag (Fix 2), then harden against recurrence (Fixes 3–4).

## Fix 1: Prove the instance is actually clean

Before appealing, verify there is nothing real on the box. A fresh n8n should pass all of these in minutes:

```bash
# 1. Check what you're actually running — official image only
docker ps --format '{{.Names}} {{.Image}}'

# 2. VirusTotal URL scan of your domain
#    https://www.virustotal.com/gui/home/url  → paste https://n8n.example.com/
#    Keep the permalink — you'll cite it in your review request.

# 3. Independent malware scan (free, no install)
#    Quttera: https://quttera.com/website-malware-scanner
#    In the n8n forum case, Quttera found zero issues on a flagged instance —
#    exactly the evidence that moved Google to lift the ban.
```

Also confirm your n8n is the official image (`n8nio/n8n`), pulled from Docker Hub — not a third-party image with bundled "extras." Save the VirusTotal and Quttera report links: they're your evidence.

## Fix 2: Request a review in Google Search Console

This is the only official path to clearing a Safe Browsing phishing/social-engineering flag. Phishing reviews typically take about **24–72 hours**.

1. **Verify ownership.** In [Google Search Console](https://search.google.com/search-console), add the property for your n8n domain (domain-prefix or URL-prefix; the DNS-TXT or meta-tag method takes ~5 minutes).
2. **Open Security issues** in the left sidebar. Expand the **Social engineering content** / phishing entry and note the flagged sample URLs (usually your `/signin` variants).
3. **Click "Request review"** at the bottom. Describe exactly what the site is and what you verified, one sentence per issue. Example text that works:

   > This is a self-hosted n8n (workflow automation software, official n8nio/n8n Docker image) private instance — the flagged /signin page is the application's own legitimate login screen, not a phishing page. Independent scans (VirusTotal + Quttera, dated [date]) report the site clean. The flag is a false positive: the domain is brand new with no history. Please re-evaluate.

4. **Wait.** The warning stays up during review — there is no way to speed it up. One accurate request is better than several; repeated or contradictory review requests can lock you out of further requests for ~30 days.
5. **Recheck** via the [Safe Browsing transparency report](https://transparencyreport.google.com/safe-browsing/search) after the review resolves. Firefox and Safari consume the same Google Safe Browsing lists, so one successful review clears them all.

If the review fails anyway: check the **Manual actions** section too (a separate penalty needs a separate resolution), clear any Cloudflare/proxy cache so Google's re-crawl sees the current site, and make sure the instance is actually live when Google rechecks — an offline site can't pass a review.

## Fix 3: Add `X-Robots-Tag: noindex` to the auth pages (reverse proxy)

The structural fix the #41280 reporter asked n8n for — "don't let crawlers index `/signin`" — doesn't exist in n8n yet. Add it yourself at your reverse proxy so crawlers never treat the login screen as a public page.

**Nginx** (add inside your n8n `server` block):

```nginx
# Keep crawlers away from the auth surface
location ~ ^/(signin|signup|reset-password) {
    add_header X-Robots-Tag "noindex, nofollow, noarchive" always;
    proxy_pass http://localhost:5678;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Cloudflare (free rule):** create a Configuration Rule matching `https://n8n.example.com/signin*` that sets the `X-Robots-Tag: noindex, nofollow` response header. Same effect, zero server changes.

This doesn't remove an existing flag — only Fix 2 does — but it stops search engines from associating your login screen with a "public deceptive page" in the first place.

## Fix 4: Reputation hygiene so it doesn't come back

- **Consider a subdomain without "n8n" in it.** The forum case found Google was more likely to flag `n8n.<domain>`; `automate.<domain>` or `workflows.<domain>` had an easier time. It's anecdotal, but on a fresh flag, renaming the subdomain before you build history is cheap.
- **Harden the public surface** so every scanner sees a serious app: strong owner password + 2FA on the n8n owner account (`N8N_OWNER_ACCOUNT` setup), keep the image pinned and updated (`n8nio/n8n:2.x`), and put the editor behind your VPN/Tailscale while leaving only the `/webhook/*` paths public if you need external webhook callbacks.
- **Verify webhooks still work after proxy changes.** After touching Nginx, test a live webhook: `curl -X POST https://n8n.example.com/webhook-test/<id> -d '{}'` should hit your test listener — a mis-edited proxy config can both 502 your webhooks and confuse a re-crawl.

## How to verify it's fixed

1. Search Console → Security issues shows **"No issues detected."**
2. The [Safe Browsing site status](https://transparencyreport.google.com/safe-browsing/search?url=n8n.example.com) (paste your own domain) reports the site as not dangerous.
3. Chrome opens your n8n with no interstitial; other browsers clear automatically since they read the same lists.

## Prevent it next time

Before pointing DNS at a fresh n8n subdomain, run this 10-minute checklist:

- Deploy behind the reverse proxy with the `X-Robots-Tag: noindex` rule on auth routes **from day one**.
- Verify the Search Console property for the new subdomain the same day — you'll want the Security issues tab already available if a flag appears.
- Name the subdomain something neutral (avoid trademark/lookalike strings Googlebot associates with phishing kits).

## FAQ

### Is a "Deceptive site ahead" flag ever real for n8n?

It can be — exposed n8n instances are genuinely attacked (see our [exposed-n8n hardening checklist](/blog/censys-114000-exposed-n8n-hardening-checklist/)). But a *fresh, private* instance flagged within days of deployment, pointing at `/signin`, with clean VirusTotal/Quttera scans, is the documented false positive from #41280.

### Will this affect my webhooks or integrations?

No — the flag is purely a browser warning driven by Safe Browsing lists. API calls, webhooks, and integrations keep working. But fix it anyway: anyone clicking your n8n link sees a red screen, which kills trust and can spook OAuth approvals.

### How long until the warning disappears?

Phishing/social-engineering reviews usually resolve in about **24–72 hours** after the request. The warning vanishes from browsers shortly after Google clears the property. There's no expedite button.

### Should I file a GitHub issue too?

#41280 already documents the missing `noindex` behavior — add your reproduction there instead of opening a duplicate. The proxy-level `X-Robots-Tag` in Fix 3 is the workaround until n8n ships it natively.

## Conclusion

A fresh self-hosted n8n looks like a phish to Googlebot: new cert, bare login screen, zero reputation. The fix sequence is prove-clean (VirusTotal + Quttera), request review in Search Console's Security issues with a precise false-positive explanation, then lock the auth pages out of crawlers with `X-Robots-Tag: noindex` at the proxy — and next time, give the subdomain a neutral name before DNS goes live.

Related: [Fix n8n Out of Memory Crashes in Docker Compose](/blog/fix-n8n-oom-crash-docker-compose/) · [Censys: 114,000 Exposed n8n Hardening Checklist](/blog/censys-114000-exposed-n8n-hardening-checklist/)

Images: Unsplash / Pexels
