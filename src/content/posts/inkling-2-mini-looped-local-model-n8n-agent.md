---
title: "Inkling 2 Mini Runs a Looped 26B Model on a Laptop — Wire It Into n8n Safely"
description: "Inkling 2 Mini is up 4,750% in Trends. Run the looped 26B open model locally and wire it into n8n with caps and an approval gate."
date: 2026-11-28
category: news
tags: ["ai agents", "n8n", "local ai", "open weights", "ollama"]
draft: false
featured: false
image: "/og/inkling-2-mini-looped-local-model-n8n-agent.webp"
---

"inkling 2 mini" is up 4,750% as the top rising related query for "AI agent" in Google Trends (US, past 7 days) this week. The spike follows a real release: on November 20, 2026, Thinking Machines Lab shipped Inkling 2 Mini, an open-weight model built to run on a laptop instead of a server rack.

An open-weight model is one whose trained weights you can download and run yourself. Inkling 2 Mini stores 26.4 billion parameters but activates only 3.4 billion per token, and it reuses its middle layers three times per token to spend more compute on reasoning without storing more weights.

By the end of this article you will know how that looping works, what hardware and runtime you actually need, which benchmark claims to trust, and how to wire the model into n8n so a local agent stays capped, logged, and behind human approval.

## What Thinking Machines released on November 20

Inkling 2 Mini arrived on November 20, 2026 under the Apache 2.0 license, with weights on Hugging Face as `thinkingmachines/Inkling-2-Mini`. It accepts text and image inputs and generates text, with a context window of up to 1 million tokens.

| Detail | Published value |
| --- | --- |
| Stored parameters | 26.4 billion |
| Active per token | 3.4 billion (5.4 billion counting loop passes) |
| Layers | 24 stored, 48 applications per token |
| Experts | 8 of 128 per token |
| Official checkpoint | About 20 GB (19.5 GB + 0.64 GB draft head) |
| Precision | NVFP4 in layers 0–19, MXFP8 in layers 20–23 |
| License | Apache 2.0 |

Interest was fast. By November 23, 2026, the official repository showed 5,301 likes and 41,888 downloads, and Unsloth's GGUF repository showed 1.29 million downloads, per a local-deployment guide checked that day against the model card and repository listings. Downloads measure curiosity, not quality — but they explain why the name is trending.

The model follows Inkling 2 Small, a 594-billion-parameter sibling built for GPU servers whose weights arrived on November 12, 2026. Mini is the personal-device rung of the same family. Do not confuse either with the July 2026 Inkling-Small generation; older files will not load as Inkling 2 Mini.

## How the loop works, in plain language

A transformer is the neural-network architecture behind most modern language models; it processes text in layers, one after another. A standard transformer runs each layer once per token, where a token is a chunk of text the model reads or writes.

Inkling 2 Mini stores 24 layers in four blocks of six. The first block and the last block each run once. The two middle blocks — 12 layers — run three times with shared weights. Each token therefore passes through 48 layer applications while the download stays at 24 layers.

Each layer is also a mixture of experts (MoE), which means only some specialist sub-networks fire for each token: here, 8 of 128 experts per token. That is why the active count is 3.4 billion even though 26.4 billion parameters are stored. Counting the repeated middle passes, the effective compute is about 5.4 billion parameters per token — use 5.4 billion, not 3.4 billion, when you estimate speed.

The lab's reason for looping the middle is that those layers do more abstract reasoning, while the first and last layers do more translating in and out of the model's internal space. Looping lets the model think longer without writing all of that work into visible output.

**Looping adds reasoning compute. It does not add stored knowledge.** The lab states that knowledge is mostly a function of total parameter count, and closed-book factual tests did not improve with more passes. Expect better multi-step work, not a better memory for facts.

![An isometric loop press: a token carriage enters past four layer blocks, the two middle blocks loop three times under an orange return chute, and only a finished token reaches the output tray.](/figures/inkling-2-mini-looped-local-model-n8n-agent-loop-press.svg)

*Figure 1: The loop press. Twenty-four stored layers produce 48 applications because the middle 12 run three times; the orange chute is the shared-weight return path. Notice the readout — 26.4B stored, 3.4B active, 5.4B effective — the gap between stored and effective is the whole design.*

