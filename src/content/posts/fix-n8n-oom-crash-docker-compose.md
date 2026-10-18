---
title: "Fix n8n Out of Memory Crashes in Docker Compose (5 Real Fixes)"
description: "n8n crashing with exit 137 or 'JavaScript heap out of memory'? Fix it with NODE_OPTIONS, container memory limits, and execution-data pruning."
date: 2026-10-18
category: automation
tags: ["n8n", "self-hosting", "Docker", "out-of-memory", "troubleshooting"]
image: "/og/fix-n8n-oom-crash-docker-compose.webp"
draft: false
featured: false
---

You wake up to a dead automations server. n8n was fine at midnight, and now the editor won't load, webhooks return 503s, and `docker compose ps` shows the container restarting in a loop. The logs say `JavaScript heap out of memory` — or nothing at all, just exit code 137. This is an OOM (out of memory) crash: n8n's process grew past what the machine or the container allowed, and the kernel killed it. This guide walks you through confirming the crash is really a memory problem, then five fixes in priority order — from the five-minute heap bump to the structural changes that stop the next crash.

## The symptom

An OOM crash in Dockerized n8n shows up in one of three ways:

1. **The container exits with code 137.** That's SIGKILL — the process didn't shut down, it was killed. `docker compose ps` shows `restarting` if you have a restart policy, or `exited (137)`.
2. **`JavaScript heap out of memory` in the logs.** That's Node.js itself hitting its internal memory ceiling and aborting before Docker even gets involved.
3. **"Connection lost" in the editor mid-run, then n8n is gone.** The UI was connected to a server that no longer exists. This one is easy to misdiagnose as a proxy problem — but if the container died, it's memory.

Common triggers: a workflow pulling 10,000 rows into a single Code node, a binary file attachment in the tens of megabytes, several AI-agent workflows running at once, or a backlog of retries after a failure storm. n8n keeps every item flowing through a workflow in memory while the run is in progress — saving settings only change what gets written to the database *after* the run, not what's held in RAM *during* it.

## The root cause

n8n runs on Node.js, which caps its main heap (the memory your code actually uses) at a fixed size — roughly 2 GB on 64-bit systems by default, regardless of how much RAM the machine has. Three things push you over that ceiling:

1. **Unbounded payloads.** n8n puts no cap on how much data a step loads. One spreadsheet, one API response, one big attachment — the whole thing lands in the heap. A nested loop over a massive array multiplies that memory several times over.
2. **Concurrent executions stacking.** Every running execution holds its own items in the same heap. Five workflows each holding 300 MB of items is 1.5 GB — past the default cap before anything unusual happens.
3. **Database bloat making every crash worse.** When a run finishes, n8n writes the full execution payload to the database. Multi-megabyte payloads on SQLite balloon the database file, and the next failure storm queues retries that contend on that same database — more memory pressure, longer recovery.

## Step 1 - Confirm the crash is really OOM

Before changing anything, verify the container was actually killed for memory. Run these from the host:

```bash
docker inspect n8n --format '{{.State.OOMKilled}}'
docker inspect n8n --format 'Exit code: {{.State.ExitCode}}'
docker compose logs --tail 50 n8n | grep -i -E "heap out of memory|Killed|exit"
```

You should see `OOMKilled: true` and/or exit code 137, possibly with `JavaScript heap out of memory` in the tail of the logs. If OOMKilled is `false` and the exit code is something else (1, for example), you have a different failure — an app crash, a bad env var, a failed migration — and the fixes below won't help.

**Watch the memory live.** Run a heavy workflow and watch the container's memory in real time:

```bash
docker stats n8n
```

If the MEM USAGE column climbs to the container's LIMIT right before the crash, the diagnosis is confirmed.

> **Warning:** Replace `n8n` with your actual container/service name in every command. If your service is called `n8n-main` or `n8n_prod`, use that instead.

## Step 2 - Raise Node's heap limit (the five-minute fix)

Node's heap cap is configurable. Add this to the n8n service in `docker-compose.yml`:

```yaml
services:
  n8n:
    image: n8nio/n8n
    environment:
      - NODE_OPTIONS=--max-old-space-size=2048
```

Then recreate the container:

```bash
docker compose up -d
```

