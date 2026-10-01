---
title: "Telegram Personal AI Assistant"
description: "Chat with an AI assistant on Telegram — GPT-powered replies with per-chat memory. Import-ready n8n workflow."
date: 2026-10-01
category: "chatbots"
difficulty: "beginner"
workflow: "/templates/telegram-ai-assistant.json"
integrations: ["Telegram", "OpenAI"]
---

## What it does

A Telegram bot that answers like a personal AI assistant. Send it any message — it replies with GPT, and remembers the last 10 messages of each chat so conversations feel continuous.

## Workflow nodes

1. **Telegram Trigger** — fires on every incoming message (webhook).
2. **AI Agent** — sends the message text to the chat model with a Telegram-friendly system prompt.
3. **OpenAI Chat Model** — `gpt-4o-mini` (cheap and fast; swap for any model).
4. **Window Buffer Memory** — keyed by Telegram chat ID, so each user gets their own memory.
5. **Send Reply** — posts the agent's answer back to the same chat.

## Setup

1. **Create a Telegram bot** — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token.
2. **Download the JSON** below and import it in n8n: *Workflows → ⋯ → Import from file*.
3. **Add credentials** — create a *Telegram* credential with your bot token (select it in *Telegram Trigger* and *Send Reply*), and an *OpenAI* credential (select it in *OpenAI Chat Model*).
4. **Activate** the workflow, then send your bot a message on Telegram.

## Customize it

- **Change the model** — open *OpenAI Chat Model* and pick `gpt-4o` or any other model.
- **Change the personality** — edit the system message in *AI Agent*.
- **Longer memory** — raise *Context Window Length* in *Window Buffer Memory*.
- **Restrict access** — add an IF node after the trigger checking `{{$json.message.chat.id}}` against your own chat ID, so only you can use the bot.

## Requirements

- n8n (self-hosted or cloud) with webhook access
- Telegram bot token (free, via @BotFather)
- OpenAI API key
