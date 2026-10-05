#!/usr/bin/env python3
"""Generate public/templates/n8n-workflow-health-watchdog.json.

Watches your n8n instance via the public REST API: flags error executions,
error spikes per workflow, and active workflows that went quiet (no executions
in the stale window). Telegram alert + Sheets audit log.

Demand: n8n forum threads on silent failures / observability (100+ posts,
Sep-Oct 2026) + Reddit r/automation asks.
"""
import json
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "public" / "templates" / "n8n-workflow-health-watchdog.json"

def nid():
    return str(uuid.uuid4())

def node(name, ntype, type_version, params, x, y):
    return {
        "id": nid(),
        "name": name,
        "parameters": params,
        "position": [x, y],
        "type": ntype,
        "typeVersion": type_version,
    }

X = 240
STEP = 250
Y = 300
nodes = []

nodes.append({
    "id": nid(),
    "name": "Sticky Note",
    "parameters": {
        "content": "## n8n Workflow Health Watchdog\n\nPolls YOUR n8n instance's public API every hour and catches what the Executions tab won't tell you at a glance:\n\n- **ERROR_SPIKE** — a workflow throwing >= `error_spike_threshold` errors inside the check window (CRITICAL)\n- **ERRORS** — any failed/crashed executions in the window (WARNING)\n- **STALE** — an *active* workflow with zero executions in `stale_hours` (WARNING). Your weekly/monthly workflows belong in `ignore_workflows`.\n\nAuth: create a **Header Auth** credential in n8n (name `X-N8N-API-KEY`, value = your n8n API key from Settings > n8n API) and select it on both HTTP nodes. The API key needs permission to read workflows + executions.\n\nHonest limits: staleness is computed from the 250 most recent executions — on very busy instances the sample may not cover the full window. `startedAfter` needs n8n >= 1.x with the public API enabled; if your version rejects it, drop that query param (the limit still bounds the call).",
        "height": 620,
        "width": 430,
        "color": 4,
    },
    "position": [X - 270, Y - 140],
    "type": "n8n-nodes-base.stickyNote",
    "typeVersion": 1,
})

# 1. Schedule — hourly
nodes.append(node("Hourly Check", "n8n-nodes-base.scheduleTrigger", 1.2,
    {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}},
    X, Y))
X += STEP

# 2. CONFIG
nodes.append(node("CONFIG \u2014 Watchdog", "n8n-nodes-base.set", 3.4,
    {"assignments": {"assignments": [
        {"id": "c-1", "name": "n8n_host", "type": "string",
         "value": "https://your-n8n-domain.com"},
        {"id": "c-2", "name": "check_window_hours", "type": "number", "value": 24},
        {"id": "c-3", "name": "stale_hours", "type": "number", "value": 24},
        {"id": "c-4", "name": "error_spike_threshold", "type": "number", "value": 5},
        {"id": "c-5", "name": "ignore_workflows", "type": "array",
         "value": "[\"Weekly Report\", \"Monthly Cleanup\"]"},
        {"id": "c-6", "name": "telegram_chat_id", "type": "string",
         "value": "PASTE_YOUR_TELEGRAM_CHAT_ID"},
    ]}, "includeOtherFields": False, "options": {}},
    X, Y))
X += STEP

# 3. Get active workflows
http_auth_note = {"genericAuthType": "httpHeaderAuth"}
nodes.append(node("Get Active Workflows", "n8n-nodes-base.httpRequest", 4.2,
    {"method": "GET",
     "options": {"response": {"response": {"responseFormat": "autodetect"}},
                 "timeout": 15000},
     "url": "={{ $json.n8n_host }}/api/v1/workflows?active=true&limit=250",
     **http_auth_note},
    X, Y))
X += STEP

# 4. Get recent executions
nodes.append(node("Get Recent Executions", "n8n-nodes-base.httpRequest", 4.2,
    {"method": "GET",
     "options": {"response": {"response": {"responseFormat": "autodetect"}},
                 "timeout": 15000},
     "url": ("={{ $json.n8n_host }}/api/v1/executions?limit=250"
              "&startedAfter={{ $now.minus({ hours: $json.check_window_hours }).toISO() }}"),
     **http_auth_note},
    X, Y))
X += STEP

# 5. Analyze Health (Code)
analyze_js = """// Join active workflows with recent executions -> issues[]
const cfg = $('CONFIG \\u2014 Watchdog').first().json;
const workflowsResp = $('Get Active Workflows').first().json;
const execResp = $input.first().json;

const workflows = workflowsResp.data || workflowsResp || [];
const executions = execResp.data || execResp || [];

const now = Date.now();
const staleMs = Number(cfg.stale_hours) * 3600 * 1000;
const spikeAt = Number(cfg.error_spike_threshold);
const ignored = new Set(cfg.ignore_workflows || []);

const byWorkflow = {};
for (const e of executions) {
  if (!e.workflowId) continue;
  (byWorkflow[e.workflowId] = byWorkflow[e.workflowId] || []).push(e);
}

const issues = [];
for (const w of workflows) {
  if (ignored.has(w.name)) continue;
  const execs = byWorkflow[w.id] || [];
  const errors = execs.filter(e => e.status === 'error' || e.status === 'crashed');
  let latest = 0;
  for (const e of execs) {
    const t = new Date(e.startedAt).getTime();
    if (!Number.isNaN(t) && t > latest) latest = t;
  }

  if (errors.length >= spikeAt) {
    issues.push({
      workflow_name: w.name, workflow_id: w.id,
      issue_type: 'ERROR_SPIKE', severity: 'CRITICAL',
      detail: errors.length + ' failed executions in the last ' + cfg.check_window_hours + 'h',
      last_error_at: errors.map(e => e.startedAt).sort().pop() || null,
    });
  } else if (errors.length > 0) {
    issues.push({
      workflow_name: w.name, workflow_id: w.id,
      issue_type: 'ERRORS', severity: 'WARNING',
      detail: errors.length + ' failed execution(s) in the last ' + cfg.check_window_hours + 'h',
      last_error_at: errors.map(e => e.startedAt).sort().pop() || null,
    });
  }

  if (!latest || now - latest > staleMs) {
    issues.push({
      workflow_name: w.name, workflow_id: w.id,
      issue_type: 'STALE', severity: 'WARNING',
      detail: latest
        ? 'no executions in the last ' + cfg.stale_hours + 'h (last ran ' + new Date(latest).toISOString() + ')'
        : 'no executions found in the sampled window at all',
      last_error_at: null,
    });
  }
}

return [{ json: { issues, issues_count: issues.length } }];
"""
nodes.append(node("Analyze Health", "n8n-nodes-base.code", 2,
    {"jsCode": analyze_js}, X, Y))
