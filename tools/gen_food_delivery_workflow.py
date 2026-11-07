#!/usr/bin/env python3
"""Generate the Food Delivery Order Automator n8n workflow JSON."""
import json, uuid

def uid():
    return str(uuid.uuid4())

def sticky(name, content, x, y, w, h, color=4):
    return {
        "parameters": {"content": content, "height": h, "width": w, "color": color},
        "id": uid(), "name": name, "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1, "position": [x, y],
    }

def set_node(name, assigns, x, y):
    return {
        "parameters": {
            "assignments": {"assignments": [
                {"id": uid(), "name": k, "type": "string", "value": v}
                for k, v in assigns
            ]},
            "options": {},
        },
        "id": uid(), "name": name, "type": "n8n-nodes-base.set",
        "typeVersion": 3.4, "position": [x, y],
    }

def code_node(name, js, x, y, run_once_all=True):
    return {
        "parameters": {"jsCode": js, "mode": "runOnceForAllItems" if run_once_all else "runOnceForEachItem"},
        "id": uid(), "name": name, "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [x, y],
    }

def sheets_node(name, operation, columns_value, matching, x, y):
    return {
        "parameters": {
            "operation": operation,
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": "Orders"},
            "columns": {
                "mappingMode": "defineBelow",
                "matchingColumns": matching,
                "schema": [],
                "attemptToConvertTypes": False, "convertFieldsToString": False,
                "value": columns_value,
            },
            "options": {},
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

def http_node(name, url_expr, json_body, x, y):
    return {
        "parameters": {
            "method": "POST",
            "url": url_expr,
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": json_body,
            "options": {},
        },
        "id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2, "position": [x, y],
    }

N = "Normalize Order Event"  # shortcut for expression references
EV = "$('Normalize Order Event').first().json"

nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY — Title",
    "## \U0001f354 FOOD DELIVERY ORDER AUTOMATOR\n"
    "**What it does:** Your food-delivery app posts order events to a webhook \u2192 the workflow acks instantly \u2192 dedupes repeat events \u2192 routes by event type \u2192 notifies the restaurant, dispatches drivers (first-accept claims it), sends AI-drafted customer updates, handles failed payments and cancellations \u2192 logs every stage to Google Sheets \u2192 Telegram summary.\n\n"
    "**You'll need:**\n- A food-delivery app/backend that POSTs order webhooks (or any system that can POST JSON)\n- OpenAI API key (platform.openai.com)\n- Google Sheets OAuth2 credentials\n- Telegram bot token + your chat ID (@BotFather \u2192 /newbot)\n- Restaurant / driver / customer notify endpoints (your backend, WhatsApp Business API, or any HTTP endpoint)\n\n"
    "**Status flow in Sheets:** `NEW` \u2192 `CONFIRMED` \u2192 `DISPATCHED` \u2192 `OUT_FOR_DELIVERY` \u2192 `DELIVERED` (plus `PAYMENT_FAILED` and `CANCELLED`)\n"
    "**Events:** `order.created` \u00b7 `restaurant.confirmed` \u00b7 `driver.assigned` \u00b7 `driver.picked_up` \u00b7 `order.delivered` \u00b7 `payment.failed` \u00b7 `order.cancelled`",
    -240, -240, 2840, 220, color=5))

nodes.append(sticky("STICKY — STEP 1",
    "## STEP 1 \u2014 Webhook intake + instant ack\nFood-delivery app POSTs an order event \u2192 normalize into one clean shape \u2192 Respond to Webhook answers immediately so the sender never times out while the rest runs.",
    -240, 180, 1160, 420))

nodes.append(sticky("STICKY — STEP 2",
    "## STEP 2 \u2014 Idempotency dedupe\nRead logged events \u2192 if this order_id + event_type was already seen, skip all notifications (no duplicate messages when many orders arrive at once). New events get a row appended with status `NEW` \u2014 the row itself is the in-flight reservation.",
    940, 180, 1060, 420))

nodes.append(sticky("STICKY — STEP 3",
    "## STEP 3 \u2014 Route by event type\nSwitch sends each event to its own branch: created \u2192 restaurant, confirmed \u2192 dispatch, assigned \u2192 AI customer update, picked up / delivered \u2192 status, payment failed \u2192 hold + retry, cancelled \u2192 release + refund flag.",
    2020, 180, 560, 420))

