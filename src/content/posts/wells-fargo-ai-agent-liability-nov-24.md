---
title: "Wells Fargo Just Made You Liable for Your AI Agent — What Builders Must Change Before Nov 24"
description: "Wells Fargo's new Section 15 makes customers liable for everything their AI agent does in their account. The 5-step checklist for builders."
date: 2026-11-07
category: news
tags: ["AI agents", "Wells Fargo", "agent liability", "banking", "n8n"]
draft: false
featured: false
image: "/og/wells-fargo-ai-agent-liability-nov-24.webp"
---

"wells fargo ai agent revocation" is a breakout search on Google Trends this week — one of the fastest-rising queries under "AI agent" in the US over the past 7 days. The reason is a quiet contract change with loud consequences: Wells Fargo has rewritten its Online Access Agreement so that anything an AI agent does inside your account counts as if you did it yourself.

The new terms take effect **November 24, 2026** — three days before Black Friday. If you build agents that touch money, or you let one touch your own bank account, this is the week to read the fine print and change how your agents are wired. Here is what Section 15 actually says, why it is bigger than one bank, and a five-step checklist to run before the deadline.

## What Wells Fargo actually changed

Wells Fargo posted an updated version of its Online Access Agreement — the contract every customer accepts to use its online banking and app — marked "Version Effective November 24, 2026." The current version, effective May 21, 2026, says nothing about AI agents. The new one adds **Section 15, "Third-Party Artificial Intelligence Agents or Agentic AI."** The change was first reported by American Banker on November 2, 2026, and confirmed by multiple outlets on November 3. Wells Fargo has not issued a public statement explaining it.

The section has five moving parts. Each one matters on its own; together they redraw who carries the risk when software acts on your behalf.

| Clause | What it says | What it means in practice |
| --- | --- | --- |
| **15(a) — Definition** | An "AI Agent" is any software, application, program, or other technology that takes autonomous, semi-autonomous, or non-autonomous action on behalf of a person or entity. | The definition is deliberately broad. Your n8n workflow, a browser agent, a voice assistant — all of it counts. |
| **15(d) — Authorization** | Any instructions, actions, or transactions initiated by the AI Agent "are deemed to have been initiated and authorized directly by you, without further verification," and the bank has "no obligation to investigate the validity or scope of such authority." | If your agent sends a payment, the bank treats it as your payment. There is no "the agent did it" defense. |
| **15(e) — Responsibility** | "Your use of any AI Agent is AT YOUR OWN RISK." The customer is solely responsible for the agent's actions, including "unintended actions" and the agent "exceeding the authority granted by you." The bank does "not monitor, screen, or review AI Agent activities." | A prompt injection that tricks your agent into a transfer, a hallucinated payee, a loop that pays twice — all of it lands on you. |
| **15(f) — Revocation** | Customers who revoke an agent's access "must retain evidence of such revocation and must provide such evidence to us, at our request." Until the bank is notified under Section 17(d), the customer "remain[s] responsible for all the AI Agent's activities." | Disconnecting the agent in its own app is not enough — the agent still knows the password. You carry the risk until the bank itself is told. |
| **15(g) — Registration and blocking** | Wells Fargo reserves the right to require customers to register their AI agents, and to "limit, prohibit, prevent, suspend, or terminate access by any AI Agent." | An agent that works today can stop working overnight, with no notice period promised. |

Three clauses carry the qualifier "subject to applicable law or regulation" — which is the one real limit on the bank's position. The federal rule most people reach for here is Regulation E, which protects consumers in electronic fund transfers. Whether it overrides a contract clause like this has not been tested, and no regulator has said so. **Treat the contract as the rule until a court or regulator says otherwise.**

The scale is worth stating plainly: Wells Fargo has roughly 70 million digital banking customers. Every one of them is covered by this agreement.

## Why this is bigger than one bank

Wells Fargo is the first major bank to put agent liability into a customer contract, but it is not acting alone. The last three weeks have been a coordinated tightening across the industry:

- **JPMorgan Chase, October 13.** On its third-quarter earnings call, CEO Jamie Dimon said the bank will not let outside agents in "because it's just too risky for clients and for JPMorgan," adding "you don't want rogue agents, and it could be thousands of them." A spokesperson told CNBC the bank does not permit third parties to access accounts by logging in with customer credentials. Read-only data through connectors like Plaid is allowed; moving money is not.
- **Schwab, October 16.** CEO Rick Wurster told Bloomberg Television that Schwab is blocking unauthorized AI agents, including Meta's Muse, and gets a weekly report on blocked attempts — "in the tens and twenties" per week. Read-only research access is fine; moving money is not.
- **Citi.** A spokesperson told USA TODAY the bank does "not permit third-party AI agents or assistants to log into a customer's account or transact directly within our digital banking platforms."
- **Bank of America.** The bank is limiting agent access to consumer deposits while it writes protocols deciding which party is liable for a payment an AI authorizes. CEO Brian Moynihan told CNBC there "should be a human in the loop to authorize money moving out of your account."
- **Axios, October 22.** Citing unnamed sources, Axios reported major US banks are detecting third-party AI agents inside customer accounts, some taking actions "that appear to be independent of user instructions," and that many banks "are broadly not able to parse whether agent account activity is user-directed."

