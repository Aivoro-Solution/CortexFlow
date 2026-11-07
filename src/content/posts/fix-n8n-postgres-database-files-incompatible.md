---
title: "Fix n8n 'FATAL: database files are incompatible with server' After a Postgres Upgrade (16→17→18)"
description: "Postgres refuses to start after a tag bump? The fix is dump-and-restore into a fresh volume — verified steps for 16→17 and the Postgres 18 path change."
date: 2026-11-07
category: automation
tags: ["n8n", "postgresql", "docker", "self-hosting", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-postgres-database-files-incompatible.webp"
---

You changed one line in `docker-compose.yml` — `postgres:16` to `postgres:17` — ran `docker compose up -d`, and n8n never came back. The Postgres container exits immediately, and its logs say:

```
PostgreSQL Database directory appears to contain a database; Skipping initialization
FATAL:  database files are incompatible with server
DETAIL:  The data directory was initialized by PostgreSQL version 16, which is not compatible with this version 17.
```

Your workflows, credentials, and execution history are all inside that database. The good news first: **nothing is damaged.** The new Postgres binaries simply refuse to read the old on-disk format, which changes between major versions. Put the old tag back and the container starts again — that is your safety net, and it is also why the fix below works. By the end of this guide you will have n8n running on the new Postgres major version, with your data intact, and a setup that can never hit this error again.

**Prerequisites**

- Self-hosted n8n on Docker Compose with PostgreSQL (the standard `n8n + postgres` stack, as of November 2026).
- SSH or host access to the machine running the stack.
- Your `.env` file, including `N8N_ENCRYPTION_KEY` — without the same key, restored credentials decrypt to garbage.
- About 30 minutes, most of it waiting on the dump and restore.

## The symptom checklist

Confirm you are hitting this exact failure and not a lookalike:

1. **The postgres container exits at once** after a tag change (`16` → `17`, `16` → `18`, or `17` → `18`). `docker compose ps` shows it restarting or exited.
2. **The log names both versions.** `docker compose logs postgres` shows `FATAL: database files are incompatible with server` plus a `DETAIL` line: `The data directory was initialized by PostgreSQL version 16, which is not compatible with this version 17.` (On a 16 → 18 jump the line reads `...not compatible with this version 18.6`.)
3. **n8n itself never starts**, or starts and immediately fails to connect — because its database is down.
4. **It started right after an image-tag change.** No `.env` edits, no volume changes, no host upgrade. One line changed, one container died.

If point 2 is true, stop debugging n8n. This is a Postgres major-version rule, not an n8n bug, and no n8n setting will fix it.

## The real root cause (not what the error says)

PostgreSQL changes its on-disk catalog layout between major versions. The data directory carries a `PG_VERSION` file, and when the server binary's major version does not match it, Postgres refuses to start — deliberately, to avoid corrupting data it cannot understand. In a container this bites harder than on a host, because the image tag *is* the version: editing one line in Compose swaps the entire server binary set under a live data volume.

Two things that mislead everyone on the first pass:

- **"Skipping initialization" is not the problem.** That line just means Postgres found existing data and skipped creating a fresh cluster. The fatal line below it is the whole story.
- **Postgres 18 adds a second trap on top of the first.** From 18 on, the official image keeps its data in a versioned directory — `/var/lib/postgresql/18/docker` — and declares its volume at `/var/lib/postgresql`, not `/var/lib/postgresql/data`. If you point Postgres 18 at the old `/var/lib/postgresql/data` path with `PGDATA`, you get the same `FATAL` error even after a correct dump-and-restore, because the container sees data in the wrong place.

The supported path is dump and restore: take a logical dump with the *new* version's client against the still-running *old* server, then load it into a fresh volume on the new tag. `pg_upgrade` (in-place, needs both binary sets side by side) also exists, but inside Docker the dump-and-restore path is simpler to verify and trivially reversible — which is why this guide uses it.

## Step 1 - Roll back and confirm nothing is lost

Before changing anything, prove your data is intact. Put the old tag back in `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
```

Then restart and check:

```bash
docker compose up -d postgres
docker compose logs postgres --tail 20
```

You should see the normal startup lines and `database system is ready to accept connections`. Then confirm n8n reaches it:

```bash
docker compose up -d
docker compose exec postgres psql -U n8n -d n8n -c "SELECT version();"
```

You should see a row starting `PostgreSQL 16.x`. If n8n's editor loads and your workflows are listed, your data survived the scare. **Do not skip this step** — if the old tag does not start either, you have a different problem (disk, permissions, corrupt volume), and the dump below will fail the same way.

> **Note:** the exact user, database, and service names depend on your stack. The commands below use the common n8n defaults — service `postgres`, user `n8n`, database `n8n`. Adjust `-U` and `-d` to match your `POSTGRES_USER` / `POSTGRES_DB`, and the service name after `exec` to match your Compose file.

## Step 2 - Back up the three things a restore needs

A complete n8n backup has three parts. Missing any one of them makes a restore fail:

```bash
mkdir -p ~/n8n-backups
# 1. The database (logical dump, taken while the OLD server is running)
docker compose exec -T postgres pg_dumpall -U postgres > ~/n8n-backups/pg-all-$(date +%F).sql
# 2. The environment file — it holds N8N_ENCRYPTION_KEY
cp .env ~/n8n-backups/.env-$(date +%F)
# 3. The Compose file itself
cp docker-compose.yml ~/n8n-backups/docker-compose-$(date +%F).yml
```

Why `pg_dumpall` and not `pg_dump`? `pg_dump` dumps one database; `pg_dumpall` dumps the whole cluster, including roles. That matters because the restore creates the `n8n` role and database from the dump — one less thing to recreate by hand.

**Verify the dump before you touch anything else.** A dump file of a few hundred bytes means the dump failed and you are about to delete a volume for nothing:

```bash
tail -3 ~/n8n-backups/pg-all-$(date +%F).sql
ls -lh ~/n8n-backups/pg-all-$(date +%F).sql
```

The last line must read `PostgreSQL database cluster dump complete`, and the file should be at least tens of kilobytes for a real n8n instance. If the tail shows an error instead, fix the dump (wrong user, wrong password, container not running) and re-run it. Copy the backup off the machine — a backup that lives only on the same disk is not a backup.

> **Warning:** `N8N_ENCRYPTION_KEY` is the single point of failure for every stored credential. Restoring the database with a different or regenerated key leaves every credential undecryptable — the exact failure covered in our [credentials-decrypt guide](/blog/fix-n8n-credentials-decrypt-encryption-key/). Keep the `.env` copy from this step until the new stack is verified.

## Step 3 - Dump with the NEW client (the step most guides get wrong)

PostgreSQL prefers the dump to be taken by the *newer* client, so run the dump from the new image against the still-running old server on the Compose network:

```bash
docker run --rm --network n8n_default \
  -e PGPASSWORD=<your-postgres-password> \
  postgres:17 pg_dumpall -h postgres -U postgres > ~/n8n-backups/pg-all-17-$(date +%F).sql
```

Here's what each part does:

- `postgres:17` — the new image, so the dump is written by the version that will read it back.
- `--network n8n_default` — the Compose project network, so the one-off container can reach the database by service name. Your network is `<project>_default` where `<project>` is your Compose project name (usually the folder name); check with `docker network ls`.
- `-h postgres` — the Compose service name of your database container, not `localhost`.
- `pg_dumpall -U postgres` — a full-cluster dump as the superuser.

Verify this dump the same way as in Step 2: it must end with `PostgreSQL database cluster dump complete`. Keep the Step 2 dump too — two backups from two client versions cost nothing and save you if one turns out corrupt.

## Step 4 - Bring up the new version on a FRESH volume

This is the step where people lose data: they change the tag and reuse the old volume, which is exactly what produced the `FATAL` error. Instead, point the new Postgres at an empty volume and keep the old one untouched until the new stack is verified.

First, stop n8n so nothing writes to the database mid-migration:

```bash
docker compose stop n8n
docker compose stop postgres
```

Then edit `docker-compose.yml`. Change the image tag **and**, for Postgres 18, the volume mount:

```yaml
services:
  postgres:
    # 16 -> 17: just change the tag, keep the volume path
    image: postgres:17-alpine
    volumes:
      - db_storage:/var/lib/postgresql/data
```

```yaml
services:
  postgres:
    # 16/17 -> 18: the data directory moved — mount the PARENT
    image: postgres:18-alpine
    volumes:
      - db_storage:/var/lib/postgresql
```

For Postgres 18 the container creates `/var/lib/postgresql/18/docker` inside the volume itself. Mounting at the old `/var/lib/postgresql/data` path makes the container see your old data directory in the wrong place and fail with the same `FATAL` error (or with a message about data in an unused mount). If you set `PGDATA` yourself, make sure it points inside the mounted volume.

Now bring up only the database, on the empty volume:

```bash
docker compose up -d postgres
docker compose logs postgres --tail 10
```

You should see the first-run initialization lines and `database system is ready to accept connections`. If you see `FATAL: database files are incompatible with server` again, the new container is still seeing the old data — check that you are on a fresh volume (a new volume name, or the old volume renamed, not reused).

## Step 5 - Restore the dump into the new server

Load the dump you took with the new client into the fresh server:

```bash
cat ~/n8n-backups/pg-all-17-$(date +%F).sql | docker compose exec -T postgres psql -U postgres
```

One error in the output is expected and harmless:

```
ERROR:  role "postgres" already exists
```

The fresh container already created the `postgres` superuser role during initialization, and the dump tries to create it again. Everything else restores normally — databases, roles, tables, and all of n8n's data. If you see errors about missing tables or permissions beyond that one line, stop: the dump may be incomplete (re-check its tail line from Step 3).

If you used `pg_dump` (single-database) instead of `pg_dumpall`, restore with the matching command and pre-create the database first:

```bash
docker compose exec postgres psql -U postgres -c "CREATE DATABASE n8n OWNER n8n;"
cat ~/n8n-backups/n8n-$(date +%F).sql | docker compose exec -T postgres psql -U n8n -d n8n
```

## Step 6 - Verify everything works

Start n8n and check, in order, that the database, the workflows, and the credentials all survived:

```bash
docker compose up -d
docker compose exec postgres psql -U n8n -d n8n -c "SELECT version();"
docker compose logs n8n --tail 30
```

You should see `PostgreSQL 17.x` (or `18.x`), and n8n's logs should show a clean startup with no migration errors. Then verify in the editor:

1. **Workflows are listed** — open the editor and confirm your workflows and folders are all present.
2. **Credentials decrypt** — open any credential (Google, OpenAI, Postgres) and confirm it shows as connected, not `unset` or erroring. If credentials fail here, the `.env` in use does not carry the original `N8N_ENCRYPTION_KEY` — restore the copy from Step 2 and restart n8n.
3. **A workflow executes** — run one real workflow end to end, ideally one that writes to the database, and confirm the execution shows success with the expected output.

Only when all three checks pass should you remove the old volume. Until then, the old data directory is your rollback: stop the stack, point the tag back at the old version and the old volume, and you are back where you started.

## Dead ends: what NOT to do

- **Do not delete the volume to "fix" the error.** The container will start — on an empty database. Your workflows and credentials are gone, and n8n will ask you to create an owner account again.
- **Do not edit the `PG_VERSION` file.** Changing `16` to `17` in the data directory does not convert the on-disk format; the server will fail with corruption errors instead of a clean refusal.
- **Do not force the old path with `PGDATA` on Postgres 18.** Pointing 18 at a 16 data directory gives the same `FATAL: database files are incompatible with server` (verified: `The data directory was initialized by PostgreSQL version 16, which is not compatible with this version 18.6`). The path change and the version change are two separate problems — fix them separately.
- **Do not use `pg_upgrade` inside a single container and hope.** In-place upgrade needs both the old and new binary sets available at once, which a single-version image does not provide. Dump-and-restore is the path that works with stock images.

## Prevent it next time

- **Pin the exact Postgres tag.** `postgres:16-alpine` in Compose, never `postgres:latest` or an unpinned `postgres`. A major bump should be a deliberate, scheduled change — never a side effect of `docker compose pull`.
- **Treat a major-version bump as a migration, not an update.** Minor upgrades inside one major version (16.4 → 16.6, 18.5 → 18.6) need only a pull and a restart. Major upgrades (16 → 17, 17 → 18) always need the dump-and-restore runbook above.
- **Automate the dump.** A daily `pg_dump` via cron, kept 14 days and copied off the machine, turns the next incident from a data-loss scare into a 10-minute restore. Test a restore at least once — an untested backup is a rumor.
- **Read the n8n release notes before upgrading either side.** n8n versions can require a minimum Postgres version, and Postgres major releases can change paths (as 18 did). Two minutes of reading saves the hour this article just cost you.

## FAQ

### Is my data lost when I see "database files are incompatible with server"?

No. The error is a refusal, not corruption — the new server will not read the old format, so it touches nothing. Reverting the image tag to the old version starts the container again with your data intact. That reversibility is what makes dump-and-restore safe: you always have a working fallback.

### Can I upgrade 16 straight to 18, skipping 17?

Yes, with dump-and-restore — a logical dump is version-independent, so `pg_dumpall` from 16 restores cleanly into 18. The only extra step is the Postgres 18 volume-path change in Step 4. (`pg_upgrade`, the in-place path, is pickier about version jumps; another reason to use dump-and-restore in Docker.)

### Why does the restore complain "role postgres already exists"?

The fresh Postgres container creates the `postgres` superuser during first initialization, and your `pg_dumpall` output also contains a `CREATE ROLE postgres`. The second create fails harmlessly; every other object restores normally. Ignore that one line.

### My n8n starts but all credentials show as unset — what happened?

The database restored fine, but n8n is running with a different `N8N_ENCRYPTION_KEY` than the one that encrypted those credentials — usually because the container was recreated without the original `.env`. Restore the `.env` copy from Step 2 (same key, character for character) and restart n8n; credentials decrypt in place.

## Key Takeaways

1. **The error means "wrong binary, right data"** — Postgres major versions cannot read each other's data directories. Nothing is corrupt; reverting the tag proves it.
2. **Dump with the new client, restore into a fresh volume.** `pg_dumpall` from the new image against the running old server, verify the `PostgreSQL database cluster dump complete` tail line, then load it into the new tag on an empty volume.
3. **Postgres 18 moved the data directory** — mount the volume at `/var/lib/postgresql`, not `/var/lib/postgresql/data`, or you will hit the same `FATAL` error after a correct restore.
4. **Back up three things, not one** — the database dump, the `.env` with `N8N_ENCRYPTION_KEY`, and the Compose file. A database without its key is unreadable credentials.
5. **Pin the Postgres tag and never bump a major version casually.** Minor upgrades are pull-and-restart; major upgrades are a migration with a runbook — this one.

Next: if your n8n instance is still on SQLite, the same backup discipline applies in reverse — our [Postgres migration guide](/blog/fix-n8n-postgres-comma-query-parameter/) covers the Postgres node quirks you will meet once the database is in place. And if the restore ever leaves credentials unreadable, the [encryption-key recovery guide](/blog/fix-n8n-credentials-decrypt-encryption-key/) walks through that failure mode step by step.
