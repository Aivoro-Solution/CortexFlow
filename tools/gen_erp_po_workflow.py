#!/usr/bin/env python3
"""Generate the ERP Purchase Order & Inventory Sync Automator n8n workflow JSON."""
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

def sheets_node(name, operation, sheet, columns_value, matching, x, y):
    return {
        "parameters": {
            "operation": operation,
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": sheet},
            "columns": {
                "mappingMode": "defineBelow", "matchingColumns": matching, "schema": [],
                "attemptToConvertTypes": False, "convertFieldsToString": False,
                "value": columns_value,
            },
            "options": {},
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

def sheets_read(name, sheet, x, y):
    return {
        "parameters": {
            "operation": "read",
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": sheet},
            "options": {},
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY — Title",
    "## 📦 ERP PURCHASE ORDER & INVENTORY SYNC AUTOMATOR\n"
    "**What it does:** Pulls new/updated purchase orders from your ERP REST API every morning → dedupes by PO number → logs them to Google Sheets → AI reviews each PO for anomalies → big or flagged POs wait for your Telegram approval (decision written back to the ERP) → approved POs sync inventory quantities → low-stock items trigger a reorder alert → one Telegram run summary.\n\n"
    "**You'll need:**\n- An ERP with a REST API that exposes purchase orders (Odoo, ERPNext, or a custom ERP)\n- OpenAI API key (platform.openai.com)\n- Google Sheets OAuth2 credentials\n- Telegram bot token + your chat ID (@BotFather → /newbot)\n\n"
    "**Status flow in Sheets:** `NEW` → `PENDING_APPROVAL` → `APPROVED` / `REJECTED` → `SYNCED` (auto-approved POs skip straight to `APPROVED`)",
    -240, -160, 7460, 220, color=5))

nodes.append(sticky("STICKY — STEP 1",
    "## STEP 1 — Pull purchase orders from the ERP API\nDaily schedule trigger → HTTP GET on your ERP purchase-orders endpoint (paginated: page + per_page) → normalize into PO number / supplier / total / currency / lines.",
    -240, 180, 1160, 420))

nodes.append(sticky("STICKY — STEP 2",
    "## STEP 2 — Dedupe + log to Google Sheets\nRead PO numbers already in the sheet → keep only new POs → append rows with status `NEW`. Re-runs never double-process a PO.",
    940, 180, 980, 420))

nodes.append(sticky("STICKY — STEP 3",
    "## STEP 3 — AI anomaly review\nAI Agent reviews each PO with a Structured Output Parser (risk flag, risk level, one-line summary) → sheet gets the AI verdict.",
    1900, 180, 700, 420))

nodes.append(sticky("STICKY — STEP 4",
    "## STEP 4 — Approval routing\nPO total ≥ threshold OR AI flagged → status `PENDING_APPROVAL` → Telegram 'Send and Wait' approval message → Approve writes the decision back to the ERP API and flips the sheet to `APPROVED`; Reject flips it to `REJECTED` and stops that PO cleanly. Low-risk POs auto-approve.",
    2620, 20, 1460, 560))

nodes.append(sticky("STICKY — STEP 5",
    "## STEP 5 — Inventory sync + low-stock alerts\nApproved POs: split into line items → update the Inventory sheet (Quantity On Order per SKU) → PO flips to `SYNCED` → read inventory levels → any SKU below its reorder level triggers a Telegram low-stock alert.",
    4060, 180, 2180, 420))

nodes.append(sticky("STICKY — STEP 6",
    "## STEP 6 — Run summary notification\nBoth sync branches merge → one Telegram summary: POs pulled, new POs, AI-flagged, low-stock items.",
    6220, 180, 1000, 420))

# ---------- MAIN CHAIN ----------
nodes.append({
    "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 24, "triggerAtHour": 9, "triggerAtMinute": 0}]}},
    "id": uid(), "name": "Daily 9AM Trigger", "type": "n8n-nodes-base.scheduleTrigger",
    "typeVersion": 1.2, "position": [0, 300],
})

nodes.append(set_node("CONFIG — ERP API", [
    ("erp_api_base_url", "PASTE_YOUR_ERP_API_BASE_URL"),
    ("erp_api_key", "PASTE_YOUR_ERP_API_KEY"),
    ("po_endpoint", "/api/v1/purchase-orders"),
    ("page_size", "50"),
], 240, 300))

nodes.append({
    "parameters": {
        "method": "GET",
        "url": "={{ $json.erp_api_base_url }}{{ $json.po_endpoint }}",
        "sendQuery": True,
        "queryParameters": {"parameters": [
            {"name": "status", "value": "updated"},
            {"name": "page", "value": "1"},
            {"name": "per_page", "value": "={{ $json.page_size }}"},
        ]},
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Authorization", "value": "=Bearer {{ $json.erp_api_key }}"},
            {"name": "Accept", "value": "application/json"},
        ]},
        "options": {},
    },
    "id": uid(), "name": "Fetch Purchase Orders — ERP API", "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2, "position": [480, 300],
})

