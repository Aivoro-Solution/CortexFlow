---
title: "Fix n8n Vector Store Inserts Keeping Only the Last Batch When Clear Is On"
description: "Insert 450 chunks with Clear on and the store keeps 50. Milvus, Pinecone, Chroma and In Memory clear before every batch — here is how to keep all your chunks."
date: 2026-11-26
category: automation
tags: ["n8n", "error-fix", "vector-store", "rag", "embeddings"]
draft: false
featured: false
image: "/og/fix-n8n-vector-store-clear-keeps-only-last-batch.webp"
---

Your RAG ingest workflow runs green. The vector store node reports 450 documents inserted. Then your chatbot answers as if most of the PDF does not exist — because it does not: the store holds only the last 50 chunks. No error, no warning, and the execution log insists everything worked. The cause is a bug in four of n8n's vector store nodes — Milvus, Pinecone, Chroma, and In Memory — where the "clear" option wipes the store again before every embedding batch instead of once per insert. By the end of this post you will know exactly which node and option combinations lose data, how to restructure the insert so every chunk survives, and how to prove the store actually holds what the node claimed to insert.

## The symptom: 450 inserted, 50 stored

Insert a document that splits into more chunks than one embedding batch — a long PDF is the classic case — with the clear option switched on. The defaults make this easy to hit: Embedding Batch Size defaults to 200, so 450 chunks become three batches of 200, 200, and 50. What happens per batch:

1. Batch 1: the store is cleared, then 200 chunks are added.
2. Batch 2: the store is cleared again — batch 1 is gone — then 200 chunks are added.
3. Batch 3: cleared again — batch 2 is gone — then 50 chunks are added.

The node reports 450 items inserted. The store holds 50. Query the store afterwards and only chunks from the tail of the document come back; everything from the first 400 chunks is missing, so retrieval silently answers from a fraction of your source material.