## What you need to run it

Thinking Machines' own guidance is conservative: Apple silicon with at least 32 GB of memory, a single NVIDIA DGX Spark, or other GPUs with 32 GB or more recommended. The launch demo ran offline on a MacBook Pro with an M5 Pro and 48 GB in airplane mode. That demo proves the shape works; it does not promise every 32 GB laptop matches it.

Smaller builds exist. Four-bit GGUF files of 15.1 to 19.7 GB run on a 24 GB GPU or a 32 GB Mac, per the November 23 local guide. The official file is already roughly 4-bit because the model was trained in its release precision, so the 52.2 GB BF16 file adds memory without adding information. Q8_0 at 27.8 GB is the practical ceiling.

Memory is weights plus the key-value (KV) cache for the context you keep, plus runtime overhead. The 1M-token window is a maximum, not a default to use: the full window needs about 34.4 GB of cache alone in the guide's llama.cpp arithmetic. For agent work, cap the context deliberately — 65,536 or 131,072 tokens leaves room to think without swapping.

Runtime support is new, and the routes differ by platform:

- **Mac:** Ollama, LM Studio, llama.cpp with Metal, and MLX all run it. Ollama v0.40.17 added the model as a pre-release for Apple silicon only; pin that version and expect manifest changes before stable.
- **NVIDIA or AMD GPU:** use llama.cpp or LM Studio with a GGUF file until Ollama adds PC support. Mainline llama.cpp supports the model from build b12600, released November 20, 2026.
- **Shared server:** vLLM needs version 0.35.0 or newer, available only as a nightly build as of November 23, 2026, with tool calling as an opt-in. SGLang support sits in a pull request and a dedicated image. Treat both as pre-release.

On a Mac, the shortest path is:

```bash
ollama run inkling-2-mini
```

This pulls the 20 GB library build with image input, tools, and thinking enabled. Raise the context only as far as your memory allows; Ollama sets a default based on available memory, and agent sessions need more than a chat default. On a GPU, the guide's llama.cpp form caps context and reasoning effort explicitly:

```bash
llama serve -hf ggml-org/Inkling-2-Mini-GGUF:IQ4_NL -c 65536 \
  --chat-template-kwargs '{"reasoning_effort":"medium"}'
```

Here `-c 65536` caps the context at 65,536 tokens, and `reasoning_effort` trades thinking depth for speed; it defaults to `high`, and even `none` does not switch reasoning off completely. You should see the server start and answer a short prompt before you connect any workflow to it.

> **Warning:** Unsloth publishes two copies of its files. The top-level files need Unsloth's own llama.cpp build; the `Mainline_Support` folder holds the same quantizations for standard llama.cpp. Mixing them wastes an evening.

## Which benchmark claims to trust

Thinking Machines reports that Inkling 2 Mini leads every open-weight model with fewer than 100 billion total parameters on DeepSWE v1.1 at 48.2% and Vals Index v2.2 at 46.5%. Those are lab-reported numbers on the lab's harness, and the announcement notes that evaluation setups vary by model. Treat them as the lab's claim, not an independent bake-off.

A third-party harness adds useful texture. Vals AI reported on November 19–20, 2026 that Mini ties Claude Opus 5.5 (CVP) on CyberBench v1.1 at 74.58%, at about $0.93 per test versus about $4.17 for Opus on the same page. The same leaderboard lists about 33 minutes median duration and about 29 million tokens per test for Mini. A tie on accuracy with 33-minute runs is not a production speed claim.

The gaps matter as much as the leads. The official post reports 50.0% on MultiChallenge, behind Qwen3.8-27B, and 33.4% on ComplexConstraints v1.1, trailing Muse Glimmer at 35.6%. The model card adds that the model can state wrong facts with confidence, that agentic runs may take destructive actions such as deleting files without asking, and that quality can drop outside English.

**Cite your own rerun, not a headline tie.** Run the model on tasks you already understand, with the harness and duration you can afford, before you replace any API route.

## Wire it into n8n so the local agent stays safe

