---
title: "n8n October 2026 Security Update: 14 Advisories Patched — Upgrade Your Self-Hosted Instance Now"
description: "n8n patched 14 advisories on Oct 1, 2026 (10 High). Self-hosted users below v1.123.83, v2.41.4, or v2.42.1 must upgrade now."
date: 2026-10-02
category: news
tags: ["n8n", "security", "CVE", "self-hosted", "upgrade"]
draft: false
featured: false
image: "/og/n8n-october-2026-security-update.webp"
---

n8n's security team published its bi-weekly security update on October 1, 2026, and this one is worth your attention: **14 advisories, 10 rated High**, including credential-theft paths in shared workflows, an unauthenticated OAuth persistence flaw, and a stored XSS in the Chat Trigger. The fixes are already live in **n8n v1.123.83, v2.41.4, and v2.42.1**. n8n Cloud instances were patched automatically — self-hosted instances were not. If you're running a self-hosted n8n below those versions, here's exactly what broke, how worried to be, and how to upgrade without breaking your workflows.

A **security advisory** is n8n's formal write-up of a single vulnerability (tracked on GitHub as `GHSA-…` identifiers). A **CVE** is the industry-wide catalog entry for the same bug. You don't need to memorize either list — you need the fixed version for your release branch and a safe upgrade path.

## The advisories that matter most

Fourteen advisories is a lot, so I'll group the ones with the widest real-world blast radius for self-hosted builders.

### 1. Credential exposure in shared workflows (High)

Two advisories fix holes in how n8n checks credentials for shared workflows. The credential check **missed nested and tool inline sub-workflows** (GHSA-r6g9-5cpp-ppwr) and **missed Agent Node parameter credentials** (GHSA-x25p-9mr6-cwgp). Relatedly, CVE-2026-103247 (CVSS 8.5) covers **credential tampering via duplicate node IDs** in versions before 1.123.80, and CVE-2026-103246 (CVSS 7.7) covers **credential disclosure via node-tool introspection** in versions before 2.39.6.

**What that means in plain language:** a low-privilege editor on your instance could, in the right conditions, reach credentials they were never granted — API keys, OAuth tokens, database passwords your production workflows rely on. This is the highest-impact class in the batch, because n8n workflows exist precisely to *hold secrets that call real systems*.

### 2. Unauthenticated OAuth client persistence (High)

GHSA-3qcw-p65v-c7vq: an **unauthenticated** attacker could persist OAuth client registrations through the authorize endpoint, with no rate limit ("unbounded"). In a self-hosted setup exposed to the internet, this is the one an attacker doesn't even need an account for.

### 3. Stored XSS via the Chat Trigger (High)

GHSA-x5cw-hm7v-q7mj: the `customCss` parameter on the hosted chat page allowed stored XSS. If you embedded an n8n chat widget on a customer-facing page, a crafted payload could have executed JavaScript in your visitors' browsers.

### 4. The agent-flavored ones (High + Medium)

This batch has several bugs that exist only because of n8n's newer agent features:

- **Send-and-Wait HMAC bypass** (High, GHSA-728h-pmr2-7cgh): unauthenticated approval of *waiting executions* — meaning an outsider could green-light a workflow that was paused waiting for a human's approval. If you use human-in-the-loop approvals on financial or destructive actions, this one is personal.
- **MCP workflow-validation prototype mutation** (High, GHSA-5jr4-xmvf-frmj): allowed owner-account takeover through the MCP (Model Context Protocol) workflow-validation interpreter.
- **Sub-workflow inline JSON identity spoofing** (High, GHSA-866p-xg8v-g2q7): a member could spoof workflow identity for credential authorization, static data, and error-workflow dispatch.
- **Cross-user agent chat resume** (Medium, GHSA-p3pg-xw4f-m72c): hijacking another user's pending tool approval.
- **Cross-project agent ownership transfer** (Medium, GHSA-2r5r-xgvc-rj4p) and **prototype pollution in the AI workflow builder** (Medium, GHSA-3p2g-2wpm-8h3g).

The honest read: agent features (MCP, tool approvals, chat resume) are n8n's newest surface area, and they attracted the most severe bugs. That's normal for new code, and it's why the release notes emphasize these paths.

## Who needs to act

| Your setup | Action needed |
|---|---|
| n8n Cloud | None — patched automatically |
| Self-hosted, on a fixed version already | None |
| Self-hosted v1.x below **1.123.83** | Upgrade to 1.123.83+ |
| Self-hosted v2 stable below **2.41.4** | Upgrade to 2.41.4+ |
| Self-hosted v2 beta below **2.42.1** | Upgrade to 2.42.1+ |

> **Warning:** if you self-host on a version from the 1.1xx branch and your workflows use shared credentials, agent nodes, or the Chat Trigger, treat this as urgent rather than routine — those are the exact surfaces this batch fixed.

