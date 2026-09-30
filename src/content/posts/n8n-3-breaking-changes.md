---
title: "n8n 3.0 Breaking Changes: What to Fix Before You Upgrade"
description: "n8n 3.0 lands October 2026: removed nodes, mandatory Docker, tighter defaults. Complete breaking-changes checklist inside."
date: 2026-10-01
category: automation
tags: ["n8n", "upgrade", "self-hosting", "Docker", "migration", "AI agents"]
image: "/og/n8n-3-breaking-changes.webp"
draft: false
featured: false
---


n8n 3.0 arrives in October 2026, and it is the most disruptive n8n upgrade in years: legacy nodes get deleted, `npm` installs stop working, and several security defaults get tightened. Upgrade blindly and workflows will fail on first boot. By the end of this guide you will have a complete checklist of every confirmed breaking change and the exact fix for each — so you upgrade on your schedule instead of firefighting on n8n's.

One honest framing first: **n8n 3.0 is not released yet.** As of September 30, 2026, the latest stable is 2.41.4. Everything below comes from n8n's official [3.0 breaking changes document](https://docs.n8n.io/changelog/v30-breaking-changes), a living pre-release page n8n says it will keep updating. Treat this as the confirmed plan, not final release notes — and re-check that page before you pull the trigger.

A **breaking change** is anything that can stop existing setups from working: a removed node, a deleted config option, a new default. A **deprecation** is the warning phase before removal. n8n has been deprecating most of this list across the 2.x line; 3.0 is when warnings turn into errors.

## Who gets hit hardest

| Your setup | Risk | Read these sections |
|---|---|---|
| Self-hosted via `npm` / `npx n8n` | **Critical** — your install method stops working | Steps 1, 5, 6 |
| Workflows using Function, Item Lists, Cron, or Interval nodes | **High** — nodes are deleted | Step 3 |
| AI Agent node v1 (SQL/Conversational/ReAct modes) | **High** — old agent modes removed | Step 3 |
| Docker self-hosted, default config | **Medium** — tighter defaults may bite | Steps 6, 7 |
| Custom chat client on the Chat Trigger WebSocket | **Medium** — wire protocol changes | Step 7 |
| n8n Cloud users | **Low** — mostly node removals apply | Step 3 |

## Step 1 - Back up your instance

n8n's database migrations only run forward — there is no downgrade path except restoring a backup. If you can restore, you can experiment. If you cannot, you cannot safely upgrade.

**Export all workflows:**

```bash
n8n export:workflow --all --output=/backups/n8n-workflows-$(date +%F).json
```

`--all` covers inactive workflows too; without it you only get active ones, a classic way to lose work.

**Back up the data directory** (`~/.n8n` for npm installs, or your mounted volume for Docker):

```bash
tar -czf /backups/n8n-data-$(date +%F).tar.gz ~/.n8n
```

Postgres users: take a database dump. And remember the community's hard lesson — bumping the Postgres image tag alone corrupts the database ("database files are incompatible with server"). Dump and restore; never just change the tag.

**Write down your encryption key** and store it off-server:

```bash
grep N8N_ENCRYPTION_KEY ~/.n8n/config 2>/dev/null || echo "check your env file"
```

> **Warning:** Losing `N8N_ENCRYPTION_KEY` is unrecoverable — every stored credential becomes unreadable, with no "forgot key" flow. The 3.0 Docker migration is exactly the kind of move during which people lose it. Copy the key before changing anything.

## Step 2 - Run n8n's migration report

n8n 2.x ships a **3.0 migration report** under **Settings** that flags exactly which parts of your instance are affected: legacy nodes in your workflows, removed environment variables, Chat Hub usage, sub-workflows using deleted sources. n8n also logs a deprecation warning at startup on 2.x for each affected setting — check your logs after a restart.

Run this on your current version before upgrading. It turns the generic checklist below into a personalized hit list.

