---
title: "Stop 429 Errors in n8n: Build a Token Bucket Rate Limiter for Any API"
description: "Your n8n loop blasts an API and dies on 429s. Build a token bucket gate in n8n with a Code node and static data: burst 20, then a steady 1 request per second."
date: 2026-10-21
category: automation
tags: ["n8n", "rate-limiting", "api", "tutorial"]
draft: false
featured: false
image: "/og/n8n-token-bucket-rate-limiter.webp"
---

Your workflow pulls 500 rows, loops over them, and fires an HTTP request for every single one — all in the same second. The API answers the first few dozen, then returns **429 Too Many Requests** (the HTTP status an API sends when you exceed its request quota, defined in [RFC 6585](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/429)) for the rest, and your execution dies halfway with partial data.

A fixed delay between requests fixes it, but badly: it is slow when the API has room, and still too fast when the limit is per-minute instead of per-second. In the next 15 minutes you will build a **token bucket** — the same algorithm APIs themselves use to throttle you — inside n8n, using one Code node and n8n's workflow static data. By the end you will have a gate you can drop in front of any HTTP Request node: it allows a burst of 20 requests, then settles to a steady 1 request per second, and calculates its own wait instead of guessing.

**Prerequisites**

- n8n 1.x or 2.x, self-hosted or Cloud (the Code node and workflow static data work on both; static data behaviour differs in one important way — see Step 4).
- A workflow that calls an API in a loop (Loop Over Items / Split in Batches) or fires repeated HTTP requests.
- Your API's documented limit, in requests per second or per minute. If the docs don't state it, start with the conservative defaults in this article (burst 20, refill 1/second) and lower them if 429s continue.

**Example terminology**

- `<your-api-url>` — the endpoint your HTTP Request node already calls. You do not change it; the gate goes *before* it.
- **Capacity (20)** — the maximum tokens the bucket holds. This is your burst size.
- **Refill rate (1/second)** — how fast tokens are added back. This is your sustained request rate: 60 requests per minute.
- **Cost (1)** — tokens one request spends. Keep it at 1 unless one API call should count double (for example, a search endpoint the provider weights as 2 calls).

## The token bucket, in plain language

A **token bucket** is a rate-limiting algorithm (a set of rules that decides whether a request may proceed *now* or must wait). It has exactly three moving parts:

1. **The bucket** holds tokens, up to its **capacity**. Tokens are just permission slips: no token, no request.
2. **The refill** adds tokens at a constant **refill rate** — say 1 token per second — and never above capacity. Tokens that arrive at a full bucket are discarded.
3. **The spend:** every request takes tokens out equal to its **cost**. If enough tokens are there, the request goes immediately. If not, it waits until the refill covers the difference.

This is not a metaphor I invented for this article; it is how providers describe their own limits. AWS documents its [ECS API throttling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/request-throttling.html) as a bucket of 50 tokens refilling at 20 per second — make 50 requests in one second and the bucket is empty, after which you can make exactly 20 per second, forever, until you slow down and let it refill. [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html) uses the same shape at account level: 10,000 requests per second sustained, with a token-bucket burst capacity of 5,000.

The one formula the whole article runs on is lazy refill — tokens are not added by a timer, they are *calculated* when a request arrives:

```
tokens = min(capacity, tokens + elapsed_seconds × refill_rate)
```

**The property that makes token bucket better than a fixed delay: idle time is saved, not wasted.** If your workflow does nothing for a minute, the bucket refills to its full capacity of 20, so the next burst of 20 goes instantly. A fixed 1-second Wait throws that minute away and still makes request 1 and request 20 wait a full second each.

<figure class="shot">
  <img src="/figures/n8n-token-bucket-rate-limiter-rig.svg" alt="Isometric bench rig of a token bucket rate limiter: a tank holding 20 tokens, requests on a rail carriage costing 18, 14 and 10 tokens, a gate plunger and a dial that reads the spend" loading="lazy" />
  <figcaption>The token bucket as a bench rig, drawn with the Anatomy figure kit. The tank on the plinth holds <strong>20 tokens</strong> — the capacity. Requests ride the carriage on rails and pass under the gate plunger one at a time, each spending tokens equal to its block: 18, 14 and 10. The dial reads the spend, and one full turn of the needle is the whole bucket. <strong>Notice:</strong> the tall 18-token request nearly empties the tank on its own, and while the tank refills at its fixed rate, the next request has nowhere to go but the end of the rail — it waits. That waiting, calculated from the refill rate instead of fixed in advance, is the entire algorithm.</figcaption>
</figure>

## Three ways to pace requests in n8n, with real numbers

Before building, here is the honest comparison for one concrete job: 100 requests against an API that allows a burst of 20 and a sustained 1 request per second.

