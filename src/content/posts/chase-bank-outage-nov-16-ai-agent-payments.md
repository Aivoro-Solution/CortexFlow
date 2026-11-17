---
title: "Chase Went Down and Took Zelle With It — What the Nov 16 Bank Outage Means for AI Agents That Move Money"
description: "Chase's Nov 16 bug slowed payments at five US banks and Zelle. What broke, what the DHS AI claim gets wrong, and the pattern your n8n money workflows need."
date: 2026-11-17
category: news
tags: ["AI agent", "bank outage", "Chase", "Plaid", "Zelle", "n8n", "payments"]
draft: false
featured: false
image: "/og/chase-bank-outage-nov-16-ai-agent-payments.webp"
---

On Monday, November 16, 2026, America's biggest bank broke — and it took the payments of five other banks with it. JPMorgan Chase says a software bug in its own on-premise hardware slowed transactions for most of the day, and by the evening the problem was fixed. Nobody lost access to their money. But the outage is the third major US infrastructure failure in five days, it hit the exact rails AI agents use to move money, and it lands one week before Wells Fargo's new terms make you personally liable for everything your agent does with your bank login. By the end of this article you will know what actually broke, which claims about the outage are unverified, and the five-part pattern that keeps an n8n money workflow safe when the rail underneath it stops.

## What happened on Monday

The timeline, as reported by Al Jazeera, USA TODAY, and Fast Company on November 16–17:

| Time (ET, Nov 16) | What happened |
|---|---|
| 9:53 a.m. | First Downdetector reports of Chase problems appear |
| 10:11 a.m. | Plaid — the service finance apps use to connect to bank accounts — opens an incident for Chase |
| ~2:00 p.m. | Downdetector Chase reports peak at about 4,800, the bank's second-highest 15-minute report count in at least a year |
| ~6:30 p.m. | A Chase spokesperson tells NBC News transactions are posting normally again |
| ~7:00 p.m. | Chase tells USA TODAY the issue is resolved |

Chase's statement, repeated across the coverage, is worth quoting in full because it is the only official cause on record: *"JPMorgan Chase has experienced a temporary issue related to a software bug in on-premise hardware systems — there is no evidence this is cyber-related."*

The customers affected were not only Chase's. Downdetector spikes also showed up for Bank of America, Wells Fargo, U.S. Bank, Capital One, and Zelle, the payment network. Chase's own explanation for that spread is that the other banks were slowed only in transactions that involved Chase — a Chase payment going out, or a Chase payment coming in. US Bank told reporters its own systems were not directly affected. Chase was explicit on one point: *"This is not a systemic issue."*

Two details matter for builders. First, the Plaid incident. Plaid is the connector layer between finance apps — and the agents built on top of them — and bank accounts. When Plaid opened a Chase incident at 10:11 a.m., every app and agent that reaches Chase through Plaid had a degraded rail, whether or not its own code was fine. Second, the Downdetector numbers are user reports, not bank counts. They tell you how many people noticed and complained, not how many transactions failed. Treat the ~4,800 peak as a measure of visibility, not of damage.

## Why one bank's bug slowed five banks

This is the part that surprises people who have never looked at how money moves. Banks do not each run a sealed pipe to every other bank. A payment from a Chase account to a Bank of America account is a transaction between the two institutions, and if one side's processing slows, the other side's customer waits. Chase is the largest US bank by assets, so a slowdown in its transaction processing is a slowdown in a large share of the country's interbank traffic.

That is also why the outage looked bigger than Chase. A Zelle payment between two Chase customers, or between a Chase customer and anyone else, touches Chase's systems. The same is true of any agent that pays, invoices, or reconciles through a bank connection: the agent's code can be perfect and the payment still stalls, because the failure is one layer down, in a system the agent cannot see or control.

