---
title: "Shopify AI Support Agent"
description: "AI triages Shopify support emails: instant replies for routine questions, human drafts for refunds, Slack escalation. Import-ready n8n workflow."
date: 2026-10-04
category: "automation"
difficulty: "intermediate"
workflow: "/templates/shopify-ai-support-agent.json"
integrations: ["Gmail", "Shopify", "OpenAI", "Google Sheets", "Slack"]
---

## How it works

Your always-on support desk for your Shopify store — routine questions get answered in seconds, money questions wait for a human:

1. **STEP 1 — New email → extract order number** — a Gmail trigger polls your support inbox every minute. A regex pulls the order number from the subject/body (`#1234` or `order 1234`). Emails without one keep flowing — the order lookup just comes back empty.
2. **STEP 2 — Log to Sheets + Shopify lookup** — every email is appended to the `Support Inbox` tab with status `RECEIVED`, then the order number is looked up in Shopify. The lookup swallows errors (unknown number, API hiccup) so triage never blocks.
3. **STEP 3 — AI triage with structured output** — an AI Agent reads the email plus the order JSON and returns a structured verdict via a Structured Output Parser: intent (`order_status` / `policy_question` / `refund_request` / `order_change` / `other`), confidence 0–100, a ready-to-send draft reply, a `needs_human` flag, and a one-line order summary. The sheet flips to `TRIAGED`.
4. **STEP 4 — Route: auto-reply / human draft / Slack** — `Compute Routing` sets two flags: `auto_resolvable` (routine intent AND confidence ≥ threshold AND no human flag) and `money_involved` (refund/change intent or flagged). Auto-resolvable → Gmail sends the reply, sheet flips to `AUTO_RESOLVED`. Money-involved → a Gmail draft is created for a human to review and send, sheet flips to `DRAFT_CREATED`. Everything else → a rich Slack alert lands in your support channel, sheet flips to `ESCALATED`.
5. **STEP 5 — Digest notification** — all three branches merge and one Telegram summary goes out: how many emails were triaged, plus auto-resolved / drafts / escalated counts.

**Status flow in Sheets:** `RECEIVED` → `TRIAGED` → `AUTO_RESOLVED` / `DRAFT_CREATED` / `ESCALATED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- Gmail OAuth2 credential for your support inbox — n8n Credentials → Gmail OAuth2 API (connect the account that receives support mail)
- Shopify Admin API access token with the `read_orders` scope — your store admin → Apps and sales channels → Develop apps → Create a custom app → Configure Admin API access scopes → install and copy the token
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credential — n8n Credentials → Google Sheets OAuth2 API
- A Slack bot token — [api.slack.com](https://api.slack.com) → Create app → OAuth & Permissions → add `chat:write`, invite the bot to your support channel
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `shopify-ai-support-agent.json`.
2. **CONFIG — Shop** — open the Set node and fill in:
   - `shop_domain` — e.g. `your-shop.myshopify.com`
   - `support_email` — the inbox address the workflow monitors
   - `confidence_threshold` — minimum AI confidence (0–100) before an email is auto-answered (80 is a safe start)
3. **Google Sheet** — create a Google Sheet with a tab named `Support Inbox` and these exact headers: `Date | From | Subject | Order Number | Intent | Confidence | Status | Resolution Note`. Select your Google Sheets credential in all four Sheets nodes (the node picks the sheet after you connect).
4. **CONFIG — AI** — set `openai_model` (default `gpt-4o-mini`), and select your OpenAI credential in the `OpenAI Chat Model — Triage` node.
5. **CONFIG — Notifications** — paste your `telegram_chat_id` and your `slack_channel` (e.g. `support-alerts`), select your Telegram and Slack credentials in their nodes.
6. **Credentials on the action nodes** — select your Gmail credential in `Gmail — Send Reply` and `Gmail — Create Draft for Human`, and your Shopify credential in `Shopify — Get Order`. Then **activate** the workflow.

## Customize it

- **Stricter auto-replies** — raise `confidence_threshold` to 90+ in `CONFIG — Shop` so the AI answers only when it's very sure; borderline emails fall through to drafts or Slack.
- **Different mailbox** — point the Gmail trigger at a dedicated address (e.g. `support@yourstore.com`) and add a trigger filter so marketing/newsletter mail never enters the flow.
- **More intents** — extend the parser schema and the `Compute Routing` code with your own categories (e.g. `wholesale_inquiry`) and wire them to a new IF branch.
- **Kill the money risk entirely** — remove the auto-reply branch and route everything to drafts while you calibrate; flip the IF back on once you trust the confidence scores.
- **Escalation instead of Slack** — swap the Slack node for WhatsApp, SMS, or a PagerDuty-style webhook; the routing logic doesn't change.
- **Log replies for QA** — add an `Auto Reply Text` column to the sheet and write `output.draft_reply` into it in `Update Sheet — AUTO_RESOLVED` so you can audit what the AI sent.
- **Cheaper triage** — `gpt-4o-mini` is already the default; for high volume, pre-filter obvious spam with an extra IF on subject keywords before the agent runs.
