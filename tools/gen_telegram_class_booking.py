#!/usr/bin/env python3
"""Generate the Telegram Class Booking Bot for Fitness Studios n8n workflow JSON.

Demand: n8n forum thread "Looking for an n8n Telegram Bot Workflow for Class
Scheduling & Booking" (2026-11-12, 15+ replies, OP asks for a template, no ready
template exists). Two flows: (A) Telegram booking bot, (B) daily 8 AM reminder sweep.
Google Sheets is the booking ledger (no DB server needed); the guide notes the
Postgres upgrade path (exclusion constraint on room + time range).
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

def code_node(name, js, x, y):
    return {
        "parameters": {"jsCode": js, "mode": "runOnceForAllItems"},
        "id": uid(), "name": name, "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [x, y],
    }

def sheets_node(name, op, config, tab_expr, tab_name, x, y, columns_value=None, matching=None):
    params = {
        "operation": op,
        "resource": "sheetWithinDocument",
        "documentId": {"__rl": True, "mode": "url",
                       "value": "={{ $('" + config + "').first().json.spreadsheet_id }}"},
        "sheetName": {"__rl": True, "mode": "list", "value": tab_expr},
        "options": {},
    }
    if op in ("append", "update"):
        params["columns"] = {
            "mappingMode": "defineBelow",
            "matchingColumns": matching or [],
            "schema": [],
            "attemptToConvertTypes": False, "convertFieldsToString": False,
            "value": columns_value or {},
        }
    return {
        "parameters": params,
        "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5, "position": [x, y],
    }

def telegram_node(name, chat_expr, text_expr, x, y):
    return {
        "parameters": {
            "chatId": chat_expr,
            "text": text_expr,
            "additionalFields": {"parse_mode": "Markdown"},
        },
        "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2, "position": [x, y],
    }

def if_node(name, left_expr, x, y, cond_id):
    return {
        "parameters": {
            "conditions": {
                "combinator": "and",
                "conditions": [{
                    "id": cond_id,
                    "leftValue": left_expr,
                    "rightValue": "",
                    "operator": {"type": "boolean", "operation": "true",
                                 "name": "filter.operator.boolean.true"},
                }],
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            },
            "options": {},
        },
        "id": uid(), "name": name, "type": "n8n-nodes-base.if",
        "typeVersion": 2.2, "position": [x, y],
    }

def switch_node(name, left_expr, rules, x, y):
    # rules: list of (outputKey, rightValue, operator dict)
    values = []
    for key, right, op in rules:
        values.append({
            "conditions": {
                "combinator": "and",
                "conditions": [{
                    "id": uid(),
                    "leftValue": left_expr,
                    "rightValue": right,
                    "operator": op,
                }],
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            },
            "outputKey": key,
            "renameOutput": True,
        })
    return {
        "parameters": {"options": {"fallbackOutput": "extra"}, "rules": {"values": values}},
        "id": uid(), "name": name, "type": "n8n-nodes-base.switch",
        "typeVersion": 3.2, "position": [x, y],
    }

def eq_str():
    return {"type": "string", "operation": "equals", "name": "filter.operator.string.equals"}

def starts_with():
    return {"type": "string", "operation": "startsWith", "name": "filter.operator.string.startsWith"}

CFG = "CONFIG — Studio"
CFG_R = "CONFIG — Reminders"
TRG = "Telegram Trigger"
AI = "AI Agent — Understand Booking Intent"

nodes = []

# ---------- STICKIES ----------
nodes.append(sticky("STICKY — Title",
    "## \U0001f3cb\ufe0f TELEGRAM CLASS BOOKING BOT FOR FITNESS STUDIOS\n"
    "**What it does:** FLOW A — a Telegram message arrives \u2192 staff role check \u2192 AI classifies the booking intent (view_schedule / book / reschedule / cancel / other) \u2192 class timetable + double-booking guard (room AND trainer) in Google Sheets \u2192 Telegram reply, every step logged. Admins manage classes with /addclass and /cancelclass. FLOW B — every morning at 8 AM, members with a class in the next 24h get a Telegram reminder \u2192 sheet flips to `REMINDER_SENT` \u2192 admin digest.\n\n"
    "**You'll need:**\n- Telegram bot token (@BotFather \u2192 /newbot) + your admin chat ID\n- OpenAI API key (platform.openai.com)\n- Google Sheets OAuth2 credentials\n\n"
    "**Status flow (Bookings tab):** `RECEIVED` \u2192 `CONFIRMED` / `PENDING_SLOT` / `CANCELLED` / `RESCHEDULED` / `REMINDER_SENT` / `HANDLED`\n"
    "**Sheets tabs:** `Classes` (weekly timetable) \u00b7 `Bookings` (ledger) \u00b7 `Staff` (admin/trainer roles)",
    -240, -160, 5840, 220, color=5))

nodes.append(sticky("STICKY — STEP 1",
    "## STEP 1 \u2014 Telegram trigger + CONFIG + role check + AI intent\n"
    "Telegram message \u2192 CONFIG \u2014 Studio \u2192 log a row with status `RECEIVED` \u2192 look the sender up in the Staff tab \u2192 staff go to the admin branch (STEP 4), everyone else goes to the AI Agent, which classifies intent and extracts class/date/time/room via a Structured Output Parser.",
    -240, 180, 1400, 420))

nodes.append(sticky("STICKY — STEP 2",
    "## STEP 2 \u2014 Switch routes by intent\n"
    "view_schedule \u2192 read the Classes timetable \u2192 Telegram reply with upcoming classes + free spots. book / reschedule \u2192 slot check (STEP 3). cancel \u2192 find the member's booking \u2192 mark CANCELLED. other \u2192 friendly fallback reply listing the commands.",
    1200, 180, 1240, 940))

nodes.append(sticky("STICKY — STEP 3",
    "## STEP 3 \u2014 Double-booking guard + confirm\n"
    "book/reschedule \u2192 read Classes + Bookings \u2192 Code checks for an overlapping CONFIRMED booking on the same date + time using the SAME room or the SAME trainer, and enforces capacity (Booked < Capacity). Free \u2192 append booking (`CONFIRMED` / `RESCHEDULED`) \u2192 Telegram confirmation. Busy/full \u2192 suggest 3 alternative slots \u2192 sheet `PENDING_SLOT`.",
    2480, 180, 1940, 1100))

nodes.append(sticky("STICKY — STEP 4",
    "## STEP 4 \u2014 Admin branch (staff only)\n"
    "`/addclass Class | Day | Time | Room | Trainer | Capacity` appends a row to Classes. `/cancelclass Class | Day | Time` marks that class CANCELLED. Anything else gets the admin help reply. Only Telegram user IDs listed in the Staff tab reach this branch.",
    1200, 1160, 1240, 560))

nodes.append(sticky("STICKY — STEP 5",
    "## STEP 5 \u2014 Daily 8 AM reminder sweep\n"
    "Schedule trigger \u2192 read Bookings \u2192 keep CONFIRMED bookings in the next 24h with an empty Reminder Sent \u2192 Telegram reminder per member \u2192 sheet `REMINDER_SENT` + Reminder Sent = YES \u2192 Telegram digest to the admin chat ID.",
    -240, 1780, 2400, 420))

nodes.append(sticky("STICKY — STEP 6",
    "## STEP 6 \u2014 Sheets logging + Telegram digest\n"
    "Every booking branch merges \u2192 one booking summary is built \u2192 Telegram digest to the admin chat ID (CONFIG \u2014 Notifications). The reminder sweep builds its own digest.",
    4460, 180, 1100, 700))

# ---------- FLOW A: MAIN CHAIN ----------
nodes.append({
    "parameters": {"additionalFields": {}, "updates": ["message", "callback_query"]},
    "credentials": {"telegramApi": {"id": "", "name": "Telegram Bot API"}},
    "id": uid(), "name": TRG, "type": "n8n-nodes-base.telegramTrigger",
    "typeVersion": 1.2, "position": [0, 300],
})

nodes.append(set_node(CFG, [
    ("studio_name", "PASTE_YOUR_STUDIO_NAME"),
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("classes_sheet", "Classes"),
    ("bookings_sheet", "Bookings"),
    ("staff_sheet", "Staff"),
    ("admin_chat_id", "PASTE_YOUR_TELEGRAM_ADMIN_CHAT_ID"),
    ("timezone", "Asia/Calcutta"),
    ("reminder_hours", "24"),
], 240, 300))

nodes.append(sheets_node("Log Message — RECEIVED", "append", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 480, 300, {
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Customer Name": "={{ $('" + TRG + "').first().json.message.from.first_name }}",
        "Phone": "",
        "Message": "={{ $('" + TRG + "').first().json.message.text }}",
        "Class": "",
        "Class Date": "",
        "Class Time": "",
        "Room": "",
        "Trainer": "",
        "Intent": "",
        "Status": "RECEIVED",
    }))

nodes.append(sheets_node("Read Staff", "read", CFG,
    "={{ $('" + CFG + "').first().json.staff_sheet }}", "Staff", 720, 300))

nodes.append(code_node("Code — Check Staff Role", """// Look the sender up in the Staff tab: Telegram User ID | Name | Role
const senderId = String($('Telegram Trigger').first().json.message.from.id || '');
const msg = $('Telegram Trigger').first().json.message || {};
const staff = $('Read Staff').all().map(i => i.json);
const hit = staff.find(r => String(r['Telegram User ID'] || '').trim() === senderId);
return [{ json: {
  sender_id: senderId,
  chat_id: String(msg.chat ? msg.chat.id : ''),
  message_text: msg.text || '',
  is_staff: !!hit,
  role: hit ? (hit.Role || 'staff') : 'member',
  staff_name: hit ? (hit.Name || '') : '',
} }];""", 960, 300))

nodes.append(if_node("IF — Is Staff?", "={{ $json.is_staff }}", 1200, 300, "if-staff"))

# ---------- FLOW A: ADMIN BRANCH ----------
nodes.append(switch_node("Switch — Admin Command", "={{ $json.message_text }}", [
    ("addclass", "/addclass", starts_with()),
    ("cancelclass", "/cancelclass", starts_with()),
], 1440, 1300))

nodes.append(code_node("Code — Parse Add Class", """// Format: /addclass Class Name | Day | Time | Room | Trainer | Capacity
// Day is a weekday (Mon..Sun) or an exact date (YYYY-MM-DD). Time is HH:MM (24h).
const text = ($('Code — Check Staff Role').first().json.message_text || '').trim();
const parts = text.replace(/^\\/addclass\\s*/i, '').split('|').map(s => s.trim());
const [class_name, day, time, room, trainer, capacity] = parts;
return [{ json: {
  class_name: class_name || '', day: day || '', time: time || '',
  room: room || '', trainer: trainer || '',
  capacity: parseInt(capacity || '0', 10) || 0,
  valid: !!(class_name && day && time && room),
  raw: text,
} }];""", 1680, 1220))

nodes.append(sheets_node("Append Class — Classes Sheet", "append", CFG,
    "={{ $('" + CFG + "').first().json.classes_sheet }}", "Classes", 1920, 1220, {
        "Class": "={{ $json.class_name }}",
        "Day": "={{ $json.day }}",
        "Time": "={{ $json.time }}",
        "Room": "={{ $json.room }}",
        "Trainer": "={{ $json.trainer }}",
        "Capacity": "={{ $json.capacity }}",
        "Booked": "0",
        "Status": "ACTIVE",
    }))

nodes.append(telegram_node("Telegram — Admin Class Added",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "=✅ Class added: *{{ $('Code — Parse Add Class').first().json.class_name }}* — {{ $('Code — Parse Add Class').first().json.day }} {{ $('Code — Parse Add Class').first().json.time }} · {{ $('Code — Parse Add Class').first().json.room }} · Trainer: {{ $('Code — Parse Add Class').first().json.trainer }} · Capacity {{ $('Code — Parse Add Class').first().json.capacity }}",
    2160, 1220))

nodes.append(code_node("Code — Parse Cancel Class", """// Format: /cancelclass Class Name | Day | Time
const text = ($('Code — Check Staff Role').first().json.message_text || '').trim();
const parts = text.replace(/^\\/cancelclass\\s*/i, '').split('|').map(s => s.trim());
const [class_name, day, time] = parts;
return [{ json: {
  class_name: class_name || '', day: day || '', time: time || '',
  valid: !!(class_name && day && time),
  raw: text,
} }];""", 1680, 1380))

nodes.append(sheets_node("Update Class — CANCELLED", "update", CFG,
    "={{ $('" + CFG + "').first().json.classes_sheet }}", "Classes", 1920, 1380, {
        "Class": "={{ $json.class_name }}",
        "Day": "={{ $json.day }}",
        "Time": "={{ $json.time }}",
        "Status": "CANCELLED",
    }, matching=["Class", "Day", "Time"]))

nodes.append(telegram_node("Telegram — Admin Class Cancelled",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "=❌ Class cancelled: *{{ $('Code — Parse Cancel Class').first().json.class_name }}* — {{ $('Code — Parse Cancel Class').first().json.day }} {{ $('Code — Parse Cancel Class').first().json.time }}. Members with bookings for it will need a new slot.",
    2160, 1380))

nodes.append(telegram_node("Telegram — Admin Help",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "=👋 Admin commands for {{ $('" + CFG + "').first().json.studio_name }}:\n\n/addclass Class | Day | Time | Room | Trainer | Capacity — add a class (Day = Mon..Sun or YYYY-MM-DD, Time = HH:MM)\n/cancelclass Class | Day | Time — cancel a class\n\nExample:\n/addclass Morning Yoga | Mon | 07:00 | Room A | Priya | 20",
    1680, 1540))

# ---------- FLOW A: AI INTENT ----------
nodes.append({
    "parameters": {
        "options": {
            "systemMessage": "=You are the friendly booking assistant for {{ $('" + CFG + "').first().json.studio_name }}, a fitness studio. A member just wrote on Telegram. Extract their class-booking intent precisely:\n- 'view_schedule' = they want to see class schedules / available slots / timings\n- 'book' = they want to BOOK a class (with or without a date/time)\n- 'reschedule' = they want to MOVE an existing booking to another day/time\n- 'cancel' = they want to CANCEL an existing booking\n- 'other' = anything else (prices, greetings, questions, membership)\n\nToday is {{ $now.toFormat('yyyy-MM-dd') }} and the studio timezone is {{ $('" + CFG + "').first().json.timezone }}. Convert any mentioned date/time into YYYY-MM-DD and 24-hour HH:MM in that timezone (assume upcoming dates when ambiguous; 'tomorrow' means the next calendar day). Leave fields empty when not mentioned. Output ONLY via the structured output parser.",
        },
        "text": "=Incoming Telegram message:\n\n{{ $('" + TRG + "').first().json.message.text }}",
    },
    "id": uid(), "name": AI, "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 1.7, "position": [1440, 460],
})

nodes.append({
    "parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {}},
    "credentials": {"openAiApi": {"id": "", "name": "OpenAI API"}},
    "id": uid(), "name": "OpenAI Chat Model — Intent", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.2, "position": [1440, 720],
})

nodes.append({
    "parameters": {
        "schemaType": "manual",
        "inputSchema": "{\n  \"intent\": \"one of: view_schedule | book | reschedule | cancel | other\",\n  \"class_name\": \"class name, or empty string if not given\",\n  \"date\": \"YYYY-MM-DD date of the class, or empty string if no date mentioned\",\n  \"time\": \"HH:MM 24-hour time, or empty string if no time mentioned\",\n  \"room\": \"room name if mentioned, or empty string\",\n  \"customer_name\": \"member's name, or empty string if not given\",\n  \"phone\": \"phone number if given, or empty string\",\n  \"notes\": \"any other relevant detail from the message, or empty string\"\n}",
    },
    "id": uid(), "name": "Structured Output Parser — Intent", "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.2, "position": [1680, 720],
})

nodes.append(switch_node("Switch — Route by Intent",
    "={{ $('" + AI + "').first().json.output.intent }}", [
        ("view_schedule", "view_schedule", eq_str()),
        ("book", "book", eq_str()),
        ("reschedule", "reschedule", eq_str()),
        ("cancel", "cancel", eq_str()),
    ], 1680, 460))

# ---------- FLOW A: view_schedule ----------
nodes.append(sheets_node("Read Classes — Schedule", "read", CFG,
    "={{ $('" + CFG + "').first().json.classes_sheet }}", "Classes", 1920, 300))

nodes.append(code_node("Code — Build Schedule Reply", """// Build the schedule reply from the weekly timetable.
// Classes rows: Class | Day | Time | Room | Trainer | Capacity | Booked | Status
// Day is a weekday (Mon..Sun) or an exact date (YYYY-MM-DD).
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const studio = $('CONFIG — Studio').first().json.studio_name;
const rows = $('Read Classes — Schedule').all().map(i => i.json)
  .filter(r => !r.Status || String(r.Status).toUpperCase() === 'ACTIVE');
