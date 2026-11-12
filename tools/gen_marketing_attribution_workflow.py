#!/usr/bin/env python3
"""Generate the Marketing Attribution & Lead Engine n8n workflow JSON.

Two entry paths in one importable workflow:
  1. Webhook lead intake -> normalize -> dedup -> AI score (Hot/Warm/Cold)
     -> round-robin rep assignment -> WhatsApp for Hot leads -> Telegram alert.
  2. Daily 08:00 attribution branch -> fetch Meta/TikTok/LinkedIn/YouTube
     spend -> compute CPL / CPLPV / CPP / ROAS -> Sheets snapshot -> Telegram
     alert when a channel's CPL exceeds the configured cap.

Node-type/version conventions copied exactly from
~/workspace/blog/tools/gen_job_hunt_workflow.py.
"""
import json, uuid

SLUG = "marketing-attribution-lead-engine"

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

def sheets_node(name, operation, sheet, value, x, y, matching=None):
    params = {
        "operation": operation,
        "resource": "sheetWithinDocument",
        "documentId": {"__rl": True, "mode": "list", "value": ""},
        "sheetName": {"__rl": True, "mode": "list", "value": sheet},
        "options": {},
    }
    if operation in ("append", "update"):
        params["columns"] = {
            "mappingMode": "defineBelow",
            "matchingColumns": matching or [],
            "schema": [],
            "attemptToConvertTypes": False, "convertFieldsToString": False,
            "value": value,
        }
    return {
        "parameters": params,
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

def if_node(name, left, right, op, x, y):
    return {
        "parameters": {
            "conditions": {
                "combinator": "and",
                "conditions": [{
                    "id": uid(),
                    "leftValue": left,
                    "rightValue": right,
                    "operator": op,
                }],
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            },
            "options": {},
        },
        "id": uid(), "name": name, "type": "n8n-nodes-base.if",
        "typeVersion": 2.2, "position": [x, y],
    }

def http_node(name, method, url, x, y, extra=None, continue_on_fail=False):
    params = {"method": method, "url": url, "options": {}}
    if extra:
        params.update(extra)
    node = {
        "parameters": params,
        "id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2, "position": [x, y],
    }
    if continue_on_fail:
        node["continueOnFail"] = True
    return node

def telegram_node(name, text_expr, x, y):
    return {
        "parameters": {
            "chatId": "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}",
            "text": text_expr,
            "additionalFields": {"parse_mode": "Markdown"},
        },
        "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2, "position": [x, y],
    }

nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY — Title",
    "## 🎯 MARKETING ATTRIBUTION & LEAD ENGINE\n"
    "**What it does:** Webhook lead intake → normalize + dedupe by phone/email → AI scores every lead 0–100 (Hot/Warm/Cold) → round-robin rep assignment → WhatsApp outreach to Hot leads → every touch logged to Google Sheets. A second daily branch pulls Meta/TikTok/LinkedIn/YouTube ad spend, computes CPL, CPLPV, CPP and ROAS per channel, and alerts on Telegram when a channel's CPL blows past your cap.\n\n"
    "**You'll need:**\n- OpenAI API key (platform.openai.com)\n- Google Sheets OAuth2 credentials\n- Telegram bot token + your chat ID (@BotFather → /newbot)\n- Meta/TikTok/LinkedIn/YouTube ad-account access + tokens (for the attribution branch)\n- A WhatsApp HTTP API endpoint (e.g. WAHA) for Hot-lead outreach\n\n"
    "**Status flow in Sheets:** `NEW` → `SCORED` → `ASSIGNED` → `CONTACTED` (returning leads flip to `TOUCHED`; low scores go to `NURTURE`)",
    -240, -160, 5600, 220, color=5))

nodes.append(sticky("STICKY — STEP 1",
    "## STEP 1 — Webhook lead intake + normalize\nForm/landing page POSTs name, email, phone, UTM tags and message → config (rep roster, thresholds, WhatsApp URL) → normalize email/phone/UTM.",
    -240, 180, 940, 420))

