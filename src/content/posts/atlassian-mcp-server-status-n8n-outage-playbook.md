---
title: "Atlassian MCP Server Status: The Nov 23 Outage, the Right Status Page, and the n8n Checks That Help"
description: "Atlassian MCP status is a Breakout trend after the Nov 23 outage. Check the right status page, run three probes, and wire n8n to fail safely."
date: 2026-11-28
category: news
tags: ["mcp", "n8n", "atlassian", "jira", "ai agents"]
draft: false
featured: false
image: "/og/atlassian-mcp-server-status-n8n-outage-playbook.webp"
---

"atlassian mcp server status" is a Breakout rising query for "MCP server" in Google Trends (US, past 7 days) this week. The search has a concrete cause: on November 23, 2026, Atlassian Rovo authentication degraded for about five and a half hours, and its MCP component went into partial outage with it.

MCP (Model Context Protocol) is the open standard that lets an AI model call external tools. The Atlassian Rovo MCP Server is Atlassian's hosted MCP server for Jira, Confluence, and related Atlassian Cloud apps, so when its sign-in service fails, every agent wired to it fails at once.

By the end of this article you will know which status page actually reports MCP health, how to tell an Atlassian-side outage from a broken sign-in in three checks, and how to wire the server into n8n so the next incident pauses your workflow instead of corrupting it.

## What happened on November 23

