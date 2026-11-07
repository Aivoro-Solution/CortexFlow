---
title: "Fix n8n AI Agent Memory Errors: 'role tool' 400s, Replayed Tool Calls, and Amnesia Between Runs (5 Fixes)"
description: "n8n AI Agent failing with 'role tool' 400s, replaying old tool calls, or forgetting everything between runs? Five verified fixes that work."
date: 2026-11-07
category: automation
tags: ["n8n", "AI agent", "memory", "error fix", "Postgres"]
draft: false
featured: false
image: "/og/fix-n8n-ai-agent-memory-errors.webp"
---

Memory is the part of n8n's AI Agent that fails in the most confusing ways. The agent works fine for one or two turns, then the run dies with a 400 error that blames your parameters. Or it starts repeating tool calls from three messages ago. Or it wakes up on Monday with no idea what it learned on Friday — even though you attached Postgres Chat Memory specifically so it would remember. Each of these is a different bug, in a different layer, and the error messages point at none of them.

I collected the five memory failures that keep recurring in the n8n community, with the exact error text, the root cause, and the fix that other users confirmed works. By the end you will know which failure you have, the one setting to change for each, and how to verify the agent actually remembers the right things. All fixes below are verified against community reports, as of November 2026.

**Prerequisites:** a self-hosted or Cloud n8n instance with an AI Agent node (Tools Agent) and a chat model connected, plus a memory node — Postgres Chat Memory, Redis Chat Memory, Window Buffer Memory, or Simple Memory. If you run queue mode, note that Simple Memory does not follow executions across workers; use Postgres or Redis memory in production.

## The symptom map — which memory error do you have?

| Error you see | When it happens | Root cause |
|---|---|---|
| `Bad request - please check your parameters. Invalid parameter: messages with role 'tool' must be a response to a preceding message with 'tool_calls'` | Turn 2–3 of a chat, after upgrading to n8n 2.30.0 | Postgres/MongoDB memory replays a context-window slice that starts on a tool row, cutting off the assistant message that carried the `tool_calls` |
| Agent repeats old tool calls from previous messages, even when they are irrelevant now | Memory enabled; never happens with memory disabled | The memory buffer stores tool-call history, and the model imitates what it sees in context |
| Agent cannot recall what its own tools did — "which messages did I send?" | Any run where the agent used tools in earlier turns | Tool usages (intermediate steps) are never written into chat memory at all |
| Scheduled agent wakes up blank every run, despite Postgres Chat Memory | Scheduled/triggered runs, not chat | The default session key is the execution ID, so every run invents a brand-new session |
| Agent stops calling tools after 2–3 requests and starts hallucinating answers | Postgres memory enabled, multi-turn chat | The replayed history grows until the model stops invoking tools and invents responses instead |

## Fix 1 — The "role 'tool'" 400 error: upgrade first, then take memory manual

This is the sharpest failure. A user on n8n 2.30.0 (self-hosted) with an Azure OpenAI Chat Model (gpt-4o), an AI Agent node with several custom HTTP Request tools, and Postgres Chat Memory reported that the workflow worked, then crashed the moment they upgraded to 2.30.0:

```
Bad request - please check your parameters. Invalid parameter:
messages with role 'tool' must be a response to a preceding message with 'tool_calls'.
```

The same crash happened after migrating to a freshly configured Postgres Chat Memory instance, so it is not a corrupt table. And swapping in the built-in Simple Memory node made the error disappear — which proves the memory node, not the model or the tools, is the trigger.

The root cause is how the persistent memory nodes store history. Postgres and MongoDB Chat Memory write the agent's tool-call and tool-result messages into the table as their own rows. On the next turn, the memory node's **Context Window Length** replays a slice of those rows. Once that slice starts on a tool row, the assistant message carrying the matching `tool_calls` is no longer in front of it — and the provider rejects the payload because a `tool`-role message now has no preceding `tool_calls` to answer. That is why a fresh session survives the first turn and fails two or three turns later: the window only slides onto a tool row once enough history has accumulated.

