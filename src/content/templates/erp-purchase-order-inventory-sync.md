---
title: "ERP Purchase Order & Inventory Sync Automator"
description: "Pulls purchase orders from your ERP API daily → AI flags anomalies → Telegram approval for big orders → syncs inventory in Sheets."
date: 2026-11-09
category: "automation"
difficulty: "intermediate"
workflow: "/templates/erp-purchase-order-inventory-sync.json"
integrations: ["ERP REST API", "OpenAI", "Google Sheets", "Telegram"]
---

## How it works

Your ERP's purchase orders, reviewed and synced every morning — no more copy-pasting POs between systems or discovering stock-outs too late:

1. **STEP 1 — Pull purchase orders from the ERP API** — a daily 9 AM schedule trigger fires an HTTP GET on your ERP's purchase-orders endpoint (paginated with `page` + `per_page`), then normalizes every PO into PO number, supplier, total, currency, order date, and line items (SKU, description, quantity, unit price).
2. **STEP 2 — Dedupe + log to Google Sheets** — the workflow reads the PO numbers already in your sheet, keeps only genuinely new POs, and appends them with status `NEW`. Re-runs are idempotent by PO number, so a PO is never processed twice.
3. **STEP 3 — AI anomaly review** — an AI Agent reviews each PO and returns a structured verdict via a Structured Output Parser: a risk flag, a risk level (`LOW` / `MEDIUM` / `HIGH`), the reasons, and a one-line plain-English summary. It catches unusual suppliers, prices far above typical, duplicate line items, and missing fields.
4. **STEP 4 — Approval routing** — a PO needs human approval when its total is at or above your threshold (default 5,000) OR the AI flagged it. Those POs flip to `PENDING_APPROVAL` and you get a Telegram "Send and Wait" message with the PO summary and Approve / Reject buttons. Approve writes the decision back to your ERP API (PATCH) and flips the sheet to `APPROVED`; Reject flips it to `REJECTED` and stops that PO cleanly — rejected POs never touch inventory. Low-risk POs auto-approve and skip straight to `APPROVED`.
5. **STEP 5 — Inventory sync + low-stock alerts** — approved POs are split into line items and the Inventory sheet is updated per SKU (Quantity On Order, last PO number, sync date); the PO flips to `SYNCED`. The workflow then reads the whole Inventory sheet and flags any SKU whose Quantity On Hand is below its Reorder Level, sending you a Telegram low-stock alert listing exactly what to reorder.
6. **STEP 6 — Run summary** — both sync branches merge into one Telegram message: how many POs were pulled, how many were new, how many the AI flagged, how many were rejected, and how many items sit below their reorder level.

**Status flow in Sheets:** `NEW` → `PENDING_APPROVAL` → `APPROVED` / `REJECTED` → `SYNCED` (low-risk POs go `NEW` → `APPROVED` → `SYNCED`)

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- An ERP with a REST API that exposes purchase orders — e.g. [Odoo](https://www.odoo.com) (Purchase app + API), [ERPNext](https://erpnext.com) (REST API for Purchase Orders), or any custom ERP with a `GET /purchase-orders` endpoint
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `erp-purchase-order-inventory-sync.json`.
2. **CONFIG — ERP API** — open the Set node and fill in:
   - `erp_api_base_url` — e.g. `https://your-erp.example.com`
   - `erp_api_key` — paste your ERP API key or token
   - `po_endpoint` — the path to the purchase-orders endpoint (default `/api/v1/purchase-orders`; Odoo uses `/api/v2/purchase.order`, ERPNext uses `/api/resource/Purchase Order` — adjust the `Fetch Purchase Orders — ERP API` node's query params to match)
   - `page_size` — how many POs to pull per run (start with 50)
3. **CONFIG — Google Sheets** — create a Google Sheet with two tabs. Tab `Purchase Orders` with headers: `PO Number | Order Date | Supplier | Total Amount | Currency | Status | Risk Flag | AI Summary`. Tab `Inventory` with headers: `SKU | Item Name | Quantity On Hand | Quantity On Order | Reorder Level | Last PO Number | Last Sync Date`. Paste the spreadsheet ID into `spreadsheet_id`. Then select your Google Sheets credential in every Google Sheets node (Read Seen PO Numbers, Log New POs — Status NEW, the four status-update nodes, Update Inventory — Sync Quantities, Read Inventory Levels).
4. **CONFIG — AI Review** — set `approval_threshold` (5,000 is the default — POs at or above this need your approval) and `openai_model` (`gpt-4o-mini`). Select your OpenAI credential in the `OpenAI Chat Model — PO Review` node.
5. **Telegram approval + notifications** — select your Telegram credential in the three Telegram nodes (`Telegram — Send and Wait for Approval`, `Telegram — Low Stock Alert`, `Telegram — Send Summary`), then paste your Telegram chat ID into `CONFIG — Notifications` → `telegram_chat_id`.
6. **Activate** — flip the workflow Active. It runs daily at 9 AM; use Execute Workflow to test it once first and check the sheet before leaving it on a schedule.

**Pagination note:** the `Fetch Purchase Orders — ERP API` node fetches page 1 with `per_page` from your config. If your ERP returns more POs than one page, wrap the fetch + normalize pair in a Loop (Split in Batches) node that increments `page` until the response has no `next_page` / returns fewer than `per_page` rows — or point the endpoint at a "changed since yesterday" filter if your ERP supports one, which is the cleaner option for a daily sync.

**Approval note:** the `Telegram — Send and Wait for Approval` node pauses the workflow until you tap Approve or Reject. It needs a recent n8n version with the Telegram "Send and Wait" operation, and the workflow must stay Active while an approval is pending — don't deactivate it mid-approval or the wait is lost (the PO stays `PENDING_APPROVAL` in the sheet and is picked up again on the next run only if you clear its status back to `NEW`).

## Customize it

- **Different approval rule** — lower `approval_threshold` to 1,000 for tighter control, or raise it to 25,000 if only very large orders need you. Add a second condition in `IF — Needs Approval` to always require approval for a specific supplier (e.g. a new vendor on probation).
- **Email the supplier on approval** — add a Gmail/SMTP node after `Update Sheet — Status APPROVED` to send the PO confirmation to the supplier automatically.
- **Auto-create reorder POs** — extend `Flag Low Stock Items` with an HTTP POST that drafts a new purchase order in your ERP for each low-stock SKU instead of just alerting.
- **Multi-currency** — the sheet logs `Currency` per PO; add a conversion step (e.g. an ExchangeRate-API call in `Normalize Purchase Orders`) if you want every total normalized to one currency before the threshold check.
- **Hourly instead of daily** — change the Schedule Trigger interval; the dedupe logic keeps it safe at any cadence, and approvals still wait for you in Telegram.
- **No AI review?** — delete the `AI Agent — Review Purchase Order` and its two sub-nodes, and change `IF — Needs Approval` to a single amount condition. The threshold-only flow still works.
- **Slack instead of Telegram** — swap the three Telegram nodes for Slack nodes; the approval step needs Slack's "Send and Wait" equivalent, or replace it with a plain Slack message plus a manual sheet edit (set Status to `APPROVED` by hand and let a second scheduled workflow pick approved rows up for sync).
