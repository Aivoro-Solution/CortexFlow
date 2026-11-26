---
title: "OpenCode 2.4 Turned Automations On by Default — Steal the Pattern for n8n (Safely)"
description: "OpenCode 2.4.0 adds scheduled agent runs and a signed-in browser. Here is the 5-part n8n pattern to copy the power without the risk."
date: 2026-11-26
category: news
tags: ["opencode", "n8n", "ai-agents", "mcp", "automation"]
draft: false
featured: false
image: "/og/opencode-240-automations-n8n-safety-pattern.webp"
---

"opencode" rose 300% as a related query for "n8n" in Google Trends (US, past 7 days) this week. The reason is a release, not a rumor: OpenCode 2.4.0 shipped on November 23, 2026, and it quietly changed what a coding agent is allowed to do while you are not watching.

OpenCode is an open-source (MIT) coding agent that runs as a terminal app, a desktop app, or an IDE extension, and works with 75+ model providers. Version 2.4.0 adds two things that matter to automation builders: **Automations** that run on a schedule, and a **built-in desktop browser** that imports your sign-ins. Both are on by default. That combination is powerful, and it is exactly where builders get hurt.

By the end of this article you will know what 2.4.0 actually does, where the risk sits, and a five-part pattern to run the same idea in n8n with a human approval gate, spend caps, and a log you can audit.

## What shipped in OpenCode 2.4.0

The official changelog for November 23, 2026 lists three headline changes.

**Automations.** You can ask the agent to run a prompt, a Code Mode script, or a fixed shell command once, on an interval, on a cron schedule, or when a connected MCP server pushes an event. You manage them with the `/automation` command or the `automation` tools. A shell action asks for approval once, when it is created, and records each run's exit code and output. If you do not want them, you set `"automations": false` in your config.

MCP (Model Context Protocol) is the open standard that lets an AI model call external tools. OpenCode 2.4.0 also ships MCP Events: push delivery from an MCP server, with argument checks, heartbeats, and automatic reconnects. An event too large for its prompt is skipped, and its automation keeps running.

**Built-in desktop browser.** The desktop app can import your sign-ins and browsing history from Chrome, Edge, Firefox, or Safari, and add extensions from Chromium browsers or the Chrome and Edge stores. Everything stays in one persistent desktop profile: chat links open signed in, tabs survive restarts, and the agent can read and drive the same pages without you switching apps.

**Video generation.** When a connected provider has a video model, the agent can call `generate_video`. The job runs in the background, survives a server restart, and saves the finished files into your workspace.

Two follow-ups landed quickly. Version 2.4.1 (also November 23, 2026) fixed session saving on macOS 12 and let plugins create, list, and delete automations. Version 2.4.2 (November 26, 2026) keeps browser access for sessions in open tabs after a restart or when an automation wakes them. That last line tells you the direction: automations and the signed-in browser are meant to work together.

![An isometric automation press: a clockwork scheduler fires agent runs through an approval gate, with a live readout of the release numbers.](/figures/opencode-240-automations-n8n-safety-pattern-automation-press.svg)

*Figure 1: The 2.4.0 automation loop as a press. Four triggers (once, interval, cron, MCP event) can fire three actions (prompt, script, shell command). Notice the single approval at creation time — that is the gap the n8n pattern below closes.*

## The risk in one sentence

Approval happens once, at creation. After that, a scheduled shell command or a woken session with browser access can act at 3 a.m. with your signed-in profile, and the only record is an exit code and output log.

That is not a flaw unique to OpenCode. It is the default shape of every always-on agent: convenience first, guardrails second. Google's Stitch Loop made the same trade and answered it with "nothing merges until you review the PR" — see [our Stitch Loop pattern for n8n](/blog/google-stitch-loop-always-on-agent-n8n-pattern/). OpenCode's answer is thinner: approve the shell action once, then trust it.

For a personal coding session, that may be fine. For anything that touches production, customer data, or money, it is not. The fix is not to avoid automations. The fix is to move the approval from creation time to run time for anything irreversible, and to cap what a run can spend or touch.

## The 5-part safe-automation pattern for n8n

n8n already has every piece you need. The pattern below mirrors OpenCode's triggers and actions, then adds the gates OpenCode leaves out. It assumes you can build a basic n8n workflow and have read [how to connect an MCP server to n8n](/blog/how-to-connect-mcp-server-n8n/).

**Prerequisites:** an n8n instance (Cloud or self-hosted) where you can create workflows, one model credential for the AI Agent node, and a place to log runs (a sheet, a table, or a file). Versions move fast; check your n8n version in Settings before you start, as of November 2026.

### Part 1 — Number the trigger

OpenCode gives you four triggers. In n8n, pick exactly one per workflow and write it down:

| OpenCode trigger | n8n equivalent | Use it for |
|---|---|---|
| Once / interval | Schedule Trigger | Nightly checks, digests |
| Cron schedule | Schedule Trigger (cron mode) | Weekday-only jobs |
| MCP event | MCP Server Trigger or Webhook | React to another system |

One trigger per workflow keeps failures readable. If a run misbehaves, you know which door it came through. Name the workflow after the trigger and the job, for example `cron-weekday-dependency-check`.