**Step 1 — Upgrade n8n and re-test.** An n8n team member replied on the thread that the issue may already be fixed in a recent release, so check your version first. If you are on 2.30.0, upgrade to the latest stable and run the same three-turn conversation again. If the error is gone, you are done — do not rebuild your memory setup for a bug that is already patched.

**Step 2 — Confirm the diagnosis with Simple Memory.** If the error survives the upgrade, swap the Postgres Chat Memory node for Simple Memory and run the same conversation. If it passes, the diagnosis is confirmed: the persistent memory rows are the problem.

> **Warning:** Simple Memory stores conversations in active RAM. It is a diagnostic tool here, not a production fix — it does not persist across restarts, and in queue mode n8n cannot guarantee every call reaches the same worker. Do not ship it as the fix.

**Step 3 — Take memory manual with the Chat Memory Manager.** The workaround the community verified keeps Postgres as the store but stops letting the agent replay raw tool rows. Disconnect the Postgres Chat Memory node from the AI Agent's memory input, and instead:

1. Place a **Chat Memory Manager** node *before* the agent, connected to the same Postgres Chat Memory node. Set Operation Mode to `Get Many Messages` and turn **Simplify Output** on. Feed the returned list into the agent's prompt as the earlier conversation.
2. After the agent, add a second **Chat Memory Manager** on the same Postgres Chat Memory node. Set Operation Mode to `Insert Messages` and Insert Mode to `Insert Messages`, with one `User` message holding the chat input and one `AI` message holding the agent output.

The table then only holds user and AI rows, so there is no tool row left to replay — and the 400 cannot happen. You lose automatic tool-history replay, which is exactly the point: the replay was the bug.

**You should see:** the same three-turn conversation that crashed now completes, and the agent's replies still reference earlier turns, because the user/AI history is still there — only the tool rows are gone.

## Fix 2 — Stop the agent replaying old tool calls from memory

A different failure, same layer. With Simple Memory or Postgres Chat Memory enabled, an agent with a Qdrant vector-store tool sometimes repeats old Qdrant tool calls from previous messages — even when they have nothing to do with the current user input. Disable memory and it never happens. The buffer stores not just human and AI messages but the tool-call history too, and when the model sees old tool calls in context it imitates them instead of generating a fresh one.

**Step 1 — Shrink the window to prove it.** The memory node's `contextWindowLength` counts turns, and each turn is a human message plus an AI message *plus all tool-call history from those turns*. A window of 3 holds 6 messages and every tool call inside them — close enough that the model treats the old calls as instructions. Drop `contextWindowLength` to `1` as a test. If the repeating stops, the window size is the culprit; raise it back one step at a time until the behaviour returns, then settle one below that.

**Step 2 — Strip tool entries from what gets replayed.** If a small window is not enough, use the **Chat Memory Manager** node's delete-messages operation to strip tool-call entries from the stored history, so only human and AI messages are replayed. This is the same manual-memory pattern as Fix 1, applied to the replay side.

**Step 3 — Remove memory from sub-agents.** Memory does not need to persist between multiple agents. If your workflow has sub-agents, remove the memory node from them — a sub-agent replaying the parent's tool calls is a common source of repeats.

**Step 4 — Check the tool definitions.** Two small-model gotchas from the same thread: keep the Qdrant tool's **description in English** even if the rest of the workflow is in another language (small models such as qwen2.5:7b have much weaker instruction-following in non-English languages and may ignore the tool entirely), and make sure the tool's **Tool Name** field is filled in — some models silently skip tools with empty names or descriptions.

## Fix 3 — Give the agent a memory of what its own tools did

This one is a design gap, not a crash, and it is the most-commented AI-agent issue in n8n's tracker (GitHub #14361). An agent uses a tool — say a "contact buyer" node that sends a message to a user — and the action is never recorded in Postgres memory. Next turn the agent cannot recall which messages it already sent, so it sends them again or contradicts itself. The tool calls and their results are intermediate steps, and the memory nodes only store the human/AI transcript.

**Step 1 — Turn on "Return Intermediate Steps".** On the AI Agent node, enable the **Return Intermediate Steps** option. The tool outputs are then included in the agent node's output, so you can extract them downstream instead of them vanishing.