nodes.append(sticky("STICKY — STEP 4",
    "## STEP 4 \u2014 Event branches\nRestaurant confirmation, driver dispatch (first-accept claims it), AI-drafted customer updates, failed-payment hold + retry, cancellation release + refund review. Every branch updates the sheet status before merging.",
    2640, -240, 1160, 220))

nodes.append(sticky("STICKY — STEP 5",
    "## STEP 5 \u2014 One Telegram summary\nAll branches merge \u2192 a single summary (order, event, outcome, AI-drafted customer message) \u2192 Telegram.",
    3840, -240, 940, 220))

# ---------- MAIN CHAIN ----------
nodes.append({
    "parameters": {
        "httpMethod": "POST",
        "path": "food-delivery-order",
        "responseMode": "responseNode",
        "options": {},
    },
    "id": uid(), "name": "Webhook — Order Events", "type": "n8n-nodes-base.webhook",
    "typeVersion": 2, "position": [0, 300], "webhookId": uid(),
})

nodes.append(set_node("CONFIG — Order Intake", [
    ("sheet_name", "Orders"),
    ("supported_events", "order.created, restaurant.confirmed, driver.assigned, driver.picked_up, order.delivered, payment.failed, order.cancelled"),
    ("claim_timeout_minutes", "5"),
    ("default_currency", "USD"),
], 240, 300))

nodes.append(code_node("Normalize Order Event", """// Normalize the incoming order event into one clean shape
const raw = $input.first().json;
const b = raw.body && typeof raw.body === 'object' ? raw.body : raw;
const orderId = String(b.order_id || b.orderId || '');
const eventType = String(b.event_type || b.eventType || b.type || 'order.created');
const items = Array.isArray(b.items)
  ? b.items.map(i => typeof i === 'string' ? i : `${i.qty || 1}x ${i.name || 'item'}`).join('; ')
  : String(b.items || '');
return [{ json: {
  order_id: orderId,
  event_type: eventType,
  dedupe_key: `${orderId}|${eventType}`,
  customer_name: b.customer_name || b.customerName || '',
  customer_phone: b.customer_phone || b.customerPhone || '',
  restaurant_id: b.restaurant_id || b.restaurantId || '',
  restaurant_name: b.restaurant_name || b.restaurantName || '',
  items,
  total: b.total != null ? String(b.total) : '',
  currency: b.currency || 'USD',
  payment_status: b.payment_status || b.paymentStatus || '',
  driver_id: b.driver_id || b.driverId || '',
  driver_name: b.driver_name || b.driverName || '',
  timestamp: b.timestamp || new Date().toISOString(),
  status: 'NEW',
  refund_review: '',
  customer_message: '',
}}];""", 480, 300))

nodes.append({
    "parameters": {
        "respondWith": "json",
        "responseBody": "={\"received\": true, \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"event_type\": \"{{ $('Normalize Order Event').first().json.event_type }}\", \"status\": \"queued\"}",
        "options": {},
    },
    "id": uid(), "name": "Respond — Order Received", "type": "n8n-nodes-base.respondToWebhook",
    "typeVersion": 1.1, "position": [720, 300],
})

nodes.append(set_node("CONFIG — Google Sheets", [
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("sheet_name", "Orders"),
], 960, 300))

nodes.append({
    "parameters": {
        "operation": "read",
        "resource": "sheetWithinDocument",
        "documentId": {"__rl": True, "mode": "list", "value": ""},
        "sheetName": {"__rl": True, "mode": "list", "value": "Orders"},
        "options": {},
    },
    "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
    "id": uid(), "name": "Read Logged Events", "type": "n8n-nodes-base.googleSheets",
    "typeVersion": 4.5, "position": [1200, 300],
})

nodes.append(code_node("Check Duplicate Event", """// Idempotency: skip events whose order_id + event_type is already logged
const event = $('Normalize Order Event').first().json;
const seen = new Set(
  $('Read Logged Events').all()
    .map(i => (i.json['Dedupe Key'] || i.json.dedupe_key || '').trim())
    .filter(Boolean)
);
const isDuplicate = seen.has(event.dedupe_key);
return [{ json: { ...event, duplicate_flag: isDuplicate ? 'true' : 'false', is_duplicate: isDuplicate } }];""", 1440, 300))

