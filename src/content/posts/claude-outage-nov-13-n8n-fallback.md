---
title: "Claude Went Down Twice on Friday the 13th — Your n8n Agent Needs a Backup Model"
description: "Claude went down twice on Nov 13, 2026 — auth failures, then API errors for 2h 29m. Timeline plus the 5-part fallback pattern for n8n AI Agent workflows."
date: 2026-11-14
category: news
tags: ["claude", "anthropic", "n8n", "outage", "ai-agent"]
draft: false
featured: false
image: "/og/claude-outage-nov-13-n8n-fallback.webp"
---

Searches for "claude status" broke out on Google Trends in the US this week, and "is claude down" was right behind it — because on Friday, 13 November 2026, Claude went down twice. First the sign-in broke, locking users out of claude.ai and Claude Code for two hours. Then, a few hours later, the API itself started returning elevated errors for 2 hours 29 minutes — which is the outage that actually hits n8n builders, because that is the endpoint your AI Agent node's Anthropic chat model calls.

This article gives the timeline from Anthropic's own status page, separates the two incidents from the Microsoft 365 connector failure that was still running at the same time, and lays out the five-part fallback pattern I would build into any n8n workflow that depends on a single model.

## What went down, hour by hour

All times are 13 November 2026, UTC, from Anthropic's status page at status.claude.com unless noted.

| Time (UTC) | What happened |
| --- | --- |
| 09:58 | **Incident 1 opens.** Anthropic is "investigating an issue with users authenticating to Claude.ai and Claude Code". Users cannot sign in, or their existing login stops being accepted. |
| 11:05 | A fix is deployed for the authentication issue; Anthropic monitors for recovery. |
| 11:58 | **Incident 1 resolved.** Two hours after it opened. Affected: claude.ai, Claude Code and the Console (platform.claude.com). The Claude API was **not** on the affected list — apps calling api.anthropic.com kept working through this one. |
| 13:09 | **Incident 2 opens.** "Elevated errors on claude.ai, the Claude API, and Claude Code." This is the one that hits n8n workflows. |
| 13:52–14:36 | Anthropic widens the scope: connectors including Claude Docs and Claude Sheets are degraded, along with Claude Security, Claude Managed Agents and Claude in Meetings. Mobile apps are affected the same way as claude.ai. |
| 15:33 | Errors return to normal levels. But: adding a new connector on claude.ai is temporarily unavailable, **scheduled tasks and routines can run more than two hours late and some runs have been skipped**, and Security scans, reviews and project setup remain delayed. |
| 15:38 | **Incident 2 resolved.** 2 hours 29 minutes after it opened. |
| 21:49 | The **separate Microsoft 365 connector incident resolves** — see below. |

User-report tracker Downdetector logged a spike of nearly 3,000 reports during the morning, and Anthropic's status page listed claude.ai and Claude Cowork as degraded even after the second incident was marked resolved.

## Three incidents, not one — and the Microsoft one is separate

It is easy to read Friday as a single bad day for Claude. It was three distinct failures, and confusing them leads to the wrong fix:

1. **The auth incident (09:58–11:58 UTC).** A sign-in problem. It locked people out of the chat product and the coding tool. It did not touch the API, so an n8n workflow calling Claude kept running.
2. **The elevated-errors incident (13:09–15:38 UTC).** The API itself returned errors. This is the one that breaks AI Agent nodes, and it also degraded connectors, scheduled tasks and Claude Security. Anthropic has not said what caused either incident.
3. **The Microsoft 365 connector incident (12 Nov 17:52 UTC – 13 Nov 21:49 UTC).** Claude's mail, calendar and search tools in the Microsoft 365 connector — and Claude for Outlook — failed for most requests for more than 24 hours, because of the Microsoft 365 outage that began on 12 November. We covered that outage yesterday: it took Outlook, Teams and SharePoint down for five-plus hours. Anthropic's final update puts the connector impact window at 16:03 UTC on 12 November to 16:40 UTC on 13 November. This incident was Microsoft's, not Anthropic's — but if your n8n workflow reads Outlook mail through Claude, it was down either way.

