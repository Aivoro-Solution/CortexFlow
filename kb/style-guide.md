# AgentCraft House Style Guide

**Purpose:** This is the single reference for how every AgentCraft article is written — voice, structure, formatting, and the anti-patterns to avoid. It is synthesized from 11 representative posts analyzed on 2026-09-30:

- **Cloudflare blog (4 posts):** "We tested our own WAF with frontier AI models", "The road to the agentic browser: A Kitesurf update", "Using AI to chart a course for our post-quantum migration" (CryptoLabe), "Building a post-quantum certificate authority with Merkle Tree Certificates"
- **Hetzner community tutorials (3):** "Setting up Seafile", "Deploy a Private AI Chat Interface with Libre WebUI and Ollama on a GPU Server", "Installing Docker on Ubuntu/Debian"
- **DEV /architecture (4 posts):** "Stop Sending Every Decision to an LLM", "Why Your AI Agent's Memory Is Broken (And How to Fix It With SQLite)", "Making a Local AI Agent Smarter: Semantic Memory with Local Embeddings", "RAG isn't memory. It's Ctrl+F with embeddings."

**Audience:** Beginner-to-intermediate builders of AI agents, automation, and chatbots. They can follow a terminal and paste a config, but they do not know the field's jargon and cannot debug your unstated assumptions.

**Non-negotiables:** Articles are in English. No emojis in body copy. No clickbait claims the article cannot substantiate.

---

## 1. Voice and Tone

- **Practitioner, not professor, not pitchman.** Write as someone who built the thing last week and is reporting back — first person ("I ran into", "we tested") is encouraged where it carries evidence. (DEV posts do this well.)
- **Opinionated but fair.** Take a position ("RAG isn't memory"), then earn it with a concrete failure case or measurement. Never take a position you only support with adjectives. (DEV + Cloudflare)
- **Respectful of the reader's time.** Short paragraphs. Cut throat-clearing sentences ("In today's fast-paced world of AI…"). (All three sources)
- **Honest about limits.** Every technique has hard cases, costs, and things you didn't test. Say them explicitly. Readers trust limitations more than superlatives. (Cloudflare: "hard-to-fix cases", honest uncertainty; Hetzner: notes beside risky steps)
- **Playful is allowed, sloppy is not.** A wry one-liner is fine (Kitesurf post). Stylized Unicode bold, repeated filler, and ten-paragraph intros are not. (DEV anti-patterns)

**Tone in one line:** A competent colleague explaining what they built, what broke, and what they'd do differently — with the receipts.

---

## 2. The Eight House Rules

1. **One question per post.** The title is the question or the thesis. The first three sentences state (a) the problem, (b) why it matters now, (c) exactly what the reader will have or know by the end.
2. **Proof before promises.** Lead with a real build, a real failure, or real numbers — never with marketing adjectives. Every claim of "faster/cheaper/better" must carry its measurement.
3. **Define before you use.** The first time a term appears (MCP, RAG, embedding, webhook), give it a one-line plain definition inline. Never assume the reader knows.
4. **How-tos follow the skeleton:** outcome promise → prerequisites → placeholders → numbered steps → verify after each step → success state at the end.
5. **No bare code dumps.** Every command, config block, or schema is followed by *why it's there* — what each key does, what breaks if you skip it.
6. **State limits and trade-offs.** Include what you didn't test, the hard cases, and when NOT to use this approach. One honest limitation beats three superlatives.
7. **End with Key Takeaways (3–5 bullets) plus one next step.** Never end with "we hope you learned a lot."
8. **Short paragraphs, descriptive H2s, one idea per section.** Maximum one bolded takeaway line per section. Code/config blocks stay copy-paste runnable and complete.

---
## 3. Article Structures

Pick ONE skeleton per post. Do not mix.

### A. The How-To (Hetzner-derived) — for anything the reader must build

