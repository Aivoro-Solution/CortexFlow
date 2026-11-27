---
title: "Microsoft's Work IQ MCP Went GA for Business Data — Wire It Into n8n Without Breaking Permissions"
description: "Work IQ MCP is a Breakout trend. Business Applications in Work IQ went GA Nov 18 — wire its MCP server into n8n read-only, per user, behind an approval gate."
date: 2026-11-27
category: news
tags: ["mcp", "n8n", "microsoft", "work iq", "ai agents"]
draft: false
featured: false
image: "/og/microsoft-work-iq-mcp-n8n-business-context.webp"
---

"workiq mcp" is a Breakout rising query for "MCP server" in Google Trends (US, past 7 days) this week. The event behind the search is real: on November 18, 2026, Microsoft announced the general availability of Business Applications in Work IQ, and its announcement names n8n as one of the clients its MCP server connects.

MCP (Model Context Protocol) is the open standard that lets an AI model call external tools. Work IQ is Microsoft's intelligence layer over Microsoft 365 and business-application data. The November 18 release grounds agents in Dynamics 365 and Power Platform records, not just mail and documents.

By the end of this article you will know exactly what went GA, what the Work IQ MCP server will and will not let an agent do, and how to wire it into n8n read-only, per user, with writes behind a human approval gate.

## What actually went GA on November 18

