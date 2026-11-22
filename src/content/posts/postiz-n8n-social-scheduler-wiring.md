---
title: "Postiz Is the Open-Source Scheduler n8n Users Keep Searching For — Wire It Into n8n in 20 Minutes"
description: "Postiz is a Breakout search for n8n users this week. Its verified n8n node + public API post to 28+ networks — here's the wiring, with an approval gate."
date: 2026-11-22
category: news
tags: ["postiz", "n8n", "social media", "mcp", "automation"]
draft: false
featured: false
image: "/og/postiz-n8n-social-scheduler-wiring.webp"
---

n8n has nodes for X, LinkedIn, YouTube, Reddit, and Facebook — but none for Instagram, TikTok, or Threads. So every workflow that posts everywhere hits the same wall: either you wire up each network's API by hand, or you pay a scheduler per post, per channel, per seat. This week, n8n builders started searching for a third option in numbers big enough to notice: "postiz" is a Breakout rising related query for "n8n" in the US over the past 7 days (Google Trends Explore, Nov 15–22, 2026, read Nov 22).

Postiz is an open-source social media scheduling platform — AGPL-3.0, 42,141 GitHub stars, 8,054 forks — with a verified n8n node, a public API on every plan, and its own MCP server. By the end of this article you will have a working n8n workflow that drafts a post, waits for your approval, and publishes it to every network you connect — and you will know exactly where the free self-hosted route beats the paid cloud one.

## What Postiz actually is

Postiz (postiz.com) is a social media management platform for scheduling, automating, and analyzing content. Its own README puts it in one line: "Perfect for automation (API) with platforms like N8N, Make.com, Zapier, etc." It comes in two shapes that share the same product:

| | Postiz Cloud | Self-hosted (open source) |
|---|---|---|
| Cost | 7-day free trial; Team is $39/month for 10 channels | Free forever under AGPL-3.0 — you pay only for your own server |
| Setup | Sign up, connect channels in minutes | Docker / Coolify / Railway / any VPS; you configure Postgres, Redis, storage, and env vars |
| Channels | Limited by plan tier | Unlimited — every supported provider |
| Social apps | Pre-approved apps for every channel | You create your own developer apps per platform; Meta, YouTube, and TikTok approval can take weeks |
| API, MCP server, CLI | Included | Included — point them at your own instance |

The numbers that matter: 28+ channels (Instagram, TikTok, YouTube, LinkedIn, Facebook, X, Threads, Pinterest, Reddit, Bluesky, Mastodon, Discord, Slack, Dribbble), a verified n8n community node (`n8n-nodes-postiz`, verified by n8n — which matters, because n8n Cloud only installs verified community nodes), a public API, and agentic surfaces including an MCP server, a CLI, and connectors for ChatGPT, Claude, Codex, and Cursor. Under the hood it is Next.js + NestJS + Prisma on PostgreSQL, with Temporal for scheduling and Redis for queues.

## What's new in November — and why the searches spiked

The trend signal has a dated trigger. Postiz shipped **v2.26.0 on November 18, 2026**, carrying security advisory PSA-2026-4QX1WG, five days after a November 13 release that added encrypted channel tokens, connect links via the API and MCP, and 40+ fixes. A November 11 walkthrough video — "Postiz: This Open-Source Tool Lets AI Agents Post to 34 Platforms" — is the other half of the spike: it framed Postiz as the scheduler you point an agent at, not just a calendar you click in.

None of this is a rebrand or a pivot. Postiz has been open source since July 2023. What changed in November is that the agent story got concrete: encrypted tokens, an MCP connector, and a verified n8n node in the same month.

## How the wiring works

The pipeline has four parts, and the order matters more than the tools. Your n8n workflow produces a draft. Postiz holds it. You approve it. Postiz publishes it to every connected network at the scheduled time — even when n8n isn't running, because Postiz keeps the post and does the publishing itself.

![Postiz scheduler press: an n8n workflow feeds draft posts into the Postiz scheduling press, a human approval lever gates every publish, and the press fans finished posts out to 28+ social channels](/figures/postiz-n8n-social-scheduler-wiring-scheduler-press.svg)

