---
title: "DigitalOcean Cuttlefish: Approve Your AI Agent's Next Move From Your iPhone — What n8n Builders Should Steal"
description: "DigitalOcean's Cuttlefish puts AI agent approvals on your iPhone — live sessions, Face ID-gated tool calls, Box Mount. The n8n playbook."
date: 2026-11-10
category: news
tags: ["DigitalOcean", "Cuttlefish", "AI agents", "human-in-the-loop", "n8n"]
draft: false
featured: false
image: "/og/digitalocean-cuttlefish-iphone-agent-approval.webp"
---

"digitalocean" is a Breakout rising query for "n8n" in US Google Trends searches over the past 7 days — and the spike has a specific source. On November 5, 2026, at BoxWorks in San Francisco, DigitalOcean launched Cuttlefish, a native iPhone app that lets you supervise an AI agent from your phone: watch its sessions live, approve or deny its tool calls, and steer or stop a run while you are nowhere near your desk. The same announcement brought Box Mount, a private-preview feature that syncs a Box folder into the agent's workspace. By the end of this article you will know exactly what Cuttlefish does, why the approval bottleneck it solves is the same one your n8n agents have, and how to steal its approval-gate pattern for your own workflows.

## What Cuttlefish actually does

Cuttlefish is not another chatbot app. It is a supervision app for agents that are already running — in DigitalOcean's Managed Agents platform, which is in public preview. Managed Agents moved agents off your laptop and into the cloud: each session runs in its own isolated sandbox, so the work keeps going after you close the lid. Cuttlefish moves the person in the loop off the desk too.

The app does four things, and all four are about the moments when an agent stops and waits:

**Follow live sessions.** Replies, reasoning, and tool calls stream into the app as they happen, and you get notified when a run needs approval, finishes, or fails. You are watching the work, not a summary of it.

**Approve or deny tool calls.** When the agent wants to run something consequential, you see the full command, file path, or diff — not a one-line summary — and approve or deny it from wherever you are. Requests classified as high risk require Face ID or your passcode before they go through.

**Steer mid-run.** Send a correction, pause, resume, or stop a session that is heading the wrong way. Messages you send while the agent works get queued, so you can line up the next task without waiting for the current one to finish.

**Work with the results.** View what the agent built, including websites and documents, right in the app. You can also browse workspace files, create checkpoints, and fork or roll back a session.

DigitalOcean built Managed Agents around three principles — choice, control, and collaboration — and Cuttlefish inherits all three. Choice means the platform runs the harness your team already uses: Claude Code, Codex CLI, OpenCode, OpenHands, Hermes, LangGraph, and CrewAI, with the models and more than 20,000 tools that fit the work. Cuttlefish supervises all of them, so the app in your pocket is not tied to a single vendor's agent. Control means you decide which actions an agent can take on its own and which are off limits. Collaboration means sessions run in DigitalOcean-hosted microVMs that persist independently of anyone's device, so a run does not depend on your laptop and a teammate can join or take over when you are away.

## The problem it solves: the stalled run

DigitalOcean's own blog opens with the scene every agent builder knows. Your agent has been refactoring for two hours. It is deep in the codebase, making real progress, and then it stops: "Can I run this migration?" Nothing happens until you answer — and you are not at your desk. You are in line at the grocery store, or waiting at school pickup.

This is the quiet failure mode of long-running agents. The agent is not broken; it is polite. It did the safe thing and asked. But the human it asked is unreachable, so a two-hour run stalls for the rest of the afternoon. Every team running agents overnight hits this wall: the longer an agent runs unsupervised, the more likely it is to need a human at exactly the moment no human is watching.

That is why the approval mechanism matters more than the app itself. Cuttlefish's design choices are the interesting part: show the full command or diff, not a summary; require biometric confirmation for high-risk calls; let the human steer, pause, or stop — not just approve. An approval button that hides what it approves is a rubber stamp. One that shows the diff and demands Face ID for the dangerous calls is a control.

## Box Mount: agents on your real files

