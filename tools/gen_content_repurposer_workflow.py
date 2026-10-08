#!/usr/bin/env python3
"""Generate the AI Content Repurposer n8n workflow JSON.

1 video transcript -> ~20 multi-platform posts, logged to Google Sheets,
completion digest on Telegram.
"""
import json
import uuid


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


def sheets_append(name, value_map, sheet_name, x, y):
    return {
        "parameters": {
            "operation": "append",
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": sheet_name},
            "columns": {
                "mappingMode": "defineBelow", "matchingColumns": [], "schema": [],
                "attemptToConvertTypes": False, "convertFieldsToString": False,
                "value": value_map,
            },
            "options": {},
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }


def telegram_node(name, chat_id_expr, text_expr, x, y):
    return {
        "parameters": {
            "chatId": chat_id_expr,
            "text": text_expr,
            "additionalFields": {"parse_mode": "Markdown"},
        },
        "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2, "position": [x, y],
    }


SHEET = "Content_Repurposing_Log"
CFG = "CONFIG — Content Source"
CHAT = "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}"

nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY — Title",
    "## 🎯 AI CONTENT REPURPOSER\n"
    "**What it does:** Paste one video/podcast transcript → an AI agent rewrites it into 8 content formats "
    "(X thread, LinkedIn post, Facebook post, Instagram caption, newsletter section, quote cards, Shorts/Reels scripts, blog summary — ~20 pieces) "
    "→ every piece logged to Google Sheets → Telegram completion summary.\n\n"
    "**You'll need:**\n- OpenAI API key (platform.openai.com)\n- Google Sheets OAuth2 credential\n- Telegram bot token + your chat ID (@BotFather → /newbot)\n\n"
    "**Status flow in Sheets:** `NEW` → `PROCESSING` → `DONE`",
    -260, -160, 4300, 220, color=5))

nodes.append(sticky("STICKY — STEP 1",
    "## STEP 1 — Trigger + paste your transcript\n"
    "Manual Trigger → `CONFIG — Content Source`: paste the transcript into `transcript_text`, set `source_title`, `brand_voice`, `target_audience`, `platforms_to_generate`. `CONFIG — Notifications` holds your Telegram chat ID.",
    -260, 180, 1020, 420))

nodes.append(sticky("STICKY — STEP 2",
    "## STEP 2 — Validate + log source\n"
    "`Sheets — Log Source NEW` appends the transcript (status `NEW`) → `IF — Transcript Not Empty` checks you actually pasted something. Empty transcript → `Telegram — Empty Transcript Error` tells you to fix the config.",
    700, 180, 780, 420))

nodes.append(sticky("STICKY — STEP 3",
    "## STEP 3 — AI repurposes the content\n"
    "Status flips to `PROCESSING` → `AI Agent — Repurpose Content` (gpt-4o-mini + `Structured Output Parser — Content Plan`) returns x_thread, linkedin_post, facebook_post, instagram_caption, newsletter_section, quote_cards, shorts_scripts, blog_summary — written in your `brand_voice`, for your `target_audience`.",
    1420, 180, 560, 640))

nodes.append(sticky("STICKY — STEP 4",
    "## STEP 4 — Split + log every piece\n"
    "`Split Output Per Platform` turns the structured output into one item per post → `Sheets — Log Content Items` appends each row (status `PROCESSING`) → `Build Completion Summary` counts pieces per platform → `Sheets — Log RUN_DONE` closes the run.",
    1900, 180, 560, 420))

nodes.append(sticky("STICKY — STEP 5",
    "## STEP 5 — Completion digest\n"
    "`Telegram — Repurposing Complete` sends the per-platform counts. Copy each row's Content cell from the sheet and publish wherever you like — X, LinkedIn, Facebook, Instagram, your newsletter.",
    2480, 180, 720, 420))

# ---------- MAIN CHAIN ----------
nodes.append({
    "parameters": {},
    "id": uid(), "name": "On Manual Trigger", "type": "n8n-nodes-base.manualTrigger",
    "typeVersion": 1, "position": [0, 300],
})

nodes.append(set_node(CFG, [
    ("source_title", "My latest video title"),
    ("transcript_text", "PASTE_YOUR_TRANSCRIPT_HERE"),
    ("brand_voice", "practical, no-fluff, contrarian"),
    ("target_audience", "solopreneurs and creators growing with AI automation"),
    ("platforms_to_generate", "x_thread, linkedin_post, facebook_post, instagram_caption, newsletter_section, quote_cards, shorts_scripts, blog_summary"),
], 240, 300))

