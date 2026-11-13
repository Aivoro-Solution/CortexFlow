---
title: "Fix n8n Form Trigger Editor Stuck on \"Waiting for you to submit the form\" (GH #43759)"
description: "Your form submits and the workflow runs, but the editor stays stuck on 'Waiting for you to submit the form'. The push event never arrives — here's the fix."
date: 2026-11-13
category: automation
tags: ["n8n", "form-trigger", "websocket", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-form-trigger-editor-stuck-waiting-submit.webp"
---

You build a workflow that starts with a Form Trigger. You click Execute Workflow, open the form's Test URL, fill it in, and submit. The workflow runs. The execution list shows a green success. And the editor just sits there, saying "Waiting for you to submit the form" — as if nothing happened. You refresh the page, the waiting state clears, and you can test again. But every single test ends the same way: success everywhere except the editor.

This is a real bug, reported in [GitHub issue #43759](https://github.com/n8n-io/n8n/issues/43759) on November 13, 2026 (team-assigned, Linear ticket GHC-9756, still open as of November 13, 2026). The reporter reproduced it on n8n 2.46.7 and 2.47.5, self-hosted in Docker on Windows 11, and confirmed the crucial detail in the thread: the saved execution's mode is `manual`, its workflow ID matches the editor's workflow, and yet no `testWebhookReceived` message ever arrives in the editor's push connection. By the end of this article you will know exactly which wire the signal dies on, how to prove it in thirty seconds with DevTools, and the four configuration fixes that get the editor unstuck — no upstream patch required.

Quick definitions before we start: the **Form Trigger** is n8n's node that shows a web form and starts a workflow when someone submits it. The **push connection** is the live channel between your browser and the n8n server — a WebSocket at `/rest/push` — that the editor uses for real-time updates like "the test execution finished". **`testWebhookReceived`** is the specific push message the editor waits for after a test form submission; when it arrives, the editor clears the waiting state and shows the completed nodes. **N8N_PUSH_BACKEND** is the environment variable that picks the push transport: `websocket` (the default) or `sse` (Server-Sent Events, plain HTTP streaming).

## The symptom: everything succeeds except the editor

The failure has a very specific shape, and that shape is the diagnostic clue:

1. Create a workflow with a Form Trigger connected to an Edit Fields node.
2. Click Execute Workflow.
3. Open the Form Trigger's Test URL and submit the form.
4. The form submission succeeds. The workflow executes successfully. The execution appears in the Executions list with mode `manual`.
5. The editor never updates. It stays on "Waiting for you to submit the form".
6. Refreshing the editor page clears the waiting state.

Nothing is lost — the workflow ran, the data is in the execution. What is broken is the *notification*: the editor never hears that the test submission happened. That is the same failure class as the [Postgres Trigger that silently stops listening](/blog/fix-n8n-postgres-trigger-stops-listening/) and the [workflow that silently stops triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/): the system works, the signal doesn't, and the UI leaves you guessing.

## The root cause: the editor waits for a push message that never arrives

When you click Execute Workflow on a Form Trigger, the editor registers a test webhook and then waits. The waiting flag is cleared by exactly one thing: a `testWebhookReceived` message arriving on the push connection, with a `workflowId` matching the workflow open in the editor. That logic lives in the editor's push handler (`packages/frontend/editor-ui/src/app/composables/usePushConnection/handlers/testWebhookReceived.ts`), and the reporter confirmed the matching side is fine — the execution's workflow ID is the one open in the editor, and its mode is `manual`, exactly as a test webhook should be.

So the message is sent by the backend and never delivered to the browser. There are only a few ways that happens, and the issue thread plus n8n's own push-connection design narrow it to three:

**1. Host/origin mismatch between the editor tab and the form URL.** The browser opens the push connection from the editor tab's origin. n8n compares the request's `Origin` header against the host it was sent to (checking `Forwarded`, then `X-Forwarded-Host`, then `Host`). If your editor tab is on `localhost:5678` while `WEBHOOK_URL` — and therefore the Form Test URL — resolves to `127.0.0.1:5678` (or vice versa), the session and the push channel don't line up, and the `testWebhookReceived` event never reaches your tab. On Docker on Windows this is the classic trap: `localhost` and `127.0.0.1` are the same machine but different origins to a browser.

**2. A reverse proxy that doesn't forward WebSocket upgrades.** By default the push connection is a WebSocket (`N8N_PUSH_BACKEND` defaults to `websocket`). If nginx, Caddy, Traefik, or Nginx Proxy Manager sits between the browser and n8n and doesn't forward the `Upgrade` and `Connection` headers, the `/rest/push` handshake never becomes a WebSocket. Depending on the proxy, you get a `401 Unauthorized` (the request reaches n8n as a plain GET), an `HTTP 500`, or a connection that opens and then closes with code 1008 and `Invalid origin!`. A proxy that buffers responses can also stall the stream even after the upgrade succeeds.

**3. Push backend mismatch.** If the proxy genuinely cannot do WebSockets, the websocket backend will never deliver — but n8n has a second transport, Server-Sent Events (`N8N_PUSH_BACKEND=sse`), which is ordinary HTTP streaming and needs no upgrade handshake at all.

Note what this bug is *not*: it is not a broken Form Trigger, not a broken workflow, and not a database problem. The execution proves the trigger works. If you chase the form node or reinstall the workflow, you will waste an afternoon. The fault is in the delivery channel between server and editor, and that is where the fixes live.

## Step 1 - Prove it in 30 seconds with DevTools

Before changing anything, confirm the diagnosis. This takes one test submission.

1. Open your n8n editor tab. Press F12 and go to the **Network** tab. Filter by **WS** (WebSockets).
2. Click Execute Workflow on the Form Trigger, then submit the form from its Test URL.
3. Click the `/rest/push` connection in the Network list, then open its **Messages** tab.
4. Look for a frame named `testWebhookReceived`.

**You should see:** a `testWebhookReceived` frame with `workflowId` and `executionId` fields, arriving within a second of submitting the form.

**If you see it but the editor is still stuck:** the message arrived but the `workflowId` doesn't match the workflow open in the editor — check you are testing the same workflow you have open, and that you haven't duplicated the workflow (a copy has a different ID).

**If no frame ever arrives:** the push connection is broken, and the rest of this article is your fix. Also check the Executions list: the saved execution's mode should be `manual` for a test submission. If it says `webhook`, you opened the production form URL, not the Test URL — use the Test URL while testing.

> **Note:** Keep DevTools open while you apply the fixes below. Re-running the test and watching the `/rest/push` Messages tab is the verification for every step — you will see the `testWebhookReceived` frame appear the moment the fix lands.

## Step 2 - Use one identical host everywhere

This is the fix for the Docker-on-Windows case in the original report, and it costs nothing to check first.

Open your editor and look at the address bar. Then open your `docker-compose.yml` (or however you pass environment variables) and check these four values:

```yaml
environment:
  - N8N_HOST=localhost
  - N8N_PORT=5678
  - N8N_PROTOCOL=http
  - N8N_WEBHOOK_URL=http://localhost:5678/
  - N8N_EDITOR_BASE_URL=http://localhost:5678/
```

Here's what each key does:

- `N8N_HOST` — the hostname n8n binds and advertises. This is what the editor tab's origin should be.
- `N8N_WEBHOOK_URL` — the public base URL n8n uses to build webhook and form URLs, including the Form Trigger's Test URL. (On n8n 2.30.0 and later this is the canonical name; the older `WEBHOOK_URL` still works as a deprecated alias.)
- `N8N_EDITOR_BASE_URL` — the URL the editor itself lives at, when it differs from the webhook URL.
- `N8N_PORT` / `N8N_PROTOCOL` — the port and scheme; they must match the URL you actually open.

**The rule is simple: the host in your browser's address bar, `N8N_HOST`, `N8N_WEBHOOK_URL`, and `N8N_EDITOR_BASE_URL` must all be the same string.** `localhost` and `127.0.0.1` are not the same string, even though they point at the same machine. Pick one — `localhost` is the usual choice on a local Docker setup — and use it in all four places. Then recreate the container:

```bash
docker compose down
docker compose up -d
```

> **Warning:** changing `N8N_WEBHOOK_URL` changes every webhook and form URL n8n generates. If you have production workflows with webhooks registered at the old URL, re-register them (deactivate and reactivate the workflow) after the change, or external callers will keep hitting the old address.

Re-run the test from Step 1. If the `testWebhookReceived` frame now arrives, you are done — skip to Step 5.

## Step 3 - Pin the push backend explicitly

If the host is already consistent and the frame still doesn't arrive, make the push transport explicit instead of relying on the default.

Add this to your `docker-compose.yml` environment block:

```yaml
environment:
  - N8N_PUSH_BACKEND=websocket
```

`N8N_PUSH_BACKEND` accepts two values:

| Value | Transport | When to use it |
|---|---|---|
| `websocket` | WebSocket at `/rest/push` (the default) | Direct access, or any proxy that forwards WebSocket upgrades |
| `sse` | Server-Sent Events over plain HTTP streaming | Your proxy cannot do WebSockets at all (some managed proxies, OpenLiteSpeed) |

If your proxy genuinely cannot upgrade connections, `websocket` will never work no matter how many times you restart — switch to `sse` instead:

```yaml
environment:
  - N8N_PUSH_BACKEND=sse
```

Recreate the container (`docker compose down && docker compose up -d`), then re-run the Step 1 test. In DevTools, the `/rest/push` connection will now show as a regular streaming request instead of a WebSocket, and the `testWebhookReceived` event should arrive as an SSE message.

## Step 4 - Fix the reverse proxy (nginx / NPM / Traefik / Apache)

If you sit behind a reverse proxy, the proxy is the most likely place the push connection dies. The proxy must do three things for `/rest/push`: pass the WebSocket upgrade, preserve the original `Host`, and not buffer the stream.

**For nginx**, add a location block for the push path:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl;
    server_name n8n.example.com;

    location /rest/push {
        proxy_pass http://127.0.0.1:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }

    location / {
        proxy_pass http://127.0.0.1:5678;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Here's what each key does:

- `proxy_set_header Upgrade` + `Connection` — forwards the WebSocket upgrade handshake. Without these, n8n sees a plain GET on `/rest/push` and the connection never becomes a WebSocket.
- `proxy_set_header Host $host` — preserves the original host so n8n's origin check passes. A connection that opens and closes with code 1008 and `Invalid origin!` means this header is missing or wrong.
- `proxy_buffering off` — stops nginx from holding streamed push messages back. Without it, events can stall indefinitely.
- `proxy_read_timeout 3600s` — stops nginx from closing an idle push connection after its default 60 seconds.

Then tell n8n to trust the proxy's forwarded headers, and which origins are allowed:

```yaml
environment:
  - N8N_HOST=n8n.example.com
  - N8N_PROTOCOL=https
  - N8N_WEBHOOK_URL=https://n8n.example.com/
  - N8N_EDITOR_BASE_URL=https://n8n.example.com/
  - N8N_PROXY_HOPS=1
  - N8N_ALLOWED_ORIGINS=https://n8n.example.com
```

`N8N_PROXY_HOPS` is the number of proxies in front of n8n — set it to `1` for one proxy, `2` for two. Without it, n8n ignores the `X-Forwarded-*` headers and the origin check compares against the wrong host. `N8N_ALLOWED_ORIGINS` is the explicit allow-list for push-connection origins; set it to the exact URL you open in the browser.

**For Nginx Proxy Manager**, open the proxy host, go to the Details tab, and turn on **Websockets Support**. NPM already sends the original `Host` and the `X-Forwarded-*` headers, so that toggle plus `N8N_PROXY_HOPS=1` is the whole fix.

**For Apache**, proxy the push path over WebSocket explicitly:

```apache
RewriteCond %{HTTP:Upgrade} =websocket [NC]
RewriteRule /rest/push/(.*) ws://127.0.0.1:5678/rest/push/$1 [P,L]
ProxyPass /rest/push ws://127.0.0.1:5678/rest/push
ProxyPassReverse /rest/push ws://127.0.0.1:5678/rest/push
```

**For Traefik**, WebSocket support works out of the box — no extra labels are needed for `/rest/push`. If it still fails behind Traefik, the problem is almost certainly the host/origin mismatch from Step 2, not the proxy.

After any proxy change, reload the proxy and recreate the n8n container, then re-run the Step 1 test. Check the n8n container logs too:

```bash
docker compose logs -f n8n
```

If you see `Invalid origin!` or `Invalid WebSocket frame` lines, the proxy is still mangling the upgrade — re-check the `Upgrade`, `Connection`, and `Host` headers first.

## Step 5 - Verify the fix end to end

Run the full test once more, with DevTools open:

1. Click Execute Workflow on the Form Trigger.
2. Submit the form from its Test URL.
3. In DevTools → Network → WS → `/rest/push` → Messages, confirm a `testWebhookReceived` frame arrives.
4. Confirm the editor clears "Waiting for you to submit the form" on its own and shows the completed nodes with their outputs — no refresh needed.

Then confirm the production path still works: deactivate and reactivate the workflow (this re-registers the production webhook at the corrected URL), submit the form from its **production** URL, and confirm an execution with mode `webhook` appears. A test submission should always save as `manual`; a production submission should always save as `webhook`. If the modes are swapped, you are testing the wrong URL.

## Prevent it next time

- **One host, everywhere, from day one.** Decide the hostname before the first `docker compose up` and put the same value in the browser, `N8N_HOST`, `N8N_WEBHOOK_URL`, and `N8N_EDITOR_BASE_URL`. Never mix `localhost` and `127.0.0.1`.
- **Treat the push connection as infrastructure.** The editor's "Connection lost" badge and a stuck test webhook are the same failure: `/rest/push` is down. Any proxy change — new host, new TLS setup, new proxy — should be followed by a 30-second Form Trigger test with DevTools open.
- **Keep `N8N_PUSH_BACKEND` explicit in your compose file.** The default is `websocket` today, but an explicit line documents the choice and makes the `sse` fallback a one-line change when a proxy can't upgrade.
- **Watch the upstream issue.** This bug is still open as of November 13, 2026 (GH #43759, Linear GHC-9756). The fixes above are configuration workarounds for a delivery failure, not a code patch — if a future release fixes the editor-side handling, the same compose file keeps working, and you can drop the workarounds only if the release notes say so.

## Limits and what I didn't test

The reporter's environment was Docker on Windows 11 with SQLite and n8n 2.46.7/2.47.5, and the thread's own checks (a local non-Docker install and n8n Cloud) did *not* reproduce the bug — which is consistent with a host/proxy delivery failure rather than a universal code defect. I did not test the Cloudflare Tunnel case, where the tunnel itself terminates WebSockets; if you run n8n behind `cloudflared`, the same diagnostic applies (watch `/rest/push` in DevTools) but the proxy fix lives in the tunnel configuration, not nginx. And if the `testWebhookReceived` frame arrives and the editor is *still* stuck, the fault is past the transport layer — file that as a separate report against the editor handler, with the frame's `workflowId` and `executionId` attached.

## Key Takeaways

1. **The workflow is fine; the notification is broken.** A stuck "Waiting for you to submit the form" with a successful execution means the `testWebhookReceived` push event never reached the editor — diagnose the push connection, not the form node.
2. **Prove it in DevTools first.** Network → WS → `/rest/push` → Messages: no `testWebhookReceived` frame means a delivery failure. That one observation separates a config problem from an editor bug.
3. **One host everywhere.** `localhost` and `127.0.0.1` are different origins. Match the browser URL, `N8N_HOST`, `N8N_WEBHOOK_URL`, and `N8N_EDITOR_BASE_URL` exactly.
4. **Proxies must forward the WebSocket upgrade.** `Upgrade` + `Connection` headers, original `Host`, `proxy_buffering off`, and `N8N_PROXY_HOPS=1` — or switch to `N8N_PUSH_BACKEND=sse` if the proxy can't do WebSockets at all.

Next: if you run n8n behind a proxy, run the same DevTools check on a Webhook Trigger test — the same push connection drives its "Waiting for trigger event" state, and the same three fixes apply. The [workflow that silently stopped triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/) covers what to do when the trigger itself, not just its notification, goes quiet.

## FAQ

### Is this bug the same as "Connection lost" in the editor?

They share a cause — a broken `/rest/push` push connection — but they look different. "Connection lost" is the editor telling you the push channel is down. The stuck Form Trigger is the quiet version: the channel looks alive but the `testWebhookReceived` event never arrives, usually because of a host/origin mismatch rather than a fully dead connection. Fix the same three things (host, push backend, proxy headers) for both.

### Does refreshing the page fix it permanently?

No. Refreshing clears the waiting state for that one test because the editor re-reads the workflow state from the server. The next test submission will stick again until the push delivery is fixed. Treat refresh as a workaround for one test, not a fix.

### Should I just set N8N_PUSH_BACKEND=sse and forget about it?

Only if your proxy cannot do WebSockets. SSE is a fully supported transport, but WebSocket is the default and the better-tested path — and if the real problem is a host mismatch, switching to SSE will not fix it either. Fix the host first, then choose the backend that matches your proxy.

### Is there a fixed n8n version for this yet?

Not as of November 13, 2026. Issue #43759 is open and team-tracked as Linear GHC-9756. The fixes in this article are configuration workarounds that work on the affected versions (2.46.7 and 2.47.5) today.

---

*Sources: [GitHub issue #43759](https://github.com/n8n-io/n8n/issues/43759) (full issue text and comments, November 13, 2026); [n8n Form Trigger test-webhook handler](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/Form/v2/FormTriggerV2.node.ts); [editor testWebhookReceived handler](https://github.com/n8n-io/n8n/blob/n8n%402.47.5/packages/frontend/editor-ui/src/app/composables/usePushConnection/handlers/testWebhookReceived.ts); [Fix n8n 'Connection Lost' and Webhook URLs Behind a Proxy](https://dev.to/deploylark/fix-n8n-connection-lost-and-webhook-urls-behind-a-proxy-3lal); [n8n behind Apache reverse proxy — push notification fix](https://community.n8n.io/t/n8n-behind-apache-reverse-proxy-with-https-and-websocket-support-issues-with-push-notifications/156425).*