Alongside Cuttlefish, DigitalOcean announced a collaboration with Box, with Box as the launch partner. Box Mount, now in private preview, syncs a Box folder into every session of a Managed Agents environment, so agents work on the same files your team already uses — under Box's permissions, version history, and audit trail.

In Cuttlefish, you open Customize, then Tools, then Box, sign in, and pick a folder. The agent works on plain files in its workspace. Its edits upload to Box, and changes made in Box show up in the workspace. Each person syncs with their own Box account.

DigitalOcean's example is a fictional legal team that keeps vendor contracts in a Box folder. An agent working on that folder stops to ask permission before writing a summary. On the way to a trial, a lawyer approves from their phone, and the summary lands back in the Box folder, where any colleague with access can see it right away. No one has to email a file or ask who has the latest copy.

There is a sharp edge here worth naming plainly: the agent can edit and delete files in the synced folder, and deletions sync back to Box. The permission model is Box's — which is the point — but a folder shared with an agent is a folder the agent can damage. That is exactly why the approval gate in front of it matters.

## The n8n builder's playbook: steal the approval gate

This is where the story stops being about DigitalOcean and starts being about your workflows. Cuttlefish is an iPhone app for DigitalOcean's platform, and most n8n builders will never open it. But the pattern it implements — a human approval gate in front of every consequential agent action — is one you can build into an n8n agent today, with tools you already have. Think of it as a gate machine: the agent's request arrives, a human on a phone stamps it, and only stamped requests reach the real world.

![An approval-gate machine for AI agents: a tool-call request card rides a conveyor into a phone-shaped press, where an approve lever stamps it and a Face ID lock guards high-risk calls; approved cards pass to the workspace, denied ones drop into a reject bin.](/figures/digitalocean-cuttlefish-iphone-agent-approval-approval-gate.svg)

*Fig 1 — The pocket approval gate. Every consequential tool call stops at the phone: the human sees the full command or diff, approves with a tap (Face ID for high-risk calls), and only then does the action run. The numbers are the ones from the story: 7 harnesses, 20,000+ tools, Face ID on high-risk calls. Denied calls never reach the workspace.*

**1. Route every consequential call through an approval node.** In n8n, that means a human-in-the-loop step — a Telegram or Slack message with Approve / Deny buttons — placed before any tool that writes, deletes, sends, or spends. Reads can run unattended. Anything irreversible waits for a tap. This is the same shape as the approval gates in our earlier coverage of [Accenture's authorized-access argument](/blog/accenture-warning-banks-blocking-ai-agents/) and [Wells Fargo's new agent-liability terms](/blog/wells-fargo-ai-agent-liability-nov-24/): the industry is converging on "approve before it acts" as the default, not the exception.

**2. Show the full action, not a summary.** Cuttlefish shows the command, the file path, or the diff. Your approval message should do the same: the exact command the agent wants to run, the exact rows it wants to update, the exact text it wants to send. An approval prompt that says "the agent wants to update the database" is asking the human to bless something they cannot see. Paste the diff into the message.

**3. Make high-risk approvals harder than low-risk ones.** Cuttlefish demands Face ID or a passcode for high-risk requests. Your version: route money, deletes, and external sends to a separate approval channel that only you can answer, with a second confirmation step. A single tap is fine for posting a draft; it is not fine for running a migration. The friction should scale with the blast radius.

**4. Give the human steering, not just a yes/no.** Cuttlefish lets you send a correction, pause, resume, or stop mid-run — and queues messages while the agent works. An n8n approval step that only offers Approve / Deny forces the human to kill a good run over a small mistake. Add a third option: "Approve with this correction," and feed the correction back into the agent's next step. The runs you save are the ones that were 90% right.