Atlassian Rovo opened an incident at 15:19 UTC on November 23, 2026. OAuth token requests could fail or time out, and related services could be unavailable or degraded. The MCP component entered partial outage at 16:08 UTC, a mitigation was reported at 16:33 UTC, and the incident resolved at 20:45 UTC — 5 hours 26 minutes end to end, per the [incident timeline](https://stackpulse.app/services/atlassian-rovo/outages/2026-11-23-1520) read from Atlassian Rovo's own status page.

| Time (UTC, Nov 23) | What the status page reported |
| --- | --- |
| 15:19 | Investigating; authentication and user management in partial outage |
| 16:08 | MCP component in partial outage |
| 16:33 | Fix in place, monitoring; some users could still see errors |
| 20:45 | Resolved; authentication and MCP back to normal |

Two details matter for builders. First, existing sessions failed too — this was not only a new-sign-in problem. Second, Atlassian said the cause had been identified but did not state what it was, so any article claiming a root cause is guessing.

There is also a current operational wrinkle: Atlassian's MCP changelog notes support-portal maintenance from November 27 to 30, 2026, with requests moving to Atlassian Support from November 30. If you need help this weekend, expect that transition.

## The status page most people check is the wrong one

MCP health lives on the [Rovo status page](https://rovo.status.atlassian.com/), where MCP is its own component, listed separately from Chat, Search, and Agents. The main Atlassian status page is a directory of product status pages and does not carry the MCP component.

This is not a theoretical trap. During the November 23 incident, the user who reported the failure on GitHub was watching the main status page at 15:43 UTC, saw nothing, and had already seen failures on and off for a day. A green main page proves nothing about MCP.

**Bookmark the Rovo page, and check the MCP component first — before you touch credentials.**

## Three checks: is it Atlassian, or is it you?

Run these in order. Each one rules out a class of failure, and together they take about a minute.

**Check 1 — the Rovo status page.** If the MCP component shows an incident, stop. No new sign-in, reinstall, or token will fix a server-side outage, and removing a working connector mid-incident can leave you unable to sign in again until it ends.

**Check 2 — an unauthenticated probe.** A healthy server refuses a tokenless call immediately:

```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" -X POST https://mcp.atlassian.com/v2/mcp

curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" \
  https://auth.atlassian.com/.well-known/oauth-authorization-server
```

The first command posts to the MCP endpoint with no token; the second asks the sign-in service for its public configuration. On November 24, 2026, a healthy setup returned **401** from the first in 0.11 to 0.63 seconds and **200** from the second. On November 23, users got 503 from the sign-in service instead. If either call hangs or answers 5xx, the fault is on Atlassian's side or in your network — wait and retry.

**Check 3 — your scopes.** Ask the agent to call `getAccessibleAtlassianResources` and show the result. Your site should appear with a list of `scopes`. An empty list means the sign-in grant is broken, whatever your client claims about being connected.

![An isometric triage press: a failing connection enters under three gauges — a status lamp, an unauthenticated probe dial, and a scope gauge — and only a connection that passes all three reaches the output tray, while the orange-lit MCP lamp marks the component that failed on November 23.](/figures/atlassian-mcp-server-status-n8n-outage-playbook-triage-press.svg)

*Figure 1: The triage press. The three gauges are the three checks — Rovo status page, unauthenticated probe, and scope list — and the orange lamp is the MCP component that entered partial outage at 16:08 UTC on November 23. Notice the readout: the whole incident ran 15:19–20:45 UTC, and reconnecting fixed none of it.*

## The endpoint and sign-in rules you must get right

Atlassian's [getting-started guide](https://developer.atlassian.com/cloud/rovo-mcp/guides/getting-started/) gives one current address for new setups:

```text
https://mcp.atlassian.com/v2/mcp
```

Gateways that need a complete, paginated tool list instead of dynamic discovery use `https://mcp.atlassian.com/v2/mcp?tools=all`. Version 2 replaces the older v1 addresses, and v1 sign-ins do not carry over — remove the old entry, add v2, and sign in once.

Authentication runs on OAuth 2.1 by default, and every action respects the signed-in user's existing Atlassian permissions. One sign-in covers **one site**: tokens are consented for a specific cloud ID, so a second site needs a second sign-in. Atlassian tracks multi-site connections as an open request (125 votes on November 24, 2026, no date given).

For unattended automation, interactive OAuth is the wrong tool. Atlassian offers API-token authentication as an alternative for non-interactive scenarios **only if an organization admin has enabled it**. If your n8n workflow runs on a schedule with nobody present to complete a browser sign-in, that admin switch is a prerequisite, not an optimization. Some tools also consume Rovo credits — Atlassian states the vast majority of calls cost 1–10 credits each — so an agent loop is a metered loop.

## Failure modes that look like outages but are not

A detailed [troubleshooting survey](https://simplify-software.org/blog/atlassian-mcp-troubleshooting) read on November 24, 2026 separates the look-alikes:

| Symptom | Likely cause | First move |
| --- | --- | --- |
| 403 "The app is not installed on this instance" | The grant lost its scopes | Clear authentication fully, then connect again |
| "Session not found" (404, code -32001) | The MCP session ended; the token may still be good | Reconnect to start a new session |
| 502, 503, a hang, "upstream connect error" | Atlassian's side | Status page, then wait |
| 429 | Too many calls at once | Fewer parallel calls; honor `Retry-After` |
| Only 20 worklogs returned | Embedded field cap in older tools | Use the paged `listJiraIssueWorklogs` tool in v2 |

The 403 case deserves emphasis because the obvious fix fails. In one published log, 209 of about 1,550 calls in a month (13%) returned this error with empty scopes, and pressing Reconnect left the scopes empty; clearing authentication and accepting the consent screen again restored them. **Reconnect is not a repair. Clear, then connect.**

Two more traps: if a token expires, Atlassian warns the session can fail silently, and an agent may answer from memory — ask which tool it called and what came back. And the 20-worklog cap is a data-integrity bug, not a display limit: a ticket with 32 entries returned 20 with no path to the rest, so time summed from it is too low. Version 2's paged worklog tool, implemented November 6, 2026, is the fix.

On rate limits, honesty matters: no confirmed MCP-specific number appears in Atlassian's English docs as of November 24, 2026. Community posts quote hourly figures by plan, but treat them as unconfirmed. What users actually hit is a burst — one report reached 429 at about 20 parallel calls. Design for bursts, not for a published quota.

## Wire it into n8n so the next outage pauses, not corrupts

The pattern below assumes the [MCP Client Tool](/blog/how-to-connect-mcp-server-n8n/) in an n8n AI Agent node pointed at the v2 endpoint over HTTP Streamable transport. If the connection misbehaves, the [MCP troubleshooting checklist](/blog/mcp-n8n-troubleshooting/) covers the n8n side.

1. **Check status before you call.** Start the workflow with an HTTP Request to the Rovo status page (or the unauthenticated probe) and branch: incident active means queue the work and notify a human, not retry blindly.
2. **Serialize calls.** Run Atlassian calls one after another, or a few at a time. Parallel subagents each open their own burst, and bursts are what trigger 429.
3. **Retry once, after a pause.** On 502/503, wait, retry once, then stop and log. On 403 with empty scopes, do not retry at all — route to a human to clear authentication.
4. **Gate every write.** Reads can flow automatically; creating or updating Jira work items and Confluence pages waits behind a human approval step, because the server acts with real user permissions.
5. **Log the receipt.** Record the tool called, the site (cloudId), the result count, and the error verbatim. When Atlassian asks for the UTC time, endpoint, tool, and `Atl-Request-Id` header, your log already has them.

Pin the `cloudId` and limit result sizes in the agent's instructions. Every rediscovery call — listing sites, listing projects — spends Rovo credits and burst budget to learn something your workflow already knows.

## Honest limits

This wiring pattern is verified against Atlassian's official guide and the November 24 troubleshooting survey, not live-tested against an Atlassian Cloud tenant for this article. The November 23 root cause was not stated by Atlassian. The MCP rate limit is unconfirmed. Multi-site OAuth remains one sign-in per site until Atlassian ships the requested change. If your organization has not enabled API-token authentication, unattended n8n runs against this server are not yet a supported shape — that is an admin decision to secure first, not a configuration detail to work around.

## FAQ

### Is the Atlassian MCP server down right now?

Check the MCP component on the Rovo status page, then run the two unauthenticated curl probes above. A fast 401 from the endpoint plus a 200 from the sign-in service means the server is up and your problem is local — most likely scopes or an expired session.

### Why does Atlassian MCP keep disconnecting?

Often the sign-in grant went stale rather than the network failing. Empty scopes behind a 403 "app is not installed" error are the signature. Clear authentication completely and connect again; Reconnect alone left scopes empty in published logs.

### Can one Atlassian MCP connection cover several sites?

No. One OAuth sign-in covers one site. Run one entry per site, or use an admin-enabled API token and pass the cloudId on each call.

### What should my n8n workflow do during an Atlassian outage?

Pause and queue. Detect the incident with a status check, retry a 5xx once after a pause, never retry a scope 403, and keep writes behind human approval so a half-failed run cannot leave partial updates behind.

## Key Takeaways

1. **MCP health lives on the Rovo status page** — the main Atlassian status page does not report it, and a green page there proved nothing on November 23.
2. **Three checks separate outage from sign-in failure:** status page, unauthenticated probe (401 fast is healthy), and a non-empty scope list.
3. **Clear authentication; do not just reconnect** — empty scopes survive Reconnect and caused 13% of calls to fail in one published log.
4. **One sign-in is one site, and headless runs need admin-enabled API tokens** — interactive OAuth does not suit unattended n8n schedules.
5. **Serialize calls and gate writes** — bursts trigger 429, credits meter every call, and the server acts with real user permissions.

Next step: add the status-check branch to one existing n8n workflow this week and run the two curl probes by hand once, so you know what healthy looks like before the next incident teaches you under pressure.

*Sources: Atlassian Rovo MCP getting-started guide (developer.atlassian.com), Rovo status incident timeline for November 23, 2026, and the Atlassian MCP troubleshooting survey read November 24, 2026.*
