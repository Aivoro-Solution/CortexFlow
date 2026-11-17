---
title: "Fix n8n Microsoft OAuth2 Token Refresh Failing on Power BI 403 TokenExpired (GH #44124)"
description: "Power BI calls in n8n die with 403 TokenExpired an hour after connecting, and the Microsoft OAuth2 credential never refreshes. Here's the fix."
date: 2026-11-17
category: automation
tags: ["n8n", "microsoft", "power-bi", "oauth2", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-microsoft-oauth2-403-token-refresh.webp"
---

You connect a Microsoft OAuth2 API credential in n8n, point an HTTP Request node at the Power BI REST API, and everything works. An hour later the same node fails with `403 TokenExpired`, and it keeps failing until you open the credential and click Reconnect. Then it works for another hour, and dies again. The credential is not broken, the app registration is not broken, and the token is not missing — n8n simply never tries to refresh it.

This is a confirmed bug in n8n, filed as [GitHub issue #44124](https://github.com/n8n-io/n8n/issues/44124) on November 16, 2026 (team-assigned, Linear GHC-9794, still open as of November 17, 2026). The Microsoft OAuth2 credential only refreshes its access token when the API answers with HTTP 401. Power BI answers an expired token with **403**, so the refresh never fires. By the end of this article you will know how to confirm you have hit this exact bug, swap the node to a generic OAuth2 credential that does refresh on 403, and verify the refresh actually happens — plus what the real fix looks like and when to switch back.

Quick definitions before we start: **OAuth2** is the login-and-token flow most APIs use — n8n stores an **access token** (short-lived, about an hour for Microsoft) and a **refresh token** (long-lived) in a **credential**, and is supposed to trade the refresh token for a new access token automatically when the old one expires. **Entra ID** (formerly Azure AD) is Microsoft's identity service; an **app registration** there is the identity your n8n credential logs in as. The **Power BI REST API** (`api.powerbi.com`) is Microsoft's API for reading workspaces, datasets, and reports. A **401** means "unauthenticated" and a **403** means "forbidden" — and which one an API returns for an expired token turns out to matter a great deal here.

## The symptom: works for an hour, then 403 TokenExpired forever

The failure needs one ingredient: a Microsoft OAuth2 API credential used against an API that answers an expired token with 403. The reported case is Power BI, with a credential scoped `https://analysis.windows.net/powerbi/api/Workspace.Read.All offline_access` and an HTTP Request node calling `GET https://api.powerbi.com/v1.0/myorg/groups?$top=1`. It works immediately after connecting. About 60–90 minutes later — once the access token expires — the same node fails with:

```
NodeApiError: Forbidden - perhaps check your credentials?
description: Access token has expired, resubmit with a new access token
httpCode: 403
cause: AxiosError 403 - {"error":{"code":"TokenExpired","message":"Access token has expired, resubmit with a new access token"}}
```

The giveaway is in the credential itself: its `updatedAt` timestamp never changes after the failure, which means no refresh was even attempted. The workflow stays broken until you manually reconnect the credential, and then the whole cycle repeats an hour later. Scheduled Power BI workflows are the worst hit — they fail silently every night until someone notices and reconnects by hand.

**How to tell this bug apart from a permissions problem.** A real permissions failure also returns 403, but it fails on the very first call, not after an hour of working fine, and a manual reconnect does not fix it for another hour. The fingerprint of this bug is the clock: works right after (re)connect, breaks 60–90 minutes later, fixed again by reconnecting. If your calls fail immediately with 403, check the app registration's API permissions and admin consent first — this article's fix will not help those.

## The root cause: a credential field that never reaches the Microsoft credential

n8n decides whether to refresh a token in `requestOAuth2` (in `packages/core`, `request-helpers/oauth.ts`). It refreshes only when the response status matches a value called `tokenExpiredStatusCode`. That value is resolved by `resolveTokenExpiredStatusCode`, which reads the credential's own `tokenExpiredStatusCode` field if one is set — and otherwise falls back to the HTTP Request node's OAuth2 options, and finally to a hardcoded **401**.

The base generic credential, `oAuth2Api`, does define the field:

```typescript
{
  displayName: 'Token Expired Status Code',
  name: 'tokenExpiredStatusCode',
  type: 'number',
  default: 401,
  description: 'HTTP status code that indicates the token has expired. Some APIs return 403 instead of 401.',
  doNotInherit: true,
}
```

That `doNotInherit: true` is the whole bug. The Microsoft OAuth2 API credential (`microsoftOAuth2Api`) is built by extending `oAuth2Api`, so it inherits most fields — but not this one, and it never re-declares it. I verified this in the source: `MicrosoftOAuth2Api.credentials.ts` contains no `tokenExpiredStatusCode` at all. The credential therefore has no value for the field, the user cannot set one (it is not exposed in the credential form), and the refresh logic falls back to 401. Power BI answers 403, the status never matches, and no refresh is ever attempted.

The precedent that proves the diagnosis is already in the codebase: `DatabricksOAuth2Api` re-declares the field as a hidden property with default 403, with a code comment explaining that without it the value is always undefined and token refresh is hardcoded to 401 — Databricks returns 403 when tokens expire. Microsoft's credential simply never got the same treatment.

There is a second piece of evidence that pins the blame on the status code and nothing else. The reporter tested the same app registration, the same tenant, and the same settings against the Power Automate (Flow) API — and that credential refreshes fine, because the Flow API answers an expired token with 401. Same credential type, same token, different API, different status code: one refreshes, one does not.

## Step 1 - Confirm you have this exact bug

Before rebuilding the credential, run the one-minute test so you are not chasing a different Microsoft problem (there are several, from admin consent to wrong scopes).

1. Open the failing HTTP Request node and run it right after reconnecting the Microsoft OAuth2 API credential. It should return 200.
2. Wait until the access token expires (about 60–90 minutes) and run the node again. If it now fails with `403 TokenExpired` and the credential's `updatedAt` has not moved, you have this bug.
3. If the first run already fails with 403, you do not have this bug — check the app registration's API permissions (the Power BI scope needs admin consent in most tenants) and confirm the scope string is exactly `https://analysis.windows.net/powerbi/api/Workspace.Read.All` plus `offline_access`.

If your calls go to Microsoft Graph rather than Power BI, you almost certainly do not have this bug either: Graph answers expired tokens with 401, so the same credential refreshes normally there. This bug bites the Microsoft APIs that answer 403 — Power BI is the reported one.

## Step 2 - Build a generic OAuth2 credential with Token Expired Status Code 403

The workaround is to stop using the Microsoft OAuth2 API credential for this node and use the generic **OAuth2 API** credential instead — the one the field was defined on. It exposes "Token Expired Status Code" in its form, so you can set it to 403. Point it at the same Entra endpoints and the same app registration.

1. In n8n, go to **Credentials → Create New → OAuth2 API** (the generic one, not "Microsoft OAuth2 API").
2. Set **Grant Type** to **Authorization Code**.
3. Set **Authorization URL** to `https://login.microsoftonline.com/<your-tenant-id>/oauth2/v2.0/authorize` — replace `<your-tenant-id>` with your Entra tenant ID (or use `common` if the app is multi-tenant).
4. Set **Access Token URL** to `https://login.microsoftonline.com/<your-tenant-id>/oauth2/v2.0/token`.
5. Set **Client ID** and **Client Secret** to the same values from the Entra app registration you already use — the same app, so no new registration or consent is needed.
6. Set **Scope** to `https://analysis.windows.net/powerbi/api/Workspace.Read.All offline_access`. The `offline_access` part is load-bearing: without it Entra does not issue a refresh token, and there is nothing to refresh with.
7. Set **Token Expired Status Code** to **403**.
8. Click **Connect my account** and complete the Microsoft sign-in.

Here is what each of those fields does, and what breaks if you get one wrong. The two URLs are Entra's v2.0 OAuth endpoints — the generic credential does not know them, so you are supplying what the Microsoft credential had built in. The scope must match the API you call (`analysis.windows.net/powerbi/api` is the Power BI resource) and must include `offline_access`, or the refresh token is never issued and the 403 will keep coming back after every expiry. The Token Expired Status Code is the actual fix: it tells `requestOAuth2` that a 403 means "token expired, refresh and retry" instead of "forbidden, fail".

> **Note:** this workaround was proposed by a community member on the issue on November 17, 2026 and has not yet been confirmed by the reporter on n8n 2.47.x. The mechanism is sound — the generic credential exposes the exact field the Microsoft credential is missing, and the refresh logic reads it — but treat the verification step below as mandatory, not optional.

## Step 3 - Point the HTTP Request node at the new credential

1. Open the HTTP Request node that calls Power BI.
2. Under **Authentication**, change the credential type from **Microsoft OAuth2 API** to **OAuth2 API** and select the credential you just created.
3. Change nothing else — same URL, same method, same headers. The request itself was never the problem.
4. Execute the node once. You should see the same 200 you saw right after connecting the old credential.

You should see a 200 with the Power BI response body. If you see a 401 now, the client secret or the scope is wrong — re-check step 2, fields 5 and 6. If you see a 403 immediately, the app registration is missing the Power BI API permission or admin consent — that is a permissions problem, not this bug.

## Step 4 - Verify the refresh actually happens

A workaround you have not verified is just a different way to fail at 2 a.m. The token lives 60–90 minutes, so verification takes one expiry cycle:

1. Note the credential's `updatedAt` timestamp (visible in the credential list) and the current time.
2. Wait until the access token expires — at least 90 minutes after connecting — then execute the node again.
3. It should return 200 without any manual reconnect, and the credential's `updatedAt` should have moved: that timestamp changing is the proof a refresh happened.

If the node still returns 403 TokenExpired after expiry, double-check that the node is actually using the new generic credential (the old Microsoft credential is easy to leave selected) and that the Token Expired Status Code field is 403, not 401. One more thing to know: a genuine permission 403 — a scope the app was never granted — will now trigger one wasted refresh attempt before failing again, because n8n cannot tell "expired" from "forbidden" by status code alone. The refresh does not mask the real error; it just costs one extra round-trip before the real 403 surfaces.

## The real fix, and when to switch back

A fix is already in review as [PR #44126](https://github.com/n8n-io/n8n/pulls/44126), opened November 16, 2026. It deliberately does not re-declare the field on the shared Microsoft credential — that would make every Microsoft credential refresh on any permission-related 403. Instead it scopes the behaviour to the HTTP Request node's `microsoftOAuth2Api` options:

```typescript
microsoftOAuth2Api: {
  tokenExpiredStatusCode: [401, 403],
  skipRefreshWhileTokenIsFresh: true,
},
```

A 403 then refreshes only when the stored token is actually expired; other Microsoft credentials keep their 401 behaviour. As of November 17, 2026 the PR is open and unmerged, so there is no fixed version yet. When it lands, upgrade n8n, switch the node back to the Microsoft OAuth2 API credential, and re-run the step 4 verification — the generic credential is a bridge, not a permanent home, because the Microsoft credential carries the Entra endpoints, certificate auth, and future fixes with it.

## Prevent it next time

- **Add a heartbeat check.** A Schedule Trigger workflow that calls `GET https://api.powerbi.com/v1.0/myorg/groups?$top=1` once an hour and alerts you (Slack, Telegram, email) on a 403 TokenExpired catches the next refresh regression before a business workflow fails on it. This is the same dead-man's-switch pattern that catches any trigger or credential that silently stops working.
- **Watch the credential's `updatedAt`.** After any n8n upgrade, run the Power BI node once after token expiry and confirm `updatedAt` moved. A credential that never updates after expiry is a credential that is not refreshing.
- **Audit your other Microsoft API calls.** Any Microsoft API you call through the HTTP Request node with the Microsoft OAuth2 API credential is exposed if that API answers expired tokens with 403 instead of 401. Graph is safe (it answers 401); Power BI is not. If you add another Microsoft API, check its expired-token status code first — Microsoft's own docs do not always say.

## FAQ

### Does this affect Microsoft Graph calls?

No. Graph answers an expired token with 401, which is the status the Microsoft credential already refreshes on. This bug only bites APIs that answer 403 for an expired token. Power BI is the reported case.

### Why not just reconnect the credential every hour with a scheduled workflow?

There is no supported way to reconnect a credential from a workflow — reconnecting is a manual, browser-based OAuth flow. The generic-credential workaround is the only hands-off fix until PR #44126 ships.

### Is this the same bug as the HTTP Request "Never Error" 401 issue?

No, although the symptom looks similar. That bug ([GH #43839](https://github.com/n8n-io/n8n/issues/43839)) is about "Never Error" swallowing the 401 throw so the preAuthentication refresh never runs. This one is about the OAuth2 credential never being told that 403 means "expired" in the first place. Different code path, different fix — check which one matches your error before applying either workaround.

### Will the generic credential work with certificate authentication?

The generic OAuth2 API credential supports client-secret auth; if your Entra app uses certificate-based auth (`private_key_jwt`), stay on the Microsoft credential and reconnect manually until PR #44126 lands, because the generic credential has no certificate field. The reporter's case used client secret, which is the common setup.

## Key Takeaways

1. **Power BI answers an expired token with 403, not 401** — and n8n's Microsoft OAuth2 credential only refreshes on 401, so the credential dies about an hour after every reconnect.
2. **The cause is one missing field:** the base credential's `tokenExpiredStatusCode` is marked `doNotInherit`, the Microsoft credential never re-declares it, and the refresh logic falls back to 401. Databricks already worked around the same gap with a hidden 403 default.
3. **The workaround is a generic OAuth2 API credential** pointed at the same Entra endpoints, with `offline_access` in the scope and Token Expired Status Code set to 403 — then verify after one expiry cycle that `updatedAt` moved and the call still returns 200.
4. **The real fix is PR #44126**, which scopes `[401, 403]` plus a freshness check to the HTTP Request node's Microsoft options. Until it merges and you upgrade, the generic credential is the bridge.

Next: if you run other Microsoft APIs through n8n, check each one's expired-token status code now — Graph is safe, Power BI was not, and the next 403 could be hiding in a workflow you have not looked at in months.
