---
title: "Fix n8n Salesforce OAuth 'The Requested Scope Is Not Allowed' Error (5 Fixes)"
description: "n8n's Salesforce credential fails with 'the requested scope is not allowed'? Align the Connected App scopes and fix PKCE — 5 verified fixes."
date: 2026-11-08
category: automation
tags: ["n8n", "salesforce", "oauth", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-salesforce-oauth-scope-error.webp"
---

You click **Connect my account** on n8n's Salesforce credential and Salesforce answers with `the requested scope is not allowed` — or its even less helpful cousin, `OAUTH_APPROVAL_ERROR_GENERIC` ("We can't authorize you because of an OAuth error"). Your Salesforce login works fine in the browser. The password is right. The error is not about your password at all: it is about what n8n is *allowed to ask for* versus what the Salesforce Connected App is *configured to grant*.

Quick definitions before we start: **OAuth 2.0** is the protocol n8n uses to connect to Salesforce without storing your Salesforce password — Salesforce issues n8n a token instead. A **Connected App** is Salesforce's record of an external application (here, n8n) and the permissions it may request. **Scopes** are the individual permissions inside that record — `api` lets the app call Salesforce APIs, `refresh_token` lets it stay connected without re-login, `offline_access` is the companion scope for long-lived access. **PKCE** (Proof Key for Code Exchange) is an extra code-challenge check Salesforce now enforces on OAuth flows.

This error is reported repeatedly on the n8n forum — as the scope error itself ([community.n8n.io/t/48336](https://community.n8n.io/t/issue-accessing-salesforce-via-n8n-with-oauth-2-method-oauth-approval-error-generic-related-to-full-scope/48336/2), June 2024, with an n8n team reply), as Salesforce nodes spinning forever after a "successful" connection ([community.n8n.io/t/253469](https://community.n8n.io/t/salesforce-nodes-just-spin-indefinitely/253469)), and as a PKCE code-challenge failure ([community.n8n.io/t/31845](https://community.n8n.io/t/salesforce-credentials-bug-with-code-challenge/31845.rss)). By the end of this article you will know which of the five causes is yours, the exact clicks to fix it, and how to prove the credential works — in about fifteen minutes.

**Prerequisites:** an n8n instance (Cloud or self-hosted, any 2.x version as of November 2026) and a Salesforce user with admin access to the org — three of the five fixes happen inside Salesforce Setup, not inside n8n.

> **Note:** this article is about *connecting at all*. If your credential test passes but Salesforce nodes spin indefinitely with no error, skip to fix 4 — that is a different failure wearing the same costume. And if you are fighting a redirect-URI error on Google instead, that is a different provider entirely — covered in [Fix n8n Google OAuth2 Redirect URI Mismatch Error](/blog/fix-n8n-google-oauth2-redirect-uri-mismatch/).

## The symptom: what the failure actually looks like

The failure has a consistent fingerprint, but the message changes depending on which check trips first:

1. **"The requested scope is not allowed"** — shown during the OAuth consent step. n8n asked for a scope the Connected App does not list. This is the most common variant.
2. **OAUTH_APPROVAL_ERROR_GENERIC** — Salesforce's catch-all for the same family of problems: "We can't authorize you because of an OAuth error. For more information, contact your Salesforce administrator." The real reason is hidden in the browser URL — more on that in the diagnosis step below.
3. **Nodes spin indefinitely, no error** — the credential connects, the OAuth dance completes, and then every Salesforce node spins forever. The token was issued but the app has no API permission, so calls never return.
4. **"Missing required code challenge" / "Insufficient parameters for OAuth2 callback"** — the PKCE variant. The authorization URL Salesforce received had no `code_challenge` parameter.

**How to confirm in one minute:** when the error page appears, look at the browser address bar before closing it. Salesforce appends `error` and `error_description` parameters to the URL — `error=invalid_scope` with a description naming the scope is the scope-mismatch diagnosis, no guessing required.

## Diagnose first: read the error out of the URL

Before changing anything, reproduce the failure once and copy the full URL from the error page. The query string carries the verdict:

| URL parameter | What it means | Go to |
|---|---|---|
| `error=invalid_scope` | A requested scope is not in the Connected App | Fix 1 |
| `error=OAUTH_APPROVAL_ERROR_GENERIC` | App not installed / user not allowed to approve it | Fix 2 |
| `error=invalid_request`, `missing required code challenge` | PKCE mismatch | Fix 3 |
| No error at all, but nodes spin forever | Token issued, API access blocked | Fix 4 |
| `redirect_uri_mismatch` | Callback URL does not match the Connected App | Fix 5 |

If the error page gives you nothing, the n8n forum's own guidance for this exact thread applies: check the URL first, because the on-screen message is generic by design.

## Fix 1 - Align the scopes in the Connected App

This is the cause in most cases, and it is the one the error message actually names. Salesforce rejects any authorization request whose scopes are not a subset of the Connected App's configured scopes. The classic trigger is the blanket `full` scope: if the app is configured with granular scopes only, a request asking for `full` fails outright — which is exactly what the June 2024 forum thread hit. Salesforce's Winter '26 release tightened this further, rejecting tokens without valid scopes that older releases tolerated.

In Salesforce, open **Setup → Apps → App Manager**, find the Connected App n8n uses, click the dropdown arrow and choose **Manage**, then **Edit Policies**. Under **OAuth Policies → Permitted Users** and **Selected OAuth Scopes**, make sure these three scopes are selected:

- `api` — "Access and manage your data" (without this, n8n cannot call the Salesforce REST API at all)
- `refresh_token` — "Perform requests on your behalf at any time" (without this, the token dies and n8n cannot refresh it)
- `offline_access` — "Perform requests at any time" (the companion scope for long-lived access)

Save, then re-run the connection in n8n. **Do not add `full`** — it grants everything and is precisely the scope that trips the mismatch when the app was set up with granular scopes. If you are on n8n Cloud, you do not create your own Connected App: n8n's own app is the one being authorized, and a Salesforce admin still needs to allow it — which is fix 2.

> **Warning:** scope changes take effect on the *next* authorization. An existing connected credential keeps its old token — after changing scopes, disconnect and reconnect the credential in n8n, or the fix will look like it did nothing.

## Fix 2 - Install the Connected App (or grant "Approve Uninstalled Connected Apps")

Salesforce's October 2025 security update changed the rules: a non-admin user can no longer authorize a Connected App that has not been installed in the org. If the app is uninstalled and the user lacks the new permission, the flow dies with `OAUTH_APPROVAL_ERROR_GENERIC` before the approval screen even renders.

A Salesforce admin has two options, and the first is the recommended one:

1. **Install the app org-wide:** **Setup → Connected Apps OAuth Usage** → find the app → **Install**. Every user can then authorize it, and the error disappears for the whole team at once.
2. **Grant the permission instead:** **Setup → Permission Sets** → select or create a permission set assigned to the affected users → enable the **Approve Uninstalled Connected Apps** system permission. This lets those users approve uninstalled apps themselves.

One caveat from the field: the permission may be greyed out or unavailable for some license types, particularly in sandboxes whose licenses do not match production. If that happens, use **Setup → Company Information → Match Production Licenses** in the sandbox to resync the license definitions, then try again — or just install the app via option 1, which sidesteps the permission entirely.

## Fix 3 - Fix the PKCE setting on the Connected App

PKCE is the code-challenge check Salesforce now mandates for OAuth flows (enforced from Spring '26). n8n's Salesforce credential had a genuine bug here: older versions sent an authorization request without the `code_challenge` parameter, and Salesforce answered `invalid_request` / `missing required code challenge`. The n8n team filed this internally as NODE-873 and the fix shipped in the credential — but the Connected App side of the setting still has to match.

In the Connected App, open **Manage → Edit Policies → OAuth Policies** and check **Require Proof Key for Code Exchange (PKCE) for Supported Authorization Flows**:

- **On n8n 2.x (current):** leave PKCE **enabled** on the app. The credential sends the challenge correctly, and disabling it weakens the flow for no benefit.
- **On an older n8n (1.x, or a version predating the NODE-873 fix):** if you see the `missing required code challenge` error, **disable PKCE on the app** as the workaround — that is the n8n team's own recommendation from the forum thread — then upgrade n8n and re-enable it.

Verify the fix by watching the authorization URL in the browser during the connect step: it should contain a `code_challenge` parameter. If it does not, you are on the old credential behavior and the upgrade is the real fix.

## Fix 4 - Give the user API access (the "spinning nodes" cause)

This is the sneakiest variant because everything *looks* connected. The OAuth flow completes, the credential test passes, and then a simple "Get an account" node spins forever. The diagnosis from the forum thread is blunt: the credential is valid but not actually allowed to make API calls. Two Salesforce settings cause it:

1. **The user profile lacks API access.** In Salesforce, open **Setup → Users → Profiles** → the user's profile → **System Permissions** → enable **API Enabled**. Without it, the token is issued but every API call is refused — and n8n waits for a response that never comes.
2. **Login IP Ranges block the request.** If the profile or the Connected App has **Login IP Ranges** configured, requests from n8n's IP (or your self-hosted server's IP) are rejected. Either add the n8n egress IP to the range or clear the restriction for the integration user.

After either change, disconnect and reconnect the credential in n8n, then run the simplest possible test: a Salesforce node with operation **Get** on a single known Account record. If it returns data in seconds instead of spinning, you found it.

## Fix 5 - Match the callback URL and the environment exactly

If the URL diagnosis shows `redirect_uri_mismatch`, the callback URL in the authorization request does not exactly match the one registered on the Connected App — and "exactly" means exactly, including the trailing slash and the scheme.

- **n8n Cloud:** the callback URL is the one n8n shows you on the credential screen. Copy it from n8n and paste it into the Connected App's **Callback URL** field — do not type it from memory.
- **Self-hosted:** the callback URL is built from your instance URL. Make sure `N8N_HOST` and `N8N_WEBHOOK_URL` are set to the public `https://` address in your environment (`.env` or compose file), restart n8n, and then copy the callback URL from the credential screen into the Connected App. An `http://` URL or a `localhost` host in the callback will fail.
- **Sandbox vs production:** use the right login host. A sandbox org authorizes at `test.salesforce.com`; a production org at `login.salesforce.com`. n8n's Salesforce credential has an **Environment** setting for exactly this — if it points at production while your user lives in a sandbox, authorization fails no matter how correct everything else is.

## Verify the fix worked

Run this checklist in order — each step proves one layer:

1. **Reconnect the credential** in n8n (Credentials → Salesforce OAuth2 → reconnect). A fresh authorization is what picks up scope, PKCE, and app-install changes.
2. **Run the credential test** — it should pass in seconds, not spin.
3. **Execute a real node:** Salesforce node → Resource **Account** → Operation **Get** → a known record ID. You should see the record's fields in the output panel.
4. **Wait out one token refresh:** access tokens last about two hours. Run the same node again after the token expires (or revoke the session in Salesforce and re-run) — if it still works, `refresh_token` and `offline_access` are correctly granted and the fix is durable, not a one-off.

If step 3 spins but step 2 passed, you are back at fix 4 — the token exists but API access is blocked.

## Prevent it next time

- **Use a dedicated integration user** with its own profile (API Enabled on, no IP-range surprises) instead of a human admin's account. When that person leaves or their profile changes, your automations do not die with them.
- **Keep the Connected App's scopes minimal and explicit** — `api`, `refresh_token`, `offline_access` — and write them down in the workflow's notes. The next person to touch the app will otherwise "tidy up" a scope and break the connection.
- **Install the Connected App org-wide on day one** (fix 2, option 1) instead of relying on per-user approval permissions.
- **Add a heartbeat check:** a tiny scheduled workflow that reads one Salesforce record and alerts you if it fails. Salesforce scope and permission changes are silent — the first symptom is usually a workflow that stopped working three days ago.

## FAQ

### Do I need to create my own Connected App for n8n?

No — on n8n Cloud you authorize n8n's own Connected App, and a Salesforce admin needs to install or allow that app in your org. On self-hosted n8n you *can* create your own Connected App with your own Client ID and Secret, which gives you full control over scopes and PKCE — and full responsibility for keeping them aligned.

### Why did this work last month and break now?

Most likely Salesforce's October 2025 security update (uninstalled-app approval now requires admin install or the new permission) or the Winter '26 scope tightening. Neither change breaks the login — both break the *authorization*, which is why the failure feels sudden and the error message feels unrelated.

### The credential test passes but nodes still spin — is that the same bug?

Same family, different cause: the token was issued but API access is blocked (fix 4). Check **API Enabled** on the user's profile and the Login IP Ranges first — that exact symptom is documented in the forum thread linked above.

## Key Takeaways

1. **The error is about permissions, not your password** — n8n asked for a scope the Connected App does not grant, or the app was never installed in the org.
2. **Read the browser URL first** — `error=invalid_scope`, `OAUTH_APPROVAL_ERROR_GENERIC`, and `missing required code challenge` each point at a different fix.
3. **The working scope set is `api` + `refresh_token` + `offline_access`** — never `full` against a granularly-configured app.
4. **A passing credential test proves nothing about API access** — if nodes spin forever, check **API Enabled** and IP ranges on the profile.
5. **Verify past one token refresh** — a fix that only works until the two-hour token expires is not a fix.

Next: if Salesforce is one of several CRMs you automate, the same scope-discipline applies everywhere — check the [n8n Google OAuth2 redirect URI fix](/blog/fix-n8n-google-oauth2-redirect-uri-mismatch/) for the Google side of the same story, and keep a heartbeat workflow on every production credential.
