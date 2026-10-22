---
title: "PHP2Shell: Two Critical PHP RCEs (CVSS 9.2) Leaked a Day Early — Check Your Version and Patch Today"
description: "PHP2Shell (CVE-2026-109618 + CVE-2026-109619): unauthenticated RCE on PHP 5.4–8.5. Fixed versions, the restart trap, and a compromise hunt checklist."
date: 2026-10-22
category: news
tags: ["php", "security", "rce", "CVE", "patch", "self-hosting"]
draft: false
featured: false
image: "/og/php2shell-php-rce-patch-guide.webp"
---

Two vulnerabilities in PHP itself — not in WordPress, not in a plugin, in the interpreter — give an unauthenticated attacker remote code execution on effectively every PHP release since 5.4. The details leaked on October 20, a day before the planned disclosure, and PHP shipped an emergency out-of-cycle fix on October 21. By the end of this article you will know whether your servers are exposed, exactly which versions fix it, and how to check for signs that someone got there first.

One boundary up front: this is a defender's guide. It explains how the bugs work at the level you need to patch and hunt, links the primary sources, and contains no exploit code and no links to proof-of-concept repositories — including the fake ones, which are worse than useless (see the warning in Step 4).

## What happened: a disclosure that leaked a day early

The flaws were found and reported to the PHP security team in August 2026, and were working through a normal coordinated disclosure with a planned reveal on October 22. The timeline then broke:

- **October 20, 2026:** A Hacker News post and screenshots of a private exploit tool named "PHP2Shell" — credited to the researcher Calif — leaked the two CVE IDs and claimed the bugs hit every PHP release since 5.4.0. The post was taken down; the screenshots were already everywhere.
- **October 20, 19:33 UTC:** PHP published an advance notice of an emergency security release and moved publication up a day, to October 21 at 14:00 UTC. [watchTowr](https://watchtowr.com/intelligence/php-remote-code-execution-php2shell/) confirmed the leak was genuine and said it had reproduced both vulnerabilities.
- **October 21, 14:00 UTC:** PHP released the fixes — 8.5.12, 8.4.27, 8.3.36 and 8.2.35 — with the full advisories: [GHSA-w8hw-w9fx-j79w](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) (CVE-2026-109618) and [GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) (CVE-2026-109619). Both are rated **CVSS v4.0 9.2** by the PHP security team.
- The story is big enough that Wikimedia took its Phabricator instance offline as a precaution, and the pair already has a [Wikipedia article](https://en.wikipedia.org/wiki/PHP2Shell).

The discoverers credited across the reporting — Calif (Calif Research), Wiz, and OpenAI — and the role AI played in building the exploit chain are covered in the AI section below; [Check Point's write-up](https://blog.checkpoint.com/security/php2shell-what-we-know-about-the-leaked-critical-php-vulnerabilities-cve-2026-109618-cve-2026-109619/) is a good second source for the timeline. First, the bugs themselves.

## How the two bugs work, in plain language

Some terms, defined once. **RCE (remote code execution)** means an attacker runs their own code on your server, with the permissions of the web server process. A **SAPI** is the layer that connects PHP to a web server — PHP-FPM, Apache's mod_php, php-cgi, FrankenPHP and LiteSpeed are all SAPIs, and all of them are in scope here. A **worker** is one long-lived PHP process inside those servers: it handles a request, cleans up, and handles the next one, thousands of times. That reuse is the heart of the second bug.

**CVE-2026-109618 — corruption through an out-of-memory crash.** PHP sets a per-request memory limit. When a request runs out of memory mid-flight, PHP aborts it and runs cleanup. If the memory runs out at one specific moment — while PHP is still setting up the request's internal data structures — that data is only half-initialised, and the cleanup code can be made to treat the half-formed data as if it were valid. An attacker who can force memory exhaustion at the right instant (crafted multipart form submissions are one way to burn memory) corrupts the interpreter's own state, and from there reaches code execution.

**CVE-2026-109619 — stale state that outlives its request.** Some internal state belongs to a single request and lives in memory the request owns. In this bug, that state can survive after its memory has been freed, and a global pointer still refers to it. When the *next* request lands on the same worker — remember, workers are reused — it can end up using the leftover state before normal initialisation resets it. This is the classic shape of a **use-after-free**: a program uses memory after giving it back, so whatever now occupies that memory is treated as something it is not. One confirmed path runs through **Session Upload Progress**, a default-on feature (`session.upload_progress.enabled`) that tracks file-upload progress in the session; PHP is explicit that other variants exist.

<figure class="shot">
  <img src="/figures/php2shell-php-rce-patch-guide-stale-state.svg" alt="Isometric bench rig of CVE-2026-109619: one PHP worker drawn as a press, request 1's part left standing in the memory tray in orange, the freed tray hoisted away empty behind it, a pointer arm still aimed at the leftover part, and request 2 arriving on a rail carriage" loading="lazy" />
  <figcaption>One PHP worker, drawn as a bench press with the Anatomy figure kit. Request 1 machined its part and left it standing in the memory tray — the orange block. Its tray was then freed and hoisted clear, empty, but the pointer arm never let go of the part. <strong>Notice:</strong> the press does not care that the part's owner is gone. When request 2 rides in on the carriage, the press works on whatever that pointer still finds — one request's leftover state, consumed by another request on the same worker. That is CVE-2026-109619, and it is also why restarting workers matters forensically: restart the press and the leftover part vanishes with the worker's memory.</figcaption>
</figure>

Two properties make the pair dangerous together. Neither needs a login, a valid session, or any application bug — Wiz demonstrated unauthenticated RCE against current WordPress, Drupal and Joomla images, and notes that even a "Hello World" script is enough surface. And on **mod_php**, PHP rates the risk highest: the attack can succeed *before any application code runs*, so application-level firewalls and plugin security tools may never see a request they can judge.

## Who is affected

Every PHP release from **5.4.0 through the versions below** is affected by at least one of the two flaws. Fixes exist only for supported branches:

| PHP branch | Status | Fixed version (released Oct 21, 2026) |
|---|---|---|
| 8.5.x | Supported | **8.5.12** |
| 8.4.x | Supported | **8.4.27** |
| 8.3.x | Supported | **8.3.36** |
| 8.2.x | Supported | **8.2.35** |
| 8.1.x and older | End of life | **No official PHP fix** — upgrade branches, or apply a vendor/distro backport (the PHP team also published minimal source backports for 7.4, 8.0 and 8.1 for source builders) |

SAPIs in scope: PHP-FPM, Apache mod_php (highest risk), php-cgi, FrankenPHP, LiteSpeed — in other words, if the PHP build serves web requests, it counts. CLI-only installs that never serve web traffic are not the concern; the forgotten PHP inside a container, a control panel, or a vendor appliance is.

## What to do now

### Step 1 - Find every PHP build you run

Servers accumulate PHP: the distro package, a second version for one legacy app, copies inside Docker images, a control panel's private build. Inventory all of them before patching any of them:

```bash
which -a php php-fpm php-cgi
ls /usr/bin/php* /usr/sbin/php-fpm* /usr/local/bin/php* 2>/dev/null
php -v
docker ps --format '{{.Image}}' | sort -u
```

`which -a` matters because it lists *every* PHP on the PATH, not just the default; the `ls` catches versioned binaries like `php8.1` that nothing points to any more; and the Docker line reminds you that containers carry their own PHP that host patching never touches. Record the version of each build — that list is your patch checklist.

### Step 2 - Patch to the fixed version, then restart the service

Install the fixed release for your branch from [php.net](https://www.php.net/downloads.php) or your distribution (distros and LTS vendors received the patches and several have shipped backports — check your vendor before assuming an old branch is stranded). Then the step people miss:

```bash
sudo systemctl restart php8.3-fpm        # adjust to your branch and SAPI
# Apache mod_php instead:  sudo systemctl restart apache2
php -v                                    # confirm the fixed version number
```

> **Warning:** Updating the PHP package on disk does **not** update the code already running. FPM and Apache workers are long-lived processes holding the old interpreter in memory; until you restart the service (or the workers recycle), you are still vulnerable — "patched" on disk, exploitable in production. Verify with `php -v` *and* by confirming the service actually restarted, and remember containers need rebuilt images, not package updates inside a running container.

### Step 3 - If you are on PHP 8.1 or older, make the EOL decision today

There is no official fix coming for end-of-life branches. Your real options are: upgrade to 8.2+ (test first — most 8.1 code runs on 8.2/8.3 with few changes), apply your distribution or LTS vendor's backport, or build from source with the PHP team's minimal backports for 7.4/8.0/8.1. "Wait and see" is not on the list: Sansec publicly expected mass scanning within minutes of the fixed release, because a patch is also a map — diffing it shows attackers exactly where the bugs live.

### Step 4 - Hunt for compromise, evidence first

Patching closes the door; it does not tell you whether someone already walked through it. Before you restart anything, read this warning — it changes the order of operations:

> **Warning:** If you find pre-exploit indicators on an unpatched host, preserve the forensic state *before* patching and restarting. CVE-2026-109619 lives in worker memory, and restarting the workers destroys that state. Snapshot the machine or capture logs and process state first, then patch.

Indicators defenders are hunting for (compiled from watchTowr, Check Point and Sansec reporting):

- Multipart POSTs carrying a `PHP_SESSION_UPLOAD_PROGRESS` field, and large or malformed multipart POSTs generally
- Repeated `Allowed memory size exhausted` fatals and request timeouts in PHP logs — the OOM bug leaves these behind
- FPM/Apache worker segfaults or bursts of worker crashes and respawns
- Unexpected files in the session save path, and new or modified `.php` files under web roots
- Changes to `auto_prepend_file` / `auto_append_file` in any `php.ini`
- Web server processes spawning `sh`, `bash`, `curl`, `wget`, `nc` or `base64`; new cron jobs, systemd units, users or `authorized_keys` entries

Starter commands for the log and file checks:

```bash
grep -h "PHP_SESSION_UPLOAD_PROGRESS" /var/log/nginx/access.log /var/log/apache2/access.log 2>/dev/null | tail -20
grep -hi "Allowed memory size" /var/log/php*.log 2>/dev/null | tail -20
find /var/www -name "*.php" -newermt "2026-10-19" -print 2>/dev/null
grep -rn "auto_prepend_file\|auto_append_file" /etc/php/ --include="*.ini" 2>/dev/null
```

Treat hits as triage, not verdicts: a `.php` file modified on October 20 might be your own deploy. What you are looking for is *correlation* — upload-progress probes plus memory fatals plus a new file is a very different picture than any one of them alone.

Two defender tools help. OpenAI published a [PHP2Shell checker on GitHub](https://github.com/openai/php2shell-checker): two Codex skills — one checks a site by public URL, one runs on the server — that compare the detected PHP version against the fixed thresholds. It does not exploit anything; it is a version screen, and a site that hides its version header will come back "unknown." For hosts that cannot patch immediately, Syhunt's [php2shell-protection toolkit](https://github.com/syhunt/php2shell-protection) collects emergency Apache mitigations (multipart blocking, request-size limits) — a stopgap with real breakage costs, not a fix.

> **Warning:** Do not download or run "php2shell.py" proof-of-concept files circulating on GitHub. Per JFrog's reporting, fake PoC repositories from unknown accounts are distributing malware. You do not need an exploit to check your exposure — the version number is the check.

And on workarounds, be clear-eyed: disabling `session.upload_progress.enabled` blocks at most one confirmed path of one bug, blocking multipart POSTs breaks every upload form you have and does nothing for the OOM bug, and the PHP core team's position is that **patching is the only real mitigation**. Cloudflare customers got WAF rules (its CTO said early attack attempts were observed before the patch shipped); everyone else has the checklist above.

## The AI angle: discovery and defence, compressed into the same week

The reporting credits the discovery to Calif, Wiz and OpenAI, and both ReliaQuest and watchTowr describe frontier AI models compressing the exploit-development side of the work — turning a memory-corruption chain that would normally take a specialist far longer into roughly **one week** of work. Hold that number at arm's length (it comes from the firms reporting the incident, not from a published methodology), but the direction is hard to argue with: a pair of bugs this subtle — an OOM that has to land mid-initialisation, a stale pointer that needs a second request on the same worker — was found, chained and weaponised fast enough to force an emergency release for a language that runs a large share of the web.

The same week produced the mirror image: OpenAI's checker is itself two AI skills, built to let any site owner ask "am I exposed?" in plain language. Offence got a tool; defence got a tool. What neither got is more *time* — the leak removed the one-day buffer the coordinated disclosure had planned, and the patch-to-mass-scanning window is now measured in minutes. The practical conclusion for anyone running infrastructure: your patch pipeline's speed is now a security control in its own right, because the other side's pipeline just got faster.

## What we don't know yet

Honesty about the gaps, because they are real. **The exploitation reports conflict:** Cloudflare's CTO said early attack attempts were observed before the patch and that Cloudflare deployed WAF rules against them, while Huntress and watchTowr initially reported no observed exploitation. Both can be true (different vantage points, different definitions of "attempt"), and the picture will sharpen over the coming days. **Version checkers are screening, not proof:** they read a version number, which a backported distro package can make misleading in either direction. And the full technical root-cause write-ups were still landing as this article was published — if a detail here conflicts with the PHP advisories, the [advisories](https://github.com/php/php-src/security/advisories) win.

## Key Takeaways

1. **PHP2Shell is two unauthenticated RCEs in PHP itself** (CVE-2026-109618 via OOM corruption, CVE-2026-109619 via stale state), CVSS 9.2, affecting PHP 5.4 through 8.5 across FPM, mod_php, php-cgi, FrankenPHP and LiteSpeed.
2. **Patch to 8.5.12, 8.4.27, 8.3.36 or 8.2.35 — and restart the service.** An updated binary with un-restarted workers is still vulnerable.
3. **PHP 8.1 and older get no official fix.** Upgrade branches or apply a vendor backport; do not wait.
4. **Hunt before you restart if you see indicators** — multipart upload-progress probes, memory-exhaustion fatals, worker crashes, new `.php` files — because the stale-state evidence dies with the worker process.
5. **There is no reliable workaround**, and the circulating "PoC" files are malware bait. The version number is your test.

Next step: run the Step 1 inventory on every host you own today, compare each version against the table, and schedule the restart in the same sitting — an inventory without a patch window is just a list of targets.