*Figure 1 — The Postiz scheduler press. Drafts enter from n8n on the left, the approval lever in the middle is the only thing standing between a draft and a published post, and the press fans the approved post out to every connected channel. Readout: 42,141 stars · AGPL-3.0 · 28+ channels · v2.26.0 Nov 18, 2026 · verified n8n node · 0 posts without approval.*

There are three ways to connect n8n to Postiz, and you should pick based on who decides the wording:

| Route | Best when | What you use |
|---|---|---|
| Verified node (`n8n-nodes-postiz`) | Fixed workflows — same post, same time, same networks | Postiz node: "Schedule a post to Postiz", upload files, list channels |
| MCP Client Tool | An AI Agent decides the wording, picks networks, or adapts captions per network | MCP Client Tool node pointed at Postiz's MCP server |
| Raw HTTP Request | You want full control, or you're on an n8n version without the node | HTTP Request node against `https://api.postiz.com` with your API key |

The node and the MCP route are the ones most builders want. The HTTP route is the fallback that always works.

## Prerequisites

- An n8n instance (Cloud or self-hosted, version 1.2 or later for the MCP Client Tool's Streamable HTTP transport).
- A Postiz account — Cloud (7-day trial) or a self-hosted instance.
- Your social accounts connected in Postiz under Integrations. Postiz uses each platform's official OAuth flow; it never asks for your social passwords.
- A chat model credential in n8n, if you want an AI Agent to write the posts.

## Step 1 - Get your Postiz API key

On Postiz Cloud this takes about fifteen seconds: open **Settings → Public API**, hit **Reveal**, and copy the key. The key inherits whatever integrations you already connected in the Postiz dashboard, so the API can only post to accounts you connected — it cannot reach anything else.

> **Note:** The key is shown once. If you lose it, revoke it and create a new one rather than sharing it in a chat log, a screenshot, or a workflow export.

Self-hosted users get the same API on their own instance — the base URL is your instance's domain instead of `https://api.postiz.com`, and everything else below works the same way.

## Step 2 - Install the verified Postiz node

In n8n, open **Settings → Community Nodes → Install** and install `n8n-nodes-postiz`. Because n8n has verified this node, it installs on n8n Cloud too — unverified community nodes do not.

Create the Postiz credential when the node asks for it: paste the API key from Step 1. The node exposes three operations you will actually use — schedule a post, upload a file, and list channels. Test the credential now, before building anything: run "List channels" and confirm your connected accounts come back. If they don't, the key is wrong or the accounts aren't connected in Postiz yet — fix that in the Postiz dashboard, not in n8n.

## Step 3 - Build the draft → approve → publish workflow

The workflow is five nodes. A Schedule Trigger fires at posting time (or a Webhook / Form Trigger hands it a topic). An AI Agent node writes the post — one caption per network, respecting each network's limits. Then the Postiz node schedules it as a **draft**, not a publish. A Wait node holds the execution until you approve. A second Postiz call flips the draft to published.

```json
{
  "nodes": [
    { "name": "Schedule Trigger", "type": "n8n-nodes-base.scheduleTrigger" },
    { "name": "AI Agent", "type": "@n8n/n8n-nodes-langchain.agent" },
    { "name": "Postiz - Schedule Draft", "type": "n8n-nodes-postiz.postiz" },
    { "name": "Wait for Approval", "type": "n8n-nodes-base.wait" },
    { "name": "Postiz - Publish", "type": "n8n-nodes-postiz.postiz" }
  ]
}
```

Why schedule as a draft first: Postiz holds drafts in its own calendar, so a failed n8n execution after the draft step doesn't lose the post — and nothing reaches a public feed until a human says so. That is the whole safety model, and it is the same pattern this blog has recommended for every agent that touches money, code, or a public audience: the agent proposes, a human disposes.

If you prefer the agent route, swap the Postiz node for an **MCP Client Tool** on the AI Agent node, pointed at Postiz's MCP server. The agent can then call `list_accounts`, check each network's rules, and create the post itself. Keep the approval gate either way — Postiz holds agent posts for approval by default, and you should leave that on for the first month at least.

For the raw HTTP route, the call is an HTTP Request node with an `Authorization` header carrying your key, pointed at `https://api.postiz.com` (Cloud) or your own instance. Use it when the node doesn't expose an operation you need — uploading media and listing integrations both work this way.

## Step 4 - Verify end to end

Run the workflow once with test data. You should see the draft appear in Postiz's calendar for every network you selected, with the right caption on each. Approve it from the Postiz dashboard, then check each network's post — not just Postiz's "published" status. A green check in Postiz means Postiz handed the post to the network; the network's own post page is the proof it landed.

Then test the failure mode on purpose: disconnect one network in Postiz and run the workflow again. The draft should still be created for the other networks, and the failure should be visible in the execution log — not silent. If a network fails silently, add an IF node after the Postiz call that checks the response status and routes failures to a Slack or email alert.

## Limits and honest trade-offs

- **Self-hosting is free, not effortless.** You own Postgres, Redis, storage, backups, and security patches. And every platform's developer app is your problem: Meta, YouTube, and TikTok approvals can take weeks, while Postiz Cloud's pre-approved apps work immediately.
- **The Cloud free tier is a trial, not a plan.** Postiz Cloud starts with a 7-day free trial; Team is $39/month for 10 channels. The public API is on every plan, but the channels you can post to are capped by your tier.
- **Postiz is a scheduler, not a social network.** It cannot bypass a platform's rules — media requirements, caption limits, and rate limits still apply, and it will not scrape or automate around them. Its compliance page is explicit: official OAuth flows only, no scraping, no stored API keys from users.
- **I did not live-test this wiring.** The node operations, API key flow, and MCP setup are verified against Postiz's own README and blog and an independent n8n scheduler guide checked November 19, 2026 — not against a running Postiz instance. Run Step 4 with a test post before you point it at a real audience.
- **The 34-platforms figure is a video title, not a docs count.** Postiz's own blog says 28+ channels. Use 28+ until Postiz's docs say otherwise.

## FAQ

### Is Postiz really free?

The self-hosted edition is free forever under the AGPL-3.0 license — you pay only for your own server. Postiz Cloud is a managed service with a 7-day free trial and paid plans after that. Both are the same product with the same features; the difference is who runs the infrastructure and whose developer apps you use.

### Do I need the n8n node, or can I just use the API?

Either works. The verified node is the fastest path and installs on n8n Cloud. The raw HTTP Request route against `https://api.postiz.com` gives you every endpoint, including ones the node doesn't expose. If an AI Agent decides what to post, use the MCP server instead — it lets the agent list accounts and check platform rules before drafting.

### What happens if n8n goes down after I schedule a post?

Nothing — Postiz already holds the scheduled post and publishes it at the set time. That is the main advantage of a scheduler over calling each network's API directly from n8n: the publish step doesn't depend on your n8n instance being up.

### Can the agent publish without my approval?

Only if you let it. Postiz holds agent-created posts for approval by default. Keep that default, and keep the Wait node in the workflow, until you have a month of clean runs — then decide whether specific low-risk networks can skip the gate. Never skip it for a brand account.

## Key Takeaways

1. **Postiz is Breakout for a reason** — an open-source scheduler (42,141 stars, AGPL-3.0) with a verified n8n node, a public API, and an MCP server landed three agent-relevant releases in November, including v2.26.0 on Nov 18.
2. **Use the verified node first** — `n8n-nodes-postiz` installs on n8n Cloud, creates posts, uploads files, and lists channels. Fall back to the raw API at `api.postiz.com` or the MCP server when the node doesn't cover your case.
3. **Draft first, approve, then publish** — schedule as a draft, hold on a Wait node, and let a human approve. Postiz keeps the post and publishes it even if n8n goes down.
4. **Self-hosted is free, Cloud is fast** — self-hosting costs only your server but means your own developer apps (weeks of approval on Meta/YouTube/TikTok); Cloud is minutes to set up, with a 7-day trial and Team at $39/month for 10 channels.
5. **Verify on the network, not in Postiz** — a green check in Postiz means it handed the post over. Open the actual post on each network before you trust the pipeline.

Next: try the same draft → approve → publish pattern with the [MCP Client Tool guide](/blog/how-to-connect-mcp-server-n8n/) if you want the agent to pick networks and adapt captions itself — and read the [n8n 2.43 agent guardrails](/blog/n8n-2430-agent-guardrails-release/) before you let any agent post unsupervised.