The pattern is the same one we saw a week earlier on the enterprise side: Google Workspace will start rejecting AI agents without a new agentic OAuth flag on November 11. The platforms that used to tolerate agents logging in as you are now drawing a line — and the line lands on the user, not the agent vendor.

White House AI czar David Sacks offered the counterpoint: most of the activity is customers sharing credentials with agents, which "may violate bank terms requiring humans to log in themselves, but these are in no way cyberattacks." His suggested middle ground is read-only access for agents, with full write access "approached carefully." That distinction — read-only versus write — is the one builders should design around now.

## The liability stamp press: how Section 15 actually works

<figure>
  <img src="/figures/wells-fargo-ai-agent-liability-nov-24-liability-press.svg" alt="Isometric liability stamp press machine: agent instruction tokens ride a feed chute into a stamping press that stamps each one AUTHORIZED BY YOU, then drops it into a ledger drum; a revocation lever on the side feeds an evidence drawer that only closes the ledger when the bank has been notified" loading="lazy" />
  <figcaption><b>Fig 1 — The Section 15 liability stamp press.</b> Every instruction your agent sends rides the feed chute into the press, which stamps it as if you sent it yourself — the stamp is clause 15(d), and there is no second check. Stamped instructions drop into the ledger drum, which is clause 15(e): the bank does not watch the drum, it just holds you responsible for everything in it. The revocation lever on the right only closes the ledger when two things happen: the agent is disconnected <i>and</i> the bank is notified — that is clause 15(f), and the evidence drawer is the proof you are required to keep. Watch the orange gate at the top: that is clause 15(g), the bank's right to shut the whole machine down or demand registration at any time.</figcaption>
</figure>

The machine above is the honest way to picture the contract. There is no approval step, no monitoring step, and no appeal step in Section 15. An instruction goes in, it is stamped as yours, it lands in the ledger, and the ledger is yours to pay for. The only exit is revocation with evidence — and the exit only works once the bank knows about it.

## What this means if you build agents that touch money

If you run n8n workflows that move money — invoice payments, subscription checks, balance-triggered transfers, anything with a banking credential in it — three of your assumptions just changed:

1. **"The agent made a mistake" is no longer a defense.** Clause 15(e) explicitly covers "unintended actions" and the agent "exceeding the authority granted by you." A prompt injection hidden in an email or a web page that tricks your agent into a transfer is your transfer. We covered the injection pattern itself in our guide to [prompt injections hiding in HTTP headers](/blog/http-header-prompt-injection-ai-agents/) — the attack has not changed, but who pays for it has.
2. **Credential sharing is the trigger.** The liability attaches when you "provide an AI Agent with access… using your login credentials, or otherwise authorize an AI Agent to act on your behalf." Every workflow that logs an agent into a bank with your username and password is now a liability machine. Official API access and read-only connectors (Plaid-style) sit outside that trigger — which is exactly why JPMorgan and Schwab allow read-only and block the rest.
3. **Revocation is a process, not a click.** Deleting an agent's access in the agent's own settings does not end your responsibility. Under 15(f) you must keep evidence of the revocation and hand it over on request, and you stay liable until the bank is notified through the channels in Section 17(d) — by phone at 1-800-956-4442, or by letter to the bank's customer correspondence office in Portland, Oregon. The contract never defines what counts as proof, which is the weakest point in the whole section.

If you build agents for clients, the exposure is worse: your client's contract, your workflow, your bug — and the liability lands on the client. That is a conversation to have before November 24, not after the first bad transfer.

## The 5-step checklist before Nov 24

Run this before the new terms take effect. It takes an afternoon, and most of it is audit, not rebuild.

**Step 1 — Inventory every agent with bank access.** List every workflow, assistant, and browser agent that holds a banking login or can initiate a payment. Check n8n credentials, saved browser sessions, and any "connect your bank" step a client set up and forgot. If you cannot list it, you cannot revoke it.

**Step 2 — Switch money-moving agents to read-only where possible.** Balance checks, transaction monitoring, and alerts do not need write access. Where a payment truly must happen, put a human approval step in front of it — a Telegram or email confirmation the workflow waits on before executing. This is the same approval-gate pattern we recommended for [rogue-agent containment](/blog/openai-rogue-agents-100-orgs/), and it is now a liability control, not just a safety preference.

**Step 3 — Revoke what you no longer use, and document it.** For every agent you are retiring, do all four: disconnect it in the agent's settings, delete any saved credentials, change the bank password so the old one is dead, and notify the bank at the number in Section 17(d), noting the date, time, and who you spoke with. Screenshot the revocation confirmation and keep it — Section 15(f) requires you to retain evidence and produce it on request.

