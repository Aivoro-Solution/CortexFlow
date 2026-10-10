---
title: "n8n AI Agent Memory Explained: Window Buffer vs Redis vs Postgres (and 3 Bugs That Break It)"
description: "n8n agents forget tool results, pollute context, and break Claude — here's how each memory backend works and how to fix all three."
date: 2026-10-10
category: ai-agents
tags: ["n8n", "ai-agent", "memory", "chat-memory", "tutorial"]
draft: false
featured: false
image: "/og/n8n-ai-agent-memory-explained.webp"
---

Memory is the single most confusing part of building an AI agent in n8n — and GitHub agrees. The most-commented AI-agent issue in n8n's repository is a memory bug: an agent that cannot remember what its own tools just did. Around it clusters a family of related failures: agents that stuff entire tool outputs into their context window, ballooning costs; and agents that silently corrupt their history when paired with certain memory backends, breaking Claude mid-conversation.

This post is the guide I wish existed when I hit all three. You will learn what each memory backend actually does, which one to pick for your use case, and exactly how to avoid the three bugs that are biting builders right now.

## What memory means in an n8n agent

An AI agent in n8n is a loop: the model receives your message, decides which tool to call, reads the tool's output, and repeats until it has an answer. **Memory** is the record of that conversation — the past messages the agent can see when it reasons about the next turn.

Without memory, your agent greets every message like a stranger. With badly configured memory, it greets every message like a stranger who has been given your entire life story on paper — expensive, slow, and occasionally confused. The memory backend decides *where* that record lives and *how much* of it the agent re-reads each turn.

In n8n, you attach memory to the AI Agent node as a sub-node. There are three backends that matter in 2026:

