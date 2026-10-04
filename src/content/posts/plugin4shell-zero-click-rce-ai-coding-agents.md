---
title: "Plugin4Shell: 'Pinned to a SHA' Was a Lie Your Coding Agent Told You"
description: "Plugin4Shell turned SHA-pinned plugins into zero-click RCE across Claude Code, Codex, Copilot, and Gemini CLI. The git trick, patch scoreboard, and the fix."
date: 2026-10-05
category: news
tags: ["ai-agents", "security", "claude-code", "supply-chain", "git", "coding-agents"]
draft: false
featured: false
image: "/og/plugin4shell-zero-click-rce-ai-coding-agents.webp"
---

You pinned the plugin to an exact commit SHA. Forty hex characters. Immutable. That's the whole point of pinning: the code cannot change underneath you.

Except it could. And across four of the most popular AI coding agents, it did — with **zero clicks** from you.

On September 17, 2026, researchers at AIR Security (Or Nevo, Dor Granat, and Niv Hoffman) disclosed [Plugin4Shell](https://www.air.security/blog-posts/plugin4shell), what they call the first supply-chain vulnerability of the AI agent ecosystem. A flaw in how Claude Code, OpenAI Codex, GitHub Copilot, and Google Gemini CLI install SHA-pinned plugins from marketplaces let whoever controls a plugin's repository swap the already-reviewed code for malicious code — and the agent would run it while cheerfully reporting the *expected* SHA as installed. AIR found working exploits against all four agents in May 2026 and disclosed to vendors in June. By the time of publication, AIR reported that 925 hijacked skills were already in active use, reaching some 134,000 agents.

If you build with coding agents — or let them touch production systems — this one deserves your full attention. Here's the mechanism in one git quirk, the vendor scoreboard, and what actually protects you.

## What the agents did on every plugin install

Every one of the four agents followed the same reasonable-sounding procedure when installing a plugin pinned to a reviewed commit:

1. Ask Git to check out the pinned commit `a1b2c3…` (40 hex characters).
2. Report success: "installed `a1b2c3…`".
3. Run the plugin.

What they *didn't* do: verify that the working tree they just checked out **actually corresponds to that SHA**. That's the entire vulnerability. The pin was checked as a *request*, never as a *result*. "I asked for this commit" is not the same as "I am running this commit."

![Colorful close-up of syntax-highlighted source code on a screen](/images/plugin4shell-zero-click-rce-ai-coding-agents/photo1.jpg)

## The git trick: refs beat objects

Git has a reference-name ambiguity that most developers never encounter. If a repository contains a *branch* whose name is the same 40-character string as a commit hash, `git checkout a1b2c3…` can resolve to the **branch ref** instead of the **commit object**. Git prefers a ref over a commit of the same name. The tool prints the SHA it *asked for*, not the one it *got*.

So the attack, end to end, looks like this:

1. A plugin author publishes something useful and gets reviewed; a commit SHA gets pinned by the marketplace and by security-conscious teams.
2. The author (or someone who compromised the repo) creates a branch named after that exact 40-character SHA and points it at malicious code. GitHub itself rejects SHA-shaped branch names, but Bitbucket and self-hosted Git servers allow them — so the attacker just hosts the repo somewhere permissive.
3. On the next background auto-update, the agent runs `git checkout <sha>`, git resolves the branch, and attacker-controlled code lands in the working tree. The agent reports the expected SHA. Nobody sees a diff, a prompt, or a warning.
4. Gemini CLI has a sibling variant: its three-step install (`clone` / `fetch origin <sha>` / `checkout FETCH_HEAD`) can be subverted by a default branch literally named `FETCH_HEAD`.

Because Claude Code and Codex auto-update installed plugins in the background, the swap required no user interaction of any kind. Zero-click, in the most literal sense.

## The patch scoreboard (as of early October 2026)

This is the part that should bother anyone running these agents in a team:

- **Claude Code — patched.** Fixed in version 2.1.179 (Anthropic shipped the fix back in June, shortly after disclosure).
- **OpenAI Codex — patched.** Fixed in version 0.146.0, titled "Verify Git plugin SHA checkouts" — exactly the missing verification.
- **GitHub Copilot — no patch shipped.** GitHub says its host-side block on SHA-shaped branch names already prevents exploitation on its platform. That's true for GitHub-hosted repos, and Copilot is the agent with the widest enterprise footprint.
- **Google Gemini CLI — never being fixed.** Google retired Gemini CLI and pointed users at Antigravity, which doesn't SHA-pin marketplace plugins. If you're still on Gemini CLI plugins, you're exposed and there is no fix coming.

No CVE has been assigned to this flaw yet. AIR disclosed the class in June; the public write-up landed September 17.

## What you should actually do this week

**1. Update Claude Code and Codex.** This is the one-minute fix. Verify you're past 2.1.179 and 0.146.0 respectively.

**2. On Copilot and Gemini CLI, constrain where plugins come from.** Only install plugins hosted on GitHub, which refuses SHA-shaped branch names. And seriously consider migrating off Gemini CLI.

**3. Verify checkouts yourself, not just the request.** The general lesson of Plugin4Shell applies to every pinned artifact your agents install — plugins, MCP servers, skills. After any checkout, assert the result:

```bash
git rev-parse HEAD
```

If the output doesn't match the pinned SHA, the checkout landed somewhere else. A pinned artifact is only pinned if the *result* is verified. This one-line check is the fix that two vendors shipped and the concept the other two still lack.

**4. Treat plugin pinning like supply chain, not security.** The reviewed-and-pinned plugin model is still better than installing unreviewed code — but Plugin4Shell proves it's an *integrity intent*, not an integrity guarantee. Pinning works only when combined with a verified checkout, a trusted host, and reviews that include checking the actual resolved state.

![Two panes of code on a dark editor screen](/images/plugin4shell-zero-click-rce-ai-coding-agents/photo2.jpg)

## Why this matters beyond the four tools

Plugin4Shell is a template for the next five years of AI agent security problems. Every agent platform is building the same three-layer stack: a marketplace of shared skills/plugins, an installation mechanism that promises integrity (pins, hashes, signatures), and background auto-updates that make everything zero-click. AIR's own framing is blunt: *the marketplace cannot fix this class of bug — the client has to assert the tree after checkout.*

The same pattern will show up in MCP server installs, agent skill registries, and whatever the next plugin format is. Any system that says "installed version X" but only verified the *request* is vulnerable to the same swap. For n8n builders, the parallel is uncomfortably close: unverified community nodes and workflow imports are the same trust surface — review is only as good as the verification of what actually runs. (We covered n8n's own unverified-node story in our [MCP + n8n troubleshooting guide](/blog/mcp-n8n-troubleshooting/); the discipline transfers.)

One honest limitation: I haven't reproduced the exploit chain in a lab, and the "925 hijacked skills / 134,000 agents" figure is AIR's, not independently audited. The mechanism itself, however, is corroborated across The Register, Help Net Security, and independent write-ups — and OpenAI's own patch notes confirm the missing verification.

## Key Takeaways

1. **The pin was checked as a request, never as a result.** Four coding agents ran `git checkout <sha>` and never confirmed HEAD resolved to that SHA — letting a branch named after the SHA win.
2. **Background auto-update made it zero-click.** Claude Code and Codex users needed no interaction at all; the malicious swap happened silently on update.
3. **Two patched, one unpatched, one abandoned.** Claude Code 2.1.179 and Codex 0.146.0 carry full fixes. Copilot relies on GitHub's host-side block. Gemini CLI will never be fixed.
4. **Verify the checkout, not just the pin.** `git rev-parse HEAD` after every install — a pin without result-verification is an integrity intent, not a guarantee.

Next: audit every pinned plugin, MCP server, and agent skill in your own stack this week. The fix takes a minute per tool; the attack took none.

*Images: Pexels*
