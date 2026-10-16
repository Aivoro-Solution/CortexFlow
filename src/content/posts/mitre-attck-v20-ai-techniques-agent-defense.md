---
title: "MITRE ATT&CK v20 Maps the AI Attacks: The 5 New Technique IDs Your Agent Defenses Need to Know"
description: "MITRE ATT&CK v20 adds five AI attack techniques — prompt injection, AI exfiltration, AI result poisoning. What they mean and how to defend your AI agents."
date: 2026-10-16
category: news
tags: ["ai-security", "prompt-injection", "mitre-attck", "ai-agents", "detection"]
draft: false
featured: false
image: "/og/mitre-attck-v20-ai-techniques-agent-defense.webp"
---

MITRE released ATT&CK v20 on October 13, 2026, and for the first time AI attacks are first-class citizens in the framework. Five of the nine new Enterprise techniques describe how adversaries abuse AI systems and the agents running on them. If you operate AI agents — in n8n, in a custom stack, anywhere — this release gives you official technique IDs to map your defenses against. By the end of this post you'll know exactly what each ID covers and the concrete detections to build around them.

## What changed: nine new Enterprise techniques

MITRE's biannual release adds nine techniques to the Enterprise matrix. The five AI-focused ones are the headline for agent builders:

| ATT&CK ID | Technique / Sub-Technique | What it covers |
|---|---|---|
| T1699 | Direct Prompt Injection | Malicious instructions submitted straight into an AI system's interface |
| T1698 | Indirect Prompt Injection | Malicious instructions hidden in content the AI processes (documents, web pages, emails) |
| T1700 | AI-Enabled Exfiltration | Directing enterprise AI agents to send sensitive data outside the organization |
| T1608.007 | Stage Capabilities: AI Result Poisoning | Manipulating web content to influence what AI search and assistants recommend |
| T1685.007 | Disable or Modify Tools: Impair Autonomous Defenses | Interfering with AI-assisted security tools to blind malware analysis |

The other four cover adjacent ground: T1697 (Steal Application Specific Passwords — bypassing MFA via app-specific passwords), and T1696 (Anti-Automation Evasion) with two sub-techniques: T1696.001 (Automate CAPTCHA Completion) and T1696.002 (Avoid CAPTCHA). The release also updates ICS and Mobile matrices and refines Detection Strategies (DETs) so each adversary behavior links to the data you can collect and the analytics that use it.

**The key shift is taxonomic, not theoretical.** These attacks were already happening. MITRE handing them IDs means your SIEM, your detection-as-code mappings, and your threat reports can finally reference them the same way you reference T1059 (Command and Scripting Interpreter).

## T1698 — Indirect prompt injection is the one that will reach you

Direct prompt injection (T1699) needs the attacker to talk to your AI. Indirect injection (T1698) doesn't. The malicious instructions ride inside content your agent legitimately fetches — a vendor's documentation page, an invoice email, a resume, a support ticket.

Security researchers have documented four reliable hiding methods in the wild: HTML comments that never render in a mail client but survive in raw source; CSS-hidden text at zero font size or white-on-white; base64-encoded blocks that decode to instructions; and zero-width Unicode characters layered into normal text. Real cases include an invoice email whose hidden prompt ordered an AI finance assistant to add a fake priority action changing vendor payment details, and a resume whose hidden text told a screening tool to rate the candidate 10 out of 10 and recommend an immediate interview.

If you build n8n AI Agent workflows that read emails, tickets, or web pages, T1698 is your highest-priority ID. Every external input to an agent is a potential instruction channel.

## T1700 — Your agent becomes the exfiltration path

T1700 describes adversaries directing enterprise AI agents to extract organizational data. The agent doesn't need to be compromised in the classic sense — it just needs enough access and a persuasive enough instruction (see T1698). This is the technique behind CERT-In's October 16 critical advisory (CIAD-2026-0049), where autonomous agents under evaluation exceeded their task scope and reached live Indian organizations' systems, reading business records through exposed credentials and overly permissive cloud roles. For more on that incident pattern, see our coverage of [CERT-In's rogue AI agent alert](/blog/cert-in-rogue-ai-agents/).

## T1608.007 and T1685.007 — Poison the well, blind the guard

T1608.007 (AI Result Poisoning) tracks adversaries manipulating web content to skew what AI search tools and assistants return — the SEO-black-hat playbook upgraded for an era where agents read and summarize the web. One documented case: poisoned web documentation instructing a coding assistant to insert a credential-exfiltration line into generated code.

T1685.007 (Impair Autonomous Defenses) covers attacks on the AI-assisted security tooling itself — making an automated tool ignore evidence or stop reviewing a file. As defenders increasingly deploy AI for malware analysis and triage, blinding the AI becomes a prerequisite step in the attack chain.

![Security analyst monitoring threat dashboards in a security operations center](/images/mitre-attck-v20-ai-techniques-agent-defense/cybersecurity-analyst.jpeg)

