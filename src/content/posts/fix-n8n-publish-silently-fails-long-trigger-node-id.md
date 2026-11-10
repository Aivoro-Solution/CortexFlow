---
title: "Fix n8n Publishing Silently Failing When a Trigger Node ID Exceeds 36 Characters (Postgres)"
description: "You publish in n8n, the editor says success — but production still runs the old version. A 36-character Postgres column is the culprit. Here is the fix."
date: 2026-11-10
category: automation
tags: ["n8n", "postgres", "publishing", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-publish-silently-fails-long-trigger-node-id.webp"
---

You edit a workflow, hit Publish, and n8n says it worked. The API returns HTTP 200, the editor shows the workflow as published, and the database even records the new version as active. Then you call the production webhook — and it answers with the old version. You publish again. Still the old version. There is no error anywhere in the UI, and nothing in the execution list, because nothing ever executed.

This is a real, confirmed bug in n8n's publish path, and it has one root cause: **a Postgres column that only holds 36 characters for a trigger node's id**. If your workflow was created or imported through the public API or source control, its trigger node can carry an id of 37 to 54 characters — and every publish after that silently does nothing. By the end of this article you will know how to prove you have this bug in one minute, unstick the workflow, and make sure it can never happen again.

Quick definitions before we start: **publishing** in n8n 2.x means activating a workflow version for production — saving a draft is not enough, only the published version runs on production webhook URLs. A **trigger node** is the node that starts a workflow (Webhook, Schedule, Email Trigger, and so on). A **node id** is the internal identifier n8n assigns to each node in a workflow's JSON — normally a standard 36-character UUID like `266791f8-fd1a-49e7-a715-794b058b2941`. The **publish outbox** is n8n's internal queue that applies a publish to the running instance: it writes the trigger's registration into the database and, if that write fails, retries it.

This is a verified bug, not a configuration mistake: [GitHub issue #40606](https://github.com/n8n-io/n8n/issues/40606) (filed October 7, 2026) reproduces it cleanly on n8n 2.41.4 and 2.42.7 with the official Docker images and Postgres 16, and a second report arrived as [#40847](https://github.com/n8n-io/n8n/issues/40847). The permanent fix landed as [PR #41007](https://github.com/n8n-io/n8n/pull/41007) ("Widen node id columns to 64 characters"). As of November 10, 2026, if you are on an affected version, the workarounds below are the fix.

**Prerequisites:** a self-hosted n8n instance backed by Postgres (this bug does not affect SQLite instances, which do not enforce the 36-character column width), shell access to the host or container, and `psql` or another way to query your Postgres database.

> **Note:** this article is about publishes that *report success* while production keeps serving the old version. If your edits never reach production because you saved a draft but never published it, that is the draft-vs-published trap, covered in [Fix n8n Workflow Changes Not Taking Effect in Production](/blog/fix-n8n-workflow-changes-not-taking-effect/). If the Publish button itself hangs on "Publishing…" forever, that is a different failure — the instance's publish path has stopped answering, and a restart is the first move.

## The symptom: what the failure actually looks like

The failure has one consistent fingerprint, reproduced in the issue report with two otherwise identical workflows — a Webhook node plus a Set node returning `{"result": "v1"}` — one with a 36-character webhook node id, one with a 40-character id:

| Step | 36-character id | 40-character id |
| --- | --- | --- |
| Import + first publish, restart | Answers `v1` | Answers `v1`; log shows `value too long for type character varying(36)`; no row in `workflow_publication_trigger_status` |
| Edit to `v2`, publish again (REST `PATCH` + `activate`, HTTP 200 for both) | Answers `v2` | **Still answers `v1`**, although the API and `workflow_entity."activeVersionId"` show the new version |
| One minute later, and after a restart | `v2` | `v1` |

Three things make this bug nasty. First, **every signal the editor gives you says the publish worked** — HTTP 200, a published badge, a new active version id. Second, **the error only exists in the server logs**, as a Postgres error on an internal insert. Third, **the publish outbox retries the failed insert forever** — thousands of failures a day in the logs — so the instance keeps doing useless work while production stays frozen on the old version.

**How to confirm in one minute:** call your production webhook twice with a visible change between publishes (change a Set node's output from `v1` to `v2` and publish). If the response never changes while the editor insists the new version is live, you have a publish-path failure, not a caching problem. Then check the logs — the next step shows exactly what to look for.

## The root cause: a varchar(36) column meets a 54-character id

When you publish a workflow, n8n records each trigger node's status in a Postgres table called `workflow_publication_trigger_status`. Its `nodeId` column is `varchar(36)` — sized for a standard UUID, which is exactly 36 characters including hyphens.

Workflows created in the editor always get 36-character UUID node ids, which is why most people never hit this. But workflows created or imported through the public API or source control can carry longer ids — the reports show **37 to 54 characters**. When such a workflow publishes, the insert into `workflow_publication_trigger_status` fails:

```text
value too long for type character varying(36)
```

No row is written, so the running instance never learns about the new version's trigger — and the production webhook keeps serving whatever was registered last. The publish outbox treats this as a transient failure and retries it indefinitely, which is why the log fills with the same error and nothing ever recovers on its own. The editor never sees any of this: the REST call that saved the version succeeded, so as far as the UI is concerned, you published.

The one trap inside the trap: **shortening the node id alone does not free a workflow that is already stuck**. The reporter tried it — change the id to 36 characters, publish, restart — and the workflow still answered `v1` every time. The stuck outbox record has to be dealt with too, which is why the fix below has two halves. Skip the second half and you will conclude the fix "doesn't work" when it actually never got a chance to run.

## Step 1 - Prove it in the logs

Before changing anything, confirm the diagnosis — a two-minute check that saves you from rebuilding a workflow that was never broken.

Run this against your n8n container (replace `n8n` with your container name):

```bash
docker logs n8n --since 1h 2>&1 | grep -i "value too long"
```

You should see the Postgres error repeating — once per publish attempt, or far more often if the outbox retry loop is running. That line is the diagnosis: a publish insert is failing on column width, not on your workflow logic.

Then check whether the trigger was ever registered. Connect to Postgres and look at the publication status table:

```bash
docker exec -it <postgres-container> psql -U <db-user> -d <db-name> \
  -c "SELECT * FROM workflow_publication_trigger_status;"
```

You should see rows for your healthy workflows' triggers — and **no row at all for the stuck workflow's trigger node**. A missing row plus the `value too long` error in the logs is conclusive: this is the 36-character bug, not a webhook URL or activation problem.

> **Warning:** do not "fix" this by editing the column to a wider type by hand. A manual `ALTER TABLE` on n8n's internal schema will be overwritten or conflicted by the next migration, and it papers over the stuck outbox record instead of clearing it. Fix the data (Step 2), clear the stuck record (Step 3), then upgrade (Step 5).

## Step 2 - Shorten the trigger node id to 36 characters or fewer

Node ids are not editable in the n8n editor, so this step goes through the workflow JSON. The goal is a trigger node id of at most 36 characters — a standard UUID is the safest choice.

1. In the editor, open the stuck workflow, click the **⋮ menu → Download** to export the workflow JSON.
2. Open the JSON and find the trigger node (the Webhook node, in the reported case). Its `"id"` field is the long one — 37 to 54 characters.
3. Replace that id with a fresh 36-character UUID. Generate one with:
   ```bash
   python3 -c "import uuid; print(uuid.uuid4())"
   ```
   You should see output like `a1b2c3d4-e5f6-4a7b-8c9d-e0f1a2b3c4d5` — 36 characters including hyphens.
4. **Do not change anything else in the JSON.** In particular, leave the node's `webhookId` and `path` untouched — those are what determine your production webhook URL, and changing them would move the webhook to a new address.
5. Push the edited workflow back with the public API, which keeps the same workflow id (create an API key under **Settings → n8n API** first):
   ```bash
   curl -X PATCH "https://<your-n8n-host>/api/v1/workflows/<workflow-id>" \
     -H "X-N8N-API-KEY: <your-api-key>" \
     -H "Content-Type: application/json" \
     --data @workflow-fixed.json
   ```
   The `--data @workflow-fixed.json` flag sends the edited JSON file as the request body; `<workflow-id>` is the id from the URL of the workflow in the editor. You should get HTTP 200 with the updated workflow back.

Why the API instead of deleting and re-importing: the API update keeps the same workflow id, the same webhook registrations, and the same execution history. Re-importing as a new workflow also works, but it creates a new workflow id and you have to deactivate and delete the old one first to avoid two workflows fighting over the same webhook path.

## Step 3 - Clear the stuck publish-outbox record

This is the half everyone misses. The publish outbox already holds a failed record for this workflow, retrying the oversized insert forever. Until that record is failed or cleared, the next publish queues behind it and nothing changes — which is exactly what the issue reporter observed when shortening the id alone did not help.

How you clear it depends on your setup:

- **If you can upgrade (recommended):** skip straight to Step 5 — upgrading to a release containing PR #41007 widens the columns, and the retried insert then succeeds on its own. This is the cleanest path and the one the n8n team shipped.
- **If you must stay on the affected version:** find the stuck outbox row for this workflow in Postgres — your container logs show the failing insert and the table it targets — and mark that record failed so the retry loop stops. Then publish the workflow again from the editor. The new publish creates a fresh outbox record with the shortened node id, and the insert succeeds.

After clearing the record, publish once more from the editor and move to verification. If the webhook still answers the old version after a publish with a short id and a cleared outbox, re-check Step 1: either the id is still over 36 characters, or the outbox record was not actually the one that got cleared.

## Step 4 - Verify the new version is actually live

Do not trust the editor badge — that is what lied to you in the first place. Verify from outside, against the production URL:

1. Edit the Set node (or any visible output) to return a new marker value, for example `{"result": "v3"}`, and publish.
2. Call the production webhook:
   ```bash
   curl -X POST "https://<your-n8n-host>/webhook/<your-webhook-path>"
   ```
   You should see `{"result": "v3"}` in the response. If you see the old value, the publish still is not landing — go back to Step 1 and re-check the logs.
3. Confirm the log is quiet:
   ```bash
   docker logs n8n --since 5m 2>&1 | grep -ci "value too long"
   ```
   You should see `0`. The outbox retry loop has stopped, which means the insert is succeeding now.

## Step 5 - Upgrade so it can never happen again

The permanent fix is [PR #41007](https://github.com/n8n-io/n8n/pull/41007), merged October 13, 2026, which widens the node id columns from 36 to 64 characters. Upgrade to a release that includes it — check the release notes for "Widen node id columns to 64 characters" before upgrading, and test the upgrade on a staging copy first if production matters to you.

Two things worth knowing about the fix. First, 64 characters is the new ceiling, not infinity: n8n 3.0.0 (October 27, 2026) added a loud failure for stored versions with trigger node ids over 64 characters ([#41519](https://github.com/n8n-io/n8n/issues/41519)), so an over-long id now fails visibly at publish time instead of silently serving stale code. Second, the fix is forward-looking — it stops new workflows from getting stuck, but a workflow that is already stuck still needs Steps 2 and 3, because its failed outbox record does not clear itself.

## Prevent it next time: a 10-second check on every API import

This bug only bites workflows that arrive with non-standard node ids — imports via the public API, source-control sync, or any tooling that generates its own ids. Add one check to that pipeline: after exporting or receiving a workflow JSON, list any node id longer than 36 characters before you import it:

```bash
jq -r '.nodes[] | "\(.name): \(.id | length) chars"' workflow.json \
  | awk -F': ' '$2 ~ /^[0-9]+ chars$/ && $2 + 0 > 36'
```

The `jq` command prints each node's name and id length; the `awk` filter keeps only lines where the length exceeds 36. You should see no output at all. If a line appears, replace that node's id with a fresh UUID (Step 2) before importing. If your tooling generates node ids, make it generate standard UUIDs — that single rule makes this entire class of bug impossible.

## Key Takeaways

1. **A publish can report success while production serves the old version** — on Postgres-backed n8n, a trigger node id over 36 characters fails the internal `workflow_publication_trigger_status` insert with `value too long for type character varying(36)`, and the editor never shows it.
2. **The log is the only honest signal.** `docker logs n8n | grep "value too long"` plus a missing row in `workflow_publication_trigger_status` confirms the bug in under a minute.
3. **The fix has two halves:** shorten the trigger node id to 36 characters or fewer via a JSON edit + API update, *and* clear the stuck publish-outbox record — shortening the id alone does not free an already-stuck workflow.
4. **Upgrade to a release containing PR #41007** (node id columns widened to 64 characters); n8n 3.0.0 additionally fails loudly for ids over 64 characters instead of silently serving stale code.
5. **Guard your imports:** reject any workflow JSON with a node id longer than 36 characters before it reaches production, and generate standard UUIDs in any tooling that creates workflows.

Next: if your workflows are imported through automation, add the `jq` length check from the prevention section to that pipeline today — it takes ten seconds and this bug takes hours to notice. And if you hit a publish that *hangs* instead of silently succeeding, check the instance's publish path first: a restart clears a hung publish, which is a different failure from the one above.

## FAQ

### Does this affect n8n Cloud?

The reported cases are all self-hosted Postgres-backed instances, and the fix (PR #41007) applies to the self-hosted codebase. Cloud workspaces are managed by n8n and were patched on their side; if a Cloud workflow shows the same symptom — publish succeeds, production serves the old version — contact n8n support with the workflow id, because you cannot inspect the internal tables yourself.

### Does this affect SQLite instances?

No. SQLite does not enforce `varchar` length limits, so the 36-character column width is never a constraint there. The bug is specific to Postgres-backed instances, which is the default for Docker Compose production setups using the `withPostgres` stack.

### I shortened the id and republished, but production still serves the old version. What did I miss?

Almost certainly Step 3: the stuck publish-outbox record. Shortening the id fixes future publishes, but the failed outbox record from the first publish keeps retrying and blocking the queue. Clear or fail that record, then publish again — and verify with a `curl` against the production URL, not the editor badge.

### Can I just rename the node in the editor?

Renaming a node changes its display name, not its internal id — the id is what the database column measures. The id only changes through a JSON edit (Step 2), which is why the fix goes through the workflow file and the API.

### How do I know which n8n version contains the fix?

Look for "Widen node id columns to 64 characters" (PR #41007, merged October 13, 2026) in the release notes of the version you plan to install. n8n 3.0.0 (October 27, 2026) also added a loud publish failure for ids over 64 characters, so on 3.0.0+ this failure mode is at least visible instead of silent.