![AI chatbot illustration — the agent's memory is its record of the conversation](/images/n8n-ai-agent-memory-explained/chatbot.jpg)

## The three memory backends

### Window Buffer Memory (a.k.a. Simple Memory)

This is the default, and it does exactly what the name says: it keeps the last *N* messages — a sliding window — in the n8n process's own RAM. Newer versions of n8n label it **Simple Memory** in the node picker, but it is the same node.

**Best for:** testing, prototypes, and any agent where losing history on restart is acceptable.

**The critical limitation:** it lives in memory of the running n8n process. Restart the process (or redeploy the container), and the history is gone. Every chat starts fresh.

**Setup:** drop the node under your AI Agent, set a session key (for a WhatsApp agent, the sender's phone number; for a web chat, the chat ID), and set the context window — 10 to 20 messages is the sane range. Longer windows raise token costs on *every single turn*, because the full window is re-sent to the model each time.

### Redis Chat Memory

The same sliding window, but the history is stored in **Redis** (a fast in-memory database that lives outside the n8n process) instead of the process RAM. The conversation survives restarts and works when you run multiple n8n workers behind a load balancer (queue mode), because every worker reads from the same store.

**Best for:** production agents, queue-mode setups, multi-user chatbots (each user gets a session key, all sessions share one Redis).

**The catch:** you need to run Redis, and you must be disciplined about the window size. Redis does not make memory cheaper — it just makes it *durable*.

### Postgres Chat Memory

History stored in a **Postgres** table. This is the durable, inspectable option: you can query the table, debug exactly what the agent saw, and keep long histories without paying for a Redis instance you otherwise wouldn't run.

**Best for:** teams that already run Postgres (most self-hosted n8n stacks do), auditing, and debugging.

**The catch:** see Bug #3 below.

![Data center servers — Redis and Postgres memory backends store conversation history outside the n8n process](/images/n8n-ai-agent-memory-explained/datacenter.jpg)

## The decision table

| Situation | Pick |
|---|---|
| Prototyping a new agent today | Simple Memory, 10–20 message window |
| Production chatbot, one n8n instance | Redis Chat Memory (survives restarts) |
| Production, queue mode / multiple workers | Redis Chat Memory (required — workers can't share process RAM) |
| Need to audit or debug exactly what the agent saw | Postgres Chat Memory |
| Already self-hosting Postgres, no Redis | Postgres, but read the Postgres bug first |

## Bug #1 — The agent doesn't remember what its tools did

This is GitHub issue #14361, the most-commented AI-agent issue in n8n's tracker: **"AI Agent doesn't store the Tool usages in memory."**

What it looks like in practice: your agent calls a tool (say, a vector store lookup), gets the answer, and replies correctly. Then the user asks a follow-up — "and what was the price you found?" — and the agent draws a blank or hallucinates. The tool *execution* happened, but the tool's input and output were never written into the chat history the agent re-reads.

**The workaround:** don't rely on memory to carry tool results across turns. Structure your workflow so critical facts get persisted explicitly — write them to a Data Table or database row keyed by session, and inject them into the agent's system message or as a preamble message before each turn. Treat tool results you need later as *state*, not *history*.

## Bug #2 — Memory pollution: the agent stores entire tool outputs

GitHub issue #22112 documents this one: **AI Agent v3 stores full intermediate tool outputs in Redis Chat Memory.** Every scratchpad step the agent takes — raw API responses, full page contents, entire database dumps — lands in the memory history, and the full history is re-sent to the model on every subsequent turn.

The cost math is brutal. If each tool call returns 2,000 tokens and the agent makes five calls, that's 10,000 tokens of garbage re-sent on *every later turn*, compounding with the sliding window. Your "cheap chatbot" starts billing like a research agent.

![Code on a laptop screen — shrinking tool outputs before the agent sees them keeps token costs under control](/images/n8n-ai-agent-memory-explained/code.jpg)

**How to control it:**

1. **Shrink tool outputs at the source.** Put a Code or Edit Fields node between your tool and the agent (or design tool workflows that return summaries) so the agent only ever sees the distilled answer, never the raw payload.
2. **Shrink the window.** If you can't shrink outputs, cut the message window to 5–10. The window is the multiplier.
3. **Monitor token usage per session** in your model provider's dashboard. A session whose input tokens grow linearly without the conversation getting longer is the signature of this bug.

## Bug #3 — The Postgres memory bug that breaks Claude

GitHub issue #20335: **Claude models failing because of an "Empty AI Message" bug in Postgres AI Memory.** The Postgres backend occasionally writes empty AI messages into the history. Claude's API is strict about message structure and rejects the conversation with an error, while OpenAI models shrug and continue. So your agent works fine on GPT and dies on Claude, and the root cause is in your memory backend, not your prompt.

**The workaround:** if you're on Postgres Chat Memory and targeting Claude, filter empty AI messages before they enter memory (a Code node that strips blank assistant turns from the history payload), or switch the agent to Redis while you wait for an upstream fix. Either way, when a Claude agent starts throwing structure errors mid-conversation, check the stored history for empty messages before you rewrite your prompts.

## Putting it together: the setup I'd recommend

For a production chatbot in 2026:

1. **Redis Chat Memory** with a 10-message window, session key per user.
2. **Shrink tool outputs** before the agent sees them — summary-first tool design.
3. **Persist facts explicitly** — session-scoped Data Table for anything the user might ask about twice.
4. **A periodic cleanup job** that expires old Redis sessions so abandoned chats don't hold memory (and tokens) forever.

If you're still prototyping, Simple Memory with a 10-message window is fine. Just remember the window's size is a cost dial, not a feature setting — every message in it is re-sent on every turn.

## FAQ

### Does memory work with the AI Agent node in queue mode?

Only with an external backend — Redis or Postgres. Simple (Window Buffer) Memory lives in the worker process's RAM, so different workers see different histories. This is the number one reason agents "forget" things after a seemingly innocent infrastructure change.

### RAG vs memory — aren't they the same thing?

No. RAG retrieves *documents* relevant to the current question; memory records the *conversation*. A retriever can't tell you what price it found two turns ago, and memory can't answer questions about your docs. You usually need both.

### How many messages should the window hold?

Start with 10. Raise it only when you can name a conversation that needed the 11th message back. Every message costs tokens on every turn forever.

## Key Takeaways

- **Simple Memory is for testing.** It dies with the process — don't ship a production agent on it.
- **The tool-usage gap is the #1 agent complaint on GitHub.** Persist important tool results as explicit state, not memory.
- **Shrink tool outputs before the agent sees them.** Memory pollution is a token-cost multiplier on every turn.
- **Claude + Postgres memory has a real bug.** Check stored history for empty AI messages before blaming your prompts.
- **Window size is a cost dial.** Start at 10, raise it with evidence, not optimism.

Next step: if you're building your first agent, pair this with the [AI Agent explainer](/blog/n8n-agents-explained/) to get the agent node itself configured correctly — then come back and wire memory the durable way.

*Images: Pexels.*
