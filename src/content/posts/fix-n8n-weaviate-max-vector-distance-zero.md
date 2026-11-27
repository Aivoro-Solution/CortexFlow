---
title: "Fix n8n Weaviate Vector Store Ignoring a Max Vector Distance of 0"
description: "Set Hybrid Max Vector Distance to 0 in n8n's Weaviate node and distant results still return. A falsy-zero bug drops the cap — here is the workaround."
date: 2026-11-27
category: automation
tags: ["n8n", "error-fix", "weaviate", "rag", "vector-store"]
draft: false
featured: false
image: "/og/fix-n8n-weaviate-max-vector-distance-zero.webp"
---

You set **Hybrid: Max Vector Distance** to `0` in n8n's Weaviate Vector Store node — exact vector matches only — and the search still returns distant chunks as if no cap existed. No error appears, and the field still shows `0` in the editor, so the workflow looks correctly configured while retrieval quietly ignores your strictest setting. By the end of this post you will know why `0` is the one value that breaks, how to confirm it in minutes, and how to enforce an exact-match cap until the upstream fix ships.

Quick definitions: **Weaviate** is a vector database — it stores embeddings (numeric representations of text) and finds the closest ones to a query. **Hybrid search** combines keyword (BM25) matching with vector similarity in one query. **Max vector distance** caps how far a result's vector may be from the query vector; a distance of `0` means only exact vector matches pass.

## The symptom: distance 0 behaves like no cap at all

In the Weaviate Vector Store node, use retrieve mode with hybrid search enabled and set **Hybrid: Max Vector Distance** to `0`. Run a search whose collection contains near-matches but no exact vector match. Expected: no results, because nothing is at distance `0`. Actual: results come back anyway, ranked as usual, with no warning that the cap was dropped.

Every other value works. Set the cap to `0.4` and distant results are filtered, exactly as Weaviate's own hybrid documentation describes the parameter ("Maximum threshold for the vector search component"). Only `0` fails — and it fails silently, which is what makes it dangerous in a RAG pipeline: your agent receives chunks you explicitly tried to exclude, and nothing in the execution output says so.