**Step 2 — Insert the tool results into memory yourself.** Add a **Chat Memory Manager** node after the agent and use it to insert the extracted tool result into the chat memory for that session. Users on the thread confirmed this works.

**The honest caveat:** there is no way to insert a tool result with the `tool` role — you have to insert it as an AI message or a System message, and both change behaviour compared with how the LLM providers intend tool results to be stored (as their own entries in the chat history). One user on the thread reported the technique "works quite poorly" for exactly this reason. Treat this as a working patch, not a clean fix: keep the inserted summary short (what the tool did and its result, not the raw payload) and prefer it for facts the agent must not repeat, like "message already sent to buyer X".

## Fix 4 — Stop the between-run amnesia: pin a stable session key

This is the failure that makes people conclude Postgres Chat Memory "doesn't work". You attach Postgres Chat Memory to a scheduled agent, it runs all week, and on Monday the weekly summary reads like a stranger wrote it. The table is full of history. None of it is reachable.

Every memory node stores history under a **Session ID** (also called the session key). Same key, same bucket; different key, strangers. The default session key is the **execution ID** — unique per run. Monday's run writes under Monday's execution ID, Tuesday's run asks for Tuesday's execution ID, finds nothing, and starts blank. The Postgres table fills up with hundreds of conversations, each one orphaned, each one unreachable from the next run.

**The fix is one setting.** Open the memory node and change the session key from the default to a stable value:

- For a single-purpose scheduled workflow, a constant such as `weekly-summary-agent` or the workflow name.
- For a chatbot, a per-user expression such as `{{ $json.customerId }}` or `{{ $json.email }}` — the value that identifies the person, not the run.

**You should see:** the next scheduled run's prompt now includes the previous runs' history, and the agent's output starts referencing decisions from earlier in the week.

> **Warning:** the same setting is also a privacy trap in the other direction. If the session key is a fixed default value shared by every user, every conversation pours into one bucket and your support bot will happily tell one customer about another customer's orders. A per-user key is not optional for multi-user bots — it is the fix for both the amnesia and the leak.

Two more things the key does not fix: memory nodes store transcripts, not knowledge. Even with the right key, the agent re-reads raw back-and-forth chat on every run — 400 lines of last month's debugging chatter do not make a better weekly report. For facts that must survive (preferences, decisions, mistakes already paid for), write them to a facts table at the end of each run and load the relevant rows into the prompt at the start of the next one. And remember that a large context window is working space for one run, not persistence — the window still empties when the run ends.

## Fix 5 — Agent stops calling tools after 2–3 requests

The last failure in the cluster: with Postgres Chat Memory connected, everything works without memory, but with memory the agent remembers the first two clarifications, then from the third request onward it stops invoking tools and generates fictional responses instead. The user who reported it traced it to the memory replay itself — the history grows until the model stops treating the tools as available and hallucinates.

**Step 1 — Isolate it.** Run the same conversation twice: once with memory connected, once without. If the tool calls stop only with memory on, the memory replay is the cause, not the model or the tools.

**Step 2 — Shrink the window and simplify the history.** Apply Fix 2's window reduction first — a smaller `contextWindowLength` is the cheapest test — and consider the Fix 1 manual-memory pattern so only user and AI messages are replayed.

**Step 3 — Try the community-built agent.** The reporter of this issue confirmed that installing the **n8n-nodes-better-ai-agent** community node ("Better AI Agent") fixed it: all 10 iterations then accessed memory and called tools correctly, with Simple, Redis, and Postgres memory alike. Treat this as a community workaround, not an official fix — vet any community node before it touches production, using the same checks as for any install: pin the version, back up first, and know how to uninstall it cleanly (see [Fix n8n Community Node Install Errors](/blog/fix-n8n-community-node-install-errors/)).

## Verify it worked

Run this five-minute check after applying the fixes:

1. Start a fresh session and run **at least three turns** that each call a tool — the 400 in Fix 1 only appears once the window slides onto a tool row.
2. Ask the agent what its tools did two turns ago. If it answers from memory instead of guessing, Fix 3 is working.
3. Trigger the scheduled workflow twice and confirm the second run references the first run's output — that is Fix 4.
4. Query the Postgres memory table directly and check the rows for the session: user and AI rows only, no orphaned sessions under random execution IDs.

