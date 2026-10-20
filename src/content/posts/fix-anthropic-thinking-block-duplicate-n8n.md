---
title: "Fix Anthropic 'Invalid signature in thinking block' 400 Error in n8n AI Agent (GH #41152)"
description: "n8n AI Agent fails with 400 Invalid signature in thinking block only when Claude makes parallel tool calls. Root cause + 4 verified fixes."
date: 2026-10-20
category: automation
tags: ["n8n", "anthropic", "ai-agent", "error-fix", "claude"]
draft: false
featured: false
image: "/og/fix-anthropic-thinking-block-duplicate-n8n.webp"
---

Your support-ticket agent runs fine all morning, then randomly throws `Bad request - please check your parameters` on the AI Agent node. No credentials expired, nothing changed in the workflow, and re-running the same prompt sometimes works. Underneath that generic message, Anthropic returned a very specific 400:

```
400 {"type":"error","error":{"type":"invalid_request_error","message":"messages.1.content.3:
Invalid `signature` in `thinking` block. The block is bound to a different conversation."}}
```

I traced this to a real bug in n8n's AI Agent node (Tools Agent V3), reported as [n8n GitHub issue #41152](https://github.com/n8n-io/n8n/issues/41152) on 2026-10-15 and verified against the n8n source on master by the reporter. **It only fires when Claude returns one thinking block followed by two or more `tool_use` blocks in the same turn** — i.e. parallel tool calls. Turns with a single tool call work fine, which is exactly why it looks intermittent: it depends on the model's choice, not your config. The issue's reporter hit it 5 times in ~24 hours on a production support-ticket agent.

By the end of this article you'll know exactly why it happens, how to confirm it's your bug in under a minute, and the four fixes that actually work — ordered from quickest to most surgical.

Quick definitions before we start: a **thinking block** is Anthropic's extended-thinking artifact — the model's private chain-of-thought, returned as a structured `thinking` content block. Every thinking block carries a **signature**, a cryptographic seal Anthropic places on it that binds the block to the exact conversation prefix it was created under. If you replay the block under different content (for example, with extra tool calls inserted before it), Anthropic rejects the request. The **Tools Agent V3** (`typeVersion 3.1`) is the current n8n AI Agent implementation that rebuilds the chat history between agent turns.

**Prerequisites:** an n8n instance (verified on 2.42.7 as of October 2026; the mechanics apply to any 2.x running Tools Agent V3), an AI Agent node with an Anthropic Chat Model (Claude Sonnet 5 or Opus 5.x, with thinking enabled explicitly or — important — *unset*, which means adaptive thinking is on by default), and at least two tools attached to the agent.

## The symptom: what the failure actually looks like

The failure has three tell-tale fingerprints:

1. **The workflow:** Manual Trigger → AI Agent (Tools Agent) → Anthropic Chat Model (e.g. `claude-opus-5-5` or `claude-sonnet-5`), Thinking Mode either Adaptive or simply unset, with two independent tools attached (two HTTP Request Tools, or one MCP Client Tool exposing several tools).
2. **The trigger prompt:** anything that invites two lookups at once — the issue's example was *"Look up the user with email X AND search for similar tickets about Y, then summarise."* When the model answers with one thinking block plus two `tool_use` blocks, both tools execute, and the *next* Anthropic call fails with the 400 above.
3. **The n8n surface:** `NodeOperationError: Bad request - please check your parameters` on the AI Agent node, thrown from `ToolsAgent/V3/helpers/executeBatch.ts`. Your parameters are fine — this message is a red herring.

**How to confirm in one minute:** open the failed execution, click the Anthropic Chat Model node, and look at the *second* run (the one that failed). Inspect the input history. If you see the pattern `AI: [thinking][tool_use]` appearing **twice with the same signature**, then the history sent back to Anthropic looked like this:

```
Human: ...
AI:   [thinking(sig S), tool_use A]
Tool: result A
AI:   [thinking(sig S), tool_use B]      <- same signature S, replayed under a different prefix
Tool: result B
```

The issue's reporter confirmed exactly this: in every failing run, both actions in `subNodeExecutionData.actions[].action.metadata.anthropic` carried the identical `thinkingSignature`. If instead you only see one tool call per turn in your failing runs, this is not your bug — keep reading past the fixes anyway, because the prevention section covers related thinking-replay problems.

> **Note:** this bug is *new* in the sense that it's the next failure after a previous fix. Merged PR [#38302](https://github.com/n8n-io/n8n/pull/38302) ("Preserve Anthropic thinking blocks with empty text across tool calls") made empty-text thinking blocks survive the history round-trip. This report is what happens after that fix: the block survives, but it gets *duplicated*.

## The root cause: n8n copies one signature into every parallel tool call

The reporter verified this in the n8n source on master (commit `40094e3`, 2026-10-15). Here's the failure chain:

