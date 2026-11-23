---
title: "Fix n8n Webhook CORS: Allowed Origins Is Ignored on Dynamic Paths"
description: "Your n8n webhook's Allowed Origins list is silently ignored when the path has a dynamic segment like :id — any site can read the response. The static-path fix."
date: 2026-11-23
category: automation
tags: ["n8n", "error-fix", "webhook", "cors", "allowed-origins"]
draft: false
featured: false
image: "/og/fix-n8n-webhook-cors-ignored-dynamic-paths.webp"
---

You set Allowed Origins (CORS) on your n8n Webhook node to `https://a.com`, and you expect only your app to read the webhook's responses from a browser. But if the webhook's path contains a dynamic segment — `user/:id`, for example — n8n ignores the list entirely. A page on any other origin can call the webhook and read the response, because the server echoes the caller's own origin back in the `Access-Control-Allow-Origin` header. By the end of this post you will know why the list is ignored, how to prove it with one `curl` command, and the two workarounds that actually enforce your origin list.

## The symptom: the configured origin list has no effect at all

The setup is ordinary. A workflow has a Webhook node with response mode "When Last Node Finishes", a dynamic path, and a locked-down origin list:

```text
Path: user/:id
Allowed Origins (CORS): https://a.com
```

Activate the workflow and call the production URL from JavaScript running on `https://b.com` — an origin that is not in the list:

```text
GET https://<your-n8n-host>/webhook/<webhookId>/user/123
Origin: https://b.com
```

The response comes back with this header:

```text
Access-Control-Allow-Origin: https://b.com
```

The browser sees that the header matches the page's origin and hands the response to the JavaScript. The webhook's response — whatever data your workflow returns — is now readable by a site you never allowed. The configured `https://a.com` was never applied.

For comparison, change the path to a static value with no `:param` segment, keep the same Allowed Origins list, and repeat the call from `https://b.com`. Now the response carries:

```text
Access-Control-Allow-Origin: https://a.com
```

The browser sees that the header does not match `https://b.com` and blocks the read, exactly as the setting promises. Static paths enforce the list correctly. Dynamic paths do not enforce it at all.

