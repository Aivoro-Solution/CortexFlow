---
title: "n8n Published Two CVEs in One Day: Expression Sandbox Escape (CVE-2026-86076) and Argument Injection (CVE-2026-44790)"
description: "n8n disclosed two CVEs on Oct 5, 2026: CVE-2026-86076 (CVSS 8.7, expression sandbox escape) and CVE-2026-44790 (CVSS 9.4). Patch guide for self-hosters."
date: 2026-10-06
category: news
tags: ["n8n", "security", "CVE", "AI agents", "self-hosting", "patch"]
draft: false
featured: false
image: "/og/n8n-expression-sandbox-escape-cve.webp"
---

On October 5, 2026, n8n disclosed **two security advisories in a single day** — both able to hand an attacker full control of the server your workflows and agents run on. The first, **CVE-2026-86076** (CVSS 8.7), is an expression sandbox escape: a crafted workflow expression can break out of n8n's expression compiler and execute arbitrary code in the n8n process. The second, **CVE-2026-44790** (CVSS 9.4), is an argument-injection flaw. Neither is known to be exploited yet, but both are published, so the fix versions are your move: **upgrade to n8n 1.123.76, 2.37.7, or 2.38.2** depending on your release line. This post explains what broke, whether you're exposed, and the exact steps to patch.

## CVE-2026-86076: the expression sandbox escape

n8n lets workflow builders write **expressions** — little snippets like `={{ $json.name }}` inside node parameters that get evaluated when the workflow runs. Expressions are supposed to run inside a **sandbox**, a restricted environment where they can transform data but can't touch the server, spawn processes, or call the JavaScript `Function` constructor.

CVE-2026-86076 broke that boundary. Per n8n's advisory (GHSA-hw8v-xxg5-vvvx), the expression compiler's **sanitizer** — the code that keeps expressions safe — was resolved through a dynamically-scoped `this`. An attacker could define a **class field named `__sanitize`** that rebound the sanitizer to a malicious value and reached the `Function` constructor. Once you have `Function`, you have arbitrary JavaScript execution. Game over.

The blast radius depends on where the expression runs:

- **On the backend:** any expression author could run code inside the n8n process — the same process that holds your credentials, your workflow definitions, and your execution history.
- **In the editor preview:** a member's crafted expression could execute JavaScript **in the browser session of whoever opened the workflow** — meaning a malicious teammate (or a compromised account) could attack other editors just by getting them to open a workflow.

The patch rejects reserved class-member names like `__sanitize`, closing the rebinding path.

![Abstract code on a screen — n8n workflow expressions are evaluated in a sandbox](/images/n8n-expression-sandbox-escape-cve/code-screen.jpg)

## Which n8n versions are affected

| Your line | Vulnerable | Patch to |
|---|---|---|
| n8n 2.38.x | >= 2.38.0, < 2.38.2 | **2.38.2** |
| n8n 2.0 – 2.37.x | >= 2.0.0, < 2.37.7 | **2.37.7** |
| n8n 1.x (LTS-era) | < 1.123.76 | **1.123.76** |

First published October 5, 2026; first seen in the wild as an advisory record on September 8, 2026. Per the advisory metadata: not known to be exploited, needs hands-on effort to exploit — but gives an attacker full control when it works.

> **Warning:** this hits hardest on **shared or multi-user n8n instances** — anyone who can create or edit a workflow is an "expression author." If you hand workflow-edit rights to clients, contractors, or junior team members, treat this as urgent rather than routine.

## CVE-2026-44790: argument injection, CVSS 9.4

