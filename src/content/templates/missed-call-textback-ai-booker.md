---
title: "Missed-Call Text-Back AI Booker"
description: "Missed call → instant SMS in seconds → AI agent classifies replies and books jobs straight into Google Calendar. Import-ready n8n workflow."
date: 2026-10-15
category: "automation"
difficulty: "intermediate"
workflow: "/templates/missed-call-textback-ai-booker.json"
integrations: ["Twilio", "OpenAI", "Google Calendar", "Google Sheets", "Telegram"]
---

## How it works

Your AI receptionist that never lets a missed call go cold:

1. **STEP 1 — Twilio webhook + instant response** — a missed-call status callback or inbound SMS hits the "Twilio Incoming (Missed Call / SMS)" webhook. "Respond Empty TwiML" answers Twilio immediately with an empty `<Response/>`, then "Normalize Twilio Payload" turns the form-encoded params into a standard lead event (`event_type`: `missed_call` or `sms`).
2. **STEP 2 — Config + 24h dedupe** — two Config Set nodes ("CONFIG — Business Settings", "CONFIG — AI + Services") hold every editable value: business name, owner phone, Twilio number, calendar ID, AI business profile, model. For missed calls, the log is read first — if this caller was already texted in the last 24h, the run stops (no double-texting).
3. **STEP 3 — Instant text-back + logging** — a new missed call is appended to the sheet with status `NEW`, a friendly SMS goes out via the Twilio Messages API ("Sorry we missed your call…"), and the sheet flips to `CONTACTED`.
4. **STEP 4 — AI classifies the reply** — inbound SMS rebuilds the conversation history from the Sheets log ("Build History Array"), then "AI Agent — Classify + Draft Reply" (gpt-4o-mini) with the "Structured Output Parser — Intent + Reply" returns `{intent, summary, missing_fields, suggested_reply}`. Intents: `booking`, `quote`, `existing_job`, `wrong_number`, `other`.
5. **STEP 5 — Booking branch** — intent `booking` with zero missing fields → "Google Calendar — Create Booking" → confirmation SMS → sheet `BOOKED` → "Telegram — Owner Alert" pings you a one-line summary. Missing details → the AI's follow-up question is texted and the sheet flips to `REPLIED`.
6. **STEP 6 — Quote / wrong-number branches** — `quote` gets a quote-capture SMS (`REPLIED`); `wrong_number` gets a polite close (`DROPPED`); `existing_job` / `other` get the AI's friendly acknowledgement (`REPLIED`).
7. **STEP 7 — Daily no-reply sweeper** — a second flow in the same workflow ("Daily No-Reply Sweeper", every 2 hours) scans for `CONTACTED` rows older than 2h with no reply → sends exactly one nudge SMS → marks `NUDGED`.

**Status flow in Sheets:** `NEW` → `CONTACTED` → `REPLIED` → `BOOKED` (plus `DROPPED`, `NUDGED`)

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Twilio account with a phone number — [twilio.com/try-twilio](https://www.twilio.com/try-twilio) (free trial works; set the number's voice status-callback URL and SMS webhook to this workflow's production URL)
- An OpenAI API key — [platform.openai.com/signup](https://platform.openai.com/signup) → API keys
- Google Sheets + Google Calendar OAuth2 credentials — n8n Credentials → Google Sheets OAuth2 / Google Calendar OAuth2
- A Telegram bot — [telegram.org](https://telegram.org) → message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `missed-call-textback-ai-booker.json`.
2. **CONFIG — Business Settings** — open the Set node and fill in:
   - `business_name` — e.g. `Acme Plumbing`
   - `owner_phone` — your phone in E.164 format (e.g. `+1555…`)
   - `twilio_number` — your Twilio number in E.164 format
   - `calendar_id` — your Google Calendar ID (Calendar settings → "Integrate calendar")
   - `nudge_hours` — how long before the sweeper nudges a silent lead (default `2`)
3. **CONFIG — AI + Services** — open the Set node and fill in:
   - `spreadsheet_id` — the Google Sheet ID
   - `sheet_name` — tab name (default `Leads`)
   - `twilio_account_sid` — from your [Twilio console](https://www.twilio.com/console)
   - `openai_model` — `gpt-4o-mini` by default
   - `telegram_chat_id` — your Telegram chat ID
   - `ai_business_profile` — describe your services, prices, hours, and booking rules — the AI receptionist's whole brain lives here
4. **Create the sheet** — in your Google Sheet, make a tab named `Leads` with exactly these headers: `Date | Phone | Name | Status | Last Message | Conversation | Intent | Booking Date | Summary | Last Updated`. Then select your Google Sheets credential in all ten Sheets nodes (or use the credential prompt on import).
5. **Twilio auth** — in each "Send * SMS" HTTP node, select your **HTTP Header Auth** credential. Set the header name to `Authorization` and the value to `Basic <base64(AccountSID:AuthToken)>` (encode it once with any base64 tool; the workflow never stores your SID/token in the JSON).
6. **Twilio webhooks** — in the [Twilio console](https://www.twilio.com/console) → your number → Voice: set the **Status Callback URL** to this workflow's production webhook URL (POST); Messaging: set **"A message comes in"** to the same URL (POST).
7. **Google Calendar + OpenAI + Telegram** — select your Google Calendar credential in "Google Calendar — Create Booking", your OpenAI credential in "OpenAI Chat Model — Booker", and your Telegram credential in "Telegram — Owner Alert". Then **activate** the workflow.

## Customize it

- **Business tone** — rewrite the instant SMS in "Send Instant SMS — Sorry We Missed You" and the nudge in "Send Nudge SMS" to match your brand voice; keep them short and human.
- **Booking requirements** — edit the `ai_business_profile` in "CONFIG — AI + Services" to list exactly what a booking needs (name, address, preferred day/time); the AI only books when `missing_fields` is empty, so this text is your real booking form.
- **Dedupe window** — "Check 24h Dedupe" skips callers texted within the last 24h; the sweeper's quiet window is `nudge_hours` in "CONFIG — Business Settings". Tighten or loosen both for your call volume.
- **Quote handling** — the quote branch just captures interest today. Route it into a CRM or a pricing sheet by swapping "Send Quote-Capture SMS"'s follow-on node.
- **Quiet hours** — add a schedule-aware IF before the SMS nodes if you don't want 2 AM texts going out; queue them for morning instead.
- **Sell it** — this is the classic $1.5–3K-setup agency product: clone the workflow per client, swap the two CONFIG nodes, point their Twilio number at it, done.
