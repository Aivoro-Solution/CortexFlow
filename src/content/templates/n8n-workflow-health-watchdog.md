---
title: "n8n Workflow Health Watchdog"
description: "Your n8n instance, watching itself: catches error spikes, failed executions, and workflows that went quietly stale — hourly, via the n8n API."
date: 2026-10-05
category: "automation"
difficulty: "intermediate"
workflow: "/templates/n8n-workflow-health-watchdog.json"
integrations: ["n8n API", "Telegram", "Google Sheets"]
---

## How it works

1. **Hourly Check wakes up every hour** — a Schedule Trigger. For busy instances with dozens of workflows, hourly is the sweet spot; for quiet ones, change it to every 6 hours in the trigger node.
2. **CONFIG — Watchdog holds every tunable** — your n8n host URL, the check window (24h), the staleness threshold (24h), the error-spike threshold (5), an `ignore_workflows` list for intentionally infrequent workflows, and your Telegram chat ID.
3. **Get Active Workflows lists what's supposed to be running** — `GET /api/v1/workflows?active=true` on your own n8n instance. Inactive workflows are skipped by design: if you turned it off, you already know.
4. **Get Recent Executions pulls the last 250 runs** — `GET /api/v1/executions?limit=250&startedAfter=...` filtered to your check window. No payload data is fetched — only statuses and timestamps, so this stays cheap.
5. **Analyze Health joins the two and finds three failure shapes** — a Code node that flags:
   - **ERROR_SPIKE** (CRITICAL) — a workflow with >= `error_spike_threshold` failed executions inside the window. This is the "something broke an hour ago and nobody noticed" case.
   - **ERRORS** (WARNING) — any failed or crashed executions in the window, below spike level.
   - **STALE** (WARNING) — an active workflow with zero executions in `stale_hours`. This catches the scheduler that silently stopped, the webhook whose source stopped calling, the cron nobody re-enabled after maintenance.
6. **Any Issues? ends quiet runs silently** — no "all clear" spam. You only hear from this workflow when something needs you.
7. **Expand Issues fans out one item per finding** — so each problem gets its own alert and its own log row.
8. **Format Alert builds the message** — 🚨 CRITICAL / ⚠️ WARNING, issue type, workflow name, the detail line, and the timestamp of the last error where relevant.
9. **Telegram — Health Alert pings you** — one message per issue.
10. **Log Issues appends the audit trail** — every finding lands in the `watchdog_log` sheet (`time`, `workflow_name`, `issue_type`, `severity`, `detail`). Review it weekly: repeat STALE flags mean your `ignore_workflows` list needs updating; repeat spikes on one workflow mean that workflow needs fixing, not more alerting.

## Set up steps

You'll need:

- A self-hosted n8n instance (or n8n Cloud) with the **public API enabled**
- An n8n API key — in your n8n instance go to *Settings → n8n API → Create an API key*. It needs permission to read workflows and executions.
- A Telegram bot — create one with BotFather at https://t.me/BotFather (send `/newbot`, copy the token) and get your chat ID
- A Google account with a sheet for the log

1. **Create the API key** in your n8n instance (*Settings → n8n API*). Copy it — you won't see it again.
2. **Create a Header Auth credential** in the *same* n8n instance where you'll run this watchdog: *Credentials → New → Header Auth*. Set the **Name** to exactly `X-N8N-API-KEY` and the **Value** to your API key. Save.
3. **Create the `watchdog_log` sheet** — headers in row 1: `time`, `workflow_name`, `issue_type`, `severity`, `detail`.
4. **Download the workflow JSON** using the download button on this page.
5. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
6. **Attach the credentials** — open *Get Active Workflows* and *Get Recent Executions*, set auth to your Header Auth credential. Open *Log Issues*, select your Google Sheets credential. Open *Telegram — Health Alert*, select your Telegram credential.
7. **Fill in CONFIG — Watchdog** — your n8n host (`https://your-n8n-domain.com`, no trailing slash), your Telegram chat ID, and add your intentionally-infrequent workflows (weekly reports, monthly cleanups) to `ignore_workflows` so they don't cry wolf.
8. **Run once manually** — you should see it complete quietly if all is well. To test the alert path, temporarily set `stale_hours` to `0` — every workflow will flag STALE and you'll get the Telegram messages. Then set it back.

Approval note: the first week will be noisy while you tune `ignore_workflows` and `stale_hours` to your instance's real rhythm. That's normal — the log sheet is your tuning evidence. Don't raise thresholds to silence a workflow that is actually broken; fix the workflow.

## Customize it

- **The "runs fine but does nothing" check** — the forum's most-requested detection. Add a branch: for each workflow's latest *successful* execution, `GET /api/v1/executions/{id}?includeData=true` and inspect whether the final node's output is empty. Costs one API call per workflow per run — fine hourly, wasteful every 5 minutes.
- **Error-workflow integration** — n8n lets you attach an *error workflow* per workflow (*Workflow Settings → Error Workflow*). Point your critical workflows at a small router workflow that POSTs to this watchdog's webhook variant for instant (not hourly) alerts on hard failures, and keep the hourly run for spikes and staleness.
- **Slack / PagerDuty instead of Telegram** — swap the Telegram node; the alert text needs no changes. For on-call rotations, route CRITICAL to PagerDuty and WARNING to Slack.
- **Auto-retry** — after flagging ERROR_SPIKE, `POST /api/v1/executions/{id}/retry` on the failed executions. Add a Code node that caps retries (max 2 per execution) so a deterministically-broken workflow doesn't retry forever.
- **Multi-instance** — run one watchdog per n8n instance (dev / staging / prod) and add an `environment` field in CONFIG so alerts say which instance is sick.
