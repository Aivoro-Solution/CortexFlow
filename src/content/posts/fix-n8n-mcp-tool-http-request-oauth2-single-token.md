---
title: "Fix n8n MCP Tool and HTTP Request Breaking Each Other's OAuth2 Auth"
description: "Your n8n MCP tool and HTTP Request node keep invalidating each other's OAuth2 token. One shared credential in n8n 3.3 fixes it. Here is how."
date: 2026-11-28
category: automation
tags: ["n8n", "error-fix", "mcp", "oauth2", "ai-agent"]
draft: false
featured: false
image: "/og/fix-n8n-mcp-tool-http-request-oauth2-single-token.webp"
---

Your MCP tool works. Your HTTP Request node works. Then one of them reconnects, and the other starts failing auth — until you reconnect that one, which breaks the first again. This is not a flaky provider: before n8n 3.3, an MCP Client Tool and an HTTP Request node talking to the same provider were forced to use two different OAuth2 credentials for one OAuth app, and providers that allow only one active token per app invalidate the other side's token on every new grant. By the end of this post you will know how to confirm this exact pattern, merge both nodes onto one shared credential, and verify the random failures are gone.

Quick definitions: **MCP** (Model Context Protocol) is the open standard n8n's AI Agent uses to call external tools, and the **MCP Client Tool** node is how an agent calls one of those tools. An **OAuth2 credential** in n8n stores the tokens n8n obtained from a provider's OAuth app — the registered app whose client ID and secret identify your integration to that provider.

## The symptom: each side passes alone, together they take turns failing

