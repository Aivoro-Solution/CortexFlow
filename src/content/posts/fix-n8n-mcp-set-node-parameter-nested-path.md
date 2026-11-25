---
title: "Fix n8n MCP setNodeParameter Silently Ignoring Nested-Path Edits"
description: "n8n's MCP setNodeParameter reports success on a nested-path edit but appends a duplicate parameters key, so the old value keeps running. Detect and repair it."
date: 2026-11-25
category: automation
tags: ["n8n", "error-fix", "mcp", "ai-agents", "workflows"]
draft: false
featured: false
image: "/og/fix-n8n-mcp-set-node-parameter-nested-path.webp"
---

You ask your AI assistant to change one line of a Code node through n8n's MCP server. The tool answers `appliedOperations: 1`, no warning, no error — and the workflow keeps running the old code. You re-read the workflow, the new value is right there in the response, and yet the next execution runs the old script. Nothing failed, nothing warned you, and the edit was a no-op from the start. The cause is a bug in the bundled n8n MCP server's `update_workflow` tool: a nested `setNodeParameter` path appends a second `parameters` key to the node instead of replacing the value, and JSON parsers keep the first key they see — the old one. By the end of this post you will know how to spot the duplicate, how to repair the node with the workaround that actually applies, and how to verify the edit took before you trust another execution.

## The symptom: the tool says success, the workflow runs the old code

The setup is n8n's bundled MCP server — the one that exposes workflow tools such as `update_workflow` and `get_workflow_details` to an AI client — pointed at a self-hosted instance. Take a workflow with a Code node whose `parameters.jsCode` is `"old"`, and call `update_workflow` with a nested JSON Pointer path:

```json
{
  "workflowId": "<id>",
  "operations": [
    { "type": "setNodeParameter", "nodeName": "My Code Node", "path": "/parameters/jsCode", "value": "new" }
  ]
}
```

The tool returns `appliedOperations: 1` and no warning. Read the workflow back with `get_workflow_details` and the node comes back carrying two `parameters` keys:

```json
{
  "parameters": { "jsCode": "old" },
  "parameters": { "jsCode": "new" }
}
```

Execute the workflow and it runs `"old"`. JSON parsers keep the first occurrence of a duplicate key, so the original value wins at parse time and the edit is silently ineffective. The tool's success response is the trap: there is no signal anywhere in the happy path that anything went wrong. The reporter hit this on a production notification hub — the edit looked applied, the workflow kept running the old code, and only a live execution revealed it.

