---
title: "Fix n8n Source Control Breaking on One Malformed JSON File (Status, Push, and Pull All Fail)"
description: "One broken JSON file in n8n's source-control work folder kills every status check, push, and pull. Here's how to find and fix it."
date: 2026-11-15
category: automation
tags: ["n8n", "source-control", "git", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-source-control-malformed-json-breaks-sync.webp"
---

You push a workflow change from dev to prod and n8n's source control answers with a JSON parse error. You try a status check instead. Same error. You try a pull. Same error. Every source control operation is dead, the error message never tells you which file is broken, and the only way out is to find the one bad file by hand.

This is a confirmed bug in n8n's source control import service, filed as [GitHub issue #43951](https://github.com/n8n-io/n8n/issues/43951) on November 15, 2026 (still open as of November 15, 2026). By the end of this article you will know how to confirm you have hit this exact bug, locate the single malformed file in under a minute, repair or remove it, and stop it from happening again.

Quick definitions before we start: **source control** is n8n's built-in Git integration (Business and Enterprise plans) that syncs workflows, credentials, variables, and projects between environments through a connected Git repository. The **work folder** is the local clone of that repository on your n8n server — n8n keeps it in a `git` folder inside the n8n user folder (`~/.n8n/git` on an npm install, `/home/node/.n8n/git` inside the official Docker image). A **JSON parse error** means a file that is supposed to be valid JSON is not — a missing closing brace, a trailing comma, a truncated write — and the parser refuses to read it.

## The symptom: every source control operation fails with the same parse error

The failure looks like this. Source control was working — you connected a repository and pushed at least once, so credential and project export files exist in the work folder. Then one file in that folder gets corrupted: a partial write, a bad manual edit, an interrupted sync. From that moment, **every** status check, push, and pull fails with a JSON parse error, and the error does not say which file is broken. The failure is total and it does not heal itself — every subsequent operation keeps failing until the file is fixed by hand.

**How to tell this bug apart from other source control failures.** A Git authentication failure mentions credentials, keys, or `Permission denied`. A merge conflict names the conflicting files. This bug is the one where the error is a bare JSON parse complaint — something like `Unexpected token`, `Unexpected end of JSON input`, or `Unexpected non-whitespace character` — with no filename attached, and it blocks status, push, *and* pull equally. If your error names a file, or only one operation fails, you have a different problem.

## The root cause: credential and project files are parsed with no safety net

The reporter diagnosed this by reading n8n's source, and the diagnosis is short. The service that imports remote state, `SourceControlImportService` (in `source-control-import.service.ee.ts`), reads the work folder in batches — one batch for credentials, one for projects, one for data tables. The credential batch (`getRemoteCredentialsFromFiles`) and the project batch (`getRemoteProjectsFromFiles`) parse each file with a bare `jsonParse` and no error handling. One bad file throws, the throw propagates, and the whole operation aborts before it has read anything else.

The frustrating part is that the fix already exists in the same file. The data-table batch wraps its parse in a try/catch that logs `Failed to parse data table from file <file>: invalid JSON format` and skips the file, so a broken data-table export can never take down a sync. Credentials and projects simply never got the same treatment. The reporter's proposed fix is to wrap those two parses in the identical try/catch — log a warning with the file path, return `undefined` for the skipped entry, filter the skipped entries out — and notes the credential flow's downstream code already guards on `!remote?.id`, so the change is minimal. As of November 15, 2026 that fix is proposed, not shipped, so self-hosters have to fix the file themselves.

**One broken file takes down everything because the parse happens up front.** Status, push, and pull all start by loading the remote state from the work folder. The credential and project batches are part of that load. A single throw anywhere in the load aborts the entire operation, so there is no partial success and no degraded mode — it is all or nothing, and the nothing comes with no filename.

## Step 1 - Open the work folder and list what is in it

First, get onto the server that runs n8n and open the work folder — the local clone of your connected repository:

```bash
cd ~/.n8n/git
```

That path is for an npm install. Inside the official Docker image the n8n user folder is `/home/node/.n8n`, so the work folder is `/home/node/.n8n/git` — run the commands inside the container with `docker exec -it <container-name> sh` first.

List the contents so you know what you are looking at:

```bash
ls -la
```

You should see the repository's folders — workflows, credentials, projects, and similar — plus the usual `.git` directory. You do not need to stop n8n for the next step: validating files is read-only, and nothing below writes to the work folder until you decide to repair a file.

> **Warning:** Do not delete or edit files in this folder casually. It is a Git clone, not a scratch directory — every file in it is either a tracked export n8n wrote or a file Git is tracking. The next step finds the broken file without touching anything.

## Step 2 - Find the broken file by validating every JSON file

Run a loop that tries to parse every `.json` file in the work folder and prints only the ones that fail:

```bash
find . -name '*.json' -type f | while read -r f; do
  node -e "JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'))" "$f" 2>/dev/null || echo "BROKEN: $f"
done
```

Each line does one thing: `find` lists every JSON file, `node -e` parses it, and `|| echo "BROKEN: $f"` prints the path only when the parse fails. Valid files print nothing. If you do not have Node on the host, the Python equivalent works the same way:

```bash
find . -name '*.json' -type f -exec sh -c 'python3 -m json.tool "$1" > /dev/null 2>&1 || echo "BROKEN: $1"' _ {} \;
```

You should see exactly one line of output, naming the broken file — usually a credential or project export, matching the two unprotected batches. If you see zero lines, the broken file is not a `.json` file in this folder, or the corruption is in a file n8n reads from elsewhere; re-check that you are in the right work folder (the one for the instance that is failing, not a different environment's clone).

Two shortcuts that often point at the same file: `git status` shows which files changed most recently — the broken file is almost always the most recently edited one — and `git diff` shows the exact change that broke it, often a missing closing brace or a truncated tail from an interrupted write.

## Step 3 - Repair the file, or restore it from Git

You have two options, and restoring from Git is the safer one.

**Option A — restore the last committed version (recommended).** The work folder is a Git clone, so the last good version of the file is already on disk in Git's history:

```bash
git checkout -- <path-to-broken-file>
```

Replace `<path-to-broken-file>` with the path from Step 2, relative to the work folder. This discards the local corruption and restores the file exactly as it was at the last commit. Then re-run the validation loop from Step 2 — it should print nothing.

**Option B — repair the JSON by hand.** Open the file and fix the syntax: add the missing closing brace, remove a trailing comma, or restore the truncated tail. Use `git diff` to see what changed versus the committed version — the break is usually one or two characters. Validate with `node -e` or `python3 -m json.tool` after every edit, and do not guess at the file's contents: if you cannot see what the correct value should be, use Option A instead.

**If the file is a stale export you do not need**, deleting it is also safe — n8n regenerates credential and project export files on the next push. That said, prefer restoring from Git: a deleted credential file means that credential's stub will not sync on the next pull, and you will have to re-create the mapping by hand. Note that credential export files contain only name-and-type stubs — secrets never sync through source control — so neither repairing nor deleting one exposes a secret.

## Step 4 - Verify status, push, and pull all work again

Go back to n8n: **Settings > Environments** and run a status check. It should complete without the parse error. Then run a push and a pull (or whichever operation you need) and confirm both succeed. If the parse error returns, the validation loop from Step 2 will tell you whether a second file is broken — repeat Step 3 for it. If status works but push still fails with a different error, you have moved past this bug and into a separate issue (usually authentication or a merge conflict), which the error message will now name.

## Step 5 - Prevent the next broken file

Three habits keep this from recurring:

1. **Never hand-edit files in the work folder.** It is n8n's private clone, not an editing surface. Make changes in the n8n UI and let n8n write the exports, or edit in a separate checkout and push through Git properly.
2. **Validate JSON before it reaches the folder.** If anything else writes into the work folder — a backup script, a CI job, a sync tool — add a validation gate. A pre-commit hook that rejects invalid JSON costs one line and would have caught this class of failure entirely:

```bash
find . -name '*.json' -type f -exec python3 -m json.tool {} > /dev/null \;
```

That command exits non-zero on the first invalid file, which is exactly what a hook needs. Run it as a scheduled check on the server too, so a partial write from an interrupted sync is caught before the next person tries a push.

3. **Watch the upstream fix.** The proposed change in issue #43951 — the same try/catch-and-skip the data-table batch already has, applied to credentials and projects — would turn this from a total outage into a warning in the logs. When it ships, upgrade and the failure mode disappears; until then, the validation loop in Step 2 is your early-warning system.

## FAQ

### Does this affect Community Edition?

No. Source control and environments is a Business and Enterprise feature. Community Edition users version workflows by exporting JSON manually or on a schedule, so there is no work folder for this bug to live in — but the same validation loop is worth running on any folder of exported workflow JSON you commit to Git.

### Can a broken workflow file cause the same total failure?

Not through this code path. The issue covers the credential and project batches, which parse with no error handling. The data-table batch already skips broken files. Workflow files go through a different import path, so a malformed workflow JSON fails that workflow's import rather than every source control operation.

### The error is gone after I fixed the file, but the push shows unexpected changes. What happened?

The broken file may have been mid-write when it corrupted, so the restored version can differ from what n8n last exported. Review the status diff before pushing — if it lists changes you do not recognise, pull first, or re-export from the UI and confirm the diff is only the change you intended.

### How do I know when the upstream fix lands?

Watch [issue #43951](https://github.com/n8n-io/n8n/issues/43951). When the try/catch lands in a release, the release notes will mention source control resilience or the issue number. Until then, treat any bare JSON parse error from a status, push, or pull as this bug and start at Step 2.

## Key Takeaways

1. **One malformed JSON file in n8n's source-control work folder breaks status, push, and pull all at once** — because the credential and project batches parse with a bare `jsonParse` and no error handling, and the error never names the file.
2. **Find it in under a minute** by validating every `.json` file in `~/.n8n/git` (or `/home/node/.n8n/git` in Docker) with a `node` or `python3 -m json.tool` loop; `git status` and `git diff` usually point at the same file.
3. **Restore from Git with `git checkout -- <file>`** rather than hand-editing — the last good version is already in the clone, and credential files only hold name-and-type stubs, so nothing secret is at stake.
4. **Prevent it by never hand-editing the work folder** and gating any external writes with a JSON validation check; the upstream try/catch-and-skip fix proposed in #43951 will remove the failure mode entirely once it ships.

Next: if you run source control between environments, read the dev-to-prod promotion traps in our guide to [fixing n8n workflow changes not taking effect in production](/blog/fix-n8n-workflow-changes-not-taking-effect/) — the draft-versus-published gap is the next most common reason a "successful" push does not change what production runs.
