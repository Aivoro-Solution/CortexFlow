---
title: "Fix n8n AI Agent Stopping When a Tool Fails or Returns Empty (5 Fixes)"
description: "Your n8n AI Agent dies the moment one tool fails or returns nothing. Real cause: the agent treats tool errors as fatal. 5 verified fixes that let it recover."
date: 2026-11-07
category: automation
tags: ["n8n", "ai-agent", "error-fix", "tools", "troubleshooting"]
draft: false
featured: false
image: "/og/fix-n8n-ai-agent-tool-fail-stop.webp"
---

Your AI Agent called three tools, the third one returned nothing, and the entire workflow stopped. No error output, no fallback message, no second chance — the run just died. Or worse: the run finished green, but the answer was empty, because the agent's final output was a tool's blank result instead of the model's reply.

This is the most confusing failure mode in n8n's AI Agent node, because the execution log looks innocent. The tool ran. The model reasoned. And yet the workflow is dead or the answer is blank. By the end of this guide you will know exactly which of the five known failure modes you are hitting, and the verified fix for each — all sourced from the n8n community forum and the n8n issue tracker.

**Prerequisites**

- n8n 2.x self-hosted or Cloud with an AI Agent node (Tools Agent, version 2.2 or 3.x) and at least one connected tool.
- Access to the workflow canvas (to change node settings) and the Executions list (to read what actually happened).
- The failure modes below are current as of November 2026; the upstream GitHub issues were still open when this was written, so treat the fixes as workarounds, not permanent cures.

## The symptom checklist

Before changing anything, match your failure to one of these five. They look similar from the outside but have different fixes.