function rowWeekday(r) {
  const d = (r.Day || '').trim();
  if (/^\\d{4}-\\d{2}-\\d{2}$/.test(d)) {
    const t = new Date(d + 'T00:00:00');
    return isNaN(t.getTime()) ? -1 : t.getDay();
  }
  return DAYS.indexOf(d);
}
const todayIdx = new Date().getDay();
const order = Array.from({ length: 7 }, (_, k) => (todayIdx + k) % 7);
const lines = ['\\U0001F3CB\\uFE0F *Class schedule \\u2014 ' + studio + '*', ''];
let shown = 0;
for (const d of order) {
  const dayRows = rows.filter(r => rowWeekday(r) === d)
    .sort((a, b) => String(a.Time || '').localeCompare(String(b.Time || '')));
  if (!dayRows.length) continue;
  lines.push('*' + DAYS[d] + '*');
  for (const r of dayRows) {
    const cap = parseInt(r.Capacity || '0', 10);
    const booked = parseInt(r.Booked || '0', 10);
    const free = cap ? Math.max(cap - booked, 0) : '?';
    lines.push('\\u2022 *' + (r.Class || '') + '* \\u2014 ' + (r.Time || '') + ' \\u00b7 ' + (r.Room || '') + ' \\u00b7 with ' + (r.Trainer || '') + ' \\u00b7 ' + free + ' spots left');
    shown++;
  }
  lines.push('');
}
if (!shown) lines.push('No classes scheduled this week yet. Reply BOOK and tell me which class you want!');
else lines.push('To book, reply e.g. \\u201cBook Morning Yoga tomorrow 7am\\u201d.');
return [{ json: { reply_text: lines.join('\\n') } }];""", 2160, 300))

nodes.append(telegram_node("Telegram — Send Schedule",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "={{ $json.reply_text }}", 2400, 300))

# ---------- FLOW A: book ----------
nodes.append(sheets_node("Read Classes — Book", "read", CFG,
    "={{ $('" + CFG + "').first().json.classes_sheet }}", "Classes", 1920, 460))
nodes.append(sheets_node("Read Bookings — Book", "read", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 2160, 460))

SLOT_CHECK_JS = """// Double-booking guard for the BOOK branch.
// Match the requested class in the timetable, then check for an overlapping
// CONFIRMED/RESCHEDULED booking on the same date + time using the SAME room
// or the SAME trainer. Also enforces capacity (Booked < Capacity).
// If the slot is taken, propose up to 3 alternative slots for the same class.
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const out = ($('AI Agent — Understand Booking Intent').first().json.output) || {};
const className = (out.class_name || '').trim();
const date = (out.date || '').trim();
const time = (out.time || '').trim();
const wantedRoom = (out.room || '').trim();
const classes = $('__READ_CLASSES__').all().map(i => i.json);
const bookings = $('__READ_BOOKINGS__').all().map(i => i.json);
const studio = $('CONFIG — Studio').first().json.studio_name;
function nextDateFor(dayStr) {
  if (/^\\d{4}-\\d{2}-\\d{2}$/.test(dayStr)) return dayStr;
  const idx = DAYS.indexOf(dayStr);
  if (idx < 0) return '';
  const d = new Date();
  d.setDate(d.getDate() + ((idx - d.getDay() + 7) % 7));
  return d.toISOString().slice(0, 10);
}
function hasClash(d, t, room, trainer) {
  return bookings.some(b => {
    const st = (b.Status || '').toUpperCase();
    if (st !== 'CONFIRMED' && st !== 'RESCHEDULED') return false;
    if ((b['Class Date'] || '').trim() !== d) return false;
    if ((b['Class Time'] || '').trim() !== t) return false;
    return (room && (b.Room || '').trim() === room) || (trainer && (b.Trainer || '').trim() === trainer);
  });
}
const weekday = date ? DAYS[new Date(date + 'T00:00:00').getDay()] : '';
function rowMatches(r, cls, dt, tm) {
  if (!cls || (r.Class || '').toLowerCase() !== cls.toLowerCase()) return false;
  if (r.Status && String(r.Status).toUpperCase() !== 'ACTIVE') return false;
  const d = (r.Day || '').trim();
  if (dt && d !== weekday && d !== dt) return false;
  if (tm && (r.Time || '').trim() !== tm) return false;
  return true;
}
let slot = classes.find(r => rowMatches(r, className, date, time)) || null;
if (!slot && className) slot = classes.find(r => (r.Class || '').toLowerCase() === className.toLowerCase() && (!r.Status || String(r.Status).toUpperCase() === 'ACTIVE')) || null;
let slot_free = false, conflict_reason = '', alternatives = [];
let room = '', trainer = '';
if (!className || !date || !time) {
  conflict_reason = 'missing_details';
} else if (!slot) {
  conflict_reason = 'no_such_class';
} else {
  room = wantedRoom || (slot.Room || '');
  trainer = slot.Trainer || '';
  const cap = parseInt(slot.Capacity || '0', 10);
  const booked = parseInt(slot.Booked || '0', 10);
  if (hasClash(date, time, room, trainer)) conflict_reason = 'double_booking';
  else if (cap && booked >= cap) conflict_reason = 'class_full';
  else slot_free = true;
  if (!slot_free) {
    for (const r of classes) {
      if (alternatives.length >= 3) break;
      if ((r.Class || '').toLowerCase() !== className.toLowerCase()) continue;
      if (r === slot) continue;
      if (r.Status && String(r.Status).toUpperCase() !== 'ACTIVE') continue;
      const c2 = parseInt(r.Capacity || '0', 10), b2 = parseInt(r.Booked || '0', 10);
      if (c2 && b2 >= c2) continue;
      const altDate = nextDateFor((r.Day || '').trim());
      if (!altDate || hasClash(altDate, (r.Time || '').trim(), (r.Room || '').trim(), (r.Trainer || '').trim())) continue;
      alternatives.push({ class_name: r.Class, date: altDate, time: r.Time, room: r.Room, trainer: r.Trainer });
    }
  }
}
let confirm_text = '', reply_text = '';
const who = out.customer_name ? ' ' + out.customer_name : '';
if (slot_free) {
  confirm_text = '\\u2705 Booking confirmed at ' + studio + '!' + '\\n\\n\\U0001F3CB\\uFE0F *' + className + '*\\n\\U0001F4C5 ' + date + ' \\u00b7 ' + time + '\\n\\U0001F4CD ' + room + (trainer ? ' \\u00b7 Trainer: ' + trainer : '') + '\\n\\nReply CANCEL to cancel or RESCHEDULE to move it. See you there!' + (who ? '\\n\\u2014 booked for' + who : '');
} else if (conflict_reason === 'missing_details') {
  reply_text = 'Thanks for reaching out to ' + studio + '! \\U0001F60A To book a class, please reply with the class, date and time \\u2014 e.g. \\u201cBook Morning Yoga tomorrow 7am\\u201d.';
} else if (conflict_reason === 'no_such_class') {
  reply_text = 'Sorry, I could not find a class called \\u201c' + className + '\\u201d in the timetable. \\U0001F615 Reply SCHEDULE to see all classes and times.';
} else {
  reply_text = 'Sorry, ' + className + ' on ' + date + ' at ' + time + ' is ' + (conflict_reason === 'class_full' ? 'fully booked' : 'already booked for that room/trainer') + '. \\U0001F615\\n\\nHere are some alternatives:\\n'
    + alternatives.map(a => '\\u2022 ' + a.class_name + ' \\u2014 ' + a.date + ' ' + a.time + ' \\u00b7 ' + a.room + ' \\u00b7 ' + a.trainer).join('\\n')
    + (alternatives.length ? '\\n\\nReply with the one you prefer, or suggest another time.' : '\\n\\nNo free slots for this class this week \\u2014 reply SCHEDULE to browse everything.');
}
return [{ json: {
  class_name: className, date, time, room, trainer,
  customer_name: (out.customer_name || '').trim(),
  phone: (out.phone || '').trim(),
  slot_free, conflict_reason, alternatives, confirm_text, reply_text,
} }];"""

nodes.append(code_node("Code — Check Slot & Find Alternatives",
    SLOT_CHECK_JS.replace("__READ_CLASSES__", "Read Classes — Book").replace("__READ_BOOKINGS__", "Read Bookings — Book"),
    2400, 460))

nodes.append(if_node("IF — Slot Free?", "={{ $json.slot_free }}", 2640, 460, "if-slot"))

nodes.append(sheets_node("Append Booking — CONFIRMED", "append", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 2880, 380, {
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Customer Name": "={{ $json.customer_name || $('" + TRG + "').first().json.message.from.first_name }}",
        "Phone": "={{ $json.phone }}",
        "Message": "={{ $('" + TRG + "').first().json.message.text }}",
        "Class": "={{ $json.class_name }}",
        "Class Date": "={{ $json.date }}",
        "Class Time": "={{ $json.time }}",
        "Room": "={{ $json.room }}",
        "Trainer": "={{ $json.trainer }}",
        "Intent": "book",
        "Status": "CONFIRMED",
    }))

nodes.append(telegram_node("Telegram — Confirm Booking",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "={{ $('Code — Check Slot & Find Alternatives').first().json.confirm_text }}",
    3120, 380))

nodes.append(telegram_node("Telegram — Suggest Alternatives",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "={{ $json.reply_text }}", 2880, 540))

nodes.append(sheets_node("Update Sheet — PENDING_SLOT", "update", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 3120, 540, {
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Class": "={{ $('Code — Check Slot & Find Alternatives').first().json.class_name }}",
        "Intent": "book",
        "Status": "PENDING_SLOT",
    }, matching=["Chat ID", "Date"]))

# ---------- FLOW A: reschedule ----------
nodes.append(sheets_node("Read Bookings — Reschedule", "read", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 1920, 620))

nodes.append(code_node("Code — Find Customer Booking", """// Find the member's upcoming CONFIRMED booking by Telegram chat id.
// Prefer the class the AI extracted; otherwise take the earliest upcoming one.
const chatId = String($('Telegram Trigger').first().json.message.chat.id || '');
const out = ($('AI Agent — Understand Booking Intent').first().json.output) || {};
const rows = $('Read Bookings — Reschedule').all().map(i => i.json)
  .filter(b => String(b['Chat ID'] || '').trim() === chatId && (b.Status || '').toUpperCase() === 'CONFIRMED');
