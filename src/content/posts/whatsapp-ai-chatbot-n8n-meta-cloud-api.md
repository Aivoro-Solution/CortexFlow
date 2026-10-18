---
title: "How to Build a WhatsApp AI Chatbot with n8n and Meta Cloud API (Step-by-Step)"
description: "Build a WhatsApp AI chatbot with n8n + Meta Cloud API: webhooks, permanent token, AI replies, templates, and the 24-hour rule."
date: 2026-10-18
category: chatbots
tags: ["n8n", "whatsapp", "ai-chatbot", "meta-cloud-api", "tutorial"]
draft: false
featured: false
image: "/og/whatsapp-ai-chatbot-n8n-meta-cloud-api.webp"
---

WhatsApp is where your customers already are — so an AI chatbot that lives inside WhatsApp is one of the highest-leverage automations you can build. The official path is Meta's **WhatsApp Cloud API** (the API Meta itself hosts; no third-party gateway, no phone left plugged in somewhere), wired into **n8n** so every incoming message triggers a workflow that thinks with an AI agent and replies.

A **webhook** is a URL you give Meta; every time someone messages your number, Meta POSTs the message to that URL. In n8n, that URL comes from a trigger node, and the rest of the workflow is just nodes: parse the message, ask the AI, send the reply.

**By the end, you will have:** a live WhatsApp number that answers messages with an AI agent, remembers the conversation, and falls back to approved template messages outside the 24-hour reply window.

**Prerequisites**

- A Meta account and a Meta Developer app (free) — developers.facebook.com
- An n8n instance reachable from the public internet (n8n Cloud, or self-hosted with HTTPS). Meta will not call a `localhost` URL.
- An OpenAI API key (we use `gpt-4o-mini` — cheap and fast enough for chat)
- Basic comfort pasting values into forms. Nothing else.

**Example placeholders** — replace these everywhere:

- `<VERIFY_TOKEN>` — a random secret you invent (e.g. `wa-verify-9f3Kx`), used once during webhook setup
- `<ACCESS_TOKEN>` — your WhatsApp Cloud API access token
- `<PHONE_NUMBER_ID>` — the ID of your WhatsApp sender number (not the phone number itself)
- `<WABA_ID>` — your WhatsApp Business Account ID
- Graph API version: pin one in every endpoint, e.g. `v24.0` (use whatever is current on developers.facebook.com; never leave it unversioned)

![A person chatting on a messaging app, like the WhatsApp conversations your bot will handle](/images/whatsapp-ai-chatbot-n8n-meta-cloud-api/phone-chat.jpg)

## Step 1 - Create the Meta app and add the WhatsApp product

In the Meta Developer dashboard, create an app (type: **Business**), open it, and under **Add products** click **Set up** on **WhatsApp**. This opens the **API Setup** page — your mission control for everything that follows.

You should see: a **temporary access token** (expires in about 24 hours — fine for testing, never for production), a **test phone number**, and its **Phone Number ID**. Note down the Phone Number ID now; the WhatsApp "send" endpoints address numbers by ID, not by the digits you dial.

## Step 2 - Add your own phone number as a test recipient

In API Setup, under **To**, add your own mobile number. Meta sends it a 6-digit verification code via WhatsApp/SMS; enter it to link the number.

> Why this step: the sandbox only delivers messages to verified test numbers. Trying to message an unverified number silently goes nowhere, and this is the single most common "my bot doesn't reply" cause I see in forum threads.

## Step 3 - Get a permanent access token (do not skip)

The temporary token from Step 1 dies in ~24 hours. For a real bot you need a **System User token**:

1. Go to **Business Settings → Users → System users** and create one.
2. Assign it your WhatsApp app, with the **WhatsApp Business Account** asset attached.
3. Generate a token with the `whatsapp_business_messaging` scope (add `whatsapp_business_management` if your workflow manages templates too).

Save it as `<ACCESS_TOKEN>`. It has no expiry. Treat it like a password — it can send messages as your business.

## Step 4 - Create the n8n workflow with the WhatsApp Trigger node

In n8n, create a new workflow and add the **WhatsApp Trigger** node. For **Credentials**, create a **WhatsApp API** OAuth credential using your Meta app's **App ID** and **App Secret** (both on your app's dashboard under Settings → Basic).

Here's the part that saves you an hour: with this credential in place, **n8n registers the webhook URL with Meta automatically** when the workflow is active. You don't hand-copy webhook URLs into the Meta dashboard.

