---
title: "Multi-Channel Support Ticket Triage"
description: "Classify support tickets by priority and category with AI, route them, auto-reply, and escalate SLA breaches."
date: 2026-10-01
category: "chatbots"
difficulty: "intermediate"
workflow: "/templates/support-ticket-triage-bot.json"
integrations: ["OpenAI", "Slack"]
---

## How it works

1. **New Ticket Webhook** — receives a ticket as JSON (`id`, `subject`, `body`, `channel`) from any channel: a web form, an email parser, or a chat widget.
2. **Classify Ticket (AI)** — asks GPT to return strict JSON with a `priority` (P1–P4), a `category`, and a one-line `summary`.
3. **Route by Priority** — a Switch node reads the AI's priority and sends the ticket down the P1, P2, P3, or P4 branch.
4. **Set Queue** — each branch assigns its support queue (P1 goes to `urgent-support`, P4 to `support-backlog`) and keeps the AI's classification.
5. **IF P1 Urgent** — on the P1 branch, confirms the priority before anything customer-visible happens.
6. **Slack Urgent Alert** — P1 tickets post an urgent alert to your on-call channel with the ticket ID, category, and summary.
7. **Update Ticket System** — PUTs the queue, priority, category, and AI summary back to your ticketing API.
8. **SLA Check Timer** — a second, independent chain that runs every 15 minutes.
9. **Read Open Tickets** — pulls open tickets and their SLA deadlines from Google Sheets.
10. **IF SLA Breached** — compares each ticket's deadline against the current time.
11. **Slack SLA Escalation** — posts breached tickets to your channel so nothing slips past its deadline.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- An OpenAI account — get an API key at platform.openai.com → API keys
- A ticketing system with an API (Zendesk, Intercom, Freshdesk, or your own) — the workflow PUTs to `https://api.your-ticket-system.com/v1/tickets/{id}`; you will point it at your real endpoint
- A Google Sheet tracking open tickets, with columns `ticket_id`, `subject`, `sla_deadline` (ISO timestamps), and `status`
- A Slack workspace for the alert channels

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, and save. Then open *Classify Ticket (AI)* and select your credential.
4. **Point at your ticket system** — open *Update Ticket System*, replace the placeholder URL with your real API endpoint, and add authentication (for example, an *HTTP Header Auth* credential holding your Zendesk or Intercom API token).
5. **Connect Google Sheets** — in n8n go to *Credentials → New → Google Sheets*, connect via OAuth, and save. Then open *Read Open Tickets*, select your spreadsheet and sheet, and check the column names match.
6. **Create your Slack credential** — in n8n go to *Credentials → New → Slack*, connect via OAuth, and save. Then open both Slack nodes, select your credential, and set your channel names.
7. **Activate** the workflow (toggle, top-right), then POST a test ticket to the webhook URL shown in *New Ticket Webhook*.

## Customize it

- **Match your queues** — edit the four *Set Queue* nodes so the queue names match your team's real queues.
- **Tune the classification** — edit the system prompt in *Classify Ticket (AI)* to use your real categories (billing, bug, feature-request) and your own priority definitions.
- **Change the SLA cadence** — edit the cron expression in *SLA Check Timer* (currently every 15 minutes).
- **Auto-reply to low-priority tickets** — add an email or chat send node on the P4 branch so simple tickets get an instant acknowledgement while the team focuses on P1s.
