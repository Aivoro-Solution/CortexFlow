---
title: "Fix n8n Source Control Pull Deleting a Variable Moved Between Team Projects"
description: "An n8n source control pull can silently delete a project variable that was moved from one team project to another upstream. Snapshot, restore, and prevent it."
date: 2026-11-24
category: automation
tags: ["n8n", "error-fix", "source-control", "variables", "environments"]
draft: false
featured: false
image: "/og/fix-n8n-source-control-pull-deletes-moved-variable.webp"
---

You move a variable from one team project to another, commit, and pull the change into your n8n instance. The pull reports success — and the variable is gone. Not blanked, not misplaced: deleted, along with the instance-local value it held. No error, no warning, and no failed execution to point at. The cause is a bug in n8n's source control import: when a pull imports several team project files at once, the prune step works from a stale snapshot taken before the loop starts, so a variable that moved projects upstream gets deleted no matter which order the files are processed in. By the end of this post you will know exactly when a pull deletes a moved variable, how to bring it back, and the pre-pull check that stops it happening again.

## The symptom: a variable disappears after a pull that moved it

The setup is a normal multi-environment n8n install using Source Control & Environments (Business and Enterprise plans). Team project A holds a project variable:

```text
Project A → Variables: VAR1 = "https://api.example.com/v2"
```

Upstream, someone moves that variable to team project B. In the Git repository, the `projects/` files record the move: `A.json` no longer contains a stub for `VAR1`, and `B.json` now owns it. You pull both project files in one pull.

After the pull, check the Variables page on the receiving instance:

```text
Project A → Variables: (VAR1 not listed)
Project B → Variables: VAR1 = "" (or not listed at all)
```

The variable is either gone entirely or recreated under project B with an empty value. Either way, the instance-local value — the real API URL, token, or database name — is lost. Any workflow reading `$vars.VAR1` now gets an empty string or fails to resolve, and because an empty string is a valid value, nothing throws. The workflows keep running with wrong data until someone notices the downstream damage.

