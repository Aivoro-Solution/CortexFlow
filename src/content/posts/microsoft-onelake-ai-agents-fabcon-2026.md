---
title: "Microsoft Rebuilt OneLake for AI Agents at FabCon: Read API, Governed Sharing, and the Security Gap"
description: "At FabCon 2026, Microsoft gave AI agents a governed path into OneLake: a Table Read API, IQ sharing, and synced security policies."
date: 2026-10-03
category: news
tags: ["microsoft-fabric", "onelake", "ai-agents", "data-governance", "enterprise"]
draft: false
featured: false
image: "/og/microsoft-onelake-ai-agents-fabcon-2026.webp"
---

Every enterprise AI agent eventually needs the same thing: your company's data. And that is exactly where most agents die. Give an agent a database connection and it becomes an over-privileged liability; keep it away from the data and it can only answer from public knowledge. This week at FabCon Barcelona 2026, Microsoft tried to split the difference: it rebuilt OneLake — the storage backbone of Microsoft Fabric — so agents get governed, read-only, policy-enforced access instead of either a key to the kingdom or nothing at all. By the end of this article, you'll know what Microsoft actually shipped, which two partner announcements matter more than the keynote, and the five-item checklist to use before you connect any agent — n8n or otherwise — to enterprise data.

**Microsoft OneLake** is a single data lake shared across all of Microsoft Fabric's analytics workloads: instead of every tool keeping its own copy of your data, everything in Fabric reads from one pool. **Microsoft Fabric** is Microsoft's all-in-one data platform (warehouses, lakehouses, Power BI, real-time analytics) running on Azure. **FabCon** is Microsoft's Fabric community conference — the 2026 European edition ran in Barcelona from September 28 to October 1.

![Rows of server racks inside a data center — the physical infrastructure behind cloud data platforms like OneLake](/images/microsoft-onelake-ai-agents-fabcon-2026/datacenter-corridor.jpg)

## What Microsoft actually announced

Microsoft's OneLake expansion, announced around FabCon and SQLCon Barcelona 2026, is a long list of ecosystem moves. The items that matter for anyone building agents:

- **A OneLake Table Read API built for AI agents.** Microsoft named this explicitly as part of the expansion. A read API for agents is the key primitive: it lets an agent fetch table data through a governed endpoint instead of being handed raw storage credentials or a shared service account.
- **IQ sharing (preview):** securely sharing governed data *and business context* across teams and partners — TomTom and EY are among the first partners onboarding to it.
- **Bidirectional Salesforce Data 360 integration**, Google BigQuery mirroring, and Dynamics 365 Business Central mirroring — your agent's data sources now flow into the lake without export files.
- **lakeFS versioned data access** and production-ready Azure Databricks native storage in OneLake — the lake starts behaving like source control for data, which is exactly what you want when an agent makes a wrong write and you need to roll back.
- **Public preview of ClickHouse workloads in Fabric**, on-demand OneLake compute billing, Fabric zero-provisioned (F0), and deeper Microsoft Foundry integration — plus new partner workloads from Esri, Telmai, Celonis, and others.

Dipti Borkar, Microsoft's VP for IQ and OneLake, framed the intent plainly: *"Maintaining a consistent security posture across OneLake, Databricks, Snowflake, and every access path is essential to giving people and AI agents the freedom to work with data without compromising governance."*

That sentence is the whole story. **The industry's framing has flipped: the blocker between agent pilots and production is no longer model quality — it is enforceable data access control.**

## The announcement that matters more: Trust3 AI

Timed with FabCon (October 2, 2026), Trust3 AI announced a capability that automatically synchronizes **row and column-level security policies across Databricks, Snowflake, and Microsoft OneLake Security**. Translation: the rules that say "this finance agent may read salaries but not this sales agent" — defined once in your existing platform — now carry over into OneLake instead of being recreated and maintained separately in each environment.

Don Bosco Durai, Trust3 AI's CTO, put it in agent terms: *"Enterprise AI agents should inherit the same trust boundaries as the people and systems they act on behalf of."*

This is the piece builders have been missing. Today's typical n8n setup connects an agent to a database through a shared credential with a SQL node — and the agent's effective permissions are whatever that credential can do, which is usually far more than the agent should touch. Policy sync attacks the root of that: the agent acts *on behalf of* a user, and the platform enforces the user's boundaries automatically.

> **Note:** Trust3 AI's announcement is a vendor claim from a press release — no independent verification or pricing has been published as of October 3, 2026. Treat the "automatic sync" as directional until you see the connector docs.

## The other partner announcement worth your time: Atlan

Also at FabCon Europe (September 29, 2026), Atlan announced general availability of its Microsoft Fabric connector with OneLake interoperability. Atlan is an AI context platform — think of it as a governed catalog of *meaning*: metric definitions, data ownership, lineage, and quality policies. The connector catalogs Fabric workspaces, lakehouses, warehouses, semantic models, reports, dashboards, dataflows, and pipelines down to the table and column level, extracts end-to-end lineage, and surfaces that context inside Fabric and Power BI through a browser extension.