## Step 3 - Replace removed nodes

n8n 3.0 deletes legacy nodes outright — workflows containing them fail after upgrade. Migrate on 2.x first, where old and new nodes exist side by side, so you can test each replacement before the old one disappears.

**The big four** — what most workflows will hit:

- **Function / Function Item → Code node.** Use **Run Once for All Items** mode for Function, **Run Once for Each Item** for Function Item.
- **Item Lists → the matching operation node.** There is no single successor: check which operation each node uses and swap in Split Out, Aggregate, Sort, Limit, Remove Duplicates, or Summarize.
- **Cron / Interval → Schedule Trigger.** Copy the schedule settings across and verify the next-run preview matches.
- **AI Agent v1 → latest AI Agent (Tools Agent).** The SQL, Conversational, OpenAI Functions, Plan and Execute, and ReAct modes are removed. Workflows already on Tools Agent keep working after a node version bump. For old SQL Agent use cases, pair a Postgres/MySQL tool sub-node with a current AI Agent node.

**Everything else removed**, with replacements:

| Removed | Replace with |
|---|---|
| HTML Extract | HTML node's Extract HTML Content operation |
| iCalendar | Convert to File → Convert to ICS |
| Convert to/from Binary Data | Convert to File / Extract from File |
| Read/Write Binary File(s) | Read/Write Files from Disk |
| Read PDF | Extract from File (Extract From PDF) |
| Workflow Trigger | n8n Trigger |
| Legacy OpenAI node | Current OpenAI node (assistants via its Assistant resource) |
| OpenAI Assistant / OpenAI Model | OpenAI node / OpenAI Chat Model |
| Legacy HTTP Request Tool | HTTP Request node on the AI Agent's Tool input |
| Manual Chat Trigger | Chat Trigger |
| Chat Messages Retriever | Chat Memory Manager (or Chat Trigger session loading) |
| Binary/JSON/GitHub Document Loaders | Default Data Loader (fetch GitHub content with the GitHub node first) |
| Old vector-store Insert/Load pairs | Unified node per store (Simple/Pinecone/Supabase Vector Store) |
| Motorhead / Zep memory + Zep Vector Store | Another memory or vector-store node (no direct replacement) |
| SerpApi (Google Search) | HTTP Request node against the SerpApi REST API |
| Orbit | Nothing — the service shut down |

Two pieces of good news: the **AI Transform** node is auto-migrated to a Code node on upgrade (same generated JavaScript, no action needed), and **Execute Sub-workflow** only loses its **Local File** and **URL** sources — switch those to **Database** or **Define Below**.

After replacing nodes, run each workflow end to end on 2.x. Do not trust the canvas alone; replacements have subtly different defaults.

## Step 4 - Fix expressions and Code node calls

**`$getPairedItem` is deleted.** Replace this deprecated expression helper with standard item linking — the `pairedItem` property or `$("Node Name").item`. Search workflows for `$getPairedItem(` and rewrite each call site.

**`$evaluateExpression()` is removed from the Code node.** Only insecure-mode task runners are affected (secure mode, the default since n8n 2.0, already fails on it). Evaluate the expression in a node field instead — e.g. an Edit Fields node before the Code node — and read the result from the input item. It keeps working inside `{{ }}` expression fields.

## Step 5 - Migrate off npm/npx to Docker

**Self-hosted n8n requires Docker in 3.0. `npm` and `npx n8n` installs are no longer supported**, and n8n stops publishing a runnable `n8n` npm package. n8n's own step-by-step guide for this move is still marked "coming soon," so here is the minimal path for a local npm install, keeping your existing data:

```bash
docker run -d --name n8n \
  -p 5678:5678 \
  -e N8N_ENCRYPTION_KEY="<paste-your-existing-key-here>" \
  -v ~/.n8n:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n:2.41.4
```

