---
title: "Gemini 4 Neon Is Google's $3 Middle Model — Wire It Into n8n in 20 Minutes"
description: "\"gemini 4 neon\" is a Breakout rising search this week: Google's Nov 18 model is 3x faster than Carbon at 32% lower cost per task. Here's the n8n wiring."
date: 2026-11-23
category: news
tags: ["gemini", "gemini 4 neon", "n8n", "google ai", "ai agents"]
draft: false
featured: false
image: "/og/gemini-4-neon-n8n-agent-wiring.webp"
---

Google shipped a new Gemini model on November 18, 2026, and searchers noticed fast enough to push "gemini 4 neon" to Breakout — the #1 rising related query for "AI agent" in the US over the past 7 days (Google Trends Explore, Nov 16–23, 2026, read Nov 23). It is the fourth Gemini 4 model in five weeks, and it is the one most n8n builders should actually reach for: frontier-level reasoning at Flash speeds, priced at $3 per million input tokens.

By the end of this article you will have a working n8n workflow that calls Gemini 4 Neon through the Gemini API, routes each task to the right thinking level, and caps spend before the bill can surprise you — plus an honest read of what Google's benchmark claims do and do not prove.

## What Gemini 4 Neon actually is

Gemini 4 Neon is the middle tier of Google's Gemini 4 family. Google's own description, from the launch post by Koray Kavukcuoglu (SVP, Google DeepMind), is "frontier-level intelligence with fast end-to-end task completion" for complex software engineering, knowledge work, and science workflows. The family, in release order:

| Model | Released | Google's job for it |
|---|---|---|
| Argon | Oct 13, 2026 | Entry tier (now being replaced by Neon in the app picker) |
| Carbon | Nov 10, 2026 | Hardest, long-horizon projects |
| Hydrogen | Nov 12, 2026 | Fast everyday execution |
| **Neon** | **Nov 18, 2026** | Complex, high-frequency work — depth plus efficiency |

Neon sits between Hydrogen and Carbon. It is built from Carbon, tuned for agent work: Google says it cuts redundant file reads, handles context compaction reliably in long sessions, and posted its lowest fabrication rate yet in internal Google Antigravity testing. It also works as an orchestrator in Antigravity, directing parallel Hydrogen subagents.

**The one number that matters for n8n builders:** at its default high thinking level, Neon pairs a high intelligence score with a 32% lower cost per task than Carbon, and roughly 50–80% lower cost per task than top competing frontier models. At xhigh, its deepest setting, it still costs 36%+ less per task than competing models at their highest setting. Indian Express, summarizing the launch, puts it more bluntly: about 3x faster than Carbon at around 60% lower cost. Those are Google's numbers, not independent measurements — treat them as the vendor's claim, not a verified benchmark.

## The benchmarks, with the fine print

Google's launch post leans heavily on third-party benchmarks. The headline figures, all from Google's Nov 18 post:

| Benchmark | Neon result |
|---|---|
| Artificial Analysis Intelligence Index | 61, #3 overall (at xhigh) |
| Vals Index | #2 (70.9%); #1 on Legal Research Bench and Tax Agent Bench |
| Artificial Analysis Coding Agent Index | #1 (58.6) |
| Terminal-Bench 4.1 | 65.2% |
| FrontierCode 2.0 | 46.2% (default high) |
| SWE-sweep | 12.8% mini harness; 39.0% inside the Antigravity harness |
| Zapier AutomationBench | #1 (56.3%) |
| Andon Labs Vending-Bench 2 | #1 ($16,843) |
| Agent Arena Index | #2 (1336, across 4,200+ real-world agent sessions); #2 on steerability |

Two things worth noticing. First, the AutomationBench #1 matters more to this blog's readers than the raw intelligence index: it is a long-horizon test of running a business through tools, which is close to what an n8n agent actually does. Second, the SWE-sweep gap — 12.8% standalone vs 39.0% inside Antigravity — is a reminder that the harness around the model does a lot of the work. Your n8n workflow is that harness. A good router and approval gate will move your results more than swapping one frontier model for another.

## Pricing and thinking levels — the part that decides your bill

Neon has four thinking levels — low, medium, high (the default), and xhigh — that scale reasoning effort and token spend steadily. The price is flat across the full 1M-token context window:

