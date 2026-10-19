---
title: "Fix n8n Google OAuth2 Redirect URI Mismatch Error (5 Exact Fixes)"
description: "Google shows Error 400: redirect_uri_mismatch on your n8n Gmail, Drive, or Sheets credential? Fix it with the exact redirect URL and correct n8n env vars."
date: 2026-10-19
category: automation
tags: ["n8n", "Google OAuth", "OAuth2", "self-hosting", "troubleshooting"]
image: "/og/fix-n8n-google-oauth2-redirect-uri-mismatch.webp"
draft: false
featured: false
---

You click "Connect a Google account" on your n8n Gmail or Google Drive credential, and instead of the Google consent screen you get this:

> **Error 400: redirect_uri_mismatch**
> You can't sign in because this app sent an invalid request.

Or the newer variant: **"Access blocked: This app's request is invalid."**

This is the single most common OAuth failure in self-hosted n8n, and the fix is almost always the same one thing: the redirect URL n8n sends in the OAuth request does not **exactly** match any redirect URI you registered in Google Cloud Console. Google compares the two strings character-for-character. One trailing slash, one `http` instead of `https`, or n8n generating the URL from the wrong base URL — and the whole flow dies.

This guide walks you through the symptom, the three root causes, and the exact fixes in order, verified against community.n8n.io threads and n8n's own docs.

## The symptom

The failure happens at credential-connect time, never mid-workflow. Typical patterns:

1. **"Error 400: redirect_uri_mismatch"** on Google's page when you try to connect a Gmail, Google Drive, Google Sheets, Google Calendar, or Google OAuth2 API credential.
2. **"Access blocked: This app's request is invalid"** — same root cause, Google's newer wording.
3. **"Error: Client authentication failed"** right after — often appears when you've half-fixed the URI but are editing the *wrong* OAuth client in a project that has several.

Click the "Error details" or "Request Details" link on Google's error page if it's shown. It names the failing parameter explicitly. If it says `redirect_uri_mismatch`, the problem is 100% the redirect URI — not your client ID, not your scopes, not your APIs.

## The root cause

Google OAuth requires you to pre-register every redirect URI your app may use. When n8n starts the OAuth dance, it sends a `redirect_uri` parameter in the authorization request. Google looks it up in your OAuth client's **Authorized redirect URIs** list. Anything less than an exact string match is rejected.

Three things break that match in n8n:

1. **A sloppy registered URI.** You registered `https://n8n.example.com/rest/oauth2-credential/callback/` (trailing slash) or `http://` (no TLS) or a subtly different domain. Google rejects all of them.
2. **n8n generates the wrong URL in the first place.** The "OAuth Redirect URL" shown in the credential window is derived from n8n's own base URL at runtime. If n8n thinks it lives at `http://localhost:5678` — because `N8N_HOST`, `WEBHOOK_URL`, and friends aren't set on a Docker/self-hosted install — the URL it sends won't match the public-domain URI you registered. No amount of editing Google Console fixes this one; you have to fix n8n's config.
3. **You're editing the wrong OAuth client.** Google Cloud projects accumulate clients. If you register the URI on client A but pasted client B's ID/secret into n8n, nothing lines up.

There's a fourth special case for **n8n Cloud** users: custom Google OAuth clients on Cloud are unreliable because n8n injects its own internal flow parameters (e.g. `?flowName=GeneralOAuthFlow`) into the callback at runtime, changing the effective redirect URI. Community-tested advice: on n8n Cloud, don't fight it — use n8n's built-in Google credentials instead of a custom OAuth client.

## Fix 1 — Register the exact redirect URI in Google Cloud (fixes ~80% of cases)

The correct URI is always:

```
https://YOUR-N8N-DOMAIN/rest/oauth2-credential/callback
```

Do this exactly:

1. In n8n, go to **Credentials → Add credential → Gmail OAuth2** (or your Google service of choice).
2. At the top of the credential window, n8n shows **"OAuth Redirect URL"**. Copy it — character for character. (For a domain install it looks like `https://n8n.example.com/rest/oauth2-credential/callback`; for local dev, `http://localhost:5678/rest/oauth2-credential/callback`.)
3. Open [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services → Credentials**.
4. Click your **OAuth 2.0 Client ID** (it must be type **Web application** — "Desktop" and "Other" types can't use redirect URIs).
5. Under **Authorized redirect URIs**, click **+ ADD URI** and paste the copied URL.
6. Save. Wait ~5 minutes — Google's propagation is fast but not instant.

**Rules that trip people up:**

- **No trailing slash.** `.../callback/` ≠ `.../callback`. Google treats these as different URIs.
- **`https`, not `http`** — except for `http://localhost` during local development, which Google explicitly allows.
- **Match the client.** If you have multiple OAuth clients in the project, make sure the one you're editing is the one whose Client ID and Secret are pasted into n8n. Copy the ID/secret again to be sure — no leading/trailing spaces.
- **The API must be enabled.** The Google Sheets API, Drive API, Gmail API (whichever you use) must be enabled in **APIs & Services → Library** for this project. A missing API gives a different error, but rule it out while you're here.

Now retry the connect flow in n8n. If you now see Google's consent screen instead of Error 400, this fix was it.

## Fix 2 — When n8n shows `http://localhost:5678/rest/oauth2-credential/callback` (the self-hosted trap)

If the "OAuth Redirect URL" in the n8n credential window shows `http://localhost:5678/...` on an instance that is *not* running on your laptop — a VPS, a home server behind a reverse proxy, a Docker install — n8n is building the URL from its internal address instead of its public one. The fix is environment variables, then a restart.

Add these to your n8n environment (`.env` file, `docker-compose.yml` `environment:` block, or your systemd service — **whichever file your instance actually reads**):

```bash
N8N_HOST=n8n.example.com
N8N_PROTOCOL=https
WEBHOOK_URL=https://n8n.example.com
N8N_EDITOR_BASE_URL=https://n8n.example.com
N8N_PROXY_HOPS=1   # only needed behind a reverse proxy (nginx, Caddy, Traefik)
```

What each one does:

- `N8N_HOST` + `N8N_PROTOCOL` — the hostname and scheme n8n advertises about itself.
- `WEBHOOK_URL` — the public base URL; most important when behind a reverse proxy, where n8n can't derive it from incoming headers.
- `N8N_EDITOR_BASE_URL` — the URL of the editor UI; OAuth flows use this to build the callback URL.
- `N8N_PROXY_HOPS=1` — tells n8n to trust `X-Forwarded-Proto` from one proxy hop so it generates `https://` URLs even though the container itself receives plain HTTP from the proxy.

Then:

```bash
docker compose down
docker compose up -d
docker compose logs -f n8n   # confirm it boots clean
```

**Gotcha:** if you changed the env file and the URL still shows localhost after restart, n8n is reading config from somewhere else — a different `docker-compose.yml` (common locations: `/opt/n8n`, `/root/n8n-docker`), a systemd override, or a preinstalled setup that bakes env into the image. Run `docker ps`, find the container name, and check which compose project it belongs to with `docker inspect <container> --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'`.

**Recreate the credential.** If the Google credential was first created while n8n believed its URL was `localhost`, the stored flow state may reference the old URL. Delete the credential in n8n, create a fresh one (client ID/secret unchanged), and redo Fix 1 with the now-correct public OAuth Redirect URL.

## Fix 3 — Consent screen: authorized domains + publish the app

Even with a perfect redirect URI, two consent-screen settings block the flow:

1. **Authorized domains.** Google Cloud Console → **APIs & Services → OAuth consent screen** → scroll to **Authorized domains**. Add your domain's root (e.g. `example.com`). Google requires the callback URI's base domain to be listed here, especially with auto-generated PaaS subdomains.
2. **Testing vs. Production.** If the consent screen's publishing status is **Testing**, OAuth works for test users — but refresh tokens are revoked after 7 days, so your Google credentials will "expire" every week and need re-authentication. For a personal instance: go to the **Audience** tab and click **Publish App**. You don't need Google verification for personal use — you'll just see the "Google hasn't verified this app" warning during auth; click **Advanced → Go to (app name) (unsafe)** to proceed.

## Fix 4 — n8n Cloud users: use the built-in Google credentials

On n8n Cloud, a custom Google OAuth client is fighting platform behavior: n8n Cloud appends internal flow parameters (e.g. `?flowName=GeneralOAuthFlow`) to the callback URL at runtime, so the redirect URI you registered never exactly matches the one sent. The community-tested fix is to **not use a custom OAuth client at all** — pick n8n's built-in Google credential for the service (Gmail, Drive, Sheets…), which is already registered against Google's OAuth policy. No client ID, no secret, no redirect URI to manage.

## How to verify the fix worked

1. In n8n, open the Google credential and click **Connect a Google account** (or "Sign in with Google").
2. You should now see Google's **"Choose an account"** screen, then the **consent screen** listing the scopes (Gmail, Drive, etc.).
3. Approve → the OAuth window closes and the credential shows **"Connected"** in n8n.
4. Run a one-node test: a Gmail node "Get many messages" with limit 1, or a Google Sheets node "Get rows" on a small sheet. If data comes back, the whole chain (redirect URI → tokens → API) is healthy.

## Prevent it next time

- **Decide the canonical public URL once** (`https://n8n.example.com`) and put `N8N_HOST`, `N8N_PROTOCOL`, `WEBHOOK_URL`, and `N8N_EDITOR_BASE_URL` in your compose file from day one. Never run a production install with defaults.
- **One URI, one client.** Register exactly one redirect URI on one "Web application" OAuth client per n8n instance. Delete stale clients and duplicate URIs (including the trailing-slash twin) so future-you can't edit the wrong one.
- **After any domain or proxy change:** restart n8n, check the OAuth Redirect URL shown in a fresh credential window, and re-register it in Google Cloud. Assume the URL is stale until you look.

## FAQ

### Why does Google say the request is invalid instead of just showing the consent screen?

Google validates `redirect_uri` before anything else. If it's not an exact match for a registered URI, Google refuses to show the consent screen at all — it can't know which app legitimately owns that callback, so it blocks with Error 400: redirect_uri_mismatch.

### Can I register multiple redirect URIs for one OAuth client?

Yes — Google allows multiple entries under Authorized redirect URIs. That's how you handle both `https://n8n.example.com/rest/oauth2-credential/callback` and `http://localhost:5678/rest/oauth2-credential/callback` on one client. But each entry must be exact; there are no wildcards.

### I added the URI exactly but still get the error. What now?

Three checks, in order: (1) you're editing the OAuth client whose credentials are pasted in n8n — not a lookalike client; (2) wait 5–10 minutes and retry in a fresh incognito window (stale cached OAuth sessions cause ghost errors); (3) the client type is "Web application". If the n8n credential window still shows a localhost URL on a remote instance, jump to Fix 2 — the problem is n8n's base URL, not Google.

### Does changing the redirect URI invalidate existing connections?

No. Already-connected credentials keep working with their stored refresh tokens. The redirect URI only matters during the initial connect/authorize flow.

## Conclusion

The redirect_uri_mismatch error looks intimidating, but it's a string-comparison problem: copy n8n's exact "OAuth Redirect URL" into Google Cloud's Authorized redirect URIs with zero deviations, or fix n8n's env vars when it generates the wrong URL in the first place. Do that once, and every Google credential — Gmail, Drive, Sheets, Calendar — connects cleanly.

If you're self-hosting n8n on Docker, pair this with proper instance configuration from the start — our guides on [fixing n8n OOM crashes in Docker Compose](/blog/fix-n8n-oom-crash-docker-compose/) and [connecting local Ollama to cloud n8n through a tunnel](/blog/connect-local-ollama-cloud-n8n-tunnel/) cover the two next most common self-hosting headaches.
