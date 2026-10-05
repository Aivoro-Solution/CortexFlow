#!/usr/bin/env python3
"""Generate public/templates/kpi-anomaly-watchdog.json — KPI Anomaly Watchdog n8n workflow.

Daily z-score anomaly detection over KPI history in Google Sheets, AI-written
explanations via the n8n AI Agent node, Telegram alerts, and an anomaly log.
Mirrors the node shapes/typeVersions of the existing published templates.
"""
import json
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "public" / "templates" / "kpi-anomaly-watchdog.json"

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
STEP = 230
Y = 300

nodes = []

# 1. Sticky note
nodes.append({
    "id": nid(),
    "name": "Sticky Note",
    "parameters": {
        "content": "## KPI Anomaly Watchdog\n\nReads daily KPI values from the `metrics_history` sheet (columns: `date`, `metric`, `value`), scores today's value against a trailing 14-day baseline with a z-score, and asks an AI agent to explain anything unusual in plain English.\n\n**Thresholds live in CONFIG — Watchdog.** Start strict (z_warn 2.0 / z_crit 3.0) and loosen only after a week of clean runs — alert fatigue kills monitoring faster than missed anomalies.\n\nGuards: needs >= 7 baseline points, ignores flat baselines (std = 0), and skips moves smaller than 10% relative change so tiny wiggles on big numbers don't page you.",
        "height": 560,
        "width": 420,
        "color": 4,
    },
    "position": [X - 260, Y - 120],
    "type": "n8n-nodes-base.stickyNote",
    "typeVersion": 1,
})

# 2. Schedule trigger — every 24h
nodes.append(node("Daily Check", "n8n-nodes-base.scheduleTrigger", 1.2,
    {"rule": {"interval": [{"field": "hours", "hoursInterval": 24}]}},
    X, Y))
X += STEP

# 3. CONFIG
nodes.append(node("CONFIG \u2014 Watchdog", "n8n-nodes-base.set", 3.4,
    {"assignments": {"assignments": [
        {"id": "c-1", "name": "metrics", "type": "array",
         "value": "[\"daily_revenue\", \"new_signups\", \"churn_rate_pct\"]"},
        {"id": "c-2", "name": "z_warn", "type": "number", "value": 2},
        {"id": "c-3", "name": "z_crit", "type": "number", "value": 3},
        {"id": "c-4", "name": "min_samples", "type": "number", "value": 7},
        {"id": "c-5", "name": "min_rel_change_pct", "type": "number", "value": 10},
        {"id": "c-6", "name": "baseline_days", "type": "number", "value": 14},
        {"id": "c-7", "name": "telegram_chat_id", "type": "string",
         "value": "PASTE_YOUR_TELEGRAM_CHAT_ID"},
    ]}, "includeOtherFields": False, "options": {}},
    X, Y))
X += STEP

# 4. Read metric history
nodes.append(node("Read Metric History", "n8n-nodes-base.googleSheets", 4.2,
    {"documentId": {"__rl": True, "cachedResultName": "KPI Watchdog",
                    "mode": "list", "value": ""},
     "operation": "read",
     "options": {},
     "resource": "sheetWithinDocument",
     "sheetName": {"__rl": True, "cachedResultName": "metrics_history",
                   "mode": "list", "value": ""}},
    X, Y))
X += STEP

