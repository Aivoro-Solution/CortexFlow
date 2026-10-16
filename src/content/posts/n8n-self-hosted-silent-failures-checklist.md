---
title: "Self-Hosted n8n Failing Silently? The 12-Point Production Checklist"
description: "Self-hosted n8n dies quietly: full disks, rotating webhook URLs, dead encryption keys. A 12-point checklist from real outages, with fixes and verify steps."
date: 2026-10-17
category: automation
tags: ["n8n", "self-hosting", "docker", "production", "monitoring"]
draft: false
featured: false
image: "/og/n8n-self-hosted-silent-failures-checklist.webp"
---

Self-hosted n8n rarely dies loudly. There is no crash, no alarm, no error email — just a workflow that quietly stopped running three weeks ago, a webhook that changed address on restart, and a disk that filled up overnight with execution logs. By the end of this checklist you will have run 12 concrete checks against your own instance and fixed the ones it fails, with a verify step for each.

The failure list below is not theoretical. It is drawn from what real operators report on the n8n forum and Reddit: one operator's Postgres filled to 11 GB of execution logs in two months; another watched webhook URLs rotate every time the container restarted; several discovered that their encryption key died with the server. The Censys October 2026 scan also found [114,000 exposed n8n instances](/blog/censys-114000-exposed-n8n-hardening-checklist/), three-quarters of them running versions with known critical vulnerabilities — unpatched is its own silent failure.

![A technician repairing server hardware in a data center](/images/n8n-self-hosted-silent-failures-checklist/datacenter-technician.jpg)

## Check 1 — Your execution logs are filling the disk

A **webhook** is a URL that an external service calls to start your workflow; every call writes an execution record to n8n's database. On a busy instance those records grow fast — one operator reported 11 GB of execution data in two months on a single VPS. When the disk fills, Postgres stops accepting writes and everything fails at once, including the workflow that was supposed to warn you.

Set retention aggressively. In your n8n environment (`.env` or compose file):

```bash
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168      # hours: 7 days
EXECUTIONS_DATA_PRUNE_MAX_COUNT=5000
```

This tells n8n to prune old executions automatically. Keep `EXECUTIONS_DATA_PRUNE_HARD_DELETE_INTERVAL` in mind if you need audit trails — pruning deletes history you may later need for debugging.

**Verify:** `docker exec <n8n-container> df -h /` should show comfortable headroom, and Settings → Executions in the UI should show no records older than your max age.

## Check 2 — Your webhook URLs are pinned, not rotating

If n8n can't determine its own public URL, it generates webhook URLs from whatever the container thinks its hostname is — and that changes on every restart. The symptom is maddening: Stripe, WhatsApp, or GitHub webhooks worked yesterday and silently stopped, with n8n showing no error at all.

Pin the public URL explicitly:

```bash
N8N_HOST=automation.example.com
N8N_PROTOCOL=https
N8N_WEBHOOK_URL=https://automation.example.com/
```

`N8N_WEBHOOK_URL` is the one that matters — it is what n8n stamps into every webhook URL it displays. Without it, each redeploy silently re-registers (or breaks) every external integration.

**Verify:** open any webhook trigger node and confirm the Production URL matches your domain; restart the container and check the URL hasn't changed.

## Check 3 — Your encryption key exists somewhere other than the server

n8n encrypts every stored credential with a single key, `N8N_ENCRYPTION_KEY`. If the key is generated on first boot and stored only inside the container's volume, then a fresh volume, a botched redeploy, or a migration means the key is gone — and with it, **every credential becomes permanently undecryptable**. This is the failure with no recovery.

Generate a key once and store it in your password manager and your deployment config:

```bash
openssl rand -hex 24
```

```bash
N8N_ENCRYPTION_KEY=<paste-the-key-here>
```

> **Warning:** a *mismatching* key on first boot is just as fatal as a missing one — the instance will fail to start or show credentials as `unset`. Set the key before the first boot, and never let two instances share a database with different keys.

**Verify:** `docker exec <n8n-container> env | grep N8N_ENCRYPTION_KEY` prints a value (not from a default), and a credential created months ago still authenticates.

## Check 4 — Your database backup would actually restore

Two classic traps here. If you run SQLite (the default), copying the database file while n8n is running produces an **incomplete backup** — SQLite's WAL (write-ahead log, the journal where recent writes sit before being merged into the main file) may not be merged, so your "backup" silently misses recent data. If you run Postgres, a `latest` image bump across a major version (16 → 17 → 18) can refuse to start with "database files are incompatible with server" — bumping the tag alone kills the database.

