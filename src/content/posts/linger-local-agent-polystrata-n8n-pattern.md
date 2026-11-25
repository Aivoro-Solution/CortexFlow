---
title: "Linger Runs a 125B Agent on a 12 GB GPU — Steal Its Local-First Pattern for n8n"
description: "Linger, the local-first personal agent rising +550% in US search, fits a 125B model on a 12 GB GPU. Here is the tiering pattern n8n builders can steal."
date: 2026-11-25
category: news
tags: ["ai-agents", "n8n", "local-ai", "open-source", "automation"]
draft: false
featured: false
image: "/og/linger-local-agent-polystrata-n8n-pattern.webp"
---

"linger ai agent" is a rising related query for "AI agent" in Google Trends Explore (US, past 7 days), up +550% as of November 25, 2026. Behind that search is Linger, a personal AI agent that runs on your own computer instead of in someone else's cloud — and a claim worth testing: a 125-billion-parameter model running on a 12 GB graphics card.

This article explains what Linger actually is, how its tiering trick works, where the claims get shaky, and the five-part local-first pattern you can rebuild in n8n today without installing anything.

## What is trending, and why

Linger is built by Simplex AI Labs. Its first desktop release, version 0.1.0, landed on November 10, 2026 for macOS, Windows, and Linux. Founder Tony Zhang — a former project lead on DeepSeek-VL — announced the open-source launch on X on November 19, 2026.

