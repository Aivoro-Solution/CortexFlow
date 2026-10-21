#!/usr/bin/env python3
"""Generate the AI Jira Ticket Autopilot n8n workflow JSON.

Inspired by n8n community forum demand (Oct 21, 2026):
"N8n workflow idea: notify your team when an AI agent finishes a Jira ticket".
Hourly: fetch open Jira tickets -> dedupe/log -> AI triage (structured output) ->
auto-resolve (comment + Done transition + label) or escalate -> team Telegram digest.
"""
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

def http_node(name, params, x, y):
    return {
        "parameters": params,
        "id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2, "position": [x, y],
    }

def sheets_node(name, operation, columns_value, matching, x, y):
    return {
        "parameters": {
            "operation": operation,
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": "TicketLog"},
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

D = "\u2014"  # em dash used in node names
nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY " + D + " Title",
    "## \U0001f3af AI JIRA TICKET AUTOPILOT\n"
    "**What it does:** Every hour \u2192 fetches open Jira tickets \u2192 dedupes against Google Sheets \u2192 an AI agent triages each ticket with structured output \u2192 safe tickets get auto-resolved (Jira comment + Done transition + `ai-resolved` label) \u2192 risky tickets get escalated to a human \u2192 your team gets one Telegram digest.\n\n"
    "**You'll need:**\n- Jira Cloud (free at atlassian.com) + an API token (Atlassian account \u2192 Security \u2192 API tokens)\n- OpenAI API key (platform.openai.com)\n- Google Sheets OAuth2 credential\n- Telegram bot token + your chat ID (@BotFather \u2192 /newbot)\n\n"
    "**Status flow in Sheets:** `NEW` \u2192 `TRIAGED` \u2192 `RESOLVED` / `ESCALATED`",
    -240, -160, 5980, 220, color=5))

nodes.append(sticky("STICKY " + D + " STEP 1",
    "## STEP 1 " + D + " Fetch open Jira tickets\nHourly schedule trigger \u2192 Basic-auth header built from your Jira email + API token \u2192 Jira REST API `/rest/api/3/search` with JQL `project=<key> AND status in (\"To Do\",\"Open\")` \u2192 normalize key/summary/description/priority/reporter/URL.",
    -240, 180, 1160, 420))

nodes.append(sticky("STICKY " + D + " STEP 2",
    "## STEP 2 " + D + " Dedupe + log to Google Sheets\nRead already-logged ticket keys \u2192 keep only new tickets \u2192 append rows with status `NEW`.",
    940, 180, 1140, 420))

nodes.append(sticky("STICKY " + D + " STEP 3",
    "## STEP 3 " + D + " AI triage with structured output\nAI Ticket Triage Agent (gpt-4o-mini) decides per ticket: auto-resolve or escalate \u2014 returns can_resolve, confidence 0\u2013100, category, resolution comment, escalation reason via a Structured Output Parser \u2192 sheet flips to `TRIAGED`.",
    2120, 180, 980, 420))

nodes.append(sticky("STICKY " + D + " STEP 4",
    "## STEP 4 " + D + " Auto-resolve / escalate gate\n`IF " + D + " Auto-Resolve?` passes only can_resolve=true AND confidence \u2265 your threshold.\nTRUE: post the AI's resolution comment \u2192 look up the Jira \"Done\" transition \u2192 transition the ticket \u2192 add your `ai-resolved` label \u2192 sheet flips to `RESOLVED`.\nFALSE: sheet flips to `ESCALATED` with the AI's escalation reason for a human.",
    3040, 20, 1640, 560))

nodes.append(sticky("STICKY " + D + " STEP 5",
    "## STEP 5 " + D + " Team digest + Telegram\nBoth branches merge \u2192 one digest built (resolved count + escalated count + per-ticket lines with links) \u2192 Telegram to your team.",
    4720, 180, 1020, 420))

# ---------- MAIN CHAIN ----------
nodes.append({
    "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}},
    "id": uid(), "name": "Hourly Trigger", "type": "n8n-nodes-base.scheduleTrigger",
    "typeVersion": 1.2, "position": [0, 300],
})

