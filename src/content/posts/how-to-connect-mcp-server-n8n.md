---
title: "How to Connect an MCP Server to n8n (Step-by-Step Guide)"
description: "Learn how to connect an MCP server to n8n using the MCP Client Tool node. Covers SSE vs Streamable HTTP, OAuth troubleshooting, and a working example."
date: 2026-09-30
category: automation
tags: ["n8n", "MCP", "AI agents", "tutorial", "Model Context Protocol"]
featured: true
---

Connecting an MCP server to n8n is one of the most useful skills you can learn as an automation builder in 2026. The Model Context Protocol (MCP) gives your n8n AI agents access to external tools and data — databases, APIs, file systems, even other SaaS apps — through a single standard interface. Instead of wiring up dozens of custom HTTP requests, you point n8n at an MCP server and your agent can suddenly *use* everything that server exposes.

In this guide, you'll learn exactly how to connect an MCP server to n8n using the built-in **MCP Client Tool** node. We'll cover the two transport types (SSE and Streamable HTTP), OAuth authentication, common errors, and finish with a working example you can copy.

## What You'll Need

Before we start, make sure you have:

- **n8n version 1.60 or later** (the MCP Client Tool node shipped in late 2024 and improved steadily since). Self-hosted or n8n Cloud both work.
- **An MCP server URL** to connect to. If you don't have one yet, you can test with a public demo server like `https://mcp.context7.com/mcp` (Context7 docs server) — it works without authentication.
- **5–10 minutes** and a basic n8n workflow to drop the node into.