The project is moving fast. By November 25, 2026 it had shipped nine stable releases in 30 days, reaching version 0.1.9 that same day, with 4,478 GitHub stars (AgentGid's reading, checked November 25 at 06:27 UTC, adding roughly 576 stars a day since November 18). Version 0.1.8 arrived November 24, and 0.1.9 added grouped model lists with explicit GPU VRAM and RAM footprints, guided NVIDIA driver updates, and automatic recovery of failed local model servers.

The pitch, in the project's own words, is "an open-source personal agent with a Claude-class brain running locally on your PC." Treat "Claude-class" as a vendor claim — more on that below. The interesting part is not the slogan. It is the mechanism.

## How Linger works: five layers

**PolyStrata, the local model runtime.** A mixture-of-experts (MoE) model holds many specialist sub-networks called experts, but only a few of them activate for each token — each small chunk of text the model processes. PolyStrata exploits that: it keeps the busiest experts in GPU memory, less-used experts in system RAM where the CPU computes them, and rarely used experts on the SSD, moving experts up a tier when they get picked more often.

That tiering is how the headline number works. The 125B Qwen3.8-Flash-Next model runs on a 12 GB card with 64 GB of system RAM, because most of its 125 billion parameters are parked in RAM or on disk at any moment. Simplex AI's lab reports 45.5 tokens per second on an RTX 3060 12 GB and 179 on an RTX 5090.

**Model Autopilot.** The installer reads your GPU, VRAM, RAM, and memory bandwidth, picks the strongest model that fits with at least a 64K context window, installs it, and checks it with a real test question before finishing.

**A nightly memory wiki.** Mail, chats, and meetings are filed into wiki pages on your device that update nightly, so agents search those pages instead of rereading raw history. The README credits the open-source Hindsight project for fact extraction and search, and publishes no memory benchmark of its own.

**"Another Me", the proactive agent.** It watches your inbox, calendar, and Slack mentions and messages you only when something needs you. A nightly process the README calls Dreaming rewrites its decision rules based on how you reacted — for example, staying quiet about deliveries after you dismiss them twice. It can also assemble agent teams that share one plan file, `team.md`.

**Desktop and browser control.** Agents open apps, click, and type; on Mac and Windows they work inside your everyday Chrome with your existing sign-ins. Long jobs run as background copies so the chat stays responsive. Voice is included too: meeting recording with live transcripts that hand off to follow-up tasks.

If you would rather not run a local model at all, version 0.1.4 (November 19) added bring-your-own-key support for OpenAI-compatible and Anthropic endpoints, and the README lists Claude Code, Codex, and Pi as runtimes you can plug in.

![Fig 1 — The PolyStrata tier press: busiest experts on the GPU, the rest in RAM and on SSD, feeding one work head. Numbers from Linger's README and release notes as of November 25, 2026.](/figures/linger-local-agent-polystrata-n8n-pattern-tier-press.svg)

*Fig 1 — The tier press. Notice the three storage tiers feeding a single work head: the GPU holds only the busiest experts, RAM holds the next tier, and the SSD holds the rest. The readout numbers (125B model, 12 GB GPU, 64 GB RAM, 45.5 tok/s) are Simplex AI's lab figures, not independent measurements.*

## The honest limits

**The speed numbers are self-reported.** Simplex AI says many figures were measured on simulated hardware tiers — a larger card held to a smaller tier's memory budget — so a real machine of that tier can be slower. We found no independent tests. One detail matters for agents: on the 12 GB tier, the first token can take about three minutes after a 62K-token prompt. An agent that stuffs context into every call will feel that.

**"Claude-class" means close to an older Claude on one blended score.** The README's SimplexAI score is built on a third-party AIHOT scale where 50 is the reference average. Its mapping puts 51.9 at "about Claude Opus 4.5" and 57.3 at "about Claude Opus 4.6" — older models than today's frontier. The 57.3 row is also not the default recommendation for a 12 GB machine.

**It is early software.** Version 0.1.9, a release every day or two, unsigned Windows installer, a macOS app that is not notarized (first launch needs a quarantine-flag workaround after you verify the checksum). Expect rough edges.

**The license is not plain Apache 2.0.** It is the Linger Open Source License, based on Apache 2.0 with additional conditions — a commercial license is required to offer Linger as a hosted service. Read it before building a product on top.

**Broad access is the feature and the risk.** An agent that watches your mail, calendar, and Slack and drives your signed-in browser can act on bad instructions in an email or web page. Running locally removes the cloud provider; it does not remove prompt-injection risk. Linger has no published answer yet for how it handles injected instructions in the mail it reads.

None of this makes Linger a bad bet to try. It makes it a bet to try in a sandbox first: separate browser profile, limited accounts, checksum verified, your own tokens-per-second measured on your own prompts.

## Steal the pattern for n8n: five parts

You do not need Linger to use its best ideas. Each layer maps to something n8n already does well.

### 1. Tier your memory like PolyStrata tiers experts

Keep only the facts the current run needs in the prompt. Put the next tier — recent summaries, open tasks, key contacts — in a fast store the workflow reads first, and the cold tier — full history, raw mail, old transcripts — in a database the agent queries only on demand. In n8n terms: a small "hot facts" object passed between nodes, a Postgres or Supabase table for warm summaries, and the original mailbox or Drive as the cold store. The principle is the same as expert tiering: the expensive fast tier holds only what gets used constantly.

### 2. Consolidate nightly, not per message

Linger's wiki and Dreaming run on a schedule, not on every email. Copy that: a Schedule Trigger workflow that runs once a night, reads the day's new items, updates your summary tables, and rewrites the rules your watcher uses. Per-message summarization is slower, costlier, and noisier than one nightly consolidation pass.

### 3. Make the watcher proactive, but quiet by default

"Another Me" messages you only when something needs you, and learns from dismissals. In n8n: Gmail or Calendar triggers feed an IF node with strict conditions — a named sender, a deadline inside 24 hours, an amount over a threshold — and everything else goes to a log, not to your phone. Log every dismissal; when the same category gets dismissed twice, tighten the condition. That is Dreaming, rebuilt with nodes you control.

### 4. Put every desktop or browser action behind an approval gate

Linger's agents drive your signed-in Chrome. Your n8n version should not act without a human yes on anything irreversible: sending mail, submitting forms, changing records. Use a Wait node that sends an approval message with the exact action spelled out, and only continue on approval. Read-only steps — search, fetch, summarize — can run freely.

### 5. Prefer a local model for private data, cloud for hard reasoning

Linger's real pitch is privacy plus zero token bills, not raw capability. The n8n version: route classification, summarization, and anything touching private mail to a local model (an Ollama node or an OpenAI-compatible local endpoint), and escalate only hard reasoning to a cloud model. Cap each route's spend, log every decision, and measure your local model's real speed on your own prompts before trusting any table — including Linger's.

## FAQ

### Is Linger really open source?

The source is public on GitHub under simplexai-labs/linger, and the desktop app is free to download. The license is the Linger Open Source License, based on Apache 2.0 with additional conditions, including a commercial license requirement for offering it as a hosted service. Read the license before commercial use.

### Can Linger really run a 125B model on a 12 GB GPU?

That is the project's claim, with 64 GB of system RAM alongside. The mechanism is credible — MoE models activate only a few experts per token, so tiering experts across GPU, RAM, and SSD is a real technique. The reported 45.5 tokens per second on an RTX 3060 is Simplex AI's own lab figure, partly from simulated hardware tiers, with no independent tests yet.

### How is Linger different from n8n's Nod?

Both are local personal agents released in November 2026. Nod, from n8n Labs, opens its own browser and finishes web tasks after you approve risky steps, using a model provider you choose. Linger bundles its own local model runtime, memory wiki, and proactive watcher, and bets on running the model itself on modest hardware.

### Should I install Linger today?

Try it if you have a 12 GB or larger NVIDIA GPU with 64 GB of RAM, or a recent Apple silicon Mac, and you want a private assistant to experiment with. Verify the release checksum, start with limited accounts and a separate browser profile, and measure your own speed. Wait if you need signed installers, a settled license position, or independent benchmarks.

## Key Takeaways

1. **Linger's tiering is the real idea** — keep the busiest experts (or facts) in the fastest tier, park the rest in RAM, disk, or a cold store, and promote on use.
2. **The 125B-on-12 GB claim is plausible but unproven** — vendor lab numbers, simulated tiers, no independent tests, and a slow first token on long prompts.
3. **Nightly consolidation beats per-message memory** — one scheduled pass that updates summaries and rules is cheaper and calmer than reacting to everything live.
4. **Proactive does not mean noisy** — a watcher earns trust by staying quiet, logging dismissals, and tightening its own conditions.
5. **Local-first is a privacy and cost choice, not a capability win** — route private work locally, escalate hard reasoning, and gate every irreversible action behind a human approval.

Next step: pick one workflow you already run — an inbox triage or a daily digest — and rebuild it with a hot-facts tier, a nightly consolidation pass, and an approval gate before any send. That is Linger's architecture, running on infrastructure you already trust.

*Sources: Linger README and releases (simplexai-labs/linger, GitHub, November 2026); i10X News launch report (November 19, 2026); ExplainX Linger analysis (figures as of November 20, 2026); AgentGid Linger page (star count and 0.1.9 release, checked November 25, 2026).*
