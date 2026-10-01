---
title: "Social Media Auto-Poster & Content Repurposer"
description: "Turn each new blog post into platform-ready social posts with AI — held for your approval before publishing."
date: 2026-10-01
category: "automation"
difficulty: "beginner"
workflow: "/templates/social-media-auto-poster.json"
integrations: ["OpenAI","Slack"]
---

## How it works

1. **RSS Feed Read** — watches your blog's RSS feed for new posts.
2. **IF New Post Found** — passes the workflow on only when the feed item has a valid link.
3. **Repurpose with AI** — GPT turns the post title and summary into three drafts: an X post (under 280 characters), a LinkedIn long-form post, and a short hook line.
4. **Format Drafts** — packages the AI output into a clean `drafts` field and keeps the source link.
5. **Slack — Review Drafts** — sends all three drafts to your `#content-review` channel for review.
6. **Wait for Approval** — pauses the execution until you approve or reject it in the n8n execution view. Nothing publishes while it waits.
7. **IF Approved** — continues only if you clicked Approve; rejected runs end here.
8. **Publish Posts** — sends the drafts to your social scheduler via a placeholder API (`https://api.your-social-scheduler.com/v1/publish`). Swap it for Buffer, Typefully, or the X API.
9. **Slack — Published** — sends you a confirmation once the posts are live.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- Your blog's RSS feed URL (e.g. `https://your-blog.com/rss.xml`)
- An OpenAI account — get an API key at platform.openai.com → API keys
- A Slack workspace — create a channel like `#content-review` and connect Slack in n8n when prompted
- A social scheduler account (Buffer, Typefully, or the X API) — only needed when you want live publishing

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Set your feed URL** — open *RSS Feed Read* and replace `https://your-blog.com/rss.xml` with your blog's real RSS feed URL.
4. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Open *Repurpose with AI* and select your credential.
5. **Create your Slack credential** — in n8n go to *Credentials → New → Slack OAuth2 API*, complete the OAuth flow, save. Open both Slack nodes, select your credential, and confirm the channel.
6. **Point the publisher at your scheduler** — open *Publish Posts* and replace the placeholder URL and header-auth credential with your real scheduler (Buffer, Typefully, or the X API endpoint). Until you do this, the workflow stops safely at approval with nothing published.
7. **Activate** the workflow (toggle, top-right), then publish a blog post to test it.

## Customize it

- **More platforms** — edit the prompt in *Repurpose with AI* to add Threads, Facebook, or a newsletter blurb.
- **Change the tone** — add style instructions (e.g. "casual, no hashtags") to the same prompt.
- **Different review channel** — change the channel in both Slack nodes.
- **Auto-publish a platform** — remove the approval gate only if you're comfortable; the workflow is designed so nothing publishes without your approval.
