---
title: "Fix n8n Email Trigger (IMAP) 'Cannot Connect' to NetEase 163.com / 126.com Mailboxes"
description: "n8n can't connect to a 163.com, 126.com or 188.com mailbox? NetEase rejects mailbox passwords — use the 16-char authorization code instead."
date: 2026-11-08
category: automation
tags: ["n8n", "imap", "email", "error-fix", "netease"]
draft: false
featured: false
image: "/og/fix-n8n-email-trigger-netease-imap-connection.webp"
---

Your n8n Email Trigger (IMAP) refuses to connect to a NetEase mailbox — `163.com`, `126.com`, `yeah.net` or `188.com` — and the credential test fails with an authentication error. The password is correct: you just used it to sign in on the web. The trigger, meanwhile, will not even get past login. This is a provider-side trap, not an n8n bug, and it is reported as a team-assigned issue on n8n's tracker ([n8n-io/n8n#40283](https://github.com/n8n-io/n8n/issues/40283), October 2026).

Quick definitions before we start: **NetEase Mail** is the free email service behind the `163.com`, `126.com`, `yeah.net` and `188.com` domains, all running on NetEase's Coremail platform. A **client authorization code** (客户端授权码) is a separate 16-character password NetEase issues for third-party mail clients — it replaces your mailbox password in every app that is not NetEase's own. **IMAP** is the protocol n8n's Email Trigger uses to read mail; port **993** is its SSL/TLS port.

By the end of this article you will know the four real reasons the connection fails, the exact settings for each NetEase domain, and how to prove the fix worked — in about ten minutes.

**Prerequisites:** an n8n instance (Cloud or self-hosted, any 2.x version as of November 2026), a NetEase mailbox, and the phone number bound to that mailbox — you need it for an SMS verification step.

> **Note:** this article is about *connecting at all*. If your credential test passes but new mail never triggers the workflow, that is a different failure — the silently-dead trigger — covered in [Fix n8n Email Trigger (IMAP) Not Firing on New Emails](/blog/fix-n8n-imap-trigger-not-firing/).

## The symptom: what the failure actually looks like

The failure has a consistent fingerprint:

1. **The credential test fails** — n8n reports it cannot connect, or returns `535 Authentication failed`, even though the same email address and password sign in fine at `mail.163.com` or `mail.126.com`.
2. **Every password retry fails identically.** Changing the password on the web and pasting the new one into n8n changes nothing — because the mailbox password is not what NetEase wants here.
3. **A 126.com address fails even with the "right" settings** copied from a 163.com guide. Pointing a 126 address at the 163 hostnames fails as an authentication error rather than a routing one, which sends people back to regenerating a code that was never wrong.

**How to confirm in one minute:** open the IMAP credential in n8n and click the connection test. If it fails while webmail login works, you have a NetEase client-access problem, not a typo. Do not keep retyping the password — it will never work.

## Root cause 1: NetEase refuses mailbox passwords from third-party clients

This is the cause in most cases, and it is the one the error message hides. NetEase does not accept your mailbox password from any outside program — n8n, Outlook, Thunderbird, anything. Third-party clients must sign in with a specially generated **16-character client authorization code**, and using the real password returns `535 Authentication failed` every single time.

The code is issued when you enable the IMAP/SMTP service (root cause 2 below), and it is shown exactly once. If you never saw a code, you never completed the switch — that is the tell.

## Root cause 2: IMAP/SMTP service is disabled by default

NetEase keeps client access off until you manually switch it on. The IMAP/SMTP service and the POP3/SMTP service are separate switches, so turning on one leaves the other off — and until the IMAP switch is on, the server refuses every login, whatever password or code you send. Enabling it requires an SMS verification to the phone number bound to the mailbox.

## Root cause 3: the wrong host for your domain

The four NetEase domains share the Coremail platform but live on different servers. A `126.com` address pointed at `imap.163.com` fails with an authentication error, not a "wrong server" error — so the real problem looks like a bad password. Some guides recommend using `imap.163.com` uniformly for all NetEase domains, and that does work for many setups, but the domain-matched host is the reliable default: if the uniform host fails, the matched host is the first thing to try, not the fifth.

## Root cause 4: NetEase refuses clients that don't identify themselves ("Unsafe Login")