This is a confirmed bug, reported in [GitHub issue #44019](https://github.com/n8n-io/n8n/issues/44019) (opened 2026-11-16, reproduced on master `53c9b488ae`, n8n 2.48.0). The reporter proved it with the node's own unit test before any Weaviate cluster was contacted, so your cluster, credentials, and collection setup are not the problem. The issue names no fixed release as of 2026-11-27, so the workarounds below are the fix for now.

## The root cause: `||` treats 0 as "not set"

The node's option mapping in `VectorStoreWeaviate.node.ts` copies your setting with a logical OR:

```ts
maxVectorDistance: options.maxVectorDistance || undefined,
```

In JavaScript, `0 || undefined` evaluates to `undefined`, because `0` is falsy. So when you enter `0`, the node creates the store client with `maxVectorDistance: undefined` — no cap — and Weaviate never sees your setting.

The store layer underneath already handles this correctly: it passes the value through with the nullish operator (`args.maxVectorDistance ?? undefined`), which keeps `0` and only substitutes `undefined` for `null`/`undefined`. The neighbouring `alpha` option is also kept correctly at `0` (pure keyword search). The bug is a one-character-class mistake in exactly one place: `||` where `??` belongs. That is also why the reporter's unit test fails precisely at `0` and passes for every positive value.

## The fix: use a near-zero cap, filter downstream, or patch the operator

### Step 1 - Confirm you have this bug

You do not need a Weaviate cluster to confirm the mapping bug — the reporter's reproduction is a unit test. If you have the n8n repo checked out:

```bash
cd packages/@n8n/nodes-langchain
pnpm test nodes/vector_store/VectorStoreWeaviate/VectorStoreWeaviate.node.test.ts --maxWorkers=1
```

Change the existing max-vector-distance case to expect `maxVectorDistance: 0` and the assertion fails, because `fromExistingIndex` receives `undefined`. In the UI, the equivalent check is behavioural: run the same hybrid query twice, once with the cap at `0` and once with it at `0.4`. If `0` returns *more* results than `0.4` — or the same distant results — the cap is being dropped. A working cap can only ever return fewer results as it tightens toward `0`.

### Step 2 - Replace 0 with a tiny positive cap

The fastest workaround needs no code: set **Hybrid: Max Vector Distance** to a small positive value such as `0.001` instead of `0`. A positive number is truthy, so `0.001 || undefined` passes `0.001` through to the store, and the cap takes effect.

Be honest about the trade-off: `0.001` is not `0`. It admits vectors within distance `0.001` of the query, which in practice means near-duplicates of the exact embedding rather than bit-identical ones. For most RAG collections — where you set `0` to mean "only if this exact chunk exists" — a `0.001` cap behaves the same, because real chunk embeddings are never that close unless they are effectively the same text. If your use case genuinely requires distance exactly `0` (for example, deduplication checks), use Step 3 or Step 4 instead.

### Step 3 - Enforce the cap downstream when exactness matters

Retrieve with the tiny cap from Step 2 (or a slightly wider one), then add a Code node immediately after the vector store node and drop anything that does not meet your real threshold. Keep the logic in one place so it is easy to remove when the upstream fix lands:

```js
// Keep only exact matches. Remove this node once n8n passes 0 through.
const MAX_DISTANCE = 0;
return $input.all().filter((item) => {
  const d = item.json.metadata?.distance ?? item.json.distance;
  return typeof d === 'number' && d <= MAX_DISTANCE;
});
```

This reads the distance from the returned metadata when your node version exposes it. If your version returns a similarity score instead of a distance, filter on that score with the equivalent threshold for your distance metric — check one real execution's output first and filter on the field that is actually there, rather than assuming. The point of the step is architectural: the cap you care about is enforced by code you control, not by the buggy option mapping.

### Step 4 - If you build n8n from source, patch the operator

The upstream fix is a one-line change in `VectorStoreWeaviate.node.ts` — replace the logical OR with the nullish operator, matching how the store layer and the `alpha` option already behave:

```ts
// before
maxVectorDistance: options.maxVectorDistance || undefined,
// after
maxVectorDistance: options.maxVectorDistance ?? undefined,
```

Then run the unit test from Step 1 with the expectation set to `0`; it should pass. This only applies if you build your own image. On the official Docker image or n8n Cloud, use Steps 2–3 and watch issue #44019 for the release that ships the fix.

## Verify it worked

Run the same hybrid query three times and compare result counts:

1. Cap `0.4` — your baseline set of results.
2. Cap `0.001` (Step 2) — only near-exact matches survive; on a collection with no exact duplicate of the query text, expect zero results. If distant chunks still appear, the value did not save — re-open the node and confirm the field shows `0.001`, not `0`.
3. Cap `0` with the Step 3 filter in place — the vector store node may return candidates, but the Code node output contains only distance-`0` items.

The ordering check is the real proof: tightening the cap must never increase the result count. Before the workaround, `0` breaks that rule; after it, the counts decrease monotonically as the cap tightens.

## Prevent it next time

- **Treat `0` as a real value in every numeric option.** This bug class — `||` swallowing a legitimate zero — is the same shape as any "falsy value" bug. When you configure a threshold, limit, or weight, test the boundary values `0` and `1` explicitly, not just a mid-range value.
- **Assert on retrieval quality, not just execution success.** A RAG workflow that "ran fine" can still be feeding your agent chunks you meant to exclude. Periodically run a query with a known exact match and a known non-match, and confirm the non-match is absent. Silent retrieval drift is the vector-store cousin of a workflow that [silently stops triggering](https://cortexflow.tech/blog/fix-n8n-workflow-silently-stopped-triggering/).
- **Check sibling vector-store settings after upgrades.** Other stores have had their own silent data bugs — for example, [insert-with-clear keeping only the last embedding batch](https://cortexflow.tech/blog/fix-n8n-vector-store-clear-keeps-only-last-batch/) across Milvus, Pinecone, Chroma, and In Memory. After any n8n upgrade, re-run your boundary-value checks before trusting retrieval again.
- **Track the upstream fix.** Watch issue #44019; when a release ships the `??` change, set the cap back to `0`, remove the Step 3 filter node, and re-run the Verify counts.

## Key Takeaways

1. **A max vector distance of `0` is silently dropped** by n8n's Weaviate node — `options.maxVectorDistance || undefined` turns `0` into `undefined`, so no cap reaches Weaviate.
2. **Every positive cap works; only `0` fails**, which makes the bug invisible unless you compare result counts across cap values.
3. **Workaround today:** use a tiny positive cap such as `0.001`, and add a downstream filter when you truly need distance exactly `0`.
4. **The upstream fix is one operator** — `||` to `??` in `VectorStoreWeaviate.node.ts` — confirmed by the node's own unit test on n8n 2.48.0.

Next step: audit your other vector-store workflows for boundary values. If any threshold, weight, or limit is set to `0`, run the tightening test from the Verify section before your next production run.

## FAQ

### Does this affect non-hybrid Weaviate searches in n8n?

The reported bug is in the hybrid options copy (`maxVectorDistance` is a hybrid-search parameter in this node). Plain similarity search does not use this field, so it is not affected by this specific bug.

### Is `0.001` safe to use in production?

For typical RAG retrieval, yes — it admits only near-identical embeddings. If your logic depends on distance being exactly `0`, pair it with the downstream filter in Step 3 rather than relying on the cap alone.

### Which n8n versions are affected?

The reporter reproduced it on master `53c9b488ae` (n8n 2.48.0) with the node's unit test. The issue names no fixed release as of 2026-11-27; check issue #44019 for the version that ships the fix.
