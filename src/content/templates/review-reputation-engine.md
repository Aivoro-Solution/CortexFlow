---
title: "Review & Reputation Engine"
description: "Auto-request reviews 2 days after service, route low ratings to support, and monitor Google reviews daily. Import-ready n8n workflow."
date: 2026-10-04
category: "automation"
difficulty: "beginner"
workflow: "/templates/review-reputation-engine.json"
integrations: ["Gmail", "Google Business Profile", "Slack", "OpenAI", "Google Sheets"]
---

## How it works

Your always-on reputation assistant — two independent flows in one workflow:

1. **STEP 1 — Job completed → 2-day wait → review request** — a POST webhook (`/job-completed`, with `customer_name`, `email`, `phone`, `job_id`) logs the job to Google Sheets with status `REQUEST_PENDING`, replies OK immediately, then waits 2 days and emails the customer 5 clickable star links.
2. **STEP 2 — Rating webhook → smart routing** — clicking a star hits the GET `/rate` webhook (`?job_id=…&stars=…`). The rating is parsed, matched to the sheet row, and routed: **1–3 stars** → Slack alert to your support channel + sheet flips to `FLAGGED`; **4–5 stars** → Gmail sends your Google review link + sheet flips to `REVIEW_ASKED`. Both branches merge into a Flow-A summary.
3. **STEP 3 — Daily Google Business Profile monitoring** — every morning at 8 AM the workflow lists your latest GBP reviews via the Google Business Profile API, drops the ones already logged, and for each new review an AI Agent classifies sentiment (positive / neutral / negative) via a Structured Output Parser, posts an alert to Slack with a suggested public reply, and appends it to the sheet as `LOGGED`. No new reviews → the flow ends quietly.
4. **STEP 4 — Sheets logging + Telegram digest** — both flows feed one digest: new Google reviews with sentiment counts, plus review-request stats (pending / asked / flagged) read from Sheets. It lands in Telegram every morning, and after every rating event.

**Status flow in Sheets:** `Review Requests` tab: `REQUEST_PENDING` → `REVIEW_ASKED` / `FLAGGED` · `GBP Reviews` tab: new → `LOGGED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Gmail account — n8n Credentials → Gmail OAuth2 ([Google Cloud Console](https://console.cloud.google.com) to create the OAuth client if you don't have one)
- Google Business Profile API access — enable the **My Business API** in [Google Cloud Console](https://console.cloud.google.com), then generate a token at the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground) (refresh it monthly)
- Your Google review link — Google Business Profile → get the "share review form" link for happy customers
- A Slack workspace — create an app at [api.slack.com/apps](https://api.slack.com/apps) and add the n8n Slack credential
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credential + one spreadsheet with two tabs: `Review Requests` and `GBP Reviews`
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `review-reputation-engine.json`.
2. **Create the `Review Requests` tab** — headers exactly: `Date | Job ID | Customer | Email | Rating | Status`. Create the **`GBP Reviews` tab** — headers exactly: `Date | Review ID | Reviewer | Stars | Text | Sentiment | Status`.
3. **CONFIG — Review Flow** — open the Set node and fill in:
   - `business_name` — your business name as customers know it
   - `rating_webhook_base_url` — your n8n webhook base URL (e.g. `https://your-n8n/webhook`) — the star links are built from this
   - `google_review_url` — the Google review link from your Business Profile
   - `support_slack_channel` — e.g. `#support`
   - `spreadsheet_id` — the ID from your sheet's URL
4. **CONFIG — GBP** — paste your `gbp_access_token` (OAuth playground token), `gbp_account_id`, `gbp_location_id`, and the same `spreadsheet_id`. Select your Google Sheets credential in all six Sheets nodes.
5. **Connect your job-completed source** — point your booking/CRM system at the `Job Completed` webhook URL with JSON body `{"customer_name": "…", "email": "…", "phone": "…", "job_id": "…"}`. Test it once and confirm a `REQUEST_PENDING` row appears.
6. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential; select your OpenAI credential in the chat model node, Gmail credential in both Gmail nodes, Slack credential in both Slack nodes. **Activate** the workflow (the schedule trigger and both webhooks).

## Customize it

- **Different wait time** — change the `Wait 2 Days` node to 1 day, 7 days, or anything else; service businesses with longer jobs may want more breathing room.
- **Rating threshold** — the `IF — Rating < 4?` node routes 1–3 stars to support; tighten it to `< 5` if you want every non-perfect rating flagged.
- **SMS instead of email** — swap the `Send Review Request` Gmail node for a Twilio/WhatsApp node; the star links work in any channel.
- **Auto-reply to reviews** — the AI already drafts a `suggested_reply`; add a GBP "reply to review" HTTP call after `Post Review Alert` to publish it automatically (review it manually first — auto-replies can backfire).
- **More review sites** — duplicate STEP 2's happy path to also send Trustpilot/Yelp links based on the customer's country.
- **Weekly digest instead of daily** — change the schedule trigger interval; the Sheets-based stats keep working at any cadence.
