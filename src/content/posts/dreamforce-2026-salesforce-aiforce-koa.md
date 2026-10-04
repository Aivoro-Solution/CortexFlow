---
title: "Dreamforce 2026: Salesforce Turned the CRM Into an Agentic Layer — What AIforce, Koa, and Long-Horizon Agents Mean for Builders"
description: "Dreamforce 2026: Salesforce's AIforce, Koa reasoning model, long-horizon agents and Agent Optimizer — what shipped and how n8n builders should respond."
date: 2026-10-04
category: news
tags: ["salesforce", "agentforce", "ai-agents", "automation", "news"]
draft: false
featured: false
image: "/og/dreamforce-2026-salesforce-aiforce-koa.webp"
---

**Salesforce no longer wants your teams to go into the CRM. It wants the CRM's data, logic, and agents to go wherever your teams already are.** At Dreamforce 2026 (kicked off September 15), Salesforce announced AIforce, its first homegrown CRM reasoning model Koa, long-horizon agents that pursue goals over weeks, and job-ready agents with names like Hunter, Piper, and Carter. This is the biggest enterprise-agent push of the year, and if you build automations for any company that runs Salesforce, the platform you're integrating with just became an agent platform itself. Here's what shipped, what it's really signaling, and how to respond if your stack is n8n.

For definitions: **AIforce** is Salesforce's architectural layer that exposes Salesforce data, workflows, business logic, permissions, and governance to external AI interfaces. **Koa** is Salesforce's first purpose-built reasoning model for CRM work. A **long-horizon agent** is an agent built to pursue a goal over days, weeks, or months — not just answer one prompt — with memory across sessions and the ability to course-correct when steps fail.

![The "Welcome to Dreamforce" entrance at Dreamforce 2022 in San Francisco — the 2026 edition was where Salesforce unveiled AIforce, Koa, and long-horizon Agentforce agents](/images/dreamforce-2026-salesforce-aiforce-koa/dreamforce-entrance.jpg)

## What actually shipped

