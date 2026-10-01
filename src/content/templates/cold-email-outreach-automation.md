---
title: "Hyper-Personalized Cold Email Outreach"
description: "Personalize every cold email with AI, send at a safe pace, handle opt-outs, and hand replies to a human."
date: 2026-10-01
category: "automation"
difficulty: "intermediate"
workflow: "/templates/cold-email-outreach-automation.json"
integrations: ["Google Sheets", "OpenAI", "Gmail"]
---

## How it works

1. **Daily Outreach Timer** — starts the run every day at 9:00 AM.
2. **Read Unsent Leads** — pulls leads with `status=unsent` from Google Sheets. Keep at most 20 unsent rows queued per day so sends stay paced.
3. **Process Leads One-by-One** — a loop node that handles exactly one lead per pass, so every email goes through the full personalization pipeline.
4. **Write First Line (AI)** — GPT writes a 1–2 sentence personalized opener from the lead's name, role, company, and recent activity.
5. **Compose Email** — builds the full email: subject line, HTML body with the AI opener, and your one-click unsubscribe link.
6. **Send Email** — sends the composed email via Gmail.
7. **Wait 90 Seconds** — pauses between sends to stay comfortably inside Gmail's rate limits.
8. **Mark Lead Sent** — updates the lead's status to `sent` in the sheet, then loops back to the next lead.
9. **Unsubscribe Webhook** — a second, independent chain that receives unsubscribe clicks with an `email` query parameter.
10. **Mark Opted Out** — sets that lead's status to `opted-out` in the sheet, so they are never emailed again.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Google Sheet of leads you have the right to email, with columns `email`, `first_name`, `last_name`, `company`, `role`, `recent_post`, and `status` — only ever use an opt-in or legitimately prospected list
- A Gmail account — you will connect it via OAuth in n8n
- An OpenAI account — get an API key at platform.openai.com → API keys

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Connect Google Sheets** — in n8n go to *Credentials → New → Google Sheets*, connect via OAuth, and save. Then open *Read Unsent Leads* and *Mark Lead Sent*, select your spreadsheet and the Leads sheet, and check the column names match.
4. **Connect Gmail** — in n8n go to *Credentials → New → Gmail*, connect via OAuth, and save. Then open *Send Email* and select your credential.
5. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, and save. Then open *Write First Line (AI)* and select your credential.
6. **Set your unsubscribe URL** — open *Compose Email* and replace `https://yourdomain.com/unsubscribe` with your real one-click unsubscribe link. It must work without requiring a login.
7. **Wire up unsubscribes** — point your unsubscribe link at the *Unsubscribe Webhook* URL with `?email=` appended, so clicks automatically flip the lead to `opted-out`.
8. **Activate** the workflow (toggle, top-right). Then monitor replies yourself — any reply means a human takes over; the workflow never auto-replies to responses.

Compliance note: only email people you have permission to contact, always include the working unsubscribe link, and honor opt-outs immediately. Rules like CAN-SPAM and GDPR apply — this template gives you the mechanics; the list is your responsibility.

## Customize it

- **Change send time and volume** — edit the cron in *Daily Outreach Timer* and the 90-second *Wait* (longer waits are safer for larger lists; shorter days keep volumes conservative).
- **Rewrite the email** — edit the template in *Compose Email* to match your voice and offer (keep the unsubscribe link in place).
- **Personalize deeper** — add more lead columns (for example `industry` or `pain_point`) and reference them in the *Write First Line (AI)* prompt.
- **Catch replies fast** — add a Gmail Trigger chain that flags replies in Slack, so your team responds within hours instead of days.