nodes.append({
    "parameters": {
        "conditions": {
            "combinator": "and",
            "conditions": [{
                "id": "if-duplicate",
                "leftValue": "={{ $json.duplicate_flag }}",
                "rightValue": "true",
                "operator": {"type": "string", "operation": "equals", "name": "filter.operator.string.equals"},
            }],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "options": {},
    },
    "id": uid(), "name": "IF — Duplicate Event?", "type": "n8n-nodes-base.if",
    "typeVersion": 2.2, "position": [1680, 300],
})

nodes.append(code_node("Build Duplicate Notice", """const e = $('Normalize Order Event').first().json;
return [{ json: {
  ...e,
  duplicate: true,
  note: `Duplicate ${e.event_type} for order ${e.order_id} — already logged, no notifications sent.`,
}}];""", 1920, 100))

nodes.append(sheets_node("Log Event — Status NEW", "append", {
    "Order ID": "={{ $('Normalize Order Event').first().json.order_id }}",
    "Dedupe Key": "={{ $('Normalize Order Event').first().json.dedupe_key }}",
    "Event Type": "={{ $('Normalize Order Event').first().json.event_type }}",
    "Customer Name": "={{ $('Normalize Order Event').first().json.customer_name }}",
    "Restaurant": "={{ $('Normalize Order Event').first().json.restaurant_name }}",
    "Items": "={{ $('Normalize Order Event').first().json.items }}",
    "Total": "={{ $('Normalize Order Event').first().json.total }}",
    "Payment Status": "={{ $('Normalize Order Event').first().json.payment_status }}",
    "Driver": "={{ $('Normalize Order Event').first().json.driver_name }}",
    "Status": "NEW",
    "Refund Review": "",
    "Timestamp": "={{ $('Normalize Order Event').first().json.timestamp }}",
    "Customer Message": "",
}, [], 1920, 300))

# ---------- SWITCH ----------
def switch_rule(event, key):
    return {
        "conditions": {
            "combinator": "and",
            "conditions": [{
                "id": uid(),
                "leftValue": "={{ $('Normalize Order Event').first().json.event_type }}",
                "rightValue": event,
                "operator": {"type": "string", "operation": "equals", "name": "filter.operator.string.equals"},
            }],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "outputKey": key,
        "renameOutput": True,
    }

nodes.append({
    "parameters": {
        "rules": {"values": [
            switch_rule("order.created", "Order Created"),
            switch_rule("restaurant.confirmed", "Restaurant Confirmed"),
            switch_rule("driver.assigned", "Driver Assigned"),
            switch_rule("driver.picked_up", "Driver Picked Up"),
            switch_rule("order.delivered", "Order Delivered"),
            switch_rule("payment.failed", "Payment Failed"),
            switch_rule("order.cancelled", "Order Cancelled"),
        ]},
        "options": {"fallbackOutput": "extra", "renameFallbackOutput": "Unknown Event"},
    },
    "id": uid(), "name": "Switch — Route by Event Type", "type": "n8n-nodes-base.switch",
    "typeVersion": 3.2, "position": [2160, 300],
})

# ---------- BRANCH A: order.created → notify restaurant ----------
nodes.append(set_node("CONFIG — Restaurant & Dispatch", [
    ("restaurant_endpoint", "PASTE_YOUR_RESTAURANT_WEBHOOK_URL"),
    ("driver_dispatch_endpoint", "PASTE_YOUR_DRIVER_DISPATCH_URL"),
    ("customer_notify_endpoint", "PASTE_YOUR_CUSTOMER_NOTIFY_URL"),
    ("payment_provider", "PASTE_YOUR_PAYMENT_PROVIDER (e.g. stripe)"),
], 2640, 60))

nodes.append(http_node("HTTP — Notify Restaurant",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.restaurant_endpoint }}",
    "={\"action\": \"new_order\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"restaurant_id\": \"{{ $('Normalize Order Event').first().json.restaurant_id }}\", \"restaurant_name\": \"{{ $('Normalize Order Event').first().json.restaurant_name }}\", \"items\": \"{{ $('Normalize Order Event').first().json.items }}\", \"total\": \"{{ $('Normalize Order Event').first().json.total }}\", \"currency\": \"{{ $('Normalize Order Event').first().json.currency }}\", \"customer_name\": \"{{ $('Normalize Order Event').first().json.customer_name }}\"}",
    2880, 60))

