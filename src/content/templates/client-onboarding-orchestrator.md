---
title: "Client Onboarding Orchestrator"
description: "New client webhook → Notion project, Drive folder, Slack channel, welcome email, kickoff event. Import-ready n8n workflow."
date: 2026-10-04
category: "automation"
difficulty: "beginner"
workflow: "/templates/client-onboarding-orchestrator.json"
integrations: ["Notion", "Google Drive", "Slack", "Gmail", "Google Calendar", "Google Sheets"]
---

## How it works

Point your CRM, form, or checkout at one webhook and the whole onboarding happens by itself:

1. **STEP 1 — Webhook intake + log RECEIVED** — a POST to `/new-client` (JSON: `name`, `email`, `company`) hits the Webhook node, reads your **CONFIG — Business** settings, slugifies the company name into a Slack-safe channel name, and appends a row to your `Clients` sheet tab with status `RECEIVED`.
2. **STEP 2 — Provision the client workspace** — creates a Notion project page in your database, a Google Drive folder under your parent folder, and a Slack channel (`client-<slug>`), then posts a welcome message in the channel tagging you with links to the Notion page and Drive folder. Every provisioning node runs with `onError: continueErrorOutput` — any failure jumps straight to the STEP 4 alert chain.
3. **STEP 3 — Welcome email + kickoff → WELCOMED** — the sheet flips to `PROVISIONED`, a Gmail welcome email goes to the client (what happens next, timeline, contact), the kickoff date is computed (N days out at 10:00, 45 min), a Google Calendar event is created with the client invited, and the sheet flips to `WELCOMED`.
4. **STEP 4 — Failure alerts + Telegram summary** — if any step (Notion / Drive / Slack channel / Gmail / Calendar) fails, the owner gets a Slack alert in `#general` with the client name, email, and the error message, and the sheet row flips to `FAILED`. On the happy path, Telegram sends the 🎉 client-onboarded summary with all the links.

**Status flow in Sheets:** `RECEIVED` → `PROVISIONED` → `WELCOMED` (or `FAILED`)

## Set up steps

You'll need:

- n8n (self-hosted or [n8n Cloud](https://n8n.io))
- A Notion integration — [notion.so/my-account/integrations](https://www.notion.so/my-account/integrations) → New integration → share your client-projects database with it. The database ID is the 32-character hex in the database URL (after the last `/`, before any `?`). Your database needs a **title property named `Name`** — the workflow only sets that one.
- Google Drive + Google Calendar + Gmail + Google Sheets OAuth2 credentials — n8n Credentials → New → Google Drive OAuth2 API / Google Calendar OAuth2 API / Gmail OAuth2 / Google Sheets OAuth2, sign in with Google.
- A Slack app — [api.slack.com/apps](https://api.slack.com/apps) → Create New App → OAuth & Permissions → add the `channels:write` and `chat:write` bot scopes → Install to Workspace → copy the Bot User OAuth Token into an n8n **Slack OAuth2 API** credential. (Use `groups:write` instead if you want private channels.)
- A Google Sheet with a tab named exactly `Clients` and these headers in row 1: `Date | Name | Email | Company | Notion Page | Drive Folder | Slack Channel | Status`
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `client-onboarding-orchestrator.json`.
2. **CONFIG — Business** — open the Set node and fill in:
   - `notion_database_id` — your Notion client-projects database ID (32-char hex from the database URL)
   - `drive_parent_folder_id` — the Drive folder ID from the parent folder's URL (`drive.google.com/drive/folders/<ID>`)
   - `slack_channel_prefix` — `client-` by default; channels become e.g. `client-acme-corp`
   - `owner_email` — your email, used in the Slack welcome post
   - `kickoff_days_ahead` — `3` by default; the kickoff call lands N days out at 10:00, 45 minutes
3. **Clients sheet** — create the sheet + tab + headers listed above, then in each of the four Google Sheets nodes (RECEIVED append, PROVISIONED / WELCOMED / FAILED updates) select your Google Sheets credential and pick your spreadsheet. The matching column for the updates is `Email`.
4. **Select credentials** — Notion API in *Notion — Create Project Page*, Google Drive API in *Drive — Create Client Folder*, Slack API in both Slack nodes and the failure alert (change `#general` to your own alerts channel), Gmail API in *Gmail — Send Welcome Email*, Google Calendar API in *Calendar — Create Kickoff Event* (creates events on your `primary` calendar — change it in the node if needed).
5. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential, and **activate** the workflow.
6. **Test it** — POST to the webhook URL: `{"name": "Jane Doe", "email": "jane@example.com", "company": "Acme Corp"}` and watch the row move `RECEIVED` → `PROVISIONED` → `WELCOMED`.

## Customize it

- **Real @mention in Slack** — the welcome post and the failure alert use your email; for a true mention, hardcode your Slack user ID as `<@U12345678>` in the message text.
- **Private Slack channels** — switch the Slack app scope to `groups:write` and add `"isPrivate": true` under the channel node's options.
- **Different kickoff timing** — change `kickoff_days_ahead` in **CONFIG — Business**, or edit the `setHours(10, 0, 0, 0)` line in *Code — Compute Kickoff Date* for a different time of day.
- **Add a contract step** — insert a DocuSign / PandaDoc node between the welcome email and the kickoff event, and add a `Contract` column to the sheet.
- **Skip a channel** — don't need Drive folders? Delete the node and remove its reference from the Sheets PROVISIONED update — the error chain reroutes automatically.
- **CRM instead of Sheets** — swap the four Sheets nodes for your CRM's create/update nodes; the status values (`RECEIVED` / `PROVISIONED` / `WELCOMED` / `FAILED`) map 1:1 to pipeline stages.
