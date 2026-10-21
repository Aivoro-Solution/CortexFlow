---
title: "Fix n8n Data Table Size-Limit Errors After Deleting Rows (VACUUM FULL Guide)"
description: "Deleted rows from an n8n Data Table but inserts still fail the storage limit? Postgres dead tuples are the cause — VACUUM FULL reclaims the space. Exact steps."
date: 2026-10-21
category: automation
tags: ["n8n", "postgresql", "data-table", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-data-table-size-after-delete.webp"
---

You deleted a few thousand rows from your n8n Data Table to make room. You go back to insert new data — and the same storage-limit error fires again: **manual additions are disabled and workflow executions fail on insert or update.** The rows are gone from the UI, but as far as n8n's size check is concerned, nothing changed.

This is not an n8n bug. It is how PostgreSQL handles deletes — and once you see the mechanism, the fix is a single command run in the right place.

## The symptom: rows deleted, size unchanged

The pattern that traps people:

1. A Data Table grows until it hits n8n's storage cap (default **50MB total** across all Data Tables on an instance).
2. Inserts start failing and manual row additions are disabled — the documented behavior when you exceed the limit.
3. You delete a large batch of rows (Data Table node → **Delete rows**, or a CSV re-import after clearing).
4. The table looks empty, but the error **persists**. Nothing you delete frees up a byte.

On self-hosted instances you can raise the cap with the `N8N_DATA_TABLES_MAX_SIZE_BYTES` environment variable, which papers over it — but the underlying table is still bloated, and the next threshold is just further away.

## Root cause: Postgres DELETE never returns disk space

n8n Data Tables live in the n8n database itself (PostgreSQL on typical self-hosted setups, SQLite on the smallest ones). The size check n8n enforces measures the **physical size of that storage**, not the count of visible rows.

PostgreSQL uses MVCC (Multi-Version Concurrency Control): a `DELETE` doesn't remove the row from disk. It marks the old version as a **dead tuple** — invisible to `SELECT`, but still occupying bytes on the page. Dead tuples accumulate with every delete and update, and the table file stays the same size even after you remove every row.

This is exactly why regular maintenance doesn't help the way you'd expect:

- **`VACUUM`** cleans up dead tuples and marks their space as reusable for *future* writes — but **it does not shrink the file** or return space to the operating system. If nothing new gets written, the measured size doesn't move.
- **`VACUUM FULL`** rewrites the entire table into a new, compact file — **this is the only command that returns the space to the OS.**

<figure class="shot">
  <img src="/figures/fix-n8n-data-table-size-after-delete-vacuum-press.svg" alt="Isometric bloat compactor press: a bloated storage drum full of crossed-out dead row slabs feeds a hydraulic VACUUM FULL press with an orange ram head, which squeezes out reclaimed space into a compact drum with a low gauge" loading="lazy" />
  <figcaption>The bloat press, as a machine. The bloated drum holds dead row slabs — deleted but still physically present, which is why n8n's size check still fails. The hydraulic press is <code>VACUUM FULL</code>: it rewrites the table from scratch into a compact drum and returns the freed space to the OS. Plain <code>VACUUM</code> only shuffles slabs around inside the same drum. <strong>Notice:</strong> the orange ram head is the only thing in this chain that actually shrinks the file.</figcaption>
</figure>

## Step-by-step fix

### Step 1: Confirm the bloat is dead tuples

Connect to the n8n database (the Postgres your `docker-compose.yml` or managed DB defines — **not** a business database your workflows talk to; this is the `n8n` database holding the app's own data). Find tables with dead tuples:

```sql
SELECT schemaname, relname, n_live_tup, n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
```

If the table backing your Data Table shows a large `n_dead_tup` with a small `n_live_tup`, that is your smoking gun: dead rows are eating the storage cap.

Measure the physical size before you touch anything:

```sql
SELECT pg_size_pretty(pg_total_relation_size('your_data_table'));
```

Run it again after the fix — this before/after pair is your proof.

### Step 2: Run VACUUM FULL on the table

Pick a maintenance window. `VACUUM FULL` takes an **exclusive lock** on the table — no reads or writes to it while it runs. On a Data Table that is actively being written to by workflows, schedule this during quiet hours or pause the writers first.

```sql
VACUUM FULL your_data_table;
```

For very large tables this can take minutes and needs free disk space roughly equal to the table's current size (it builds the new file alongside the old one before swapping). If you're tight on disk, address that first.

**Managed Postgres caveat:** some managed providers (Neon, Supabase pooler, RDS read replicas) restrict `VACUUM FULL` or require a superuser. On Neon, run it against the direct (non-pooled) connection with a privileged role; on Supabase, the `postgres` role works but not via the pooler. If `VACUUM FULL` is unavailable, the fallback is `TRUNCATE` + re-import of the rows you want to keep, or `pg_repack` where extensions are allowed.

### Step 3: Verify the space came back

```sql
SELECT pg_size_pretty(pg_total_relation_size('your_data_table'));
```

Compare with the pre-fix value — the file should be dramatically smaller. Then check the dead tuples are gone:

```sql
SELECT n_live_tup, n_dead_tup
FROM pg_stat_user_tables
WHERE relname = 'your_data_table';
```

Finally, the real test: insert a row into the Data Table from the n8n UI or a workflow. Manual additions should work again and executions should no longer fail on insert.

### Step 4: If you're on SQLite instead of Postgres

Self-hosted n8n on the default SQLite database has the same bloat behavior with a different fix — SQLite's equivalent is a plain `VACUUM`:

```sql
VACUUM;
```

Run it against the n8n SQLite file (`~/.n8n/database.sqlite` by default) while n8n is stopped. Unlike Postgres's plain `VACUUM`, SQLite's `VACUUM` rebuilds the file and does return space to the OS.

## Prevent it next time

- **Raise the cap deliberately:** `N8N_DATA_TABLES_MAX_SIZE_BYTES` in your `.env` (e.g. `N8N_DATA_TABLES_MAX_SIZE_BYTES=524288000` for 500MB), then restart. Don't just bump it forever — monitor with the size query from Step 1 monthly.
- **Stop mass-deleting as your cleanup strategy:** archive old rows to an external store (a Postgres table your workflows own, S3, a spreadsheet) and `TRUNCATE` or rotate Data Tables wholesale instead of row-by-row deletes that bloat.
- **Schedule bloat checks:** a monthly cron or n8n workflow that queries `pg_stat_user_tables` for high `n_dead_tup` and alerts you catches the next bloat cycle before inserts start failing.

## FAQ

### Why didn't deleting rows free any space at all?

Because n8n's Data Table storage is a PostgreSQL table, and Postgres `DELETE` only marks rows as dead tuples. The physical file keeps its size until `VACUUM FULL` rewrites it. Plain `VACUUM` (including autovacuum) marks space reusable for future writes but never shrinks the file.

### Can I just raise N8N_DATA_TABLES_MAX_SIZE_BYTES instead?

Yes, on self-hosted — it unblocks inserts immediately. But the bloat stays: queries get slower as they scan dead pages, backups grow, and the next cap is only further away. Reclaim the space with `VACUUM FULL`, then set a cap that matches real usage.

### Is VACUUM FULL safe on a production n8n database?

It is correct but not free: it locks the table exclusively and needs disk headroom equal to the table size. Never run it on the whole `n8n` database's `execution_entity` table at peak — scope it to the Data Table's table and do it in a quiet window.

### Does n8n Cloud have this problem?

n8n Cloud runs on managed Postgres under the hood, and the same MVCC mechanics apply — but you can't reach the database directly. If you're on Cloud and deleting rows doesn't clear the size limit, contact n8n support with the table name and ask them to reclaim the space; on self-hosted, this article's steps are yours to run.

## Conclusion

Deleting rows from an n8n Data Table doesn't free the storage cap because PostgreSQL keeps deleted rows on disk as dead tuples — and plain `VACUUM` never shrinks the file. `VACUUM FULL` on the table (in a maintenance window, with the managed-DB caveats above) is the fix that actually returns space to the OS, verified with `pg_total_relation_size` before and after.

Related reading: our guide to [n8n out-of-memory crashes in Docker Compose](/blog/fix-n8n-oom-crash-docker-compose/) covers the other classic self-hosting resource trap.
