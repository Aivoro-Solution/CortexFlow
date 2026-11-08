---
title: "Fix n8n 'Database is not ready' and 503 Errors on Docker First Boot (Postgres Healthcheck Guide)"
description: "n8n crashes on first boot with 'Database is not ready!' and a 503. Diagnose the three causes, then fix startup order with one healthcheck."
date: 2026-11-08
category: automation
tags: ["n8n", "error fix", "docker", "postgres", "self-hosting", "docker compose"]
draft: false
featured: false
image: "/og/fix-n8n-database-not-ready-docker-postgres.webp"
---

You ran `docker compose up -d`, waited a minute, opened your n8n domain — and got a 503. The logs say `Database is not ready!`. You run it again, and this time it works. Or it doesn't. Either way, the same stack that "works" on your laptop fails on a fresh VPS, and every restart feels like a coin flip.

This is the most common first-boot failure in self-hosted n8n, and it has a boring root cause: **Docker Compose started n8n before Postgres was ready to accept connections.** The fix is a healthcheck, not a bigger server — but only after you confirm startup order is actually your problem, because an OOM restart loop and a full disk produce the exact same 503. By the end of this guide you will know how to tell the three apart in two minutes, apply the one-line fix, and prove the stack boots cleanly every time. All fixes are verified against community reports and the official n8n hosting repo, as of November 2026.

**Prerequisites:** a self-hosted n8n stack on Docker Compose with Postgres (the `withPostgres` layout from the official n8n-hosting repo), shell access to the host, and Docker Compose v2 (`docker compose`, not the legacy `docker-compose`).

## The symptom: what "Database is not ready" actually means

When n8n starts, it connects to its database before doing anything else — loading credentials, workflows, and execution history all depend on it. If Postgres is still initializing (running `initdb` on a fresh volume, replaying its write-ahead log after a restart, or just slow on a small VPS), n8n's first connection attempt fails and the process logs `Database is not ready!` and exits.

The 503 you see in the browser is not n8n refusing you. It is your reverse proxy (Caddy, Nginx, Traefik) reporting that there is nothing listening behind it — n8n already died. That is why the error feels inconsistent: on a warm restart Postgres is already up, so n8n connects fine; on a cold boot, or after a host reboot, the race is real again.

Two other failures wear the same disguise, so diagnose before you fix. The community thread that documented this exact pattern — a Hostinger VPS with recurring `database-not-ready`/503 errors and workflow execution failures (community.n8n.io, October 2026) — had responders split on exactly this point: the 503 alone does not say why.

## Step 0 — Diagnose in two minutes: which of the three causes is yours

Run these three checks before changing any config. Each one points at a different fix.

```bash
docker compose ps
docker compose logs --timestamps --since 10m n8n
docker inspect --format '{{.State.OOMKilled}} {{.RestartCount}}' $(docker compose ps -q n8n)
df -h && docker system df
```

| What you see | What it means | Go to |
|---|---|---|
| `Database is not ready!` in the n8n log, only on cold boots / first boot, `RestartCount` stays 0 or 1 | Startup order — n8n started before Postgres accepted connections | Step 1 |
| `OOMKilled: true`, or `RestartCount` climbs by one with every 503 you saw | Restart loop — n8n is being killed for memory, not failing on the database | Step 2 |
| Disk at 90%+ used, or `docker system df` shows a large reclaimable volume | Disk full — Postgres stops accepting writes when the volume fills, and on a small VPS the thing that fills it is usually execution data | Step 3 |
| None of the above, and the error is intermittent at random times | A real database fault — check Postgres logs at the same timestamp (`docker compose logs --timestamps --since 10m postgres`) before changing anything | Step 4 |

One more check that costs nothing: `docker events --since 15m` timestamps every container die, restart, and health-status change in one stream — the fastest way to see which container actually died first, which the logs on their own will not tell you.

> **Warning:** do not change configuration until the topology is clear. n8n uses SQLite by default, so confirm `DB_TYPE` is actually `postgresdb` before assuming a Postgres container is involved — and remember that `localhost` inside the n8n container refers to the n8n container itself, not the host or the database. The database host must be the Compose service name, usually `postgres`.

## Step 1 — Fix startup order with a Postgres healthcheck

This is the fix for the cold-boot case, and it is the only one most people need.

**The trap:** short-form `depends_on` does not do what its name suggests. In a Compose file, `depends_on: [postgres]` (or the list form) only waits for the Postgres container to be **created and started**. It says nothing about whether the process inside is ready. A Postgres container is "started" the instant its process forks — seconds before it accepts a single query, and longer on a fresh volume while `initdb` runs. So n8n boots, tries to connect, fails, and exits — one line before Postgres logs `database system is ready to accept connections`.

The fix has two parts, and both are required:

1. A `healthcheck` on the Postgres service, so Compose can tell when the database is actually ready.
2. The long form of `depends_on` with `condition: service_healthy` on n8n, so Compose holds n8n back until that healthcheck passes.