> **New to MCP?** The Model Context Protocol is an open standard (originally from Anthropic, now stewarded under the Linux Foundation's Agentic AI Foundation) that lets AI applications connect to external tools in a uniform way. Think of it like USB for AI tools: one plug, many devices.

## Step 1: Add an AI Agent Node to Your Workflow

The MCP Client Tool is a *tool* node — it doesn't run on its own. It must be connected to an agent that can call it.

1. In n8n, create a new workflow.
2. Add a **Manual Trigger** (or a **Chat Trigger** if you want a conversational interface).
3. Add an **AI Agent** node. Choose your model — OpenAI's GPT models, Anthropic Claude, or a local model all work, as long as the model supports tool calling.
4. In the AI Agent node, set the prompt to something like: *"You are a helpful assistant with access to external tools. Use them when needed."*

## Step 2: Add the MCP Client Tool Node

1. Click the **"+"** on the AI Agent node's **Tools** input (the small connector at the bottom of the node).
2. Search for **"MCP Client Tool"** and add it.
3. You'll see a configuration panel with two key settings: **MCP Server URL** and the transport/authentication options.

This is where most people get stuck, so let's slow down and get it right.

## Step 3: Choose Your Transport — SSE vs Streamable HTTP

MCP servers communicate over HTTP using one of two transports. **You must pick the one your server actually uses**, or the connection will fail silently.

### SSE (Server-Sent Events)

The original MCP HTTP transport. The server exposes a dedicated `/sse` endpoint, and n8n keeps a long-lived connection open.

- **URL format:** `https://your-server.com/sse`
- **When to use it:** older MCP servers, or when the server's docs explicitly mention an SSE endpoint.
- **Downside:** less efficient — it holds connections open and doesn't support resumable streams as cleanly.

### Streamable HTTP (the modern default)

The current MCP specification transport. A single `/mcp` endpoint handles everything with regular request/response cycles plus optional streaming.

- **URL format:** `https://your-server.com/mcp`
- **When to use it:** any server built against the current MCP spec (most servers from 2025 onward).
- **This is the default you should try first.**

### How to tell which one your server uses

| Clue | Transport |
|---|---|
| Docs mention `/mcp` endpoint | Streamable HTTP |
| Docs mention `/sse` endpoint | SSE |
| Server built in 2025+ with a recent MCP SDK | Almost certainly Streamable HTTP |
| Connection hangs then times out | You're probably using the wrong one — try the other |

**Practical tip:** if you're unsure, try Streamable HTTP first. In n8n's MCP Client Tool node, the transport is inferred from the URL pattern and node settings — entering the full endpoint URL (`.../mcp` or `.../sse`) is the most reliable approach.

## Step 4: Configure Authentication

Most production MCP servers require authentication. n8n's MCP Client Tool supports several methods:

### No auth (testing only)

Leave the credentials empty. Fine for local servers and public demo servers.

### API key / Bearer token

1. In the MCP Client Tool node, under **Authentication**, select **"Generic Auth"** or header-based auth.
2. Add a header: `Authorization: Bearer YOUR_TOKEN`.
3. Many hosted MCP servers (e.g., Context7, Apify actors exposed over MCP) use this pattern.

### OAuth 2.0

Some MCP servers use OAuth with dynamic client registration:

1. Select **OAuth2** as the authentication method.
2. n8n will attempt to discover the OAuth endpoints from the server's `/.well-known/oauth-authorization-server` metadata.
3. Complete the browser-based consent flow when prompted.

**OAuth troubleshooting** (the most common pain points):

- **"Failed to discover OAuth metadata"** — the server doesn't publish a `.well-known` endpoint. Check the server docs for manual OAuth URLs, or ask the provider whether they support the MCP OAuth flow at all. Some servers only support API keys despite mentioning OAuth.
- **Redirect URI mismatch** — n8n Cloud uses a fixed OAuth redirect URL. Copy it exactly from the n8n credentials screen into the OAuth app's allowed redirect URIs. One trailing slash can break it.
- **Token expires mid-workflow** — enable n8n's automatic token refresh in the credential settings. If the server issues short-lived tokens without refresh tokens, consider switching to a long-lived API key if the provider offers one.
- **Self-hosted n8n behind a tunnel** — OAuth callbacks must reach your instance. If you're using a tunnel (ngrok, Cloudflare Tunnel), make sure the callback URL uses the public tunnel address, not `localhost`.

## Step 5: Test the Connection and List Tools

Once configured:

1. Click **"Execute step"** on the MCP Client Tool node.
2. n8n will connect and list the tools the server exposes. You should see tool names and descriptions — e.g., `resolve-library-id`, `get-library-docs` on the Context7 server.
3. If the list is empty but there's no error, the server may require additional scopes or the tools may be filtered server-side. Check the server logs.

## Step 6: Let the Agent Use the Tools

Now go back to your AI Agent node and run the workflow:

1. **Execute the workflow** (or send a chat message if you used a Chat Trigger).
2. Ask something the MCP server can answer. With Context7, try: *"How do I use the Next.js App Router for a blog?"*
3. Open the AI Agent node's output and expand the execution log — you'll see the agent **decide to call the MCP tool**, n8n fetch the data, and the agent incorporate it into its answer.

Congratulations — your n8n agent now has live access to external tools through MCP.

## A Complete Working Example

Here's a minimal setup you can replicate in under 10 minutes:

1. **Trigger:** Chat Trigger node (so you can talk to the agent).
2. **AI Agent node:** model of your choice, system prompt: *"You are a documentation assistant. When asked about a library or framework, use your tools to fetch up-to-date documentation before answering."*
3. **MCP Client Tool:** URL `https://mcp.context7.com/mcp`, no authentication.
4. Open the chat, ask: *"What's the latest way to do ISR in Next.js?"*
5. Watch the agent call the MCP tools, retrieve current docs, and answer — with knowledge fresher than its training data.

This same pattern scales: swap Context7 for your company's internal MCP server (database queries, ticket systems, file storage) and you have a genuinely useful internal agent.

## Common Errors and How to Fix Them

| Error | Likely cause | Fix |
|---|---|---|
| Connection timeout | Wrong transport (SSE vs Streamable HTTP) | Try the other endpoint format |
| 401 Unauthorized | Missing or wrong credentials | Re-check token; verify header format `Bearer <token>` |
| 404 on `/mcp` | Server uses a different path | Read the server docs — some use `/api/mcp` or custom paths |
| "No tools found" | Server requires scopes / auth | Check server-side tool filtering and OAuth scopes |
| OAuth redirect fails | Redirect URI mismatch | Copy n8n's exact callback URL into the OAuth app config |
| Works locally, fails on Cloud | Server blocks non-localhost origins | Allowlist n8n Cloud IPs or use a tunnel |

## SSE vs Streamable HTTP: Which Should You Choose?

If you're *running* your own MCP server (not just connecting to one): **use Streamable HTTP**. It's the current spec, it's what new SDKs default to, and SSE is effectively legacy. Only choose SSE if you must support an older client that doesn't speak Streamable HTTP.

If you're *connecting* to someone else's server: **match whatever their docs say**. When docs are silent, try `/mcp` first, then `/sse`.

## FAQ

### Do I need to self-host n8n to use MCP?

No. The MCP Client Tool node works on n8n Cloud and self-hosted instances alike. The only caveat: if your MCP server is on a private network (e.g., `localhost` or a company intranet), n8n Cloud can't reach it — self-host n8n on the same network or expose the server through a secure tunnel.

### Can n8n act as an MCP *server* too?

Yes. n8n has an **MCP Server Trigger** node that exposes your workflows as MCP tools to external clients like Claude Desktop. That means n8n can be both an MCP client (this guide) and an MCP server — a powerful combination for agent-to-agent workflows.

### Is MCP secure for production use?

MCP itself is a protocol, not a security model — security depends on the server implementation. For production: always use HTTPS, prefer OAuth or scoped API keys over shared secrets, and treat tool descriptions as untrusted input (a malicious MCP server could try prompt injection through tool descriptions). Only connect to servers you trust.

### What's the difference between MCP and n8n's regular HTTP Request node?

An HTTP Request node calls one fixed endpoint. An MCP connection gives your agent a *menu* of tools it can choose from dynamically, with structured schemas the model understands. For agentic workflows where the model decides what to do, MCP is far more flexible.

### Why is my agent not calling the MCP tools?

Three usual suspects: (1) the model doesn't support tool calling — switch to a model that does; (2) the system prompt doesn't encourage tool use — explicitly tell the agent tools are available; (3) the tools failed to load — re-run the MCP Client Tool node alone and confirm it lists tools.

## Conclusion

Connecting an MCP server to n8n takes minutes once you know the two things that trip everyone up: **picking the right transport** (Streamable HTTP `/mcp` vs legacy SSE `/sse`) and **getting authentication right** (especially OAuth redirect URIs). With those solved, your n8n AI agents gain live, structured access to any tool exposed over MCP — documentation, databases, SaaS apps, and your own internal systems.

**Next step:** build the working example above with the Context7 server, then try pointing n8n at an MCP server for a tool you actually use daily. If you found this guide useful, [browse more automation tutorials](/categories/automation/) or subscribe via [RSS](/rss.xml) to get the next one.
