---
title: "Metricool's MCP Now Wires Straight Into n8n — Add Tags, Flows and an Approval Gate"
description: "Metricool's November update adds tags, paid Flows and an n8n-ready MCP endpoint. Wire it safely with drafts, Slack approvals and execution caps."
date: 2026-11-26
category: news
tags: ["metricool", "n8n", "mcp", "social media", "automation"]
draft: false
featured: false
image: "/og/metricool-mcp-n8n-tags-flows-approval-gate.webp"
---

"metricool" is a Breakout rising query for "n8n" in Google Trends (US, past 7 days) this week. The reason is a stack of November releases, not a rumor: Metricool published its November product update on November 24, 2026, its n8n-ready MCP connection guide on November 17, and new Flows pricing on November 9.

Metricool is a social media scheduling and analytics platform organized by brand: you plan posts in a Planner, publish to connected networks, and read the results in Analytics. MCP (Model Context Protocol) is the open standard that lets an AI model call external tools. Metricool's MCP server lets an AI client read and act on your Metricool account, and n8n is one of its documented clients.

By the end of this article you will know what shipped, how to wire Metricool's MCP into n8n the documented way, and a five-part pattern that adds tags, Slack approvals, and a Flows execution cap so the agent never publishes on its own.

## What Metricool shipped in November

Three dated changes explain the search spike.

| Date (2026) | What shipped | The gate to know |
|---|---|---|
| November 9 | Flows add-on pricing takes effect | $12 per 2,500 executions/month, no free quota |
| November 17 | MCP connection guide, including n8n steps | n8n uses a header token, not OAuth |
| November 24 | November product update: Tags, Slack, team members | AI auto-tag and team members need paid add-ons/plans |

