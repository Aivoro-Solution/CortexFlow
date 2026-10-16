---
title: "Multi-Store Sales Consolidator"
description: "Weekly n8n workflow that consolidates multi-store sales sheets from Google Drive, analyzes them with AI, and emails the owner an HTML report. Import-ready."
date: 2026-10-16
category: "automation"
difficulty: "intermediate"
workflow: "/templates/multi-store-sales-consolidator.json"
integrations: ["Google Sheets", "Google Drive", "Gmail", "OpenAI", "Telegram"]
---

## How it works

Your Monday-morning sales briefing, fully automatic:

1. **STEP 1 — Weekly trigger + config + NEW log** — the "Weekly Monday Trigger" fires every Monday at 8:00 AM. "CONFIG — Store Settings" holds every editable value (owner email, spreadsheet ID, Drive folder ID, per-store tab names, anomaly threshold). The run is logged to the `Report Runs` tab with status `NEW`.
2. **STEP 2 — List store sheets + prepare store list** — "List Store Sheets — Google Drive" lists every spreadsheet in your configured Drive folder (one per store). "Prepare Store List" maps each file to a store name (from the file name) plus its sales tab, and "IF — Sheets Found" stops cleanly when the folder is empty.
3. **STEP 3 — Loop stores: read, tag, consolidate** — "Loop Stores — Split In Batches" processes one store at a time: "Read Store Sheet" reads that store's sales tab, "Tag Rows — Add Store Name" stamps every row with the store, and "Append Consolidated Rows" appends them to the `Consolidated Sales` sheet.
4. **STEP 4 — Aggregate totals + WoW + PROCESSING** — "Read Consolidated Rows — This Week" pulls the consolidated rows, then "Compute Weekly Totals" calculates per-store revenue, units sold, the top 5 items, and week-over-week changes (this week vs last week). The run flips to `PROCESSING` in the log.
5. **STEP 5 — AI weekly analyst** — "AI Agent — Weekly Sales Analyst" (gpt-4o-mini) reads the totals and, via the "Structured Output Parser — Sales Insights", returns `{total_revenue, revenue_wow_change_pct, per_store, top_items, insights, red_flags}`.
6. **STEP 6 — Anomaly check → Telegram alert** — "IF — Revenue Anomaly" compares |week-over-week revenue change| against your `revenue_anomaly_threshold_pct`. A swing past the threshold fires an instant "Telegram — Anomaly Alert" with the red flags. Both branches continue to the report.
7. **STEP 7 — HTML report → Gmail → DONE → Telegram** — "Build Report HTML" renders the owner email (per-store table, top items, AI insights, red flags), "Gmail — Send Weekly Report" emails it to you, the log flips to `DONE`, and "Telegram — Success Notification" confirms with the headline numbers.
8. **STEP 8 — Failure path** — if no store sheets are found, the run is logged as `FAILED` and "Telegram — Failure Alert" tells you to check the Drive folder ID.

**Status flow in Sheets (`Report Runs` tab):** `NEW` → `PROCESSING` → `DONE` (or `FAILED` when no store sheets are found)

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- Google Sheets + Google Drive OAuth2 credentials — n8n Credentials → Google Sheets OAuth2 / Google Drive OAuth2
- An OpenAI API key — [platform.openai.com/signup](https://platform.openai.com/signup) → API keys
- Gmail OAuth2 credential — n8n Credentials → Gmail OAuth2 (send the report from your own account)
- A Telegram bot — [telegram.org](https://telegram.org) → message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `multi-store-sales-consolidator.json`.
2. **Prepare your store sheets** — in Google Drive, create one spreadsheet per store inside a single folder (the file name becomes the store name). Each sheet needs a tab with exactly these headers: `Date | Item | Qty | Revenue`. Share every sheet with the Google account connected to n8n.
3. **Create the log workbook** — make a Google Sheet with two tabs:
   - `Report Runs` with headers: `Run Date | Week Of | Status | Stores | Total Revenue | Notes`
   - `Consolidated Sales` with headers: `Date | Store | Item | Qty | Revenue`
4. **CONFIG — Store Settings** — open the Set node and fill in:
   - `owner_email` — where the weekly HTML report goes
   - `spreadsheet_id` — the log workbook's ID (from its URL)
   - `sales_drive_folder_id` — the Drive folder ID containing one spreadsheet per store (from its URL)
   - `store_sheet_tabs` — comma-separated tab names, one per store in file order (e.g. `Weekly Sales`)
   - `revenue_anomaly_threshold_pct` — alert when |week-over-week revenue change| hits this % (default `15`)
   - `telegram_chat_id` — your Telegram chat ID
   - `log_sheet_name` / `consolidated_sheet_name` — only change if you renamed the tabs in step 3
5. **Credentials** — select your Google Sheets credential in all seven Sheets nodes, your Google Drive credential in "List Store Sheets — Google Drive", your OpenAI credential in "OpenAI Chat Model — Analyst", your Gmail credential in "Gmail — Send Weekly Report", and your Telegram credential in both Telegram nodes (or use the credential prompt on import). Then **activate** the workflow.

## Customize it

- **Schedule** — "Weekly Monday Trigger" runs Mondays at 8:00 AM; change the weekday or time for your reporting cadence (daily runs work too — the WoW logic keys off whatever day it runs).
- **Anomaly sensitivity** — raise or lower `revenue_anomaly_threshold_pct` in "CONFIG — Store Settings" (10 for twitchy, 25 for only real fires).
- **More stores, no changes** — drop another store spreadsheet in the Drive folder and it gets picked up automatically next run. Store name comes from the file name, so name files like `Downtown.xlsx` / `Airport Mall.xlsx`.
- **Report branding** — edit the HTML template in "Build Report HTML" to add your logo, currency symbols, or a section linking back to the `Consolidated Sales` sheet.
- **AI depth** — the system prompt in "AI Agent — Weekly Sales Analyst" is your analyst's brief: add margin targets, promo calendars, or "compare against last month too" and the structured output keeps the report format stable.
- **Sell it** — this is the classic agency product the YouTube crowd keeps pitching: clone the workflow per retail client, swap the one CONFIG node, point it at their Drive folder, done.