nodes.append(set_node("CONFIG — Notifications", [
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 480, 300))

nodes.append(sheets_append("Sheets — Log Source NEW", {
    "Timestamp": "={{ $now.toISO() }}",
    "Source Title": "={{ $json.source_title }}",
    "Content Type": "source_transcript",
    "Content": "={{ $json.transcript_text.slice(0, 500) }}",
    "Status": "NEW",
    "Notes": "run started",
}, SHEET, 720, 300))

nodes.append({
    "parameters": {
        "conditions": {
            "combinator": "and",
            "conditions": [{
                "id": "if-transcript",
                "leftValue": "={{ $json.transcript_text }}",
                "rightValue": "",
                "operator": {"type": "string", "operation": "notEmpty", "name": "filter.operator.string.notEmpty"},
            }],
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        },
        "options": {},
    },
    "id": uid(), "name": "IF — Transcript Not Empty", "type": "n8n-nodes-base.if",
    "typeVersion": 2.2, "position": [960, 300],
})

nodes.append(telegram_node("Telegram — Empty Transcript Error", CHAT,
    "=⚠️ *Transcript is empty*\n\nOpen `CONFIG — Content Source`, paste your transcript into `transcript_text`, and run the workflow again.",
    960, 560))

nodes.append(sheets_append("Sheets — Status PROCESSING", {
    "Timestamp": "={{ $now.toISO() }}",
    "Source Title": "={{ $('CONFIG — Content Source').first().json.source_title }}",
    "Content Type": "run_status",
    "Content": "Repurposing started",
    "Status": "PROCESSING",
    "Notes": "",
}, SHEET, 1200, 300))

nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are an expert content repurposing strategist who turns one long-form transcript into platform-native content.\n\nVoice: {{ $('CONFIG — Content Source').first().json.brand_voice }}\nTarget audience: {{ $('CONFIG — Content Source').first().json.target_audience }}\nGenerate ALL of these formats: {{ $('CONFIG — Content Source').first().json.platforms_to_generate }}\n\nRules:\n- X thread: 5-8 punchy tweets, first one a scroll-stopping hook, each under 280 characters.\n- LinkedIn post: hook + personal story + 3 takeaways + CTA. Minimal hashtags.\n- Facebook post: conversational, ends with a question to drive comments.\n- Instagram caption: short lines, 5-8 relevant hashtags.\n- Newsletter section: headline + 3 short paragraphs.\n- Quote cards: 4-6 standalone quotable one-liners.\n- Shorts/Reels scripts: 3 scripts, each = 3-second hook + 3 beats + CTA, under 60 seconds spoken.\n- Blog summary: ~150 words.\nNever invent facts not present in the transcript. Output ONLY via the structured output parser.",
            "text": "=Source title: {{ $('CONFIG — Content Source').first().json.source_title }}\n\nTRANSCRIPT:\n{{ $('CONFIG — Content Source').first().json.transcript_text }}",
        },
    },
    "id": uid(), "name": "AI Agent — Repurpose Content", "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7, "position": [1440, 300],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model — Repurposer", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.2, "position": [1440, 560],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n  \"x_thread\": [\"Hook tweet (under 280 chars)\", \"Tweet 2\", \"Tweet 3\", \"Tweet 4\", \"Tweet 5\"],\n  \"linkedin_post\": \"Professional LinkedIn post: hook + story + 3 takeaways + CTA\",\n  \"facebook_post\": \"Conversational Facebook post ending with a question\",\n  \"instagram_caption\": \"Instagram caption with short lines and 5-8 hashtags\",\n  \"newsletter_section\": \"Newsletter section: headline + 3 short paragraphs\",\n  \"quote_cards\": [\"Standalone quotable one-liner 1\", \"Standalone quotable one-liner 2\", \"Standalone quotable one-liner 3\"],\n  \"shorts_scripts\": [\"Shorts script 1: 3-second hook + 3 beats + CTA\", \"Shorts script 2: 3-second hook + 3 beats + CTA\"],\n  \"blog_summary\": \"~150 word blog-style summary of the video\"\n}",
    },
    "id": uid(), "name": "Structured Output Parser — Content Plan", "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.2, "position": [1680, 560],
})

nodes.append(code_node("Split Output Per Platform", """// Split the agent's structured output into one item per content piece
const out = $('AI Agent — Repurpose Content').first().json.output || {};
const cfg = $('CONFIG — Content Source').first().json;
const ts = new Date().toISOString();
const title = cfg.source_title || 'Untitled';

const items = [];
const push = (content_type, content) => {
  if (!content) return;
  items.push({ json: {
    timestamp: ts,
    source_title: title,
    content_type,
    content: String(content),
    status: 'PROCESSING',
    notes: '',
  }});
};

const arr = (v) => Array.isArray(v) ? v : [];
arr(out.x_thread).forEach(t => push('x_tweet', t));
push('linkedin_post', out.linkedin_post);
push('facebook_post', out.facebook_post);
push('instagram_caption', out.instagram_caption);
push('newsletter_section', out.newsletter_section);
arr(out.quote_cards).forEach(q => push('quote_card', q));
arr(out.shorts_scripts).forEach(s => push('shorts_script', s));
push('blog_summary', out.blog_summary);

return items;""", 1680, 300))