| Item | Value |
|---|---|
| Model ID | `gemini-4-neon` |
| Input | $3.00 per million tokens |
| Cached input | $0.15 per million tokens (95% discount) |
| Output (thinking tokens included) | $15.00 per million tokens |
| Context window | 1,048,576 tokens, shared by input, thinking, and output |
| Max output per synchronous hop | 65,536 tokens |

Do the math on one realistic call before you wire anything up. A task that sends 20,000 input tokens and gets 4,000 output tokens back costs 20,000 × $3/1M = $0.06 input plus 4,000 × $15/1M = $0.06 output — **$0.12 per call**, before thinking tokens. Thinking tokens are billed as output, so an xhigh call that thinks hard before answering can cost several times that. That is why the routing pattern below matters: most n8n tasks do not need xhigh.

> **Warning:** Neon is paid tier only. Google's pricing page states plainly that it is not available on the free tier — every token is billed, thinking tokens included. A Gemini API key alone is not enough; the project behind it needs billing enabled. There is no introductory price, unlike Carbon's promotional rate, which ends November 30, 2026.

Where you can use it today: the Gemini API paid tier in Google AI Studio and Android Studio, Gemini for business (via API or model dropdown), Google Antigravity for paid AI Pro and Ultra subscribers, and the Gemini app for Pro and Ultra subscribers. It is also listed on OpenRouter as `google/gemini-4-neon`. It does not generate images or audio, and it is not available on the Live API.

A separate variant, **Gemini 4 Neon for cyber**, is rolling out to trusted defenders through Google's Fairwind Program. It posts state-of-the-art numbers on the security benchmarks Google cites — 90.5% on SEC-bench Pro, 51.26% on WebExploitBench v1.2, 70.7% on CWE-bench v2 — but it is not something you can call from n8n today, so it is context, not a wiring target.

## Prerequisites

- An n8n instance (Cloud or self-hosted, any recent version) with the HTTP Request node available.
- A Gemini API key on a Google Cloud project **with billing enabled** — create one at Google AI Studio → API keys. Free-tier keys will fail on Neon.
- A rough idea of your per-run budget. If you do not have one, start with $5/day and the spend-cap step below.

## Step 1 - Verify the model with one curl call

Before touching n8n, prove the key and the model ID work from your terminal. Neon supports both the Interactions API (Google's new quickstart shape) and the classic `generateContent` endpoint. The classic endpoint is the easier one to wire into n8n, so verify that:

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-4-neon:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{ "parts": [{ "text": "Reply with the single word OK." }] }],
    "generationConfig": {
      "thinkingConfig": { "thinkingLevel": "low" }
    }
  }'
```

You should see a JSON response with a `candidates` array containing the word OK, plus a `usageMetadata` block showing what you were billed for — input tokens, output tokens, and thinking tokens. If you get a 400 error about the model, the key's project has no billing; if you get a 403, the key is wrong or the project is not on the paid tier.

The `thinkingLevel` field is the whole point of this model: `low`, `medium`, `high` (default), or `xhigh`. Set it per task, not per workflow — that is Step 3.

> **Note:** These request shapes follow Google's published API contract as documented in the Neon guides checked November 23, 2026. I did not make a live Neon call while writing this — the shapes, field names, and prices come from Google's launch post and the API guides that checked them against Google's docs on November 19. If a field name has moved since, Google's API reference is the source of truth.

## Step 2 - Call Neon from n8n with an HTTP Request node

n8n's built-in Google Gemini node may not list `gemini-4-neon` in its model dropdown yet — new model IDs take a while to appear there. The HTTP Request node has no such lag, so use it:

1. Add an **HTTP Request** node. Set the method to POST and the URL to `https://generativelanguage.googleapis.com/v1beta/models/gemini-4-neon:generateContent`.
2. Under Headers, add `x-goog-api-key` with your key stored as an n8n credential (never paste the key into the workflow JSON), and `Content-Type: application/json`.
3. Set the body to JSON and pass the prompt in from the previous node:

```json
{
  "contents": [
    { "parts": [{ "text": "={{ $json.prompt }}" }] }
  ],
  "generationConfig": {
    "thinkingConfig": { "thinkingLevel": "={{ $json.thinkingLevel || 'high' }}" }
  }
}
```

