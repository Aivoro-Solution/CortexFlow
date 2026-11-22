---
title: "Fix n8n Webhook CORS: Only the First Allowed Origin Works When the List Has Spaces"
description: "Your n8n webhook's Allowed Origins list ignores every origin after the first when a space follows the comma. The one-character fix."
date: 2026-11-22
category: automation
tags: ["n8n", "error-fix", "webhook", "cors", "allowed-origins"]
draft: false
featured: false
image: "/og/fix-n8n-webhook-cors-allowed-origins-space-after-comma.webp"
---

You list two origins in your n8n Webhook node's Allowed Origins (CORS) field — `https://a.com, https://b.com` — and requests from `https://a.com` work perfectly. Requests from `https://b.com` get blocked by the browser with a CORS error, even though you explicitly allowed that origin. The difference between a working list and a broken one is a single space character. By the end of this post you will know why n8n treats the second origin as a stranger, the one-character fix, and how to prove it works with a single `curl` command.

## The symptom: the second origin is blocked, the first works fine

The setup is ordinary. A workflow has a Webhook node with an Allowed Origins (CORS) list containing two origins, separated the way every human writes a list — comma, space:

```text
https://a.com, https://b.com
```

Activate the workflow and call the webhook from `https://a.com`. The response comes back with `Access-Control-Allow-Origin: https://a.com` and the browser is happy. Call the exact same webhook from `https://b.com` and the response carries a different header:

```text
Access-Control-Allow-Origin: https://a.com
```

The browser sees that the header does not match the page's origin and refuses to hand the response to your JavaScript, with the familiar console error:

```text
Access to fetch at 'https://<your-n8n-host>/webhook/<path>' from origin
'https://b.com' has been blocked by CORS policy: The
'Access-Control-Allow-Origin' header has a value 'https://a.com' that is
not equal to the supplied origin.
```

Nothing in n8n logs an error. The webhook execution itself succeeds — the response is sent, the browser just will not let your page read it. And the maddening part: remove the space after the comma and `https://b.com` starts working immediately, with no other change. The whitespace alone decides whether an allowed origin works.

