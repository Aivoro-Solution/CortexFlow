---
title: "Fix n8n 'Cannot Resolve Paired Item' Error (5 Fixes That Actually Work)"
description: "n8n's 'Cannot resolve paired item' error means the item-linking chain broke. 5 verified fixes — from $json to pairedItem in the Code node."
date: 2026-11-07
category: automation
tags: ["n8n", "expressions", "error-fix", "code-node", "workflows"]
draft: false
featured: false
image: "/og/fix-n8n-cannot-resolve-paired-item.webp"
---

Your workflow runs fine in the editor. Then a real execution hits a node that references data from an earlier step, and n8n stops with:

```
Expression evaluation failed: Cannot resolve paired item for node 'Extract from File'
```

Or its sibling:

```
ERROR: Can't determine which item to use
Paired item data could not be resolved
```

The workflow is not broken in the way you think. The data is there. The expression is (probably) right. What broke is the invisible thread n8n uses to connect one item to the next — and once you understand that thread, this error becomes a five-minute fix. By the end of this guide you will know how item linking works, how to find the node that cut the thread, and the five fixes that resolve it, verified against real community threads.

**Prerequisites**

- An n8n workflow that throws a paired-item error (any version; the examples below use n8n 2.x, as of November 2026).
- Access to the workflow editor and the Executions tab, so you can inspect a failed run.
- Basic familiarity with n8n expressions (`$json`, `$('Node Name')`). If the whole items model is new to you, read [n8n Items & Expressions: The Mental Model](/blog/n8n-items-expressions-mental-model/) first — this post is the error-fix companion to it.

## The symptom checklist

Confirm you are hitting this exact bug and not a lookalike before changing anything:

1. **The error names a node you are not currently in.** `Cannot resolve paired item for node 'Extract from File'` appears in a *later* node (Edit Fields, Google Sheets, an HTTP node). The failing node is fine; the named node is the one whose link broke.
2. **It works in the editor, fails in production.** The editor tests with one pinned item, so pairing usually resolves. Real executions with multiple items, loops, or branches are where the link snaps.
3. **It is intermittent.** The same workflow succeeds for some executions and fails for others — typically when the input has more than one item, or when a branch or loop changes the item count mid-run.
4. **A related symptom: the wrong row's data.** Instead of an error, a node silently returns the *first* customer's email for every customer. That is the same broken link, papered over by `.first()` — see Fix 2 for why that is dangerous.

If point 4 sounds familiar, you have the bug even without an error message. Read on either way.

## The real root cause: item linking, not your expression

Every item flowing through an n8n workflow carries hidden metadata — a *paired item* pointer that says "I came from item 3 of the node before me, which came from item 3 of the node before that." This chain is called **item linking**. It is how n8n knows which output item belongs to which input item when you write an expression like:

```js
{{ $('Customer Lookup').item.json.email }}
```

That `.item` does not mean "the current item." It means "follow the pairing chain back to Customer Lookup and fetch the item that *this* item descended from." When the chain is intact, you get the right customer's email. When any node in between broke the chain, n8n cannot land on exactly one item — and you get the error.

