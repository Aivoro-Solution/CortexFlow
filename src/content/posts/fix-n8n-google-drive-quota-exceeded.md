---
title: "Fix n8n Google Drive \"Quota Exceeded\" Errors in Production (5 Fixes)"
description: "Google Drive worked in testing, then production died with \"Quota exceeded for quota metric 'Queries'\". Diagnose the exact quota and fix it — 5 verified steps."
date: 2026-11-07
category: automation
tags: ["n8n", "google-drive", "error-fix", "quotas", "self-hosting"]
draft: false
featured: false
image: "/og/fix-n8n-google-drive-quota-exceeded.webp"
---

Your Google Drive workflow ran fine for weeks. Then, the moment real volume hit it, every execution started failing with **"Quota exceeded for quota metric 'Queries' and limit 'Queries per minute' of service 'drive.googleapis.com'"**. Nothing in the workflow changed. The credential still tests fine. The files are still there. What changed is the volume — and Google is now enforcing a limit your testing never came close to.

By the end of this guide you will know exactly which quota you hit, how to get the workflow running again today, and how to set things up so a quota error can never silently kill a production workflow again.

**Example terminology** — used consistently in every command and click-path below:

- `<project>`: your Google Cloud project that owns the OAuth client n8n uses for Google Drive (find it in the error message as `project_number:...`)
- `<workflow>`: the n8n workflow hitting the error

## The symptom

The failing node — usually a Google Drive or Google Sheets node, or a Drive Trigger — returns an error like this:

```text
Quota exceeded for quota metric 'Queries' and limit 'Queries per minute'
of service 'drive.googleapis.com' for consumer 'project_number:123456789012'.
```

Three things about this error are worth reading carefully, because the fix depends on them:

1. **The metric is `Queries`.** This is Google's count of Drive API calls. Every poll, every file list, every download counts against it.
2. **The limit names its window** — here, per minute. The same error can name a per-day limit instead; the fix differs.
3. **The consumer is a project number, not a user.** The quota belongs to the Google Cloud project behind your n8n OAuth credential. Every workflow using credentials from that project draws from the same pool — which is why one busy workflow can break five quiet ones that share the project.

The error usually arrives as a `403` from Google. It is not an n8n bug and not an authentication failure — your credential is valid, which is exactly why the credential test still passes while executions fail.

## The root cause

**Google Drive API quotas are enforced per Google Cloud project (and, for some limits, per user within that project).** Your n8n instance makes Drive API calls through one OAuth client, registered in one project. In development, a handful of manual runs barely register. In production, three things multiply the call count until it crosses the line:

- **Trigger polling.** A Google Drive Trigger checks for changes on an interval — often every minute. Each poll is one or more queries, all day, whether or not anything changed.
- **Per-item calls.** A node that lists files, then acts on each file, multiplies one trigger event into dozens of queries. Ten files per poll at one poll per minute is 600 queries an hour before the workflow does anything useful.
- **Shared quota pool.** Every workflow that uses a Google credential from the same Cloud project shares the same quota. One workflow's burst is every workflow's outage.

The reason this feels sudden is that quotas are a cliff, not a slope: everything works at 99% of the limit and fails at 101%. A workflow that grew from 20 files a day to 200 did not get 10x slower — it went from fine to dead overnight.

## Prerequisites

- Access to the Google Cloud Console for the project behind your n8n Google credential (the project number is in the error message).
- Admin access to your n8n instance to edit the workflow and its credential.
- The exact error text from a failed execution — copy it from the Executions tab, because it names the metric and the project.

## Step 1 - Diagnose which quota you actually hit

Do not guess. The error names the metric, the limit, and the project — go read the numbers.

In the Google Cloud Console, open the project from the error message, then go to **IAM & Admin → Quotas**. Filter the list by service `drive.googleapis.com` and find the **Queries** metric. You will see the current usage against the limit, and whether the exhausted dimension is per-minute, per-day, per-project, or per-user. Check the usage graph for the time the failures started — a cliff at that hour confirms the diagnosis.