For Postgres, back up with `pg_dump` on a schedule and test the restore:

```bash
docker exec <postgres-container> pg_dump -U n8n n8n > n8n-$(date +%F).sql
```

Never upgrade Postgres major versions by changing the image tag. The safe path is dump → fresh container on the new major version → restore → verify, with n8n stopped throughout.

**Verify:** restore the dump into a scratch Postgres container once a quarter and confirm workflows and credentials come back. A backup you have never restored is a hope, not a backup.

## Check 5 — Your health check actually checks something

A shallow health check — `curl https://your-host/healthz` returning 200 — tells you the web server is up. It tells you nothing about whether workflows execute, whether the database accepts writes, or whether the queue is moving. n8n can be "healthy" by this metric while silently broken.

Build a canary workflow: a Schedule Trigger that runs every 10 minutes, writes a timestamp row to your database (or a Data Table), and a second scheduled check that alerts you if the newest timestamp is older than 15 minutes. This is a **dead man's switch** — silence itself becomes the alarm.

![A system administrator organizing network cables](/images/n8n-self-hosted-silent-failures-checklist/sysadmin-cables.jpg)

**Verify:** stop the n8n main process for 20 minutes on purpose. You should get the alert. If you didn't, your monitoring has a hole.

## Check 6 — Failed executions reach a human

n8n's default error handling is per-workflow and easy to miss: a workflow fails, its execution log records it, and nobody looks. The forum thread "when a workflow quietly stopped in your own business, who noticed first?" resonated precisely because everyone has lived it — the client notices first.

Set a global error workflow (Settings → Error workflows) that posts to Telegram/Slack/email with the workflow name, the error message, and a link to the execution. Keep it short — an alert that reads like a log dump gets muted.

**Free template:** [Uptime Monitor with Incident Escalation](/templates/uptime-monitor-incident-escalation/) — download the n8n workflow JSON and get alerted the moment a workflow fails, before your users notice.

**Verify:** force a failure in a test workflow (a Code node that throws). The alert should arrive within a minute of the execution failing.

## Check 7 — Long-running steps survive the timeout

The HTTP Request node defaults to a 300-second timeout — fine for APIs, fatal for long LLM calls chained in a workflow. Worse, n8n 3.0 cuts the task-runner timeout from five minutes to one, so Code nodes that run long loops or wait on slow APIs will start failing after the upgrade with no code change on your part.

Audit your workflows for any step that can legitimately run longer than 60 seconds: LLM calls with big context windows, file processing, polling loops. For HTTP calls, raise `timeout` on the node; for Code nodes, break long work into smaller steps or move it to a sub-workflow with its own execution.

**Verify:** run your longest production workflow end to end and check its total execution time against the timeout of its slowest step. Anything within 20% of the limit is a future incident.

## Check 8 — You are not months behind on security patches

Self-hosted n8n does not patch itself. The [October 2026 security update](/blog/n8n-october-2026-security-update/) bundled 14 advisories — including agent-node credential leaks and webhook execution flaws — and the Censys scan found 76% of parseable exposed instances vulnerable to at least one critical CVE. An unpatched instance is not just insecure; several of those advisories describe silent failures (cross-project execution, unauthenticated approvals of waiting executions).

Pin a version and update monthly, not yearly:

```bash
docker compose pull n8n
docker compose up -d n8n
docker exec <n8n-container> n8n --version
```

Read the breaking-changes notes before crossing a major version — 3.0 removes legacy nodes and ends npm/npx installs.