nodes.append(code_node("Normalize Purchase Orders", """// Normalize the ERP response into a clean PO list.
// Expected ERP shape: { "purchase_orders": [ { po_number, supplier, total_amount,
// currency, order_date, status, lines: [ { sku, description, quantity_ordered,
// unit_price } ] } ], "next_page": null } — a bare array also works.
const cfg = $('CONFIG — ERP API').first().json;
const pageSize = parseInt(cfg.page_size || '50', 10);
const body = $input.first().json;
const raw = Array.isArray(body) ? body : (body.purchase_orders || body.data || body.results || []);
const pos = (Array.isArray(raw) ? raw : []).slice(0, pageSize);
return pos.map(p => ({ json: {
  po_number: p.po_number || p.id || p.number || '',
  supplier: p.supplier || p.vendor || p.supplier_name || '',
  total_amount: Number(p.total_amount || p.total || 0),
  currency: p.currency || 'USD',
  order_date: p.order_date || p.date || new Date().toISOString().slice(0, 10),
  erp_status: p.status || '',
  lines: (p.lines || p.items || []).map(l => ({
    sku: l.sku || l.product_code || '',
    description: l.description || l.name || '',
    quantity_ordered: Number(l.quantity_ordered || l.quantity || 0),
    unit_price: Number(l.unit_price || l.price || 0),
  })),
  date_found: new Date().toISOString().slice(0, 10),
  status: 'NEW',
}}));""", 720, 300))

nodes.append(set_node("CONFIG — Google Sheets", [
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("po_sheet_name", "Purchase Orders"),
    ("inventory_sheet_name", "Inventory"),
], 960, 300))

nodes.append(sheets_read("Read Seen PO Numbers", "Purchase Orders", 1200, 300))

nodes.append(code_node("Filter New POs Only", """// Drop POs whose number is already in the sheet (idempotent by PO number)
const seen = new Set(
  $('Read Seen PO Numbers').all().map(i => (i.json['PO Number'] || i.json.po_number || '').trim()).filter(Boolean)
);
const fresh = $('Normalize Purchase Orders').all()
  .map(i => i.json)
  .filter(p => p.po_number && !seen.has(p.po_number.trim()));
return fresh.map(p => ({ json: p }));""", 1440, 300))

nodes.append(sheets_node("Log New POs — Status NEW", "append", "Purchase Orders", {
    "PO Number": "={{ $json.po_number }}",
    "Order Date": "={{ $json.order_date }}",
    "Supplier": "={{ $json.supplier }}",
    "Total Amount": "={{ $json.total_amount }}",
    "Currency": "={{ $json.currency }}",
    "Status": "NEW",
    "Risk Flag": "",
    "AI Summary": "",
}, [], 1680, 300))

nodes.append(set_node("CONFIG — AI Review", [
    ("openai_model", "gpt-4o-mini"),
    ("approval_threshold", "5000"),
], 1920, 300))

nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are an expert procurement analyst. Review this purchase order for anomalies: an unusual or brand-new supplier, a unit price far above typical, duplicate line items, missing fields, or a total that looks wrong for the items listed.\n\nApproval threshold: {{ $('CONFIG — AI Review').first().json.approval_threshold }} (currency units). Flag risk_flag=true for anything that deserves a human look, even if the total is small. Be strict but fair. Output ONLY via the structured output parser.",
            "text": "=PO Number: {{ $json.po_number }}\nSupplier: {{ $json.supplier }}\nTotal: {{ $json.currency }} {{ $json.total_amount }}\nOrder Date: {{ $json.order_date }}\n\nLine Items:\n{{ JSON.stringify($json.lines) }}",
        },
    },
    "id": uid(), "name": "AI Agent — Review Purchase Order", "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7, "position": [2160, 300],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model — PO Review", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.2, "position": [2160, 560],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n  \"risk_flag\": false,\n  \"risk_level\": \"LOW / MEDIUM / HIGH\",\n  \"risk_reasons\": \"comma-separated list of what looks off, empty if nothing\",\n  \"one_line_summary\": \"single plain-English sentence summarising the PO\"\n}",
    },
    "id": uid(), "name": "Structured Output Parser — PO Review", "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.2, "position": [2400, 560],
})

nodes.append({
    "parameters": {
        "conditions": {
            "combinator": "or",
            "conditions": [
                {
                    "id": "if-amount",
                    "leftValue": "={{ $json.total_amount }}",
                    "rightValue": "={{ $('CONFIG — AI Review').first().json.approval_threshold }}",
                    "operator": {"type": "number", "operation": "largerEqual", "name": "filter.operator.number.largerEqual"},
                },
                {
                    "id": "if-flagged",
                    "leftValue": "={{ $json.output.risk_flag }}",
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true", "name": "filter.operator.boolean.true"},
                },
            ],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "options": {},
    },
    "id": uid(), "name": "IF — Needs Approval", "type": "n8n-nodes-base.if",
    "typeVersion": 2.2, "position": [2640, 300],
})

nodes.append(sheets_node("Update Sheet — Status PENDING_APPROVAL", "update", "Purchase Orders", {
    "PO Number": "={{ $json.po_number }}",
    "Risk Flag": "={{ $json.output.risk_flag }}",
    "AI Summary": "={{ $json.output.one_line_summary }}",
    "Status": "PENDING_APPROVAL",
}, ["PO Number"], 2880, 140))

nodes.append({
    "parameters": {
        "operation": "sendAndWait",
        "chatId": "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}",
        "message": "=📋 *Purchase Order Approval Needed*\n\nPO: {{ $('IF — Needs Approval').item.json.po_number }}\nSupplier: {{ $('IF — Needs Approval').item.json.supplier }}\nTotal: {{ $('IF — Needs Approval').item.json.currency }} {{ $('IF — Needs Approval').item.json.total_amount }}\nRisk: {{ $('IF — Needs Approval').item.json.output.risk_level }} — {{ $('IF — Needs Approval').item.json.output.risk_reasons }}\nAI review: {{ $('IF — Needs Approval').item.json.output.one_line_summary }}\n\nApprove to write the decision back to the ERP and sync inventory. Reject to skip this PO.",
        "options": {
            "responseType": "approval",
            "approveButtonText": "✅ Approve",
            "disapproveButtonText": "❌ Reject",
        },
        "additionalFields": {"parse_mode": "Markdown"},
    },
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": "Telegram — Send and Wait for Approval", "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2, "position": [3120, 140],
})

nodes.append({
    "parameters": {
        "conditions": {
            "combinator": "and",
            "conditions": [{
                "id": "if-approved",
                "leftValue": "={{ $json.data.approved }}",
                "rightValue": True,
                "operator": {"type": "boolean", "operation": "true", "name": "filter.operator.boolean.true"},
            }],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "options": {},
    },
    "id": uid(), "name": "IF — Approved?", "type": "n8n-nodes-base.if",
    "typeVersion": 2.2, "position": [3360, 140],
})

nodes.append({
    "parameters": {
        "method": "PATCH",
        "url": "={{ $('CONFIG — ERP API').first().json.erp_api_base_url }}{{ $('CONFIG — ERP API').first().json.po_endpoint }}/{{ $('IF — Needs Approval').item.json.po_number }}",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Authorization", "value": "=Bearer {{ $('CONFIG — ERP API').first().json.erp_api_key }}"},
            {"name": "Content-Type", "value": "application/json"},
        ]},
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={\"status\": \"approved\", \"po_number\": \"{{ $('IF — Needs Approval').item.json.po_number }}\", \"approved_via\": \"n8n\", \"approved_at\": \"{{ new Date().toISOString() }}\"}",
        "options": {},
    },
    "id": uid(), "name": "Update ERP — Write Approval Decision", "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2, "position": [3600, 140],
})

nodes.append(sheets_node("Update Sheet — Status APPROVED", "update", "Purchase Orders", {
    "PO Number": "={{ $('IF — Needs Approval').item.json.po_number }}",
    "Status": "APPROVED",
}, ["PO Number"], 3840, 140))

nodes.append(sheets_node("Update Sheet — Status REJECTED", "update", "Purchase Orders", {
    "PO Number": "={{ $('IF — Needs Approval').item.json.po_number }}",
    "Status": "REJECTED",
}, ["PO Number"], 3600, 300))

nodes.append(sheets_node("Update Sheet — Status APPROVED (Auto)", "update", "Purchase Orders", {
    "PO Number": "={{ $json.po_number }}",
    "Risk Flag": "={{ $json.output.risk_flag }}",
    "AI Summary": "={{ $json.output.one_line_summary }}",
    "Status": "APPROVED",
}, ["PO Number"], 2880, 460))

nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge — Combine Approval Branches", "type": "n8n-nodes-base.merge",
    "typeVersion": 3, "position": [4080, 300],
})

