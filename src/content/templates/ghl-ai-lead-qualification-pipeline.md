---
title: "AI Lead Qualification Pipeline for GoHighLevel"
description: "New lead → dedupe → AI scores intent → qualified leads sync to GoHighLevel (contact + opportunity + note), the rest go to nurture or junk."
date: 2026-10-19
category: "automation"
difficulty: "intermediate"
workflow: "/templates/ghl-ai-lead-qualification-pipeline.json"
integrations: ["GoHighLevel", "OpenAI", "Google Sheets", "Telegram", "n8n Form Trigger"]
---

## How it works

A complete lead-intake → AI-qualification → GoHighLevel-sync pipeline for agencies, insurance brokers, and any service business that loses money on slow follow-up:

1. **STEP 1 — Lead intake & config** — a visitor fills the n8n form (name, email, phone, service interest, message). `CONFIG — Pipeline Settings` holds every user-editable value (GHL API key, Location ID, Pipeline + Stage IDs, score threshold, booking link — all `PASTE_YOUR_*` placeholders). `Prepare Lead Record` generates a `LEAD-YYYYMMDD-XXXX` reference, `Search Existing Leads` reads the Lead Log, `Detect Duplicate` compares emails, and `IF — Duplicate Email?` splits the flow.
2. **STEP 2 — Dedupe + AI qualification** — duplicates are logged with status `DISCARDED` and skipped entirely. Fresh leads are appended with status `LEAD_RECEIVED`, then `AI Agent — Qualify Lead` (gpt-4o-mini with a Structured Output Parser) scores intent 0–100 and returns a verdict (`qualified` / `nurture` / `junk`), budget range, timeline, and a one-line summary. `Update Lead Log — Status DEDUP_CHECKED` records the score and verdict.
3. **STEP 3 — Verdict routing + GoHighLevel sync** — if `IF — Verdict Qualified?` is true, the lead goes to GoHighLevel via the v2 REST API: `GHL — Create Contact` (POST `/contacts/` with a Bearer token built from the config node), `GHL — Create Opportunity` (POST `/opportunities/` with your pipeline + stage IDs, status `open`), then `GHL — Add Score Note` (the AI's score, verdict and summary on the contact record). The Lead Log flips to `QUALIFIED` with the GHL contact id stored, and `Telegram — Qualified Alert` fires with your booking link and a direct GHL contact link.
4. **STEP 4 — Nurture / junk + final summary** — `IF — Verdict Nurture?` routes lukewarm leads to `Append Nurture List` (the **Nurture List** tab with `follow_up_status` set to `PENDING`) and the Lead Log flips to `NURTURED`. Junk verdicts flip the Lead Log to `DISCARDED` and are **never** synced to GHL. All branches merge, `Build Summary Message` compiles the run, and `Telegram — Send Summary` reports name, verdict, score, and status.

**Status flow in Sheets:** `LEAD_RECEIVED` → `DEDUP_CHECKED` → `QUALIFIED` / `NURTURED` / `DISCARDED`

**Hard rules (from real buyer demand):** no credentials are hardcoded — every secret lives in the CONFIG nodes behind `PASTE_YOUR_*` placeholders and empty credential selects. The AI never invents a lead: junk verdicts and duplicates are logged, never pushed to your CRM.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- A GoHighLevel account — [gohighlevel.com](https://www.gohighlevel.com) → Sub-account Settings → Integrations → create an API key (needs **contacts** and **opportunities** scope)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — [sheets.google.com](https://sheets.google.com) for the spreadsheet; connect in n8n under Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather) ([telegram.org](https://telegram.org)) → `/newbot` → copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `ghl-ai-lead-qualification-pipeline.json`.
2. **Create the spreadsheet** — make one Google Sheet with these 2 tabs and exact headers:
   - `Lead Log`: `lead_ref | name | email | phone | service_interest | received_at | stage | status | intent_score | verdict | summary | ghl_contact_id | notes`
   - `Nurture List`: `lead_ref | name | email | phone | service_interest | intent_score | summary | follow_up_status | status`
3. **CONFIG — Pipeline Settings** — open the Set node and fill in:
   - `spreadsheet_id` — paste your spreadsheet ID (from the sheet URL)
   - `ghl_api_key` — your GoHighLevel API key
   - `ghl_location_id` — your sub-account Location ID (Sub-account Settings → Company)
   - `ghl_pipeline_id` + `ghl_stage_id` — Opportunities → Pipelines → open your pipeline and copy both IDs
   - `score_threshold` — `70` is a good start (only scores ≥ threshold get synced as qualified)
   - `booking_link` — your calendar/booking URL sent with the qualified alert
   - `business_name`, `owner_name` — used in the AI's system prompt and messages
   - Then select your Google Sheets credential in all six Google Sheets nodes (`Search Existing Leads`, `Log Duplicate — Status DISCARDED`, `Log Lead — Status LEAD_RECEIVED`, `Update Lead Log — Status DEDUP_CHECKED`, `Append Nurture List`, `Update Lead Log — Status NURTURED`, `Update Lead Log — Status DISCARDED (Junk)`, `Update Lead Log — Status QUALIFIED`)
4. **AI qualification** — select your OpenAI credential in `OpenAI Chat Model — Qualifier` (model is `gpt-4o-mini` by default; you can swap it for an Anthropic/Claude chat model if you prefer Claude-style reasoning — just reconnect the `ai_languageModel` input on `AI Agent — Qualify Lead`).
5. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in `Telegram — Qualified Alert` and `Telegram — Send Summary`, then **activate** the workflow and open the form URL from `Lead Intake — Form Trigger` to test with a sample lead.

## Customize it

- **Stricter scoring** — raise `score_threshold` to `80` and only high-intent leads reach GoHighLevel; everything else lands in the nurture list or junk.
- **Speed-to-lead SMS** — insert an HTTP Request to GHL's `/conversations/messages` endpoint right after `GHL — Create Contact` to fire an instant SMS ("Hi {name}, we got your request…") inside the same thread.
- **Missed-call textback** — point GHL's inbound call webhook at the form trigger's idea: replace the Form Trigger with a Webhook Trigger and let missed calls enter the same qualification pipeline.
- **Calendar booking** — after `GHL — Create Opportunity`, add a GHL `/calendars/events/appointments` HTTP call so qualified leads are booked automatically instead of just receiving the link.
- **Auto-follow-up drip** — the Nurture List's `follow_up_status` column (`PENDING` → `CONTACTED`) is your flag: add a scheduled n8n workflow that reads `PENDING` rows and sends a 3-day email/SMS sequence.
- **Richer contact fields** — extend the Structured Output Parser schema (e.g. `service_budget_band`, `location`) and map the new fields into the contact-creation JSON body.
- **Round-robin assignment** — set the `assignedTo` field in the opportunity body per lead (cycle through salespeople in `Prepare Lead Record`) so new leads land directly on the right owner.
