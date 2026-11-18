---
title: "Emma Is an AI Agent You Can See: Nuance Labs' Full-Duplex Video Persona, Explained for n8n Builders"
description: "The emma ai agent is trending +550%. What Nuance Labs' Nuplex video persona does, what the 89% claim proves, and how to wire it to n8n safely."
date: 2026-11-18
category: news
tags: ["AI agent", "voice agents", "n8n", "Nuance Labs", "Nuplex"]
draft: false
featured: false
image: "/og/emma-ai-agent-nuance-labs-nuplex-video-persona.webp"
---

Voice agents have a missing sense: they can hear you, but they cannot see you. That is the problem Emma is built to solve — and why the "emma ai agent" query jumped more than 550% in the past week, becoming the fifth-fastest rising related search for "AI agent" on Google Trends in the United States. Emma is the first persona on Nuplex 1.0, a full-duplex audiovisual foundation model from Seattle startup Nuance Labs, launched on November 9, 2026. By the end you will know what Emma is, what the 89% claim does and does not prove, what the Nuplex Beta API gives builders, and a five-part pattern for wiring a face-to-face agent into n8n without letting it move money or collect secrets.

## What Emma actually is

Emma is a video persona: a face on screen that talks with you in real time, rather than a voice from a speaker or text in a chat box. She runs on Nuplex 1.0, which Nuance Labs describes as a full-duplex audiovisual foundation model — a system that listens and speaks simultaneously, so it can hear you while it is talking instead of waiting for silence before it replies. The model sees, hears, reasons, and speaks in the same instant — and a persona that nods, looks away, or interjects at the right moment behaves differently from one that only produces audio.