Three things break the chain, and they account for nearly every report on the [n8n forum](https://community.n8n.io/t/referencing-a-previous-node-returns-the-wrong-customers-data/321140):

1. **A Code node that creates new items without saying where they came from.** In "Run Once for All Items" mode, if you return brand-new objects, n8n has no pairing information for them. The chain ends at that node. This is the single most common cause.
2. **Nodes that reshape items: Merge, Aggregate, Split In Batches (Loop Over Items), and some community nodes.** Merging two streams or aggregating many items into one creates outputs with ambiguous or missing lineage. AI Agent and Wait nodes can also drop or alter pairing metadata mid-chain, which is why the error loves agent workflows.
3. **A branch or filter that changes the item count or order.** After an If node or a filter, the surviving items no longer line up one-to-one with the earlier node's items, so `.item` cannot resolve.

The n8n documentation is explicit about the core rule: `.item` fails when the link points to more than one item in the earlier node, because n8n cannot tell which one you want. The fix is never "try harder with `.item`" — it is to stop depending on the broken link, or to repair it at the node that broke it.

## Fix 1 — Use `$json` for the current item (fastest fix)

If the data you need is already on the item flowing into the node, do not reach back at all. Replace the cross-node reference with `$json`:

```js
// Before — depends on the pairing chain:
{{ $('Loop Over Items').item.json.row_number }}

// After — reads the item already in front of the node:
{{ $json.row_number }}
```

`$json` only ever reads the incoming item. It never touches paired-item tracking, so it cannot trigger this error. This is the fix the forum's top-voted answer recommends first, and it resolves the majority of cases — most people reference an earlier node for data that is already sitting on the current item.

**Verify:** re-run the workflow with two or more items. Each row should carry its own value. If every row now shows the *same* value, the field was never on the current item — move to Fix 5 instead.

## Fix 2 — Use `.first()`, `.last()`, or `.all()[index]` for single-item nodes

When the earlier node returns exactly one item — a config record, an auth token, a settings row — say so explicitly instead of asking n8n to pair:

```js
{{ $('Get Settings').first().json.api_url }}
{{ $('Get Token').last().json.access_token }}
{{ $('Lookup').all()[0].json.email }}
```

The n8n docs recommend this pattern for single-item lookups, and it is the right call there.

> **Warning:** `.first()` is a band-aid, not a fix, for per-item data. It always returns the first item, so `{{ $('Customer Lookup').first().json.email }}` will happily give *every* customer the first customer's email — silently, with no error. If your data varies per item, `.first()` trades a loud failure for a quiet wrong answer. Use it only when the earlier node genuinely returns one item.

**Verify:** run with at least two different input items and check the output per item. If row 2 shows row 1's data, you used `.first()` where you needed Fix 1, 3, or 5.

## Fix 3 — Add `pairedItem` in the Code node (the real repair)

If a Code node is the node that broke the chain, repair the chain there. When your Code node runs in "Run Once for All Items" mode and builds new items, tell n8n which input item each output came from:

```js
return $input.all().map((item, index) => ({
  json: {
    ...item.json,
    total: item.json.price * item.json.quantity,
  },
  pairedItem: { item: index },
}));
```

Here is what each part does:

- `$input.all()` gives you every incoming item with its original index.
- `...item.json` carries the original fields forward, so downstream nodes can use `$json` too.
- `pairedItem: { item: index }` re-attaches the link: output item `index` descends from input item `index`. (A bare number, `pairedItem: index`, works the same way.)

Two details that catch people out:

- **If you filter or reorder, preserve the original index.** Do not assign the new output position — map each surviving item back to the index it came from, or the link will point at the wrong row.
- **n8n warns you about this in the editor.** If the Code node shows "To make sure expressions after this node work, return the input items that produced each output item," that is this fix, stated as a reminder.

**Verify:** after the Code node, add a temporary Edit Fields node with `{{ $('Customer Lookup').item.json.email }}` (or whatever your original failing expression was). It should now resolve for every item, not just the first.

## Fix 4 — Switch the Code node to "Run Once for Each Item"

If your Code node processes items independently — one input in, one output out — you may not need `pairedItem` at all. Change the node's mode from "Run Once for All Items" to **"Run Once for Each Item"** and n8n handles pairing automatically:

```js
// Run Once for Each Item — $input.first() is the current item,
// and n8n pairs the output to it for you.
const item = $input.first().json;

return {
  json: {
    ...item,
    total: item.price * item.quantity,
  },
};
```

This is the simplest correct fix when the logic is per-item anyway. Keep "Run Once for All Items" (with Fix 3) only when you genuinely need the whole batch at once — aggregations, sorting, deduplication.

**Verify:** same as Fix 3 — the downstream `.item` expression should resolve, and a two-item test run should produce two correctly paired outputs.

## Fix 5 — Carry the data forward before it is lost (the bulletproof pattern)

When you cannot repair the chain — an AI Agent, a Wait node, or a community node in the middle drops the metadata and you do not control it — stop reaching back entirely. Attach the fields you will need later to each item *before* the chain-breaking node, using an Edit Fields (Set) node with **"Include Other Input Fields"** turned on:

1. Add an Edit Fields node just before the agent, loop, or Wait node.
2. Add the fields you need downstream (customer ID, email, row number) — or simply turn on "Include Other Input Fields" so everything travels with the item.
3. Downstream, read them with `{{ $json.email }}`. No cross-node reference, no pairing, no error.

This is the pattern the forum's accepted answers converge on for agent and loop workflows: "Stop reaching back 3–4 nodes. Carry the row_number forward and use `$json`." It is also the only fix that survives a chain with *multiple* breaking nodes in it.

**Verify:** run the full workflow end to end, including the agent/Wait/loop section, with two items that have visibly different values (e.g. `alice@example.com` and `bob@example.com`). Confirm each downstream output carries its own value.

## The last resort: rejoin with a Merge node

If none of the above fits — the data lives in a genuinely separate branch and cannot be carried forward — rejoin the two streams on a stable key with a Merge node in **Combine (Merge By Key / Matching Fields)** mode, matching on something immutable like a customer ID or order ID. After the merge, the lookup data is a field on the current item, and `$json` works again.

Two stopgaps exist but should stay stopgaps: `$items('Node Name', 0, $itemIndex)` reads by position instead of pairing, which works only if both nodes always have the same number of items in the same order — a promise loops and filters routinely break. And `.first()`, as above, is only safe for single-item nodes.

## Prevent it next time

- **Never use `$('Node').item` inside loops, AI Agent chains, or after Wait nodes.** Those are the three places pairing is most likely to be dropped. Carry the fields forward instead.
- **Every Code node that returns new items gets `pairedItem` or "Run Once for Each Item."** Make it a code-review rule for your own workflows — n8n's own editor warning is the reminder.
- **Test with two items, not one.** A single-item test run cannot catch a pairing bug; the chain resolves trivially when there is only one candidate. Two items with different values (different emails, different IDs) expose both the error and the silent wrong-row variant.
- **Watch for the silent variant.** If a workflow "works" but every row shows the first row's data, you have a `.first()` band-aid somewhere. Search the workflow for `.first()` on any node that returns more than one item.

## FAQ

### Is "Cannot resolve paired item" a bug in n8n?

Usually no. It is n8n telling you the item-linking metadata was lost — most often by a Code node that returned new items without `pairedItem`. There are genuine edge cases (some community nodes do not set pairing correctly, and AI Agent/Wait chains can drop it), but in those cases the fix is still the same: stop depending on the broken link or repair it at the source.

### Why does the error appear in a node that looks innocent?

The error names the *earlier* node whose link could not be resolved, not the node that broke it. The breaking node sits between the two. Walk backwards from the failing expression through the nodes in between — the Code, Merge, Aggregate, Loop, or AI Agent node in that stretch is your suspect.

### Does upgrading n8n fix this?

No version upgrade removes the error, because pairing is by design: `.item` must resolve to exactly one item. Upgrades have fixed specific pairing bugs in individual nodes, so staying current helps, but a Code node without `pairedItem` will fail on any version.

### What is the difference between `.item`, `.first()`, and `$json`?

`$json` reads the current item only — no pairing involved. `$('Node').item` follows the pairing chain to the matching item in an earlier node — precise, but fails when the chain is broken. `$('Node').first()` ignores pairing and always returns the first item — safe only when the earlier node returns exactly one item.

## Key Takeaways

1. **Paired items are a hidden chain linking each output item to its source input item** — `.item` follows that chain, and the error means the chain snapped somewhere between the two nodes.
2. **The fastest fix is `$json`** — if the data is already on the current item, stop reaching back to an earlier node.
3. **The real repair is `pairedItem` in the Code node** (or "Run Once for Each Item" mode) — that is where most chains break.
4. **`.first()` is a band-aid that can silently return the wrong row's data** — use it only for genuinely single-item nodes.
5. **The bulletproof pattern is carrying data forward** with an Edit Fields node before any loop, agent, or Wait chain, then reading it with `$json`.

Next: audit one workflow that uses `$('Node').item` — search for every `.item` reference, test it with two different input items, and replace any that fail (or silently return the first row) with one of the five fixes above. If your workflow also uses Wait nodes, the [Wait-node timing guide](/blog/n8n-wait-node-timing-explained/) covers the related resume and timeout pitfalls that compound pairing problems.
