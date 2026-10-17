#!/usr/bin/env python3
"""Generate the AI Guest Messaging Assistant for Vacation Rentals n8n workflow JSON."""
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

def code_node(name, js, x, y):
    return {
        "parameters": {"jsCode": js, "mode": "runOnceForAllItems"},
        "id": uid(), "name": name, "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [x, y],
    }

def sheets_node(name, operation, columns_value, matching_columns, x, y):
    return {
        "parameters": {
            "operation": operation,
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": "Guest Messages"},
            "columns": {
                "mappingMode": "defineBelow", "matchingColumns": matching_columns,
                "schema": [], "attemptToConvertTypes": False, "convertFieldsToString": False,
                "value": columns_value,
            },
            "options": {},
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

def telegram_node(name, text, x, y):
    return {
        "parameters": {
            "chatId": "={{ $('CONFIG \u2014 Properties & Rules').first().json.telegram_chat_id }}",
            "text": text,
            "additionalFields": {"parse_mode": "Markdown"},
        },
        "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2, "position": [x, y],
    }

nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY \u2014 Title",
    "## \U0001f3e0 AI GUEST MESSAGING ASSISTANT FOR VACATION RENTALS\n"
    "**What it does:** Webhook receives inbound guest messages (Airbnb / Booking.com via channel-manager or PMS webhook, email via an IMAP-to-webhook bridge) \u2192 AI classifies the message and drafts a reply \u2192 safe FAQs (WiFi, check-in/out, house rules, amenities) get an instant auto-reply \u2192 sensitive topics (refunds, complaints, access codes, safety) escalate to the host on Telegram with a suggested draft.\n\n"
    "**You'll need:**\n"
    "- OpenAI API key (platform.openai.com)\n"
    "- Google Sheets OAuth2 credential\n"
    "- Telegram bot token + your chat ID (@BotFather \u2192 /newbot)\n"
    "- A channel-manager/PMS (Hostaway, Lodgify, Guesty\u2026) or OTA webhook forwarding inbound guest messages to the workflow's webhook URL\n\n"
    "**Status flow in Sheets:** `NEW` \u2192 `PROCESSING` \u2192 `AUTO_REPLIED` / `ESCALATED`",
    -240, -180, 6200, 260, color=5))

nodes.append(sticky("STICKY \u2014 STEP 1",
    "## STEP 1 \u2014 Inbound guest message\nWebhook receives the guest message from your PMS/channel-manager/email bridge \u2192 normalize channel, property, guest name and message text.",
    -240, 160, 1320, 420))

nodes.append(sticky("STICKY \u2014 STEP 2",
    "## STEP 2 \u2014 Log to Google Sheets\nAppend a row with status `NEW`, then flip it to `PROCESSING` while the AI works.",
    940, 160, 880, 420))

nodes.append(sticky("STICKY \u2014 STEP 3",
    "## STEP 3 \u2014 AI classify + draft\nAI Agent reads the message with property context and returns structured output: intent, confidence 0\u20131, auto_reply_allowed, draft_reply, escalation_reason.",
    1840, 160, 560, 420))

nodes.append(sticky("STICKY \u2014 STEP 4",
    "## STEP 4 \u2014 Safe auto-reply branch\n`auto_reply_allowed = true` AND confidence \u2265 threshold \u2192 POST the draft to your reply endpoint \u2192 sheet flips to `AUTO_REPLIED` \u2192 host gets a Telegram summary.",
    2220, -40, 1420, 150))

nodes.append(sticky("STICKY \u2014 STEP 5",
    "## STEP 5 \u2014 Escalation branch\nRefunds, complaints, access codes, safety, schedule changes or low confidence \u2192 sheet flips to `ESCALATED` \u2192 host gets a Telegram alert with the AI's suggested draft. The host replies manually.",
    2220, 590, 1420, 150))

nodes.append(sticky("STICKY \u2014 STEP 6",
    "## STEP 6 \u2014 Acknowledge webhook\nBoth branches merge \u2192 return `{\"status\": \"ok\"}` to the caller.",
    3060, 160, 660, 420))

# ---------- MAIN CHAIN ----------
nodes.append({
    "parameters": {
        "httpMethod": "POST",
        "path": "guest-message",
        "responseMode": "respondToWebhook",
        "options": {},
    },
    "id": uid(), "name": "Guest Message Webhook",
    "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 300],
})

