---
title: "n8n Security Advisory Triage"
description: "Daily n8n security advisory triage: AI checks if your version is affected and sends urgent Telegram alerts for high/critical CVEs. Import-ready workflow."
date: 2026-10-04
category: "automation"
difficulty: "intermediate"
workflow: "/templates/n8n-security-advisory-triage.json"
integrations: ["GitHub", "OpenAI", "Google Sheets", "Telegram"]
---

## How it works

Your daily security guard for self-hosted n8n. In October 2026 GitHub published the largest single batch of n8n security advisories to date — 10 High + 4 Medium GHSA items, fixed in n8n 2.41.4 / 2.42.1. Miss those and your instance stays exposed. This workflow watches the GitHub Advisory Database and tells you within hours whether YOUR version is affected:

1. **STEP 1 — Daily trigger + fetch GitHub advisories** — a 7 AM schedule trigger pulls the latest n8n advisories from the GitHub Advisory Database (npm ecosystem). No auth needed.
2. **STEP 2 — Dedupe vs seen IDs + log NEW** — the workflow reads the GHSA IDs already in your Google Sheet, keeps only genuinely fresh advisories, and appends them with status `NEW`. On quiet days you just get a short all-clear Telegram message.
3. **STEP 3 — AI impact assessment vs YOUR version** — an AI Agent compares each advisory's vulnerable version range against your configured n8n version and returns a structured verdict (`severity`, `is_my_version_affected`, `patch_action`, one-line summary) via a Structured Output Parser. The sheet flips to `ASSESSED`.
4. **STEP 4 — Urgent alerts + daily digest** — advisories that affect your version AND are high or critical severity fire an instant 🚨 Telegram alert with the patch action and advisory link, and the sheet flips to `NOTIFIED_URGENT`. Both branches then merge into one daily digest on Telegram: new advisories triaged plus the urgent ones worth patching now.

**Status flow in Sheets:** `NEW` → `ASSESSED` → `NOTIFIED_URGENT`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- A Google Sheets OAuth2 credential — n8n Credentials → New → Google Sheets OAuth2 (Google account sign-in)
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- Your n8n version — in n8n: Settings → About

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `n8n-security-advisory-triage.json`.
2. **CONFIG — Instance** — open the Set node and fill in:
   - `n8n_version` — e.g. `2.41.6` (find it in n8n under Settings → About). This is what the AI compares against every advisory's vulnerable range.
   - `github_token` — optional, leave empty. Only add a token (generate one at [github.com/settings/tokens](https://github.com/settings/tokens)) if you ever hit GitHub's unauthenticated rate limit.
3. **CONFIG — Google Sheets** — create a Google Sheet with a tab named `Advisories` and headers: `GHSA ID | Published | Severity | Affected Versions | My Version Affected | Patch Action | Status`. Paste the spreadsheet ID into `spreadsheet_id`. Then select your Google Sheets credential in the four Sheets nodes.
4. **OpenAI** — select your OpenAI credential in the `OpenAI Chat Model — Assessment` node (`gpt-4o-mini` is the default; plenty for this task).
5. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential, and **activate** the workflow. The first run fires at 7 AM the next morning (use "Execute workflow" to test immediately).

## Customize it

- **Watch more than n8n** — change the `affects` query param in the `Fetch n8n Advisories` HTTP node (e.g. `affects=langchain`, or drop the filter and post-filter by ecosystem in the `Filter New Advisories` code node).
- **Lower the urgency bar** — in `Compute Urgency`, add `"moderate"` to the severity list so medium advisories affecting your version also fire instant alerts.
- **Add Slack alongside Telegram** — clone the `Telegram — URGENT Security Alert` node, swap in an n8n-nodes-base.slack node, and connect it to the same TRUE branch of `IF — Urgent?`.
- **Run hourly during active incident windows** — change the Schedule Trigger from daily 7 AM to hourly; the GHSA-ID dedupe keeps it safe at any cadence (GitHub allows 60 unauthenticated requests/hour, plenty for hourly polling).
- **Track patching** — add a `Patched` column to the sheet and flip `NOTIFIED_URGENT` rows manually after upgrading, so your history doubles as a patch log.
