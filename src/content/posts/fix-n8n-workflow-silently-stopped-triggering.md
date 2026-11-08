---
title: "Fix n8n Workflow That Silently Stopped Triggering (No Error, No Executions)"
description: "Your n8n workflow is active, manual runs work, but the trigger never fires — no error, no execution. 7 verified fixes."
date: 2026-11-08
category: automation
tags: ["n8n", "error fix", "schedule trigger", "webhook", "queue mode", "monitoring"]
draft: false
featured: false
image: "/og/fix-n8n-workflow-silently-stopped-triggering.webp"
---

Your workflow was running fine for weeks. Then a client messages you: "Hey, are the leads still syncing? We haven't seen anything come through since Tuesday." You open n8n expecting a wall of red. There isn't one. The workflow is active. You hit Execute Workflow and it runs perfectly — pulls the records, syncs them, finishes green. So you scroll to the execution list, and that's when it sinks in: the only recent entry is the manual run you just triggered. The scheduler didn't fail on Tuesday. It simply never tried to run.

This is the worst failure mode in n8n, because every debugging tool you own assumes a run exists. The Error Trigger only fires when an execution fails. A missed run produces no execution, no error, and no log line in the workflow — so there is nothing for your error handling to catch. By the end of this guide you will know how to find which of the seven causes stopped your trigger, fix it, and set up the one monitor that actually catches a silent stop next time. All fixes are verified against community reports and GitHub issues, as of November 2026.

**Prerequisites:** a self-hosted or Cloud n8n instance (self-hosted for the queue-mode and pruning fixes), shell access to the host if you run Docker, and the workflow ID of the silent workflow (visible in the URL when the workflow is open in the editor).

## Step 0 — Diagnose in two minutes: read the executions list first

Before touching anything, open the workflow and click **Executions**. What you see splits the problem in half, and it decides which steps below apply to you.

| What the executions list shows | What it means | Go to |
|---|---|---|
| No execution at all since the last good run | The trigger never fired | Steps 1–6 |
| A failed execution | The trigger fired; something downstream broke — read the failing node, this guide is not your problem | The error message names the node |
| Executions exist, but at the wrong hour | The trigger fires on a different clock than you think | Step 3 |
| An execution stuck in `running` for hours | A hung run is blocking the workflow | Step 5 |

Two traps when reading this list. First, **manual runs count**: clicking Execute Workflow in the editor saves an execution, so a workflow that looks recently active may only have been run by hand. Filter by mode and look for production runs specifically. Second, **pruning eats history**: `EXECUTIONS_DATA_MAX_AGE` defaults to 336 hours (14 days), so for a monthly workflow an empty result can mean the last run was deleted, not that it never ran. Workflows set to not save successful executions only ever show failures.

## Step 1 — Confirm the workflow is actually published

This is the single most common cause, and the easiest to overlook once you have been staring at the canvas for an hour. Since n8n 2.0, the old Active toggle is gone. Your edits save automatically as a draft, and **nothing goes live until you click Publish**. Production always runs the last published version — never your latest edits.

Check three things:

1. The workflow shows **Published** in the editor header — not "Published, has changes", which means your latest edits are still a draft.
2. There is a real trigger node. A Manual Trigger only runs when you click it; a workflow needs a Schedule, Webhook, or app trigger to run by itself, and since 2.0 n8n will not publish a workflow without one.
3. If you edited a published workflow, publish again (Shift+P). A publish can also partly fail, with some triggers switched on and others not — republish and check the trigger state.

If your workflow uses a webhook, the same publish rule applies to the URL. The **test URL** (with `/webhook-test/` in it) only listens for 120 seconds after you click Listen for test event. The **production URL** (with `/webhook/`) is live whenever the workflow is published — and its runs appear in the Executions tab, not on the canvas, which is expected, not a fault. A webhook that worked in testing and then went quiet is very often still pointing at the test address. If you publish and the webhook still never registers, the registration step itself may be the problem — see [Fix n8n WhatsApp Trigger Production Webhook Never Registering](/blog/fix-n8n-whatsapp-trigger-production-webhook/) for the full production-registration checklist, which applies to any app trigger, not just WhatsApp.

## Step 2 — Check whether the trigger's upstream went quiet

A trigger can only fire when something calls it. For polling triggers (Google Sheets, IMAP, app triggers), the upstream app can silently stop delivering while n8n looks healthy.

