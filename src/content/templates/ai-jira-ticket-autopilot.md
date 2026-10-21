---
title: "AI Jira Ticket Autopilot"
description: "AI triages your Jira tickets hourly — auto-resolves safe ones (comment + Done transition), escalates the rest, and sends your team a Telegram digest."
date: 2026-10-21
category: "automation"
difficulty: "intermediate"
workflow: "/templates/ai-jira-ticket-autopilot.json"
integrations: ["Jira","OpenAI","Google Sheets","Telegram"]
---

## How it works

This template is the idea from the n8n community forum thread **"N8n workflow idea: notify your team when an AI agent finishes a Jira ticket"** (Oct 21, 2026, 6 replies) — real teams asking for an AI agent that works Jira tickets and tells the team when it's done. Built end-to-end:

1. **STEP 1 — Fetch open Jira tickets** — `Hourly Trigger` fires every hour → `CONFIG — Jira + AI` holds your host, project key, and thresholds → `Build Jira Auth Header` base64-encodes your Jira email + API token into a `Basic` auth header (nothing hardcoded) → `Jira — Fetch Open Tickets` calls the Jira REST API `/rest/api/3/search` with JQL `project=<key> AND status in ("To Do","Open") ORDER BY created DESC` (25 max) → `Normalize Tickets` flattens each issue to key, summary, description (ADF → plain text), priority, status, reporter, created, and URL.
2. **STEP 2 — Dedupe + log NEW** — `Read Logged Ticket Keys` pulls ticket keys already in Google Sheets → `Filter New Tickets Only` drops anything already seen → `Log Tickets — Status NEW` appends fresh tickets to the sheet with status `NEW`.
3. **STEP 3 — AI triage with structured output** — `AI Ticket Triage Agent` (model `gpt-4o-mini` via `OpenAI Chat Model — Triage`) reads each ticket and returns a strict verdict through `Structured Output Parser — Triage`: `can_resolve` (boolean), `confidence` (0–100), `summary`, `category`, `resolution_comment`, and `escalation_reason`. The prompt is deliberately conservative — incidents, security issues, billing, customer data, or anything ambiguous gets escalated. → `Update Sheet — Status TRIAGED`.
4. **STEP 4 — Auto-resolve / escalate gate** — `IF — Auto-Resolve?` passes only tickets where `can_resolve` is true **and** confidence ≥ your `confidence_threshold` (75 by default). **TRUE branch:** `Jira — Add Resolution Comment` posts the AI's resolution comment (Jira ADF format) → `Jira — Get Transitions` fetches the ticket's available transitions → `Pick Done Transition` finds the transition named "Done" (and throws a clear error if your Jira workflow names it differently) → `Jira — Transition to Done` moves the ticket → `Jira — Add Resolved Label` tags it with your `label_resolved` label (`ai-resolved`) → `Build Resolved Record` rebuilds a clean record → `Update Sheet — Status RESOLVED`. **FALSE branch:** `Update Sheet — Status ESCALATED` records the AI's escalation reason for a human.
5. **STEP 5 — Team digest + Telegram** — `Merge — Combine Branches` collects both branches → `Build Team Digest` assembles one message: resolved count + escalated count, with per-ticket lines (key, confidence, summary, link) → `Telegram — Send Digest` pings your team.

**Status flow in Sheets:** `NEW` → `TRIAGED` → `RESOLVED` / `ESCALATED`

*How this differs from our [Shopify AI Support Agent](/templates/shopify-ai-support-agent/): that template answers incoming customer chats in real time — this one is a back-office autopilot that works your Jira queue on a schedule, resolves what it safely can, and only bothers humans with what it can't.*

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- Jira Cloud (free) — sign up at [atlassian.com](https://www.atlassian.com/software/jira) → create an API token at Atlassian account → Security → API tokens
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credential — n8n Credentials → Google Sheets OAuth2 ([sheets.google.com](https://sheets.google.com))
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `ai-jira-ticket-autopilot.json`.
2. **CONFIG — Jira + AI** — open the Set node and fill in:
   - `jira_host` — e.g. `yourcompany.atlassian.net` (no `https://`)
   - `jira_email` — the Atlassian account email the API token belongs to
   - `jira_api_token` — paste your token (replacing `PASTE_YOUR_JIRA_API_TOKEN`)
   - `project_key` — e.g. `PROJ`
   - `confidence_threshold` — `75` default; raise to 85+ to auto-resolve less, lower to 60 to auto-resolve more
   - `spreadsheet_id` — your Google Sheet ID (replacing `PASTE_YOUR_SPREADSHEET_ID`)
   - `sheet_name` — `TicketLog`
   - `telegram_chat_id` — where the team digest lands
   - `label_resolved` — `ai-resolved` default; change to match your team's label convention
3. **Google Sheet** — create a Google Sheet with a tab named `TicketLog` and these exact headers: `Ticket Key | Summary | Priority | Reporter | Ticket URL | Created | AI Summary | Category | Can Resolve | Confidence | Escalation Reason | Resolution Comment | Status`. Put the spreadsheet ID in `spreadsheet_id`, and select your Google Sheets credential in all five Sheets nodes (`Read Logged Ticket Keys`, `Log Tickets — Status NEW`, `Update Sheet — Status TRIAGED`, `Update Sheet — Status ESCALATED`, `Update Sheet — Status RESOLVED`).
4. **AI + notifications** — select your OpenAI credential in `OpenAI Chat Model — Triage` (model is `gpt-4o-mini` by default), select your Telegram credential in `Telegram — Send Digest`, and **activate** the workflow.
5. **First run** — run it once manually: check the sheet flips new tickets `NEW` → `TRIAGED`, and that auto-resolved tickets actually show the AI comment + `Done` status + `ai-resolved` label in Jira. If `Pick Done Transition` throws "No Done transition found", your Jira workflow names the terminal transition differently (e.g. "Closed") — either rename it in Jira or adjust the name match in that Code node.

## Customize it

- **Scope the JQL** — edit the `jql` query parameter in `Jira — Fetch Open Tickets`: add `AND priority in (High, Highest)` for a VIP queue, or `AND labels = bug` per team. Keep `maxResults` under 50 for heavy descriptions.
- **Tune the gate** — `confidence_threshold` at 85+ makes the agent very conservative (more escalations); the `systemMessage` in `AI Ticket Triage Agent` is where you encode your team's auto-resolve policy — add your own rules there (e.g. "never auto-resolve tickets tagged production").
- **Faster/slower cadence** — change `Hourly Trigger` to every 15 minutes for a hot queue, or daily for a low-volume project.
- **Different transition** — if your Done-equivalent is "Closed" or "Resolved", update the name match in `Pick Done Transition`.
- **Discord instead of Telegram** — swap `Telegram — Send Digest` for a Discord webhook node and reformat the lines in `Build Team Digest`.
- **Per-ticket notifications** — move the Telegram node before the merge to ping per resolved ticket instead of one digest.
