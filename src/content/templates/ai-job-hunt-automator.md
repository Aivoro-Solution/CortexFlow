---
title: "AI Job Hunt Automator"
description: "Daily job search → AI scores each posting against your resume (0-100) → tailored cover letters for top matches → Telegram digest. Import-ready n8n workflow."
date: 2026-10-04
category: "automation"
difficulty: "intermediate"
workflow: "/templates/ai-job-hunt-automator.json"
integrations: ["JSearch (RapidAPI)", "OpenAI", "Google Sheets", "Google Docs", "Telegram"]
---

## How it works

Your personal job-hunting assistant that runs every morning while you sleep:

1. **STEP 1 — Fetch new job listings** — a daily 9 AM schedule trigger fires the JSearch API (RapidAPI, aggregates Google Jobs) with your keywords and location, then normalizes every posting into title, company, location, URL, and description.
2. **STEP 2 — Dedupe + log to Google Sheets** — the workflow reads the job URLs already in your sheet, keeps only genuinely new postings, and appends them with status `NEW`.
3. **STEP 3 — AI resume match scoring** — an AI Agent compares each job against your resume and returns a structured score (0–100), a verdict (`STRONG_MATCH` → `NO_MATCH`), top strengths, and key gaps via a Structured Output Parser. The sheet flips to `SCORED`.
4. **STEP 4 — Cover letters for top matches** — jobs scoring at or above your threshold get a tailored cover letter (max 250 words, referencing your real achievements) written by a second AI Agent, saved to Google Docs, and the sheet flips to `COVER_LETTER_READY`. Below-threshold jobs skip this step automatically.
5. **STEP 5 — Daily digest** — both branches merge into one Telegram message: how many new jobs were scanned plus your strong matches with direct apply links.

**Status flow in Sheets:** `NEW` → `SCORED` → `COVER_LETTER_READY`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A RapidAPI key with the **JSearch API** subscribed — [rapidapi.com](https://rapidapi.com) → search "JSearch" → Subscribe (free tier available)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets + Google Docs OAuth2 credentials — n8n Credentials → Google Sheets OAuth2 / Google Docs OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `ai-job-hunt-automator.json`.
2. **CONFIG — Job Search** — open the Set node and fill in:
   - `keywords` — e.g. `AI engineer`, `Python developer`
   - `location` — e.g. `Remote`, `Bangalore`
   - `max_results` — how many postings to process per run (start with 20)
   - `rapidapi_key` — paste your RapidAPI key
3. **CONFIG — Google Sheets** — create a Google Sheet with a tab named `Jobs` and headers: `Date Found | Job Title | Company | Location | Job URL | Match Score | Verdict | Key Gaps | Status`. Paste the spreadsheet ID into `spreadsheet_id`. Then select your Google Sheets credential in the three Sheets nodes.
4. **CONFIG — AI Scoring** — paste your resume text into `resume_text` (or store it in Drive and reference it), set `match_threshold` (70 is a good start), and pick your model. Select your OpenAI credential in both chat model nodes.
5. **Cover letter docs** — select your Google Docs credential in the Google Docs node; letters are created in your Drive root by default (set a folder in the node if you prefer).
6. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential, and **activate** the workflow.

## Customize it

- **Different job board** — swap the JSearch HTTP node for the Adzuna API (free tier) or any jobs API; only the `Normalize Job Listings` code node needs remapping.
- **Stricter/looser matching** — raise `match_threshold` to 80+ for senior roles, lower it to 60 when exploring new domains.
- **Auto-apply?** — deliberately not included: auto-submitting applications can violate job board terms and hurt your reputation. The workflow prepares everything; you click apply.
- **Track applications** — add an `Applied` / `Interview` / `Rejected` column to the sheet and update statuses manually for a full pipeline view.
- **Weekly instead of daily** — change the Schedule Trigger interval; the dedupe logic keeps it safe at any cadence.
- **Cheaper scoring** — `gpt-4o-mini` is already the default; for very high volumes, batch the scoring step or score only jobs from target companies with an extra IF filter.