nodes.append(set_node("CONFIG \u2014 Properties & Rules", [
    ("property_name", "PASTE_YOUR_PROPERTY_NAME (comma-separated list for multiple properties)"),
    ("checkin_time", "PASTE_YOUR_CHECKIN_TIME (e.g. 15:00)"),
    ("checkout_time", "PASTE_YOUR_CHECKOUT_TIME (e.g. 11:00)"),
    ("wifi_password", "PASTE_YOUR_WIFI_PASSWORD"),
    ("house_rules_url", "PASTE_YOUR_HOUSE_RULES_URL"),
    ("safe_intents", "wifi,checkin,checkout,houserules,amenities,parking,directions"),
    ("confidence_threshold", "0.85"),
    ("reply_api_url", "PASTE_YOUR_REPLY_ENDPOINT (your PMS/channel-manager reply webhook URL)"),
    ("reply_api_key", "PASTE_YOUR_REPLY_API_KEY"),
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
    ("escalation_email", "PASTE_YOUR_EMAIL"),
], 280, 300))

nodes.append(code_node("Normalize Guest Message", """// Normalize inbound payloads from PMS/channel-manager/email bridges into one shape
const body = $input.first().json;
const cfg = $('CONFIG \u2014 Properties & Rules').first().json;
const msg = body.message || body.text || body.body || '';
return [{ json: {
  message_id: body.message_id || ('msg-' + Date.now()),
  timestamp: new Date().toISOString(),
  channel: body.channel || body.source || 'unknown',
  property: body.property || body.property_name || cfg.property_name,
  guest_name: body.guest_name || body.guest || 'Guest',
  message: msg,
} }];""", 560, 300))

nodes.append(set_node("CONFIG \u2014 Google Sheets", [
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("sheet_name", "Guest Messages"),
], 840, 300))

nodes.append(sheets_node("Log Message \u2014 Status NEW", "append", {
    "Message ID": "={{ $json.message_id }}",
    "Timestamp": "={{ $json.timestamp }}",
    "Channel": "={{ $json.channel }}",
    "Property": "={{ $json.property }}",
    "Guest Name": "={{ $json.guest_name }}",
    "Message": "={{ $json.message }}",
    "Intent": "",
    "Confidence": "",
    "Status": "NEW",
    "Draft Reply": "",
    "Replied At": "",
}, [], 1120, 300))

nodes.append(sheets_node("Update Sheet \u2014 Status PROCESSING", "update", {
    "Message ID": "={{ $json.message_id }}",
    "Status": "PROCESSING",
}, ["Message ID"], 1400, 300))

nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are the guest-messaging concierge for a vacation-rental business (15\u201330 properties). Answer ONLY from the property context below; never invent policies, prices or access codes.\n\n"
            "PROPERTY CONTEXT:\n"
            "- Properties: {{ $('CONFIG \u2014 Properties & Rules').first().json.property_name }}\n"
            "- Check-in: {{ $('CONFIG \u2014 Properties & Rules').first().json.checkin_time }} \u00b7 Check-out: {{ $('CONFIG \u2014 Properties & Rules').first().json.checkout_time }}\n"
            "- House rules: {{ $('CONFIG \u2014 Properties & Rules').first().json.house_rules_url }}\n"
            "- WiFi password: {{ $('CONFIG \u2014 Properties & Rules').first().json.wifi_password }}\n\n"
            "SAFE INTENTS you may answer yourself: {{ $('CONFIG \u2014 Properties & Rules').first().json.safe_intents }}\n\n"
            "ALWAYS ESCALATE (set auto_reply_allowed=false) when the message involves: refunds or payment disputes, complaints or damage reports, safety/security issues (lockouts, alarms, intruders), access codes or door codes, early check-in / late checkout requests, anything illegal or medical, or when you are unsure what the guest wants.\n\n"
            "Draft replies in a warm, professional host tone, under 80 words, in the guest's language. Output ONLY via the structured output parser.",
        },
        "text": "=Guest message (channel: {{ $json.channel }}, property: {{ $json.property }}):\n\n{{ $json.message }}\n\nGuest: {{ $json.guest_name }}",
    },
    "id": uid(), "name": "AI Agent \u2014 Classify & Draft",
    "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 1.7, "position": [1680, 300],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model \u2014 Guest AI",
    "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi", "typeVersion": 1.2, "position": [1680, 560],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n"
        "  \"intent\": \"one of wifi, checkin, checkout, houserules, amenities, parking, directions, refund, complaint, access, schedule_change, other\",\n"
        "  \"confidence\": 0.0,\n"
        "  \"auto_reply_allowed\": true,\n"
        "  \"draft_reply\": \"the reply text \u2014 ALWAYS fill this, even when escalating (it becomes the suggested draft)\",\n"
        "  \"escalation_reason\": \"empty string if auto-reply is safe, otherwise a one-line reason\"\n"
        "}",
    },
    "id": uid(), "name": "Structured Output Parser \u2014 Guest Intent",
    "type": "@n8n/n8n-nodes-langchain.outputParserStructured", "typeVersion": 1.2, "position": [1960, 560],
})

