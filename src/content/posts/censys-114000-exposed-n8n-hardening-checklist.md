---
title: "Censys Counted 114,000 Exposed n8n Instances: Your Self-Hosted Hardening Checklist"
description: "Censys's 2026 report: n8n is the most exposed AI product online (114,000 hosts). A 6-step checklist to harden your self-hosted instance."
date: 2026-10-15
category: news
tags: ["n8n", "security", "self-hosted", "hardening", "docker"]
draft: false
featured: false
image: "/og/censys-114000-exposed-n8n-hardening-checklist.webp"
---

Censys published its fifth annual State of the Internet Report yesterday (October 14, 2026), and the headline number for our corner of the internet is uncomfortable: **n8n is the single most widely exposed AI product on the public internet — 113,926 hosts and counting.**

Exposed AI infrastructure grew 63% in nine months (from October 2025 to July 2026), reaching nearly 268,000 systems, according to the Censys Advanced Research Collective's analysis of the Censys Internet Map. These are not just chatbots — they are the behind-the-scenes tools connecting AI to data, applications, and user accounts. And the worst stat: among n8n hosts with parseable versions, **76% were running a version within the affected range of at least one recent critical vulnerability.**

If you self-host n8n, this post is for you. By the end, you will have run through a six-step checklist that takes your instance from "probably on the list" to "hardened" — most of it in under an hour.

## What the report actually says

The numbers that matter for n8n builders:

- **n8n: ~114,000 exposed hosts**, the most exposed AI product measured. Second place is OpenClaw (~54,000), the personal AI agent assistant.
- **Where they live:** the US (62,687), China (42,511), and Germany (31,222) account for just over half of all exposed AI infrastructure.
- **Patch posture is the killer:** 76% of n8n instances with a detectable version were vulnerable to at least one recent critical flaw. Exposure is bad; unpatched exposure is the whole ballgame.
- **Bonus finding that breaks a common habit:** 68% of exposed HTTP(S) services and 34% of SSH services sat on **non-standard ports**. Running n8n on port 5679 instead of 5678 does not hide you from internet-wide scanners — it just annoys your team.

Censys also found roughly 134,000 internet-exposed hosts running industrial control systems (ICS), with about 70% on consumer and mobile networks — a reminder that "exposed by accident" is the default failure mode of the modern internet, not a rare event.

