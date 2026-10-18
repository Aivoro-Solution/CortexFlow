---
title: "AI RFQ-to-Quote Automator"
description: "Upload an RFQ PDF → AI extracts line items → matches them against your catalogue and approved price list → quote draft + review queue."
date: 2026-10-18
category: "automation"
difficulty: "intermediate"
workflow: "/templates/rfq-to-quote-automator.json"
integrations: ["Google Sheets", "OpenAI", "Telegram", "SMTP Email", "n8n Form Trigger"]
---

## How it works

A complete RFQ-to-quotation pipeline for distributors, wholesalers, and trading companies that receive customer quotation requests as PDFs:

1. **STEP 1 — RFQ intake** — a customer (or your sales team) opens the n8n form, uploads the RFQ PDF, and fills in the customer name. The Extract from File node pulls the PDF text, `Prepare RFQ Record` generates an `RFQ-YYYYMMDD-XXXX` reference, and `Log RFQ — Status NEW` appends a row to the RFQ Log sheet.
2. **STEP 2 — AI line-item extraction** — the `AI Agent — Extract Line Items` (gpt-4o-mini with a Structured Output Parser) reads the PDF text and returns every line item as structured data: product code, description, quantity, unit. The RFQ Log flips to `EXTRACTED`.
3. **STEP 3 — Catalogue + price matching** — the workflow reads your **Catalogue** and **Price List** sheets, then `Match Lines Against Catalogue` scores each line: an exact product-code match scores 1.0, a normalized description match scores 0.8. Prices are taken **only** from the approved price list — never from the AI. Unknown codes, missing prices, missing units, or low-confidence matches are flagged `REVIEW` and never auto-substituted. Matched lines land in the **Quote Draft** sheet; flagged lines land in the **Review Queue** sheet. The RFQ Log flips to `MATCHED`.
4. **STEP 4 — Review alert or quote email** — if any lines need review, `Telegram — Review Alert` lists every flagged line with its issue (`UNKNOWN_CODE`, `NO_APPROVED_PRICE`, `UNIT_MISSING`, `LOW_CONFIDENCE`). If everything matched, `Email — Send Quote Draft` sends the reviewer an HTML quote table with line totals and the quote total. Both branches merge back together.
5. **STEP 5 — Final log + summary** — the RFQ Log gets its final status (`QUOTED` → `SENT`, or `REVIEW_NEEDED`), and `Telegram — Send Summary` sends you the totals: lines, matched, review count, quote total.

**Status flow in Sheets:** `NEW` → `EXTRACTED` → `MATCHED` → `QUOTED` / `REVIEW_NEEDED` → `SENT`

**Hard rules (from real buyer demand):** prices come only from the approved price list, and product substitutions always require human approval — the workflow never invents or swaps a product on its own. When a customer asks for an Excel quotation, open the **Quote Draft** sheet and use File → Download → Microsoft Excel (.xlsx) — one click, no extra nodes needed.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- SMTP credentials — any provider (Gmail app password, SendGrid, your host); n8n Credentials → SMTP

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `rfq-to-quote-automator.json`.
2. **Create the spreadsheet** — make one Google Sheet with these 5 tabs and exact headers:
   - `Catalogue`: `product_code | description | category`
   - `PriceList`: `product_code | unit_price | currency | price_version`
   - `RFQ Log`: `rfq_reference | customer_name | received_at | stage | line_count | matched_count | review_count | quote_total | currency | status | notes`
   - `Quote Draft`: `rfq_reference | line_no | code | matched_code | description | quantity | unit | unit_price | line_total | currency | confidence | status`
   - `Review Queue`: `rfq_reference | line_no | code | description | quantity | unit | issue | confidence`
3. **CONFIG — RFQ Settings** — open the Set node and fill in:
   - `spreadsheet_id` — paste your spreadsheet ID
   - `company_name`, `currency` (e.g. `USD`, `INR`), `confidence_threshold` (`0.8` is a good start), `reviewer_email` — who receives the quote draft email
   - Tab names only if you renamed them from the defaults above
   - Then select your Google Sheets credential in all six Google Sheets nodes (`Log RFQ — Status NEW`, `Update RFQ Log — Status EXTRACTED`, `Read Catalogue`, `Read Price List`, `Append Review Queue`, `Append Quote Draft`, `Update RFQ Log — Status MATCHED`, `Update RFQ Log — Final Status`)
4. **AI extraction** — select your OpenAI credential in `OpenAI Chat Model — Extraction` (model is `gpt-4o-mini` by default).
5. **Quote email** — select your SMTP credential in `Email — Send Quote Draft`. The recipient and sender both come from `reviewer_email` in the config.
6. **CONFIG — Notifications** — paste your Telegram chat ID, select your Telegram credential in `Telegram — Review Alert` and `Telegram — Send Summary`, then **activate** the workflow and open the form URL from `RFQ Intake — Form Trigger` to test with a real RFQ PDF.

## Customize it

- **Stricter matching** — raise `confidence_threshold` to `1.0` and only exact product-code matches will auto-quote; everything else goes to human review.
- **Price versions** — the matcher uses the first price row per product code. Keep an `active` price version at the top of your PriceList tab, or sort by `price_version` descending so the newest price wins.
- **Units enforcement** — add a `unit` column to your Catalogue and extend the match code to flag unit mismatches (e.g. RFQ says "boxes", catalogue sells "pcs").
- **Approval before sending** — insert an n8n Wait node (approval) between `Build Quote Email` and `Email — Send Quote Draft` so a human signs off before the quote goes out.
- **Multi-currency RFQs** — add a currency column to the PriceList and match on `(product_code, currency)` instead of code alone.
- **Push to your ERP/CRM** — after `Merge — Combine Notify Branches`, add an HTTP Request node posting the quote draft rows to your ERP's sales-quotation endpoint.
- **Customer portal** — the Form Trigger URL is shareable: send it to repeat customers so RFQs arrive structured instead of as email attachments.
