---
title: "Dataiku Agent Management Explained: Counting the AI Agents Nobody Inventoried"
description: "Dataiku's Agent Management (GA October 2026) inventories AI agents across AWS, Azure, Salesforce and more, then risk-tiers them. Here's what it does and costs."
date: 2026-10-02
category: news
tags: ["dataiku", "ai-agents", "agent-governance", "enterprise", "agent-safety"]
draft: false
featured: false
image: "/og/dataiku-agent-management-explained.webp"
---

Fewer than one in five organizations keep a complete, current inventory of their AI systems — IBM's "AI in Motion" research puts the number that low. Dataiku's answer, announced September 24, 2026 at its Succeed conference in New York and generally available in October 2026, is **Agent Management**: a standalone product that scans AI agents across competing enterprise platforms into one inventory, measures their business and technical performance, and flags the ones that carry the most risk. Think of it as a CMDB (configuration management database) for the era where every team ships a chatbot.

This matters now because the agent estate is growing faster than anyone's ability to count it. Teams built agents faster than governance could track them — Dataiku's CEO put it bluntly: *"Ask a bank how many servers it runs, and you get an answer to the decimal. Ask how many AI agents it's running, and you get a shrug or a guess."* Below is what Agent Management actually does, what it costs, where it falls short, and what you can steal from the idea for your own stack today — free.

## What Agent Management actually is

Agent Management sits **above** the platforms where agents are built and operated, not inside them. It connects to the systems enterprise teams already use to run agents:

- AWS Bedrock
- Databricks Agents
- Google Vertex
- Microsoft Copilot Studio and Azure Foundry
- Salesforce Agentforce
- Snowflake Cortex
- Dataiku's own platform
- Custom environments, via **OpenTelemetry**

Once connected, it scans every platform into a single inventory. Each record captures who owns the agent, what its purpose is, which systems it connects to, when it last ran, and — the part I find most interesting — the agent's **structure**: the tools and models it actually relies on. A supervisor doesn't just learn that an agent exists; they learn how it works.

That structure mapping is the real product. Agent platforms only show you the agents built on them. If a sales team bought an assistant inside a SaaS product while an engineering team deployed custom agents in two clouds, neither platform sees the other's half. An inventory problem exists *before* anyone can test quality, compare cost, or decide what to retire.

<figure class="shot">
  <img src="/images/dataiku-agent-management-explained/inventory-dashboard.jpg" alt="Close-up of enterprise server racks with blinking indicator lights and network cables — hardware that is always inventoried, unlike most companies' AI agents" width="1200" height="800" loading="lazy" />
  <figcaption>Every server in this rack has an asset tag and an owner. Dataiku's bet: soon every AI agent will need one too — and right now, most companies can't name theirs.</figcaption>
</figure>

## It measures value and flags risk — continuously

A static registry would be a spreadsheet. Dataiku says Agent Management goes further, monitoring each agent's health, usage, cost, quality, and behavior over time, with alerts when an agent drifts away from its normal pattern.

For higher-risk agents — the ones that touch customers, sensitive data, or live transactions — it keeps a standing record of:

- **Certification status** — is this agent approved for what it's doing?
- **Named risks** — Dataiku names examples like excessive privileges, shared credentials, and the absence of a human override
- **Scheduled tests** — tests that rerun on a schedule, so the evidence trail exists *before* a manager, auditor, or regulator asks for it

That last point is the enterprise pitch in one sentence: continuous evidence, not a pre-audit scramble. The risk categories are worth noting for any builder, not just enterprises — "no human override" as a named risk is exactly the approval-gate conversation every n8n builder should already be having.

## What it costs

Dataiku has not published a dollar figure. Per the launch reporting, pricing is **per-instance annually, with monitoring metered per agent** — so the meter grows with your agent estate. The pricing model itself tells you who this is for: companies with enough agents that counting them is already a job.

If you're a solo builder or a small team running a dozen n8n workflows, this product is not priced or aimed at you. The idea behind it, however, is one you should copy for free — more on that below.

## What's missing and where it falls short

Honest limits first, because an enterprise announcement needs them:

