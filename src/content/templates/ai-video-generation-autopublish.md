---
title: "AI Video Generation & Auto-Publishing Pipeline"
description: "Generate video scripts with AI, render via a video API, hold for human approval, then auto-publish to socials."
date: 2026-10-01
category: "automation"
difficulty: "advanced"
workflow: "/templates/ai-video-generation-autopublish.json"
integrations: ["OpenAI","Gmail","Slack"]
---

## How it works

1. **Schedule Trigger** — starts the workflow every Monday at 9:00 AM (change the day and time in the node).
2. **Set Topic** — defines the video topic and target audience for this run; edit the values to change what gets produced.
3. **OpenAI: Write Script** — sends the topic to GPT and gets back a ready-to-render 60-second video script.
4. **HTTP Request: Render Video** — POSTs the script to your video-generation API (HeyGen/Synthesia-style) and gets back a video URL.
5. **Gmail: Request Approval** — emails you the finished video link plus an approval link; nothing publishes until you approve.
6. **Wait: Human Approval** — pauses here. You open the approval link from the email and submit Approve or Reject on the form.
7. **IF: Approved?** — routes approved videos toward publishing and rejected ones to a notification.
8. **HTTP Request: Publish to Socials** — POSTs the approved video to your social scheduler (X/LinkedIn placeholder).
9. **Slack: Notify Published** — posts a "published" message to your channel.
10. **Slack: Notify Held** — posts a "held for review" message when the video is rejected.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- An OpenAI account — get an API key at platform.openai.com → API keys
- A video-generation API account (e.g., HeyGen or Synthesia) — get an API key from your provider's dashboard → API settings
- A Gmail account — connect via OAuth in n8n
- A Slack workspace — connect via OAuth in n8n
- A social scheduling API (e.g., your X/LinkedIn scheduler) — get an API key from the scheduler's settings

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Then open the *OpenAI: Write Script* node and select your credential.
4. **Point the video API at your provider** — open *HTTP Request: Render Video*, replace `https://api.your-video-provider.com/v1/videos` with your provider's real endpoint (e.g., HeyGen's or Synthesia's video-creation URL), and select your header-auth credential containing your API key.
5. **Create your Gmail credential** — in n8n go to *Credentials → New → Gmail OAuth2*, complete the OAuth flow, save. Open *Gmail: Request Approval*, select the credential, and change the recipient to your own email address.
6. **Create your Slack credential** — in n8n go to *Credentials → New → Slack OAuth2*, complete the OAuth flow, save. Open both Slack nodes, select the credential, and set the channel (e.g., `#content`).
7. **Point the publish step at your scheduler** — open *HTTP Request: Publish to Socials*, replace `https://api.your-social-scheduler.com/v1/publish` with your scheduler's real endpoint and select your API credential.
8. **Activate** the workflow (toggle, top-right), then wait for the first Monday run or trigger it manually with *Execute workflow*.

The approval email contains a link built from `{{$execution.resumeUrl}}`. Clicking it opens an Approve/Reject form — submitting the form resumes the workflow exactly where it paused.

## Customize it

- **Change the schedule** — open *Schedule Trigger* and edit the cron expression (`0 9 * * 1` = Monday 9 AM).
- **Change the topic** — edit the values in *Set Topic*; you can also feed topics in from a Google Sheet instead.
- **Use a different model** — open *OpenAI: Write Script* and change the model from `gpt-4o-mini` to any other model.
- **Add more platforms** — duplicate *HTTP Request: Publish to Socials* and point the copy at another scheduler endpoint.
- **Auto-publish without approval** — only do this once you trust the pipeline: delete the *Wait* and *IF* nodes and connect *Gmail: Request Approval* directly to *HTTP Request: Publish to Socials*.
