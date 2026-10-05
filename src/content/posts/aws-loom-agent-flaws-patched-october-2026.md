---
title: "AWS Patched Critical Flaws in Loom, Its AI Agent Platform — Upgrade to 1.7.0 Now"
description: "AWS disclosed 3 critical flaws in Loom (auth bypass, OAuth token theft, SSRF) on Oct 2, 2026, plus a SageMaker command-injection flaw. Patch guide."
date: 2026-10-06
category: news
tags: ["aws", "security", "CVE", "AI agents", "Loom", "MCP", "SageMaker"]
draft: false
featured: false
image: "/og/aws-loom-agent-flaws-patched-october-2026.webp"
---

On October 2, 2026, AWS published security bulletin 2026-124-AWS covering four vulnerabilities in its AI agent infrastructure: three in **Loom**, the AWS Labs open-source AI agent orchestration platform, and one in **SageMaker Unified Studio**. The worst of the Loom flaws, tracked as **CVE-2026-103956**, lets any network client take full administrative control of an agent control plane without logging in — but only when the deployment runs without an identity provider configured. The other two Loom flaws let an authenticated user steal OAuth tokens or probe internal network addresses, and the SageMaker flaw allows command injection into another user's Studio Space. AWS's recommendation is direct: **upgrade Loom to 1.7.0 and restart affected SageMaker Spaces**. If you run either, this post tells you exactly what broke, whether you're exposed, and what to do about it.

**Loom** is the agent control plane here: it registers tool servers, stores integration credentials, and manages the IAM role policies attached to your agents. That makes it a concentration point of trust — the same pattern as GitLab's AI Gateway flaw I covered earlier this week. The lesson keeps repeating: whoever controls the agent broker controls everything the agents can touch.

## What the three Loom flaws are

### CVE-2026-103956 — Authentication bypass (CWE-306, CWE-1188)

An issue in Loom's authentication dependency in versions **before 1.6.1** allows any network client to obtain full administrative authority over the agent control plane — **via any request to the application API** — in a deployment where no identity provider (IdP) is configured. That's missing authentication for a critical function (CWE-306) plus insecure default resource permissions (CWE-1188). With that access, an attacker could register malicious tool servers, read stored integration credentials, and rewrite the IAM role policies attached to managed agent roles.

> **Warning:** "no identity provider configured" is the key condition. If your Loom deployment never wired up an IdP — common in test, demo, or hastily-provisioned environments — this flaw treats every anonymous request as admin. The gap is widest exactly where the deployment was set up fastest.

AWS fixed this in **Loom 1.6.1** (released August 4, 2026), but the bulletin says to skip it and go straight to 1.7.0, which also fixes the two issues below.

### CVE-2026-103957 — OAuth2 token and credential disclosure (CWE-918, CWE-201)

An issue in the OAuth2 discovery handling in Loom versions **before 1.7.0** allowed an authenticated user with the `mcp:write` or `a2a:write` scope to configure a malicious well-known discovery URL. The backend then sent OAuth2 client secrets or another user's access token to an attacker-controlled endpoint. The 1.6.1 release blocked internal-address reach for this code path but did not fully close the token disclosure — **only 1.7.0 fully resolves it**.

This one deserves attention because `mcp:write` (Model Context Protocol, the open standard for exposing tools to AI models) and `a2a:write` (Agent2Agent, the protocol agents use to talk to each other) are scopes that a legitimate integration developer would hold. An authenticated attacker — or a compromised integration account — could siphon OAuth client secrets through a configuration field that looks entirely routine.

### CVE-2026-103958 — SSRF-style outbound request handling

The third Loom issue, in versions **before 1.7.0**, let a user with `mcp:write` or `a2a:write` permissions force Loom's MCP tool-server or A2A remote-agent logic to connect to arbitrary internal destinations and return the responses. In AWS terms, the dangerous endpoint is the **container credential-vending service**: hit it, and you get temporary AWS credentials for the environment's role. This is the classic server-side request forgery pattern applied to agent infrastructure.

![Server racks in a modern data center](/images/aws-loom-agent-flaws-patched-october-2026/datacenter.jpg)

## The SageMaker flaw: CVE-2026-104019

The fourth vulnerability is an **OS command injection** in the SageMaker Distribution startup scripts — the scripts that run when a SageMaker Unified Studio Space starts. Affected versions are **before 2.14.12, 3.9.12, 4.0.11, 4.1.11, 4.2.8, and 4.3.5** (4.4.3 and 4.5.x are unaffected). A project member could execute arbitrary code in another user's SageMaker Space — and if Trusted Identity Propagation is enabled, potentially steal temporary execution-role credentials from that space. The fix is to **restart affected Studio Spaces** so they pick up patched images.

![Close-up of server hardware in a datacenter](/images/aws-loom-agent-flaws-patched-october-2026/servers.jpg)

## Who must act

