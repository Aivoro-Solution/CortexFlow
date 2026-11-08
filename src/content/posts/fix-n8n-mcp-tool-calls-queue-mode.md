---
title: "Fix n8n MCP Tool Calls Failing in Queue Mode: 'Worker tool execution timeout' and Duplicate Writes"
description: "MCP tool calls work on a single n8n instance but fail or double-write in queue mode? The 120-second 'Worker tool execution timeout' trap — 4 verified fixes."
date: 2026-11-08
category: automation
tags: ["n8n", "error fix", "MCP", "queue mode", "webhooks"]
draft: false
featured: false
image: "/og/fix-n8n-mcp-tool-calls-queue-mode.webp"
---

Your MCP server works perfectly on a single n8n instance. You enable queue mode to handle load — and the same tool calls start failing with `Worker tool execution timeout`, or worse, they succeed twice: one CRM record becomes two, one payment request becomes two charges, one form submission writes two rows. Nothing in the execution log looks wrong. The workflow even reports success.

This is the queue-mode MCP trap, and it has two separate causes that get confused into one bug. The first is a tool-resolution bug on workers, fixed in n8n 2.38.7. The second is structural: in queue mode the main instance stops waiting after 120 seconds and fails the call — **without cancelling the job** — so the write still lands, the result is dropped, and any client retry sends it again. By the end of this guide you will know which of the two you have, the four fixes that actually work, and the regression test that proves a call can only write once. All fixes are verified against community reports and GitHub issues, as of November 2026.

**Prerequisites:** a self-hosted n8n instance running in queue mode (`EXECUTIONS_MODE=queue` with Redis and at least one worker), an MCP Server Trigger workflow with an HTTP Request Tool (or an MCP Client Tool), and shell access to the host running Docker or the n8n processes.

## The symptom map — which queue-mode MCP failure do you have?

| Symptom | When it happens | Root cause |
|---|---|---|
| `Worker tool execution timeout` after exactly 120 seconds, but the downstream write still lands | A tool call takes longer than 120 seconds in queue mode | Main stops waiting and fails the call without cancelling the job; the worker finishes anyway |
| One logical call writes twice (duplicate CRM rows, double charges) | The MCP client retries after a timeout, or the SSE stream drops and resends | No at-most-once guarantee in queue mode; `$execution.id` changes on every retry |
| MCP tool calls fail or pick the wrong tool on workers, but work on a single instance | n8n older than 2.38.7, MCP Client Tool (a toolkit) on a worker | Worker-side toolkit resolution bug, fixed in 2.38.7 |
| SSE connection drops and tool calls fail intermittently | Multiple webhook replicas behind a load balancer | SSE needs one persistent connection to the same instance |

If your symptom is the last row — SSE breaking across replicas — that is a different failure mode, covered in detail in [MCP in n8n: the troubleshooting guide](/blog/mcp-n8n-troubleshooting/). This article fixes the timeout and duplicate-write failures.

## Root cause: the 120-second wait that doesn't cancel anything

