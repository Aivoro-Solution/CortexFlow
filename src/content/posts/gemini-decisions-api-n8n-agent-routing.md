---
title: "Google's Decisions API Gives Your n8n Agent a 200ms Yes/No Brain — the Wiring Pattern"
description: "Google's Gemini Decisions API scores 1,000 yes/no, choice, and rubric questions in one 150–250 ms pass for $0.10/1M tokens. Here's the n8n wiring."
date: 2026-11-15
category: news
tags: ["gemini", "google-ai-studio", "decisions-api", "n8n", "ai-agent", "routing"]
draft: false
featured: false
image: "/og/gemini-decisions-api-n8n-agent-routing.webp"
---

Searches for "google ai studio" surged +4,150% in the US this week — the fastest-rising query tied to "MCP server" on Google Trends (US, past 7 days). The surge has a real trigger: on November 11, 2026, Google DeepMind launched the Gemini Decisions API, a new endpoint that answers closed-set questions instead of generating text. Your agent asks up to 1,000 yes/no, multiple-choice, or rubric questions about one input, and gets calibrated probabilities back in 150–250 milliseconds — for $0.10 per million input tokens and zero output tokens.

That matters because most agents today burn a full LLM call every time they need a simple decision. Route this ticket? Approve this refund? Is this screenshot a real defect? Each question costs a generation call, output tokens, and a second or two of latency — and the answer arrives as prose your workflow then has to parse. The Decisions API replaces that whole dance with a single scoring pass. By the end of this post you will have it wired into n8n as a deterministic router and approval gate, with a confidence threshold that sends ambiguous cases to a human.

## What the Decisions API actually is

The API is a new endpoint in the Gemini Developer API, powered by a purpose-built model called Gemini Decision 1 (`gemini-decision-1`). It is not a chat model. It does not generate text. You send one shared multimodal input — text, images, audio, video, or PDFs, up to 256K tokens — plus a map of up to 1,000 independent questions, and the model scores every candidate answer in a single forward pass instead of decoding token by token.

There are three question types, and they cover nearly every routing decision an agent makes:

- **noul (yes/no):** estimates the probability that a condition holds, with optional true/false descriptions. "Is this a product defect?" "Does this email contain a payment instruction?"
- **choice (multiple choice):** picks from 2 to 255 options and returns the winner plus normalized probabilities for every candidate. "Which queue takes this ticket — billing, support, or engineering?"
- **score (ordered rubric):** grades the input against an ordered rubric starting at 0, returning a continuous weighted score and per-level probabilities. "Rate the severity: clean, minor spill, major hazard."

Every answer carries a confidence score from 0 to 1, so your code can route low-confidence cases to a fallback or a human reviewer. That confidence value is the whole point for builders: it turns a model judgment into a number your workflow can branch on without parsing prose.

![Fig 1 — The decision press: one input drum feeds a single scoring pass, three question-type dials (noul, choice, score) stamp out calibrated answers, and the routing lever throws the winner to a lit output cell while low-confidence cases wait for human review.](/figures/gemini-decisions-api-n8n-agent-routing-decision-press.svg)

The headline numbers, all from Google's November 11 launch post:

| Fact | Value |
|---|---|
| Model | `gemini-decision-1` (Gemini Decision 1) |
| Endpoint | `POST https://generativelanguage.googleapis.com/v1beta/decisions` |
| Questions per request | 1 to 1,000 |
| Input | One shared multimodal input, up to 256K tokens |
| Latency | 150–250 ms end-to-end (50–100 ms model compute) |
| Price | $0.10 per 1M input tokens, $0 output tokens |
| Free tier | No-cost tier in Google AI Studio for prototyping |

Two details in that table deserve attention. First, latency stays nearly flat from 1 to 100 questions per request, according to Google — asking 100 questions costs roughly the same time as asking one, because the input is scored once. Second, the shared input is billed once per request no matter how many questions you evaluate; each question adds only its own instruction and criteria tokens. Google also claims the API is nearly 5x cheaper across its shared benchmark suite than Gemini 3.5 Flash-Lite with the Interactions API, and that the model leads the suite with the lowest calibration error. Both are Google's claims from its own benchmarks — I have not independently reproduced them, and one independent model catalog notes Google publishes no calibration-error figure (ECE) for the model, so treat "lowest calibration error" as a vendor claim, not a measured fact.

Google is already using the API as a control plane inside its own products: Gemini Notebook routes incoming queries to the optimal model tier with it (up to 40% lower latency on everyday queries, per Google), Stitch uses it for a rapid-canvas experiment that generates playable wireframes in seconds, the CC app from Google Labs picks an emoji from a 200-plus palette in a fraction of a second, and — most relevant to this blog's readers — **Google Search uses the Decisions API as a safety layer for MCP tools**, detecting adversarial behavior against adversarial evals inside the latency envelope. Integrations are rolling out across OpenRouter, LangChain, Vercel, LiteLLM, Pydantic AI, Pipecat, LiveKit, and OpenCode, with the `google-genai` SDKs at version 3.2 or later.