nodes.append(sticky("STICKY — STEP 2",
    "## STEP 2 — Dedupe + log to Google Sheets\nRead the Leads sheet → match on phone or email. Returning lead: flip status to `TOUCHED` + log a Journey touchpoint. New lead: append with status `NEW`.",
    720, 180, 1400, 420))

nodes.append(sticky("STICKY — STEP 3",
    "## STEP 3 — AI lead scoring\nAI Agent (gpt-4o-mini + Structured Output Parser) scores 0–100 and assigns a tier: Hot / Warm / Cold. Sheet flips to `SCORED`.",
    2140, 180, 760, 420))

nodes.append(sticky("STICKY — STEP 4",
    "## STEP 4 — Round-robin assignment + WhatsApp\nHot leads go to the senior rep (first in the roster) + instant WhatsApp. Warm leads rotate round-robin across reps. Cold leads go to `NURTURE`. Every touch is logged to the Journey sheet.",
    2920, 180, 1500, 420))

nodes.append(sticky("STICKY — STEP 5",
    "## STEP 5 — Lead alert\nAll branches merge → one Telegram alert with score, tier, channel, campaign and assigned rep.",
    4440, 180, 860, 420))

nodes.append(sticky("STICKY — STEP 6",
    "## STEP 6 — Daily attribution branch (08:00)\nSchedule trigger → fetch Meta/TikTok/LinkedIn/YouTube spend → join with Leads/Journey sheets → compute CPL, CPLPV, CPP, ROAS per channel → append a daily snapshot → Telegram alert for any channel over the CPL cap. Ad-fetch nodes have Continue On Fail ON: an unconfigured channel reports spend 0 instead of killing the run.",
    -240, 780, 3120, 560))

# ---------- LEAD PATH ----------
nodes.append({
    "parameters": {
        "httpMethod": "POST",
        "path": "marketing-lead",
        "responseMode": "lastNode",
        "options": {},
    },
    "id": uid(), "name": "Lead Webhook", "type": "n8n-nodes-base.webhook",
    "typeVersion": 2, "position": [0, 300],
})

nodes.append(set_node("CONFIG — Lead Engine", [
    ("hot_threshold", "70"),
    ("warm_threshold", "40"),
    ("rep_roster", "Rep One:PASTE_REP_1_EMAIL,Rep Two:PASTE_REP_2_EMAIL,Rep Three:PASTE_REP_3_EMAIL"),
    ("whatsapp_api_url", "PASTE_YOUR_WHATSAPP_API_URL"),
    ("whatsapp_enabled", "true"),
], 240, 300))

nodes.append(code_node("Normalize Lead", """// Normalize a raw lead submission: lowercase/trim email, digits-only phone, parsed UTM
const b = ($input.first().json.body && typeof $input.first().json.body === 'object')
  ? $input.first().json.body
  : $input.first().json;
const norm = (v) => String(v || '').trim().toLowerCase();
const phone = String(b.phone || '').replace(/[^+\\d]/g, '');
return [{ json: {
  name: String(b.name || '').trim(),
  email: norm(b.email),
  phone,
  message: String(b.message || '').trim(),
  utm_source: norm(b.utm_source || b.utmSource || 'direct'),
  utm_medium: norm(b.utm_medium || b.utmMedium || ''),
  utm_campaign: String(b.utm_campaign || b.utmCampaign || '').trim().toLowerCase(),
  date_received: new Date().toISOString().slice(0, 10),
  status: 'NEW',
}}];""", 480, 300))

nodes.append(set_node("CONFIG — Google Sheets", [
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("leads_sheet", "Leads"),
    ("journey_sheet", "Journey"),
    ("attribution_sheet", "Attribution"),
], 720, 300))

nodes.append(sheets_node("Read Leads Sheet", "read", "Leads", None, 960, 300))

