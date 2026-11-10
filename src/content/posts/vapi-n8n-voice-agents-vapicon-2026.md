---
title: "Vapi + n8n Voice Agents: The Wiring Pattern Behind the Breakout — VapiCon Starts Tomorrow"
description: "Vapi is a Breakout search for n8n — and VapiCon 2026 starts tomorrow. How the Vapi + n8n voice-agent wiring works, what it costs, and the traps."
date: 2026-11-10
category: news
tags: ["Vapi", "voice agents", "n8n", "VapiCon", "AI agents"]
draft: false
featured: false
image: "/og/vapi-n8n-voice-agents-vapicon-2026.webp"
---

"vapi ai" is a Breakout rising query for "n8n" in US Google Trends searches over the past 7 days — and the spike has a specific source. VapiCon 2026, the voice AI summit run by Vapi, opens tomorrow, November 11, at Fort Mason in San Francisco. The n8n builders searching for Vapi are not looking for conference news, though. They are looking for the wiring: how to put a Vapi voice agent on the phone and let an n8n workflow do everything behind it. By the end of this article you will know what Vapi does, why the VapiCon timing matters, the exact webhook pattern that connects Vapi to n8n, what a minute of it costs, and the four ways the setup breaks in production.

## What Vapi actually does

Vapi is a voice-agent orchestration platform. You configure an assistant — its prompt, its model, its voice, its transcriber, its tools — and Vapi runs the real-time pipeline: speech-to-text transcribes the caller, a large language model decides what to say, text-to-speech speaks the reply. Assistants can be grouped into Squads, which hand calls between specialized agents the way a team hands off a customer.

