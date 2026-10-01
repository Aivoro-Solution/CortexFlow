---
title: "MCP + n8n Troubleshooting: 3 Common Fixes"
description: "MCP in n8n breaks in three predictable places: stripped headers, OAuth re-auth loops, and queue mode. Diagnosis and fixes for each, from real issues."
date: 2026-10-01
category: automation
tags: ["n8n", "MCP", "troubleshooting", "AI agents", "self-hosting"]
image: "/og/mcp-n8n-troubleshooting.webp"
draft: false
featured: false
---

MCP (Model Context Protocol, Anthropic's open standard for exposing tools and data to AI models) is the hottest thing in n8n right now — and the n8n integration has sharp edges everywhere. If you followed a "connect MCP to n8n" tutorial and things mostly worked, this is the article for the other days: the ones where the client refuses to connect, credentials demand re-authorization every session, or everything breaks the moment you scale up. In practice, MCP failures in n8n cluster in **three predictable places**: stripped request headers, OAuth re-auth loops, and queue mode. Each has a concrete diagnosis and a concrete fix. By the end you will have a troubleshooting checklist you can run in order instead of debugging blind.

**How to use this guide:** start with the symptom table, then jump to the matching section. Every section gives the failure, the root cause, and the fix.

## Symptom → section map

| Symptom | Go to |
|---|---|
| Client fails to connect, or connects but "falls back to an older protocol version" | Headers |
| Client connects but asks to authorize again every session; 401 errors | OAuth re-auth |
| MCP works on a single instance but breaks after enabling queue mode / scaling | Queue mode |
| Claude Desktop cannot register the n8n MCP server at all | Headers (fix), then Queue mode |

## Problem 1 - The headers your proxy silently eats

**The failure:** your MCP client fails to connect to n8n's MCP endpoint, or connects but misbehaves — and nothing in the n8n logs looks wrong.

**Why it happens:** MCP clients send three non-standard headers on every request: `MCP-Protocol-Version`, `Mcp-Method`, and `Mcp-Name`. n8n allows these in its CORS policy (since n8n 2.36.0), so a direct connection works. But if you run n8n behind a reverse proxy, load balancer, or web application firewall that strips unknown headers — or only forwards an allowlisted set — those headers never reach n8n. The client then fails to negotiate the protocol version, or drops to a degraded fallback. This is the most common cause of "it works locally but not through my domain."

**The fix:** add the three headers to your proxy's allowlist. With nginx, that means making sure you are not filtering them out (nginx forwards unknown headers by default, but some hardened configs and WAFs drop them — check your WAF rules first). With Traefik or a cloud load balancer, verify header passthrough is enabled and no "allowed headers" list is excluding them.

Test from outside the proxy so you test the real path:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -H "Accept: application/json, text/event-stream" \
  https://<your-n8n-domain>/mcp/<your-path>
```

**Related gotcha — "Access to request headers":** a recurring community question asks how to read raw request headers *inside* an MCP-triggered workflow. Short answer: you cannot — the MCP Server Trigger node deliberately does not expose raw headers to the workflow. The supported pattern is to put identity in the tool's input schema instead: add explicit parameters like `account_id` or `tenant_id` to the tool definition and let the calling agent supply them. If you need authentication on the trigger itself, use Header Auth on the MCP Server Trigger node, then resolve the tenant from the token inside the workflow on every call. Never try to smuggle identity through headers the trigger will not show you.

> **Note:** this is also where Claude Desktop registration failures (GitHub issue #32278) usually live. Claude Desktop speaks SSE, while newer n8n MCP endpoints prefer Streamable HTTP — a mismatch in headers or transport kills registration. The community's working workaround is a translation shim (`supergateway --sse <MCP_URL> --header "Authorization: Bearer <TOKEN>"`) in the Claude Desktop config, which adapts the transport and carries the headers through.

## Problem 2 - OAuth re-auth loops and 401s

**The failure:** the client connects, asks you to authorize, works for a while — then demands re-authorization. Or you get `401 Unauthorized` from a client whose token you are sure is valid.

**Why it happens, case A — instance-level MCP is off:** if you use n8n's built-in instance MCP server (Settings → MCP Access), the client sends you to n8n to approve access and you land on a page reading **"You do not have sufficient permissions to authorize this request."** That message is misleading: per n8n's own troubleshooting docs, it has exactly one cause — MCP access is not enabled for your instance. While the server runs, any signed-in user can approve a client; while it is off, n8n refuses everyone.

**The fix for case A:** an instance owner or admin enables MCP access in Settings → MCP Access, generates the MCP access token, and the client connects with it. Keep this token separate from your `N8N_API_KEY` — they are different credentials for different doors. If you self-host and drive the client from automation, set it as the `N8N_MCP_ACCESS_TOKEN` environment variable.

**Why it happens, case B — re-auth on the MCP Server Trigger:** community reports of "MCP Server Trigger: Requiring re-auth" trace to OAuth2 credentials whose refresh flow breaks: expired refresh tokens, revoked grants, or scopes that changed on the provider's side (the Salesforce "requested scope is not allowed" thread is the same family of failure). The symptom looks like an MCP problem; the cause is the credential.

**The fix for case B:** in n8n, open the credential, hit reconnect, and re-authorize from scratch — do not just retry the workflow. Check the provider's side for revoked or expired grants, and confirm the requested scopes still exist (providers rename scopes without telling you). If re-auth loops persist across providers, check your reverse proxy is not stripping the OAuth redirect or the headers from Problem 1 — the two failures love to travel together.

**Why it happens, case C — 401 on header auth:** the token is valid but the client sends it wrong — a classic is the `Bearer` prefix (some clients add it, some expect the raw token, some double it up as `Bearer Bearer ...`). Check the exact `Authorization` header value the client transmits; match it to what n8n expects. A reproducible community case had `hermes mcp add` fail with 401 while `hermes mcp test` succeeded against the same URL and token — the difference was how each code path constructed the header.

## Problem 3 - Queue mode breaks MCP

**The failure:** MCP works perfectly on your single instance. You enable queue mode (Redis + workers) to handle load — and MCP tool calls start failing or SSE connections drop.

**Why it happens:** the MCP Server Trigger node communicates over SSE (Server-Sent Events), which requires a persistent connection to the *same* server instance for the whole session. Queue mode splits n8n into a main instance, workers, and webhook processors. n8n's docs are explicit about the consequence: with a **single webhook replica**, the MCP Server Trigger works as expected. With **multiple webhook replicas** behind a load balancer, requests land on different instances, SSE connections break, and tool calls fail intermittently — the exact symptom in GitHub issue #26394.

**The fix:** route all `/mcp*` traffic to one dedicated webhook replica. In practice:

1. Run one webhook processor as a separate replica set (a single `n8n webhook` container).
2. In your ingress or load balancer, add a rule: everything under `/mcp*` goes to that replica only. Route `/webhook/*` and `/webhook-waiting/*` to the general webhook pool as usual, and keep the main instance out of the load-balancer pool entirely.
3. Do not scale that dedicated MCP replica horizontally — one instance is the point.

If you do not run queue mode yet and MCP is your main workload, the honest recommendation is to **stay on a single instance** until you actually need scale. Queue mode adds Redis, Postgres (SQLite is unsupported in queue mode), and this SSE routing problem — real costs for hypothetical load. The community's rule of thumb from the n8n forums: enable `EXECUTIONS_MODE=queue` when a loaded VPS starts dropping executions, not before.

A related queue-mode trap worth knowing even if MCP is not involved: large webhook responses in queue mode travel from worker back to main inside a Redis message (capped at 64 MiB by default via `N8N_WEBHOOK_RESPONSE_RELAY_SIZE_MAX`). If your MCP tools return big payloads, keep them small or move binary data to shared storage — filesystem binary storage is not supported in queue mode.

## The troubleshooting checklist, in order

When MCP breaks and you do not know which problem you have, run this top to bottom:

1. **Bypass the proxy.** Hit the MCP endpoint directly (no reverse proxy, no WAF). Works? It is Problem 1 — allowlist the three headers.
2. **Check MCP access.** Settings → MCP Access enabled? Token valid and separate from the API key? "Insufficient permissions" always means the server is off.
3. **Re-auth the credential from scratch.** Reconnect, re-authorize, verify scopes on the provider's side. Retry is not a fix for a dead grant.
4. **Inspect the Authorization header.** Exact bytes the client sends vs. what n8n expects. Watch for doubled `Bearer` prefixes.
5. **Check your topology.** Queue mode with multiple webhook replicas? Route `/mcp*` to one dedicated replica, or drop back to a single instance.
6. **Read the server logs.** `docker compose logs n8n` (or your process output) during a failing connection — n8n logs MCP connection errors, and the absence of any log line points back at the proxy eating the request.

## What this guide does not cover

Sub-agent tool-call reliability (empty tool observations, dropped calls on retries) is a separate, active bug cluster in the AI Agent node itself — worth its own guide. I also have not tested every third-party MCP client against n8n; the header and transport behaviors above are verified against n8n's documented behavior and the linked community/GitHub reports, not an exhaustive client matrix. Versions referenced: n8n 2.41.4 stable, MCP Server Trigger docs as of late September 2026.

## Key Takeaways

1. **Allowlist `MCP-Protocol-Version`, `Mcp-Method`, and `Mcp-Name` through your proxy/WAF** — stripped headers are the #1 cause of "works locally, fails through my domain."
2. **"Insufficient permissions" means MCP access is off** — enable it in Settings → MCP Access; keep the MCP token separate from your API key.
3. **Re-auth loops are credential problems, not MCP problems** — reconnect from scratch and verify scopes on the provider's side.
4. **Queue mode + multiple webhook replicas breaks SSE** — route `/mcp*` to one dedicated webhook replica, or stay on a single instance until you need scale.
5. **The MCP Server Trigger never exposes raw request headers** — put identity in the tool input schema instead of fighting the trigger.

Next: if you have not built the thing you are troubleshooting yet, start with the companion guide [How to Connect an MCP Server to n8n](/blog/how-to-connect-mcp-server-n8n/) — it covers the happy path (SSE vs Streamable HTTP, the MCP Client Tool node) that this guide assumes you have working.