This was reported in [GitHub issue #44776](https://github.com/n8n-io/n8n/issues/44776) (opened 2026-11-22, Linear GHC-9835, still open as of 2026-11-22), against n8n 2.49.0 and current master. An earlier report of the same symptom, #18528, was closed as fixed in n8n 1.109.0 — but the reporter verified the behavior still reproduces on current master, and the origin-parsing code is unchanged.

## The root cause: the list is split on commas and never trimmed

CORS (Cross-Origin Resource Sharing) is the browser's rule for when a web page on one origin may read a response from another origin. The server declares which origins are allowed by sending back an `Access-Control-Allow-Origin` header; if that header does not match the page's origin, the browser blocks the response.

n8n decides which value to send in the production webhook handler, `packages/cli/src/webhooks/webhook-request-handler.ts`. I verified the code on current master. This is the relevant block:

```typescript
const { allowedOrigins } = options ?? {};

if (allowedOrigins && allowedOrigins !== '*' && allowedOrigins !== req.headers.origin) {
	const originsList = allowedOrigins.split(',');
	const defaultOrigin = originsList[0];

	if (originsList.length === 1) {
		res.header('Access-Control-Allow-Origin', defaultOrigin);
	}

	if (originsList.includes(req.headers.origin as string)) {
		res.header('Access-Control-Allow-Origin', req.headers.origin);
	} else {
		res.header('Access-Control-Allow-Origin', defaultOrigin);
	}
} else {
	res.header('Access-Control-Allow-Origin', req.headers.origin);
}
```

Walk through it with `https://a.com, https://b.com` and a request whose `Origin` header is `https://b.com`:

1. `allowedOrigins.split(',')` produces `["https://a.com", " https://b.com"]`. Note the leading space on the second entry — `split` does not trim.
2. `originsList.includes("https://b.com")` compares the request origin against `" https://b.com"` (with the space). They are not equal, so the match fails.
3. The `else` branch falls back to `defaultOrigin`, which is `originsList[0]` — `https://a.com`. The response tells the browser the only allowed origin is `https://a.com`, and the browser blocks it.

The first entry works because it never has a leading space. Every entry after the first is silently dead as long as you write the list the natural way, with a space after each comma. A trailing space after the last entry breaks that entry the same way, for the same reason.

Team member goutham-valugula confirmed this on 2026-11-22 in the issue thread: the whitespace issue is in the production webhook handler, which splits `allowedOrigins` on `,` and uses `originsList.includes(req.headers.origin)` without trimming. Trimming each split entry before both matching and selecting the fallback would fix both cases. A regression test for `https://a.com, https://b.com` in the webhook request-handler tests was suggested to pin it down.

## The fix: remove the spaces from the list

There is no setting to change and no restart required. Edit the Allowed Origins (CORS) field in the Webhook node and delete every space in the list.

### Step 1 - Open the Webhook node and find the CORS field

Open the workflow, click the Webhook node, and open its options. The field is **Allowed Origins (CORS)**. It holds the comma-separated list of origins that may call this webhook from a browser.

### Step 2 - Rewrite the list with no spaces

Change the list from this:

```text
https://a.com, https://b.com
```

to this — the same origins, no spaces anywhere:

```text
https://a.com,https://b.com
```

That is the whole fix. n8n compares each entry exactly against the request's `Origin` header, so the stored text must match the header byte for byte. No space after the comma, no space before it, no trailing space at the end of the field. If you have three or more origins, the same rule applies to every separator: `https://a.com,https://b.com,https://c.com`.

> **Note:** the check is also case-sensitive and scheme-sensitive. `https://B.com` and `http://b.com` are different origins from `https://b.com` and will not match. Copy the origin exactly as the browser sends it — including the `https://` prefix and any port, for example `http://localhost:3000`.

### Step 3 - Save and reactivate the workflow

Save the workflow. If it is already active, the change takes effect when the workflow is saved — but if the webhook URL is a production URL, deactivate and reactivate once to be certain the running version carries the new value.

### Step 4 - Verify with curl

You do not need a browser to prove the fix. Send a request with the `Origin` header of the origin that was failing, and read the `Access-Control-Allow-Origin` header in the response:

```bash
curl -s -D - -H "Origin: https://b.com" \
  https://<your-n8n-host>/webhook/<your-webhook-path> -o /dev/null
```

Replace `<your-n8n-host>` with your n8n host and `<your-webhook-path>` with the webhook's path. Look for this line in the response headers:

```text
Access-Control-Allow-Origin: https://b.com
```

If you see your origin echoed back, the fix works — the browser will now accept the response. If you still see `Access-Control-Allow-Origin: https://a.com`, a space is still hiding somewhere in the list: re-open the field and check every separator and the end of the field.

Repeat the same `curl` for each origin in the list. Before the fix, only the first origin echoes; after the fix, every listed origin echoes.

You can also verify in the browser: open DevTools on the page that calls the webhook, go to the Network tab, run the request, and check the response headers for the same `Access-Control-Allow-Origin` line.

## What about `*`?

Setting Allowed Origins to `*` also sidesteps this bug — when the value is `*`, n8n echoes the request's origin back. That is fine while you are testing, but it is not a fix: it allows any website on the internet to call your webhook from a browser. Only use `*` to confirm the webhook itself answers correctly, then put the explicit list back — without spaces.

## Prevent it next time

- **Adopt a no-spaces convention for this field.** Any comma-separated list n8n splits without trimming is vulnerable to the same class of bug. When you paste origins from documentation or a teammate's message, strip the spaces first.
- **Test every origin, not just the first.** A list with one working origin hides this bug completely. After adding an origin, run the `curl` check from Step 4 for that origin before you ship the integration.
- **Watch for the upstream fix.** The proper fix is to trim each entry after splitting, in `webhook-request-handler.ts`. As of 2026-11-22 no fix has been merged — the issue is team-confirmed (Linear GHC-9835) with a regression test suggested, but no pull request yet. When a release containing the trim lands, the space-after-comma spelling will start working; until then, the no-spaces list is the workaround.
- **Do not confuse this with the dynamic-paths bug.** A separate issue filed the same day, [#44775](https://github.com/n8n-io/n8n/issues/44775), reports that Allowed Origins is ignored entirely for webhooks with dynamic paths. That is a different bug with a different cause — if your webhook path contains a dynamic segment (for example `:id`) and no origin is ever matched, you are hitting #44775, not this one.

## FAQ

### Does this affect the test (editor) webhook URL too?

The parsing code lives in the production webhook request handler, so production URLs are the affected path. If you see the same symptom on a test URL, check the list for spaces first — the same field feeds both — and verify with `curl` against the test URL.

### Why did the first origin always work?

`split(',')` only adds a leading space to entries after a comma. The first entry starts at the beginning of the string, so it never carries a space and always matches exactly. That is why the bug looks like "only the second origin is blocked" rather than "CORS is broken".

### I removed the spaces and it still fails — what else could it be?

Check three things. First, a trailing space at the very end of the field — it breaks the last entry. Second, the origin must match exactly: scheme (`http` vs `https`), host case, and port all matter. Third, if your webhook path has a dynamic segment, see the #44775 note above — that is a separate bug.

### Was this not already fixed in 1.109.0?

Issue #18528 reported the same symptom and was closed as fixed in 1.109.0, but the reporter of #44776 verified the origin-parsing code is unchanged on current master and the behavior still reproduces. Treat 1.109.0's fix as not having landed for this code path, and use the no-spaces list regardless of version.

## Key Takeaways

1. **A space after the comma silently kills every origin after the first** — n8n splits the Allowed Origins list on `,` without trimming, so ` https://b.com` never equals the request's `Origin: https://b.com`.
2. **The fix is one character class: delete all spaces** — write the list as `https://a.com,https://b.com`, with no spaces after commas, before them, or at the end.
3. **Verify with curl, not by re-testing in the browser** — `curl -H "Origin: https://b.com"` should return `Access-Control-Allow-Origin: https://b.com`; check every origin in the list, not just the first.
4. **No upstream fix is merged yet** — the bug is team-confirmed (GH #44776, Linear GHC-9835) as of 2026-11-22, so the no-spaces list is the workaround until a release containing the trim lands.

Next: if your webhook path contains a dynamic segment and no origin matches at all, read [issue #44775](https://github.com/n8n-io/n8n/issues/44775) — that is a separate Allowed Origins bug with a different cause.