1. The model returns a single assistant turn shaped like `[thinking, tool_use A, tool_use B]`. The thinking block's signature is minted for *that exact turn*.
2. When the agent rebuilds history after the tools run, `createEngineRequests.ts` → `extractThinkingMetadata()` (line 43) copies the **same** `thinkingContent` and `thinkingSignature` into the metadata of **every** tool action of the batch. Both tool calls end up carrying an identical signature.
3. `buildSteps.ts` → `buildSteps()` (line 345) builds the conversation steps. For Gemini, there is a branch that detects parallel calls sharing a thought signature and merges them into one assistant message via `buildSharedGeminiAIMessage()` — the code comment above it describes *exactly this problem* ("Splitting into separate model turns invalidates the signature").
4. There is **no equivalent branch for Anthropic**. Each Anthropic tool call goes through `buildIndividualAIMessage()` → `buildAnthropicContentBlocks()`, which always returns `[thinkingBlock, toolUseBlock]` — one thinking block per tool call, each with the same signature.

So n8n replays the thinking block once per tool call, and the second copy sits after `tool_use A` and `result A` — content that did not exist when the signature was created. Anthropic's signature validation sees a block replayed under a different prefix and rejects the request. The Gemini path got the merge fix; the Anthropic path simply never did. As of the issue filing date there is no merged upstream fix — the workarounds below are the accepted solutions from the issue thread itself.

## The fixes

Decision table first, then steps:

| Fix | Effort | Thinking kept? | Best when |
|---|---|---|---|
| 1. Thinking Mode: Disabled | 1 click | No | You don't need chain-of-thought quality on this agent |
| 2. Sequential tool calls | Prompt edit | Yes | One agent does independent lookups; you can tolerate sequential latency |
| 3. Swap the chat model | 2 clicks | Depends | You're not married to Anthropic for this workflow |
| 4. Anthropic beta `drop_block` | Advanced | Partially | You call the API directly or can pass custom headers |

### Fix 1 - Set Thinking Mode to Disabled on the Anthropic Chat Model node

This is the fastest fix and the first workaround listed in the issue.

1. Open the **Anthropic Chat Model** sub-node on your AI Agent.
2. Find the **Thinking Mode** option and set it to **Disabled**.
3. Save and re-run the workflow with the same "two lookups at once" prompt.

**Why this works:** with thinking disabled there is no thinking block and therefore no signature to duplicate — the replay path can't break what doesn't exist. It also fixes the related default: since n8n 2.37.0 (via `@langchain/anthropic` 1.5.6), Claude Sonnet 5 and Opus 5 *think adaptively even when Thinking Mode is unset*, so "I never enabled thinking" does not protect you. Merged fix [#37954](https://github.com/n8n-io/n8n/pull/37954) ("Send disabled thinking to the provider") makes the Disabled setting actually reach the API — make sure your n8n includes it (any n8n updated after that fix landed, including the 2.42.x line, is fine).

> **Warning:** this is not available on models that cannot disable thinking. If your model enforces thinking, skip to Fix 2.

**Verify:** send the same prompt that triggered parallel tool calls. The agent should complete with no 400, and the execution input for the chat model node should show turns without any `thinking` blocks.

### Fix 2 - Keep the model to one tool call per turn

Also from the issue: *"Prompt it so that it only calls one tool per turn: works."*

Rephrase the system prompt to force sequential tool use, e.g.:

> You are a support assistant. When you need multiple pieces of information, request them strictly one at a time: call a tool, wait for its result, and only then decide whether to call another tool. Never call two tools in the same response.

**Why this works:** the duplication only happens when one turn contains two or more `tool_use` blocks. With one tool call per turn, the thinking signature is replayed exactly once under the correct prefix — the same reason single-tool turns already work today.

The trade-off is latency: two sequential tool calls take roughly twice as long as two parallel ones, and you're relying on the model to obey the instruction (in practice, explicit "one at a time" instructions are followed reliably on frontier models — but it's still a prompt, not a guarantee).

### Fix 3 - Use a different chat model node for this agent

The issue lists this as a workaround, and there is an interesting technical reason to prefer one specific alternative: **Gemini**. n8n's history builder already has `buildSharedGeminiAIMessage()`, which merges parallel tool calls sharing a thought signature into a single assistant message — the exact handling the Anthropic path is missing. So Gemini agents don't hit this bug at all. OpenAI chat models work too, since they don't use signed thinking blocks in this flow.

**When to use this:** if the agent's job doesn't specifically need Claude's strengths, swapping the sub-node is a two-click change with zero prompt or quality trade-offs on the thinking side.

### Fix 4 - (Advanced) Tell Anthropic to drop mismatched blocks

The error message itself names this escape hatch: set `thinking.block_binding.prefix_mismatch_behavior` to `"drop_block"`, which requires the `thinking-binding-controls-2026-08-01` value in the `anthropic-beta` header. When Anthropic sees the duplicated signature replayed under a wrong prefix, it drops the block instead of rejecting the request.