let hit = null;
if (out.class_name) hit = rows.find(b => (b.Class || '').toLowerCase() === out.class_name.toLowerCase()) || null;
if (!hit) hit = rows.sort((a, b) => String(a['Class Date'] || '').localeCompare(String(b['Class Date'] || '')))[0] || null;
return [{ json: {
  found: !!hit,
  old_class: hit ? (hit.Class || '') : '',
  old_date: hit ? (hit['Class Date'] || '') : '',
  old_time: hit ? (hit['Class Time'] || '') : '',
  old_room: hit ? (hit.Room || '') : '',
  old_trainer: hit ? (hit.Trainer || '') : '',
  new_class: (out.class_name || '').trim(),
  new_date: (out.date || '').trim(),
  new_time: (out.time || '').trim(),
  new_room: (out.room || '').trim(),
  customer_name: (out.customer_name || '').trim(),
} }];""", 2160, 620))

nodes.append(if_node("IF — Booking Found?", "={{ $json.found }}", 2400, 620, "if-found-reschedule"))

nodes.append(sheets_node("Update Sheet — Cancel Old Booking", "update", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 2640, 700, {
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Class": "={{ $json.old_class }}",
        "Class Date": "={{ $json.old_date }}",
        "Status": "CANCELLED",
    }, matching=["Chat ID", "Class", "Class Date"]))

nodes.append(sheets_node("Read Classes — Reschedule", "read", CFG,
    "={{ $('" + CFG + "').first().json.classes_sheet }}", "Classes", 2880, 700))
nodes.append(sheets_node("Read Bookings — Reschedule Check", "read", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 3120, 700))

RESCHEDULE_CHECK_JS = SLOT_CHECK_JS.replace(
    "const out = ($('AI Agent — Understand Booking Intent').first().json.output) || {};",
    "const found = $('Code — Find Customer Booking').first().json;\nconst out = { class_name: found.new_class, date: found.new_date, time: found.new_time, room: found.new_room, customer_name: found.customer_name, phone: '' };"
).replace("__READ_CLASSES__", "Read Classes — Reschedule").replace("__READ_BOOKINGS__", "Read Bookings — Reschedule Check").replace(
    "Booking confirmed at ", "Booking moved to "
).replace(
    "To book a class, please reply with the class, date and time",
    "To move your booking, please reply with the new class, date and time"
)

nodes.append(code_node("Code — Check New Slot & Alternatives", RESCHEDULE_CHECK_JS, 3360, 700))
nodes.append(if_node("IF — New Slot Free?", "={{ $json.slot_free }}", 3600, 700, "if-new-slot"))

nodes.append(sheets_node("Append Booking — RESCHEDULED", "append", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 3840, 620, {
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Customer Name": "={{ $json.customer_name || $('" + TRG + "').first().json.message.from.first_name }}",
        "Phone": "={{ $json.phone }}",
        "Message": "={{ $('" + TRG + "').first().json.message.text }}",
        "Class": "={{ $json.class_name }}",
        "Class Date": "={{ $json.date }}",
        "Class Time": "={{ $json.time }}",
        "Room": "={{ $json.room }}",
        "Trainer": "={{ $json.trainer }}",
        "Intent": "reschedule",
        "Status": "RESCHEDULED",
    }))

nodes.append(telegram_node("Telegram — Confirm Reschedule",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "={{ $('Code — Check New Slot & Alternatives').first().json.confirm_text }}",
    4080, 620))

nodes.append(telegram_node("Telegram — Suggest Alternatives (Reschedule)",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "={{ $json.reply_text }}", 3840, 780))

nodes.append(sheets_node("Update Sheet — PENDING_SLOT (Reschedule)", "update", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 4080, 780, {
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Class": "={{ $('Code — Check New Slot & Alternatives').first().json.class_name }}",
        "Intent": "reschedule",
        "Status": "PENDING_SLOT",
    }, matching=["Chat ID", "Date"]))

nodes.append(telegram_node("Telegram — No Booking Found",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "=I couldn't find an upcoming booking for you. 😕 Please reply with the class and date you'd like to move (e.g. “reschedule my Yoga class to Friday 7am”).",
    2640, 860))

nodes.append(sheets_node("Update Sheet — HANDLED (Reschedule)", "update", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 2880, 860, {
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Intent": "reschedule",
        "Status": "HANDLED",
    }, matching=["Chat ID", "Date"]))

# ---------- FLOW A: cancel ----------
nodes.append(sheets_node("Read Bookings — Cancel", "read", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 1920, 940))

nodes.append(code_node("Code — Find Booking to Cancel", """// Find the member's CONFIRMED booking by Telegram chat id, preferring the
// class/date the AI extracted; otherwise take the earliest upcoming one.
const chatId = String($('Telegram Trigger').first().json.message.chat.id || '');
const out = ($('AI Agent — Understand Booking Intent').first().json.output) || {};
const rows = $('Read Bookings — Cancel').all().map(i => i.json)
  .filter(b => String(b['Chat ID'] || '').trim() === chatId && (b.Status || '').toUpperCase() === 'CONFIRMED');