1. **The agent stops dead when a tool fails.** One tool throws or returns no result and the whole execution ends. The agent never says "I couldn't find anything" — it just stops. Reported in [community thread 297687](https://community.n8n.io/t/ai-agent-stop-when-tool-fail/297687).
2. **"Received tool input did not match expected schema."** The agent calls the wrong tool, or passes five inputs to a tool that accepts one, and the run fails with a schema error — even though the tool is visibly connected on the canvas. Reported in [community thread 290395](https://community.n8n.io/t/agent-not-using-correct-tools-and-sending-wrong-mismatched-inputs/290395).
3. **The run succeeds but the reply is empty.** The model generated a correct answer, then a memory or bookkeeping tool ran after it, and the workflow received that tool's empty output as the final result. Reported in [community thread 224901](https://community.n8n.io/t/n8n-agent-returns-the-second-tool-output-instead-of-the-actual-llm-response-empty-reply-problem/224901).
4. **"The Tool attempted to return an engine request, which is not supported in Agents."** Sub-agent tools fail on the first tool call in Tools Agent V3, while the same setup works on V2. Reported in [community thread 269658](https://community.n8n.io/t/error-the-tool-attempted-to-return-an-engine-request-which-is-not-supported-in-agents/269658).
5. **The agent loops or replays a tool call forever.** The agent repeats the same tool call with empty arguments, or a retry resets the whole agent context — one documented case ran 11 consecutive reset cycles and 105 tool calls for a task that needed a fraction of that. Documented in [GitHub issue #37779](https://github.com/n8n-io/n8n/issues/37779) (`retryOnFail` wiping the agent's suspend/resume context).

If none of these match — for example the agent fails only with Anthropic thinking models — see the related fix at the end: [Fix Anthropic "Invalid signature in thinking block" 400 Error](/blog/fix-anthropic-thinking-block-duplicate-n8n/).

## The real root cause (not what the error says)

n8n's error handling is node-level, not job-level. Each node knows how to retry itself or fail. The AI Agent node is different: it runs a loop — model reasons, model calls a tool, tool result comes back as an observation, model reasons again. When a tool throws, that observation never arrives. The agent loop has no observation to reason about, so it has nothing to do next — and the execution ends.

That is why the standard advice fails here. Setting "Continue on Fail" on the AI Agent node itself does not help, because the crash happens inside the tool, not in the agent. And the execution can still report success while the answer is wrong: a tool that returns an empty result is not an error to n8n, so nothing throws — the model just fills the gap with a confident guess, or the empty tool output becomes the final answer.

The upstream bugs behind this are tracked, not fixed: [GitHub #38870](https://github.com/n8n-io/n8n/issues/38870) (tool responses intermittently return empty even though the tool executed), [#38503](https://github.com/n8n-io/n8n/issues/38503) (AI Agent V3 loses canonical tool names and silently drops the next tool call), [#24042](https://github.com/n8n-io/n8n/issues/24042) (tool node errors fail the workflow instead of returning the error to the agent), [#37916](https://github.com/n8n-io/n8n/issues/37916) (a schema-invalid tool call terminates the whole execution), and [#40360](https://github.com/n8n-io/n8n/issues/40360) (Anthropic thinking replay sends earlier tool calls back as `input: {}`). Until those ship fixes, the workarounds below are the fix.

## Fix 1 - Let the tool fail gracefully with "Continue (Using Error Output)"

This is the first fix to apply, and it solves symptom 1 directly. Open the tool node that fails — not the AI Agent node, the tool itself — go to its **Settings** tab, and set **On Error** to **Continue (Using Error Output)**.

What this changes: when the tool throws, n8n routes the error into the tool's error output instead of killing the execution. The AI Agent receives the error as the tool's observation, so the model can do what a human would do: say it failed, try a different tool, or ask for the missing input. The workflow keeps running.

```text
Tool node (e.g. HTTP Request, Google Sheets, Code)
  → Settings tab
  → On Error: Continue (Using Error Output)
```

**Verify it:** force the tool to fail once — a bad credential, a wrong URL, a query that returns nothing — and run the workflow. The execution should complete, and the agent's reply should mention the failed tool instead of the run dying.

> **Warning:** once the tool continues on error, the failure becomes invisible. The agent routes around it, the run finishes green, and you never know that tool has been failing every time. Fix the underlying input or auth problem too — a tool that fails on every run is usually a bad input, not a flaky service. Add a notification (Slack, Telegram, or an error workflow) on repeated tool errors so silent failures don't stay silent.

## Fix 2 - Wrap the tool in a "Call n8n Workflow" sub-workflow

When Fix 1 is not enough — the tool is a chain of nodes, or the failure happens two steps deep — move the tool's logic into a separate sub-workflow and call it with the **Call n8n Workflow** tool.

Inside the sub-workflow, set **Continue on Fail** on the specific nodes that are glitchy. The sub-workflow can also normalise its own output: always return a structured object like `{"success": true, "data": ...}` or `{"success": false, "error": "...", "suggestion": "..."}`. Then add one line to the agent's system prompt:

```text
If a tool returns success: false, do NOT stop the workflow.
Read the error and suggestion fields and continue with the next step.
```

Why this works when Fix 1 doesn't: the error handling now lives inside a workflow you control, at the exact node that fails, instead of at the agent's tool boundary. The agent only ever sees a clean, structured result — success or a described failure — never a raw exception. This is the most reliable pattern in production, and the one the community thread's accepted answers converge on.

**Verify it:** run the agent with the sub-workflow's inner node forced to fail. The agent should receive `success: false` as an observation and keep going.

## Fix 3 - Turn off retryOnFail on the AI Agent node

Open the AI Agent node, go to **Settings**, and make sure **Retry on Fail** is off. This sounds backwards — retries are supposed to help flaky calls — but on the AI Agent node a retry does not replay the model's decision. It restarts the agent from scratch without the tool-call history it had accumulated.

The result is the loop from symptom 5: the agent hits its iteration limit, the node retries, the context resets, the agent redoes the same tool calls, hits the limit again. One report in the issue tracker shows 11 consecutive reset cycles and 105 tool calls for a task that should have needed a fraction of that. Worse, the retry can produce a plausible-looking answer stitched from stale reasoning and fresh tool data — a corrupted trajectory that looks like success.

**The rule: node retries are for transient 503s from a third-party API. They are not job retries.** If a whole agent run fails, retry the run from the trigger (or from your queue), not the node. Let the agent node fail fast and expose the failure.

**Verify it:** check the Executions list for a failed agent run — you should see one execution with one attempt, not a chain of identical re-runs.

## Fix 4 - Delete and recreate the tool node to re-register its schema

Symptom 2 — "Received tool input did not match expected schema" — is not a prompt problem. When you first connect a tool to the agent, n8n stores the tool's input schema (the parameters it accepts) inside the agent's configuration. The visual connection on the canvas and that internal config are two separate things. The schema can get lost or corrupted, so the agent no longer sees the tool as usable — then it grabs the next closest tool and tries to pass all the gathered inputs to it, which only accepts one parameter. No amount of prompt rewriting fixes a tool that isn't properly registered.

The fix is mechanical:

1. Delete the tool node from the canvas.
2. Add a fresh copy of the same tool node.
3. Reconnect it to the AI Agent node.
4. Re-enter its parameters and description — make the description extremely explicit about when to call it and what it returns, for example: "Call this tool when the user asks about contracts. It returns the contract status and renewal date."

Also add the trigger to the agent's system prompt: "You MUST call [tool name] for [specific trigger]."

**Verify it:** ask the agent the exact question that failed before. It should now call the correct tool with the correct inputs. If it still calls the wrong tool, the description is too vague — the description is what the agent uses to decide when to call a tool.

## Fix 5 - Downgrade the AI Agent node to v2.2 (last resort)

If the failures started after upgrading the agent to V3, and Fixes 1–4 don't stop them, downgrade the AI Agent node back to version 2.2. In the node panel, change the version from `3.1` (or `3.x`) to `2.2`. Version 2.2 runs the tool loop inline, so a tool failure or empty result does not kill the agent the way the V3 engine boundary does.

This is also the workaround for symptom 4 ("engine request, which is not supported in Agents"): V3's `agentTool` boundary fires an engine request on the first tool-call decision, before the tool itself runs. V2 does not have that boundary, so the same sub-agent tools work there.

> **Warning:** downgrading is a holding pattern, not a solution. You lose V3 features, and n8n will eventually remove V2. Use it to unblock production today, and re-test V3 on every n8n upgrade until the upstream issues (#38503, #38870, #24042) are closed.

**Verify it:** run the same failing prompt on V2.2. The agent should keep running when a tool fails or returns nothing.

## Fix the empty final reply: pull the model's output, not the last tool's

Symptom 3 has a different shape from the others, so it gets its own fix. The agent returns the **last tool's output** as its final result. If the last thing that ran was a memory tool like Simple Memory's `saveContext` — which returns no text — the workflow receives an empty message, even though the model generated the correct response one step earlier.

Add a **Set** node immediately after the AI Agent node and map the agent's response field into your output:

```text
Set node after AI Agent:
  message = {{ $json.output }}
```

This pins the downstream value to the model's actual reply instead of whatever the last tool returned. If your agent version exposes the field under a different name, open a successful execution and check the agent node's output JSON — use the field that holds the model's text.

**Verify it:** run a prompt that triggers the memory tool, then inspect the Set node's output. The message should be the model's answer, not an empty object.

## Prevent it next time

- **Give every tool a structured contract.** Tools should return `success` plus either `data` or `error`/`suggestion` — never a bare empty result. An empty result is the hardest failure to debug because nothing throws.
- **Keep the system prompt lean.** Anthropic models silently drop tools when `systemMessage` is large ([GitHub #37840](https://github.com/n8n-io/n8n/issues/37840)). Put long instructions in a tool description or a sub-workflow, not the system prompt.
- **One tool call per turn for Anthropic thinking models.** Parallel tool calls with thinking enabled can duplicate thinking signatures and produce 400 errors — see [Fix Anthropic "Invalid signature in thinking block" 400 Error](/blog/fix-anthropic-thinking-block-duplicate-n8n/). If you use thinking mode, set **Thinking Mode: Disabled** on the Anthropic Chat Model sub-node until [#40360](https://github.com/n8n-io/n8n/issues/40360) is fixed.
- **Alert on tool errors, don't just swallow them.** Fix 1 hides failures by design. Pair it with an error workflow or a counter so a tool failing 100 times a day still wakes someone up. The monitoring pattern is covered in our [AI Agent memory guide](/blog/n8n-ai-agent-memory-explained/)'s companion theme — a dead tool is a silent failure until you measure it.
- **Re-test V3 after every n8n upgrade.** The V3 bugs are tracked and team-assigned; each release may fix one. Keep a saved test execution (one prompt per tool) and replay it after upgrading before you touch production.

## FAQ

### Why does the agent stop instead of telling me the tool failed?

Because the tool's exception never becomes an observation. The agent loop waits for a tool result to reason about; when the tool throws, there is no result, so the loop has nothing to continue with and the execution ends. Fix 1 turns the exception into an observation, which is what the model needs to recover.

### Is "Continue (Using Error Output)" safe to leave on?

Yes, with one condition: you must also monitor it. The setting converts crashes into data, which is what you want — but it also means a permanently broken tool produces green runs forever. Add an alert on repeated tool errors.

### Should I use AI Agent V2 or V3?

Use V3 for new builds — it is the maintained path and the one receiving fixes. Downgrade to V2.2 only as a temporary workaround for the specific V3 tool-call bugs listed here, and re-test V3 on each upgrade.

### Does this affect n8n Cloud too, or only self-hosted?

Both. The failure modes are in the AI Agent node's tool loop, not in hosting. Self-hosted users see them slightly more because they upgrade (and hit regressions) on their own schedule.

## Key Takeaways

1. **The agent dies because a tool failure never becomes an observation** — set the tool node's On Error to Continue (Using Error Output) so the model can recover.
2. **Wrap flaky tools in a Call n8n Workflow sub-workflow** with Continue on Fail inside and a structured success/error return — the most reliable production pattern.
3. **Turn off retryOnFail on the AI Agent node** — retries reset the agent's context and can loop 100+ tool calls on a corrupted trajectory.
4. **"Received tool input did not match expected schema" means the tool's schema is corrupted in the agent config** — delete and recreate the tool node to re-register it.
5. **An empty final reply is the last tool's output, not the model's** — put a Set node after the agent and map the model's output field.

Next: if your agent also forgets things between turns, read [n8n AI Agent Memory Explained](/blog/n8n-ai-agent-memory-explained/) — memory failures and tool failures often arrive together, and the fixes complement each other.

*Sources: [n8n Community — AI Agent stop when tool fail](https://community.n8n.io/t/ai-agent-stop-when-tool-fail/297687) · [n8n Community — Agent not using correct tools](https://community.n8n.io/t/agent-not-using-correct-tools-and-sending-wrong-mismatched-inputs/290395) · [n8n Community — empty reply problem](https://community.n8n.io/t/n8n-agent-returns-the-second-tool-output-instead-of-the-actual-llm-response-empty-reply-problem/224901) · [n8n Community — engine request not supported in Agents](https://community.n8n.io/t/error-the-tool-attempted-to-return-an-engine-request-which-is-not-supported-in-agents/269658) · GitHub n8n-io/n8n [#37779](https://github.com/n8n-io/n8n/issues/37779), [#38503](https://github.com/n8n-io/n8n/issues/38503), [#38870](https://github.com/n8n-io/n8n/issues/38870), [#24042](https://github.com/n8n-io/n8n/issues/24042), [#37916](https://github.com/n8n-io/n8n/issues/37916), [#37840](https://github.com/n8n-io/n8n/issues/37840), [#40360](https://github.com/n8n-io/n8n/issues/40360).*