This is an API-level control — useful if you're calling the Anthropic API directly from an HTTP Request node or a Code node, not something you click into the Anthropic Chat Model node's options. If you do use it, **verify**: the request succeeds, but check the model's behavior — a dropped thinking block means the turn proceeds without the chain-of-thought it was built on, which can subtly change reasoning quality on that turn.

## What NOT to do

- **Don't chase "please check your parameters."** The `NodeOperationError: Bad request - please check your parameters` message points at your node config; the actual problem is the history n8n reconstructs. Editing credentials, remapping fields, or re-creating the agent node won't help.
- **Don't disable execution-data saving or tune execution settings.** Nothing about this failure involves the execution store — it's the conversation history payload sent to the Anthropic API.
- **Don't assume it won't recur because your last three runs worked.** The failure is model-choice-dependent: it only fires when Claude happens to emit parallel tool calls. A prompt that worked yesterday fails tomorrow on a different day with a different phrasing.

## Prevent it next time

1. **Treat parallel-tool-call agents on Claude as a known risk class.** Any AI Agent with an Anthropic Chat Model and 2+ independent tools can hit this until the upstream fix lands. Pick Fix 1, 2, or 3 as your default posture for new agents now, not after the first production failure.
2. **Watch [GH #41152](https://github.com/n8n-io/n8n/issues/41152) for the official fix.** The expected behavior per the issue: parallel Anthropic tool calls from one thinking turn should be replayed as a single assistant message `[thinking, tool_use A, tool_use B]`, mirroring what `buildSharedGeminiAIMessage()` already does for Gemini. When an n8n release closes this issue, upgrade and re-enable thinking.
3. **Know the neighboring bugs.** The same replay path in `buildSteps.ts` is implicated in two related open reports: [#40360](https://github.com/n8n-io/n8n/issues/40360) (thinking replay sends earlier tool calls back as `input: {}`) and the older [#37730](https://github.com/n8n-io/n8n/issues/37730) regression where Thinking Mode: Disabled stopped disabling thinking. If you see a *different* Anthropic 400 on this node, check those before assuming it's #41152.

## Key Takeaways

1. **The 400 fires only on parallel tool calls.** One thinking block + two `tool_use` blocks in a single turn is the trigger; single-tool turns never fail — that's why it looks intermittent.
2. **n8n duplicates the thinking signature across every parallel tool call**, but only Gemini's replay path merges them. The Anthropic path in `buildSteps.ts` has no equivalent, so the second copy is replayed under a different conversation prefix and Anthropic rejects it.
3. **Fastest fix: Thinking Mode: Disabled** on the Anthropic Chat Model node (effective since fix #37954); also prompt for one tool call per turn, or swap to Gemini/OpenAI.
4. **"Bad request - please check your parameters" is a red herring** — confirm the real cause by checking the failed execution's chat-model input for `[thinking][tool_use]` repeated with the same signature.
5. **This is a known upstream bug (GH #41152) with no merged fix yet** — treat Claude agents with multiple independent tools as a risk class and design around it until the release notes say otherwise.

Next: open your highest-traffic AI Agent that uses an Anthropic model with 2+ tools, reproduce the "two lookups at once" prompt in a manual execution, and check the chat-model input. If you see the duplicated signature, apply Fix 1 or 2 today — the five-failures-in-24-hours pattern from the issue is exactly how this starts in production.

## FAQ

### Why does the same workflow fail sometimes and succeed other times?

The failure depends on the model's choice in each run, not your workflow. Claude emits a thinking block followed by *one* `tool_use` on some turns and *two or more* on others. Only the parallel-tool-call turns trigger the duplicate-signature rejection. Same prompt, different day, different tool-call pattern — that's the intermittence.

### If I never enabled thinking, how am I affected?

Since n8n 2.37.0 (via `@langchain/anthropic` 1.5.6), Claude Sonnet 5 and Opus 5 think *adaptively by default* when Thinking Mode is unset — no explicit opt-in required. Check your Anthropic Chat Model node: if Thinking Mode is unset on one of these models, thinking is on.

### Will disabling thinking hurt my agent's quality?

It depends on the task. For lookup-and-summarise agents (fetch two records, summarise), disabling thinking typically costs little — the model still has full tool outputs to work with. For multi-step reasoning agents, expect some degradation. That's what Fix 2 (sequential tool calls, thinking kept) is for.

### Is Gemini affected by the same bug?

No — n8n's `buildSteps.ts` already merges parallel calls sharing a thought signature into one assistant message for Gemini (`buildSharedGeminiAIMessage()`). The issue explicitly notes the comment above that code describes exactly this signature problem. The Anthropic branch just never got the same handling.

### Where is this tracked upstream?

[n8n-io/n8n issue #41152](https://github.com/n8n-io/n8n/issues/41152), filed 2026-10-15, verified against master source at commit `40094e3`, reproduced on 2.42.7. Related: open [#40360](https://github.com/n8n-io/n8n/issues/40360) on the same replay path, merged [#38302](https://github.com/n8n-io/n8n/pull/38302) which made thinking blocks survive the round-trip in the first place.