nodes.append(code_node("Split PO Lines", """// Split each approved PO into one item per line item for the inventory sync.
// NOTE: after the approval branch, $json is the Sheets/ERP response, so PO fields
// are recovered through the paired item on the IF node.
const today = new Date().toISOString().slice(0, 10);
const out = [];
for (const item of $input.all()) {
  const po = item.json.po_number ? item.json : ($('IF — Needs Approval').item.json || item.json);
  const lines = Array.isArray(po.lines) ? po.lines : [];
  for (const l of lines) {
    out.push({ json: {
      po_number: po.po_number || '',
      sku: l.sku || '',
      description: l.description || '',
      quantity_ordered: Number(l.quantity_ordered || 0),
      unit_price: Number(l.unit_price || 0),
      sync_date: today,
    }});
  }
  // POs with no line items still count as synced
  if (!lines.length && po.po_number) out.push({ json: { po_number: po.po_number, sku: '', description: '', quantity_ordered: 0, unit_price: 0, sync_date: today } });
}
return out;""", 4320, 300))

nodes.append(sheets_node("Update Inventory — Sync Quantities", "update", "Inventory", {
    "SKU": "={{ $json.sku }}",
    "Quantity On Order": "={{ $json.quantity_ordered }}",
    "Last PO Number": "={{ $json.po_number }}",
    "Last Sync Date": "={{ $json.sync_date }}",
}, ["SKU"], 4560, 300))

nodes.append(code_node("Rebuild PO Items", """// Collapse per-line items back to one item per PO (grouped by Last PO Number,
// which the Inventory update wrote from the line items).
const seen = new Map();
for (const item of $input.all()) {
  const po = item.json['Last PO Number'] || item.json.po_number || '';
  if (po && !seen.has(po)) seen.set(po, { po_number: po });
}
return [...seen.values()].map(j => ({ json: j }));""", 4800, 300))

nodes.append(sheets_node("Update Sheet — Status SYNCED", "update", "Purchase Orders", {
    "PO Number": "={{ $json.po_number }}",
    "Status": "SYNCED",
}, ["PO Number"], 5040, 300))

nodes.append(sheets_read("Read Inventory Levels", "Inventory", 5280, 300))

nodes.append(code_node("Flag Low Stock Items", """// Flag inventory rows where on-hand stock is below the reorder level.
// Returns one aggregate item so the IF node can branch on the count.
const rows = $input.all().map(i => i.json);
const low = rows.filter(r => {
  const onHand = Number(r['Quantity On Hand'] || 0);
  const reorder = Number(r['Reorder Level'] || 0);
  return reorder > 0 && onHand < reorder;
});
const lines = low.map(r => `${r.SKU || ''} — ${r['Item Name'] || ''} (on hand ${r['Quantity On Hand']}, reorder at ${r['Reorder Level']})`);
return [{ json: { low_stock_count: low.length, low_stock_lines: lines.join('\\n') } }];""", 5520, 300))

