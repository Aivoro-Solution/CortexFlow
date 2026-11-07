---
title: "Fix n8n Workflow Changes Not Taking Effect in Production (Draft vs Published Trap)"
description: "You fixed your n8n workflow, but production still runs the old version? The draft vs published trap in n8n 2.x — 5 verified fixes."
date: 2026-11-07
category: automation
tags: ["n8n", "error fix", "workflows", "publishing", "webhooks"]
draft: false
featured: false
image: "/og/fix-n8n-workflow-changes-not-taking-effect.webp"
---

You edited a workflow, tested it, watched every node turn green — and production kept running the old version. The form still misses the new field. The webhook still calls the old logic. The schedule still fires the version from last week. Nothing is broken, nothing errors, and your fix simply never went live.

This is the draft vs published trap, and in n8n 2.x it is the single most common reason a "fix" doesn't fix anything. Since n8n 2.0 (December 2025), the old Active toggle is gone: your edits save automatically as a draft, and nothing goes live until you click **Publish**. Production always runs the last *published* version — never your latest edits. By the end of this guide you will know how to tell which version is actually live, the five ways a change fails to reach production, and the checks that prove your fix is the one running. All fixes below are verified against community reports and n8n documentation, as of November 2026.

**Prerequisites:** an n8n instance on version 2.x (self-hosted or Cloud), a workflow with a real trigger (Schedule, Webhook, or an app trigger), and access to the Executions tab. If you self-host with Docker, you will also need shell access to the container for Fix 4.

## The symptom map — which version problem do you have?

| Symptom | When it happens | Root cause |
|---|---|---|
| `Workflow is not active and cannot be executed` | A schedule, webhook, or parent workflow tries to run it | The workflow was never published, or a sub-workflow it calls was never published |
| Your fix works in the editor, production runs the old logic | You edited a published workflow and only saved | Saving updates the draft; production keeps the last published version until you re-publish |
| Webhook works in testing, then goes silent | The caller still uses the test URL | The test URL (`/webhook-test/`) only listens for 120 seconds after you click Listen for test event; production needs the `/webhook/` URL |
| Production runs the old version even after you clicked Publish | Queue mode (`EXECUTIONS_MODE=queue`) | In-memory cached workflow state on main/workers, or jobs already enqueued in Redis carrying the old version payload |
| Error workflow never fires on a failed production run | The error workflow was never published | Since 2.x, n8n runs the *published* version of the error workflow; an unpublished one cannot start |

## Fix 1 — Publish the workflow: Save is not Publish

This is the fix for most cases, and it is embarrassingly small — which is exactly why it keeps happening.

In n8n 2.x there are three different actions that sound alike, and mixing them up is the root of the problem:

| Action | What it does | When to use it |
|---|---|---|
| **Save** | Stores your edits as a draft. The live workflow keeps its last published version. | You want to keep a change without making it live yet. |
| **Execute workflow** | Runs the draft once, right now, in the editor. Webhooks answer on the test URL only. | You are building and testing. |
| **Publish** | Hands the workflow to its trigger. Webhooks answer on the Production URL, schedules start firing. | A full test has passed and the change should go live. |

n8n saves automatically within 1 to 5 seconds of an edit, so the **Saved** label in the top-right means your draft is stored — not that it is live. The status to watch is the badge next to it: **"Published, has changes"** means the workflow is running, but not the version you just fixed. The **Publish** button lights up again whenever your saved version differs from the live one.

**Step 1 — Click Publish (or press `Shift + P`).** Do it after every edit to a live workflow, before you close the tab. Publishing locks the workflow to a specific version, and production runs that version — not your latest draft edits.

**Step 2 — Confirm the badge clears.** After publishing, the status should read **Published** with no "has changes" qualifier. If the button is still lit, your click did not land — check for a validation error on the canvas.

> **Note:** If **Publish is greyed out**, the workflow either has no unpublished changes (nothing to push) or has no trigger that requires publishing. A workflow that still starts with a Manual Trigger will never run on its own — it needs a Schedule, Webhook, or app trigger before n8n will let you publish it. Add a real trigger, then publish.

**You should see:** the next production run — a schedule firing, a webhook call, an app event — executes the version you just edited. Check the Executions tab: the run's input data should include your new field or logic.

## Fix 2 — Point the caller at the Production URL, not the test URL

Publishing alone does not fix a webhook that goes quiet, because every Webhook node has two addresses and they behave differently:

