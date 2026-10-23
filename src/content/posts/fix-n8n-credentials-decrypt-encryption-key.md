---
title: "Fix n8n \"Credentials Could Not Be Decrypted\" After a Restore or Re-Deploy (N8N_ENCRYPTION_KEY Recovery)"
description: "Every n8n credential fails with \"Credentials could not be decrypted\" after a restore? The fix is restoring N8N_ENCRYPTION_KEY. Recovery runbook here."
date: 2026-10-23
category: automation
tags: ["n8n", "self-hosting", "credentials", "encryption", "docker"]
draft: false
featured: false
image: "/og/fix-n8n-credentials-decrypt-encryption-key.webp"
---

n8n starts normally after your restore. The editor loads, your workflows are all there — and then every single workflow that touches an external service fails with **"Credentials could not be decrypted."** Nothing in your workflows changed. The database is intact. What broke is invisible: the encryption key that n8n used to lock every credential no longer matches the one protecting the data.

By the end of this guide you will have your credentials decrypting again — either by restoring the original `N8N_ENCRYPTION_KEY`, or, if the key is truly gone, by rebuilding credentials in the safest order — plus a backup setup that makes this impossible next time.

**Example terminology** — used consistently in every command below:

- `<old-key>`: the original 64-character hex `N8N_ENCRYPTION_KEY` from your previous deployment (from your old `.env` backup or secrets manager)
- `<compose-dir>`: the directory holding your `docker-compose.yml`, e.g. `/opt/n8n`

## Symptom — everything works except authentication

The signature of this failure is distinctive: n8n boots clean, the UI works, workflows load — but **all** credentials fail at once. Opening any credential in the editor shows it as undecryptable, and executions die the moment a node tries to authenticate with an external service. If one credential failed while the rest worked, you'd have a credential problem. When they all fail together right after a restore, re-deploy, volume loss, or migration, you have a key problem.

## Root cause — one key encrypts every credential

`N8N_ENCRYPTION_KEY` is the AES-256 key n8n uses to encrypt every credential stored in its database: API keys, OAuth tokens, database passwords, SMTP passwords — all of it. The ciphertext lives in the database; the key lives in the environment. When the two drift apart, decryption is mathematically impossible. There is no reset mechanism, no master key, and no support ticket that can fix it.

Three scenarios cause the drift, and they all show up in real incident reports (n8n GitHub issues #17986, #17816, #12949 and the [community thread "Noticed some missing credentials"](https://community.n8n.io/t/noticed-some-missing-credentials/282423/1)):

1. **Container recreated without its data.** A `docker compose down -v` deletes the named volume, or a fresh server starts with a fresh environment. The database gets restored from backup, but the key in the new environment is different — or auto-generated fresh.
2. **Postgres dump restored onto a fresh instance.** The dump carries the ciphertext; the new instance's key doesn't match the one that encrypted it. n8n starts fine, which makes this failure mode cruel: everything looks healthy until the first execution.
3. **A second instance sharing one database.** Two n8n containers pointed at the same Postgres with different keys. Whichever instance writes credentials last wins; the other sees garbage.

The first-boot trap makes this worse: if you never set `N8N_ENCRYPTION_KEY` explicitly, n8n generates one on first run and stores it locally. It works perfectly — until the volume dies with it. And if you deployed without a key at all on older behavior, credentials were encrypted with a default value, which is functionally equivalent to no encryption.

## Step 1 - Confirm it's a key drift, not a credential problem

Before touching anything, confirm the diagnosis. Check which key your running container actually has:

```bash
cd <compose-dir>
docker compose exec n8n env | grep N8N_ENCRYPTION_KEY
```

Now compare it against your old deployment's `.env` backup (the one you made when you first set up the server — if you didn't, check your password manager or wherever deployment secrets live). If the strings differ, or the running container has no key at all while the credentials were encrypted with one, you've found it.

> **Note:** This diagnosis is confirmed by scope, not by the logs. One broken credential is a credential problem. All credentials broken at once, right after a restore, migration, or re-deploy, is a key drift. Don't re-enter credentials yet — with the right key, they decrypt in place and re-entering is wasted work.

## Step 2 - Restore the original encryption key

This is the entire fix when you still have the old key. Put the exact original string back in the environment:

```bash
cd <compose-dir>
# in your .env file (or docker-compose.yml environment block):
# N8N_ENCRYPTION_KEY=<old-key>
```

The key is a 64-character hexadecimal string — copy it character-for-character. A single wrong character produces a different key, and n8n will report the same error with no additional detail about *which* side is wrong.

Then recreate the container so the new environment takes effect:

```bash
docker compose up -d
```

n8n will boot and decrypt every credential in place. You do not need to re-enter anything.

**Verify:** open any credential in the editor — it should load its stored values without errors. Then run one affected workflow end to end. Finally, grep the logs for the decrypt failure to confirm it's gone:

```bash
docker compose logs n8n --tail=200 | grep -i "could not be decrypted" || echo "OK: no decrypt errors"
```

You should see `OK: no decrypt errors`.