**Verify:** compare your running version against the latest stable on [n8n's releases page](https://github.com/n8n-io/n8n/releases). If you are more than two minor versions behind, schedule the upgrade this week.

## Check 9 — Your triggers are actually listening

Trigger nodes fail in ways the editor never shows you. The IMAP Email Trigger has at least four documented failure modes: it silently stops receiving (no executions, no errors), a malformed message can crash the process, some providers need different connection settings, and credential tests pass while the trigger stays dead. The same pattern applies to any polling trigger — Postgres Trigger channels going quiet, Schedule Triggers lost on leadership handoff in multi-main setups.

Treat every trigger as guilty until proven innocent: each production trigger gets a heartbeat. Add a final step to trigger-driven workflows that logs a heartbeat timestamp, and alert (Check 5's dead man's switch) when it goes stale.

**Verify:** pick your three most business-critical triggers and confirm each has fired in the last 24 hours. A trigger with no recent executions and no error is the most dangerous state your instance can be in.

## Check 10 — Your Postgres upgrade plan exists on paper

This deserves its own check because it is the upgrade most likely to be done casually and most likely to destroy data. `postgres:16` → `postgres:18` by changing one tag will not migrate your data; it will refuse to start. Every Postgres major release triggers a wave of broken self-hosted instances, and n8n's own hosting docs call this out explicitly.

The runbook: stop n8n, `pg_dump` the database, spin up the new major version on a fresh volume, restore, point n8n at it, verify workflows run, keep the old volume until you are sure. Budget a maintenance window — there is no zero-downtime path for a single-node Postgres.

**Verify:** you have a written runbook (even a checklist in a doc) and a tested backup (Check 4). If the plan is "figure it out when the time comes," you don't have a plan.

## Check 11 — Workflows are versioned outside n8n

n8n has no built-in dev-to-production promotion: workflows live in the database, edits and published versions drift apart, and "it worked in my test run" is not version control. When an instance dies, restoring the database restores the workflows — but restoring individual workflows, reviewing what changed, or rolling back a bad edit is painful without exports.

Export workflows to git on a schedule — the n8n CLI or a scheduled workflow that hits the API and commits JSON to a repo. This also gives you a diff history, which the database never will.

**Verify:** pick a workflow, find its last three versions in your git history, and confirm you could re-import any of them. If the answer is "the database has it," you have one copy of everything that matters.

## Check 12 — Your install method survives n8n 3.0

If you installed n8n with npm or npx, that road ends at 3.0: self-hosted n8n requires Docker from 3.0 onward, and npm installs will no longer receive updates — including security patches. Running `npx n8n` on a VPS past the 3.0 release means a silently unmaintained instance, which is Check 8's nightmare scenario on autopilot.

Migrate before the upgrade, not during it: stand up the official Docker Compose stack (Postgres + n8n), export workflows and credentials from the npm instance, import them into the Docker one, switch DNS, and keep the old instance stopped-but-intact for a week.

**Verify:** `which n8n` should not be how your production instance starts. If it is, the migration is your highest-priority item on this list.

## What this checklist won't cover

This is a single-node, Docker Compose view of the world — the setup most self-hosters run. It does not cover multi-main HA clusters, custom task-runner scaling, or execution loads above ~100k/day, where you need queue mode tuning and real SRE practices. I also did not test every fix against n8n 3.0 release candidates; verify timeout and node-removal behavior against the 3.0 breaking-changes doc before upgrading. If downtime costs you money and this list feels long, n8n Cloud exists precisely to make it someone else's checklist — that is a legitimate engineering decision, not a failure.

## FAQ

### How often should I run through this checklist?

Quarterly for the full list, monthly for Checks 1, 5, and 8 (disk, heartbeats, patches). Automate what you can — the canary workflow and disk alerts should be permanent, not quarterly rituals.

### Is self-hosted n8n safe for client work?

Yes, with this checklist in place — several freelancers run client workloads on single VPS instances. The failure mode is never n8n itself; it is the absence of pruning, backups, monitoring, and patching. If you cannot commit to those four, use n8n Cloud.

### Should I use SQLite or Postgres for self-hosted n8n?

Postgres for anything production. SQLite is fine for trying n8n out, but its backup story (Check 4) and its behavior under concurrent load make it a liability for scheduled, business-critical workflows.

### What is the single highest-impact fix on this list?

Pin your webhook URL (Check 2) and back up your encryption key (Check 3) today — both take five minutes, and both failures are unrecoverable-by-design. Then set up execution pruning (Check 1) and a dead man's switch (Check 5).

## Key Takeaways

1. **Self-hosted n8n fails silently by default** — no crash, no alarm, just workflows that stop and webhooks that move.
2. **Disk, keys, and URLs are the unrecoverable trio** — prune execution logs, back up `N8N_ENCRYPTION_KEY` off-server, and pin `N8N_WEBHOOK_URL`.
3. **Monitor for silence, not just errors** — a canary workflow plus a dead man's switch catches the failures that never raise an exception.
4. **Patch monthly and plan Postgres upgrades on paper** — 14 advisories in one October batch is the new normal, and major-version Postgres upgrades are never a tag bump.
5. **Back up what you can't regenerate** — database dumps you have restored, workflows in git, and an install method (Docker) that survives 3.0.

Next: run Checks 2 and 3 right now — they take five minutes each. Then set a monthly calendar reminder for Checks 1 and 8, and read the [n8n 3.0 breaking-changes guide](/blog/n8n-3-breaking-changes/) before the upgrade window closes.

*Images: Pexels (Field Engineer, cottonbro studio)*
