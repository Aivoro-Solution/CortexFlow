---
title: "Fix n8n MCP OAuth 'Couldn't Register With n8n's Sign-in Service' Error (Claude.ai)"
description: "Claude.ai can't register with your self-hosted n8n's MCP server? n8n advertises localhost OAuth URLs behind your tunnel — 5 env vars fix it."
date: 2026-11-09
category: automation
tags: ["n8n", "mcp", "oauth", "claude", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-mcp-oauth-register-claude-ai.webp"
---

You point Claude.ai at your self-hosted n8n instance, hit connect, and Claude answers: *"Couldn't register with n8n's sign-in service. You can try again, or add an OAuth Client ID in the connector settings."* Your n8n is up. The tunnel is up. The OAuth settings page saved without complaint. And yet Claude cannot register — ever.

The maddening part is that half the handshake works. Claude fetches n8n's OAuth discovery documents and gets clean 200s. Then nothing: no client registration ever arrives, and the MCP endpoint answers 401. This article explains why that exact fingerprint means one thing — n8n is advertising its own localhost address to the outside world — and fixes it with five environment variables. The fix comes straight from an n8n team reply on the forum thread where this error was reported, and it takes about ten minutes.

Quick definitions before we start: **MCP** (Model Context Protocol) is Anthropic's open standard for letting AI clients like Claude call tools exposed by a server — here, your n8n workflows. **Instance-level MCP** is n8n's built-in feature (Preview in 2.x) that exposes your published workflows as MCP tools to remote clients like Claude.ai. **Dynamic client registration** (RFC 7591) is the step where Claude introduces itself to n8n's OAuth server and gets a client ID automatically — no manual Client ID and Secret needed. **ngrok** is a tunneling service that gives a local server a public HTTPS address.

**Prerequisites:** a self-hosted n8n instance (2.30.x or later, as of November 2026 — the report that verified this fix ran 2.30.7), exposed through ngrok or another public tunnel/reverse proxy, with Instance-level MCP enabled under Settings.

> **Note:** this article is about the *registration* failure — Claude never gets a client ID. If your MCP connection fails later with `invalid_target` / "Invalid resource indicator", that is a different bug on a different hostname setup, covered in [Fix ChatGPT MCP Connector 'invalid_target' Error in n8n](/blog/fix-mcp-chatgpt-oauth-invalid-target/).

## The symptom: what the failure actually looks like

The failure has a very specific fingerprint. If yours matches all five points, the diagnosis in this article is almost certainly correct:

1. **Claude shows:** "Couldn't register with n8n's sign-in service. You can try again, or add an OAuth Client ID in the connector settings."
2. **Discovery works:** your tunnel logs show Claude successfully fetching `/.well-known/oauth-authorization-server` and `/.well-known/oauth-protected-resource` — both return 200.
3. **Registration never arrives:** no POST request to any `/register` endpoint ever shows up in the tunnel logs.
4. **MCP endpoint rejects:** `GET /mcp-server/http` returns 401 Unauthorized.
5. **No clients connected:** in n8n, Settings → Instance-level MCP → "Connected clients" always shows "No OAuth clients connected".

The combination of points 2 and 3 is the giveaway. Claude can *reach* your instance fine — it read the discovery documents. It then tried to register somewhere else entirely, and that somewhere else was never your server.

## Diagnose first: read what n8n is advertising

Before changing anything, confirm the diagnosis in one command. Fetch the protected-resource document the way Claude sees it:

```bash
curl -s https://<your-subdomain>.ngrok-free.app/.well-known/oauth-protected-resource | python3 -m json.tool
```

Replace `<your-subdomain>.ngrok-free.app` with your tunnel's public address. Look at the `resource` field (and the `authorization_servers` list) in the output. On a broken instance it looks like this:

```json
{
  "resource": "http://localhost:5678",
  "authorization_servers": ["http://localhost:5678"]
}
```

That is the whole bug in one line. n8n builds the OAuth endpoint URLs it advertises — authorize, token, and the dynamic-registration endpoint — from its own base URL. Behind a tunnel, that base URL still defaults to `http://localhost:5678`, because nothing ever told n8n its public address. Claude reads the discovery document over the tunnel (your 200s), then POSTs its client registration to the `localhost` registration endpoint it read from that document. That request goes to Claude's own machine — or nowhere — and never reaches your instance. No registration, no client, and every MCP call afterwards gets a 401 because no OAuth client exists.

**You should see after the fix:** the same command returns your public tunnel URL in `resource` and `authorization_servers`, with `https` and no `localhost` anywhere.

## Fix 1 - Tell n8n its public address (the actual fix)

This is the fix the n8n team gave in the forum thread, and it is the only fix most people need. Add these five environment variables to your n8n configuration, pointing at your tunnel's public address, then restart n8n:

```bash
N8N_HOST=<your-subdomain>.ngrok-free.app
N8N_PROTOCOL=https
N8N_EDITOR_BASE_URL=https://<your-subdomain>.ngrok-free.app/
N8N_WEBHOOK_URL=https://<your-subdomain>.ngrok-free.app/
N8N_PROXY_HOPS=1
```

Here is what each variable does, because setting them blind is how this bug comes back:

- **`N8N_HOST`** — the public hostname n8n uses to build URLs for itself. Without it, n8n falls back to `localhost`, which is exactly the advertised address Claude choked on.
- **`N8N_PROTOCOL=https`** — tells n8n the public scheme is HTTPS, so the advertised URLs start with `https://` instead of `http://`. OAuth clients reject plain-HTTP authorization servers, so this is not cosmetic.
- **`N8N_EDITOR_BASE_URL`** — the canonical base URL of the editor. This is the value n8n uses when it constructs the OAuth endpoint URLs in the `.well-known` documents. It must match, character for character, the URL Claude connects to — including the trailing slash.
- **`WEBHOOK_URL`** — the public base for webhook URLs. It does not drive the OAuth documents directly, but leaving it at localhost while fixing the others leaves your webhook URLs pointing at an unreachable address, so set it in the same pass.
- **`N8N_PROXY_HOPS=1`** — tells n8n there is exactly one proxy (ngrok) in front of it, so it trusts the `X-Forwarded-*` headers ngrok sets. Without this, n8n may ignore the forwarded host and scheme and keep advertising localhost even with the other four variables set.

If you run n8n in Docker Compose, the variables go in the `environment:` block of the n8n service:

```yaml
services:
  n8n:
    image: n8nio/n8n:2.30.7
    environment:
      - N8N_HOST=<your-subdomain>.ngrok-free.app
      - N8N_PROTOCOL=https
      - N8N_EDITOR_BASE_URL=https://<your-subdomain>.ngrok-free.app/
      - WEBHOOK_URL=https://<your-subdomain>.ngrok-free.app/
      - N8N_PROXY_HOPS=1
```

Then restart the container:

```bash
docker compose up -d
```

> **Warning:** changing these variables requires a restart — n8n reads them at boot. Editing the compose file without restarting changes nothing, and the `.well-known` documents will keep advertising localhost.

After the restart, re-run the diagnosis command from the previous section. The `resource` field must now show your public HTTPS URL. If it still shows `localhost:5678`, one of the five variables is misspelled or the container did not actually restart — check with `docker compose exec n8n env | grep N8N_` before going further.

## Fix 2 - Re-copy the OAuth server URL and reconnect from Claude

Fixing the advertised URLs is not enough on its own, because Claude cached the old ones. n8n's Settings page shows the OAuth server URL that clients should use, and that displayed URL was built from the same broken base URL — so the copy you pasted into Claude the first time was itself a localhost URL.

1. In n8n, open **Settings → Instance-level MCP** and copy the OAuth server URL again. It should now start with your public `https://` address.
2. In Claude.ai, remove the existing n8n connector (the failed one holds the stale registration data) and add it again with the freshly copied URL.
3. Complete the OAuth consent flow. Dynamic client registration will now POST to the public endpoint, and n8n will issue Claude a client ID automatically — you do not need to enter a Client ID manually.

Verify the registration landed: back in **Settings → Instance-level MCP → Connected clients**, Claude should now appear as a connected client. If the tab still says "No OAuth clients connected", the registration POST is still not reaching n8n — go back to Fix 1 and re-check the diagnosis command output.

## Fix 3 - Make the tunnel address stable (ngrok free domains move)

This fix is about the bug coming back tomorrow. On ngrok's free plan, your tunnel address changes every time ngrok restarts, unless you reserve a static domain. Every time the address changes, the five variables in Fix 1 point at a dead address, and the advertised OAuth URLs break again — same error, same fingerprint, new subdomain.

Reserve a static domain in the ngrok dashboard (Domains → Create), then start the tunnel with it:

```bash
ngrok http 5678 --domain=<your-reserved-subdomain>.ngrok-free.app
```

Then use that reserved domain in all five environment variables. If you cannot reserve a domain, treat every ngrok restart as a re-run of Fix 1 and Fix 2: update the variables, restart n8n, re-copy the OAuth server URL, reconnect from Claude.

The same warning applies to the redirect URL. When you enabled Instance-level MCP, you registered `https://claude.ai/api/mcp/auth_callback` as an allowed redirect URL under n8n's OAuth settings. That value is Claude's side of the flow and does not change with your tunnel address — but if you ever re-create the OAuth configuration from scratch, it must be registered again, or the consent step will fail with a redirect error instead of the registration error.

## Fix 4 - The same fix behind a reverse proxy (nginx, Caddy, Cloudflare Tunnel)

If you expose n8n through a reverse proxy instead of ngrok, the root cause is identical — n8n still defaults to localhost — and the fix is the same five variables with your own public domain:

```bash
N8N_HOST=n8n.example.com
N8N_PROTOCOL=https
N8N_EDITOR_BASE_URL=https://n8n.example.com/
WEBHOOK_URL=https://n8n.example.com/
N8N_PROXY_HOPS=1
```

Two proxy-specific notes:

- **Count your proxies for `N8N_PROXY_HOPS`.** The value is the number of proxies between the internet and n8n. One reverse proxy means `1`. If traffic passes through Cloudflare *and* nginx before reaching n8n, that is two hops — set `N8N_PROXY_HOPS=2`. A wrong count makes n8n distrust the forwarded headers and advertise its internal address again.
- **Cloudflare Tunnel (cloudflared) users:** the same five variables apply, with your tunnel's public hostname. The n8n team's reply for the ngrok case generalizes directly — whatever your public entry point is, that is what `N8N_HOST` and `N8N_EDITOR_BASE_URL` must say.

## Verify it worked

Run this checklist in order — each step proves one link in the chain:

1. **Discovery advertises the public URL:**
   ```bash
   curl -s https://<your-subdomain>.ngrok-free.app/.well-known/oauth-protected-resource
   ```
   You should see your public `https://` URL in `resource`. No `localhost` anywhere.
2. **Registration arrives:** watch the tunnel request log (ngrok's web interface at `http://127.0.0.1:4040` or `ngrok http --log`) while connecting from Claude. You should now see a `POST` to the registration endpoint — the request that was missing entirely before.
3. **Client appears:** Settings → Instance-level MCP → Connected clients lists Claude.
4. **A tool call works:** in Claude, ask it to use one of your published n8n workflows (you need at least one workflow published with a Chat Trigger and MCP access enabled for it). A successful tool result — not a 401 — is the end-to-end proof.

If step 1 passes but step 2 still shows no registration POST, Claude is likely still holding the old connector configuration — remove and re-add the connector (Fix 2) rather than retrying the same connection.

## Prevent it next time

- **Put the five variables in your compose file, not in a one-off shell command.** A variable set with `docker run -e` on the command line is lost the next time someone recreates the container from the compose file. The compose file is the source of truth.
- **Use a reserved/static domain for the tunnel.** Ephemeral tunnel addresses are the number-one reason this error resurfaces after a "fixed" setup.
- **Add the discovery check to your deployment checklist.** After any n8n move, restart, or tunnel change, run the `curl` from the diagnosis section. If `resource` says `localhost`, stop — nothing downstream will work until it says your public URL.
- **Keep n8n current.** This report was verified on 2.30.7 (July 2026). Instance-level MCP was still a Preview feature then; later versions may change the Settings path or add a dedicated base-URL field, but the underlying rule — n8n advertises whatever base URL you give it — does not change.

## What this error is not

A few lookalike failures get confused with this one, and the fixes above will not help them:

- **`invalid_target` / "Invalid resource indicator"** — the MCP server is on a *different hostname* than n8n's main base URL (a deliberate split-hostname setup), and n8n's RFC 8707 validation rejects the mismatch. Fixed by upgrading to 2.31.0+ and setting `N8N_MCP_BASE_URL` — see [Fix ChatGPT MCP Connector 'invalid_target' Error in n8n](/blog/fix-mcp-chatgpt-oauth-invalid-target/).
- **"Couldn't connect to the server" from Claude Code's UI connector flow** — the connector path is brokered server-to-server from Anthropic's backend, so it only works if your instance is publicly reachable on port 443 with a full certificate chain. A private instance works fine when added manually in the Claude Code CLI, and that is the intended route for non-public instances.
- **Claude Desktop silently dropping an MCP server entry** — the desktop app only supports local (stdio) servers in `claude_desktop_config.json`; a remote HTTP URL entry is silently rejected. Bridge it with `mcp-remote` (`npx -y mcp-remote <your-mcp-url>`) instead of entering the URL directly.

## FAQ

### Do I need to create an OAuth Client ID and Secret manually?

No. n8n's Instance-level MCP uses dynamic client registration — Claude registers itself and gets a client ID automatically once the advertised registration endpoint is reachable. The "add an OAuth Client ID" line in Claude's error message is a fallback suggestion for servers that do not support dynamic registration. n8n supports it; the endpoint was just unreachable because it was advertised as localhost.

### I set the variables and it still shows localhost in the discovery document. Why?

The container did not pick up the change. Either n8n was not restarted after the edit, or the variables went into the wrong place (a `.env` file the compose file does not load, or the host shell instead of the container environment). Verify inside the container with `docker compose exec n8n env | grep N8N_` — if the variables are absent there, they are absent for n8n.

### Does this affect n8n Cloud?

No. n8n Cloud instances already have a public base URL configured by n8n, so the discovery documents advertise a reachable address. This is a self-hosted-only failure, specific to setups behind a tunnel or reverse proxy where the public address was never configured.

### Why did the discovery documents return 200 if the URLs inside them were wrong?

Because the *documents* are served by your instance over the tunnel — Claude asked for them at the public URL and got them. The URLs *inside* the documents are a separate matter: they are built from n8n's configured base URL, which was localhost. Fetching a document and following the URLs inside it are two different steps, and only the second one failed.

## Key Takeaways

1. **"Couldn't register with n8n's sign-in service" with 200s on `/.well-known/*` and no `/register` POST means n8n is advertising localhost.** Claude reads the discovery documents fine, then posts registration to an address that never reaches your server.
2. **Set the five variables** — `N8N_HOST`, `N8N_PROTOCOL=https`, `N8N_EDITOR_BASE_URL`, `WEBHOOK_URL`, and `N8N_PROXY_HOPS=1` — to your public tunnel URL and restart n8n.
3. **Re-copy the OAuth server URL and reconnect** — Claude cached the old localhost-based URL, so the old connector entry must be removed and added again.
4. **Use a reserved tunnel domain** so the address — and the fix — survives a restart.
5. **Prove it with `curl`**: the `resource` field in `/.well-known/oauth-protected-resource` must show your public `https://` URL before anything else will work.

Next: if your MCP setup works but tool calls fail once you scale past a single instance, read [Fix n8n MCP Tool Calls Failing in Queue Mode](/blog/fix-n8n-mcp-tool-calls-queue-mode/) — the queue-mode failure looks similar from the client side but has a completely different cause. For the general MCP setup walkthrough, see [How to Connect n8n to an MCP Server](/blog/how-to-connect-mcp-server-n8n/).

*Sources: the error, tunnel logs, and fix in this article are verified against the n8n community thread [MCP OAuth registration fails when connecting Claude.ai](https://community.n8n.io/t/mcp-oauth-registration-fails-when-connecting-claude-ai/304382) (July 2026, n8n 2.30.7, ngrok), including the n8n team reply with the exact environment variables. The `invalid_target` distinction is covered in our own [invalid_target fix article](/blog/fix-mcp-chatgpt-oauth-invalid-target/), verified against [community.n8n.io/t/302460](https://community.n8n.io/t/instance-level-mcp-oauth-re-auth-fails-with-invalid-target-on-n8n-2-29-7-works-on-earlier-version/302460).*