# ---------- BRANCH B: restaurant.confirmed → CONFIRMED + dispatch drivers ----------
nodes.append(sheets_node("Update Sheet — Status CONFIRMED", "update", {
    "Dedupe Key": "={{ $('Normalize Order Event').first().json.dedupe_key }}",
    "Status": "CONFIRMED",
}, ["Dedupe Key"], 2640, 220))

nodes.append(http_node("HTTP — Dispatch to Drivers",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.driver_dispatch_endpoint }}",
    "={\"action\": \"dispatch\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"restaurant_name\": \"{{ $('Normalize Order Event').first().json.restaurant_name }}\", \"items\": \"{{ $('Normalize Order Event').first().json.items }}\", \"total\": \"{{ $('Normalize Order Event').first().json.total }}\", \"claim_timeout_minutes\": \"{{ $('CONFIG — Order Intake').first().json.claim_timeout_minutes }}\", \"note\": \"First driver to accept claims this delivery.\"}",
    2880, 220))

# ---------- BRANCH C: driver.assigned → DISPATCHED + AI customer update ----------
nodes.append(sheets_node("Update Sheet — Status DISPATCHED", "update", {
    "Dedupe Key": "={{ $('Normalize Order Event').first().json.dedupe_key }}",
    "Driver": "={{ $('Normalize Order Event').first().json.driver_name }}",
    "Status": "DISPATCHED",
}, ["Dedupe Key"], 2640, 380))

nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are the customer-support copywriter for a food-delivery app. Draft one short, warm customer status update (max 2 sentences, under 280 characters) for the order below. Mention the driver by name when known. No placeholders, no brackets, no generic fluff. Output ONLY via the structured output parser.",
        },
        "text": "=Order {{ $('Normalize Order Event').first().json.order_id }} from {{ $('Normalize Order Event').first().json.restaurant_name }}. Event: driver assigned. Driver: {{ $('Normalize Order Event').first().json.driver_name }}. Items: {{ $('Normalize Order Event').first().json.items }}. Total: {{ $('Normalize Order Event').first().json.currency }} {{ $('Normalize Order Event').first().json.total }}.",
    },
    "id": uid(), "name": "AI Agent — Draft Customer Update", "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7, "position": [2880, 380],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model — Customer Updates", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.2, "position": [2880, 640],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n  \"message_text\": \"the customer update message, max 280 characters\",\n  \"eta_minutes\": 0,\n  \"tone\": \"friendly / apologetic / neutral\"\n}",
    },
    "id": uid(), "name": "Structured Output Parser — Customer Message", "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.2, "position": [3120, 640],
})

nodes.append(http_node("HTTP — Send Customer Update",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.customer_notify_endpoint }}",
    "={\"action\": \"customer_update\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"customer_name\": \"{{ $('Normalize Order Event').first().json.customer_name }}\", \"customer_phone\": \"{{ $('Normalize Order Event').first().json.customer_phone }}\", \"message\": \"{{ $('AI Agent — Draft Customer Update').first().json.output.message_text }}\", \"eta_minutes\": \"{{ $('AI Agent — Draft Customer Update').first().json.output.eta_minutes }}\"}",
    3120, 380))

# ---------- BRANCH D: driver.picked_up → OUT_FOR_DELIVERY ----------
nodes.append(sheets_node("Update Sheet — Status OUT_FOR_DELIVERY", "update", {
    "Dedupe Key": "={{ $('Normalize Order Event').first().json.dedupe_key }}",
    "Status": "OUT_FOR_DELIVERY",
}, ["Dedupe Key"], 2640, 540))

# ---------- BRANCH E: order.delivered → DELIVERED ----------
nodes.append(sheets_node("Update Sheet — Status DELIVERED", "update", {
    "Dedupe Key": "={{ $('Normalize Order Event').first().json.dedupe_key }}",
    "Status": "DELIVERED",
}, ["Dedupe Key"], 2640, 700))