nodes.append(set_node("CONFIG " + D + " Jira + AI", [
    ("jira_host", "yourcompany.atlassian.net"),
    ("jira_email", "PASTE_YOUR_JIRA_EMAIL"),
    ("jira_api_token", "PASTE_YOUR_JIRA_API_TOKEN"),
    ("project_key", "PROJ"),
    ("confidence_threshold", "75"),
    ("openai_model", "gpt-4o-mini"),
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("sheet_name", "TicketLog"),
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
    ("label_resolved", "ai-resolved"),
], 240, 300))

nodes.append(code_node("Build Jira Auth Header", r"""// Build the Jira Basic auth header from email + API token (no creds hardcoded)
const cfg = $('CONFIG — Jira + AI').first().json;
const email = (cfg.jira_email || '').trim();
const token = (cfg.jira_api_token || '').trim();
if (!email || !token || token.indexOf('PASTE_YOUR') === 0 || email.indexOf('PASTE_YOUR') === 0) {
  throw new Error('Fill jira_email and jira_api_token in the "CONFIG — Jira + AI" node first (Atlassian account → Security → API tokens).');
}
const auth = 'Basic ' + Buffer.from(email + ':' + token, 'utf8').toString('base64');
return $input.all().map(i => ({ json: { ...i.json, auth_header: auth } }));""", 500, 300))

nodes.append(http_node("Jira " + D + " Fetch Open Tickets", {
    "method": "GET",
    "url": "=https://{{ $('CONFIG " + D + " Jira + AI').first().json.jira_host }}/rest/api/3/search",
    "sendQuery": True,
    "queryParameters": {"parameters": [
        {"name": "jql", "value": "=project={{ $('CONFIG " + D + " Jira + AI').first().json.project_key }} AND status in (\"To Do\",\"Open\") ORDER BY created DESC"},
        {"name": "maxResults", "value": "25"},
        {"name": "fields", "value": "summary,description,priority,status,reporter,created"},
    ]},
    "sendHeaders": True,
    "headerParameters": {"parameters": [
        {"name": "Authorization", "value": "={{ $('Build Jira Auth Header').first().json.auth_header }}"},
        {"name": "Accept", "value": "application/json"},
    ]},
    "options": {},
}, 760, 300))

nodes.append(code_node("Normalize Tickets", r"""// Flatten Jira issues into clean ticket objects (ADF description -> plain text)
function adfText(node) {
  if (!node) return '';
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(adfText).join('\n');
  let t = node.text || '';
  if (node.content) t += (t ? '\n' : '') + adfText(node.content);
  return t;
}
const cfg = $('CONFIG — Jira + AI').first().json;
const host = (cfg.jira_host || '').trim();
const issues = $input.first().json.issues || [];
return issues.map(issue => {
  const f = issue.fields || {};
  return { json: {
    ticket_key: issue.key,
    summary: (f.summary || '').slice(0, 200),
    description: adfText(f.description).slice(0, 2000),
    priority: (f.priority && f.priority.name) || '',
    status: (f.status && f.status.name) || '',
    reporter: (f.reporter && f.reporter.displayName) || '',
    created: f.created || '',
    ticket_url: 'https://' + host + '/browse/' + issue.key,
    status_flow: 'NEW',
  }};
});""", 1020, 300))

nodes.append(sheets_node("Read Logged Ticket Keys", "read", {}, [], 1280, 300))

nodes.append(code_node("Filter New Tickets Only", r"""// Drop tickets whose key is already in the sheet
const seen = new Set(
  $('Read Logged Ticket Keys').all().map(i => (i.json['Ticket Key'] || i.json.ticket_key || '').trim()).filter(Boolean)
);
const fresh = $('Normalize Tickets').all()
  .map(i => i.json)
  .filter(t => t.ticket_key && !seen.has(t.ticket_key.trim()));
return fresh.map(t => ({ json: t }));""", 1540, 300))

nodes.append(sheets_node("Log Tickets " + D + " Status NEW", "append", {
    "Ticket Key": "={{ $json.ticket_key }}",
    "Summary": "={{ $json.summary }}",
    "Priority": "={{ $json.priority }}",
    "Reporter": "={{ $json.reporter }}",
    "Ticket URL": "={{ $json.ticket_url }}",
    "Created": "={{ $json.created }}",
    "Status": "NEW",
}, [], 1800, 300))

nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are a senior support engineer triaging Jira tickets for project {{ $('CONFIG " + D + " Jira + AI').first().json.project_key }}. For each ticket decide: can it be safely AUTO-RESOLVED (clear question with a known answer, simple config/access change with a documented procedure, duplicate of an already-resolved ticket) or must it be ESCALATED to a human (ambiguous requirements, production incidents, security issues, anything touching customer data, billing, or access grants, low confidence)? Be conservative: when in doubt, escalate. Output ONLY via the structured output parser — no prose.",
        },
        "text": "=Ticket: {{ $json.ticket_key }} — {{ $json.summary }}\nPriority: {{ $json.priority }} | Status: {{ $json.status }} | Reporter: {{ $json.reporter }}\nURL: {{ $json.ticket_url }}\n\nDescription:\n{{ $json.description }}",
    },
    "id": uid(), "name": "AI Ticket Triage Agent", "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7, "position": [2060, 300],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model " + D + " Triage", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.2, "position": [2060, 560],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n  \"can_resolve\": true,\n  \"confidence\": 85,\n  \"summary\": \"one-line summary of the issue\",\n  \"category\": \"BUG / QUESTION / ACCESS_REQUEST / FEATURE_REQUEST / INCIDENT / OTHER\",\n  \"resolution_comment\": \"the exact comment to post on the Jira ticket when auto-resolving (empty string when escalating)\",\n  \"escalation_reason\": \"one-line reason a human must handle this (empty string when auto-resolving)\"\n}",
    },
    "id": uid(), "name": "Structured Output Parser " + D + " Triage", "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.2, "position": [2320, 560],
})

nodes.append(sheets_node("Update Sheet " + D + " Status TRIAGED", "update", {
    "Ticket Key": "={{ $json.ticket_key }}",
    "AI Summary": "={{ $json.output.summary }}",
    "Category": "={{ $json.output.category }}",
    "Can Resolve": "={{ $json.output.can_resolve }}",
    "Confidence": "={{ $json.output.confidence }}",
    "Escalation Reason": "={{ $json.output.escalation_reason }}",
    "Status": "TRIAGED",
}, ["Ticket Key"], 2320, 300))

