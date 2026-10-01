---
title: "AI Lead Capture → Enrich → Score → CRM Routing"
description: "Capture leads via webhook, enrich company data, AI-score them 0–100, and route hot leads to your CRM with a Slack alert."
date: 2026-10-01
category: "ai-agents"
difficulty: "intermediate"
workflow: "/templates/ai-lead-capture-enrich-score-crm.json"
integrations: ["OpenAI", "Google Sheets", "Slack"]
---

## How it works

1. **Lead Webhook captures the lead** — your form POSTs the lead's name, email, company, and company domain to the webhook URL.
2. **Enrich Company pulls firmographics** — an HTTP request fetches company data (size, industry, location) from your enrichment provider.
3. **Score Lead (AI agent) scores 0–100** — GPT weighs the enriched data against your ideal customer profile and returns a JSON score plus a one-line reason.
4. **Parse Score extracts the number** — a Code node pulls `score` and `reason` into clean fields (clamped to 0–100) so routing stays deterministic.
5. **IF Hot Lead checks the threshold** — a score of 70 or above goes down the hot path; anything below goes to nurture.
6. **Save Hot Lead appends to Google Sheets** — the lead lands in your "Hot Leads" tab with their score and reason.
7. **Slack Alert pings the team** — sales sees the hot lead instantly, with score, reason, and contact details.
8. **Save Nurture Lead files the rest** — lower-scoring leads land in the "Nurture" tab for later campaigns.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- An OpenAI account — get an API key at platform.openai.com → API keys
- A lead-enrichment provider (Clearbit, Apollo, or similar) — sign up and get an API key plus your company-lookup endpoint URL
- A Google account — create a spreadsheet with two tabs named "Hot Leads" and "Nurture"
- A Slack workspace — create a Slack app at api.slack.com and complete OAuth2

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Then open the *OpenAI Chat Model* node and select your credential.
4. **Connect your enrichment provider** — in n8n go to *Credentials → New → Header Auth*, add your provider's API key header, save. Open *Enrich Company*, select the credential, and replace the placeholder URL (`https://api.your-enrichment-provider.com/v1/companies`) with your provider's real company endpoint.
5. **Connect Google Sheets** — in n8n go to *Credentials → New → Google Sheets OAuth2*, complete OAuth2, save. Open *Save Hot Lead* and *Save Nurture Lead*, select your credential, and set your spreadsheet and tab in each node.
6. **Connect Slack** — in n8n go to *Credentials → New → Slack*, complete OAuth2, save. Open *Slack Alert*, select your credential, and set your channel.
7. **Activate** the workflow (toggle, top-right), then POST a test lead to the *Lead Webhook* URL.

## Customize it

- **Move the threshold** — edit the *IF Hot Lead* condition (currently 70) to match your definition of a hot lead.
- **Change the scoring criteria** — edit the system prompt in *Score Lead* to describe your ideal customer profile.
- **Route to a real CRM** — swap the Google Sheets nodes for HubSpot, Salesforce, or Pipedrive nodes, or add them after the Slack alert.
- **Add more enrichment** — chain a second HTTP Request after *Enrich Company* to pull in technographic or funding data before scoring.
