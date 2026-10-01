---
title: "Gmail AI Auto-Labeling & Inbox Triage"
description: "Auto-classify incoming Gmail with AI (urgent, action, fyi, spam), apply labels, and get a daily digest."
date: 2026-10-01
category: "automation"
difficulty: "intermediate"
workflow: "/templates/gmail-ai-auto-labeling-triage.json"
integrations: ["Gmail","OpenAI"]
---

## How it works

This template has two independent chains (the second one is not connected to the first — both run on their own triggers).

**Chain 1 — instant triage:**

1. **Gmail Trigger: New Email** — fires on every new incoming message (polls every minute).
2. **OpenAI: Classify Email** — reads the subject and snippet and classifies the email into exactly one category: `urgent`, `action`, `fyi`, or `spam`.
3. **Switch: Route by Category** — sends the email down one of four branches based on the classification.
4. **Gmail: Apply Label** (one node per branch) — applies the matching Gmail label (Urgent, Action, FYI, or Spam) to the message.

**Chain 2 — daily digest:**

5. **Schedule Trigger: Daily Digest** — fires every day at 8:00 AM.
6. **Gmail: Fetch Labeled Unread** — searches for unread emails labeled urgent or action from the last day.
7. **OpenAI: Summarize Digest** — turns that list into a short plain-English digest with one line per email.
8. **Gmail: Send Digest** — emails the digest to you.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- An OpenAI account — get an API key at platform.openai.com → API keys
- A Gmail account — connect via OAuth in n8n

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Then open both OpenAI nodes (*OpenAI: Classify Email* and *OpenAI: Summarize Digest*) and select your credential.
4. **Create your Gmail credential** — in n8n go to *Credentials → New → Gmail OAuth2*, complete the OAuth flow, save. Open every Gmail node and select the credential.
5. **Create the labels in Gmail** — go to Gmail → *Settings → See all settings → Labels* and create four labels: `Urgent`, `Action`, `FYI`, `Spam`. In n8n, open each *Gmail: Apply Label* node and set its `labelIds` to the matching label (for labels you create yourself, the label ID is usually the label name itself).
6. **Set your digest recipient** — open *Gmail: Send Digest* and change the recipient to your own email address.
7. **Activate** the workflow (toggle, top-right). New emails will be labeled within a minute, and the digest arrives at 8:00 AM daily.

## Customize it

- **Change the categories** — edit the prompt in *OpenAI: Classify Email* and rename the Switch branches and labels to match (e.g., `receipts`, `newsletters`).
- **Change the digest time** — open *Schedule Trigger: Daily Digest* and edit the cron expression (`0 8 * * *` = 8:00 AM daily).
- **Skip spam from the digest** — the digest query already only looks at urgent and action labels; adjust the `q` filter in *Gmail: Fetch Labeled Unread* to include or exclude categories.
- **Add an alert for urgent mail** — connect a Slack or Telegram node after *Gmail: Apply Label — Urgent* to get pinged the moment something urgent arrives.