This was reported in [GitHub issue #45221](https://github.com/n8n-io/n8n/issues/45221) (opened 2026-11-25, reproduced against current master with the real insert code and fake embeddings), tracked internally as Linear GHC-9843 and confirmed against the source by an n8n team member the same day. As of 2026-11-26 the issue is open with no merged fix and no fixed version yet, so the restructured inserts below are the fix for now. Note what the bug is *not*: inserts with the clear option off are unaffected, and so are inserts that fit in a single batch — 200 chunks or fewer at the default batch size never trigger a second clear. That is exactly what makes it easy to miss in testing with small documents.

## Which nodes and options are affected

The bug needs three ingredients: a vector store node at version 1.1 or later (the version that introduced batched inserts), the clear option on, and more documents than one embedding batch. The four affected nodes and their clear options:

| Node | Clear option | Clear action that repeats |
|---|---|---|
| Milvus Vector Store | Clear Collection | `dropCollection` before every batch |
| Pinecone Vector Store | Clear Namespace (with a namespace set) | `namespace.deleteAll()` before every batch |
| Chroma Vector Store | Clear Collection | `deleteCollection` before every batch |
| In Memory Vector Store | Clear Store | buffer dropped on every `addDocuments` call |

Three stores are **not** affected: Weaviate (fixed in PR #43518), Redis, and Azure AI Search already clear once per insert. If your ingest uses one of those, this post is a warning about the others, not a repair job.

## The root cause: the clear lives in the per-batch function

A vector store is a database that stores embeddings — numeric vectors produced from text chunks — so a workflow can later retrieve the chunks closest in meaning to a question. In n8n's Insert Documents mode, the shared insert operation (`packages/@n8n/ai-utilities/src/utils/vector-store/createVectorStoreNode/operations/insertOperation.ts`) collects every document from the input, calls a one-time `beforeInsert` hook, then calls the node's `populateVectorStore` function once per embedding batch.

`beforeInsert` is where a one-time clear belongs, and Weaviate, Redis, and Azure AI Search put it there. The four affected nodes still clear inside `populateVectorStore` — the per-batch function — so the clear runs as many times as there are batches. Milvus drops the collection at `VectorStoreMilvus.node.ts`, Pinecone calls `namespace.deleteAll()` at `VectorStorePinecone.node.ts`, Chroma deletes the collection at `VectorStoreChromaDB.node.ts`, and In Memory passes `clearStore=true` into every `addDocuments` call, which drops the buffer each time. The agreed upstream fix mirrors the Weaviate split: move each clear into `beforeInsert` for node versions 1.1+, keeping the existing behavior for version 1, which calls `populateVectorStore` per input item and never calls `beforeInsert`.

## The fix: clear once, then insert everything

Until a release ships that fix, make the clear happen exactly once per ingest. Pick the option that fits your chunk count.

### Step 1 - Raise Embedding Batch Size above your chunk count

The simplest fix: if everything lands in one batch, the clear runs once and nothing is lost. In the vector store node, set **Embedding Batch Size** to a value larger than the total number of chunks the insert will produce — for a 450-chunk PDF, 500 covers it; for a large corpus, use a round number above your expected maximum.

Here is what the setting does: it controls how many documents are embedded and handed to `populateVectorStore` per call. One batch means one `populateVectorStore` call, one clear, and all chunks added after it. You should see the same "inserted" count as before — the difference only shows up when you query the store (see Verify below).

> **Warning:** A bigger batch means one bigger embedding request and more memory held at once. Embedding APIs cap how many inputs a single request may carry, and a batch of several thousand chunks can fail or time out where batches of 200 sailed through. Use this step when your chunk count is in the hundreds, not the tens of thousands — for large ingests, use Step 2.

### Step 2 - Clear the store yourself, then insert with clear off

For large ingests, separate the clear from the insert entirely:

1. Turn the clear option **off** in the vector store node (Clear Collection / Clear Namespace / Clear Store).
2. Clear the store once, outside the batched insert: delete the collection or namespace in the provider's console or API, or run a one-off insert of a single throwaway document with clear on, then switch clear off for the real run.
3. Run the real insert with clear off. Every batch now only adds — nothing wipes the previous batch.

This keeps the default batch size of 200 (and its gentler embedding requests) while guaranteeing the clear happens exactly once, before batch 1. If the ingest runs on a schedule, put the manual clear in its own first step of the workflow so the ordering is enforced by the workflow, not by memory.

### Step 3 - Or split the insert into a clear phase and an append phase

If you cannot clear outside n8n, split the documents into two inserts: a first insert carrying at most one batch worth of chunks (200 or fewer at the default) with clear **on**, followed by a second insert carrying the rest with clear **off**. A Loop Over Items node feeding the store in slices works for the append phase, provided every slice after the first runs with clear off. The first insert empties the store and loads the first slice; every later slice only appends. The one arrangement to avoid is a loop where clear stays on for every iteration — that reproduces the same data loss one slice at a time.

## Verify it worked

Never trust the node's "inserted" count — it reported 450 while storing 50. Query the store and count what is actually there:

1. Add a second node for the same store in Get Many mode (for In Memory, use the same memory key) with a high limit, or check the record count in the provider's console (Pinecone index stats, Milvus collection row count, Chroma collection count).
2. Compare the stored count against the chunk count your splitter produced. They must match exactly.
3. Spot-check the head of the document, not just the tail: query for a phrase from the first page. Before the fix, only tail chunks (chunk 400 onward in the 450-chunk example) exist; after the fix, the first chunk is retrievable.

If the count matches and the head-of-document query returns its chunk, the insert is whole again.

## Prevent it next time

Add a count check to every ingest workflow: after the insert, read the store's record count and compare it with the number of chunks sent, and fail loudly on a mismatch. Silent partial inserts are worse than failed ones — a failed run gets retried, a 50-of-450 run gets trusted. Keep the clear option off by default in shared templates and clear explicitly as a separate, visible step; that habit survives this bug and the next one like it. Watch [issue #45221](https://github.com/n8n-io/n8n/issues/45221) for the fix release — when the clear moves into `beforeInsert`, the clear option becomes safe to use as intended again, but the count check is worth keeping either way.

## Key Takeaways

1. **With clear on, Milvus, Pinecone, Chroma, and In Memory clear before every embedding batch** — only the last batch survives, while the node still reports the full inserted count (GitHub #45221, Linear GHC-9843, open as of 2026-11-26).
2. **The trigger is size**: node version 1.1+, clear on, and more chunks than one batch (default 200). Single-batch inserts and clear-off inserts are unaffected; Weaviate, Redis, and Azure AI Search already clear once.
3. **Fix it by clearing exactly once**: raise Embedding Batch Size above your chunk count for small ingests, or clear the store yourself and insert with clear off for large ones.
4. **Verify by counting the store, not the node output** — and query for a phrase from the first page, since the bug preserves only the document's tail.

Next: if your chatbot has been answering from partial documents, re-run the affected ingests with one of the fixes above before you debug prompts or models — retrieval over 50 chunks cannot answer questions whose evidence sits in the missing 400. For the broader set of silent-failure patterns in self-hosted n8n, see our [self-hosted silent failures checklist](/blog/n8n-self-hosted-silent-failures-checklist/).
