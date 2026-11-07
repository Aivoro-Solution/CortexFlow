---
title: "Food Delivery Order Automator — Webhook Intake, Restaurant, Driver & Customer Updates"
description: "Food-delivery order events via webhook → dedupe, route by event, notify restaurant, drivers and customers (AI-drafted) → Sheets log + Telegram summary."
date: 2026-11-07
category: "automation"
difficulty: "intermediate"
workflow: "/templates/food-delivery-order-automator.json"
integrations: ["Webhook", "Google Sheets", "OpenAI", "Telegram", "HTTP Request"]
---

## How it works

One webhook endpoint runs your whole food-delivery order pipeline — no duplicate notifications, even when dozens of orders land in the same minute:

1. **STEP 1 — Webhook intake + instant ack** — your food-delivery app POSTs an order event (`order.created`, `restaurant.confirmed`, `driver.assigned`, `driver.picked_up`, `order.delivered`, `payment.failed`, `order.cancelled`) to the **Webhook — Order Events** node. **Normalize Order Event** flattens the payload into one clean shape, then **Respond — Order Received** answers `{"received": true, ...}` immediately, so the sender never times out while the rest of the workflow runs.
2. **STEP 2 — Idempotency dedupe** — **Read Logged Events** pulls every row from the Orders sheet and **Check Duplicate Event** looks for a matching `order_id + event_type` key. If the event was already seen, the **IF — Duplicate Event?** node routes it to **Build Duplicate Notice** and nothing is sent twice. New events get a row appended by **Log Event — Status NEW** — that row is itself the in-flight reservation, so a retry arriving mid-processing is caught as a duplicate.
3. **STEP 3 — Route by event type** — **Switch — Route by Event Type** sends each event to its own branch. Unknown event types fall through to the fallback output and are logged only.
4. **STEP 4 — Event branches** — each branch does its job and updates the sheet status before merging:
   - `order.created` → **HTTP — Notify Restaurant** posts the order to the restaurant endpoint.
   - `restaurant.confirmed` → sheet flips to `CONFIRMED`, then **HTTP — Dispatch to Drivers** notifies available delivery partners — the first driver to accept claims the delivery (claim window from `claim_timeout_minutes`).
   - `driver.assigned` → sheet flips to `DISPATCHED`, then **AI Agent — Draft Customer Update** writes a short, warm customer message via a Structured Output Parser (`gpt-4o-mini`), and **HTTP — Send Customer Update** delivers it.
   - `driver.picked_up` → sheet flips to `OUT_FOR_DELIVERY`. `order.delivered` → sheet flips to `DELIVERED`.
   - `payment.failed` → sheet flips to `PAYMENT_FAILED`, **HTTP — Hold Prep at Restaurant** tells the kitchen not to start cooking, and **Build Retry Payment Message** + **HTTP — Send Retry Payment Message** ask the customer to retry payment.
   - `order.cancelled` → sheet flips to `CANCELLED` with `Refund Review` flagged `YES`, **HTTP — Release Driver** frees the driver, and the restaurant and customer are both notified.
5. **STEP 5 — One Telegram summary** — all branches merge in **Merge — Combine Branches**, **Build Order Summary** composes a single message (order, event, outcome, and the AI-drafted customer message when there is one), and **Telegram — Send Order Update** sends it to you.

**Status flow in Sheets:** `NEW` → `CONFIRMED` → `DISPATCHED` → `OUT_FOR_DELIVERY` → `DELIVERED` (plus `PAYMENT_FAILED` and `CANCELLED`)

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A food-delivery app or backend that can POST order events as JSON webhooks — any platform works; the webhook path is `food-delivery-order` (see the [n8n Webhook node docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/) for the production URL)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- Restaurant / driver / customer notify endpoints — your own backend, or a messaging provider such as the [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp/) (the workflow posts plain JSON, so any HTTP endpoint works)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `food-delivery-order-automator.json`.
2. **CONFIG — Order Intake** — open the Set node and check `claim_timeout_minutes` (5 by default — how long drivers have to accept before the dispatch is re-offered) and `default_currency`.
3. **CONFIG — Google Sheets** — create a Google Sheet with a tab named `Orders` and headers: `Order ID | Dedupe Key | Event Type | Customer Name | Restaurant | Items | Total | Payment Status | Driver | Status | Refund Review | Timestamp | Customer Message`. Paste the spreadsheet ID into `spreadsheet_id`, then select your Google Sheets credential and the sheet in **Read Logged Events**, **Log Event — Status NEW**, and all seven **Update Sheet — Status …** nodes.
4. **CONFIG — Restaurant & Dispatch** — paste your three endpoint URLs (`restaurant_endpoint`, `driver_dispatch_endpoint`, `customer_notify_endpoint`) and your payment provider name. These are the only places your backend URLs live — no other node hardcodes them.
5. **AI customer updates** — select your OpenAI credential in **OpenAI Chat Model — Customer Updates** (model is `gpt-4o-mini`). The parser schema (`message_text`, `eta_minutes`, `tone`) is already set in **Structured Output Parser — Customer Message**; adjust the agent's system message if you want a different tone.
6. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in **Telegram — Send Order Update**, then **activate** the workflow and point your app at the webhook production URL.
7. **Test it** — POST a sample `order.created` event (see the example payload below) and watch the row appear in Sheets with status `NEW`, then POST the same event again and confirm the second one is skipped as a duplicate.

Example webhook payload:

```json
{
  "order_id": "ORD-1042",
  "event_type": "order.created",
  "customer_name": "Priya Sharma",
  "customer_phone": "+919999999999",
  "restaurant_id": "rest_88",
  "restaurant_name": "Spice Route Kitchen",
  "items": [{ "name": "Butter Chicken", "qty": 2 }, { "name": "Naan", "qty": 4 }],
  "total": 24.5,
  "currency": "USD",
  "payment_status": "paid"
}
```

## Customize it

- **Real restaurant POS** — point `restaurant_endpoint` at your POS or kitchen-display-system webhook instead of a generic endpoint; the payload already carries `order_id`, `items`, and `total`.
- **SMS instead of app push** — swap the `customer_notify_endpoint` for a Twilio or Vonage SMS endpoint; the JSON body stays the same shape.
- **Re-dispatch on timeout** — if no driver claims within `claim_timeout_minutes`, add a Wait node after **HTTP — Dispatch to Drivers** and re-POST the dispatch to a wider radius.
- **Refund automation** — the `CANCELLED` branch flags `Refund Review: YES` for a human check; wire your payment provider's refund API into that branch once you trust the flow.
- **Delivery-time SLA alerts** — add a scheduled sweep over the Orders sheet: any row stuck in `DISPATCHED` for over 30 minutes gets a Telegram alert.
- **More events** — the Switch already handles `driver.picked_up` and `order.delivered`; add a `driver.arriving` output the same way if your app emits it.
- **Cheaper AI** — `gpt-4o-mini` is already the default; customer messages are short, so cost per order is a fraction of a cent.