| Your setup | Action needed |
|---|---|
| Loom for AWS **below 1.7.0** | **Upgrade to 1.7.0 immediately** (don't stop at 1.6.1) |
| Loom below 1.6.1 **without an IdP configured** | Treat as highest priority — anonymous admin takeover is possible |
| Forked or derivative Loom code | Port the fixes from the official 1.7.0 release |
| SageMaker Unified Studio Spaces on an affected distribution | **Restart the spaces** to pull patched images |
| SageMaker Spaces on 4.4.3 / 4.5.x | None — unaffected |

AWS's bulletin states that the 1.6.1 release (August 4, 2026) addressed the auth bypass and partially addressed token disclosure, but only **1.7.0** fully fixes all three Loom issues. The patched versions exist today — the advisory was published October 2, 2026, and AWS's recommendation is explicit: upgrade to the latest version (1.7.0) and make sure any forked or derivative code incorporates the new fixes.

## Step 1 - Check your Loom version

Find the Loom version you're running — check the deployment you provisioned (container image tag, Helm release, or the version shown in the Loom admin UI). If it's anything below 1.7.0, you're affected by at least one of these flaws. If it's below 1.6.1 and you never configured an identity provider, treat this as a **critical, unauthenticated exposure** and patch today.

> **Note:** forked or re-branded Loom deployments don't report the upstream version tag. If your team built on Loom's code, check the upstream commit your fork tracks against and compare with the fixes in 1.6.1 and 1.7.0.

## Step 2 - Upgrade to Loom 1.7.0

Upgrade to the latest version (1.7.0) following your deployment's normal path — replace the image tag or re-run the Helm upgrade, then verify the running version reports 1.7.0. This single step closes the auth bypass (fully fixed in 1.6.1, included in 1.7.0), the OAuth token disclosure (fully fixed in 1.7.0), and the SSRF (fixed in 1.7.0).

## Step 3 - Restart affected SageMaker Spaces

If you use SageMaker Unified Studio, check the SageMaker Distribution version in each Space. Anything below the fixed lines (2.14.12, 3.9.12, 4.0.11, 4.1.11, 4.2.8, 4.3.5, depending on your line) needs a restart so it pulls the patched image. Spaces on 4.4.3 or 4.5.x are fine as-is.

## Step 4 - Audit for the things the bulletin can't check

AWS's bulletin, like GitLab's last week, offers no detection guidance — no way to check whether a gateway or control plane was already attacked before patching. After upgrading:

- **Rotate stored integration credentials** registered in Loom. If CVE-2026-103956 was reachable in your environment, those credentials were readable by an unauthenticated attacker. Rotating them is the only way to close that window.
- **Review IAM role policies** attached to managed agent roles for changes you didn't make. The auth bypass explicitly allowed rewriting them — a change there outlives the patch.
- **Audit the `mcp:write` / `a2a:write` holders.** Those scopes are exactly the privileges needed for the token-disclosure and SSRF flaws. Tighten who holds them and whether they still need them.

## What this pattern is telling us

This is the second critical agent-infrastructure disclosure this month, after GitLab's AI Gateway flaw on the same day. Both hit the same architectural weak point: the broker between the agent and everything else — credentials, tools, model providers — is a privilege concentration point, and it's being built fast enough that classic mistakes (missing auth checks, unsanitized outbound requests, command injection in startup scripts) are shipping in production code. The CWE-306 on CVE-2026-103956 is about as basic as it gets: a critical function with no authentication check.

One honest limit: as of this writing there is **no public proof of concept and no confirmed in-the-wild exploitation** reported for these flaws. Treat that as a snapshot, not a comfort — the advisory is four days old.

## FAQ

### Is Loom widely deployed enough for this to matter?

Loom is an AWS Labs open-source project, so production counts aren't public. But the exposure model matters more than headcount: any deployment without an IdP was remotely administrable, and the token-disclosure flaw is reachable by any authenticated user with common integration scopes. If you deployed Loom, check it.

### Do I need 1.7.0 if I already have 1.6.1?

Yes. 1.6.1 fixed the auth bypass and partially mitigated the token disclosure, but CVE-2026-103957 (full token disclosure) and CVE-2026-103958 (SSRF) require 1.7.0. AWS's bulletin explicitly recommends upgrading to 1.7.0.

### Does this affect SageMaker users who don't use Unified Studio Spaces?

The SageMaker flaw (CVE-2026-104019) is in the SageMaker Distribution startup process used by SageMaker Unified Studio. If you don't use Studio Spaces, this one doesn't apply to you — but the Loom flaws are independent of SageMaker.

## Key Takeaways

1. **AWS patched three Loom flaws on Oct 2, 2026** — an unauthenticated admin-takeover auth bypass (CVE-2026-103956), an OAuth token disclosure (CVE-2026-103957), and an SSRF-style flaw (CVE-2026-103958) — plus a SageMaker command-injection flaw (CVE-2026-104019).
2. **Upgrade Loom to 1.7.0**, not 1.6.1 — only 1.7.0 fully closes all three. Restart affected SageMaker Spaces to pull patched images.
3. **No IdP + old Loom = remotely administrable agent control plane.** If that was your setup, patch today and assume worst case.
4. **After patching, rotate credentials and audit IAM role policies** — the bulletin can't tell you whether you were attacked before you patched.
5. **The broker is the new bullseye.** Agent control planes concentrate credentials and tool access; the same class of classic bugs keeps showing up there first.

Next: if you run agents through n8n, the same audit habit applies — check who holds admin and who can register MCP tool servers in your own deployment, before a bulletin tells you to.

Images: Unsplash