# ---------- BRANCH F: payment.failed → hold prep + retry message ----------
nodes.append(sheets_node("Update Sheet — Status PAYMENT_FAILED", "update", {
    "Dedupe Key": "={{ $('Normalize Order Event').first().json.dedupe_key }}",
    "Payment Status": "FAILED",
    "Status": "PAYMENT_FAILED",
}, ["Dedupe Key"], 2640, 860))

nodes.append(http_node("HTTP — Hold Prep at Restaurant",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.restaurant_endpoint }}",
    "={\"action\": \"hold_prep\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"restaurant_id\": \"{{ $('Normalize Order Event').first().json.restaurant_id }}\", \"reason\": \"payment_failed\", \"note\": \"Do not start cooking until payment clears.\"}",
    2880, 860))

nodes.append(code_node("Build Retry Payment Message", """const e = $('Normalize Order Event').first().json;
const msg = `Hi ${e.customer_name || 'there'} — your payment for order ${e.order_id} (${e.restaurant_name}) failed, so we have paused preparation. Tap your payment link to retry — your food starts cooking as soon as payment clears. Total: ${e.currency} ${e.total}.`;
return [{ json: { ...e, retry_message: msg } }];""", 3120, 860))

nodes.append(http_node("HTTP — Send Retry Payment Message",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.customer_notify_endpoint }}",
    "={\"action\": \"retry_payment\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"customer_name\": \"{{ $('Normalize Order Event').first().json.customer_name }}\", \"customer_phone\": \"{{ $('Normalize Order Event').first().json.customer_phone }}\", \"message\": \"{{ $json.retry_message }}\"}",
    3360, 860))

# ---------- BRANCH G: order.cancelled → release driver, notify, refund flag ----------
nodes.append(sheets_node("Update Sheet — Status CANCELLED", "update", {
    "Dedupe Key": "={{ $('Normalize Order Event').first().json.dedupe_key }}",
    "Status": "CANCELLED",
    "Refund Review": "YES — review before refund",
}, ["Dedupe Key"], 2640, 1020))

nodes.append(http_node("HTTP — Release Driver",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.driver_dispatch_endpoint }}",
    "={\"action\": \"release_driver\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"driver_id\": \"{{ $('Normalize Order Event').first().json.driver_id }}\", \"reason\": \"order_cancelled\"}",
    2880, 1020))

nodes.append(http_node("HTTP — Notify Restaurant — Cancelled",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.restaurant_endpoint }}",
    "={\"action\": \"cancel_order\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"restaurant_id\": \"{{ $('Normalize Order Event').first().json.restaurant_id }}\", \"reason\": \"order_cancelled\", \"note\": \"Stop preparation. Refund under review.\"}",
    3120, 1020))

nodes.append(http_node("HTTP — Notify Customer — Cancelled",
    "= {{ $('CONFIG — Restaurant & Dispatch').first().json.customer_notify_endpoint }}",
    "={\"action\": \"order_cancelled\", \"order_id\": \"{{ $('Normalize Order Event').first().json.order_id }}\", \"customer_name\": \"{{ $('Normalize Order Event').first().json.customer_name }}\", \"customer_phone\": \"{{ $('Normalize Order Event').first().json.customer_phone }}\", \"message\": \"Your order has been cancelled. If you were charged, a refund is under review and we will update you shortly.\"}",
    3360, 1020))

# ---------- BRANCH H: fallback ----------
nodes.append(code_node("Build Unknown Event Note", """const e = $('Normalize Order Event').first().json;
return [{ json: {
  ...e,
  outcome: `Unknown event type "${e.event_type}" for order ${e.order_id} — logged only, no notifications sent.`,
}}];""", 2640, 1180))

# ---------- MERGE + SUMMARY + TELEGRAM ----------
nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge — Combine Branches", "type": "n8n-nodes-base.merge",
    "typeVersion": 3, "position": [3600, 300],
})