What each flag does: `-p 5678:5678` exposes the editor on the same port npm used. `N8N_ENCRYPTION_KEY` must be **your existing key** from Step 1 — a fresh key here means n8n cannot decrypt your stored credentials. `-v ~/.n8n:/home/node/.n8n` carries your workflows, credentials, and settings into the container. The tag is pinned to `2.41.4` deliberately: **migrate the deployment method first on your current version, verify everything works, and only then bump the tag to 3.0.** Changing deployment method and major version in one move is how you end up debugging blind.

> **Note:** `docker.n8n.io/n8nio/n8n` is n8n's official registry. Never use `:latest` in production — pin exact versions so a routine `docker pull` cannot surprise-upgrade you.

## Step 6 - Update configuration and environment variables

n8n logs a deprecation warning at startup on 2.x for each of these affecting you. Check those logs.

| Variable | Change in 3.0 | Action |
|---|---|---|
| `N8N_PRE_EXECUTE_ERROR_CREATES_EXECUTION` | Removed | Delete it; the new behavior (no execution record when a pre-execute hook throws) becomes permanent |
| `N8N_UNVERIFIED_PACKAGES_ENABLED` | Default `true` → `false` | Set `=true` explicitly to keep installing unverified community nodes |
| `N8N_RUNNERS_TASK_TIMEOUT` | Default 300s → 60s | Set explicitly (e.g. `300`) if any Code task runs longer than a minute |
| `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS` | Removed | Delete it; queue-mode manual executions now always run on workers — size worker memory accordingly |
| `N8N_DB_PING_TIMEOUT` | Removed | Use `DB_PING_TIMEOUT_MS` |
| `N8N_DEFAULT_BINARY_DATA_MODE=default` | Invalid | Set `filesystem`, `s3`, `azure`, or `database`; confirm container disk has room |
| `N8N_MIGRATE_FS_STORAGE_PATH` | Removed | See storage rename below |
| `N8N_ENABLED_MODULES` | Chat Hub now opt-in | Add `chat-hub` (e.g. `agents,chat-hub`) only if you still use it — deleted in 4.0 |

**Storage directory rename.** On first start, 3.0 renames `~/.n8n/binaryData` to `~/.n8n/storage`. If you mount a volume at the old path, remount at `~/.n8n/storage` — or set `N8N_STORAGE_PATH` to the old path. If both directories exist, n8n refuses to start: move `binaryData`'s contents into `storage`, delete the empty `binaryData`, then start. **In-memory binary data mode is also gone** — switch to `filesystem` or an external store.

## Step 7 - Adjust to tighter security defaults and behavior changes

3.0 is primarily a security-hardening release, and the new defaults can break unusual-but-legitimate setups:

- **Larger SSRF block list.** SSRF (Server-Side Request Forgery) protection stops n8n calling internal or cloud-metadata addresses. 3.0 additionally blocks `100.64.0.0/10` and IPv6 transition ranges. If your workflows call hosts there, allowlist them via `N8N_SSRF_ALLOWED_IP_RANGES` (or hostnames via `N8N_SSRF_ALLOWED_HOSTNAMES`). Keep the keyword `default` in `N8N_SSRF_BLOCKED_IP_RANGES` — it stands for the whole built-in list.
- **Key rotation on by default.** Strictly an improvement for most, but test anything external that reads n8n's credential store directly.
- **Lower Compression node limits.** Max decompressed size drops 2 GiB → 256 MiB and max zip entries 5,000 → 1,000. If your workflows unzip large archives, set `N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES=2147483648` and `N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES=5000` explicitly before upgrading.
- **Gmail Trigger below v1.4 runs as v1.4.** Drafts are skipped unless you enable **Include Drafts**; sent and scheduled emails no longer trigger. If a workflow depends on sent mail, rebuild with a Schedule Trigger plus Gmail's Get Many operation.
- **Chat Trigger WebSocket frames are now JSON.** Every frame carries a `type` field (`heartbeat`, `continue`, `error`, `message`, `with-buttons`); a text reply is `{ "type": "message", "text": "..." }`. The official `@n8n/chat` widget handles both formats from v1.31.0 — update it before upgrading if you self-host the embed. Only custom-built chat clients need code changes.
- **Webflow OAuth2: Legacy toggle defaults off.** Existing connected credentials keep working, but if you use the deprecated Webflow v1 Data API, turn **Legacy** back on before reconnecting.
- **Always Output Data on multi-output nodes.** If/Switch nodes now emit an empty item only when *every* output is empty — previously each empty output emitted one, so branches could run when they should not have. Review flagged nodes.