nodes.append({
    "parameters": {
        "conditions": {
            "combinator": "and",
            "conditions": [
                {
                    "id": "if-auto",
                    "leftValue": "={{ $json.output.auto_reply_allowed }}",
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true", "name": "filter.operator.boolean.true"},
                },
                {
                    "id": "if-conf",
                    "leftValue": "={{ $json.output.confidence }}",
                    "rightValue": "={{ $('CONFIG \u2014 Properties & Rules').first().json.confidence_threshold }}",
                    "operator": {"type": "number", "operation": "largerEqual", "name": "filter.operator.number.largerEqual"},
                },
            ],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "options": {},
    },
    "id": uid(), "name": "IF \u2014 Safe to Auto-Reply?",
    "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [1960, 300],
})

# ---- auto-reply branch ----
nodes.append({
    "parameters": {
        "method": "POST",
        "url": "={{ $('CONFIG \u2014 Properties & Rules').first().json.reply_api_url }}",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Authorization", "value": "=Bearer {{ $('CONFIG \u2014 Properties & Rules').first().json.reply_api_key }}"},
        ]},
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ message_id: $json.message_id, channel: $json.channel, property: $json.property, guest_name: $json.guest_name, reply_text: $json.output.draft_reply }) }}",
        "options": {},
    },
    "id": uid(), "name": "Send Guest Reply",
    "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [2240, 140],
})

nodes.append(sheets_node("Update Sheet \u2014 Status AUTO_REPLIED", "update", {
    "Message ID": "={{ $json.message_id }}",
    "Intent": "={{ $json.output.intent }}",
    "Confidence": "={{ $json.output.confidence }}",
    "Status": "AUTO_REPLIED",
    "Draft Reply": "={{ $json.output.draft_reply }}",
    "Replied At": "={{ $now.toISO() }}",
}, ["Message ID"], 2520, 140))

nodes.append(telegram_node("Telegram \u2014 Notify Host (Auto-replied)",
    "=\u2705 *Auto-replied to guest*\n\n"
    "\U0001f3e0 {{ $json.property }} \u2014 {{ $json.guest_name }} ({{ $json.channel }})\n"
    "\U0001f3af Intent: `{{ $json.output.intent }}` (confidence {{ $json.output.confidence }})\n\n"
    "\U0001f4e4 *Reply sent:*\n"
    "{{ $json.output.draft_reply }}",
    2800, 140))

# ---- escalate branch ----
nodes.append(sheets_node("Update Sheet \u2014 Status ESCALATED", "update", {
    "Message ID": "={{ $json.message_id }}",
    "Intent": "={{ $json.output.intent }}",
    "Confidence": "={{ $json.output.confidence }}",
    "Status": "ESCALATED",
    "Draft Reply": "={{ $json.output.draft_reply }}",
}, ["Message ID"], 2240, 460))

nodes.append(telegram_node("\U0001f6a8 Telegram \u2014 Escalate to Host",
    "=\U0001f6a8 *Guest message needs you*\n\n"
    "\U0001f3e0 Property: {{ $json.property }}\n"
    "\U0001f464 Guest: {{ $json.guest_name }} (via {{ $json.channel }})\n\n"
    "\U0001f4ac *Message:*\n"
    "{{ $json.message }}\n\n"
    "\U0001f916 *AI read:* intent `{{ $json.output.intent }}` \u2014 confidence {{ $json.output.confidence }}\n"
    "\u26a0\ufe0f *Why escalated:* {{ $json.output.escalation_reason }}\n\n"
    "\u270f\ufe0f *Suggested draft (edit before sending):*\n"
    "{{ $json.output.draft_reply }}",
    2520, 460))

# ---- merge + respond ----
nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge \u2014 Combine Branches",
    "type": "n8n-nodes-base.merge", "typeVersion": 3, "position": [3080, 300],
})

