#!/usr/bin/env python3
"""Generate the Reddit RSS Migration Monitor n8n workflow JSON.

Migration kit for Reddit's RSS shutdown (Nov 13, 2026) / public API end (Mar 2027):
paste old .rss URLs -> parse subreddits/queries -> fetch via swappable JSON source
-> dedupe by post ID in Google Sheets -> AI relevance scoring -> Telegram digest
with a heartbeat note on empty runs.
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

def sheets_append(name, sheet, value_map, x, y):
    return {
        "parameters": {
            "operation": "append",
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": sheet},
            "options": {},
            "columns": {
                "mappingMode": "defineBelow",
                "matchingColumns": [],
                "schema": [],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
                "value": value_map,
            },
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

def sheets_update(name, sheet, match_cols, value_map, x, y):
    return {
        "parameters": {
            "operation": "update",
            "resource": "sheetWithinDocument",
            "documentId": {"__rl": True, "mode": "list", "value": ""},
            "sheetName": {"__rl": True, "mode": "list", "value": sheet},
            "options": {},
            "columns": {
                "mappingMode": "defineBelow",
                "matchingColumns": match_cols,
                "schema": [],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
                "value": value_map,
            },
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

def http_node(name, url_expr, x, y, query_params, custom=False):
    params = {
        "method": "GET",
        "url": url_expr,
        "sendQuery": True,
        "queryParameters": {"parameters": query_params},
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "User-Agent", "value": "n8n-cortexflow-template/1.0"},
        ]},
        "options": {},
    }
    return {
        "parameters": params,
        "id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2, "position": [x, y],
    }

def if_node(name, conditions, x, y):
    return {
        "parameters": {"conditions": conditions, "options": {}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.if",
        "typeVersion": 2.2, "position": [x, y],
    }

nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY — Title",
    "## 📡 REDDIT RSS MIGRATION MONITOR\n"
    "**What it does:** Reddit kills RSS feeds on Nov 13, 2026 (public API ends Mar 2027). Paste your OLD `.rss` URLs → this workflow parses the subreddits + queries out of them → fetches posts through a swappable JSON source (Reddit public `.json` today, your Apify actor / JSON proxy for after Mar 2027) → dedupes by post ID against Google Sheets → AI relevance-scores each post → Telegram digest with a heartbeat note when nothing qualifies.\n\n"
    "**You'll need:**\n- Your old Reddit `.rss` feed URLs (find them before Nov 13)\n- OpenAI API key (platform.openai.com)\n- Google Sheets OAuth2 credential\n- Telegram bot token + your chat ID (@BotFather → /newbot)\n- (Only needed after Mar 2027) an Apify actor endpoint or any JSON proxy URL\n\n"
    "**Status flow in Sheets:** `NEW` → `SCORED` → `SENT` (+ `IGNORED` for below-threshold posts)",
    -240, -160, 5480, 220, color=5))

nodes.append(sticky("STICKY — STEP 1",
    "## STEP 1 — Paste old RSS feeds\nCONFIG — RSS Migration holds your old `.rss` URLs, the swappable source setting, and filters. Parse Old RSS Feed URLs extracts the subreddit + search query from each `.rss` URL and maps old RSS fields (title / link / pubDate) to Reddit JSON fields (title / permalink / created_utc).",
    -240, 180, 1160, 420))

nodes.append(sticky("STICKY — STEP 2",
    "## STEP 2 — Fetch via swappable source\nIF — JSON Source Selector routes on `json_source`. `reddit_public` → Fetch Reddit — Public JSON (polite User-Agent, no key). `custom` → Fetch Reddit — Custom JSON Source (your Apify actor or JSON proxy, ready for the Mar 2027 shutdown).",
    1140, 180, 1120, 420))

nodes.append(sticky("STICKY — STEP 3",
    "## STEP 3 — Normalize, dedupe, log\nNormalize Reddit Posts — RSS Field Map flattens results and applies your keyword/upvote/recency filters → Read Logged Post IDs → Filter New Posts Only drops already-seen post IDs → Log Posts — Status NEW.",
    2280, 180, 1080, 420))

nodes.append(sticky("STICKY — STEP 4",
    "## STEP 4 — AI relevance scoring\nAI Agent — Score Relevance reads each post against your `business_description` with a Structured Output Parser (relevance_score 0–100, verdict, why_relevant, suggested_action) → Update Sheet — Status SCORED.",
    3380, 180, 1000, 420))

nodes.append(sticky("STICKY — STEP 5",
    "## STEP 5 — Relevance gate\nIF — Relevance ≥ Threshold sends qualifying posts to Merge — Collect Alert Posts; below-threshold posts go to Update Sheet — Status IGNORED first, then join the merge.",
    4400, 180, 980, 420))

nodes.append(sticky("STICKY — STEP 6",
    "## STEP 6 — Digest + heartbeat\nBuild Migration Digest builds one Telegram digest (top posts sorted by score). Empty runs send a 💓 heartbeat so you notice if the source ever breaks silently → Telegram — Send Digest → Expand Sent URLs → Update Sheet — Status SENT.",
    5400, 180, 1060, 420))

# ---------- MAIN CHAIN ----------
nodes.append({
    "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 24, "triggerAtHour": 9, "triggerAtMinute": 0}]}},
    "id": uid(), "name": "Daily 9AM Trigger", "type": "n8n-nodes-base.scheduleTrigger",
    "typeVersion": 1.2, "position": [0, 300],
})

nodes.append(set_node("CONFIG — RSS Migration", [
    ("old_rss_feeds",
     "https://www.reddit.com/r/n8n/new.rss\nhttps://www.reddit.com/r/selfhosted/search.rss?q=automation+workflow&restrict_sr=on&sort=new&t=week"),
    ("json_source", "reddit_public"),
    ("custom_json_url", "PASTE_YOUR_JSON_PROXY_OR_APIFY_ENDPOINT (only used when json_source = custom; must return Reddit-shaped JSON: data.children[].data)"),
    ("min_upvotes", "5"),
    ("min_relevance_score", "60"),
    ("watch_keywords", "automation,workflow,n8n"),
    ("business_description", "PASTE_YOUR_BUSINESS_DESCRIPTION (what you sell or monitor for — the AI scores each post's relevance to this)"),
    ("days_back", "7"),
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 240, 300))

nodes.append(code_node("Parse Old RSS Feed URLs", """// Parse old Reddit .rss URLs into fetchable subreddit/query specs.
// RSS -> JSON field map (used later):
//   <title>     -> p.title
//   <link>      -> 'https://www.reddit.com' + p.permalink
//   <pubDate>   -> new Date(p.created_utc * 1000).toISOString()
//   <dc:creator>-> p.author
//   <guid>      -> p.id  (used for dedupe)
const cfg = $('CONFIG — RSS Migration').first().json;
const source = (cfg.json_source || 'reddit_public').trim();
if (source === 'custom' && (cfg.custom_json_url || '').includes('PASTE_YOUR')) {
  throw new Error('CONFIG — RSS Migration: json_source is "custom" but custom_json_url still has the PASTE_YOUR placeholder.');
}
const feeds = (cfg.old_rss_feeds || '').split('\\n').map(s => s.trim()).filter(Boolean);
const days = parseInt(cfg.days_back || '7', 10);
const t = days <= 1 ? 'day' : days <= 7 ? 'week' : days <= 30 ? 'month' : 'year';
const specs = [];
for (const raw of feeds) {
  let u;
  try { u = new URL(raw); } catch (e) { throw new Error('Could not parse RSS URL: ' + raw); }
  const path = u.pathname.replace(/\\.rss$/, '');
  const q = u.searchParams.get('q') || '';
  const m = path.match(/^\\/r\\/([^/]+)(?:\\/(new|hot|top|rising|search))?$/);
  let endpoint, subreddit = '', query = q, sort = 'new', restrict = '';
  if (path === '/search') {
    endpoint = 'https://www.reddit.com/search.json';  // all-Reddit search
  } else if (m) {
    subreddit = m[1];
    const listing = m[2] || 'new';
    if (listing === 'search') {
      endpoint = 'https://www.reddit.com/r/' + subreddit + '/search.json';
      restrict = '1';
    } else {
      endpoint = 'https://www.reddit.com/r/' + subreddit + '/' + listing + '.json';
      sort = listing;
      query = '';  // listing feeds have no query; ignore any q param
    }
  } else {
    throw new Error('RSS URL not recognized (expected /r/<sub>/[new|hot|top|search].rss or /search.rss): ' + raw);
  }
  specs.push({ json: {
    subreddit, query, sort, restrict_sr: restrict,
    t_window: t, days_back: days,
    endpoint_url: endpoint, source_label: raw,
  }});
}
if (!specs.length) throw new Error('CONFIG — RSS Migration: paste at least one old .rss URL into old_rss_feeds.');
return specs;""", 480, 300))

nodes.append(if_node("IF — JSON Source Selector", {
    "combinator": "and",
    "conditions": [{
        "id": "if-source",
        "leftValue": "={{ $('CONFIG — RSS Migration').first().json.json_source }}",
        "rightValue": "reddit_public",
        "operator": {"type": "string", "operation": "equals", "name": "filter.operator.string.equals"},
    }],
    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
}, 720, 300))

nodes.append(http_node("Fetch Reddit — Public JSON", "={{ $json.endpoint_url }}", 960, 140, [
    {"name": "q", "value": "={{ $json.query }}"},
    {"name": "restrict_sr", "value": "={{ $json.restrict_sr }}"},
    {"name": "sort", "value": "new"},
    {"name": "t", "value": "={{ $json.t_window }}"},
    {"name": "limit", "value": "25"},
]))

nodes.append(http_node("Fetch Reddit — Custom JSON Source", "={{ $('CONFIG — RSS Migration').first().json.custom_json_url }}", 960, 460, [
    {"name": "q", "value": "={{ $json.query }}"},
    {"name": "subreddit", "value": "={{ $json.subreddit }}"},
    {"name": "sort", "value": "new"},
    {"name": "t", "value": "={{ $json.t_window }}"},
    {"name": "limit", "value": "25"},
], custom=True))

nodes.append(code_node("Normalize Reddit Posts — RSS Field Map", """// Flatten Reddit JSON and apply the RSS -> JSON field map + filters.
const cfg = $('CONFIG — RSS Migration').first().json;
const minUp = parseInt(cfg.min_upvotes || '5', 10);
const kws = (cfg.watch_keywords || '').split(',').map(k => k.trim().toLowerCase()).filter(Boolean);
const cutoff = Date.now() - (parseInt(cfg.days_back || '7', 10) * 24 * 3600 * 1000);
const out = [];
for (const item of $input.all()) {
  const children = (((item.json || {}).data || {}).children) || [];
  for (const c of children) {
    const p = c.data || {};
    const title = p.title || '';
    const selftext = p.selftext || '';
    const text = (title + '\\n' + selftext).toLowerCase();
    const hasKw = kws.length === 0 || kws.some(k => text.includes(k));
    const upvotes = Number(p.ups != null ? p.ups : 0);
    const createdAt = p.created_utc ? new Date(p.created_utc * 1000).toISOString() : '';
    const fresh = p.created_utc ? (p.created_utc * 1000 >= cutoff) : True;
    if (!hasKw || upvotes < minUp || !fresh) continue;
    out.push({ json: {
      date_found: new Date().toISOString().slice(0, 10),
      post_id: p.id || '',
      subreddit: p.subreddit || item.json.subreddit || '',
      title: title,
      post_url: 'https://www.reddit.com' + (p.permalink || ''),
      author: p.author || '[deleted]',
      upvotes: upvotes,
      comments: Number(p.num_comments != null ? p.num_comments : 0),
      created_at: createdAt,
      selftext: selftext.slice(0, 2000),
      status: 'NEW',
    }});
  }
}
return out;""", 1200, 300))

nodes.append(set_node("CONFIG — Google Sheets", [
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("sheet_name", "RedditMonitor"),
], 1440, 300))

nodes.append(sheets_read("Read Logged Post IDs", "RedditMonitor", 1680, 300))

nodes.append(code_node("Filter New Posts Only", """// Drop posts whose post ID is already in the sheet
const seen = new Set(
  $('Read Logged Post IDs').all().map(i => (i.json['Post ID'] || i.json.post_id || '').trim()).filter(Boolean)
);
const fresh = $('Normalize Reddit Posts — RSS Field Map').all()
  .map(i => i.json)
  .filter(p => p.post_id && !seen.has(String(p.post_id).trim()));