**What this does:** `--max-old-space-size=2048` raises the V8 heap ceiling to 2 GB (2048 MB). The default is around 2 GB already on newer Node versions, so on a 4 GB machine you may need `3072` or `4096`. The rule of thumb: set it to about 70% of the memory actually available to the container, never above physical RAM — Node can't use swap efficiently and a heap larger than real memory just moves the crash around.

**Be honest about this fix:** it raises the ceiling. If a workflow leaks memory on every run (a Code node accumulating a nested array across loops, for example), the same crash returns once the payload grows past the new ceiling. The community has documented exactly this pattern. Treat Step 2 as the stopgap that buys you time while you apply Steps 4 and 5.

## Step 3 - Give the container a defined memory limit

An unbounded container on a shared host will keep growing until the kernel's OOM killer picks a victim — and it might pick your database instead of n8n. Set explicit limits so failures are predictable:

```yaml
services:
  n8n:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

**What each key does:** `limits.memory: 4G` is the hard ceiling — Docker kills the container past 4 GB instead of letting it eat the host. `reservations.memory: 2G` tells the Docker scheduler the minimum the container needs, which matters when several services share a small VPS. Pair the limit with Step 2's heap: set `--max-old-space-size` to roughly 70% of `limits.memory` (2.5–3 GB for a 4 GB limit) so Node's heap plus overhead fits inside the container's ceiling.

You should see the change reflected in `docker stats n8n` — the LIMIT column now shows 4GiB, and memory usage should stabilize below it.

## Step 4 - Stop saving giant execution payloads

These settings don't fix the heap crash itself — the items are held in memory during the run no matter what — but they stop the database bloat that turns one crash into a failure storm, and they make recovery far faster:

```yaml
services:
  n8n:
    environment:
      - EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
      - EXECUTIONS_DATA_SAVE_ON_ERROR=all
      - EXECUTIONS_DATA_PRUNE=true
      - EXECUTIONS_DATA_MAX_AGE=168h
      - EXECUTIONS_DATA_PRUNE_MAX_COUNT=50000
```

**What each key does:** `EXECUTIONS_DATA_SAVE_ON_SUCCESS=none` stops writing the full item payload to the database for every successful run (you can still see it ran) — keep `EXECUTIONS_DATA_SAVE_ON_ERROR=all` so failed runs retain their data for debugging. `EXECUTIONS_DATA_PRUNE=true` with `EXECUTIONS_DATA_MAX_AGE=168h` (7 days) deletes old executions automatically, and `EXECUTIONS_DATA_PRUNE_MAX_COUNT=50000` caps how many the prune job processes at once so pruning itself doesn't become a memory event. Also leave `EXECUTIONS_DATA_SAVE_ON_PROGRESS` off — saving progress mid-run multiplies database writes.

## Step 5 - Shrink the payloads that actually crash the heap

The heap crash comes from too much data in one run. Two changes address it directly:

**Process in batches.** Instead of pulling 10,000 rows through the whole workflow at once, use the Loop Over Items node with a batch size of 100–200, or split the workflow into a parent that fetches batches and a sub-workflow that processes each one. Each batch's items are released from memory when the batch finishes, so the heap never holds the full dataset.

**Keep binary data out of the heap.** Files, PDFs, images, and audio held as binary data sit in memory too. Offload them to disk (or S3):

```yaml
services:
  n8n:
    environment:
      - N8N_DEFAULT_BINARY_DATA_MODE=filesystem
      - N8N_BINARY_DATA_STORAGE_PATH=/data/n8n-binary
    volumes:
      - n8n_binary:/data/n8n-binary
