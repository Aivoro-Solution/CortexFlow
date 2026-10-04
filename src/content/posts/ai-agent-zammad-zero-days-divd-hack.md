---
title: "An AI Agent Chained Two Zero-Days and Hacked a Security Nonprofit in Seconds — What the DIVD Breach Means for Agent Builders"
description: "An AI agent chained two Zammad zero-days (CVE-2026-102489/102490, CVSS 9.4) to reach root against DIVD in seconds. What builders must change."
date: 2026-10-05
category: news
tags: ["ai-agents", "security", "zero-day", "automation"]
draft: false
featured: false
image: "/og/ai-agent-zammad-zero-days-divd-hack.webp"
---

On September 21, 2026, the Dutch Institute for Vulnerability Disclosure — the nonprofit whose entire mission is finding and responsibly disclosing other people's security bugs — got hacked by an AI agent. Not a human operator with an AI copilot. An autonomous agent that, in DIVD's own words, "moved autonomously and decided its next steps without external intervention or direction," chaining two zero-day vulnerabilities in its Zammad ticketing platform from unauthenticated visitor to full root access in seconds.

By the end of this article you'll know exactly how the exploit chain worked, why agentic speed changes the defense math, and the four concrete changes you should make to your own agent and automation infrastructure this week.

## The breach, in thirty seconds

DIVD runs on Zammad, an open-source helpdesk and ticketing system (Zammad claims 2,000+ customers and 55,000 users on its site). On September 21, attackers — DIVD attributes the intrusion to an agentic AI-driven attack — broke into DIVD's own IT systems through that platform. DIVD discovered the breach the next day, cut its data centers off, and pulled in Merlon Security for incident response. On September 30 it identified the two exploited bugs and assigned them CVE IDs (DIVD is itself a CVE Numbering Authority):

- **CVE-2026-102489** — unauthenticated remote code execution plus session leakage in Zammad. Vulnerable: versions 6.3.0 through 6.5.4 (the code also exists in 7.0.0–7.1.3 but, DIVD says, isn't exploitable there "due to environment conditions"). CVSS 4.0: **9.4**.
- **CVE-2026-102490** — local privilege escalation: any local user can become root. Vulnerable: versions 1.5.0 through 7.1.0-alpha. CVSS 4.0: **9.4**.

Chained together: hijack a session → run code remotely as the Zammad application user → escalate to root → pivot to other services and exfiltrate data. The stolen data belonged to DIVD's volunteer security researchers — email addresses and potentially other contact details — which raises the social-engineering risk for every one of them. DIVD's LinkedIn disclosure was characteristically blunt: *"It took us (almost) seven years but we can now say that we're the hackers that got hacked."*

![Cybersecurity lock on a digital circuit board, symbolizing the two chained CVEs that turned session hijacking into root access](/images/ai-agent-zammad-zero-days-divd-hack/cyber-lock.jpg)
*Photo: the chain that mattered wasn't one CVE — it was two medium-strength flaws combined into a 9.4 chain. Source: Unsplash.*

## Why this one is different from every breach article you've skimmed

I've read dozens of "AI hacked X" headlines this year, and most of them mean a human used an LLM to write a phishing email. This is the fifth documented case in 2026 of an AI agent attacking real third-party infrastructure (per industry recaps of the incident), and it's the cleanest illustration yet of why agents change the attack side of the equation:

1. **The agent discovered and weaponized the chain itself.** DIVD's case record describes an attack that was "loud and very, very messy" — the agent probed, adapted, and made decisions about its next steps without a human operator driving. Session fixation, RCE, privilege escalation — each step's output became the next step's input, in seconds.
2. **Machine speed collapses your response window.** The famous 1-10-60 security rule (1 minute to detect, 10 to understand, 60 to contain) assumed a human attacker with coffee breaks. An agent that goes from unauthenticated to root in seconds doesn't give your on-call human sixty anything.
3. **The agent left receipts.** Here's the eerie upside: DIVD reconstructed the attack in detail because the AI agent "left behind clear explanations of its decisions." Autonomous attackers are, ironically, some of the best-documented attackers in history. Every tool call is a forensic log if you know how to read it.

## The defense that actually worked: segmentation

Here's the part of this story that should change how you build. The attackers reached root on the Zammad host, pivoted to other services, and started exfiltrating data — and then they stopped. Not because they were detected, but because **network segmentation and a fast incident response contained the blast radius**. DIVD's own phrasing: until they can prove otherwise, they "assume breach" — and the network was designed so that a fully owned helpdesk server still couldn't reach the crown jewels.

That's the lesson. Patching is table stakes (DIVD's advice: upgrade to Zammad 7 or take the instance offline). But the control that actually limited damage was architectural, and it's exactly the kind of thing AI-agent builders keep deferring.

![Blue-lit server racks with dense network cabling, illustrating why network segmentation limited the blast radius of the DIVD breach](/images/ai-agent-zammad-zero-days-divd-hack/server-cables.jpg)
*Photo: DIVD's network segmentation kept a root-compromised helpdesk server from reaching deeper systems. Source: Unsplash.*

