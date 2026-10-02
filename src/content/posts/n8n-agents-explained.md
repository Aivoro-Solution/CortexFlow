---
# ============================================================
#  POST TEMPLATE — copy this file to create a new post.
#
#  1. Copy:  cp src/content/posts/_template.md src/content/posts/my-new-post.md
#  2. Edit the frontmatter below + write your content.
#  3. Set draft: false when ready to publish.
# ============================================================

# The <title> and H1 of the post. Include the target keyword near the front.
title: "n8n Agents Explained: The Standalone AI Assistant That Sits Beside Your Workflows"

# Meta description for Google (~150-160 chars). Include the keyword + a reason to click.
description: "n8n rolled out standalone Agents to 100% of users on 23 Sep 2026. Here's what they are, how they differ from the AI Agent node, and when to use each."

# Publish date (YYYY-MM-DD). Used for sorting + sitemap.
date: 2026-10-02

# Optional: set when you significantly update the post.
# updated: 2026-10-15

# Must be one of: ai-agents | automation | chatbots | news
category: news

# Free-form tags. Keep 3-6 per post.
tags: ["n8n", "ai-agents", "automation"]

# Keep true while writing. Drafts are NEVER published, sitemapped, or in RSS.
draft: false

# Set true to feature on the homepage hero section (use sparingly, 1-3 posts).
featured: false

# Optional: shown in the post byline. Defaults to the site name.
# author: "Your Name"

# Optional: social/OG image path in /public, e.g. "/og/my-post.png" (1200x630).
image: "/og/n8n-agents-explained.webp"
---

# n8n Agents Explained: The Standalone AI Assistant That Sits Beside Your Workflows

Until recently, "agent" in n8n meant one thing: the AI Agent node, a box you wired into a workflow between a chat trigger and a set of tools. On 23 September 2026, n8n rolled out **Agents** — standalone AI assistants that live *beside* your workflows, described in plain language and published to Slack, Telegram, Linear, or Discord. The old AI Agent node hasn't changed; you now have two different tools with the same name.

By the end of this article you'll know exactly what an n8n Agent is, how its parts (instructions, tools, skills, memory, channels, sessions) fit together, when to reach for it instead of a workflow, and what the Preview status means for production use.

**Free template:** [Telegram Personal AI Assistant](/templates/telegram-ai-assistant/) — download the n8n workflow JSON, import it, and chat with your own AI assistant on Telegram today.

## The two kinds of "agent" in n8n, and why the distinction matters

Confusion is the biggest real-world cost of this feature. Both things are called agents, and both use a model plus tools, but they live in different places and answer different needs.

**The AI Agent node** is a step inside a workflow. You place it on the canvas, attach sub-nodes for a chat model, tools, and memory, and the workflow decides when the agent runs. Everything the agent can do is bounded by the workflow's structure: triggers, branches, and error handling stay exactly where you drew them.

**An Agent** is a first-class component of the n8n instance, alongside workflows. You don't draw it — you describe it. Name it, pick a model, write instructions ("you are the support triage bot; you may read tickets but never refund without approval"), attach tools, and publish it. People then talk to it in Slack or Telegram, it runs on a schedule, or a workflow calls it via the **Message an Agent** node.

The mental model that worked for me: a workflow is a procedure, an Agent is a colleague. You write procedures for things with a known correct sequence (a new form submission gets logged to the CRM). You hand work to a colleague when the right next step depends on what they find (an inbox review where half the threads need a reply, a quarter need a ticket, and a quarter need nothing at all).

One important clarification from the changelog: **a workflow and an Agent can call each other.** An Agent can use any of your workflows as a tool — it decides *when* the workflow runs, and the workflow runs with its own credentials, so the Agent never needs direct write access to your CRM. In the other direction, the Message an Agent node calls an Agent from inside a workflow and passes its answer downstream. You don't have to pick a side.

## What goes into an Agent

Each Agent is assembled from these parts, all in the Agent Builder (or via MCP, more on that below):

