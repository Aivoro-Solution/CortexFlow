---
title: "Reddit Intent Lead Finder"
description: "Scan Reddit daily for high-intent buying conversations, AI-score them 0-100, and get Telegram alerts with reply angles."
date: 2026-10-05
category: "automation"
difficulty: "intermediate"
workflow: "/templates/reddit-intent-lead-finder.json"
integrations: ["Reddit", "OpenAI", "Google Sheets", "Telegram"]
---

## How it works

Your automated Reddit scout that finds people actively asking for what you sell — before your competitors do:

1. **STEP 1 — Scan Reddit daily** — a daily 9 AM schedule trigger reads your subreddits and search keywords from `CONFIG — Reddit Intent Finder`, expands them into every subreddit × keyword pair, and queries Reddit's public `search.json` API (no API key needed, just a polite `User-Agent` header).
2. **STEP 2 — Filter + dedupe + log NEW** — the results are flattened and filtered: a post must have at least `min_upvotes` upvotes, `min_comments` comments, AND contain one of your `intent_keywords` (e.g. "looking for", "recommend", "alternative to") in its title or selftext. Posts already logged in your sheet are dropped, and the rest are appended to Google Sheets with status `NEW`.
3. **STEP 3 — AI intent scoring** — an AI Agent reads each post against your `business_description` and returns a structured verdict via a Structured Output Parser: `intent_score` (0–100), `category` (`BUYING_INTENT` / `PROBLEM_MATCH` / `BRAND_MENTION` / `IGNORE`), a `suggested_angle` for your reply, and `reasoning`. The sheet flips to `SCORED`.
4. **STEP 4 — Intent gate + Telegram digest** — only posts scoring at or above `min_intent_score` with a category other than `IGNORE` pass the IF gate. They are merged into one Telegram digest — score, link, category, and reply angle per lead — and the sheet flips those rows to `ALERTED`. Days with no hot leads still send a short "nothing today" note so you know the scan ran.

**Status flow in Sheets:** `NEW` → `SCORED` → `ALERTED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credential — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `reddit-intent-lead-finder.json`.
2. **CONFIG — Reddit Intent Finder** — open the Set node and fill in:
   - `subreddits` — comma-separated, without `r/` (e.g. `smallbusiness,Entrepreneur,marketing`)
   - `search_keywords` — comma-separated phrases to search (e.g. `looking for a tool,software for,automate,alternative to`)
   - `intent_keywords` — phrases that must appear in the title or body (e.g. `looking for,recommend,anyone know,best tool for,alternative to,how do you`)
   - `min_upvotes` (10), `min_comments` (3) — engagement floor filters out ghost threads
   - `min_intent_score` (70) — only leads at or above this reach your Telegram
   - `business_description` — what you sell, who it's for, key differentiators (the AI prompt is built from this, so be specific)
   - `days_back` (7) — how far back the Reddit search window goes
3. **CONFIG — Google Sheets** — create a Google Sheet with a tab named `Leads` and these exact headers: `Date | Subreddit | Title | Post URL | Author | Upvotes | Comments | Intent Score | Category | Suggested Angle | Reasoning | Status`. Put the spreadsheet ID in `sheet_doc_id` inside `CONFIG — Reddit Intent Finder`, and select your Google Sheets credential in all four Sheets nodes (`Read Logged Post URLs`, `Log Leads — Status NEW`, `Update Sheet — Status SCORED`, `Update Sheet — Status ALERTED`).
4. **AI scoring** — select your OpenAI credential in `OpenAI Chat Model — Intent Scoring` (model is `gpt-4o-mini` by default).
5. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in `Telegram — Send Lead Digest`, and **activate** the workflow.

## Customize it

- **More subreddits, more keywords** — every subreddit × keyword pair becomes one API call; keep total pairs under ~40 per run to stay polite to Reddit's public API.
- **Tune the funnel** — raise `min_intent_score` to 80+ when volume is high, or loosen `min_upvotes` to 5 to catch brand-new threads early.
- **Track outreach** — add a `Replied` column to the sheet and a timestamp column for when you commented; your future self will thank you.
- **Smarter windows** — `days_back` maps automatically: 1 → today's posts, ≤7 → this week, ≤30 → this month; use 1 for hot/fast subreddits.
- **Multiple businesses** — duplicate the workflow and give each copy its own `business_description`, sheet, and Telegram chat.
- **Etiquette (read this)** — this workflow finds conversations; it does not earn trust for you. Reply helpfully first and sell never: answer the question, mention your tool only if it's genuinely the best fit, read each subreddit's self-promotion rules before posting, disclose affiliation where required, and never automate the replies themselves — spammy accounts get banned and burn your brand.
