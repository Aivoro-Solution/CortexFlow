---
title: "Invoice AR Chaser"
description: "Chase unpaid invoices automatically: day 1/7/14 reminders, Slack escalation at 14 days, full AR status in Sheets. Import-ready n8n workflow."
date: 2026-10-04
category: "automation"
difficulty: "beginner"
workflow: "/templates/invoice-ar-chaser.json"
integrations: ["Stripe", "Gmail", "Slack", "Google Sheets", "Telegram"]
---

## How it works

Your automated accounts-receivable assistant that runs every morning:

1. **STEP 1 — Daily trigger + list open invoices** — a daily 8 AM schedule trigger fires, then Stripe lists all invoices with status `open` (unpaid). No coding needed — it's a single Stripe node.
2. **STEP 2 — Days overdue + sync AR ledger** — a Code node computes `days_overdue` for each invoice (skipping invoices not due yet) and flags whether today is reminder day 1, 7, or 14. The workflow reads your `AR` sheet, appends brand-new invoices with status `UNPAID`, and refreshes the days-overdue on existing rows.
3. **STEP 3 — Day 1/7/14 reminders** — invoices exactly 1, 7, or 14 days overdue get a branded Gmail reminder: a friendly nudge (day 1) → a firm "payment overdue" email (day 7) → a final notice (day 14), each with the invoice number, amount, and pay link. The sheet flips to `REMINDER_SENT_DAY_1`, `_DAY_7`, or `_DAY_14`.
4. **STEP 4 — Escalation + summary** — invoices 14+ days overdue with no reminder due today are escalated to your Slack channel (customer, amount, days overdue, pay link), the sheet flips to `ESCALATED`, all branches merge, and you get one Telegram summary: total outstanding, oldest overdue invoice, reminders sent, and escalations today.

**Status flow in Sheets:** `UNPAID` → `REMINDER_SENT_DAY_1` / `REMINDER_SENT_DAY_7` / `REMINDER_SENT_DAY_14` → `ESCALATED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Stripe account — [stripe.com](https://stripe.com) → Developers → API keys (restricted key with Invoice read permissions is enough)
- A Gmail OAuth2 credential — n8n Credentials → Gmail OAuth2
- A Slack OAuth2 credential — n8n Credentials → Slack OAuth2
- A Google Sheets OAuth2 credential — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `invoice-ar-chaser.json`.
2. **CONFIG — AR** — open the Set node and fill in:
   - `business_name` — your business name (used in reminder email sign-offs)
   - `sender_name` — the name signing the reminders
   - `reminder_days` — which days-overdue trigger a reminder (default `1,7,14`)
   - `escalation_day` — days overdue before Slack escalation (default `14`)
   - `owner_slack_channel` — your Slack channel name for escalations (e.g. `finance`)
3. **AR sheet** — create a Google Sheet with a tab named `AR` and headers: `Invoice ID | Number | Customer | Email | Amount | Due Date | Days Overdue | Status`. Select your Google Sheets credential in the four Sheets nodes (Read AR Ledger, Append New Invoices, Update Existing Invoices, and both Status update nodes).
4. **Connect Stripe** — select your Stripe credential in the `List Open Invoices` node.
5. **Connect Gmail + Slack** — select your Gmail credential in `Gmail — Send Reminder` and your Slack credential in `Slack — Escalate to Owner`.
6. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in `Telegram — Send AR Summary`, and **activate** the workflow.

## Customize it

- **Real-time instead of daily** — swap the Schedule Trigger for a Stripe webhook (`invoice.created` / `invoice.finalized`) so the workflow reacts the moment an invoice is issued.
- **PAID sync** — add a second Stripe webhook (`invoice.paid`) that flips the row's Status to `PAID` in the same AR sheet, giving you a full invoice lifecycle.
- **Change the reminder cadence** — edit `reminder_days` in the `CONFIG — AR` node (e.g. `1,3,7,14,30`); the reminder-day logic in `Compute Days Overdue` maps directly off these values.
- **Tiered escalation** — add another IF branch (e.g. 30+ days) that notifies a different Slack channel or emails you directly.
- **Friendly vs. firm copy** — all three email templates live in the `Build Reminder Email` Code node; tweak tone, add your logo signature, or CC your accountant.