Here is the corrected pair, matching the official n8n-hosting `withPostgres` layout (Postgres 16):

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n
    restart: unless-stopped
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
      - DB_POSTGRESDB_USER=${POSTGRES_USER}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16
    restart: always
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_storage:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -h 127.0.0.1 -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
```

Here is what each piece does:

- **`healthcheck.test` runs `pg_isready`**, which ships in the official Postgres image and exits 0 only when the server accepts connections. That is exactly the readiness signal Compose needs — no sleep loops, no wait-for-it scripts in your entrypoint.
- **`interval: 5s` / `timeout: 5s` / `retries: 10`** gives Postgres up to ~50 seconds of failed probes before Compose marks it unhealthy. On a slow VPS the first boot can take 30–60 seconds while Postgres initializes; `start_period: 30s` is worth adding if your first boot is slower than that, so a slow start does not burn your retries.
- **`condition: service_healthy`** is the long form of `depends_on`. The short list form cannot express health conditions at all — switching to the map form is the whole point.
- **`DB_POSTGRESDB_HOST=postgres`** is the Compose service name, not `localhost`. Inside the n8n container, `localhost` is the n8n container itself.

Apply it and restart the stack:

```bash
docker compose down
docker compose up -d
docker compose ps
```

You should see `postgres` show `(healthy)` before n8n starts, and n8n stay `Up` instead of cycling through `Restarting`. If n8n still exits, read its log again — with the healthcheck in place, a `Database is not ready!` line now means Postgres is genuinely unhealthy, not merely slow, and Step 4 applies.

> **Note:** the official images define no built-in `HEALTHCHECK` on purpose, so `condition: service_healthy` with no `healthcheck:` block of your own fails outright with "has no healthcheck configured". The healthcheck and the condition are a pair — one without the other does nothing.

### The fresh-volume trap: probe over TCP, not the Unix socket

There is one more subtlety, and it only bites on a fresh volume — which is exactly when you are most likely to be testing this fix. On first initialization, the official Postgres image starts Postgres **twice**: a temporary server that listens only on the Unix socket (to run your `/docker-entrypoint-initdb.d` scripts), then shuts it down and starts the real server on TCP. Plain `pg_isready` with no `-h` flag talks to the Unix socket, so it can report "ready" during that temporary phase — your healthcheck goes green, n8n starts, and the real server is still seconds away.

The fix is one flag: **`-h 127.0.0.1` forces the check over TCP**, the same path n8n itself uses to connect. The official n8n-hosting example uses `-h localhost`, which resolves the same way inside the container; `-h 127.0.0.1` is the explicit form. Either way, the point is the same: probe the way your app connects.

## Step 2 — If it is a restart loop: check for OOM kills

If Step 0 showed `OOMKilled: true` or a climbing `RestartCount`, the healthcheck will not save you — n8n is being killed for memory and restarted, and every restart looks like a database failure from the outside. The giveaway is timing: a restart loop produces 503s at random, not just on cold boots.

Confirm it and see the memory limit in force:

```bash
docker inspect --format '{{.State.OOMKilled}} {{.RestartCount}}' $(docker compose ps -q n8n)
docker stats --no-stream --format '{{.Name}}: {{.MemUsage}} / {{.MemLimit}}'
```

If n8n is being OOM-killed, raise the container memory limit (`deploy.resources.limits.memory` or the host's available RAM — a 1 GB VPS running n8n + Postgres + a reverse proxy is marginal) and cap Node's heap with `NODE_OPTIONS=--max-old-space-size=512` so the process fails gracefully instead of being killed mid-write. The full memory playbook — heap sizing, `EXECUTIONS_DATA` pruning, binary-data mode, and queue-mode isolation — is in our guide to [fixing n8n out-of-memory crashes in Docker Compose](/blog/fix-n8n-oom-crash-docker-compose/).

## Step 3 — If the disk is full: free space before anything else

Postgres stops accepting writes when its volume fills, and n8n then fails in confusing ways — including, again, a 503. On a small VPS the usual culprit is execution data: every execution n8n saves (and by default it saves them all) lands in Postgres, and months of runs add up to gigabytes.

```bash
df -h
docker system df
docker compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
```

Free space in this order: `docker system prune` for unused images and build cache, then enable execution pruning so the problem does not return — `EXECUTIONS_DATA_PRUNE=true`, `EXECUTIONS_DATA_MAX_AGE=336` (14 days), `EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000`. Pruning only deletes execution history, never workflows or credentials. If the database itself is still large after pruning, deleted rows leave dead tuples behind — that is a different fix, covered in our guide to [fixing n8n data-table size errors after deleting rows](/blog/fix-n8n-data-table-size-after-delete/).

## Step 4 — Verify the whole stack boots clean

A fix you cannot prove is a guess. After applying Step 1 (and Steps 2–3 if they applied), do a cold-boot test — this is the only test that exercises the race you just fixed:

```bash
docker compose down
docker compose up -d
sleep 30
docker compose ps
curl -s http://localhost:5678/healthz; echo
```

You should see both services `Up`, Postgres `(healthy)`, and `{"status":"ok"}` from `/healthz`. For a stronger check, hit the readiness endpoint, which also verifies the database connection:

```bash
curl -s http://localhost:5678/healthz/readiness; echo
```

`{"status":"ok"}` here means n8n is up **and** can reach Postgres. (In queue mode the readiness endpoint on workers only exists when `QUEUE_HEALTH_CHECK_ACTIVE=true` — and queue mode needs the same treatment for Redis: a `redis-cli ping` healthcheck on the Redis service plus `condition: service_healthy` on every worker, because binary data in `filesystem` mode is not supported in queue mode either. See our [n8n queue mode guide](/blog/n8n-queue-mode-explained/) for the full stack.)

Then open the editor and run any workflow once. If it executes green, the stack is healthy — the cold boot is the test that matters, not a warm restart.

## Prevent it next time

Three habits keep this class of failure away permanently:

1. **Never ship a Compose file without healthchecks on stateful services.** Postgres, Redis, and any database get a healthcheck; every service that depends on them gets `condition: service_healthy`. Treat a bare `depends_on: [postgres]` in a tutorial as a bug in that tutorial.
2. **Pin the database host to the service name and the port to the internal one.** `DB_POSTGRESDB_HOST=postgres`, port `5432` — never `localhost`, never the published host port. The day you add a reverse proxy or move to queue mode, the wrong host is the first thing that breaks.
3. **Monitor the boot, not just the editor.** A dead-man's-switch workflow that pings your instance's `/healthz` every 5 minutes and alerts on two consecutive failures catches the next silent stop — including the kind where the workflow itself never runs. Our guide to [workflows that silently stop triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/) covers the heartbeat pattern in detail.

## FAQ

### Why does n8n work when I run `docker compose up` a second time?

Because the second run is a warm start. Postgres was already initialized by the first attempt, so it accepts connections immediately and n8n connects fine. The race only exists on a cold boot or a fresh volume — which is why it passes on your laptop and fails on a new VPS.

### Is `restart: always` on n8n a substitute for the healthcheck?

No. Restarting n8n until Postgres happens to be ready usually works eventually, but it is a retry loop masquerading as a fix: every restart replays database migrations, burns a few seconds, and leaves `Database is not ready!` errors in your logs that will mislead the next person debugging the instance. The healthcheck removes the race instead of outrunning it.

### I added the healthcheck and n8n still says "Database is not ready!"

Then Postgres is genuinely unhealthy, not slow. Check `docker compose logs postgres` for the real error: the most common next causes are a Postgres major-version upgrade done by changing the image tag alone (see our guide to [fixing "database files are incompatible with server"](/blog/fix-n8n-postgres-database-files-incompatible/)), a corrupted or full volume (Step 3), or wrong credentials — `POSTGRES_USER`/`POSTGRES_PASSWORD` in the Postgres service must match `DB_POSTGRESDB_USER`/`DB_POSTGRESDB_PASSWORD` in n8n exactly.

### Does this apply to the `n8n` service in queue mode too?

Yes, and more so: in queue mode the main instance, the webhook processor, and every worker each need `condition: service_healthy` on both Postgres and Redis. A worker that starts before Redis is ready fails its first jobs the same way. The official queue-mode compose layout gates all of them on healthchecks.

## Key Takeaways

1. **Short-form `depends_on` only waits for the container to start, not for Postgres to accept connections** — that gap is the entire bug.
2. **The fix is a pair: a `pg_isready` healthcheck on Postgres plus `condition: service_healthy` on n8n** — one without the other does nothing.
3. **Probe over TCP (`-h 127.0.0.1`)**, because on a fresh volume the temporary init server answers on the Unix socket and a socket-only check lies.
4. **A 503 with `Database is not ready!` has two lookalikes** — an OOM restart loop and a full disk — and the two-minute diagnosis in Step 0 tells them apart before you change anything.
5. **Prove it with a cold boot**: `docker compose down && docker compose up -d`, then `curl /healthz/readiness` should return `{"status":"ok"}`.

Next: if your instance is now booting cleanly but workflows still fail silently in production, read our guide to [workflows that silently stop triggering](/blog/fix-n8n-workflow-silently-stopped-triggering/) — the heartbeat monitor there is the single highest-value addition to any self-hosted n8n setup.

*Sources: n8n Community thread on recurring database-not-ready/503 errors on a Hostinger VPS (Oct 2026); n8n-hosting official `withPostgres` Docker Compose layout; n8n self-hosted Docker installation guides (triggerworkflow, ajayk.sh queue-mode guide, n8n 2.43.8 / Postgres 17.11); Docker Compose `depends_on` healthcheck writeups on dev.to. Verified as of November 2026.*