nodes.append(code_node("Check Dedup", """// Match the normalized lead against existing Leads rows by phone or email
const lead = $('Normalize Lead').first().json;
const rows = $input.all().map(i => i.json);
const normEmail = (v) => String(v || '').trim().toLowerCase();
const normPhone = (v) => String(v || '').replace(/[^+\\d]/g, '');
const match = rows.find(r => {
  const e = normEmail(r['Email']);
  const p = normPhone(r['Phone']);
  return (lead.email && e === lead.email) || (lead.phone && p === lead.phone);
});
return [{ json: {
  ...lead,
  is_duplicate: !!match,
  existing_rep: match ? (match['Assigned Rep'] || '') : '',
}}];""", 1200, 300))

nodes.append(if_node("IF — Duplicate Lead?",
    "={{ $json.is_duplicate }}", "", 
    {"type": "boolean", "operation": "true", "name": "filter.operator.boolean.true"},
    1440, 300))

nodes.append(sheets_node("Update Lead — Status TOUCHED", "update", "Leads", {
    "Email": "={{ $json.email }}",
    "Status": "TOUCHED",
    "Last Touch Date": "={{ $json.date_received }}",
}, 1680, 140, matching=["Email"]))

nodes.append(sheets_node("Log Journey — Returning Lead", "append", "Journey", {
    "Date": "={{ $json.date_received }}",
    "Email": "={{ $json.email }}",
    "Phone": "={{ $json.phone }}",
    "Channel": "={{ $json.utm_source }}",
    "Campaign": "={{ $json.utm_campaign }}",
    "Touch Type": "Returning lead — repeat submission",
    "Rep": "={{ $json.existing_rep }}",
    "Notes": "Duplicate detected by phone/email; routed to existing rep",
}, 1920, 140))

nodes.append(sheets_node("Log New Lead — Status NEW", "append", "Leads", {
    "Date Received": "={{ $json.date_received }}",
    "Name": "={{ $json.name }}",
    "Email": "={{ $json.email }}",
    "Phone": "={{ $json.phone }}",
    "Message": "={{ $json.message }}",
    "UTM Source": "={{ $json.utm_source }}",
    "UTM Medium": "={{ $json.utm_medium }}",
    "UTM Campaign": "={{ $json.utm_campaign }}",
    "Status": "={{ $json.status }}",
}, 1680, 300))

nodes.append(set_node("CONFIG — AI Scoring", [
    ("openai_model", "gpt-4o-mini"),
    ("business_context", "PASTE_YOUR_BUSINESS_CONTEXT (what you sell, who your ideal customer is, 2-3 sentences)"),
], 1920, 300))

nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are a senior sales-qualification analyst. Score this inbound lead 0-100 for buying intent and fit.\n\nBUSINESS CONTEXT:\n{{ $('CONFIG — AI Scoring').first().json.business_context }}\n\nScoring guidance: a real name + business email + specific message about a real need scores high; vague one-liners, free-mail throwaways, gibberish or obvious spam score low. Hot = 70+, Warm = 40-69, Cold = below 40. Output ONLY via the structured output parser.",
        },
        "text": "=Name: {{ $json.name }}\nEmail: {{ $json.email }}\nPhone: {{ $json.phone }}\nChannel: {{ $json.utm_source }} / {{ $json.utm_medium }} / {{ $json.utm_campaign }}\nMessage:\n{{ $json.message }}",
    },
    "id": uid(), "name": "AI Agent — Score Lead", "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7, "position": [2160, 300],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model — Scoring", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.2, "position": [2160, 560],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n  \"lead_score\": 0,\n  \"tier\": \"Hot / Warm / Cold\",\n  \"reason\": \"one sentence explaining the score\",\n  \"intent\": \"buying intent in 3-5 words\",\n  \"spam_risk\": \"low / medium / high\"\n}",
    },
    "id": uid(), "name": "Structured Output Parser — Lead Score", "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.2, "position": [2400, 560],
})

