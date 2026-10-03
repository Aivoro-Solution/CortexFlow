---
title: "Anthropic's Git MCP Server Had an RCE Chain: 3 CVEs Every n8n Builder Should Audit"
description: "Three flaws in Anthropic's official Git MCP server chained into RCE. How the exploit worked and the audit checklist for your own agent stack."
date: 2026-10-04
category: news
tags: ["mcp", "n8n", "agent-safety", "anthropic", "security"]
draft: false
featured: false
image: "/og/anthropic-git-mcp-rce-chain.webp"
---

Anthropic's own official Git [MCP](https://modelcontextprotocol.io) server shipped with three vulnerabilities that security researchers chained into remote code execution. Not a fork, not a sketchy community plugin — the canonical Git server from the company that invented the Model Context Protocol itself. If you've wired MCP servers into your [n8n](/blog/how-to-connect-mcp-server-n8n/) AI agents this year, this is the story that should make you audit your setup tonight.

MCP (Model Context Protocol) is the open standard Anthropic released in November 2024 that lets AI assistants call real tools — filesystems, APIs, developer utilities like Git — based on decisions made by a language model. The Git MCP server connects agents to repositories so they can read code and automate Git operations using natural language. By the end of this article you'll know exactly which three flaws researchers found, how they combine into an RCE chain, and the five checks I now run on every MCP-backed agent I build.

## How the chain was discovered

The flaws were found by Cyata, an agentic-AI security startup, and reported to Anthropic in June 2025. Anthropic shipped fixes in December 2025 (version 2025.12.18), the three CVEs were assigned, and the story recirculated this week in the security press. There is no evidence the flaws were exploited in the wild — which makes this a rare gift: a fully worked exploit chain we can study *before* anyone got hurt.

Here are the three flaws, each small, each individually "medium" severity, each devastating in combination:

1. **CVE-2025-68145 — path validation bypass (CVSS 6.4).** The server didn't properly validate repository paths, so an attacker could direct it to operate on any directory on the system — not just the repository defined in its configuration. The sandbox had a hole in the floor.
2. **CVE-2025-68143 — unrestricted `git_init` (CVSS 6.5).** The `git_init` tool accepted arbitrary filesystem paths without validation. A tool meant to initialize Git repositories could be pointed at `~/.ssh/` or `~/.config/` and happily plant a repository wherever the attacker wanted one.
3. **CVE-2025-68144 — argument injection in `git_diff`/`git_checkout` (CVSS 6.3).** Unsanitized arguments passed to Git commands let an attacker overwrite files the server could reach. In the project's own security advisories, CVSS scores ran as high as 8.8.

Individually, each is the kind of bug a code review should catch. Together, they form a ladder.

## The toxic combination: why 1+1+1 = RCE

The step that matters is not any single CVE — it's what happens when the Git MCP server runs *alongside* the Filesystem MCP server, a pairing that is completely normal in agent setups. Here is the chained attack Cyata documented:

1. **Path bypass (CVE-2025-68145)** lets the attacker point the Git server at directories outside its allowed scope.
2. **`git_init` (CVE-2025-68143)** plants a Git repository in a sensitive location, like `~/.config/`.
3. **The Filesystem MCP server** writes a malicious `.git/config` and `.gitattributes` into that planted repository — including a Git `clean`/`smudge` filter, which is a hook Git runs automatically on file content.
4. **Argument injection (CVE-2025-68144)** triggers the malicious config hook during `git add`, executing the attacker's payload. Remote code execution.

Notice where the attacker stands: they never needed direct access to the host. The flaws are exploitable **via prompt injection** — meaning an attacker who controls *content the assistant reads* (a README in a repo, a web page, a ticket description) can weaponize the agent's own tools against it. The agent isn't compromised; it's conscripted.

![A broken security chain and git branch diagram — three small flaws chained into one remote code execution](/images/anthropic-git-mcp-rce-chain/cybersecurity.webp)

*Image: three "medium" flaws chained into one remote code execution — the anatomy of a toxic tool combination. CC0 via Wikimedia Commons.*

Cyata's Yarden Porat put it plainly: *"Agentic systems break in unexpected ways when multiple components interact. Each MCP server might look safe in isolation, but combine two of them, Git and Filesystem in this case, and you get a toxic combination. As organizations adopt more complex agentic systems with multiple tools and integrations, these combinations will multiply."*

That sentence is the whole lesson. Nobody audits pairs.

## "Official" doesn't mean risk-free