X += STEP

# 6. IF — any issues?
nodes.append(node("Any Issues?", "n8n-nodes-base.if", 2.2,
    {"conditions": {"combinator": "and", "conditions": [{
        "id": nid(),
        "leftValue": "={{ $json.issues_count }}",
        "operator": {"name": "filter.operator.number.larger",
                     "operation": "larger", "type": "number"},
        "rightValue": 0}],
        "options": {"caseSensitive": True, "leftValue": "",
                    "typeValidation": "loose"}},
     "looseTypeValidation": True, "options": {}},
    X, Y))
X += STEP

# 7. Expand Issues
expand_js = """const data = $input.first().json;
return (data.issues || []).map(i => ({ json: i }));
"""
nodes.append(node("Expand Issues", "n8n-nodes-base.code", 2,
    {"jsCode": expand_js}, X, Y))
X += STEP

# 8. Format Alert
nodes.append(node("Format Alert", "n8n-nodes-base.set", 3.4,
    {"assignments": {"assignments": [{
        "id": "f-1", "name": "alert_text", "type": "string",
        "value": ("={{ ($json.severity === 'CRITICAL' ? '\U0001F6A8 CRITICAL' : '⚠️ WARNING') }}"
                  " + ' [' + $json.issue_type + '] ' + $json.workflow_name + '\\n' + $json.detail"
                  " + ($json.last_error_at ? '\\nLast error: ' + $json.last_error_at : '')")}]},
     "includeOtherFields": True, "options": {}},
    X, Y))
X += STEP

# 9. Telegram alert
nodes.append(node("Telegram \u2014 Health Alert", "n8n-nodes-base.telegram", 1.2,
    {"additionalFields": {},
     "chatId": "={{ $('CONFIG \u2014 Watchdog').first().json.telegram_chat_id }}",
     "text": "={{ $json.alert_text }}"},
    X, Y))
X += STEP

# 10. Log Issues
nodes.append(node("Log Issues", "n8n-nodes-base.googleSheets", 4.2,
    {"columns": {"mappingMode": "defineBelow", "matchingColumns": [],
                 "schema": [],
                 "value": {
                     "time": "={{ $now.toISO() }}",
                     "workflow_name": "={{ $json.workflow_name }}",
                     "issue_type": "={{ $json.issue_type }}",
                     "severity": "={{ $json.severity }}",
                     "detail": "={{ $json.detail }}"}},
     "documentId": {"__rl": True, "cachedResultName": "n8n Watchdog",
                    "mode": "list", "value": ""},
     "operation": "append",
     "options": {},
     "resource": "sheetWithinDocument",
     "sheetName": {"__rl": True, "cachedResultName": "watchdog_log",
                   "mode": "list", "value": ""}},
    X, Y))

connections = {
    "Hourly Check": {"main": [[{"node": "CONFIG \u2014 Watchdog", "type": "main", "index": 0}]]},
    "CONFIG \u2014 Watchdog": {"main": [[{"node": "Get Active Workflows", "type": "main", "index": 0}]]},
    "Get Active Workflows": {"main": [[{"node": "Get Recent Executions", "type": "main", "index": 0}]]},
    "Get Recent Executions": {"main": [[{"node": "Analyze Health", "type": "main", "index": 0}]]},
    "Analyze Health": {"main": [[{"node": "Any Issues?", "type": "main", "index": 0}]]},
    "Any Issues?": {"main": [[{"node": "Expand Issues", "type": "main", "index": 0}], []]},
    "Expand Issues": {"main": [[{"node": "Format Alert", "type": "main", "index": 0}]]},
    "Format Alert": {"main": [[{"node": "Telegram \u2014 Health Alert", "type": "main", "index": 0}]]},
    "Telegram \u2014 Health Alert": {"main": [[{"node": "Log Issues", "type": "main", "index": 0}]]},
}

workflow = {
    "active": False,
    "connections": connections,
    "meta": {"instanceId": "", "templateCredsSetupCompleted": False},
    "name": "n8n Workflow Health Watchdog",
    "nodes": nodes,
    "pinData": {},
    "settings": {"executionOrder": "v1"},
    "tags": [],
    "versionId": "",
}

OUT.write_text(json.dumps(workflow, indent=1, ensure_ascii=False) + "\n")
print(f"Wrote {OUT} ({len(nodes)} nodes)")
