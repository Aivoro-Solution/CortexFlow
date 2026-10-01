---
title: "AI Agent Run Costs: Claude Opus 5.5 vs GPT-6"
description: "What does one n8n agent run cost after the Sept 2026 price war? Claude Opus 5.5 vs GPT-6 Astra, Sol, Luna — real per-1,000-run numbers."
date: 2026-10-01
category: ai-agents
tags: ["AI agents", "n8n", "Claude", "GPT-6", "pricing", "cost optimization"]
image: "/og/ai-agent-costs-claude-opus-55-gpt-6.webp"
draft: false
featured: false
---

If you run AI agents in n8n, September 2026 rewrote your cost model twice in a single week. Anthropic launched Claude Opus 5.5 at $4/$20 per million tokens; OpenAI answered within about 90 minutes with GPT-6 Sol — then cut again at its DevDay on September 29 with GPT-6.1 Sol at $2/$10, exactly one-fifth of flagship GPT-6 Astra's $10/$50. Bottom line up front: **for most n8n agent workloads, GPT-6.1 Sol is now the cheapest capable option; Claude Opus 5.5 earns its premium only on long-horizon tasks where a failed run costs more than tokens.**

That verdict needs numbers behind it, because a price table alone will not tell you your bill. **Input tokens** are the text you send the model (system prompt, tool definitions, conversation history); **output tokens** are what it generates — billed separately, and usually the expensive side. **Cached input** is the discount (typically ~90% off) for resending the same prompt prefix, which agents do on literally every step. An n8n agent multiplies all three: the system prompt, the tool schemas, and the growing history get re-sent each iteration. So this article models the cost per completed agent run, not per token — for the four models that matter in n8n right now.

## What we measured and how

The model is a typical n8n AI Agent run doing customer-support triage: a system prompt plus tool definitions of about 6,500 tokens, conversation and tool results of about 1,500, and roughly 1,500 output tokens per completed run. That is 8,000 input + 1,500 output tokens per run — a mid-size agent, not a toy and not a 20-step researcher.

Prices are official list rates as of September 30, 2026, Standard processing, short context (under 272K input tokens — GPT-6 doubles input pricing past that threshold for the whole request). Excluded: Fast mode (2x), Batch/Flex (50% off), subscription credits, and self-hosted open models. n8n Cloud vs self-hosted does not change model billing — the tokens cost what the provider charges either way.

