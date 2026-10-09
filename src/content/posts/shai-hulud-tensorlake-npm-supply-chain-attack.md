---
title: "Shai-Hulud Just Infected an AI Agent Platform's npm Package — What Self-Hosted n8n Builders Must Do Now"
description: "Tensorlake's npm SDK (v0.5.144) was poisoned by the Shai-Hulud worm. The attack chain, plus a secrets checklist for n8n self-hosters."
date: 2026-10-09
category: news
tags: ["n8n", "supply chain", "security", "npm", "AI agents"]
draft: false
featured: false
image: "/og/shai-hulud-tensorlake-npm-supply-chain-attack.webp"
---

On October 8, 2026, the npm package `tensorlake` — the TypeScript SDK for Tensorlake's AI agent infrastructure — was compromised by a new Shai-Hulud worm variant. Version 0.5.144 shipped a preinstall hook that stole npm tokens, GitHub tokens, AWS keys, SSH keys, `.env` files, crypto wallets, and browser passwords from every machine that installed it. The version was pulled within minutes, but the malware persists on infected hosts.

If you self-host n8n, this is your threat model: you live on npm. Every community node you install, every Docker rebuild that runs `npm install`, every `npx` in your CI pipeline runs install scripts. This article walks through exactly how this attack worked — and the concrete checklist that keeps your secrets out of the next one.

## The attack chain: verified commits to poisoned publish in 20 hours

According to Aikido's analysis, the infection didn't start with a typo-squatted package. It started inside the legitimate `tensorlake` GitHub repository. On October 7, the threat actor made verified commits under the identity of a maintainer — the malware was introduced in commit `41b38f0` via direct file upload, and the actor then bumped the version to trigger a publish. The repository was compromised for roughly 20 hours before version 0.5.144 went live on npm.

**Your dependency can be poisoned at the source, not just by a lookalike name.** The registry did everything "right" — the package was real, the version was real, the publisher identity was stolen at the repo level.

Timeline, per Socket (who flagged the malicious release 11 minutes after it published, at 01:23:10 UTC on October 8):

1. **01:12:07 UTC, Oct 8** — `tensorlake@0.5.144` published to npm.
2. **01:23:10 UTC** — Socket's scanner flags it; researchers confirm a ChainDrop/Shai-Hulud payload.
3. Shortly after — version 0.5.144 is removed from the registry. Clean versions remain, but damage is already done on any host that ran `npm install` in between.

With ~12,000 weekly downloads and 1k+ GitHub stars, the package's reach is far from trivial — even a minutes-long window can hit CI pipelines that install the latest version on every run.

![A hooded figure typing at a laptop with data streams on screen — illustrating the threat actor behind the Tensorlake npm compromise](/images/shai-hulud-tensorlake-npm-supply-chain-attack/hacker-laptop.jpeg)
*A compromised package doesn't attack your server — it attacks the developer machine that installs it.*

## What the malware actually does: preinstall is the whole game

The poisoned release carried an npm `preinstall` hook — a script that runs automatically the moment you install the package, before your code ever touches it. Here's the chain:

- `preinstall` launches `package/lib/setup.mjs`, an obfuscated loader.
- The loader installs the **Bun** runtime and uses it to execute `package/lib/Math_Symbol.js` — the main credential-stealing, self-propagating worm.
- The stealer harvests credentials from local files, CI environments, Kubernetes configs, and Vault sources, then drops the **HackBrowserData** binary to extract browser-stored credentials too.
- It exfiltrates everything, establishes persistence on the host, and opens a channel for remotely supplied code execution — with C2 coordinated through an Ethereum contract and GitHub as a fallback.

The stolen-data list reads like an inventory of a working developer's life: npm tokens, GitHub tokens, AWS credentials and secrets, HashiCorp Vault data, Kubernetes credentials, SSH keys, `.env` files, crypto wallets, browser passwords, Anthropic Claude config files, and messaging app data. This variant also targets 14 cryptocurrency browser extensions specifically — Aikido notes this suggests an operator more focused on quickly monetizing infected developer endpoints than on further supply-chain propagation.

The nasty part Socket warns about: **persistence can survive removing the dependency**. And per The Register's reporting, this variant monitors certain stolen GitHub tokens — if one is revoked, the malware can trigger deletion of the infected user's home directory under specific conditions. That means the cleanup order matters: disable the malicious token monitor *before* you revoke credentials, or the attacker burns the machine out of spite.

## Why n8n self-hosters are squarely in the blast radius

Most self-hosted n8n setups depend on npm in at least one of these ways:

- **npm-installed n8n itself** (`npm install -g n8n`) — every update executes install scripts as your user.
- **Community nodes** — installed via npm from the editor; [n8n 3.0 is already disabling unverified community nodes](/blog/n8n-3-unverified-community-nodes/) because this vector is that serious.
- **Custom Docker builds** — `RUN npm install` during image build runs preinstall hooks inside your build environment, which often holds registry credentials.
- **CI pipelines** — a nightly `npm install` pulling `latest` is exactly the shape of install that caught the malicious Tensorlake window.

The deeper problem: a workflow automation server is a secrets concentration point. Your n8n host holds API keys for OpenAI, Stripe, your database, your CRM — the exact kind of material this worm was built to harvest. An infected build machine doesn't just compromise one account; it compromises the keys that run your business.

