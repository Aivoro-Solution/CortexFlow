---
title: "Fix n8n Email Trigger (IMAP) Not Firing on New Emails (6 Verified Fixes)"
description: "n8n IMAP trigger silently dead on new emails? 6 verified fixes: re-save credential, reset UID watermark, Format=Resolved, Force Reconnect."
date: 2026-10-21
category: automation
tags: ["n8n", "imap", "email", "error-fix", "trigger"]
draft: false
featured: false
image: "/og/fix-n8n-imap-trigger-not-firing.webp"
---

Your n8n workflow is active, the IMAP credential tests "Connection successful", and clicking "Execute workflow" manually pulls new emails just fine. But real incoming mail never triggers the workflow. No error in the Executions tab, no red banner in the editor — just silence. This is one of the most-reported n8n trigger bugs of 2026, with a long trail of community threads and a genuine upstream fix in progress.

Quick definitions before we start: an **IMAP trigger** (the green "Email Trigger (IMAP)" node) holds a persistent connection to your mail server and listens for new messages via **IMAP IDLE** (the protocol's push mechanism — "tell me when new mail arrives"). The node also keeps a **UID watermark** — the ID of the last email it processed — so it only fetches *newer* mail on each reconnect. **Force Reconnect** is a node option that drops and re-opens the IMAP connection every N minutes, falling back to a fresh scan each time.

By the end of this article you'll know the five real causes of a silently-dead IMAP trigger, how to diagnose which one you have, and the six fixes that actually work — ordered from quickest to most structural.

**Prerequisites:** an n8n instance (the mechanics below apply to both n8n Cloud and self-hosted Docker installs; verified against threads on versions 2.0.x–2.43.x as of October 2026) and access to the workflow's IMAP credentials.

## The symptom: what the failure actually looks like

The failure has a consistent fingerprint across the threads:

1. **The workflow is active** (the toggle is green / the workflow is "Published"), but zero production executions appear in the Executions tab when mail arrives.
2. **Manual execution works** — "Execute workflow" or "Test step" fetches mail, proving the credential, mailbox path, and search rules are all valid.
3. **No error anywhere** — the IMAP connection never raises, because the node thinks everything is fine: it is either listening on a dead IDLE connection, waiting on a stale watermark, or crashing on a malformed message and silently deactivating in the background.

**How to confirm in one minute:** send a brand-new email to the monitored mailbox, leave it *unread*, and watch the Executions tab for 3 minutes. If nothing appears but manual execution picks the email up immediately, you have a trigger-path problem, not a credential problem.

## Root cause 1: stale credentials after an n8n upgrade

The most common fix reported on n8n Cloud: after upgrades, the IMAP trigger fails **silently** with a stale credential — while other nodes (HTTP Request, Read Email actions) still pass their tests. The credential handling changed in recent upgrades, so the trigger's background process uses a credential that is effectively invalid, but the "Connection successful" test you run in the UI tests a *fresh* connection, not the trigger's stored session ([community.n8n.io/t/316150](https://community.n8n.io/t/imap-trigger-stopped-working-completely-manual-automatic/316150)).

## Root cause 2: a stale UID watermark

The trigger only fetches mail *newer than its last-seen UID*. After upgrades this watermark state can reset or go stale, so the trigger "succeeds" on every check and finds zero new emails — even when five unread messages arrived today. This is why re-saving the workflow doesn't help: the watermark lives in the node's state, not in the workflow JSON ([t/316150](https://community.n8n.io/t/imap-trigger-stopped-working-completely-manual-automatic/316150)).

## Root cause 3: malformed email headers crashing the trigger (Simple format)

When the IMAP server returns certain malformed email headers, the trigger **crashes silently and deactivates the workflow in the background**. The cruel part: the emails are still marked as read (that happens before the crash), so it looks like everything worked and nothing ran. This particularly affects the **Simple** format parser; the n8n team fixed it in [PR #30375](https://github.com/n8n-io/n8n/pull/30375) (safety check for malformed headers, fixed mark-as-read to only flag actually-emitted emails, fixed duplicate processing on large batches). A related, deeper variant: one malformed message in INBOX (e.g. a forwarded email attached inside another email, with a `NIL` media type) crashes the underlying node-imap parser with `'toLowerCase' is not a function` — while a subfolder works fine, because the broken message isn't there ([t/313299](https://community.n8n.io/t/imap-trigger-drops-error-tolowercase-and-does-not-fetch-any-emails-from-inbox-but-from-sub-inbox-folder/313299)).

## Root cause 4: dead IMAP IDLE connections

The trigger relies on IMAP IDLE push notifications for new mail. Some servers (and many reverse proxies / firewalls in between) silently kill long-lived idle connections without telling either side. The node sits on a dead connection forever, waiting for notifications that will never arrive. Enabling **Force Reconnect Every N Minutes** replaces the dead-listener model with a periodic rescan ([t/120280](https://community.n8n.io/t/imap-not-triggering/120280)).

## Root cause 5: a broken date filter in Custom Email Config

If you use a custom `SINCE`-style date filter, an invalid date format breaks the query — and the connection dies. The standard IMAP query n8n passes through only understands `UNSEEN` flags and `SINCE <dd-MMM-yyyy>` dates, nothing like "emails from the last 2 minutes" ([t/262775](https://community.n8n.io/t/help-with-imap-trigger/262775)).

## Root cause 6 (upstream, in progress): broken IMAP4rev2 servers

Some providers (notably **STRATO**) run IMAP4rev2 in a way that defeats the trigger's "find new mail" logic. n8n merged the official fix in [PR #41018](https://github.com/n8n-io/n8n/pull/41018) — "Find new mail on servers with a broken IMAP4rev2 mode" — on 2026-10-15. **Important:** n8n support confirmed the fix is *not* in 2.43.8, and no release version has been announced yet. The trigger also got a related upstream improvement earlier: "Recover from silently dead connections by moving to imapflow (#36716)", which shipped in **n8n@2.41.0** ([release notes](https://newreleases.io/project/github/n8n-io/n8n/release/n8n@2.41.0)). If you're on 2.40.x or older, the imapflow fix alone may resolve a dead-trigger problem ([t/316150](https://community.n8n.io/t/imap-trigger-stopped-working-completely-manual-automatic/316150)).

## The 6 fixes, in order

### Fix 1 — Re-save the IMAP credential

Open the IMAP credential, re-enter the password, and save. Then deactivate and re-activate the workflow. This is the #1 rescue for post-upgrade silent death ([t/316150](https://community.n8n.io/t/imap-trigger-stopped-working-completely-manual-automatic/316150)). Try this first — it takes 30 seconds and fixes a surprising share of cases.

### Fix 2 — Reset the UID watermark (recreate the trigger node)

Delete **only** the Email Trigger (IMAP) node and add a fresh one (re-select the credential, re-enter the mailbox and options). This resets the internal UID watermark. Do not delete the whole workflow — the state is per-node ([t/316150](https://community.n8n.io/t/imap-trigger-stopped-working-completely-manual-automatic/316150)).

### Fix 3 — Switch Format to Resolved

In the trigger node, change **Format** from **Simple** to **Resolved**. This dodges the malformed-header crash that silently deactivates the workflow, and it's the official community-verified workaround for the pre-#30375 behavior ([t/120280](https://community.n8n.io/t/imap-not-triggering/120280)).

### Fix 4 — Enable Force Reconnect

Under the node's **Options**, set **Force Reconnect Every Minutes** to `5`. This gives up on fragile IDLE push and rescans on a schedule — production executions arrive on a 5-minute delay instead of never ([t/120280](https://community.n8n.io/t/imap-not-triggering/120280)).

### Fix 5 — Fix the Custom Email Config and bisects a poison message

If you use **Custom Email Config**, set it to just `["UNSEEN"]`. If you need a date filter, use the valid form:

```json
["UNSEEN", ["SINCE", "20-Oct-2026"]]
```

Never use "last N minutes" logic — standard IMAP can't express it, and a broken date format kills the connection ([t/262775](https://community.n8n.io/t/help-with-imap-trigger/262775)).

If INBOX itself fails while a subfolder works, **one specific email is crashing the parser**. Bisect it: move emails out of INBOX in batches until the trigger works again, then narrow down. Prime suspects: forwarded emails attached inside other emails, or `.eml` attachments. Remove or repair the message, or temporarily point the trigger at a clean folder ([t/313299](https://community.n8n.io/t/imap-trigger-drops-error-tolowercase-and-does-not-fetch-any-emails-from-inbox-but-from-sub-inbox-folder/313299)).

### Fix 6 — Upgrade past 2.41.0 (and watch for PR #41018)

If you're self-hosted, upgrade to at least **n8n 2.41.0** to get the imapflow recovery fix (#36716). Then keep an eye on the release notes for **#41018** ("Find new mail on servers with a broken IMAP4rev2 mode") — if your provider is STRATO or your trigger still dies with no other cause, that merged-but-unreleased fix is likely the one you're waiting for ([t/316150](https://community.n8n.io/t/imap-trigger-stopped-working-completely-manual-automatic/316150)).

## Verify it worked

1. Activate (publish) the workflow.
2. Send a **brand-new email** to the monitored mailbox and leave it **unread**.
3. Watch the **Executions** tab — a production execution should appear within the Force Reconnect interval (≤5 min if you set Fix 4; within ~1–2 min if IDLE works).
4. Confirm the email was marked read (or moved, per your **Post-process Action**), so it won't re-trigger.
5. For self-hosted installs with nothing in the Executions tab: `docker logs <your_n8n_container_name>` and grep for `emailReadImap` — trigger-path errors surface there, never in the UI ([t/303476](http://community.n8n.io/t/email-trigger-imap-fires-on-manual-execute-workflow-but-never-triggers-after-publish-production-v2-0-3/303476)).

## Prevent it next time

- **Pin a Force Reconnect interval (5 min) as standard practice** on every IMAP trigger you ship to production. IDLE push is elegant but fragile across firewalls; a periodic rescan is boring and reliable.
- **Keep Format on Resolved** unless you specifically need Simple and have upgraded past the #30375 fix.
- **Pin your n8n version tag** (`image: n8nio/n8n:2.41.0` style) and read the IMAP-related lines of each release's changelog before upgrading — two of the six fixes here are "the version you're on had a bug".
- **Monitor the trigger, not just the workflow.** Build a watchdog: a Schedule Trigger every hour that checks when the IMAP workflow last produced an execution (e.g. via the n8n API `/executions` or a "last run" timestamp written to a Data Table by the workflow itself), and alerts you if it goes quiet. One user in t/303476 sketched exactly this, and it's the only way to catch silent deactivation before it costs you a day's mail.

## FAQ

### Why does the IMAP trigger work when I test it manually but never fire automatically?

Manual execution uses the "fetch now" path with a fresh connection and ignores the UID watermark. Automatic mode uses the persistent IDLE listener (or the periodic scan) plus the watermark — so a stale credential, stale watermark, dead IDLE connection, or malformed-header crash only shows up in automatic mode.

### The credential test says "Connection successful" — why does the trigger still fail?

The UI test opens a fresh connection with the stored credential. The trigger's background process can hold a stale session (especially after n8n upgrades on Cloud). Re-saving the credential (Fix 1) forces the stored session to refresh.

### Does the Email Trigger (IMAP) watch subfolders?

It watches exactly the mailbox you put in the **Mailbox** field (e.g. `INBOX`). To watch a subfolder, use the provider's path format (e.g. `INBOX.Archive`) — and note the custom-folder support has its own upstream limitations.

### Which n8n version fixes the IMAP trigger?

Two separate fixes: the imapflow recovery fix (#36716) shipped in **2.41.0**; the broken-IMAP4rev2 fix (#41018) is merged but, as of 2.43.8, **not yet released**. If your server (e.g. STRATO) is affected by #41018, you'll need a release that contains it.

## Key Takeaways

- A silent IMAP trigger is almost never a broken credential — manual execution working while production stays dead is the tell.
- The four fast fixes: re-save the credential, recreate the trigger node (resets the UID watermark), switch Format to Resolved, and enable Force Reconnect every 5 minutes.
- Malformed email headers can silently crash the trigger (especially on Simple format) — fixed upstream in PR #30375; a poisoned INBOX needs bisecting.
- Upgrade past 2.41.0 for the imapflow recovery fix; PR #41018 (broken IMAP4rev2 servers like STRATO) is merged but unreleased as of 2.43.8.
- Add a watchdog workflow that alerts when the trigger goes quiet — it's the only way to catch silent deactivation early.

One next step: if none of the six fixes work, collect `docker logs` output filtered on `emailReadImap`, your n8n version, and your mail provider, and post it on [the IMAP thread](https://community.n8n.io/t/imap-trigger-stopped-working-completely-manual-automatic/316150) — that thread is where n8n staff are triaging the remaining cases.
