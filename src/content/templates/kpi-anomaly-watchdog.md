---
title: "KPI Anomaly Watchdog"
description: "Your metrics, watched daily: z-score anomaly detection on any KPI in Google Sheets, AI-written explanations, and instant Telegram alerts."
date: 2026-10-05
category: "automation"
difficulty: "intermediate"
workflow: "/templates/kpi-anomaly-watchdog.json"
integrations: ["OpenAI", "Google Sheets", "Telegram", "n8n"]
---

## How it works

1. **Daily Check fires every 24 hours** — a Schedule Trigger that wakes the workflow once a day. Change the interval in the trigger node if you want hourly checks on fast-moving metrics.
2. **CONFIG — Watchdog holds every tunable** — the metrics you watch, z-score thresholds (`z_warn` 2.0 / `z_crit` 3.0), minimum baseline samples (7), minimum relative move (10%), baseline window (14 days), and your Telegram chat ID. One node, no hunting through the canvas.
3. **Read Metric History pulls your KPI log** — reads the `metrics_history` sheet, which has exactly three columns: `date`, `metric`, `value`. One row per metric per day. Append-only; the workflow never writes here.
4. **Detect Anomalies scores today against the trailing baseline** — a Code node groups rows by metric, takes the last 14 days *excluding today* as the baseline, and computes the z-score of today's value: how many standard deviations it sits from its own recent normal. Guards: skips metrics with fewer than 7 baseline points, skips flat baselines (standard deviation of zero makes z-scores meaningless), and ignores moves under 10% so tiny wiggles on big numbers don't page you.
5. **Any Anomalies? routes on the count** — if nothing crossed the warning threshold, the run ends quietly. No "all clear" spam.
6. **Expand Anomalies fans out one item per anomaly** — so the AI explanation and the alert run once for each flagged metric, not once for the whole batch.
7. **AI Agent — Explain Anomaly writes the diagnosis** — GPT-4o-mini reads the metric, the size and direction of the move, and the baseline stats, then returns a strict structured verdict through the Structured Output Parser: a plain-English `explanation`, `likely_causes`, `suggested_checks`, and whether a human `needs_human` eyes on it.
8. **Format Alert builds the message** — severity emoji (🚨 CRITICAL / ⚠️ WARNING), metric, direction, percentage move, z-score, the AI explanation, likely causes, and first checks — in one Telegram-ready text.
9. **Telegram — Anomaly Alert pings you** — one message per anomaly, straight to your chat.
10. **Log Anomaly appends the audit trail** — every flagged anomaly lands in the `anomaly_log` sheet with timestamp, values, z-score, severity, and the AI explanation, so you can review the week's hits every Monday and tune thresholds with evidence.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Google account with two sheets in one spreadsheet: `metrics_history` and `anomaly_log`
- An OpenAI account — get an API key at https://platform.openai.com/signup (used with the `gpt-4o-mini` model)
- A Telegram bot — create one with BotFather at https://t.me/BotFather (send `/newbot`, copy the token) and get your chat ID

1. **Create the `metrics_history` sheet** — column headers in row 1, exactly: `date`, `metric`, `value`. Dates as `YYYY-MM-DD`. Example rows:
   - `2026-10-01 | daily_revenue | 1240.50`
   - `2026-10-01 | new_signups | 38`
   - `2026-10-02 | daily_revenue | 1189.00`
   Add at least 8 days of history per metric before the first run — the detector needs 7 baseline points minimum.
2. **Create the `anomaly_log` sheet** — headers in row 1: `time`, `metric`, `date`, `latest_value`, `baseline_mean`, `z_score`, `severity`, `direction`, `ai_explanation`.
3. **Download the workflow JSON** using the download button on this page.
4. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
5. **Create your Google Sheets credential** — complete OAuth2 for Google Sheets, then open *Read Metric History* and *Log Anomaly* and select it (pick the spreadsheet; the sheet names are already set).
6. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Open *OpenAI Chat Model — Explainer* and select it.
7. **Create your Telegram credential** — in n8n go to *Credentials → New → Telegram*, paste your bot token, save. Open *Telegram — Anomaly Alert* and select it.
8. **Fill in CONFIG — Watchdog** — replace `PASTE_YOUR_TELEGRAM_CHAT_ID` with your chat ID, and edit the `metrics` list to the metric names you actually log.
9. **Feed it history, then activate** — backfill at least 8 days per metric, toggle the workflow active, and run once manually. With healthy data you should see the run end at *Any Anomalies?* with zero alerts. To test the alert path, temporarily add a row with an obviously wrong value (e.g. revenue of `1`), run manually, and confirm the Telegram message reads sensibly — then delete the test row.

Approval note: thresholds are a judgment call, not a default. `z_warn: 2.0` pages on moves that happen ~5% of the time by pure chance; if you watch 10 metrics daily, expect a warning every couple of days at first. Run a week, read the `anomaly_log`, and only then decide whether to tighten or loosen. Start strict, loosen with evidence.

## Customize it

- **Per-metric thresholds** — revenue deserves a tighter leash than vanity metrics. Duplicate the *Detect Anomalies* Code node per metric group, or extend CONFIG with a `strict_metrics` list and branch on it in the Code node.
- **Pull metrics automatically** — replace the Sheets read with HTTP Request nodes: Stripe's `/v1/charges` for revenue, GA4's Data API for sessions, Shopify's orders endpoint. Write the fetched values into `metrics_history` with a second workflow (or a branch in this one) so the detector stays source-agnostic.
- **Day-of-week seasonality** — weekend dips trip naive z-scores. Either maintain separate baselines per weekday in the Code node, or add a `dow` column and filter the baseline to matching weekdays.
- **Escalation digest** — instead of one Telegram message per anomaly, collect the day's anomalies and send a single 08:00 digest. Move *Format Alert* after a Merge that gathers all items, and join the texts.
- **Slack instead of Telegram** — swap the Telegram node for n8n's Slack node; the alert text needs no changes.