## Step 3 - If the key is truly gone: rebuild credentials in the safest order

If there is no backup of the key anywhere — not in an old `.env`, not in a password manager, not in a secrets vault — the encrypted credentials are permanently unrecoverable. Accept this before spending hours: no key rotation, no database surgery, and no n8n feature will resurrect them. What you can do is rebuild efficiently.

1. **Inventory first.** List every credential in the n8n UI (Settings → Credentials, or the credentials view). Every single one is dead — don't assume any survived.
2. **Start with the credentials your most critical workflows need.** Re-enter API keys manually, and re-run OAuth flows for Google, Microsoft, and similar providers (each gets a fresh token pair on re-auth; revoking the old app connection in the provider's console first avoids "duplicate grant" confusion).
3. **Test workflow by workflow, most critical first.** Don't try to re-authenticate all 40 credentials in one sitting and then discover step 4 of workflow 3 was broken. Fix, test, move on.
4. **Don't delete and recreate credential records blindly.** Re-entering values into the existing credential record keeps every node referencing it intact. Deleting the record orphans the references and forces you to re-wire nodes.

> **Warning:** while you're rebuilding, workflows that run on schedules will keep failing with auth errors on every trigger. Pause your schedules (or set the workflows inactive) until their credentials are healthy again — otherwise you'll wake up to hundreds of failed executions and, on some providers, locked-out accounts from repeated failed auth attempts.

## Step 4 - Lock it down so this never happens again

This failure is a backup-design problem, not a one-time accident. Five minutes now prevents the next incident:

- **Generate the key once, on day one, and pin it:** `openssl rand -hex 32` produces the 64-char hex string. Set `N8N_ENCRYPTION_KEY` in your `.env` before the first boot and never change it.
- **Back up the key separately from the database.** A database backup without its key is a backup of ciphertext. Store the key in a password manager and your team's secrets vault — the two must be restorable together.
- **Inject it via a proper secret mechanism:** an `.env` file with `chmod 600`, Docker secrets, or Kubernetes secrets. Never commit it to a git repo, never bake it into a container image, never paste it into chat or logs.
- **Back up the n8n volume too.** With Docker named volumes, a nightly tarball costs one cron line and captures anything the database dump misses:

```bash
# /opt/n8n/backup.sh — nightly, ships off-box
docker run --rm \
  -v n8n_n8n_data:/data \
  -v /opt/n8n/backups:/backup \
  alpine tar czf /backup/n8n-$(date +%F).tar.gz -C /data .
```

```bash
chmod +x /opt/n8n/backup.sh
echo "0 3 * * * /opt/n8n/backup.sh" | crontab -
```

A backup that lives only on the server you're backing up isn't a backup — ship the tarballs and the key off-box.

**Limits:** this runbook doesn't cover key *rotation* (n8n has no supported re-encryption path — changing the key on a live instance is the same as losing it; you must re-enter every credential). It also assumes you control the deployment; n8n Cloud manages keys for you, which is exactly why this is a self-hosting failure mode.

## FAQ

### Where is the encryption key stored if I never set one?

On first run, n8n generates a random key and stores it in its local configuration. With Docker named volumes that means it lives inside the `n8n_data` volume — which is exactly why losing the volume loses the key. Set `N8N_ENCRYPTION_KEY` explicitly and manage it through a real secret store so restores are predictable.

### Can I restore a database backup on a new server without the old key?

You can restore the database and n8n will run — but you won't be able to decrypt any stored credential. The only practical recovery path is recreating every credential from your providers, as in Step 3.

### I changed the key on purpose for security. What now?

Changing the key has the same effect as losing it: every stored credential becomes undecryptable. The safe sequence is: keep the old key running, re-enter (re-encrypt) all credentials under it, export your secrets inventory — there is no shortcut. Plan key changes like a migration, not a config edit.

### Does this affect n8n Cloud users?

No. n8n manages encryption keys for Cloud workspaces. This is strictly a self-hosting failure mode — which is also why it bites hardest: there's no one else to call.

## Key Takeaways

1. **"Credentials could not be decrypted" on all credentials at once, after a restore or re-deploy, is always a key drift** — one broken credential is a credential problem; all of them is a key problem.
2. **The fix is restoring the original `N8N_ENCRYPTION_KEY` character-for-character**, then `docker compose up -d` — credentials decrypt in place, no re-entry needed.
3. **Without the original key there is no recovery** — rebuild credentials workflow-by-workflow, most critical first, reusing existing credential records.
4. **Back up the key next to the database, off-box** — a DB backup without its key is a backup of ciphertext.
5. **Pin the key on day one** with `openssl rand -hex 32`, inject it via a secret mechanism, and never commit it to git or bake it into an image.

Next: run the volume backup cron above tonight and confirm the key is in your password manager — five minutes that converts this from a recurring incident into a solved problem. If you're hardening the rest of the instance, read [how to fix n8n out-of-memory crashes in Docker Compose](/blog/fix-n8n-oom-crash-docker-compose/), the other way self-hosted n8n dies quietly.
