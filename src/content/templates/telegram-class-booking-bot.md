---
title: "Telegram Class Booking Bot for Fitness Studios"
description: "Telegram AI bot for fitness studios: view class schedules, book/reschedule/cancel classes with a double-booking guard, plus daily reminders."
date: 2026-11-14
category: "automation"
difficulty: "intermediate"
workflow: "/templates/telegram-class-booking-bot.json"
integrations: ["Telegram", "OpenAI", "Google Sheets"]
---

## How it works

Your AI receptionist on Telegram for a fitness studio, running two independent flows in one workflow. Built for the exact use case fitness-studio owners keep asking for on the [n8n forum](https://community.n8n.io/t/looking-for-an-n8n-telegram-bot-workflow-for-class-scheduling-booking/328331) — view class schedules and available slots, book/reschedule/cancel classes, multiple training rooms, no double bookings, notifications and reminders, and role-based access for admins and trainers.

1. **STEP 1 — Telegram trigger + CONFIG + role check + AI intent** — every incoming Telegram message fires the workflow, gets logged to Google Sheets with status `RECEIVED`, and the sender's Telegram user ID is looked up in the Staff tab. Staff (admin/trainer roles) go to the admin branch (step 4); everyone else goes to an AI Agent, which classifies the intent (`view_schedule` / `book` / `reschedule` / `cancel` / `other`) through a Structured Output Parser, extracting the class name, date, time, room, member name, and phone. A Switch routes the conversation by intent.
2. **STEP 2 — Switch routes by intent** — for `view_schedule`, the workflow reads the Classes timetable and replies on Telegram with the upcoming classes, rooms, trainers, and free spots. For `cancel`, it finds the member's upcoming booking by Telegram chat ID and marks it `CANCELLED`. For `reschedule`, it finds the existing booking, marks the old row `CANCELLED`, then runs the same slot check as a new booking and confirms it as `RESCHEDULED`. For `other`, a fallback reply lists the SCHEDULE / BOOK / RESCHEDULE / CANCEL commands and the sheet flips to `HANDLED`.
3. **STEP 3 — Double-booking guard + confirm** — for `book` (and the new slot in `reschedule`), the workflow reads the Classes timetable and the Bookings ledger, and a Code node checks for an overlapping CONFIRMED booking on the same date + time using the SAME room or the SAME trainer — so neither a room nor a trainer can be double-booked. It also enforces capacity (`Booked < Capacity`). If the slot is free: the booking is appended with status `CONFIRMED` and the member gets a Telegram confirmation with class, room, and time. If busy or full: three alternative slots for the same class are computed and suggested on Telegram, and the sheet flips to `PENDING_SLOT`. If the AI couldn't parse a class, date, or time, Telegram asks the member for the missing detail instead of guessing.
4. **STEP 4 — Admin branch (staff only)** — staff send `/addclass Class | Day | Time | Room | Trainer | Capacity` to append a class to the timetable, or `/cancelclass Class | Day | Time` to mark a class `CANCELLED`. Any other staff message gets the admin help reply with the command formats. Only Telegram user IDs listed in the Staff tab reach this branch.
5. **STEP 5 — Daily 8 AM reminder sweep** — every morning at 8 AM the workflow reads the Bookings tab, keeps CONFIRMED bookings in the next 24 hours whose Reminder Sent is empty, sends each member a Telegram reminder, flips the sheet to `REMINDER_SENT` with Reminder Sent = YES, and sends you a Telegram digest summarizing the reminders sent.
6. **STEP 6 — Sheets logging + Telegram digests** — every booking branch merges into one booking summary sent to Telegram, and the reminder sweep builds its own digest. Both read the chat ID from a single CONFIG node.

**Status flow (Bookings tab):** `RECEIVED` → `CONFIRMED` / `PENDING_SLOT` / `CANCELLED` / `RESCHEDULED` / `REMINDER_SENT` / `HANDLED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your admin chat ID from [@userinfobot](https://t.me/userinfobot)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `telegram-class-booking-bot.json`.
2. **CONFIG — Studio** — open the Set node and fill in:
   - `studio_name` — e.g. `IronWorks Fitness Studio`
   - `spreadsheet_id` — paste your Google Sheet ID
   - `admin_chat_id` — your Telegram chat ID (admin digests go here)
   - `timezone` — e.g. `Asia/Calcutta`
   - `reminder_hours` — `24` by default (how far ahead the reminder sweep looks)
   - The `classes_sheet`, `bookings_sheet`, and `staff_sheet` values (`Classes`, `Bookings`, `Staff`) only need changing if you rename the tabs.
3. **Google Sheets tabs** — in that spreadsheet create three tabs with these exact headers:
   - `Classes`: `Class | Day | Time | Room | Trainer | Capacity | Booked | Status`
   - `Bookings`: `Date | Chat ID | Customer Name | Phone | Message | Class | Class Date | Class Time | Room | Trainer | Intent | Status | Reminder Sent`
   - `Staff`: `Telegram User ID | Name | Role`
   - Select your Google Sheets credential in every Sheets node. Seed the `Classes` tab with your timetable — `Day` is a weekday (`Mon`…`Sun`) or an exact date (`YYYY-MM-DD`), `Time` is 24-hour `HH:MM`, `Status` is `ACTIVE`. Add your own Telegram user ID to `Staff` with role `admin` (get it from [@userinfobot](https://t.me/userinfobot)).
4. **Telegram trigger + replies** — select your Telegram credential in the "Telegram Trigger" node and in every "Telegram — …" node. The bot replies in the member's own chat automatically; no chat ID to configure per reply.
5. **AI intent parsing** — select your OpenAI credential in the "OpenAI Chat Model — Intent" node (model is `gpt-4o-mini` by default). No prompt editing needed — the agent reads the studio name and timezone from CONFIG — Studio.
6. **CONFIG — Reminders** — this second CONFIG node powers the 8 AM reminder sweep independently: fill in the same `studio_name` and `spreadsheet_id`, plus `admin_chat_id` (where the reminder digest goes) and `reminder_hours`. Select your Google Sheets credential in "Read Bookings — Reminders" and "Update Sheet — REMINDER_SENT".
7. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in both digest nodes ("Telegram — Booking Activity Digest" and "Telegram — Send Reminder Digest"), and **activate** the workflow. Send a test Telegram message to your bot ("What classes are on tomorrow?") and watch the execution flow.

## Customize it

- **Class length** — the slot guard compares exact date + time, so any class length works as long as every class in the timetable uses the same start-time grid. For back-to-back classes in the same room, add a buffer by treating the time as a start time plus your class length inside "Code — Check Slot & Find Alternatives" (search for the `hasClash` check).
- **Track booked counts** — the timetable's `Booked` column is read for the capacity check but not auto-incremented. Add a Google Sheets update in the book branch that increments `Booked` for the matched class row, or maintain it from your front-desk process.
- **Reminder timing** — change `reminder_hours` in CONFIG — Reminders to `48` for two-day-ahead reminders, or change the "Daily 8AM Trigger" to 6 PM for evening reminders.
- **Payments / deposits** — add a step after "Append Booking — CONFIRMED" that sends a payment link (e.g. Razorpay/Stripe) and flips the booking to `CONFIRMED` only after payment succeeds; until then keep it `PENDING_SLOT`.
- **High-concurrency upgrade (Postgres)** — Google Sheets is the ledger here so any small studio can import the template with no database server. If two members book the same slot at the same second, Sheets can't guarantee atomicity. For a busy studio, swap the Bookings reads/writes for Postgres and add an exclusion constraint on `(room, tstzrange(start_time, end_time))` (and one on `(trainer, tstzrange(...))`) — the database then rejects overlapping bookings outright, and the Code node only needs to catch that error and suggest alternatives. The n8n forum consensus recommends exactly this upgrade path.
- **More staff commands** — extend "Switch — Admin Command" with a `/listbookings` rule that reads the Bookings tab and replies with today's confirmed classes, using "Code — Build Schedule Reply" as the template.
- **Waitlist** — when a class is full (`class_full`), append the member to a `Waitlist` tab instead of only suggesting alternatives, and notify them first when a cancellation frees a spot.
