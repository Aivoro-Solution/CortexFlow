---
title: "Appointment Waitlist Backfill: Fill Cancelled Slots Automatically"
description: "A cancellation triggers waitlist scoring, WhatsApp/SMS offers to top candidates, first-TAKE-wins booking, and full status logging in Google Sheets."
date: 2026-10-06
category: "automation"
difficulty: "intermediate"
workflow: "/templates/appointment-waitlist-backfill.json"
integrations: ["Webhook", "Google Sheets", "Telegram", "WhatsApp/SMS", "Code"]
---

## How it works

Your 24/7 receptionist for cancelled appointments — no slot ever goes to waste:

1. **STEP 1 — Cancellation intake + config** — your booking system POSTs the freed slot (`appointment_id`, `slot_time`, `service`) to the `waitlist-cancel` webhook. The workflow loads your rules from **CONFIG — Waitlist Rules**, normalizes the payload, and logs it to the Offers tab with status `NEW`.
2. **STEP 2 — Deterministic scoring + ranking** — the waitlist is read from Google Sheets and every candidate is scored by a Code node (no black-box AI): days waiting × your weight, minus a no-show penalty, plus loyalty and priority-flag bonuses. The top N candidates are logged with status `RANKED`.
3. **STEP 3 — AI offer copy + send** — an AI Agent writes a warm, personalized offer message for each candidate (Structured Output, `gpt-4o-mini`), the reply instruction ("Reply TAKE within 120 minutes") is appended deterministically, and the message goes out through the demo HTTP node pointed at your WhatsApp/SMS provider. Rows flip to `OFFER_SENT` and you get a Telegram summary of who was contacted.
4. **STEP 4 — Reply-window expiry sweep** — a Wait node pauses for your configurable reply window, then the Offers tab is re-read: any still-open offer is marked `EXPIRED` and you get the window-closed summary on Telegram.
5. **STEP 5 — Reply handling (first TAKE wins)** — a second webhook, `waitlist-reply`, receives `{phone, message}` from your messaging provider. The reply is normalized, matched to the latest still-open offer for that phone, the winner flips to `BOOKED`, and every other open offer for that slot flips to `EXPIRED`. You get a Telegram alert naming the winner.
6. **STEP 6 — Owner notifications** — Telegram messages at every stage: offers sent, window closed, slot booked, and unmatched-reply alerts for messages that don't match any open offer.

**Status flow in Sheets:** `NEW` → `RANKED` → `OFFER_SENT` → `BOOKED` / `EXPIRED`

## Set up steps

You'll need:

- n8n (self-hosted or [cloud](https://n8n.io))
- A Google account — create a spreadsheet with two tabs (headers below), then n8n Credentials → Google Sheets OAuth2 API
- A WhatsApp/SMS provider — [Twilio](https://www.twilio.com) (WhatsApp + SMS), [360dialog](https://www.360dialog.com) (WhatsApp Business API), or [WATI](https://www.wati.io)
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- (Optional) An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys, for the AI-written offer copy

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `appointment-waitlist-backfill.json`.
2. **Create the Google Sheet** — two tabs with these exact headers:
   - `Waitlist`: `Name | Phone | Service | Wait Since | No Shows | Visits | Priority` (add your waitlisted clients; `Wait Since` as a date, `Priority` as YES/blank)
   - `Offers`: `Appointment ID | Slot Time | Service | Name | Phone | Score | Status | Offer Sent At | Offer Expires At | Reply At` (the workflow fills this; leave it empty)
3. **CONFIG — Waitlist Rules** — open the Set node and fill in:
   - `business_name` — shown in the AI-written offer messages
   - `spreadsheet_id` — from your sheet's URL; leave `waitlist_tab` / `offers_tab` as-is unless you renamed the tabs
   - `offer_count` — how many candidates get the offer (3 is a good start)
   - `reply_window_minutes` — how long a candidate has to reply (120 = 2 hours)
   - `reply_keyword` — the word that claims the slot (`TAKE`)
   - `weight_wait_day`, `weight_no_show`, `weight_visit_loyalty`, `weight_priority_flag`, `min_score` — tune the scoring to your business
   - `message_provider_url`, `message_api_token`, `sender_id` — your WhatsApp/SMS provider's send-message endpoint and credentials
   - `telegram_chat_id` — where owner alerts go
4. **Credentials** — select your Google Sheets OAuth2 credential in all eight Sheets nodes, your Telegram credential in the four Telegram nodes, and your OpenAI credential in **OpenAI Chat Model — Offer Copy**. Then **activate** the workflow and copy both webhook URLs (n8n shows the production URLs once active).
5. **Wire up your booking system** — POST cancellations to the `waitlist-cancel` URL with JSON body: `{"appointment_id": "APT-123", "slot_time": "2026-10-07 14:00", "service": "Dental Cleaning"}`.
6. **Wire up replies** — point your messaging provider's inbound webhook at the `waitlist-reply` URL so incoming messages arrive as `{"phone": "+919876543210", "message": "TAKE"}`. (Twilio: Messaging Service → Inbound Settings; 360dialog/WATI: webhook URL in the dashboard.)

## Customize it

- **Real provider payloads** — **HTTP — Send Offer (Demo Provider)** is a clearly-marked placeholder: it POSTs `{to, from, text}` with a Bearer token. Swap the URL/body to match your provider's API (e.g. Twilio's `Messages.json` endpoint or 360dialog's `/v1/messages`) — nothing downstream changes.
- **Scoring weights** — a salon might crank `weight_visit_loyalty` to reward regulars; a clinic might raise `weight_wait_day` so the longest-waiting patient always wins. `weight_no_show` is negative on purpose: chronic no-shows sink to the bottom.
- **Service matching** — candidates are only offered slots matching their `Service` column (blank = any service). Delete that filter in **Code — Score & Rank Waitlist** if your waitlist is service-agnostic.
- **Skip the AI copy** — don't want the OpenAI call? Delete the AI Agent and its two sub-nodes, and connect **Sheets — Log Ranked (RANKED)** straight to **Code — Build Offer Message**: the fallback template message still works.
- **Tighter reply windows** — 120 minutes suits clinics and salons; for same-day slots, drop `reply_window_minutes` to 30. Note the cancellation webhook's response waits for the window to close (responseMode `lastNode`) — use a short window while testing.
- **Escalation ladder** — instead of offering all N candidates at once, chain the flow: offer candidate #1, wait 30 minutes, and only if unclaimed, offer candidate #2. Duplicate the STEP 3–4 block with `offer_count` = 1 and an IF on the BOOKED status.