One more data point, from the morning after: at 02:54 UTC on 14 November, Anthropic opened a **third** incident — elevated errors affecting purchases, plan upgrades and cancellations on claude.ai. By 03:09 UTC it was monitoring recovery, with purchases working normally and delayed plan changes being applied, some taking up to an hour. Core functionality was not affected and the API stayed operational. Three incident days in one week, after a 14-minute outage on 8 November that hit claude.ai, the API, Claude Code and Cowork.

## Why this hits n8n builders harder than chat users

A chat user retries a prompt and moves on. An n8n AI Agent node that calls Claude has no retry button and no human watching:

- **The workflow fails, not the prompt.** When api.anthropic.com returns errors, the Anthropic Chat Model node errors, and the AI Agent node errors with it. Unless the workflow is designed for it, the execution stops and the run is recorded as failed.
- **Scheduled runs are lost, not delayed.** Claude's own scheduled tasks ran more than two hours late or were skipped entirely during the incident. An n8n Schedule Trigger workflow that fires once and fails has the same property: the slot is gone. If the workflow sends a customer reply, files a report, or moves money, a missed run is a missed obligation, not a late one.
- **Retries during the outage make it worse.** An agent that retries immediately, in a tight loop, burns through your Anthropic rate limit and your budget while the provider is still down — and if the workflow has side effects, a retry that eventually succeeds twice is a duplicate action.
- **Your alert probably uses the same model.** If the workflow that tells you something broke also calls Claude to draft the alert, the alert fails too.

## The fallback pattern: five parts

![Fig 1 — The model switchboard: the Claude API cell trips its breaker and goes dark, the switch lever flips to a lit backup-model cell, and pending requests wait in the queue drum instead of being dropped. Watch the queue drum — it is what turns a 2-hour outage into a delay instead of a loss.](/figures/claude-outage-nov-13-n8n-fallback-model-switch.svg)
*Fig 1 — The model switchboard. When the Claude API cell trips, the lever flips to a backup model and pending requests wait in the queue drum. The numbers are from Friday: two outages, the API down 2 hours 29 minutes, authentication down 2 hours, and scheduled tasks running more than two hours late.*

### 1. Check the status page before you debug your workflow

When an AI Agent node starts failing, the first check is status.claude.com — not your credentials, not your prompt. Anthropic posted the first incident within minutes of it starting. A 30-second check saves an hour of debugging a workflow that was never broken. Put the status-page URL in the workflow's documentation, and in the error message your error workflow sends you.

### 2. Retry with backoff, capped — on the node, not in a loop

n8n nodes have a **Retry on fail** setting in the node's Settings tab: enable it, set a wait interval between attempts, and cap the number of tries. A retry that waits 60 seconds, then 5 minutes, then 15 minutes rides out a short blip without hammering a recovering API. What you must not do is wrap the agent call in a loop node that retries immediately until it succeeds — during a two-and-a-half-hour outage that loop is a denial-of-service attack on your own quota.

> **Warning:** retries are only safe for read-only steps. If the agent step sends an email, posts a message, or charges a card, a retry that succeeds after the first attempt actually went through is a duplicate. For side effects, use the idempotency gate from our [webhook duplicate guide](/blog/fix-n8n-webhook-duplicate-idempotency/) — claim each action once before executing it — so a retry can never fire twice.

### 3. Fail over to a second model

