---
title: "Fix n8n Merge Nodes Deadlocking Inside a Loop (Execution Stops with 'Success', GH #44423)"
description: "Two Merge nodes in a loop body wait on each other and n8n ends the run as 'Success' without running either. Here's the cause and the fix."
date: 2026-11-19
category: automation
tags: ["n8n", "merge-node", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-merge-nodes-deadlock-in-loop.webp"
---

Your loop runs one iteration, then the execution ends. Status: "Success". No error, no red node, no failed execution to investigate — but half your workflow never ran. The nodes after the loop never execute, the second iteration never starts, and the output node gets nothing.

This is a confirmed bug in n8n, filed as [GitHub issue #44423](https://github.com/n8n-io/n8n/issues/44423) on November 18, 2026 (team-assigned, Linear GHC-9811, still open as of November 19, 2026). When a loop body contains **two Merge nodes that are both waiting on partial input at the same time**, the execution engine decides each one is waiting on the other and runs neither. By the end of this article you will know how to confirm you have hit this exact bug, fix it with the reporter-verified workaround, and verify the loop runs to completion.

Quick definitions before we start: a **Merge node** combines data from two or more input streams into one output — in **Append mode** it simply concatenates the items from each input, one after another. **Loop Over Items** (the SplitInBatches node) processes a list one batch at a time, looping back to the start of the loop body until every item is done. **Waiting execution** is the engine's internal list of nodes that have received data on some inputs and are waiting for the rest before they can run. The **v1 execution order** is the current default order in which n8n schedules nodes (workflows created before n8n 1.0 may still use the legacy v0 order, which this bug does not affect).

## The symptom: the loop stops after one iteration, with no error

The failure needs three ingredients at once:

1. A loop that connects back to an earlier node (here, an **Aggregate** node feeding back into **Loop Over Items**).
2. Two Merge nodes inside the loop body, both in Append mode.
3. Both Merge nodes receiving data on only one of their two inputs during the same iteration.

The reporter's reproduction makes the timing concrete. The workflow has pinned trigger data — two items, each carrying a `docs` array of two elements — and a Switch node that routes docs by whether the doc number is odd or even. In iteration 1 (docs 1 and 2):

- Doc 1 is the first item. It goes through `If first item` (true) → `Switch` → output `odd` → `Merge` input 2. `Merge` waits for input 1.
- Doc 2 goes through `If first item` (false) → `Merge1` input 2. `Merge1` waits for input 1.

Neither Merge node executes. `Aggregate`, the second loop iteration (docs 3 and 4), and the `return` node never run. The execution status is "Success".

**The most dangerous part is the status.** A failed execution shows up in your executions list and can trigger an Error Trigger workflow. A "Success" that silently dropped half the work shows up nowhere. If you run this in production, the only sign is missing output downstream — rows never written, messages never sent, records never updated.

## The root cause: each Merge node is the other's ancestor

The bug lives in the execution scheduler, not in the Merge node. When the execution stack empties, `WorkflowExecute.processRunExecutionData` (in `packages/core/src/execution-engine/workflow-execute.ts`) looks at the nodes in `waitingExecution` and tries to pick one to run. For each waiting node it collects all ancestors with `workflow.getParentNodes(nodeName)` — and if any ancestor is also waiting (`parentIsWaiting`), it skips the node, on the assumption that the ancestor will run first and unblock it.

The problem is that `getParentNodes` follows connections back through the loop. So each Merge node is an ancestor of the other:

- `Merge1` ← `Merge` (a direct connection: `Merge` feeds `Merge1`'s input 1).
- `Merge` ← `Switch` ← `If first item` ← `Split Out` ← `Loop Over Items` ← `Aggregate` ← `Merge1` (the same path, traced back through the loop's feedback connection).

The engine skips both Merge nodes. The `waitingExecution` loop ends with no node to execute, and the execution finishes — silently, as "Success".

n8n team member grinem confirmed the diagnosis in the issue thread: `getParentNodes` in `packages/core/src/Workflow.ts` does a standard BFS/DFS traversal over `node.connections` without checking for cyclic back-edges leading back into loop controllers. The proposed upstream fix is to ignore ancestors a node reaches only through a loop back connection when evaluating `parentIsWaiting`, or to fall back to topological depth from the active iteration root if every waiting node is skipped. The reporter also notes this may be the root cause of the older [issue #37895](https://github.com/n8n-io/n8n/issues/37895), where a Merge node fails to execute in a large graph but works in an isolated copy of the surrounding nodes.

One thing this bug is **not**: a Merge node configuration mistake. A Merge node always waits for all of its connected inputs before it runs — even in Append mode, which only controls how the data is combined, not whether the node waits. That waiting behaviour is by design. The bug is that the scheduler deadlocks two correctly-configured Merge nodes against each other through the loop.

## How to confirm this is your bug

Before restructuring anything, check the four signs. All four together point at #44423, not at a data or configuration problem:

1. **The execution status is "Success" but downstream nodes never ran.** Open the execution and check the nodes after the loop — they show no input data and no run.
2. **Two Merge nodes in the same loop body are both stuck.** In the execution view, both Merge nodes show partial input: data on one input, nothing on the other.
3. **The loop body feeds back into the loop node.** There is a connection from a node at the end of the loop body (here, `Aggregate`) back to `Loop Over Items`.
4. **Removing the feedback connection makes the same graph execute.** The reporter verified this: disconnect `Aggregate` → `Loop Over Items` and the Merge nodes run. (This is a diagnostic only — it breaks the loop, so it is not a fix.)

If only one Merge node is stuck, or the workflow has no loop, you have a different problem — most likely a branch that never executes, so the Merge node is correctly waiting for input that will never arrive. In that case the fix is upstream, in the branch, not in the Merge node.

## The fix: move the loop body into a sub-workflow

The reporter-verified workaround removes the cycle the scheduler chokes on. A sub-workflow has no loop, so its Merge nodes can never be ancestors of each other.

### Step 1 - Cut the loop body into a sub-workflow

Create a new workflow containing everything currently inside the loop body — the `Split Out`, `If first item`, `Switch`, both Merge nodes, and `Aggregate` — minus the `Loop Over Items` node itself. Give the sub-workflow an **Execute Workflow Trigger** as its first node.

> **Note:** keep the Merge nodes exactly as they are. The bug is in the scheduler's loop handling, not in the Merge configuration, so nothing about the Merge nodes needs to change.

### Step 2 - Call the sub-workflow once per item

In the parent workflow, replace `Loop Over Items` with an **Execute Workflow** node pointing at the new sub-workflow, and set its mode to **Run once for each item**. Delete the `Loop Over Items` node and the `Aggregate` → `Loop Over Items` feedback connection — there is no loop left in the parent, so nothing feeds back.

Here is what each setting does: **Run once for each item** makes the Execute Workflow node invoke the sub-workflow separately for every item, which is exactly what one loop iteration did. The sub-workflow receives one item at a time, so the two Merge nodes inside it see the same per-item data they saw inside the loop body — but without a loop back-edge, the scheduler's ancestor walk can no longer make them ancestors of each other.

### Step 3 - Reconnect the output

Connect the Execute Workflow node's output to whatever followed the loop in the parent workflow (in the reporter's case, the `return` node). The parent now runs straight through: trigger → Execute Workflow (once per item) → output.

## Verify the fix worked

Run the workflow with the same pinned data the reporter used — two input items, each with a `docs` array of two elements — and check three things:

1. **Both Merge nodes execute.** In the execution view, `Merge` and `Merge1` each show input data on both inputs and produce output.
2. **Every iteration runs.** Both doc pairs (docs 1–2 and docs 3–4) are processed, not just the first pair.
3. **The output node gets the full result.** The `return` node should receive 2 items, one for each input item. If it receives 1 item or none, the loop body is still dropping work.

If the sub-workflow version passes all three checks, the deadlock is gone.

## Alternative fixes when a sub-workflow does not fit

The sub-workflow is the verified workaround, but two structural changes achieve the same thing — breaking the cycle so only one Merge node is ever waiting at a time:

- **Restructure to a single Merge node.** If the two Merge nodes exist only to combine the two Switch outputs with the If branches, re-route the branches so one Merge node collects all of them. One waiting Merge node has no other waiting Merge to deadlock against.
- **Combine with a Code node instead of a second Merge.** Replace the downstream Merge node with a Code node that concatenates the arrays itself (`return [{ json: { items: $input.all().map(i => i.json) } }]` is the shape — adapt it to your fields). A Code node does not wait on multiple inputs, so it cannot enter the deadlock.

Both alternatives are untested against the reporter's exact workflow — the sub-workflow fix is the one verified to work. Prefer it unless the sub-workflow's trade-offs (below) rule it out.

## Limits and trade-offs

- **Sub-workflow executions are separate executions.** Each call appears as its own execution in the executions list, and `$execution.id` inside the sub-workflow is the sub-workflow's id, not the parent's. If downstream logic keys on the parent's execution id, carry it explicitly as a field in the item data.
- **Error handling moves.** Errors inside the loop body now surface in the sub-workflow's executions. If you use an Error Trigger workflow, point it at the sub-workflow too, or the failures will be invisible in exactly the way this bug was.
- **No fixed n8n version yet.** As of November 19, 2026 the issue is team-assigned (Linear GHC-9811) with no merged fix and no release containing one. The workaround is the fix until the scheduler change lands — re-check the issue before removing the sub-workflow in a future upgrade.
- **This bug needs the v1 execution order.** Workflows still on the legacy v0 order are not affected, but v0 is legacy for a reason — do not switch a workflow back to v0 to dodge this bug.

## Prevent it next time

Three design rules keep this deadlock out of future workflows:

1. **One Merge node per loop body.** If a loop body needs to combine more than two streams, do the combining outside the loop or in a sub-workflow.
2. **Keep every Merge node's inputs inside the same iteration.** A Merge input that can only arrive from a later iteration is a deadlock waiting for the right data split.
3. **Treat silent "Success" as a failure signal.** If a workflow's output count drops — fewer rows written, fewer messages sent — check the execution view for nodes that never ran, even when the status is green. A quick canary helps: a final node that compares the output item count against the input count and alerts when they disagree catches this whole class of bug, including the related [SplitInBatches loop that ends early](https://cortexflow.tech/blog/fix-n8n-splitinbatches-loop-ends-early/) and workflows that [silently stop triggering](https://cortexflow.tech/blog/fix-n8n-workflow-silently-stopped-triggering/).

## FAQ

### Is this the same as the SplitInBatches loop ending early?

No. The SplitInBatches bug ends the loop when a node inside it returns zero items — the branch halts and the loop never continues. This bug ends the loop when two Merge nodes wait on each other through the loop's feedback connection. Different root cause, different fix, same misleading "Success" status.

### Why does removing the Aggregate → Loop Over Items connection fix it?

Because it breaks the cycle. Without the feedback connection, `getParentNodes` can no longer trace `Merge` back to `Merge1` through the loop, so the scheduler stops seeing each Merge as the other's ancestor and runs them. It is a diagnostic proof, not a fix — without the connection there is no loop.

### Does this affect Merge nodes outside loops?

Not this bug. A Merge node outside a loop that never runs is almost always waiting on a branch that never executed — check the branch, not the scheduler. The deadlock needs the loop back-edge to create the mutual-ancestor cycle.

### What should n8n do instead?

The reporter's expectation, which the team has not disputed: if the engine cannot select a node to execute, the execution must fail with a clear error. It must not finish with the status "Success". Until that lands, the sub-workflow workaround is the way to keep the work running.

## Key Takeaways

1. **Two Merge nodes in one loop body can deadlock** — the scheduler sees each as the other's ancestor through the loop's feedback connection and runs neither.
2. **The giveaway is a "Success" execution with unrun nodes** — downstream nodes show no input data and no run, and the second iteration never starts.
3. **The verified fix is a sub-workflow** — move the loop body out, call it with Execute Workflow in "Run once for each item" mode, and delete the Loop Over Items node.
4. **A Merge node always waits for all connected inputs**, even in Append mode — Append controls how data is combined, not whether the node waits.
5. **No fixed version exists yet** — the issue (GH #44423, Linear GHC-9811) is team-assigned and still open as of November 19, 2026.

Next: check the [issue #44423 thread](https://github.com/n8n-io/n8n/issues/44423) for the upstream scheduler fix, and audit your own loop workflows for a second Merge node hiding in the loop body — this bug only needs the right data split to fire.
