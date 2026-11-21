---
title: "Retell AI Crossed $100M ARR on $4.6M Raised — Wire Tell-1 Into n8n as an AI Receptionist"
description: "Retell AI hit $100M ARR in 17 months and launched Tell-1, a voice model that speaks before it finishes reasoning. The n8n wiring inside."
date: 2026-11-21
category: news
tags: ["retell ai", "voice agents", "n8n", "AI receptionist", "tell-1"]
draft: false
featured: false
image: "/og/retell-ai-100m-arr-tell-1-n8n-receptionist.webp"
---

A voice AI startup just crossed $100 million in annualized revenue on a $4.6 million seed round, with fewer than 80 employees — and in the same week it shipped a voice model that starts speaking before it finishes thinking. Retell AI's November 12 announcement, plus its Tell-1 model launch the next day, is the sharpest signal yet that the AI receptionist has moved from demo to production: searches for "retell ai" are now breaking out in the US, and "ai receptionist for small business" is the single rising query for "AI automation" on Google Trends this week.

This is not another wrapper story. Retell builds the voice layer for contact centers — agents that answer and place phone calls, book appointments, qualify leads, and hand off to a human with context. By the end of this article you will know what actually shipped, why the numbers are unusual, and the five-part pattern for wiring Retell into n8n as an AI receptionist that books appointments instead of just taking messages.

## What Retell announced on November 12

Retell announced on November 12, 2026 that it has surpassed $100 million in annualized run rate, less than three years after launch. The numbers, all company-reported in its press release:

| Metric | Figure (company-reported) |
|---|---|
| Annualized run rate | $100M+, up from $10M 17 months earlier |
| Total funding | $4.6M, one seed round led by Alt Capital |
| Profitability | Reached in 2025 |
| Team size | Fewer than 80 employees |
| Businesses on the platform | 4,000+, including Lenovo, CVS Health, BILL, and Grab |
| Connected calls | 100M+ per month |
| Monthly active users | 56,000+ |
| Enterprise revenue growth in 2026 | 9x |

The funding number is the one that makes people stop. Voice AI competitors in the same revenue range have raised hundreds of millions. Retell got there on a single seed round, stayed profitable since 2025, and grew enterprise revenue 9x in 2026 while its monthly call volume went from roughly 30 million in early 2026 to over 100 million by September. The launch post on X on November 12 reached 6.7 million views — 32 times the median for launches tracked by Launch Video.

Retell was founded in 2023, joined Y Combinator's Winter 2024 batch, and launched publicly in February 2024. The $100M milestone is real momentum, but keep the framing honest: Retell is private, so every figure above comes from its own press release and blog post, not audited financials. Run rate is not booked revenue.

## Tell-1: a voice model that speaks before it finishes reasoning

The product news matters more than the revenue number. Alongside the milestone, Retell launched Tell-1 (branded Retell LLM), its first dedicated AI voice model built for enterprise contact centers, and Conductor, an automated debugging tool for failed calls.

Tell-1 was trained on more than 1 million hours of real customer calls, and it is designed around the failure mode that kills most voice agents: the pause. A normal voice agent waits for the language model to finish reasoning, then speaks. Tell-1 writes the first sentence of a reply, starts speaking it, and keeps reasoning while that sentence plays. Retell reports a 72 millisecond median time to the first meaningful chunk of speech — a vendor figure, model time only, not the full round trip a caller experiences. It is priced at $0.035 per minute and became selectable on November 19, 2026.

Conductor attacks the other end of the problem: what happens when a call goes wrong. Instead of a support team combing through hours of call logs, Conductor automatically analyzes failed calls, generates test cases, and proposes targeted fixes for review and deployment. The human still approves the fix — the tool proposes, it does not ship.

The combination is the point. Tell-1 makes the agent sound less like a machine reading a script, and Conductor makes the agent cheaper to keep correct. Both are aimed at the same buyer: teams moving voice agents from pilot to production, which is exactly where Retell says its enterprise growth is coming from.

