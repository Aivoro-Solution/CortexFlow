---
title: "Fix n8n Webhook URLs Showing localhost:5678 Behind a Reverse Proxy"
description: "n8n webhook URLs stuck on localhost:5678 behind Nginx or Caddy? Set N8N_WEBHOOK_URL, N8N_PROXY_HOPS, and forward the right headers. Copy-paste fix."
date: 2026-10-18
category: automation
tags: ["n8n", "self-hosting", "reverse-proxy", "webhooks", "Docker"]
image: "/og/fix-n8n-webhook-localhost-reverse-proxy.webp"
draft: false
featured: false
---

You put n8n behind a reverse proxy, opened `https://n8n.example.com`, and everything looked fine — until you added a Webhook node. Its URLs read `http://localhost:5678/webhook/...`. Paste one of those into Stripe, GitHub, or Telegram, and the external service can never reach it. The fix takes two environment variables and three proxy headers, but the failure has layers: n8n's URL generation, its trust in forwarded headers, and the proxy's WebSocket handling. By the end of this guide, every URL your Webhook node generates will start with your domain, and the editor's live connection will survive the proxy too.

## The symptom

A **webhook** is a URL that an outside service calls to wake up your workflow — Stripe calls it when a payment succeeds, Telegram calls it when a message arrives. n8n generates two URLs per Webhook node: a test URL (`/webhook-test/...`, live for 120 seconds after you click "Listen for test event") and a production URL (`/webhook/...`, live whenever the workflow is published). Both are built inside n8n's container, which only knows its internal address. So behind a proxy you get one of these:

- `http://localhost:5678/webhook/abc123` — unusable from anywhere outside the server
- `https://n8n.example.com:5678/webhook/abc123` — your domain, but with n8n's internal port appended; the proxy only listens on 443, so the request dies

A third symptom often rides along: a red **"Connection lost"** badge in the n8n editor that never reconnects. That is the proxy's fault, not n8n's, and it has its own fix below.

## The root cause

n8n builds webhook URLs from what it knows about itself: its configured host, port, and protocol. Behind a reverse proxy, all three are wrong from the outside world's point of view. Three distinct gaps cause the failure:

1. **n8n doesn't know its public address.** Unless told, it generates URLs from its internal host/port (`localhost:5678`). No proxy header can fix this — the URL is generated, not derived from the request.
2. **n8n doesn't trust the proxy's headers.** Your proxy sends `X-Forwarded-Proto: https` and `X-Forwarded-Host`, but n8n ignores forwarded headers unless you tell it how many proxies sit in front of it.
3. **The proxy drops the editor's live connection.** n8n's editor holds a WebSocket to the server. If the proxy doesn't forward the `Upgrade` and `Connection` headers, the handshake fails and you get "Connection lost."

## What you'll need

- n8n running in Docker behind Nginx or Caddy, reachable at your domain over HTTPS
- n8n version that knows `N8N_WEBHOOK_URL` (renamed from `WEBHOOK_URL` around n8n 2.30–2.35; set both variables to be safe)
- SSH access to the host

**Placeholder:** `n8n.example.com` is your public domain. Replace it everywhere.

## Step 1 - Tell n8n its public webhook URL

Open your `docker-compose.yml` (or `.env` file) and add these environment variables to the n8n service:

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n
    environment:
      - N8N_WEBHOOK_URL=https://n8n.example.com/
      - WEBHOOK_URL=https://n8n.example.com/
      - N8N_HOST=n8n.example.com
      - N8N_PROTOCOL=https
      - N8N_PROXY_HOPS=1