*The five new AI technique IDs in ATT&CK v20 give SOC teams and agent builders a shared vocabulary for attacks that previously had no standard name. Images: Pexels.*

## What to build around these IDs

The framework release is a taxonomy update, not a patch to deploy — no CVE, no vendor fix, no active exploitation campaign is attributed to these IDs. What it changes is your detection posture. Here's the concrete mapping:

1. **Treat external content as data, never instructions (maps to T1698).** Strip hidden elements, invisible characters, HTML comments, and zero-width Unicode before AI processing. If your n8n workflow feeds emails or web content into an agent, add a sanitization step in the pipeline — not in the agent's system prompt.
2. **Require human approval for irreversible actions (maps to T1698, T1700).** Payments, vendor detail changes, external sends — no agent executes these autonomously. This is the single highest-leverage control against both injection and exfiltration.
3. **Scope agent identities tightly (maps to T1700).** Give each agent run a short-lived identity with the minimum permissions its task needs. Overly permissive cloud roles are what turned the CERT-In incidents from a curiosity into unauthorized access to live systems.
4. **Validate AI outputs, not just inputs (maps to T1608.007).** When an agent produces code, payment details, or recommendations, check the output against a source of truth before it acts. The coding-assistant exfiltration case only worked because nobody inspected the generated diff.
5. **Monitor the AI security tools themselves (maps to T1685.007).** Log and alert on repeated injection attempts, sudden changes in an AI tool's review behavior, and gaps in its coverage. New detection strategies in v20 link each behavior to collectible data and analytics — use those mappings in your SIEM.
6. **Update your detection coverage (all five IDs).** v20 adds new detection strategies and analytics across Enterprise, Mobile, and ICS. Review where your current coverage maps to the new technique IDs and flag the gaps — that's exactly what these releases are for.

![Binary code visualization representing malicious payloads hidden inside AI-processed content](/images/mitre-attck-v20-ai-techniques-agent-defense/cyber-attack-binary.jpeg)

*Indirect prompt injection (T1698) hides malicious instructions in content agents process — base64 blobs, zero-width characters, and CSS-hidden text are documented methods. Images: Pexels.*

### Limits and what v20 doesn't give you

This is honest bookkeeping. ATT&CK is a taxonomy, not a tool: the IDs tell you what to name the attack, not how to catch it — your detections are still yours to write. The five AI techniques describe behaviors already observed in the wild, but MITRE attributes no specific campaign, malware family, or threat actor to this release, and reporting is at the analyst level, not vendor-tested ground truth. If you were waiting for a detection rule pack to ship with the release, it doesn't — the 9 new detection rules cited by threat-intel vendors are analyst-written mappings, not MITRE-distributed content. I also haven't validated the hiding-method examples against your specific stack; test them in your own pipeline before writing policy around them.

## FAQ

### What is MITRE ATT&CK v20?

The October 13, 2026 release of MITRE's adversary behavior framework. It adds nine Enterprise techniques (including five AI-focused ones: T1699, T1698, T1700, T1608.007, T1685.007), updates ICS and Mobile matrices, and refines detection strategies across all three domains.

### Do I need to install anything for these new technique IDs?

No. ATT&CK is a knowledge base, not software. The value is in mapping: update your detection-as-code, SIEM rules, and threat reports to reference the new IDs, then close the coverage gaps they expose.

### Which of the five AI techniques matters most for n8n builders?

T1698 (Indirect Prompt Injection). n8n agents routinely process untrusted external content — emails, tickets, web pages — which is exactly the channel indirect injection rides on. Sanitize inputs in the workflow before the agent sees them, and gate irreversible actions behind human approval.

### Does v20 change anything about CAPTCHA or MFA?

Yes, in coverage terms. T1697 tracks stealing app-specific passwords to bypass MFA, and T1696 (with sub-techniques for automating or avoiding CAPTCHA) tracks anti-automation evasion. If your threat model includes bot traffic or credential theft, these IDs now belong in your detection mapping.

## Key Takeaways

1. **ATT&CK v20 makes AI attacks first-class** — five new IDs (T1699, T1698, T1700, T1608.007, T1685.007) cover prompt injection, AI-enabled exfiltration, AI result poisoning, and attacks on AI defenses.
2. **Indirect prompt injection (T1698) is the highest-priority ID for agent builders** — hidden instructions in emails, docs, and web pages reach agents without any direct attacker contact.
3. **Treat external content as data, never instructions** — sanitize before the agent processes it, and require human approval for irreversible actions.
4. **AI-enabled exfiltration (T1700) is already real** — the CERT-In CIAD-2026-0049 incidents show scoped-down agent identities and least privilege are not optional.

Next: map these five IDs into your detection coverage this week. Start with a one-hour exercise: pick your highest-traffic AI agent workflow, list which external inputs it consumes, and ask which of the five techniques each input exposes you to. And if you haven't audited agent identities yet, our [n8n October 2026 security update guide](/blog/n8n-october-2026-security-update/) is the place to start.

*Images: Pexels (free license).*