- **A model.** Any model you have credentials for, or n8n's Gateway credits.
- **Instructions.** Its role, tone, what it should and shouldn't do, and which tools to prefer. The official docs are blunt about a habit worth forming early: *if the agent misbehaves, fix the instructions before adding more tools.* Most flaky agent behavior I have seen traces back to vague instructions, not missing tools.
- **Tools.** Built-in n8n integrations, your own workflows, custom tools defined from a JSON schema, or external tools via [MCP](https://cortexflow.tech/blog/how-to-connect-mcp-server-n8n/) servers. MCP (Model Context Protocol, Anthropic's open standard for exposing tools to AI models) means an Agent can reach any tool an MCP server exposes without a dedicated n8n node existing for it.
- **Skills.** Reusable bundles of instructions and reference files the agent loads when it needs them, shareable across agents. Reach for these when one agent handles several distinct jobs — one skill per job keeps the main instructions short.
- **Sub-agents.** One agent can call another, which lets you split a big job (research agent, writer agent, reviewer agent) the way you would split it across people.
- **Knowledge.** Upload CSV, PDF, Markdown, or TXT files for the agent to ground its answers in. Available on n8n Cloud; on self-hosted it needs a Daytona sandbox. Vector stores are supported too.
- **Memory.** The agent holds the session conversation by default — no setup. To remember across conversations, enable episodic memory in settings, which needs an OpenAI credential.
- **Sessions.** Every conversation is stored, reviewable, and can be picked up again. The Sessions tab shows the messages exchanged, the tools the agent called, and the input and output of each call.

That last point is the one I would tattoo on every agent builder's forearm. An Agent's sessions are an audit log: you can see every step it took and every tool call it made. When something goes wrong — and with a Preview feature, it will — that log is how you find out whether the instructions were ambiguous or the tool returned garbage.

## How publishing and approvals work

The lifecycle is deliberately software-like: **draft, validate, publish**. You chat with the draft in the Agent Builder's chat panel to check its behavior, and only the *published* version is what channels and schedules run. Editing a draft breaks nothing for current users until you publish again.

Two mechanics matter for safety:

1. **One turn with an agent counts as one execution.** Calls to workflow tools and sub-agents don't count separately. Agents draw on the same execution quota as your workflows — so a chatty agent in a busy Slack channel will consume executions the way a busy workflow does. Size your plan accordingly.

2. **Sensitive tools require approval.** You can mark tools so the agent pauses before running them and asks a human to approve or reject. In chat, you click Approve or Reject, and the agent continues from your decision. n8n's own guidance is to require approval on tools that write to your systems — and during Preview, I would treat that as a rule, not a suggestion.

You can also manage agents from an MCP client such as Claude Desktop or Claude Code using n8n's [instance-level MCP server](https://cortexflow.tech/blog/how-to-connect-mcp-server-n8n/). If you connected an MCP client before agents existed, reconnect it in **Settings > Instance-level MCP** to get the agent management tools.

## What it costs and what you need

On n8n Cloud, Agents are available to everyone on the latest stable version, on all plans — but they are in **Preview**, and availability on Enterprise adds "additional governance features on the way," per the docs.

Self-hosted users need n8n **2.32.3 or later** and must enable the `agents` module:

```bash
N8N_ENABLED_MODULES=instance-ai,agents
```

This is the one env block you need to understand. `N8N_ENABLED_MODULES` selects which optional modules boot with n8n: `instance-ai` adds n8n's AI Assistant (which includes AI-assisted agent building — describe the agent, and n8n scaffolds it), and `agents` enables the Agent runtime itself. You can run with just `agents` and build everything by hand, which is what I would do in production while this is in Preview.

Two optional pieces:

- **Knowledge base:** set `N8N_AGENTS_AI_SANDBOX_ENABLED=true` and `N8N_AGENTS_AI_SANDBOX_PROVIDER=daytona`. This reuses the Daytona sandbox you set up for the n8n Assistant. Skip it if your agent doesn't need file search.
- **Channels:** set `WEBHOOK_URL=https://your-public-url`. Slack, Telegram, and Linear need a public URL to reach your instance. Without it, you can still build agents and chat with them in the Agent Builder, but nobody outside can reach them.

> **Note:** Agents aren't available on self-hosted Enterprise yet, and queue mode is unsupported. n8n also warns that self-hosted channel connections like Telegram can fail — regular mode is the current recommendation.

## The official demo is worth copying

n8n's launch material demos a Telegram assistant that turns **sticky-note photos into tasks, logs receipts, and sorts email**. It is a well-chosen example, because all three tasks share the property that makes Agents worth using: the input is messy (a photo, a receipt, an inbox), the right action depends on interpretation, and the cost of getting it wrong is low enough that an approval-gated tool call is an acceptable safety net.

If you want to test whether Agents are worth your time, rebuild that demo. Point an agent at a channel you actually use, give it your workflows as tools (not direct credentials), require approval on every write, and watch the Sessions tab for a week. That week will teach you more about the Preview's rough edges than any review article.

## When to pick which: a decision guide

| Your job | Reach for |
|---|---|
| Known sequence: form → validation → CRM | A workflow |
| Conversational triage: inbox, tickets, research requests | An Agent |
| Something an agent should do *as part of* a fixed process | A workflow with a Message an Agent node |
| Something deterministic an agent should trigger | An Agent with your workflow as a tool |
| Production system where downtime costs money | A workflow (until Agents leave Preview) |

The honest architecture, which the best community write-ups converge on: keep the workflow in charge of every sequence you already know. Put the Agent only at the point where a conversation must choose what comes next. Give it narrow workflows as tools, store the session, publish a tested snapshot, and put approval in front of every meaningful side effect.

## Hard cases and limitations

- **Preview status is real.** The docs warn that agents can make mistakes and their behavior may change while in development. Test before you publish.
- **Self-hosted Enterprise:** not supported yet. No target version announced.
- **Queue mode:** unsupported. If your instance runs queue mode, channel connections such as Telegram can fail.
- **Costs are execution-based.** One turn equals one execution against the same quota as workflows. A public-facing agent with a chatty model can burn quota faster than you expect — monitor usage the first week.
- **Episodic memory needs an OpenAI credential**, even if the agent itself uses a different model. If you don't set it up, memory is session-scoped only.
- I have not tested the MCP-based agent management flow end to end, and the 100%-rollout changelog is days old — treat the exact availability edges (which versions, which Enterprise tiers) as moving targets and check [the docs](https://docs.n8n.io/build/build-and-manage-agents) before deploying.

## FAQ

### Do n8n Agents replace the AI Agent node?

No. The AI Agent node is unchanged, and everything built with it keeps working. Agents are a new, standalone component that sits alongside workflows. Use the node for reasoning steps inside a fixed process; use Agents for conversational, open-ended work.

### Can I use n8n Agents self-hosted?

Yes, from n8n 2.32.3 with the `agents` module enabled via `N8N_ENABLED_MODULES`. Knowledge files need a Daytona sandbox, and channels need a public `WEBHOOK_URL`. Self-hosted Enterprise and queue mode are not supported yet.

### How are agents billed?

Agents draw on the same execution quota as your workflows, and one turn with an agent counts as one execution. Calls to workflow tools and sub-agents don't count separately.

## Key Takeaways

1. **n8n now has two kinds of agent:** the AI Agent node (a step inside a workflow) and the standalone Agent (a first-class component you describe in plain language and publish to channels).
2. **Agents and workflows call each other** — use narrow workflows as an Agent's tools, or call an Agent from inside a workflow with the Message an Agent node.
3. **Draft → validate → publish** is the lifecycle; channels and schedules only run the published version, and sessions are fully reviewable.
4. **Preview limits are real:** no self-hosted Enterprise, no queue mode, behavior may change — require approval on every tool that writes.
5. **Keep workflows in charge of known sequences** and put the Agent only where the next step depends on interpretation.

Next: try the sticky-note Telegram demo against a channel you actually use, approval-gated, and watch the Sessions tab for a week. When you're ready for deterministic pipelines feeding agents, read [How to Connect an MCP Server to n8n](https://cortexflow.tech/blog/how-to-connect-mcp-server-n8n/) to wire up tools without dedicated nodes.