nodes.append(sheets_node("Update Sheet — Status SCORED", "update", "Leads", {
    "Email": "={{ $json.email }}",
    "Lead Score": "={{ $json.output.lead_score }}",
    "Tier": "={{ $json.output.tier }}",
    "Score Reason": "={{ $json.output.reason }}",
    "Status": "SCORED",
}, 2400, 300, matching=["Email"]))

nodes.append(if_node("IF — Hot Lead",
    "={{ $json.output.lead_score }}",
    "={{ $('CONFIG — Lead Engine').first().json.hot_threshold }}",
    {"type": "number", "operation": "largerEqual", "name": "filter.operator.number.largerEqual"},
    2640, 300))

ASSIGN_HOT_JS = """// Round-robin rep assignment — Hot leads go to the senior rep (first in the roster)
const cfg = $('CONFIG — Lead Engine').first().json;
const roster = String(cfg.rep_roster || '').split(',').map(s => s.trim()).filter(Boolean).map(s => {
  const parts = s.split(':').map(x => (x || '').trim());
  return { name: parts[0] || 'Unassigned', email: parts[1] || '' };
});
const lead = $input.first().json;
const rep = roster.length ? roster[0] : { name: 'Unassigned', email: '' };
return [{ json: { ...lead, lead_tier: 'Hot', assigned_rep: rep.name, assigned_rep_email: rep.email } }];"""

ASSIGN_WARM_JS = """// Round-robin rep assignment — rotate by the number of leads already in the sheet
const cfg = $('CONFIG — Lead Engine').first().json;
const roster = String(cfg.rep_roster || '').split(',').map(s => s.trim()).filter(Boolean).map(s => {
  const parts = s.split(':').map(x => (x || '').trim());
  return { name: parts[0] || 'Unassigned', email: parts[1] || '' };
});
const leadCount = $('Read Leads Sheet').all().length;
const lead = $input.first().json;
const rep = roster.length ? roster[leadCount % roster.length] : { name: 'Unassigned', email: '' };
return [{ json: { ...lead, lead_tier: 'Warm', assigned_rep: rep.name, assigned_rep_email: rep.email } }];"""

nodes.append(code_node("Assign Rep — Round-Robin (Hot)", ASSIGN_HOT_JS, 2880, 140))
nodes.append(sheets_node("Update Sheet — Status ASSIGNED (Hot)", "update", "Leads", {
    "Email": "={{ $json.email }}",
    "Assigned Rep": "={{ $json.assigned_rep }}",
    "Status": "ASSIGNED",
}, 3120, 140, matching=["Email"]))

nodes.append(http_node("Send WhatsApp — Hot Lead", "POST",
    "={{ $('CONFIG — Lead Engine').first().json.whatsapp_api_url }}",
    3360, 140, extra={
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ chatId: $json.phone + '@c.us', text: 'Hi ' + $json.name + ' — thanks for reaching out about ' + ($json.utm_campaign || 'our services') + '. A specialist will call you shortly.' }) }}",
    }))

nodes.append(sheets_node("Update Sheet — Status CONTACTED", "update", "Leads", {
    "Email": "={{ $('Assign Rep — Round-Robin (Hot)').first().json.email }}",
    "Status": "CONTACTED",
}, 3600, 140, matching=["Email"]))

nodes.append(sheets_node("Log Journey — Hot Assigned", "append", "Journey", {
    "Date": "={{ $('Normalize Lead').first().json.date_received }}",
    "Email": "={{ $('Assign Rep — Round-Robin (Hot)').first().json.email }}",
    "Phone": "={{ $('Normalize Lead').first().json.phone }}",
    "Channel": "={{ $('Normalize Lead').first().json.utm_source }}",
    "Campaign": "={{ $('Normalize Lead').first().json.utm_campaign }}",
    "Touch Type": "Assigned — Hot lead",
    "Rep": "={{ $('Assign Rep — Round-Robin (Hot)').first().json.assigned_rep }}",
    "Notes": "WhatsApp sent to hot lead",
}, 3840, 140))