nodes.append({
    "parameters": {
        "respondWith": "json",
        "responseBody": "{\"status\": \"ok\"}",
        "options": {},
    },
    "id": uid(), "name": "Respond \u2014 OK",
    "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1, "position": [3360, 300],
})

connections = {
    "Guest Message Webhook": {"main": [[{"node": "CONFIG \u2014 Properties & Rules", "type": "main", "index": 0}]]},
    "CONFIG \u2014 Properties & Rules": {"main": [[{"node": "Normalize Guest Message", "type": "main", "index": 0}]]},
    "Normalize Guest Message": {"main": [[{"node": "CONFIG \u2014 Google Sheets", "type": "main", "index": 0}]]},
    "CONFIG \u2014 Google Sheets": {"main": [[{"node": "Log Message \u2014 Status NEW", "type": "main", "index": 0}]]},
    "Log Message \u2014 Status NEW": {"main": [[{"node": "Update Sheet \u2014 Status PROCESSING", "type": "main", "index": 0}]]},
    "Update Sheet \u2014 Status PROCESSING": {"main": [[{"node": "AI Agent \u2014 Classify & Draft", "type": "main", "index": 0}]]},
    "AI Agent \u2014 Classify & Draft": {"main": [[{"node": "IF \u2014 Safe to Auto-Reply?", "type": "main", "index": 0}]]},
    "IF \u2014 Safe to Auto-Reply?": {"main": [
        [{"node": "Send Guest Reply", "type": "main", "index": 0}],
        [{"node": "Update Sheet \u2014 Status ESCALATED", "type": "main", "index": 0}],
    ]},
    "Send Guest Reply": {"main": [[{"node": "Update Sheet \u2014 Status AUTO_REPLIED", "type": "main", "index": 0}]]},
    "Update Sheet \u2014 Status AUTO_REPLIED": {"main": [[{"node": "Telegram \u2014 Notify Host (Auto-replied)", "type": "main", "index": 0}]]},
    "Telegram \u2014 Notify Host (Auto-replied)": {"main": [[{"node": "Merge \u2014 Combine Branches", "type": "main", "index": 0}]]},
    "Update Sheet \u2014 Status ESCALATED": {"main": [[{"node": "\U0001f6a8 Telegram \u2014 Escalate to Host", "type": "main", "index": 0}]]},
    "\U0001f6a8 Telegram \u2014 Escalate to Host": {"main": [[{"node": "Merge \u2014 Combine Branches", "type": "main", "index": 1}]]},
    "Merge \u2014 Combine Branches": {"main": [[{"node": "Respond \u2014 OK", "type": "main", "index": 0}]]},
    "OpenAI Chat Model \u2014 Guest AI": {"ai_languageModel": [[{"node": "AI Agent \u2014 Classify & Draft", "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser \u2014 Guest Intent": {"ai_outputParser": [[{"node": "AI Agent \u2014 Classify & Draft", "type": "ai_outputParser", "index": 0}]]},
}

wf = {
    "name": "AI Guest Messaging Assistant for Vacation Rentals",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/ai-guest-messaging-vacation-rentals.json"
json.dump(wf, open(out, "w"), indent=2, ensure_ascii=False)
print("wrote", out, "| nodes:", len(nodes))

# ---- validation ----
d = json.load(open(out))
names = {n["name"] for n in d["nodes"]}
missing = []
for src, conns in d["connections"].items():
    assert src in names, "bad source %s" % src
    for ctype, outs in conns.items():
        for branch in outs:
            for t in branch:
                if t["node"] not in names:
                    missing.append((src, t["node"]))
assert not missing, "missing targets: %s" % missing
blob = json.dumps(d)
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook.com", "bot1", "bot9"]:
    assert bad not in blob, "possible hardcoded secret: %s" % bad
assert "PASTE_YOUR_" in blob, "placeholders missing"
stickies = [n for n in d["nodes"] if n["type"] == "n8n-nodes-base.stickyNote"]
assert len(stickies) >= 6, "stickies missing"
configs = [n for n in d["nodes"] if n["type"] == "n8n-nodes-base.set"]
assert len(configs) >= 2, "config set nodes missing"
# empty credential selects
for n in d["nodes"]:
    for ctype, cred in (n.get("credentials") or {}).items():
        assert cred.get("id") == "", "non-empty credential id in %s" % n["name"]
print("validation OK:", len(names), "nodes connected |", len(stickies), "stickies |",
      len(configs), "config sets | all credential selects empty | no hardcoded secrets")