return fresh.map(p => ({ json: p }));""", 1920, 300))

nodes.append(sheets_append("Log Posts — Status NEW", "RedditMonitor", {
    "Date": "={{ $json.date_found }}",
    "Post ID": "={{ $json.post_id }}",
    "Subreddit": "={{ $json.subreddit }}",
    "Title": "={{ $json.title }}",
    "Post URL": "={{ $json.post_url }}",
    "Author": "={{ $json.author }}",
    "Upvotes": "={{ $json.upvotes }}",
    "Comments": "={{ $json.comments }}",
    "Created At": "={{ $json.created_at }}",
    "Status": "={{ $json.status }}",
}, 2160, 300))

nodes.append(set_node("CONFIG — AI Scoring", [
    ("openai_model", "gpt-4o-mini"),
    ("min_relevance_score", "60"),
    ("business_description", "PASTE_YOUR_BUSINESS_DESCRIPTION (what you sell or monitor for — the AI prompt is built from this, so be specific)"),
], 2400, 300))

nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are a relevance analyst. Score how relevant this Reddit post is to the business/topic below.\n\nOUR BUSINESS / WATCHLIST:\n{{ $('CONFIG — AI Scoring').first().json.business_description }}\n\nScore 0-100 strictly: 90+ = directly about our topic, actionable opportunity or threat; 60-89 = genuinely relevant discussion worth reading; 30-59 = loosely adjacent, probably skippable; 0-29 = irrelevant, jokes, or memes. Category verdict: HIGHLY_RELEVANT / RELEVANT / LOW / IGNORE. why_relevant: one sentence on the connection. suggested_action: one concrete next step (read, reply angle, or 'skip'). Output ONLY via the structured output parser.",
        },
        "text": "=Subreddit: r/{{ $json.subreddit }}\nTitle: {{ $json.title }}\nUpvotes: {{ $json.upvotes }} | Comments: {{ $json.comments }}\nAuthor: u/{{ $json.author }} | Posted: {{ $json.created_at }}\nPost:\n{{ $json.selftext }}\nLink: {{ $json.post_url }}",
    },
    "id": uid(), "name": "AI Agent — Score Relevance", "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7, "position": [2640, 300],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model — Relevance Scoring", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.2, "position": [2640, 560],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n  \"relevance_score\": 0,\n  \"verdict\": \"HIGHLY_RELEVANT / RELEVANT / LOW / IGNORE\",\n  \"why_relevant\": \"one sentence on the post's connection to our watchlist\",\n  \"suggested_action\": \"one concrete next step: read, reply angle, or 'skip'\"\n}",
    },
    "id": uid(), "name": "Structured Output Parser — Relevance Score", "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.2, "position": [2900, 560],
})

nodes.append(sheets_update("Update Sheet — Status SCORED", "RedditMonitor", ["Post ID"], {
    "Post ID": "={{ $json.post_id }}",
    "Relevance Score": "={{ $json.output.relevance_score }}",
    "Verdict": "={{ $json.output.verdict }}",
    "Why Relevant": "={{ $json.output.why_relevant }}",
    "Status": "SCORED",
}, 2900, 300))

nodes.append(if_node("IF — Relevance ≥ Threshold", {
    "combinator": "and",
    "conditions": [{
        "id": "if-score",
        "leftValue": "={{ $json.output.relevance_score }}",
        "rightValue": "={{ $('CONFIG — AI Scoring').first().json.min_relevance_score }}",
        "operator": {"type": "number", "operation": "largerEqual", "name": "filter.operator.number.largerEqual"},
    }],
    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
}, 3160, 300))

nodes.append(sheets_update("Update Sheet — Status IGNORED", "RedditMonitor", ["Post ID"], {
    "Post ID": "={{ $json.post_id }}",
    "Status": "IGNORED",
}, 3420, 460))

nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge — Collect Alert Posts", "type": "n8n-nodes-base.merge",
    "typeVersion": 3, "position": [3680, 300],
})

nodes.append(code_node("Build Migration Digest", """// Build one Telegram digest; empty runs send a heartbeat so a broken source is noticed
const cfg = $('CONFIG — AI Scoring').first().json;
const threshold = parseInt(cfg.min_relevance_score || '60', 10);
const src = ($('CONFIG — RSS Migration').first().json.json_source || 'reddit_public').trim();
const items = $input.all().map(i => i.json);
const hits = items
  .filter(j => j.output && Number(j.output.relevance_score) >= threshold)
  .sort((a, b) => Number(b.output.relevance_score) - Number(a.output.relevance_score));
