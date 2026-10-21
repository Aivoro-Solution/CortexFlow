---
title: "Fix n8n Cloud + Neon PostgreSQL: pg_stat_ssl Says ssl=false but Your Connection Is Encrypted"
description: "pg_stat_ssl says ssl=false on Neon but your n8n Cloud connection is encrypted. The proxy explanation, real TLS checks, and exact credential settings."
date: 2026-10-21
category: automation
tags: ["n8n", "postgresql", "neon", "ssl", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-cloud-neon-postgres-ssl.webp"
---

You connect n8n Cloud to your Neon PostgreSQL database. The Postgres node credential is set to **SSL: Require** with **Ignore SSL Issues: OFF** — encryption, enforced. Then you run a sanity check:

```sql
SELECT ssl, version, cipher
FROM pg_stat_ssl
WHERE pid = pg_backend_pid();
```

And it returns:

```
ssl     | version | cipher
--------+---------+--------
false   |         |
```

Your stomach drops. Encryption is supposed to be on — is your data flying across the internet in plaintext? A real n8n user asked exactly this on the community forum (thread [322682](https://community.n8n.io/t/322682)), and the answer is counter-intuitive: **your connection is encrypted. The query is measuring the wrong leg of the journey.**

By the end of this article you will know why `pg_stat_ssl` lies to you on Neon, the exact credential settings that keep the connection secure, and two independent ways to prove TLS is actually working.

## The symptom: ssl=false with SSL: Require set

The setup that triggers the scare is completely normal:

- n8n Cloud Postgres node, host set to your Neon hostname (e.g. `ep-quiet-dawn-123456.us-east-2.aws.neon.tech`)
- Port `5432`, SSH tunnel off
- Credential **SSL: Require**, **Ignore SSL Issues: OFF**
- Connection test succeeds

Then `SELECT ssl FROM pg_stat_ssl ...` says `false`, and `version` / `cipher` are NULL. The natural conclusion — TLS negotiated nothing and fell back to plaintext — is wrong.

## The root cause: Neon terminates TLS at its proxy, not at Postgres

TLS stands for Transport Layer Security: the protocol that encrypts the data in transit between two network endpoints. To see why the query misleads, you need Neon's architecture.

Neon sits a **connection proxy** in front of your actual Postgres compute. Your client never talks to Postgres directly:

1. **Leg 1 — n8n Cloud to the Neon proxy.** This is where TLS is negotiated and enforced. Neon refuses any connection that does not use TLS, full stop.
2. **Leg 2 — the proxy to your Postgres compute.** This travels over Neon's internal network, and the TLS from leg 1 is terminated at the proxy. From Postgres's point of view, the backend connection arriving from the proxy is not TLS.

`pg_stat_ssl` is a Postgres system view: it reports the TLS state of the *backend* connection — leg 2, the proxy-to-compute hop. So `ssl = false` describes the internal hop, and says absolutely nothing about leg 1, which is where your data actually crosses the internet.

<figure class="shot">
  <img src="/figures/fix-n8n-cloud-neon-postgres-ssl-tls-inspector.svg" alt="Isometric two-leg TLS inspection bench: an n8n client station flows through a Neon proxy tower with a glowing verification seal, then through a plain pipe into a Postgres tank whose gauge reads false" loading="lazy" />
  <figcaption>The connection as a two-leg inspection bench. The client station (n8n Cloud) flows into the Neon proxy tower, whose lit seal means TLS terminated and the certificate verified — that is leg 1, carrying your data across the internet, encrypted. A plain pipe then runs to the Postgres tank (leg 2, Neon's internal network), and its gauge reads <strong>false</strong> — the misleading <code>pg_stat_ssl</code> readout. <strong>Notice:</strong> the gauge that scares you measures the wrong leg. The leg that matters is the one with the seal.</figcaption>
</figure>

The forum's accepted explanation (and a local reproduction by a community member against the n8n 2.44.4 PostgreSQL transport, which showed the same `false/null/null` while the client-to-proxy hop was encrypted) confirms this: **with Require and Ignore SSL Issues OFF, a working connection is already the verification.** With Ignore SSL Issues off, n8n does not skip certificate checking — the TLS handshake verifies Neon's certificate chain and that it matches your Neon hostname. If either check failed, the connection would be refused, not silently downgraded.

## Step 1 — Set the credential exactly this way

In your n8n Postgres credential (Postgres node → Credentials → Postgres account):

| Field | Value | Why |
|---|---|---|
| Host | your Neon hostname, e.g. `ep-quiet-dawn-123456.us-east-2.aws.neon.tech` | Copy it from the Neon dashboard **without** the username prefix and **without** the database name suffix |
| Port | `5432` | Neon's pooled and direct endpoints both listen here |
| SSL | **Require** | Forces TLS on leg 1 |
| Ignore SSL Issues | **OFF** | Keeps certificate verification on — do not toggle this just to make a connection work |
| SSH Tunnel | OFF | Not needed for a public cloud database |

Neon gives you the connection details as a single URL string. Split it yourself: the host is the part after the `@` and before the first `/`. Do not paste the whole URL into the Host field — the forum is full of people whose connection failed purely from that.

**You should see:** the credential "Test" button returns a success. If it does, TLS leg 1 negotiated and the certificate checked out. That success is the proof the `pg_stat_ssl` scare is a measurement artifact.

## Step 2 — Prove it from your own machine (independent check)

If you want evidence outside n8n's managed environment, verify the certificate yourself from a terminal with `psql`:

```bash
psql "postgresql://USER:PASSWORD@YOUR-NEON-HOST/DBNAME?sslmode=verify-full"
```

Breaking down the important part:

- `sslmode=verify-full` asks Postgres's client to do **full certificate verification**: the server certificate must chain to a trusted certificate authority *and* match the hostname you connected to. This is the same check n8n performs with Ignore SSL Issues OFF.
- Replace `USER`, `PASSWORD`, `YOUR-NEON-HOST`, and `DBNAME` with your Neon values. Quote the whole URL — shells mangle unquoted `?` and `&`.

**You should see:** a normal `psql` prompt. If the connection opens, Neon's certificate is valid for your hostname and trusted by a public CA — the exact property you were doubting. If it fails with a certificate error, that is genuinely worth reporting to n8n support or the forum thread.

A second, lower-level check confirms TLS at the network layer without any client library in between:

```bash
openssl s_client -starttls postgres -connect YOUR-NEON-HOST:5432
```

Look at the output's chain and the `Verify return code`. A code of `0 (ok)` means the full chain validated. This bypasses every n8n abstraction and asks the Neon endpoint directly.

## Step 3 — Stop using pg_stat_ssl for this (and what to check instead)

The tempting next step is to keep running the `pg_stat_ssl` query hoping for `true` one day. Don't — it will keep saying `false` for as long as Neon terminates TLS at its proxy, which is the documented, intended behavior. On Neon, that view can never tell you about your client hop.

Instead, run this negative test to confirm encryption is *enforced*, not just available: flip the credential's SSL to **Disable** temporarily and test. The connection will fail, because Neon rejects non-TLS connections. Flip it back to Require. You have now proven two things the query couldn't: TLS is on, and it cannot be turned off by accident.

## If the connection actually fails — the real fix checklist

If your problem isn't the scary query but a genuine connection failure, work this list top to bottom before touching SSL settings:

1. **Host parsing.** Neon connection strings look like `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname`. Only `ep-xxx.us-east-2.aws.neon.tech` goes in the Host field. (This is the single most common failure in the forum's Neon threads.)
2. **Pooled vs direct.** Neon gives you two hostnames; the pooled one routes through PgBouncer. If the pooled endpoint misbehaves with prepared statements, try the direct endpoint hostname.
3. **SSL mode on the credential.** For the Postgres *node* credential, **Require** is the correct mode with Neon — `prefer` can silently downgrade in some client stacks, and Disable will always fail.
4. **Password special characters.** If you pasted a connection string anywhere, URL-encode special characters in the password (`@` → `%40`, `/` → `%2F`, `#` → `%23`). In the n8n credential fields this doesn't apply, but it bites people who test with `psql` first.
5. **Don't "fix" it with Ignore SSL Issues: ON.** That toggle disables certificate verification entirely — it turns a TLS-encrypted channel into one you can't distinguish from a man-in-the-middle's. The forum thread is explicit: don't.

## Limits and things I didn't test

- I tested nothing against n8n Cloud's managed infrastructure directly; the two-leg explanation comes from the forum thread's community reproduction against the n8n 2.44.4 PostgreSQL transport and Neon's documented proxy architecture.
- If n8n changes its PostgreSQL transport's default SSL behavior in a future version, re-verify — the settings above are correct for the versions current as of October 2026.
- Self-hosted n8n talking to Neon uses the same credential, but self-hosted instances also have the `DB_POSTGRESDB_*` environment variables for n8n's *internal* database — a different thing from the workflow Postgres node covered here. Don't confuse the two.

## FAQ

### Is my data really encrypted between n8n Cloud and Neon?

Yes. Neon refuses non-TLS connections, and with SSL: Require + Ignore SSL Issues: OFF, n8n verifies Neon's certificate chain and hostname during the handshake. `ssl=false` in `pg_stat_ssl` measures the proxy-to-compute hop inside Neon's network, not your leg.

### Can I make pg_stat_ssl return true?

Not on Neon, and you shouldn't need to. TLS termination at the proxy is by design. Chasing `true` there would mean bypassing the proxy, which Neon doesn't offer.

### Should I ever turn on "Ignore SSL Issues"?

Only as a temporary diagnostic to isolate certificate problems, never as the production setting. It disables the check that proves you're talking to Neon and not an impostor.

### Does this apply to Supabase or other hosted Postgres?

The exact proxy detail is Neon-specific, but the principle generalizes: `pg_stat_ssl` always reports the connection the *database server* sees. With any proxy, pooler (PgBouncer, Supabase's pooler), or load balancer in front of Postgres, treat that view's output as describing the last hop, not your client hop.

## Key Takeaways

- `pg_stat_ssl` on Neon always shows `ssl=false` — it measures the proxy-to-compute hop inside Neon's network, not your connection.
- Neon terminates TLS at its connection proxy and refuses non-TLS connections, so leg 1 (yours) is encrypted by construction.
- With **SSL: Require** and **Ignore SSL Issues: OFF**, a successful n8n connection test *is* the verification — certificate chain and hostname are both checked.
- Verify independently with `psql "...?sslmode=verify-full"` or `openssl s_client -starttls postgres -connect HOST:5432` and look for `Verify return code: 0 (ok)`.
- Never "fix" a Postgres connection by enabling Ignore SSL Issues — it disables the check that protects you from impersonation.

Next step: if you use Neon as n8n's *internal* database too, the `DB_POSTGRESDB_SSL_CA_FILE` vs `DB_POSTGRESDB_SSL_CA` distinction on self-hosted setups is the next trap — search the community forum's SSL thread before pasting certificates into env vars.
