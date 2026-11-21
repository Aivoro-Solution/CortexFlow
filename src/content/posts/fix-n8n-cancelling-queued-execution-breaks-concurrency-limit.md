---
title: "Fix n8n Cancelling a Queued Execution Breaking Your Concurrency Limit"
description: "Cancelling a queued n8n execution starts the next one immediately — even with every slot full — breaking N8N_CONCURRENCY_PRODUCTION_LIMIT. Cause and fix inside."
date: 2026-11-21
category: automation
tags: ["n8n", "error-fix", "concurrency", "queue-mode", "executions"]
draft: false
featured: false
image: "/og/fix-n8n-cancelling-queued-execution-breaks-concurrency-limit.webp"
---

You set `N8N_CONCURRENCY_PRODUCTION_LIMIT=1` because a downstream API can only handle one call at a time. One execution is running, two are queued, and everything is behaving. Then you cancel one of the queued executions — the one you no longer need — and the *other* queued execution starts immediately, while the first one is still running. Two executions are now running with a limit of one, and nothing in the UI tells you the limit was broken. By the end of this post you will know why cancelling a queued execution releases the next one, how to reproduce it in two minutes, and what to do until the fix ships.

## The symptom: the limit holds until you cancel something

The setup is ordinary. n8n is running in regular mode with production concurrency control enabled — the environment variable `N8N_CONCURRENCY_PRODUCTION_LIMIT` caps how many production executions (webhook and trigger executions, not manual editor runs) run at the same time. Anything over the limit waits in a queue and runs first-in, first-out as slots free up. The default value of `-1` disables the limit entirely, so this only bites you if you deliberately set a limit.

