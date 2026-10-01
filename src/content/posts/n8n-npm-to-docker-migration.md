---
title: "Migrate n8n from npm to Docker Before 3.0"
description: "n8n 3.0 kills npm installs. Migrate your self-hosted n8n to Docker Compose without losing credentials, workflows, or execution history — step by step."
date: 2026-10-01
category: automation
tags: ["n8n", "Docker", "self-hosting", "migration", "tutorial"]
image: "/og/n8n-npm-to-docker-migration.webp"
draft: false
featured: false
---

If you installed n8n with `npm install -g n8n` a year ago and it has been humming along since, here is the bad news in one line: **n8n 3.0 removes npm/npx installs entirely.** After October 2026, Docker is the only supported self-hosting method. The good news: the migration is mostly mechanical — and if you do it before 3.0 lands, the jump to 3.x afterward is a one-tag change. By the end of this guide you will have your exact n8n instance (workflows, credentials, execution history, settings) running in Docker Compose, with a verified rollback path if anything goes sideways.

**Who this is for:** you run n8n via `npm`/`npx` on a server or local machine and it stores data in `~/.n8n`. If you are already on Docker, skip this — but pin your version tag now (see Step 5).

## Why this migration loses data if you rush it

An npm-installed n8n keeps everything in one folder on the host: `~/.n8n`. That folder holds `database.sqlite` (your workflows, credentials, and execution history), a `config` file (which contains your **encryption key** — the secret that makes your stored credentials readable), and a binary-data directory (called `binaryData` in 2.x, renamed to `storage` in 3.0).

A Docker-installed n8n keeps the same files, but inside the container at `/home/node/.n8n`. The migration is therefore a folder handoff: point the container at your existing data instead of letting it start fresh. There are exactly two silent ways people lose data here:

1. **Mounting an empty volume instead of the existing folder.** n8n boots, sees no database, and creates a brand-new empty instance. Your workflows are not deleted — but you are looking at a blank n8n and panicking at 2 AM.
2. **Losing the encryption key.** Credentials in n8n's database are encrypted at rest. Lose the key and every credential shows as broken; there is no recovery. (See the community's painful `N8N_ENCRYPTION_KEY` loss threads — this is the single most expensive mistake in n8n self-hosting.)

Both are avoidable. The whole plan: back up first, copy nothing by hand if possible, bind-mount your existing `~/.n8n` straight into the container, and verify logins, credentials, and history before you touch the old install.

**Prerequisites**

- Your npm-installed n8n, running (check your version: `n8n --version`). As of this writing the latest stable 2.x is 2.41.4 — migrate on the 2.x line first, upgrade to 3.0 after.
- Docker Engine + Compose plugin on the host (Compose is included with Docker since v20.10).
- Shell access to the machine n8n runs on, and a few hundred MB of free disk for a backup copy.
- Your n8n editor URL/port handy (default: `http://localhost:5678`).

**Example terminology** — used consistently below:

- `~/.n8n` — your npm install's data directory (e.g. `/home/deploy/.n8n`).
- `<old-version>` — the n8n version your npm install reports, e.g. `2.41.4`.

## Step 1 - Back up everything before you touch anything

Stop nothing yet. First, take two backups: a file-level copy of the whole data directory, and an n8n-native workflow export.

```bash
# File-level backup of the entire data directory
cp -r ~/.n8n ~/n8n-backup-$(date +%F)
ls -la ~/n8n-backup-$(date +%F)
```

You should see `database.sqlite`, a `config` file, and a `binaryData` directory. `database.sqlite` is the load-bearing file — workflows, credentials, users, executions all live there. The `config` file holds the encryption key n8n generated on first boot (look for `encryptionKey`).

Now the export, as a second safety net:

```bash
n8n export:workflow --all --output=~/n8n-backup-$(date +%F)/workflows.json
```

`--all` covers inactive workflows too. Without it you silently skip every workflow that is not currently active — a classic way to discover losses after the fact.

> **Warning:** database migrations only run forward. If you start a *newer* n8n against your data and then try to go back, the older version cannot read the migrated database. Your `~/n8n-backup-<date>` copy is the only way back. Keep it until the migration is fully verified.

## Step 2 - Confirm your version and encryption key

Run:

```bash
n8n --version
grep -i encryption ~/.n8n/config
```

The version matters for Step 5: the Docker image tag you pull must be the **same or newer** than your npm version. Never start an older n8n against a newer database.

The encryption check matters because of the key trap: if `grep` finds an `encryptionKey` in `~/.n8n/config`, that key travels with the folder and Docker will pick it up automatically when you bind-mount the same directory. If you ever set `N8N_ENCRYPTION_KEY` as an environment variable for the npm install instead, you must pass that same variable to the container in Step 5 — write it down now.

## Step 3 - Stop the npm instance

The npm process and the container cannot both hold the SQLite database or port 5678 at once. Stop n8n however you run it:

```bash
# If you run it in the foreground: Ctrl+C in that terminal.
# If you run it under PM2:
pm2 stop n8n && pm2 save

# Confirm nothing is listening on 5678 anymore:
ss -ltn | grep 5678 || echo "port 5678 is free"
```

You should see "port 5678 is free". Keep PM2/systemd installed but disabled for now — it is your rollback path (Step 8).

## Step 4 - Install Docker if needed

If Docker is not on the host yet, follow the official install docs for your distro (docs.docker.com/engine/install). Then verify:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

If you see "Hello from Docker!", Docker is working. The Compose plugin is what Step 5 uses — `docker compose` (space, not hyphen).

## Step 5 - Write the Compose file

