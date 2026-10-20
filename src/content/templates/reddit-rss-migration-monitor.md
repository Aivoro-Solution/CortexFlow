---
title: "Reddit RSS Migration Monitor"
description: "Migrate your dying Reddit RSS feeds before the Nov 13, 2026 shutdown: daily AI-scored monitoring via a swappable JSON source, with a Telegram heartbeat."
date: 2026-10-20
category: "automation"
difficulty: "intermediate"
workflow: "/templates/reddit-rss-migration-monitor.json"
integrations: ["Reddit", "OpenAI", "Google Sheets", "Telegram"]
---

## How it works

Reddit is killing RSS feeds on **Nov 13, 2026** (and its public API ends **March 2027**), which will silently break every n8n workflow built on `.rss` monitoring. This is your migration kit:

1. **STEP 1 — Bring your old RSS feeds** — a daily 9 AM schedule trigger reads your old `.rss` URLs from `CONFIG — RSS Migration`. `Parse Old RSS Feed URLs` extracts the subreddit + search query from each URL (e.g. `/r/n8n/search.rss?q=webhook` → subreddit `n8n`, query `webhook`) and maps old RSS fields to their Reddit JSON equivalents: `<title>` → `title`, `<link>` → `permalink`, `<pubDate>` → `created_utc`, `<guid>` → post ID for dedupe.
2. **STEP 2 — Fetch through a swappable source** — `IF — JSON Source Selector` routes on `json_source`. With `reddit_public` (the default) it calls Reddit's public `.json` API with a polite `User-Agent: n8n-cortexflow-template/1.0` header — no API key needed. Set `json_source` to `custom` and it switches to `Fetch Reddit — Custom JSON Source`, which hits your `custom_json_url` (an Apify actor or any JSON proxy returning Reddit-shaped JSON) — ready-made for the March 2027 public-API shutdown.
3. **STEP 3 — Normalize, dedupe, log NEW** — `Normalize Reddit Posts — RSS Field Map` flattens the JSON and applies your `watch_keywords`, `min_upvotes`, and `days_back` freshness filters. `Read Logged Post IDs` → `Filter New Posts Only` drops already-seen post IDs, and the rest are appended to Google Sheets with status `NEW`.
4. **STEP 4 — AI relevance scoring** — an AI Agent reads each post against your `business_description` and returns a structured verdict via a Structured Output Parser: `relevance_score` (0–100), `verdict` (`HIGHLY_RELEVANT` / `RELEVANT` / `LOW` / `IGNORE`), `why_relevant`, and a `suggested_action`. The sheet flips to `SCORED`.
5. **STEP 5 — Relevance gate** — posts scoring at or above `min_relevance_score` pass `IF — Relevance ≥ Threshold` into `Merge — Collect Alert Posts`; below-threshold posts are first marked `IGNORED` in the sheet, then join the merge.
6. **STEP 6 — Digest + heartbeat** — `Build Migration Digest` assembles one Telegram digest — score, link, verdict, and why-it-matters per post. On days with nothing relevant it sends a 💓 heartbeat instead, so a silently broken source (rate limit, blocked endpoint, post-March-2027 API death) shows up as a missing message. The sent posts flip to `SENT` via `Expand Sent URLs` → `Update Sheet — Status SENT`.

**Status flow in Sheets:** `NEW` → `SCORED` → `SENT` (+ `IGNORED` for below-threshold posts)

*How this differs from our [Reddit Intent Lead Finder](/templates/reddit-intent-lead-finder/): that template hunts buying-intent conversations with `search.json` + intent keywords — this one is the migration path for your dying RSS feeds, with feed-URL migration, a swappable source, and a heartbeat so a broken source can't go unnoticed.*

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- Your old Reddit `.rss` feed URLs — grab them from your existing workflows **before Nov 13, 2026**
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credential — n8n Credentials → Google Sheets OAuth2 ([sheets.google.com](https://sheets.google.com))
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `reddit-rss-migration-monitor.json`.
2. **CONFIG — RSS Migration** — open the Set node and fill in:
   - `old_rss_feeds` — one old `.rss` URL per line (e.g. `https://www.reddit.com/r/n8n/new.rss` or `https://www.reddit.com/r/selfhosted/search.rss?q=automation&restrict_sr=on&sort=new`)
   - `json_source` — `reddit_public` today; switch to `custom` after March 2027 and paste your Apify/JSON-proxy endpoint into `custom_json_url`
   - `min_upvotes` (5) and `days_back` (7) — engagement floor and freshness window
   - `watch_keywords` — comma-separated terms that must appear in the title or body
   - `business_description` — what you sell or monitor for (the AI prompt is built from this, so be specific)
   - `telegram_chat_id` — where the digest and heartbeat land
3. **CONFIG — Google Sheets** — create a Google Sheet with a tab named `RedditMonitor` and these exact headers: `Date | Post ID | Subreddit | Title | Post URL | Author | Upvotes | Comments | Created At | Relevance Score | Verdict | Why Relevant | Suggested Action | Status`. Put the spreadsheet ID in `spreadsheet_id`, and select your Google Sheets credential in all five Sheets nodes (`Read Logged Post IDs`, `Log Posts — Status NEW`, `Update Sheet — Status SCORED`, `Update Sheet — Status IGNORED`, `Update Sheet — Status SENT`).
4. **AI scoring** — select your OpenAI credential in `OpenAI Chat Model — Relevance Scoring` (model is `gpt-4o-mini` by default), and set your `min_relevance_score` in `CONFIG — AI Scoring`.
5. **Notifications** — select your Telegram credential in `Telegram — Send Digest`, and **activate** the workflow. If the daily heartbeat ever stops arriving, your JSON source is broken — check the workflow's execution log first.

## Customize it

- **After March 2027** — point `custom_json_url` at an Apify actor run endpoint (e.g. their Reddit scraper) or any JSON proxy that returns Reddit-shaped JSON (`data.children[].data`), flip `json_source` to `custom`, done. No other node changes.
- **Tune the funnel** — raise `min_relevance_score` to 75+ when volume is high, or loosen `min_upvotes` to 0 to catch fresh threads in slow subreddits.
- **More feeds** — every `.rss` line becomes fetch specs; `/r/<sub>/new.rss` polls the newest posts, `/r/<sub>/search.rss?q=...` searches, `/search.rss?q=...` searches all of Reddit. Keep total lines under ~20 per run to stay polite.
- **Discord instead of Telegram** — swap the Telegram node for a Discord webhook node and reformat the digest lines in `Build Migration Digest`.
- **Track replies** — add a `Replied` column to the sheet; you already get `suggested_action` per post from the AI.
- **Migration audit** — before Nov 13, run the workflow once manually and compare the fetched titles against your old RSS reader output: they should match post-for-post, proving the JSON replacement is faithful.
