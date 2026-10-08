---
title: "Claude Haiku 5.5 Costs $0.10 Per Million Tokens and Beats GPT-6 Luna on Agent Benchmarks"
description: "Claude Haiku 5.5 launched October 7, 2026: 75% cheaper than Haiku 4.5 at $0.10/M tokens, with agent benchmarks beating GPT-6 Luna."
date: 2026-10-08
category: news
tags: ["claude", "anthropic", "llm-pricing", "ai-agents", "n8n"]
draft: false
featured: false
image: "/og/claude-haiku-55-explained.webp"
---

Anthropic shipped Claude Haiku 5.5 on October 7, 2026 — the third model in its Claude 5.5 family in about a month — and the headline number is the price: **$0.10 per million input tokens**, roughly 75% cheaper to run than Haiku 4.5.

That matters because Haiku is the model that does the unglamorous bulk work in agent systems: classification, tool-call routing, summarization, extraction, voice-agent turns. If you've priced an n8n AI agent lately and felt the LLM bill, this is the release that moves the math.

Here's what launched, what the numbers actually say, and how to put it to work this week.

![Server racks in a modern data center, representing the infrastructure behind cheap high-volume AI inference](/images/claude-haiku-55-explained/datacenter.jpg)

## The headline numbers

Haiku (Anthropic's small, fast, cheap model tier — the sibling of the mid-size Sonnet and the flagship Opus) has always been the "good enough for the boring stuff" model. Version 5.5 extends that role with three changes:

| What changed | Detail |
|---|---|
| Input price | **$0.10 / 1M tokens** under 100k context, $0.50 / 1M above it |
| Output price | **$0.50 / 1M tokens** under 100k context, $2.50 / 1M above it |
| Running cost vs Haiku 4.5 | ~75% cheaper on average, per Anthropic |
| FrontierCode 1.1 (coding) | **46.4%**, vs GPT-6 Luna's 42.4% |
| OSWorld (computer-use) | **72.4%**, vs GPT-6 Luna's 48.9% |
| New | Adjustable **effort setting** — dial between more intelligence and lower cost |
| New | First Haiku with built-in **safeguards for high-risk cybersecurity requests** |

Also relevant for builders: Anthropic **cut Sonnet 5.5 cache-read prices**, which the company says makes Sonnet 5.5 about 20% cheaper for most agentic workloads. Prompt caching is how you keep a multi-turn agent affordable, so this is the price cut that compounds.

The model is live on Anthropic's platform, AWS, Google Cloud, and Azure, and it ships months ahead of Anthropic's planned IPO — the third 5.5-family launch in roughly a month, after Opus 5.5 and Sonnet 5.5.

## Why this is an agent-economics story, not a model story

Benchmarks are Anthropic's own, so treat the GPT-6 Luna comparisons with the usual grain of salt. The number that deserves your attention is the price, because of how agentic workflows actually spend tokens.

A single agent run is not one big prompt. It's dozens of small ones: classify this email, extract the invoice fields, decide which tool to call, summarize the tool output, draft the reply. On Haiku 4.5 pricing, a production support agent doing thousands of runs a day spent its budget on exactly these sub-tasks — the boring, high-volume work where a frontier model is overkill and a cheap model is the whole business model.

At $0.10 per million input tokens, the cost of a 2,000-token classification call drops to roughly **$0.0002** — effectively free at any sane scale. The adjustable effort setting is the lever that makes this practical: route the trivial decisions to low effort, and bump the ambiguous ones up.

**The honest takeaway: Haiku 5.5 isn't about better agents. It's about affordable ones** — the tier of agent workload (monitoring, triage, extraction, voice turns) that previously failed the ROI test now clears it.

![Close-up of a developer's screen showing code being written, illustrating the everyday tooling where small fast models do the heavy lifting](/images/claude-haiku-55-explained/coding-screen.jpg)

## How to use it in n8n this week

If you run n8n AI Agents with Anthropic models, the swap is small. The pattern I use: keep the flagship model (Opus/Sonnet) on the top-level agent where reasoning matters, and move the sub-agent routing and tool-call loops to Haiku 5.5.

In the n8n editor:

1. Open the **AI Agent** node (or **AI Agent Tool** sub-agent) that handles routing/classification.
2. In the chat model sub-node, change the model from your current Anthropic model to **Claude Haiku 5.5** (`claude-haiku-5-5` — confirm the exact model string in the node's model picker, as Anthropic model IDs change with releases).
3. Re-run a representative execution and compare output quality on your own prompts before rolling it to production. Small models drift on formatting and edge cases even when the benchmarks look fine.

> **Note:** verify the model string in the Anthropic docs rather than guessing it — an invalid model ID fails silently at the provider and surfaces as a generic API error in n8n.

Where Haiku 5.5 fits best in your stack:

- **Router/classifier sub-agents** — the "which tool does this request need" decision
- **Extraction and summarization** — invoice fields, ticket summaries, meeting notes
- **Voice agent turns** — Haiku has always been the latency pick for voice; 75% cheaper makes always-on voice cheaper to run
- **Evaluation loops** — cheap judge models for checking your expensive model's output

Where it doesn't: anything that needs long-horizon planning, nuanced tool orchestration, or writing you will sign your name to. Keep Sonnet or Opus there — and note Sonnet 5.5 just got 20% cheaper for agentic workloads via the cache-read cut, so check that price too.

## What to watch (the honest limits)

- **The 100k-token pricing cliff.** Pricing doubles-tier at 100,000 tokens ($0.10→$0.50 input). Most agentic prompts never get there, but if you stuff long documents into context on every turn, your bill steps up quietly. Watch the context column in your usage dashboard.
- **Benchmarks are vendor-supplied.** FrontierCode 1.1 (46.4% vs GPT-6 Luna 42.4%) and OSWorld (72.4% vs 48.9%) are Anthropic's picks. Run your own prompts — benchmark leaderboards correlate loosely with your support-ticket classifier.
- **New safeguards, untested edges.** Haiku 5.5 is the first Haiku with built-in safeguards for high-risk cybersecurity requests. Anthropic says most everyday tasks won't be affected — worth confirming if your agent handles security-adjacent content.
- **Availability churn.** The 5.5 family has shipped three models in a month, and the provider ID is the string the API expects. Pin your model IDs and check the Anthropic model list rather than assuming continuity.

For the broader price-war context, see our earlier breakdown of [AI agent costs after the Claude Opus 5.5 vs GPT-6 price war](/blog/ai-agent-costs-claude-opus-55-gpt-6/) — Haiku 5.5 extends the same trend one tier down.

## Key Takeaways

1. **$0.10/M input tokens makes high-volume agent sub-tasks nearly free** — classification, routing, extraction, voice turns.
2. **The adjustable effort setting is the real feature** — one model for both cheap bulk decisions and harder calls, instead of juggling two models.
3. **Sonnet 5.5's cache-read price cut (~20% cheaper agentic workloads)** matters as much as the Haiku launch for multi-turn agents.
4. **Swap the router, keep the planner** — move n8n sub-agent routing to Haiku 5.5, keep flagship models on the planning agent.

**Next:** audit one agent workflow this week — find the sub-agent or tool loop burning the most tokens and point it at Haiku 5.5. Measure the cost delta for a day before touching the planner.

*Images: Pexels*
