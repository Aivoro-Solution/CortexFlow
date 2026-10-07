---
title: "Agency Ad Report Automation — Meta + Google Ads + GA4 Weekly Client Reports"
description: "Meta + Google Ads + GA4 pulled every Monday, AI-written plain-language summary, branded HTML client email, full Sheets audit trail. Import-ready n8n workflow."
date: 2026-10-07
category: "automation"
difficulty: "advanced"
workflow: "/templates/agency-ad-report-automation.json"
integrations: ["meta-ads", "google-ads", "google-analytics-4", "google-sheets", "gmail", "telegram", "openai"]
---

## How it works

Your Monday-morning reporting assistant: every Monday at 8 AM it pulls last week's numbers from Meta Ads, Google Ads, and GA4, computes blended totals, has an AI analyst write a plain-language client summary, emails a branded HTML report to the client, and drops a digest in your Telegram — with every stage logged to Google Sheets:

1. **STEP 1 — Monday trigger + config** — `Weekly Monday 8AM Trigger` fires, `CONFIG — Report` supplies the client name, sheet ID, client email, Telegram chat ID, and brand color, and `Sheets — Log RUN_STARTED` opens the audit trail.
2. **STEP 2 — Pull three platforms in parallel** — `CONFIG — API Access` holds every token and ID as `PASTE_YOUR_*` placeholders, feeding three HTTP requests: `Meta Ads — Pull Insights` (Graph API: impressions, clicks, spend, actions), `Google Ads — Pull GAQL` (campaign cost, clicks, conversions), and `GA4 — Pull Conversions` (Data API: conversions and revenue by channel).
3. **STEP 3 — Blend + sanity check** — `Merge — Ads Platforms` and `Merge — All Channels` combine the three responses, then `IF — Any Data?` verifies at least one platform returned rows. Empty data takes the failure branch: `Sheets — Log REPORT_FAILED` records it and `Telegram — Failure Alert` pings you, so a silent miss never happens.
4. **STEP 4 — Totals + AI summary** — `Compute Totals` blends everything into total spend, clicks, impressions, conversions, revenue, ROAS, CTR, and CPA, and the sheet flips to `DATA_FETCHED`. `AI Agent — Write Ad Summary` (gpt-4o-mini with `Structured Output Parser — Summary`) returns `standout_metric`, `risk`, `recommendation`, and a 60-second `summary`, and the sheet flips to `SUMMARY_GENERATED`.
5. **STEP 5 — Report + delivery** — `Build Report HTML` assembles the branded email, the sheet flips to `REPORT_SENT`, `Gmail — Send Client Report` emails the client, and `Telegram — Run Digest` posts the totals plus the AI take to the agency.

**Status flow in Sheets:** `RUN_STARTED` → `DATA_FETCHED` → `SUMMARY_GENERATED` → `REPORT_SENT` (or `REPORT_FAILED` on empty data)

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Meta app with Marketing API access — [developers.facebook.com](https://developers.facebook.com/) → create an app, add the Marketing API product, generate a token with `ads_read`
- Google Ads API access — [developers.google.com/google-ads/api/docs/first-call/overview](https://developers.google.com/google-ads/api/docs/first-call/overview) → apply for a developer token, set up OAuth for the customer ID
- GA4 Data API access — [developers.google.com/analytics/devguides/reporting/data/v1](https://developers.google.com/analytics/devguides/reporting/data/v1) → service account or OAuth with `analytics.readonly`
- An OpenAI API key — [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Google Sheets + Gmail OAuth2 credentials — n8n Credentials → Google Sheets OAuth2 / Gmail OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `agency-ad-report-automation.json`.
2. **CONFIG — Report** — open the Set node and fill in:
   - `client_name` — e.g. `Acme Corp` (used in the report header and emails)
   - `gsheet_id` — paste your Google Sheet ID
   - `sheet_tab` — the log tab name (default `Report Log`)
   - `client_email` — where the HTML report is sent
   - `telegram_chat_id` — your agency chat for the run digest
   - `brand_color` — hex for the report header (default `#FF4D00`)
   - `lookback_days` — reporting window (default `7`)
3. **Report Log sheet** — create a Google Sheet with a tab named `Report Log` and headers: `timestamp | client_name | stage | detail`. The five Sheets nodes (`Sheets — Log RUN_STARTED`, `DATA_FETCHED`, `SUMMARY_GENERATED`, `REPORT_SENT`, `REPORT_FAILED`) read `gsheet_id` and `sheet_tab` from `CONFIG — Report`; select your Google Sheets OAuth2 credential in each one.
4. **CONFIG — API Access** — paste the six values: `meta_access_token`, `meta_ad_account_id`, `google_ads_customer_id`, `google_ads_developer_token`, `google_oauth_token`, `ga4_property_id`.
5. **CONFIG — AI** — the model is `gpt-4o-mini` by default; select your OpenAI credential in `OpenAI Chat Model — Summary`.
6. **Connect Gmail + Telegram** — select your Gmail OAuth2 credential in `Gmail — Send Client Report`, and your Telegram Bot API credential in `Telegram — Run Digest` and `Telegram — Failure Alert`.
7. **Test, then activate** — run once manually, confirm the sheet shows `RUN_STARTED` → `DATA_FETCHED` → `SUMMARY_GENERATED` → `REPORT_SENT`, check the client email renders, then activate the workflow.

> **Note:** the template authenticates Google Ads and GA4 with a plain OAuth access-token placeholder (`google_oauth_token`). Google access tokens expire after about an hour, so for production either refresh the token before each run (an n8n Google OAuth2 credential plus a token-refresh step) or wire the two nodes to your own OAuth flow. Meta tokens are long-lived by comparison — generate a long-lived user token in the App Dashboard. GA4 `totalRevenue` only populates if purchase events are firing on the property.

## Customize it

- **Multi-client loop** — keep a `Clients` sheet (name, IDs, emails) and wrap the flow in a Split In Batches loop so one run reports for every retainer client.
- **Week-over-week deltas** — store each week's totals in a second tab and add a Code node that computes spend/ROAS deltas before the AI step; the summary gets much sharper with a trend to react to.
- **Add TikTok or LinkedIn Ads** — duplicate one HTTP pull node, extend `Compute Totals` with the new platform's fields, and add a row to the report table.
- **PDF attachment** — add an HTML-to-PDF step (e.g. a Convert to File or an external API) between `Build Report HTML` and Gmail for clients who file reports.
- **Slack instead of Telegram** — swap the two Telegram nodes for Slack nodes; the digest text works unchanged.
- **Client Q&A** — add a Gmail Trigger + a second AI Agent so clients can reply to the report with questions and get answers from the same week's data.
