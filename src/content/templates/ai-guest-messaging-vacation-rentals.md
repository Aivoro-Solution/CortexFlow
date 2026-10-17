---
title: "AI Guest Messaging Assistant for Vacation Rentals"
description: "AI agent auto-answers Airbnb, Booking.com and email guest questions in n8n — FAQs reply instantly, refunds and complaints escalate to you."
date: 2026-10-17
category: "automation"
difficulty: "intermediate"
workflow: "/templates/ai-guest-messaging-vacation-rentals.json"
integrations: ["Webhook", "OpenAI", "Google Sheets", "Telegram", "HTTP Request"]
---

## How it works

Your always-on messaging desk for your vacation-rental business — routine guest questions get answered in seconds, money and safety questions wait for you:

1. **STEP 1 — Inbound guest message** — the `Guest Message Webhook` receives each guest message (POST). Your channel-manager/PMS (Hostaway, Lodgify, Guesty…) forwards Airbnb and Booking.com threads to this webhook; email arrives through an IMAP-to-webhook bridge. `Normalize Guest Message` turns every payload into one shape: channel, property, guest name, message text, message ID.
2. **STEP 2 — Log to Sheets** — every message is appended to the `Guest Messages` tab with status `NEW`, then `Update Sheet — Status PROCESSING` flips the row while the AI works.
3. **STEP 3 — AI classify + draft** — `AI Agent — Classify & Draft` reads the message with your property context (check-in/out times, WiFi password, house rules) and returns a structured verdict via `Structured Output Parser — Guest Intent`: intent (`wifi` / `checkin` / `checkout` / `houserules` / `amenities` / `parking` / `directions` / `refund` / `complaint` / `access` / `schedule_change` / `other`), confidence 0–1, an `auto_reply_allowed` flag, a ready-to-send `draft_reply`, and an `escalation_reason`.
4. **STEP 4 — Safe auto-reply branch** — `IF — Safe to Auto-Reply?` passes only when `auto_reply_allowed = true` AND confidence ≥ your threshold (default 0.85). `Send Guest Reply` POSTs the draft to your reply endpoint, the sheet flips to `AUTO_REPLIED`, and you get a Telegram summary of the guest and the reply sent.
5. **STEP 5 — Escalation branch** — refunds, complaints, access codes, safety issues, early check-in/late checkout requests, or low confidence → the sheet flips to `ESCALATED` and `🚨 Telegram — Escalate to Host` sends you the guest's message, the AI's read, the escalation reason, and a suggested draft so you can reply manually.
6. **STEP 6 — Acknowledge webhook** — both branches merge and `Respond — OK` returns `{"status": "ok"}` to the caller.

**Status flow in Sheets:** `NEW` → `PROCESSING` → `AUTO_REPLIED` / `ESCALATED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credential — n8n Credentials → Google Sheets OAuth2 API
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- A channel-manager/PMS or email bridge that can POST inbound guest messages to a webhook — e.g. Hostaway, Lodgify, or Guesty for [Airbnb](https://www.airbnb.com/host) / [Booking.com](https://www.booking.com) threads; an IMAP-to-webhook bridge (e.g. n8n's own IMAP trigger → webhook) for email

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `ai-guest-messaging-vacation-rentals.json`.
2. **CONFIG — Properties & Rules** — open the Set node and fill in:
   - `property_name` — comma-separated list if you run multiple properties
   - `checkin_time` / `checkout_time` — e.g. `15:00` / `11:00`
   - `wifi_password` — the WiFi password guests ask for most
   - `house_rules_url` — link to your house rules page
   - `safe_intents` — which intents the AI may answer alone (default `wifi,checkin,checkout,houserules,amenities,parking,directions`)
   - `confidence_threshold` — minimum AI confidence (0–1) before a message is auto-answered (0.85 is a safe start)
   - `reply_api_url` / `reply_api_key` — your PMS/channel-manager reply endpoint and key
   - `telegram_chat_id` and `escalation_email`
3. **Google Sheet** — create a Google Sheet with a tab named `Guest Messages` and these exact headers: `Message ID | Timestamp | Channel | Property | Guest Name | Message | Intent | Confidence | Status | Draft Reply | Replied At`. Enter the sheet in `CONFIG — Google Sheets` (`spreadsheet_id`, `sheet_name`), and select your Google Sheets credential in all four Sheets nodes (`Log Message — Status NEW`, `Update Sheet — Status PROCESSING`, `Update Sheet — Status AUTO_REPLIED`, `Update Sheet — Status ESCALATED`).
4. **AI** — select your OpenAI credential in `OpenAI Chat Model — Guest AI` (model defaults to `gpt-4o-mini`).
5. **Notifications** — select your Telegram credential in `Telegram — Notify Host (Auto-replied)` and `🚨 Telegram — Escalate to Host`.
6. **Activate** — click Activate, copy the `Guest Message Webhook` production URL from the node, and point your PMS/channel-manager inbound-message webhook (or email bridge) at it. Send a test message ("What is the WiFi password?") and check the sheet row and Telegram.

## Customize it

- **Stricter auto-replies** — raise `confidence_threshold` to 0.9+ in `CONFIG — Properties & Rules` so the AI answers only when very sure; borderline messages fall through to escalation.
- **Per-property answers** — extend the system prompt in `AI Agent — Classify & Draft` with a property-specific facts block (gate codes, parking spots, quiet hours) keyed off the `property` field.
- **More intents** — extend the parser schema's intent list and the IF logic; add a third branch for e.g. `upsell` (airport transfer, late checkout fees) routed to a human draft.
- **Kill the auto-reply risk entirely** — disconnect the true branch of `IF — Safe to Auto-Reply?` into escalation while you calibrate; reconnect it once you trust the confidence scores.
- **Audit every reply** — the `Draft Reply` column already stores what was sent; add a weekly review by filtering rows with status `AUTO_REPLIED`.
- **Cheaper at scale** — `gpt-4o-mini` is already the default; pre-filter obvious OTA auto-messages (e.g. booking confirmations) with an extra IF on message keywords before the agent runs.
- **Add a human-draft mode** — clone the escalation branch, swap Telegram for a Gmail `create draft` to `escalation_email`, and send polished replies from your inbox.
