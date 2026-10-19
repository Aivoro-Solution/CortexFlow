---
title: "The n8n Wait Node Doesn't Wait the Way You Think — Timing, Resume, and 5 Fixes"
description: "n8n webhook answers before your agent finishes? Wait node never resumes? The real timing mechanics plus 5 verified fixes."
date: 2026-10-19
category: automation
tags: ["n8n", "troubleshooting", "webhooks", "error-fix"]
draft: false
featured: false
image: "/og/n8n-wait-node-timing-explained.webp"
---

Your n8n workflow looks right. The form says "submitted", the webhook fired, the Wait node is sitting there patiently. And yet the downstream step never got its data, the AI agent's answer never reached the user, or the parent workflow crashed with `workflowResult is not iterable`.

The Wait node in n8n is one of the most misunderstood nodes in the tool. It pauses an execution — but *what waits, for whom, and for how long* depends on response modes, sub-workflow semantics, and resume mechanics that the UI never quite explains. In the next 10 minutes you'll learn exactly how waiting and responding work in n8n (as of October 2026, n8n 2.x), fix the four most common broken patterns, and know how to verify each one.

## What "waiting" actually means in n8n

A **webhook trigger** is a node that starts a workflow when an external HTTP request arrives at a URL n8n gives you. A **Wait node** is a mid-workflow node that pauses a *running* execution and resumes it later — after a time delay, on a webhook call, or on a form submission.

The confusion starts because n8n has **three different "wait" mechanics**, and they compose in surprising ways:

| Mechanic | What it controls | Default behavior |
|---|---|---|
| Webhook **Respond** mode | When the HTTP caller gets its answer | "When Received" — answers immediately, before downstream nodes run |
| **Wait node** resume | When a paused execution wakes up | Only three ways: time elapses, `$execution.resumeUrl` gets called, `$execution.resumeFormUrl` gets called |
| **Execute Sub-workflow** node | Whether the parent blocks for the child | "Wait for Sub-Workflow Completion" ON — but pre-2.0, suspended children broke this |

I hit all three in one week building an approval flow. Here's each failure and its fix.

## Failure 1 - The webhook answers before the AI agent finishes

**Symptom:** You wire a form to a webhook-triggered workflow: Webhook → AI Agent → Respond to Webhook. The form's user sees "Success" in under a second — but the response body is empty or wrong, because the webhook responded *before the agent finished*.

**Root cause:** The Webhook node's **Respond** setting defaults to "When Received". In that mode, n8n sends the HTTP response the moment the request arrives, then keeps running the workflow in the background. The downstream nodes still execute — your agent still runs, your database still gets written — but the HTTP caller already got its answer and left.

**Fix — tell the webhook to wait for a Respond to Webhook node:**

1. Open the Webhook trigger node → **Respond** dropdown → select **"Using 'Respond to Webhook' Node"**.
2. Add a **Respond to Webhook** node *after* the slow step (the AI agent, the HTTP request, whatever produces the real answer).
3. Set its **Respond With** to "JSON" and put the actual result in the body, e.g. `{{ $json.output }}`.

Why this works: n8n now holds the HTTP connection open and only answers when execution reaches that node. The caller gets the real result.

> **Note:** Your sender has to tolerate the wait. Form connections commonly die after ~60 seconds (typical browser/server default timeout). If the downstream work takes minutes, this fix alone isn't enough — see Fix 2.

**Verify:** Submit the form (or POST to the webhook URL with `curl`). You should get the response body containing the agent's output. Check the execution in n8n's Executions tab — it should show as *completed*, with the Respond to Webhook node as one of the last executed nodes.

## Failure 2 - Slow work keeps the webhook hanging until it times out

**Symptom:** You did Fix 1, and now the webhook responds correctly — but only when the agent is fast. When the agent takes 90+ seconds, the caller sees a timeout error even though n8n's execution eventually succeeds.

**Root cause:** Waiting for the full result is the wrong job for the webhook. The webhook's only job should be to acknowledge receipt. This pattern has a name in production engineering: **respond first, work later**.

**Fix — acknowledge immediately, finish in the background:**

Rearrange the flow to:

```
Webhook Trigger (Respond: When Received)
  → Respond to Webhook (status 200, body {"received": true, "event_id": "{{ $json.id }}"})
  → Dedupe check (have I seen this event_id? skip if yes)
  → ... all the slow LLM / database / email work ...
```

The response goes out in under a second — one dev.to practitioner measured webhook response p95 dropping from ~70 seconds to ~400 milliseconds with this change — while the execution continues asynchronously. Because senders no longer see failures, they stop retrying, which also kills duplicate executions.

