---
title: "Strands Decider 2B: AWS's Free Local Decision Model That Replaces LLM Routing Calls in n8n"
description: "AWS Strands Decider 2B is a free, open-weight decision model that answers structured agent questions in ~115ms locally — no API fees, no text generation."
date: 2026-10-02
category: news
tags: ["aws", "strands", "decision-models", "ai-agents", "n8n", "local-llm"]
draft: false
featured: false
image: "/og/strands-decider-2b-explained.webp"
---

Every routine choice your AI agent makes — route this message, escalate this ticket, approve this tool call — currently burns a full LLM call: seconds of latency, per-token cost, and a regex over generated text to extract the answer. On October 1, 2026, AWS Strands Labs released **Strands Decider 2B**, a free, open-weight decision model that settles those choices locally in about 115 milliseconds with a calibrated confidence score. A decision model is a model that answers structured questions (yes/no, pick one option, rate on a rubric) instead of generating free-form text. By the end of this article you'll have Strands Decider running on your own machine, serving decisions over a local HTTP endpoint, and wired into an n8n workflow as a confidence-gated routing layer.

## What Decider 2B actually is

Strands Decider 2B has 1.9 billion parameters and is built on the **Qwen3.5-2B** language model (a small open base model), fine-tuned with LoRA — a technique that adjusts a small set of extra weights instead of retraining the whole model. AWS then added what it calls a **pointer head**: a ~1-million-parameter add-on that looks at your predefined options and scores them directly. It picks the best fit **without generating text word by word** — which is the whole trick. No generated words means no token charges, no waiting for a response to stream, and no output that drifts off your allowed answers.

The model supports three question types, the same trio its competitors use:

- **`choice`** — pick 1 of N named options, with per-option probabilities and a confidence value
- **`noul`** — a yes/no question, returning the probability of "yes" as a number between 0 and 1
- **`score`** — rate against an ordered rubric, returning a probability-weighted score