![Rows of server racks in a data center — where self-hosted automation servers concentrate the secrets attackers want](/images/shai-hulud-tensorlake-npm-supply-chain-attack/data-center.jpeg)
*A self-hosted automation server is a secrets concentration point — exactly what this worm hunts.*

## The checklist: what to do today

This is a how-to embedded in the news, because the next Shai-Hulud wave will use the same shape.

### 1. Check whether you installed 0.5.144

Search your lockfiles and install history:

```bash
grep -r "tensorlake" package-lock.json yarn.lock pnpm-lock.yaml 2>/dev/null
npm ls tensorlake 2>/dev/null
```

If the answer is yes: **do not just uninstall.** Uninstalling removes the package but not the persistence. Socket's guidance: rebuild the affected system from a trusted source *before* restoring access to secrets, and rotate every credential the machine could see — then revoke. And per researcher warnings, neutralize the token monitor before revoking affected tokens.

### 2. Stop running npm install scripts by default

Most install scripts are conveniences, not necessities. Disable them:

```bash
npm config set ignore-scripts true
```

Why it works: preinstall/preinstall hooks — the exact mechanism this worm used — simply never execute. If a package genuinely needs its build step (rare for apps), allow it explicitly per-package. In Docker builds, this one line removes the install-time attack surface from every image you build.

### 3. Pin versions and audit the diff

Floating ranges (`^0.5.144`) in a CI pipeline that runs nightly is how a 20-hour malicious window becomes your incident. Pin exact versions, commit the lockfile, and make dependency updates a deliberate, reviewable PR — not an automatic pull. n8n's own 3.0 guidance on unverified community nodes points the same direction: treat every installed package as a trust decision.

### 4. Isolate where you install

Run `npm install` in throwaway CI runners or containers with no long-lived credentials mounted — never on the machine that holds your production secrets. If your n8n host and your build machine are the same box, that is the single biggest structural fix available to you.

### 5. Scan before you trust

Socket flagged this release in 11 minutes. Tools like Socket's scanner or Aikido's Safe Chain intercept `npm`/`npx` installs and check packages against malware intel before they run. One of them on your CI is cheap insurance against the next wave — the August keyv/flat-cache compromise used the same ChainDrop family, and the pattern is clearly not done.

## Where this pattern is heading

Shai-Hulud has evolved from generic npm typosquatting into a purpose-built AI-infrastructure hunter. The Tensorlake compromise is the first public case of the worm jumping to an AI agent platform — and the operator's pivot toward crypto wallets and browser stores suggests these campaigns are being run as profitable criminal operations, not one-off stunts.

For agent builders, the takeaway is structural: **your automation stack's security is the union of every dependency's security.** The AI Agent node you configured perfectly means nothing if the install script that delivered your community node ran `setup.mjs` first. Secrets hygiene, install isolation, and script-disabled installs are the cheapest defenses you have — adopt them before you need them.

## Key Takeaways

1. **`tensorlake@0.5.144` was poisoned on Oct 8, 2026** — preinstall hook → obfuscated loader → Bun-executed worm stealing npm/GitHub/AWS/Vault/SSH/crypto credentials and browser passwords.
2. **The repo itself was compromised** — verified commits under a stolen maintainer identity, 20 hours before publish. Lockfile pinning plus malware scanning beat trust in upstream.
3. **Persistence survives uninstall** — rebuild from a trusted source, rotate everything, and neutralize the token monitor *before* revoking tokens.
4. **Kill the install-script vector now** — `npm config set ignore-scripts true`, pin exact versions, and never `npm install` on the machine that holds your production secrets.
5. **n8n self-hosters are high-value targets** — community nodes, npm installs, and CI builds are exactly the surfaces this worm family hunts.

Next: run the `grep` in step 1 across your projects today — and if any lockfile shows 0.5.144, treat it as an active incident, not a cleanup task.

## FAQ

### Was I affected if I never installed the tensorlake package?

No. The malicious code only ran on machines that installed `tensorlake@0.5.144` during the window before it was removed from npm. If you never had it in a lockfile or install log, you're not affected by this specific incident — but the hardening steps above protect you from the next one.

### Why is preinstall so dangerous compared to a normal compromised package?

A normal compromised package only runs when *you* execute its code. A `preinstall` hook runs automatically during `npm install`, with your user's permissions, on the machine doing the install — which often holds CI secrets, AWS keys, and SSH credentials. You get infected without ever importing the library.

### Does using Docker protect me from this class of attack?

Partially. Docker isolates the *running* workflow from the host, but `RUN npm install` in your Dockerfile still executes preinstall hooks during the build — and build environments often carry registry credentials. The fix is `npm config set ignore-scripts true` in your Dockerfiles plus multi-stage builds that don't leak build-time secrets.

### How fast was this caught?

Socket flagged `tensorlake@0.5.144` at 01:23:10 UTC on October 8, 2026 — roughly 11 minutes after publication. The version was then removed from the npm registry. Speed of detection doesn't help hosts that installed during the window, which is why scanning must happen *before* install.

*Images: Pexels*

[Sources: [Socket](https://socket.dev/blog/tensorlake-compromise), [Aikido](https://www.aikido.dev/blog/tensorlake-npm-package-compromised), [The Hacker News](https://thehackernews.com/2026/10/tensorlake-npm-package-compromised-to.html), [The Register](https://www.theregister.com/security/2026/10/08/shai-hulud-worm-makes-jump-to-ai-infrastructure-with-tensorlake-compromise/5302054)]