The same-day second advisory, CVE-2026-44790 (GHSA-57g9-58c2-xjg3), is classified **CWE-88: improper neutralization of argument delimiters** — an argument-injection flaw. The published details are thinner than for CVE-2026-86076, but the metadata is unambiguous: **CVSS 9.4, critical**, published October 5, 2026, gives an attacker full control, needs hands-on effort, not known to be exploited. Track it through the [GitHub advisory](https://github.com/advisories/GHSA-57g9-58c2-xjg3) and the [NVD record](https://nvd.nist.gov/vuln/detail/CVE-2026-44790), and patch on the same upgrade window as CVE-2026-86076 — the advisory metadata notes vendor patches were already being shipped through the fixed lines above.

## How to patch your self-hosted n8n

![Server racks in a data center — the machines running your self-hosted n8n](/images/n8n-expression-sandbox-escape-cve/server-racks.jpg)

**Prerequisites:** SSH or terminal access to the host running n8n, and a recent backup. n8n's data (workflows, credentials, executions) lives in its SQLite file or Postgres database plus the `N8N_ENCRYPTION_KEY` — back up both before upgrading, because a failed upgrade without the key means locked credentials.

**Example terminology:** `<your-n8n-host>` is your server. Replace it in every command.

### Step 1 - Back up before you touch anything

Why: credential blobs are encrypted with `N8N_ENCRYPTION_KEY`; if the upgrade fails midway and you lose the data volume, the key alone won't restore your workflows.

```bash
# If n8n runs in Docker with a named volume:
docker stop n8n
docker run --rm -v n8n_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/n8n-backup-$(date +%F).tar.gz /data
docker start n8n
```

You should see `docker start n8n` report the container is running. Keep the tarball somewhere off-host. If you use Postgres externally, take your usual `pg_dump` instead.

> **Note:** if you have never exported `N8N_ENCRYPTION_KEY` to a safe place, do it now — printenv it from the running container and store it in your secrets manager. A volume backup without the key is a paperweight.

### Step 2 - Upgrade to the fixed version

Why: the patch is only in 1.123.76, 2.37.7, and 2.38.2 (or later). Match your line from the table above — don't jump lines casually, especially from 1.x to 2.x, which has breaking changes.

Docker (most self-hosted setups):

```bash
docker pull n8nio/n8n:2.38.2
docker stop n8n && docker rm n8n
docker run -d --name n8n \
  --env-file /path/to/your/n8n.env \
  -v n8n_data:/home/node/.n8n \
  -p 5678:5678 \
  n8nio/n8n:2.38.2
```

Replace the image tag with `1.123.76` or `2.37.7` if that's your line, and keep your own `--env-file`, volumes, and port mapping — the lines above are the shape, not your exact config.

npm installs:

```bash
npm update -g n8n
# then pin-check: n8n --version
```

You should see the fixed version number in the output — for example `2.38.2`.

### Step 3 - Verify the fix is live

Why: a container can restart on the old image if the pull failed or the tag was cached.

```bash
docker exec n8n n8n --version
```

You should see `2.38.2` (or `2.37.7` / `1.123.76`). Then open the n8n UI: **Settings → About** (bottom-left) should show the same version.

### Step 4 - Audit who could have written expressions

Why: the vulnerability window was open from first-seen (September 8, 2026) to your patch. If untrusted users had workflow-create or workflow-edit rights during that window, check whether they planted anything.

- Review **Users / members** in the instance: anyone with edit rights you don't fully trust should have them reviewed.
- Scan recently modified workflows for unfamiliar expressions in node parameters, especially anything referencing `__sanitize`, `constructor`, or `Function`.
- If anything looks wrong, treat it as a compromise: rotate credentials stored in n8n, check connected services for unexpected activity, and review execution logs for the affected period.

## If you can't upgrade today

n8n's advisory lists short-term mitigations — they reduce exposure but **do not fix** the flaw:

1. Restrict instance access to fully trusted users only.
2. Stop granting workflow-create or workflow-edit permissions to untrusted users.
3. Audit existing workflows for unexpected expressions in node parameters.
4. Set the environment variable `N8N_EXPRESSION_ENGINE=vm` to switch the expression engine.

Do these only as a bridge to the upgrade, not instead of it.

## Key Takeaways

1. **CVE-2026-86076 (CVSS 8.7):** a class field named `__sanitize` rebinds n8n's expression sanitizer and reaches the `Function` constructor — full code execution in the n8n process, or in another editor's browser session via workflow preview.
2. **CVE-2026-44790 (CVSS 9.4):** an argument-injection flaw disclosed the same day — thinner public detail, higher severity; patch in the same window.
3. **Fix versions: 1.123.76, 2.37.7, 2.38.2** — match your release line; back up data + `N8N_ENCRYPTION_KEY` first.
4. **Multi-user instances are the high-risk case** — anyone with workflow-edit rights is an expression author.
5. **The pattern repeats:** agent and automation control planes concentrate credentials and tool access, so classic bug classes (sandbox escapes, argument injection) keep landing there. My earlier pieces on the n8n October security update and the GitLab AI Gateway flaw are the same story from different angles.

Next: check which of your n8n members hold workflow-edit rights right now, and whether any of them shouldn't. The patch closes the hole; the permission audit closes the habit.

Images: Unsplash