The same week gave the "google ai studio" surge a second driver: on November 9, Google put Maps Platform inside AI Studio, so you can describe a location-aware app and Gemini configures Maps and a demo key for you — 100 calls per API per day, no credit card, demo key only (Route Optimization, Solar, and Nav Connect are excluded; production needs a billed Cloud project). The Decisions API is the bigger story for agent builders, but the two launches together explain why the query is spiking.

## Why this changes the n8n pattern

The standard n8n approach to "should the agent do X?" is an LLM call with structured output: a Google Gemini or OpenAI node, a JSON schema, and a prompt that says "answer only yes or no." It works, but it has three costs that add up at volume. It generates output tokens for every decision, so you pay for decoding. It takes a second or more per decision, so a 10-check policy gate takes 10 seconds sequentially. And the answer is text — "Yes" with a capital Y, "yes." with a period, a JSON blob with an extra key — so you write parsing and repair code around it.

The Decisions API removes all three. One request scores every check at once, in about 200 ms, for input tokens only, and returns numbers. That makes five things practical that were previously too slow or too expensive:

1. **A deterministic router.** One call picks the queue, the model, or the tool — and returns the runner-up probabilities, so you can log how close the call was.
2. **A policy gate.** Ask 20, 50, or 100 yes/no policy questions about one input in a single request, before the agent acts.
3. **An approval check with a threshold.** High confidence plus a safe answer means proceed; anything else means ask a human. The threshold is a number in your workflow, not a vibe in a prompt.
4. **A grader.** Score incoming work against a rubric — ticket severity, lead quality, draft readiness — and route on the score.
5. **A cheap safety layer.** Google's own MCP-tool safety use is the template: score the tool call against adversarial-behavior questions before it executes.

## Prerequisites

