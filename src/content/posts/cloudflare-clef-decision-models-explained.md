---
title: "Cloudflare's Clef Decision Models: Stop Sending Every Agent Decision to an LLM"
description: "Cloudflare's open-weight Clef decision models answer structured agent questions in milliseconds — faster and cheaper than chat LLMs for routing and gating."
date: 2026-10-02
category: news
tags: ["cloudflare", "ai-agents", "decision-models", "n8n", "workers-ai"]
draft: false
featured: false
image: "/og/cloudflare-clef-decision-models-explained.webp"
---

Cloudflare launched **Clef and Clef-flash** on October 1, 2026 — two open-weight "decision models" that answer structured questions about your agent's state instead of generating text. The flagship Clef returns a decision in a median of 209.3 milliseconds; Clef-flash does it in 38.8 milliseconds. A decision model is a model that returns probabilities for a fixed set of allowed answers (yes/no, pick one option, score against a rubric) instead of generating free-form text — so if your AI agent currently burns an LLM call on every routing or gating choice, this is the part of your pipeline that's about to get dramatically cheaper.

The timing is not a coincidence. Three weeks ago, OpenAI shipped its [Decisions API](/blog/openai-devday-2026-announcements/), Amazon's Strands Labs released the 2B-parameter **Strands Decider 2B** for local use, and Typesafe's **Jev** kicked off the category in September. Decision models have quietly become the fastest-moving new layer in the agent stack. Here's what Clef is, what the numbers say, and how to use it in an agent you actually run.

## What Clef actually does

Forget chat. You hand Clef an input state (text, JSON, or up to four images) plus a schema of typed questions, and it returns a probability for every allowed answer. No free-form output to parse, no reasoning tokens to wait for, no prompt drift between calls. Cloudflare describes the three question types:

- **`noul`** — yes/no questions, returns the probability of "yes" (e.g. "should this ticket escalate?")
- **`choice`** — pick one named option, with per-option probabilities and a confidence value (e.g. route this request to billing, support, or sales)
- **`score`** — rate against an ordered rubric, returning a probability-weighted score (e.g. toxicity or urgency on a 1–5 scale)

A single Workers AI request can carry up to 64 questions, so one forward pass can settle an entire routing tree for an incoming event.

Both models run on GPUs across Cloudflare's network on **Workers AI** (`@cf/cloudflare/clef` and `@cf/cloudflare/clef-flash`), and the weights are open-sourced under the **Apache 2.0 license** on Hugging Face — you can self-host your own copy. Clef implements the same **System One API** as Typesafe's Jev, so an existing Jev integration migrates by changing the endpoint and the model name.

![A classic decision tree: one input, a fixed set of branches, one answer — the structured pattern decision models apply to agent routing](/images/cloudflare-clef-decision-models-explained/decision-tree.png)

## The numbers: latency and accuracy

Cloudflare's published benchmarks (43 runs; as of October 1, 2026) make the latency case plainly:

| Latency | Clef (27B) | Clef-flash (9B) | Jev |
|---|---|---|---|
| Median | 209.3 ms | **38.8 ms** | 524.1 ms |
| p95 | 238.6 ms | **122.4 ms** | 536.0 ms |

Clef is 2.5x faster than Jev at the median; Clef-flash is 13x faster. On accuracy, Clef leads on 7 of the 10 decision benchmarks Cloudflare tested. On BANKING77 (a standard intent-classification set), macro-F1 scores were **94.20 for Clef**, 90.93 for Clef-flash, and 79.74 for Jev.

For context on the other entrant: Strands Decider 2B (open weights plus training scripts, built to run locally) scores around 72% accuracy on the public JevBench v19 set — competitive for a 2B model, but well below Clef's accuracy tier. And one Clef feature neither competitor advertises: **vision** — up to four images per request, so the same model can classify a screenshot or a photo the way it classifies text.

One honest caveat: these are vendor benchmarks on decision-specific evals. Independent runs are just starting to land — one early community benchmark ran Clef against Jev on a paid production-shaped workload from a spare RTX 3090, with more results expected this week.

## Why this matters for AI agent builders

The pattern every agent builder knows: you pipe every small decision through a chat model — route this message, check whether that tool call is safe, decide whether to escalate — and pay in latency (seconds), cost (per-token pricing on every pass), and brittleness (regexes over generated text). A decision model replaces that with one forward pass ending in a probability.

The concrete uses for n8n and automation builders:

1. **Routing gates** — classify an incoming webhook or chat message and route it to the right branch, no LLM needed.
2. **Tool-call gating** — verify a tool call is grounded and safe before an expensive LLM executes it (Strands Labs' own framing: "gating premature actions").

![A neural network diagram: decision models are classifiers that output calibrated probabilities, not free-form text generators](/images/cloudflare-clef-decision-models-explained/neural-network.png)
3. **Human-approval triage** — score incoming events against an escalation rubric; auto-approve the low-risk ones, flag the rest.
4. **Quality supervision** — score agent outputs against a rubric cheaply enough to run on every execution, not just samples.

The System One API compatibility is the practical hook: if you already call a decision API from an n8n **HTTP Request node**, swapping to Clef is an endpoint change. A sketch of the request shape (replace `<your-token>` and `<your-account-id>` with your Workers AI credentials):

```json
{
  "input": { "message": "My invoice is wrong and I'm furious", "channel": "chat" },
  "questions": [
    { "name": "escalate", "type": "noul", "question": "Does this need a human?" },
    { "name": "route", "type": "choice", "question": "Which team owns this?", "options": ["billing", "support", "sales"] },
    { "name": "urgency", "type": "score", "question": "Urgency on a 1-5 scale", "rubric": ["not urgent", "mild", "moderate", "high", "critical"] }
  ]
}
```

You get back calibrated probabilities per answer — a decision your workflow can act on immediately, with no parser between the model and your `IF` node.

## Limits: what Clef is not

A decision model is a classifier with opinions, not a reasoner. It doesn't generate text, call tools, or handle novel categories gracefully — if your decision space changes weekly, you'll be retraining or fine-tuning, which is exactly why Cloudflare is launching an **RL fine-tuning service** alongside Clef (currently invite-only with forward-deployed engineers; self-serve comes later). Calibration on *your* distribution is the real work; the 94.20 macro-F1 was on BANKING77, not your tickets.

Vendor lock-in is worth naming too: the Jev-System One API compat means you can move between providers today, but a pipeline built on a closed API is a bet on one company's uptime and pricing. Clef's Apache 2.0 weights are the hedge — download your own copy and you own the model regardless of what hosting costs next year.

## Key Takeaways

1. **Decision models are the new agent layer** — Clef, Clef-flash, Strands Decider 2B, and Jev all launched within six weeks; the category is real and moving fast.
2. **Keep the LLM off the hot path** — route, gate, and triage with a decision model (38.8 ms median for Clef-flash), then hand off to an LLM only for actions that need reasoning.
3. **Structured beats parsed** — probabilities for fixed answers eliminate the regexes over generated text that break your routing in production.
4. **Open weights change the math** — Apache 2.0 Clef weights mean you can self-host and own the model, not just rent the API.

Next step: if you have an agent that routes messages with a chat model today, benchmark one decision-model call against it this week — measure median latency and cost per 1,000 decisions. That's the number that decides whether this layer earns its place in your pipeline.

*Images: Wikimedia Commons (public domain / CC BY-SA 3.0)*
