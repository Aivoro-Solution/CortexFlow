---
title: "Talk to Your Data: Sheets Chat & Digests"
description: "Ask questions about any Google Sheet in plain English, plus a daily AI digest of what changed."
date: 2026-10-01
category: "ai-agents"
difficulty: "intermediate"
workflow: "/templates/sheets-data-chat-digests.json"
integrations: ["Google Sheets","OpenAI","Gmail"]
---

## How it works

1. **Chat Trigger** — receives your question from the n8n chat panel.
2. **Read Sheet Rows** — pulls every row from your Google Sheet deterministically (no AI guessing here).
3. **Format Rows as Table** — converts the rows into a compact text table the model can read.
4. **AI Agent** — answers your question using only the table data, with gpt-4o-mini under the hood. If the answer is not in your data, it says so instead of inventing numbers.
5. **Digest Schedule** — a second, unconnected chain that fires every morning at 8:00.
6. **Read Sheet (Digest)** — pulls the sheet rows again for the digest run.
7. **Summarize Changes** — GPT reads the data and writes a short bullet-point digest of key figures and changes.
8. **Send Digest Email** — emails the digest to you via Gmail.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Google account with access to the spreadsheet you want to query
- An OpenAI account — get an API key at platform.openai.com → API keys
- A Gmail account to receive the digest

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your Google Sheets credential** — in n8n go to *Credentials → New → Google Sheets OAuth2 API*, sign in with Google, and save. Then open *Read Sheet Rows* and *Read Sheet (Digest)*, pick your spreadsheet in the *Document* field and the tab in the *Sheet* field, and select your credential in both nodes.
4. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Then open *OpenAI Chat Model* and *Summarize Changes* and select your credential in both.
5. **Create your Gmail credential** — in n8n go to *Credentials → New → Gmail OAuth2 API*, sign in, save. Open *Send Digest Email*, select your credential, and replace `you@example.com` with your own address.
6. **Activate** the workflow (toggle, top-right), then open the chat panel and ask a question about your sheet.

## Customize it

- **Change the digest time** — open *Digest Schedule* and edit the cron expression (e.g. `0 18 * * *` for 6:00 PM).
- **Change the model** — open *OpenAI Chat Model* or *Summarize Changes* and pick another model.
- **Add more context** — chain extra Set nodes before the agent to pull in more sheets or documents.
- **Digest to Slack instead** — swap *Send Digest Email* for a Slack node.