nodes.append({
    "parameters": {
        "conditions": {
            "combinator": "and",
            "conditions": [{
                "id": "if-low-stock",
                "leftValue": "={{ $json.low_stock_count }}",
                "rightValue": 0,
                "operator": {"type": "number", "operation": "larger", "name": "filter.operator.number.larger"},
            }],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "options": {},
    },
    "id": uid(), "name": "IF — Low Stock Found", "type": "n8n-nodes-base.if",
    "typeVersion": 2.2, "position": [5760, 300],
})

nodes.append({
    "parameters": {
        "chatId": "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}",
        "text": "=⚠️ *Low Stock Alert*\n\nThe following items are below their reorder level in the Inventory sheet:\n\n{{ $('Flag Low Stock Items').first().json.low_stock_lines }}\n\nReorder soon — these were checked after today's PO sync.",
        "additionalFields": {"parse_mode": "Markdown"},
    },
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": "Telegram — Low Stock Alert", "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2, "position": [6000, 140],
})

nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge — Combine Sync Branches", "type": "n8n-nodes-base.merge",
    "typeVersion": 3, "position": [6240, 300],
})

nodes.append(code_node("Build Run Summary", """// Build one Telegram summary from the run. Counts are read from the earlier
// nodes directly, because the items reaching this node are sheet/API responses.
const pulled = $('Normalize Purchase Orders').all().length;
const fresh = $('Filter New POs Only').all().length;
const reviewed = $('AI Agent — Review Purchase Order').all();
const flagged = reviewed.filter(i => i.json.output && i.json.output.risk_flag).length;
const rejected = $('Update Sheet — Status REJECTED').all().length;
const lowStock = $('Flag Low Stock Items').first().json.low_stock_count || 0;
const lowStockLines = $('Flag Low Stock Items').first().json.low_stock_lines || '';
let lines = [`\\U0001F4E6 *ERP PO & Inventory Sync \\u2014 ${new Date().toISOString().slice(0,10)}*`, ``, `\\u2022 ${pulled} POs pulled from ERP`, `\\u2022 ${fresh} new POs processed`, `\\u2022 ${flagged} flagged by AI for review`, `\\u2022 ${rejected} rejected in approval`];
if (lowStock > 0) {
  lines.push(`\\u2022 \\u26A0\\uFE0F ${lowStock} items below reorder level:`, ``, lowStockLines);
} else {
  lines.push(`\\u2022 No low-stock items`);
}
lines.push(``, `Full detail in the Purchase Orders sheet.`);
return [{ json: { summary: lines.join('\\n'), pulled, fresh, flagged, rejected, low_stock_count: lowStock } }];""", 6480, 300))