Be precise about the scope, because Microsoft has shipped Work IQ in layers. Work IQ itself reached general availability on June 16, 2026. What went GA on November 18, 2026 is **Business Applications in Work IQ**: business context from Dynamics 365 and Power Platform, usable in production in Copilot Chat, Agent Builder, and Copilot Studio, per [Microsoft's announcement](https://www.microsoft.com/en-us/dynamics-365/blog/it-professional/2026/11/18/business-applications-work-iq-generally-available/).

The GA release includes four things:

- **Business context** in Copilot Chat, Agent Builder, and Copilot Studio.
- **Business skills and automatically generated semantic models.** A semantic model is a machine-readable map of what your data means: Work IQ generates one in Dataverse from the views, forms, and relationships already in your apps. Business skills capture how a team works — for example, the steps of a renewal-readiness check — so every agent follows the same definitions.
- **Business context for pro-dev scenarios:** the Work IQ MCP server, the Work IQ CLI, and the Dataverse Ask API. The Ask API answers a plain-language question from a semantic model and returns matching records, a short summary, and source links, limited to what the caller can read.
- **Admin controls** in the Microsoft 365 and Power Platform admin centers.

Two things in the same announcement are still preview, not GA: Copilot Cowork and Dynamics 365 ERP data (finance and operations) in Work IQ. Sales and Customer Service data are the GA business sources today.

## The permission model is the whole story

Most MCP servers you wire into n8n authenticate as one shared service identity. Work IQ does the opposite, and that difference decides how you deploy it.

- **Every request runs as the signed-in user.** The hosted MCP server exposes mail, calendar, Teams, SharePoint, OneDrive, and Copilot data through one remote endpoint, `https://workiq.svc.cloud.microsoft/mcp`, with per-user OAuth 2.0 delegated auth. The agent sees only what that user can already see.
- **Turning it on grants nothing new.** Microsoft states it plainly: Work IQ does not give any user or agent access they did not already have. Actions are proposed, approvals are followed, and records update only within each user's permissions.
- **Mutations are blocked by default.** Create, update, delete, and action requests stay off until a tenant administrator enables them through Work IQ tenant policy. A valid token can still be refused by that policy layer.
- **Admins keep two switches.** In the Microsoft 365 admin center, admins set who can use AI and which policies apply, hide business data from Copilot, and allow or block business apps as a source on the MCP server. In the Power Platform admin center, one setting per environment decides which environments take part.

The endpoint also enforces hard caps, documented in the [Work IQ MCP setup reference](https://www.truefoundry.com/docs/ai-gateway/mcp/work-iq-mcp-server):

| Limit | Value |
|---|---|
| Allowed path prefixes | `/me/`, `/users/`, `/sites/` by default |
| Collection size | Default `$top` 25, maximum 100 |
| Chat messages | Capped at 10 per request |
| Blob size | 4 MB by default, configurable per path |
| Retries | None — Graph status codes and `Retry-After` pass through to your client |

**The one-line summary: this is a permission-scoped, read-first MCP server, not an all-powerful Microsoft 365 superuser.**

![An isometric context press: business records ride a rail under semantic-model plates that stamp meaning onto each record, a cam drum steps them through a business skill, and an orange-lit permission gate lets only read-only answers reach the output tray while write blocks stop at the gate.](/figures/microsoft-work-iq-mcp-n8n-business-context-context-press.svg)

*Figure 1: The context press. The plates are the semantic model stamping meaning onto each record, the cam drum is a business skill stepping it through a process, and the orange gate is the permission model: reads pass with source links, writes stop until a tenant admin enables them. Notice the caps on the readout — 25 by default, 100 at most, 4 MB per blob.*

## What it costs

Everyday AI is included in the Microsoft 365 Copilot license, so licensed users can ask Copilot Chat about business data at no extra cost. Advanced AI is billed by usage through Copilot Credits, and that includes calls through the Work IQ MCP server and API. In practice, MCP calls from n8n meter against a usage-based billing plan set up in Copilot Studio, backed by an Azure subscription and resource group, with each user assigned to the plan. Without that plan in place, metered tools stay blocked.

## Wire it into n8n

**Prerequisites:** a Microsoft 365 tenant with Work IQ available, a usage-based billing plan in Copilot Studio with your users assigned, a Microsoft 365 Copilot license for users of the `ask` tool, and a tenant administrator who can grant admin consent for the Work IQ application in Microsoft Entra. If MCP wiring itself is new to you, read [how to connect an MCP server to n8n](/blog/how-to-connect-mcp-server-n8n/) first.

### Step 1 - Get consent and billing in place first

Work IQ needs administrative consent in your Entra tenant before any client works, and the billing plan before metered calls run. Do both before touching n8n. Skipping this order is how you end up debugging OAuth for an hour when the real blocker is an unassigned billing plan.

You should see: the Work IQ application consented in Entra, and your test user assigned to the Copilot Studio usage-based billing plan.

### Step 2 - Add the MCP Client Tool in n8n

Create a workflow with an AI Agent node. From the agent's Tool connector, add an MCP Client Tool and configure it:

- **Endpoint:** `https://workiq.svc.cloud.microsoft/mcp`
- **Server Transport:** HTTP Streamable
- **Authentication:** OAuth2, delegated per user. The required scope is `api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask`, plus `offline_access` so tokens refresh instead of expiring mid-workflow.
- **Tools to Include:** Selected, read-only tools only. Leave the generic write tools (`create_entity`, `update_entity`, `delete_entity`, `do_action`) out of the selection entirely.

Here is what each choice does. HTTP Streamable is the modern MCP transport this endpoint serves. Delegated OAuth means the workflow acts as the user who authorized it, which is the entire permission model — there is no shared bot identity to fall back on. Selecting read-only tools gives you a second lock on top of Microsoft's default mutation block.

> **Warning:** OAuth redirect URIs must match exactly. Copy n8n's callback URL from the credentials screen into your Entra app registration character for character; one trailing slash breaks the flow. Our [MCP troubleshooting guide](/blog/mcp-n8n-troubleshooting/) covers the redirect and scope failures in order.

### Step 3 - Verify with a read the user can already do

Ask the agent a question whose answer the authorizing user can already see, for example: "Which opportunities are closing next month?" You should see matching records with source links back to the source record, the same pattern the Dataverse Ask API returns.

Then run the negative test: ask for a record the user has no permission to read. You should see a refusal or an empty result, not the record. If the agent can see more than the user can, stop and fix the authorization before building anything else.

### Step 4 - Put writes behind an approval gate

Only after Step 3 passes should writes enter the picture, and only if your tenant admin has enabled mutations in Work IQ policy. Keep the n8n-side gate anyway: the agent drafts the proposed record update, a Wait node pauses for a human decision, and only an approved draft reaches a write tool. This mirrors how Work IQ itself describes governed actions — agents propose changes and follow required approvals.

## The pattern worth stealing

Whether or not you run Dynamics 365, Work IQ's design is a clean template for business-data agents in n8n:

1. **Read first, write never by default.** Start every agent read-only at two layers: the server's tenant policy and your tool selection. Add writes one tool at a time.
2. **One identity per user, never a shared superuser.** Delegated auth means the agent inherits the user's permissions and audit trail. A shared service account quietly deletes both.
3. **Meaning before access.** A semantic model generated from your existing views and relationships beats raw table access: the agent reasons over defined business terms, not column names.
4. **Process as a skill, not a prompt.** Capture the steps of a business process once, as a reusable skill, instead of re-prompting every agent to improvise it.
5. **Cap and log every call.** Collections cap at 100, blobs at 4 MB, and credits meter by usage. Log the user, the tool, and the credit spend per execution so a runaway loop shows up in your log before it shows up on your Azure bill.

Pair this with the guardrails in [n8n's agent guardrails release](/blog/n8n-2430-agent-guardrails-release/) and the agent's blast radius stays the size of one user's permissions, which is exactly the point.

## Honest limits

- **This wiring is pattern-verified from Microsoft's and the gateway reference documentation, not live-tested against a Work IQ tenant.** The endpoint, scope, caps, and prerequisites above are documented; your tenant's policy settings decide the rest.
- **Delegated per-user auth breaks the shared-bot pattern.** A workflow that runs unattended at 3 a.m. still acts as some user. Decide whose identity that is, and what happens when that person leaves, before you schedule it.
- **GA scope is narrower than the headline.** Business Applications in Work IQ is GA for Sales and Customer Service data; ERP finance and operations data and Copilot Cowork are public preview. Plan production workflows on the GA surface only.
- **Work IQ is proprietary and tenant-gated.** Admin consent, licensing, and a Copilot Studio billing plan are prerequisites, not optional extras. Small teams without a Microsoft 365 estate get nothing from this server.
- **No automatic retries.** Work IQ passes Graph errors and `Retry-After` headers to your client. Your n8n workflow owns retry logic, and it should respect the header instead of hammering the endpoint.

## FAQ

### Is Work IQ MCP free to call from n8n?

No. Everyday Copilot Chat use is included in the Microsoft 365 Copilot license, but calls through the Work IQ MCP server bill by usage through Copilot Credits against a Copilot Studio usage-based billing plan. Budget credits per workflow execution and log them.

### Can the agent update Dynamics 365 records through n8n?

Only if a tenant administrator enables mutations in Work IQ tenant policy; they are blocked by default. Even then, keep write tools out of the MCP Client Tool selection until a human approval gate sits in front of them.

### Do I need the local CLI instead of the hosted endpoint?

For n8n, use the hosted endpoint over HTTP Streamable. The local route (`npx -y @microsoft/workiq mcp`, per the [Work IQ CLI docs](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/cli)) starts a stdio server for desktop coding assistants on Windows, Linux, and macOS. It is the right tool for GitHub Copilot in VS Code, not for a shared n8n instance.

### What does the agent see if a user lacks permission for a record?

Nothing beyond what that user can already read. Work IQ retrieves on demand under the user's permissions, stores no Microsoft 365 data of its own, and tenant policy can refuse a call even when the token is valid.

## Key Takeaways

1. **Business Applications in Work IQ went GA on November 18, 2026** — Dynamics 365 and Power Platform context for agents, with the MCP server, CLI, and Dataverse Ask API as the pro-dev routes.
2. **The MCP server is permission-scoped by design:** per-user delegated OAuth, no new access granted, mutations blocked by default, and hard caps (100 records, 4 MB blobs).
3. **Wire n8n read-only first:** HTTP Streamable to `https://workiq.svc.cloud.microsoft/mcp`, OAuth2 with the `WorkIQAgent.Ask` scope, read tools only, writes behind a Wait-node approval gate.
4. **Billing is usage-based:** MCP calls meter against Copilot Credits, so log spend per execution from day one.
5. **The reusable lesson:** meaning (semantic model) plus process (business skills) plus per-user permissions beats raw database access for business agents.

Next step: run the Step 3 negative test in a sandbox tenant this week. If the agent respects a permission boundary it was never told about, you have a foundation worth building on; if it does not, you found the bug before production did.
