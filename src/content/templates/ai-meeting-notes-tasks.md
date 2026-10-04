---
title: "AI Meeting Notes → Tasks"
description: "Turn meeting transcripts into Notion tasks automatically: AI extracts action items, owners and due dates, posts a Slack summary. Import-ready n8n workflow."
date: 2026-10-04
category: "automation"
difficulty: "intermediate"
workflow: "/templates/ai-meeting-notes-tasks.json"
integrations: ["Google Drive", "OpenAI", "Notion", "Slack", "Google Sheets"]
---

## How it works

Never let a meeting decision die in a transcript again. Drop a transcript file into a Google Drive folder and the workflow does the rest:

1. **STEP 1 — Drive trigger + transcript extraction** — a Google Drive trigger fires when a new transcript lands in your folder (polled every 5 minutes), downloads the file, and a Code node decodes the binary into text (`.txt` and `.md` supported; long transcripts are truncated at ~12,000 characters with a note).
2. **STEP 2 — AI action-item extraction** — an AI Agent reads the transcript and, via a Structured Output Parser, returns a `meeting_summary` plus an `action_items` array — each with a task title, owner, due date (`YYYY-MM-DD`), and priority (`high` / `medium` / `low`). Items with no named owner fall back to your configured default owner.
3. **STEP 3 — Notion tasks + Sheets log** — the items are split into one item per action item; each becomes a page in your Notion Tasks database (`Name` / `Owner` / `Due` / `Priority` / `Source`), and every task is appended to the `Meeting Tasks` Google Sheet tab with status `CREATED`.
4. **STEP 4 — Slack summary + Telegram notification** — all items are aggregated into one meeting summary with a numbered task list (owner + due date + priority) and posted to your Slack channel; Telegram confirms how many tasks were created, listing the top 3.

**Status flow in Sheets:** `EXTRACTED` → `CREATED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Google Drive OAuth2 credential and a folder for transcripts — n8n Credentials → Google Drive OAuth2
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- A Notion integration — [notion.so/my-integrations](https://www.notion.so/my-integrations) → New integration, share your Tasks database with it
- A Slack OAuth2 credential — create an app at [api.slack.com/apps](https://api.slack.com/apps) (or [slack.com](https://slack.com)), connect it in n8n
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `ai-meeting-notes-tasks.json`.
2. **New Transcript Arrived** — open the Google Drive Trigger node and select your transcripts folder in `folderToWatch` (it polls every 5 minutes; change `pollTimes` if you prefer a different cadence). Select your Google Drive credential in this node and in **Download Transcript**.
3. **CONFIG — Task Routing** — open the Set node and fill in:
   - `notion_database_id` — paste your Notion Tasks database ID (open the database in Notion, copy the ID from its URL)
   - `slack_channel` — e.g. `#meetings` — the channel the summary posts to
   - `default_owner` — fallback assignee (e.g. your name) when the AI can't identify an owner
4. **Notion database** — create a database with exactly these columns: `Name` (title), `Owner` (text), `Due` (date), `Priority` (select with options `high`, `medium`, `low`), `Source` (text). Select your Notion credential in the **Notion — Create Task** node. If your property types differ, remap them in the node's property list.
5. **Google Sheet** — create a Google Sheet with a tab named `Meeting Tasks` and headers: `Date | Meeting File | Task | Owner | Due Date | Priority | Status`. Select your Google Sheets credential in the **Log Task — CREATED** node and pick the spreadsheet in the node.
6. **Slack — Post Meeting Summary** — select your Slack OAuth2 credential; the channel comes from `CONFIG — Task Routing`.
7. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in **Telegram — Notify — Tasks Created**, and **activate** the workflow.

Then save any meeting transcript (Fireflies, Otter.ai, Whisper — any tool, as `.txt` or `.md`) into the watched Drive folder and watch the tasks appear.

### Alternative trigger: Webhook instead of Drive

If your transcription tool can POST directly, skip Drive entirely: delete the **New Transcript Arrived**, **Download Transcript**, and **Extract Transcript Text** nodes, add a **Webhook** node as the new trigger, and have the tool POST JSON like `{"file_name": "standup-2026-10-04.txt", "transcript_text": "...", "meeting_date": "2026-10-04"}`. The rest of the chain (CONFIG → AI Agent → …) works unchanged.

## Customize it

- **No action items?** — if the AI finds nothing, the chain ends silently after the split. Add an IF (`task_count = 0`) + Telegram "nothing found" branch if you want confirmation.
- **Approval gate** — add a human-in-the-loop before **Notion — Create Task**: pause the workflow (n8n Wait node) and let someone review the extracted items first.
- **Archive processed transcripts** — add a Google Drive "move" node after extraction to file processed transcripts into an `Archive/` folder.
- **Per-team routing** — duplicate the Notion node and add an IF on file name (e.g. `standup` vs `sales-call`) to route tasks into different databases.
- **Richer Slack message** — the summary builder is plain JS; add mention formatting (`<@U123>`) if you map owners to Slack user IDs.
- **Cheaper model** — `gpt-4o-mini` is the default; long meetings can be summarized first with a cheaper pass, or raise the 12,000-char cap in **Extract Transcript Text** for very long transcripts (watch token costs).
