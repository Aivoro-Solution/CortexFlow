---
title: "AI Agents Pay With Cards, Not Crypto — TOKEN2049's FLOP Network Says Otherwise"
description: "TOKEN2049: Hayes unveiled FLOP so AI agents pay for compute on-chain; Dragonfly's Qureshi says agents just use cards. The builder's playbook."
date: 2026-10-10
category: news
tags: ["ai-agents", "payments", "crypto", "token2049"]
draft: false
featured: false
image: "/og/token2049-flop-agent-payments.webp"
---

Twenty-five thousand people just left Singapore arguing about how AI agents should pay for things. On one stage at TOKEN2049, BitMEX co-founder Arthur Hayes unveiled FLOP — a network built so AI agents can pay for computing power on-chain, with a 90-day testnet starting in late October and mainnet targeted for Q1 2027. On another stage, Dragonfly's Haseeb Qureshi said the uncomfortable part out loud: he had been wrong a year earlier, because in practice the AI tools buying things online ended up paying with ordinary credit cards, not crypto wallets.

Both men are describing real things. But both are answering the wrong question. The question for builders is not which rail wins — it is how you give a spending agent a budget it cannot blow through, on whatever rail it uses. This post lays out what happened at TOKEN2049, why cards are winning today, where they genuinely fail, and a five-part payment design you can build this week.

## What actually happened at TOKEN2049

The Singapore edition wrapped on October 8, 2026 at Marina Bay Sands: 25,000 attendees from 160 countries, 250 speakers across six stages, and the only flagship edition this year (the Dubai edition moved to 2027). AI agents were the loudest theme of the builders' day — and the stage did not agree on them.

Hayes's pitch: FLOP, a network that lets AI agents pay for computing power on-chain. Target: a 90-day testnet from late October, mainnet in Q1 2027. The idea is that agents buying GPU time from each other should not need a bank account — just a wallet and a protocol.

Qureshi's rebuttal was simpler and harder to argue with: he admitted he had been wrong a year earlier. Agents ended up paying with cards rather than crypto. The AI tools that buy things online today mostly use ordinary payment cards, not crypto wallets.

A third data point came from Eric Trump, speaking for World Liberty Financial: the family's hotel business is looking at paying salaries in stablecoins, and USD1 payments are supposed to reach large online merchants via Mesh this quarter. Stablecoins, in other words, are positioning as the middle path between volatile crypto and the card rails.

This is the second act of a story we covered last week, when [Cloudflare gave AI agents wallets](/blog/cloudflare-agent-stablecoin-payments/) — agent-native stablecoin payments built into the network layer. The industry is clearly converging on one belief: agents will spend money. The fight is over the plumbing.