Here is what each piece does. The `contents` array is the conversation — one user message carrying the prompt from the previous node. `generationConfig.thinkingConfig.thinkingLevel` sets the reasoning effort for this call, read from the incoming item so the router in Step 3 can control it. The response arrives as JSON: the text lives at `candidates[0].content.parts[0].text`, and the bill for the call lives at `usageMetadata`.

4. Add a **Set** node after it to pull out just the two fields you need — `candidates[0].content.parts[0].text` as `answer`, and `usageMetadata.totalTokenCount` as `tokensUsed`. Everything downstream reads those two fields and nothing else.

## Step 3 - Route each task to the cheapest thinking level that can do it

This is the pattern that makes Neon worth using instead of Carbon. A router node classifies the incoming task, then sets `thinkingLevel` before the HTTP Request node runs:

| Task type | Thinking level | Why |
|---|---|---|
| Classify, extract, reformat, short summary | `low` | No reasoning needed; cheapest per call |
| Draft a reply, triage a ticket, summarize a doc | `medium` | Some judgment, short horizon |
| Multi-file code change, research synthesis, planning | `high` (default) | Neon's headline performance lives here |
| Hard debugging, architecture, multi-step science | `xhigh` | Deepest reasoning; use sparingly, it bills the most thinking tokens |

In n8n, implement this as a **Switch** node on a `taskType` field, with four branches that each set `thinkingLevel` and pass through to the same HTTP Request node. The Abacus AI xHigh router article on this blog uses the same shape for routing between models — here the routing is between effort levels inside one model, which is cheaper to operate because there is only one API key, one price table, and one failure mode to handle.

![Fig 1 — The Neon thinking press: an n8n agent drops a task into the hopper, the four thinking-level dials (LOW, MEDIUM, HIGH, XHIGH) set the effort, the token meter and cost gauge track the bill, and the approval lever stays locked until a human pulls it.](/figures/gemini-4-neon-n8n-agent-wiring-thinking-press.svg)

*Fig 1 — The Neon thinking press. The n8n agent console (left) feeds a task into the press; the four thinking-level dials select the effort before the call runs, the token meter counts input, thinking, and output tokens, and the cost gauge reads the $3/$15 price table. The approval lever gates the irreversible-action chute: nothing writes, sends money, or publishes until a human pulls it. Readout: $3/1M in · $15/1M out · $0.15 cached · 1M ctx · 32% cheaper per task than Carbon · 0 without approval.*

**The rule that keeps the bill sane:** default every new task type to `medium`. Promote a task type to `high` only after you have seen `medium` fail on it twice. Demote it back the moment `high` stops adding anything. Thinking level is a dial, not a status symbol.

## Step 4 - Cap the spend and gate the writes

Two guards, both before anything irreversible happens:

1. **Spend cap.** After the Set node, add an **IF** node: if the running total of `tokensUsed` for the day (keep it in a Google Sheet or a database row the workflow reads first) exceeds your daily budget, stop the workflow and send yourself a notification instead of calling the model again. A $5/day cap at Neon's prices buys roughly 40 of those $0.12 calls — plenty for testing, and the cap is what stops a runaway loop from turning into a $500 morning.
2. **Human approval before writes.** Neon's own safety story is relevant here: Google reports its lowest fabrication rate yet in Antigravity testing, 0.0% cheating on Terminal-Bench 4.0, and a 0.0% attack success rate on Gray Swan's indirect prompt-injection benchmark at xhigh. That is genuinely good — and still not a reason to let an agent write to a production system unsupervised. Route any step that sends money, deletes data, or publishes something through n8n's **Wait** node (human approval) first. The model being safer does not remove the approval gate; it just means the gate fires less often.

## Step 5 - Verify everything works

Run the workflow with a test prompt at each thinking level and check three things:

1. Each call returns text at `candidates[0].content.parts[0].text` — not an error object.
2. `usageMetadata` shows thinking tokens growing as you go from `low` to `xhigh`.
3. The daily total in your spend sheet matches the sum of the calls you just made.

If a call fails with a 400, check the thinking level value first — `minimal` is rejected, and only `low`, `medium`, `high`, and `xhigh` are valid. If it fails with a 403, re-check billing on the project.