**5. Keep the session alive outside your laptop.** Managed Agents runs sessions in hosted microVMs that persist when your device sleeps, and a teammate can take over. The n8n equivalent is boring and essential: run the agent on a server or in queue mode, not on a laptop that closes, and log every approval decision with who approved it and when. An approval nobody can audit later is a rubber stamp with extra steps — and it is the same audit-trail logic behind [Replit's sandbox containment work](/blog/replit-microvm-sandbox-agent-containment/) and the [guardrails in n8n 2.43](/blog/n8n-2430-agent-guardrails-release/).

## What to watch: the honest limits

Cuttlefish is a launch, not a finished product, and three limits matter for anyone evaluating it. First, Managed Agents is in public preview, offered as-is with no production support guarantees — DigitalOcean says so in its own release. Do not run anything you cannot afford to lose through it yet. Second, Cuttlefish is available on the App Store for Managed Agents customers only, and it is iPhone-only for now; there is no Android version announced. Third, Box Mount is in private preview, so the Box half of the story is not something you can try today unless you get access.

There is also a pricing-shaped hole: DigitalOcean has not published what Managed Agents will cost when it leaves preview, or what Cuttlefish itself costs. The Agent Droplets tier we covered in October started at $50 a month; whether Managed Agents lands anywhere near that is unanswered. Treat the platform as a design to learn from until the pricing and the production guarantees exist.

One more thing to watch: the name. The cuttlefish is one of the ocean's most dynamic camouflagers — it changes color, pattern, and texture to match whatever is around it. DigitalOcean says that is the metaphor: an agent that adapts to the harness, tools, and models around it. It is a good name for a supervision app, because the thing being supervised is, by design, always changing shape. That is precisely why it needs a human watching it.

## FAQ

### What is DigitalOcean Cuttlefish?

Cuttlefish is a native iPhone app, launched November 5, 2026, for DigitalOcean's Managed Agents platform. It lets you follow live agent sessions, approve or deny tool calls, steer or stop runs, and view results from your phone. High-risk approvals require Face ID or your passcode.

### Which agent frameworks does Cuttlefish work with?

Any harness running on Managed Agents: Claude Code, Codex CLI, OpenCode, OpenHands, Hermes, LangGraph, and CrewAI, with the models and 20,000+ tools that fit the work. The app supervises all of them rather than being tied to one vendor's agent.

### What is Box Mount?

Box Mount is a private-preview feature that syncs a Box folder into a Managed Agents session, so agents work on the same files your team already uses under Box's permissions, version history, and audit trail. The agent can edit and delete files in the synced folder, and deletions sync back to Box.

### Can I build the same approval pattern in n8n?

Yes. Put a human-in-the-loop approval step (Telegram or Slack Approve / Deny buttons) before any tool that writes, deletes, sends, or spends; show the full command or diff in the approval message; require a second confirmation for high-risk actions; and log every decision. The pattern is the product — the phone app is just one implementation of it.

### Is Cuttlefish available now?

Cuttlefish is available on the App Store for Managed Agents customers. Managed Agents itself remains in public preview, and Box Mount is in private preview.

## Key Takeaways

1. **"digitalocean" is a Breakout rising query for "n8n" in US Google Trends** — the spike is Cuttlefish, launched November 5, 2026, at BoxWorks.
2. **Cuttlefish is a supervision app, not a chatbot** — live sessions, approve/deny on full commands and diffs, Face ID for high-risk calls, pause/resume/stop mid-run.
3. **Box Mount puts agents on real business files** — a Box folder synced into the agent workspace under Box permissions and audit trail, in private preview.
4. **The pattern is portable to n8n** — approval node before consequential tools, full action in the message, harder approvals for riskier calls, steering plus audit log.
5. **Limits are real** — Managed Agents is public preview with no production guarantees, iPhone-only, and no pricing published yet.

Next: try the approval-gate pattern on one of your own agents this week — add a Telegram approval step before a single consequential tool and see how many runs it saves versus how many it stalls. If your agent never asks for approval, that is not a sign it is safe; it is a sign nobody is watching. For the bigger picture on where agent authorization is heading, read our coverage of [Accenture's warning that bank agent bans won't last](/blog/accenture-warning-banks-blocking-ai-agents/) and [China's agent ID cards](/blog/china-ai-agent-id-cards-wuzhen-2026/).