The pattern is now a weekly rhythm. Microsoft 365 went down on November 12 and took the AI connectors with it — I covered that outage and the connector-dependency pattern it exposed in [Microsoft 365 Went Down for 5 Hours — and Took Your AI Agent's Tools With It](/blog/microsoft-365-outage-ai-connectors-down/). The FAA ordered a nationwide ground stop on November 13, three days after putting an AI agent on every flight route, in [The FAA Put an AI Agent on Every US Flight Route](/blog/faa-smart-ai-agent-nationwide-ground-stop/). Now the banks, on November 16. Three different systems, three different causes, one lesson: **the services your agent depends on fail on their own schedule, and your workflow has to survive that.**

![Payment-rail press — a jammed gear in the Chase source cell slows the transaction drum, and the slowness fans out through distribution pipes to five bank cells and Zelle, while the Plaid connector lamp burns and delayed payments stack up in the queue drum beside a lit approval lever.](/figures/chase-bank-outage-nov-16-ai-agent-payments-rail-press.svg)

*Figure 1: The payment-rail press. A jammed gear in the Chase source cell slows the central transaction drum; five distribution pipes carry the slowness to BofA, Wells Fargo, U.S. Bank, Zelle, and others, each with a stalled dial. The Plaid connector's incident lamp is lit, and delayed payments stack in the queue drum beside the approval lever. Readout: first reports 9:53 AM, peak ~4,800 reports ~2 PM, resolved ~6:30 PM, 5 banks + Zelle affected, Plaid incident 10:11 AM ET.*

## The DHS secretary's AI claim — what was actually said

On Monday night, Homeland Security Secretary Markwayne Mullin told Fox News that his office had found no proof the outages were caused by a cyberattack, and then suggested the outages may have been caused by a malfunction brought on by incorporating artificial intelligence into existing digital infrastructure. USA TODAY's live coverage reports that Mullin said he had talked with a technology expert who suggested AI being incorporated into these systems is causing the existing infrastructure to malfunction.

Be careful with that claim, because it is already being repeated as fact in places that should know better. What is on the record:

- Chase, the bank that actually had the bug, says the cause was a software bug in on-premise hardware systems, with no evidence it was cyber-related.
- Mullin offered no evidence, no named expert, and no mechanism — only that a technology expert suggested it.
- No other bank has reported an AI-related cause, and DHS has published no finding.

That is not a debunking of the AI theory; it is a statement about evidence. A software bug in hardware systems is a specific, testable claim from the operator. "AI broke the infrastructure" is a suggestion from an unnamed expert, relayed by a cabinet secretary on television. Until someone publishes a mechanism — which system, which AI component, which failure mode — the AI claim belongs in the unverified column, and any article that states it as the cause is guessing.

There is a real question underneath the speculation, and it is worth asking properly. Banks are wiring AI into fraud detection, transaction routing, and customer service, and the failure modes of those integrations are genuinely not well understood. But the way to answer that question is an incident report with a root cause, not a television suggestion. Watch for Chase's follow-up disclosure; if it names an AI component, that changes the story completely.

## The part that matters for agent builders: November 24 is one week away

The outage is a one-day story. The deadline it collides with is not. On November 24, 2026, Wells Fargo's updated Online Access Agreement takes effect, with a new Section 15 covering third-party AI agents. I covered the terms in detail in [Wells Fargo Shifts AI Agent Liability Onto Customers — Nov 24 Deadline](/blog/wells-fargo-ai-agent-liability-nov-24/), and the short version is this: anything an agent does under your login is deemed to have been initiated and authorized directly by you, your use of any AI agent is "AT YOUR OWN RISK", you remain responsible for the agent's actions until you notify the bank, and you must keep proof of any revocation and produce it on request.

Put the two stories together and the risk becomes concrete. On November 16, the rail your agent pays through stopped working for nine hours through no fault of the agent. On November 24, if your agent retries a stalled payment twice, pays the wrong invoice while a bank feed is stale, or keeps acting on a revoked authorization because the revocation never reached the bank, the liability for that action is yours. The outage shows the failure mode; the Wells Fargo terms show who pays for it.

The banks have been moving in this direction all autumn. JPMorgan, Bank of America, Citi, and Morgan Stanley restricted third-party agents from customer accounts in late October, and Accenture's global banking lead has warned that blocking agents won't win long-term — I covered that in [Banks Are Banning Your AI Agent — Accenture Says the Bans Won't Last](/blog/accenture-warning-banks-blocking-ai-agents/). Wells Fargo's approach is different from a block: it lets the agent in and hands you the bill. That is the model other banks are most likely to copy, because it costs them nothing and transfers the entire risk.

## The 5-part money-rail pattern for n8n

Here is the pattern to build before November 24. It is the same shape as the model-fallback pattern from the Claude outage article — [Claude Went Down Twice on Friday the 13th](/blog/claude-outage-nov-13-n8n-fallback/) — applied to money instead of models.

**1. Probe the rail before the agent acts.** Before any workflow that moves money, add an HTTP Request node that checks the status of the rail it depends on — Plaid's status page, your bank's status endpoint, or the payment provider's status API. If the rail reports degraded, the workflow stops before it touches a transaction. A status check costs one HTTP call; a payment sent into a broken rail costs a reconciliation nightmare.

**2. Fail loudly on a channel outside the bank.** When the probe fails, or a payment node errors, the workflow must alert you somewhere the outage cannot reach — a Telegram message, a Slack DM, an email on a different provider. The Microsoft 365 outage taught the same lesson: if your alert goes through the system that just failed, you find out hours late. In n8n, wire the Error Trigger to a notification node that uses credentials from a different provider than the one that failed.

**3. Queue, don't retry blindly.** A payment that fails because the rail is down must go into a queue with an idempotency key — a unique reference your workflow generates once per payment — and wait. It must never be retried by a loop that re-sends the same payment, because the classic double-payment happens exactly like this: the first attempt actually went through slowly, the retry goes through too, and the vendor gets paid twice. Store the queued payment, its idempotency key, and its status in a database or a sheet, and drain the queue only after the rail reports healthy again.

**4. Put an approval gate before money moves.** No agent should send a payment, change a payee, or alter an amount without a human approval step — a Telegram or Slack message with the exact amount, payee, and invoice reference, and a workflow that waits for your explicit yes. This is the same gate the [n8n 2.43 agent guardrails release](/blog/n8n-2430-agent-guardrails-release/) made standard, and it is the single control that would have caught every agent-payment horror story in the Wells Fargo coverage. During an outage, the approval gate is also your pause button: nothing moves while you cannot verify the state of the rail.

**5. Keep written proof of every revocation.** Wells Fargo's Section 15(f) requires you to retain proof that you revoked an agent's access and produce it on request. Build that into the workflow: when you revoke an agent's bank access, log the date, time, method, and confirmation to a sheet or a database, and screenshot the confirmation page. A revocation with no paper trail is, under the new terms, a revocation that never happened.

## What I didn't verify

Honest limits, as always. Downdetector's numbers are user reports, not Chase's transaction counts — I have no figure for how many payments actually failed or were delayed. Chase has published no root-cause detail beyond "a software bug in on-premise hardware systems", so I cannot tell you which system or which bug. The DHS AI claim is unverified and I have treated it as such. The Wells Fargo terms are quoted from the bank's posted agreement as reported by American Banker and secondary coverage on November 17 — I have not re-read the full agreement text in this run. And I did not test an n8n-to-Plaid payment flow against the live outage; the pattern above is assembled from the verified outage facts and the guardrail patterns this blog has already published, not from a live reproduction.

## FAQ

### Was the November 16 bank outage a cyberattack?

No evidence points to one. Chase says the cause was a software bug in its on-premise hardware systems, and DHS Secretary Mullin said on Monday night that his office found no proof of a cyberattack. No bank has reported an attack, and no threat actor has claimed one.

### Did AI cause the outage?

Unverified. Secretary Mullin suggested on Fox News that AI being incorporated into existing infrastructure may be causing malfunctions, citing an unnamed technology expert. Chase's own explanation is a software bug. Until a root-cause disclosure names an AI component, treat the AI claim as speculation, not fact.

### Will my n8n agent's payments be affected by bank outages?

Yes, if your agent pays through a bank connection or a connector like Plaid. The agent's code can be flawless and the payment still stalls, because the failure is in the rail underneath it. Build the probe-queue-approve pattern above so a rail outage becomes a paused workflow instead of a double payment.

### What changes on November 24, 2026?

Wells Fargo's updated Online Access Agreement takes effect, with a new Section 15 on third-party AI agents. Anything your agent does under your login is deemed authorized by you, your use of an agent is at your own risk, and you must keep proof of any revocation. Read the full breakdown in [Wells Fargo Shifts AI Agent Liability Onto Customers](/blog/wells-fargo-ai-agent-liability-nov-24/).

## Key Takeaways

1. **Chase's Nov 16 outage was a software bug, not a cyberattack** — first reports 9:53 a.m. ET, peak ~4,800 Downdetector reports ~2 p.m., resolved ~6:30 p.m., with the slowness rippling to BofA, Wells Fargo, U.S. Bank, Capital One, and Zelle.
2. **Plaid opened a Chase incident at 10:11 a.m.** — the connector layer agents use to reach bank accounts was degraded, so agent payments stalled even when the agent's own code was fine.
3. **The DHS AI claim is unverified** — a suggestion from an unnamed expert, with no evidence or mechanism published. Don't repeat it as the cause.
4. **Three major US outages in five days** — Microsoft 365 (Nov 12), the FAA ground stop (Nov 13), the banks (Nov 16). Your agent's dependencies fail on their own schedule.
5. **November 24 is the real deadline** — Wells Fargo's new terms make you liable for everything your agent does with your login. Probe the rail, queue with idempotency keys, gate every payment behind human approval, and keep written proof of revocations.

Next: audit one money-moving workflow this week against the five-part pattern — start with the approval gate, because it is the control that catches every other failure mode. Then read the Wells Fargo terms breakdown before November 24, and check whether your bank has published anything similar.