## The catch — what Neon does not solve

- **It is not free, and there is no free tier.** Every token bills, including thinking tokens. A workflow that calls xhigh on every task will cost more than the same workflow on Hydrogen, which is free-tier eligible. Route first, upgrade effort second.
- **Benchmarks are vendor-framed.** The #1 on AutomationBench and #3 on the Intelligence Index are real third-party benchmarks, but Google chose which ones to headline. Independent replication takes weeks; treat the rankings as a shortlist, not a verdict.
- **The model picker churn is real.** Neon replaces Argon, Gemini 3.1 Pro is going away, and 3.5 Flash-Lite is now "Auto" for paid users. If you hardcode model names anywhere, keep them in one place — an environment variable or a config node — so the next rename is a one-line change.
- **Output is text only, capped at 65,536 tokens per synchronous hop.** Long outputs need follow-up calls; plan for that in the workflow rather than discovering it mid-run.

## Where Neon fits in your stack

Use Neon as the default brain for n8n agents that do complex work often: code review across a repo, research synthesis, multi-step planning with tool calls. Keep Hydrogen for fast everyday execution and the free tier, and keep Carbon for the hardest long-horizon problems where its extra depth is worth the higher cost per task. That three-tier split is the same shape as the model-routing pattern in the [Abacus AI router article](/blog/abacus-ai-xhigh-frontier-router-smaug-routing-week/) — Neon just makes the middle tier strong enough that most tasks never need to escalate past it.

For more on Google's agent-side thinking, the [Decisions API article](/blog/gemini-decisions-api-n8n-agent-routing/) covers the 200ms yes/no brain that pairs well with a Neon worker, and the [Gemini universal-worker playbook](/blog/gemini-agent-universal-work-n8n-playbook/) covers the four design ideas behind Google's own agent.

## FAQ

### Is Gemini 4 Neon free?

No. It is paid tier only on the Gemini API — $3 per million input tokens and $15 per million output tokens, thinking tokens included. You can use it at $0 only through a Google AI Pro or Ultra subscription (trial or student offer) in the Gemini app or AI Studio, not through the API.

### What is the model ID for n8n?

`gemini-4-neon`. Call `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-4-neon:generateContent` with your key in the `x-goog-api-key` header. The Interactions API (`POST /v1beta/interactions`) works too.

### Which thinking level should I use?

`high` is the default and where Neon's headline benchmarks were measured. Start new task types at `medium`, promote to `high` only after two failures, and reserve `xhigh` for hard debugging and architecture. `low` is for classification and extraction.

### How is Neon different from Carbon and Hydrogen?

Carbon is the deepest model for the hardest long-horizon work; Hydrogen is the fast, cheap everyday model; Neon is the middle — Carbon-level reasoning quality at roughly 3x Carbon's speed and about 60% lower cost, per Google. It replaces Argon in the lineup.

### Can I use Neon in n8n's Google Gemini node?

Possibly not yet — the node's model dropdown may not list `gemini-4-neon`. Use the HTTP Request node as shown in Step 2; it takes any model ID and keeps working when Google renames the picker again.

## Key Takeaways

1. **"Gemini 4 neon" is a Breakout search** — the #1 rising related query for "AI agent" in the US this week — because Google launched it November 18, 2026 as the middle of the Gemini 4 family.
2. **Neon is the cost-per-task play**: 32% cheaper per task than Carbon at high, 50–80% cheaper than top competing frontier models, at $3/$15 per million tokens with a 1M-token context window.
3. **Route by thinking level, not by model**: low for extraction, medium by default, high for real work, xhigh only for the hardest tasks — thinking tokens bill as output.
4. **Wire it with the HTTP Request node** (`gemini-4-neon:generateContent`), not the Gemini node's dropdown, and keep the model name in one place.
5. **Cap spend and gate writes**: a daily token budget and a human approval step before anything irreversible — a safer model does not remove the approval gate.

Next: swap one existing n8n agent from its current model to Neon at `medium`, run it for a day, and compare the token bill and the failure rate. If `medium` holds, you just cut the cost of that agent by a third; if it fails twice, promote that task type to `high` and move on.