**You should see one of two patterns:**

- **Per-project quota exhausted:** usage across all your workflows hit the project-wide ceiling. Every Drive workflow in that project fails at once. Go to Fix 3.
- **Per-user quota exhausted:** one credential (one user) is making all the calls while the project still has headroom. Go to Fix 2 and Fix 4 — and check whether one trigger is polling far more often than the rest.

> **Note:** Do not confuse this with a `429` rate-limit error. A 429 means "slow down right now"; a quota error means "you have used up this allowance for the window". Both need pacing, but only the quota error needs the console-side changes in Fixes 2 and 3.

## Step 2 - Slow the polling (the fix that works today)

The fastest relief is to make fewer calls. Open the Google Drive Trigger (or Sheets Trigger) in the workflow and change its polling interval from every minute to **every 5–10 minutes**. This alone cuts trigger queries by 5–10x, and it is the same fix that stops Google Sheets nodes from tripping Google's per-minute throttles — every-minute polling is the single most common self-inflicted quota burn in n8n.

While you are there, narrow what the trigger watches: a trigger pointed at a whole shared drive polls far more than one pointed at a single folder, and a trigger that fires on every change type when you only need new files wastes queries on events you ignore downstream. Save, activate the workflow, and re-run it — if the error was a polling burn, executions should succeed within a minute.

## Step 3 - Give n8n its own quota project (the fix that raises the ceiling)

Slowing polling lowers your usage; this step raises your allowance. Create a **separate Google Cloud project** for n8n, enable the Drive API in it, create a new OAuth client, and re-create the Google Drive credential in n8n against the new project. The new project gets its own quota pool, so n8n's usage no longer competes with anything else — and a burst in one workflow can no longer take down the others.

Here is the order that matters:

1. In the Cloud Console, create the new project and enable the Google Drive API (APIs & Services → Library → Google Drive API → Enable).
2. Create the OAuth consent screen and client ID in the new project — the same steps as your original credential setup. If you need the exact redirect URI, see [the Google OAuth2 redirect-URI guide](/blog/fix-n8n-google-oauth2-redirect-uri-mismatch/).
3. In n8n, create a new Google Drive credential with the new client ID and secret, and point the workflow's Drive nodes at it.
4. Run the workflow once and confirm the error is gone.

This is also the moment to stop sharing one OAuth client across everything: one credential per project boundary (one per client, or one per high-volume workflow) means a quota event stays local instead of cascading. The Reddit version of this lesson is blunt — one shared API key hit its cap and broke five workflows at once.

If a separate project is not an option, request a quota increase instead: on the same Quotas page, select the Queries metric, click **Edit Quotas**, and submit the increase with a short justification. Google reviews these manually, it can take days, and approval is not guaranteed — treat it as a backup plan, not the primary fix.

## Step 4 - Pace the workflow so bursts cannot trip the limit

Even with headroom, a burst can still cross a per-minute limit: a trigger fires, 200 files arrive, and the workflow hammers the Drive API 200 times in ten seconds. Pace it with the two nodes built for exactly this:

- **Loop Over Items (Split in Batches)** before the Drive calls, with a small batch size (5–10 items per batch).
- **Wait** node inside the loop, pausing 5–10 seconds between batches.

A batch of 10 files every 10 seconds is 60 queries a minute instead of 200 in ten seconds — same work, no cliff. If you want the general pattern behind this, [the token-bucket rate limiter guide](/blog/n8n-token-bucket-rate-limiter/) builds the same idea as a reusable gate for any API.

## Step 5 - Make quota hits survivable with retries

Quotas refill — per-minute limits continuously, daily limits at midnight Pacific — so a short, patient retry often succeeds where an immediate re-run fails. On every Google node in the workflow, open **Settings → Retry on Fail**, turn it on, and set a wait between retries (30–60 seconds) with 3–5 attempts. The node will back off and retry instead of failing the execution on the first quota hit.