```

**What this does:** binary data is written to files under `/data/n8n-binary` instead of being held in the Node heap; nodes read it back from disk when they need it. On a persistent volume this survives container restarts too. An S3-compatible bucket (`N8N_DEFAULT_BINARY_DATA_MODE=s3`) works the same way for multi-node setups.

## Step 6 - Isolate crashes with queue mode (the structural fix)

In single-instance mode, one workflow's OOM crash kills the whole n8n process — the editor, the webhooks, everything. Queue mode (`EXECUTIONS_MODE=queue`) splits n8n into a main instance, webhook handlers, and worker containers coordinated through Redis. A worker that OOMs dies alone: the main instance and the UI stay up, the crashed execution is marked failed, and the next execution runs on a healthy worker.

This is the right call when you run production workloads with concurrent executions — especially AI agent workflows that hold large context windows in memory. It requires PostgreSQL and Redis, so it's a bigger change than the steps above; the earlier steps work on a plain single-container setup.

## Verify the fix

Run your heaviest workflow (or a load test with several concurrent executions) and check three things:

```bash
docker stats n8n
docker inspect n8n --format '{{.State.OOMKilled}}'
docker compose logs n8n | grep -i -E "heap out of memory"
```

You should see: memory usage stabilizing well below the container limit, `OOMKilled: false`, and no heap errors in the logs. Then confirm execution data pruning is actually cleaning up: in the n8n UI, check **Executions** and verify entries older than your `EXECUTIONS_DATA_MAX_AGE` are being removed on the prune cycle.

## Prevent it next time

Three habits keep OOM crashes from coming back:

1. **Alert on memory, not on crashes.** Set up `docker stats` or host-level monitoring to alert at 80% of the container's memory limit. A crash is the last symptom, not the first.
2. **Move off SQLite before queue mode.** Queue mode requires PostgreSQL 13+. Migrating mid-incident — while n8n is crash-looping — is painful. Do it on a quiet afternoon.
3. **Add a swap file as a safety net on small VPSs.** A 2 GB swap file won't prevent a heap crash, but it stops the kernel from killing the wrong process when memory spikes briefly:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Limits and trade-offs:** none of these fixes make an infinitely large payload fit in finite memory. If your workflow genuinely needs to hold a 500 MB file in memory — say, a Code node transforming it wholesale — the only real fix is restructuring the workflow (streaming, pagination, or batching). The heap bump buys headroom; the payload discipline is the actual cure. And queue mode protects availability, not the crashed execution — an in-flight run on a dead worker is still lost.

## FAQ

### How do I know the exit code 137 was really an OOM kill?

`docker inspect <container> --format '{{.State.OOMKilled}}'` returns `true` only when the kernel's OOM killer did it. Exit code 137 plus `OOMKilled: true` is definitive. If OOMKilled is `false`, look for app-level errors in the logs instead.

### What should max-old-space-size be?

Roughly 70% of the memory available to the container — 2048 on a 4 GB container is the common starting point, 3072 on a 6–8 GB host. Never set it above physical RAM: Node can't use swap well, and an oversized heap just turns a clean abort into thrashing followed by a kill anyway.

### Does disabling execution data saving fix the OOM?

No. Execution save settings control what gets written to the *database* after a run; the items flowing through the workflow are held in *memory* during the run regardless. The settings in Step 4 reduce database bloat and speed recovery — they don't lower peak heap usage. Batching (Step 5) does.

### Should I just add more RAM instead of changing config?

More RAM helps, but it's the most expensive fix and it masks workflow problems. A 4 GB machine with batching and pruning outperforms an 8 GB machine running unbounded payloads — and when the unbounded workflow grows, it will crash the 8 GB machine too.

### Is queue mode required to fix OOM crashes?

No — queue mode fixes *blast radius*, not the crash. A worker still dies on a heap crash; the difference is the editor, webhooks, and other executions survive it. It's the right architecture for production, but Steps 2–5 fix the crashes themselves on any setup.

## Key Takeaways

1. **Confirm before you configure** — `OOMKilled: true` plus exit 137 is the only proof the crash is a memory problem; everything else is a guess.
2. **NODE_OPTIONS=--max-old-space-size=2048 raises Node's heap ceiling** — the five-minute stopgap, set to ~70% of the container's memory.
3. **Set a container memory limit** (`deploy.resources.limits.memory`) so failures are predictable kills of the right container, not the kernel picking victims.
4. **Batch large payloads and offload binary data to disk** — batching is the only fix that lowers peak heap usage; everything else manages the aftermath.
5. **Queue mode isolates the blast radius** — a worker crash stops killing the editor and webhooks along with it.

Next: if you're setting up the stack from scratch, read our queue mode walkthrough and the production hardening checklist so these settings are in place before the first crash, not after.

---
