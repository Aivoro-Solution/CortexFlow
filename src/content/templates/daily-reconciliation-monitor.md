---
title: "Daily Reconciliation Monitor"
description: "A daily n8n check that compares yesterday's source vs destination records, lists missing, extra and mismatched rows, and pings you on Telegram."
date: 2026-10-23
category: "automation"
difficulty: "intermediate"
workflow: "/templates/daily-reconciliation-monitor.json"
integrations: ["Google Sheets","Telegram"]
---

## How it works

This template answers the n8n community forum thread **"A daily count check for failures that never show as an error"** (Oct 19, 2026, 6 replies, 92 views — https://community.n8n.io/t/a-daily-count-check-for-failures-that-never-show-as-an-error/322653) and its follow-up Built-with-n8n showcase **"Scheduled count check: missing, extra and mismatched orders in one daily email"** (Oct 23, 2026). The core insight from both threads: executions run green while data silently breaks — a sync job "succeeds" but rows never land, and nobody notices for days. This workflow is the scheduled safety net: every morning it reconciles yesterday's source rows against yesterday's destination rows and tells you exactly what drifted, before it becomes a week-old mystery.

1. **STEP 1 — Yesterday's window + read both sides** — `Daily 7AM Trigger` fires every morning at 07:00 → `CONFIG — Reconciliation` holds every user-editable value (spreadsheet, sheet names, key/timestamp/compare fields, tolerance, alert threshold, Telegram chat ID) → `Build Yesterday Window` computes yesterday's date (YYYY-MM-DD) → `Log Run — Status NEW` appends a run row to the Run Log → `Read Source Rows` and `Read Destination Rows` pull both sheets from Google Sheets.
2. **STEP 2 — Compare row sets on the key field** — `Compare Row Sets` filters both sides to yesterday using your `timestamp_field`, matches rows on `key_field`, and flags three break types: `MISSING_IN_DESTINATION` (in source, never landed), `EXTRA_IN_DESTINATION` (in destination, no source row — phantom data), and `MISMATCHED` (same key, different values — numeric fields compared within your `tolerance`, everything else exact match). It emits one summary item with counts → `Log Run — Status COMPARING` records the counts → `IF — Breaks ≥ Threshold` routes on your `alert_threshold`.
3. **STEP 3 — Log every break** — on the TRUE branch, `Expand Break Rows` turns each break into its own item → `Log Breaks — Status BREAK_FOUND` appends one row per break to the Run Log sheet so you have a full audit trail.
4. **STEP 4 — AI classifies each mismatch** — `AI Agent — Classify Mismatches` (model `gpt-4o-mini` via `OpenAI Chat Model — Classifier`) reads every mismatched record and returns a strict classification through `Structured Output Parser — Cause`: `timing_difference` (destination usually catches up — sync lag), `transformation_bug` (mapping/rounding error), or `genuine_loss` (values irreconcilable — investigate). The prompt is deliberately conservative about calling something a genuine loss.
5. **STEP 5 — Telegram summary + final statuses** — `Merge — Combine Reports` collects both branches (the FALSE branch skips logging and the agent) → `Build Summary` assembles one message: "🔍 Reconciliation 2026-10-22: ✅ clean — 2,480 rows checked, no breaks." or "⚠️ 3 missing / 1 extra / 2 mismatched" with the top break details and likely causes → `Telegram — Send Summary` pings you → `Log Run — Status REPORTED` → `Log Run — Status DONE`.

**Status flow in the Run Log:** `NEW` → `COMPARING` → `BREAK_FOUND` (one row per break) → `REPORTED` → `DONE`

*How this differs from our [Uptime Monitor Incident Escalation](/templates/uptime-monitor-incident-escalation/): that template watches whether your endpoints are up — this one assumes everything is "up" and checks whether the data that moved yesterday is actually correct.*

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- Google Sheets OAuth2 credential — n8n Credentials → Google Sheets OAuth2 ([sheets.google.com](https://sheets.google.com))
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `daily-reconciliation-monitor.json`.
2. **CONFIG — Reconciliation** — open the Set node and fill in:
   - `spreadsheet_id` — your Google Sheet ID (replacing `PASTE_YOUR_SPREADSHEET_ID`)
   - `source_sheet` — `SourceRows` default; the tab holding yesterday's source records
   - `dest_sheet` — `DestRows` default; the tab holding yesterday's destination records
   - `log_sheet` — `RunLog` default; the audit-trail tab
   - `key_field` — `order_id` default; the column both sheets join on
   - `timestamp_field` — `created_at` default; the column used to filter to yesterday (values like `2026-10-22` or `2026-10-22T14:03:00`)
   - `compare_fields` — `total,quantity,status` default; comma-separated columns compared per matched key
   - `tolerance` — `0.01` default; numeric fields within this difference count as equal (use `0` for exact match)
   - `alert_threshold` — `1` default; the break-count that triggers the detailed branch (AI classification + per-break logging)
   - `telegram_chat_id` — where the daily summary lands (replacing `PASTE_YOUR_TELEGRAM_CHAT_ID`)
3. **Google Sheet** — create a Google Sheet with three tabs:
   - `SourceRows` and `DestRows` (or your names) with these exact headers: `order_id | created_at | total | quantity | status` — rename the headers to match your `key_field`, `timestamp_field`, and `compare_fields` if you change them
   - `RunLog` with these exact headers: `Run Date | Source | Destination | Rows Checked | Missing | Extra | Mismatched | Status | Note`
   - Put the spreadsheet ID in `spreadsheet_id`, and select your Google Sheets credential in all seven Sheets nodes (`Log Run — Status NEW`, `Read Source Rows`, `Read Destination Rows`, `Log Run — Status COMPARING`, `Log Breaks — Status BREAK_FOUND`, `Log Run — Status REPORTED`, `Log Run — Status DONE`).
4. **AI + notifications** — select your OpenAI credential in `OpenAI Chat Model — Classifier` (model is `gpt-4o-mini` by default), select your Telegram credential in `Telegram — Send Summary`, and **activate** the workflow.
5. **First run** — run it once manually against a small test sheet: check the Run Log flips `NEW` → `COMPARING` → `REPORTED` → `DONE`, that a deliberately missing row produces a `BREAK_FOUND` row plus a ⚠️ Telegram message, and that matching rows produce the ✅ clean message.

## Customize it

- **Different source of truth** — `Read Source Rows` / `Read Destination Rows` are plain Google Sheets reads; swap either for an HTTP Request node hitting your API or a database node, as long as the rows carry your `key_field`, `timestamp_field`, and compare columns.
- **Tune the tolerance** — `tolerance` at `0` means exact numeric match; raise it (e.g. `0.5`) when source and destination round differently and you only care about real drift.
- **Raise the alert bar** — set `alert_threshold` to `5` so single-row noise just lands in the Run Log, and only real breakage triggers the AI classification + detailed Telegram message.
- **Tune the classifier** — the `systemMessage` in `AI Agent — Classify Mismatches` is where you encode your domain knowledge — add rules like "status flips from paid to refunded are always genuine_loss" or "quantity diffs under 2 are timing_difference during sale hours".
- **Compare more fields** — add column names to `compare_fields` (e.g. `total,quantity,status,customer_email`) — but keep exact-match fields truly exact; fuzzy fields belong behind a tolerance or the AI branch.
- **Different cadence** — change `Daily 7AM Trigger` to hourly for hot pipelines, or weekly for slow ones (the "yesterday" window in `Build Yesterday Window` then becomes the last 24h — adjust that Code node for a different window).
- **No AI needed** — delete `AI Agent — Classify Mismatches` and its two sub-nodes, and reconnect `Log Breaks — Status BREAK_FOUND` straight into `Merge — Combine Reports`; `Build Summary` already handles a missing classification.