## Why the AI receptionist is the use case to build

"AI receptionist for small business" is not a vague trend phrase — it is the only rising query for "AI automation" in the US this week. The job is concrete: answer the phone when no human can, take the caller's details, book the appointment, and hand off the tricky calls to a person. A missed call is a lost lead, and small businesses miss a lot of calls.

Retell is built for exactly this shape. Its agents answer and place calls, book appointments, qualify leads, and transfer to a person with context. The n8n hook is direct: Retell maintains its own official n8n integration, with a community node (`@retellai/n8n-1odes-retellai`) for managing agents, calls, phone numbers, and knowledge bases from inside a workflow, plus a REST API and webhooks for everything else. Retell also provisions phone numbers itself, so you do not need a separate Twilio account to get started.

![Fig 1 — A receptionist press for the Retell AI voice stack. An incoming call drops into the hopper, the Tell-1 drum speaks the first sentence while it is still reasoning, the routing switchboard throws the lit lever toward booking or transfer, the n8n webhook gear turns the conversation into structured actions, and the CRM drum stamps the appointment.](/figures/retell-ai-100m-arr-tell-1-n8n-receptionist-receptionist-press.svg)

## The five-part AI receptionist pattern for n8n

The integration is two webhooks pointing in opposite directions: Retell tells n8n what happened on a call, and n8n tells Retell what to do next. Here is the pattern, built the way production users wire it.

**Part 1 — Trigger the call from n8n, never from a human's memory.** A missed call, a form submission, or a new row in a sheet fires the workflow. An HTTP Request node calls Retell's create-phone-call endpoint with the caller's name, number, and context as dynamic variables, so the agent opens already knowing who it is calling and why.

```http
POST https://api.retellai.com/v2/create-phone-call
Authorization: Bearer <your-retell-api-key>
Content-Type: application/json

{
  "from_number": "+1-555-010-1000",
  "to_number": "+1-555-010-2000",
  "agent_id": "agent_9f3c2a1b",
  "retell_llm_dynamic_variables": {
    "caller_name": "Priya Sharma",
    "reason": "missed call — asked about Saturday availability",
    "business_name": "Riverside Dental"
  }
}
```

Store the API key in n8n credentials, never inline in the node — a plaintext key in an exported workflow JSON is the single most common mistake in shared Retell setups. `from_number` is a number registered to your Retell account, `agent_id` is the agent you configured in the Retell dashboard, and the dynamic variables are what the agent says in its first sentence instead of asking the caller to repeat themselves.

**Part 2 — Let the agent ask n8n questions mid-call.** Inside the agent, define custom functions such as `check_availability` or `book_appointment`. When the caller asks for a slot, Retell POSTs to your n8n Webhook node with the function name and arguments; n8n checks the real calendar and returns the answer while the caller is still on the line. The agent never invents an appointment time — it can only offer what the calendar actually returned.

**Part 3 — Transfer to a human on uncertainty, not on failure.** Set the agent's transfer rules up front: unknown request, angry caller, or any question outside the knowledge base goes to a person with the full call context attached. A transfer is a designed outcome, not an error path. Tell-1's speed makes this safer, not riskier — a fast wrong answer is still a wrong answer, so the transfer rule is what keeps the receptionist trustworthy.

**Part 4 — Write everything back when the call ends.** Retell POSTs `call_started`, `call_ended`, and `call_analyzed` events to your n8n webhook. On `call_ended`, write the transcript, the extracted outcome (booked, interested, no answer, callback requested), and the call recording link into your CRM or database, and send the confirmation SMS from n8n — not from the agent. The call record is the audit trail; if a customer disputes what was booked, the transcript settles it.

**Part 5 — Put an approval gate before anything that moves money.** The agent books appointments and answers questions. It never issues a refund, changes a price, or cancels a paid booking without a human approval step in n8n. Conductor's fix proposals get the same treatment: review, then deploy. This is the same rule that applies to every agent that touches a customer's wallet, and voice agents are no exception just because they sound friendly.

