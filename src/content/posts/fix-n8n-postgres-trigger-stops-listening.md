---
title: "Fix n8n Postgres Trigger Silently Stops Listening (Two Root Causes, Five Fixes)"
description: "Your n8n Postgres Trigger fires fine for hours, then goes silent with no error. Two verified causes and five fixes."
date: 2026-11-11
category: automation
tags: ["n8n", "postgres", "trigger", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-postgres-trigger-stops-listening.webp"
---

Your Postgres Trigger workflow runs perfectly all morning. New rows land in the table, the workflow fires, orders get processed. Then, sometime in the afternoon, it stops. No error. No failed execution. The executions list is simply empty — as if the database went quiet, even though rows keep arriving. Restarting the workflow fixes it, until it happens again a few hours later.

This is a real, long-running failure mode of n8n's Postgres Trigger node, reported in [GitHub issue #13646](https://github.com/n8n-io/n8n/issues/13646) ("Postgres Trigger listening to a channel not responsive after some time"), which was still being re-activated in October 2026. A second, separate failure looks identical from the outside — the trigger never fires in production at all — but has a completely different cause, confirmed in a January 2026 community thread. By the end of this article you will know how to tell the two apart in two minutes, fix each one, and add a guard so a silent trigger can never again swallow a day of production events.

Quick definitions before we start: the **Postgres Trigger node** is n8n's trigger that fires a workflow when a row is inserted, updated, or deleted in a PostgreSQL table. Under the hood it uses Postgres's **LISTEN/NOTIFY** system — n8n installs a small database trigger that sends a notification on a channel every time a row changes, and n8n holds one long-lived database connection open, listening on that channel. **Published mode** is the state a workflow is in after you click Publish — it is the version production actually runs, as opposed to the draft you edit. A **heartbeat** is a tiny scheduled action whose only job is to keep a connection or process provably alive.

## The symptom: two failures that look identical

Both failures share the same visible symptom — the workflow is active, manual runs work, but no production execution ever appears — and the executions list is the first clue. If the trigger fired at first and then stopped after hours, you have the listener-drop failure. If it never fired in production even once, you probably have the multiple-triggers failure.

| | Listener drop (GH #13646) | Multiple triggers in one workflow (community t/255666) |
| --- | --- | --- |
| First fires? | Yes, works for hours | No — never fires in production |
| Manual "Execute workflow" | Works | Works |
| When it goes silent | After roughly 4–24 hours | Immediately, from the first publish |
| Executions list | Executions, then nothing | Empty from the start |
| Root cause | The LISTEN connection dies and is never re-established | Only one trigger node registers when a workflow is published |

The distinction matters because the fixes are different, and the wrong fix wastes an afternoon. The rest of this article handles each in turn.

> **Note:** if your workflow *does* produce executions but they fail, or if it stopped triggering with no executions at all and it uses a Schedule or Webhook trigger instead, that is a different failure — the general silent-stop case is covered in [Fix n8n Workflow That Silently Stopped Triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/), and the draft-vs-published trap in [Fix n8n Workflow Changes Not Taking Effect in Production](/blog/fix-n8n-workflow-changes-not-taking-effect/).

## Step 1 - Prove which failure you have (2 minutes)

Before changing anything, confirm the diagnosis — because "trigger never fires" also happens when the database user lacks permission to create triggers, or when the trigger was dropped by a migration.

1. Open the workflow's **Executions** list. If you see successful executions that stop at some point in the past, with new rows arriving in the table since, you have the listener drop. If the list is empty for the published version while manual runs work, suspect the multiple-triggers failure.
2. Check how many trigger nodes the workflow has. In published mode a workflow can only have **one** trigger node — if you added two or more Postgres Trigger nodes (for example, one watching inserts on `orders` and another watching inserts on `customers`), only one of them is actually registered when the workflow is activated. The others silently never fire. This is expected n8n behavior, confirmed in [community thread t/255666](https://community.n8n.io/t/postgres-trigger-node-not-firing-when-workflow-is-published/255666) (n8n 2.3.6, Docker Swarm with Supabase), and it applies to all trigger nodes, not just Postgres.
3. If there is exactly one trigger node and it worked for hours before going quiet, check whether n8n still holds a listener connection. Connect to Postgres and run:

```sql
SELECT pid, application_name, state, query
FROM pg_stat_activity
WHERE query ILIKE '%listen%';
```

You should see one connection from n8n sitting in `idle` state with a `LISTEN` query. If there is no such row, the listener is gone — the trigger's notification channel has nobody on the other end, which is exactly why rows arrive and nothing happens. Also check the Postgres log around the time the executions stopped for connection resets or restarts; a database restart, a proxy timeout, or a network hiccup can kill the listener without n8n noticing.

4. Confirm the database trigger itself still exists. The node installs a trigger in your database when the workflow is activated; a migration or a restore can drop it without touching n8n:

```sql
SELECT tgname, tgenabled FROM pg_trigger WHERE NOT tgisinternal;
```

If the trigger is missing, deactivate and reactivate the workflow (Step 2) — activation re-creates it.

If the trigger exists, the listener connection is present in `pg_stat_activity`, and there is exactly one trigger node, but nothing fires — check the credential's database user still has permission on the table and schema, and check that the "Trigger On" setting (Insert / Update / Delete) matches the operation actually happening on the table.

## Step 2 - Re-register the listener by deactivating and reactivating

This is the fastest fix for a dropped listener, and the one to try first when the trigger worked and then stopped.

1. Open the workflow and click the **Active** toggle off. Wait a few seconds — deactivation tears down the LISTEN connection and removes the database trigger.
2. Click **Active** on again. Activation re-creates the database trigger and opens a fresh listener connection.
3. Insert a test row in the watched table and confirm a new execution appears within seconds.

This works because the failure is in the long-lived connection, not in your workflow logic. But it is a reset, not a cure: on the reported cases the trigger went quiet again after roughly 4–24 hours, so treat this step as the recovery and Step 3 or 4 as the prevention.

> **Warning:** deactivating and reactivating drops the listener for a few seconds. Any row inserted in that gap produces no notification and is never processed — LISTEN/NOTIFY has no durable history, so a notification nobody is listening for is simply lost. If you cannot afford to lose rows, use the polling replacement in Step 4, which catches up on missed rows by design.

## Step 3 - Keep the listener alive with a 1-minute heartbeat

The workaround reported against issue #13646 is simple: a scheduled event every minute keeps the connection alive, and the trigger stops going silent. The mechanism is the same one that keeps any idle TCP connection from being dropped by a proxy, firewall, or the database itself — regular traffic proves the connection is still in use.

Build a second, tiny workflow:

1. Add a **Schedule Trigger** set to run **every minute**.
2. Add a **Postgres** node that performs a trivial write — for example, inserting a row into a `heartbeat` table:

```sql
INSERT INTO heartbeat (checked_at) VALUES (now());
```

3. Activate the workflow.

That is the whole keepalive: one row a minute, and the connection path between n8n and Postgres stays warm. Keep the heartbeat table small — add a scheduled cleanup, or use `DELETE FROM heartbeat WHERE checked_at < now() - interval '1 day'` in the same workflow once a day, so the table does not grow forever.

This is a workaround, not a guarantee. It treats the symptom (an idle connection being dropped) rather than the cause (n8n not noticing and re-establishing a dead listener). If your trigger still goes quiet with the heartbeat running, move to Step 4 — it removes the fragile connection entirely.

## Step 4 - Replace the trigger with polling (the durable fix)

If the trigger has gone silent twice, stop depending on a push notification that can die without telling you. Polling — asking the database "what changed since I last looked?" on a schedule — is slightly slower (a minute or two of latency instead of seconds) but it cannot silently lose rows, because every run re-reads from a stored watermark.

1. In a new workflow, add a **Schedule Trigger** — every 1 minute for near-real-time, every 5 minutes if the table is busy.
2. Add a **Code** node that reads the last processed row id from the workflow's static data:

```javascript
const staticData = $getWorkflowStaticData('global');
const lastId = staticData.lastId || 0;
return [{ json: { lastId } }];
```

`$getWorkflowStaticData('global')` is n8n's built-in way to persist a small value between executions of the same workflow — it survives restarts, and it is the right place for a watermark.

3. Add a **Postgres** node that fetches only rows newer than the watermark:

```sql
SELECT * FROM orders
WHERE id > {{ $json.lastId }}
ORDER BY id ASC;
```

4. Add a second **Code** node at the end that advances the watermark — but only after the downstream nodes have processed the rows, and only to the highest id actually seen:

```javascript
const staticData = $getWorkflowStaticData('global');
const items = $input.all();
if (items.length > 0) {
  staticData.lastId = Math.max(...items.map(i => i.json.id));
}
return items;
```

5. Move your existing processing steps after the Postgres node, unchanged.

Verify it the same way as the trigger: insert a test row, wait for the next scheduled run, and confirm one execution processes exactly that row — then insert nothing and confirm the next run produces zero items and still updates nothing. The two properties that make this durable are that a missed run is caught by the next one (the watermark has not moved), and that a database restart changes nothing (there is no listener to re-establish).

Use an incrementing `id` or a `created_at` timestamp as the watermark — never a boolean `processed` flag you update in the same query, which risks marking rows processed before they actually are.

## Step 5 - Split multiple triggers into separate workflows

This is the fix for the second failure mode, and it is a design rule rather than a repair: **one trigger node per workflow, always**.

If your workflow has two Postgres Trigger nodes — say one for inserts on `orders` and one for inserts on `customers` — only one registers when you publish, and the other never fires, with no warning anywhere. The community-confirmed fix is to split each trigger into its own workflow, as the original reporter did in thread t/255666.

If the two triggers feed the same downstream logic, keep one trigger node and branch after it instead:

1. Keep a single Postgres Trigger node set to fire on the table that changes most often, or on a combined view.
2. Add an **IF** node (or **Switch**) right after it that routes on the row content — for example, on `$json.table` or a type field — to the branch that handles each case.
3. If the two tables genuinely need independent triggers, create two workflows and use **Execute Workflow** to call a shared sub-workflow for the common logic, so you still maintain the processing in one place.

The same rule applies to mixing trigger types: a workflow with a Postgres Trigger *and* a Webhook trigger publishes with only one of them live. When a trigger "never fires in production but works manually", count the trigger nodes first — it is the cheapest diagnosis in this article.

## Verify it worked

Run this check after whichever fix you applied, before calling the incident closed:

1. Insert one test row in the watched table.
2. Confirm a new execution appears — within seconds for the trigger, within one schedule interval for polling — and that it processes exactly that row.
3. Leave the workflow alone for a few hours, then check the executions list again and compare it against the row count in the table (`SELECT count(*) FROM orders WHERE created_at > <time of fix>`). The counts must match; a gap means the trigger went quiet again.
4. For the polling workflow, confirm a run with no new rows produces zero items and leaves the watermark unchanged.

## Prevent it next time

A trigger that fails silently needs an external witness, because n8n's own error handling cannot see a failure that produces no execution. Two cheap guards cover it:

- **Heartbeat + execution-age guard:** a separate workflow that runs every 15 minutes, queries the executions of the trigger workflow (or simply checks the newest row's `created_at` against the last processed watermark), and alerts you — Telegram, email, Slack — if nothing has been processed for longer than your normal quiet period. The pattern is the same one used for workflows that silently stop triggering in general.
- **Prefer polling for anything money-critical.** The trigger is fine for notifications and low-stakes automation. For orders, payments, or anything where a lost row costs money, the polling workflow in Step 4 is the right default — a minute of latency is cheaper than a lost order.

## Limits and what I did not test

The listener-drop failure has no released fix in n8n as of November 11, 2026 — issue #13646 is still open, and the heartbeat and polling fixes above are workarounds, not patches. I did not reproduce the drop in a lab; the 4–24 hour window and the heartbeat workaround come from the issue reports, and the exact timeout depends on your Postgres, proxy, and network setup, so your instance may go quiet sooner or later than the reported range. The multiple-triggers rule is confirmed behavior, not a bug, and it will not change — design around it. Finally, the polling replacement assumes your table has a monotonic `id` or a reliable `created_at`; tables without either need a different watermark, such as a `processed_at` column you control.

## Key Takeaways

1. **A Postgres Trigger that worked and then stopped is a dead LISTEN connection** — deactivate and reactivate to recover, then add a 1-minute heartbeat or switch to polling so it does not happen again.
2. **A Postgres Trigger that never fires in production is usually a second trigger node in the same workflow** — published workflows register only one trigger; split one trigger per workflow or branch after a single trigger.
3. **LISTEN/NOTIFY loses rows inserted while nobody is listening** — polling with a stored watermark catches up on missed rows by design.
4. **No execution means the trigger never fired** — check the executions list first, then `pg_stat_activity` for the listener connection, then `pg_trigger` for the database trigger itself.
5. **Guard anything silent with an external check** — a 15-minute execution-age guard that alerts you is the only way to notice the next quiet failure before your users do.

Next: if triggers going quiet is a pattern across your instance, read the general silent-stop guide for the heartbeat and execution-age guard patterns — [Fix n8n Workflow That Silently Stopped Triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/) — and apply the same guard to every trigger workflow you run in production.

## FAQ

### Why does the Postgres Trigger stop working after a few hours?

The node holds one long-lived database connection open and listens on a Postgres notification channel (LISTEN/NOTIFY). If that connection is dropped — by a database restart, a proxy or firewall idle timeout, or a network hiccup — n8n does not always notice or re-establish it, so notifications arrive with nobody listening. There is no error because, from n8n's side, nothing failed: the trigger simply never fires.

### Does upgrading n8n fix the Postgres Trigger going silent?

Not as of November 11, 2026 — GitHub issue #13646 is still open with no fixed release. Upgrade anyway for everything else it fixes, but treat the heartbeat keepalive or the polling replacement as the fix for this specific failure.

### Can I use two Postgres Trigger nodes in one workflow?

No — in published mode only one trigger node registers per workflow, and the others silently never fire. Split each trigger into its own workflow, or use one trigger node and branch on the row content with an IF or Switch node.

### Is polling slower than the Postgres Trigger?

Yes, by one schedule interval — typically 1–5 minutes instead of seconds. In exchange, polling cannot silently lose rows: a missed run is caught by the next one because the watermark has not moved. For money-critical workflows, that trade is worth making.
