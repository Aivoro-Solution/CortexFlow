---
title: "WhatsApp Appointment Booking + Recall"
description: "WhatsApp AI books appointments via Google Calendar and winbacks inactive customers automatically. Import-ready n8n workflow."
date: 2026-10-04
category: "automation"
difficulty: "intermediate"
workflow: "/templates/whatsapp-appointment-booking.json"
integrations: ["WhatsApp", "OpenAI", "Google Calendar", "Google Sheets"]
---

## How it works

Your AI receptionist on WhatsApp, running two independent flows in one workflow:

1. **STEP 1 — WhatsApp trigger + AI intent parsing** — every incoming WhatsApp message fires the workflow, gets logged to Google Sheets with status `RECEIVED`, and an AI Agent classifies the intent (`book` / `cancel` / `reschedule` / `other`) through a Structured Output Parser, extracting the customer name, preferred date/time, and notes. A Switch routes the conversation by intent.
2. **STEP 2 — Calendar availability + booking** — for `book`, the workflow builds a ±1 hour availability window around the requested time, fetches overlapping Google Calendar events, and a Code node decides if the slot is free. If free: the event is created, the sheet flips to `BOOKED`, and the customer gets a WhatsApp confirmation. If busy: three alternative 1-hour slots are computed and suggested on WhatsApp, and the sheet flips to `PENDING_SLOT`. If the AI couldn't parse a date/time, WhatsApp asks the customer for one instead of guessing.
3. **STEP 3 — Cancel / reschedule / fallback** — for `cancel`, the customer's upcoming event is found (sender's phone number in the event description first, then name in the summary), deleted from Google Calendar, the sheet flips to `CANCELLED`, and WhatsApp confirms. For `reschedule`, WhatsApp asks for the new preferred time and the sheet flips to `RESCHEDULE_REQUESTED` — the customer's reply re-enters the booking flow. For `other`, a fallback reply explains the BOOK / CANCEL / RESCHEDULE commands and the sheet flips to `HANDLED`.
4. **STEP 4 — Weekly inactive-customer recall** — every Monday at 10 AM the workflow reads your Customers tab, keeps customers whose last visit is 60+ days ago, sends each a WhatsApp re-engagement message with your offer, flips the sheet to `RECALLED` with today's contact date, and sends you a Telegram digest. Note: Meta requires an approved message template for business-initiated WhatsApp messages — keep the text simple and approve it in WhatsApp Manager first.
5. **STEP 5 — Sheets logging + Telegram digests** — every booking branch merges into one booking summary sent to Telegram, and the weekly recall builds its own digest. Both read the chat ID from a single CONFIG node.

**Status flow (Bookings tab):** `RECEIVED` → `BOOKED` / `PENDING_SLOT` / `CANCELLED` / `RESCHEDULE_REQUESTED` / `HANDLED`
**Recall flow (Customers tab):** inactive 60+ days → WhatsApp re-engagement → `RECALLED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- WhatsApp Business API access via Meta — [developers.facebook.com](https://developers.facebook.com) → WhatsApp → get a test number or connect your business number; approve your re-engagement message template in [WhatsApp Manager](https://business.facebook.com/wa/manage/) (required for business-initiated messages in Flow B)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Calendar + Google Sheets OAuth2 credentials — n8n Credentials → Google Calendar OAuth2 / Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `whatsapp-appointment-booking.json`.
2. **CONFIG — Business** — open the Set node and fill in:
   - `business_name` — e.g. `Sharma Dental Clinic`
   - `calendar_id` — your Google Calendar ID (usually your Gmail address, or the calendar's ID under Settings)
   - `timezone` — e.g. `Asia/Calcutta`
   - `whatsapp_number` — your WhatsApp Business number in international format
   - `spreadsheet_id` — paste your Google Sheet ID
   - Then select your WhatsApp credential in the trigger and all WhatsApp send nodes, and your Google Calendar credential in the three Calendar nodes.
3. **Google Sheets tabs** — in that spreadsheet create two tabs with these exact headers:
   - `Bookings`: `Date | From | Message | Intent | Status`
   - `Customers`: `Name | Phone | Last Visit | Status | Last Contact`
   - Select your Google Sheets credential in every Sheets node.
4. **CONFIG — Recall** — set `recall_days` (60 is the default), and edit `reengagement_message` — replace `PASTE_YOUR_BUSINESS_NAME` and `PASTE_YOUR_OFFER` with your real business name and offer (`{name}` is auto-replaced with the customer's name). Keep it close to the template you got approved in WhatsApp Manager.
5. **AI intent parsing** — select your OpenAI credential in the "OpenAI Chat Model — Intent" node (model is `gpt-4o-mini` by default). No prompt editing needed — the agent reads the business name and timezone from CONFIG — Business.
6. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in both Telegram nodes, and **activate** the workflow. Send a test WhatsApp message ("I want to book tomorrow 4pm") and watch the execution flow.

## Customize it

- **Appointment length** — the Code nodes assume 1-hour slots (`3600000` ms). Search the two Code nodes in the book branch for `3600000` and change it to e.g. `1800000` for 30-minute appointments.
- **Business hours guard** — add an IF node after intent parsing to auto-reply "we're closed" outside working hours, before the Switch.
- **Richer confirmations** — the "Calendar — Create Event" node writes the customer's phone into the event description, which is what the cancel branch matches on. Add a Google Meet link via `additionalFields` → `conferenceData` if you do video appointments.
- **Recall cadence** — change the "Weekly Recall — Mondays 10AM" trigger to bi-weekly, or lower `recall_days` to 30 for faster-moving businesses.
- **Human handoff** — route the `other` intent to a staff WhatsApp number when the message contains words like "urgent" or "human", using an extra IF branch after the Switch.
- **Double-booking safety** — the ±1 hour window prevents back-to-back collisions; widen it to ±2 hours in "Code — Build Availability Window" if you need buffer time between appointments.