![Security patch illustration: a shield locking down connected automation nodes](/images/n8n-october-2026-security-update/patch-shield.webp)

## Step 1 - Back up before you touch anything

Upgrade steps differ by how you installed n8n, but the backup is non-negotiable for all of them.

**Export your workflows** from the editor (⋮ menu → Export, or select-all → Download) and copy them somewhere off the server. **Back up your database** — if you run the default SQLite, copy the `database.sqlite` file; if you run Postgres, take a snapshot or `pg_dump`. And most importantly: **confirm you have your `N8N_ENCRYPTION_KEY` value saved somewhere safe.** Without the exact same encryption key, your restored instance cannot decrypt stored credentials, and every credential in n8n becomes unusable. I treat the encryption key backup as step zero, not step one.

## Step 2 - Upgrade Docker deployments

For the common Docker Compose install:

```bash
# 1. Pull the patched image for your branch
docker compose pull n8n

# 2. Recreate the container with the new image
docker compose up -d

# 3. Check the logs for clean startup
docker compose logs -f n8n
```

Pin to a fixed version tag rather than `latest` — that's the whole point of this article. Use `n8nio/n8n:2.41.4` (stable) or `n8nio/n8n:1.123.83` (1.x branch). The patched tag is set in your `docker-compose.yml` under `image:`:

```yaml
services:
  n8n:
    image: n8nio/n8n:2.41.4
```

You should see `n8n ready on 0.0.0.0, port 5678` in the logs and no migration errors. Migrations run automatically on first boot of the new image; they are what fix the schema-level issues in this batch.

## Step 3 - Upgrade npm deployments

```bash
# Stop the running process first (systemd/pm2/task manager — however you run it)
npm install -g n8n@2.41.4
# then start it again
```

Verify the running version in the editor: **Settings → About** shows the exact build. It should read `2.41.4` (or your branch's fixed version) after the restart.


## Step 4 - Verify the patch and re-check your exposure

1. Confirm the version in **Settings → About**.
2. Trigger one workflow that uses shared credentials, and one Chat Trigger workflow if you have one — the two surfaces that got the biggest fixes.
3. If your instance is internet-exposed, this is a good moment to also verify your reverse proxy, firewall rules, and that the editor isn't open to the public without authentication. The OAuth persistence flaw (GHSA-3qcw-p65v-c7vq) needed *no credentials at all* — internet-exposed instances were the ones at risk.

> **Note:** n8n 2.41.4 was released September 30, 2026 as a stability release (execution tracking, database health, queue results) and became the security-fixed stable with this update. The 2.42 beta line expands AI-agent and MCP capabilities — stay on stable (2.41.4) unless you have a reason to run beta.

## What I didn't cover (honest limits)

I did not test the exploit paths for individual advisories — reproducing them against a live instance would be reckless, and the GHSA write-ups contain the details if you need them for a compliance report. I also can't tell you whether any of these were exploited in the wild before the patch; n8n's update doesn't say, and no KEV (Known Exploited Vulnerabilities) listing was cited in the sources I checked. Patch first, investigate logs second.

## FAQ

### Am I affected if I only use n8n Cloud?

No. n8n Cloud instances were patched automatically with no action required.

### Do I need to rotate my credentials after upgrading?

n8n's update doesn't say any credential was exfiltrated — these are patch advisories, not breach notifications. But if you run a multi-user self-hosted instance where untrusted people had editor access, rotating your most sensitive API keys after upgrading is cheap insurance. The credential-exposure advisories required editor-level access, so single-user instances have little to worry about.

### Where do the full advisory details live?

On the [n8n GitHub Security Advisories page](https://github.com/n8n-io/n8n/security/advisories) and the [community announcement thread](https://community.n8n.io/t/security-update-01-october-2026/318054). You can also opt into these bi-weekly updates by email from n8n's site.

### What version exactly do I need?

v1.123.83 for the 1.x branch, v2.41.4 for stable v2, v2.42.1 for the v2 beta. Anything at or above those for your branch is already patched.

## Key Takeaways

1. **n8n patched 14 advisories on Oct 1, 2026 — 10 rated High.** The worst class is credential exposure in shared workflows and agent nodes.
2. **Cloud users are already safe.** Self-hosted users below v1.123.83 / v2.41.4 / v2.42.1 must upgrade.
3. **The new agent surfaces (MCP, tool approvals, chat) drew the most severe bugs** — if you run agentic workflows, patching is urgent, not routine.
4. **Back up workflows, database, and your N8N_ENCRYPTION_KEY before upgrading** — without the key, restored credentials are unreadable.

Next: if you skipped backing up your encryption key in the past, do it now — it's the single cheapest disaster-prevention step in self-hosted n8n, and every upgrade is a reminder.

*Images: Unsplash*
