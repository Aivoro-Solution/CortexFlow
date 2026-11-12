---
title: "Marketing Attribution & Lead Engine — Multi-Channel Ad Spend, AI Lead Scoring, Dedup & Round-Robin Routing"
description: "Capture leads from any channel, dedupe them, AI-score Hot/Warm/Cold, route round-robin to reps, WhatsApp hot leads, and track CPL, CPP and ROAS daily."
date: 2026-11-12
category: "automation"
difficulty: "intermediate"
workflow: "/templates/marketing-attribution-lead-engine.json"
integrations: ["Google Sheets", "OpenAI", "Meta Graph API", "TikTok", "LinkedIn", "YouTube", "WhatsApp HTTP API", "Telegram"]
---

One workflow, two jobs: it turns every form submission into a scored, assigned, followed-up lead — and every morning it tells you which ad channel is actually earning its spend. A business coaching company was hiring a freelancer to build exactly this pipeline in November 2026 (Meta/TikTok/LinkedIn/YouTube ingestion, AI lead scoring, dedup, round-robin routing, WhatsApp outreach, CPL/ROAS tracking) — this template is that pipeline, ready to import.

## How it works

1. **Lead Webhook captures the lead** — your form or landing page POSTs name, email, phone, UTM source/medium/campaign and message to the webhook URL.
2. **Normalize Lead cleans the submission** — emails are lowercased and trimmed, phones are reduced to digits, UTM tags are parsed into clean fields.
3. **Check Dedup matches phone or email** — the workflow reads your Leads sheet (*Read Leads Sheet*) and checks whether this person already exists. A returning lead (*IF — Duplicate Lead?* → true) flips to `TOUCHED` via *Update Lead — Status TOUCHED*, gets a new touchpoint logged in the Journey sheet (*Log Journey — Returning Lead*), and goes straight to the alert — no double-counting, no second rep fighting over the same lead.
4. **Log New Lead appends with status `NEW`** — first-time leads land in the Leads sheet (*Log New Lead — Status NEW*) with their UTM tags attached.
5. **AI Agent — Score Lead scores 0–100** — GPT-4o-mini weighs the lead against your business context (set in *CONFIG — AI Scoring*) and returns a score, a tier (Hot / Warm / Cold), a one-line reason, an intent phrase and a spam-risk flag via the *Structured Output Parser — Lead Score*. The sheet flips to `SCORED` (*Update Sheet — Status SCORED*).
6. **Hot leads go to the senior rep + WhatsApp** — a score of 70 or above (*IF — Hot Lead*) routes to the first rep in your roster via *Assign Rep — Round-Robin (Hot)* (your senior rep), flips the sheet to `ASSIGNED` (*Update Sheet — Status ASSIGNED (Hot)*), then *Send WhatsApp — Hot Lead* messages the lead instantly via your WhatsApp HTTP API and the sheet flips to `CONTACTED` (*Update Sheet — Status CONTACTED*), with the touch logged by *Log Journey — Hot Assigned*.
7. **Warm leads rotate round-robin** — a score of 40–69 (*IF — Warm Lead*) rotates across your rep roster via *Assign Rep — Round-Robin (Warm)* based on how many leads are already in the sheet, flips to `ASSIGNED` (*Update Sheet — Status ASSIGNED (Warm)*), and the touch is logged to the Journey sheet (*Log Journey — Warm Assigned*).
8. **Cold leads go to `NURTURE`** — anything below 40 is filed for later campaigns (*Update Sheet — Status NURTURE*) instead of burning rep time.
9. **Merge — Lead Branches combines every path** — duplicate, hot, warm and cold branches all converge; *Build Lead Alert* composes one Telegram alert (*Telegram — Send Lead Alert*) with score, tier, channel, campaign and assigned rep.
10. **Daily 8AM Attribution Trigger starts the second branch** — every morning at 08:00 the workflow pulls yesterday's spend from Meta, TikTok, LinkedIn and YouTube.
11. **Compute Attribution Metrics joins spend with your sheets** — it counts leads and conversions per channel from the Leads sheet (*Read Leads Sheet — Attribution*) and computes CPL, CPLPV, CPP and ROAS for each channel, then appends a daily snapshot row to the Attribution sheet (*Log Attribution Snapshot*).
12. **IF — CPL Over Cap watches your budget** — any channel whose CPL exceeds the cap in *CONFIG — Attribution* triggers *Build CPL Alert* → *Telegram — CPL Alert* so you can pause or reallocate before the spend runs away.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- An OpenAI account — get an API key at platform.openai.com → API keys
- A Google account — create a spreadsheet with three tabs named "Leads", "Journey" and "Attribution"
- A Telegram bot — create one with @BotFather (t.me/BotFather) and get your chat ID
- Meta ad account — create an app at developers.facebook.com/apps and get an access token with `ads_read` permission
- TikTok, LinkedIn and YouTube ad accounts — get their insights/analytics API endpoints and tokens (TikTok: business-api.tiktok.com/portal, LinkedIn: linkedin.com/developers/apps, YouTube Analytics API: console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com)
- A WhatsApp HTTP API endpoint — the template is written for a WAHA-style endpoint (github.com/devlikeapro/waha); any API that accepts a JSON POST with a chat ID and text works

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your spreadsheet** with these exact headers:
   - **Leads:** Date Received | Name | Email | Phone | Message | UTM Source | UTM Medium | UTM Campaign | Lead Score | Tier | Score Reason | Assigned Rep | Status
   - **Journey:** Date | Email | Phone | Channel | Campaign | Touch Type | Rep | Notes
   - **Attribution:** Date | Channel | Spend | Leads | Conversions | CPL | CPLPV | CPP | ROAS
4. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Then open the *OpenAI Chat Model — Scoring* node and select your credential.
5. **Connect Google Sheets** — in n8n go to *Credentials → New → Google Sheets OAuth2*, complete OAuth2, save. Open every Google Sheets node, select your credential, and set your spreadsheet (the tab names are already set).
6. **Connect Telegram** — in n8n go to *Credentials → New → Telegram*, paste your bot token, save. Open *Telegram — Send Lead Alert* and *Telegram — CPL Alert* and select your credential.
7. **Fill in the CONFIG nodes** (all values are `PASTE_YOUR_*` placeholders — nothing is hardcoded):
   - *CONFIG — Lead Engine*: `hot_threshold` (70), `warm_threshold` (40), `rep_roster` (format `Name:email,Name:email` — the first rep is treated as the senior rep for Hot leads), `whatsapp_api_url`, `whatsapp_enabled`.
   - *CONFIG — Google Sheets*: your `spreadsheet_id` (the long ID in the sheet URL).
   - *CONFIG — AI Scoring*: a 2–3 sentence `business_context` describing what you sell and who your ideal customer is — the AI scores against this.
   - *CONFIG — Attribution*: `meta_ad_account_id`, `meta_access_token`, the three insights endpoint URLs (`tiktok_insights_url`, `linkedin_insights_url`, `youtube_analytics_url`), `cpl_cap` (50), `avg_deal_value` (100, used for ROAS), `currency`, and your `telegram_chat_id`.
   - *CONFIG — Notifications*: your `telegram_chat_id`.
8. **Point your form at the webhook** — activate the workflow, copy the *Lead Webhook* production URL, and set your form/landing page to POST `name`, `email`, `phone`, `utm_source`, `utm_medium`, `utm_campaign` and `message` to it.
9. **Test it** — submit a test lead, then check the Leads sheet: it should read `SCORED` with a tier, an assigned rep, and (for a Hot lead) a WhatsApp message sent. Send a second identical submission to confirm the duplicate path flips the row to `TOUCHED` instead of creating a new row.

## Customize it

- **Move the thresholds** — edit `hot_threshold` / `warm_threshold` in *CONFIG — Lead Engine* (currently 70 / 40) to match your definition of a hot lead.
- **Change the senior-rep rule** — edit *Assign Rep — Round-Robin (Hot)* if you want Hot leads to rotate among your top two reps instead of always going to the first in the roster.
- **Change the scoring criteria** — edit the system prompt in *AI Agent — Score Lead* and the `business_context` in *CONFIG — AI Scoring* to describe your ideal customer.
- **Swap the WhatsApp provider** — *Send WhatsApp — Hot Lead* is a plain HTTP Request node: point `whatsapp_api_url` at Twilio, 360dialog, Qontak or any provider and adjust the JSON body to their format.
- **Add or drop ad channels** — each platform is one HTTP Request node (*Fetch Meta Insights*, *Fetch TikTok Insights*, *Fetch LinkedIn Insights*, *Fetch YouTube Analytics*). Delete the ones you don't run, or add a new one and add a matching line to the `channels` array in *Compute Attribution Metrics*. Unconfigured channels report spend 0 instead of failing the run (Continue On Fail is on).
- **Track CPLPV properly** — CPLPV currently mirrors CPL until page-view data is wired in; add a page-view count per channel in *Compute Attribution Metrics* if you track landing-page views.
- **Route to a real CRM** — swap the Google Sheets nodes for HubSpot, Salesforce or Pipedrive nodes, or add them after the assignment step — the Leads sheet stays as your audit trail.