| Approach | How it paces | Time for 100 requests | Burst behaviour | Where it breaks |
|---|---|---|---|---|
| Wait node, fixed 1 s after every request | Flat 1 request/second, always | ~100 s, even when the API is idle | No burst allowed — request 1 waits like request 99 | Wastes idle capacity; still wrong if the real limit is 20/minute (you need a 3 s wait you have to compute by hand) |
| Loop Over Items, batch 10 + Wait 6 s | 10 at once, pause, repeat | ~60 s | Bursts of 10 regardless of the API's actual burst limit | If the API allows only 5 in a second, every batch still opens with five instant 429s |
| Token bucket (capacity 20, refill 1/s) | Spend from the bucket; wait only when it is empty | ~80 s first run, ~80 s steady — but the first 20 are instant | Burst of exactly 20, matching the API | Needs shared state, so multi-worker setups need Redis instead of static data (see Limits) |

**The token bucket is the only option whose pacing adapts to both the burst limit and the time since the last run.** The other two hard-code one number and hope it matches a limit that has two.

## Step 1 - Put the gate inside a one-item loop

Why this step exists: the gate must make a decision *per request*, and it must run *sequentially* — two gate checks running in parallel can both see the same token and both spend it. A loop with batch size 1 gives you that sequence for free.

1. Where your workflow currently feeds items into the HTTP Request node, insert a **Loop Over Items (Split in Batches)** node.
2. Set **Batch Size** to `1`.
3. Wire the loop as: Loop Over Items → **Code node (Step 2)** → **Wait node (Step 3)** → **HTTP Request node** → back into Loop Over Items. Connect whatever came after the HTTP node to the loop's **Done** output.

You should see the HTTP Request node inside the loop body, executed once per item, in order.

> **Note:** If your HTTP Request node was relying on n8n's built-in per-item iteration (most nodes process all input items automatically), batch size 1 changes nothing about the results — only about the pacing. Each item still gets its own request and its own response item.

## Step 2 - Add the Token Bucket Gate Code node

Add a **Code** node after the Loop Over Items node, set it to **Run Once for Each Item**, name it `Token Bucket Gate`, and paste this:

```javascript
// Token Bucket Gate — one decision per request.
// State lives in workflow static data: { tokens, lastRefill }.
const CAPACITY = 20;       // burst size: max tokens the bucket holds
const REFILL_PER_SEC = 1;  // sustained rate: 1 token = 1 request per second
const COST = 1;            // tokens this request spends

const bucket = $getWorkflowStaticData('global');
const now = Date.now();

if (bucket.tokens === undefined) {
  bucket.tokens = CAPACITY;   // first ever run: start with a full bucket
  bucket.lastRefill = now;
}

// Lazy refill: tokens = min(capacity, tokens + elapsed * refill rate)
const elapsedSec = (now - bucket.lastRefill) / 1000;
bucket.tokens = Math.min(CAPACITY, bucket.tokens + elapsedSec * REFILL_PER_SEC);
bucket.lastRefill = now;

let waitSeconds = 0;
if (bucket.tokens >= COST) {
  bucket.tokens -= COST;                       // spend and go now
} else {
  // Not enough tokens: how long until the refill covers the shortfall?
  waitSeconds = Math.ceil((COST - bucket.tokens) / REFILL_PER_SEC);
  bucket.tokens = 0;                           // the Wait node downstream
                                               // lets real time pass, and the
                                               // next item's refill counts it
}

return [{
  json: {
    ...$json,
    bucket_wait_seconds: waitSeconds,
    bucket_tokens_after: Math.round(bucket.tokens * 100) / 100,
  },
}];
```

Here's what each key does:

- **`$getWorkflowStaticData('global')`** returns a small object that persists across executions of *this workflow* — the bucket's memory. `global` scope means every node in the workflow shares the same object; we only store two numbers in it.
- **`CAPACITY` / `REFILL_PER_SEC`** are the two numbers from your API's documentation: burst limit and sustained rate. An API that says "600 requests per minute, bursts of 50" becomes `CAPACITY = 50`, `REFILL_PER_SEC = 10`.
- **Lazy refill** (the `elapsedSec` block) is the formula from the explainer above. There is no timer node dripping tokens in; each gate run tops the bucket up mathematically from the timestamp of the last run.
- **`waitSeconds`** is a *deficit calculation*, not a guess: `(cost − tokens) / refill rate`, rounded up. With an empty bucket and a refill of 1/second, the next request waits exactly 1 second — the time one token takes to arrive.
- **`bucket.tokens = 0` on the wait branch** is deliberate. The Wait node in Step 3 will let that real second pass, and the *next* item's lazy refill will count it via the timestamp. Nothing is double-counted, and nothing is lost.

> **Warning:** Do not "simplify" this by sleeping inside the Code node (`await new Promise(...)` in a loop over all items). It blocks the worker for the whole batch, defeats n8n's execution model, and still isn't shared state. The Wait node exists precisely to pause an execution without holding it in memory the same way — use it.