**Tags.** You can now label posts with tags you create, each with a name and an optional color, from Brand settings, the Planner, the Post library, or Analytics. Tags carry into Analytics after a post publishes, so you can filter and analyze by campaign, client, or content type. With the Advanced Analytics add-on, you can also build Campaign Dashboards from tags and use Auto-tag with AI to label posts that match a description you write. Full detail is in [Metricool's November 2026 product update](https://metricool.com/product-updates-november-2026/).

**Slack approvals.** Metricool can now connect to Slack from Organization Settings, with a separate channel per brand for social media approvals, notes, and publishing updates. That is the human checkpoint this article builds on.

**Flows as a paid add-on.** Flows is Metricool's automation that replies for you on Instagram, TikTok, and X. It now runs on execution packs: 2,500 executions a month per pack, shared across all brands and networks. The pricing rules are in [Metricool's Flows add-on guide](https://help.metricool.com/your-guide-to-the-flows-add-on-fy0m9/).

![An isometric tag press: drafted post cards ride a belt under a press that stamps a tag chip, an approval lever gates the output, and a drum counts Flows executions.](/figures/metricool-mcp-n8n-tags-flows-approval-gate-tag-press.svg)

*Figure 1: The Metricool tag press. Draft cards arrive from n8n, the press stamps each card's tag chip, and the lit APPROVE lever decides what reaches the channel tiles. Notice the drum: it counts Flows executions, because every automated reply now draws from a paid monthly quota.*

## Wire Metricool's MCP into n8n

Metricool's own guide is explicit about the one mistake to avoid: match your client to the right connection method. Most clients use URL-based OAuth. n8n does not. The steps below follow [Metricool's MCP connection guide](https://help.metricool.com/how-to-connect-metricools-mcp-eqp9h/) (published November 17, 2026). If MCP itself is new to you, read [how to connect an MCP server to n8n](/blog/how-to-connect-mcp-server-n8n/) first.

**Prerequisites:** a Metricool account on any plan, including Free (your plan limits still apply to MCP usage), an n8n instance where you can create workflows, and your Metricool API key from Account Settings > API.

### Step 1 - Add the MCP Client Tool

Create a new workflow, add an AI Agent node, then add the MCP Client Tool from the agent's tools. Set the endpoint to `https://ai.metricool.com/mcp`. That is Metricool's production MCP URL; use it exactly.

### Step 2 - Authenticate with the header token

Set Authentication to Header Auth and create a new credential. Set the header name to `X-Mc-Auth` and the value to your Metricool API key. Save the credential.

> **Warning:** Metricool states that MCP access is full access, similar to signing in directly: brands, metrics, posts, inbox messages, reviews, and ad campaigns are all in scope. Treat the API key like a password. Store it only in the n8n credential, never in a prompt, a Code node, or a workflow export you share.

### Step 3 - Verify read-only before any write

Run the workflow with a read-only request first: ask the agent to list your brands or show scheduled posts. You should see output that matches your Metricool dashboard. If the connection fails, check the method before anything else: n8n needs the header token, and Metricool calls the wrong method a common reason the server never connects. Our [MCP troubleshooting guide for n8n](/blog/mcp-n8n-troubleshooting/) covers the n8n side.

The same endpoint also connects through OAuth in other clients, including ChatGPT, [Make](https://www.make.com/en/register?pc=cortexflow), and Zapier. The n8n header-token path is the one to use inside a workflow.

## The safe pattern: draft, tag, approve, publish, count

Connecting is the easy part. The pattern below keeps a human between the agent and the publish button.

### Part 1 - Draft first in n8n

Let the AI Agent node produce a draft post as structured output: text, target network, proposed tag, and reason. Do not give the first output a write tool. Validate the structure in a Code node against an allowlist of networks and tags. If a value is not on the list, stop and log the rejection. This is the same allowlist idea as in [the n8n agent guardrails guide](/blog/n8n-2430-agent-guardrails-release/).

### Part 2 - Tag every post

Apply one of your Metricool tags to every draft: campaign, client, or content type. Because tags carry into Analytics, a consistent tag is what makes next month's report readable. If you use Auto-tag with AI, treat its label as a suggestion and check it against your allowlist in n8n before approval. An AI-applied tag you never verified is just a faster way to misfile a campaign.

### Part 3 - Approve in Slack

Send the exact draft, media included, to your brand's Slack channel and wait for a human decision with a Wait node. Metricool's new Slack connection already routes approvals, notes, and publishing updates per brand; your n8n workflow should respect the same checkpoint. Only an approval that matches the run continues the workflow. Everything else times out and logs "no approval."

### Part 4 - Publish through MCP only after approval

Metricool's MCP can see, create, and publish posts in any connected network. That power is the point, and it is why Parts 1 to 3 exist. Put the publish tool behind the approval step, and log the post ID, tag, approver, and timestamp for every publish.

### Part 5 - Count Flows executions

Flows replies draw from your execution packs. One execution counts when a Flow fires and completes its first action, no matter how many steps the Flow has. The quota is per account, shared by every brand, resets on your subscription renewal day, and unused executions do not carry over. Metricool warns at 80% and 100% of quota. By default, Flows stop at the limit; if you choose to keep them running, each extra execution costs $0.01. Review the counter weekly in n8n so one noisy brand cannot silently starve the others.

If you prefer an open-source scheduler you host yourself, compare this with [our Postiz wiring guide](/blog/postiz-n8n-social-scheduler-wiring/). Metricool's edge is the analytics and approval layer around the schedule, not the schedule alone.

## What it costs, honestly

| Item | Price (as of November 2026) | Note |
|---|---|---|
| Metricool MCP | Included on any plan, including Free | Plan limits still apply after you connect |
| Flows pack | $12/month per 2,500 executions | Same price on every paid plan; no free quota, no annual discount |
| Flows overage | $0.01 per extra execution | Only if you set Flows to keep running; under 100 extra executions are not charged |
| AI auto-tag + tag dashboards | Advanced Analytics add-on | Tags themselves work without it |
| Team members (org-wide roles) | Advanced plans | Collaborators keep per-brand access |

Three packs give you 7,500 executions a month for $36. Automating on X needs both the X add-on and the Flows add-on. The Metricool API is a separate path from MCP: Metricool's ChatGPT connector guide states that API access requires an Advanced or Custom plan, while MCP works on every plan.

## Limits: what I did not test

This wiring is pattern-verified from Metricool's official guides, read directly on November 26, 2026. I did not run it against a live Metricool account, so treat Step 3's read-only check as mandatory, not optional.

Three limits deserve emphasis. First, MCP grants broad access, so a compromised workflow credential is a compromised Metricool account; revoke access from the client where you connected if anything looks wrong. Second, the Flows quota has no per-brand reserve: every brand draws from one shared pool. Third, Flows is not available on the Free plan or in the mobile app, and only the account owner can manage packs and the stop-or-continue setting.

Do not use this pattern for unattended crisis replies or regulated claims. If a wrong post costs more than a slow post, keep the approval gate and shorten the draft list instead.

## FAQ

### Does Metricool's MCP work on the Free plan?

Yes. Metricool's guide states that MCP works with any Metricool plan, including Free. Your plan limits still apply to what the MCP can do after you connect.

### Does n8n connect to Metricool MCP with OAuth?

No. n8n uses header token authentication: the MCP Client Tool points at `https://ai.metricool.com/mcp` with a Header Auth credential named `X-Mc-Auth` holding your Metricool API key.

### What counts as one Flows execution?

A Flow firing and completing its first action. A three-step Flow is still one execution. If the triggering comment no longer exists when the Flow acts, it does not count.

### What happens when Flows hits the monthly limit?

By default, Flows stop. You can instead let them keep running at $0.01 per extra execution, with a hard cap of 100,000 executions a month. Under 100 extra executions in a month are not charged.

### Can the agent publish without approval?

Technically, the MCP can publish. That is exactly why the pattern puts drafting, tagging, and a Slack approval before the publish tool. The gate is yours to build; Metricool does not build it for you.

## Key Takeaways

1. **The trend is dated, not vague:** November 9 Flows pricing, November 17 MCP guide, November 24 product update.
2. **n8n connects by header token:** MCP Client Tool to `https://ai.metricool.com/mcp` with `X-Mc-Auth`, verified read-only first.
3. **Tags are the reporting layer:** tag every draft, verify AI-applied tags against an allowlist, and read results by tag in Analytics.
4. **Approval stays human:** Slack per brand plus an n8n Wait node means 0 posts without approval.
5. **Flows is metered:** $12 per 2,500 executions, shared per account, stops at the limit unless you pay $0.01 per extra run.

Next step: connect the MCP read-only today, list your brands from n8n, then run one tagged draft through the Slack approval gate before you enable any publish tool.