let hit = null;
if (out.class_name) {
  hit = rows.find(b => (b.Class || '').toLowerCase() === out.class_name.toLowerCase()
    && (!out.date || (b['Class Date'] || '').trim() === out.date)) || null;
}
if (!hit) hit = rows.sort((a, b) => String(a['Class Date'] || '').localeCompare(String(b['Class Date'] || '')))[0] || null;
return [{ json: {
  found: !!hit,
  old_class: hit ? (hit.Class || '') : '',
  old_date: hit ? (hit['Class Date'] || '') : '',
  old_time: hit ? (hit['Class Time'] || '') : '',
  old_room: hit ? (hit.Room || '') : '',
} }];""", 2160, 940))

nodes.append(if_node("IF — Booking Found? (Cancel)", "={{ $json.found }}", 2400, 940, "if-found-cancel"))

nodes.append(sheets_node("Update Sheet — CANCELLED", "update", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 2640, 940, {
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Class": "={{ $json.old_class }}",
        "Class Date": "={{ $json.old_date }}",
        "Status": "CANCELLED",
    }, matching=["Chat ID", "Class", "Class Date"]))

nodes.append(telegram_node("Telegram — Confirm Cancellation",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "=❌ Done — your *{{ $('Code — Find Booking to Cancel').first().json.old_class }}* class on {{ $('Code — Find Booking to Cancel').first().json.old_date }} at {{ $('Code — Find Booking to Cancel').first().json.old_time }} is cancelled. Reply BOOK anytime to grab a new slot. 🙏",
    2880, 940))

nodes.append(telegram_node("Telegram — No Booking Found (Cancel)",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "=I couldn't find an upcoming booking for this chat. 😕 Please reply with the class and date you'd like to cancel (e.g. “cancel my Yoga class tomorrow 7am”).",
    2640, 1100))

nodes.append(sheets_node("Update Sheet — HANDLED (Cancel)", "update", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 2880, 1100, {
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Intent": "cancel",
        "Status": "HANDLED",
    }, matching=["Chat ID", "Date"]))

# ---------- FLOW A: other ----------
nodes.append(telegram_node("Telegram — Fallback Reply",
    "={{ $('" + TRG + "').first().json.message.chat.id }}",
    "=Hello from {{ $('" + CFG + "').first().json.studio_name }}! 👋\n\nI can help you:\n• SCHEDULE — see class timings and free slots\n• BOOK — book a class (e.g. “Book Morning Yoga tomorrow 7am”)\n• RESCHEDULE — move an existing booking\n• CANCEL — cancel an existing booking\n\nJust reply with what you'd like to do!",
    1920, 1100))

nodes.append(sheets_node("Update Sheet — HANDLED", "update", CFG,
    "={{ $('" + CFG + "').first().json.bookings_sheet }}", "Bookings", 2160, 1100, {
        "Chat ID": "={{ $('" + TRG + "').first().json.message.chat.id }}",
        "Date": "={{ $now.toFormat('yyyy-MM-dd') }}",
        "Intent": "= {{ $('" + AI + "').first().json.output.intent }}",
        "Status": "HANDLED",
    }, matching=["Chat ID", "Date"]))

# ---------- FLOW A: MERGE + DIGEST ----------
nodes.append({
    "parameters": {"mode": "append", "options": {}},
    "id": uid(), "name": "Merge — Booking Branches", "type": "n8n-nodes-base.merge",
    "typeVersion": 3, "position": [4320, 600],
})

nodes.append(code_node("Code — Build Booking Summary", """// Build one Telegram digest line for this booking-flow run.
function ran(name) { try { return $(name).all().length > 0; } catch (e) { return false; } }
const biz = $('CONFIG — Studio').first().json.studio_name;
const trigger = $('Telegram Trigger').first().json.message || {};
const intent = (($('AI Agent — Understand Booking Intent').first().json.output) || {}).intent || 'unknown';
const status = ran('Append Booking — CONFIRMED') ? 'CONFIRMED \\u2705'
  : ran('Append Booking — RESCHEDULED') ? 'RESCHEDULED \\u2705'
  : ran('Update Sheet — PENDING_SLOT') ? 'PENDING_SLOT \\u23f3 (alternatives suggested)'
  : ran('Update Sheet — CANCELLED') ? 'CANCELLED \\u274c'
  : 'HANDLED \\U0001F4AC';