If you use OpenAI models, one more signal is worth watching: a separate community report found the Tools Agent flattens the entire Postgres history into a single system-message string before sending it to the API, which kills prompt caching — a user with an 8–9k-token system prompt measured a 2% cache hit rate. There is no supported setting that changes this today; the manual Chat Memory Manager pattern from Fix 1 is the workaround that sidesteps it too.

## Prevent it next time

- **Cap the window on purpose.** Window Buffer Memory defaults to 5 exchanges; that is barely a greeting for a real conversation, and a large window is a large bill — every replayed message is re-sent to the model on every turn. Pick the smallest window that still answers follow-ups.
- **One session key per user, one key per scheduled job.** Never leave the execution-ID default on a scheduled workflow, and never share one fixed key across users.
- **No memory on sub-agents.** Only the top-level agent needs history; sub-agents replaying it is a bug source, not a feature.
- **Upgrade before you rebuild.** The tool-role 400 was reported against 2.30.0 and the n8n team indicated a fix in a recent release. Re-test on the latest stable before restructuring your memory setup.
- **Watch the provider's cache metrics**, not just the agent's answers. A cache hit rate collapsing toward zero is an early warning that history is being flattened into the prompt.

## What I did not test

I did not reproduce the Claude 4.5 + Postgres memory failure reported in GitHub #20335 ("Empty AI Message") in a live instance, so it is not one of the five fixes above — if you hit it, the same isolation test (Simple Memory vs Postgres) will tell you whether the memory backend is involved. I also did not test the manual Chat Memory Manager pattern against MongoDB Chat Memory; the 400 report covers Postgres and MongoDB, but the workaround steps were confirmed on Postgres. And the Better AI Agent community node is a user-reported workaround for one thread, not an n8n-endorsed replacement — if it stops working on a future n8n version, fall back to the window and manual-memory fixes.

## FAQ

### Is Postgres Chat Memory broken?

No. It stores transcripts faithfully — the problem is what gets replayed from the table, and under which session key. The 400 error comes from the window slice starting on a tool row; the amnesia comes from the execution-ID session key. Both are fixable without abandoning Postgres.

### Which memory node should I use in production?

Postgres Chat Memory if you want memory you can query, back up, and audit; Redis Chat Memory if you run queue mode and need workers to share it. Simple Memory is for testing only — it does not survive restarts and does not follow executions across workers in queue mode. Window Buffer Memory is the practical middle ground for a single-instance chatbot: the last N exchanges, persisted in n8n's internal store.

### Why does my agent remember other users' conversations?

Every user is sharing one session key. Bind the key to a per-user value — a chat ID, a sender ID, an email — so each user gets their own bucket.

### My agent worked yesterday and now fails on turn 3 with a 400. What changed?

Probably your n8n version (2.30.0 introduced the tool-role replay failure for some Azure OpenAI setups) or your history simply grew long enough for the window to slide onto a tool row. Upgrade first, then apply Fix 1.

## Key Takeaways

1. **The "role 'tool'" 400 is a replay bug, not a parameter bug** — Postgres/MongoDB memory replays a window slice that can start on a tool row; upgrade n8n first, then take memory manual with the Chat Memory Manager if it persists.
2. **Memory stores tool calls too, and the model imitates them** — shrink `contextWindowLength` to 1 to prove it, then strip tool entries from what gets replayed.
3. **Tool usages are never stored in memory** — enable Return Intermediate Steps and insert the results yourself with the Chat Memory Manager, keeping the inserted summary short.
4. **The default session key is the execution ID** — every scheduled run invents a new session. Pin a stable key per job, or a per-user key for chatbots.
5. **A small window and manual memory beat a big one** — cap the window, keep memory off sub-agents, and watch prompt-cache hit rate as an early warning.

Next: if your agent's *tools* are the thing failing rather than its memory, read [Fix n8n AI Agent Stopping When a Tool Fails or Returns Empty](/blog/fix-n8n-ai-agent-tool-fail-stop/) — the two failure modes look identical in the execution log, and the fix is on the tool side, not the memory side.
