---
title: "KPI Anomaly Watchdog"
description: "Stats detect KPI anomalies each morning (7-day baseline + z-scores); an AI agent explains each — critical alerts instantly, warnings in a digest."
date: 2026-10-09
category: "automation"
difficulty: "intermediate"
workflow: "/templates/kpi-anomaly-watchdog.json"
integrations: ["Google Sheets", "OpenAI", "Telegram", "Schedule Trigger"]
---

## How it works

A morning watchdog for your business numbers that separates detection from explanation — statistics find the anomalies, AI explains them:

1. **STEP 1 — Daily trigger + config + read KPIs** — a daily 8 AM schedule trigger fires, `CONFIG — Watchdog Settings` sets your thresholds and KPI columns, `CONFIG — Google Sheets` points at your spreadsheet, and `Read KPI Metrics` pulls every row from your `Metrics` tab.
2. **STEP 2 — Statistical anomaly detection (no AI)** — `Compute Anomaly Scores` builds a 7-day mean/std baseline per metric, then computes a z-score and day-over-day change. Metrics crossing your thresholds become `CRITICAL`, `WARNING`, or `WATCH`; quiet metrics emit nothing. This runs before any AI call, so quiet days cost you zero OpenAI tokens.
3. **STEP 3 — Log + AI explains** — each anomaly is appended to the `Anomalies` tab with status `NEW`, then `AI Agent — Explain Anomaly` explains it with a Structured Output Parser: plain-English summary, ranked probable causes (each with supporting evidence and where to check), one recommended action, and a confidence score. The sheet flips to `TRIAGED`.
4. **STEP 4 — Route by severity → Telegram** — `CRITICAL` anomalies fire an instant Telegram alert with the stats and the AI's explanation; `WARNING` anomalies are collected by `Build Warning Digest` into one daily digest message; `WATCH` anomalies stay in the audit sheet for your weekly review (flip those rows to `RESOLVED` manually once reviewed).

**Status flow in Sheets:** `NEW` → `TRIAGED` → `RESOLVED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2; a spreadsheet with two tabs: `Metrics` and `Anomalies` — [sheets.google.com](https://sheets.google.com)
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Your `Metrics` tab needs these headers (add your own KPI columns to the right if you track more):

`Date | Revenue | Orders | Ad Spend | Sessions`

Your `Anomalies` tab needs these headers (the workflow fills them; copy-paste this row):

`Anomaly ID | Date | Business | Metric | Latest Value | Previous Value | Baseline Mean | Baseline Std | Z-Score | DoD Change % | Direction | Severity | AI Summary | Probable Causes | Confidence | Recommended Action | Status`

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `kpi-anomaly-watchdog.json`.
2. **CONFIG — Watchdog Settings** — open the Set node and fill in:
   - `business_name` — your business name (appears in alerts)
   - `kpi_columns` — comma-separated **exact** headers of your numeric KPI columns (default: `Revenue,Orders,Ad Spend,Sessions`)
   - `warning_z` / `critical_z` — z-score thresholds (defaults: 2 / 3)
   - `warning_pct` / `critical_pct` — day-over-day % thresholds (defaults: 20 / 40)
   - `lookback_days` — baseline window in days (default: 7)
3. **CONFIG — Google Sheets** — paste your spreadsheet ID into `spreadsheet_id`, then select your Google Sheets OAuth2 credential in the three Sheets nodes. If you renamed the tabs, update `metrics_sheet_name` and `anomalies_sheet_name` in `CONFIG — Watchdog Settings` and the sheet names in the Sheets nodes to match.
4. **CONFIG — AI Analysis** — pick your model (`gpt-4o-mini` is the cost-efficient default), then select your OpenAI credential in the `OpenAI Chat Model — Anomaly Explainer` node.
5. **CONFIG — Notifications** — paste your Telegram chat ID into `telegram_chat_id`, select your Telegram credential in both Telegram nodes, and **activate** the workflow.

## Customize it

- **More KPIs** — add a column to the `Metrics` tab (e.g. `Refunds`, `Signups`, `CAC`) and append its exact header name to `kpi_columns`. The baseline math handles it automatically.
- **Smarter vs. quieter** — lower `warning_z` to 1.5 for early warning on volatile metrics, or raise `critical_pct` to 60 if day-over-day noise triggers too many critical alerts.
- **Richer explanations** — add context the agent can use (e.g. "we run weekly flash sales", "marketing spends peak on weekends") to the system message in `AI Agent — Explain Anomaly` — better context means sharper probable causes.
- **Watch-tier digest** — route the `WATCH` branch (the empty output of `IF — Severity is WARNING`) into a second digest node for a weekly Friday summary instead of relying on the sheet.
- **Auto-resolution** — add a second scheduled flow that flips `TRIAGED` rows to `RESOLVED` when the metric returns to baseline for 3 consecutive days.
- **Alert fatigue guard** — insert a dedupe step (like the job-hunt template's seen-URLs filter) so a multi-day anomaly only alerts once: skip metrics whose `Anomaly ID` already exists in the sheet with status `NEW` or `TRIAGED`.
