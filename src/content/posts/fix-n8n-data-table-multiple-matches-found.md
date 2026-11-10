---
title: "Fix n8n 'Multiple matches found' Error: Data Table Get Row(s) Breaks Item Pairing"
description: "Your Data Table lookup works with one item and throws 'Multiple matches found' with two. Always Output Data is the cause — here are the two fixes."
date: 2026-11-10
category: automation
tags: ["n8n", "data-table", "item-pairing", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-data-table-multiple-matches-found.webp"
---

You build a workflow that looks up each incoming item in an n8n Data Table. You test it with one item and it works perfectly. Then production sends two items, one of which has no matching row — and the whole execution fails with **"Multiple matches found"**. Nothing about your data changed. The lookup node is the same. The only difference is item count.

The culprit is a real, confirmed behaviour in n8n's Data Table node: with **Always Output Data** enabled, a "Get row(s)" that finds nothing emits a single empty item — and that one item claims to be paired with *every* input item at once. Any downstream node that reaches back with `$('Node').item` then cannot decide which input it belongs to, and the execution dies. By the end of this article you will know how to prove you have this bug in two minutes, fix it with a two-node restructure, and design lookups so it can never happen again.

Quick definitions before we start: a **Data Table** is n8n's built-in structured storage — a table you create inside n8n and query with the Data Table node, no external database needed. **"Get row(s)"** is the node's lookup operation: it takes each incoming item, applies a filter (for example, "email equals the ticket's email"), and outputs the matching rows. **Always Output Data** is a node setting that forces the node to emit at least one item even when a lookup finds nothing — so downstream nodes still run. **Item pairing** (n8n calls it `pairedItem`) is the invisible link each output item keeps to the input item that produced it; expressions like `$('Split Out').item.json.email` use that link to find "the email from the same item I started with."

This is a verified bug, not a configuration mistake: [community.n8n.io thread 323830](https://community.n8n.io/t/data-table-get-row-s-with-alwaysoutputdata-breaks-item-pairing-for-downstream-node-item-references-when-inputs-and-outputs-differ/323830) (filed October 22, 2026, n8n 2.41.6 on Docker) reproduces it with a clean three-flow workflow, and the accepted answer comes from the n8n community team. A related upstream report, [GitHub issue #39746](https://github.com/n8n-io/n8n/issues/39746), shows the same Always Output Data trap inside Split In Batches loops. As of November 10, 2026, the behaviour is still present in 2.41.6, and the workarounds below are the fix.

**Prerequisites:** an n8n instance (any version from 2.41.x onward exhibits this; the thread was confirmed on 2.41.6), a workflow that looks up items in a Data Table, and the workflow's editor open so you can rewire two nodes.

> **Note:** this article is about the specific "Multiple matches found" error from a Data Table "Get row(s)" with Always Output Data on. If you see "Cannot resolve paired item" after a Code node, a loop, or a Merge, that is a different failure — the item-linking chain breaking in a different place — covered in [Fix n8n "Cannot Resolve Paired Item" / "Can't Determine Which Item to Use" Error](/blog/fix-n8n-cannot-resolve-paired-item/). If your loop ends early with status "success" and items missing, that is the Split In Batches variant, covered in [Fix n8n SplitInBatches Loop Ending Early](/blog/fix-n8n-splitinbatches-loop-ends-early/).

## The symptom: what the failure actually looks like

The reporter's reproduction is the clearest way to see it. Three parallel flows, each feeding a "Get row(s)" node, then an If node checking `hasField('uuid')`, then a Set node. The data table contains two rows: `alice` and `bob`.

| Flow | Inputs | Matches | Result |
| --- | --- | --- | --- |
| Good | alice, bob | 2 | 2 matched outputs — works |
| Partial | alice, bobby | 1 | 1 output; the no-match branch never triggers |
| Broken | alfred, bobby | 0 | No-match branch runs — and throws "Multiple matches found" |

Two things make this bug nasty. First, **the single-item test passes**: with one input and no match, the single empty item pairs to the single input, so everything resolves. The bug only appears when more than one item enters the lookup. Second, **the Partial flow fails silently**: it does not throw, it just drops the unmatched item — the no-match branch never fires, the execution reports success, and a ticket quietly vanishes from the workflow. The Broken flow is actually the lucky one, because at least it errors loudly.

## The root cause: one empty item, paired to every input

Here is what the node does under the hood, as confirmed in the thread:

1. "Get row(s)" runs the filter once per input item.
2. A matched input produces its matching row, with `pairedItem` pointing at that one input. So far, correct.
3. An unmatched input produces **nothing** — unless Always Output Data is on.
4. With Always Output Data on and the *entire* Get returning nothing, the node emits **one single empty item `{}`** — and links it to **all** input items at once.
5. A downstream node that evaluates `$('Split Out').item.json.email` asks n8n: "which input does this empty item belong to?" The answer is ambiguous — it belongs to all of them — so n8n throws "Multiple matches found".

With partial matches the mechanism is slightly different but the outcome is the same class of problem: the node does not create one empty item per missed lookup. The matched rows keep their pairing, the unmatched inputs simply produce no output, and the item count changes mid-workflow. Any downstream node that reaches back with `.item` is now resolving against a different item list than the one it was written for.

**The one-sentence version: once a lookup can return a different number of items than it received, pairing is no longer 1:1, and any expression that reaches back to an earlier node is guessing.**

## Step 1 - Prove it is this bug (2 minutes)

Before rewiring anything, confirm the diagnosis — because "Multiple matches found" can also come from a Merge node with duplicate keys, and the fix for that is different.

1. Open the failed execution and click the node that threw the error. The error message reads exactly **"Multiple matches found"**.
2. Click the Data Table "Get row(s)" node in the same execution and check its output: if it shows **one empty item `{}`** while the node received **two or more input items**, you have this bug.
3. Confirm the pattern: re-run the workflow with a single item that has no match. It should succeed. Add a second non-matching item and re-run. It should fail with the same error.

If the output shows multiple rows instead of one empty item, your error is coming from somewhere else — check the Merge node first, not the Data Table node.

## Step 2 - Fix it with the If Row Exists split (recommended)

This is the cleanest fix, and it is the accepted answer in the thread. The idea is simple: **stop using "Get row(s)" to branch on existence**. Use the two Data Table operations that were built for exactly that — and that forward the original item instead of replacing it.

1. Delete the "Get row(s)" node and the If node that checks `hasField('uuid')`.
2. Add a Data Table node set to the **If Row Exists** operation, with the same lookup condition you had in "Get row(s)" (for example, the column `email` equals `{{ $json.email }}`).
3. Add a second Data Table node set to **If Row Does Not Exist**, with the identical condition.
4. Feed both nodes **directly from the node that produces your items** (in the reporter's workflow, the "Transform data" node) — not from each other.
5. Leave **Always Output Data off** on both nodes.
6. Wire the "match" branch downstream of If Row Exists, and the "no-match" branch downstream of If Row Does Not Exist.

Why this works: both operations **forward the original input item** and preserve its item link, instead of emitting a looked-up row that replaces it. The item count never changes — every input item exits through exactly one of the two branches, still paired to itself — so `$('Split Out').item` always resolves to exactly one input.

> **Note:** if the match branch also needs fields from the stored row, add a "Get row(s)" node **after** If Row Exists, on the match branch only. At that point every item entering the Get is guaranteed to have a match, so the empty-item trap cannot trigger — and the Get's output is a row you actually want, not a branch signal.

## Step 3 - Fix it with pre-fetch plus Merge (when you need the row's fields on every item)

Use this pattern when the branch split is not enough — for example, when every item needs to carry the looked-up row's fields forward whether or not it matched, or when you are doing many lookups and want one query instead of one per item.

1. Add a Data Table node **before** your per-item logic, set to "Get row(s)" with **no filter** — pull the whole table once.
2. Turn **Execute Once** on for that node, so it runs a single time regardless of how many items flow through.
3. Add a **Merge** node, mode **Combine**, operation **Combine by matching fields**. Set input 1 to your items (the field you match on, for example `email`) and input 2 to the table rows (the matching column).
4. Set the Merge output to **Enrich Input 1**: every item comes out carrying its own fields, plus the looked-up row's fields (such as `uuid`) when a match exists — and with no extra fields when it does not.
5. Downstream, branch with a plain If node on `hasField('uuid')` — and read the fields from `$json`, the current item, not from an earlier node.

Why this works: the lookup is no longer per-item, so there is no per-item pairing to break. The Merge does the matching in one place, and every item keeps its own identity throughout. The reporter confirmed this pattern works for 1, 2, or 20 tickets.

## Step 4 - Verify the fix with the three-flow test

Rebuild the reporter's test, or run your own workflow against these three cases:

| Test | Inputs | Expected result |
| --- | --- | --- |
| All match | alice, bob | Both items take the match branch; no error |
| Partial match | alice, bobby | alice takes the match branch, bobby takes the no-match branch; both branches run |
| No match | alfred, bobby | Both items take the no-match branch; no "Multiple matches found" error |

Run the partial-match case twice: once with the items in the order above, once reversed (bobby first, alice second). Pairing bugs love order-dependence — if the reversed run also passes, the fix is real.

> **Warning:** do not "verify" by re-running the original workflow with Always Output Data still on and a single test item. That is exactly the test that hid the bug in the first place. Always verify with two or more items and at least one non-match.

## Prevent it next time: the rule for every lookup node

The pattern that caused this bug is not specific to Data Tables. Any node that can change the item count — a lookup, a filter, a split, a sub-workflow call — creates the same risk. Adopt this rule, which is the reporter's own conclusion after debugging it:

**Once a lookup can return a different item count than it received, carry the data forward on the item itself instead of referencing back with `.item`.**

In practice, that means three habits:

- **Prefer existence operations for branching.** If Row Exists / If Row Does Not Exist, or an If node on a field carried on `$json`, instead of Get-then-branch.
- **Keep the original item alive.** Use Edit Fields or Set to attach the looked-up values to the item you already have, rather than replacing the item with the lookup's output.
- **Never trust a single-item test for a lookup.** Any lookup that runs per item gets tested with zero matches, partial matches, and all matches — at two or more items — before it ships.

The same habit also protects you from the related trap in [GitHub issue #39746](https://github.com/n8n-io/n8n/issues/39746): Always Output Data inside a Split In Batches loop still emits zero items in some paths, so the loop ends early with status "success". The fix there is structural too — pre-fetch before the loop — for the same reason: the node that changes the item count is the node that breaks the pairing.

## What this fix does not cover

- **This is a workaround, not an upstream fix.** The expected behaviour in the thread — one empty item per non-matching input, each paired to its own input — is still not how the node behaves as of n8n 2.41.6. If a future release changes "Get row(s)" to emit per-input empty items, the If Row Exists pattern still works; it just becomes optional.
- **"Multiple matches found" from a Merge node is a different bug.** If your error comes from a Merge with duplicate keys on the matching field, deduplicate the merge inputs first — the Data Table fix above will not help.
- **I did not test this against Postgres-backed Data Tables at scale.** The reproduction used the built-in Data Table on Docker with SQLite defaults. The pairing logic is in the node, not the storage backend, so the behaviour should be the same — but if you run Data Tables on Postgres with thousands of rows, pre-fetching the whole table in Step 3 is a real cost, and the If Row Exists split in Step 2 is the better pattern there.

## FAQ

### Does turning off Always Output Data fix the error?

No — it changes the failure mode. With Always Output Data off, a no-match lookup emits zero items, so downstream nodes never run for that item at all. The error disappears, but so does your no-match handling: the item silently vanishes and the execution still reports success. That is the Partial flow from the symptom table. Turning it off is only correct when you have already replaced the branch with If Row Exists / If Row Does Not Exist.

### Why did my workflow work for weeks and then break?

Because it only ever received one item at a time, or every item matched. The bug needs two or more inputs with at least one non-match. The day a second ticket arrives, or the first genuinely new email address shows up, the workflow that "always worked" starts throwing — and the change looks like a data problem, not a node problem.

### Can I just use a Code node to re-emit the missing items?

You can, but you should not need to. A Code node after the Get that returns `$input.all()` or synthesises an empty item per input re-creates pairing by hand — and it is exactly the kind of manual repair that breaks again the next time someone edits the workflow. The If Row Exists split expresses the same intent in the node's own operations, and it is what the community team recommends.

### Is this the same as the "Cannot resolve paired item" error?

Related, not identical. Both are item-pairing failures, but "Cannot resolve paired item" means the link is broken or missing (typically after a Code node without `pairedItem`, or a loop), while "Multiple matches found" means the link is ambiguous — one output item claims several inputs. The fixes differ: the first needs the pairing rebuilt, the second needs the lookup restructured so pairing is never ambiguous.

## Key Takeaways

1. **Data Table "Get row(s)" with Always Output Data emits one empty item linked to all inputs when nothing matches** — so any downstream `$('Node').item` reference throws "Multiple matches found" as soon as two or more items enter the lookup.
2. **Single-item tests hide this bug completely** — with one input, the empty item pairs to the one input and everything resolves. Always test lookups with partial and zero matches at two or more items.
3. **Replace Get-then-branch with If Row Exists / If Row Does Not Exist** — both operations forward the original item and preserve its pairing, with Always Output Data off.
4. **If every item needs the row's fields, pre-fetch the table once and Merge with "Enrich Input 1"** — the lookup stops being per-item, so pairing can never break.
5. **The general rule: once a node can change the item count, carry data forward on `$json`** — never reach back with `.item` across a lookup.

Next: if your lookups live inside a loop, read [Fix n8n SplitInBatches Loop Ending Early](/blog/fix-n8n-splitinbatches-loop-ends-early/) — Always Output Data has the same class of trap there, and the fix is the same structural one: pre-fetch before the loop. If you hit pairing errors from Code nodes or Merges instead, [Fix n8n "Cannot Resolve Paired Item"](/blog/fix-n8n-cannot-resolve-paired-item/) covers the rebuild.