![Physical cryptocurrency coins — the on-chain vision of agent payments that TOKEN2049's FLOP is betting on](/images/token2049-flop-agent-payments/crypto-coins.jpg)
*The on-chain vision: agents holding wallets and paying each other directly. FLOP wants to make this the default for compute — but it is still pre-testnet.*

## Why Qureshi is right about today

Cards did not win by accident. Three structural reasons:

**Disputes exist.** A card charge can be reversed; an on-chain transfer cannot. When an agent buys the wrong thing at 3 AM, the finance team wants a chargeback button, not a blockchain explorer.

**Acceptance is universal.** Every API that takes money takes cards. Almost none take agent-held wallets. The agent that needs to pay for a SaaS seat, an API tier, or a domain renewal reaches for the rail that works everywhere.

**Keys are a liability.** A card number can be rotated in seconds by the issuer. A compromised private key means the agent's money is gone permanently, with no one to call. Key management for fleets of agents is an unsolved operational problem, not a solved one.

There is also a softer reason: auditors understand cards. "The agent has a virtual card with a $50 daily cap" passes a security review. "The agent holds ETH in a multisig" gets you a meeting with legal.

## Where cards genuinely fail — Hayes's opening

The card story has three holes you can drive a truck through:

**Micropayments.** Card fee floors make sub-cent machine-to-machine payments uneconomic. An agent that should pay $0.0004 for a single API call cannot do it on Visa. Multiply by millions of calls and the card rail is not just expensive — it is structurally wrong.

**No human cardholder.** Cards assume a person with a name, a billing address, and a dispute process. An autonomous agent is none of those. Every card transaction by an agent is a human's identity being borrowed by software.

**Settlement speed and borders.** Cross-border card payments still take days and shave percentage points. On-chain settlement is minutes and near-flat. For agents operating globally around the clock, that gap matters.

**The honest caveat: FLOP is pre-testnet.** There is no usage data, no fee schedule, no evidence agents will adopt it. Hayes is selling a roadmap. Do not architect around an announcement.

![A customer paying with a credit card — the rail that AI agents actually use today, whatever the conference stages say](/images/token2049-flop-agent-payments/card-pay.jpg)
*The reality Dragonfly's Qureshi described: today's agents pay with ordinary cards. The winning design assumes this and contains the blast radius.*

## The five-part payment design you can build this week

Forget picking a rail. Build the controls, and they work on any of them:

**1. One virtual card per agent.** Single-purpose cards (Stripe Issuing, Lithic, and similar) with per-card limits. If one agent is compromised, you freeze one card — not the company account.

**2. Hard spend caps per task, per hour, per day.** Caps are enforced by the issuer, not by the agent's good intentions. An agent cannot promise its way past a limit it does not control.

**3. Approval gates above a threshold.** Anything over $X pauses for a human. We wrote about this pattern last week for [approval-gated agents](/blog/pricelabs-athena-approval-gated-agents/) — the same gate works for spend. In n8n terms, the gate is a Wait node or a human-in-the-loop sub-workflow sitting between "the agent decided to buy" and "the payment executes." The agent proposes; the workflow disposes.

**4. A ledger for every cent.** Log each transaction with the task ID, the agent ID, and the vendor. When the bill surprises you — and it will — the ledger tells you which agent did it and why.

**5. Velocity alerts.** A $5 charge is fine. Fifty $5 charges in four minutes is an incident. Alert on rate, not just totals.

## The stablecoin middle path

USD1 reaching merchants via Mesh, Cloudflare's agent wallets — stablecoins dodge crypto's volatility while keeping programmability. That combination is exactly what the card rail cannot offer and what volatile crypto cannot either. Worth a pilot where your vendors support it. Not the default yet.

Watch the FLOP testnet (late October) the way you would watch any beta: interesting, not load-bearing. If agents start paying for compute on-chain in real volume, the ledger-and-caps design above ports over unchanged — the controls are rail-agnostic.

## What this doesn't cover

I have not tested FLOP — nobody has; it is not live. Virtual cards still require a human-owned account and pass KYC, and some jurisdictions restrict issuing. And none of this replaces fraud monitoring on the vendor side: your controls stop your agent from overspending, not a compromised vendor from overcharging.

## FAQ

### What is FLOP?

FLOP is a network unveiled by Arthur Hayes at TOKEN2049 Singapore in October 2026, designed to let AI agents pay for computing power on-chain. A 90-day testnet is targeted from late October 2026, with mainnet in Q1 2027. It is an announcement, not a live product.

### Do AI agents really pay with credit cards today?

According to Dragonfly's Haseeb Qureshi, speaking at the same event: yes. The AI tools buying things online today mostly use ordinary payment cards rather than crypto wallets — which is why he publicly revised his own earlier prediction.

### Should I build my agent payments on crypto now?

No. Build on cards with caps and approval gates today, run a stablecoin pilot if your vendors support it, and watch FLOP's testnet from the sidelines.

### How do I stop an AI agent from overspending?

Give it a single-purpose virtual card with a hard cap, require human approval above a threshold, log every transaction with its task ID, and alert on spend velocity.

## Key Takeaways

1. **TOKEN2049 split on agent payments:** Hayes's FLOP bets on-chain; Dragonfly's Qureshi says cards already won.
2. **Cards win today** on disputes, acceptance, and key rotation — but fail on micropayments, machine identity, and cross-border speed.
3. **FLOP is pre-testnet:** watch it, don't build on it.
4. **The builder's design:** one virtual card per agent, hard caps, approval gates, a full ledger, velocity alerts.
5. **Stablecoins are the plausible middle path** — pilot, don't commit.

Next step: audit one agent's spending this week — list every credential it can spend with, put a cap on each, and add one approval gate. Then read our [Cloudflare agent-wallets piece](/blog/cloudflare-agent-stablecoin-payments/) for the on-chain side of the story.

*Images: Pexels*