This was reported in [GitHub issue #44775](https://github.com/n8n-io/n8n/issues/44775) (opened 2026-11-22), against n8n 2.49.0 and current master (75fe21cb / bf31087b), still open as of 2026-11-23. No team reply, pull request, or fixed version has appeared yet, so the workarounds below are the fix for now.

## The root cause: the origin lookup compares a template path with a real path

CORS (Cross-Origin Resource Sharing) is the browser's rule for when a web page on one origin may read a response from another origin. The server declares which origins are allowed by sending back an `Access-Control-Allow-Origin` header; if that header does not match the page's origin, the browser blocks the response.

To decide which value to send, n8n has to find the Webhook node that owns the incoming request, so it can read that node's Allowed Origins setting. The lookup compares the node's configured path with the concrete path of the request — and for a dynamic webhook those two can never be equal:

- The node registers under its template path: `<webhookId>/user/:id`
- The request arrives at the concrete path: `<webhookId>/user/123`

`:id` is a placeholder, `123` is a value. The string comparison fails, no node is matched, and the CORS handling falls back to reflecting whatever `Origin` the caller sent. The fallback is what turns a restriction into an open door: instead of answering with the first entry of your configured list (which the browser would reject for an unlisted origin), the server answers with the caller's own origin, which the browser accepts.

The same lookup problem exists in the test-webhook path — the registration search cannot resolve dynamic paths there at all — so do not expect the editor's test URL to behave differently.

Note the difference from the bug in yesterday's post: [issue #44776](https://github.com/n8n-io/n8n/issues/44776) was about spaces after commas in the Allowed Origins list, which silently disabled every origin after the first. That bug breaks a list that was matched. This bug never matches the node in the first place, so the entire list — including the first origin — is ignored. If your webhook path has no `:param` segment, you are hitting #44776, not this one.

## The fix: give the webhook a static path

There is no setting that repairs this, and no restart helps — the lookup itself is the problem. The reliable fix is to stop using a dynamic segment in the webhook path and pass the value another way.

### Step 1 - Change the Webhook node path to a static value

Open the workflow, click the Webhook node, and change the path from the dynamic template to a static one. If the id was the only dynamic part, the path becomes just:

```text
Path: user
```

The webhook URL is now `https://<your-n8n-host>/webhook/<webhookId>/user`. Because the configured path and the request path are now identical strings, the lookup finds the node and the Allowed Origins list is enforced — the reporter verified this exact comparison in the issue.

### Step 2 - Pass the id as a query parameter (or in the body)

Callers that used to hit `/user/123` now pass the value as a query parameter:

```text
GET https://<your-n8n-host>/webhook/<webhookId>/user?id=123
```

For a POST webhook, the same value can go in the JSON body instead:

```json
{
  "id": "123"
}
```

### Step 3 - Read the id from the webhook output in the workflow

Downstream nodes read the value from the Webhook node's output instead of from the path. For a GET request, the query parameters arrive under `$json.query`:

```text
{{ $json.query.id }}
```

For a POST with a JSON body, the value is under `$json.body`:

```text
{{ $json.body.id }}
```

That is the only change the rest of the workflow needs. Every node that previously used the `:id` path parameter now reads the same value from the query or the body, and the workflow behaves identically — except the CORS list is now enforced.

> **Note:** if the dynamic segment carried a secret or a token (for example `/user/:token`), do not move it into a query string — URLs with query parameters are logged by proxies and stored in browser history. Put the value in the POST body, or better, switch the webhook to Header Auth (see Step 5) and send the credential as a header.

### Step 4 - Verify with curl

You do not need a browser to prove the fix. Send a request with the `Origin` header of an origin that is not in your list, and read the `Access-Control-Allow-Origin` header in the response:

```bash
curl -s -D - -H "Origin: https://b.com" \
  "https://<your-n8n-host>/webhook/<webhookId>/user?id=123" -o /dev/null
```

Replace `<your-n8n-host>` with your n8n host and `<webhookId>` with the webhook's id. Look for this line in the response headers:

```text
Access-Control-Allow-Origin: https://a.com
```

That is the first entry of your configured list, not the caller's origin — the browser will block `https://b.com` from reading the response, which is the correct behavior. If you still see `Access-Control-Allow-Origin: https://b.com`, the path still contains a dynamic segment: re-open the Webhook node and check the path field.

Repeat the same `curl` with the origin that *is* allowed:

```bash
curl -s -D - -H "Origin: https://a.com" \
  "https://<your-n8n-host>/webhook/<webhookId>/user?id=123" -o /dev/null
```

This time you should see your origin echoed back:

```text
Access-Control-Allow-Origin: https://a.com
```

You can also verify in the browser: open DevTools on the page that calls the webhook, go to the Network tab, run the request, and check the response headers for the same `Access-Control-Allow-Origin` line.

### Step 5 - If the path must stay dynamic, enforce CORS at the reverse proxy

Sometimes the dynamic path cannot change — a third-party service calls your webhook at a fixed URL pattern, or the path is part of a public API contract. In that case, do not rely on n8n's Allowed Origins setting for that webhook at all. Enforce the origin list in the reverse proxy in front of n8n, which sees the request before n8n's broken lookup runs. For nginx:

```nginx
location /webhook/ {
    proxy_pass http://localhost:5678;
    add_header 'Access-Control-Allow-Origin' 'https://a.com' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type' always;
}
```

Reload nginx after the change (`nginx -s reload`). The proxy now stamps the allowed origin onto every webhook response, and a browser on any other origin is blocked regardless of what n8n's lookup does. Note that this sets the header for all webhooks behind that location — if different webhooks need different origin lists, split the location blocks per path.

A second layer worth adding for a dynamic webhook that returns sensitive data: put Header Auth on the Webhook node, so a call without the credential is rejected before the workflow runs. That does not fix the CORS reflection, but it means an arbitrary third-party page cannot call the webhook at all without the key — it can only read responses it cannot obtain.

## What about `*`?

Setting Allowed Origins to `*` does not fix this either — it tells n8n to allow every origin, which is what the broken fallback is already doing by accident. Only use `*` while testing that the webhook itself answers, then put the explicit list back and apply the static-path fix above.

## Prevent it next time

- **Avoid dynamic segments in webhook paths that browsers call.** If a browser fetches the webhook, the path should be static and parameters should travel in the query string or the body. Reserve `:param` paths for server-to-server calls, where CORS never applies.
- **Test CORS from an origin that is *not* allowed, not just from the one that is.** A call from your own app passing tells you nothing — the broken fallback reflects your origin too. The `curl` check in Step 4, with a foreign `Origin` header, is the test that catches this bug.
- **Treat a reflected origin as a red flag.** If `Access-Control-Allow-Origin` ever echoes an origin you did not configure, the allowlist is not being applied — check the path first, then the list.
- **Watch for the upstream fix.** The proper fix is for the lookup to match dynamic paths against their templates instead of comparing raw strings. As of 2026-11-23 no fix has been merged — the issue is still open with no team reply or pull request — so the static path (or proxy enforcement) is the workaround until a release containing the fix lands.
- **Audit your other dynamic webhooks.** Any webhook with a `:param` in its path and an Allowed Origins list has the same hole. The `curl` check takes seconds per webhook.

## FAQ

### Does this affect the test (editor) webhook URL too?

Yes. The issue reports that the same lookup problem exists in the test-webhook path, where the registration search cannot resolve dynamic paths at all. Test with the production URL after activating the workflow — the test URL is not a reliable place to check CORS behavior for dynamic paths.

### My webhook is only called server-to-server. Does this matter?

No. CORS is a browser rule — servers do not enforce it, and `curl` or another backend ignores the `Access-Control-Allow-Origin` header entirely. The bug only matters when a browser page calls the webhook directly. If no browser ever calls it, the dynamic path is fine as it is.

### I switched to a static path and the allowed origin still gets blocked — what else could it be?

Check the list itself: if it contains spaces after the commas, every origin after the first is silently dead — that is the separate bug in [issue #44776](https://github.com/n8n-io/n8n/issues/44776), fixed by writing the list with no spaces (`https://a.com,https://b.com`). Also check that the origin matches exactly: scheme (`http` vs `https`), host case, and port all matter.

### Is this a security vulnerability I should report?

It is a real access-control bypass for browser-called webhooks: any site can read responses your allowlist was meant to restrict. If your dynamic webhook returns sensitive data, treat it as an exposure — apply the static-path fix or proxy enforcement now, rotate anything the responses may have leaked, and follow [issue #44775](https://github.com/n8n-io/n8n/issues/44775) for the upstream fix.

## Key Takeaways

1. **Dynamic webhook paths silently disable the entire Allowed Origins list** — the lookup compares the template path (`user/:id`) with the real path (`user/123`), never matches, and the CORS handling falls back to reflecting the caller's own origin.
2. **The fix is a static path plus a query or body parameter** — change the path to `user`, pass the id as `?id=123`, read it with `{{ $json.query.id }}`; the reporter's own comparison proves static paths enforce the list.
3. **Verify from an origin that is not allowed** — `curl -H "Origin: https://b.com"` should return `Access-Control-Allow-Origin: https://a.com` (your list), not `https://b.com` (the caller). A call from your own origin passing proves nothing.
4. **No upstream fix is merged yet** — the issue (GH #44775) is still open as of 2026-11-23 with no team reply or pull request, so the static path — or CORS enforcement at your reverse proxy — is the workaround until a release fixes the lookup.

Next: if your webhook path is static but only the first listed origin works, read the companion post on [issue #44776](https://cortexflow.tech/blog/fix-n8n-webhook-cors-allowed-origins-space-after-comma/) — spaces after the commas in the list break every origin after the first.