One price-war footnote, because the table below will look stale fast: GPT-6 Sol shipped September 22 explicitly to undercut Opus 5.5 within 90 minutes of Anthropic's launch, and the September 29 DevDay brought GPT-6.1 Sol at one-fifth of Astra's rate — while the planned GPT-6.1 Astra launch was reportedly scrapped after internal safety tests. Verify current numbers on [OpenAI's pricing page](https://developers.openai.com/api/docs/pricing.md) before you commit to anything; this market reprices monthly now.

## Head-to-head table

| | Claude Opus 5.5 | Claude Sonnet 5.5 | GPT-6.1 Sol | GPT-6 Astra |
|---|---|---|---|---|
| Input $/1M tokens | $4 | $2 | $2 | $10 |
| Output $/1M tokens | $20 | $10 | $10 | $50 |
| Cached input $/1M | ~$0.40* | ~$0.20* | $0.10 | $1 |
| **Cost per 1,000 runs** | **$62** | **$31** | **$31** | **$155** |

\*Anthropic's standard ~90% cache-read discount applied to the input rate; not separately itemized for the 5.5 generation, so treat as approximate. GPT-6 cache rates are published.

The arithmetic, so you can re-run it with your own token counts: per run = (8,000 / 1M × input rate) + (1,500 / 1M × output rate). For Opus 5.5 that is $0.032 + $0.030 = $0.062 per run, or $62 per thousand. GPT-6.1 Sol and Sonnet 5.5 both land at $0.031 per run — $31 per thousand, exactly half. GPT-6 Astra is $0.155 per run — $155 per thousand, five times Sol.

Two things the table hides. First, **output tokens dominate as agents get chattier** — at 1,500 output tokens the output side is already ~half the bill on every model, and a verbose agent doubles it. Second, **caching is where the real money is**: agents resend the system prompt and tool schemas every step, and the minimum cacheable prompt on recent Claude models dropped to 512 tokens, so even short system prompts now create cache entries. With heavy cache hits, expect real bills 30–60% below the uncached table — but apply that discount to *your measured* cache-hit ratio, not mine.

## When to pick which

**For high-volume n8n agents — triage, classification, extraction, drafting: pick GPT-6.1 Sol or Claude Sonnet 5.5.** They are price-identical in this model ($31 per 1,000 runs). Choose by measured behavior on your workload, not by brand: run the same 50 representative tasks through both, count tool-call failures and retries, and keep the one that finishes cleanly. The price war made the token cost a tie; reliability breaks it.

**For long-horizon, multi-tool agents where a retry is expensive: pick Claude Opus 5.5.** It costs twice the tokens of Sol — $62 vs $31 per thousand runs — but one avoided retry wipes out that premium instantly, because a retry is a *whole second run* at full price. If your agent chains 8+ tool calls and a mid-run failure means starting over, the stronger model's completion rate is the cheaper option in practice. This is the one case where "better model" and "cheaper bill" are the same decision.

**For maximum capability where cost is secondary: GPT-6 Astra.** At $155 per thousand runs it sits in the same $10/$50 tier as Anthropic's ceiling model (Claude Fable 5.1) — five times Sol on both input and output. In n8n terms, that is a specialist tool: the agent that writes your migration scripts or reviews security-sensitive output, not the one answering 10,000 support tickets.

**For offline and batch work: stop paying Standard rates.** Both providers sell Batch/Flex processing at 50% of Standard — evaluations, dataset labeling, and nightly bulk runs in n8n should never run at full price. Fast mode (2x) is for interactive latency, not agents.

Three n8n-specific cost controls that matter more than model choice: set **Max iterations** on the AI Agent node so a confused agent cannot loop for 50 steps on your dime; log token usage per execution for a week before optimizing (n8n's execution data shows you exactly where tokens go); and if you are self-hosting 3.0, note that first-class agents now require `N8N_ENABLED_MODULES=agents` — a free setting, but one that silently gates the feature.

## Limits and what I did not test

I did not run a benchmark — the per-run numbers are a transparent model, not measurements, and your token profile will differ. A 2-step classifier and a 20-step researcher differ by 10x in cost on the *same* model, which swamps the between-model differences. Subscription plans (ChatGPT, Claude Pro/Max) are metered separately from API billing and are not in this table. And the obvious one: this market reprices constantly — GPT-6.1 Sol itself is a week old as I write this. Re-check the provider pricing pages before you sign off on a budget.

## Key Takeaways

1. **The September 2026 price war halved the cost of capable agent models** — GPT-6.1 Sol and Claude Sonnet 5.5 both run a mid-size n8n agent at ~$31 per 1,000 runs.
2. **Claude Opus 5.5 ($62/1K) earns its 2x premium on long-horizon tasks** where one avoided retry costs more than the token difference.
3. **GPT-6 Astra ($155/1K) is a specialist model** — same price tier as Claude's ceiling; reserve it for work where capability, not volume, is the constraint.
4. **Output tokens and cache hits move the bill more than the model name** — verbose agents double costs; prompt caching cuts 30–60% for agents that resend stable prompts.
5. **Batch/Flex at 50% off and Max iterations on the AI Agent node** are the two cheapest optimizations, and both are free to apply today.

Next step: log one week of your own n8n executions, pull the real input/output token counts, and re-run the table above with your numbers — that single measurement is worth more than any pricing article, including this one.