- The **test URL** (it has `/webhook-test/` in it) only listens for 120 seconds after you click **Listen for test event** in the editor. It exists so you can see the incoming data on the canvas.
- The **Production URL** (it has `/webhook/` in it) only answers once the workflow is published, and its runs appear in the Executions tab rather than on the canvas.

The classic failure is a form, a Shopify webhook, or a third-party app that was pointed at the test URL during setup and never switched. It worked during testing and then went silent — because the test listener expired, not because anything broke.

**Step 1 — Publish the workflow** (Fix 1).

**Step 2 — Open the Webhook node, switch to Production URL, and copy the address with `/webhook/` in it** into the calling app, form, or service. Replace the `/webhook-test/` address everywhere it was pasted — including any stored copy in the external service's settings, not just the one you remember.

**Step 3 — Send a real request to the Production URL** and check the Executions tab for a production run. A green canvas after a manual run proves nothing about this path: manual runs never use the Production URL.

> **Warning:** If n8n hands out webhook URLs starting with `http://localhost:5678`, nothing outside your server can reach them. n8n builds webhook addresses from `N8N_HOST`, which defaults to localhost. Behind a reverse proxy, set `N8N_WEBHOOK_URL` to your public `https` address (and `N8N_PROXY_HOPS` to `1`) and recreate the container. `WEBHOOK_URL` is the old name — deprecated from version 2.35, though it still works with a warning.

## Fix 3 — Republish every sub-workflow and the error workflow too

A parent workflow that calls a sub-workflow does not call "the latest code" — it calls the specific published version stored in the database on that instance. If the sub-workflow was edited but never re-published, the parent keeps executing the old stored definition, even while running the sub-workflow directly in the editor works fine (because that runs the draft).

The same rule applies to error workflows. In n8n 1.x, an error workflow did not need to be published. Since 2.x split workflows into drafts and published versions, n8n runs the published version of the error workflow. If it was never published, failing workflows cannot start it, the server log shows `... is not active and cannot be executed`, and you get no alert at all. Newer releases catch this earlier: when you assign the error workflow, the save is rejected with `The selected error workflow has no published version.`

**Step 1 — Open each sub-workflow** called by an Execute Workflow node (or an Execute Sub-workflow node) and check its status badge. Publish any that show "has changes".

**Step 2 — Open the error workflow** assigned under the workflow's Settings → Error Workflow and publish it too — then republish it again after any later edit. Saving alone leaves the old published version running.

**Step 3 — Re-run the parent workflow in production** and confirm the sub-workflow's new logic executes. If you upgraded to 2.0 and an Execute Workflow Trigger node suddenly errors, the sub-workflow being called now has to be published — it did not in 1.x.

## Fix 4 — Prove which version is actually live (and force it with the CLI)

When you have published and production still runs old logic, stop guessing and export what n8n actually has stored as the published version. If that export is the old flow, the published pointer never moved.

**Step 1 — Check Version History in the editor.** It shows which version is currently published and lets you roll back or re-publish a specific version. If the published version is not the one you expect, re-publish from here.

**Step 2 — Export the published version from the CLI** (self-hosted Docker). This reads the database directly, so it settles whether the publish landed at all:

```bash
docker exec -u node -it <your-n8n-container-name> n8n export:workflow --id=<WORKFLOW_ID> --published --output=/tmp/published.json
```

Replace `<your-n8n-container-name>` with your container name and `<WORKFLOW_ID>` with the workflow's ID from its URL. Open `/tmp/published.json` and compare it against your editor — look for the node or field you changed. If the file is the old flow, the publish never landed.

**Step 3 — Publish the current draft by ID** if the export proves the pointer is stale:

```bash
docker exec -u node -it <your-n8n-container-name> n8n publish:workflow --id=<WORKFLOW_ID>
```

Both commands act on the database directly, so the change applies on the next n8n start. Restart the instance, then re-run the export to confirm the published version now matches your draft.

## Fix 5 — Queue mode: restart main and workers after publishing

If you self-host with `EXECUTIONS_MODE=queue`, there is one more layer between Publish and production: cached workflow state.

Jobs already enqueued in Redis before you hit Publish finish executing using the version payload present when the trigger fired — they do not pick up the new version mid-flight. And in some cases the main instance and workers hold an in-memory cached copy of the workflow that survives the publish.

**Step 1 — Publish, then restart the main n8n instance and all worker processes** to clear the in-memory cached workflow states. A restart is the reliable way to force every process to reload the published version from the database.

