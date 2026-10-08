---
title: "AI Content Repurposer: 1 Transcript → 20 Posts"
description: "Turn 1 video transcript into an X thread, LinkedIn/Facebook posts, Instagram caption, newsletter section, quote cards, Shorts scripts + blog summary."
date: 2026-10-08
category: "automation"
difficulty: "intermediate"
workflow: "/templates/ai-content-repurposer.json"
integrations: ["openai", "google-sheets", "telegram"]
---

## How it works

Your one-click content multiplication machine: paste a video or podcast transcript once, and an AI agent rewrites it into ~20 platform-native pieces — an X thread, a LinkedIn post, a Facebook post, an Instagram caption, a newsletter section, quote cards, Shorts/Reels scripts, and a blog summary — all in your brand voice. Every piece is logged to Google Sheets and a per-platform count lands in your Telegram:

1. **STEP 1 — Trigger + paste your transcript** — `On Manual Trigger` fires, `CONFIG — Content Source` supplies the `source_title`, the `transcript_text` you paste in, your `brand_voice`, `target_audience`, and the `platforms_to_generate` list, and `CONFIG — Notifications` holds your Telegram chat ID.
2. **STEP 2 — Validate + log the source** — `Sheets — Log Source NEW` appends the transcript to the log with status `NEW`, then `IF — Transcript Not Empty` checks you actually pasted something. An empty transcript takes the failure branch: `Telegram — Empty Transcript Error` tells you to fix the config, so a blank run never wastes API calls.
3. **STEP 3 — AI repurposes the content** — `Sheets — Status PROCESSING` flips the run status, then `AI Agent — Repurpose Content` (gpt-4o-mini with `Structured Output Parser — Content Plan`) returns `x_thread`, `linkedin_post`, `facebook_post`, `instagram_caption`, `newsletter_section`, `quote_cards`, `shorts_scripts`, and `blog_summary` — written in your brand voice, for your target audience, with no invented facts.
4. **STEP 4 — Split + log every piece** — `Split Output Per Platform` turns the structured output into one item per post, `Sheets — Log Content Items` appends each row with status `PROCESSING`, `Build Completion Summary` counts the pieces per platform, and `Sheets — Log RUN_DONE` closes the run.
5. **STEP 5 — Completion digest** — `Telegram — Repurposing Complete` sends the per-platform counts. Copy each row's Content cell from the sheet and publish it wherever you like — X, LinkedIn, Facebook, Instagram, your newsletter.

**Status flow in Sheets:** `NEW` → `PROCESSING` → `DONE`

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- An OpenAI API key — [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `ai-content-repurposer.json`.
2. **CONFIG — Content Source** — open the Set node and fill in:
   - `source_title` — e.g. `Ep 12 — Automating Client Onboarding` (used in the sheet log and the Telegram digest)
   - `transcript_text` — paste the full video/podcast transcript here (replaces `PASTE_YOUR_TRANSCRIPT_HERE`)
   - `brand_voice` — e.g. `practical, no-fluff, contrarian` (the AI writes every piece in this voice)
   - `target_audience` — e.g. `solopreneurs and creators growing with AI automation`
   - `platforms_to_generate` — comma list of the output formats (default covers all eight)
3. **Content_Repurposing_Log sheet** — create a Google Sheet with a tab named `Content_Repurposing_Log` and headers: `Timestamp | Source Title | Content Type | Content | Status | Notes`. The four Sheets nodes (`Sheets — Log Source NEW`, `Sheets — Status PROCESSING`, `Sheets — Log Content Items`, `Sheets — Log RUN_DONE`) use the log tab name directly; select your Google Sheets OAuth2 credential and pick the sheet in each one.
4. **CONFIG — Notifications** — paste your chat ID into `telegram_chat_id` (replaces `PASTE_YOUR_TELEGRAM_CHAT_ID`).
5. **Connect OpenAI + Telegram** — select your OpenAI credential in `OpenAI Chat Model — Repurposer` (model is `gpt-4o-mini` by default), and your Telegram Bot API credential in `Telegram — Repurposing Complete` and `Telegram — Empty Transcript Error`.
6. **Test, then activate** — run once manually, confirm the sheet shows `NEW` → `PROCESSING` → `DONE` and every piece appears as its own row, check the Telegram digest counts, then activate the workflow.

> **Note:** a full 30-minute transcript costs roughly 3 cents per run on gpt-4o-mini (about 1M input tokens per $0.15). Long transcripts are automatically truncated to 500 characters in the source-log row so the sheet stays readable — the AI still sees the full text.

## Customize it

- **Auto-transcribe from YouTube** — add an HTTP Request node to a transcription API (or a Whisper step) before the config, so pasting a video URL is all you need instead of a transcript.
- **Platform toggles** — keep a `Platforms` sheet (platform, enabled) and add an IF per format before `Split Output Per Platform`, so one run can target only the platforms you publish on that day.
- **Schedule it weekly** — swap the Manual Trigger for a Schedule Trigger that reads the week's newest transcript from a `Content Queue` sheet and repurposes each one automatically.
- **Human review gate** — change the `Status` the content items log with from `PROCESSING` to `NEEDS_REVIEW`, and only flip to `DONE` after you've edited each piece.
- **Auto-post the X thread** — add an X (Twitter) node after `Split Output Per Platform` that posts items with `Content Type = x_tweet` in order, turning the digest into a publish pipeline.