Everything ships open source under the **Apache 2.0 license**: weights on Hugging Face, plus training data and training scripts on GitHub. One honest note up front: I could not complete a full local install in my test environment this morning (the PyTorch download exhausted the test VM's disk), so the commands below follow the official Strands Labs repo docs as reported on October 1–2, 2026 — not a run I personally executed end to end.

**Prerequisites** — Python 3.10+, pip, and any machine you're willing to run a 2B model on: CPU works, Apple silicon Macs work, a consumer GPU like an RTX 3090 gets you the headline ~115 ms numbers. An n8n instance (self-hosted or Cloud) for the integration step.

**Example terminology** — `<decider-url>` is the local server address you'll run below, `http://127.0.0.1:8000` unless you change the port.

## Step 1 - Install the package

The PyPI package gives you both a CLI and a local HTTP server in one shot:

```bash
pip install strands-decider
```

You should see pip resolve the package along with its inference dependencies (PyTorch, Transformers). If the download is slow, that's the model runtime, not the decision model itself — the weights download separately from Hugging Face on first use.

## Step 2 - Start the local decision server

The bundled server starts on your loopback interface and answers decision questions over HTTP:

```bash
strands-decider serve --port 8000
```

You should see a startup line confirming it's listening on `127.0.0.1:8000`. The first request triggers the weight download from Hugging Face (a few GB — expect a pause on first call, then sub-second answers after).

> **Warning:** the bundled server binds to 127.0.0.1 with **no authentication** (per the October 1 release notes). Never expose that port to the network or the internet — anyone who can reach it can spend your compute. For anything beyond a dev box, put your own auth layer (reverse proxy, token check) in front of it.

## Step 3 - Ask your first decision

With the server up, a routing question is one POST away — here asking whether an incoming message needs a human, in the same typed-question shape the model expects:

```bash
curl -X POST http://127.0.0.1:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"message": "My invoice is wrong and I want a refund today", "channel": "chat"},
    "questions": [
      {"name": "escalate", "type": "noul", "question": "Does this message need a human agent?"},
      {"name": "route", "type": "choice", "question": "Which team owns this?", "options": ["billing", "support", "sales"]}
    ]
  }'
```

You should get back structured JSON — per-question answers with calibrated confidences, e.g. `escalate: 0.91`, `route: billing (0.87)` — shaped like the vendor's documented response format. The shape is what matters: probabilities you can act on directly, no text parsing between the model and your workflow logic. Because the pointer head scores your fixed options rather than generating words, an answer arrives in roughly 115 milliseconds median on an RTX 3090 (vendor number, October 1, 2026), versus seconds for a chat-model round trip.

## Step 4 - Wire it into n8n as a confidence gate

The practical pattern for n8n builders: keep the LLM off the hot path and let Decider do triage, with a confidence threshold as the safety valve.

1. Add an **HTTP Request** node pointing at `<decider-url>/decide`, POSTing your typed questions built from the incoming item's data (webhook body, chat message).
2. Follow it with an **IF** node: if the returned confidence is **above your threshold** (say 0.7), follow the model's routing decision automatically.
3. If confidence is **below** the threshold, route to the fallback: a chat-model call, a human-approval step, or a default queue.

That one IF node is the whole reliability story. A decision model can't explain itself — it returns no text, only a number — so the threshold decides how much you trust it, and the fallback decides what happens when you don't. This is exactly the "gate premature tool calls" pattern Strands Labs pitches: verify the action is grounded and safe with a 115 ms local call *before* an expensive LLM executes it.

## How it compares: Decider 2B vs Jev vs Clef vs a chat LLM

Pick ONE skeleton per post — here's the comparison table, with the numbers as reported (vendor benchmarks unless noted):

| | Strands Decider 2B | Typesafe Jev | Cloudflare Clef-flash | Chat LLM call |
|---|---|---|---|---|
| Price | $0 — self-hosted, Apache 2.0 | $0.042 / 1M input tokens | Hosted, per-request | Per-token, most expensive |
| Median latency | ~115 ms (RTX 3090, vendor) | ~70–500 ms end-to-end (vendor) | 38.8 ms (vendor) | Seconds |
| Hosted API | None yet — you run it | Yes | Yes (Workers AI) | Yes |
| Privacy | Fully local, data never leaves | Sent to Typesafe | Sent to Cloudflare | Sent to provider |
| Accuracy tier | ~72% on public JevBench v19 (vendor chart); 2nd among ~2B public models | 79.74 macro-F1 on BANKING77 (Cloudflare's test) | 90.93 macro-F1 on BANKING77 | Highest (but overkill for routing) |

The honest read, with the caveats the vendors won't headline: VentureBeat's comparison notes there is **no demonstrated accuracy or latency win** over Jev — the clear, proven advantages of Decider 2B are openness (weights, training data, and scripts all public) and self-hosting (run it on your own MacBook; your data never leaves). Whether it's actually cheaper than Jev's hosted API depends on your hardware and volume, since you supply the compute. And accuracy is vendor-chart territory until independent benchmarks land — treat the JevBench numbers as directional.

When to pick Decider 2B: you need routing/gating/triage at high volume, you care about data staying on your infrastructure, and your decision space is stable (fixed options, fixed rubrics). When not to: your categories change weekly (you'd be retraining), you need an explanation for each decision (it returns none), or the decision needs reasoning rather than classification — send those to the LLM.

## Key Takeaways

1. **Strands Decider 2B makes routine agent decisions free and local** — 1.9B params, Apache 2.0, ~115 ms answers on a consumer GPU, no per-call fee.
2. **It can't generate text** — the pointer head scores your fixed options directly, which is exactly why it's fast and cheap.
3. **Pair every decision with a confidence threshold** — auto-act above it, fall back to an LLM or a human below it; the model can't explain itself.
4. **Self-hosted is the real win, not the headline speed** — no hosted API exists yet, so you supply compute; the proven edge over Jev is openness and data privacy, not measured accuracy.

Next step: pick one routing decision in a workflow you already run — the chat-model call that classifies incoming messages — and run Decider 2B against it for a week. Log the model's choice, its confidence, and what the LLM would have chosen. That comparison table is the only benchmark that matters for your traffic, and it costs you nothing but local compute.

---

## FAQ

### Where do I get Strands Decider 2B?

`pip install strands-decider` gives you the CLI and local HTTP server; weights are on Hugging Face and training data plus scripts on GitHub, all Apache 2.0 (as of October 1, 2026).

### Does it need a GPU?

No — it runs on CPU and Apple silicon Macs, though latency will be higher than the ~115 ms vendor number measured on an RTX 3090.

### Can it replace my LLM entirely?

No. It's a classifier, not a reasoner — worse than reasoning models on complex problems, and unsuited for chat, coding, or summarization. Use it for routing, gating, and triage; keep the LLM for decisions that need reasoning.

### How is it different from Cloudflare Clef?

Clef is hosted and faster at the top end (Clef-flash: 38.8 ms median), with vision support; Decider 2B is self-hosted and free, so your data never leaves your infrastructure. They target the same new layer of the agent stack — see our [Clef breakdown](/blog/cloudflare-clef-decision-models-explained/) for the hosted side.

### Is it production-safe out of the box?

Not quite: the bundled HTTP server has no authentication, so put your own auth layer in front of it, and gate decisions with a confidence threshold plus an LLM/human fallback.