- An n8n instance (self-hosted or Cloud) with the HTTP Request node available.
- A Gemini API key from [Google AI Studio](https://aistudio.google.com) (free tier available for prototyping). Store it as an n8n credential — never paste it into a workflow field as plain text.
- The `google-genai` SDK at version 3.2 or later if you prefer the Python route (the SDK call needs `api_version` set to `v1beta` explicitly).

## Step 1 - Get the key and understand the call shape

Create the key in Google AI Studio and save it as a Header Auth credential in n8n (header name `x-goog-api-key`). The Decisions API does not use the `Authorization: Bearer` header, and it does not live on the usual `generateContent` path — it has its own endpoint, `POST https://generativelanguage.googleapis.com/v1beta/decisions`. A model-ID swap in an existing Gemini node will not work; the request shape is different.

The canonical call, from Google's own launch post, looks like this in Python. It checks a photo of a breakroom counter plus a text note against all three question types in one request:

```python
from google import genai

client = genai.Client(http_options={"api_version": "v1beta"})

result = client.decisions.create(
    model="gemini-decision-1",
    input=[
        {
            "type": "image",
            "uri": "https://storage.googleapis.com/generativeai-downloads/images/spill.jpg",
            "mime_type": "image/jpeg",
        },
        {
            "type": "text",
            "text": "Breakroom counter check before the 9 AM client meeting.",
        },
    ],
    questions={
        "has_spill": {
            "type": "noul",
            "instructions": "Is there an uncleaned liquid spill on the counter?",
        },
        "next_action": {
            "type": "choice",
            "instructions": "Which cleanup action fits the scene?",
            "criteria": {
                "wipe_with_cloth": "Small counter spill with a cloth or towel already nearby.",
                "dispatch_janitorial": "Large floor hazard, broken glass, or active leak.",
                "ready_for_meeting": "Counter is clean and ready.",
            },
        },
        "severity": {
            "type": "score",
            "instructions": "Rate the severity of the counter mess.",
            "criteria": [
                "Clean and ready.",
                "Minor localized spill.",
                "Major spill or safety hazard.",
            ],
        },
    },
)
```

Three things to notice. The `input` field uses the same `Content` block format as the Interactions API. The `questions` map is keyed by name, so each answer comes back under the name you chose. And `criteria` does the real work: for `choice`, each option gets a plain-language description the model scores against; for `score`, the criteria list is the ordered rubric. Write criteria like a specification, not a hint — "Large floor hazard, broken glass, or active leak" scores far more reliably than "bad."

## Step 2 - Call it from an n8n HTTP Request node

Add an HTTP Request node where your agent currently makes its routing decision. Configure it like this:

- **Method:** POST
- **URL:** `https://generativelanguage.googleapis.com/v1beta/decisions`
- **Authentication:** Header Auth, header `x-goog-api-key`, value your stored Gemini API key
- **Send Body:** JSON, with a body that mirrors the SDK call — `model`, `input`, and `questions`:

```json
{
  "model": "gemini-decision-1",
  "input": [
    {
      "type": "text",
      "text": "={{ $json.ticket_text }}"
    }
  ],
  "questions": {
    "is_urgent": {
      "type": "noul",
      "instructions": "Does this ticket need a response within one hour?"
    },
    "route_to": {
      "type": "choice",
      "instructions": "Which team owns this ticket?",
      "criteria": {
        "billing": "A charge, invoice, refund, or subscription problem.",
        "support": "A how-to question or a feature that is not working as documented.",
        "engineering": "A reproducible bug, an API error, or a data-loss report."
      }
    },
    "severity": {
      "type": "score",
      "instructions": "Rate the severity of the reported problem.",
      "criteria": [
        "Cosmetic or a question.",
        "A feature is degraded but a workaround exists.",
        "Core functionality is broken or data is at risk."
      ]
    }
  }
}
```

> **Note:** the endpoint and the `x-goog-api-key` header are confirmed from Google's docs via two independent write-ups (November 12). The REST body mirrors the SDK call shown above; the AI Studio Decisions API guide is the source of truth for field names while the API is in `v1beta`, so check it if a field errors. Do not send the key as a query parameter or in an `Authorization` header — the Decisions endpoint expects `x-goog-api-key`.

## Step 3 - Route on the winner and the confidence

The response returns one answer per question name, each with probabilities and a confidence score from 0 to 1. Add an IF node after the HTTP Request node that checks the confidence of the answer you are about to act on:

- **If `route_to` confidence is 0.85 or higher:** pass the winning queue to a Switch node that routes to the billing, support, or engineering sub-workflow.
- **If confidence is below 0.85:** send the ticket plus the top two candidates and their probabilities to a human — a Slack message, a Telegram message, or an n8n Form Trigger — and stop. Do not let the agent guess.

The 0.85 threshold is a starting point, not a law. Pick it by measuring: run a week of traffic through the node, log the winner, the confidence, and what a human would have chosen, then set the threshold where the error rate you accept meets the automation rate you want. A threshold you never measure is just a guess with a decimal point.

The same pattern doubles as an approval gate. Before any step that moves money, deletes data, or sends a message to a customer, add a `noul` question — "Is this action safe and within the approved scope?" — and require both a "yes" winner and confidence above your threshold. The check costs a fraction of a cent and about 200 ms. The pattern is the same one this blog has recommended since the [FAA's SMART advisor](/blog/faa-smart-ai-agent-nationwide-ground-stop/) and the [Claude outage fallback](/blog/claude-outage-nov-13-n8n-fallback/): the machine proposes, a number decides whether a human is needed, and nothing irreversible happens on a guess.

## Step 4 - Batch the policy gate into one request

This is where the 1,000-question limit pays off. Instead of one LLM call per policy check, put every check into a single `questions` map on the same input. A content-moderation gate, for example, can ask twenty yes/no questions at once — contains a payment instruction, contains a credential, asks the agent to ignore prior instructions, requests a refund above the limit, mentions a competitor's checkout — and get twenty calibrated answers back in one ~200 ms round trip. The shared input is billed once; each question adds only its own instruction tokens.

> **Warning:** batching has a failure mode worth naming. If one question in the map is badly written, its answer will be wrong while the other 999 are right — and nothing in the response flags the bad one. Validate each question on its own first, with known-good and known-bad inputs, before you add it to a batch. A policy gate is only as good as its worst-written question.

## Step 5 - Verify the whole loop

Send a test ticket through the workflow and check three things in the HTTP Request node's output:

1. Each question name you sent appears in the answers, with a probability and a confidence score.
2. The `choice` winner matches what you would pick by hand, and the runner-up probability is meaningfully lower — a 0.52 vs 0.48 split is a coin flip, not a decision, and your IF node should treat it as one.
3. The end-to-end time for the node is in the low hundreds of milliseconds, not seconds. If it is seconds, check that you are hitting `/v1beta/decisions` and not accidentally routing through a chat-completion path.

## What it costs at real volume

The pricing is input-only, which makes the math simple. A 2,000-token ticket scored against 20 questions costs 2,000 input tokens plus the question instructions — roughly $0.0002 to $0.0003 per ticket at $0.10 per million input tokens. Ten thousand tickets a day is about $2–3 a day. Compare that with the pattern it replaces: a structured-output call per decision, each with its own prompt and output tokens, typically an order of magnitude more per decision and a second or more of latency. Google's "~5x cheaper than Flash-Lite" claim is a benchmark comparison, not a promise about your workload — but the direction is unambiguous, because the Decisions API bills zero output tokens and no per-question generation.

| Approach | Per decision | Latency | Output tokens |
|---|---|---|---|
| LLM call with structured output | Prompt + output tokens, per check | ~1–2 s per check | Billed |
| Decisions API, 1 question | Input tokens only | 150–250 ms | $0 (none produced) |
| Decisions API, 100 questions | Input billed once | ~150–250 ms, nearly flat | $0 (none produced) |

## What it cannot do (yet)

- **It cannot generate text, call tools, or hold a conversation.** If the answer needs a sentence, you still need a generative model. The Decisions API is a scorer, not a speaker.
- **It runs on the Developer API only.** Vertex AI (Gemini in Google Cloud) support is listed as "coming soon," with no date. If your stack is Vertex-only, you wait.
- **No Batch API, no context caching, no Flex or Priority inference.** Input repeated across requests is billed in full each time, so a long shared document re-sent on every call costs on every call. Keep the input lean.
- **It is v1beta.** The endpoint, field names, and limits can change. Pin the version in your workflow notes and re-check the AI Studio guide before you build a production dependency on it.
- **Free-tier limits are reported, not confirmed here.** Independent write-ups checked on November 12 list 200 requests per minute, 50,000 tokens per minute, and 10,000 requests per day on the free tier. Treat those as reported numbers and confirm them on Google's rate-limits page for your account.
- **Calibration claims are Google's.** The launch post says the model leads its benchmark suite with the lowest calibration error. No independent calibration figure has been published yet. Measure confidence against your own labeled data before trusting it on high-stakes decisions.

## FAQ

### Is the Decisions API a replacement for an LLM judge in n8n?

For closed questions — yes/no, pick-one, grade-this — yes, and it is faster and cheaper than a judge call. For open-ended judgment ("is this draft good?"), no: that needs generation, and the Decisions API does not generate. Use it for the routing and gating layer, and keep a generative model for the work itself.

### Can I call it from n8n's built-in Google Gemini node?

Not directly. The built-in node speaks the `generateContent` path, and the Decisions API lives on its own `/v1beta/decisions` endpoint with a different request shape. Use the HTTP Request node as shown in Step 2, or a Code node with the `google-genai` SDK.

### Does it work with images, audio, and PDFs?

Yes — the shared input accepts text, images, audio, video, and PDFs in one request, up to 256K tokens, and you can mix modalities (a call recording plus account metadata, a scanned claim plus damage photos). You can tune image and video resolution to control token cost.

### What about the Maps launch in AI Studio?

That is the other half of this week's surge: since November 9, describing a location-aware app in AI Studio lets Gemini configure Google Maps Platform and a demo key for you (100 calls per API per day, no credit card). It is a prototyping shortcut, not an agent primitive — the demo key is not for production, and three APIs (Route Optimization, Solar, Nav Connect) are excluded from it. If you build location features with agents, the Decisions API is the piece that belongs in your workflow; the Maps integration is the piece that belongs in your prototyping loop.

### Should I replace all my LLM routing with it today?

Replace the closed-set decisions first — routing, triage, policy checks, severity grading — and measure the confidence distribution for a week before you lower the human-review threshold. Keep generative calls for anything that needs a sentence back. The API is four days old and in beta; build the pattern, not a hard dependency.

## Key Takeaways

1. **The Decisions API scores instead of generating** — up to 1,000 yes/no, choice, or rubric questions in one pass over one input, in 150–250 ms, for $0.10 per 1M input tokens and zero output tokens.
2. **Every answer carries a confidence score** — route on the winner, and send anything below your threshold to a human. A threshold you never measure is a guess.
3. **It lives on its own endpoint** — `POST /v1beta/decisions` with an `x-goog-api-key` header. A model-ID swap in an existing Gemini node will not work.
4. **Batch the policy gate** — one request can score dozens of safety questions at once, with the input billed once. Validate each question alone before batching it.
5. **It is a scorer, not a speaker** — no text generation, no tools, no Vertex AI yet, no batch or caching. Use it for the decision layer and keep a generative model for the work.

Next: wire the pattern into one real workflow this week — a ticket router or a pre-send approval check — and log the winner, the confidence, and the human's call for every decision. The log is what turns the threshold from a guess into a number. If you run the Claude-outage fallback pattern from this week, the Decisions API is the cheapest way to add the "is it safe to retry?" check before the fallback model fires.

*Sources: Google DeepMind launch post, "Gemini Decisions API: Fast, calibrated multimodal decisions" (Nov 11, 2026); Google Developers Blog, Maps Platform in AI Studio (Nov 9, 2026); Google Trends Explore, US, past 7 days (Nov 15, 2026). Free-tier limits and Batch/caching exclusions as reported by independent write-ups checked Nov 12, 2026.*