The important design choice is that Vapi does not lock you to one provider for each layer. You pick the transcription, model, and voice providers yourself — Deepgram or Whisper for speech-to-text, your choice of LLM, [ElevenLabs](https://try.elevenlabs.io/cortexflow) or another voice for text-to-speech — and Vapi charges a flat hosting fee on top. Telephony runs through Twilio, Vonage, Telnyx, or a Vapi-provisioned number. There is no on-premise deployment; it is a proprietary hosted service, and the EU region is limited to Premier plans.

That unbundled pricing is the first thing to understand, because it is where the cost confusion starts. Vapi's published rate is $0.05 a minute for hosting, with the speech, model, and voice providers passed through at cost. With its default providers, a minute works out to roughly $0.08 to $0.13 before telephony. New accounts start with $5 of credit and 4 concurrent calls without a package — down from 10 before Vapi repackaged its plans into Success Packages in September 2026 (Core at $29 a month, Pro at 10% of hosting with a $999 minimum). A HIPAA add-on runs $2,000 a month. The company raised a $50M Series B in May 2026, led by Peak XV, taking total funding to $72M.

## Why the search spike is happening now

VapiCon 2026 runs November 11–12 at the Festival Pavilion at Fort Mason, San Francisco. It is the second edition of the first summit dedicated entirely to voice AI — the inaugural event drew more than 850 people on October 2, 2025 — and the organizers expect 1,200+ attendees, 50+ speakers, and 20+ sponsors this time, across parallel Builder and Operator tracks.

The agenda is the reason the n8n pairing is trending rather than just the conference itself. The opening is a product and company update from Vapi, and the sessions are about the engineering of voice agents in production: Deepgram co-founder and CEO Scott Stephenson, Soniox CEO Klemen Simonic, Gradium CEO Neil Zeghidour, Cartesia co-founder Brandon Yang, Daily co-founder and CEO Kwindla Hultman Kramer, and Twilio VP and Field CTO Andy O'Dower are all on the program, alongside a speech-to-speech discussion with Justin Uberti, a practical agent-building workshop with Vapi engineer Andre Natal, a model-selection session with Kramer and Vapi's Vitali Korezki, and a panel on building voice models for real conversations. A pre-event hackathon at Vapi HQ on November 9 — with Exa, Deepgram, Manus AI, and TypeSafe AI (Jev) — set teams the challenge of building a production-grade voice agent in three hours.

In other words, the search spike is builders getting ready: the conference puts voice agents in front of a thousand-plus practitioners this week, and the first thing many of them will try afterward is wiring one into the automation stack they already run. For a large share of that audience, that stack is n8n.

## How Vapi and n8n actually connect

The pattern is the same across every independent tutorial that wires the two together, and it is worth stating plainly because it is not an official integration with a setup wizard. Vapi handles everything voice. n8n handles everything else — the business logic, the CRM updates, the appointment booking, the workflow that runs when the AI decides to take an action.

The connection is webhooks, in both directions:

**Inbound: the call comes in, Vapi answers.** A caller dials the number Vapi manages. The Vapi assistant runs the conversation — transcribing, reasoning, speaking — with no n8n involvement in the audio loop at all. n8n never hears the call; it hears about the call.

**Mid-call: the agent needs a fact, it asks n8n.** When the LLM decides it needs to check a calendar, look up a customer, or save lead information, it invokes a tool. Vapi sends an HTTP request to your n8n Webhook node carrying the tool name and its arguments. Your workflow runs — queries the calendar, checks the CRM — and returns the result to the call, live, while the caller is still on the line. This is the step that makes the agent useful instead of merely conversational: the voice is Vapi's, the answers are your systems'.

**End of call: Vapi reports back.** When the call ends, Vapi fires a webhook to n8n carrying the transcript, the extracted fields (name, phone, job type, availability), the call duration, and the recording URL. n8n parses and validates that payload — flagging incomplete bookings for manual review — and writes the result into the CRM or ticketing system.

**Outbound: n8n dials.** The flow runs in reverse for outbound calls. An n8n workflow dispatches an HTTP request to Vapi's outbound-call endpoint, injecting lead-specific variables — name, company, CRM notes — into the assistant's prompt so the opening is personalized. When the prospect shows interest, the agent triggers a tool call back to n8n mid-call to verify live calendar availability, and the end-of-call webhook routes the outcome to an AI Agent node that classifies it and books or logs accordingly.

![A vintage telephone switchboard machine for Vapi voice agents: a handset rests in its cradle while three provider dials read STT, LLM, and TTS; a patch cord runs from the board to an n8n webhook socket, a lit orange tool-call lever glows, and a transcript tape spools out of a slot at the base.](/figures/vapi-n8n-voice-agents-vapicon-2026-switchboard.svg)

*Fig 1 — The voice switchboard. The caller talks to Vapi's loop (transcribe, decide, speak); the moment the agent needs a real fact, a patch cord carries the tool call to an n8n webhook, and the answer comes back while the caller waits. The numbers are the ones from the story: $0.05/min hosting, providers at cost, 4 concurrent calls without a package, 1,200+ builders at VapiCon 2026.*

## The wiring pattern, step by step

This is the shape every tutorial converges on. Some builders use a community Vapi node; the webhook pattern below is the one every independent guide agrees on, so it is the one this article teaches.

**Step 1 — Create the assistant in Vapi.** Sign up, create an assistant, and set its system prompt, voice, transcriber, and model. Write the prompt to extract structured data — name, phone, issue, preferred time — and to confirm the details back to the caller before ending. The prompt is the product here; a vague prompt produces a vague transcript, and a vague transcript produces a booking your workflow cannot trust.

**Step 2 — Point Vapi's webhooks at n8n.** In the assistant's settings, set the server/webhook URL to your n8n Webhook node's production URL. Vapi will call it when the call ends, and again for each mid-call tool invocation. Keep the two apart in n8n: one workflow (or one branch) handles tool calls that need a live answer, another handles the end-of-call payload that needs storing.

**Step 3 — Build the n8n receiving workflow.** Add a Webhook node, set the HTTP method to POST, and copy the production URL — test URLs only work while you are clicking "Execute step" in the editor, and the workflow must be Active (toggled on) before Vapi can reach it. Inactive workflows do not respond, and this is the single most common reason a first Vapi + n8n test "does nothing." Add a Code or Set node to pull the fields out of the payload: mid-call tool calls arrive with the arguments nested under the tool-call list, while the end-of-call payload carries the transcript and extracted fields at the top level.

**Step 4 — Wire the business logic.** From the parsed payload, add the nodes that do the real work: a calendar lookup for availability, a CRM node that creates or updates the record, a Slack or Telegram message for the human when a booking is incomplete. Validate before you write — flag a missing phone number or an unparseable time for manual review instead of creating a broken record in the CRM.

**Step 5 — Call out from n8n for outbound.** For outbound campaigns, add an HTTP Request node that calls Vapi's outbound-call endpoint with the assistant ID, the phone number, and the lead variables. Then build the return path: a Webhook node that receives the end-of-call payload and routes it to classification and booking.

**Step 6 — Test with a real call, then watch the first ten.** Call the number yourself. Check three things: the transcript extracted the fields correctly, the tool call returned before the caller noticed a pause, and the CRM record matches what the caller actually said. Then watch the first ten real calls the same way — voice agents fail in ways text agents do not, and the transcript is your log.

## Four ways this breaks in production

**Latency is the product.** A voice agent that pauses for three seconds after every question sounds broken, and the caller hangs up. The webhook round trip — Vapi to n8n and back — is the slowest part of the loop, and it is the part you control. One advanced guide recommends self-hosted n8n specifically so webhook responses stay under 200ms, and reports Vapi answering in under two seconds with a tuned prompt. If your n8n instance is a free-tier cloud box on the other side of the world from your callers, the agent will sound drunk. Host the workflow close to the caller, keep the tool-call workflow short, and never put a slow node — a big spreadsheet scan, an LLM call of your own — in the live path. Do the slow work after the call ends.

**Tool-call timeouts strand the caller.** If n8n is slow or down, Vapi's tool call fails and the agent has to improvise in front of a live human. Give the assistant a fallback line in its prompt ("Let me check that and text you the confirmation") and a workflow that retries or queues the failed write instead of dropping it. The end-of-call webhook is your safety net: even if the mid-call lookup failed, the transcript still arrives, and a second workflow can reconcile it.

**Consent law applies to the voice, not just the call.** In the US, the FCC's February 2024 declaratory ruling confirmed that AI-generated voices count as "artificial" voices under the Telephone Consumer Protection Act (TCPA), so most outbound AI calls need prior express consent — the same rule that governs robocalls. India added its own layer in September 2026, with telecom rules requiring AI calls to be pre-declared to the operator. An outbound voice agent is a regulated activity, not just a workflow. Keep a consent record per number, honor do-not-call lists, and treat the compliance step as part of the build, not a footnote.

**Cost is per minute, and minutes add up while the agent rambles.** At roughly $0.08–$0.13 a minute with default providers, a single 5-minute qualification call costs under a dollar — but a thousand calls a month is $400–$650 before telephony, and an agent that asks three clarifying questions per caller burns minutes on every conversation. Cap call length in the assistant settings, write prompts that confirm once instead of looping, and watch the per-call cost in Vapi's dashboard for the first week. The pricing is honest; the surprise comes from not measuring it.

There is also a versioning trap worth naming: Vapi retired its Workflows feature on August 18, 2026, and recommends Squads as the replacement — existing workflows stopped running that day. If you are following a tutorial from before August, its workflow screenshots are describing a feature that no longer exists. Build on Squads and the current assistant model, and check Vapi's weekly changelog when something in an old guide does not match the dashboard.

## What to watch at VapiCon

The conference itself is the news hook, and the thing to watch is not the keynotes but the product update that opens the event. Vapi's last big packaging change — the September move to Success Packages, the concurrency cut from 10 calls to 4 without a package — changed what a hobby build costs. If the opening update touches pricing, concurrency, or the tool-calling surface again, every Vapi + n8n tutorial written this week, including this one, needs a second look. The second thing to watch is the model-selection and reliability sessions: the industry's open question right now is not whether voice agents can talk, but whether they can survive real callers, crosstalk, and bad audio — the exact problems the "Building Voice Models for Real Conversations" panel is about.

For n8n builders, the practical move is simple: build the wiring pattern above this week, while the conference is fresh and the tutorials are current, and treat VapiCon's announcements as the update pass. The voice layer is a commodity you rent by the minute. The workflow behind it — the calendar, the CRM, the validation, the audit trail — is the part you own, and it is the part that survives whatever the conference announces.

## FAQ

### Is Vapi free to try?

Yes, to a point. New accounts get $5 of credit and 4 concurrent calls without buying a package. After that, hosting is $0.05 a minute plus the cost of the speech, model, and voice providers you choose — roughly $0.08 to $0.13 a minute with Vapi's default providers, before telephony.

### Do I need a Vapi node in n8n to connect them?

No. The pattern every independent tutorial uses is webhooks: Vapi calls your n8n Webhook node for mid-call tool calls and again when the call ends, and n8n calls Vapi's API for outbound calls. A community Vapi node exists, but the webhook pattern is the one all the guides agree on.

### Can Vapi call my n8n workflow in the middle of a live call?

Yes — that is the core of the pattern. When the LLM invokes a tool, Vapi sends an HTTP request to your n8n webhook with the tool name and arguments, waits for the response, and feeds the result back into the conversation. Keep that workflow fast: anything over a second or two becomes an audible pause.

### Is it legal to have an AI agent make outbound sales calls?

It is regulated, not banned. In the US, AI-generated voices are "artificial" voices under the TCPA, so most outbound AI calls need the recipient's prior express consent. Keep consent records, honor do-not-call lists, and check the rules in every jurisdiction you call into — this article is not legal advice.

### What is VapiCon?

VapiCon is Vapi's voice AI summit — the first summit dedicated entirely to voice AI. The inaugural event drew 850+ people in October 2025; the 2026 edition runs November 11–12 at Fort Mason in San Francisco, with 1,200+ attendees expected across Builder and Operator tracks.

## Key Takeaways

1. **"vapi ai" is a Breakout search for "n8n" because builders want the wiring, not the conference** — Vapi on the phone, n8n behind it, connected by webhooks.
2. **The pattern is two webhooks and one API call**: Vapi calls n8n mid-call for tool lookups and again at call end with the transcript; n8n calls Vapi to place outbound calls.
3. **Cost is $0.05/min hosting plus providers at cost** — roughly $0.08–$0.13/min with defaults — and the surprise is rambling agents, not the rate.
4. **Latency is the product**: keep tool-call workflows under a second, host n8n close to your callers, and never put slow nodes in the live path.
5. **Consent law applies**: AI voices count as "artificial" under the TCPA, so outbound calling needs prior express consent and a consent record.

Next step: build the pattern above against your own calendar and CRM this week, make ten test calls, and read the transcripts before you let it near a real customer. And watch VapiCon's opening product update — if pricing or tool-calling changes, the wiring stays the same but the numbers in this article need a refresh.

*Sources: Google Trends Explore, US, past 7 days (Nov 3–10, 2026) — "vapi ai" Breakout as a rising related query for "n8n". VapiCon 2026 details: [Vapi's own blog](https://vapi.ai/blog/announcing-vapicon-2026) (Aug 12, 2026) and [audioXpress](https://audioxpress.com/news/vapicon-brings-voice-ai-models-and-real-time-audio-infrastructure-to-san-francisco). Vapi pricing and packaging: [Neura Dynamics](https://neuradynamics.ai/blogs/ai-voice-agent-platforms-compared) and [eCorpIT](https://ecorpit.com/ai-voice-agent-platforms-vapi-retell-bland-livekit-2026/) (both checked against vendor pages, Oct 2026). Vapi + n8n wiring pattern: [MM Intelligence](https://www.mmintelligence.ai/blog/vapi-n8n-voice-agent-tutorial), [GetAAB](https://www.getaab.com/blog/build-ai-phone-agent-hvac-appointment-booking), and [n8n Lab](https://n8nlab.io/blog/n8n-outbound-voice-agent).*