nodes.append(code_node("Build Order Summary", """// One Telegram summary for the processed order event
const e = $('Normalize Order Event').first().json;
const items = $input.all().map(i => i.json);
const dup = items.find(i => i.duplicate);
const outcomeMap = {
  'order.created': 'Restaurant notified — order received into the pipeline.',
  'restaurant.confirmed': 'Restaurant confirmed — drivers notified, first-accept claims the delivery.',
  'driver.assigned': `Driver ${e.driver_name || e.driver_id || 'assigned'} — customer update sent.`,
  'driver.picked_up': 'Driver picked up the order — out for delivery.',
  'order.delivered': 'Order delivered.',
  'payment.failed': 'Payment failed — prep held, retry-payment message sent to customer.',
  'order.cancelled': 'Order cancelled — driver released, restaurant + customer notified, refund flagged for review.',
};
let lines = [
  `\\u{1F354} *Food Delivery \\u2014 Order ${e.order_id}*`,
  ``,
  `Event: ${e.event_type}`,
  `Restaurant: ${e.restaurant_name || '—'}`,
  `Customer: ${e.customer_name || '—'}`,
  `Items: ${e.items || '—'}`,
  `Total: ${e.currency} ${e.total || '—'}`,
];
if (dup) {
  lines.push(``, `\\u26A0\\uFE0F Duplicate event — already processed, no notifications sent.`);
} else if (outcomeMap[e.event_type]) {
  lines.push(``, `\\u2705 ${outcomeMap[e.event_type]}`);
} else {
  lines.push(``, `\\u2139\\uFE0F Unknown event type — logged only.`);
}
let aiMsg = '';
try {
  const a = $('AI Agent — Draft Customer Update').first().json;
  if (a && a.output && a.output.message_text) aiMsg = a.output.message_text;
} catch (err) { /* agent only runs for driver.assigned */ }
if (aiMsg) lines.push(``, `\\u{1F4AC} Customer message: \\u201C${aiMsg}\\u201D`);
return [{ json: { ...e, summary: lines.join('\\n') } }];""", 3840, 300))