For nodes where a single failure should not kill the whole run, also consider **Continue on Fail** in the node settings — the workflow keeps going and you handle the failed branch explicitly (for example, logging the file ID to a retry queue) instead of losing the entire batch.

## Verify it worked

Run the workflow at production volume — not one test file — and check three things:

1. **The Executions tab shows green** across several consecutive runs, with no `Quota exceeded` errors.
2. **The GCP Quotas page shows usage comfortably below the limit** during those runs, with no cliff at the old failure time.
3. **Downstream results are complete** — spot-check that every file the trigger saw actually got processed. A quota error mid-batch can silently drop files, so count outputs against inputs once.

## Dead ends: what NOT to do

- **Do not just re-run the failed execution.** Each retry burns more quota against the same exhausted limit. Diagnose first, then re-run.
- **Do not add more workers or raise n8n's concurrency.** Parallelism makes more API calls per second, which is the opposite of what an exhausted quota needs.
- **Do not create more OAuth credentials in the same project.** Credentials share the project's quota pool — a second credential in the same project draws from the same allowance and changes nothing.
- **Do not assume it is an n8n bug.** The credential test passing while executions fail is the signature of a Google-side quota, not an n8n-side fault.

## Prevent it next time

- **Set a quota alert.** In the Cloud Console, create an alert on the Drive API Queries metric at 80% of the limit. You want a warning a week before the cliff, not an error message after it.
- **Keep production polling at 5 minutes or slower** unless a workflow genuinely needs faster. One minute is a development default, not a production setting.
- **One quota project per boundary.** A separate Cloud project per client — or per high-volume workflow — caps the blast radius of any single burst.
- **Test at production volume before go-live.** A workflow tested with 5 files and shipped to 500 will find the quota on its first real day. Run a full-volume dry run once and watch the Quotas page while it runs.

## FAQ

### Is "Quota exceeded" the same as a 429 rate-limit error?

Related, not identical. A 429 means you are calling too fast right now; backing off for seconds fixes it. A quota error means you have used up an allowance for the window (per minute or per day); it needs fewer calls overall or a bigger allowance. Both are fixed by pacing, but only the quota error needs the console-side changes in this guide.

### How long until the quota resets?

Per-minute quotas refill continuously — wait a minute and retry. Daily quotas reset at midnight Pacific time. If the error names a per-minute limit and retries still fail after several minutes, you are hitting the limit continuously, not waiting it out — slow the polling instead.

### Can I just pay Google to raise the limit?

You can request an increase from the Quotas page, and a billing-enabled project is usually required for higher limits. Requests are reviewed manually and can take days. A separate project (Fix 3) is faster and also isolates you from other workloads sharing the pool.

### Why did this work for months and then break overnight?

Because quotas are cliffs. Your usage grew gradually — more files, more workflows, one more trigger — and stayed just under the limit until one ordinary day pushed it over. The fix is not to go back to last month's volume; it is to add the headroom and pacing in this guide so growth does not hit the same cliff again.

## Key Takeaways

1. **Read the error — it names the metric, the limit, and the project.** Diagnose in the GCP Console Quotas page before changing anything.
2. **Slow the polling first** — 1 minute to 5–10 minutes cuts trigger queries 5–10x and fixes most production quota errors the same day.
3. **A separate Cloud project is the only fix that raises the ceiling** — new project, new OAuth client, new credential; never share one quota pool across everything.
4. **Pace bursts with SplitInBatches + Wait, and retry with backoff** — the same file count spread over minutes instead of seconds never trips a per-minute limit.
5. **Alert at 80%, not at failure** — a quota alert in the console turns the next cliff into a warning you act on a week early.

Next: if your workflows call other Google APIs too, the same quota mechanics apply to Sheets, Gmail, and Calendar — audit their polling intervals with the same checklist. And if you want pacing as a reusable pattern instead of per-workflow fixes, [the token-bucket rate limiter](/blog/n8n-token-bucket-rate-limiter/) shows how to build one gate that protects every API your workflows touch.