This was reported in [GitHub issue #44758](https://github.com/n8n-io/n8n/issues/44758) (opened 2026-11-21, reporter Mattenhaim), reproduced with a unit test against current master. It is team-assigned (team:lifecycle) with Linear ticket GHC-9829, still open as of 2026-11-24, with no pull request or fixed version yet — so the steps below are the fix for now.

## The root cause: the prune step works from a snapshot taken before the move

n8n's source control import processes team project files one at a time in `SourceControlImportService.importTeamProjectsFromWorkFolder`. Inside that per-project loop, each project prunes its own variables — deleting local variables the project file no longer contains. The problem is *when* the deletion list is computed: from a `getAllCached()` snapshot taken **before** the loop starts, not from the state at the moment each project is processed.

Walk through a pull that moves `VAR1` (id `V`) from project A to project B:

1. Before the loop, the snapshot says: `VAR1` belongs to project A.
2. If A's file is processed first: A no longer lists `VAR1`, so the prune deletes it from A — while it still lives there, before B's file has had a chance to claim it.
3. If B's file is processed first: B's import moves `VAR1` into B, then A's prune runs against the stale snapshot, sees `VAR1` still attributed to A, and deletes it from B anyway.

Either order ends with the variable gone — or recreated empty by B's import, because variable values are instance-local and never travel through Git; only the stub (id, key, and an empty placeholder value) is synced. The value is destroyed in both outcomes.

Note the difference from the sibling bug reported the same day: [issue #44757](https://github.com/n8n-io/n8n/issues/44757) is about a pull *blanking* a variable's value when Git tracks the same key under a different id. That bug keeps the variable and empties it; this one deletes the variable outright. If a pull leaves a variable blank but present, you are hitting #44757, not this one.

## The fix: restore the variable, then stop the move from deleting it

There is no setting that repairs this, and no restart helps — the import itself deletes the variable. The fix is a restore plus a pre-pull habit.

### Step 1 - Snapshot your variable values before every pull

Before you pull, record the current values of every variable on the instance. The Variables page in the sidebar shows them, or list them through the Public API (use an API key from Settings → n8n API):

```bash
curl -s -H "X-N8N-API-KEY: <your-api-key>" \
  "https://<your-n8n-host>/api/v1/variables"
```

Keep that snapshot somewhere outside Git — a password manager, a sealed note, or an encrypted file. Never commit real values to the repository; the whole point of the stub design is that values stay out of Git.

If you have already pulled and the variable is gone, check whether you have a snapshot from before the pull — a previous API export, a screenshot, or the value recorded in your team's runbook. If nothing exists, the value is gone from n8n and must be re-entered from wherever it originally came from (the service that issued it, your secrets store, or the other environment that holds the same key).

### Step 2 - Recreate the variable under the correct project and restore its value

Open the Variables page, switch to the project that should own the variable (project B in the example above), create the variable with the same key, and type the real value back in from your snapshot.

Or restore the value through the Public API with the variable's id (list the variables first with the `GET` call above to get the id):

```bash
curl -s -X PATCH -H "X-N8N-API-KEY: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"value": "https://api.example.com/v2"}' \
  "https://<your-n8n-host>/api/v1/variables/<variable-id>"
```

Replace `<your-n8n-host>` with your n8n host, `<your-api-key>` with an API key, `<variable-id>` with the variable's id, and the value with the real one from your snapshot.

### Step 3 - Verify the variable is back, in the right project

Re-read the variables through the API and confirm the variable exists under the correct project with the real value, not `""`:

```bash
curl -s -H "X-N8N-API-KEY: <your-api-key>" \
  "https://<your-n8n-host>/api/v1/variables"
```

Check each variable's `projectId` in the response and confirm the moved variable is listed under the project that should own it. Then run a workflow that reads the variable — a Code node with `return [{ json: { v: $vars.VAR1 } }];` is enough — and confirm the execution output carries the real value. Do this before reactivating anything the pull may have touched: a workflow that ran with the missing or empty variable may have already written bad data downstream.

### Step 4 - Prevent the next pull from deleting a moved variable

The deletion only happens when one pull imports several project files and a variable moved between projects in that same pull. Pick one of these before the next pull:

- **Move variables in their own pull.** Commit and pull the project move separately from other project-file changes, so no pull ever contains both the old project's file without the variable and the new project's file with it. One project file changing per pull means the stale snapshot can never attribute the variable to the wrong project.
- **Do not move variables between projects at all until a fix ships.** If the variable must live under a different project, create the new variable under the target project first, update the workflows that read it, and only then delete the old one — in separate pulls, with a snapshot taken before each.
- **Re-pull after restoring.** Once you have recreated the variable under the correct project and set its value, run the pull again only after confirming the repository's project files agree on which project owns it. If the files still disagree, fix the repository first — a second pull over a still-wrong `projects/` state will delete it again.

## Prevent it next time

- **Diff the `projects/` files before you pull.** Open the project files in the repository (they sit in the source control work folder, the local clone of the connected repo under `~/.n8n/git` for npm installs or `/home/node/.n8n/git` for Docker) and look for a variable stub that changed projects between commits. That is the exact move this bug needs — if you see it, split the move into its own pull before pulling.
- **Snapshot variables as part of every deploy.** The `GET /api/v1/variables` call in Step 1 takes seconds and turns a silent data-loss bug into a one-minute restore. Make it a checklist item next to the pull itself.
- **Treat a missing variable as a red flag, not a missing configuration.** If a variable that existed is suddenly gone after a pull, do not just recreate it and move on — check whether the pull also hit the sibling bug (#44757) and blanked another variable's value, and check whether any workflow ran with the missing variable in between.
- **Keep values out of Git, always.** The placeholder `""` in the stub is by design. The bug is that the import deletes a variable (or recreates it empty) when it moves projects; committing real values to the repo to "fix" that would trade a recoverable bug for a permanent secret leak.
- **Watch for the upstream fix.** The proper fix is for the prune step to compute its deletion list from current state inside the per-project loop, instead of from the snapshot taken before it. As of 2026-11-24 no fix has been merged — issue #44758 is still open, team-assigned under GHC-9829 — so the separate-pull habit above is the workaround until a release fixes the prune.
- **Audit the other source control import paths.** The same service had two more bugs reported the same day: #44757 (pull blanks a variable's value on a same-key, different-id collision) and #44759 (export reports file entries by resource name instead of the id-based path it writes). If your team uses source control with variables, read the #44757 post too.

## FAQ

### The variable is blank after the pull, not missing. Is this still the bug?

No — that is the sibling bug, [issue #44757](https://github.com/n8n-io/n8n/issues/44757): the pull's key-collision fallback writes the stub's placeholder `value: ""` over your instance-local value. Restore it the same way (Variables page or `PATCH /api/v1/variables/{id}`), and check the pull's `variable_stubs.json` for a key that exists under a different id. If the variable is missing entirely, you are hitting #44758.

### I only pulled one project file. Can this still delete a variable?

Not through this bug — the stale snapshot only hurts when the pull imports several team project files and a variable moved between them. A single-project pull cannot contain both sides of the move. If a variable vanished after a single-project pull, check the sibling bug (#44757, blanking) or a forced pull, which can delete a variable the repository marks as a conflicting deletion.

### I use n8n Cloud, not self-hosted. Am I affected?

Source control and environments are available on n8n Cloud's Business and Enterprise plans as well as self-hosted, and the import service is the same. If your Cloud instance pulls from Git and a variable moved between team projects upstream, the same prune runs. The API restore in Step 2 works on Cloud too.

### Can I just re-push from the instance to fix the project files?

Pushing writes the instance's stubs to Git, including the project each variable belongs to — but it does not reconcile the move that is already recorded upstream. If the repository still says the variable moved from A to B while your instance has it under A, the next pull hits the same stale-snapshot prune. Align the repository's project files first (the move in its own commit, pulled separately), then push.

### Does this affect credentials too?

No — this bug is specific to project variables. Credentials travel as stubs as well, but the credential import path is separate and this per-project prune is in the variable import. Credentials have their own long-standing sync quirks (values resetting on pull has been reported separately), so snapshot those too, but a deleted credential is a different bug.

## Key Takeaways

1. **A source control pull can silently delete a variable moved between team projects** — the prune step computes its deletion list from a snapshot taken before the per-project loop, so whichever order the project files are processed, the moved variable is deleted (or recreated empty), with no error and no failed execution.
2. **The value is instance-local and never travels through Git** — only the stub does, so once the variable is deleted or recreated empty, the real value can only come back from a snapshot taken before the pull.
3. **Restore, then move variables in their own pull** — recreate the variable under the correct project, restore its value with the Variables page or `PATCH /api/v1/variables/{id}`, and never let one pull contain both sides of a project move until a fix ships.
4. **No upstream fix is merged yet** — issue #44758 is still open as of 2026-11-24, team-assigned under Linear GHC-9829, so diffing the `projects/` files before you pull is the protection until a release fixes the prune.

Next: if a pull leaves a variable blank but present instead of missing, you are hitting the sibling bug, [issue #44757](https://github.com/n8n-io/n8n/issues/44757) — the same service blanks a variable's value when Git tracks the same key under a different id. That post covers the restore and the id-alignment fix.
