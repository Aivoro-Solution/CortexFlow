---
title: "China Just Gave Every AI Agent an ID Card — What the Wuzhen Rules Mean for Builders"
description: "China's Wuzhen Summit gave AI agents verifiable ID cards — while its enterprise agent market hit 21.2B yuan. What builders must change now."
date: 2026-11-08
category: news
tags: ["ai agents", "agent identity", "China", "governance", "MCP"]
draft: false
featured: false
image: "/og/china-ai-agent-id-cards-wuzhen-2026.webp"
---

On November 5, at the 2026 World Internet Conference Wuzhen Summit, China published a document that sounds boring and changes everything for agent builders: a Self-Discipline Convention on AI Agent Development that proposes giving every AI agent a layered, verifiable identity — an ID card it must show before it acts.

The timing is not a coincidence. The same summit released the China Internet Development Report 2026, and the numbers behind it explain why identity moved from a nice-to-have to a national agenda item: China's enterprise AI agent market reached 21.2 billion yuan (about $3.18 billion) in 2025, and average daily token calls hit 140 trillion in March 2026 — more than 1,000 times the volume of early 2024. When agents place orders, sign contracts, and call other agents on a user's behalf at that scale, "who did this?" stops being a philosophical question and becomes an infrastructure problem.

This is the third time in a month that a major power has answered that question with identity and liability rules. [Wells Fargo's new agreement](/blog/wells-fargo-ai-agent-liability-nov-24/) makes customers liable for their agents' instructions from November 24. [Google's Workspace will reject AI agents without its new agentic OAuth flag](/blog/google-workspace-agentic-oauth-november-deadline/) from November 11. Now China has added the state-led version: verifiable agent identities, permission controls, and rule embedding as shared infrastructure. The pattern is unmistakable — **the agent era's next dividing line is not model quality, it's whether your agent can prove who it is.**

## What actually happened at Wuzhen

The 2026 World Internet Conference Wuzhen Summit ran November 2–5 in Zhejiang Province, with roughly 1,800 delegates from 138 countries and regions. Three things landed there that matter for builders:

**1. The market numbers.** The China Internet Development Report 2026, released by the Chinese Academy of Cyberspace Studies, put China's enterprise AI agent market at 21.2 billion yuan in 2025. The embodied intelligence market — robots and physical AI — reached about 915 billion yuan, up 20.4% year on year. By June 2026, 924 generative AI services had completed official filings, alongside 573 registered generative AI applications. Daily token calls averaged 140 trillion in March 2026, up more than 1,000-fold in two years. A separate report from the China Center for Information Industry Development, released October 31, added the crossover point: for the first time, the volume of inference data in Chinese AI has surpassed the volume of training data — daily token invocations exceeded 175 trillion by June 2026. The industry has flipped from building intelligence to billing for it.

**2. The agent identity convention.** Published on November 5 by the National Blockchain Technology Innovation Center together with the China Academy of Information and Communications Technology and other units, the Self-Discipline Convention on AI Agent Development proposes strengthening the agent trust system with layered and verifiable agent identity markers, plus mechanisms for identity verification and management, permission granting and control, and rule expression and embedding, alongside shared interoperable infrastructure. In plain language: every agent gets a checkable ID card that says who it is, who it works for, and what it is allowed to do.

**3. The open-source wave that makes identity unavoidable.** On the same day, Moonshot AI open-sourced Kimi K3.1 Pro — a 2.8-trillion-parameter mixture-of-experts model with about 104 billion parameters activated per inference and roughly one million tokens of context — which topped the open-weights rankings on the Agent Arena leaderboard. Baidu open-sourced ERNIE 5.5 Flash (280 billion total parameters, 14 billion activated per token). The summit also released the first Global Open AI Action Initiative, with 18 action items across open development, safety and trustworthiness, dialogue and governance, and mutual benefit and inclusion.

Note what the convention is not: it sets no mandatory standard. It is a self-discipline convention, not a law. But naming identity markers explicitly usually signals that industry standards and filing requirements are already in the pipeline — and the 924 services already filed show the filing machinery exists.

## Why an agent needs an ID card

<figure>
  <img src="/figures/china-ai-agent-id-cards-wuzhen-2026-id-press.svg" alt="Isometric agent ID-card press machine: an agent's ID card rides a feed rail into a stamping press whose orange head stamps it official; three dials behind the press read WHO the agent is, how much SCOPE it was granted, and which OWNER is accountable; the stamped card lands in the output tray and the verification lamp lights" loading="lazy" />
  <figcaption><b>Fig 1 — The agent ID-card press.</b> An agent's card rides the feed rail into the press, which stamps it official — that stamp is the Wuzhen convention's verifiable identity marker. The three dials behind the press are the three questions every system must answer before it acts on an agent's request: WHO is this agent, how much SCOPE was it granted, and which OWNER is accountable when something breaks. The stamped card lands in the output tray and the lamp lights: only then is the agent allowed to place orders, sign contracts, and call other agents. The numbers behind the machine are real — 924 generative AI services filed by June 2026, 140 trillion daily token calls by March 2026, a 21.2-billion-yuan enterprise agent market in 2025.</figcaption>
</figure>

The convention's logic is simple, and it is the same logic driving the Wells Fargo and Google moves. Once an agent can spend money, sign things, and call other agents on your behalf, any system it touches must answer three questions:

1. **Who initiated this action?** Which agent, acting for which user or organization?
2. **How much authority was it granted?** Read-only, or can it move money and change state?
3. **Who is accountable when something breaks?** The user, the developer, or the platform?

The past two years of agents calling each other through hand-built integrations happened precisely because no cross-platform trust layer existed. Every integration invented its own answer — usually an API key with far too much permission, shared in a config file. The convention proposes fixing that at the infrastructure layer: identity markers that any platform can check, permission grants that travel with the agent, and rules embedded in the call itself rather than bolted on afterwards.

DeepSeek underlined the same point from the research side. On October 31, its harness team published "Exploring Super-Agent Design: Toward More Autonomous Agent Systems," a five-piece stack — two-layer architecture, event-driven execution, asynchronous multi-channel interaction, compute-storage separation, and an external watchdog — aimed at the ceiling on parallel tasks, which the paper frames as human attention. Agents that run many tasks in parallel need an external watchdog precisely because no human can watch them all.

## What this means for your agent stack

You do not need to comply with a Chinese convention to feel its effects. Identity registries, scoped permissions, and audit trails are becoming the default expectation everywhere an agent touches money or other people's systems. Here is the practical checklist, in priority order:

**Give every agent an identity, not just an API key.** An API key says "someone with this secret may act." An identity says "this specific agent, owned by this specific principal, may do these specific things." If your n8n workflows call external services through a single shared credential, that credential is an identity problem waiting to happen — split credentials per workflow and per agent, and name the owner in the credential itself.

**Scope permissions to the task, not the platform.** The convention's "permission granting and control" is the same principle as least privilege. An agent that reads a spreadsheet does not need write access to the billing system. Audit every credential your agents hold and ask: if this agent went rogue or got prompt-injected, what is the blast radius?

**Log who did what, in a form a third party can check.** The Wells Fargo rule puts the burden of proving revocation on the customer. The Wuzhen convention wants identity markers a verifier can check. Both point the same way: keep an append-only record of agent actions — which agent, which instruction, which tool call, which result. If you cannot reconstruct an agent's actions after the fact, you cannot dispute them either.

**Design for registries, not just allowlists.** The direction of travel is that agents will need to be registered somewhere before they can act on serious systems — Google's agentic OAuth flag is one version, China's identity markers another, [ServiceNow's AI Passport](/blog/servicenow-ai-passport-runtime-credentials-agents/) a third. Build your agents so that registering them (a name, an owner, a scope) is a configuration change, not a rewrite.

**Watch the license fine print on open models.** Baidu's ERNIE 5.5 Flash ships under a custom license that excludes use in the EU, the UK, and South Korea, and requires separate written authorization for commercial use by products with more than $50 million in revenue over the preceding twelve months. Open source is shifting from handing over weights to handing over weights with conditions. Check the license before you wire a new open model into a production agent.

## The honest limits

A few caveats, because this story has them. First, the convention is self-discipline, not law — its teeth depend on standards and filing rules that have not been published yet, so treat the timeline as uncertain. Second, the numbers come from Chinese state-affiliated research bodies and summit reporting; the 140-trillion token figure (March 2026) and the 175-trillion figure (June 2026, CCID) come from different reports with different measurement scopes, so treat them as directional, not precise. Third, the open-model leaderboard claims (Kimi K3.1 Pro first among open-weights models) come from the Agent Arena leaderboard, a third-party benchmark with its own methodology. And fourth, none of this changes what your agents can do today — it changes what they will be asked to prove tomorrow.

## Key Takeaways

1. **China's Wuzhen Summit published agent identity rules** — a convention proposing layered, verifiable ID markers for every AI agent, with permission control and rule embedding as shared infrastructure.
2. **The scale behind it is real** — a 21.2-billion-yuan enterprise agent market in 2025, 140 trillion daily token calls by March 2026, and 924 filed generative AI services.
3. **This is the third identity move in a month** — after Wells Fargo's agent-liability terms (effective Nov 24) and Google's agentic OAuth flag (enforced Nov 11). Agent identity is becoming a global compliance pattern, not a regional quirk.
4. **Give every agent an identity, scoped permissions, and an audit trail** — split credentials per agent, log actions in a checkable form, and design so registration is a config change.
5. **Check open-model licenses before shipping** — ERNIE 5.5 Flash excludes the EU, UK, and South Korea and gates large commercial users behind written authorization.

Next: read [the Wells Fargo piece](/blog/wells-fargo-ai-agent-liability-nov-24/) on this blog to see the liability side of the same pattern — what happens when an agent acts and nobody can prove who told it to. Then audit one of your own production agents against the four-point checklist above; the credential split alone is usually the biggest win.

## FAQ

### Is China's agent identity convention a law?

No. It is a Self-Discipline Convention published by the National Blockchain Technology Innovation Center and the China Academy of Information and Communications Technology, among others. It proposes identity markers and permission mechanisms but sets no mandatory standard. Its significance is directional: naming identity explicitly usually precedes industry standards and filing requirements.

### What is the China Internet Development Report 2026?

An annual report from the Chinese Academy of Cyberspace Studies, released at the World Internet Conference Wuzhen Summit. The 2026 edition reports China's enterprise AI agent market at 21.2 billion yuan in 2025, 924 filed generative AI services by June 2026, and average daily token calls of 140 trillion in March 2026.

### Does this affect builders outside China?

Not directly — but the pattern does. Google, Wells Fargo, and ServiceNow are all moving toward agent registration, identity, and liability rules in the same month. If your agents touch banks, Workspace, or enterprise systems, expect to prove who your agent is and what it may do, wherever you operate.

### What is an agent identity marker?

A verifiable credential attached to an agent — analogous to an ID card — stating which agent it is, who owns it, and what permissions it holds, in a form other systems can check before acting on its requests. The Wuzhen convention proposes layered markers, so different verifiers can check different levels of detail.

### Which open models were released at Wuzhen?

Moonshot AI open-sourced Kimi K3.1 Pro (2.8 trillion parameters, ~104 billion activated per inference, ~1M context) on November 5, and Baidu open-sourced ERNIE 5.5 Flash (280 billion parameters, 14 billion activated). ERNIE 5.5 Flash uses a custom license with geographic and commercial-use restrictions.

---

*Sources: China Internet Development Report 2026 via Bastille Post (Nov 4, 2026); AI News Daily Wuzhen Summit coverage (Nov 6, 2026); China Center for Information Industry Development Ten Trends report via Today for AI (Nov 1, 2026). Trend signal: "chinese ai agent industry status" — Breakout rising query for "AI agent", Google Trends Explore, US, past 7 days (Nov 1–8, 2026).*