The failure looks like this, reported against n8n 2.48.7 in [GitHub issue #44720](https://github.com/n8n-io/n8n/issues/44720) (opened 2026-11-20):

1. `N8N_CONCURRENCY_PRODUCTION_LIMIT=1`, one execution running, two queued.
2. Cancel the older of the two queued executions from the Executions tab.
3. The remaining queued execution starts **immediately**, while the first execution is still running.

Two executions are now running with a limit of one. Every queued execution you cancel or delete lets one more through, so the overshoot grows with the number of queued executions you remove. The limit is not being ignored — it works perfectly until a queued execution is removed. The removal itself is what breaks it.

> **Note:** Deleting a queued execution (status `new`) does the same thing as cancelling one. Both paths reach the same queue code, so both trigger the overshoot.

## Reproduce it in two minutes

You do not need a real workload to see this. A Webhook node that answers immediately, followed by a 30-second Wait node, is enough — the Wait holds the slot while the others queue up.

1. Start n8n in regular mode with the limit set to one:

```bash
N8N_CONCURRENCY_PRODUCTION_LIMIT=1 npx n8n
```

2. Build a workflow with a Webhook trigger (respond immediately) followed by a Wait node set to 30 seconds, and activate it.

3. Fire three webhook calls at once:

```bash
for i in 1 2 3; do curl -s http://localhost:5678/webhook/concurrency-test & done
```

Replace `concurrency-test` with your webhook's path. The `&` backgrounds each call so all three land at the same time.

4. Open the workflow's Executions tab. You should see 1 execution **Running** and 2 **Queued** — exactly what a limit of one promises.

5. Cancel the older of the two queued executions.

6. Watch the remaining queued execution. It starts immediately, while the first execution is still inside its 30-second Wait. The Executions tab now shows 2 Running with a limit of 1.

That is the whole bug: a queued execution that should have waited for a free slot started because a *different* queued execution was removed.

## Root cause: removing a queued execution frees a slot that was never taken

The concurrency queue lives in `packages/cli/src/concurrency/concurrency-queue.ts`. Its `remove()` method takes a queued execution out of the queue:

```typescript
remove(executionId: string) {
	const index = this.queue.findIndex((item) => item.executionId === executionId);
	if (index > -1) {
		this.queue.splice(index, 1);
		this.capacity++;
		this.resolveNext();
	}
}
```

Two of those three lines are correct, and one is not. A queued execution has reserved a *place in line*, not a running slot, so incrementing `capacity` when it leaves is right — that place is genuinely free again. The problem is `this.resolveNext()`. That call releases the next waiting execution, and it should only run when a **running** execution finishes — which is exactly what `dequeue()` does. Here it runs when a queued execution is *removed*, while every running slot is still occupied.

The call chain makes it easy to hit from the UI. `ConcurrencyQueue.remove()` is reached through `ConcurrencyControlService.remove()`, which runs when a queued execution is stopped (`ExecutionService.stopInRegularMode()`) or when an execution with status `new` is deleted. Cancelling or deleting a queued execution is a normal housekeeping action — and each one silently starts the next execution in line.

The bug is confirmed, not just suspected. Team member goutham-valugula verified the cited queue implementation and unit test on 2026-11-21, and the reporter, HakeemTheEmperor, submitted the fix as PR #44724 the same day. The existing unit test, `should limit concurrency`, even asserts the wrong behaviour today: with a limit of one, after `queue.remove('4')` it expects executions 3 and 5 to both be `started` — two executions running at once. The PR removes the `resolveNext()` call from `remove()`, corrects that test, and adds a regression test that keeps execution 5 queued after removing 4, releasing it only once execution 3 calls `dequeue()`.

## The fix: stop cancelling queued executions (until PR #44724 lands)

There is no configuration change that fixes this — the bug is in the queue code itself, and the fix is a one-line upstream change. Until a release containing PR #44724 ships, the workarounds are about avoiding the trigger and limiting the damage.

### Step 1 - Let the queue drain instead of cancelling

If a queued execution is harmless — it will run, do its work, and finish — leave it alone. Cancelling it is what starts the next one early. This is the only workaround that avoids the overshoot entirely, so make it the default: queued executions are a waiting room, not a to-do list to clear.

### Step 2 - If you must remove one, deactivate the workflow first

Sometimes a queued execution really has to go — a bad deploy, a stale trigger, a run you know will fail. In that case, deactivate the workflow *before* you cancel the queued execution. Deactivation stops new executions from entering the queue, so the overshoot is bounded to the executions already waiting instead of growing as new webhooks arrive. Then cancel, then re-activate once the running execution finishes.

### Step 3 - Make the overshoot harmless downstream

The reason a concurrency limit exists is usually a downstream constraint — an API rate limit, a database connection pool, a third-party service that falls over under parallel load. Until the fix ships, assume the limit can be exceeded by one execution per cancelled queued execution, and defend the downstream side:

- Make the workflow idempotent, so two executions running at once cannot double-charge, double-send, or double-write.
- If the downstream API has its own rate limit, add a Wait or a throttle inside the workflow rather than relying on n8n's concurrency gate alone.
- If you run in queue mode, remember the same variable also sets worker concurrency when it is anything other than `-1`, overriding the `--concurrency` flag — the overshoot applies there too.

### Step 4 - Check whether you are already affected

Open the Executions tab during a burst and count the Running executions against your limit. If Running ever exceeds `N8N_CONCURRENCY_PRODUCTION_LIMIT` — and nobody changed the variable — this bug is the likely cause, especially if someone cancelled or deleted a queued execution shortly before. There is no log line that announces it; the overshoot is silent, which is why it is worth checking rather than assuming the limit held.

## Verify the fix when it ships

Once you upgrade to a release containing PR #44724, re-run the two-minute reproduction above. With the fix, cancelling the older queued execution leaves the remaining one **Queued** until the running execution finishes its 30-second Wait — and only then does it start. If it starts early, you are still on an affected version.

## When this does not apply

- If `N8N_CONCURRENCY_PRODUCTION_LIMIT` is unset or `-1`, there is no limit to break — the queue is disabled and every execution starts immediately. The bug is invisible because there is nothing to violate.
- Manual executions from the editor are excluded from the concurrency limit, so cancelling a manual run cannot trigger this.
- Cancelling a **running** execution is fine. That genuinely frees a slot, and the next queued execution starting is the correct behaviour. Only cancelling or deleting a **queued** execution is the trigger.

## FAQ

### Does this affect n8n Cloud?

Cloud plans enforce their own concurrency ceilings (Starter 5, Pro up to 50), and the queue code path is the same family of logic, but issue #44720 was reported and reproduced on a self-hosted instance in regular mode. If you are on Cloud and see Running exceed your plan limit after cancelling a queued execution, report it with the same reproduction — the mechanism is the same, but the self-hosted case is the confirmed one.

### Is my data at risk, or just my rate limits?

The overshoot itself does not corrupt data — it runs an extra execution concurrently. The risk is whatever your workflows do when two of them run at once: duplicate API calls, race conditions on shared rows, rate-limit errors from a downstream service. The danger is proportional to how much your workflows assume they run alone.

### Can I just raise the limit to hide it?

Raising the limit does not fix the bug; it just moves the ceiling. The overshoot is relative to whatever limit you set — cancel three queued executions and you can run three over the new limit. Raise the limit only if your downstream systems can genuinely handle the extra concurrency, and treat that as a capacity decision, not a fix.

## Key Takeaways

1. **Cancelling a queued execution starts the next one early** — `ConcurrencyQueue.remove()` calls `resolveNext()` even though no running slot was freed, so each cancelled or deleted queued execution lets one more execution past `N8N_CONCURRENCY_PRODUCTION_LIMIT`.
2. **The limit works until you touch the queue** — with a limit of one, one running and two queued behaves correctly right up to the moment you cancel one of the queued executions.
3. **Do not cancel queued executions while slots are full** — let the queue drain; if you must remove one, deactivate the workflow first so the overshoot stays bounded.
4. **The fix is PR #44724** — it removes the `resolveNext()` call from `remove()` and corrects the unit test that currently asserts the buggy behaviour. Upgrade to a release containing it, then re-run the two-minute reproduction to confirm the remaining execution stays queued.

Next: if you rely on concurrency limits to protect a downstream API, audit the workflows behind that API for idempotency — the limit is a gate, not a guarantee, and this bug is a reminder that a gate can open from the wrong side. Related reading: our guide to [fixing n8n SplitInBatches loops that end early](/blog/fix-n8n-splitinbatches-loop-ends-early/), another case where an execution silently does less — or more — than the UI promises.
