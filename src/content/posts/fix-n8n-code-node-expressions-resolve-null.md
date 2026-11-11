---
title: "Fix n8n $('Code') Expressions Resolving to null After Upgrading to 1.123.x"
description: "After upgrading to n8n 1.123.85, $('Code') expressions silently resolve to null while executions report success. Two team-confirmed fixes."
date: 2026-11-11
category: automation
tags: ["n8n", "code-node", "expressions", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-code-node-expressions-resolve-null.webp"
---

You upgrade n8n from 1.121.3 to 1.123.85, change nothing in your workflows, and the next morning your Google Drive folders are being created as "Untitled" in the Drive root. Your Gmail node crashes. Your Postgres queries fail. Every execution still reports **success**. Nothing in the editor looks wrong — the expression preview even shows the correct value.

The cause is a confirmed regression in n8n 1.123.x: any expression in a node parameter that reads a Code node's output through `$('Code')` silently resolves to `null` at execution time — but only when task runners are disabled, which is the default for a plain Docker install. By the end of this article you will know how to prove you have this bug in two minutes, fix it with one environment variable, and add a guard so a silent `null` can never again write your users' files into the wrong folder.

Quick definitions before we start: a **Code node** is n8n's JavaScript node — it takes items in and returns items out, and builders use it to shape data between steps. A **named reference** like `$('Code').first().json.value` is an expression that reaches back to a specific earlier node by name and reads a field from its output, instead of reading the current node's own input (`$json`). **Task runners** are the separate processes n8n uses to execute Code nodes in isolation (enabled with `N8N_RUNNERS_ENABLED=true`); with them off, Code nodes run inside the main n8n process. The **expression engine** is the component that evaluates `{{ ... }}` expressions in node parameters — 1.123.x evaluates them inside a sandboxed VM "isolate", which is where this bug lives.

This is a verified bug, not a configuration mistake: [GitHub issue #41588](https://github.com/n8n-io/n8n/issues/41588) (filed October 20, 2026, n8n 1.123.85 on Docker with SQLite, task runners disabled) reproduces it in a clean container with a five-expression test workflow, and the n8n team has confirmed two workarounds in the thread. A duplicate report, [#41920](https://github.com/n8n-io/n8n/issues/41920) ("After Upgrade To 1.123.87: No named reference is working anymore!"), was merged into it on October 23, confirming the bug is still present in 1.123.87. As of November 11, 2026, the issue is open in the team's tracker (Linear GHC-9617) with no fixed release yet — so the workarounds below are the fix for now.

**Prerequisites:** a self-hosted n8n instance on the 1.123.x line (the report covers 1.123.85 and 1.123.87), access to your `docker-compose.yml` or `docker run` command, and a workflow that reads a Code node's output with a `$('...')` expression in a node parameter.

> **Note:** this article is about expressions that resolve to `null` *silently* — no error, execution status "success". If your expression throws "Cannot resolve paired item" or "Can't determine which item to use", that is a different failure — the item-linking chain breaking — covered in [Fix n8n "Cannot Resolve Paired Item" / "Can't Determine Which Item to Use" Error](/blog/fix-n8n-cannot-resolve-paired-item/). If your loop ends early with status "success" and items missing, that is the Split In Batches variant, covered in [Fix n8n SplitInBatches Loop Ending Early](/blog/fix-n8n-splitinbatches-loop-ends-early/).

## The symptom: correct in the editor, null at runtime

The reporter's reproduction is the clearest way to see it. A Code node returns one item, `{ "value": "from_code" }`, and a Set node reads it back five different ways:

| Expression | Referenced node | 1.123.85, runners disabled | 1.123.85, `N8N_RUNNERS_ENABLED=true` |
| --- | --- | --- | --- |
| `$('Code').first().json.value` | Code | `null` | `from_code` |
| `$('Code').item.json.value` | Code | `null` | `from_code` |
| `$node['Code'].json.value` (legacy syntax) | Code | `from_code` | `from_code` |
| `$('Edit Fields').first().json.value_set` | Set | `from_set` | `from_set` |
| `$json.value` (direct input from the Code node) | Code | `from_code` | `from_code` |

Three things make this bug nasty. First, **only Code-node references are affected**: the same `$('...')` syntax works fine against Webhook, Postgres, and Set nodes, and even `JSON.stringify($('Code').first())` returns `null` while the identical expression inside another Code node returns the correct value. Second, **the editor lies to you**: the parameter preview shows the correct value, and the `null` only appears at execution time — manual, webhook, and schedule executions are all affected. Third, **most nodes raise no error**, so the execution finishes as "success" and the wrong data flows downstream silently.

The production damage in the report is concrete, and it is the reason this bug deserves a same-day fix rather than a "we'll look at it" ticket:

- **Google Drive → Folder → Create**, with the folder name and parent folder taken from a Code node, created a folder named **"Untitled" in the Drive root** — no error. Uploads with a `folderId` from a Code node also went to the root, and those files contained personal data.
- **Google Drive → File → Move** with a `folderId` from a Code node left the file in the root, again with no error.
- **Postgres → Execute Query** with `queryReplacement` set to `{{ [$("Code").item.json.x] }}` failed with "Query Parameters must be a string of comma-separated values or an array of values".
- **Gmail → Send** with `sendTo` set to `{{ $('Code').item.json.email }}` crashed with "Cannot read properties of undefined (reading 'split')".
- **Odoo** filters and **IF** conditions fed from a Code node got empty values and produced silently wrong results.

The regression evidence is airtight: the same production workflow, with identical node parameters, worked on 1.121.3. An execution on October 14 created a Google Drive folder with the name and parent taken from `$('Configuración').first().json…` correctly. After the upgrade to 1.123.85, the first two executions created "Untitled" folders in the Drive root.

## The root cause: the expression isolate cannot see the in-process Code output

The reporter's hypothesis — not yet verified in source, but consistent with every observation — is that the output of the legacy in-process Code sandbox cannot be transferred into the expression isolate, and the resulting internal error is swallowed and becomes `null` instead of an error. Two related reports support that reading: [issue #35559](https://github.com/n8n-io/n8n/issues/35559) (expressions silently resolving to `null` because an internal error is swallowed while rendering the expression) and [issue #41322](https://github.com/n8n-io/n8n/issues/41322) (the expression VM isolate behind the webhook-latency regression), plus the 1.123.63 release note "Preserve Date values passed to the expression isolate", which shows the isolate boundary was being actively reworked in exactly this version range.

That also explains the pattern in the table: the legacy `$node['Code']` syntax and `$json` take different evaluation paths that never cross the isolate boundary, references to non-Code nodes never involve the Code sandbox at all, and expressions *inside* another Code node evaluate in the Code runtime itself. Only the combination — a node parameter, evaluated in the isolate, reaching back to a Code node that ran in-process — hits the broken handoff. Enabling task runners moves Code execution out of the main process into the runner, and the handoff works again.

**The one-sentence version: after the 1.123.x upgrade, a node parameter that reaches back to a Code node with `$('Code')` gets `null` instead of the value — but only when task runners are off, and nothing tells you it happened.**

## Step 1 - Prove it is this bug (2 minutes)

Before changing environment variables, confirm the diagnosis — because a `null` in a node parameter can also come from a genuinely empty upstream value, and the fix for that is different.

1. Open a failed or wrong execution and find a node that received a `null` where you expected a value. Check the expression in that node's parameter: if it reads a Code node through `$('Code').first()` or `$('Code').item`, you are in the suspect set.
2. Add a temporary Set node after the Code node with two assignments: `A_code_first` = `={{ $('Code').first().json.value }}` and `B_direct` = `={{ $json.value }}`. Execute the workflow manually.
3. If `A_code_first` is `null` while `B_direct` holds the correct value, and the editor's preview for `A_code_first` showed the correct value before you ran it, you have this bug.
4. Confirm the version: check **Settings → About** (or run `docker exec <container> n8n --version`). The regression was reported on **1.123.85** and confirmed still present in **1.123.87**.

If both assignments are `null`, your Code node is genuinely returning nothing — check its output first, not the expression engine. If `A_code_first` is correct, you do not have this bug; look at the node that produced the wrong value instead.

## Step 2 - Fix it by enabling task runners (recommended)

This is the workaround the n8n team confirmed in the issue thread, and the one the reporter is running in production. It enables the task-runner mode that moves Code execution out of the main process, which restores the `$('Code')` handoff.

Add one environment variable to your n8n service and restart:

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:1.123.85
    environment:
      - N8N_RUNNERS_ENABLED=true
```

Here is what that key does: `N8N_RUNNERS_ENABLED=true` starts n8n's task-runner broker and runs Code nodes (and other task-runner-backed nodes) in separate runner processes instead of inside the main process. With no `N8N_RUNNERS_MODE` set, it uses **internal mode** — no extra container is needed, the runners live inside the same container. (External mode, with a separate `n8nio/runners` container, is a different setup; you do not need it for this fix.)

Then restart and verify:

```bash
docker compose down && docker compose up -d
```

You should see the container come back up, and the task-runner broker listening on its internal port in the startup logs. Re-run the Set node from Step 1: `A_code_first` should now read `from_code` (or your real value), matching `B_direct`.

> **Warning:** task runners change Code-node resource isolation, so watch memory after enabling them on a tight container. The reporter noted this explicitly in the thread: on a small VPS, give the container headroom (the n8n docs suggest at least 1 GB for the main process plus runner overhead) and check `docker stats` after the first few executions. If you run queue mode, set the variable on the main instance and the workers — the Code node runs wherever the execution runs.

## Step 3 - Fall back to the legacy expression engine (if runners are not an option)

If you cannot enable task runners — for example, your deployment pins a runner configuration you cannot change right now — the team confirmed a second workaround in the thread: fall back to the legacy expression engine.

```yaml
services:
  n8n:
    environment:
      - N8N_EXPRESSION_ENGINE=legacy
```

Here is what that key does: `N8N_EXPRESSION_ENGINE=legacy` tells n8n to evaluate `{{ ... }}` expressions with the pre-isolate engine, the one that ran before 1.123.x. The `$('Code')` reference resolves through the old path and returns the correct value.

Treat this as a bridge, not a destination. The legacy engine is the old evaluation path, and the long-term fix is either the runner-based setup from Step 2 or the upstream patch the team is working on (Linear GHC-9617). Use it to stop the bleeding today, then plan the move to task runners — and check the issue thread for a fixed release before your next upgrade.

Do not set both workarounds at once and call it belt-and-braces: pick one, verify it with Step 4, and keep the other in your back pocket. Two changed variables make the next debugging session harder, not easier.

## Step 4 - Verify the fix end to end

One passing Set node is not enough — the damage this bug does is silent, so verify the places it actually hurt.

1. Re-run the Step 1 test: `A_code_first` and `B_direct` should now agree.
2. Re-run the production workflow that created the "Untitled" folder. Check in Google Drive that the folder is created with the correct name under the correct parent — not in the root. If your workflow already created stray "Untitled" folders, move or delete them now; the fix does not clean up the wrong data the bug already wrote.
3. Check the nodes that crashed: Gmail `sendTo` should resolve to a real address, and the Postgres `queryReplacement` should no longer throw the comma-separated-values error.
4. Open the execution and confirm the status is "success" *with correct output values* — remember, "success" was also the status while the bug was active, so status alone proves nothing. Read the actual output items.

## Step 5 - Prevent it next time

This bug's real lesson is not about one environment variable. It is that an upgrade can change the *meaning* of a working expression without changing its *appearance*, and the execution status will not save you. Three habits close that gap:

- **Pin your image tag and test upgrades on a copy first.** Never run `:latest` in production. When a new 1.123.x (or any) tag lands, spin up a staging copy with the same workflows, run the Step 1 test, and only then promote the tag. The reporter caught this in production; a staging run would have caught it in five minutes.
- **Add a canary workflow that runs after every upgrade.** A three-node workflow — Manual Trigger → Code node returning `{ "value": "from_code" }` → Set node with `$('Code').first().json.value` — plus an IF node that fails loudly if the value is `null`. Run it once after every deploy. If it ever goes red, you know within a minute instead of discovering "Untitled" folders the next morning.
- **Guard the fields that can hurt you.** Wherever a `null` would silently write data to the wrong place — a Drive `folderId`, a Gmail `sendTo`, a Postgres parameter — add an IF node before the action that checks the field is not empty, and route the empty branch to a Slack/email alert (or an Error Trigger workflow). A loud failure on one execution beats a week of silently misplaced files.

## Limits and what I did not test

The fix status is the honest limit here. As of November 11, 2026, issue #41588 is open with no fixed release named, and the duplicate #41920 only confirms the bug persists through 1.123.87. If a later 1.123.x patch or a 2.x/3.x release fixes it, upgrade to that release and remove the workaround — check the issue thread, not this article, for the fixed version. I also did not test the external task-runner mode (`N8N_RUNNERS_MODE=external` with a separate `n8nio/runners` container); the internal mode from Step 2 is what the reporter verified, and it is the simpler change. Finally, the isolate-handoff explanation is the reporter's hypothesis, consistent with the evidence but not verified in source — the two workarounds are team-confirmed regardless of the exact mechanism.

## Key Takeaways

1. **After upgrading to n8n 1.123.85 (or 1.123.87), `$('Code')` expressions in node parameters silently resolve to `null` when task runners are disabled** — and executions still report "success".
2. **The editor preview shows the correct value; only execution-time is `null`.** That mismatch is the fastest way to identify this bug.
3. **Fix it with `N8N_RUNNERS_ENABLED=true`** (internal mode, one env var, restart) — team-confirmed in the issue thread.
4. **If runners are not an option, fall back with `N8N_EXPRESSION_ENGINE=legacy`** — a bridge, not a destination.
5. **A `null` from a Code reference can write real data to the wrong place** — "Untitled" Drive folders, files in the root, crashed Gmail sends — so verify output values, not just execution status, after every upgrade.

Next: add the three-node canary workflow from Step 5 to your instance today, before the next upgrade — it takes five minutes and it is the difference between catching the next silent regression in a minute and discovering it in a customer's Drive folder.

## FAQ

### Does this bug affect n8n Cloud?

The report is against self-hosted 1.123.x (Docker, SQLite, task runners disabled). Cloud instances run the 2.x line with task runners on, so this specific regression does not apply there — but the diagnostic pattern (editor preview correct, execution-time `null`, status "success") is worth knowing on any setup.

### Why does `$json` still work but `$('Code')` does not?

`$json` reads the current node's own input item, which never leaves the execution's item flow. `$('Code')` reaches back to a *different* node's output, and in 1.123.x that cross-node read passes through the expression isolate — the handoff that breaks when the Code node ran in-process. The legacy `$node['Code']` syntax takes a different evaluation path and is unaffected, which is why it still works.

### Will upgrading to the next 1.123.x patch fix it?

Unknown as of November 11, 2026. The duplicate #41920 confirms the bug in 1.123.87, and no fixed release has been named in the issue. Apply one of the two workarounds now, and check [issue #41588](https://github.com/n8n-io/n8n/issues/41588) for the fixed version before your next upgrade.

### Is `N8N_EXPRESSION_ENGINE=legacy` safe to leave on?

It restores the pre-1.123.x evaluation path, so it fixes this bug — but it is a stopgap. The legacy engine is the old path, and the durable setup is task runners enabled (Step 2) or the upstream patch. If you use the legacy fallback, note it in your deployment docs with a reminder to re-check the issue after your next upgrade.
