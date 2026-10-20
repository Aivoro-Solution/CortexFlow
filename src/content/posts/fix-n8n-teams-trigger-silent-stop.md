---
title: "Fix n8n Microsoft Teams Trigger Stopping After a Few Days (Silent Expiry)"
description: "Your n8n Microsoft Teams Trigger fires fine for 3 days then goes silent with no error? The Microsoft Graph subscription expired. 4 verified fixes inside."
date: 2026-10-20
category: automation
tags: ["n8n", "microsoft-teams", "webhook", "self-hosting", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-teams-trigger-silent-stop.webp"
---

You built a workflow with the Microsoft Teams Trigger, tested it, watched messages flow in for a few days — then nothing. The workflow still shows as active, n8n logs show zero errors, sending a test message through the trigger manually still works. It's just… silent in production.

I hit this exact pattern on a Teams alerting workflow and, after reading the community threads, found the root cause has nothing to do with n8n being broken: **Microsoft Graph change-notification subscriptions expire**. The Teams Trigger registers one of these subscriptions when you activate the workflow, and for Teams message subscriptions Microsoft caps the lifetime at 3 days. n8n doesn't renew it for you. After 3 days Microsoft stops calling your webhook, n8n never fires, and there is nothing to fail — so nothing errors.

By the end of this article you'll know how to confirm the diagnosis in 30 seconds and have four fixes, from the 10-second reset to a renewal workflow that keeps the trigger alive forever.

Quick definitions so we're on the same page: the **Microsoft Teams Trigger** node is n8n's app trigger that fires your workflow when a new message arrives in a channel or chat. Under the hood it uses **Microsoft Graph change notifications** — Graph (Microsoft's API for Teams/Outlook/etc.) registers a *subscription* pointing at your n8n webhook URL and POSTs to it whenever something changes. Every such subscription carries an **`expirationDateTime`** — a hard expiry date set by Microsoft, after which it silently stops.

## The symptom

The Teams Trigger fires reliably for roughly 2–3 days after you activate the workflow, then stops reacting to new messages entirely. The workflow is still published and active. The Executions list shows no failures — because no executions are starting at all. There is nothing red in the n8n editor.

What makes it maddening: manual testing works. Click "execute step" on the trigger, send a message, and the test webhook fires fine. The problem is only the *production* webhook path, which depends on the Graph subscription that is now dead.

## The root cause

When the workflow activates, the Teams Trigger node creates a Microsoft Graph subscription for the Teams resource (channel messages). Microsoft allows a maximum subscription lifetime of **3 days** for Teams message resources. Community reports match this exactly: "trigger works at the beginning, but after a couple days it stops… no error logs" ([community.n8n.io](https://community.n8n.io/t/problem-teams-trigger-webhook/147354/12)).

One user in that thread found the smoking gun: querying `GET https://graph.microsoft.com/v1.0/subscriptions` lists your active subscriptions with their `expirationDateTime` — and the Teams one was expired. They also noticed the subscription's `creatorId` pointed at their personal user ID rather than the n8n app registration, a hint that the subscription was created with delegated credentials and inherits that context.

**Why n8n doesn't warn you:** a trigger that receives no webhook calls doesn't fail — it simply never starts an execution. n8n has no built-in monitor that says "this trigger hasn't heard from Microsoft in 3 days." So you get silence, not an error. The same silence appears in the Microsoft Graph Explorer list: the expired subscription just disappears from the API response.

## Prerequisites

- A self-hosted or Cloud n8n instance with the workflow using the Microsoft Teams Trigger
- A way to call Microsoft Graph: the [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) (signed in as your Teams user) is enough for diagnosis
- Your Azure app registration details (the one behind the n8n Microsoft credential), for the renewal workflow later

**Example terminology** used below:

- `<subscription-id>` — the `id` of your Teams subscription from the Graph API
- `<your-n8n-host>` — your n8n host, e.g. `n8n.example.com`
- `<credential>` — your existing n8n Microsoft credential (delegated user permissions)

## Step 1 - Confirm the subscription expired

This takes 30 seconds and rules out every other cause.

Open the Microsoft Graph Explorer (or an n8n HTTP Request node with your Microsoft credential) and run:

```http
GET https://graph.microsoft.com/v1.0/subscriptions
```

You should see a JSON array of your active subscriptions. Look for the entry whose `notificationUrl` points at your n8n Teams webhook (something like `https://<your-n8n-host>/webhook/<id>/microsoft-teams-trigger`).

- **If your Teams entry is missing entirely or its `expirationDateTime` is in the past:** the diagnosis is confirmed — Microsoft dropped the subscription. Skip to Step 2.
- **If it's present with a future `expirationDateTime`:** your problem is something else — check that the workflow is published (n8n 2.x keeps drafts unpublished until you click Publish), that the app registration has tenant admin consent, and that the Teams channel the trigger watches still exists.

> **Note:** this GET call lists *subscriptions you created* — you must be signed in as the same account that owns the n8n Microsoft credential, or the list will look empty even when subscriptions exist.

## Step 2 - Restore it right now: deactivate and reactivate

On activation, trigger nodes in n8n delete their old registration and create a fresh one. So the fastest recovery is:

1. Open the workflow in n8n, unpublish (or toggle inactive on n8n 1.x).
2. Wait a few seconds, then publish it again.
3. Send a message in the watched Teams channel — the trigger should fire within seconds.

**Why this works:** re-activation creates a brand-new Graph subscription with a fresh 3-day `expirationDateTime`. Expect this to fix you for exactly the next ~3 days — which is why Step 3 exists. Treat this as the emergency lever, not the solution.

## Step 3 - Make it permanent: auto-renew the subscription with a scheduled workflow

Microsoft lets you extend a subscription's life with a PATCH request before it expires:

```http
PATCH https://graph.microsoft.com/v1.0/subscriptions/<subscription-id>
Content-Type: application/json

{
  "expirationDateTime": "2026-10-23T12:00:00Z"
}
```

The new date must be within the resource's maximum (3 days from now for Teams messages). So a separate n8n workflow can renew the trigger's subscription every 2 days, forever. Here's the build:

1. **Schedule Trigger** — set it to run every 2 days (e.g. daily at 03:00 with a cron you can reason about: `0 3 */2 * *`).
2. **Code node** — compute a new expiration 2 days out, in ISO-8601 UTC:
   ```javascript
   const expiry = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000);
   return [{ json: { expirationDateTime: expiry.toISOString().split('.')[0] + 'Z' } }];
   ```
3. **HTTP Request node** — PATCH `https://graph.microsoft.com/v1.0/subscriptions/<subscription-id>`, body `{{ $json }}` from the Code node, authentication via your Microsoft credential (delegated, same user that owns the subscription).
4. Optional: add an IF node after it — if the PATCH returns 404, the subscription is already gone (someone deactivated the workflow); route to a notification (email/Slack) so you know to re-activate via Step 2.

**Why each piece is there:** the schedule runs more often than the 3-day expiry, so the subscription never lapses. The 404 branch matters because PATCH-ing an expired subscription returns "resource not found" — you can't renew what's already deleted; you must recreate via re-activation first, then renew on schedule afterwards.

> **Warning:** this renewal workflow renews the *Teams* subscription with delegated user permissions. If that user leaves the tenant or their password changes, the refresh token dies and the renewals start failing — you'll see 401s. Re-authenticate the Microsoft credential in n8n and you're back.

## Step 4 - Check permissions and admin consent

Several threads in the community report connect the silent stop to permission drift:

1. In Azure (Entra ID) → your app registration → **API permissions**, confirm the Microsoft Graph delegated permissions the Teams Trigger needs are still granted *and* admin-consented. If consent was revoked or the app was re-registered, the trigger may create a subscription that silently fails to deliver.
2. The tenant must have admin consent granted by a global administrator — the community FAQ answer in the same thread notes this requirement explicitly ([community.n8n.io](https://community.n8n.io/t/problem-teams-trigger-webhook/147354/12)).
3. If you changed the Teams channel name or the watched team, re-open the trigger node and re-select the channel — a subscription points at a specific resource ID, and a renamed/moved channel means notifications go nowhere.

If the subscription's `creatorId` shows your personal user instead of the app (as one forum user noticed), that's expected with delegated permissions — but it means the subscription's lifetime is tied to that user's session. Using the same dedicated "service" account for both the credential and the renewal workflow keeps this predictable.

## Step 5 - Alternative: switch to polling when push isn't worth the maintenance

If the renewal plumbing feels like too much machinery, replace the Teams Trigger with a **Schedule Trigger + Microsoft Teams "Get messages" node**:

- Schedule every 5 minutes (or whatever latency you can tolerate).
- The Teams node lists recent messages in the channel; a Code node filters by `createdDateTime` newer than the last run (store a watermark in a Data Table or use `{{ $now }}` window arithmetic).
- New items flow into the rest of the workflow exactly like trigger items.

**Trade-off:** you get up to 5 minutes of latency instead of seconds, and you spend API calls on empty polls. What you gain is a trigger that *cannot* silently expire — scheduled triggers don't depend on any Microsoft subscription. For non-urgent alerting, this is the most robust option.

## Step 6 - Verify the fix

After applying Step 2 (or Step 3):

1. Query `GET https://graph.microsoft.com/v1.0/subscriptions` again — your Teams entry should be back with a future `expirationDateTime`.
2. Post a message in the watched channel. An execution should start within seconds.
3. For the renewal workflow: check its Executions the next day — the PATCH should return 200 each run. Set the workflow's execution history retention high enough (`EXECUTIONS_DATA_PRUNE`) to see the pattern over a week.

The real test is boring: **the trigger still fires on day 4**. Note the date you applied the fix, and check the subscription's `expirationDateTime` once more after 72 hours — if it moved forward, the renewal loop is holding.

## When NOT to use the renewal workflow

- If your trigger only needs to run for a short campaign (a few days), the deactivate/reactivate reset from Step 2 is enough — don't build machinery for a temporary job.
- If near-real-time delivery doesn't matter, the polling approach in Step 5 is simpler and has no expiry surface at all.
- If you can't guarantee the delegated user account will stay alive (shared team credentials, frequent password rotations), consider the polling approach or an application-permission-based custom integration instead.

## FAQ

### Why doesn't n8n just renew the subscription itself?

As of October 2026 the Teams Trigger node creates the Graph subscription on activation but has no renewal logic — the community has flagged this as the root cause of the silent stops. Until the node handles renewal natively, the scheduled PATCH in Step 3 is the reliable workaround.

### How long do Microsoft Graph subscriptions last for Teams?

Three days maximum for Teams message resources — that's why the failure shows up "after a couple days." The limit is set by Microsoft, not n8n, and it applies to any Graph integration, not just n8n.

### Does re-activating the workflow delete my old subscription?

Yes — trigger nodes clean up their registrations on deactivation and recreate them on activation. That's what makes Step 2 safe: no duplicate subscriptions, no orphan webhooks.

## Key Takeaways

1. **The silent stop is a Microsoft Graph subscription expiry** — Teams message subscriptions max out at 3 days, n8n doesn't renew them, and Microsoft stops calling your webhook without telling anyone.
2. **Diagnose in 30 seconds** with `GET https://graph.microsoft.com/v1.0/subscriptions` — a missing or past-dated `expirationDateTime` confirms it.
3. **Deactivate/reactivate buys you 3 more days** — the emergency lever, not the fix.
4. **A scheduled PATCH workflow renews it forever** — run every 2 days, handle the 404 (already-deleted) case with an alert.
5. **When push isn't worth the upkeep, poll instead** — Schedule Trigger + Get messages can't silently expire.

Next: build the heartbeat check — a tiny workflow that alerts you (Slack/email) when any critical trigger hasn't produced an execution in its expected window. That one catches every silent-failure class, not just Teams.