## What I would not do yet

Three honest limits before you build this.

First, the headline numbers are Retell's own. $100M run rate, 72ms first chunk, 1M+ hours of training calls — all vendor-reported, none independently verified. Treat them as direction, not as a benchmark you can quote to a client.

Second, Tell-1 is new — selectable November 19, 2026, two days before this article. There is no public track record yet for how it behaves on long, messy, real-world calls with interruptions, accents, and background noise. Run it on a subset of calls first and compare its booking accuracy against your existing setup before switching everything over.

Third, the n8n integration is pattern-verified, not live-tested by us. The official community node, the REST API, the webhook events, and the create-phone-call endpoint are all documented and in production use by other builders, but we did not run a live Retell-to-n8n call for this article. Test the full loop — missed call to booked appointment to CRM record — with your own number before you point it at real customers. And check current pricing on Retell's pricing page: $0.035 per minute is the listed Tell-1 model price, and telephony and other model costs sit on top of it.

## FAQ

### Is Retell AI the same as an AI receptionist?

Not exactly. Retell is the voice AI platform; an AI receptionist is one thing you build on it. Retell provides the voice model (Tell-1), the phone numbers, the call handling, and the API. Your n8n workflow provides the business logic: calendars, CRM, booking rules, and the human handoff.

### How much does Tell-1 cost?

Retell lists Tell-1 at $0.035 per minute. That is the model price; check Retell's pricing page for telephony and any other charges before quoting a per-call cost to a client.

### Do I need Twilio to use Retell with n8n?

No. Retell provisions phone numbers itself. You connect it to n8n through the official community node (`@retellai/n8n-1odes-retellai`) or the REST API — `POST https://api.retellai.com/v2/create-phone-call` — plus webhooks for call events.

### What is Conductor?

Conductor is Retell's automated debugging tool, launched alongside Tell-1. It analyzes failed calls, generates test cases, and proposes targeted fixes for a human to review and deploy. It does not change a live agent on its own.

### Can the agent take payments or issue refunds?

It should not, without a human approval gate in n8n. The safe pattern is: the agent books and answers, n8n routes anything involving money to a human for approval, and the call transcript is the audit trail.

## Key Takeaways

1. **Retell crossed $100M in annualized run rate on $4.6M raised** — $10M to $100M in 17 months, profitable since 2025, 100M+ calls a month across 4,000+ businesses. All figures are company-reported.
2. **Tell-1 speaks before it finishes reasoning** — 72ms median to the first chunk of speech (vendor figure), $0.035/min, selectable November 19, 2026. The pause, not the voice, was the problem it solves.
3. **Conductor closes the loop on failed calls** — auto-diagnosis, generated test cases, proposed fixes, human approval before deployment.
4. **The n8n wiring is two webhooks** — Retell calls n8n on call events and mid-call functions; n8n calls Retell's API to place calls. The official community node covers both directions.
5. **The receptionist pattern is: trigger, ask, transfer, write back, gate** — never let the agent invent an appointment or move money without a human in the loop.

Next: pick one phone number, one agent, and one calendar, and run the missed-call callback loop for a week before you point it at real customers. If a call books wrong, the transcript will tell you whether the model, the function, or the calendar was at fault — and Conductor will propose the fix.

*Sources: Retell press release via BusinessWire, November 12, 2026; IFAI, November 12, 2026; VoiceAISpace week-46 roundup, November 13, 2026 (Tell-1 details); Retell AI n8n integration page; "An AI Voice Agent Is Just Two Webhooks: Wiring Retell to n8n in Production", DEV, July 24, 2026. Trend signal: "retell ai" — Breakout, rising related query for "n8n"; "ai receptionist for small business" — Breakout, rising query for "AI automation"; Google Trends Explore, US, past 7 days, November 21, 2026.*
