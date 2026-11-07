---
title: "Invoice Auto-Pay Guardian — 3-Way Match, Caps & Audit Trail"
description: "Auto-pay supplier invoices only on an exact 3-way match — invoice vs PO vs receiving — with caps, dedupe, a kill-switch and a full audit trail."
date: 2026-11-07
category: "automation"
difficulty: "advanced"
workflow: "/templates/invoice-auto-pay-guardian.json"
integrations: ["Gmail", "Google Sheets", "OpenAI", "Telegram", "HTTP Request"]
---

## How it works

Most teams either pay every invoice by hand (slow) or let a workflow pay anything that arrives (dangerous). This template draws the line the n8n community converged on: **match-then-release with guardrails**. Money moves only when the invoice, the purchase order, and the receiving record agree line by line — and only inside hard caps.

1. **STEP 1 — Invoice intake** — a Gmail Trigger watches for emails with `subject:invoice` and an attachment. The PDF is downloaded, its text extracted, and a Code node parses the invoice number, supplier, PO number, amount, currency, due date, and bank account last-4.
2. **STEP 2 — Log, dedupe + kill-switch** — the invoice is appended to the `PayablesLog` sheet as `RECEIVED`. The workflow then reads the whole log: if the same invoice number + supplier is already there, it's a duplicate. If any row is `BLOCKED`, or a `PAID` row has lost its settlement status, the **kill-switch** fires — the invoice is marked `BLOCKED`, a Telegram alert goes out, and autopay pauses until you clear the log. Nothing is paid.
3. **STEP 3 — Supplier check** — the supplier is looked up in the `Suppliers` allowlist. A new supplier, a supplier marked blocked, or bank details that changed since the stored record (last-4 mismatch) all route the invoice to the `REVIEW` queue. This is the single most important fraud control in the workflow: changed bank details never auto-pay.
4. **STEP 4 — 3-way match (AI)** — an AI Agent (gpt-4o-mini + Structured Output Parser) compares the invoice against the `PurchaseOrders` and `Receiving` sheets line by line — flagging short quantities, substitutions, price changes, missing lines, and credit memos — and returns a structured verdict (`EXACT_MATCH` / `PARTIAL_MATCH` / `MISMATCH`) with per-line evidence quotes.
5. **STEP 5 — Caps & approval gate** — the invoice is auto-approved **only** when the match is exact, the supplier is known, the amount is at or under your per-payment cap, and today's paid + approved total stays under your daily cap. Anything else goes to the `REVIEW` queue with a Telegram message and an approve/reject form. A human approval sends the invoice straight into the payment step; a rejection marks it `REJECTED`.
6. **STEP 6 — Payment + audit** — the payment is released via HTTP Request to your payment provider with an `Idempotency-Key` header built from the invoice number, supplier, and amount — so a retried execution can never pay the same invoice twice. The workflow verifies the settlement response, then updates the log to `PAID` (or `QUEUED_FOR_PAYMENT` with `UNSETTLED` if settlement can't be confirmed — which trips the kill-switch next run) with the payment reference and policy version. A Telegram summary closes the run.
7. **STEP 7 — Review queue & alerts** — review items, blocked duplicates, and paid batches each get their own Telegram message, so finance always knows what was paid, what is waiting, and what was stopped.

**Status flow in Sheets:** `RECEIVED` → `MATCHING` → `APPROVED` → `QUEUED_FOR_PAYMENT` → `PAID` / `REVIEW` / `BLOCKED` / `REJECTED`

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- A Gmail account that receives supplier invoices — n8n Credentials → Gmail OAuth2
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- A payment provider with API access — e.g. [Stripe](https://stripe.com) (use **test mode** first) or [Wise](https://wise.com) — you need an API key and the provider's base URL

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `invoice-auto-pay-guardian.json`.
2. **CONFIG — Policy & Caps** — open the Set node and fill in:
   - `per_payment_cap` — max auto-payable amount per invoice (default `5000`)
   - `daily_cap` — max total auto-paid per day (default `20000`)
   - `currency` — e.g. `USD`
   - `policy_version` — bump this (`v1.2` → `v1.3`) whenever you change a rule, so the audit trail shows which policy paid each invoice
   - `spreadsheet_id` — paste your Google Sheet ID
   - `payment_provider_base_url` — e.g. `https://api.stripe.com` (no trailing slash)
   - `payment_api_key` — paste your provider API key (**test-mode key first**)
   - `telegram_chat_id` — paste your Telegram chat ID
   - `finance_email` — your finance inbox, for reference in review messages
3. **Create the Google Sheet** — one spreadsheet with four tabs and these exact headers:
   - `PayablesLog` — `Date Received | Invoice Number | Supplier | PO Number | Amount | Currency | Due Date | Status | Idempotency Key | Payment Reference | Settlement Status | Review Reason | Match Verdict | Policy Version`
   - `Suppliers` — `Supplier | Bank Account Last 4 | Bank Details Hash | Status` (add your trusted suppliers here; `Status` = `active` or `blocked`)
   - `PurchaseOrders` — `PO Number | Supplier | Line Description | Quantity | Unit Price | Line Total | Status`
   - `Receiving` — `PO Number | Line Description | Quantity Received | Received Date | Received By`
   Then select your Google Sheets credential in every Sheets node (the spreadsheet is picked by the `spreadsheet_id` in the CONFIG node — select the same sheet in each node).
4. **Credentials** — select your Gmail credential in `Gmail Trigger: Invoice Email` and `Gmail: Download Attachment`; your OpenAI credential in `OpenAI Chat Model — 3-Way Match`; your Telegram credential in the three Telegram nodes.
5. **Test before you activate** — send yourself a test invoice email (subject contains `invoice`, PDF attached) with an amount **above** your per-payment cap: it must land in `REVIEW`, never in `PAID`. Then send one that matches a PO + receiving record exactly and is under the cap: it should pay (in test mode) and log `PAID` with a payment reference. Only switch the provider key to live mode after both tests pass.
6. **Activate** the workflow. The Gmail Trigger polls every minute.

## Customize it

- **Lower the caps to start** — `per_payment_cap: 500` and `daily_cap: 2000` for the first month, then raise them once you trust the match verdicts. The caps are the cheapest insurance in the whole workflow.
- **Stricter matching** — the AI agent only recommends `AUTO_APPROVE` on a perfect line-by-line match; if your POs use different units or descriptions than invoices, add a normalization step in `Code — Normalize Invoice Fields` (e.g. strip units, lowercase descriptions) before the agent sees them.
- **Partial matches** — today a `PARTIAL_MATCH` goes to review. If you trust small variances, add an IF branch that auto-approves when `total_variance` is within a tolerance you set in the CONFIG node (`match_tolerance_percent`).
- **Approval via Slack or email instead of Telegram** — swap the `Telegram — Review Request` node for a Slack or Gmail node; the `Wait — Human Approval` form works the same way, and the approval link in the message is `{{ $execution.resumeUrl }}`.
- **Reconciliation** — add a scheduled run that pulls your bank statement and compares it against `PayablesLog` rows with `Settlement Status = SETTLED`; any `PAID` row that never appears on the statement should flip the kill-switch. (Our [Daily Reconciliation Monitor](/templates/daily-reconciliation-monitor/) covers the statement side of this.)
- **Never auto-pay these** — new suppliers and changed bank details are hard-routed to review by design. If you ever feel tempted to relax that rule, don't: it is the one control that stops the most common invoice fraud (a spoofed invoice with the attacker's bank details).
- **Multi-currency** — the workflow records the invoice currency and passes it to the provider, but the caps are compared in one currency. If you pay in several currencies, add a conversion step before `Code — Build Match Decision` or keep separate caps per currency.