### Part 2 — Draft first, never act first

Let the agent produce a draft: a proposed diff, a drafted message, a list of commands it wants to run. Do not let the first output touch anything real.

In n8n, put the AI Agent node before any write node, and have it output structured JSON with three fields: `action`, `target`, and `reason`. A Code node then validates that JSON against an allowlist. If `action` is not on the list, the workflow stops and logs the rejection. This is the same allowlist idea we use in [the n8n agent guardrails release guide](/blog/n8n-2430-agent-guardrails-release/).

### Part 3 — Approve at run time

This is the part OpenCode skips. Add a Wait node configured for approval, or an IF node that checks a human decision stored outside the workflow.

A simple version: the workflow sends the draft to you (email or chat), then waits. Only a reply that matches the run ID continues the workflow. Everything else times out and logs "no approval." For shell commands, show the exact command string in the approval message. Approving "run the cleanup" is not approving `rm -rf`. Show the bytes.

> **Warning:** Never approve a shell command you have not seen in full. If the command is generated by the model at run time, treat every run as a new command, not a repeat of the one you approved at creation.

### Part 4 — Cap the execution

Give every run a budget: maximum model tokens, maximum runtime, and a fixed list of tools. In n8n, set the AI Agent node's max iterations, add a timeout on HTTP and Execute Command nodes, and keep credentials scoped to the smallest permission that works.

For browser work, use a dedicated profile with only the accounts the job needs. OpenCode's import-everything browser is convenient; a scoped profile is safer. If an agent can read your signed-in pages, assume a prompt injection on one of those pages can try to steer it. The cap that matters most is the tool list: no send, no delete, no pay unless Part 3 approved that exact action.

### Part 5 — Log every run, off the agent's channel

Append one row per run: timestamp, trigger, draft hash, approver, command or action taken, exit code, and output location. Keep the log somewhere the agent cannot edit.

OpenCode records exit code and output for shell actions, which is a good start. Your log should also record the runs that were rejected or timed out. A pattern of rejections is often the first sign that a prompt or a data source has drifted. If a run fails, [the MCP troubleshooting guide](/blog/mcp-n8n-troubleshooting/) covers the connection checks to run first.

## How to wire it in 20 minutes

1. Create a workflow with a Schedule Trigger set to your interval. You should see the next run time in the trigger panel.
2. Add an AI Agent node with a prompt that asks for a draft in the `action` / `target` / `reason` JSON shape. Run it once manually; you should see valid JSON in the output.
3. Add a Code node that checks `action` against your allowlist and throws on anything else. Test it with a deliberately bad action; the execution should stop there.
4. Add a Wait node for approval and a notification node before it that sends you the full draft. Approve once and reject once; both paths should be visible in the execution list.
5. Add your real action node after the approval, with a timeout set. Run the full workflow end to end and confirm one log row appears for the approved run and one for the rejected run.

If all five steps pass, you have OpenCode's automation shape with run-time approval. Turn the schedule on, then watch the first week of logs before you widen the allowlist.

## Limits and trade-offs

This pattern is slower than OpenCode's approve-once model, by design. A human in the loop means some 3 a.m. runs will wait until morning. For read-only jobs (summaries, checks, reports), you can skip Part 3 and rely on caps and logs. For writes, keep it.

OpenCode itself moves fast — 2.4.0, 2.4.1, and 2.4.2 all landed within four days — so tool names and flags may change again. The `"automations": false` opt-out and the `/automation` command are current as of November 26, 2026; check the changelog before you build on them. We did not run OpenCode 2.4.0 against a production n8n instance for this article; the n8n wiring above follows n8n's documented nodes and the pattern we have shipped in earlier guides.

## FAQ

### Is OpenCode 2.4.0 safe to use with automations on?

For personal, read-mostly work, yes, with the shell-approval and logging it provides. For production writes, add run-time approval and caps as above, or set `"automations": false` until you have them.

### How do I turn OpenCode automations off?

Set `"automations": false` in your OpenCode config. The changelog lists this as the opt-out for 2.4.0.

### Can n8n trigger an OpenCode automation?

Indirectly. OpenCode automations fire on timers, cron, or MCP events. An n8n workflow can push an MCP event or call a webhook that your automation listens to, but keep n8n as the approver and logger rather than a blind trigger.

### Does the built-in browser share my passwords with the model?

The browser keeps sign-ins in a persistent desktop profile so the agent can open pages as you. Treat that profile like a logged-in session: scope it to the job, and never let an unapproved run send, delete, or pay from it.

## Key Takeaways

1. **OpenCode 2.4.0 (November 23, 2026) turns scheduled agent runs on by default** — four triggers, three actions, one approval at creation.
2. **The signed-in browser is the risk multiplier.** Automations that wake sessions keep browser access, so scope the profile to the job.
3. **Move approval to run time for writes.** Show the exact command or action, every run.
4. **Cap tokens, time, and tools, then log approvals and rejections alike.** The log is your early-warning system.

Next step: build the five-part workflow above for one read-only job this week, watch its logs for seven days, and only then add a single write action behind the approval gate.