NetEase requires the connecting client to identify itself with the IMAP `ID` command before it authenticates, and refuses anonymous clients with an `Unsafe Login` message that has nothing to do with your credentials. If you see that exact phrase, your password and code are fine — the client handshake is the problem. This one is rarer with n8n than the first three, but it is the correct diagnosis when the code is right, the service is on, the host is right, and the connection still fails.

## The exact NetEase settings

Use this table when filling in the n8n IMAP credential. **User** is always your full email address, never just the part before the `@`. **Password** is always the 16-character client authorization code, never the mailbox password.

| Domain | IMAP host | IMAP port | SMTP host | SMTP port |
|---|---|---|---|---|
| `163.com` | `imap.163.com` | 993 (SSL/TLS) | `smtp.163.com` | 465 (SSL/TLS) |
| `126.com` | `imap.126.com` | 993 (SSL/TLS) | `smtp.126.com` | 465 (SSL/TLS) |
| `yeah.net` | `imap.yeah.net` | 993 (SSL/TLS) | `smtp.yeah.net` | 465 (SSL/TLS) |
| `188.com` | `imap.163.com` | 993 (SSL/TLS) | `smtp.163.com` | 465 (SSL/TLS) |

## The 4 fixes, in order

### Fix 1 — Enable the IMAP/SMTP service and generate the authorization code

This is the fix for root causes 1 and 2, and it solves the large majority of cases. Do it in the browser, not in n8n.

1. Sign in to webmail at the matching domain — `mail.163.com` for a 163 address, `mail.126.com` for a 126 address. Signing in at the wrong domain's webmail is a common stumble.
2. Open **Settings** (设置), then choose **POP3/SMTP/IMAP**.
3. Switch the **IMAP/SMTP Service** on. NetEase will offer its own 邮箱大师 client first; carry on past it.
4. Complete the SMS verification: NetEase shows a QR code that composes a verification SMS on your phone, with a manual-send fallback underneath. Send the message exactly as prompted, wait a moment, then confirm you have sent it.
5. The **16-character client authorization code appears once and is never shown again.** Copy it immediately into a password manager. If you close the popup without copying it, you can only regenerate a new code on the same settings page — the old one is gone.

> **Warning:** the code is tied to the service being on. If you later change your mailbox password or switch the IMAP service off and on again, the old code stops working and you must generate a fresh one — then re-save the credential in n8n (Fix 3).

### Fix 2 — Use the domain-matched host in the n8n credential

In n8n, open the IMAP credential used by the Email Trigger and set it from the table above:

- **Host:** the IMAP host for your domain — `imap.126.com` for a `126.com` address, `imap.163.com` for `163.com` and `188.com`, `imap.yeah.net` for `yeah.net`.
- **Port:** `993`.
- **SSL/TLS:** on (implicit TLS — port 993 is the SSL port, not STARTTLS on 143).
- **User:** your full email address, e.g. `you@126.com`.
- **Password:** the 16-character authorization code from Fix 1.

If the domain-matched host fails and you are confident the code is right, try the uniform host `imap.163.com` as a second attempt — some NetEase accounts route through it. But try the matched host first: a failure against the wrong host looks exactly like a bad password, and that misreading is what costs people an afternoon.

### Fix 3 — Re-save the credential and re-activate the workflow

After changing any of the above, re-enter the authorization code in the credential and save it — n8n can hold a stale copy after a failed test. Then deactivate and re-activate the workflow so the trigger picks up the fresh credential, and run the credential test. You should see `Connection successful`.

If the test still fails at this point, check the two silent invalidators: did you change the mailbox password after generating the code (that kills the code — regenerate it), and did you paste the code with a trailing space or line break (the code is exactly 16 characters; anything extra fails authentication).

### Fix 4 — Isolate the client handshake ("Unsafe Login") with a desktop mail app

If Fixes 1–3 are all verified and the connection still fails — especially with an `Unsafe Login` message — the problem is the client handshake, not your settings. Prove it by testing the same mailbox in Thunderbird or Apple Mail with the same host, port, and authorization code:

- **Desktop app connects, n8n doesn't:** the issue is specific to how n8n's IMAP client introduces itself. As a workaround, use the **Read Email (IMAP)** action node on a Schedule Trigger instead of the Email Trigger (IMAP) node — the action node opens a fresh connection per run rather than holding a persistent IDLE session, which sidesteps the handshake problem entirely. Poll every 5–10 minutes; that delay is the price of the workaround.
- **Desktop app fails too:** the problem is still on the NetEase side. Re-check that the IMAP/SMTP switch is actually on (it can silently revert if the SMS verification was not completed) and regenerate the authorization code.

## Verify it worked

Send a brand-new email to the NetEase mailbox from another account, leave it unread, and watch the Executions tab. A working trigger fires within seconds on the IDLE push path. Then check the execution's output: the email should appear exactly once, with the sender and subject intact.

If executions appear but arrive minutes late instead of instantly, that points at a dead IDLE connection rather than a NetEase problem — enable **Force Reconnect Every Minutes: 5** in the trigger node's options, as covered in the [IMAP trigger not-firing guide](/blog/fix-n8n-imap-trigger-not-firing/).

## Prevent it next time

- **Store the authorization code in a password manager the day you generate it.** It is shown once; losing it means regenerating and updating every client that uses it.
- **Never paste your mailbox password into n8n for a NetEase account.** If a teammate sets up a second workflow, hand them the authorization code, not the password — a leaked code can be revoked without touching the account.
- **After any mailbox password change, regenerate the code first, then update n8n.** Password changes invalidate the code silently, and the next failure will look like n8n broke for no reason.
- **Pin the host per domain in your own runbook.** The `163.com`-for-everything shortcut works until it doesn't; the table above is the version that survives a 2 AM incident.

## FAQ

### Does this also fix sending mail from n8n to a NetEase mailbox?

The same two rules apply to SMTP: enable the service and use the authorization code as the password, with `smtp.163.com` (or `smtp.126.com` for 126 addresses) on port 465 with SSL/TLS. A `535 Authentication failed` on send is the same cause as on receive.

### I generated the code but n8n still says authentication failed. What now?

Work the list in order: the code is exactly 16 characters with no trailing space; the IMAP/SMTP switch is still on; you are using the host for your domain (`imap.126.com` for 126, not `imap.163.com`); and you did not change the mailbox password after generating the code. If all four check out, run the Fix 4 desktop-app isolation test.

### Is this an n8n bug that will be fixed in a release?

No — the password rejection and the disabled-by-default service are NetEase's documented behavior for all third-party clients, not n8n-specific. The n8n tracker entry ([n8n-io/n8n#40283](https://github.com/n8n-io/n8n/issues/40283)) is team-assigned because users keep hitting it, but the fix lives in the mailbox settings, not in an n8n update. No n8n upgrade will make your mailbox password work.

### What about Gmail, Outlook, or QQ Mail in the same trigger?

Different providers, different traps. Gmail needs an app password with 2-Step Verification on; QQ Mail has its own authorization-code flow similar to NetEase's. The diagnostic pattern is the same — credential test fails while webmail works means the provider wants a client-specific password — but the settings and steps are provider-specific.

## Key Takeaways

1. **NetEase never accepts your mailbox password in n8n** — third-party clients must use the 16-character client authorization code, or every login returns `535 Authentication failed`.
2. **Enable IMAP/SMTP in Settings → POP3/SMTP/IMAP first**, with SMS verification; the service is off by default and the code is shown exactly once.
3. **Use the host for your domain** — `imap.126.com` for 126 addresses, `imap.163.com` for 163 and 188 — because the wrong host fails as an auth error and misleads you into regenerating a good code.
4. **Regenerate the code after any mailbox password change**, and re-save the n8n credential — the old code dies silently.
5. **If the credential test passes but mail never triggers**, you have the other IMAP bug — see [Fix n8n Email Trigger (IMAP) Not Firing on New Emails](/blog/fix-n8n-imap-trigger-not-firing/).

Next: if your trigger now connects but fires late or stops after a few days, the [IMAP trigger not-firing guide](/blog/fix-n8n-imap-trigger-not-firing/) covers the dead-IDLE and UID-watermark fixes. If you run several mail-driven workflows, the [silent-failures checklist](/blog/n8n-self-hosted-silent-failures-checklist/) shows how to add a heartbeat so a dead trigger pages you instead of failing quietly.
