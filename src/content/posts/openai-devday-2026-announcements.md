---
title: "OpenAI DevDay 2026: GPT-6.1 Sol, Pro 500, and the Decisions API"
description: "DevDay 2026's 5 announcements that matter for agent builders: GPT-6.1 Sol pricing, the $500 Pro tier, Decisions API, Codex upgrades, Sign in with ChatGPT."
date: 2026-10-01
category: news
tags: ["OpenAI", "DevDay", "AI agents", "GPT-6"]
image: "/og/openai-devday-2026-announcements.webp"
draft: false
featured: false
---

OpenAI's DevDay 2026 keynote on September 29 packed more than 20 announcements into one session — new models, new pricing tiers, new APIs, and a new way to spend your ChatGPT subscription inside other people's products. If you build agents or automations, most of it is noise; five of the announcements change the math you do every day. Below are the confirmed facts, the numbers that matter, and what to watch before you rebuild anything around them.

One note on sourcing: everything here comes from OpenAI's DevDay recap as reported by multiple outlets on September 29-30. I have not tested these products hands-on — several are still rolling out — so treat capability claims as announced, not independently verified.

## 1. GPT-6.1 Sol: near-flagship intelligence at one-fifth the price

**Sol is the pricing story of the keynote.** GPT-6.1 Sol is positioned just below GPT-6 Astra (OpenAI's flagship) on capability, at roughly one-fifth of Astra's token prices. It is aimed squarely at agentic coding, computer use, and multi-step professional work — the workloads where token bills compound fastest.

The API prices, as reported: **$2 per million input tokens, $0.10 per million cached input tokens, and $10 per million output tokens**. For context on what "near-Astra" means in measured terms: on Artificial Analysis's Intelligence Index, Sol scores 52 against Claude Opus 5.5's 58 — while costing **$0.72 per index task versus $5.98** for Opus 5.5. That is the number to remember: roughly 90% of the benchmark score at roughly 12% of the cost.

Sol is live now on the API and in ChatGPT Work and Codex for Plus, Pro, Business, Enterprise, and Edu users. An Ultrafast variant (faster inference) is listed as coming soon. If you run agents on a per-token budget — n8n AI Agent nodes, custom loops, anything with tool calls — Sol is the first model in a while that changes which model you default to.

## 2. Pro 500: a $500/month tier with 25x the Plus allowance

OpenAI added **ChatGPT Pro 500 at $500 per month**, joining the existing $100 and $200 Pro tiers. It includes **25 times the ChatGPT Plus usage allowance** and access to Astra Ultrafast (the premium-speed inference tier).

Two related moves: **Pro 200 subscriptions reopened** after a brief pause, but new Pro 200 signups now get a lower usage allowance — existing eligible subscribers keep their previous allowance through **October 29, 2026**. The pattern is clear: OpenAI is segmenting heavy users by wallet size, and the heaviest agent workloads are being pushed toward the top tier.

For builders, the practical read: if your product wraps ChatGPT usage (internal copilots, client-facing bots on Plus/Pro accounts), the allowance math just got more granular. Watch where your usage actually lands before assuming a tier.

## 3. Decisions API: Luna answering fixed questions, fast

The most directly relevant launch for automation builders got the least stage time. The **Decisions API**, now in limited preview, uses the Luna model for **low-latency, deterministic choices** — classification, routing, and picking an agent's next action.

**Deterministic** here means the API is designed to return the same kind of structured answer to the same kind of question, quickly and cheaply — the opposite of asking a frontier model to "think about it" for a routing decision. If you have ever burned GPT-4-class tokens just to decide which branch of a workflow to take, this is the product built for that exact pain. Pricing and general availability have not been announced; it is in limited preview for developers.

## 4. Codex grows up: cloud tasks, voice CLI, security scanning

Codex, OpenAI's coding agent, got a cluster of upgrades aimed at making it a background worker rather than a foreground tool:

- **Codex in the cloud:** start a coding task, close your laptop, and the task continues. Review changes and continue work from web, mobile, or desktop. Available to Plus and above.
- **Refreshed Codex CLI:** adds voice controls and an `/agents` view for tracking delegated work. Code review is now in the desktop app too.
- **Codex Security Cloud:** scans connected GitHub repositories for vulnerabilities, investigates findings, deduplicates them, and prepares fixes — you review the patch before it becomes a draft pull request. Available to Pro, Business, Enterprise, and Edu.

The through-line: coding agents are moving from "assistant in your editor" to "engineer you dispatch." If you maintain repos with automation around them, the Security Cloud pattern — scan, investigate, propose patch, human approves — is worth copying even if you never touch Codex.

## 5. Sign in with ChatGPT: spend your subscription inside other tools

**Sign in with ChatGPT** lets paid subscribers use their ChatGPT plan allowance inside third-party products. Sixteen launch partners were named, including **Devin, Notion, Vercel, T3, OpenClaw, and Dactyl**. Plan usage (not just sign-in) is available to Plus and Pro subscribers, who can control how much each tool consumes, with eligible usage counting toward existing plan limits.

This is the quiet structural shift: your OpenAI subscription becomes a **portable AI budget** rather than a ChatGPT-only allowance. For tool builders, it is a new distribution and monetization surface — users bring their own inference budget. For everyone else, it is a reason to audit where your AI spend actually goes before adding another per-seat AI subscription.

## Also worth knowing

- **Agents API public beta:** managed agent infrastructure with memory, multi-agent support, and computer use — the engine behind Dots, now open to builders. (We covered Dots themselves [here](/blog/openai-dots-always-on-agents/).)
- **Dots** got their full launch (see our earlier piece); DevDay added the roadmap: SMS support soon, teams of dots later.
- **ChatGPT Space and Pages:** shared workspaces and collaborative documents for people and agents, rolling out to Pro/Business/Enterprise.
- **OpenAI Marketplace:** eligible enterprise customers can spend part of an OpenAI commitment on partner software.

Sources: [Neowin](https://www.neowin.net/news/openai-unveils-500-chatgpt-pro-plan-decisions-api-and-major-codex-upgrades-at-devday-2026/), [Digit](https://www.digit.in/news/general/openai-devday-2026-dots-to-pro-500-plan-check-key-announcements-from-chatgpt-makers-developer-conference.html), [Nerdschalk's plan-by-plan breakdown](https://nerdschalk.com/everything-openai-launched-at-devday-2026/).

## What to watch

- **Independent benchmarks on Sol.** The 52-vs-58 Intelligence Index number comes from one index; wait for task-specific evals (coding, tool use, long-horizon agents) before switching production workloads.
- **Decisions API pricing and GA.** The value proposition lives or dies on price per decision. Until it is generally available, treat it as a roadmap item.
- **Pro 500 uptake.** Whether heavy users actually pay $500/month will tell you how OpenAI prices agent compute next — and what your customers will consider "normal."
- **Sign in with ChatGPT partner quality.** Sixteen partners at launch; the question is whether usage controls are fine-grained enough for teams, and which tools join next.

## Key Takeaways

1. **GPT-6.1 Sol resets the price-performance default**: ~90% of a flagship benchmark score at ~12% of the cost per task — check whether your agents still need the flagship model.
2. **The Decisions API targets your cheapest, most frequent LLM call** — routing and classification. Watch its pricing; it could replace a lot of wasted frontier-model calls.
3. **$500/month Pro 500 and portable plan allowances** signal where OpenAI thinks heavy agent usage is going: metered, tiered, and spendable outside ChatGPT.
4. **Codex's direction is "dispatch, don't babysit"** — cloud tasks, security scanning with human-approved patches. Copy the pattern in your own automation.
5. **Nothing here is hands-on verified yet.** Rollout is gradual and several products are in preview or beta — pilot before you rebuild.

Next step: pull one agent workflow's token bill from last month and re-price it at Sol's $2/$10 per-million rates. If the saving is real, that workflow is your pilot candidate.
