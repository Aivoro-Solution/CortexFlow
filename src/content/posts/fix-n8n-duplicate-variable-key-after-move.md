---
title: "Fix n8n Duplicate Variable Keys After Moving a Variable to Another Project"
description: "Moving an n8n variable into a project that already has the same key silently creates a duplicate — and $vars then returns whichever value comes back first."
date: 2026-11-23
category: automation
tags: ["n8n", "error-fix", "variables", "projects", "$vars"]
draft: false
featured: false
image: "/og/fix-n8n-duplicate-variable-key-after-move.webp"
---

You move a variable called `SHARED_KEY` from project A to project B. The request succeeds, no error anywhere. But project B already had its own `SHARED_KEY` — and now it has two. From that moment on, every workflow in project B that reads `{{ $vars.SHARED_KEY }}` gets whichever value the database happens to return last: `1` or `2`, depending on row and cache ordering, not on anything you configured. The workflow runs green either way, so nothing tells you the value flipped.

This is [GitHub issue #44774](https://github.com/n8n-io/n8n/issues/44774) (opened 2026-11-22, Linear GHC-9833, team-assigned, still open as of 2026-11-22), against n8n 2.49.0 and current master. A team member verified the root cause in the service code the same day. There is no merged fix yet — so the fix below is what you do today, plus what to watch for.

## The symptom: the same key twice in one project, and $vars flips a coin

The setup needs the variables feature (a licensed feature — Pro/Enterprise or n8n Cloud). Two projects each hold a variable with the same key, which is perfectly legal because keys only have to be unique *within* a project:

- Project A: `SHARED_KEY` = `1`
- Project B: `SHARED_KEY` = `2`

Now move the project A variable into project B, sending only the destination project — for example with the editor's internal endpoint:

```bash
curl -X PATCH "https://<your-n8n-host>/variables/<id-of-project-A-variable>" \
  -H "Content-Type: application/json" \
  -d '{"projectId": "<project B id>"}'
```

The request succeeds. Project B now lists `SHARED_KEY` twice — once with value `1`, once with value `2`. Run a workflow in project B that reads `{{ $vars.SHARED_KEY }}` and the result depends on row order, not on your configuration. Change nothing, re-run later, and the value can change: the `$vars` resolver lets the later row overwrite the earlier one, so whichever row the database or cache returns last wins.

There is no error at any point. Creating a variable with a duplicate key is rejected, and renaming a variable into a taken key is rejected — the move is the only path that reaches this state.

## The root cause: the move path skips the uniqueness check

The duplicate check lives in the variables service, `variables.service.ee.ts`. The `update()` method computes the destination project, but it only calls `validateUniqueVariable()` inside `if (variable.key)` — that is, only when the request actually changes the `key` field. A move request that only sends `projectId` never enters that branch, so the duplicate check never runs.

Two more things make the bug possible:

- Neither the database nor the entity model enforces uniqueness on `(key, project)`, so nothing below the service catches the duplicate either.
- The create path and the rename path *do* validate, which is why this only happens on a move — and why it is so easy to assume the move is safe.

Team member goutham-valugula confirmed this in the issue on 2026-11-22: the check needs to use the *effective* key — `variable.key ?? existingVariable.key` — whenever the key or the scope changes, while excluding the current variable's own ID. That is the fix the team needs to ship; until a release contains it, the check is yours to do by hand.

## Step 1: find out whether you already have duplicates

Open the Variables page in the editor and look at each project's list for a repeated key. If you manage variables through the API, list them per project instead:

```bash
curl "https://<your-n8n-host>/api/v1/variables?projectId=<project B id>" \
  -H "X-N8N-API-KEY: <your-api-key>"
```

Scan the response for the same `key` appearing twice in one project. Do this for every project you have ever moved a variable into — the duplicate only exists in the project a variable was moved *to*.

If you find a duplicate, note both variable IDs and both values before touching anything. One of them is the value your workflows should be reading; the other is the intruder.

## Step 2: remove the duplicate

Pick the value that is correct for that project, then eliminate the other copy. You have two options, and both go through paths that *do* validate:

**Rename one of the duplicates.** A rename triggers the uniqueness check, so it cannot silently create a second collision. Give the intruder a distinct key — for example `SHARED_KEY_OLD` — from the Variables page, or with the public API (a full replace, so send both fields):

```bash
curl -X PUT "https://<your-n8n-host>/api/v1/variables/<id-of-duplicate>" \
  -H "X-N8N-API-KEY: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"key": "SHARED_KEY_OLD", "value": "1"}'
```

**Or delete the duplicate outright**, from the Variables page or with:

```bash
curl -X DELETE "https://<your-n8n-host>/api/v1/variables/<id-of-duplicate>" \
  -H "X-N8N-API-KEY: <your-api-key>"
```

Delete only when you are sure the remaining copy holds the value your workflows need. If you are not sure which value is correct, rename instead of deleting — a renamed variable is recoverable, a deleted one is not.

## Step 3: verify $vars reads the right value

After the cleanup, list the project's variables again and confirm the key appears exactly once. Then run a workflow in that project that outputs `{{ $vars.SHARED_KEY }}` (an Edit Fields node that copies it into the output is enough) and check the value matches the one you kept. Run it twice: the bug's signature is a value that depends on ordering, so a single green run is not proof.

If workflows were already running against the duplicated key, audit their recent executions too — any run that read the wrong value may have written the wrong data downstream (wrong API base URL, wrong spreadsheet ID, wrong model name). Re-run the affected executions once the key is unique again.

## Prevent it next time: check the destination before you move

Until a release ships the fix for GHC-9833, treat every variable move as a manual uniqueness check:

1. **Before moving**, list the destination project's variables and confirm the key does not already exist there.
2. **If you are moving and renaming at the same time**, send the new `key` in the same request — the rename path validates, so a collision is rejected with an error instead of silently succeeding.
3. **After moving**, list the destination project's variables once more and confirm the key appears exactly once.

The expected behavior once the fix lands: the move is rejected with the same error the create and rename paths already produce — `A variable with key "SHARED_KEY" already exists in the specified project` (and the equivalent message when moving to global scope). When that error starts appearing on a move, the bug is fixed in your version; until then, the pre-move check is the fix.

## FAQ

### Does this affect global variables too?

Yes — the same gap applies when moving a variable into global scope. The expected fix message covers that case ("the equivalent message when moving to global"), and the same pre-move check applies: confirm the key does not already exist in the global scope before moving.

### Why did creating the second variable not fail?

Because the two variables were created in *different* projects, where the same key is allowed. The duplicate only appears when one is moved into the other's project — and the move path is the one path that skips validation.

### Can I fix this from the workflow side instead?

No — not reliably. `$vars` resolution happens before your workflow logic runs, and the value you get depends on row order. A Code node cannot tell which of two same-key rows it received. Fix the data (one key, one value per project); do not try to work around it in expressions.

### Which n8n versions are affected?

Reported against n8n 2.49.0 and current master (75fe21cb, still present on bf31087b) as of 2026-11-22. The gap is in the service logic, not in any particular database or hosting setup, so it affects all platforms running an unpatched version.

## Conclusion

Moving an n8n variable into a project that already has the same key silently creates a duplicate, because the move path skips the uniqueness check that the create and rename paths both run. From then on `$vars` returns whichever duplicate the database hands back last — a silent wrong value with green executions. Check the destination project before every move, clean up any duplicates by renaming or deleting one copy, and verify `$vars` reads the intended value. Watch for a release containing the fix for GHC-9833; until then, the pre-move check is the fix.