# 5. Detect Anomalies (Code)
detect_js = """// Z-score anomaly detection over a trailing baseline.
// Expects items: { date, metric, value }. Emits one item:
// { anomalies: [...], anomalies_count: N }
const cfg = $('CONFIG \\u2014 Watchdog').first().json;
const Z_WARN = Number(cfg.z_warn);
const Z_CRIT = Number(cfg.z_crit);
const MIN_SAMPLES = Number(cfg.min_samples);
const MIN_REL = Number(cfg.min_rel_change_pct) / 100;
const BASELINE_DAYS = Number(cfg.baseline_days);

const rows = $input.all()
  .map(i => i.json)
  .filter(r => r.metric && r.date && r.value !== undefined && r.value !== '' && r.value !== null)
  .map(r => ({ metric: String(r.metric).trim(), date: String(r.date).slice(0, 10), value: Number(r.value) }))
  .filter(r => !Number.isNaN(r.value));

const byMetric = {};
for (const r of rows) (byMetric[r.metric] = byMetric[r.metric] || []).push(r);

const anomalies = [];
for (const [metric, pts] of Object.entries(byMetric)) {
  pts.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  if (pts.length < MIN_SAMPLES + 1) continue; // need history + today
  const latest = pts[pts.length - 1];
  const baseline = pts.slice(Math.max(0, pts.length - 1 - BASELINE_DAYS), pts.length - 1);
  if (baseline.length < MIN_SAMPLES) continue;
  const mean = baseline.reduce((s, p) => s + p.value, 0) / baseline.length;
  const variance = baseline.reduce((s, p) => s + Math.pow(p.value - mean, 2), 0) / baseline.length;
  const std = Math.sqrt(variance);
  if (std === 0) continue; // flat baseline: z-score is meaningless
  const z = (latest.value - mean) / std;
  const rel = mean !== 0 ? Math.abs(latest.value - mean) / Math.abs(mean) : 1;
  if (Math.abs(z) >= Z_WARN && rel >= MIN_REL) {
    anomalies.push({
      metric,
      date: latest.date,
      latest_value: latest.value,
      baseline_mean: Math.round(mean * 100) / 100,
      baseline_std: Math.round(std * 100) / 100,
      z_score: Math.round(z * 100) / 100,
      rel_change_pct: Math.round(rel * 1000) / 10,
      direction: z > 0 ? 'UP' : 'DOWN',
      severity: Math.abs(z) >= Z_CRIT ? 'CRITICAL' : 'WARNING',
      baseline_points: baseline.length,
    });
  }
}

return [{ json: { anomalies, anomalies_count: anomalies.length } }];
"""
nodes.append(node("Detect Anomalies", "n8n-nodes-base.code", 2,
    {"jsCode": detect_js}, X, Y))
X += STEP

# 6. IF — any anomalies?
nodes.append(node("Any Anomalies?", "n8n-nodes-base.if", 2.2,
    {"conditions": {"combinator": "and", "conditions": [{
        "id": nid(),
        "leftValue": "={{ $json.anomalies_count }}",
        "operator": {"name": "filter.operator.number.larger",
                     "operation": "larger", "type": "number"},
        "rightValue": 0}],
        "options": {"caseSensitive": True, "leftValue": "",
                    "typeValidation": "loose"}},
     "looseTypeValidation": True, "options": {}},
    X, Y))
X += STEP

# 7. Expand Anomalies (Code) — one item per anomaly
expand_js = """// Split the anomalies array into one item per anomaly
// so the AI agent + alert run once each.
const data = $input.first().json;
return (data.anomalies || []).map(a => ({ json: a }));
"""
nodes.append(node("Expand Anomalies", "n8n-nodes-base.code", 2,
    {"jsCode": expand_js}, X, Y))
X += STEP

# 8. AI Agent — Explain Anomaly
agent_name = "AI Agent \u2014 Explain Anomaly"
nodes.append(node(agent_name, "@n8n/n8n-nodes-langchain.agent", 1.7,
    {"options": {"systemMessage": "=You are a senior business analyst. Explain KPI anomalies in plain English for a non-technical founder. Be concrete: name the metric, the size of the move, and what usually causes moves like this. Never invent data you were not given. Output ONLY via the structured output parser."},
     "text": "=Metric: {{ $json.metric }}\\nDate: {{ $json.date }}\\nLatest value: {{ $json.latest_value }} (baseline mean {{ $json.baseline_mean }}, std {{ $json.baseline_std }} over {{ $json.baseline_points }} days)\\nZ-score: {{ $json.z_score }} ({{ $json.direction }}, {{ $json.rel_change_pct }}% move)\\nSeverity: {{ $json.severity }}\\n\\nExplain this anomaly and suggest what to check first."},
    X, Y))
agent_x = X
X += STEP

# 9. OpenAI Chat Model (sub-node)
nodes.append(node("OpenAI Chat Model \u2014 Explainer",
    "@n8n/n8n-nodes-langchain.lmChatOpenAi", 1.2,
    {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"},
     "options": {}},
    agent_x - 60, Y + 220))

# 10. Structured Output Parser (sub-node)
schema = {
    "explanation": "2-3 sentence plain-English explanation of what happened",
    "likely_causes": ["most likely cause", "second most likely cause"],
    "suggested_checks": ["first thing to verify", "second thing to verify"],
    "needs_human": True,
}
nodes.append(node("Structured Output Parser \u2014 Explanation",
    "@n8n/n8n-nodes-langchain.outputParserStructured", 1.2,
    {"schemaType": "manual", "inputSchema": json.dumps(schema, indent=2)},
    agent_x + 180, Y + 220))