nodes.append(sheets_append("Sheets — Log Content Items", {
    "Timestamp": "={{ $json.timestamp }}",
    "Source Title": "={{ $json.source_title }}",
    "Content Type": "={{ $json.content_type }}",
    "Content": "={{ $json.content }}",
    "Status": "={{ $json.status }}",
    "Notes": "={{ $json.notes }}",
}, SHEET, 1920, 300))

nodes.append(code_node("Build Completion Summary", """// Count generated items per platform and build the Telegram summary
const items = $input.all().map(i => i.json);
const cfg = $('CONFIG — Content Source').first().json;
const title = cfg.source_title || 'Untitled';

const count = (t) => items.filter(i => i.content_type === t).length;
const rows = [
  ['X thread tweets', count('x_tweet')],
  ['LinkedIn post', count('linkedin_post')],
  ['Facebook post', count('facebook_post')],
  ['Instagram caption', count('instagram_caption')],
  ['Newsletter section', count('newsletter_section')],
  ['Quote cards', count('quote_card')],
  ['Shorts/Reels scripts', count('shorts_script')],
  ['Blog summary', count('blog_summary')],
];
const total = rows.reduce((a, r) => a + r[1], 0);

const lines = [
  '✅ *Content repurposing complete*',
  '',
  '🎬 *' + title + '*',
  '',
  '📦 ' + total + ' pieces generated:'
];
rows.forEach(r => lines.push('• ' + r[0] + ': ' + r[1]));
lines.push('', '📊 All items logged to Google Sheets (NEW → PROCESSING → DONE).');

return [{ json: { summary: lines.join('\\n'), total, title } }];""", 2160, 300))

nodes.append(sheets_append("Sheets — Log RUN_DONE", {
    "Timestamp": "={{ $now.toISO() }}",
    "Source Title": "={{ $json.title }}",
    "Content Type": "run_summary",
    "Content": "={{ $json.total }} pieces generated",
    "Status": "DONE",
    "Notes": "={{ $json.summary }}",
}, SHEET, 2400, 300))

nodes.append(telegram_node("Telegram — Repurposing Complete", CHAT,
    "={{ $json.summary }}", 2640, 300))

connections = {
    "On Manual Trigger": {"main": [[{"node": CFG, "type": "main", "index": 0}]]},
    CFG: {"main": [[{"node": "CONFIG — Notifications", "type": "main", "index": 0}]]},
    "CONFIG — Notifications": {"main": [[{"node": "Sheets — Log Source NEW", "type": "main", "index": 0}]]},
    "Sheets — Log Source NEW": {"main": [[{"node": "IF — Transcript Not Empty", "type": "main", "index": 0}]]},
    "IF — Transcript Not Empty": {"main": [
        [{"node": "Sheets — Status PROCESSING", "type": "main", "index": 0}],
        [{"node": "Telegram — Empty Transcript Error", "type": "main", "index": 1}],
    ]},
    "Sheets — Status PROCESSING": {"main": [[{"node": "AI Agent — Repurpose Content", "type": "main", "index": 0}]]},
    "AI Agent — Repurpose Content": {"main": [[{"node": "Split Output Per Platform", "type": "main", "index": 0}]]},
    "Split Output Per Platform": {"main": [[{"node": "Sheets — Log Content Items", "type": "main", "index": 0}]]},
    "Sheets — Log Content Items": {"main": [[{"node": "Build Completion Summary", "type": "main", "index": 0}]]},
    "Build Completion Summary": {"main": [[{"node": "Sheets — Log RUN_DONE", "type": "main", "index": 0}]]},
    "Sheets — Log RUN_DONE": {"main": [[{"node": "Telegram — Repurposing Complete", "type": "main", "index": 0}]]},
    "OpenAI Chat Model — Repurposer": {"ai_languageModel": [[{"node": "AI Agent — Repurpose Content", "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser — Content Plan": {"ai_outputParser": [[{"node": "AI Agent — Repurpose Content", "type": "ai_outputParser", "index": 0}]]},
}

wf = {
    "name": "AI Content Repurposer",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/ai-content-repurposer.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
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
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook", "ghp_", "AIza"]:
    assert bad not in blob, f"possible hardcoded secret: {bad}"
types = {n["type"] for n in d["nodes"]}
for req in ["n8n-nodes-base.stickyNote", "n8n-nodes-base.set", "@n8n/n8n-nodes-langchain.agent",
            "n8n-nodes-base.googleSheets", "n8n-nodes-base.telegram", "n8n-nodes-base.code",
            "n8n-nodes-base.if"]:
    assert req in types, f"missing node type {req}"
ai_conns = d["connections"]
assert "ai_languageModel" in ai_conns["OpenAI Chat Model — Repurposer"]
assert "ai_outputParser" in ai_conns["Structured Output Parser — Content Plan"]
print("validation OK: all", len(names), "nodes connected, sub-node connections present, no hardcoded secrets")