nodes.append(if_node("IF — Warm Lead",
    "={{ $json.output.lead_score }}",
    "={{ $('CONFIG — Lead Engine').first().json.warm_threshold }}",
    {"type": "number", "operation": "largerEqual", "name": "filter.operator.number.largerEqual"},
    2880, 300))

nodes.append(code_node("Assign Rep — Round-Robin (Warm)", ASSIGN_WARM_JS, 3120, 460))
nodes.append(sheets_node("Update Sheet — Status ASSIGNED (Warm)", "update", "Leads", {
    "Email": "={{ $json.email }}",
    "Assigned Rep": "={{ $json.assigned_rep }}",
    "Status": "ASSIGNED",
}, 3360, 460, matching=["Email"]))

nodes.append(sheets_node("Log Journey — Warm Assigned", "append", "Journey", {
    "Date": "={{ $('Normalize Lead').first().json.date_received }}",
    "Email": "={{ $('Assign Rep — Round-Robin (Warm)').first().json.email }}",
    "Phone": "={{ $('Normalize Lead').first().json.phone }}",
    "Channel": "={{ $('Normalize Lead').first().json.utm_source }}",
    "Campaign": "={{ $('Normalize Lead').first().json.utm_campaign }}",
    "Touch Type": "Assigned — Warm lead",
    "Rep": "={{ $('Assign Rep — Round-Robin (Warm)').first().json.assigned_rep }}",
    "Notes": "Warm lead assigned round-robin; no WhatsApp sent",
}, 3600, 460))

nodes.append(sheets_node("Update Sheet — Status NURTURE", "update", "Leads", {
    "Email": "={{ $json.email }}",
    "Status": "NURTURE",
}, 3120, 300, matching=["Email"]))

nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge — Lead Branches", "type": "n8n-nodes-base.merge",
    "typeVersion": 3, "position": [4320, 300],
})

nodes.append(code_node("Build Lead Alert", """// Build one Telegram alert from whichever lead branch ran
const items = $input.all().map(i => i.json);
const j = items[0] || {};
const val = (...keys) => { for (const k of keys) { if (j[k] !== undefined && j[k] !== null && j[k] !== '') return j[k]; } return ''; };
const score = j.output ? j.output.lead_score : val('Lead Score', 'lead_score');
const tier = j.output ? j.output.tier : val('Tier', 'lead_tier', 'tier');
const lines = [
  `🎯 *New lead — ${tier || '—'} (${score ?? '?'}/100)*`,
  ``,
  `👤 ${val('name', 'Name')}`,
  `📧 ${val('email', 'Email')}`,
  `📱 ${val('phone', 'Phone')}`,
  `📣 ${val('utm_source', 'Channel') || 'direct'} / ${val('utm_campaign', 'Campaign')}`,
  `🧑‍💼 Rep: ${val('assigned_rep', 'Assigned Rep', 'Rep') || '—'}`,
  `📌 Status: ${val('status', 'Status') || ''}`,
];
return [{ json: { alert: lines.join('\\n') } }];""", 4560, 300))