```

Here's what each key does:

- `N8N_WEBHOOK_URL` — the base URL n8n uses when generating webhook and OAuth callback URLs. This single variable fixes the `localhost:5678` symptom. `WEBHOOK_URL` is the same variable's older name; setting both covers old and new n8n versions without you having to check which rename happened in your release.
- `N8N_HOST` / `N8N_PROTOCOL` — belt and braces for the editor and OAuth redirects, which in some versions build URLs from these instead of `N8N_WEBHOOK_URL`.
- `N8N_PROXY_HOPS=1` — tells n8n there is exactly one reverse proxy in front of it, so it trusts the `X-Forwarded-*` headers the proxy sends. Set this to `2` if you have two layers (e.g. Cloudflare in front of Nginx).

> **Note:** `N8N_WEBHOOK_URL` must be the full public HTTPS address, trailing slash included. A missing scheme or a trailing-slash typo is the most common reason "I set the variable and nothing changed."

## Step 2 - Fix the proxy headers

### Nginx

Your `server` block needs these lines inside the `location /` block:

```nginx
location / {
    proxy_pass http://localhost:5678;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

The first four headers let n8n see the visitor's real host, IP, and protocol instead of the proxy's. The last three lines (`proxy_http_version 1.1`, `Upgrade`, `Connection`) keep the editor's WebSocket alive — this is what cures the "Connection lost" badge. Without them, n8n's editor polls in the dark while webhooks themselves work.

### Caddy

```caddyfile
n8n.example.com {
    reverse_proxy localhost:5678 {
        header_up Host {host}
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Port 443
    }
}
```

Caddy handles WebSocket upgrades automatically, so there is no "Connection lost" fix needed — the three `header_up` lines make sure n8n sees the public host and the HTTPS scheme even when the forwarded request itself is plain HTTP between Caddy and the container. Test the config with `caddy validate --config /etc/caddy/Caddyfile` before reloading.

## Step 3 - Recreate the container

New environment variables are **not** picked up by a plain `docker restart`. Recreate the container so the new values take effect:

```bash
docker compose up -d
```

Then confirm the variables actually reached the container:

```bash
docker compose exec n8n env | grep -E "N8N_WEBHOOK_URL|WEBHOOK_URL|PROXY_HOPS"
```

You should see `N8N_WEBHOOK_URL=https://n8n.example.com/` in the output. If a variable is missing here, you edited the wrong compose file or the wrong service block — this single check saves most debugging.

## Step 4 - Verify it worked

1. Open the n8n editor and add a Webhook node.
2. Both the test and production URLs must start with `https://n8n.example.com/webhook/...` — **no `localhost`, no `:5678`**.
3. Click **Listen for test event**, then trigger the URL from another device (your phone, `curl` from a different machine). The event should appear on the canvas — if it does, the production URL works too, and the WebSocket fix is holding.
4. If you still see the old URLs, clear them: the Webhook node caches generated paths per workflow. Toggle the workflow off and on, or delete and re-add the Webhook node.

## Prevent it next time

Make the two variables part of your standard self-hosting template. Every new n8n install behind a proxy needs `N8N_WEBHOOK_URL` and `N8N_PROXY_HOPS` from day one — adding them after the fact means regenerating every webhook URL your external services already call. If you manage n8n for clients, put a comment above the variables in `docker-compose.yml` noting that a container **recreate** (not restart) is required after changing them.

**What I didn't test:** this guide covers one proxy hop on Docker. If you run n8n in Kubernetes behind an ingress plus a cloud load balancer, set `N8N_PROXY_HOPS=2` and verify `X-Forwarded-*` survives both layers with a request-bin check — stacked proxies eat headers in ways a single-proxy setup never shows.

## FAQ

### Why does n8n use localhost at all? Isn't it reading the request?

n8n generates webhook URLs when you open the node, using its configured base address — it doesn't derive them per-request from the `Host` header. That design is why headers alone can never fix the symptom; you must give n8n its public address explicitly.

### I set N8N_WEBHOOK_URL but the URLs still show the port. Why?

Two usual culprits. First, you restarted instead of recreating the container — environment variables only apply at container creation. Second, an old n8n version (before the rename) reads `WEBHOOK_URL`, not `N8N_WEBHOOK_URL`. Setting both, as in Step 1, removes this guessing.

### Does WEBHOOK_URL still work in the latest n8n?

The variable was renamed to `N8N_WEBHOOK_URL` (the rename landed across the n8n 2.30–2.35 releases). New versions read the new name; older versions read the old one. Set both and you stop caring which version you're on.

### Can I just expose port 5678 publicly instead?

You could, but you'd be putting an unauthenticated attack surface on the internet and your webhook URLs would still carry the port. The proxy exists to give you TLS and one clean address — fix the config once and keep the port internal.

## Key Takeaways

1. **n8n generates webhook URLs from its config, not from the request** — so the fix is `N8N_WEBHOOK_URL` (plus legacy `WEBHOOK_URL`), never proxy magic alone.
2. **`N8N_PROXY_HOPS=1` makes n8n trust your proxy's `X-Forwarded-*` headers** — without it, protocol and host detection silently fall back to internal values.
3. **Recreate the container with `docker compose up -d`** — a plain restart never applies new environment variables.
4. **"Connection lost" in the editor is a separate WebSocket problem** — forward `Upgrade`/`Connection` over HTTP/1.1 (Nginx) or rely on Caddy's automatic handling.
5. **Verify with `docker compose exec n8n env | grep WEBHOOK_URL`** — if the variable isn't inside the container, nothing downstream can work.

Next: if your n8n crashes under load instead of mis-generating URLs, the likely culprit is memory — read the upcoming guide on fixing OOM crashes in Docker Compose.