const date = new Date().toISOString().slice(0, 10);
let lines = ['\\U0001F4E1 *Reddit Migration Digest \\u2014 ' + date + '*', '',
  '\\U0001F50C Source: ' + src, '\\U0001F4E5 ' + items.length + ' posts checked', ''];
if (hits.length) {
  lines.push('\\u2B50 ' + hits.length + ' relevant (score \\u2265 ' + threshold + '):', '');
  for (const h of hits.slice(0, 10)) {
    lines.push('\\u2022 *' + h.output.relevance_score + '* \\u2014 [' + (h.title || '').slice(0, 90) + '](' + h.post_url + ')');
    lines.push('  r/' + h.subreddit + ' \\u2022 ' + h.output.verdict + ' \\u2022 _' + (h.output.why_relevant || '') + '_');
  }
} else {
  lines.push('\\U0001F493 Heartbeat: scan ran clean \\u2014 ' + items.length + ' posts checked, none met your bar.');
  lines.push('If this message ever stops arriving, check your JSON source (the Reddit public API ends March 2027).');
}
return [{ json: { digest: lines.join('\\n'), total: items.length, relevant: hits.length,
  alerted_urls: hits.map(h => h.post_url) } }];""", 3940, 300))

nodes.append(set_node("CONFIG — Notifications", [
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 4200, 300))

nodes.append({
    "parameters": {
        "chatId": "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}",
        "text": "={{ $json.digest }}",
        "additionalFields": {"parse_mode": "Markdown"},
    },
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": "Telegram — Send Digest", "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2, "position": [4460, 300],
})

nodes.append(code_node("Expand Sent URLs", """// Expand the digest's alert URLs back into items so the sheet can flip to SENT
const urls = $input.first().json.alerted_urls || [];
return urls.map(u => ({ json: { post_url: u } }));""", 4720, 300))

nodes.append(sheets_update("Update Sheet — Status SENT", "RedditMonitor", ["Post URL"], {
    "Post URL": "={{ $json.post_url }}",
    "Status": "SENT",
}, 4980, 300))

# ---------- CONNECTIONS ----------
connections = {
    "Daily 9AM Trigger": {"main": [[{"node": "CONFIG — RSS Migration", "type": "main", "index": 0}]]},
    "CONFIG — RSS Migration": {"main": [[{"node": "Parse Old RSS Feed URLs", "type": "main", "index": 0}]]},
    "Parse Old RSS Feed URLs": {"main": [[{"node": "IF — JSON Source Selector", "type": "main", "index": 0}]]},
    "IF — JSON Source Selector": {"main": [
        [{"node": "Fetch Reddit — Public JSON", "type": "main", "index": 0}],
        [{"node": "Fetch Reddit — Custom JSON Source", "type": "main", "index": 0}],
    ]},
    "Fetch Reddit — Public JSON": {"main": [[{"node": "Normalize Reddit Posts — RSS Field Map", "type": "main", "index": 0}]]},
    "Fetch Reddit — Custom JSON Source": {"main": [[{"node": "Normalize Reddit Posts — RSS Field Map", "type": "main", "index": 0}]]},
    "Normalize Reddit Posts — RSS Field Map": {"main": [[{"node": "CONFIG — Google Sheets", "type": "main", "index": 0}]]},
    "CONFIG — Google Sheets": {"main": [[{"node": "Read Logged Post IDs", "type": "main", "index": 0}]]},
    "Read Logged Post IDs": {"main": [[{"node": "Filter New Posts Only", "type": "main", "index": 0}]]},
    "Filter New Posts Only": {"main": [[{"node": "Log Posts — Status NEW", "type": "main", "index": 0}]]},
    "Log Posts — Status NEW": {"main": [[{"node": "CONFIG — AI Scoring", "type": "main", "index": 0}]]},
    "CONFIG — AI Scoring": {"main": [[{"node": "AI Agent — Score Relevance", "type": "main", "index": 0}]]},
    "AI Agent — Score Relevance": {"main": [[{"node": "Update Sheet — Status SCORED", "type": "main", "index": 0}]]},
    "Update Sheet — Status SCORED": {"main": [[{"node": "IF — Relevance ≥ Threshold", "type": "main", "index": 0}]]},
    "IF — Relevance ≥ Threshold": {"main": [
        [{"node": "Merge — Collect Alert Posts", "type": "main", "index": 0}],
        [{"node": "Update Sheet — Status IGNORED", "type": "main", "index": 0}],
    ]},
    "Update Sheet — Status IGNORED": {"main": [[{"node": "Merge — Collect Alert Posts", "type": "main", "index": 1}]]},
    "Merge — Collect Alert Posts": {"main": [[{"node": "Build Migration Digest", "type": "main", "index": 0}]]},
    "Build Migration Digest": {"main": [[{"node": "CONFIG — Notifications", "type": "main", "index": 0}]]},
    "CONFIG — Notifications": {"main": [[{"node": "Telegram — Send Digest", "type": "main", "index": 0}]]},
    "Telegram — Send Digest": {"main": [[{"node": "Expand Sent URLs", "type": "main", "index": 0}]]},
    "Expand Sent URLs": {"main": [[{"node": "Update Sheet — Status SENT", "type": "main", "index": 0}]]},
    "OpenAI Chat Model — Relevance Scoring": {"ai_languageModel": [[{"node": "AI Agent — Score Relevance", "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser — Relevance Score": {"ai_outputParser": [[{"node": "AI Agent — Score Relevance", "type": "ai_outputParser", "index": 0}]]},
}

wf = {
    "name": "Reddit RSS Migration Monitor",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/reddit-rss-migration-monitor.json"
json.dump(wf, open(out, "w"), indent=2, ensure_ascii=False)
print("wrote", out, "| nodes:", len(nodes))

# ---- validation ----
d = json.load(open(out))
names = [n["name"] for n in d["nodes"]]
ids = [n["id"] for n in d["nodes"]]
assert len(names) == len(set(names)), "duplicate node names"
assert len(ids) == len(set(ids)), "duplicate node ids"
name_set = set(names)
missing = []
for src, conns in d["connections"].items():
    assert src in name_set, f"bad connection source: {src}"
    for ctype, outs in conns.items():
        for branch in outs:
            for t in branch:
                if t["node"] not in name_set:
                    missing.append((src, t["node"]))
assert not missing, f"missing targets: {missing}"
blob = json.dumps(d)
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook.com", "AIza", "ghp_", "BotFather token"]:
    assert bad not in blob, f"possible hardcoded secret: {bad}"
types = {n["name"]: (n["type"], n["typeVersion"]) for n in d["nodes"]}
expected = {
    "Parse Old RSS Feed URLs": ("n8n-nodes-base.code", 2),
    "Fetch Reddit — Public JSON": ("n8n-nodes-base.httpRequest", 4.2),
    "Fetch Reddit — Custom JSON Source": ("n8n-nodes-base.httpRequest", 4.2),
    "IF — JSON Source Selector": ("n8n-nodes-base.if", 2.2),
    "IF — Relevance ≥ Threshold": ("n8n-nodes-base.if", 2.2),
    "Merge — Collect Alert Posts": ("n8n-nodes-base.merge", 3),
    "Read Logged Post IDs": ("n8n-nodes-base.googleSheets", 4.5),
    "Log Posts — Status NEW": ("n8n-nodes-base.googleSheets", 4.5),
    "Update Sheet — Status SCORED": ("n8n-nodes-base.googleSheets", 4.5),
    "Update Sheet — Status IGNORED": ("n8n-nodes-base.googleSheets", 4.5),
    "Update Sheet — Status SENT": ("n8n-nodes-base.googleSheets", 4.5),
    "AI Agent — Score Relevance": ("@n8n/n8n-nodes-langchain.agent", 1.7),
    "OpenAI Chat Model — Relevance Scoring": ("@n8n/n8n-nodes-langchain.lmChatOpenAi", 1.2),
    "Structured Output Parser — Relevance Score": ("@n8n/n8n-nodes-langchain.outputParserStructured", 1.2),
    "Telegram — Send Digest": ("n8n-nodes-base.telegram", 1.2),
    "STICKY — Title": ("n8n-nodes-base.stickyNote", 1),
}
for name, (t, tv) in expected.items():
    got = types.get(name)
    assert got == (t, tv), f"{name}: expected {(t, tv)}, got {got}"
sticky_names = [n for n in names if n.startswith("STICKY")]
config_names = [n for n in names if n.startswith("CONFIG")]
assert len(sticky_names) == 7, f"expected 7 stickies, got {len(sticky_names)}"
assert set(config_names) == {"CONFIG — RSS Migration", "CONFIG — Google Sheets", "CONFIG — AI Scoring", "CONFIG — Notifications"}, config_names
title = [n for n in d["nodes"] if n["name"] == "STICKY — Title"][0]
assert title["parameters"]["color"] == 5, "title sticky must be color 5"
print("validation OK")
print("node list:")
for n in d["nodes"]:
    print(f"  {n['name']} | {n['type']} v{n['typeVersion']}")
print("connection check: all", len(d["connections"]), "sources -> targets exist")