Retired capabilities, briefly: **Chat Hub is off by default** (deleted in 4.0; re-enable via `N8N_ENABLED_MODULES` as borrowed time); **workflow import from URL** is removed from the editor (copy-paste, file import, CLI, and API remain); the **external-secrets project-roles setting** is removed (Enterprise — use custom project roles to restrict); the **Ask AI tab in the Code node** is removed.

## Step 8 - Roll back safely and verify

If the upgrade goes wrong, do not debug forward on production:

1. Stop the 3.0 container.
2. Restore the pre-upgrade backup from Step 1 (data directory or Postgres dump).
3. Start the previous image tag.
4. Verify the editor loads and one scheduled workflow fires.

After a successful upgrade, test before declaring victory: manually execute each migrated workflow; confirm a scheduled trigger fires on time; hit one webhook workflow externally; execute a credential-heavy workflow to prove decryption works; and check startup logs for deprecation warnings you missed.

## Limitations and what I could not verify

**I could not test the 3.0 upgrade hands-on** — no 3.0 build existed as of September 30, 2026, and the official doc says n8n will update it with full details and migration guides as release approaches. The Docker steps above use standard n8n Docker patterns, not a 3.0-tested procedure. Community-node developer changes (`n8n-node dev` requiring Docker/Podman, per-image test-data volumes) affect node authors, not end users, so I left them out. Re-check the [official breaking changes page](https://docs.n8n.io/changelog/v30-breaking-changes) before upgrade day — if anything here changed, the official page wins.

## FAQ

### When exactly is n8n 3.0 released?

Scheduled for October 2026; no exact date announced. Do not upgrade on day one — let early adopters find the surprises.

### Do n8n Cloud users need to do anything?

The node removals apply to everyone, so audit workflows for deleted nodes. The Docker, env-var, and storage changes are self-hosting concerns.

### Will my workflows break the moment I upgrade?

Workflows using removed nodes or deleted expression helpers will fail. Everything else keeps working — and the Settings migration report on 2.x tells you exactly which workflows are affected before you commit.

### Can I stay on 2.x?

You can, but 2.x will stop receiving updates, and each skipped major makes the eventual jump harder. Audit now, fix at your pace, upgrade when ready.

## Key Takeaways

- **Back up first: n8n migrations only run forward.** Export workflows, archive `~/.n8n` (or dump Postgres), and copy `N8N_ENCRYPTION_KEY` off-server before anything else.
- **Migrate nodes on 2.x, not on 3.0.** Function → Code, Item Lists → operation nodes, Cron/Interval → Schedule Trigger, AI Agent v1 → Tools Agent — swap while both versions exist so you can test.
- **`npm`/`npx` installs end at 3.0.** Move to Docker on your current version first, verify, then bump the image tag. Never change deployment method and major version in one move.
- **Audit the quiet killers:** the task timeout dropping to 60s, unverified packages defaulting off, the storage rename, and the enlarged SSRF block list.
- **3.0 is scheduled, not shipped.** Everything here comes from n8n's official pre-release doc — re-check it before upgrade day.

Next step: open n8n's Settings today and run the 3.0 migration report on your instance. Whatever it flags is your personal hit list — work through it this week, and October's upgrade becomes a non-event.