**Lineage** means the full map of where a table came from and where its data flows next. For agents this matters because the most dangerous agent failure isn't a wrong answer — it's a *confident* wrong answer built on a stale or unowned table. A governed context layer that follows the data wherever the agent runs is the antidote, and it is why Atlan's pitch is "governed context, not just governed storage."

(Also launched at the event: Daivio, an AI analyst workload that runs as an item inside the Fabric workspace — profiling, cleaning, and plain-language analysis over OneLake data, signed in with the analyst's existing Entra ID. Same theme, analyst-sized.)

## The five-item checklist before you connect an agent to enterprise data

Whether your agent runs in n8n, a Fabric workload, or a custom stack, this is the pattern the FabCon announcements are pushing. Apply it before your next deployment:

1. **Give the agent an identity, not a shared credential.** Use a service principal or managed identity (in Fabric-land, Microsoft Entra ID) scoped to exactly what the agent needs. A shared SQL credential that five workflows reuse is how over-privileged agents are born.
2. **Enforce row and column-level policies, not table-level grants.** If your lakehouse platform supports masking or row filtering, define policies for the *users* the agent serves — and let the agent inherit them, the Trust3 AI way.
3. **Read through a governed API, not raw storage keys.** Prefer read APIs and SQL endpoints over handing the agent a storage account key. This is the OneLake Table Read API pattern: narrower surface, logged access.
4. **Require a context layer for any metric the agent quotes.** Connect your catalog (Atlan-style or otherwise) so the agent pulls metric definitions from the governed source instead of inventing them. Lineage goes in the agent's system prompt, not just the wiki.
5. **Log every agent query like an audit trail.** The n8n–NVIDIA NemoClaw lab demo at GTC Berlin uses a human-approved decision gate for the same reason: when the agent touches real data, someone must be able to reconstruct what it asked and why.

![Close view of server racks — enterprise data lives behind layers of access control](/images/microsoft-onelake-ai-agents-fabcon-2026/datacenter-racks.jpg)

## Honest limits

This is still week-one territory. The OneLake Table Read API and IQ sharing are announced, not battle-tested — expect SDK rough edges, sparse documentation, and at least one breaking change before GA. Microsoft disclosed no pricing for agent read traffic, and on-demand OneLake compute billing plus Fabric F0 change the cost math in ways nobody has modeled publicly yet. The partner announcements are press releases, not benchmarks. And for n8n builders specifically: there is no OneLake node — you reach Fabric data through SQL endpoints, REST, or HTTP Request nodes today, and the governed-agent story is something you assemble yourself with the checklist above, not something you download.

## Key Takeaways

1. **Agent data access is a governance problem, not a plumbing problem** — FabCon 2026 makes that the industry consensus.
2. **The OneLake Table Read API + IQ sharing** give agents a governed, read-first path into enterprise data instead of shared credentials.
3. **Trust3 AI's policy sync** attacks the real root cause: agents should inherit the trust boundaries of the people they act for.
4. **Atlan's GA Fabric connector** adds the missing layer — governed context (definitions, lineage, ownership) that travels with the data.
5. **Before connecting any agent to enterprise data:** identity per agent, row/column policies, read API over raw keys, a context layer for metrics, and an audit trail.

Next step: if you run n8n agents against company data, audit your credentials this week — list every database node, check what each credential can touch, and shrink them to least privilege before your next deployment. That's the cheapest version of everything Microsoft just announced.

## FAQ

### What is Microsoft OneLake?

OneLake is the single data lake that sits underneath all of Microsoft Fabric's analytics workloads — lakehouses, warehouses, Power BI, and real-time analytics all read from the same pool instead of keeping separate copies. Think of it as OneDrive, but for data tables instead of documents.

### What did Microsoft announce for AI agents at FabCon 2026?

A OneLake Table Read API built for AI agents, governed data-and-context sharing via IQ sharing (preview), cross-platform security posture (Databricks, Snowflake, OneLake), versioned data access through lakeFS, and partner integrations including Trust3 AI (policy sync) and Atlan (governed context, GA connector).

### Does this change anything for n8n builders?

Directly: not yet — there is no OneLake node, and most features are in preview. Indirectly: the pattern is the point. If your n8n agent touches enterprise data, the five-item checklist above (agent identity, row/column policies, read API, context layer, audit trail) is the safest architecture you can run today, with or without Fabric.

### Is agent data governance really the main blocker for production agents?

It's the one enterprises keep naming: security teams can't approve agents that inherit blanket credentials, so pilots stall. Microsoft, Trust3 AI, and Atlan all framed their FabCon announcements around exactly this — governance as the precondition for moving from pilot to production.

*Images: Pexels (Brett Sayles)*