# 11. Format Alert (Set)
nodes.append(node("Format Alert", "n8n-nodes-base.set", 3.4,
    {"assignments": {"assignments": [{
        "id": "f-1", "name": "alert_text", "type": "string",
        "value": ("={{ $json.severity === 'CRITICAL' ? '\U0001F6A8' : '⚠️' }} "
                  "KPI anomaly: {{ $json.metric }} moved {{ $json.direction }} "
                  "{{ $json.rel_change_pct }}% (z={{ $json.z_score }})\\n\\n"
                  "{{ $json.output.explanation }}\\n\\n"
                  "Likely causes: {{ $json.output.likely_causes.join('; ') }}\\n"
                  "Check first: {{ $json.output.suggested_checks.join('; ') }}")}]},
     "includeOtherFields": True, "options": {}},
    X, Y))
X += STEP

# 12. Telegram alert
nodes.append(node("Telegram \u2014 Anomaly Alert", "n8n-nodes-base.telegram", 1.2,
    {"additionalFields": {},
     "chatId": "={{ $('CONFIG \u2014 Watchdog').first().json.telegram_chat_id }}",
     "text": "={{ $json.alert_text }}"},
    X, Y))
X += STEP

# 13. Log Anomaly (Google Sheets append)
nodes.append(node("Log Anomaly", "n8n-nodes-base.googleSheets", 4.2,
    {"columns": {"mappingMode": "defineBelow", "matchingColumns": [],
                 "schema": [],
                 "value": {
                     "time": "={{ $now.toISO() }}",
                     "metric": "={{ $json.metric }}",
                     "date": "={{ $json.date }}",
                     "latest_value": "={{ $json.latest_value }}",
                     "baseline_mean": "={{ $json.baseline_mean }}",
                     "z_score": "={{ $json.z_score }}",
                     "severity": "={{ $json.severity }}",
                     "direction": "={{ $json.direction }}",
                     "ai_explanation": "={{ $json.output.explanation }}"}},
     "documentId": {"__rl": True, "cachedResultName": "KPI Watchdog",
                    "mode": "list", "value": ""},
     "operation": "append",
     "options": {},
     "resource": "sheetWithinDocument",
     "sheetName": {"__rl": True, "cachedResultName": "anomaly_log",
                   "mode": "list", "value": ""}},
    X, Y))

names = [n["name"] for n in nodes]
by_name = {n["name"]: n["name"] for n in nodes}

def link(src, dst, out_index=0):
    return {"node": dst, "type": "main", "index": out_index}

connections = {
    "Daily Check": {"main": [[link("Daily Check", "CONFIG \u2014 Watchdog")]]},
    "CONFIG \u2014 Watchdog": {"main": [[link("CONFIG \u2014 Watchdog", "Read Metric History")]]},
    "Read Metric History": {"main": [[link("Read Metric History", "Detect Anomalies")]]},
    "Detect Anomalies": {"main": [[link("Detect Anomalies", "Any Anomalies?")]]},
    "Any Anomalies?": {"main": [[link("Any Anomalies?", "Expand Anomalies")], []]},
    "Expand Anomalies": {"main": [[link("Expand Anomalies", agent_name)]]},
    agent_name: {"main": [[link(agent_name, "Format Alert")]]},
    "Format Alert": {"main": [[link("Format Alert", "Telegram \u2014 Anomaly Alert")]]},
    "Telegram \u2014 Anomaly Alert": {"main": [[link("Telegram \u2014 Anomaly Alert", "Log Anomaly")]]},
    "OpenAI Chat Model \u2014 Explainer": {
        "ai_languageModel": [[{"node": agent_name, "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser \u2014 Explanation": {
        "ai_outputParser": [[{"node": agent_name, "type": "ai_outputParser", "index": 0}]]},
}

workflow = {
    "active": False,
    "connections": connections,
    "meta": {"instanceId": "", "templateCredsSetupCompleted": False},
    "name": "KPI Anomaly Watchdog",
    "nodes": nodes,
    "pinData": {},
    "settings": {"executionOrder": "v1"},
    "tags": [],
    "versionId": "",
}

OUT.write_text(json.dumps(workflow, indent=1, ensure_ascii=False) + "\n")
print(f"Wrote {OUT} ({len(nodes)} nodes)")