Create a project directory and a `compose.yaml`. The critical line is the volume: **bind-mount your existing `~/.n8n` directly** — do not create a fresh named volume. This is what avoids both data-loss traps at once.

```yaml
services:
  n8n:
    image: n8nio/n8n:2.41.4
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - GENERIC_TIMEZONE=Asia/Kolkata
      - TZ=Asia/Kolkata
      # Only needed if you set N8N_ENCRYPTION_KEY as an env var for the npm install:
      # - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
    volumes:
      - ~/.n8n:/home/node/.n8n
```

Here's what each key does:

- **`image: n8nio/n8n:2.41.4`** — pin an explicit version, never `:latest` in production. Use the same 2.x version your npm install reported (or newer, e.g. 2.41.4 as of late September 2026). The 3.0 upgrade comes later as a tag change.
- **`restart: unless-stopped`** — the correct default for a VPS: survives crashes and reboots, unlike the default `no`.
- **`ports: "5678:5678"`** — maps the container's port to the host, same as your npm install. If you serve n8n behind a reverse proxy with a domain, add `N8N_HOST` and `WEBHOOK_URL=https://<your-domain>/` to the environment so webhooks generate correct URLs.
- **`GENERIC_TIMEZONE` + `TZ`** — set both to your timezone. Without these, Schedule Trigger nodes default to UTC and your cron-style workflows drift by hours. Replace `Asia/Kolkata` with yours.
- **`volumes: ~/.n8n:/home/node/.n8n`** — the migration itself. Your existing data directory, mounted where the container expects its data. The encryption key in `~/.n8n/config` travels with it.

> **Note:** the container runs as the `node` user (uid 1000). If your `~/.n8n` files are owned by a different uid, the container cannot write to them and n8n will fail to boot with permission errors. Check with `ls -ln ~/.n8n` and, if needed, `sudo chown -R 1000:1000 ~/.n8n`.

Start it:

```bash
cd ~/n8n-compose   # wherever you put compose.yaml
docker compose up -d
docker compose logs -f n8n
```

You should see the n8n boot log ending with `Editor is now accessible via: http://localhost:5678`. Watch for the database migration lines on first boot — n8n upgrades your SQLite schema forward automatically. That is expected and fine, as long as your backup from Step 1 exists.

## Step 6 - Verify: logins, credentials, workflows, history

Do not declare victory from the boot log. Check all four:

1. **Logins:** open `http://<your-host>:5678` and sign in with your existing owner account. If you see a "create owner account" screen, something is wrong — the container started on a fresh database (the empty-volume trap). Stop, re-check the volume path, and retry.
2. **Credentials:** open any workflow that uses a credential (e.g. an API key) and confirm it is intact. Broken credentials after migration mean the encryption key did not travel — re-check Step 2.
3. **Workflows:** count your workflows against the npm install. Inactive ones included.
4. **Executions:** open the Executions tab and confirm history is present.

Then the end-to-end proof — execute one real workflow manually:

```bash
curl -s http://localhost:5678/healthz
```

You should get `{"status":"ok"}`. That confirms the HTTP layer, but the real test is triggering a workflow that uses a credential and a binary file (exercises `database.sqlite`, the encryption key, and the `binaryData` directory in one shot).

## Step 7 - Clean up the npm install

Only after Step 6 passes:

```bash
# Remove the npm install so nothing restarts it accidentally
npm uninstall -g n8n
pm2 delete n8n 2>/dev/null; pm2 save
```

Keep the `~/n8n-backup-<date>` copy for a week or two. Disk is cheap; regret is not.

## Step 8 - When you are ready: the 3.0 upgrade

Once Docker is stable for a few days, 3.0 is a tag change:

```bash
docker compose pull   # with image: n8nio/n8n:3.x set in compose.yaml
docker compose up -d
```

Take another backup first (3.0's renames — `binaryData` to `storage`, tightened defaults — are one-way). Read the [official 3.0 breaking-changes document](https://docs.n8n.io/changelog/v30-breaking-changes) and the CortexFlow [n8n 3.0 breaking-changes checklist](/blog/n8n-3-breaking-changes/) before pulling.

**Rollback (any time before Step 7):** `docker compose down` in the project directory, then restart your npm process (`pm2 start n8n` or `n8n &`). Because you bind-mounted the original folder, nothing was ever copied — the npm install reads the same files.

## What I did not test

I have not migrated an n8n instance that uses PostgreSQL instead of SQLite — the same bind-mount principle applies to the `~/.n8n` folder, but the database lives separately, so you also need to keep the Postgres container/service reachable with the same `DB_POSTGRESDB_*` settings. I also have not tested the npm→Docker path on Windows, where path translation for bind mounts (`C:\Users\...` vs `/home/node/.n8n`) needs Docker Desktop's file-sharing settings. If either is your setup, migrate on 2.x and verify Step 6 twice.

## Key Takeaways

1. **n8n 3.0 (October 2026) removes npm/npx installs — Docker is mandatory.** Migrate on the 2.x line now; the 3.0 jump is a tag change afterward.
2. **Bind-mount your existing `~/.n8n` to `/home/node/.n8n`** — this single line avoids both silent data-loss traps (empty fresh instance, lost encryption key).
3. **Pin the image tag and match or exceed your npm version** — database migrations only run forward, and `:latest` in production is how you get surprised.
4. **Set `GENERIC_TIMEZONE` + `TZ` and fix file ownership** — the two unglamorous failures that eat the most debugging time.

Next: once you are on Docker, consider moving to PostgreSQL if you run dozens of workflows — SQLite is fine for a handful of automations but becomes the bottleneck under concurrent executions. The [official Docker Compose guide](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/) includes a Postgres variant.