Nuance Labs was founded by three former Apple researchers — Fangchang Ma, Edward Zhang, and Karren Yang — and Emma is the result of 18 months of research. The company has raised $60 million: a $10 million seed round in 2025, then a $50 million Series A in September 2026 led by Lightspeed, with Accel, South Park Commons, NVIDIA, and Define Ventures. The launch was announced in ["Meet Emma, the First Nuplex Persona"](https://home.nuancelabs.ai/research/meet-emma-the-first-nuplex-persona); a Hacker News thread picked it up the same evening.

Emma has a designed personality, not a neutral one. She is curious and quick-witted, has opinions, will disagree with you, and is always upfront that she is an AI. That is deliberate: Nuance argues most AI is agreeable to a fault because the preference data used to train it rewards agreement, citing the sycophancy research of Sharma et al. from 2024. Her face and voice are licensed from a real actress who collaborated with the team, and her mannerisms were designed: a long blink for emphasis, a squint, eyes that wander and come back, a little jump when she feels strongly.

The voice agents we have covered on this blog are voice-only — [Vapi wired into n8n](/blog/vapi-n8n-voice-agents-vapicon-2026/) or [ElevenLabs](https://try.elevenlabs.io/cortexflow) — or they are text. Emma adds a face, and the visual cues are part of the conversation, not decoration. Nuance names Tavus, LemonSlice, and Keyframe Labs as companies in the same space — but Emma is the one trending now.

![Fig 1 — The face-to-face console: camera and microphone drums feed the full-duplex press, the reply-timing dial reads 89%, and the approval lever gates every tool call.](/figures/emma-ai-agent-nuance-labs-nuplex-video-persona-face-press.svg)
*Fig 1 — Emma's conversation, drawn as a machine: the camera and mic drums feed the full-duplex press, the reply-timing dial reads 89% overlap with a human speaker, and the approval lever sits between the persona and any tool call. Notice the watermark stamp and the kill-switch cable — both are part of the design, not decoration.*

## The 89% number, honestly

The headline number is about reply timing: on 1,785 questions from its own recordings of real conversations, Nuplex's reply timing overlapped the original speaker's timing 89% of the time; the next closest system managed 35%. Nuance says no existing benchmark measures face-to-face naturalness properly, which is why it built its own test.

**Treat that number as a company-reported claim on the company's own dataset, not as an independent benchmark.** It tells you Nuplex was tuned to reply at human-like moments on Nuance's own recordings, and beat the compared systems by a wide margin on that test. It does not tell you how Emma will time replies on your calls, with your users, over your connection — and there is no independent benchmark to check it against, because Nuance's own point is that none exists yet.

The comparators show what "good timing" was measured against. The open models PersonaPlex and Moshi were tuned to answer fast; GPT-Live and Gemini Live take longer, likely to avoid cutting users off. Speed alone is not the goal; the goal is replying at the moment a person would. The 89% figure is a claim about hitting the human window, not raw speed — and until someone else reproduces the test, it is a claim, not a fact.

Try her yourself at [emma.nuancelabs.ai](https://emma.nuancelabs.ai) and watch the timing. The company admits she still cuts in too early and waits too long sometimes. Read 89% as a signal Nuance cared enough to build a test for it — and test it yourself before you build on it.

## What the Nuplex Beta API gives builders

Talking to Emma needs no account — you can do it today at emma.nuancelabs.ai. Building with her is a different door: the Nuplex Beta API at [platform.nuancelabs.ai](https://platform.nuancelabs.ai), behind a sign-up. The beta offers a few different personas, not just Emma. You brief a persona with your own prompt, follow the conversation as it happens, and let it hand longer tasks to your tools in the background while it keeps talking.

Two details matter for n8n builders. First, the persona keeps talking while tools work — conversation and work run in parallel, not in sequence. Second, Nuplex works with any language model, but the beta serves one itself, and your tools can call any model or service. Custom personas are available for enterprises by arrangement, only with explicit permission from anyone whose face or voice is used.

What the beta does not give you is a tool list, a pricing page, or a ready-made n8n integration — no public pricing, no n8n node. The wiring pattern in the next section is a pattern built from webhooks, not a tested integration.

The [voice models](/blog/microsoft-mai-voice-models-explained/) we have covered produce audio; Emma adds a face that is part of the interaction. On a phone call, a face adds nothing; on a screen — a kiosk, a demo, an onboarding flow — the face is the product. Pick the medium before you pick the model.

## The 5-part face-to-face-agent pattern for n8n

Here is the pattern I would use in n8n. It is a wiring pattern, not a tested integration — there is no Nuplex node, and I have not run this end to end.

**1. Let the persona talk while tools work in the background.** Wire the tool call to an n8n webhook, acknowledge immediately, and let the workflow run asynchronously. If it takes thirty seconds, the user should hear "I'm looking that up now", not dead air.

**2. Never let the persona move money or collect secrets.** Nuplex's own design backs this up: if a persona asks for a passcode, card details, money, or remote access, the call ends automatically. Approvals for money, credentials, or irreversible actions must happen off-call — a message, a dashboard, an approval link — never inside the conversation. The [approval pattern](/blog/digitalocean-cuttlefish-iphone-agent-approval/) for a phone-based agent applies here too.

**3. Send the transcript to n8n and turn it into structured actions.** Point a transcript webhook at an n8n workflow, extract decisions and commitments into fields, and log every action. The log is the audit trail: if a user later asks "why did it do that?", the transcript plus the log is your answer. Without both, you have a charming demo and no accountability.

**4. Treat interruptions as incomplete intents.** Full-duplex means the user can cut the persona off mid-sentence, and vice versa. Every interruption is a half-finished intent: log interrupted turns explicitly and confirm before acting on anything from a cut-off exchange. A workflow acting on half a sentence will eventually book the wrong thing or email the wrong person. Confirmation is cheap; undoing is not.

**5. Mirror Nuplex's own rails in your workflow.** Nuance screens every developer prompt before a call, checks the persona's words during it, and ends calls on violations. Do the same: screen the persona prompt before the call, validate tool-call arguments against an allowlist during it — the same deterministic checks used in [agent routing](/blog/gemini-decisions-api-n8n-agent-routing/) — and keep a kill-switch that ends the interaction on any request for a secret, a payment, or remote access. This is the [guardrails](/blog/n8n-2430-agent-guardrails-release/) mindset: the rails belong in your workflow, not just the vendor's platform. And [banks are already blocking agents](/blog/accenture-warning-banks-blocking-ai-agents/) that act without clear authorization.

## Honest limits

Nuance published its own list of Emma's limits. She can make confident mistakes — miscounting the e's in "seventeen" or the r's in "strawberry". She can jump in mid-thought, wait a beat too long, or miss a cue a person would catch; long pauses mid-sentence are the hardest case. She speaks English only for now. Background voices, a television, a speakerphone, or a weak microphone all make turn-taking worse; headphones help. With the camera on she can talk about what she sees, but streaming visual understanding is still early: she can miss details and misread scenes. Lip sync, gaze, and head motion occasionally look off, especially on a poor connection; her expression can slip back to neutral mid-conversation. And she cannot sing.

The commercial limits are just as real: no public pricing, so you cannot budget a build on it yet; and restricted availability — the United States except Colorado, Connecticut, Illinois, and Texas; the EU; the UK; and Canada except Quebec.

The safety rails shape what you can build. Emma never claims to be human, and developer prompts that try to make a persona claim humanity are refused. Video served through the API carries a visible watermark. There is no cloning: you cannot upload a face or a voice. No sexually explicit content, no AI girlfriends or boyfriends. Healthcare and anything involving under-18s, including education, are closed in the beta. The system is tested against published benchmarks for sycophancy, manipulation, and emotional reliance. Every developer prompt is screened before a conversation starts, and automated checks end a call if a user expresses intent toward serious violence, uses slurs or hate speech, raises sexual content, or shows weapons or gore on camera. Someone in crisis is pointed to the Suicide & Crisis Lifeline, not hung up on. Repeated violations pause new conversations. The beta is 18+ only.

One more fact, reported plainly. Emma is a Black woman; her face and voice are licensed from a real Black actress who consented, was compensated, and helped choose the name "Emma". The launch drew criticism about representation, noting that none of the 14 publicly visible team members appear to be Black. Worth knowing before you present Emma to your users: who builds a persona and who embodies it are questions they may ask.

## FAQ

### What is the Emma AI agent?

Emma is the first persona on Nuplex 1.0, a full-duplex audiovisual foundation model from Nuance Labs — a video persona you can talk to in real time at emma.nuancelabs.ai. The "emma ai agent" query rose more than 550% on Google Trends in the US in the week of her November 9, 2026 launch.

### Is the 89% reply-timing figure independently verified?

No. It is a company-reported result on Nuance's own dataset: 1,785 questions from its own recordings, where Nuplex's reply timing overlapped the original speaker's 89% of the time, against 35% for the next closest system. Nuance says no existing benchmark measures face-to-face naturalness properly.

### Can I use Emma in n8n?

There is no n8n integration or node for Nuplex, and no public pricing. The Nuplex Beta API lets you brief a persona and hand longer tasks to your tools in the background while it keeps talking. The practical path is the webhook pattern in this article — tool calls to n8n webhooks, approvals off-call, transcripts logged — not a plug-and-play connector. See also our [local ElevenLabs alternative](/blog/voicestudio-local-elevenlabs-alternative-n8n/).

### Where is Emma available?

In the United States except Colorado, Connecticut, Illinois, and Texas; the EU; the UK; and Canada except Quebec. Talking to Emma needs no account; the beta is 18+ only, with healthcare and under-18 cases closed.

## Key Takeaways

1. **Emma adds a face to the voice agent** — full-duplex means the persona listens and speaks at once, and visual cues are part of the conversation.
2. **The 89% timing figure is company-reported on its own data** — impressive on its own test, unproven anywhere else.
3. **The Nuplex Beta API is a front-end, not a finished product** — no public pricing, no tool list, no n8n integration yet.
4. **Never let a talking face move money or collect secrets** — approvals happen off-call, and any secret or payment request should kill the interaction.
5. **Interruptions are the failure mode** — log cut-off turns as incomplete intents and confirm before acting.

Next step: spend ten minutes talking to Emma at emma.nuancelabs.ai and watch the reply timing. Then decide whether your use case needs a face at all, or whether a voice-only agent does the same job for less.