- **It can only see what its connectors reach.** Agents running in platforms outside the connector list, shadow IT tools, or personal accounts of employees are invisible to it. The inventory is complete only where the estate is already known.
- **No published pricing** means you can't comparison-shop. "Per-instance annually plus per-agent metering" is a model, not a number.
- **It measures agents, not outcomes.** Business and technical performance are tracked, but whether the agent's work is *correct* in a domain sense still depends on the tests you write and the certifications you define. Garbage in, certified garbage out.
- **It's a new control layer, not a standard.** Dataiku is one vendor's product; cross-platform agent governance standards are still forming. Buying this is betting on Dataiku's connectors, not on an industry-wide protocol.

I haven't tested the product — it's generally available this month, and this post is based on the launch materials and reporting, not hands-on use.

## What builders should steal from this (for free)

You don't need Dataiku to fix your own agent sprawl. The pattern is simple enough to run on a spreadsheet plus discipline — and if you run n8n or any agent stack, this is a weekend project with real payoff:

1. **Keep an agent registry.** One row per agent: owner, purpose, connected systems, model(s) it uses, tools it can call, last run date. This is exactly the inventory Dataiku auto-discovers — do it manually and you already beat the four-out-of-five organizations IBM measured.

<figure class="shot">
  <img src="/images/dataiku-agent-management-explained/agent-network.jpg" alt="Rows of server hardware in a data center — the physical analogue of an agent estate that needs one inventory across all platforms" width="1124" height="750" loading="lazy" />
  <figcaption>A data center's estate, fully catalogued. Your agent registry can be a spreadsheet — but it has to exist, and it has to include every platform you run on.</figcaption>
</figure>
2. **Tag risk, not just metadata.** For each agent, note: does it touch customers, sensitive data, or money? Does a human approve its consequential actions? Agents with privileges but no override go at the top of your review list.
3. **Record scheduled checks.** You don't need a product for this — a quarterly reminder to re-run a test prompt and check the credentials still in use is the same evidence trail, at your scale.
4. **Use OpenTelemetry for custom agents.** Dataiku's connector for custom environments is OpenTelemetry, which means your own agents can emit spans today. If you build custom agents, instrumenting them with OpenTelemetry gives you portability: the same telemetry a vendor product would read.

## FAQ

### What is Dataiku Agent Management?

A standalone product (announced September 24, 2026; generally available October 2026) that discovers AI agents across enterprise platforms, builds one inventory with ownership, structure, and run history, measures performance, and risk-tiers agents that touch customers, sensitive data, or live transactions.

### Which platforms does it connect to?

AWS Bedrock, Databricks Agents, Google Vertex, Microsoft Copilot Studio and Azure Foundry, Salesforce Agentforce, Snowflake Cortex, Dataiku itself, plus custom environments via OpenTelemetry.

### How much does it cost?

Pricing is per-instance annually with monitoring metered per agent. Dataiku has not published a specific dollar figure as of October 2, 2026.

### Do I need this for a small n8n setup?

No. The product targets enterprises with large agent estates. But the underlying idea — one inventory with owner, purpose, tools, and risk for every agent — is worth copying with a spreadsheet.

## Key Takeaways

1. **Agent sprawl is now a measured problem** — fewer than one in five organizations can inventory their AI agents, and the gap is becoming an audit risk.
2. **Dataiku's Agent Management (GA October 2026) attacks exactly that gap** — one cross-platform inventory with structure mapping, continuous performance monitoring, and risk-tiering with certification records.
3. **"No human override" is a named risk in the product's risk model** — a signal that approval gates are becoming a compliance expectation, not just good practice.
4. **You can copy the core idea for free** — a manual agent registry with owner, purpose, tools, and risk tags beats 80% of organizations today.
5. **OpenTelemetry is the portability layer** — Dataiku uses it for custom environments; instrumenting your own agents with it keeps your options open regardless of vendor.

Next: instrument one of your own agents or n8n workflows with OpenTelemetry-style logging this week — owner, purpose, tools, last run — and see how far a single registry row gets you. If you want the enforcement layer on top, pair it with human approval gates on every consequential action, the same pattern our [OpenShell + Sentry](/blog/nvidia-openshell-sentry-agent-safety/) and [DigitalOcean Agent Droplets](/blog/digitalocean-agent-droplets-explained/) coverage keeps coming back to.

---

*Dataiku announced Agent Management on September 24, 2026 at Dataiku Succeed in New York; general availability is set for October 2026. Reporting via [Help Net Security](https://www.helpnetsecurity.com/2026/09/25/dataiku-agent-management/). Images: Pexels.*
