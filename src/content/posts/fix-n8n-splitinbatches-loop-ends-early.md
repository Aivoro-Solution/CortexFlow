---
title: "Fix n8n SplitInBatches Loop Ending Early: Execution Says Success but Items Are Missing"
description: "Your n8n loop processes 49 of 350 items, then ends with 'success' and no error. A node returning zero items silently kills the loop — here are 5 fixes."
date: 2026-11-09
category: automation
tags: ["n8n", "splitinbatches", "loop", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-splitinbatches-loop-ends-early.webp"
---

You run a workflow that loops over 350 records. It processes 49 of them, then stops. The execution status reads **success**. There is no error, no failed node, no red banner — and the loop's Done branch never fires. The remaining 301 records simply never happen, and nothing in n8n tells you why.

This is one of the most reported silent-failure patterns in n8n, and it has a single root cause: **a node inside the loop returned zero items, and n8n treats zero items as "nothing left to do"**. The branch halts, the loop never gets its next batch, and the execution ends as if everything worked. By the end of this article you will know how to find the exact node that starved your loop, fix it in about ten minutes, and add a count check so it can never silently eat your data again.

Quick definitions before we start: **SplitInBatches** (also called Loop Over Items) is n8n's loop node — it hands your workflow one batch of items at a time (often one item), and you wire the last node in the loop back to it until the items run out, at which point it fires its Done output. **Always Output Data** is a per-node setting (Settings tab) that makes a node emit one empty item `{}` instead of nothing when it finds no results. **An item** is n8n's unit of data flowing between nodes — one JSON object per row, record, or message. If a node outputs zero items, the next node in line never runs at all.

This is a real, still-open bug at the sharp end: [GitHub issue #39746](https://github.com/n8n-io/n8n/issues/39746) (filed September 28, 2026) shows a Data Table lookup with `alwaysOutputData: true` nested inside a SplitInBatches loop still emitting zero items — reproduced 7 out of 7 times in both manual and production runs. The same silent-stop pattern has been reported on the [n8n forum](https://community.n8n.io/t/newbie-problem-loop-ends-before-every-item-has-been-looped/198427) for years, with the same fix confirmed again and again. As of November 9, 2026, issue #39746 has no released fix, so the workarounds below are the fix.

**Prerequisites:** an n8n instance (Cloud or self-hosted, any 2.x version as of November 2026), a workflow with a SplitInBatches loop, and access to its Executions list.

> **Note:** this article is about loops that end early with a success status. If your workflow never triggers at all — no execution, no error, nothing — that is a different failure, covered in [Fix n8n Workflow That Silently Stopped Triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/). If your loop fails with "Cannot resolve paired item", see [Fix n8n "Cannot Resolve Paired Item" Error](/blog/fix-n8n-cannot-resolve-paired-item/).

## The symptom: what the failure actually looks like

The failure has one consistent fingerprint:

1. The workflow runs and the execution status is **Success** — green, no error anywhere.
2. The loop ran fewer times than you expected. Real reports from the forum: 49 loops out of 350 Salesforce records, 42 out of 81 items, 4 out of 7 items, 1,168 out of 5,852 CSV rows.
3. The **Done** output of the SplitInBatches node never fires, so anything wired after the loop — a summary email, a Slack message, a status update — never runs either.
4. Re-running the workflow gives the same count, or a different-but-still-short count, depending on which item happens to hit the empty result first.

**How to confirm in one minute:** open the execution, click the SplitInBatches node, and look at its context data. In the #39746 report, n8n's own bookkeeping showed `"done": false, "noItemsLeft": false` — the loop knew it was not finished, yet the execution stopped anyway with status `"success"`. If your Done branch has no output and the loop's run count is lower than your input count, you have this bug, not a data problem.

## The root cause: zero items means "stop", not "skip"

n8n's execution model has one rule that catches almost everyone: **a node only runs when it receives at least one item**. When a node returns zero items — a database search with no matches, a Filter node that matches nothing, an HTTP request that returns an empty array, a lookup with no matching row — the node itself reports success, and then nothing downstream of it runs. There is no error, because from n8n's point of view nothing went wrong. The data simply ran out.

Inside a loop this is fatal, because the loop only advances when the last node in the loop hands control back to SplitInBatches. If any node in the middle of the loop returns zero items, the hand-back never happens. The loop does not error, does not retry, and does not fire Done — it just stops, and the execution is marked successful.

There are four ways this bites in practice:

| Trigger | What happens | Where it hides |
|---|---|---|
| A search/lookup returns no rows for one item | The loop dies on that item; all later items are skipped | Data Table, Postgres, Google Sheets, Notion nodes |
| An IF node's false branch is not connected | The item falls off the false output into nothing | Any IF node inside the loop |
| A Filter node matches nothing | Zero items out, loop stalls | Filter node inside the loop |
| `alwaysOutputData` is set on the wrong node | The setting only helps on the node that returned nothing — on the loop node itself it does nothing | SplitInBatches node settings |

The last row is the #39746 trap, and it deserves its own section because it is the one case where the standard fix does not work.

## Step 1 - Find the node that starved the loop

Before changing anything, find exactly where the execution stopped. Guessing wastes the most time on this bug.

1. Open **Executions**, find the short run, and open it.
2. Look at the run count on each node inside the loop. The loop ran N times, so every node in the loop should show N runs — except one. The node with a lower count, or the node right after the last node that ran, is the one that returned zero items.
3. Click that node and check its output for the final iteration. You will see an empty output — `[[]]` (zero items) — with a success status.

**You should see:** one node whose output is empty on the iteration where the loop stopped. That node is the whole diagnosis. Everything after this step is fixing that node, not the loop.

> **Note:** check the *last* iteration, not the first. The node may return rows happily for 48 items and return nothing on the 49th. The empty result on the failing item is the evidence.

## Step 2 - Enable "Always Output Data" on the node that returned nothing

This is the fix the n8n team and forum regulars give for the common case, and it works whenever the node in question is a plain lookup, search, or HTTP node that is not buried in the nested-loop case from Step 4.

1. Click the node you identified in Step 1.
2. Open its **Settings** tab.
3. Turn on **Always Output Data**.
4. Save the workflow and re-run it with the same input.

What this does: instead of emitting zero items when it finds nothing, the node emits exactly one empty item `{}`. That single item is enough to keep the chain alive — the next node runs, the loop hands control back to SplitInBatches, and the remaining items get processed. The empty item carries no data, so downstream nodes that reference fields will see `undefined` for that iteration; if that matters, add an IF node after it checking `{{ $json.fieldName }}` is not empty before doing real work.

**Verify:** re-run the workflow and compare counts. The loop's run count should now equal your input count (350 in, 350 loop runs), and the Done branch should fire. If the count is still short, you are in the #39746 case — go to Step 4.

> **Warning:** do not enable this on the SplitInBatches node itself expecting it to fix the loop. The setting only forces output from the node it is set on. Setting it on the loop node while the lookup inside the loop still returns zero items changes nothing — this is exactly the misunderstanding behind issue #39746.

## Step 3 - Wire the IF node's false branch back to the loop

If the node that starved the loop is an IF node (or a Filter node), the problem is usually a dead branch, not a setting.

An IF node has two outputs: true and false. If you only connected the true output, every item that evaluates to false falls off the end of the workflow. The loop never sees it again, and Done never fires. The forum thread on this exact shape — a date check inside the loop where the last item was older than 7 days — ended with the workflow stopping on the final false item, with "workflow successfully completed" as its only message.

Fix it like this:

1. Connect the IF node's **false output** back to the SplitInBatches node's input (or to the Wait node that leads back to it, if your loop has a pacing delay).
2. If the false branch should skip the rest of the loop body but still count the item as processed, that single wire is the whole fix — the item returns to the loop and the next batch starts.

**Verify:** run the workflow with an input set where the last item evaluates to false. The loop should complete and Done should fire. If wiring false back to the loop risks an infinite loop in your workflow (it can, if the loop body can re-emit the same item), use the exit check below instead.

### The clean-exit check: `noItemsLeft`

If you want the loop to exit explicitly rather than relying on the Done branch, add an IF node right after SplitInBatches with this expression, set to boolean:

```javascript
{{ $node["SplitInBatches"].context["noItemsLeft"] }}
```

Replace `"SplitInBatches"` with your loop node's actual name. When this is true, the loop has no items left — route the true branch to whatever should run after the loop. This is the pattern from the n8n forum's own FAQ answer for "last node never executed with SplitInBatches and IF statement", and it works even when Done misbehaves.

## Step 4 - The #39746 workaround: pre-fetch the lookup before the loop

This is the case where Steps 2 and 3 do not help. In [GitHub issue #39746](https://github.com/n8n-io/n8n/issues/39746), a Data Table "get" node with `alwaysOutputData: true`, nested several levels deep inside a SplitInBatches loop after an IF branch, still emitted zero items when no rows matched — and a Code node placed immediately downstream, also with `alwaysOutputData: true`, was **never invoked at all**. The execution reported `"status": "success"` while the loop's own context showed `"done": false, "noItemsLeft": false`. The reporter reproduced it 7 out of 7 times, in manual and production runs, on an instance running `executionMode: scaling` (single-main).

The lesson: **do not put a lookup that can return zero rows inside a loop that also branches**. Restructure so the lookup can never starve the loop:

1. Move the lookup **before** the SplitInBatches node. One Data Table (or Postgres, or Sheets) "get" with return-all enabled, fetching the whole lookup table once. This node always returns items, because it runs outside the loop.
2. Inside the loop, add a **Code node** right after SplitInBatches that looks the current item up in the pre-fetched rows and supplies defaults when there is no match. The Code node always receives the batch item as input, so it always runs:

```javascript
// Look up the current item in the table fetched BEFORE the loop.
// Runs for every batch item, even when there is no matching row.
const rows = $('Lookup Cadence Map').all();
const match = rows.find(r => r.json.segment === $json.segment);

return [{
  json: {
    ...$json,
    cadence_id: match ? match.json.cadence_id : '',
    cadence_found: Boolean(match)
  }
}];
```

Replace `'Lookup Cadence Map'` with the name of your pre-fetch node, and `segment` / `cadence_id` with your own match key and fields. The `...$json` spread keeps the batch item's data; the fallback `''` keeps the chain alive with an explicit "no match" value instead of a missing field.

3. Downstream, branch on `cadence_found` with an IF node instead of relying on the lookup returning rows. Both branches must be wired — true to the work, false back to the loop (Step 3).

**Why this works when Always Output Data does not:** the Code node is fed by the loop itself, not by the lookup. The lookup's zero-row result can no longer kill the branch, because the lookup is no longer in the branch. The "check if a state row exists yet, proceed with defaults if not" pattern — the exact pattern #39746 says is blocked — works again, because the default is produced by a node that always runs.

**Verify:** run the workflow with an input item that has no matching row in the lookup table. The loop should process it, `cadence_found` should be `false`, and the loop should continue to the next item and finish with Done firing.

> **Note:** if your lookup table is huge (tens of thousands of rows), pre-fetching it all is wasteful. Fetch it once with a Filter or a limited query that returns only the rows your batch could match, or page it in chunks before the loop. The point is that the fetch happens outside the loop, not how many rows it returns.

## Step 5 - Fix the loop repeating the first item

A related loop bug with the same silent symptom: the loop runs the right number of times, but every iteration processes the **first** item's data. Your Notion or Sheets writes all land on the same record, and the execution still reports success.

The cause is a stale reference: nodes further down the workflow point directly at the Trigger node (or another upstream node) instead of at the current batch item. n8n reuses item 0 from the referenced node, so every iteration reads the first item.

Fix it in one move: right after SplitInBatches, add a **Code node** with this single line:

```javascript
return $input.all();
```

Then change every downstream expression that references the trigger (for example `{{ $('Google Calendar').item.json.title }}`) to reference this Code node instead. The Code node re-emits the currently active batch item as the local reference, so each iteration sees its own data. This is the confirmed fix from the [forum's Tips & Tricks post on the bug](https://community.n8n.io/t/solution-found-split-in-batches-always-repeats-the-first-item-here-s-the-fix/171549).

**Verify:** run with three distinct items and check the output of the last node in the loop — you should see three different records, not the first one three times.

## Step 6 - Verify the loop actually finished

Do not trust the green "Success" status — this whole bug exists because success lies. Add a count check that proves the loop finished:

1. Connect an **Aggregate node** to the SplitInBatches **Done** output and set it to count the items that came out of the loop.
2. After the Aggregate node, add an **IF node** comparing the processed count to the expected count. The expected count is the number of items that entered the loop — capture it before the loop with a Set node, for example `{{ $json.expectedCount }}` set from `{{ $input.all().length }}` on the input node.
3. On mismatch, send yourself an alert (Telegram, Slack, or email). On match, let the workflow end normally.

```javascript
// IF node condition (boolean): did the loop process everything?
{{ $json.processedCount !== $json.expectedCount }}
```

True means items went missing — investigate with Step 1. False means the loop genuinely finished.

**You should see:** processed count equals expected count on every run, and Done fires. The first time the alert fires after this, you will catch the next silent-stop variant in minutes instead of discovering it three weeks later in a half-processed dataset.

## Prevent it next time

- **Never put a lookup that can return zero rows inside a loop.** Pre-fetch before the loop and match in a Code node (Step 4). This one rule kills the worst variant of the bug.
- **Wire every branch.** Every IF and Filter node inside a loop needs both outputs connected, or an explicit exit check. An unconnected output is a silent kill switch.
- **Keep loops shallow.** A lookup nested three levels deep inside a loop after a branch is where #39746 lives. Flatten the branching before the loop starts.
- **Test with a no-match item before going live.** Add one input row that matches nothing in your lookup, one that fails the IF condition, and one with an empty search result. If the loop survives all three and Done fires, it will survive production.
- **Keep the count check from Step 6 permanently.** It costs two nodes and it is the only thing that turns the next silent failure into a notification.

## Limits and trade-offs

- Issue #39746 is still open as of November 9, 2026, and the reporter flagged it may be specific to `executionMode: scaling` (single-main). If you run queue mode or regular mode, test the nested-lookup case yourself before assuming you are affected — but the pre-fetch restructure in Step 4 is good practice regardless.
- Pre-fetching a lookup table costs one extra read per execution and holds the table in memory for the run. For tables with tens of thousands of rows, filter the fetch to the rows you need.
- "Always Output Data" emits an empty item `{}`. If a downstream node does arithmetic or string operations on fields that do not exist on that empty item, it will error on the empty iteration. Guard with an IF node checking the field exists, or accept the empty iteration as a deliberate skip.
- The `noItemsLeft` context check reads internal loop state. It is a documented community pattern, but it depends on the loop node's context data, which is not part of n8n's public node API — re-check it after major n8n upgrades.

## FAQ

### Why does n8n report success when the loop clearly did not finish?

Because from n8n's point of view nothing failed. A node returning zero items is a valid result, not an error — and when a branch has no items, n8n simply stops executing it. The execution status reflects "no node errored", not "all your data was processed". That is why the count check in Step 6 matters more than the status badge.

### Does "Always Output Data" fix this or not?

Usually, yes — on the node that returned nothing. It does not fix the nested case in GitHub issue #39746, where a lookup with the setting enabled, buried inside a loop after a branch, still emitted zero items. If the setting does not change the count, restructure with the pre-fetch pattern in Step 4 instead of toggling the setting on more nodes.

### My loop ends early but there is no lookup or IF node inside it. What else can return zero items?

Any node whose result depends on the data: an HTTP Request that returns an empty array, a Split Out node given an empty array, a Google Sheets "lookup" with no match, a Code node that returns `[]` for some input, or a node with "Continue on Fail" that failed and produced nothing. Use Step 1 to find it — the diagnosis is always the node after the last one that ran.

### Should I just avoid SplitInBatches and use a Code node loop instead?

No. SplitInBatches is the right tool for paced, per-item work (rate limits, one API call at a time). A Code node loop cannot pace API calls or wait between items. Fix the zero-item handling instead of abandoning the loop node — the patterns above are the standard way to do it.

## Key Takeaways

1. **A node returning zero items halts its branch silently** — the execution still reports success, and the loop's Done branch never fires.
2. **Diagnose by run count, not by error messages** — the node after the last one that ran is the one that returned nothing; n8n's own loop context (`done: false, noItemsLeft: false`) confirms the loop never finished.
3. **Enable Always Output Data on the node that returned nothing** — it emits one empty item and keeps the loop alive. Set it on the lookup, not on the loop node.
4. **For the #39746 case, restructure instead of toggling settings** — pre-fetch the lookup table before the loop and match rows in a Code node with explicit defaults.
5. **Wire every IF false branch back to the loop**, and add a permanent count check after Done — success status alone will lie to you again.

Next: if your workflows keep failing without any signal at all, the monitoring stack in [Fix n8n Workflow That Silently Stopped Triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/) (external heartbeat plus an execution-age guard) catches the cases this article's count check cannot — a workflow that never starts in the first place.

*Sources: [GitHub issue #39746](https://github.com/n8n-io/n8n/issues/39746) (September 28, 2026) · [n8n forum: loop ends before every item has been looped](https://community.n8n.io/t/newbie-problem-loop-ends-before-every-item-has-been-looped/198427) · [n8n forum: SplitInBatches last item hits IF (false)](https://community.n8n.io/t/splitinbatches-last-item-hits-if-false-loop-never-triggers-no-items-left-done-without-causing-infinite-loop/187044) · [n8n forum: iteration count wrong](https://community.n8n.io/t/iteration-not-count-right/82935) · [n8n forum: empty output flow break](https://community.n8n.io/t/empty-output-flow-break/280247) · [n8n forum: SplitInBatches repeats the first item](https://community.n8n.io/t/solution-found-split-in-batches-always-repeats-the-first-item-here-s-the-fix/171549).*
