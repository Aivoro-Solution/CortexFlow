---
title: "Fix n8n MCP Client Error Hiding the HTTP Status"
description: "n8n's MCP nodes show the same blank error for 401, 429 and 503. Here is how to recover the real HTTP status and fix the actual cause."
date: 2026-11-26
category: automation
tags: ["n8n", "error-fix", "mcp", "ai-agent", "debugging"]
draft: false
featured: false
image: "/og/fix-n8n-mcp-client-error-hides-http-status.webp"
---

Your MCP tool connection fails and n8n shows you this, in full: `Streamable HTTP error: Error POSTing to endpoint:` — and then nothing. No status code, no body, no hint. That one blank message is what n8n currently shows for an expired token (401), a wrong URL (404), a rate limit (429), and a dead server (503) alike, as long as the server's error response has an empty body. By the end of this post you will know how to recover the real HTTP status in under a minute, what each status means for an MCP connection, and how to stop your workflows from failing blind while the upstream fix is pending.

Quick definitions: **MCP** (Model Context Protocol) is the open standard n8n's AI Agent uses to call external tools. The **Streamable HTTP** transport is the remote variant: the client sends JSON-RPC messages as HTTP POSTs to one endpoint, conventionally `/mcp`, and the server answers with JSON or a small event stream.

## The symptom: one blank error for four different failures

Add an MCP Client or MCP Client Tool node, point it at a Streamable HTTP server, and try to load the tool list while the server is returning an error with an empty body. The connection fails with:

```
Streamable HTTP error: Error POSTing to endpoint:
```

Change what the server returns — 401, then 429, then 503 — and the message in n8n does not change at all. The same loss happens later, too: if a connection succeeds and a tool call then receives an empty unsuccessful response, the tool result handed to your agent also carries no status, so the agent cannot tell "slow down" from "server down" either.

