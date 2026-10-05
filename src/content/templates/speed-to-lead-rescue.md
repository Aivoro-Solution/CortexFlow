---
title: "Speed-to-Lead Rescue"
description: "Missed call or form lead? Instant SMS text-back, AI qualification, and a Telegram alert for hot leads — in under 60 seconds."
date: 2026-10-05
category: "automation"
difficulty: "intermediate"
workflow: "/templates/speed-to-lead-rescue.json"
integrations: ["Twilio", "OpenAI", "Google Sheets", "Telegram", "Webhooks"]
---

## How it works

1. **Webhook — Lead Intake catches every lead** — missed-call events (Twilio/VAPI) or any web form POST a JSON payload `{name, phone, email, message, source}` to `/lead-in`.
2. **Normalize Lead cleans the input** — trims whitespace and strips non-dialable characters from the phone number, so every downstream step gets consistent data.
3. **CONFIG — Lead Business holds your settings** — business name, Twilio number, Telegram chat ID, sheet ID, booking link, hot-score threshold, SMS template, and services list in one editable node.
4. **Log Lead — Status NEW writes to Google Sheets** — one row per lead with status `NEW` and empty score/priority columns.
5. **Send Welcome SMS — Twilio fires the instant text-back** — the lead gets your welcome SMS within ~60 seconds of their missed call or form submit, before they call a competitor.
6. **Update Sheet — Status CONTACTED flips the status** — the row moves from `NEW` to `CONTACTED` the moment the SMS goes out.
7. **AI Agent — Qualify Lead scores the lead** — GPT-4o-mini reads the lead's message and business context, then returns a strict structured verdict through the Structured Output Parser: `lead_score` 0–100, `urgency` HOT / WARM / COLD, `summary`, `suggested_next_step`, `best_contact_time`.
8. **Parse Qualification flattens the AI output** — pulls the score, urgency, summary, next step, and contact time into clean fields for the rest of the flow.
9. **Update Sheet — Status QUALIFIED fills in the row** — the sheet row moves to `QUALIFIED` with `lead_score`, `priority` (HOT / WARM / COLD), and `ai_summary` filled in.
10. **IF — Hot Lead? routes the flow** — leads scoring at or above `HOT_SCORE_THRESHOLD` (75) go down the hot path; everything else continues quietly.
11. **Telegram — Hot Lead Alert pings you instantly** — 🔥 owner alert with name, score, phone, summary, and next step so you can call back immediately.
12. **Merge — Combine Branches rejoins the paths** — hot and non-hot leads merge back into one stream.
13. **Telegram — Lead Summary sends the final recap** — name, phone, source, status, priority, score, summary, next step, and best contact time in one Telegram message.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- A Twilio account — sign up for a free trial at https://www.twilio.com/try-twilio (gives you a phone number, an Account SID, and an Auth Token)
- An OpenAI account — get an API key at https://platform.openai.com/signup (used with the `gpt-4o-mini` model)
- A Telegram bot — create one with BotFather at https://t.me/BotFather (send `/newbot`, copy the token) and get your chat ID
- A Google account with a Google Sheet — create the sheet with a Google Sheets OAuth2 credential in n8n

1. **Create your Google Sheet** — make a sheet named `Leads` with exactly these column headers in row 1: `timestamp`, `name`, `phone`, `email`, `message`, `source`, `status`, `lead_score`, `priority`, `ai_summary`. Share it with the Google service account n8n uses.
2. **Download the workflow JSON** using the download button on this page.
3. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
4. **Create your Twilio credential** — in n8n go to *Credentials → New → HTTP Basic Auth*, use your Twilio **Account SID as the username** and your Twilio **Auth Token as the password**, save. Then open *Send Welcome SMS — Twilio* and select this credential; replace `PASTE_YOUR_TWILIO_ACCOUNT_SID` in the request URL with your real Account SID.
5. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Open *OpenAI Chat Model — Qualify* and select it.
6. **Create your Google Sheets credential** — complete OAuth2 for Google Sheets, then open *Log Lead — Status NEW*, *Update Sheet — Status CONTACTED*, and *Update Sheet — Status QUALIFIED* and select it.
7. **Create your Telegram credential** — in n8n go to *Credentials → New → Telegram*, paste your bot token, save. Open *Telegram — Hot Lead Alert* and *Telegram — Lead Summary* and select it.
8. **Fill in CONFIG — Lead Business** — open the node and replace every placeholder: `BUSINESS_NAME`, `TWILIO_FROM_NUMBER` (your Twilio number), `OWNER_TELEGRAM_CHAT_ID`, `SHEET_DOC_ID` (the sheet's ID from its URL), `BOOKING_LINK`, and `SERVICES_LIST`. Adjust `HOT_SCORE_THRESHOLD` (default 75) and `WELCOME_SMS_TEMPLATE` to taste.
9. **Activate** the workflow (toggle, top-right), then test with: `curl -X POST https://YOUR-N8N-DOMAIN/webhook/lead-in -H 'Content-Type: application/json' -d '{"name":"Ravi Sharma","phone":"+15551234567","email":"ravi@example.com","message":"AC stopped working, need someone today","source":"missed-call"}'`. You should get the SMS on the test phone, a new `QUALIFIED` row in your sheet, and two Telegram messages.

Approval note: this workflow sends SMS automatically to anyone who submits a lead. Before going live, point it at your own phone number and confirm the welcome message, timing, and qualification verdicts look right — and check that your Twilio sender number is allowed to message your market's numbers (some countries require registered sender IDs).

## Customize it

- **Business-hours gating** — add an IF node after *Normalize Lead* that checks the current hour (e.g. 9:00–19:00): during hours, keep the instant-SMS path; outside hours, swap the body to an "after hours" template that promises a morning callback. Edit `WELCOME_SMS_TEMPLATE` or add a second template in the CONFIG node.
- **Swap the SMS provider** — replace *Send Welcome SMS — Twilio* with any other sender: a Vonage/Msg91 HTTP Request node (same form-body shape), or n8n's native Twilio node if you prefer the UI over the raw API call.
- **Second follow-up workflow** — build a companion workflow on a Schedule Trigger (daily, e.g. 10:00): read the sheet for rows stuck at `CONTACTED` for 24h+ without a `QUALIFIED` outcome, send a gentle follow-up SMS ("Still need help with…? Reply YES and I'll call you in 10 minutes"), then flip status to `FOLLOWED_UP`.
- **Tune the hot threshold** — if you're drowning in 🔥 alerts, raise `HOT_SCORE_THRESHOLD` in the CONFIG node to 85; if you're missing good jobs, drop it to 65.