nodes.append(set_node("CONFIG — Notifications", [
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 4080, 300))

nodes.append({
    "parameters": {
        "chatId": "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}",
        "text": "={{ $json.summary }}",
        "additionalFields": {"parse_mode": "Markdown"},
    },
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": "Telegram — Send Order Update", "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2, "position": [4320, 300],
})

def main(src, dst):
    return {"main": [[{"node": dst, "type": "main", "index": 0}]]}

connections = {
    "Webhook — Order Events": main("Webhook — Order Events", "CONFIG — Order Intake"),
    "CONFIG — Order Intake": main("CONFIG — Order Intake", "Normalize Order Event"),
    "Normalize Order Event": main("Normalize Order Event", "Respond — Order Received"),
    "Respond — Order Received": main("Respond — Order Received", "CONFIG — Google Sheets"),
    "CONFIG — Google Sheets": main("CONFIG — Google Sheets", "Read Logged Events"),
    "Read Logged Events": main("Read Logged Events", "Check Duplicate Event"),
    "Check Duplicate Event": main("Check Duplicate Event", "IF — Duplicate Event?"),
    "IF — Duplicate Event?": {"main": [
        [{"node": "Build Duplicate Notice", "type": "main", "index": 0}],
        [{"node": "Log Event — Status NEW", "type": "main", "index": 0}],
    ]},
    "Log Event — Status NEW": main("Log Event — Status NEW", "Switch — Route by Event Type"),
    "Switch — Route by Event Type": {"main": [
        [{"node": "CONFIG — Restaurant & Dispatch", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status CONFIRMED", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status DISPATCHED", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status OUT_FOR_DELIVERY", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status DELIVERED", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status PAYMENT_FAILED", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status CANCELLED", "type": "main", "index": 0}],
        [{"node": "Build Unknown Event Note", "type": "main", "index": 0}],
    ]},
    # Branch A
    "CONFIG — Restaurant & Dispatch": main("CONFIG — Restaurant & Dispatch", "HTTP — Notify Restaurant"),
    "HTTP — Notify Restaurant": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 0}]]},
    # Branch B
    "Update Sheet — Status CONFIRMED": main("Update Sheet — Status CONFIRMED", "HTTP — Dispatch to Drivers"),
    "HTTP — Dispatch to Drivers": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 1}]]},
    # Branch C
    "Update Sheet — Status DISPATCHED": main("Update Sheet — Status DISPATCHED", "AI Agent — Draft Customer Update"),
    "AI Agent — Draft Customer Update": main("AI Agent — Draft Customer Update", "HTTP — Send Customer Update"),
    "HTTP — Send Customer Update": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 2}]]},
    # Branch D
    "Update Sheet — Status OUT_FOR_DELIVERY": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 3}]]},
    # Branch E
    "Update Sheet — Status DELIVERED": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 4}]]},
    # Branch F
    "Update Sheet — Status PAYMENT_FAILED": main("Update Sheet — Status PAYMENT_FAILED", "HTTP — Hold Prep at Restaurant"),
    "HTTP — Hold Prep at Restaurant": main("HTTP — Hold Prep at Restaurant", "Build Retry Payment Message"),
    "Build Retry Payment Message": main("Build Retry Payment Message", "HTTP — Send Retry Payment Message"),
    "HTTP — Send Retry Payment Message": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 5}]]},
    # Branch G
    "Update Sheet — Status CANCELLED": main("Update Sheet — Status CANCELLED", "HTTP — Release Driver"),
    "HTTP — Release Driver": main("HTTP — Release Driver", "HTTP — Notify Restaurant — Cancelled"),
    "HTTP — Notify Restaurant — Cancelled": main("HTTP — Notify Restaurant — Cancelled", "HTTP — Notify Customer — Cancelled"),
    "HTTP — Notify Customer — Cancelled": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 6}]]},
    # Branch H + duplicate
    "Build Unknown Event Note": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 7}]]},
    "Build Duplicate Notice": {"main": [[{"node": "Merge — Combine Branches", "type": "main", "index": 8}]]},
    # Tail
    "Merge — Combine Branches": main("Merge — Combine Branches", "Build Order Summary"),
    "Build Order Summary": main("Build Order Summary", "CONFIG — Notifications"),
    "CONFIG — Notifications": main("CONFIG — Notifications", "Telegram — Send Order Update"),
    # AI sub-nodes
    "OpenAI Chat Model — Customer Updates": {"ai_languageModel": [[{"node": "AI Agent — Draft Customer Update", "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser — Customer Message": {"ai_outputParser": [[{"node": "AI Agent — Draft Customer Update", "type": "ai_outputParser", "index": 0}]]},
}

wf = {
    "name": "Food Delivery Order Automator",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/food-delivery-order-automator.json"
json.dump(wf, open(out, "w"), indent=2, ensure_ascii=False)
print("wrote", out, "| nodes:", len(nodes))

# ---- validation ----
d = json.load(open(out))
names = {n["name"] for n in d["nodes"]}
missing = []
for src, conns in d["connections"].items():
    assert src in names, f"bad source {src}"
    for ctype, outs in conns.items():
        for branch in outs:
            for t in branch:
                if t["node"] not in names:
                    missing.append((src, t["node"]))
assert not missing, f"missing targets: {missing}"
blob = json.dumps(d)
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook", "api_key\": \"", "AKIA"]:
    assert bad not in blob, f"possible hardcoded secret: {bad}"
# stickies + config present
assert any(n["type"] == "n8n-nodes-base.stickyNote" for n in d["nodes"]), "no stickies"
assert sum(1 for n in d["nodes"] if n["name"].startswith("CONFIG")) >= 3, "config nodes missing"
assert "NEW" in blob and "CONFIRMED" in blob and "DISPATCHED" in blob
assert "OUT_FOR_DELIVERY" in blob and "DELIVERED" in blob and "PAYMENT_FAILED" in blob and "CANCELLED" in blob
assert "gpt-4o-mini" in blob and "outputParserStructured" in blob
# every node except webhook has an incoming connection (or is a sub-node source)
sources = set(d["connections"].keys())
targets = {t["node"] for conns in d["connections"].values() for outs in conns.values() for branch in outs for t in branch}
orphans = [n["name"] for n in d["nodes"] if n["name"] not in targets and n["name"] not in sources and n["name"] != "Webhook — Order Events" and "STICKY" not in n["name"]]
assert not orphans, f"orphan nodes (no incoming edge): {orphans}"
print("validation OK:", len(names), "nodes, all connections resolve, no hardcoded secrets, stickies/config/status flow present")
