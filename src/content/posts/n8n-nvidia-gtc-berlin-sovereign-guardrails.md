---
title: "n8n at NVIDIA GTC Berlin: AI Guardrails"
description: "n8n's Claire Knight speaks at NVIDIA GTC Berlin on Oct 20 about sovereign guardrails for AI agents, plus a hands-on NemoClaw sandbox lab on Oct 22."
date: 2026-10-01
category: news
tags: ["n8n", "NVIDIA", "GTC Berlin", "AI agents", "governance"]
image: "/og/n8n-nvidia-gtc-berlin-sovereign-guardrails.webp"
draft: false
featured: false
---

n8n is taking a named slot at NVIDIA GTC Berlin 2026 to talk about the least glamorous — and most enterprise-blocking — part of AI agents: keeping them under control. **Claire Knight**, n8n's Director of Engineering, speaks on **Tuesday, October 20, 11:00 a.m.–1:00 p.m. CEST** in a session titled **"Bring Your Own Agent: Sovereign Guardrails for the Age of Autonomous Claws"**, listed in NVIDIA's official GTC Berlin catalog under the *Agentic AI and Claws* track. Below are the confirmed facts, what "sovereign guardrails" appears to mean here, and why the session matters for anyone running agents against real business systems.

One note on sourcing: the session details come from NVIDIA's official GTC Berlin session catalog, as reported this week. NVIDIA has not published the talk's slides or technical specifics, and nothing in the catalog describes a new n8n product or feature launch — so treat this as a confirmed presentation of n8n's governance approach, not a product announcement.

## What is confirmed

- **Who:** Claire Knight, Director of Engineering at n8n.
- **What:** a talk on autonomous AI agents with sandboxed agents, guardrails, and production-grade governance for workflow use cases at its center.
- **When/where:** Tuesday, October 20, 2026, 11:00 a.m.–1:00 p.m. CEST, at NVIDIA GTC Berlin (October 20–22).
- **Track:** *Agentic AI and Claws* — NVIDIA's "claws" branding for its agentic-AI program.
- **Also on the program:** a hands-on training lab on **Thursday, October 22, 3:00–4:45 p.m. CEST**, titled **"Your Agent Doesn't Get Root: Governing AI Actions With n8n and NVIDIA NemoClaw."**

The lab is arguably the more concrete of the two. Per the session description, attendees work with an agent running in a locked-down **NemoClaw** and **OpenShell** sandbox with **no direct network or API access** — the agent's only way to act is through n8n workflows, and consequential actions require human approval, with the system recording *who approved what and where the request originated*. That is the guardrail pattern made executable: least privilege by construction, not by policy document.

## What "sovereign guardrails" signals

**Guardrails**, in this context, are the limits that shape what an agent can access, what actions it can take, and when it must stop or ask a human. **Sandboxing** confines the agent's operating environment so a task cannot silently reach unrelated systems. The "sovereign" framing points at control and jurisdiction: European enterprises — the GTC Berlin audience — increasingly need agent infrastructure they can inspect, host, and govern themselves rather than renting opaque autonomy from a black box.

That framing did not come out of nowhere. Two days before this news cycle, on September 29, NVIDIA launched its **Open Agent Safety Platform**: **OpenShell**, an open-source (Apache 2.0) secure agent runtime that sandboxes agents and enforces policy on what they can reach, plus **Sentry**, a hardware-based watchdog running on BlueField-4 DPUs that monitors agent behavior from a trust domain the agent cannot touch — quarantining it within milliseconds if it steps outside its boundary. The GTC lab pairing n8n workflows with NemoClaw and OpenShell sandboxing sits directly on top of that platform story.

For n8n specifically, the positioning is coherent with where the product has been heading: the workflow engine as the *governed action layer* for agents — every tool call an explicit node, every consequential step gated by approval, every action logged. It is the opposite of giving an agent a shell and hoping for the best.

## Why it matters for builders

Most agent failures in production are not model failures — they are permission failures: the agent read the wrong mailbox, wrote to the wrong database, or acted on stale instructions with no human in the loop. The questions worth borrowing from this session's framing before you connect any agent to operational tools:

- What can the agent read, and what is explicitly out of scope?
- Which actions complete automatically, and which require approval — and who approves?
- Can the workflow run in a sandbox before it touches live systems?
- What happens when the agent fails or produces something unexpected — is there a log, and does anyone get paged?

Those are process-design questions, not model-selection questions. Teams that can answer all four are ready for agents; teams that cannot need tighter workflow design first, regardless of which model they use.

## What to watch

The session itself is October 20 — the substance to look for afterward is whether n8n publishes the talk's specifics: how permission boundaries get defined in practice, what the approval UX looks like, and whether any of the sandboxing patterns land as documented n8n features or stay as conference architecture. n8n's enterprise motion has been accelerating through 2026, and a GTC keynote-adjacent slot suggests the company wants "governed agents" as its enterprise calling card.

No n8n booth number has been confirmed in NVIDIA's public materials, so plan around the session and lab times if you are attending.

## Key Takeaways

1. **n8n's Claire Knight speaks at NVIDIA GTC Berlin on October 20** — "Bring Your Own Agent: Sovereign Guardrails for the Age of Autonomous Claws," in the Agentic AI and Claws track.
2. **A hands-on lab on October 22** demonstrates the pattern concretely: a sandboxed agent with no direct network access, acting only through n8n workflows with human approval and full audit trails.
3. **No product launch is confirmed** — this is a governance-approach presentation, landing days after NVIDIA's own Open Agent Safety Platform (OpenShell + Sentry) launch.
4. **The takeaway for builders is process, not product** — scoped permissions, approval gates, sandboxing, and audit logging are what make agents production-ready.

Next: if you run n8n agents today, audit one workflow against the four questions above this week — most teams find at least one action that runs with broader permissions than the task requires.