- **OAuth credentials in "Testing" mode expire.** If your workflow uses a Google credential and the OAuth consent screen is still in Testing in Google Cloud, Google expires the refresh token after about 7 days. The credential test still passes while the trigger is dead. Publish the consent screen, reconnect the credential, and republish the workflow.
- **App-side subscriptions expire.** Microsoft Teams subscriptions cap at 3 days; a polling trigger whose subscription lapsed simply stops receiving. The same pattern hits any trigger backed by a webhook subscription — see [Fix n8n Microsoft Teams Trigger Stopping After a Few Days](/blog/fix-n8n-teams-trigger-silent-stop/) for the renewal pattern.
- **Send a canary through the real path.** For event-driven triggers, silence alone cannot distinguish "no customers today" from "dead trigger". Send a real test event through the actual upstream — a real email to the IMAP mailbox, a real form submission — and watch the executions list. A direct webhook ping tests the webhook; it does not test the email delivery path.

## Step 3 — Pin the timezone (your 9 AM may be running at 1 AM)

If executions exist but land at the wrong hour, the trigger is firing — on a different clock than yours. The Schedule Trigger has no timezone field of its own. It follows a fixed precedence: the **workflow's Timezone setting** if you set one, otherwise the instance timezone from the `GENERIC_TIMEZONE` environment variable, and if neither is set, self-hosted n8n defaults to **America/New_York**.

That last default is the trap. Your container clock is UTC, your `TZ` variable is UTC, and your schedule still fires on New York time — because `TZ` only sets the container's system clock (what `date` prints, what Code nodes see). It is never consulted when a Schedule Trigger fires.

Fix it with both variables in your Compose file, under the n8n service:

```yaml
services:
  n8n:
    environment:
      - GENERIC_TIMEZONE=Asia/Kolkata
      - TZ=Asia/Kolkata
```

Here's what each key does: `GENERIC_TIMEZONE` is the n8n instance timezone — the one Schedule Triggers and the Date & Time node use. `TZ` is the container's system timezone — logs and scripts. Set both to the same IANA zone name (`Region/City` form). Then apply with `docker compose up -d`, not `docker compose restart` — a restart reuses the container's existing environment, so the file changes and the running process does not.

Verify with the first real run, not with config alone. Put a guard as the first node that logs the actual execution time with its zone:

```
{{ $now.toFormat('yyyy-MM-dd HH:mm z') }}
```

If the first real run does not say what you expect, you catch it on day one — not via a client at 1 AM. Two more timezone notes: a workflow-level Timezone setting (canvas, three dots, Settings) overrides `GENERIC_TIMEZONE` for that one workflow, and if your pinned zone observes daylight saving, avoid the 1:00–3:00 AM window — cron can double-fire or skip on transition days.

## Step 4 — Queue mode: check who owns the scheduler

If you run queue mode (`EXECUTIONS_MODE=queue`), the Schedule Trigger is owned exclusively by the **main process (the leader)**. Workers execute jobs; they never schedule. Three queue-mode-only failure modes wedge the scheduler silently:

1. **More than one main replica.** If your Helm chart or Compose file runs two `main` processes — or an old pod persists during a rolling update — you get "ghost triggers" and registration conflicts in Redis that eventually wedge the scheduler. Exactly one main replica may run.
2. **A worker running the wrong command.** If a worker pod runs `n8n start` instead of `n8n worker`, it attempts to act as a main process and competes for the scheduler. Check every pod's start command.
3. **Known scheduler bugs on older versions.** GitHub issues #30220 and #30256 describe the Schedule Trigger silently stopping after roughly 700+ ticks on high-frequency workflows: a recursion/stack-overflow error in the trigger's activation logic. The crash happens in the scheduler's internal loop *before* an execution is created, so it never appears in the execution logs — only in the main container's stdout/stderr. A related issue (#28423) used a strict-equality check to decide whether it was time to fire, so a missed tick could block a workflow for days; the fix changed it to an elapsed-time check that self-heals. If your main container logs show stack-overflow errors from the scheduler, or your schedule stopped after hundreds of ticks, **upgrade n8n** — then restart the main instance and republish the affected workflows so the triggers re-register cleanly.