This was reported in [GitHub issue #45022](https://github.com/n8n-io/n8n/issues/45022) (opened 2026-11-24, n8n `latest` Docker image, self-hosted, client DeepSeek Harness), status `in-linear`, still open as of 2026-11-25, with no pull request or fixed version yet — so the steps below are the fix for now. Note that the same class of bug shows up with a top-level path too: `setNodeParameter` with `/parameters/command` produced a nested `parameters.parameters.command` instead of replacing the value.

## The root cause: the path is assigned into a fresh object, not merged

MCP (Model Context Protocol) is the open standard that lets an AI client call tools exposed by a server — here, n8n's own server, which turns tool calls into workflow edits. The `update_workflow` tool applies each operation to the workflow JSON, and `setNodeParameter` takes a JSON Pointer path such as `/parameters/jsCode` and a new value.

Per the reporter's diagnosis in the issue, both failure shapes point at one root cause: the path is applied by assignment into a fresh object instead of merging into the existing node object. The nested path `/parameters/jsCode` creates a new `parameters` object containing the new value and attaches it to the node — alongside the original `parameters` object, which is never touched. The node ends up with two keys of the same name in one JSON object, which is technically malformed: the JSON specification says names in an object *should* be unique, and parsers resolve the collision by keeping the first. The old value is first, so the old value wins.

The top-level variant confirms the mechanism: `/parameters/command` does not replace the node's `command` parameter either — it nests a whole new `parameters` object *inside* the existing one, producing `parameters.parameters.command`. In both cases the edit lands somewhere the runtime never reads, while the tool reports it applied. There is no validation step that reads the node back and compares, so the silent no-op sails through.

## The fix: detect the duplicate, repair with a full replace, verify the edit

There is no setting that repairs this, and restarting n8n does not help — the duplicate key is already written into the saved workflow. The fix is to find every node the bad operation touched, repair it with the operation that replaces the whole `parameters` object, and verify the edit with a check that can actually see duplicate keys.

### Step 1 - Find every node carrying a duplicate `parameters` key

A normal JSON parse cannot see this bug: `JSON.parse` silently drops the second duplicate key, so reading the workflow through the n8n editor or a plain API call shows only the first (old) value — exactly what the runtime sees. You need a read that inspects the raw text. Pull the workflow JSON through the Public API (API key from Settings → n8n API) and scan it with a duplicate-key detector:

```bash
curl -s -H "X-N8N-API-KEY: <your-api-key>" \
  "https://<your-n8n-host>/api/v1/workflows/<workflow-id>" \
  -o /tmp/workflow.json
```

Then run a detector that keeps every key it sees instead of collapsing duplicates:

```python
import json

def pairs_hook(pairs):
    seen = {}
    dups = []
    obj = {}
    for k, v in pairs:
        if k in seen:
            dups.append(k)
        seen[k] = True
        obj[k] = v
    if dups:
        print("DUPLICATE KEYS:", dups)
    return obj

with open("/tmp/workflow.json") as f:
    json.load(f, object_pairs_hook=pairs_hook)
```

Replace `<your-n8n-host>` with your n8n host, `<your-api-key>` with an API key, and `<workflow-id>` with the workflow's id. If the script prints `DUPLICATE KEYS: ['parameters']`, the node is hit. If it prints nothing, that workflow is clean — check the other workflows the assistant edited the same way, because every nested-path `setNodeParameter` call on any node produces the same duplicate.

> **Note:** a quick `grep -c '"parameters"'` on the raw file is not a reliable check — a workflow legitimately contains the word `parameters` many times, once per node. The Python detector above reports only keys duplicated *inside the same object*, which is the actual defect.

### Step 2 - Repair the node with updateNodeParameters and replace: true

Do not re-run `setNodeParameter` on the same path — it appends another duplicate key. Use the reporter's workaround: `updateNodeParameters` with `replace: true` and the complete `parameters` object, so the whole object is replaced instead of patched:

```json
{
  "workflowId": "<id>",
  "operations": [
    {
      "type": "updateNodeParameters",
      "nodeName": "My Code Node",
      "replace": true,
      "parameters": { "jsCode": "new" }
    }
  ]
}
```

Two details matter here. First, `replace: true` must be set — without it you are back to a merge-style update against a node that already has two `parameters` keys, and the result is undefined. Second, the `parameters` object you send must be *complete*: every parameter the node needs, not just the one you are changing. A replace drops anything you omit, so read the node's current parameters first with `get_workflow_details`, copy the full object, change the one value, and send the whole thing back. If the node has many parameters, build the object in the editor instead — see the alternative below.

If you would rather not fight the MCP tool at all, the simplest repair is the n8n editor: open the workflow, open the affected node, change the value in the UI, and save. The editor writes a clean single `parameters` object. Use this whenever the node is one you can reach by hand; reserve the MCP workaround for bulk repairs across many workflows.

### Step 3 - Verify the edit took — read back, then execute

Re-run the duplicate-key detector from Step 1 against the repaired workflow. It should print nothing. Then confirm the new value is the one the runtime sees: execute the workflow (or run the single node with pinned test data) and check the execution output carries the result of the *new* code, not the old. In the reporter's case the old code was a notification hub script — the proof was a live execution producing the new message, not the tool's success response.

Do not trust `appliedOperations: 1` as verification. That count is what lied the first time: it counts operations the tool attempted, not values the runtime will read. Until a fix ships, treat the MCP success response as "the call was accepted" and the detector plus a test execution as the real confirmation.

### Step 4 - Stop using nested setNodeParameter until a fix ships

Until the upstream fix lands, avoid `setNodeParameter` with any path that starts with `/parameters/` — nested or top-level. For every edit through the MCP server, use one of these instead:

- **`updateNodeParameters` with `replace: true`** and the full parameters object, as in Step 2.
- **The n8n editor**, for one-off edits where you can see the node.
- **A full workflow replacement** (`update_workflow` with the complete `nodes` array) when you are already rewriting several nodes at once — the whole-node object you send has exactly one `parameters` key by construction.

If your AI client or harness builds `setNodeParameter` calls on its own, add the rule to its instructions or system prompt: never use `setNodeParameter` with a nested path; always send the whole parameters object with `replace: true`. The assistant cannot see the duplicate it creates, so the guard has to live in the instructions, not in a read-back.

## Prevent it next time

- **Verify every MCP edit with a read-back that can see duplicates.** The Python detector in Step 1 belongs in your post-edit checklist for any workflow an AI assistant touches. A plain `get_workflow_details` read is not enough — it shows the duplicate keys in the raw response, but only if you look at the raw text rather than a parsed view.
- **Never trust a success count as proof an edit applied.** `appliedOperations: 1` means the tool ran one operation, not that the value changed. The same gap exists anywhere a tool reports success without a read-back comparison — check the execution, not the receipt.
- **Keep the parameters object whole when you edit through MCP.** The bug only triggers on path-based patching. Whole-object replacement sidesteps it entirely, and it is also easier to review: the object you sent is the object the node now has.
- **Audit past MCP edits.** If an assistant has been editing workflows through this tool, re-run the detector across the workflows it touched. Any node it edited with a nested path is still running its old value, silently, with a success response in the conversation history. The reporter only caught theirs because a live execution behaved unexpectedly — most silent no-ops are never noticed.
- **Watch for the upstream fix.** The proper fix is for `setNodeParameter` to merge the path into the existing node object instead of assigning into a fresh one. As of 2026-11-25 no fix has been merged — issue #45022 is still open, status `in-linear` — so the `replace: true` habit above is the workaround until a release fixes the operation.

## FAQ

### I edited a node through MCP and the workflow still runs the old code. Is this the bug?

Almost certainly, if the edit used `setNodeParameter` with a nested path such as `/parameters/jsCode`. Run the duplicate-key detector from Step 1 on the workflow JSON: if it reports `DUPLICATE KEYS: ['parameters']`, you are hitting issue #45022. Repair with `updateNodeParameters` and `replace: true`, then verify with a test execution.

### The read-back shows my new value. Doesn't that mean the edit worked?

No — that is exactly how this bug hides. `get_workflow_details` returns the raw node object, which contains *both* keys: the old one first, the new one second. A parsed view shows one of them (usually the new one, depending on the client), while the n8n runtime parses the same JSON and keeps the first — the old value. Only the raw-text detector or a live execution tells you which value actually runs.

### Can I just delete the duplicate key by hand in the workflow JSON?

Yes, if you are comfortable editing workflow JSON directly: export the workflow, remove the second `parameters` object, and re-import or update via the API. But it is easy to delete the wrong one — the duplicate keys are identical except for their values, and most editors collapse them in the display. The `replace: true` repair in Step 2 is safer because it overwrites the whole object in one operation.

### Does this affect the n8n editor or the Public API?

No. The editor and the REST API write the workflow JSON you give them, with one `parameters` key per node. The bug is specific to the MCP server's `setNodeParameter` operation and how it applies a JSON Pointer path. Edits made in the editor, or through `PUT /api/v1/workflows/{id}`, do not create duplicate keys.

### Does this affect every MCP client, or just one?

Any client driving the bundled n8n MCP server's `update_workflow` tool hits it — the reporter used DeepSeek Harness, but the faulty path handling is in the server, not the client. Third-party MCP servers for n8n (such as the community `n8n-mcp` projects) have their own update operations and are not covered by this issue; check their own operation names before assuming the same workaround applies.

### I used setNodeParameter with a top-level path. Am I affected too?

Yes — the issue notes the same class of bug with a top-level path: `/parameters/command` produced a nested `parameters.parameters.command` instead of replacing the value. The node then carries a `parameters` object that itself contains a `parameters` object, which the runtime ignores. Repair it the same way: `updateNodeParameters` with `replace: true` and the complete parameters object.

## Key Takeaways

1. **A nested `setNodeParameter` edit through n8n's MCP server is a silent no-op** — it appends a second `parameters` key to the node, JSON parsers keep the first (old) value, and the tool still reports `appliedOperations: 1` with no warning.
2. **A normal JSON parse cannot see the bug** — it collapses duplicate keys, so detection needs a raw-text check such as the `object_pairs_hook` detector in Step 1, or a live execution that runs the old code.
3. **Repair with a full replacement, not another patch** — `updateNodeParameters` with `replace: true` and the complete parameters object, or edit the node directly in the n8n editor; never re-run `setNodeParameter` on the same path.
4. **No upstream fix is merged yet** — issue #45022 is still open as of 2026-11-25, status `in-linear`, so until a release fixes the path handling, avoid nested `setNodeParameter` entirely and verify every MCP edit with a read-back plus a test execution.

Next: if your MCP-driven edits touch credentials or variables instead of node parameters, read the source control variable bugs from the same week — a pull can blank a variable's value ([issue #44757](https://github.com/n8n-io/n8n/issues/44757)) or delete a variable moved between team projects ([issue #44758](https://github.com/n8n-io/n8n/issues/44758)). Same silent-failure shape, different service.