```
H1: [Outcome]: How to [do X] with [tool Y]

Introduction (3–5 short paragraphs)
- What X is, in one line. Who it's for. The concrete outcome by the end
  ("By the end, you will have…").
- Optional: a "What you'll set up" bullet list if there are several parts.

**Prerequisites** — bullet list: what they need installed, accounts, skills.
  Include versions and "as of" dates for anything that moves fast.

**Example terminology** — define every placeholder ONCE:
  - Host: `<your-host>`, IP: `<10.0.0.1>` …
  Tell the reader to replace them in all commands.

## Step 1 - [Verb + thing]
  Short paragraph: why this step exists.
  Command(s) in code blocks.
  Paragraph: what the important flags/keys do.
  "You should see…" — expected output.
  > Note/Warning placed NEXT to the risky step, not at the end.

## Step 2 - [Verb + thing]
  …same pattern. Use sub-steps (Step 2.1, 2.2) for complex phases.

## Step N - Verify everything works
  One command that proves the whole thing works (e.g. pull a model,
  hit the endpoint, send the test message).

## Conclusion
  State the success state concretely ("You now have a private,
  GPU-accelerated chat UI at http://<your-ip>:8080").
  Name the next thing to read/do — one link, not a link farm.
```

Rules from the sources:
- Steps are **numbered and imperative** ("Step 2 - Install NVIDIA Drivers"), never cute.
- After a config file, add a **"Here's what each key does"** list. The Hetzner Ollama tutorial does this for every Compose key; copy that exact habit.
- Verification is part of the step, not an appendix. `nvidia-smi` → "you should see a table showing your GPU model"; `docker run hello-world` → 'If you see "Hello from Docker!", Docker is installed correctly.'
- When two options exist, show a **decision table** first (docker.io vs docker-ce: Vendor | Source | Updates), then the steps for each.

### B. The Build Log (Cloudflare-derived) — for experiments, benchmarks, migrations

```
H1: [We/our team] [tested/built/measured X]. Here's what we found.

Intro: the question a real person asked → why it matters → experiment scope,
  numbers, limitations, and what the article covers ("Here's how the loop
  worked, what got through, and what we did about it").

## The problem / why now
  Concrete pain, with scale if you have it.

## Goals
  Numbered, measurable, 2–4 items. (CryptoLabe pattern:
  "1. Discover all cryptographic usage in our codebase…")

## How it works / architecture
  Plain-language walkthrough + diagram. Define terms before use.

## What we tested / results
  Tables with real numbers. State method briefly (environment,
  attack categories, dataset size).

## Hard cases and limitations
  What didn't work. What you're not sure about. Open questions.

## What's next / what you can do now
  Roadmap + a concrete action for the reader (try it, read this, watch for this).
```

### C. The Opinionated Explainer (DEV-derived) — for architecture takes and myth-busting

```
H1: [Strong claim]. [Plain-English consequence.]
  ("RAG isn't memory. It's Ctrl+F with embeddings.")

First 3 sentences: your thesis. No throat-clearing.

## [Concrete failure anecdote — what happened]
  Real, specific, first person: "A user said 'I prefer Python.' A week later…
  the agent blended click with clap." Name the failure, not the abstraction.

## [The problem, decomposed]
  2–4 named holes ("Three holes you can drive a truck through"), each with
  a short example.

## [The solution / what to do instead]
  Architecture, code, or config that fixes it. Runnable and complete.

## Key Takeaways
  Numbered, one line each, self-contained (readers screenshot these).
```

- Open with a **scene or story** when you have one (the 3 AM debugging story beats "Memory is important").
- **Analogy budget: one per article.** The good DEV posts use one vivid analogy, then move on. Analogies explain; they don't substitute for the technical content.
- Address the obvious objection explicitly ("But memory frameworks fix this, right?" / "Why not just push context to 1M tokens?") — with numbered rebuttals, not dismissal.

### D. The Comparison (hybrid) — for "X vs Y" decisions

```
H1: [X] vs [Y] for [use case]: what [measurement] actually shows

Intro: who needs this decision, what you'll conclude up front.

## What we measured / how
  Method in one paragraph. What's excluded.

## Head-to-head table
  Rows = criteria (cost, latency, privacy, setup effort).
  Cells = concrete values ("$0 vs $0.13/1M tokens", "5ms vs 100–300ms"),
  never "Good / Better".

## When to pick X, when to pick Y
  Direct statements: "For an agent whose job is remembering personal
  information, local embeddings aren't just cheaper — they're the correct
  design choice."

## Key Takeaways
```