Source: [Censys 2026 State of the Internet Report](https://www.prnewswire.com/news-releases/censys-2026-state-of-the-internet-report-finds-exposed-ai-infrastructure-grew-63-in-nine-months-302908111.html) (released October 14, 2026), with n8n-specific figures summarized in [this independent breakdown](https://cyber.hendryadrian.com/article/3184/censys-report-highlights-internet-exposure-blind-spots-in-ai-ics-and-legacy-software).

![Rows of server racks in a data center aisle, the kind of infrastructure the Censys report scans](/images/censys-114000-exposed-n8n-hardening-checklist/racks.jpg)

*Censys continuously scans the entire internet — if your n8n answers on a public IP, it is almost certainly in their data.*

## Prerequisites

- SSH access to the machine running your n8n instance.
- Your n8n is self-hosted (Docker, npm, or a VPS install). n8n Cloud users: most of this is handled for you — skip to Step 4 for the version check.
- A domain name pointing at your server (needed for the TLS step). No domain yet? Do Step 5's VPN approach instead and get the domain later.

**Terminology:** `<your-domain>` = your server's public domain (e.g. `n8n.example.com`). `<your-port>` = the port n8n listens on (default `5678`).

## Step 1 - Check whether you are exposed

Before changing anything, confirm your current exposure. Two free checks:

1. **Censys itself:** go to [search.censys.io](https://search.censys.io), create a free account, and search for your server's public IP or domain. If your n8n login page shows up, scanners have you.
2. **From your own terminal**, see what your server answers on the open internet:

```bash
# Run from a machine OUTSIDE your network (not from the server itself)
curl -s -o /dev/null -w "%{http_code}\n" http://<your-domain>:<your-port>/
```

A `200` with an n8n login page means anyone on the internet can reach your editor. A connection timeout means you are already firewalled — skip ahead to Step 4 for the patch check.

> **Warning:** if Step 1 showed your editor is reachable AND you have no login configured (Step 2), treat this as urgent — anyone can open your workflows, read your credentials store entries, and execute workflows against your connected accounts.

## Step 2 - Turn on authentication (or verify yours works)

n8n self-hosted instances should never serve the editor without a login. If you can open your editor in an incognito window without being asked for credentials, fix this now.

For a Docker Compose install, add to your `docker-compose.yml` (or `.env` file):

```yaml
environment:
  - N8N_BASIC_AUTH_ACTIVE=true
  - N8N_BASIC_AUTH_USER=<your-username>
  - N8N_BASIC_AUTH_PASSWORD=<a-long-random-password>
  - N8N_BLOCK_ENV_ACCESS_IN_NODE=true
```

Why each key matters:

- `N8N_BASIC_AUTH_ACTIVE` / `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` — forces a username/password prompt on the editor. This is the single highest-value change on this list.
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` — stops Code and Execute nodes from reading your process environment variables (where API keys and secrets often live). Enabled by default in recent n8n versions; set it explicitly so an upgrade never silently relaxes it.

Recreate the container (`docker compose up -d`), then open the editor in an incognito window. **You should see a login prompt.** If you don't, the variables didn't take — check for typos and that you edited the right compose file.

## Step 3 - Put a reverse proxy with TLS in front

Exposed HTTP on port 5678 means login credentials travel in cleartext. Caddy is the fastest way to fix this — it fetches a free Let's Encrypt certificate automatically:

```caddy
n8n.<your-domain> {
    reverse_proxy localhost:<your-port>
}
```

That's the whole file for the common case. Point your DNS at the server, run `caddy run`, and `https://n8n.<your-domain>` gets a valid certificate within a minute. Then close port `<your-port>` to the internet in your firewall — the proxy is the only thing that should talk to n8n directly:

```bash
sudo ufw deny <your-port>
sudo ufw allow 80,443/tcp
```

You should see: port scan of your server shows only 80/443 open, and `https://` loads n8n with a valid certificate.

## Step 4 - Patch n8n now (the 76% step)

This is the step the report is really about. Three out of four exposed n8n instances were running versions with known critical vulnerabilities — and the n8n [October 2026 security update](https://cortexflow.tech/blog/n8n-october-2026-security-update/) alone patched 14 advisories. Check your version in the n8n UI (bottom-left, Settings) and compare against the latest release:

```bash
# Docker Compose install: pull and restart with the latest stable image
docker compose pull n8n
docker compose up -d n8n
docker exec <n8n-container-name> n8n --version
```

You should see a version matching the current release line (2.43.x as of October 15, 2026 — verify against [n8n's releases page](https://github.com/n8n-io/n8n/releases)). Then re-check Censys or the UI: your version should no longer fall in any advisory's affected range.

![A person typing on a laptop in a dark room — attackers automate scanning for unpatched instances](/images/censys-114000-exposed-n8n-hardening-checklist/laptop.jpg)

*Unpatched instances get found by automation, not by humans picking targets. Patching removes you from the easy list.*

> **Note:** if you still run n8n via npm or npx, this is your deadline pressure too — [n8n 3.0 drops npm/npx installs entirely](https://cortexflow.tech/blog/n8n-npm-to-docker-migration/). Migrate to Docker first, then patch.

## Step 5 - Shrink the attack surface: firewall + editor access

Even patched and logged-in, an editor facing the whole internet is a standing invitation to password-spraying bots. Pick one:

**Option A — IP allowlist (simplest).** In your reverse proxy, only allow your office/home IPs on the editor paths, while leaving `/webhook/*` paths open for integrations:

```nginx
# nginx example: editor locked down, webhooks public
location / {
    allow 203.0.113.0/24;   # your office IP range
    deny all;
    proxy_pass http://localhost:<your-port>;
}
location /webhook/ {
    proxy_pass http://localhost:<your-port>;
}
```

**Option B — VPN only (strongest).** Put the editor behind Tailscale or WireGuard and expose *only* webhook URLs publicly. Nothing on the internet can even start a login attempt.

Remember the report's non-standard-port finding: changing the port is not a defense. Scanners enumerate all 65,535 ports. Authentication, TLS, patching, and network restriction are defenses; obscurity is decoration.

## Step 6 - Verify everything and schedule the next check

Run this final pass and set a calendar reminder:

1. Incognito window: editor requires login — confirmed.
2. `curl` from outside: only 443 answers; direct port is refused — confirmed.
3. n8n version matches the current release line — confirmed.
4. Search your domain on Censys again in 48 hours — your instance should show the updated version, or nothing at all if you went VPN-only.

Then make it recurring: subscribe to [n8n's security advisories](https://docs.n8n.io/hosting/security/) and re-run this checklist quarterly. The Censys trend line is one direction — exposure grew 63% in nine months — so "set and forget" is how instances end up in next year's report.

## FAQ

### Is my n8n really at risk if I only use it for personal automations?

Yes — arguably more. Personal instances tend to run older versions with weaker passwords, and they hold the same credentials (Gmail, Stripe, GitHub) an attacker wants. The 76%-unpatched figure includes exactly these installs.

### Does n8n Cloud have this problem?

No. Cloud instances sit behind n8n's own hardened infrastructure with forced authentication. This checklist is for self-hosted instances — Docker, npm, or bare VPS installs.

### I use a non-standard port. Am I safe?

No. Censys's report explicitly found most exposed services on non-standard ports — 68% of HTTP(S) and 34% of SSH. Scanners do not care about your port number.

### How often should I update n8n?

At minimum, within days of any security advisory. n8n ships advisories through its docs and the October 2026 batch had 14 of them. A quarterly calendar reminder is the floor; same-week patching for security releases is the goal.

## Key Takeaways

1. **Censys's October 14 report names n8n the most exposed AI product on the internet** — ~114,000 hosts, with 76% of version-detectable instances running vulnerable versions.
2. **The fix is four layers, not one:** forced authentication, TLS via reverse proxy, current patched version, and network restriction (firewall/VPN/IP allowlist).
3. **Non-standard ports are not security** — the report proves scanners find them routinely.
4. **Patching is the highest-leverage step** — exposure plus a known CVE is what turns a scan result into a breach.

Next: run Step 1 right now — it takes two minutes and tells you which half of this checklist is urgent for you. Then read our [n8n October 2026 security update](https://cortexflow.tech/blog/n8n-october-2026-security-update/) to see exactly which 14 advisories your patch covers.

*Images: Pexels*