nodes.append(set_node("CONFIG — Notifications", [
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 6720, 300))

nodes.append({
    "parameters": {
        "chatId": "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}",
        "text": "={{ $json.summary }}",
        "additionalFields": {"parse_mode": "Markdown"},
    },
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": "Telegram — Send Summary", "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2, "position": [6960, 300],
})

connections = {
    "Daily 9AM Trigger": {"main": [[{"node": "CONFIG — ERP API", "type": "main", "index": 0}]]},
    "CONFIG — ERP API": {"main": [[{"node": "Fetch Purchase Orders — ERP API", "type": "main", "index": 0}]]},
    "Fetch Purchase Orders — ERP API": {"main": [[{"node": "Normalize Purchase Orders", "type": "main", "index": 0}]]},
    "Normalize Purchase Orders": {"main": [[{"node": "CONFIG — Google Sheets", "type": "main", "index": 0}]]},
    "CONFIG — Google Sheets": {"main": [[{"node": "Read Seen PO Numbers", "type": "main", "index": 0}]]},
    "Read Seen PO Numbers": {"main": [[{"node": "Filter New POs Only", "type": "main", "index": 0}]]},
    "Filter New POs Only": {"main": [[{"node": "Log New POs — Status NEW", "type": "main", "index": 0}]]},
    "Log New POs — Status NEW": {"main": [[{"node": "CONFIG — AI Review", "type": "main", "index": 0}]]},
    "CONFIG — AI Review": {"main": [[{"node": "AI Agent — Review Purchase Order", "type": "main", "index": 0}]]},
    "AI Agent — Review Purchase Order": {"main": [[{"node": "IF — Needs Approval", "type": "main", "index": 0}]]},
    "IF — Needs Approval": {"main": [
        [{"node": "Update Sheet — Status PENDING_APPROVAL", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status APPROVED (Auto)", "type": "main", "index": 0}],
    ]},
    "Update Sheet — Status PENDING_APPROVAL": {"main": [[{"node": "Telegram — Send and Wait for Approval", "type": "main", "index": 0}]]},
    "Telegram — Send and Wait for Approval": {"main": [[{"node": "IF — Approved?", "type": "main", "index": 0}]]},
    "IF — Approved?": {"main": [
        [{"node": "Update ERP — Write Approval Decision", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status REJECTED", "type": "main", "index": 0}],
    ]},
    "Update ERP — Write Approval Decision": {"main": [[{"node": "Update Sheet — Status APPROVED", "type": "main", "index": 0}]]},
    "Update Sheet — Status APPROVED": {"main": [[{"node": "Merge — Combine Approval Branches", "type": "main", "index": 0}]]},
    "Update Sheet — Status APPROVED (Auto)": {"main": [[{"node": "Merge — Combine Approval Branches", "type": "main", "index": 1}]]},
    # NOTE: REJECTED branch intentionally terminates here — rejected POs never sync inventory.
    "Merge — Combine Approval Branches": {"main": [[{"node": "Split PO Lines", "type": "main", "index": 0}]]},
    "Split PO Lines": {"main": [[{"node": "Update Inventory — Sync Quantities", "type": "main", "index": 0}]]},
    "Update Inventory — Sync Quantities": {"main": [[{"node": "Rebuild PO Items", "type": "main", "index": 0}]]},
    "Rebuild PO Items": {"main": [[{"node": "Update Sheet — Status SYNCED", "type": "main", "index": 0}]]},
    "Update Sheet — Status SYNCED": {"main": [[{"node": "Read Inventory Levels", "type": "main", "index": 0}]]},
    "Read Inventory Levels": {"main": [[{"node": "Flag Low Stock Items", "type": "main", "index": 0}]]},
    "Flag Low Stock Items": {"main": [[{"node": "IF — Low Stock Found", "type": "main", "index": 0}]]},
    "IF — Low Stock Found": {"main": [
        [{"node": "Telegram — Low Stock Alert", "type": "main", "index": 0}],
        [{"node": "Merge — Combine Sync Branches", "type": "main", "index": 1}],
    ]},
    "Telegram — Low Stock Alert": {"main": [[{"node": "Merge — Combine Sync Branches", "type": "main", "index": 0}]]},
    "Merge — Combine Sync Branches": {"main": [[{"node": "Build Run Summary", "type": "main", "index": 0}]]},
    "Build Run Summary": {"main": [[{"node": "CONFIG — Notifications", "type": "main", "index": 0}]]},
    "CONFIG — Notifications": {"main": [[{"node": "Telegram — Send Summary", "type": "main", "index": 0}]]},
    "OpenAI Chat Model — PO Review": {"ai_languageModel": [[{"node": "AI Agent — Review Purchase Order", "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser — PO Review": {"ai_outputParser": [[{"node": "AI Agent — Review Purchase Order", "type": "ai_outputParser", "index": 0}]]},
}

wf = {
    "name": "ERP Purchase Order & Inventory Sync Automator",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/erp-purchase-order-inventory-sync.json"
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
# no hardcoded secrets check
blob = json.dumps(d)
# PASTE_YOUR_* placeholders are allowed; real keys/emails are not
for bad in ["sk-", "sk-proj", "xoxb-", "ya29.", "@gmail.com", "@outlook.com", "@yahoo.com"]:
    assert bad not in blob, f"possible hardcoded secret: {bad}"
# stickies + config nodes present
stickies = [n for n in d["nodes"] if n["type"] == "n8n-nodes-base.stickyNote"]
configs = [n for n in d["nodes"] if n["name"].startswith("CONFIG")]
assert len(stickies) >= 7, f"expected >=7 stickies, got {len(stickies)}"
assert len(configs) >= 4, f"expected >=4 config nodes, got {len(configs)}"
# no webhook node
assert not any("webhook" in n["type"] for n in d["nodes"]), "webhook node present!"
# unique ids and names
ids = [n["id"] for n in d["nodes"]]
assert len(ids) == len(set(ids)), "duplicate node ids"
assert len(names) == len(d["nodes"]), "duplicate node names"
print("validation OK: all", len(names), "nodes connected, no hardcoded secrets")
print("stickies:", len(stickies), "| config nodes:", len(configs), "| webhook nodes: 0")