nodes.append({
    "parameters": {
        "conditions": {
            "combinator": "and",
            "conditions": [
                {
                    "id": "if-can-resolve",
                    "leftValue": "={{ $json.output.can_resolve === true ? 'yes' : 'no' }}",
                    "rightValue": "yes",
                    "operator": {"type": "string", "operation": "equals", "name": "filter.operator.string.equals"},
                },
                {
                    "id": "if-confidence",
                    "leftValue": "={{ $json.output.confidence }}",
                    "rightValue": "={{ $('CONFIG " + D + " Jira + AI').first().json.confidence_threshold }}",
                    "operator": {"type": "number", "operation": "largerEqual", "name": "filter.operator.number.largerEqual"},
                },
            ],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "options": {},
    },
    "id": uid(), "name": "IF " + D + " Auto-Resolve?", "type": "n8n-nodes-base.if",
    "typeVersion": 2.2, "position": [2580, 300],
})

# ----- TRUE branch -----
nodes.append(http_node("Jira " + D + " Add Resolution Comment", {
    "method": "POST",
    "url": "=https://{{ $('CONFIG " + D + " Jira + AI').first().json.jira_host }}/rest/api/3/issue/{{ $json.ticket_key }}/comment",
    "sendHeaders": True,
    "headerParameters": {"parameters": [
        {"name": "Authorization", "value": "={{ $('Build Jira Auth Header').first().json.auth_header }}"},
        {"name": "Accept", "value": "application/json"},
        {"name": "Content-Type", "value": "application/json"},
    ]},
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": "={\"body\": {\"type\": \"doc\", \"version\": 1, \"content\": [{\"type\": \"paragraph\", \"content\": [{\"type\": \"text\", \"text\": \"{{ $json.output.resolution_comment }}\"}]}]}}",
    "options": {},
}, 2840, 140))

nodes.append(http_node("Jira " + D + " Get Transitions", {
    "method": "GET",
    "url": "=https://{{ $('CONFIG " + D + " Jira + AI').first().json.jira_host }}/rest/api/3/issue/{{ $('IF " + D + " Auto-Resolve?').item.json.ticket_key }}/transitions",
    "sendHeaders": True,
    "headerParameters": {"parameters": [
        {"name": "Authorization", "value": "={{ $('Build Jira Auth Header').first().json.auth_header }}"},
        {"name": "Accept", "value": "application/json"},
    ]},
    "options": {},
}, 3100, 140))

nodes.append(code_node("Pick Done Transition", r"""// Find the Jira "Done" transition id; carry ticket context forward (paired by index)
const ifItems = $('IF — Auto-Resolve?').all();
const auth = $('Build Jira Auth Header').first().json.auth_header;
return $input.all().map((item, i) => {
  const ticket = (ifItems[i] && ifItems[i].json) || {};
  const transitions = item.json.transitions || [];
  const done = transitions.find(t => String(t.name || '').toLowerCase() === 'done');
  if (!done) {
    throw new Error('No "Done" transition found for ticket ' + (ticket.ticket_key || '?') + ' — check your Jira workflow has a transition named "Done".');
  }
  return { json: {
    ticket_key: ticket.ticket_key,
    ticket_url: ticket.ticket_url,
    summary: ticket.summary,
    confidence: ticket.output ? ticket.output.confidence : 0,
    ai_category: ticket.output ? ticket.output.category : '',
    resolution_comment: ticket.output ? ticket.output.resolution_comment : '',
    done_transition_id: done.id,
    auth_header: auth,
  }};
});""", 3360, 140))

nodes.append(http_node("Jira " + D + " Transition to Done", {
    "method": "POST",
    "url": "=https://{{ $('CONFIG " + D + " Jira + AI').first().json.jira_host }}/rest/api/3/issue/{{ $('Pick Done Transition').item.json.ticket_key }}/transitions",
    "sendHeaders": True,
    "headerParameters": {"parameters": [
        {"name": "Authorization", "value": "={{ $('Pick Done Transition').item.json.auth_header }}"},
        {"name": "Accept", "value": "application/json"},
        {"name": "Content-Type", "value": "application/json"},
    ]},
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": "={\"transition\": {\"id\": \"{{ $('Pick Done Transition').item.json.done_transition_id }}\"}}",
    "options": {},
}, 3620, 140))

nodes.append(http_node("Jira " + D + " Add Resolved Label", {
    "method": "PUT",
    "url": "=https://{{ $('CONFIG " + D + " Jira + AI').first().json.jira_host }}/rest/api/3/issue/{{ $('Pick Done Transition').item.json.ticket_key }}",
    "sendHeaders": True,
    "headerParameters": {"parameters": [
        {"name": "Authorization", "value": "={{ $('Pick Done Transition').item.json.auth_header }}"},
        {"name": "Accept", "value": "application/json"},
        {"name": "Content-Type", "value": "application/json"},
    ]},
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": "={\"update\": {\"labels\": [{\"add\": \"{{ $('CONFIG " + D + " Jira + AI').first().json.label_resolved }}\"}]}}",
    "options": {},
}, 3880, 140))

nodes.append(code_node("Build Resolved Record", r"""// Rebuild a clean digest item after the Jira writes (paired by index with Pick output)
const ctx = $('Pick Done Transition').all();
return $input.all().map((item, i) => {
  const c = (ctx[i] && ctx[i].json) || {};
  return { json: {
    ticket_key: c.ticket_key,
    ticket_url: c.ticket_url,
    summary: c.summary,
    verdict: 'RESOLVED',
    confidence: c.confidence,
    ai_category: c.ai_category,
    resolution_comment: c.resolution_comment,
  }};
});""", 4140, 140))

nodes.append(sheets_node("Update Sheet " + D + " Status RESOLVED", "update", {
    "Ticket Key": "={{ $json.ticket_key }}",
    "Confidence": "={{ $json.confidence }}",
    "Category": "={{ $json.ai_category }}",
    "Resolution Comment": "={{ $json.resolution_comment }}",
    "Status": "RESOLVED",
}, ["Ticket Key"], 4400, 140))

# ----- FALSE branch -----
nodes.append(sheets_node("Update Sheet " + D + " Status ESCALATED", "update", {
    "Ticket Key": "={{ $json.ticket_key }}",
    "Escalation Reason": "={{ $json.output.escalation_reason }}",
    "Confidence": "={{ $json.output.confidence }}",
    "Category": "={{ $json.output.category }}",
    "Status": "ESCALATED",
}, ["Ticket Key"], 2840, 440))

# ----- digest -----
nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge " + D + " Combine Branches", "type": "n8n-nodes-base.merge",
    "typeVersion": 3, "position": [4660, 300],
})

nodes.append(code_node("Build Team Digest", r"""// One Telegram digest: resolved vs escalated tickets with links
const items = $input.all().map(i => i.json);
const date = new Date().toISOString().slice(0, 10);
const resolved = items.filter(j => j.verdict === 'RESOLVED');
const escalated = items.filter(j => j.verdict !== 'RESOLVED');
const lines = ['\U0001F3AF *AI Jira Ticket Autopilot — ' + date + '*', '',
  '\u2705 Auto-resolved: ' + resolved.length,
  '\U0001F6A8 Escalated to humans: ' + escalated.length, ''];
if (resolved.length) {
  lines.push('*Resolved:*');
  for (const r of resolved.slice(0, 15)) {
    lines.push('\u2022 ' + r.ticket_key + ' (' + r.confidence + '% confident) — ' + r.summary + ' ([open](' + r.ticket_url + '))');
  }
  lines.push('');
}
if (escalated.length) {
  lines.push('*Needs a human:*');
  for (const e of escalated.slice(0, 15)) {
    const reason = (e.output && e.output.escalation_reason) || 'no reason given';
    const key = e.ticket_key || '?';
    const url = e.ticket_url || '#';
    lines.push('\u2022 ' + key + ' — ' + reason + ' ([open](' + url + '))');
  }
}
return [{ json: { digest: lines.join('\n'), resolved: resolved.length, escalated: escalated.length } }];""", 4920, 300))

nodes.append({
    "parameters": {
        "chatId": "={{ $('CONFIG " + D + " Jira + AI').first().json.telegram_chat_id }}",
        "text": "={{ $json.digest }}",
        "additionalFields": {"parse_mode": "Markdown"},
    },
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": "Telegram " + D + " Send Digest", "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2, "position": [5180, 300],
})

connections = {
    "Hourly Trigger": {"main": [[{"node": "CONFIG " + D + " Jira + AI", "type": "main", "index": 0}]]},
    "CONFIG " + D + " Jira + AI": {"main": [[{"node": "Build Jira Auth Header", "type": "main", "index": 0}]]},
    "Build Jira Auth Header": {"main": [[{"node": "Jira " + D + " Fetch Open Tickets", "type": "main", "index": 0}]]},
    "Jira " + D + " Fetch Open Tickets": {"main": [[{"node": "Normalize Tickets", "type": "main", "index": 0}]]},
    "Normalize Tickets": {"main": [[{"node": "Read Logged Ticket Keys", "type": "main", "index": 0}]]},
    "Read Logged Ticket Keys": {"main": [[{"node": "Filter New Tickets Only", "type": "main", "index": 0}]]},
    "Filter New Tickets Only": {"main": [[{"node": "Log Tickets " + D + " Status NEW", "type": "main", "index": 0}]]},
    "Log Tickets " + D + " Status NEW": {"main": [[{"node": "AI Ticket Triage Agent", "type": "main", "index": 0}]]},
    "AI Ticket Triage Agent": {"main": [[{"node": "Update Sheet " + D + " Status TRIAGED", "type": "main", "index": 0}]]},
    "Update Sheet " + D + " Status TRIAGED": {"main": [[{"node": "IF " + D + " Auto-Resolve?", "type": "main", "index": 0}]]},
    "IF " + D + " Auto-Resolve?": {"main": [
        [{"node": "Jira " + D + " Add Resolution Comment", "type": "main", "index": 0}],
        [{"node": "Update Sheet " + D + " Status ESCALATED", "type": "main", "index": 1}],
    ]},
    "Jira " + D + " Add Resolution Comment": {"main": [[{"node": "Jira " + D + " Get Transitions", "type": "main", "index": 0}]]},
    "Jira " + D + " Get Transitions": {"main": [[{"node": "Pick Done Transition", "type": "main", "index": 0}]]},
    "Pick Done Transition": {"main": [[{"node": "Jira " + D + " Transition to Done", "type": "main", "index": 0}]]},
    "Jira " + D + " Transition to Done": {"main": [[{"node": "Jira " + D + " Add Resolved Label", "type": "main", "index": 0}]]},
    "Jira " + D + " Add Resolved Label": {"main": [[{"node": "Build Resolved Record", "type": "main", "index": 0}]]},
    "Build Resolved Record": {"main": [[{"node": "Update Sheet " + D + " Status RESOLVED", "type": "main", "index": 0}]]},
    "Update Sheet " + D + " Status RESOLVED": {"main": [[{"node": "Merge " + D + " Combine Branches", "type": "main", "index": 0}]]},
    "Update Sheet " + D + " Status ESCALATED": {"main": [[{"node": "Merge " + D + " Combine Branches", "type": "main", "index": 1}]]},
    "Merge " + D + " Combine Branches": {"main": [[{"node": "Build Team Digest", "type": "main", "index": 0}]]},
    "Build Team Digest": {"main": [[{"node": "Telegram " + D + " Send Digest", "type": "main", "index": 0}]]},
    "OpenAI Chat Model " + D + " Triage": {"ai_languageModel": [[{"node": "AI Ticket Triage Agent", "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser " + D + " Triage": {"ai_outputParser": [[{"node": "AI Ticket Triage Agent", "type": "ai_outputParser", "index": 0}]]},
}

wf = {
    "name": "AI Jira Ticket Autopilot",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/ai-jira-ticket-autopilot.json"
json.dump(wf, open(out, "w"), indent=2, ensure_ascii=False)
print("wrote", out, "| nodes:", len(nodes))

# ---- validation ----
d = json.load(open(out))
names = [n["name"] for n in d["nodes"]]
assert len(names) == len(set(names)), "duplicate node names"
ids = [n["id"] for n in d["nodes"]]
assert len(ids) == len(set(ids)), "duplicate node ids"
name_set = set(names)
missing = []
for src, conns in d["connections"].items():
    assert src in name_set, f"bad connection source {src}"
    for ctype, outs in conns.items():
        for branch in outs:
            for t in branch:
                if t["node"] not in name_set:
                    missing.append((src, t["node"]))
assert not missing, f"missing connection targets: {missing}"

# every non-sticky node is reachable as a connection target (except trigger + sub-nodes)
targets = set()
for conns in d["connections"].values():
    for outs in conns.values():
        for branch in outs:
            for t in branch:
                targets.add(t["node"])
sub_nodes = {"OpenAI Chat Model " + D + " Triage", "Structured Output Parser " + D + " Triage"}
for n in d["nodes"]:
    if n["type"] == "n8n-nodes-base.stickyNote" or n["name"] == "Hourly Trigger" or n["name"] in sub_nodes:
        continue
    assert n["name"] in targets, f"node not reachable: {n['name']}"

# stickies + config present
stickies = [n for n in d["nodes"] if n["type"] == "n8n-nodes-base.stickyNote"]
assert len(stickies) == 6, f"expected 6 stickies, got {len(stickies)}"
assert any(n["name"] == "STICKY " + D + " Title" for n in stickies)
assert sum(1 for n in stickies if "STEP" in n["name"]) == 5
assert any(n["name"] == "CONFIG " + D + " Jira + AI" for n in d["nodes"]), "CONFIG node missing"
# openai empty credential select on chat model
lm = next(n for n in d["nodes"] if n["name"] == "OpenAI Chat Model " + D + " Triage")
assert lm["credentials"]["openAiApi"]["id"] == "", "chat model credential not empty"
assert lm["parameters"]["model"]["value"] == "gpt-4o-mini"
tg = next(n for n in d["nodes"] if n["name"] == "Telegram " + D + " Send Digest")
assert tg["credentials"]["telegramApi"]["id"] == "", "telegram credential not empty"

# no hardcoded secrets
blob = json.dumps(d)
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook.com", "AKIA", "ghp_", "xoxp-"]:
    assert bad not in blob, f"possible hardcoded secret pattern: {bad}"
# placeholders still placeholders
assert blob.count("PASTE_YOUR_") >= 4, "expected PASTE_YOUR_ placeholders"
print("validation OK:", len(names), "nodes,", len(stickies), "stickies, all connections valid, no hardcoded secrets")