Serve the model locally first — Ollama on a Mac, llama.cpp server on a GPU, or vLLM once you accept nightly code — then point n8n at that local endpoint. The pattern below assumes an n8n AI Agent workflow whose chat model calls your local server instead of a cloud API. If you are new to local-first routing, the [Linger local-first pattern](/blog/linger-local-agent-polystrata-n8n-pattern/) covers the same discipline from the runtime side.

1. **Cap context and reasoning before you connect tools.** Set an explicit context (start at 65,536 tokens) and a reasoning budget. A 1M-token window with uncapped thinking turns every workflow run into an unbounded compute bill on your own hardware.
2. **Route by task, not by hope.** Send coding and multi-step reasoning to Mini; keep multi-turn chat with many constraints and non-English work on a model you have verified for it. The lab's own gaps tell you where Mini is weakest.
3. **Gate every write behind human approval.** The model card warns that agentic runs may delete files without asking. Reads can flow automatically; file writes, shell commands, and anything irreversible wait for a human to approve the exact action.
4. **Sandbox the first runs.** Start with a small, disposable task and a copy of your data, not your main repository. Local weights remove the network dependency; they do not remove the need for isolation.
5. **Log every run.** Record the model tag, context cap, reasoning effort, tokens used, and wall-clock time. When a run takes 30 minutes, your log should show whether the loop, the context, or the task caused it.

Keep a tested cloud fallback live while you evaluate. Local-first is strongest when data cannot leave the device or when you already own suitable hardware; it is weakest when you need vendor indemnity, sub-second routing at high volume, or guaranteed parity you have not measured. For model-routing discipline across local and cloud routes, see the [Gemini 4 Neon wiring pattern](/blog/gemini-4-neon-n8n-agent-wiring/).

## Honest limits

This wiring pattern is verified against the November 23–24, 2026 guides checked against the official announcement, model card, and repository listings, not live-tested on local hardware for this article. Benchmarks are lab-reported or Vals-reported; neither substitutes for your own eval. Ollama support is a pre-release, vLLM support needs a nightly build, and looped-model support in local runtimes is days old, so expect breaking changes. Speed varies by runtime and hardware, and single-request decoding costs about 5.4 billion parameters per token across 48 sequential steps — budget throughput accordingly.

## FAQ

### Can Inkling 2 Mini run on my laptop?

If it is Apple silicon with 32 GB or more of memory, yes — that is the lab's recommended tier, and Ollama v0.40.17 supports it there as a pre-release. A 24 GB Mac or GPU should use a smaller GGUF build and a capped context. Below that, expert offloading to system RAM works but speed follows RAM bandwidth.

### Is Inkling 2 Mini free to use commercially?

The weights are released under Apache 2.0, per the announcement and model card. Apache 2.0 permits commercial use, but you carry the operational liability for what your agent does — open weights put indemnity on you, not on a vendor.

### Does looping make the model know more facts?

No. The lab states that looping improves reasoning compute, while knowledge is mostly a function of total parameter count. Closed-book factual tests did not improve with more passes. Verify facts with retrieval or tools instead of trusting the loop.

### Should I replace my cloud model with Inkling 2 Mini in n8n?

Not on headline benchmarks alone. Run both on your own tasks, compare accuracy, duration, and tokens, and keep writes behind approval either way. Mini earns its place where data must stay local or where your measured cost per task beats the API route.

## Key Takeaways

1. **24 layers, 48 applications** — the middle 12 layers run three times with shared weights, so reasoning compute rises without a larger download.
2. **Budget 5.4 billion, not 3.4 billion** — effective compute per token, plus KV cache, decides whether your hardware keeps up.
3. **32 GB is the comfortable tier** — 4-bit GGUF fits smaller machines, but long agent sessions need context headroom.
4. **Benchmarks are claims until you rerun them** — lab leads and a Vals tie come with 33-minute medians and named gaps.
5. **Local does not mean unsupervised** — cap context, sandbox first runs, and gate every write behind human approval.

Next step: pull the model on one machine this week, run a single capped task you already understand, and log accuracy, tokens, and wall-clock time before connecting it to any n8n workflow that can write.

*Sources: ExplainX Inkling 2 Mini report (read November 28, 2026), vdf.ai local-deployment guide checked November 23, 2026 against the model card and runtime docs, and 4Geeks guide checked November 24, 2026 against the official announcement, model card, and Hugging Face weights page.*