MCP (Model Context Protocol, Anthropic's open standard for exposing tools to AI models) in n8n runs over SSE (Server-Sent Events), a long-lived connection between the MCP client and the n8n main instance. In queue mode, the main instance does not execute anything itself: it pushes the job onto a Redis queue (Bull) and a worker picks it up.

That split creates the trap. The main instance waits for the worker's result — and gives up after 120 seconds. When it gives up, it fails the call with `Worker tool execution timeout`. But **it does not cancel the job**. The worker keeps running, the HTTP POST to your CRM or payment API still lands, and the result is dropped because nobody is listening any more. From the client's side, the call failed. From the downstream system's side, it succeeded. If the client retries — and MCP clients do retry on errors — the same logical call writes a second time.

Three facts from the community investigation make this worse than a simple timeout:

- **The queue will not re-run your call either.** n8n builds the Bull queue with `maxStalledCount: 0`, so a job whose worker dies is marked failed rather than retried. The duplicate does not come from the queue — it comes from the client resending after the 120-second failure.
- **Nothing in queue mode gives at-most-once.** A worker crash, a job retry, or a client reconnect each produce a fresh execution with a fresh id.
- **You cannot dedupe on the execution id.** `$execution.id` changes on every retry, and the MCP JSON-RPC request id is not exposed inside the workflow. The key has to come from the caller.

The second, separate cause is the pre-2.38.7 worker bug. The fix shipped in 2.38.7 changed `job-processor.ts` to unwrap a `StructuredToolkit` — which is what an MCP Client Tool returns — to the named member tool, and to close that MCP connection afterwards. Before that version, a toolkit on a worker could fail to resolve its member tools at all. That fix handles tool *resolution* on workers. It adds no deduplication logic, and it does not apply to a workflow whose tool is a single HTTP Request Tool — a single tool is not a toolkit, so that code path never runs for it.

## Fix 1 - Upgrade to n8n 2.38.7 or later

If your MCP Client Tool calls fail on workers but work on a single instance, upgrade first. The 2.38.7 worker-side fix is the only thing that addresses tool resolution on workers, and no amount of retry configuration works around it.

Check your version on every process — main and workers must run the same version, or you will chase version-skew ghosts:

```bash
docker exec <n8n-main-container> n8n --version
docker exec <n8n-worker-container> n8n --version
```

Both should print `2.38.7` or later. If you use the `n8nio/n8n` image, pin the tag on both services and recreate them:

```bash
docker compose pull n8n n8n-worker
docker compose up -d n8n n8n-worker
```

You should see the MCP Client Tool resolve its member tools on the worker the same way it does on a single instance. If the failure was the 120-second timeout instead of a resolution failure, upgrading alone changes nothing — move on to Fix 2, which is the fix that actually stops duplicate writes.

> **Note:** the 2.38.7 change fixes tool resolution on workers only. It does not add deduplication, and it does not change the 120-second wait. Do not treat "upgraded" as "fixed" for the duplicate-write symptom.

## Fix 2 - Put an idempotency key on every unsafe HTTP tool

This is the fix that stops duplicate writes, and it is the only one that can — because nothing in queue mode gives at-most-once, the dedup has to happen on the receiving side, keyed on something stable across retries.

In your HTTP Request Tool, add a header named `Idempotency-Key` with this value:

```
{{ $fromAI('call_id', 'unique id for this call', 'string') || $execution.id }}
```

Here is what each part does, and why the fallback matters:

- `$fromAI('call_id', 'unique id for this call', 'string')` asks the model to supply a stable, unique id for this specific call — the same logical call keeps the same `call_id` when the client retries it, because the call's arguments and intent are the same.
- `|| $execution.id` is the fallback when the model supplies nothing. It dedupes within one run only, because `$execution.id` changes on every retry — so treat it as a safety net, not the mechanism.
- **Dedupe on the receiving side by that header, never by the call arguments.** Two deliberate calls with identical inputs must still write twice; two retries of the same call must write once. Arguments cannot tell those apart. The header can.

On the receiving side — your CRM, your database, your payment API — the check is one rule: **if a write with this `Idempotency-Key` already exists, return the stored result instead of writing again.** Stripe, for example, accepts an `Idempotency-Key` header natively; for a database, store the key in a unique column and use `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING RETURNING id` as the gate. The general dedup pattern, including the Data Table gate, is covered in [Fix n8n Webhook Retries Causing Duplicate Orders/Charges](/blog/fix-n8n-webhook-duplicate-idempotency/).

You should see duplicate writes stop even while the 120-second timeout still fires occasionally. The timeout is a latency problem; the duplicate is a correctness problem. Fix 2 solves correctness. Fixes 3 and 4 reduce how often the timeout happens at all.

> **Warning:** do not dedupe on `$execution.id` alone, and do not use the operation id from your own workflow as the key if the client can resend the same operation with a new execution. A resent call gets a new execution, so `$execution.id` will not match — and the duplicate slips through.

## Fix 3 - Keep tool calls under the 120-second wait

The timeout fires because the main instance stops waiting after 120 seconds. The most reliable way to avoid it is to make sure a tool call never needs that long — or, if it does, to stop waiting for it synchronously.

First, find out whether your tools are actually slow or just stuck. In the Executions tab, open a timed-out run and check how long the HTTP Request Tool spent. If the downstream API routinely takes over 120 seconds, no timeout setting on the n8n side fixes the design: split the work so the tool call returns fast and the slow part runs asynchronously (webhook responds immediately with a job id, the rest of the workflow continues in the background).

If the tool is slow because the worker is starved, check the two settings that decide how long a worker waits for work and how long a task runner waits for a task. The task runner has its own 60-second default — set it on both the task runner and the worker if your Code or Python tasks legitimately run longer:

```bash
N8N_RUNNERS_TASK_TIMEOUT=300
```

And cap how long a single execution may run before n8n kills it, so a hung tool call cannot hold a worker slot forever:

```bash
EXECUTIONS_TIMEOUT=600
```

You should see the 120-second failures become rare instead of routine. If they persist for one specific tool, that tool's downstream API is the bottleneck — move it behind the asynchronous pattern above rather than raising timeouts further. Raising a timeout trades a fast, visible failure for a slow, silent one: the worker slot stays occupied while the client has already given up.

## Fix 4 - Route /mcp* to a single webhook replica

If you run multiple webhook replicas behind a load balancer, SSE connections land on different instances and tool calls fail intermittently — a symptom that looks like the timeout but has a different cause. Route all MCP traffic to one dedicated replica, or drop back to a single webhook instance until you genuinely need the scale.

In your reverse proxy, pin the MCP paths to one backend. With nginx, a location block like this keeps every MCP request — including the long-lived SSE stream — on the same instance:

```nginx
location /mcp {
    proxy_pass http://n8n-webhook-1:5678;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_read_timeout 300s;
}
```

`proxy_buffering off` matters: with buffering on, nginx holds SSE events instead of streaming them, and the client sees the same 120-second silence that triggers a retry. `proxy_read_timeout 300s` gives the stream room beyond the 120-second wait so the proxy is not the thing that gives up first.

You should see intermittent SSE drops disappear while the timeout and duplicate fixes above stay in place. If you do not run queue mode yet and MCP is your main workload, the honest recommendation is to stay on a single instance until you actually need scale — queue mode adds Redis, Postgres, and this whole failure surface for load you may not have.

## Verify it worked — the regression test

Do not trust a single successful call. The bug only shows up under failure, so test under failure:

1. **Four distinct calls, one write each.** Send four different MCP tool calls through the trigger. You should see four executions and exactly one write per call in the downstream system.
2. **Kill the worker mid-call.** Run `docker kill <n8n-worker-container>` while a tool call is in flight, then restart the worker. You should see the job marked failed — not retried, not duplicated — because `maxStalledCount: 0`.
3. **Drop the SSE stream and resend.** Disconnect the MCP client mid-call and reconnect with the same `call_id`. You should see one row per `Idempotency-Key` in the downstream system, and the execution count by header — not by operation id — should show one write.
4. **Hold a response past 120 seconds.** Have the receiver record the write and delay its response beyond 120 seconds, then resend the same `call_id` when the timeout returns. You should see one write. This is the exact test that catches the original bug: without the idempotency key, the resend writes twice.

If all four pass, the fix holds. If test 3 or 4 writes twice, the receiving side is not actually deduping on the header — recheck Fix 2 before touching anything else.

## Prevent it next time

- **Every unsafe HTTP tool gets an idempotency key.** A tool that writes, charges, or creates anything must carry a caller-supplied key, from the day it is built. Add it to your review checklist for new MCP tools.
- **Never dedupe on `$execution.id` or on arguments.** The first changes on retry; the second cannot distinguish a retry from a deliberate repeat.
- **Pin main and workers to the same n8n version.** Version skew between main and worker is how the 2.38.7 toolkit fix silently fails to apply.
- **Monitor for the timeout, not just for errors.** Alert on executions whose error contains `Worker tool execution timeout` — each one is a write that landed without a result, and a client that will probably retry.
- **Keep MCP on one webhook replica.** The moment you add a second replica behind a load balancer, route `/mcp*` to one of them or the SSE failures return.

## FAQ

### Does upgrading to 2.38.7 fix the duplicate writes?

No. The 2.38.7 change fixes tool *resolution* on workers — it unwraps a `StructuredToolkit` to the named member and closes the MCP connection afterwards. It adds no deduplication. Duplicate writes need the idempotency key in Fix 2.

### Why can't I just use $execution.id as the idempotency key?

Because `$execution.id` changes on every retry. A resent call is a new execution with a new id, so the receiving side sees a new key and writes again. The key has to come from the caller — here, `$fromAI('call_id', ...)` — so the same logical call keeps the same key across retries.

### Is this the same bug as MCP breaking across multiple webhook replicas?

No, but they look alike. The replica problem breaks SSE routing: requests land on different instances and the stream drops. The timeout problem breaks the wait: the main gives up after 120 seconds while the job keeps running. Fix 4 covers the replica case; Fixes 1–3 cover the timeout and duplicate case.

### Should I just turn queue mode off?

If MCP is your main workload and you do not need the scale, staying on a single instance is a legitimate fix — it removes the main/worker split entirely. Turn queue mode on when a loaded instance starts dropping executions, not before. The trade-off is real: queue mode adds Redis, Postgres, and this failure surface.

## Key Takeaways

1. **The 120-second timeout does not cancel the job** — the write still lands, the result is dropped, and a client retry writes twice.
2. **Upgrade to n8n 2.38.7+** for the worker-side toolkit fix, but know it only fixes tool resolution, not duplicates.
3. **Add an `Idempotency-Key` header** (`$fromAI('call_id', ...) || $execution.id`) to every unsafe HTTP tool and dedupe on the receiving side by that header — never by arguments or `$execution.id`.
4. **Route `/mcp*` to one webhook replica** and disable proxy buffering, or SSE drops will mimic the timeout.
5. **Prove it with the regression test** — kill the worker mid-call, drop the SSE stream and resend, hold a response past 120 seconds — and assert one row per key.

Next: if your MCP setup also drops connections at the proxy layer, read [MCP in n8n: the troubleshooting guide](/blog/mcp-n8n-troubleshooting/) for the headers and OAuth re-auth fixes — and if duplicate writes show up on non-MCP webhooks too, the general dedup patterns are in [Fix n8n Webhook Retries Causing Duplicate Orders/Charges](/blog/fix-n8n-webhook-duplicate-idempotency/).

*Sources: [community.n8n.io — Need guidance: idempotency for MCP Server Trigger calling unsafe HTTP tools in queue mode (n8n 2.38.7)](https://community.n8n.io/t/need-guidance-idempotency-for-mcp-server-trigger-calling-unsafe-http-tools-in-queue-mode/313705) · [GitHub n8n-io/n8n #38545](https://github.com/n8n-io/n8n/issues/38545) · [GitHub n8n-io/n8n #26394](https://github.com/n8n-io/n8n/issues/26394).*
