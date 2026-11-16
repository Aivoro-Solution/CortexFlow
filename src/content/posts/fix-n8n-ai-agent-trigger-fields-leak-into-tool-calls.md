---
title: "Fix n8n AI Agent Leaking Chat Trigger Fields Into MCP Tool Calls (GH #43911)"
description: "Your n8n AI Agent calls an MCP tool and the server rejects a parameter nobody sent. The Chat Trigger's action field is leaking in — here's the fix."
date: 2026-11-16
category: automation
tags: ["n8n", "ai-agent", "mcp", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-ai-agent-trigger-fields-leak-into-tool-calls.webp"
---

Your AI Agent calls an MCP tool, the tool server rejects the call with a validation error naming a parameter the model never sent, and the tool node's Input panel agrees with the model: the parameter is not there. You re-run it. Same failure. The agent insists it did not pass the field, the panel shows it did not pass the field, and the server says it did.

This is a confirmed bug in n8n, filed as [GitHub issue #43911](https://github.com/n8n-io/n8n/issues/43911) on November 14, 2026 (team-assigned, Linear GHC-9763, still open as of November 15, 2026). n8n quietly merges your trigger's fields into every tool call the agent makes, and when a trigger field happens to share a name with a tool parameter, the trigger's value wins the collision. By the end of this article you will know how to confirm you have hit this exact bug, stop the leak with a one-node fix, and verify the tool server receives only what the model actually sent.

Quick definitions before we start: a **Chat Trigger** is the node that starts a workflow when a user sends a chat message — its output item carries `chatInput` (the message text), `sessionId` (the conversation), and `action: "sendMessage"`. An **AI Agent** is n8n's agent node: it reads the trigger item, picks tools, and calls them. The **MCP Client Tool** node connects the agent to an external MCP (Model Context Protocol) server — a standard way to expose tools to AI models — and each MCP tool declares an `inputSchema`, the list of parameters it accepts. A **tool call** is one invocation of a tool by the model, carrying the arguments the model chose.

## The symptom: the server rejects a parameter nobody sent

The failure looks like this. You have a Chat Trigger feeding an AI Agent, and the agent has an MCP Client Tool. The MCP tool has an optional parameter named `action` — in the reporter's real case, a `create_signing_session` tool whose `action` parameter expects an object. Every call from the agent fails with:

```
path: ["action"], Expected object, received string
```

The model correctly states it never sent `action`. The MCP Client node's Input panel — JSON view included — shows no `action` either. Yet the MCP server logs `action: "sendMessage"` arriving with every call.

**How to tell this bug apart from a bad prompt or a broken tool.** If the model actually sent the wrong value, the Input panel shows it. Here the panel and the wire disagree: the panel shows only the model's arguments, while the server receives an extra field. That disagreement is the fingerprint. If your MCP tool has no parameter named `action`, `sessionId`, or `chatInput` — the three fields a Chat Trigger item carries — you have a different problem, because the leak only survives when a trigger field's name matches a tool parameter's name.

## The root cause: the agent's input item is spread under the model's arguments

The reporter traced this to two code paths that combine into one silent collision.

First, when the agent dispatches a tool call, n8n builds the tool node's input by spreading the agent's own input item *underneath* the arguments the model produced. In `packages/core/src/execution-engine/requests-response.ts` (n8n-core 2.47.2):

```js
const agentInputData = executionData.data.main?.[0]?.[itemIndex];
const mergedJson = {
  ...(agentInputData?.json ?? {}),   // the trigger item: action, sessionId, chatInput, ...
  ...action.input,                   // the model's tool arguments
  toolCallId: action.id,
};
const displayJson = { ...action.input };   // what the tool node's Input panel shows
```

`mergedJson` becomes the tool node's real input item. `displayJson` — only the model's arguments — is what the Input panel renders. The panel never shows the trigger fields, so the leak is invisible in the editor.

Second, the MCP Client Tool filters that merged object against the tool's schema. In `@n8n/n8n-nodes-langchain` 2.47.3, `nodes/mcp/shared/runtime.ts`, `runToolCall` does:

```js
const sanitizedToolArguments = schema.additionalProperties !== true
  ? pick(toolArguments, Object.keys(schema.properties ?? {}))
  : toolArguments;
```

The filter keeps only keys that appear in the tool's `inputSchema`. A trigger field survives exactly when its name matches a tool parameter. Behind a Chat Trigger, `action: "sendMessage"` is a string, so any MCP tool with an `action` parameter that expects an object fails validation with `Expected object, received string`. The model's own arguments would have overridden the trigger value if it had sent one — the spread puts `action.input` second — but when the model omits the parameter, the trigger's value is what goes out.

**The blast radius is wider than `action`.** Any field of whatever trigger feeds the agent can collide with a same-named tool parameter: `sessionId` and `chatInput` from a Chat Trigger, or any field from any other trigger. And if a tool's schema sets `additionalProperties: true`, the filter is skipped entirely and *every* trigger field is sent to the server. Other tool types that read parameters from the input item may be affected too — the reporter only tested the MCP Client Tool. The issue's own words sum it up: spreading trigger items at the root of `mergedJson` while only rendering `displayJson` on the canvas makes this silent collision a nightmare to trace.

## Step 1 - Confirm the collision with an echo test

Before changing anything, prove the trigger field is the one arriving at the server. The reporter built a minimal MCP server — one tool, `echo(text: string, action?: string)`, that returns exactly the arguments it receives and logs each call — and pointed the agent at it. Ask the agent to call `echo` with only `text: "hello"`, then check what the server received.

If the server logs `{"text": "hello", "action": "sendMessage"}`, you have the bug: the `action` field came from the Chat Trigger, not the model. If the server receives only `{"text": "hello"}`, your failure is something else — check the tool's schema and the model's actual arguments first.

You can run the same check without a test server if your MCP server logs incoming calls: look for trigger-field names (`action`, `sessionId`, `chatInput`) in the logged arguments of a call where the model sent none of them.

## Step 2 - Strip the trigger fields before the agent (the verified fix)

Put an **Edit Fields (Set)** node between the Chat Trigger and the AI Agent, and keep only the two fields the agent actually needs: `chatInput` and `sessionId`. The reporter verified this with screenshots: with the Edit Fields node in place, its output carries only `chatInput` and `sessionId`, and the echo server receives exactly `{"text": "hello"}` — no `action`, no collision.

Configure the Edit Fields node like this:

- **Mode:** Manual Mapping
- **Fields to Set:**
  - `chatInput` — `{{ $json.chatInput }}`
  - `sessionId` — `{{ $json.sessionId }}`

Leave **Include Other Fields** off, so every other trigger field — including `action` — is dropped before the item ever reaches the agent. The agent only needs `chatInput` (the message) and `sessionId` (only if memory is attached, so the agent keeps the right conversation). With `action` gone from the agent's input item, there is nothing left to leak into the tool call.

> **Note:** if your agent prompt or any downstream expression reads other trigger fields — for example a custom field your trigger adds — add those fields to the Edit Fields node too, or the expressions will resolve to nothing. Only strip fields you have checked nothing else uses.

## Step 3 - Alternative: strip the field with a Code node

If you prefer code, or you only need to remove one colliding field, a Code node between the trigger and the agent does the same job. This variant was confirmed by n8n team member grinem in the issue thread:

```javascript
delete $input.item.json.action;
return $input.item;
```

The Code node deletes `action` from the trigger item in place and passes the rest through untouched. Use this when `action` is the only collision and you want the smallest possible change. Use the Edit Fields node from Step 2 when you want an explicit allowlist — it also protects you against a second collision you have not noticed yet, for example a tool parameter named `sessionId`.

## Step 4 - Verify the tool server receives only the model's arguments

Re-run the echo test from Step 1 with the fix in place, then run the real tool call:

1. Ask the agent to call the `echo` tool with only `text: "hello"`. The server should now receive exactly `{"text": "hello"}`.
2. Run the real workflow and confirm the MCP tool call succeeds — no more `Expected object, received string`.
3. Check the execution log: the tool node's Input panel still shows only the model's arguments, which is expected. The proof is on the server side, not in the panel — the panel never showed the leak in the first place.

If the call still fails, check two things. First, make sure the Edit Fields or Code node sits *between the trigger and the agent*, not after the agent — the merge happens when the agent dispatches the tool call, so the item must be clean before it reaches the agent. Second, check whether the tool call goes through a sub-workflow or a second agent whose input item still carries the trigger fields; each agent's input needs the same treatment.

## Prevent it next time: audit tool parameter names against trigger fields

The long-term fix belongs in n8n core — scoping tool arguments strictly to `action.input` instead of merging the trigger item underneath — and a regression test has been proposed that calls an MCP tool with an optional field matching a Chat Trigger field and asserts the server receives only the model arguments. Until that ships, treat the boundary between trigger and agent as a place where fields leak:

- **Name MCP tool parameters distinctly.** If you control the MCP server, avoid parameter names that collide with common trigger fields: `action`, `sessionId`, `chatInput`, `body`, `headers`, `query`. A parameter named `operation` or `signingAction` can never collide with a Chat Trigger field.
- **Keep an Edit Fields node after every trigger that feeds an agent.** Make it a habit, not a one-off: the allowlist costs one node and protects every tool the agent can call, including tools you add later.
- **Distrust the Input panel for this class of bug.** The panel shows `displayJson`, the model's arguments only. When a tool server rejects a field the panel says was never sent, look at what the server actually received — server-side logging of argument names is what cracked this case.
- **Watch the upstream fix.** The issue is team-assigned (Linear GHC-9763) with no fixed version as of November 15, 2026. When a release notes the fix, remove the strip node and re-run the echo test to confirm the leak is gone at the source.

## What this fix does not cover

This workaround stops the leak at the trigger-to-agent boundary, but it does not fix the underlying merge in `requests-response.ts`. A tool with `additionalProperties: true` still receives whatever the agent's input item contains — the Edit Fields allowlist handles that too, but only for the fields you chose to keep. And the same hidden-input mismatch may exist in other tool types that read parameters from the input item; the reporter only verified the MCP Client Tool. If you see a tool server receiving a field the model never sent and the Input panel shows nothing, check the trigger fields first — whatever the tool type.

Related but different: GitHub issue #36863 reports another MCP Client Tool failure that is likewise recorded as a successful execution with a message that does not name its cause. It is a separate bug, not this one.

## FAQ

### Why does the error say "Expected object, received string"?

The MCP tool's `action` parameter is declared as an object in its `inputSchema`, but the value it receives is the string `"sendMessage"` — the Chat Trigger's `action` field. The validation error is accurate about the value; it is misleading about the sender, because the sender is n8n's merge, not the model.

### Does this affect tools other than MCP tools?

Possibly. The merge happens for every tool call the agent dispatches, and any tool type that reads parameters from the input item can pick up a colliding trigger field. The reporter confirmed the MCP Client Tool; other tool types were not tested. If a non-MCP tool rejects a field the model never sent, apply the same Edit Fields fix and check whether it resolves it.

### Will removing `action` break the Chat Trigger's reply?

No. The Chat Trigger's `action: "sendMessage"` field describes what the trigger should do with the agent's reply; it is not needed by the agent itself. The agent needs `chatInput` to know what the user said and `sessionId` to keep the conversation in memory. Stripping `action` before the agent changes nothing about how the reply is delivered.

### Why doesn't the Input panel show the leaked field?

The panel renders `displayJson`, which is built from the model's arguments only. The actual input, `mergedJson`, includes the trigger fields spread underneath. The panel and the wire show two different objects, which is why this bug sends you looking everywhere except the real cause.

## Key Takeaways

1. **n8n merges the trigger item into every tool call the agent makes** — trigger fields sit underneath the model's arguments, and any field whose name matches a tool parameter is sent to the server.
2. **The Input panel hides the leak** — it shows only the model's arguments, so a server-side validation error naming a field nobody sent is the signature of this bug.
3. **An Edit Fields node keeping only `chatInput` and `sessionId` fixes it** — reporter-verified; the echo server then receives exactly what the model sent.
4. **A Code node (`delete $input.item.json.action`) is the minimal alternative** — team-confirmed, for when `action` is the only collision.
5. **Audit tool parameter names against trigger fields** — avoid `action`, `sessionId`, and `chatInput` as tool parameter names if you control the MCP server.

Next: if you run agents behind other triggers — Webhook, Form, Schedule — check what fields those triggers put on the item, and put the same Edit Fields allowlist in front of the agent. The leak is not specific to chat; it is specific to any trigger field that shares a name with a tool parameter.

*Sources: [GitHub issue #43911](https://github.com/n8n-io/n8n/issues/43911) (full issue text and comments read November 16, 2026; team-assigned, Linear GHC-9763, still open as of November 15, 2026; workaround verified by the reporter with screenshots and confirmed by n8n team member grinem).*
