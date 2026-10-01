---
title: "Telegram Personal AI Assistant"
description: "Chat with an AI assistant on Telegram — GPT-powered replies with per-chat memory. Import-ready n8n workflow."
date: 2026-10-01
category: "chatbots"
difficulty: "beginner"
workflow: "/templates/telegram-ai-assistant.json"
integrations: ["Telegram", "OpenAI"]
---

## How it works

1. **Telegram Trigger receives the message** — the workflow fires on every incoming Telegram message via webhook.
2. **The AI Agent reads the message** — it takes the message text and sends it to the chat model with a Telegram-friendly system prompt.
3. **OpenAI generates the reply** — `gpt-4o-mini` writes the answer (cheap and fast; swap it for any model).
4. **Window Buffer Memory keeps context** — the last 10 messages are remembered per chat, keyed by Telegram chat ID, so every user gets their own continuous conversation.
5. **Send Reply posts the answer** — the agent's output is sent back to the same Telegram chat.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- A Telegram bot token — message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, and copy the token it gives you
- An OpenAI API key — get one at [platform.openai.com](https://platform.openai.com) → API keys

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your Telegram credential** — in n8n go to *Credentials → New → Telegram*, paste your bot token, and save. Then open the *Telegram Trigger* node and the *Send Reply* node and select your credential in each.
4. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, and save. Then open the *OpenAI Chat Model* node and select your credential.
5. **Activate** the workflow (toggle, top-right), then send your bot a message on Telegram.

## Customize it

- **Change the model** — open the *OpenAI Chat Model* node and pick `gpt-4o` or any other model.
- **Change the personality** — edit the system message in the *AI Agent* node.
- **Longer memory** — raise *Context Window Length* in the *Window Buffer Memory* node.
- **Restrict access** — add an IF node after the trigger checking `{{$json.message.chat.id}}` against your own chat ID, so only you can use the bot.
