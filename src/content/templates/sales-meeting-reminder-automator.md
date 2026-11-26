---
title: "Sales Meeting Reminder Automator — CRM Poll, AI-Personalized SMS + Email, Send-Once Guard"
description: "Polls Pipedrive every 15 min for meetings due in ~1 hour, sends an AI-personalized SMS + email reminder once, and logs every send in Google Sheets."
date: 2026-11-26
category: "automation"
difficulty: "intermediate"
workflow: "/templates/sales-meeting-reminder-automator.json"
integrations: ["Pipedrive", "Google Sheets", "OpenAI", "Gmail", "Telegram", "SMS via HTTP"]
---

## How it works

One hour before a sales meeting, your prospect gets a short text and an email that name the meeting time and one real detail from the CRM — no manual chasing, no double reminders. Built for the exact setup salespeople keep asking for on the [n8n forum](https://community.n8n.io/t/spoonfeed-me-great-people-of-n8n/): a Pipedrive meeting should trigger a text (from your CloudTalk/Twilio-style number) plus an email, automatically. The workflow polls on a schedule instead of using a Wait node, which is the reliable pattern — a Wait-based design breaks the moment a meeting is rescheduled or the workflow restarts.

1. **STEP 1 — Poll the CRM for meetings due in ~1 hour** — the "Every 15 Minutes Trigger" fires, "CONFIG — Reminder Settings" supplies the window and timezone, and "Fetch Meetings — Pipedrive Activities" pulls open meetings (`type=meeting`, `done=0`) from the Pipedrive API. "Normalize Meetings — Window + Timezone" keeps only meetings due in the next 55–65 minutes, converts the CRM's UTC times into your `instance_timezone` for display, drops internal attendees (anyone whose email ends with your `internal_email_domain`), picks the first external prospect, and normalizes their phone number to E.164 format (e.g. `+14155550123`) so SMS providers accept it.
2. **STEP 2 — Send-once guard + log to Google Sheets** — "Read Reminder Log" reads the `ReminderLog` tab and "Dedupe — Send-Once Guard" skips any `activity_id` already marked `REMINDER_SENT`, so overlapping runs can never text a prospect twice. New meetings are written by "Log Reminder — Status NEW" and immediately flipped to `PROCESSING` by "Update Sheet — Status PROCESSING", both keyed on `activity_id`.
3. **STEP 3 — AI writes the reminder** — "AI Agent — Write Reminder" (gpt-4o-mini via "OpenAI Chat Model — Reminder") drafts the copy through "Structured Output Parser — Reminder Copy", which returns `sms_text`, `email_subject`, `email_body`, and `personalization_notes`. The prompt only allows facts passed in from the CRM — meeting time, company, title, note — so the AI names one concrete detail instead of inventing one.
4. **STEP 4 — Send SMS + email (independent branches)** — "Send SMS — Provider API" POSTs the text to your SMS provider and "Gmail — Send Reminder Email" sends the email, in parallel. Both nodes are set to continue on error, so a failed text never swallows the email (or vice versa). "Mark SMS Result" and "Mark Email Result" tag each outcome `SENT`/`FAILED`, "Merge — Combine Channel Results" joins the branches, and "Evaluate Send Results" decides the final status: `REMINDER_SENT` if at least one channel succeeded, `FAILED` otherwise.
5. **STEP 5 — Final status + Telegram summary** — "Update Sheet — Final Status" writes the final status, per-channel results, and `sent_at` back to `ReminderLog`. "Build Run Summary" then composes a digest and "Telegram — Send Run Summary" sends it to your chat, so you can see at a glance which prospects were reminded.

**Status flow (ReminderLog tab):** `NEW` → `PROCESSING` → `REMINDER_SENT` / `FAILED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Pipedrive account — [pipedrive.com](https://www.pipedrive.com); your API token is under Settings → Personal preferences → API
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- A Gmail OAuth2 credential — n8n Credentials → Gmail OAuth2
- An SMS provider with an HTTP API — e.g. [CloudTalk](https://www.cloudtalk.io) or [Twilio](https://www.twilio.com) — plus a sender number in E.164 format
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `sales-meeting-reminder-automator.json`.
2. **CONFIG — Reminder Settings** — open the Set node and fill in:
   - `crm_base_url` — `https://api.pipedrive.com/v1` (change only if your Pipedrive company domain uses a different API host)
   - `reminder_window_min_minutes` / `reminder_window_max_minutes` — `55` / `65` by default; together with the 15-minute poll this targets "about 1 hour before"
   - `instance_timezone` — the timezone your prospects should see, e.g. `America/New_York`. This must match how you read meeting times — a mismatch here is the #1 cause of reminders naming the wrong hour
   - `internal_email_domain` — your company domain without the `@`, e.g. `yourcompany.com`; attendees on this domain are never treated as prospects
   - `sms_provider_url` — your SMS provider's send endpoint
   - `sms_sender_number` — your sending number in E.164 format, e.g. `+14155550123`
   - `from_email` — the name/address the reminder signs off with
   - `spreadsheet_id` — your Google Sheet ID (for reference; the Sheets nodes select the document directly in step 3)
   - `telegram_chat_id` — where the run summary goes
3. **Google Sheets tab** — in that spreadsheet create one tab named `ReminderLog` with these exact headers in row 1: `activity_id | prospect_name | prospect_email | prospect_phone | meeting_title | due_at | status | sms_result | email_result | sent_at`. Then select your Google Sheets credential and the spreadsheet in all four Sheets nodes: "Read Reminder Log", "Log Reminder — Status NEW", "Update Sheet — Status PROCESSING", and "Update Sheet — Final Status".
4. **Pipedrive credential** — in "Fetch Meetings — Pipedrive Activities", create/select a Header Auth credential: header name `x-api-token`, value = your Pipedrive API token. (If your account uses OAuth instead, switch the node's authentication to your Pipedrive OAuth credential — the query parameters stay the same.)
5. **AI copy** — select your OpenAI credential in "OpenAI Chat Model — Reminder" (model is `gpt-4o-mini` by default). No prompt editing needed — the agent reads the timezone and sender from CONFIG — Reminder Settings.
6. **SMS + email sending** — in "Send SMS — Provider API", select your SMS provider's Header Auth credential and adjust the JSON body keys (`to`, `from`, `text`) if your provider expects different field names. Select your Gmail credential in "Gmail — Send Reminder Email". Both nodes already continue on error — leave that setting as is.
7. **Telegram summary + activate** — select your Telegram credential in "Telegram — Send Run Summary", then **activate** the workflow. Test it by creating a Pipedrive meeting roughly 60 minutes out with an external attendee who has a phone number and email, and watch the execution: the row should walk `NEW` → `PROCESSING` → `REMINDER_SENT` in `ReminderLog`.

## Customize it

- **Reminder lead time** — widen or shift the window in CONFIG — Reminder Settings (e.g. `25`/`35` for ~30 minutes before). Keep the window at least as wide as your poll interval or meetings can slip between runs; if you poll every 5 minutes, a 10-minute window still works.
- **Different CRM** — swap "Fetch Meetings — Pipedrive Activities" for your CRM's activities endpoint and adjust the field mapping at the top of "Normalize Meetings — Window + Timezone" (due date/time, participants, person phone/email). Everything downstream — dedupe, AI copy, sending, logging — stays unchanged.
- **Phone country default** — bare 10-digit numbers are normalized to `+1…` (US) in the `toE164` helper inside "Normalize Meetings — Window + Timezone". Change the default country code there if your prospects are elsewhere, or store full E.164 numbers in the CRM.
- **Retry failed sends** — rows ending in `FAILED` are not retried automatically. To retry, extend "Dedupe — Send-Once Guard" to also pass `FAILED` rows whose `sent_at` is older than your poll interval — the send-once guard still protects `REMINDER_SENT` rows from duplicates.
- **Richer personalization** — add CRM fields (deal stage, last note, meeting link) to the output of "Normalize Meetings — Window + Timezone" and reference them in the "AI Agent — Write Reminder" prompt. Keep the "only facts provided" rule — it is what stops the AI from inventing a meeting link that doesn't exist.
- **Skip weekends / business hours** — add an IF node after "Every 15 Minutes Trigger" that checks the current time in `instance_timezone` and stops the run outside your sending hours.