**Step 4 — Add guardrails to the agents you keep.** Scope the agent's authority in writing inside the workflow: an allow-list of payees, a per-transaction cap, a daily cap, and a hard rule that the agent never follows payment instructions found in emails, web pages, or documents. Log every action with a timestamp. If the bank ever asks what your agent did, that log is your evidence.

**Step 5 — Tell your clients.** If you built payment or banking workflows for clients, send them a short note this week: the terms change November 24, their agent's actions are now legally theirs, and here is what you have changed in their workflows. The liability conversation is much cheaper before a bad transfer than after one.

## What we don't know yet

Honesty requires the gaps. No court has tested whether Regulation E overrides Section 15's liability shift — the "subject to applicable law or regulation" qualifier is untested language. Wells Fargo has not said how agent registration under 15(g) would work, what form revocation evidence must take, or whether it will actually enforce the section against ordinary customers. And this is a contract change, not a law: it binds Wells Fargo customers, not every bank. Other banks may follow with different wording, or not at all.

What is certain is the direction. Banks spent October detecting agents in their systems and deciding they could not tell authorized agents from rogue ones. Their answer, so far, is not better detection — it is a contract that makes the customer responsible either way. Builders who design for that reality now — read-only by default, approval gates on money movement, documented revocation — will not have to redesign under pressure later.

## FAQ

### Does this affect me if I don't use Wells Fargo?

Not directly — Section 15 is a Wells Fargo contract term. But JPMorgan, Schwab, Citi, and Bank of America all moved in the same direction in October, and the pattern (read-only allowed, credential-based write access blocked or liability-shifted) is now the industry default. If you bank elsewhere, check your own bank's online access agreement for an AI agent section before you assume you are unaffected.

### I only let my agent check balances. Am I liable for that?

Under Section 15, liability attaches to actions the agent takes with your credentials. Read-only checks are lower risk, but the section's definition of an agent is broad and the bank reserves the right to restrict any agent access. The safer posture is still an official read-only connection (Plaid-style) rather than handing the agent your login.

### What counts as "evidence of revocation"?

The contract does not say. The prudent sequence is: disconnect the agent in its settings, delete saved credentials, change the bank password, notify the bank by phone (1-800-956-4442) or letter, and keep dated screenshots and a written note of the call. Until a regulator or court defines it, more documentation beats less.

### Does Regulation E protect me from an agent's bad transfer?

Maybe, and nobody knows yet. Regulation E protects consumers in electronic fund transfers, and Section 15 repeatedly says its terms apply "subject to applicable law or regulation." Whether that qualifier saves a customer from a transfer their agent made is untested. Do not rely on it as your plan — rely on the checklist above.

### My n8n workflow pays invoices automatically. What should I change first?

Add a human approval step before any payment executes, and cap amounts per transaction and per day. Then audit whether the workflow needs write access at all — most invoice workflows can check, match, and draft, and only need a person to click approve. That single change removes most of the exposure Section 15 creates.

## Key Takeaways

1. **Wells Fargo's Section 15, effective November 24, 2026, makes customers liable for everything their AI agent does in their account** — including unintended actions, prompt-injection tricks, and actions beyond the agent's authority.
2. **Revocation is your job, with proof.** Disconnecting the agent is not enough: change the password, notify the bank, and keep dated evidence of the revocation.
3. **The bank can require agent registration or block agent access at any time** — an agent that works today can stop working overnight.
4. **This is an industry pattern, not a one-off.** JPMorgan, Schwab, Citi, and Bank of America all tightened agent access in October; Google Workspace starts rejecting non-agentic agents on November 11.
5. **The builder's fix is read-only by default and approval gates on money movement** — plus a documented revocation process for every agent you retire.

Next step: run the five-step checklist this week, before the terms take effect. If you run banking workflows in n8n, start with Step 1 — the inventory — because every agent you forgot about is an agent you cannot revoke. For the parallel lockdown on the enterprise side, read our guide to [Google Workspace's agentic OAuth deadline](/blog/google-workspace-agentic-oauth-november-deadline/).

*Sources: the text of Section 15 is quoted from Wells Fargo's Online Access Agreement (version effective November 24, 2026) as reported by American Banker on November 2, 2026, [Tech Times, November 3, 2026](https://www.techtimes.com/articles/329947/20261103/wells-fargo-just-made-you-legally-responsible-every-transaction-your-ai-agent-makes.htm), [AccountsRecovery.net, November 3, 2026](https://www.accountsrecovery.net/2026/11/03/wells-fargo-makes-customers-liable-for-ai-agent-transactions-including-unintended-ones/), and [PayPath, November 3, 2026](https://paypath.ai/blog/ai-agents-in-customer-bank-accounts-servicing-collections). Trend signal: "wells fargo ai agent revocation" — Breakout rising query for "AI agent," Google Trends Explore, US, past 7 days, checked November 7, 2026.*