This is a confirmed bug, reported in [GitHub issue #44145](https://github.com/n8n-io/n8n/issues/44145) (opened 2026-11-17, reproduced on n8n master `fec3317e` with `@n8n/n8n-nodes-langchain` 2.48.0 and MCP SDK 1.32.0). The reporter proved it with a ten-line fixture server that returns an empty 503, then an empty 429 — n8n showed the identical blank description both times. As of 2026-11-26 the issue is open with no merged fix, so the diagnosis steps below are the fix for now. Note the boundary: if the server returns a non-empty error body, its text does reach the message. The blind spot is specifically the empty-body case — which is exactly what many proxies, gateways, and rate limiters return.

## The root cause: the status is in the error object, n8n just never prints it

The MCP SDK does not lose the status. Its transport error, `StreamableHTTPError`, carries the HTTP status in its `code` property. The problem is on the n8n side: the MCP nodes format the visible error from the error's `message` only, and when the response body is empty the message ends right after the colon. The status in `code` never reaches the connection error description or the agent-facing tool result.

The expected behavior, per the issue, is a message like `HTTP 503: Streamable HTTP error: Error POSTing to endpoint:` — with one guardrail: JSON-RPC error codes and timeout codes must not be mislabeled as HTTP statuses. Until a release ships that, you have to read the status yourself. The good news: it takes one command.

## The fix: ask the endpoint directly, then act on the real status

### Step 1 - Reproduce the status with curl

Run this from a machine that can reach your MCP server the same way n8n does — if n8n runs in Docker and the server is on the host, use an address the container can reach, or run the command inside the container's network. Replace the URL and token with the ones from your MCP node:

```bash
curl -i -X POST https://your-mcp-server.example.com/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'
```

Here is what each part does. `-i` prints the response headers, and the first line is the status n8n hid from you — that line is the whole point. The two mandatory headers are `Content-Type: application/json` and an `Accept` header listing **both** `application/json` and `text/event-stream`; Streamable HTTP requires both because the server may answer either way. The body is the standard MCP `initialize` handshake, the same first request the n8n node sends.

You should see a status line such as `HTTP/2 503` or `HTTP/1.1 429 Too Many Requests`, plus headers worth reading: `Retry-After` on a 429, `WWW-Authenticate` on a 401, and `Mcp-Session-Id` on a successful stateful initialize. If you instead get **406**, that is your curl command missing `text/event-stream` in `Accept` — fix the command before blaming the server.

### Step 2 - Fix the cause the status names

| Status from curl | What it means for MCP | What to do |
|---|---|---|
| 401 / 403 | Token missing, expired, or not accepted | Reconnect the credential in n8n or mint a fresh token; check the `Authorization` header the node sends |
| 404 | Wrong path, or an expired session on a stateful server | Confirm the endpoint path (often `/mcp`); reload the tool list so n8n re-initializes |
| 429 | Rate limited | Wait for the `Retry-After` interval; reduce agent call frequency or raise the server quota |
| 502 / 503 / 504 | Server or its proxy is down or overloaded | Check the MCP server and reverse-proxy logs; retry once it recovers |
| 400 | Malformed request or missing session header | Compare the URL and headers against the server's docs; stateful servers reject requests without `Mcp-Session-Id` after initialize |
| 200 | Endpoint and auth are fine | The failure is later — re-check the tool call itself and the server's own logs |

One distinction matters here: a JSON-RPC error inside a 200 response (codes like `-32601` for "method not found") is an application-level answer from a working server, not an HTTP failure. If curl returns 200 with a JSON-RPC error body, debug the method and parameters, not the connection.

### Step 3 - Make the workflow fail loudly instead of blindly

Until the node prints statuses itself, add a pre-flight check in front of the AI Agent so a dead endpoint stops the run with a readable reason. Use an HTTP Request node with the same POST, headers, and credential as Step 1, turn on **Include Response Headers and Status**, and follow it with an IF node on the returned status code: anything other than 200 routes to a Stop and Error node whose message includes the status. Your executions then say "MCP endpoint returned 429" instead of failing inside the agent with a blank description.

> **Note:** On a stateful MCP server, the pre-flight `initialize` creates a session that then sits unused until it expires. That is harmless for diagnosis, but if your server caps concurrent sessions, prefer Step 1's manual curl for debugging and keep the pre-flight only where a loud failure is worth a spare session.

### Step 4 - If you run the MCP server, return a body with your errors

Server operators can close this blind spot today: n8n's message does include the response body text when one exists. Return a short JSON-RPC error body (or plain text) with 4xx and 5xx responses instead of an empty body, send `Retry-After` with 429s and `WWW-Authenticate` with 401s, and log the status server-side. Every client — n8n included — gets a diagnosable error instead of a colon followed by silence.

## Verify it worked

1. Re-run the Step 1 curl command. You should see `HTTP/2 200` (or `HTTP/1.1 200 OK`), and on a stateful server an `Mcp-Session-Id` header.
2. In n8n, reload the MCP node's tool list. The tools should load without the blank error.
3. Run the workflow once end to end. The agent's tool calls should return results, and if you added the Step 3 pre-flight, a deliberately wrong token should now stop the run with your status message — proof the loud failure works.

To confirm the bug itself on your instance, the reporter's fixture is decisive: serve an empty 503 from any small HTTP server, point an MCP Client Tool at it, and watch n8n show the blank message while curl shows 503. Switch the fixture to 429 and n8n's message stays identical — that sameness is the bug.

## Prevent it next time

- **Monitor the endpoint, not the workflow.** A scheduled check that POSTs `initialize` and alerts separately on 401, 429, and 5xx catches credential expiry, quota exhaustion, and outages as three different incidents — which they are.
- **Never debug this error inside n8n first.** The node cannot currently tell you the status; go straight to curl with `-i` and read the status line.
- **Watch issue #44145** and upgrade when a release includes the fix (status included in the visible error, e.g. `HTTP 503: ...`). After upgrading, re-run the fixture test: the description should name the status.

If your MCP trouble is different — tools failing mid-run in queue mode, or trigger fields leaking into tool calls — see [Fix n8n MCP Tool Calls Failing in Queue Mode](/blog/fix-n8n-mcp-tool-calls-queue-mode/) and [Fix n8n AI Agent Leaking Chat Trigger Fields Into MCP Tool Calls](/blog/fix-n8n-ai-agent-trigger-fields-leak-into-tool-calls/).

## Key Takeaways

1. **The blank MCP error hides the HTTP status, not the failure** — 401, 404, 429, and 503 with empty bodies all render as `Streamable HTTP error: Error POSTing to endpoint:` in n8n's MCP nodes (GH #44145, open as of 2026-11-26).
2. **The status exists; n8n just doesn't print it** — the SDK keeps it in `StreamableHTTPError.code`, and the node formats errors from `message` only.
3. **One curl command recovers the truth** — POST `initialize` with both `Accept` values and `-i`, then fix what the status line names.
4. **Server operators can mitigate today** — non-empty error bodies, `Retry-After` on 429, and `WWW-Authenticate` on 401 make every client's errors readable.