Why the dedupe check matters: "respond first" means the sender *will* sometimes retry (its own timeout can still fire). Without an idempotency check on `event_id`, retries create duplicate work — the exact class of bug this pattern exists to avoid.

**Verify:** POST the same payload twice in a row. The first execution does the slow work; the second execution's dedupe check should skip it (you'll see the skipped branch in the execution log). Both calls return `{"received": true}` in under a second.

**When NOT to use this:** If the caller *needs* the computed result synchronously (a chat widget waiting for the agent's reply), keep Fix 1 and optimize the work instead. Respond-first is for fire-and-forget flows: notifications, data ingestion, lead capture.

## Failure 3 - The Wait node never resumes the way you expect

**Symptom:** A Wait node configured to resume "On Webhook Call" or "On Form Submitted" sits paused forever, or you try to click something in the UI to resume it and nothing happens.

**Root cause:** A Wait node can resume in exactly **three ways**, and there is no fourth:

1. **Automatically**, when the configured time elapses (wait 1 hour, wait until a date).
2. **Via an external call** to the resume URL, exposed in expressions as `$execution.resumeUrl`. When someone (or something) POSTs/GETs that URL, execution continues.
3. **Via a form submission** using the form resume URL, `$execution.resumeFormUrl`.

It is *not* possible to resume a waiting execution by clicking inside the workflow UI. For human-in-the-loop approval flows, the recommended pattern is to **send the resume link to the human** — by email, Slack, or an internal system — and let their click or form submit do the resuming.

**Fix — build the approval loop correctly:**

```
Webhook Trigger → AI Agent (drafts proposal)
  → Set node: build approval message with {{ $execution.resumeUrl }}
  → Send Email / Slack: "Approve this proposal: <link>"
  → Wait node (Resume: On Webhook Call; Limit Wait Time: ON, e.g. 24 hours)
  → ... continue with the approved proposal ...
```

Two things people get wrong here:

- **No Limit Wait Time = zombie executions.** Always turn on "Limit Wait Time" so the wait expires into a fallback branch (notify the requester, escalate, cancel) instead of parking in your executions list forever.
- **Waits under ~65 seconds never leave memory.** n8n only offloads a paused execution's data to the database for waits longer than about 65 seconds. Shorter waits sleep in-process. That means a server restart during a long wait is safe (the execution resumes from the DB), but a restart during a 30-second wait kills it. Design human-approval waits for hours, not seconds — they belong in the database anyway.

**Verify:** Trigger the workflow, open the execution in the Executions tab — it should show status "Waiting". Click the resume link you received by email/Slack. The execution should continue and show "Completed". Then test the fallback: trigger again, don't click the link, wait for the limit to expire — the timeout branch should fire.

## Failure 4 - Sub-workflow with a Wait node: "workflowResult is not iterable"

**Symptom:** Parent workflow calls a sub-workflow via **Execute Sub-workflow**. The sub-workflow contains a Wait node (Telegram "Send and Wait", form approval, webhook wait). The parent throws `workflowResult is not iterable` and the child's data never arrives.

**Root cause:** The parent expects the child to *finish and return a result*. But the child is *suspended* at its Wait node — it hasn't finished, so there is no result to iterate. Pre-2.0 n8n handled paused children poorly: it tried to resolve the output too early and crashed.

**Fix — depends on your n8n version:**

- **n8n 2.0+:** The **Execute Sub-workflow** node has an option called **"Wait for Sub-Workflow Completion"**. When enabled, the parent execution pauses when the child hits a Wait-style operation, and only receives the child's *true final output* when the child resumes and completes. Leave it ON for approval-in-sub-workflow patterns. (This is the v2.0 engine fix — "return expected sub-workflow data when the sub-workflow resumes from waiting.")
- **Pre-2.0 (or if the upgrade isn't an option):** decouple the two executions. Have the child POST its final result to an external channel — a Redis key, a database row, or a callback webhook back into the parent — and replace the parent's blocking call with a polling Wait (loop until the result exists). It's clunky, but it's the pattern the n8n community converged on: one forum thread documents the full HTTP + Webhook + Redis workaround, and replacing the fixed Wait with a polling loop removes the fragile fixed-delay.

> **Warning:** Don't "fix" this by turning "Wait for Sub-Workflow Completion" OFF unless the parent truly doesn't need the child's output. With it off, nodes after the Execute Sub-workflow node have no access to the sub-workflow's data — you'd be trading an error for silently missing data.

**Verify:** Run the parent workflow. In the Executions tab you should see the parent's execution go to "Waiting" when the child hits its Wait node. Resume the child (submit the form / call the resume URL). Both executions should then complete, and the Execute Sub-workflow node's output should contain the child's final data — not an error.

## Failure 5 - The whole execution gets killed while waiting

**Symptom:** A workflow with a long Wait (days, for a client reply) never resumes, or executions die with a timeout you never configured.

**Root cause:** n8n has execution-level timeouts separate from anything in the Wait node: `EXECUTIONS_TIMEOUT` and `EXECUTIONS_TIMEOUT_MAX` cap how long a *single execution* can live before n8n itself kills it. A parked, database-offloaded wait doesn't consume CPU, but it is still an open execution subject to those caps — especially in queue mode, where a stuck long-running job can also occupy a worker slot (`N8N_CONCURRENCY_PRODUCTION_LIMIT`).

**Fix:**

1. Check your timeout env vars. For a self-hosted instance that needs multi-day waits, raise them in your `docker-compose.yml` or environment:
   ```yaml
   environment:
     - EXECUTIONS_TIMEOUT=86400        # seconds; 24h. Raise for multi-day waits
     - EXECUTIONS_TIMEOUT_MAX=604800   # hard ceiling n8n won't exceed
   ```
   Why these two: `EXECUTIONS_TIMEOUT` is the default cap; `EXECUTIONS_TIMEOUT_MAX` is the ceiling the UI can't exceed. Set both deliberately — raising only one leaves the other as the silent killer.
2. **Prefer webhook-resume over fixed long waits** for open-ended human waits ("wait until the client replies"). Set the Wait node to resume **On Webhook Call** with a **Limit Wait Time** of X days: a reply resumes it early, and the limit fires the follow-up path. The execution is parked in the DB using basically no resources while it waits.
3. On n8n Cloud, note the historical 5-minute execution limit no longer applies — but self-hosted defaults still can.

**Verify:** Set a short test timeout (e.g. `EXECUTIONS_TIMEOUT=120`) and run a workflow with a 5-minute Wait. It should die at ~2 minutes — proving the cap is real and your config file is the one being read. Then restore your intended values and confirm a wait completes past the old cap.

## Key Takeaways

1. **The Webhook node decides when the caller gets answered; the Wait node decides when the execution continues.** They're different mechanics — check the Respond mode before blaming the Wait node.
2. **Default Respond mode ("When Received") answers before downstream nodes run.** Use "Using 'Respond to Webhook' Node" when the caller needs the real result, and respond-first-work-later when it doesn't.
3. **A Wait node resumes only three ways: time, `$execution.resumeUrl`, or `$execution.resumeFormUrl`.** You can't click-resume from the UI; send the link to the human.
4. **Always set Limit Wait Time** on webhook/form waits, and remember waits under ~65 seconds live in memory — restarts kill them.
5. **n8n 2.0's "Wait for Sub-Workflow Completion" is the real fix** for `workflowResult is not iterable`; pre-2.0, decouple with Redis/webhook callbacks.

Next: pick one flow in your own n8n where a form or webhook "sometimes returns nothing". Check its Respond mode first — in my experience, that's the culprit more often than the Wait node itself. If you hit the sub-workflow variant, the [community thread on suspended sub-workflows](https://community.n8n.io/t/this-discussion-is-about-a-bug-in-n8n-where-sub-workflows-containing-a-wait-node-webhook-telegram-etc-fail-to-return-their-output-to-the-parent-workflow/284625) has the full workaround history.

## FAQ

### Does the Wait node consume resources while waiting?

For waits longer than ~65 seconds, n8n offloads the paused execution's data to the database and it uses basically no resources — it sits as a row until it resumes. Shorter waits sleep in-memory. Either way, a waiting execution is not counted as concurrency; it's paused, not running.

### Why does my form submission time out even though the workflow succeeds?

The webhook answered "When Received" (or the response waited for slow downstream work and the caller's ~60-second connection timeout fired first). Either way, the fix is on the *response* side: respond-first-work-later with a Respond to Webhook node right after the trigger, or hold the response only if the caller tolerates the wait.

### Can I run a Wait node inside a sub-workflow called by Execute Sub-workflow?

Yes — on n8n 2.0+, with "Wait for Sub-Workflow Completion" enabled, the parent pauses and resumes correctly with the child's final output. On older versions, expect `workflowResult is not iterable`; decouple via a Redis/webhook callback pattern instead.