const lines = [
  '\\U0001F3CB\\uFE0F *Booking Activity \\u2014 ' + biz + '*', '',
  '\\U0001F464 ' + (trigger.chat ? trigger.chat.id : ''),
  '\\U0001F4AC \\u201c' + String(trigger.text || '').slice(0, 140) + '\\u201d',
  '\\U0001F9ED Intent: ' + intent,
  '\\U0001F4CC Status: ' + status,
];
return [{ json: { digest: lines.join('\\n') } }];""", 4560, 600))

nodes.append(set_node("CONFIG — Notifications", [
    ("telegram_chat_id", "PASTE_YOUR_TELEGRAM_CHAT_ID"),
], 4800, 600))

nodes.append(telegram_node("Telegram — Booking Activity Digest",
    "={{ $('CONFIG — Notifications').first().json.telegram_chat_id }}",
    "={{ $json.digest }}", 5040, 600))

# ---------- FLOW B: DAILY 8 AM REMINDER SWEEP ----------
nodes.append({
    "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 24, "triggerAtHour": 8, "triggerAtMinute": 0}]}},
    "id": uid(), "name": "Daily 8AM Trigger", "type": "n8n-nodes-base.scheduleTrigger",
    "typeVersion": 1.2, "position": [0, 1900],
})

nodes.append(set_node(CFG_R, [
    ("studio_name", "PASTE_YOUR_STUDIO_NAME"),
    ("spreadsheet_id", "PASTE_YOUR_SPREADSHEET_ID"),
    ("bookings_sheet", "Bookings"),
    ("admin_chat_id", "PASTE_YOUR_TELEGRAM_ADMIN_CHAT_ID"),
    ("reminder_hours", "24"),
], 240, 1900))

nodes.append(sheets_node("Read Bookings — Reminders", "read", CFG_R,
    "={{ $('" + CFG_R + "').first().json.bookings_sheet }}", "Bookings", 480, 1900))

nodes.append(code_node("Code — Filter Due Reminders", """// Keep CONFIRMED bookings in the next reminder_hours whose Reminder Sent is empty.
// Class Date + Class Time define when the class starts.
const hours = parseInt($('CONFIG — Reminders').first().json.reminder_hours || '24', 10);
const studio = $('CONFIG — Reminders').first().json.studio_name;
const now = Date.now(), horizon = now + hours * 3600 * 1000;
const rows = $('Read Bookings — Reminders').all().map(i => i.json);
const due = rows.filter(b => {
  if ((b.Status || '').toUpperCase() !== 'CONFIRMED') return false;
  if ((b['Reminder Sent'] || '').trim() !== '') return false;
  const dt = new Date(((b['Class Date'] || '').trim()) + 'T' + ((b['Class Time'] || '00:00').trim()) + ':00');
  const t = dt.getTime();
  return !isNaN(t) && t > now && t <= horizon;
});
return due.map(b => ({ json: {
  'Chat ID': b['Chat ID'],
  'Customer Name': b['Customer Name'] || '',
  Class: b.Class || '',
  'Class Date': b['Class Date'] || '',
  'Class Time': b['Class Time'] || '',
  Room: b.Room || '',
  Trainer: b.Trainer || '',
  reminder_text: '\\u23F0 Reminder from ' + studio + '!\\n\\n\\U0001F3CB\\uFE0F Your *' + (b.Class || 'class') + '* is coming up:\\n\\U0001F4C5 ' + (b['Class Date'] || '') + ' \\u00b7 ' + (b['Class Time'] || '') + '\\n\\U0001F4CD ' + (b.Room || '') + (b.Trainer ? ' \\u00b7 Trainer: ' + b.Trainer : '') + '\\n\\nSee you there! Reply CANCEL if you can\\u2019t make it.',
} }));""", 720, 1900))

nodes.append(telegram_node("Telegram — Send Reminder",
    "={{ $json['Chat ID'] }}",
    "={{ $json.reminder_text }}", 960, 1900))

nodes.append(sheets_node("Update Sheet — REMINDER_SENT", "update", CFG_R,
    "={{ $('" + CFG_R + "').first().json.bookings_sheet }}", "Bookings", 1200, 1900, {
        "Chat ID": "={{ $json['Chat ID'] }}",
        "Class": "={{ $json.Class }}",
        "Class Date": "={{ $json['Class Date'] }}",
        "Reminder Sent": "YES",
        "Status": "REMINDER_SENT",
    }, matching=["Chat ID", "Class", "Class Date"]))

nodes.append(code_node("Code — Build Reminder Digest", """// Count the reminder run for the Telegram digest.
const sent = $('Telegram — Send Reminder').all().length;
const items = $('Code — Filter Due Reminders').all().map(i => i.json);
const lines = [
  '\\u23F0 *Class Reminders \\u2014 ' + new Date().toISOString().slice(0, 10) + '*', '',
  '\\U0001F4AC ' + sent + ' reminder(s) sent for classes in the next 24h',
];
if (items.length) {
  lines.push('', items.slice(0, 10).map(b => '\\u2022 ' + (b['Customer Name'] || b['Chat ID']) + ' \\u2014 ' + b.Class + ' ' + b['Class Date'] + ' ' + b['Class Time']).join('\\n'));
}
lines.push('', 'Sheet status \\u2192 REMINDER_SENT.');
return [{ json: { digest: lines.join('\\n') } }];""", 1440, 1900))

nodes.append(telegram_node("Telegram — Send Reminder Digest",
    "={{ $('" + CFG_R + "').first().json.admin_chat_id }}",
    "={{ $json.digest }}", 1680, 1900))

connections = {
    TRG: {"main": [[{"node": CFG, "type": "main", "index": 0}]]},
    CFG: {"main": [[{"node": "Log Message — RECEIVED", "type": "main", "index": 0}]]},
    "Log Message — RECEIVED": {"main": [[{"node": "Read Staff", "type": "main", "index": 0}]]},
    "Read Staff": {"main": [[{"node": "Code — Check Staff Role", "type": "main", "index": 0}]]},
    "Code — Check Staff Role": {"main": [[{"node": "IF — Is Staff?", "type": "main", "index": 0}]]},
    "IF — Is Staff?": {"main": [
        [{"node": "Switch — Admin Command", "type": "main", "index": 0}],
        [{"node": AI, "type": "main", "index": 0}],
    ]},
    "Switch — Admin Command": {"main": [
        [{"node": "Code — Parse Add Class", "type": "main", "index": 0}],
        [{"node": "Code — Parse Cancel Class", "type": "main", "index": 0}],
        [{"node": "Telegram — Admin Help", "type": "main", "index": 0}],
    ]},
    "Code — Parse Add Class": {"main": [[{"node": "Append Class — Classes Sheet", "type": "main", "index": 0}]]},
    "Append Class — Classes Sheet": {"main": [[{"node": "Telegram — Admin Class Added", "type": "main", "index": 0}]]},
    "Code — Parse Cancel Class": {"main": [[{"node": "Update Class — CANCELLED", "type": "main", "index": 0}]]},
    "Update Class — CANCELLED": {"main": [[{"node": "Telegram — Admin Class Cancelled", "type": "main", "index": 0}]]},
    AI: {"main": [[{"node": "Switch — Route by Intent", "type": "main", "index": 0}]]},
    "Switch — Route by Intent": {"main": [
        [{"node": "Read Classes — Schedule", "type": "main", "index": 0}],
        [{"node": "Read Classes — Book", "type": "main", "index": 0}],
        [{"node": "Read Bookings — Reschedule", "type": "main", "index": 0}],
        [{"node": "Read Bookings — Cancel", "type": "main", "index": 0}],
        [{"node": "Telegram — Fallback Reply", "type": "main", "index": 0}],
    ]},
    "Read Classes — Schedule": {"main": [[{"node": "Code — Build Schedule Reply", "type": "main", "index": 0}]]},
    "Code — Build Schedule Reply": {"main": [[{"node": "Telegram — Send Schedule", "type": "main", "index": 0}]]},
    "Telegram — Send Schedule": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 0}]]},
    "Read Classes — Book": {"main": [[{"node": "Read Bookings — Book", "type": "main", "index": 0}]]},
    "Read Bookings — Book": {"main": [[{"node": "Code — Check Slot & Find Alternatives", "type": "main", "index": 0}]]},
    "Code — Check Slot & Find Alternatives": {"main": [[{"node": "IF — Slot Free?", "type": "main", "index": 0}]]},
    "IF — Slot Free?": {"main": [
        [{"node": "Append Booking — CONFIRMED", "type": "main", "index": 0}],
        [{"node": "Telegram — Suggest Alternatives", "type": "main", "index": 0}],
    ]},
    "Append Booking — CONFIRMED": {"main": [[{"node": "Telegram — Confirm Booking", "type": "main", "index": 0}]]},
    "Telegram — Confirm Booking": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 1}]]},
    "Telegram — Suggest Alternatives": {"main": [[{"node": "Update Sheet — PENDING_SLOT", "type": "main", "index": 0}]]},
    "Update Sheet — PENDING_SLOT": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 2}]]},
    "Read Bookings — Reschedule": {"main": [[{"node": "Code — Find Customer Booking", "type": "main", "index": 0}]]},
    "Code — Find Customer Booking": {"main": [[{"node": "IF — Booking Found?", "type": "main", "index": 0}]]},
    "IF — Booking Found?": {"main": [
        [{"node": "Update Sheet — Cancel Old Booking", "type": "main", "index": 0}],
        [{"node": "Telegram — No Booking Found", "type": "main", "index": 0}],
    ]},
    "Update Sheet — Cancel Old Booking": {"main": [[{"node": "Read Classes — Reschedule", "type": "main", "index": 0}]]},
    "Read Classes — Reschedule": {"main": [[{"node": "Read Bookings — Reschedule Check", "type": "main", "index": 0}]]},
    "Read Bookings — Reschedule Check": {"main": [[{"node": "Code — Check New Slot & Alternatives", "type": "main", "index": 0}]]},
    "Code — Check New Slot & Alternatives": {"main": [[{"node": "IF — New Slot Free?", "type": "main", "index": 0}]]},
    "IF — New Slot Free?": {"main": [
        [{"node": "Append Booking — RESCHEDULED", "type": "main", "index": 0}],
        [{"node": "Telegram — Suggest Alternatives (Reschedule)", "type": "main", "index": 0}],
    ]},
    "Append Booking — RESCHEDULED": {"main": [[{"node": "Telegram — Confirm Reschedule", "type": "main", "index": 0}]]},
    "Telegram — Confirm Reschedule": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 3}]]},
    "Telegram — Suggest Alternatives (Reschedule)": {"main": [[{"node": "Update Sheet — PENDING_SLOT (Reschedule)", "type": "main", "index": 0}]]},
    "Update Sheet — PENDING_SLOT (Reschedule)": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 4}]]},
    "Telegram — No Booking Found": {"main": [[{"node": "Update Sheet — HANDLED (Reschedule)", "type": "main", "index": 0}]]},
    "Update Sheet — HANDLED (Reschedule)": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 5}]]},
    "Read Bookings — Cancel": {"main": [[{"node": "Code — Find Booking to Cancel", "type": "main", "index": 0}]]},
    "Code — Find Booking to Cancel": {"main": [[{"node": "IF — Booking Found? (Cancel)", "type": "main", "index": 0}]]},
    "IF — Booking Found? (Cancel)": {"main": [
        [{"node": "Update Sheet — CANCELLED", "type": "main", "index": 0}],
        [{"node": "Telegram — No Booking Found (Cancel)", "type": "main", "index": 0}],
    ]},
    "Update Sheet — CANCELLED": {"main": [[{"node": "Telegram — Confirm Cancellation", "type": "main", "index": 0}]]},
    "Telegram — Confirm Cancellation": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 6}]]},
    "Telegram — No Booking Found (Cancel)": {"main": [[{"node": "Update Sheet — HANDLED (Cancel)", "type": "main", "index": 0}]]},
    "Update Sheet — HANDLED (Cancel)": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 7}]]},
    "Telegram — Fallback Reply": {"main": [[{"node": "Update Sheet — HANDLED", "type": "main", "index": 0}]]},
    "Update Sheet — HANDLED": {"main": [[{"node": "Merge — Booking Branches", "type": "main", "index": 8}]]},
    "Merge — Booking Branches": {"main": [[{"node": "Code — Build Booking Summary", "type": "main", "index": 0}]]},
    "Code — Build Booking Summary": {"main": [[{"node": "CONFIG — Notifications", "type": "main", "index": 0}]]},
    "CONFIG — Notifications": {"main": [[{"node": "Telegram — Booking Activity Digest", "type": "main", "index": 0}]]},
    "OpenAI Chat Model — Intent": {"ai_languageModel": [[{"node": AI, "type": "ai_languageModel", "index": 0}]]},
    "Structured Output Parser — Intent": {"ai_outputParser": [[{"node": AI, "type": "ai_outputParser", "index": 0}]]},
    "Daily 8AM Trigger": {"main": [[{"node": CFG_R, "type": "main", "index": 0}]]},
    CFG_R: {"main": [[{"node": "Read Bookings — Reminders", "type": "main", "index": 0}]]},
    "Read Bookings — Reminders": {"main": [[{"node": "Code — Filter Due Reminders", "type": "main", "index": 0}]]},
    "Code — Filter Due Reminders": {"main": [[{"node": "Telegram — Send Reminder", "type": "main", "index": 0}]]},
    "Telegram — Send Reminder": {"main": [[{"node": "Update Sheet — REMINDER_SENT", "type": "main", "index": 0}]]},
    "Update Sheet — REMINDER_SENT": {"main": [[{"node": "Code — Build Reminder Digest", "type": "main", "index": 0}]]},
    "Code — Build Reminder Digest": {"main": [[{"node": "Telegram — Send Reminder Digest", "type": "main", "index": 0}]]},
}

wf = {
    "name": "Telegram Class Booking Bot for Fitness Studios",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False, "instanceId": ""},
}

out = "/home/hatch/workspace/blog/public/templates/telegram-class-booking-bot.json"
json.dump(wf, open(out, "w"), indent=2, ensure_ascii=False)
print("wrote", out, "| nodes:", len(nodes))

# ---- validation ----
d = json.load(open(out))
names = [n["name"] for n in d["nodes"]]
assert len(names) == len(set(names)), "duplicate node names!"
name_set = set(names)
missing = []
for src, conns in d["connections"].items():
    assert src in name_set, f"bad source {src}"
    for ctype, outs in conns.items():
        for branch in outs:
            for t in branch:
                if t["node"] not in name_set:
                    missing.append((src, t["node"]))
assert not missing, f"missing targets: {missing}"
blob = json.dumps(d)
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook", "api_key\":\"", "PASTE_YOUR" ]:
    pass
# secrets check: only PASTE_YOUR_* placeholders allowed
for bad in ["sk-", "xoxb-", "ya29.", "@gmail.com", "@outlook.com", "AKIA"]:
    assert bad not in blob, f"possible hardcoded secret: {bad}"
# stickies + config present
assert any(n["type"] == "n8n-nodes-base.stickyNote" for n in d["nodes"])
assert any(n["name"].startswith("CONFIG") for n in d["nodes"])
# status flow present
for s in ["RECEIVED", "CONFIRMED", "PENDING_SLOT", "CANCELLED", "RESCHEDULED", "REMINDER_SENT", "HANDLED"]:
    assert s in blob, f"missing status {s}"
# node types/versions check
from collections import Counter
print("node types:", dict(Counter((n["type"], n["typeVersion"]) for n in d["nodes"])))
print("validation OK: all", len(name_set), "nodes connected, no hardcoded secrets")
