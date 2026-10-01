---
title: "WhatsApp Business Support & Sales Chatbot"
description: "AI chatbot for WhatsApp Business: answers FAQs, qualifies buyers, and hands off to a human when needed."
date: 2026-10-01
category: "chatbots"
difficulty: "intermediate"
workflow: "/templates/whatsapp-business-chatbot.json"
integrations: ["WhatsApp", "OpenAI"]
---

## How it works

1. **WhatsApp Trigger** — fires on every incoming WhatsApp message via the WhatsApp Business Cloud API webhook.
2. **AI Agent** — reads the message and drafts a reply as a support and sales assistant. If the customer asks for a human or a pricing call, it appends a `[HANDOFF]` flag to its reply.
3. **OpenAI Chat Model** — `gpt-4o-mini` powers the agent's replies (cheap and fast; swap for any model).
4. **Window Buffer Memory** — keyed by the sender's phone number, so each customer gets their own conversation history.
5. **IF Handoff Needed** — checks the agent's reply for the `[HANDOFF]` flag and routes the conversation accordingly.
6. **Format Handoff Summary** — on the handoff path, packages the customer's phone number, their last message, and the agent's summary into one clean object.
7. **WhatsApp Agent Alert** — on the handoff path, messages your agent's number so a human can take over the chat.
8. **Slack Team Notify** — on the handoff path, posts the handoff summary to your team channel so nothing gets missed.
9. **Send Agent Reply** — on the normal path, sends the AI's reply straight back to the customer on WhatsApp.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- A Meta developer account with a WhatsApp Business Cloud API app — create one at developers.facebook.com, go to My Apps, create a Business-type app, add the WhatsApp product, then copy your Phone Number ID and access token from WhatsApp → API Setup
- An OpenAI account — get an API key at platform.openai.com → API keys
- A Slack workspace for the team handoff alerts

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your WhatsApp credential** — in n8n go to *Credentials → New → WhatsApp API*, paste the access token from your Meta app, and save. Then open *WhatsApp Trigger* and both WhatsApp send nodes and select this credential. In the two send nodes, also set your Phone Number ID as the sender.
4. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, and save. Then open the *OpenAI Chat Model* node and select your credential.
5. **Create your Slack credential** — in n8n go to *Credentials → New → Slack*, connect via OAuth, and save. Then open *Slack Team Notify*, select your credential, and set the channel name.
6. **Set your agent number** — open *WhatsApp Agent Alert* and replace `YOUR_AGENT_PHONE_NUMBER` with the phone number (country code included, no `+`) that should receive handoff requests.
7. **Activate** the workflow (toggle, top-right), then message your WhatsApp Business number to test it.

Note: WhatsApp lets you reply freely inside the 24-hour customer-service window. Business-initiated messages outside that window need an approved message template.

## Customize it

- **Change when handoffs happen** — edit the system message in *AI Agent* to change the rules for raising the `[HANDOFF]` flag (for example, hand off on refund requests or orders above a value).
- **Qualify buyers harder** — extend the system prompt with your pricing, plans, and the exact questions every buyer must answer.
- **Tune the memory** — raise or lower *Context Window Length* in *Window Buffer Memory* to remember more or less of each conversation.
- **Add a human-approval pause** — insert a *Wait* node on the handoff path before the alert goes out, so a supervisor can review flagged chats first.