**Step 2 — Wait for in-flight jobs to drain.** Executions that started before the publish will still finish on the old version. Do not judge the fix until a run that *started* after the restart has completed.

**Step 3 — Re-check with the Fix 4 export.** If the published export matches your draft and a post-restart run still shows old behaviour, the problem is no longer versioning — check pinned data (data you pinned while testing is ignored in live runs, so a workflow that only worked because of pinned data behaves differently once published) and the Production URL (Fix 2).

## Prevent it next time

- **The one-glance rule:** after any edit to a live workflow, glance at the Publish button before you close the tab. If it is lit, your change is not live.
- **Publish sweep:** whenever you change a workflow, open every workflow it calls — sub-workflows and the error workflow — verify the status badge, and publish anything with pending changes. A community-reported "publish sweep" routine (open → verify indicator → publish if yellow) is the cheapest defence against version drift across dependent workflows.
- **Version History as the source of truth:** when production behaviour surprises you, check Version History before debugging nodes. If the published version is not the version you think it is, no amount of node debugging will help.
- **Test the production path, not just the canvas:** after publishing, trigger the workflow the way production does — real webhook call to the Production URL, real schedule tick, real app event — and confirm the run in the Executions tab. A manual Execute workflow run bypasses every part of this trap by design.

## FAQ

### Why does my n8n workflow work when I click Execute but never run on its own?

Since n8n 2.0, edits save as drafts and only go live when you publish, so check for "Published, has changes". The workflow also needs a real trigger, not a Manual Trigger — a Manual Trigger only runs when you click it.

### Why does my webhook work in test but not in production?

The test URL (`/webhook-test/`) only listens for 120 seconds after you click Listen for test event. The Production URL (`/webhook/`) only works while the workflow is published, and its runs show up in the Executions tab, not on the canvas. Make sure the calling app uses the Production URL.

### I published, but executions still run the old version. What now?

First, export the published version with `n8n export:workflow --id=<WORKFLOW_ID> --published` and compare it to your draft. If it is stale, publish by ID with `n8n publish:workflow --id=<WORKFLOW_ID>`. In queue mode, restart the main instance and workers, and let jobs enqueued before the publish drain — they finish on the old version payload.

### Do sub-workflows need publishing too?

Yes. A parent workflow calls the published version stored in the database, not your latest draft. The same applies to error workflows: since 2.x, an unpublished error workflow cannot start, and newer releases reject assigning one with `The selected error workflow has no published version.`

### Does changing only a workflow's settings require publishing?

No — according to the n8n documentation, when you change only settings on a published workflow, n8n republishes it for you. Node and connection changes still need an explicit Publish.

## Key Takeaways

1. **Save is not Publish.** In n8n 2.x, edits autosave as drafts; production always runs the last published version. "Published, has changes" means your fix is not live yet.
2. **Webhooks have two URLs.** The test URL dies 120 seconds after Listen for test event; production needs the `/webhook/` URL on a published workflow.
3. **Sub-workflows and error workflows need publishing too** — a parent calls the stored published version, and an unpublished error workflow silently never fires.
4. **Verify, don't assume.** Version History and `n8n export:workflow --published` show which version is actually live; in queue mode, restart main and workers and let pre-publish jobs drain.
5. **Test the production path.** A manual Execute run bypasses this entire trap by design — only a real trigger through the Production URL proves the fix is live.

Next: if your workflows run but silently stop with no error at all, read [Fix n8n Microsoft Teams Trigger Stopping After a Few Days](/blog/fix-n8n-teams-trigger-silent-stop/) for the silent-expiry pattern, and [Fix n8n WhatsApp Trigger Not Firing in Production](/blog/fix-n8n-whatsapp-trigger-production-webhook/) for the full test-vs-production webhook checklist.

*Sources: [n8n community — "In n8n Version 2.1.4 the active workflow button doesn't exist?"](https://community.n8n.io/t/in-n8n-version-2-1-4-the-active-workflow-button-doesnt-exist/243790) · [n8n community — "Change from Save/Activate to Publish for workflows"](https://community.n8n.io/t/change-from-save-activate-to-publish-for-workflows/258417) · [n8n community — "N8n versioning is not maintaining"](https://community.n8n.io/t/n8n-versioning-is-not-maintaining/305971) · [n8n community — "HELP: Workflow running older version of subworkflow"](https://community.n8n.io/t/help-workflow-running-older-version-of-subworkflow/258245) · [n8n docs — Save and publish workflows](https://docs.n8n.io/workflows/save-publish/)*