The AI Agent node takes one chat model, so the fallback lives one level up: put the agent call in a sub-workflow, and catch its failure with an [Error Trigger](https://docs.n8n.io/) workflow — n8n's built-in node that starts a workflow when another workflow errors. The error workflow can then invoke the same sub-workflow with a different model attached (OpenAI's GPT or Google's Gemini, via their chat model nodes), or route the request to a simpler, non-agent path: a templated reply, a summary instead of a full draft, a ticket instead of an answer.

Two honest limits. First, the fallback model will answer differently — prompts tuned for Claude do not transfer verbatim, so test the fallback path with real inputs before you need it. Second, a fallback is a cost decision: you are paying for a second provider's capacity to sit idle. For a workflow that answers customers, that is cheap insurance. For a nightly summariser, a queue (step 4) is cheaper than a second model.

### 4. Queue the request, then replay it idempotently

When the model is down, park the job instead of dropping it. Store the request — input, user, and a stable idempotency key — in a table, and let a second workflow drain the queue once the API recovers. The key is what makes the replay safe: when service returns, the drain must not send the same message twice. Our [idempotency gate pattern](/blog/fix-n8n-webhook-duplicate-idempotency/) is the exact shape: `INSERT ... ON CONFLICT DO NOTHING` as the first step, so a duplicate execution is claimed once and rejected after that.

For scheduled workflows, add a "did this run already happen?" check at the start — a row in the same table, keyed by the scheduled slot. If Friday's run was skipped because Claude was down, Saturday's drain replays it once; if it already ran, the check skips it. That is the difference between a missed obligation and a late one.

### 5. Alert on a channel that does not depend on Claude

The failure notification should not go through the thing that failed. An Error Trigger workflow that sends a Telegram message — Telegram is one API call, no model involved — reaches you while Claude is down. Keep the message short and factual: workflow name, execution ID, error text, and the status-page link. Our [n8n 2.43 guardrails release](/blog/n8n-2430-agent-guardrails-release/) covers the approval-gate shape that belongs in front of any replayed side effect: nothing that moves money or messages a customer fires from the queue without a human approving it first.

## What I would do this weekend

If Claude is the model behind your n8n agents, three small changes cover most of Friday's failure modes: enable capped retry-with-backoff on every Anthropic Chat Model node; add an Error Trigger workflow that alerts you on Telegram and parks the failed request in a queue table; and give one high-value workflow a second-model fallback path and test it once. The queue and the fallback are the parts that take an afternoon — the retry setting takes two minutes, and it is the one that would have saved most executions on Friday.

The Microsoft side of Friday is the same lesson from the other direction: our [Microsoft 365 outage article](/blog/microsoft-365-outage-ai-connectors-down/) covers the connector-dependency pattern — probe before acting, fail loudly, and keep a fallback channel outside the account that is down.

## FAQ

### Was Claude down on 13 November 2026?

Yes, twice. Anthropic's status page records an authentication incident from 09:58 to 11:58 UTC affecting claude.ai, Claude Code and the Console, and an elevated-errors incident from 13:09 to 15:38 UTC affecting claude.ai, the Claude API and Claude Code. A separate Microsoft 365 connector incident ran from 12 November into the evening of 13 November.

### Did the outage affect the Claude API used by n8n?

The second incident did: api.anthropic.com returned elevated errors from 13:09 to 15:38 UTC. The first incident, the sign-in failure, did not list the API as affected. n8n workflows calling Claude through the Anthropic Chat Model node would have failed during the second window.

### What caused the Claude outage?

Anthropic has not disclosed a cause for either 13 November incident as of the morning of 14 November. The Microsoft 365 connector failure was caused by Microsoft's own outage, which Microsoft attributed to a network capacity upgrade issue.

### Is Claude still down?

No. Both 13 November incidents are marked resolved. A third incident opened at 02:54 UTC on 14 November affecting purchases and plan changes on claude.ai; by 03:09 UTC Anthropic was monitoring recovery, core functionality was unaffected, and the API was operational.

## Key Takeaways

1. **Claude failed twice on 13 November** — sign-in down 2 hours (09:58–11:58 UTC), then the API down 2 hours 29 minutes (13:09–15:38 UTC). A separate Microsoft 365 connector failure ran for more than 24 hours alongside them.
2. **The API outage is the one that breaks n8n workflows** — the auth incident never touched api.anthropic.com. Check status.claude.com before debugging your workflow.
3. **Retry with backoff, capped, on the node** — never an immediate retry loop, and never retry a side effect without an idempotency gate.
4. **A second model is the real fallback** — via a sub-workflow plus an Error Trigger workflow. Test it with real inputs before you need it.
5. **Queue what you cannot run, and replay it once** — a "did this slot already run?" check turns a skipped schedule into a late one instead of a lost one.

Next: if your workflows read Outlook or Teams through Claude, read yesterday's [Microsoft 365 outage breakdown](/blog/microsoft-365-outage-ai-connectors-down/) — the connector failure outlasted both Claude incidents, and the resilience pattern there is the same shape with different dependencies.
