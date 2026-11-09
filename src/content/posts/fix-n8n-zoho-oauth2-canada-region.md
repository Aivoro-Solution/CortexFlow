---
title: "Fix n8n Zoho OAuth2 'Unable to sign without access token' for Canada Accounts (CN Points to China)"
description: "n8n's Zoho credential has no Canada option — 'CN' routes you to China's endpoint. Use a Generic OAuth2 credential pointed at accounts.zohocloud.ca instead."
date: 2026-11-09
category: automation
tags: ["n8n", "zoho", "oauth", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-zoho-oauth2-canada-region.webp"
---

You connect n8n to Zoho, pick the region that is supposed to be Canada, and every Zoho node fails with `Unable to sign without access token`. Your client ID and secret are correct. The redirect URI matches. The failure is not your credentials at all: n8n's built-in Zoho credential has no Canada option, and the option the documentation tells Canadian users to pick — **CN** — points at China's OAuth endpoint, not Canada's.

Quick definitions before we start: **OAuth 2.0** is the protocol n8n uses to connect to Zoho without storing your Zoho password — Zoho issues n8n a token instead. A **data center** (DC) is the regional Zoho cloud your account lives in — US, EU, IN, AU, CN, JP, CA, and others each have their own login and API domains, and a token issued by one DC is useless against another. A **Generic OAuth2 credential** is n8n's do-it-yourself credential type: you type the authorization and token URLs yourself instead of using a vendor's built-in preset.

This is a real, still-open bug: [GitHub issue #40365](https://github.com/n8n-io/n8n/issues/40365) (October 5, 2026, n8n 2.41.7) reopens [#26021](https://github.com/n8n-io/n8n/issues/26021), which was closed as stale without a fix, and the same trap has been reported on the [n8n forum since June 2025](https://community.n8n.io/t/zoho-crm-nodes/131803?page=2). As of November 9, 2026 the issue is still open and no fix appears in the 2.44 or 2.45 release notes. By the end of this article you will have a working Zoho connection for a Canada account — in about twenty minutes, using the Generic OAuth2 workaround the community has verified.

**Prerequisites:** an n8n instance (Cloud or self-hosted, any 2.x version as of November 2026), a Zoho account hosted in the Canada data center, and access to the [Zoho API Console](https://api-console.zoho.com/) to register an OAuth client.

> **Note:** this article is about Canada accounts only. If your Zoho account lives in the US, EU, or IN data center, the built-in Zoho credential works — pick the matching region and stop here. If you are fighting a redirect-URI error on Google instead, that is a different provider entirely — covered in [Fix n8n Google OAuth2 Redirect URI Mismatch Error](/blog/fix-n8n-google-oauth2-redirect-uri-mismatch/).

## The symptom: what the failure actually looks like

The failure has one consistent fingerprint:

1. You create a Zoho OAuth2 credential in n8n, select **CN** as the region (because the [n8n Zoho credentials docs](https://docs.n8n.io/integrations/builtin/credentials/zoho) say "CN: Select this option for Canada data center"), and the OAuth flow appears to complete.
2. The first Zoho node that runs fails with: `Problem in node 'Get a lead' — Unable to sign without access token`.
3. Reconnecting, re-issuing the client secret, and recreating the credential all fail the same way. Switching to the **US** region also fails — the US endpoint cannot authenticate a Canada account either.

**How to confirm in one minute:** look at the Access Token URL the CN option actually configured. If it reads `https://accounts.zoho.com.cn/oauth/v2/token`, you are knocking on China's door with a Canadian account. The Canada endpoint is `https://accounts.zohocloud.ca` — a completely different domain. That one URL is the whole diagnosis.

## The root cause: CN means China, and there is no CA option

Zoho runs separate regional clouds, and every account lives in exactly one of them. The regions and their login domains:

| Data center | Accounts (OAuth) domain | API domain |
|---|---|---|
| US | accounts.zoho.com | www.zohoapis.com |
| EU | accounts.zoho.eu | www.zohoapis.eu |
| IN | accounts.zoho.in | www.zohoapis.in |
| AU | accounts.zoho.com.au | www.zohoapis.com.au |
| **CA (Canada)** | **accounts.zohocloud.ca** | **www.zohoapis.ca** |
| CN (China) | accounts.zoho.com.cn | www.zohoapis.com.cn |

n8n's built-in Zoho credential exposes a region dropdown with no CA entry. The documentation papered over the gap by labelling CN as the Canada option — but CN configures `accounts.zoho.com.cn`, the China endpoint. A token request sent there can never return a token your Canada account will accept, so n8n ends up with no access token at all and every node reports `Unable to sign without access token`. The issue reporter verified this on n8n 2.41.7 (Docker, self-hosted) and asked for what should exist: a CA region option using `https://accounts.zohocloud.ca`.

**The fix, in one sentence: stop using the built-in Zoho credential and build the same connection yourself with a Generic OAuth2 credential pointed at the `.ca` domains.** The four fixes below are that workaround, end to end, plus the two Zoho-specific quirks that break the naive version of it.

## Fix 1 — Build a Generic OAuth2 credential for the Canada data center

This is the fix the forum has verified for Quebec and Ontario accounts since June 2025: the HTTP Request node plus a Generic OAuth2 credential, with every URL pointed at the Canada domains.

**Step 1.1 — Register a Server App in the Zoho API Console.** Go to the [Zoho API Console](https://api-console.zoho.com/), create a client, and choose **Server-based Applications** as the client type — not a client-side or self-client app. Set the authorized redirect URI to your n8n OAuth callback:

```text
https://<your-n8n-host>/rest/oauth2-credential/callback
```

Replace `<your-n8n-host>` with your instance's public host (for n8n Cloud, your `*.app.n8n.cloud` domain). Copy the **Client ID** and **Client Secret** — you will paste them into n8n in the next step.

> **Warning:** a client registered as the wrong type is the second-most-common failure after the region itself. If the console offers "Server-based Applications", "Client-based", and "Self Client", only Server-based issues the refresh tokens this setup depends on.

**Step 1.2 — Create the Generic OAuth2 credential in n8n.** In n8n, go to **Credentials → New → OAuth2 API** (the generic one, not the Zoho preset) and fill in exactly these values:

| Field | Value |
|---|---|
| Grant Type | Authorization Code |
| Authorization URL | `https://accounts.zohocloud.ca/oauth/v2/auth` |
| Access Token URL | `https://accounts.zohocloud.ca/oauth/v2/token` |
| Client ID | From the Zoho API Console (step 1.1) |
| Client Secret | From the Zoho API Console (step 1.1) |
| Scope | `ZohoCRM.modules.ALL` (narrow this to the modules you actually use, e.g. `ZohoCRM.modules.leads.ALL`) |
| Auth URI Query Parameters | `access_type=offline&prompt=consent` |
| Authentication | Header (default) |

**Here's what each value does:** the two `.ca` URLs are the entire fix — they send the OAuth dance to Canada instead of China. `access_type=offline` tells Zoho to issue a refresh token alongside the access token; without it, Zoho issues an access token that dies after one hour and n8n has nothing to refresh with. `prompt=consent` forces Zoho to show the consent screen every time you connect, which is what makes Zoho actually store that refresh token — forum users who skipped it got a new "re-authenticate" error an hour later.

**Step 1.3 — Connect and confirm.** Click **Connect my account**, sign in with your Canada Zoho account, and approve the consent screen. You should see the credential save with a green "Account connected" state. If Zoho shows an error page instead, check the URL bar: an `error=invalid_client` means the Client ID/secret or redirect URI does not match the API Console entry — re-check step 1.1 character by character.

## Fix 2 — Call the API on the .ca domain with the right header

A connected credential is only half the job. Zoho API calls go to a different domain than the OAuth endpoints, and the header format is Zoho-specific.

**Use the Canada API domain, not the US one.** Every HTTP Request node call should target `https://www.zohoapis.ca`, for example:

```text
GET https://www.zohoapis.ca/crm/v8/Contacts?fields=Last_Name
```

**Do not hardcode the API domain if you can avoid it.** The token response Zoho returns includes an `api_domain` field — that value is the base URL your account is supposed to use. Read it from the token response and use it as the base URL; it protects you if Zoho ever moves your account between domains.

**Send `Zoho-oauthtoken`, not `Bearer`.** This is the quirk that costs people a second afternoon: Zoho's token response says `token_type: Bearer`, but the API rejects the `Bearer` scheme with a 401. The correct header is:

```text
Authorization: Zoho-oauthtoken <your-access-token>
```

n8n's Generic OAuth2 credential handles this for you once it is configured — it attaches the token using the header format the credential defines — but if you ever call Zoho from a Code node or an external script, use `Zoho-oauthtoken`.

## Fix 3 — Handle Zoho's refresh-token quirk before it bites you

Zoho access tokens live for one hour. The refresh is where this workaround can still break, for a Zoho-specific reason: Zoho's own documentation lists `grant_type`, `client_id`, `client_secret`, and `refresh_token` as **query string** parameters for `/oauth/v2/token`, and Zoho's backend records refresh calls that send them in the request body as missing `grant_type`. n8n's OAuth client sends the refresh in the body. The practical consequences:

- **If n8n's automatic refresh works on your version, do nothing.** Test it: connect, wait just over an hour (or revoke the access token in the Zoho console), and run the workflow again. If it succeeds, your version's refresh path is fine.
- **If the workflow fails after an hour with a token error, refresh manually.** Add a small refresh step to your workflow: an HTTP Request node that POSTs to the Canada token URL with the parameters in the query string, then stores the new access token for the calls that follow:

```text
POST https://accounts.zohocloud.ca/oauth/v2/token?grant_type=refresh_token&client_id=<your-client-id>&client_secret=<your-client-secret>&refresh_token=<your-refresh-token>
```

- **Never refresh against a different data center's URL.** A token issued by the Canada DC will not refresh against `accounts.zoho.com` or `accounts.zoho.com.cn` — the refresh must go to the same `.ca` domain that issued it. This is the same rule as the original bug, one layer down.

## Fix 4 — Verify the whole chain with one real API call

Run this check after fixes 1–3. It proves the credential, the domain, the header, and the token all work at once:

1. Add an HTTP Request node using the Generic OAuth2 credential from fix 1.
2. Method `GET`, URL `https://www.zohoapis.ca/crm/v8/Contacts?fields=Last_Name`, and execute it.
3. **You should see** an HTTP 200 response with a JSON body containing your contacts' `Last_Name` values.

If you get a 401 here, the token is wrong for the domain — re-check that the credential's token URL is `accounts.zohocloud.ca` and the API call is `www.zohoapis.ca`. If you get a 200 with an empty `data` array, the connection works and your CRM simply has no contacts yet — that is a success, not a failure.

## Prevent it next time

- **Check the data center before creating any Zoho credential.** Log in at `accounts.zohocloud.ca` — if that is where your Zoho account lives, you are a Canada account and the built-in Zoho credential will not work for you. The same check applies to any integration tool: if its Zoho region list has no CA entry, use its generic OAuth2 option with the `.ca` URLs above.
- **Watch GitHub issue #40365** for a native fix. The correct upstream fix is a CA region option in the built-in Zoho credential using `https://accounts.zohocloud.ca`. Until that ships, the Generic OAuth2 setup in this article is the supported path — keep it even after upgrading n8n, and only switch back once the changelog explicitly mentions a Canada region.
- **Keep the refresh test in your runbook.** After every n8n upgrade, re-run the one-hour-later check from fix 3. OAuth client behavior is exactly the kind of thing a minor release changes silently.

## FAQ

### Is this the same as the "CN" region other tools show for Zoho?

No — and that is the trap. In Zoho's own naming, CN is China (`accounts.zoho.com.cn`). Some tools and docs have mislabelled CN as Canada, which is how this bug survived: the label looked right and the endpoint was wrong. Canada is CA, endpoint `accounts.zohocloud.ca`.

### My Zoho account is 10+ years old and the US endpoint works for me. Why?

Older Canadian accounts were sometimes created on the US data center before Zoho opened the Canada DC. If `accounts.zoho.com` authenticates you, your account lives in the US region and the built-in credential is fine. The bug only hits accounts actually hosted in Canada.

### Does this affect Zoho Desk, Zoho Books, or other Zoho apps?

Yes — every Zoho product shares the same accounts domain per data center. The Generic OAuth2 workaround works for any of them; only the scope and the API base path change (for example, `desk.zoho.ca` for Desk). The ten Zoho data centers are US, EU, IN, AU, CN, JP, CA, SA, SG, and UAE.

### Will upgrading n8n fix this?

Not as of November 9, 2026. Issue #40365 is still open, and the 2.44/2.45 release notes contain no Zoho region fix. Upgrade for everything else, but keep the Generic OAuth2 credential until a release explicitly adds the CA option.

## Key Takeaways

1. **CN is China, not Canada** — n8n's docs mislabel it, and the CN option configures `accounts.zoho.com.cn`, which can never authenticate a Canada account.
2. **The symptom is `Unable to sign without access token`** — the credential ends up with no token at all, so reconnecting and re-issuing secrets never helps.
3. **Use a Generic OAuth2 credential** with Authorization and Token URLs at `accounts.zohocloud.ca`, API calls at `www.zohoapis.ca`, and `access_type=offline&prompt=consent` so Zoho stores a refresh token.
4. **Send `Zoho-oauthtoken`, not `Bearer`**, and read `api_domain` from the token response instead of hardcoding an API domain.
5. **Refresh against the same `.ca` domain that issued the token** — and if automatic refresh fails, POST the refresh with `grant_type` in the query string, as Zoho's docs require.

Next: if OAuth is your recurring pain point across providers, read [Fix n8n Salesforce OAuth 'The Requested Scope Is Not Allowed' Error](/blog/fix-n8n-salesforce-oauth-scope-error/) — same family of bug, different provider, same diagnose-from-the-URL discipline.

*Sources: [n8n-io/n8n#40365](https://github.com/n8n-io/n8n/issues/40365) (Oct 5, 2026; n8n 2.41.7; reopens #26021) · [n8n forum: Zoho CRM nodes](https://community.n8n.io/t/zoho-crm-nodes/131803?page=2) (June 2025, `.ca` workaround) · [n8n forum: Builtin OAuth 2.0 refresh-token grant type](https://community.n8n.io/t/builtin-oauth-2-0-supports-grant-type-refresh-token/305910) (Zoho query-string refresh quirk) · [n8n Zoho credentials docs](https://docs.n8n.io/integrations/builtin/credentials/zoho).*