Diagnose by checking the main container's logs, not the execution list: `docker logs <n8n-main-container> 2>&1 | grep -i -E "scheduler|trigger|stack"`. If the logs are clean and the schedule still never fires, the trigger simply did not re-register after the last restart — unpublish and republish the workflow, which forces re-registration.

## Step 5 — Unstick a hung execution or a wedged execution queue

A workflow can also go silent because an earlier run never finished. A stuck execution holds the workflow: the scheduler thinks it is still running, and the UI can freeze when you try to deactivate it because the deactivation waits on a lock that never releases.

1. Open **Executions**, filter by **Running**, and stop any active instance of the workflow.
2. If the UI will not let you deactivate it, restart the container: `docker restart <n8n-container-name>`. A full restart kills lingering child processes and clears stuck transactions.
3. If executions are piling up behind a concurrency overload, the internal queue counter can get stuck even when the dashboard shows 0 active. Prune old executions and restart:

```bash
docker exec -it <your-n8n-container> n8n execution:prune
docker restart <your-n8n-container>
```

Then prevent the pile-up from recurring. Cap execution history in your environment so the executions table cannot grow until Postgres becomes the bottleneck or the disk fills:

```yaml
environment:
  - EXECUTIONS_DATA_PRUNE=true
  - EXECUTIONS_DATA_MAX_AGE=336        # keep 14 days
  - EXECUTIONS_DATA_PRUNE_MAX_COUNT=50000
```

`EXECUTIONS_DATA_PRUNE=true` turns pruning on; `EXECUTIONS_DATA_MAX_AGE=336` keeps 14 days of history; `EXECUTIONS_DATA_PRUNE_MAX_COUNT=50000` caps the total retained runs. On the default SQLite database, freed space is only reused, never returned to the OS — so pruning early matters more than pruning late. The same disk-fill failure mode is covered in the wider checklist at [Self-Hosted n8n Failing Silently? The 12-Point Production Checklist](/blog/n8n-self-hosted-silent-failures-checklist/).

## Step 6 — Handle runs missed while n8n was down

Before n8n 2.45, the default scheduler did not persist schedules: anything due while the server was rebooting or the container was updating was **skipped, not caught up**. A restart at the wrong minute silently ate a run, and nothing flagged it.

The durable scheduler arrived in n8n 2.36 (off by default) and is on by default from 2.45. It writes upcoming runs to the database first, so a run that is slightly late (within 60 seconds by default) still fires. Beyond that window, the **If Execution Is Missed** option in the Schedule Trigger's Settings tab decides whether to run one catch-up execution — and the default is not to.

So: if you are on 2.45 or later, open the Schedule Trigger, go to Settings, and set **If Execution Is Missed** to run a catch-up for any workflow where a missed run is worse than a late run (invoices, digests, syncs). For workflows where a late duplicate is worse than a skip (a "good morning" message at 3 PM), leave the default. And if you are on an older version, upgrade — or accept that every deploy window can silently eat a scheduled run.

## Step 7 — Prevent the next silent stop: monitor from outside n8n

This is the step most people skip, and it is the only one that actually catches the failure. Your Error Trigger workflow cannot do it: it fires when an execution fails, and a missed run is not an execution. You need a monitor that notices *absence*.

**The external heartbeat (best for scheduled workflows).** Add an HTTP Request node as the last step of the workflow you care about, calling your heartbeat service's ping URL after the expected work succeeds. Healthchecks.io is the usual free choice: set the actual schedule plus a grace period, so a weekly workflow is not expected to report daily. The alert must live **outside** the n8n instance — otherwise the monitoring workflow can stop alongside everything else it is supposed to watch.

**The execution-age guard (best if you want it inside n8n).** A separate scheduled workflow that checks whether the guarded workflow ran recently, using the n8n node with an API key:

1. Schedule Trigger (every hour, or twice the guarded workflow's interval).
2. n8n node → **Execution → Get Many**, filtered by the guarded workflow, limit 1.
3. IF node: is the latest execution's `startedAt` older than expected (twice the interval)?
4. If yes, send the alert (Telegram, Slack, email).

Mind the guard's own blind spots: limit 1 also returns manual runs, so a hand test resets the "last run" clock and makes a dead schedule look fresh — filter those out or ignore manual executions. And remember pruning: with the 14-day default, a monthly workflow's empty result may mean the run was deleted, not that it never ran.

For event-driven workflows, the only honest monitor is a canary: an independently scheduled test email (or test event) with a unique marker that the real trigger receives, acknowledges to the monitor, and routes away from customer-facing actions.

## Verify it worked

Run this regression check after any fix, and again after your next deploy:

1. Confirm the workflow shows **Published** with no "has changes" badge.
2. Trigger it through the real path (wait for the next schedule tick, or send a real upstream event) — not a manual run.
3. Confirm a production execution appears in the Executions tab with the correct timestamp and timezone.
4. Confirm the heartbeat ping arrived (Healthchecks.io shows the check green) or the guard workflow reports a fresh run.
5. After the next container restart or deploy, repeat steps 2–4. A schedule that re-registers cleanly after a restart is the actual fix; a schedule that only works until the next deploy is not.

## Limits and trade-offs

- This guide covers the trigger never firing. If your workflow fires and then hangs after the trigger — executions stuck in `running` with only the trigger's output — that is a different failure (node dispatch or execution-mode issue), and the fixes here will not help.
- The heartbeat pattern adds one HTTP call per run and one external dependency. For workflows that run every minute, prefer the execution-age guard — a ping per minute is noise, and the guard's hourly check is enough.
- The durable scheduler's catch-up only applies to Schedule Trigger nodes added in 2.45 or later (or upgraded triggers); older trigger nodes keep the old skip-on-miss behaviour until you recreate them.
- I did not test the queue-mode ghost-trigger scenario against a live multi-replica cluster; the diagnosis comes from the community thread and the GitHub issues cited, not from a reproduction.

## FAQ

### Why doesn't my Error Trigger workflow catch a workflow that stopped triggering?

Because the Error Trigger fires when an execution fails, and a workflow that never triggers produces no execution. There is nothing to fail. It can also receive trigger and activation errors that happen before an execution exists, but it still cannot catch an upstream system silently stopping deliveries. Only absence-detection — a heartbeat or an execution-age guard — catches this class.

### My workflow runs when I click Execute, but never on its own. What is the most likely cause?

Publish state. Since n8n 2.0, edits save as drafts and production runs the last published version. Confirm the workflow shows Published (not "Published, has changes"), that it has a real trigger node rather than only a Manual Trigger, and — for webhooks — that the upstream is calling the production URL (`/webhook/`), not the test URL (`/webhook-test/`), which only listens for 120 seconds.

### My schedule fires, but at the wrong hour. What do I check first?

The timezone chain: workflow Timezone setting first, then `GENERIC_TIMEZONE`, then the built-in default of America/New_York. Set `GENERIC_TIMEZONE` explicitly in your Compose file (and `TZ` alongside it for the container clock), apply with `docker compose up -d`, and verify with a first node that logs `{{ $now.toFormat('yyyy-MM-dd HH:mm z') }}`.

### Does upgrading n8n fix a Schedule Trigger that silently stops after days?

Often, yes — if you are on an affected version. The ~700-tick stack-overflow stall (GH #30220, #30256) and the strict-equality missed-tick bug (#28423) were scheduler bugs fixed in later releases, and the durable scheduler (on by default from 2.45) stops missed runs from vanishing during restarts. Upgrade, restart the main instance, and republish the affected workflows so triggers re-register.

## Key Takeaways

1. **No execution means the trigger never fired** — read the executions list before touching any node, and remember manual runs and 14-day pruning can both lie to you.
2. **Publish state is the most common cause** — since n8n 2.0, Save is not Publish, and production runs the last published version.
3. **Pin the timezone explicitly** — workflow setting beats `GENERIC_TIMEZONE`, which beats the America/New_York default; `TZ` alone never affects schedules.
4. **In queue mode, the main instance owns the schedule** — one main replica only, workers must run `n8n worker`, and scheduler bugs live in the main container's logs, not the execution list.
5. **Error handling cannot catch absence** — only an external heartbeat or an execution-age guard notices a run that never started.

Next: pick your three most business-critical scheduled workflows and add the heartbeat ping today — it takes ten minutes per workflow, and it is the difference between finding out from a client on Tuesday and finding out from an alert within the hour. If your workflows depend on webhooks rather than schedules, read [Fix n8n Webhook Retries Causing Duplicate Orders/Charges](/blog/fix-n8n-webhook-duplicate-idempotency/) next — the other silent failure that only shows up downstream.