nodes.append(set_node("CONFIG — Notifications", [
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 4800, 300))

nodes.append(telegram_node("Telegram — Send Lead Alert", "={{ $json.alert }}", 5040, 300))

# ---------- ATTRIBUTION BRANCH ----------
nodes.append({
    "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 24, "triggerAtHour": 8, "triggerAtMinute": 0}]}},
    "id": uid(), "name": "Daily 8AM Attribution Trigger", "type": "n8n-nodes-base.scheduleTrigger",
    "typeVersion": 1.2, "position": [0, 1000],
})

nodes.append(set_node("CONFIG — Attribution", [
    ("meta_ad_account_id", "PASTE_YOUR_META_AD_ACCOUNT_ID"),
    ("meta_access_token", "PASTE_YOUR_META_ACCESS_TOKEN"),
    ("tiktok_insights_url", "PASTE_YOUR_TIKTOK_INSIGHTS_URL"),
    ("linkedin_insights_url", "PASTE_YOUR_LINKEDIN_INSIGHTS_URL"),
    ("youtube_analytics_url", "PASTE_YOUR_YOUTUBE_ANALYTICS_URL"),
    ("cpl_cap", "50"),
    ("avg_deal_value", "100"),
    ("currency", "USD"),
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 240, 1000))

nodes.append(http_node("Fetch Meta Insights", "GET",
    "https://graph.facebook.com/v21.0/act_={{ $('CONFIG — Attribution').first().json.meta_ad_account_id }}/insights",
    480, 1000, extra={
        "sendQuery": True,
        "queryParameters": {"parameters": [
            {"name": "fields", "value": "spend,impressions,clicks,actions"},
            {"name": "date_preset", "value": "yesterday"},
            {"name": "access_token", "value": "={{ $('CONFIG — Attribution').first().json.meta_access_token }}"},
        ]},
    }, continue_on_fail=True))

nodes.append(http_node("Fetch TikTok Insights", "GET",
    "={{ $('CONFIG — Attribution').first().json.tiktok_insights_url }}",
    720, 1000, continue_on_fail=True))

nodes.append(http_node("Fetch LinkedIn Insights", "GET",
    "={{ $('CONFIG — Attribution').first().json.linkedin_insights_url }}",
    960, 1000, continue_on_fail=True))

nodes.append(http_node("Fetch YouTube Analytics", "GET",
    "={{ $('CONFIG — Attribution').first().json.youtube_analytics_url }}",
    1200, 1000, continue_on_fail=True))

nodes.append(sheets_node("Read Leads Sheet — Attribution", "read", "Leads", None, 1440, 1000))

nodes.append(code_node("Compute Attribution Metrics", """// Per-channel CPL / CPLPV / CPP / ROAS from ad spend + Leads sheet counts
const cfg = $('CONFIG — Attribution').first().json;
const cap = parseFloat(cfg.cpl_cap || '50');
const adv = parseFloat(cfg.avg_deal_value || '100');
const leads = $('Read Leads Sheet — Attribution').all().map(i => i.json);
const countBy = (src) => leads.filter(r => String(r['UTM Source'] || '').toLowerCase() === src).length;
const convBy = (src) => leads.filter(r => String(r['UTM Source'] || '').toLowerCase() === src && String(r['Status'] || '').toUpperCase() === 'CONTACTED').length;
const spendOf = (node) => {
  try {
    const d = $(node).first().json;
    const arr = d.data || [];
    if (!Array.isArray(arr)) return 0;
    return arr.reduce((a, x) => a + parseFloat(x.spend || 0), 0);
  } catch (e) { return 0; }
};
const channels = [
  { channel: 'Meta', spend: spendOf('Fetch Meta Insights') },
  { channel: 'TikTok', spend: spendOf('Fetch TikTok Insights') },
  { channel: 'LinkedIn', spend: spendOf('Fetch LinkedIn Insights') },
  { channel: 'YouTube', spend: spendOf('Fetch YouTube Analytics') },
];
const today = new Date().toISOString().slice(0, 10);
return channels.map(c => {
  const n = countBy(c.channel.toLowerCase());
  const conv = convBy(c.channel.toLowerCase());
  const cpl = n ? c.spend / n : 0;
  const cpp = conv ? c.spend / conv : 0;
  const revenue = conv * adv;
  const roas = c.spend ? revenue / c.spend : 0;
  return { json: {
    date: today, channel: c.channel,
    spend: +c.spend.toFixed(2), leads: n, conversions: conv,
    cpl: +cpl.toFixed(2), cplpv: +cpl.toFixed(2), cpp: +cpp.toFixed(2),
    roas: +roas.toFixed(2), cpl_cap: cap, over_cap: cpl > cap,
  } };
});""", 1680, 1000))

nodes.append(sheets_node("Log Attribution Snapshot", "append", "Attribution", {
    "Date": "={{ $json.date }}",
    "Channel": "={{ $json.channel }}",
    "Spend": "={{ $json.spend }}",
    "Leads": "={{ $json.leads }}",
    "Conversions": "={{ $json.conversions }}",
    "CPL": "={{ $json.cpl }}",
    "CPLPV": "={{ $json.cplpv }}",
    "CPP": "={{ $json.cpp }}",
    "ROAS": "={{ $json.roas }}",
}, 1920, 1000))

nodes.append(if_node("IF — CPL Over Cap",
    "={{ $json.cpl }}", "={{ $json.cpl_cap }}",
    {"type": "number", "operation": "larger", "name": "filter.operator.number.larger"},
    2160, 1000))

nodes.append(code_node("Build CPL Alert", """// Alert listing every channel whose CPL is over the configured cap
const items = $input.all().map(i => i.json);
const lines = [`⚠️ *CPL over cap — ${new Date().toISOString().slice(0, 10)}*`, ``];
for (const c of items) {
  lines.push(`• *${c.channel}* — CPL $${c.cpl} (cap $${c.cpl_cap}), spend $${c.spend}, ${c.leads} leads, ROAS ${c.roas}x`);
}
lines.push(``, `Check the Attribution sheet and pause or reallocate budget.`);
return [{ json: { alert: lines.join('\\n') } }];""", 2400, 840))

# CPL alert uses CONFIG — Attribution's chat id (this branch runs on its own
# schedule, so CONFIG — Notifications from the lead path has no data here).
nodes.append({
    "parameters": {
        "chatId": "={{ $('CONFIG — Attribution').first().json.telegram_chat_id }}",
        "text": "={{ $json.alert }}",
        "additionalFields": {"parse_mode": "Markdown"},
    },
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": "Telegram — CPL Alert", "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2, "position": [2640, 840],
})

connections = {
    "Lead Webhook": {"main": [[{"node": "CONFIG — Lead Engine", "type": "main", "index": 0}]]},
    "CONFIG — Lead Engine": {"main": [[{"node": "Normalize Lead", "type": "main", "index": 0}]]},
    "Normalize Lead": {"main": [[{"node": "CONFIG — Google Sheets", "type": "main", "index": 0}]]},
    "CONFIG — Google Sheets": {"main": [[{"node": "Read Leads Sheet", "type": "main", "index": 0}]]},
    "Read Leads Sheet": {"main": [[{"node": "Check Dedup", "type": "main", "index": 0}]]},
    "Check Dedup": {"main": [[{"node": "IF — Duplicate Lead?", "type": "main", "index": 0}]]},
    "IF — Duplicate Lead?": {"main": [
        [{"node": "Update Lead — Status TOUCHED", "type": "main", "index": 0}],
        [{"node": "Log New Lead — Status NEW", "type": "main", "index": 0}],
    ]},
    "Update Lead — Status TOUCHED": {"main": [[{"node": "Log Journey — Returning Lead", "type": "main", "index": 0}]]},
    "Log Journey — Returning Lead": {"main": [[{"node": "Merge — Lead Branches", "type": "main", "index": 1}]]},
    "Log New Lead — Status NEW": {"main": [[{"node": "CONFIG — AI Scoring", "type": "main", "index": 0}]]},
    "CONFIG — AI Scoring": {"main": [[{"node": "AI Agent — Score Lead", "type": "main", "index": 0}]]},
    "AI Agent — Score Lead": {"main": [[{"node": "Update Sheet — Status SCORED", "type": "main", "index": 0}]]},
    "Update Sheet — Status SCORED": {"main": [[{"node": "IF — Hot Lead", "type": "main", "index": 0}]]},
    "IF — Hot Lead": {"main": [
        [{"node": "Assign Rep — Round-Robin (Hot)", "type": "main", "index": 0}],
        [{"node": "IF — Warm Lead", "type": "main", "index": 0}],
    ]},
    "Assign Rep — Round-Robin (Hot)": {"main": [[{"node": "Update Sheet — Status ASSIGNED (Hot)", "type": "main", "index": 0}]]},
    "Update Sheet — Status ASSIGNED (Hot)": {"main": [[{"node": "Send WhatsApp — Hot Lead", "type": "main", "index": 0}]]},
    "Send WhatsApp — Hot Lead": {"main": [[{"node": "Update Sheet — Status CONTACTED", "type": "main", "index": 0}]]},
    "Update Sheet — Status CONTACTED": {"main": [[{"node": "Log Journey — Hot Assigned", "type": "main", "index": 0}]]},
    "Log Journey — Hot Assigned": {"main": [[{"node": "Merge — Lead Branches", "type": "main", "index": 0}]]},
    "IF — Warm Lead": {"main": [
        [{"node": "Assign Rep — Round-Robin (Warm)", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status NURTURE", "type": "main", "index": 0}],
    ]},
    "Assign Rep — Round-Robin (Warm)": {"main": [[{"node": "Update Sheet — Status ASSIGNED (Warm)", "type": "main", "index": 0}]]},
    "Update Sheet — Status ASSIGNED (Warm)": {"main": [[{"node": "Log Journey — Warm Assigned", "type": "main", "index": 0}]]},
    "Log Journey — Warm Assigned": {"main": [[{"node": "Merge — Lead Branches", "type": "main", "index": 0}]]},
    "Update Sheet — Status NURTURE": {"main": [[{"node": "Merge — Lead Branches", "type": "main", "index": 1}]]},
    "Merge — Lead Branches": {"main": [[{"node": "Build Lead Alert", "type": "main", "index": 0}]]},
    "Build Lead Alert": {"main": [[{"node": "CONFIG — Notifications", "type": "main", "index": 0}]]},
    "CONFIG — Notifications": {"main": [[{"node": "Telegram — Send Lead Alert", "type": "main", "index": 0}]]},
    "OpenAI Chat Model — Scoring": {"ai_languageModel": [[{"node": "AI Agent — Score Lead", "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser — Lead Score": {"ai_outputParser": [[{"node": "AI Agent — Score Lead", "type": "ai_outputParser", "index": 0}]]},
    "Daily 8AM Attribution Trigger": {"main": [[{"node": "CONFIG — Attribution", "type": "main", "index": 0}]]},
    "CONFIG — Attribution": {"main": [[{"node": "Fetch Meta Insights", "type": "main", "index": 0}]]},
    "Fetch Meta Insights": {"main": [[{"node": "Fetch TikTok Insights", "type": "main", "index": 0}]]},
    "Fetch TikTok Insights": {"main": [[{"node": "Fetch LinkedIn Insights", "type": "main", "index": 0}]]},
    "Fetch LinkedIn Insights": {"main": [[{"node": "Fetch YouTube Analytics", "type": "main", "index": 0}]]},
    "Fetch YouTube Analytics": {"main": [[{"node": "Read Leads Sheet — Attribution", "type": "main", "index": 0}]]},
    "Read Leads Sheet — Attribution": {"main": [[{"node": "Compute Attribution Metrics", "type": "main", "index": 0}]]},
    "Compute Attribution Metrics": {"main": [[{"node": "Log Attribution Snapshot", "type": "main", "index": 0}]]},
    "Log Attribution Snapshot": {"main": [[{"node": "IF — CPL Over Cap", "type": "main", "index": 0}]]},
    "IF — CPL Over Cap": {"main": [
        [{"node": "Build CPL Alert", "type": "main", "index": 0}],
        [],
    ]},
    "Build CPL Alert": {"main": [[{"node": "Telegram — CPL Alert", "type": "main", "index": 0}]]},
}

wf = {
    "name": "Marketing Attribution & Lead Engine",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/marketing-attribution-lead-engine.json"
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
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook.com"]:
    assert bad not in blob, f"possible hardcoded secret: {bad}"
print("validation OK: all", len(names), "nodes connected, no hardcoded secrets")
