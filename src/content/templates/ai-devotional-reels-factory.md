---
title: "AI Devotional Reels Factory"
description: "Turn a Telegram photo + idea into a cinematic devotional reel — NanoBanana keyframe, VEO3 video, auto-posted to 5 platforms via Blotato. Import-ready n8n workflow."
date: 2026-10-02
category: "automation"
difficulty: "advanced"
workflow: "/templates/ai-devotional-reels-factory.json"
integrations: ["Telegram", "OpenAI", "NanoBanana (fal.ai)", "VEO3 (kie.ai)", "Blotato", "Google Sheets", "Google Drive"]
---

## How it works

Send a deity or scene photo with a caption idea to your Telegram bot — the workflow does the rest:

1. **Telegram Trigger collects the idea** — every photo message (with caption) fires the workflow via webhook.
2. **The photo is archived** — the file is pulled from Telegram, uploaded to Google Drive, and logged in Google Sheets with status `RECEIVED`.
3. **GPT-4o Vision analyzes the photo** — it outputs a structured YAML description (subject, colors, setting, mood) so every later step stays faithful to the reference.
4. **NanoBanana creates the keyframe** — an AI agent writes a devotional keyframe prompt (diya glow, marigold tones, cinematic realism), fal.ai renders it, and the result is downloaded.
5. **An AI agent writes the reel script** — using a structured master prompt, it outputs a title plus a full VEO3-ready JSON prompt (camera, lighting, motion, VFX, audio).
6. **VEO3 generates the vertical video** — kie.ai renders a 9:16 reel from the keyframe image, then the workflow polls until it's ready.
7. **GPT-4o writes the Hindi caption** — a reverent Devanagari caption under 150 characters with bhakti hashtags.
8. **Blotato posts everywhere** — the video is uploaded once and published to Instagram, YouTube Shorts, TikTok, Facebook, and X in parallel; the sheet flips to `Published` and you get a Telegram confirmation.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- A Telegram bot token — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- A kie.ai API key — [kie.ai](https://kie.ai) → API keys (for VEO3)
- A fal.ai API key — [fal.ai](https://fal.ai) → Keys (for NanoBanana)
- A Blotato account with API access — [blotato.com](https://blotato.com) → Settings → API, and connect your Instagram, YouTube, TikTok, Facebook, and X accounts there
- A Google account — for Drive and Sheets (OAuth sign-in inside n8n)

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Telegram** — *Credentials → New → Telegram*, paste your bot token. Select it in *Telegram Trigger: Receive Reel Idea*, *Telegram: Get Photo File*, *Send Final Reel Preview*, and *Telegram: Send Published Notification*. Then open the *Set: Bot Token* node and paste the same token into `YOUR_BOT_TOKEN`.
4. **OpenAI** — *Credentials → New → OpenAI*, paste your API key. Select it in *OpenAI Vision: Analyze Photo*, *LLM: OpenAI Chat*, *OpenAI Chat Model*, and *Rewrite Caption with GPT-4o*.
5. **kie.ai** — *Credentials → New → Header Auth*, name it `kie.ai API Key`, set Name to `Authorization` and Value to `Bearer YOUR_KIE_KEY`. Select it in *Generate Video with VEO3* and *Download Video from VEO3*.
6. **fal.ai** — *Credentials → New → Header Auth*, name it `fal.ai API Key`, set Name to `Authorization` and Value to `Key YOUR_FAL_KEY`. Select it in *NanoBanana: Create Image* and *Download Edited Image*.
7. **Google** — create a *Google Drive OAuth2* credential and a *Google Sheets OAuth2* credential (n8n walks you through Google sign-in). Select them in the Drive/Sheets nodes. Create a tracker sheet with columns `IMAGE NAME, IMAGE URL, IMAGE DESCRIPTION, CAPTION, TITRE VIDEO, CAPTION VIDEO, URL VIDEO FINAL, STATUS`, then open each Google Sheets node and pick your document and sheet.
8. **Blotato** — in n8n, enable *Verified Community Nodes* under *Settings*, install the **Blotato** node, then *Credentials → New → Blotato* and paste your API key. Select it in *Upload Video to BLOTATO* and each platform node, then pick the right social account in every platform node.
9. **Activate** the workflow, then send your bot a photo with a caption like "Radha Krishna at Vrindavan ghat at dawn".

## Customize it

- **More platforms** — duplicate any Blotato platform node, pick another platform (LinkedIn, Threads, Bluesky, Pinterest), and wire it into the *Merge* node (raise *Number of inputs* to match).
- **Different video ratio** — edit the *Format Prompt* code node: change `aspectRatio` to `"16:9"` for YouTube-style landscape.
- **Caption language** — edit the prompt in *Rewrite Caption with GPT-4o* to write in English or Hinglish instead of Hindi.
- **Faster/cheaper video** — in *Format Prompt*, change `model` to another kie.ai video model.
- **Approval before posting** — insert a *Wait* (webhook) or *Telegram approval* step between *Send Final Reel Preview* and *Upload Video to BLOTATO* so nothing posts without your OK.
- **Posting schedule** — add a *Schedule Trigger* branch that reads `READY` rows from the sheet and posts them at fixed times instead of instantly.
