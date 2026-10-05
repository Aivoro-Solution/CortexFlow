# Forum reply drafts — n8n Workflow Health Watchdog
# Post ONLY after cortexflow.tech deploy is live (links must resolve).
# Tone: peer-to-peer, substantive, honest about limits. Link at the end.

## 1. Topic 308805 — "Silent Failures in Production" (the 200-OK payload-change story)

That 200-OK-with-changed-payload story is the nightmare case — and I'll be honest about the boundary: no execution-metadata monitor would have caught yours, because n8n never marked anything failed. That one needs content-level assertions *inside* the workflow (validate the fields you depend on, throw loudly when the shape changes).

But the failure modes *around* it — error spikes on one workflow, a workflow that stops triggering entirely, a scheduler that quietly dies — are all visible in execution metadata. I built a small hourly watchdog that polls the n8n public API and flags exactly those: ERROR_SPIKE (≥5 failures/24h → critical), any failed runs, and active workflows with zero runs in 24h. Telegram alert + Google Sheets log, quiet when everything's fine.

Free template + setup guide: https://cortexflow.tech/templates/n8n-workflow-health-watchdog/ (the guide also walks through the in-workflow assertion pattern for your payload-shape case)

## 2. Topic 308708 — "How do you catch workflows that run fine but do nothing?"

This is the exact problem I built something for. The trick is that n8n's own API exposes everything you need — execution statuses and timestamps — so a tiny hourly workflow can watch all your other workflows:

- ERROR_SPIKE: ≥5 failures on one workflow in 24h → critical alert
- ERRORS: 1–4 failures → warning
- STALE: active workflow, zero executions in 24h → warning (this is your "runs fine but does nothing" case)

Alerts go to Telegram, everything gets logged to a Google Sheet, and quiet hours stay quiet — it only pings you when something needs you. The key config is the ignore list for workflows that are *supposed* to be infrequent (weekly/monthly).

Free import-ready template + full setup walkthrough: https://cortexflow.tech/templates/n8n-workflow-health-watchdog/

## 3. Topic 315077 — "When a workflow quietly stopped, who noticed first?"

The honest answer for most of us: the customer noticed first. That's what pushed me to build a watchdog — an hourly n8n workflow that checks all my other workflows via the public API and pings Telegram when something's off (error spikes, failed runs, or an active workflow that went stale with zero executions in 24h).

Nobody should be the one who notices first; a machine should. Template + guide (free): https://cortexflow.tech/templates/n8n-workflow-health-watchdog/

## 4. Topic 316953 — "How do you catch a workflow that stops triggering entirely?"

This one's directly solvable with n8n's own API. I run an hourly watchdog workflow that lists all active workflows and their recent executions, then flags any active workflow with zero executions inside 24h as STALE. It also catches error spikes (≥5 failures/24h → critical) and individual failed runs. Telegram alert + Sheets audit log.

One tuning tip: keep an ignore list for workflows that legitimately run weekly/monthly, or you'll get noise the first week.

Free template + setup guide: https://cortexflow.tech/templates/n8n-workflow-health-watchdog/

## Reddit — SKIP for now
The r/n8n threads found in research (wholesale business, WhatsApp local AI) don't match this workflow. Posting there would be off-topic. Only reply if a matching observability thread is found.
