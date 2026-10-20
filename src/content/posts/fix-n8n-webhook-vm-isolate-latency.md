---
title: "Fix n8n Webhook Latency Spikes from VM Expression-Isolate Overhead (GH #41322)"
description: "n8n webhook alternating ~60ms/~280ms on every request? The VM expression-isolate pool is cold-starting. Two env vars fix it."
date: 2026-10-20
category: automation
tags: ["n8n", "webhook", "latency", "self-hosting", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-webhook-vm-isolate-latency.webp"
---

Your production webhook feels haunted. A minimal two-node workflow — Webhook → Respond to Webhook — answers in ~60 ms, then ~280 ms, then ~60 ms again, alternating like clockwork. There is no reverse proxy in the path, no TLS, no database slowness, and the workflow itself contains zero dynamic expressions. The latency is not coming from *your* logic at all.

I traced this pattern to n8n's **VM expression engine** — the isolated-vm sandbox that evaluates every `{{ }}` expression — eagerly acquiring an expression isolate on every execution and cold-starting it half the time. The fix is two environment variables: `N8N_EXPRESSION_ENGINE_LAZY_ACQUIRE=true` and a pool size bigger than 1. The reporter of [n8n GitHub issue #41322](https://github.com/n8n-io/n8n/issues/41322) measured the before/after: alternating ~50–70 ms / ~210–300 ms dropped to a steady ~51–80 ms with zero spikes after the first two warm-up requests.

Quick definitions so we're on the same page: **isolated-vm** is a library that runs untrusted JavaScript in a separate V8 isolate — a sandboxed memory space — inside the same Node.js process. n8n 2.x evaluates all workflow expressions through it, which is the "VM expression engine" (`N8N_EXPRESSION_ENGINE=vm`, the default). The **IsolatePool** is n8n's pool of pre-initialized expression "bridges" (ready-to-use isolates) that executions check out on startup. **Lazy acquisition** means an execution only checks out an isolate when it actually needs to evaluate an expression, instead of grabbing one up front on every run.

## The symptom

On self-hosted n8n 2.43.5 (Docker, official image, regular execution mode), sequential HTTP requests to a *minimal* production webhook — a Webhook node using GET on a static path, piped straight into a Respond to Webhook node with a static response, no expressions, no Code nodes — show an alternating latency pattern: fast responses of ~50–70 ms, then slow ones of ~210–300 ms, repeat. The issue reporter hit the endpoint directly on `127.0.0.1:5678`, so reverse-proxy and TLS overhead were excluded from the reproduction path.

What makes this disorienting: the workflow is doing almost nothing. The nodes execute in single-digit milliseconds. Yet every other request burns an extra ~170–185 ms somewhere between "request received" and "nodes started".

The reporter instrumented the installed execution engine and found the delay inside `WorkflowExecute.initializeExecution() → workflow.expression.acquireIsolate() → Expression.vmEvaluator.acquire()`. Measured isolate-acquisition durations across consecutive executions told the whole story: **5.2 ms, 182.6 ms, 5.8 ms, 182.9 ms, 5.2 ms, 186.2 ms** — a perfect alternation matching the response-time pattern.

## The root cause

When a workflow execution initializes, n8n's VM expression engine eagerly acquires an expression isolate — even when the workflow contains no dynamic expressions at all. The acquisition path works like this:

1. `ExpressionEvaluator.acquire()` asks the `IsolatePool` for an initialized bridge (a ready isolate).
2. `IsolatePool.acquire()` removes a bridge from the pool and *asynchronously* starts building a replacement.
3. If the pool is exhausted at that moment — the default pool size is **1** — the evaluator falls back to a synchronous cold `createBridge()`, which takes ~168–186 ms.

With pool size 1, this degenerates into an alternation: request N takes the single ready bridge (fast), request N+1 arrives while the pool is still rebuilding and eats a cold-start bridge (slow). The reporter is honest that pool exhaustion is a strongly supported hypothesis rather than a directly instrumented certainty, but the numbers fit: increasing the pool size to 2 made slow requests less frequent but didn't eliminate them, which is exactly what you'd expect from a pool that still occasionally can't keep up under eager acquisition.

Also worth knowing: disabling execution-data saving did **not** eliminate the pattern, so don't waste time there. This is purely expression-engine overhead.

## The fix

Prerequisites: self-hosted n8n 2.x (verified on 2.43.5 as of October 2026), access to your Docker Compose file or container environment variables, and the ability to restart n8n.

### Step 1 - Confirm you're seeing the same pattern

Reproduce the benchmark from the issue before changing anything — send 20 sequential requests at your production webhook URL and record the timings:

```bash
for i in $(seq 1 20); do
  curl -sS -o /dev/null \
    -w "Request $i | HTTP %{http_code} | %{time_total}s\n" \
    http://127.0.0.1:5678/webhook/<your-path>
done
```

Replace `http://127.0.0.1:5678/webhook/<your-path>` with your own production webhook URL. You're looking for the signature pattern: requests alternating between fast and ~150–250 ms slower. If your timings are uniformly slow instead, you have a different problem (check Step 3's neighbors, or our [OOM crash fix](https://cortexflow.tech/blog/fix-n8n-oom-crash-docker-compose/)).

> **Note:** run this against the **production** webhook URL (the `/webhook/` path on an active workflow), not the `/webhook-test/` URL — test URLs behave differently and won't show this pattern.

### Step 2 - Enable lazy isolate acquisition and grow the pool

Add these two environment variables to your n8n service's environment (Docker Compose shown, but the keys are what matter for any deployment):

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:2.43.5
    environment:
      - N8N_EXPRESSION_ENGINE_LAZY_ACQUIRE=true
      - N8N_EXPRESSION_ENGINE_POOL_SIZE=2
```

Here's what each key does:

- `N8N_EXPRESSION_ENGINE_LAZY_ACQUIRE=true` — executions acquire an expression isolate **only when they actually evaluate an expression**, instead of eagerly on every execution start. Your Webhook → Respond workflows with no expressions never pay the isolate cost at all. (It defaults to `false`, i.e. eager, which is the behavior that produced the spikes.)
- `N8N_EXPRESSION_ENGINE_POOL_SIZE=2` — raises the pre-initialized isolate pool from the default of 1. With lazy acquisition, `2` was enough for the reporter's minimal workload; if you run expressions at higher concurrency, size it to roughly match `N8N_CONCURRENCY_PRODUCTION_LIMIT` so a burst of parallel executions doesn't exhaust the pool.

> **Warning:** don't confuse this pool with the *task runner* (the external JS/Python runners controlled by `N8N_RUNNERS_*`). Those run Code nodes in separate processes — this pool is for the expression engine inside the main process. Changing task-runner settings will not fix this latency.

### Step 3 - Restart and warm the pool

Restart n8n so the variables take effect:

```bash
docker compose up -d n8n
```

Then send two warm-up requests to your production webhook before you trust the steady state. The reporter's numbers show why: after a restart, the first two requests took 3252 ms and 377 ms (cold isolates being built), and **only then** did the following 18 requests settle at ~51–80 ms with zero requests over 200 ms. If you measure immediately after a restart and see one or two slow hits, that's normal cold-start behavior, not the bug.

### Step 4 - Verify it worked

Re-run the 20-request benchmark from Step 1. Success looks like this, from the issue's own measurements:

| Configuration | Result |
|---|---|
| Pool 1, eager (default) | Alternating ~50–70 ms / ~210–300 ms |
| Pool 2, eager | 3–6 of 20 requests >200 ms (better, not fixed) |
| **Pool 2, lazy** | **First 2 requests warm-up; remaining 18 at ~51–80 ms, 0/18 >200 ms** |

You should see no recurring slow requests after the initial warm-up pair. The reporter's real application workflows — including ones with dynamic-expression evaluation and authenticated navigation — all completed successfully with lazy acquisition enabled, so this isn't a "disable the feature" workaround; it's the intended fast path.

## Prevent it next time

- **Bake the two env vars into your Compose file or deployment config permanently**, not just as a one-off `docker run` flag. This is a safe, supported configuration — the reporter asks maintainers whether `LAZY_ACQUIRE` should arguably be the default, and nothing in the thread suggests downsides for production workflows.
- **Size the pool to your concurrency.** If you later raise `N8N_CONCURRENCY_PRODUCTION_LIMIT`, raise `N8N_EXPRESSION_ENGINE_POOL_SIZE` in proportion (start with ~half your concurrency limit and watch the 20-request benchmark). The default pool size of 1 is the trap.
- **Add a warm-up step to your deploy pipeline.** After every n8n restart or version upgrade, fire 2–3 requests at your highest-traffic production webhook before declaring the deploy healthy. The first requests after a cold start are the expensive ones — don't let a user be the one who pays for them.
- **Keep the benchmark handy.** The `curl` loop from Step 1 takes 30 seconds and is the fastest way to tell "expression-engine overhead" apart from network, proxy, or workflow-logic slowness when latency complaints come back.

## Limitations and what wasn't tested

The issue reporter is explicit that pool exhaustion is a hypothesis backed by timing correlation, not by direct pool-state instrumentation — maintainers may clarify the exact lifecycle (acquired bridges are disposed on release and replenished asynchronously) when they respond. The benchmark covered n8n 2.43.5 in regular execution mode only; queue-mode behavior with workers was not measured, and there was no controlled comparison against n8n 1.x to confirm the VM engine as a regression. If lazy acquisition causes any expression-evaluation issue in an unusual workflow, the fallback is trivial: remove the `LAZY_ACQUIRE` line and restart.

## FAQ

### Does this affect n8n Cloud or the turing expression engine?

This was reproduced on self-hosted Docker with the default VM engine (`N8N_EXPRESSION_ENGINE=vm`). n8n Cloud is managed for you, and the turing engine path wasn't benchmarked in the issue — but if you self-host and still run the default VM engine, the env vars apply.

### Will lazy acquisition break expressions in my workflows?

The reporter ran real application workflows with dynamic-expression evaluation under Stage smoke tests after enabling it — all passed. Lazy acquisition defers isolate creation until an expression actually needs evaluation; it doesn't skip evaluation.

### Should I just make the pool huge, like 32?

Not blindly. Each bridge holds a live V8 isolate, which costs memory. Start at 2, match it to your observed concurrency, and verify with the benchmark loop rather than guessing.

## Key Takeaways

1. **Alternating fast/slow webhook responses on n8n 2.x are expression-isolate cold starts**, not your workflow logic — `acquireIsolate()` costs ~170–185 ms when the default size-1 pool is exhausted.
2. **`N8N_EXPRESSION_ENGINE_LAZY_ACQUIRE=true` + `N8N_EXPRESSION_ENGINE_POOL_SIZE=2`** eliminated recurring spikes in the issue's benchmark (18/18 requests at ~51–80 ms after warm-up).
3. **Disabling execution-data saving doesn't help** — don't chase that; the overhead is in `WorkflowExecute.initializeExecution()`.
4. **Warm your pool after every restart** — the first 2 post-restart requests are cold (seconds, not milliseconds); make them yours, not your users'.

Next: if your webhook latency is uniformly high rather than alternating, the culprit is probably workflow design (long synchronous steps holding the response open) — see [the webhook timeout trap fix pattern](https://dev.to/haopengai/the-webhook-timeout-trap-why-my-n8n-webhook-stopped-timing-out-respond-first-work-later-36bg) of responding first and working later.

*Sources: [n8n-io/n8n issue #41322](https://github.com/n8n-io/n8n/issues/41322) (primary — symptom, instrumentation, measured fix), n8n self-hosting environment-variable docs.*
