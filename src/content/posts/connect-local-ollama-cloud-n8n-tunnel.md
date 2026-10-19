---
title: "How to Connect Local Ollama to Cloud n8n (Cloudflare Tunnel vs Tailscale)"
description: "Cloud n8n can't reach localhost:11434. Here's the exact fix: expose local Ollama with Cloudflare Tunnel or Tailscale, then point n8n at the URL."
date: 2026-10-19
category: automation
tags: ["n8n", "ollama", "self-hosting", "cloudflare", "ai-agents"]
draft: false
featured: false
image: "/og/connect-local-ollama-cloud-n8n-tunnel.webp"
---

Your cloud n8n workflow throws `ECONNREFUSED` the moment it tries `http://localhost:11434`. Of course it does — on n8n Cloud (or any VPS-hosted n8n), `localhost` is *their* server, not your laptop. Your Ollama is sitting behind your home NAT, invisible to the internet.

The fix is not "open a firewall port." You expose Ollama over a secure tunnel, then point n8n's Ollama Chat Model credential at the tunnel URL. Two ways to do it — here's both, with exact commands.

## The symptom

You add an **Ollama Chat Model** sub-node in cloud n8n, set the Base URL to `http://localhost:11434`, and get one of:

- `Error: connect ECONNREFUSED 127.0.0.1:11434`
- Timeout after 60s
- `connect ECONNREFUSED ::1:11434` (the IPv6 variant)

**Root cause:** Ollama binds to `127.0.0.1` by default — only processes on your own machine can reach it. A cloud n8n instance lives in another datacenter entirely. Even if you set `OLLAMA_HOST=0.0.0.0`, your home router still won't route inbound port 11434 to your laptop.

## Step 0: Make Ollama listen on all interfaces

The tunnel proxies *to* your machine, so Ollama must accept local non-loopback connections first.

**Linux (systemd — permanent):**

```bash
sudo systemctl edit ollama
```

Add in the editor:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**macOS / Windows (temporary, current shell):**

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

Verify it's listening on all interfaces:

```bash
curl http://127.0.0.1:11434/api/tags
```

⚠️ **Security warning:** from this point Ollama has no auth — anyone who can reach port 11434 can run prompts and manage models. The tunnel approach below does *not* add auth. If you want an API key in front of Ollama, put a reverse proxy (Caddy or nginx) between the tunnel and Ollama and require an `Authorization: Bearer` header. Or use Tailscale, which restricts access to devices on your tailnet.

## Option A: Cloudflare Tunnel (public HTTPS URL, free)

Best when cloud n8n (e.g. n8n Cloud) needs a stable public URL — tunnels work behind NAT with zero port forwarding.

1. Install `cloudflared` (Linux):

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

2. Log in and create the tunnel:

```bash
cloudflared tunnel login
cloudflared tunnel create ollama-tunnel
```

3. Route a DNS name to it (any domain on your Cloudflare account, e.g. `ollama.example.com`):

```bash
cloudflared tunnel route dns ollama-tunnel ollama.example.com
```

4. Create `~/.cloudflared/config.yml`:

```yaml
tunnel: ollama-tunnel
credentials-file: /home/YOUR_USER/.cloudflared/<TUNNEL_ID>.json
ingress:
  - hostname: ollama.example.com
    service: http://localhost:11434
  - service: http_status:404
```

5. Run it (use systemd or `cloudflared service install` for persistence):

```bash
cloudflared tunnel run ollama-tunnel
```

6. Test from anywhere:

```bash
curl https://ollama.example.com/api/tags
```

Now in n8n: create an **Ollama** credential with **Base URL** = `https://ollama.example.com`, pick your model — done.

## Option B: Tailscale (private mesh, no public URL)

Best when n8n runs on a VPS you control (or Docker) and you don't want Ollama on the public internet at all.

1. Install Tailscale on **both** machines: the one running Ollama and the n8n host.
2. `sudo tailscale up` on both and approve them in the Tailscale admin console.
3. Find your Ollama machine's tailnet IP:

```bash
tailscale ip -4
# e.g. 100.81.197.36
```

4. In n8n, create the **Ollama** credential with **Base URL** = `http://100.81.197.36:11434`.

Traffic stays inside the encrypted WireGuard mesh — no public exposure, no DNS, no open ports. Works even when both machines are behind NATs.

### Docker n8n + Tailscale gotcha

A containerized n8n can't see the host's Tailscale interface by default. Either run n8n with `--network host`, or point the credential at your Ollama host's LAN IP instead of the tailnet IP.

## Wire it into n8n

Whichever option you chose, the n8n side is identical:

1. **Credentials → New → Ollama** — Base URL: your tunnel URL or tailnet IP (`https://ollama.example.com` or `http://100.81.197.36:11434`).
2. Add an **AI Agent** node → **Chat Model** → **Ollama Chat Model**, select the credential and your model (e.g. `llama3.1:8b`).
3. Run a test prompt. First inference is slow (model loads into RAM) — that's normal, not a bug.

**Test with a small model first.** A model that exceeds your RAM/VRAM fails with a 500 several minutes in, once the KV cache loads. Prove the pipe works with something like `llama3.2:1b` or `phi3:mini` before scaling up to 14B+ models.

## Which option should you pick?

| | Cloudflare Tunnel | Tailscale |
|---|---|---|
| Works with n8n **Cloud** | ✅ Yes (public URL) | ❌ No (no tailnet on n8n Cloud) |
| Public exposure | HTTPS URL (add auth yourself) | None — private mesh only |
| Setup time | ~15 min (DNS + config) | ~5 min |
| Cost | Free | Free |

**Rule of thumb:** n8n Cloud → Cloudflare Tunnel. Self-hosted n8n on your own VPS/Docker → Tailscale (simpler, zero public surface).

## FAQ

### Why not just set OLLAMA_HOST=0.0.0.0 and open port 11434?

Because your home router won't forward it without port-forwarding config, and even then you'd be exposing an unauthenticated API to the whole internet. Ollama's local API has no login — anyone scanning port 11434 could burn your GPU. A tunnel gives you controlled access instead.

### Does the n8n "Ollama" credential need an API key?

No. Ollama's local API doesn't require authentication, so any value (or none) works in the API key field. Keys only become relevant if you put a reverse proxy with bearer-auth in front of Ollama yourself.

### Can n8n Cloud reach my machine via Tailscale?

No — n8n Cloud runs in n8n's infrastructure, not on your tailnet. Use Cloudflare Tunnel (public HTTPS) for n8n Cloud. Tailscale only works when you control the n8n host.

## Conclusion

`localhost` inside cloud n8n is never your laptop — stop fighting it. Expose Ollama once (Cloudflare Tunnel for n8n Cloud, Tailscale for self-hosted n8n), point the Ollama credential at that URL, and your local models become first-class n8n chat models. Keep the tunnel behind bearer auth if the URL is public, and test the pipe with a small model first.