---
## 4. Formatting Rules

- **H1** = the title. Exactly one per post.
- **H2s are descriptive mini-titles**, never "Step 3" alone — always "Step 3 - Install Docker" or "The post-quantum scaling problem". A reader scanning the TOC should understand the whole argument.
- **Paragraphs: 1–4 sentences.** One blank line between them. No walls of text.
- **Bold:** one takeaway line per section maximum, for the sentence that survives screenshotting. Never whole paragraphs in bold. Never stylized Unicode (𝐥𝐢𝐤𝐞 𝐭𝐡𝐢𝐬) — it's unreadable for screen readers and looks cheap.
- **Lists:** bullets for features/options; numbers only for sequences that must run in order. Keep list items to 1–2 lines; longer than that belongs in prose.
- **Tables:** for evidence and decisions (benchmarks, option comparisons, schemas). Never for layout.
- **Code blocks:** always specify the language (`bash`, `yaml`, `python`, `json`). Every block must be copy-paste runnable — include imports, paths, and placeholder values with the terminology section backing them. No `…` ellipses hiding load-bearing code.
- **Diagrams/images:** one per major concept, max. Prefer a simple ASCII/text diagram or a real screenshot over a decorative stock image. Every image gets a caption explaining what to notice.
- **Notes and warnings:** `> **Note:**` / `> **Warning:**` placed immediately beside the step they apply to. The Hetzner warning about `JWT_SECRET` ("without a fixed secret, all users are logged out whenever the container restarts") is the model: specific consequence, specific fix.
- **Links:** link to primary sources (official docs, the repo, the RFC), not aggregator copies. Link the first mention of a tool. Don't link the same thing twice in one post.
- **Dates and versions:** anything that rots gets a date — "as of February 2026", "driver version 580 is current for Ubuntu 24.04". If a version might change, tell the reader where to check.

---

## 5. Anti-Patterns (Do Not Do These)

Learned from the weakest moments of the reference posts:

1. **Throat-clearing intros.** "In today's fast-paced world of artificial intelligence…" — delete. Start at the problem.
2. **Adjective-supported claims.** "blazingly fast", "revolutionary", "seamless" — replace every one with a number or delete it.
3. **Bare code dumps.** A 60-line config with no explanation of a single key. (The inverse of the Ollama tutorial's key-by-key breakdown.)
4. **Unexplained jargon chains.** "We used RAG with cosine similarity over pgvector for the agent's episodic memory." — a beginner just drowned in sentence one.
5. **Fragment sprawl.** Ten standalone one-sentence paragraphs, each its own section. If a section is one sentence, merge it.
6. **Repetition padding.** Saying the same takeaway in the intro, the body, and the conclusion in the same words. Say it once, well.
7. **"We hope you learned a lot" endings.** A conclusion that restates the title and wishes the reader well. End with takeaways and a next step.
8. **Corporate vagueness.** "We are excited to announce synergies…" — Cloudflare at its worst; we copy Cloudflare at its best (numbers, diagrams, honest limits).

---

## 6. Before / After Examples

### Example 1 — Title + opening (DEV + Cloudflare rule)

**Before:**
> ## Connecting n8n to an MCP Server
> In this article, we will discuss how to connect an MCP server to n8n. MCP is a powerful new protocol and n8n is a great automation tool. Let's get started!

**After:**
> ## n8n Can't See Your Tools? Connect It to an MCP Server in 15 Minutes
> n8n's built-in nodes cover a few hundred apps — but your internal API isn't one of them. MCP (Model Context Protocol, Anthropic's open standard for exposing tools to AI models) turns any script into a tool your n8n AI Agent can call. In the next 15 minutes you'll wire up a real MCP server, give an agent one working tool, and test it end to end.

Why: one question, thesis up front, jargon defined inline, concrete outcome and timebox.

### Example 2 — Explaining a command, not just printing it (Hetzner rule)

**Before:**
> ```bash
> docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
> ```
> Now let's deploy the stack.

**After:**
> Run a minimal CUDA container to confirm Docker can see the GPU — this pulls a small NVIDIA base image and runs `nvidia-smi` inside it:
> ```bash
> docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
> ```
> You should see the same GPU table you saw on the host. If you get `could not select device driver`, the NVIDIA Container Toolkit wasn't configured — re-run `nvidia-ctk runtime configure --runtime=docker` and restart Docker.

Why: the *why* precedes the command, and the reader knows what success looks like plus the one likely failure.

### Example 3 — Honest limits (Cloudflare rule)

**Before:**
> This setup gives you blazing-fast, fully private AI chat with zero compromises.

**After:**
> This gives you private, GPU-accelerated chat on hardware you control. The trade-offs: a 12B model on 24 GB VRAM answers slower than GPT-4-class APIs (roughly 20–40 tokens/sec in our test), and you're responsible for updates and backups. Don't use this for anything where downtime costs money until you've added monitoring.

Why: adjectives replaced with measured numbers; limits stated with consequences.

### Example 4 — Ending (all sources)

**Before:**
> ## Conclusion
> In this tutorial we learned how to build an AI chatbot. We hope you found this useful and will try it yourself. Stay tuned for more articles!

**After:**
> ## Key Takeaways
> 1. **SQLite is enough for agent memory at small scale** — FTS5 + sqlite-vec replace a vector DB for hundreds of thousands of chunks.
> 2. **Keep the LLM off the hot path** — write fast, consolidate in the background.
> 3. **Memory needs forgetting** — decay stale facts or they'll outvote fresh ones.
>
> Next: part 2 covers conflict resolution between old and new facts, with the `supersedes` edge pattern. Try the schema above against your own chat logs this week — if retrieval misses, check whether the fact was ever *typed* (episodic vs semantic) before blaming the embedding.

Why: self-contained takeaways (screenshotable), a concrete next step, and an honest pointer to the next failure mode.

---

## 7. Pre-Publish Checklist

Run through this for every article before it ships:

- [ ] Title states the question or thesis; first 3 sentences give problem → why it matters → outcome.
- [ ] One skeleton (How-To / Build Log / Opinionated Explainer / Comparison) — not a mix.
- [ ] Every jargon term defined inline on first use.
- [ ] Every code/config block: runnable, language-tagged, followed by a "why" and (for how-tos) a verification.
- [ ] At least one real number, measurement, or concrete failure case.
- [ ] Limits/trade-offs section or paragraph exists — what you didn't test, when NOT to use this.
- [ ] Ends with Key Takeaways (3–5 bullets) + one next step.
- [ ] No throat-clearing, no adjective-only claims, no bare dumps, no Unicode-styled text.
- [ ] All versions/dates marked ("as of …"); link freshness checked.
- [ ] Placeholders (if any) defined in an Example terminology section and used consistently.

---

## 8. What We Borrowed From Where

| Source | Borrow for AgentCraft | Do NOT imitate |
|---|---|---|
| **Cloudflare blog** | Evidence-led depth: real tests, numbered goals, benchmark tables, diagrams, "hard cases" honesty, "what you can do now" | Corporate announcements, vague enthusiasm, jargon without definitions |
| **Hetzner tutorials** | The how-to skeleton: prerequisites → placeholders → numbered steps → explain-each-key → verify → success state | Over-long theory intros (the Docker/namespaces tutorial front-loads too much before Step 1) |
| **DEV /architecture** | Practitioner voice, strong theses, failure anecdotes, trade-off statements, Key Takeaways endings | Stylized Unicode, fragment sprawl, repetition padding, 5,000-word rambles |

**The house formula in one sentence:** Hetzner's step-by-step reliability, Cloudflare's evidence and honesty, DEV's voice and nerve — aimed at a beginner-to-intermediate builder who wants to ship something today.

---

*Created 2026-09-30. Revisit after the first 5 published articles: check which rules survived contact with real writing and tighten this guide.*