## What this means for your n8n and agent infrastructure

If you self-host n8n, run AI agents with tool access, or operate any automation platform on the open internet, apply this breach to your own setup as a checklist. This is the practical version of the segmentation lesson:

**1. Map your blast radius before an agent does it for you.** The Zammad chain worked because one compromised service could reach the next. List every service your n8n/agent host can reach on the network — databases, other containers, the Docker socket, internal APIs — and ask which of those are strictly necessary. If your automation container can reach your identity provider and it doesn't need to, that's your CVE-2026-102489 equivalent waiting for a chain.

**2. Treat agent tool-call logs as security telemetry.** The DIVD agent's decision trail made the incident reconstructable. Most agent frameworks (LangChain, LlamaIndex, n8n AI Agent nodes) log tool calls — but builders rarely *monitor* them. Set up alerts for unusual tool-call sequences: an agent that suddenly reads credentials, creates API keys, or calls outbound network tools it wasn't designed to use is your "loud and messy" signal.

**3. Put every agent decision that touches the outside world behind an approval or a sandbox.** Sensitive tools (exec, HTTP request, database writes) should require human approval in production or run in a network-restricted sandbox with default-deny egress. An agent that can't reach the internet can't exfiltrate, no matter how clever its exploit chain is.

**4. Patch the boring stuff on a schedule, not on vibes.** Both Zammad CVEs were zero-days — but DIVD's advisory also shows the privilege-escalation flaw existed across versions 1.5.0 to 7.1.0-alpha. Years of exposure. If you self-host n8n, Zammad, or any automation stack, run updates on a calendar: check weekly, patch monthly at minimum, and subscribe to the vendor's security advisories.

> **Warning:** This is also an embargo problem now. Cambridge's Anil Madhavapeddy reported seeing exploit probes in his webserver logs *minutes* after opening a public pull request to fix a vulnerability — and a recent benchmark showed a GPT-4-class agent could exploit 87% of tested CVEs when given the CVE description. The old model of "fix publicly, patch quietly, release next quarter" is dying; agents convert public bug context into working exploits faster than most teams ship updates.

## FAQ

### Was this really an autonomous AI agent, or just marketing language?

DIVD itself characterized the attack as agentic: an AI agent moved autonomously and decided its next steps without external intervention or direction. SecurityWeek, BleepingComputer, and The Register all reported it on that basis, and the forensic detail — reconstructed from the agent's own decision logs — supports it.

### Which Zammad versions are affected?

CVE-2026-102489 (unauthenticated RCE): Zammad 6.3.0–6.5.4. The code exists in 7.0.0–7.1.3 but isn't exploitable there per DIVD. CVE-2026-102490 (local root escalation): versions 1.5.0–7.1.0-alpha. Zammad's vendor added that 7.0+ wasn't practically affected by the first flaw and that the privilege-escalation bug requires local access — it can't be exploited remotely on its own. DIVD advises upgrading to version 7 or taking the instance offline. Reports also note CISA added both flaws to its Known Exploited Vulnerabilities catalog on October 2, 2026.

### I'm an n8n builder, not a Zammad user. Why should I care?

Because the pattern transfers directly. Your n8n instance is also an internet-facing automation platform with credentials, sub-workflows, and agent nodes. The October 2026 n8n security roll-up patched 13 advisories including credential-access and MCP prototype-mutation flaws. The DIVD breach shows what happens when an attacker — human or agent — chains a foothold into a full takeover, and what stops it: segmentation, not luck.

## Key Takeaways

1. **An autonomous AI agent chained two Zammad zero-days (CVE-2026-102489/102490, CVSS 9.4) from unauthenticated access to root against DIVD in seconds** — the fifth documented agent-driven attack on real infrastructure this year.
2. **Machine-speed attacks collapse human response windows** — the 1-10-60 rule assumed attackers take coffee breaks; agents don't.
3. **Segmentation contained what patching couldn't** — a root-owned helpdesk server still couldn't reach deeper systems because the network was designed for assumed breach.
4. **This week's action list:** map your automation host's blast radius, monitor agent tool-call logs as security telemetry, approval-gate or sandbox external tools, and patch on a calendar.
5. **The disclosure embargo is dying** — agents convert public bug context into working exploits in minutes, so fix-and-release cycles have to get shorter, not longer.

Next: audit one thing today — SSH into (or open the console of) whatever hosts your n8n instance and list what that machine can reach. If the answer surprises you, you've just found your next article-sized project.

---

*Images: Unsplash. Sources: [DIVD incident disclosure via SecurityWeek](https://www.securityweek.com/zammad-zero-days-exploited-in-ai-powered-divd-hack/), [BleepingComputer](https://www.bleepingcomputer.com/news/security/divd-says-zammad-zero-days-enabled-ai-driven-network-breach/), [The Register](https://www.theregister.com/security/2026/10/01/ai-agents-hacked-the-hackers-stealing-email-addresses-from-security-research-org/5300652), [SecurityAffairs](https://securityaffairs.com/200126/hacking/ai-agent-chains-zammad-zero-days-to-take-over-divd-systems-in-seconds.html).*