Prefer the manual route? Use a plain **Webhook** node instead (Method: GET first — Meta's verification handshake is a GET request with `hub.mode=subscribe`, `hub.challenge`, and `hub.verify_token` query parameters). Then in Meta's **WhatsApp → Configuration**, paste the webhook URL, enter your `<VERIFY_TOKEN>`, and click **Verify and save**. Meta calls your URL with the challenge; your workflow must echo `hub.challenge` back with HTTP 200. In n8n this means: Webhook node (Response: "Using Respond to Webhook node") → IF node checking `hub.verify_token` equals your token → **Respond to Webhook** node returning the challenge as plain text. Once verified, switch the Webhook node to POST and let Meta's `messages` events flow.

Either way, subscribe to the **`messages`** webhook field (add `message_status` too if you want delivery/read receipts — the trigger fires on those as well, so handle them separately).

**Verify:** in the Meta dashboard, the webhook field shows a green checkmark and "Subscribed". If verification fails, the verify token in Meta and in your workflow don't match — that's the cause 9 times out of 10.

## Step 5 - Parse the incoming message

Activate the workflow (webhooks only fire on **active** workflows in production mode). Send "hello" from your test phone to the test number.

WhatsApp POSTs a nested payload. The message lives at `entry[0].changes[0].value.messages[0]`:

- `messages[0].from` — the sender's number (the `wa_id`)
- `messages[0].text.body` — the message text (only when `messages[0].type` is `"text"`)
- `messages[0].type` — `text`, `image`, `audio`, `interactive`, etc.

Add an **IF** node right after the trigger: continue only when `messages` exists in the payload (status-update events have no `messages` array and would crash the downstream nodes). Then a **Set** node to pull `from`, `text.body`, and `type` into clean fields. This two-node guard is the difference between a bot that works and one that errors at 3 AM on a delivery receipt.

## Step 6 - Generate the reply with an AI agent

Add an **AI Agent** node (n8n's agent node, v1.7+). Connect:

- **Chat model:** OpenAI `gpt-4o-mini` (create the OpenAI credential with your API key)
- **Memory:** **Window Buffer Memory** — this is what gives the bot conversational context instead of amnesia per message. For production, swap it for **Redis/Postgres Chat Memory** keyed by the sender's number so memory survives restarts.
- **System prompt:** tell it who it is, e.g. "You are the support assistant for Acme Store. Answer briefly, in the customer's language. If you don't know, say so and offer to connect a human."

Feed the parsed message text in as the prompt. Optionally attach a **Structured Output Parser** if you need the reply in a strict shape (e.g. `{ "reply": "...", "needs_human": true/false }`) for routing.

**Verify:** run the workflow in test mode, send a message, and check the AI Agent node's output — you should see a sensible reply in the execution log before anything is sent anywhere.

## Step 7 - Send the reply with the WhatsApp Business Cloud node

Add the **WhatsApp Business Cloud** node, operation **Send message**:

- **Credentials:** new **WhatsApp API** credential (API key type) with your `<ACCESS_TOKEN>` and `<WABA_ID>`
- **From (Phone Number ID):** `<PHONE_NUMBER_ID>`
- **To (Recipient):** `={{ $json.from }}` (the sender from Step 5)
- **Message Type:** **Text**, body = the AI's reply

The node POSTs to `https://graph.facebook.com/v24.0/<PHONE_NUMBER_ID>/messages` with the standard messaging-product JSON behind the scenes. Keep the version pinned.

**Verify:** send a message from your phone — the AI's reply should arrive in WhatsApp within seconds. Check the execution log: green on every node.

![A phone showing a lively chat thread — the kind of back-and-forth your AI agent will power](/images/whatsapp-ai-chatbot-n8n-meta-cloud-api/chatbot-bot.jpg)

## Step 8 - Respect the 24-hour messaging window (this is the rule that gets bots banned)

Meta's **24-hour customer service window**: you can send free-form messages (like the AI replies above) only within 24 hours of the customer's last message. After the window closes, you may only send **approved template messages** — pre-written messages in the **utility**, **marketing**, or **authentication** categories that Meta reviews (approval typically takes 24–48 hours; write them in the customer's language, no marketing fluff in utility templates).

In n8n: the same WhatsApp Business Cloud node has a **Send template** operation. Build a branch — IF node checking "last customer message older than 24h" → send template (e.g. a utility template: "Hi {{1}}, following up on your question…") → done. Never try to sneak free-form text outside the window; Meta rejects it and repeated attempts hurt your quality rating.

> Pricing note: messaging is conversation-based. Marketing and utility template messages are billed per delivery; **1,000 free service conversations per month** are included. Check Meta's current pricing page before you scale — it changes.

## Step 9 - Run the full testing checklist

1. **Verify token mismatch** — webhook won't verify; re-enter `<VERIFY_TOKEN>` identically in both places.
2. **Trigger never fires** — workflow not active, or you messaged the bot's own number (sending to the same number doesn't trigger events). Use a different phone.
3. **Replies stop after a day** — the temporary token expired. You skipped Step 3; go back and install the System User token.
4. **"Outside 24h window" errors** — route through template messages (Step 8).
5. **Bot answers its own messages in a loop** — your IF guard from Step 5 must also ignore messages where `from` equals your own sender number.

**You now have:** a WhatsApp number powered by an AI agent — incoming messages trigger the workflow, the agent replies with conversation memory, and the 24-hour window plus templates keep you compliant. The natural next step is plugging in tools: let the agent check order status or book appointments via HTTP Request nodes before it answers.

## Key Takeaways

- Meta's WhatsApp Cloud API is the official, phone-free path — app + WhatsApp product + webhook + System User token.
- n8n's WhatsApp Trigger node with the Meta OAuth credential auto-registers your webhook; the manual Webhook-node route needs the `hub.challenge` echo.
- Guard every run with an IF node: status events carry no `messages` array.
- Window Buffer Memory gives the bot a brain; key it per sender number for real conversations.
- Outside the 24-hour window, only approved template messages — no exceptions.
- Permanent token via System User; the sandbox token dies in ~24 hours.

## FAQ

### Do I need a verified business to start?

No. The sandbox (test number + up to 5 test recipients) works with any Meta Developer account. You need business verification only when you go live with your own number at scale.

### Can the bot send images, buttons, or lists?

Yes — the WhatsApp Business Cloud node supports media messages and interactive messages (buttons, lists). The AI can decide which to send; interactive replies arrive back as `interactive` type payloads, so extend your Step 5 parser.

### What does it cost to run?

n8n self-hosted is free; OpenAI `gpt-4o-mini` costs fractions of a cent per reply; Meta includes 1,000 free service conversations monthly, then conversation-based pricing applies. A small support bot typically runs on pocket change.

### Will Meta ban my number for automation?

Not for using the official Cloud API as documented. Bans happen with unofficial gateways, spammy broadcast behavior, or low quality ratings from users blocking/reporting you. Keep messages wanted and within the rules.

---
Images: Pexels