The pattern, reported by a team running MCP Client Tool nodes in client setups on the [n8n community forum](https://community.n8n.io/t/two-credentials-for-one-oauth-app-kept-breaking-auth-n8n-3-3-fixed-that/331259) (November 27, 2026), looks like this:

- The MCP Client Tool node authenticates with an **MCP OAuth2** credential. The HTTP Request node, calling the same provider's API directly, authenticates with a plain **OAuth2 API** credential. Same provider, same OAuth app, two n8n credentials.
- Both sides test fine on their own. Credential tests pass, single-node executions pass.
- In production, auth fails at random. Reconnecting the MCP tool drops the token the HTTP Request node was holding, so the workflow fails depending on which side refreshed or reconnected last.

That last detail is the fingerprint. If your failures correlate with reconnects or refreshes on the *other* node — and never reproduce when you test either node in isolation — you have this bug's setup, whatever exact 401 text your provider returns.

## The root cause: one OAuth app, two credentials, one active token

Two facts combine to break you. First, the credential types did not overlap: the MCP Client and MCP Client Tool nodes only accepted the MCP OAuth2 credential type, while the HTTP Request node used the generic OAuth2 API credential. There was no way to point both nodes at one stored credential, so one OAuth app necessarily had two token sets living in n8n.

Second, some providers allow only **one active token per OAuth app**. On those providers, a new token grant — a reconnect, or a refresh that mints a replacement — supersedes the previous token. With two credentials refreshing independently, each side keeps invalidating the other. Neither credential is misconfigured; the duplication itself is the fault.

n8n 3.3, released 2026-11-17, removes the duplication. Per the [official release notes](https://docs.n8n.io/changelog/release-notes.md), the MCP Client and MCP Client Tool nodes now accept the generic OAuth2 API credential alongside the existing MCP OAuth2 credential ([PR #37371](https://github.com/n8n-io/n8n/pull/37371)) — explicitly so you can reuse the same credential for both the HTTP Request node and an MCP server when a provider allows one active token per app. The team in the forum thread moved one client onto the shared credential and the random auth failures stopped.

## The fix: one credential for both nodes

### Step 1 - Confirm you have the two-credential setup

Open both nodes and read their credential fields. You have this problem if all three are true: the MCP Client or MCP Client Tool node uses an MCP OAuth2 credential, the HTTP Request node uses a generic OAuth2 API credential, and both credentials were created from the same provider OAuth app (same client ID). If the two nodes talk to different providers or different apps, stop here — your random failures have a different cause.

### Step 2 - Make sure you are on n8n 3.3 or later

The shared-credential option ships in n8n 3.3 (released 2026-11-17). On older versions the MCP nodes will not offer the generic OAuth2 API credential, so check your instance version first and update if you are below 3.3. Self-hosted users update through their normal deployment path; n8n Cloud workspaces show their version in the workspace settings.

### Step 3 - Point the MCP node at the HTTP Request node's credential

Open the MCP Client or MCP Client Tool node and change its credential from the MCP OAuth2 credential to the **same generic OAuth2 API credential the HTTP Request node already uses** — the existing credential, not a copy of it. A copy is still a second token set and changes nothing.

If no generic OAuth2 API credential exists for this provider yet, create one OAuth2 API credential from the provider's app details and select that single credential in both nodes. From this point there is exactly one stored token set for the app, so there is nothing left to invalidate.

### Step 4 - Reconnect the shared credential once

Reconnect the shared credential so it holds a fresh token under the new arrangement. Expect the old MCP OAuth2 credential's token to be superseded — that is the point. Once Step 5 passes, retire the old MCP OAuth2 credential: check that no other node still references it, then delete it so nobody re-selects it later and recreates the split.

### Step 5 - Verify both sides back to back, twice

Run the HTTP Request node, then an MCP tool call, then the HTTP Request node again — in that order, without reconnecting anything in between. Then run the full workflow twice. Success looks like this: both nodes pass in sequence, and the second full run passes with no auth error and no manual reconnect. On the old setup, that same sequence is exactly what produced the intermittent failure, because whichever side refreshed last won.

## The one exception: servers that require a Resource URL

There is a hard caveat in the release notes, and it decides whether you can switch at all. The generic OAuth2 API credential has **no Resource URL field** (the RFC 8707 resource indicator some MCP servers require). If your MCP server requires a Resource URL, keep the MCP OAuth2 credential for the MCP node — the shared-credential fix cannot express that requirement.

In that case your options are narrower: ask the provider whether a second OAuth app (with its own token allowance) is permitted for the MCP side, or accept the two-credential setup and schedule reconnects deliberately instead of discovering them through failures. Do not force the generic credential onto a server that rejects token requests without a resource indicator; you will trade random failures for permanent ones.

One related bonus in the same release: n8n 3.3 also fixes initial token acquisition for client-credentials OAuth2 credentials that had no token yet, which used to fail. If your shared credential uses the client-credentials grant and its first connection attempt failed on older versions, that failure is fixed by the same update.

## Prevent it next time

- **One credential per OAuth app.** Whenever a provider is reached from more than one node type, select the same stored credential everywhere the node types allow it. Duplicated credentials for one app are a latent auth bug, not a convenience.
- **Audit for duplicates after upgrades.** Search your Credentials list for pairs created from the same app — an MCP OAuth2 credential and an OAuth2 API credential with matching client IDs is the exact pair this article removes.
- **Name credentials by app, not by node.** A credential named after the provider app reads as shared infrastructure; one named after a single node invites a second copy when the next node type arrives.
- **Treat "tests fine alone" as a clue, not a clearance.** Intermittent auth that never reproduces in isolation usually means two token holders are interfering — look for the second holder before blaming the provider.

## Honest limits

This fix addresses one specific mechanism: single-active-token providers plus duplicated credentials. If your provider allows multiple concurrent tokens, sharing one credential is still cleaner, but your random failures likely come from somewhere else — token expiry handling is the next suspect, and our guide to [Microsoft OAuth2 credentials not refreshing on 403 TokenExpired](https://cortexflow.tech/blog/fix-n8n-microsoft-oauth2-403-token-refresh/) covers that failure shape. The evidence here is the official 3.3 release notes plus one team's production report; the mechanism is documented by n8n itself, but your provider's token policy is the variable only you can confirm.

## FAQ

### The generic OAuth2 credential does not appear in my MCP node. Why?

You are almost certainly below n8n 3.3. The MCP Client and MCP Client Tool nodes gained generic OAuth2 API credential support in 3.3 (released 2026-11-17, PR #37371). Update, then reopen the node.

### Do I have to delete the old MCP OAuth2 credential?

Not immediately, but retire it once verification passes and nothing references it. Leaving it selectable invites someone to reintroduce the two-credential split during a later edit.

### My MCP server needs a Resource URL. Can I still share one credential?

No. The generic OAuth2 API credential has no Resource URL (RFC 8707) field, so a server that requires one still needs the MCP OAuth2 credential. The release notes state this explicitly.

## Key Takeaways

1. **Random auth failures that never reproduce in isolation point at token interference** — two credentials for one OAuth app, on a provider that allows one active token.
2. **Before n8n 3.3 the duplication was forced**: MCP nodes took only MCP OAuth2 credentials, HTTP Request used generic OAuth2 API credentials.
3. **n8n 3.3 lets MCP Client and MCP Client Tool nodes use the generic OAuth2 API credential** — point both nodes at the one existing credential, reconnect once, and verify back to back.
4. **The exception is RFC 8707**: servers requiring a Resource URL still need the MCP OAuth2 credential, because the generic credential has no such field.

Next step: open your Credentials list and look for the duplicate pair — an MCP OAuth2 credential and an OAuth2 API credential sharing a client ID. If you find one, you have ten minutes of work and one less intermittent failure. If your MCP errors instead arrive with no HTTP status at all, read [how to recover the hidden status from n8n's MCP client errors](https://cortexflow.tech/blog/fix-n8n-mcp-client-error-hides-http-status/) next.