The official recap is on [Salesforce's blog](https://www.salesforce.com/blog/dreamforce-2026-announcements/). Five announcements matter:

**1. AIforce — the CRM escapes its own UI.** AIforce puts the full Salesforce platform — data, workflows, permissions, governance — into whatever AI interface your team already works in. It launched with three named products: **Claudeforce**, which feeds Salesforce data and controls into Claude through a prebuilt connector, shipping with 37 ready-made sales skills already trialled by Deloitte, GitLab, and Legora (open beta via AppExchange); **Slackforce**, which brings Salesforce context into Slack with an assistant called Slackbot and a shared coding space called Slack Code; and **Agentforce Coworker**, an AI teammate inside the Lightning interface itself. Salesforce says 100,000 people switched Coworker on within its first 35 days. The claim is Zero Data Retention — governed, permission-respecting access, not a bulk export.

**2. Koa — a reasoning model that owns its trust boundary.** Koa is Salesforce's first CRM reasoning model for Agentforce, built on NVIDIA Nemotron for agent reasoning, tool use, and decision-making. Its training corpus comes entirely from *synthetic* scenarios — no real customer data ever trains the model. Salesforce owns the weights and runs Koa inside its own infrastructure, so no customer data crosses the trust boundary during training or inference. Pilot now; enterprise GA expected Winter 2026. This is the "don't send every decision to a generic frontier model" move — specialized reasoning on your CRM graph, inside your walls.

**3. Long-horizon agents — goals, not prompts.** A new kind of Agentforce agent built to pursue a goal over days, weeks, or months: assign it something like "re-engage my at-risk deals," and it builds a multi-step plan, executes it, and checks in for your approval based on guardrails you define. It runs on a new long-horizon runtime with memory to stay on track across sessions, durable execution to course-correct when a step fails, and dynamic steering so you can adjust the plan conversationally. Pilot now; GA November 2026. This is the direct answer to the "agents do demos, not jobs" critique — the runtime itself now handles persistence and recovery.

**4. Agent Optimizer — an agent that builds and fixes your other agents.** In Agentforce Builder, you describe what you need in plain language and Optimizer creates subagents and stubs out actions, testing as it builds. In Agentforce Observability, it reads thousands of production sessions, finds recurring failure patterns, and ranks them by impact — then you work with it to build, test, and stage changes in one conversation. GA October 2026. Agent-on-agent maintenance is now a shipping product, not a research demo.

**5. Job-ready named agents and the cloud partnerships.** Salesforce shipped prebuilt agents with job titles: Hunter analyzes buying signals, Piper engages inbound leads, Campaign Agent builds and optimizes campaigns, Palmata tracks how your brand appears in AI search (answer-engine optimization), plus Casey, Paige, Fin, Carter, and Marshall. On the infrastructure side, Salesforce expanded with AWS (activate Agentforce inside AWS environments, buy Salesforce through the AWS Marketplace) and Google Cloud (unified stack, no data silos), and Siemens confirmed it is connecting Agentforce to its Teamcenter engineering software so field technicians and sales staff can get engineer-level answers without calling an engineer.

## Why this is actually a big deal

Ignore the keynote theater for a moment. The structural change is this: **Salesforce is repositioning itself from the system of record you visit into the permission-and-data layer that agents run on top of.** A CRM with 25 years of customer-interaction history is, in agent terms, a pre-trained world model of how a business works. Koa being trained on synthetic scenarios derived from 27 years of deployments is the clearest sign that Salesforce understands this: the moat isn't the chatbot, it's the governed context.

This also settles a design debate we've covered before. In our piece on [Cloudflare's Clef decision models](https://cortexflow.tech/blog/cloudflare-clef-decision-models-explained/), the argument was: stop sending every agent decision to an LLM. Salesforce just did exactly that at enterprise scale — a purpose-built reasoning model for CRM decisions, running inside the trust boundary, so the frontier model never sees the data. Same pattern, bigger checkbook.

The governance angle matters too. Long-horizon agents only work if they're allowed to touch production systems for weeks — which means the agent's permission model *is* the company's access-control model. After [OpenAI had to warn 100+ orgs about rogue agents](https://cortexflow.tech/blog/openai-rogue-agents-100-orgs/), the enterprise answer is shaping up as: agents that inherit your Salesforce permissions, run under Zero Data Retention, and check in based on guardrails you define. Whether that answer is good enough is the open question — but it's now the frame everyone has to argue against.

## What this means for n8n builders

Three practical implications:

**1. Your Salesforce integrations are about to get competition from inside.** If your clients run Salesforce, the "build the agent in n8n, connect Salesforce as a data source" pattern now competes with "let Agentforce do it with native governance." n8n's edge stays where it always was: multi-vendor orchestration (Salesforce *and* your data warehouse *and* Slack *and* the weird internal API), self-hosting control, and per-execution cost. If the workflow lives entirely inside Salesforce, Agentforce's native context will be hard to beat. If it spans systems, n8n still wins — wire Agentforce's outputs into your flows via webhooks and APIs rather than rebuilding them.

**2. The long-horizon runtime is a blueprint you can copy cheaply.** n8n doesn't have a "long-horizon agent runtime," but you can build the pattern: a scheduled workflow that resumes state, evaluates progress against a stored goal, course-corrects, and escalates to a human on defined conditions. We built the [AI Meeting Notes to Tasks workflow](https://cortexflow.tech/templates/ai-meeting-notes-tasks/) on a simpler version of this loop (receive → process → verify → escalate). Salesforce just validated the architecture; you can ship it without Salesforce's licensing.

**3. Specialized reasoning models will keep shrinking your LLM bill.** Koa is a CRM reasoning model; AWS shipped [Strands Decider 2B](https://cortexflow.tech/blog/strands-decider-2b-explained/) as a free local decision model; Cloudflare has Clef. The pattern is consistent: route the routine decisions to a small, specialized model and reserve the frontier model for the genuinely ambiguous cases. In n8n, that's a LangChain or OpenAI-node branch: fast model for classification and tool-calling, big model for the edge cases.

## The honest limits

![Salesforce Tower in San Francisco — the headquarters of a company repositioning itself as the permission-and-data layer for enterprise agents](/images/dreamforce-2026-salesforce-aiforce-koa/salesforce-tower.jpg)

What we don't know yet: Koa's actual benchmark numbers versus the frontier models on CRM tasks (Salesforce hasn't published head-to-heads as of October 4, 2026), what Claudeforce and Slackforce will cost at scale (governance layers historically get priced per-seat or per-action), and whether long-horizon agents in pilot actually complete multi-week goals without humans quietly finishing the work. The 100,000 Coworker activations in 35 days is an adoption number, not a success metric. And everything here is vendor self-reporting — treat the timelines (Agent Optimizer GA October, long-horizon GA November, Koa GA Winter) as targets, not facts, until they're live.

Also: **this architecture deepens lock-in.** An agent platform whose agents inherit Salesforce permissions, reason on Salesforce-trained models, and run inside Salesforce's infrastructure is extremely hard to migrate off. If you're a builder recommending Agentforce to a client, price in the exit cost on day one.

## FAQ

### What is AIforce?

AIforce is the layer Salesforce announced at Dreamforce 2026 that extends Salesforce data, workflows, business logic, permissions, and governance into external AI interfaces — launched with Claudeforce (Claude connector), Slackforce (Slack), and Agentforce Coworker (Lightning). It turns the CRM from a place you visit into an agentic layer that follows your team.

### What is Salesforce's Koa model?

Koa is Salesforce's first purpose-built reasoning model for CRM work, built on NVIDIA Nemotron. It's trained entirely on synthetic scenarios (no real customer data), Salesforce owns the weights and runs it inside its own infrastructure, and it's designed for agent reasoning, tool use, and decision-making inside Agentforce. Pilot as of October 2026; GA expected Winter 2026.

### When do long-horizon Agentforce agents become generally available?

According to Salesforce's Dreamforce 2026 announcement: the long-horizon runtime is in pilot now, with GA targeted for November 2026. Agent Optimizer is GA October 2026. These are vendor-stated targets.

### Should I build on Agentforce or n8n?

If the workflow lives entirely inside one company's Salesforce org and needs native governance, Agentforce's context advantage is real. If it spans multiple vendors, needs self-hosting, or must control per-execution cost, n8n wins — use it to orchestrate Agentforce outputs alongside everything else.

## Key Takeaways

1. **Dreamforce 2026 repositioned Salesforce as the permission-and-data layer for enterprise agents**, not just a CRM you visit — AIforce brings it into Claude, Slack, and Lightning.
2. **Koa is the enterprise version of the specialized-model pattern**: CRM reasoning inside your trust boundary, trained on synthetic data, so the frontier model never sees customer data.
3. **Long-horizon agents (GA November) and Agent Optimizer (GA October) are the interesting technical moves** — durable multi-week execution and agent-maintains-agent tooling are now shipping products.
4. **For n8n builders, the response is orchestration**: compete on multi-system workflows and cost, integrate with Agentforce where the client already runs it, and copy the long-horizon pattern with scheduled resume-and-recover loops.

Next: if you're wiring Salesforce into agent workflows today, read our [n8n Salesforce OAuth setup patterns](https://cortexflow.tech/blog/n8n-agents-explained/) — and keep an eye on the November GA for long-horizon agents before recommending Agentforce to a client.

*Images: Wikimedia Commons (Dreamforce venue photos, CC BY-SA 2.0)*
