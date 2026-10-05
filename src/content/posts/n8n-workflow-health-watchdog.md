---
title: "Your n8n Workflows Are Failing Silently. Build the Watchdog That Catches It"
description: "A webhook returns 200 OK, downstream mapping breaks silently, and hundreds of syncs sit unprocessed for days. Here's an hourly n8n watchdog that catches it."
date: 2026-10-05
category: automation
tags: ["n8n", "monitoring", "observability", "error handling", "self-hosting"]
draft: false
featured: false
---

A production n8n pipeline returned a clean `200 OK` on every webhook call — and silently dropped hundreds of data syncs for three days. An upstream API had changed its payload shape without notice; n8n registered no system-level failure, so nothing alerted. The team found out from a customer. That story, posted on the n8n forum, pulled 30+ replies in days, and it sits next to two more threads asking the same thing in different words: *how do you catch a workflow that runs fine but does nothing?* and *when a workflow quietly stops, who notices first?*

The answer is a watchdog: a small n8n workflow that polls your n8n instance's own public API every hour and flags the three failure shapes that the Executions tab won't shout about — error spikes, failed runs, and active workflows that went quietly stale. By the end of this guide you'll have it imported, configured, and tested, with Telegram alerts and a Sheets audit log. The [ready-made template](/templates/n8n-workflow-health-watchdog/) does the heavy lifting; this post explains every piece so you can trust it.

**Silent failure**, for this post, means any case where a workflow *should* have done work and didn't — or did it wrong — without n8n marking the execution as failed. A **stale** workflow is an active one with zero executions inside your expected window: the scheduler that stopped, the webhook whose source went quiet, the cron nobody re-enabled after maintenance.

## What the watchdog catches

| Failure shape | What it means | Severity |
|---|---|---|
| ERROR_SPIKE | ≥5 failed executions on one workflow inside 24h | 🚨 CRITICAL |
| ERRORS | 1–4 failed/crashed executions inside 24h | ⚠️ WARNING |
| STALE | Active workflow, zero executions in 24h | ⚠️ WARNING |

**One honest boundary up front:** this catches failures *visible in execution metadata* — statuses and timestamps. It does not catch the "200 OK but the mapping was wrong" case from the forum story; that needs content-level checks inside the workflow itself (assert on the fields you depend on, fail loudly). The watchdog catches everything around that hole: the spikes, the quiet deaths, the schedulers that stopped.

## Prerequisites

- A self-hosted n8n instance (or n8n Cloud) with the **public API enabled** — on self-hosted it's on by default; the API key is created per-user under *Settings → n8n API*.
- A Telegram bot token (via [@BotFather](https://t.me/BotFather)) and your chat ID.
- A Google account, for the audit-log sheet.
- About 20 minutes.

**Example terminology** — replace these everywhere they appear:

- `<your-n8n-domain>` — your instance, e.g. `https://n8n.example.com` (no trailing slash)
- `<your-chat-id>` — the Telegram chat ID from BotFather's `/getid` flow

## Step 1 — Create the n8n API key

In your n8n instance: *Settings → n8n API → Create an API key*. Give it a label like `watchdog` and copy the key — you won't see it again.

> **Note:** the key inherits *your* user permissions. A viewer-role key can't read executions. Use an owner/admin key, and treat it like a password: it goes into a credential, never into a node field.

## Step 2 — Create the Header Auth credential

In n8n: *Credentials → New → Header Auth*. Set **Name** to exactly `X-N8N-API-KEY` and **Value** to the key from Step 1. Save it as `n8n API`.

Why header auth and not Basic? n8n's public API authenticates on the `X-N8N-API-KEY` header — there is no username/password form. The [template](/templates/n8n-workflow-health-watchdog/)'s two HTTP nodes are pre-wired to ask for a Header Auth credential; you just select this one.

## Step 3 — Import the watchdog workflow

Download the [n8n Workflow Health Watchdog template](/templates/n8n-workflow-health-watchdog/) and import it: *Workflows → ⋯ → Import from file*. You'll see 11 nodes on the canvas:

```
Hourly Check → CONFIG → Get Active Workflows → Get Recent Executions
    → Analyze Health → Any Issues? → Expand Issues → Format Alert
    → Telegram Alert → Log Issues
```

The two HTTP nodes call `GET /api/v1/workflows?active=true` and `GET /api/v1/executions?limit=250&startedAfter=…` on *your own instance*. No execution payload data is fetched — statuses and timestamps only — so each hourly run costs a handful of light API calls.

## Step 4 — Configure it

Open **CONFIG — Watchdog** and set:

- `n8n_host` → `https://<your-n8n-domain>`
- `telegram_chat_id` → `<your-chat-id>`
- `ignore_workflows` → workflows that are *supposed* to be infrequent (`["Weekly Report", "Monthly Cleanup"]`). This list is the difference between a useful watchdog and alert noise — be honest here.
- `stale_hours` → `24` to start; `error_spike_threshold` → `5`.

Then create a Google Sheet named `watchdog_log` with headers `time, workflow_name, issue_type, severity, detail`, and point the **Log Issues** node at it with your Google Sheets credential. Select your Telegram credential on the Telegram node and the Header Auth credential on both HTTP nodes.

## Step 5 — Verify it works

Don't wait for a real failure. Temporarily set `stale_hours` to `0` in CONFIG and run once manually — every active workflow will flag STALE, and your phone should buzz with one Telegram message per workflow plus new rows in `watchdog_log`. Then set `stale_hours` back to `24` and activate the workflow (toggle, top-right).

You should see the pattern the template is designed around: **quiet runs end silently** at the *Any Issues?* node. You only hear from it when something needs you.

## How the detection actually works

The **Analyze Health** Code node does a join your eyes can't do at a glance: it groups the 250 sampled executions by `workflowId`, then walks every *active* workflow and asks three questions — how many errors in the window, when was the last run, and is this workflow on the ignore list. Z-scores aren't needed here; counts and timestamps are the right tool because the failure modes are discrete, not statistical.

Two approximations to know about: staleness is computed from the 250 most recent executions, so on instances doing more than 250 runs inside the window, the sample won't cover the full period — the STALE check degrades gracefully rather than erroring. And `startedAfter` needs a recent n8n version; if yours rejects the parameter, drop it from the URL and the `limit=250` still bounds the call.

## Limits

- It won't catch wrong-but-successful runs (the 200-OK-with-broken-mapping case). Put assertions inside critical workflows for that.
- The first week is tuning week: expect STALE noise until `ignore_workflows` matches reality. Tune from the log sheet, don't just raise thresholds.
- One watchdog per n8n instance. If you run dev/staging/prod, import it three times and label CONFIG accordingly.

## Key Takeaways

1. **Silent failures are a metadata problem** — statuses and timestamps, which the n8n API exposes, catch spikes, errors, and stale workflows without touching payload data.
2. **Quiet runs should end quietly** — a monitor that cries "all clear" hourly trains you to ignore it.
3. **The ignore list is the product** — a watchdog is only as good as its knowledge of which workflows are *supposed* to be quiet.
4. **Content-level correctness still needs in-workflow assertions** — metadata monitoring and payload validation are complementary, not substitutes.

Next: import the [template](/templates/n8n-workflow-health-watchdog/), run the `stale_hours: 0` test, and check the forum threads that motivated this — if you've lived the 200-OK-silent-break, you'll recognize your own war story in the replies.
