---
title: "Fix n8n HTTP Request Pagination Failing with ERR_INVALID_ARG_TYPE on 204 Empty Responses (GH #43928)"
description: "n8n's HTTP Request node crashes with ERR_INVALID_ARG_TYPE when a paginated API returns 204 No Content. Here's the fix."
date: 2026-11-15
category: automation
tags: ["n8n", "http-request", "pagination", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-http-request-pagination-204-empty-response.webp"
---

Your paginated workflow runs fine for three pages. Then the API sends its last page — a `204 No Content` with an empty body, the standard way of saying "there is nothing more" — and the whole execution dies with `ERR_INVALID_ARG_TYPE`. No pages are returned. No downstream node runs. The completion expression you carefully wrote to handle exactly this case never even gets evaluated.

This is a confirmed bug in n8n's execution engine, filed as [GitHub issue #43928](https://github.com/n8n-io/n8n/issues/43928) on November 14, 2026 (team-assigned, Linear ticket GHC-9768, still open as of November 15, 2026, reproduced on n8n 2.41.3 through master 2.48.0). By the end of this article you will know how to confirm you have hit this exact bug, replace the built-in pagination with a manual loop that handles empty pages correctly, and track the upstream fix.

Quick definitions before we start: **pagination** is the HTTP Request node's built-in feature that follows "next page" links automatically until a completion condition is met. A **204 No Content** is the HTTP status a server returns when a request succeeded but there is deliberately no body — a common way for APIs to signal an empty page. **ERR_INVALID_ARG_TYPE** is a Node.js error code meaning a function received a value of the wrong type; here, Node's `Hash.update()` received `undefined` where it needed a string or buffer.

## The symptom: a crash on the empty page, before the completion check

The failure looks like this. You have an HTTP Request node configured like the reporter's:

- Method: `GET`, Response Format: `JSON`, **Include Response Headers and Status**: enabled
- Pagination mode: **Response Contains Next URL**
- Next URL: `{{ $response.body?._links?.next?.href }}`
- Pagination Complete When: **Other**
- Complete Expression: `{{ !$response.body?._links?.next?.href }}`

The endpoint returns `204 No Content` with an empty body, no `ETag` header, and a missing or zero `Content-Length`. Instead of evaluating the completion expression — which would correctly conclude there is no next link and stop — the node throws:

```text
The "data" argument must be of type string or an instance of Buffer, TypedArray, or DataView. Received undefined
```

Error code: `ERR_INVALID_ARG_TYPE`.

Two details make this bug nasty. First, it strikes in two places: on an **empty first page** (an API with zero results) and on an **empty page after one or more populated pages** (the normal end of a paginated list). Second, the exact same empty response works fine with pagination turned off — the reporter verified that the 204 returns successfully when the node is not paginating. So the bug is not in the API, the credential, or your expression. It is in the pagination path itself.

**Which workflows are affected?** Any workflow where an HTTP Request node uses built-in pagination against an API that returns a truly empty body on some page — most commonly a `204 No Content` on the last page, or an empty result set on the first page. If your API always returns `200` with an empty array (`[]`) or an empty object (`{}`), you will never see this bug, because the body is never `undefined`.

## The root cause: hashing an undefined body before checking whether to stop

The reporter diagnosed this by reading n8n's source, and the diagnosis has two parts. Both live in code that runs before your completion expression is ever evaluated.

**Part 1 — the duplicate-page hash crashes on an empty body.** When pagination is on, n8n hashes each page's body to detect duplicate pages (a safety net against infinite loops). That hashing happens in `requestWithAuthenticationPaginated`, in `packages/core/src/execution-engine/node-execution-context/utils/request-helpers/pagination.ts`. The code does roughly this:

```ts
if (typeof contentBody !== 'string') {
	contentBody = JSON.stringify(contentBody);
}
```

For a 204 with no body, `contentBody` is `undefined`. And `JSON.stringify(undefined)` returns `undefined` — not the string `"undefined"`, not an empty string, but the value `undefined`. That `undefined` is then passed to Node's `Hash.update()`, which throws `ERR_INVALID_ARG_TYPE`. The completion expression never runs because the crash happens first. The reporter's proposed one-line fix:

```diff
 if (typeof contentBody !== 'string') {
-    contentBody = JSON.stringify(contentBody);
+    contentBody = JSON.stringify(contentBody) ?? '';
 }
```

The `?? ''` supplies an empty string only for hashing. It preserves the original response body, the configured completion conditions, and duplicate-page detection.

**Part 2 — a second crash when full-response output is off.** The reporter found a second failure while testing: when Response Format is `JSON` and **Include Response Headers and Status** is disabled, the HTTP Request node creates an output item with `json: undefined` for the empty response. Its Split Out hint then accesses `returnItems[0].json.data`, which throws:

```text
Cannot read properties of undefined (reading 'data')
```

The proposed fix, in `packages/nodes-base/nodes/HttpRequest/V3/HttpRequestV3.node.ts`, normalizes the missing body when creating the output item:

```diff
 returnItems.push({
-    json: response,
+    json: response ?? {},
     pairedItem: {
         item: itemIndex,
     },
 });
```

This returns a valid empty JSON item, preserves the existing handling of `null`, and leaves full-response output unchanged. The reporter shipped both fixes with regression tests in [PR #43929](https://github.com/n8n-io/n8n/pull/43929) (closed unmerged — the in-house team implements pagination fixes itself, per the reporter's comment) and in the [fork branch `fix/http-pagination-empty-response`](https://github.com/shustovTE/n8n/tree/fix/http-pagination-empty-response). With both fixes, all 21 pagination tests and 100 HTTP Request V3 tests pass; three pagination cases fail without the first fix, and three HTTP Request cases fail without the second.

**Status as of November 15, 2026:** the issue is open and team-assigned (GHC-9768). The latest stable release, 2.47.7 (November 13, 2026), predates any fix, and the bug reproduces against master (2.48.0). There is no fixed version yet — so until the fix ships, the workarounds below are the way to keep paginated workflows running.

## Fix 1 — Replace built-in pagination with a manual loop (recommended)

The key verified fact: with pagination disabled, the same 204 returns successfully. So turn the node's pagination off and drive the paging yourself with a loop. In a manual loop, an empty body is just data — your IF node sees there is no next link and ends the loop, and the pages already fetched stay in the output.

**Prerequisites:** n8n 2.41.3 or later (any version with the bug — the loop works on all of them), and an API whose pages carry a next-page link in the body, as in the reporter's example (`_links.next.href`).

### Step 1 - Turn off pagination in the HTTP Request node

Open the HTTP Request node and disable pagination. Keep Response Format on `JSON` and **Include Response Headers and Status** on — the full-response output shape is what the loop below reads, and it also avoids the second failure mode above.

> **Warning:** do not just switch the pagination mode or rewrite the completion expression. The crash happens before the completion expression is evaluated, so no completion setting can avoid it.

### Step 2 - Seed the first page URL with a Set node

Add an Edit Fields (Set) node before the loop, named `Seed URL`, that outputs one item with the first page's URL:

```json
{
  "nextUrl": "https://api.example.com/items?page=1"
}
```

Replace the URL with your API's first page. This item is the loop's starting point.

### Step 3 - Add a Split In Batches node to drive the loop

Connect `Seed URL` to a Split In Batches node with **Batch Size** set to `1`. This is n8n's standard looping construct: each iteration processes one item, and wiring a later node's output back into this node feeds the next iteration. (The same node is the subject of [Fix n8n SplitInBatches Loop Ending Early](/blog/fix-n8n-splitinbatches-loop-ends-early/).)

### Step 4 - Point the HTTP Request node at the current item's URL

Connect Split In Batches to the HTTP Request node and set its URL to the expression:

```text
{{ $json.nextUrl }}
```

`$json` here is the current loop item, so the first iteration fetches the seed URL and later iterations fetch whatever the previous response's next link was. Pagination stays off; the node makes exactly one request per iteration.

### Step 5 - Add an IF node that checks for a next link

Connect the HTTP Request node to an IF node with a String condition, **is not empty**, on:

```text
{{ $('HTTP Request').item.json.body?._links?.next?.href }}
```

(Adjust `HTTP Request` to your node's actual name.) With full-response output on, the parsed body lives under `json.body`. On a 204, `body` is `undefined`, the optional chaining yields `undefined`, the condition is false, and the loop ends — exactly the behavior the built-in completion expression was supposed to give you. On a populated page with a next link, the condition is true.

### Step 6 - Wire the loop back, and the exit forward

- **IF true branch:** connect to an Edit Fields (Set) node named `Next Page URL` that sets `nextUrl` to `{{ $('HTTP Request').item.json.body._links.next.href }}`, then connect that node's output back to the **Split In Batches** node. This feeds the next page's URL into the next iteration.
- **IF false branch (Done):** connect onward to the rest of your workflow. When the loop ends, the pages already fetched are available upstream as the HTTP Request node's output items — the same outcome the fixed built-in pagination promises.

### Step 7 - Verify it works

Run the workflow against an endpoint whose last page is a 204. You should see a successful execution, one HTTP Request output item per fetched page, and the run ending on the Done branch — no `ERR_INVALID_ARG_TYPE` anywhere. Then test the empty-first-page case (an endpoint that returns 204 immediately): the run should succeed with no pages fetched and exit on the first Done branch. If either case still errors, check that pagination is really off in the HTTP Request node — that is the one setting this workaround depends on.

## Fix 2 — If you control the API, stop sending 204 for the last page

If the API is yours, the cheapest fix is at the source: return `200` with an empty array (`[]`) or an empty object (`{}`) instead of `204 No Content` for the final page. A body that parses to a value — even an empty one — never triggers the hashing crash, because `JSON.stringify([])` is the string `"[]"`, not `undefined`. This is also friendlier to every other client, not just n8n: many HTTP clients and SDKs treat a 204 as "no body at all" and need special handling. If the API is third-party, this option is closed to you — use Fix 1.

## Fix 3 — Self-hosters: track the upstream fix, don't patch node_modules

If you self-host n8n and build from source, the two one-line diffs in the root-cause section above are the fix, with regression coverage in the reporter's fork branch. For everyone else, the correct move is to watch the issue ([GH #43928](https://github.com/n8n-io/n8n/issues/43928), Linear GHC-9768) and the release changelog, and upgrade once a version containing the fix is listed. Do not hand-edit files inside `node_modules` or the Docker image — the change will not survive the next upgrade, and you will have silently forked your install.

## Prevent it next time

- **Add a canary for the empty last page.** Build a small test workflow that pages an endpoint whose final page is a 204 (or an endpoint that returns 204 immediately) and run it after every n8n upgrade. It catches this bug class before production does.
- **Alert on the error code, not just on failed executions.** `ERR_INVALID_ARG_TYPE` from the HTTP Request node is a signature of this bug. If your error workflow or log monitor sees it, the first thing to check is whether a paginated call just hit an empty page.
- **Put the empty-page case in your API contract tests.** Whenever you integrate a new paginated API, test three responses, not one: a full page, a partial last page, and an empty page. The empty page is the one that breaks pagination — in n8n and elsewhere.
- **Prefer `200` + `[]` over `204` in APIs you build.** The 204 is valid HTTP, but an explicit empty collection is unambiguous for every consumer downstream.

## FAQ

### Does this affect all pagination modes, or only "Response Contains Next URL"?

The crash is in the duplicate-page hashing that runs for paginated requests generally, so any pagination mode can hit it when a page comes back with an empty body. The reporter's reproduction used "Response Contains Next URL", which is the most common mode for link-based APIs.

### My completion expression already handles an empty body — why doesn't it work?

Because the crash happens before the completion expression is evaluated. Your expression is correct; it simply never gets the chance to run. That ordering is the bug.

### Is this the same bug as the HTTP Request "Never Error" 401 issue?

No. That is a different bug in the same node — [Fix n8n HTTP Request "Never Error" Returning 401 Forever](/blog/fix-n8n-http-request-never-error-401-token-refresh/) covers a token refresh that never runs because the error is swallowed. This one is a crash in pagination hashing on empty bodies. The two can combine, though: a paginated request with "Never Error" on that hits a 204 will crash the same way.

### Does switching Response Format to Text avoid the crash?

It was not verified by the reporter, and the completion expression would need rewriting anyway because the body would be a string instead of parsed JSON. The manual loop in Fix 1 is the workaround with verified behavior behind it — with pagination disabled, the same 204 returns successfully — so use that instead of guessing at format changes.

### Which n8n versions are affected?

Reported against 2.46.6 (Docker, Postgres, Node.js 26.12.1) and reproduced from 2.41.3 through master (2.48.0). No fixed version exists as of November 15, 2026.

## Key Takeaways

1. **A 204 empty page crashes n8n's built-in HTTP pagination with `ERR_INVALID_ARG_TYPE`** — the duplicate-page hash receives `undefined` because `JSON.stringify(undefined)` returns `undefined`, and the crash happens before your completion expression is evaluated.
2. **Turn pagination off and loop manually** — Split In Batches plus an IF node on the next link handles empty pages correctly, because with pagination disabled the same 204 returns successfully.
3. **Keep "Include Response Headers and Status" on** — turning it off exposes a second crash (`Cannot read properties of undefined (reading 'data')`) on empty JSON responses.
4. **If you own the API, return `200` with `[]` instead of `204`** — an explicit empty collection never triggers the bug.
5. **The upstream fix is two one-line changes** (GH #43928, Linear GHC-9768) with no fixed release yet — watch the changelog and upgrade when it lands.

Next: if your paginated workflows fetch binary data or large pages, check whether the queue-mode-only disk-fill bug applies to you — and keep the manual loop pattern in your toolkit, because it is also the escape hatch when any other built-in pagination assumption breaks.