## Step 3 - Let the Wait node spend the calculated wait

Add a **Wait** node between the Gate and the HTTP Request node:

1. **Resume** → **After Time Interval**.
2. **Wait Amount** → switch to expression and enter `{{ $json.bucket_wait_seconds }}`.
3. **Unit** → **Seconds**.

Why an expression and not a fixed value: most items will carry `bucket_wait_seconds: 0` (the bucket had a token ready) and pass through instantly. Only items that arrive at an empty bucket pause, and only for exactly the seconds the gate calculated. This is the difference between the token bucket row and the fixed-Wait row in the table above.

Then, as a safety net on the **HTTP Request** node itself, open **Settings** and set **Retry on Fail** to 3 tries with a 5-second wait between tries. The gate makes 429s rare; the retry covers the cases the gate cannot see — for example, a *different* workflow or a colleague's script spending from the same API quota.

You should see, on a manual test run with a handful of items, `bucket_wait_seconds: 0` on the first items in the Gate node's output panel.

## Step 4 - Activate the workflow, because static data only persists in production

This is the step everyone skips, then concludes static data "doesn't work". **Workflow static data is only saved after a successful production execution** — a workflow triggered by its real trigger while **Active**. Manual test executions from the editor do not persist it: the docs and a long [community thread on static data not persisting](https://community.n8n.io/t/workflow-static-data-not-persisting-between-production-executions/255097) both trace "it resets every run" reports back to this.

1. Toggle the workflow to **Active**.
2. Trigger it the real way (its schedule, webhook, or trigger node — not the editor's Execute button).
3. Let it complete successfully once. An execution that errors before finishing does not save the updated bucket either.

**Verify everything works:** Run the production workflow with 25 items queued. Open the Gate node's output across the execution. You should see the first 20 items with `bucket_wait_seconds: 0` and `bucket_tokens_after` counting down 19, 18, 17…; items 21–25 should each show `bucket_wait_seconds: 1`, and the whole execution should take roughly 5 seconds longer than the raw API calls alone — 5 items × 1 second of refill. Run it again immediately: this time the bucket starts empty, so *every* item waits about 1 second. Run it a third time after a 30-second pause: the bucket has refilled to its cap of 20, and you get the free burst again. That third run is the proof the algorithm — not a fixed delay — is doing the pacing.

## Limits and when NOT to use this

Honesty section, because this pattern has sharp edges:

- **One workflow, one bucket.** Static data is scoped to a single workflow. Two workflows calling the same API each keep their *own* bucket of 20, so together they can burst 40 against a limit of 20. If several workflows share one API quota, they must share one bucket — which means shared storage, below.
- **Queue mode and multiple workers break it.** In n8n queue mode, executions run on different worker processes, and static data is not a reliable, atomic store across them: two workers can read the same token count concurrently and both spend it. The community consensus in the thread linked in Step 4 is the same as the official guidance for hot-path state: move the bucket to **Redis** (an atomic Lua script or `INCR`-with-timestamps pattern) or a database row with locking. The algorithm is identical; only the store changes.
- **The bucket does not read the API's mind.** If the provider lowers your quota, or another system shares your API key, you can still get a 429. Keep the Step 3 retry, and if the API returns a `Retry-After` header, honour it — it overrides your refill math for that request.
- **Don't use it for one-off calls.** A workflow that makes three API calls an hour has no rate-limit problem. The gate earns its place at roughly the point where a loop exceeds the API's documented burst limit.

You now have a rate limiter that behaves the way the APIs limiting you behave: a bucket of 20 tokens in workflow static data, lazy refill at 1 token per second, a per-request spend, and a Wait node that pauses only for the calculated deficit.

## Key Takeaways

1. **429 means you outran a token bucket** — most APIs throttle with capacity (burst) plus refill rate (sustained), like AWS ECS's documented 50 tokens at 20/second.
2. **A fixed Wait is the wrong shape for a two-number limit.** It cannot burst after idle time, and one delay value cannot match both a per-second and a per-minute limit.
3. **The whole algorithm is one formula:** `tokens = min(capacity, tokens + elapsed × refill)`, spend if you can, otherwise wait `(cost − tokens) / refill`.
4. **In n8n, the bucket fits in two numbers of workflow static data** plus a Code node gate and an expression-driven Wait node — but it only persists on successful *production* executions.
5. **Static data is a single-workflow, single-process store.** Shared quotas or queue mode mean the same algorithm on Redis, not a bigger bucket.

Next: take the workflow that most recently died on a 429, read its API's rate-limit page, and set `CAPACITY` and `REFILL_PER_SEC` to the two documented numbers before you change anything else. If you are not sure whether your limit is being shared, check whether the same API key appears in any other workflow first — that decides static data versus Redis, and it decides it before you write a line of code.
