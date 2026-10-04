---
title: "Relay.app Shut Down: Where to Move Your Automations in 2026"
description: "Relay.app shut down in September 2026. Compare the best alternatives — n8n, Make, Zapier — with migration paths for your existing workflows."
date: 2026-10-04
tool_a: "n8n"
tool_b: "Relay.app alternatives"
verdict: "Relay.app is gone — export what you can, then move to n8n if you're technical (free self-hosted, best AI-agent support) or Make if you want the closest visual-builder feel at $9/month."
---

## What happened to Relay.app?

Relay.app — the human-in-the-loop automation platform known for approval steps and AI-assisted workflows — **shut down in September 2026**. If you built automations on it, they're on borrowed time: export your workflow documentation now while you still have dashboard access, because the shutdown clock doesn't wait for your migration plan.

The good news: every major alternative is more capable than Relay.app was, and two of them are cheaper. Here's where to go.

## The alternatives at a glance

| | **n8n** | **Make** | **Zapier** |
|---|---|---|---|
| **Pricing model** | Per workflow execution | Per operation | Per task (action step) |
| **Free option** | Self-hosted: free, unlimited | 1,000 ops/month | 100 tasks/month |
| **Entry paid** | €24/mo (2,500 executions) | $9/mo (10,000 ops) | $19.99/mo annual (750 tasks) |
| **Self-hosting** | Yes | No | No |
| **Human-in-the-loop approvals** | Yes (Wait/Form nodes) | Partial (workarounds) | Partial (add-ons) |
| **AI agents** | Native LangChain, best in class | Included in paid plans | AI actions, less flexible |
| **Learning curve** | Moderate–steep | Moderate | Easiest |

*Pricing verified October 2026.*

## If you loved Relay.app's approval steps → n8n

Relay.app's signature feature was human-in-the-loop: "run this, wait for my approval, then continue." n8n replicates this natively with **Wait nodes** and **Form nodes** — a workflow can pause mid-run, ping you on Telegram or email, collect your decision, and resume. No add-ons, no workarounds.

n8n is also the strongest AI-agent platform of the three, which matters because Relay.app's other signature was AI-assisted workflows. And if cost was a reason you picked Relay.app, self-hosted n8n is free.

**Migration path:** document each Relay workflow's trigger → steps → approval points, then rebuild in n8n. The logic maps almost 1:1; budget a day per complex workflow.

## If you want the easiest landing → Make

Make's visual scenario canvas is the closest in spirit to Relay.app's builder, and at **$9/month for 10,000 operations** it's the cheapest soft landing. Approval-style flows need workarounds (webhook → wait → resume patterns), but for straightforward automations you'll be rebuilt in hours, not days.

> You can [try Make free here](https://www.make.com/en/register?pc=cortexflow) — 1,000 operations a month, no credit card.

## If your team is non-technical → Zapier

Zapier remains the fastest path from zero to automated for non-technical teams, with 8,000+ integrations. You'll pay more at scale (per-task billing adds up), but if your Relay.app usage was light, the Professional plan at $19.99/mo annual covers it.

## Migration checklist

1. **Export now:** screenshot or document every workflow while Relay.app access lasts — triggers, steps, filters, approval points.
2. **Inventory integrations:** list every app each workflow touches; confirm the alternative has connectors (or an API you can hit).
3. **Rebuild approvals first:** they're the hardest part — prototype one approval flow in your chosen platform before migrating everything.
4. **Run in parallel:** keep Relay.app workflows live while you test replacements; cut over one workflow at a time.
5. **Audit credentials:** rotate API keys as you move — don't reuse Relay.app-era tokens blindly.

## FAQ

**Did Relay.app really shut down?**
Yes — Relay.app shut down in September 2026. Migrate as soon as possible.

**What's the closest free alternative to Relay.app?**
Self-hosted n8n: free forever, unlimited executions, native approval/wait steps. You need a small VPS ($5–7/month) and basic technical comfort.

**Can I import Relay.app workflows into n8n or Make?**
No direct importer exists — you'll rebuild them. The logic maps cleanly; the work is mostly re-creating steps, not re-thinking them.

**Which alternative is cheapest?**
Self-hosted n8n (software free), then Make at $9/mo, then n8n Cloud at €24/mo, then Zapier at $19.99/mo for much lower included volume.
