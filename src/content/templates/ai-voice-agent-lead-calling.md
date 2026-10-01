---
title: "AI Voice Agent for Lead Calling & Appointment Booking"
description: "Qualify inbound leads with AI, then trigger an AI voice call and book the appointment on your calendar. Human-approved calling."
date: 2026-10-01
category: "ai-agents"
difficulty: "advanced"
workflow: "/templates/ai-voice-agent-lead-calling.json"
integrations: ["OpenAI", "Google Calendar", "Slack"]
---

## How it works

1. **Lead Webhook receives the lead** — your form or CRM POSTs the lead's name, phone, and notes to the webhook URL.
2. **Normalize Fields cleans the input** — trims whitespace and strips non-dialable characters from the phone number, so every downstream step gets consistent data.
3. **Qualify Lead (AI agent) judges intent** — GPT reads the lead's notes and decides whether they show real buying intent, replying with a strict JSON verdict: `qualified` true/false plus a one-line reason.
4. **Parse Decision extracts the verdict** — a Code node safely pulls `qualified` and `reason` out of the AI's JSON, keeping the rest of the flow deterministic.
5. **IF Qualified routes the flow** — qualified leads continue down the calling path; everyone else is sent to the nurture tag.
6. **Trigger Voice Call starts the AI call** — an HTTP request fires your voice provider (Vapi, Twilio, or similar) to call the lead.
7. **Book Calendar Event creates the follow-up** — the call books a follow-up event on your calendar through the Google Calendar API.
8. **Notify Team posts to Slack** — your team sees who was called, when the follow-up is, and why the lead qualified.
9. **Tag Nurture files the rest** — unqualified leads are tagged `nurture` so you can follow up with them later.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- An OpenAI account — get an API key at platform.openai.com → API keys
- An AI voice provider (Vapi, Twilio, or similar) — sign up and get an API key plus your call endpoint URL
- A Google account with Calendar access — create a Header Auth credential with an OAuth2 bearer token, or swap in n8n's Google Calendar node
- A Slack workspace — create a Slack app at api.slack.com and complete OAuth2

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Then open the *OpenAI Chat Model* node and select your credential.
4. **Connect your voice provider** — in n8n go to *Credentials → New → Header Auth*, add a header named `Authorization` with the value `Bearer YOUR_API_KEY`, save. Open *Trigger Voice Call*, select the credential, and replace the placeholder URL (`https://api.your-voice-provider.com/v1/calls`) with your provider's real call endpoint.
5. **Connect Google Calendar** — create a Header Auth credential with your Google OAuth2 bearer token and select it in *Book Calendar Event* (or replace the node with n8n's Google Calendar node). Adjust the event start-time logic in the node body to match your timezone.
6. **Connect Slack** — in n8n go to *Credentials → New → Slack*, complete OAuth2, save. Open *Notify Team*, select your credential, and set your channel.
7. **Activate** the workflow (toggle, top-right), then POST a test lead to the *Lead Webhook* URL.

Human approval note: voice calls fire only for AI-qualified leads. Before going live, review the *Parse Decision* output on real leads — and if you want a human sign-off on every call, insert a Wait node between *IF Qualified* and *Trigger Voice Call* so nothing is dialed without review.

## Customize it

- **Tighten qualification** — edit the system prompt in *Qualify Lead* to add your own criteria (budget, geography, company size).
- **Change the call script** — edit the JSON body in *Trigger Voice Call* to pass your provider's script, voice, or prompt parameters.
- **Smarter scheduling** — replace the fixed "tomorrow at 10:00 UTC" logic in *Book Calendar Event* with your availability rules or a round-robin across your team.
- **Log every decision** — add a Google Sheets node after *Parse Decision* to record each lead, verdict, and reason for later review.