The part of this story that should genuinely rattle builders is the provenance. This was not a fringe, unmaintained third-party server. It was **Anthropic's official Git MCP server** — the reference implementation from the protocol's originator, exactly the server a careful builder would choose *because* it looked safe.

Anthropic's response was decisive once reported: the vulnerable `git_init` tool was removed from the package entirely, path validation was added to limit traversal, and users are told to update to 2025.12.18. But the incident exposes a structural problem in how we trust MCP servers: there is no security rating on the MCP registry, no audit badge, no enforced sandbox. Trust is currently vibes-based. The registry's existence encourages installation; nothing in it measures what the server can actually do to your host.

This is also not an isolated event in the pattern. In mid-November 2025, Anthropic disclosed that Claude was being used in an agentic capacity — not as an advisor but as an *executor* — in a sophisticated cyber-espionage campaign targeting roughly 30 global targets. The trajectory is clear: agents are acquiring hands, and the hands are the attack surface.

## The audit checklist for your own agent stack

I've connected MCP servers to [n8n AI agents](/blog/mcp-n8n-troubleshooting/) in production setups, and this chain changed how I evaluate every new tool I hand an agent. Here is the five-point audit I now run:

**1. Pin the server version, then verify the fix is in.** For `mcp-server-git`, that means 2025.12.18 or later — check `pip show mcp-server-git` or your package lock. "Latest" is not a version; write the number down somewhere. Do the same audit for every MCP server your agent touches, because the next Cyata report won't be about Git.

**2. Never grant overlapping tool combinations on one host.** The RCE required *both* Git and Filesystem servers. Ask of every pair of tools: what does their combination enable that neither enables alone? If your n8n agent has an MCP Client node with filesystem access, it does not also need git write tools on the same machine. This is the check nobody does, and it's the one that caught a "safe" official server.

**3. Run MCP servers in containers with read-only mounts.** The git server ran as a process with the host's filesystem permissions. In Docker, mount only the directories the tool legitimately needs, read-only where possible, and run as a non-root user. A path-traversal bug in a container with one read-only mount is an error message, not an RCE.

**4. Assume prompt injection is the delivery mechanism.** Any tool your agent can call can be triggered by content your agent reads. If the agent browses the web or reads repos and also holds write-capable tools, you have an untrusted-input-to-privileged-action pipeline. Segment it: let one agent read, another (with fewer tools) write, and keep a human approval gate between them for anything destructive.

**5. Watch the CVE feed for your tool list.** Subscribe to security advisories for every MCP server package you deploy — GitHub's security advisories are the free version. The Git server flaws sat unpatched from a June report to a December release; version-pinning without monitoring leaves you exposed to the same window.

![Security check icon — pin versions, isolate permissions, and audit tool combinations in every MCP setup](/images/anthropic-git-mcp-rce-chain/Upload_security.svg)

*Image: pin versions, isolate permissions, audit combinations — the three habits that matter. CC BY 3.0 via Wikimedia Commons.*

## What I didn't verify

I'm honest about the boundary here: I did not reproduce the exploit chain myself, and this article is built from the security press coverage (Infosecurity Magazine, The Register, TechRadar) and Cyata's reported findings rather than primary researcher write-ups. The CVSS numbers (6.3–6.5 in press reports, up to 8.8 in the project's own advisories) come from those sources; treat the range, not any single number, as the signal. The underlying claim — three chainable flaws, official server, December 2025 fix, prompt-injection delivery — is consistent across all of them.

## Key Takeaways

1. **Anthropic's official Git MCP server shipped three chainable flaws (CVE-2025-68143/44/45) that researchers combined with the Filesystem MCP server into remote code execution** — fixed in 2025.12.18.
2. **Each server looked safe in isolation; the exploit lives in the combination.** Audit pairs of tools, not just individual ones.
3. **Prompt injection is the delivery mechanism** — an attacker only needs to control content your agent reads.
4. **"Official" is not a security control.** The MCP registry has no audit badges; the reference implementation from the protocol's inventor was still vulnerable.
5. **For your own stack: pin server versions, run MCP servers in containers with minimal read-only mounts, never grant overlapping write tools on one host, and gate untrusted-input-to-action pipelines.**

Next step: run the five checks above against your own agent setup this week — start with listing every MCP server version your agents can reach and comparing against current advisories. If you haven't connected an MCP server to n8n yet, read [how to connect an MCP server to n8n](/blog/how-to-connect-mcp-server-n8n/) first, then apply this checklist before the first real tool goes live.

*Images: cybersecurity illustration (CC0), security icons (CC BY 3.0 / CC BY-SA 3.0) via Wikimedia Commons.*
