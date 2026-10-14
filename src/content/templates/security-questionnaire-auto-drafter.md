---
title: "Security Questionnaire Auto-Drafter"
description: "AI drafts vendor security questionnaire answers from your own policy docs in n8n — confidence-scored, human-review gated, fully logged."
date: 2026-10-14
category: "automation"
difficulty: "intermediate"
workflow: "/templates/security-questionnaire-auto-drafter.json"
integrations: ["Google Sheets", "Google Docs", "OpenAI", "Telegram"]
---

## How it works

Enterprise security teams are drowning in vendor questionnaires — this workflow turns your approved policy docs into a drafting machine with a human in the loop, so high-confidence answers ship fast and shaky ones never go out unreviewed:

1. **STEP 1 — Trigger + config + read questions** — `Start Drafting` (a manual trigger, so it's safe to import; swap in a Google Drive trigger for full automation) fires, `CONFIG — Inputs` holds every editable value, and `Read Questions` pulls the questionnaire rows from your `Questions` tab.
2. **STEP 2 — Log every question as NEW** — `Log NEW` appends each question to the `Draft Log` tab with status `NEW`, creating the audit trail for the whole run.
3. **STEP 3 — Read knowledge base + loop** — `Read Knowledge Base` pulls your approved security-policy Google Doc as plain text, and `Loop Over Questions` processes the questions one at a time so every answer gets its own agent call.
4. **STEP 4 — AI drafts the answer** — `Prepare Question` shapes `{question, category, context, question_number, knowledge_text}`, then `Draft Answer Agent` (gpt-4o-mini with the `Answer Schema Parser`) drafts strictly from your knowledge text: it never invents certifications, and questions your docs don't cover get low confidence plus `needs_human`. `Mark DRAFTED` writes the draft, confidence, and source section back to the log row.
5. **STEP 5 — Confidence gate** — `Confidence Check` compares the score against your threshold: at or above → `Mark APPROVED`; below → `Mark IN_REVIEW` plus `Send Review Request` on Telegram with the question, the draft, its confidence, and its source section — reply `APPROVED #<n>` in Telegram to approve manually.
6. **STEP 6 — Run summary** — after the loop finishes, `Read Draft Log` re-reads the tab, `Build Run Summary` counts total / auto-approved / in-review, and `Final Telegram Notification` sends the summary.

**Status flow in Sheets:** `NEW` → `DRAFTED` → `APPROVED` (low-confidence answers go `DRAFTED` → `IN_REVIEW`)

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- An OpenAI API key — sign up at [platform.openai.com/signup](https://platform.openai.com/signup), then create a key under API keys
- A Google Workspace account — [workspace.google.com](https://workspace.google.com); connect Google Sheets + Google Docs OAuth2 credentials in n8n, and prepare one spreadsheet with two tabs (`Questions`, `Draft Log`) plus one Google Doc holding your approved security language (SOC 2 answers, policies, certifications)
- A Telegram bot — create one via [@BotFather](https://core.telegram.org/bots#botfather) (`/newbot`), and get your chat ID from [@userinfobot](https://t.me/userinfobot)

Your `Questions` tab needs these headers (copy-paste this row; `Context` is optional but improves drafts):

`Question # | Category | Question | Context`

Your `Draft Log` tab needs these headers (the workflow fills them; copy-paste this row):

`Timestamp | Question # | Category | Question | Draft Answer | Confidence | Source Doc | Status`

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `security-questionnaire-auto-drafter.json`.
2. **CONFIG — Inputs** — open the Set node and fill in:
   - `COMPANY_NAME` — your company name (appears in drafts)
   - `QUESTIONNAIRE_SHEET_ID` — the ID in your questionnaire spreadsheet's URL
   - `QUESTIONS_TAB` — tab holding the questions (default: `Questions`)
   - `KNOWLEDGE_DOC_ID` — the ID in your policy doc's URL (the doc the agent drafts from)
   - `CONFIDENCE_THRESHOLD` — auto-approve bar, 0–1 (default: `0.7`)
   - `LOG_SHEET_ID` — spreadsheet ID for the draft log (can be the same sheet)
   - `LOG_TAB` — log tab name (default: `Draft Log`)
   - `REVIEWER_CHAT_ID` — your Telegram chat ID for review requests and the final summary
3. **Select your credentials** — Google Sheets OAuth2 in `Read Questions`, `Log NEW`, `Mark DRAFTED`, `Mark APPROVED`, `Mark IN_REVIEW`, and `Read Draft Log`; Google Docs OAuth2 in `Read Knowledge Base`; OpenAI in `GPT-4o-mini Chat Model`; Telegram in `Send Review Request` and `Final Telegram Notification`.
4. **Load your data** — paste the questionnaire rows into the `Questions` tab (headers must match exactly), and make sure your knowledge doc contains your approved security answers.
5. **Run it** — click Execute on `Start Drafting`. Review `IN_REVIEW` rows in the Draft Log tab (or reply `APPROVED #<n>` in Telegram), then flip those rows to `APPROVED` in the sheet once a human signs off.

## Customize it

- **Stricter or looser gating** — raise `CONFIDENCE_THRESHOLD` to `0.9` when answers go to regulated customers; drop it to `0.5` for internal drafts where speed matters.
- **Fully automatic** — replace `Start Drafting` with a Google Drive Trigger watching the questionnaire sheet, so new questionnaires start drafting themselves.
- **Per-framework knowledge** — split the knowledge doc by framework (SOC 2, ISO 27001, GDPR) and add a routing step on `Category` so each question pulls the right doc.
- **Policy-gap radar** — answers with `needs_human=true` reveal holes in your docs; log them to a separate tab and treat recurring gaps as policies to write.
- **Brand-voice pass** — add a second agent after `Mark APPROVED` that rewrites approved answers in your company's tone before export.
- **Feedback loop** — append human-edited answers back into the knowledge doc so every review makes the next draft stronger.
