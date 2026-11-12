---
title: "Fix n8n 'Building Workflow Dependency Index' Stuck Forever After Upgrade (GH #40246)"
description: "n8n prints 'Building workflow dependency index...' after an upgrade and never finishes — high CPU, zero executions, no error. One SQL delete unblocks it."
date: 2026-11-12
category: automation
tags: ["n8n", "postgres", "upgrade", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-dependency-index-rebuild-loops-forever.webp"
---

You upgrade your self-hosted n8n, restart it, and the startup log prints `Building workflow dependency index...` — and then nothing. No `Finished building workflow dependency index.` line. No error. The main process and Postgres each sit at 45–50% CPU for hours, and not a single workflow executes. Restarting changes nothing; the loop starts again on every boot.

This is a real bug, reported in [GitHub issue #40246](https://github.com/n8n-io/n8n/issues/40246) (October 4, 2026, team-assigned, still open as of November 12, 2026). It hits instances that were upgraded across a big version jump and that deploy workflows from git with `n8n import:workflow`. The good news: the fix is a single, safe SQL statement, and the reporter confirmed the stuck instance finished rebuilding within seconds of running it. By the end of this article you will know how to confirm the diagnosis in two minutes, apply the fix, and stop it from ever happening again.

Quick definitions before we start: the **workflow dependency index** is an internal table (`workflow_dependency`) that n8n rebuilds on startup. It records which workflows call which other workflows, so the editor can show "used by" relationships and so n8n knows what to re-index when a workflow changes. The **versionCounter** is a number stored on every workflow that increments each time you save it in the editor. `n8n import:workflow` is the CLI command that imports a workflow JSON file into an instance — the standard way teams deploy workflows from a git repo.

## The symptom: startup never finishes, CPU burns, nothing runs

The reporter's instance upgraded from 2.10.4 to 2.41.6 in one jump (Docker, queue mode with one worker, Postgres 18). On restart, the log showed the index rebuild starting and never finishing. The main process and Postgres each held 45–50% CPU for **14+ hours** with no executions running. When the loop was finally unblocked, the log said:

```
Finished building workflow dependency index. Processed 12921816 draft workflows, 20 published workflows.
```

Only 15 workflows were actually stuck — the instance had 20 published workflows in total, and the "12,921,816 draft workflows" number is itself a symptom of the loop re-processing the same handful of workflows over and over. The key diagnostic detail: **no error is ever logged**. The only visible signals are the missing "Finished" line, the sustained CPU, and this repeating query pattern in `pg_stat_activity`:

```sql
SELECT id FROM "workflow_entity" WHERE id = $1 FOR UPDATE
DELETE FROM "public"."workflow_dependency" WHERE ("workflowId" = $1 AND "workflowVersionId" <= $2 AND "indexVersionId" < $3 AND "publishedVersionId" IS NULL)
COMMIT
```

If you see that DELETE repeating for the same workflow IDs while the rebuild never completes, you have this bug — not a slow migration, not a corrupt database, and not a hardware problem.

> **Note:** a genuinely large instance can take minutes to build the index the first time after an upgrade. The difference is progress: a healthy rebuild logs `Finished building workflow dependency index.` and moves on. If the line never appears after an hour and CPU stays high with no executions, it is stuck, not slow. Do not confuse this with the Postgres major-upgrade failure — "FATAL: database files are incompatible with server" — which is a different error with a different fix, covered in [Fix n8n "FATAL: database files are incompatible with server" After a Postgres Major Upgrade](/blog/fix-n8n-postgres-database-files-incompatible/).

## The root cause: stale index rows that can never be replaced

The reporter traced the bug by reading `WorkflowIndexService` and `WorkflowDependencyRepository` in n8n 2.41.6 (the code looks the same in `master` and 2.42.2). The rebuild loop works like this:

1. `findWorkflowsNeedingIndexing()` selects a workflow when the smallest `indexVersionId` among its draft rows is below the current index version (currently 2). In other words, any workflow whose index rows were written by the old indexer needs rebuilding.
2. `executeUpdate()` replaces those rows — but its DELETE only matches rows where `workflowVersionId` is below the workflow's current `versionCounter`, or where `workflowVersionId` is at most `versionCounter` **and** `indexVersionId` is below the current version.
3. If a workflow's existing draft rows have `indexVersionId = 1` **and** `workflowVersionId` greater than the workflow's `versionCounter`, **neither DELETE predicate matches**. `acquireLockAndCheckForExistingData()` still finds rows, so the update is skipped entirely.
4. The workflow is still returned by `findWorkflowsNeedingIndexing()` on the next batch, so `buildIndexInternal()` loops — until `LOOP_LIMIT`, which is **1,000,000,000** iterations.

That is the whole bug: a set of rows that can never be replaced, checked forever, with no error and no exit.

How does `workflowVersionId` end up higher than `versionCounter` in the first place? Through `n8n import:workflow`. The command writes the `versionCounter` contained in the JSON file. If you export a workflow, then keep editing it in the UI (each save bumps the counter and the index rows' version), and later re-import the older exported JSON, the import moves `versionCounter` backwards while the old index rows keep the higher version. That alone is harmless while the index rows are version 2 — but the moment an upgrade bumps the index version, those rows become un-replaceable and the rebuild spins forever.

## Step 1 - Confirm the diagnosis (2 minutes)

Run this query against your n8n Postgres database. It lists exactly the rows that can never be replaced:

```sql
SELECT w.id, w."versionCounter", d."workflowVersionId", d."indexVersionId", count(*)
FROM workflow_entity w
JOIN workflow_dependency d ON d."workflowId" = w.id AND d."publishedVersionId" IS NULL
WHERE d."indexVersionId" < 2 AND d."workflowVersionId" > w."versionCounter"
GROUP BY 1, 2, 3, 4;
```

If it returns rows, the diagnosis is confirmed: those workflows are the ones the rebuild keeps re-processing. If it returns nothing, your stuck rebuild has a different cause — check disk space, long-running migrations, and whether another process holds the workflow locks before going further.

You can also confirm from the live side while n8n is running. Connect to Postgres and look at current activity:

```sql
SELECT pid, state, now() - query_start AS running_for, left(query, 120) AS query
FROM pg_stat_activity
WHERE query ILIKE '%workflow_dependency%';
```

You should see the same `DELETE FROM "workflow_dependency" ...` statement repeating for the same workflow IDs. That repetition, combined with rows from the diagnostic query above, is conclusive.

> **Warning:** run the diagnostic query read-only first and note which workflow IDs it returns. You are about to delete rows from an internal index table — that is safe here (the rebuild re-creates them), but do it with a backup of the table in hand, not from memory.

## Step 2 - Back up the index table

Before deleting anything, take a copy of the table so you can restore it if something unexpected happens. From the Postgres container or any `psql` session with access to the n8n database:

```bash
pg_dump -t workflow_dependency -f workflow_dependency-backup-$(date +%Y%m%d).sql <your-n8n-database>
```

Replace `<your-n8n-database>` with your database name. If you run n8n in Docker Compose, run this inside the Postgres container with `docker compose exec postgres pg_dump ...`. This is a small table in most instances — the dump takes seconds.

## Step 3 - Delete the stale rows

This is the reporter-confirmed fix. It deletes only the rows that can never be replaced — draft rows (`"publishedVersionId" IS NULL`) written by the old indexer (`"indexVersionId" < 2`) whose version is ahead of the workflow's current counter:

```sql
DELETE FROM workflow_dependency d USING workflow_entity w
WHERE d."workflowId" = w.id AND d."publishedVersionId" IS NULL
  AND d."indexVersionId" < 2 AND d."workflowVersionId" > w."versionCounter";
```

Here is what each condition does, so you can see why the delete is narrow and safe:

- `d."workflowId" = w.id` — only touch rows belonging to a real workflow.
- `"publishedVersionId" IS NULL` — only draft rows. Published-version index rows are not part of this bug and are left alone.
- `"indexVersionId" < 2` — only rows written by the old (v1) indexer. Rows the current indexer already wrote are untouched.
- `"workflowVersionId" > w."versionCounter"` — only rows whose version is ahead of the workflow's current counter, which is exactly the set the rebuild's own DELETE predicates can never match.

The reporter ran this while the loop was still spinning. The running rebuild then re-inserted the rows correctly and **finished within seconds**, logging the `Finished building workflow dependency index.` line. No workflows were lost, no executions were harmed, and the instance started serving traffic normally.

## Step 4 - Restart n8n and verify the rebuild finishes

If n8n is still running its stuck loop, restart it so the rebuild starts clean:

```bash
docker compose restart n8n
```

Then watch the startup log:

```bash
docker compose logs -f n8n
```

You should see, within seconds to a few minutes depending on instance size:

```
Building workflow dependency index...
Finished building workflow dependency index. Processed <N> draft workflows, <M> published workflows.
```

The `Processed` counts should now be sane — roughly your real number of workflows, not millions. After that, confirm the instance is actually healthy:

1. Open the editor and confirm workflows load and the "used by" relationships show.
2. Trigger one workflow manually and confirm an execution completes.
3. Check Postgres CPU returns to idle in `pg_stat_activity` — no more repeating `workflow_dependency` DELETEs.

If the `Finished` line still does not appear, re-run the diagnostic query from Step 1. If it returns rows again, you may have a second batch of stale rows (for example, rows created by another import after your first delete) — repeat Step 3. If it returns nothing and the rebuild is still stuck, the cause is something else; capture the repeating query from `pg_stat_activity` and the startup log and report it on [issue #40246](https://github.com/n8n-io/n8n/issues/40246).

## Step 5 - Stop it from happening again

The bug is in n8n's indexer, and the upstream fix — dropping the `workflowVersionId <= versionCounter` bound when `indexVersionId` is below the current version, and stopping the loop when a whole batch is skipped instead of relying on `LOOP_LIMIT` — is proposed in the issue but not yet shipped as of November 12, 2026. Until it lands, the prevention is procedural, and it costs nothing:

1. **Never re-import a stale export after editing the workflow in the UI.** If a workflow has been edited since it was exported, re-export it first and import the fresh JSON. The stale `versionCounter` in the old file is what moves the counter backwards and creates the poisoned rows.
2. **If you deploy from git, export from the source of truth.** Make the repo the only place workflows are edited, or make the UI the only place — not both. The moment the same workflow is edited in two places, an old export can carry a lower counter than the database.
3. **Check the startup log after every upgrade.** A healthy upgrade logs `Finished building workflow dependency index.` within minutes. If it does not, run the diagnostic query from Step 1 before the instance burns a day of CPU.
4. **Keep the Step 2 backup habit for upgrades.** Dumping `workflow_dependency` (and the rest of the database) before an upgrade costs seconds and turns any indexer surprise into a restore instead of a rebuild.

## Limits and what I did not test

This fix was verified on one reported instance: Docker, queue mode, Postgres 18, upgrade 2.10.4 → 2.41.6, with the import-from-git deployment pattern. The SQL targets Postgres; n8n Cloud users never see this (Cloud is patched and managed), and SQLite instances use the same code path in principle but the reporter's evidence is Postgres-only, so I would not run the same delete on SQLite without first checking the table contents with the diagnostic query adapted to SQLite.

The workaround also does not fix the underlying indexer logic — it clears the rows the current indexer cannot handle. If you re-import another stale export later, the same rows can come back. That is why Step 5 matters more than Step 3.

## FAQ

### Does deleting rows from workflow_dependency lose my workflows?

No. The table is a derived index, not the source of truth — the workflows themselves live in `workflow_entity`. The rebuild re-creates the deleted rows from the workflow definitions. The reporter confirmed the rebuild re-inserted them and finished within seconds.

### Why does n8n burn 45–50% CPU instead of erroring out?

The rebuild loop has no progress check: it re-processes the same stuck workflows batch after batch until `LOOP_LIMIT` (1,000,000,000 iterations). Each batch issues the same SELECT FOR UPDATE and DELETE, which keeps both the main process and Postgres busy. Nothing fails, so nothing is logged as an error — the only sign is the missing `Finished` line.

### I upgraded but never use import:workflow. Can this still hit me?

The reported trigger is specifically a stale `versionCounter` from an import moving the counter backwards. Without imports, `workflowVersionId` should never exceed `versionCounter`. If your rebuild is stuck anyway, run the Step 1 diagnostic query — if it returns nothing, you have a different problem.

### Is there an official fix version yet?

As of November 12, 2026, issue #40246 is still open and team-assigned, with no fixed release named. The SQL workaround in Step 3 is the accepted interim fix, confirmed by the reporter. Watch the issue for the upstream fix, which is expected to change the delete predicates in `WorkflowIndexService` and add a stop condition when a whole batch is skipped.

## Key Takeaways

1. **"Building workflow dependency index..." with no "Finished" line after an hour means the rebuild is stuck, not slow** — sustained ~50% CPU on n8n and Postgres with zero executions is the signature.
2. **The cause is stale draft rows in `workflow_dependency`** — `indexVersionId = 1` and `workflowVersionId` ahead of the workflow's `versionCounter`, created by re-importing an old export after UI edits.
3. **The fix is one DELETE** — remove only the un-replaceable draft rows; the running rebuild re-inserts them and finishes within seconds.
4. **Prevention is free** — never re-import a stale export; re-export before importing, and check for the `Finished` line after every upgrade.

Next: if you deploy n8n workflows from git, read [Fix n8n Workflow Changes Not Taking Effect in Production](/blog/fix-n8n-workflow-changes-not-taking-effect/) — the draft-vs-published trap is the other half of the same deployment workflow, and it bites the same teams.
