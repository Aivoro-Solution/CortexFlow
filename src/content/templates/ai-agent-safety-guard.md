---
title: "AI Agent Safety Guard — Idempotency, Budget Caps & Kill Switch"
description: "Guard every AI-agent action before it fires: idempotency keys, monthly budget caps, rate limits, a kill switch, and an AI risk review."
date: 2026-11-10
category: "automation"
difficulty: "advanced"
workflow: "/templates/ai-agent-safety-guard.json"
integrations: ["Webhook", "Google Sheets", "OpenAI", "Telegram", "HTTP Request", "Code"]
---

## How it works

AI agents are only as safe as the last action they took unsupervised. The failure stories are always the same: a retry re-sent an email that already went out, a runaway loop burned through an API budget overnight, or an automation fired 83 tickets while its owner slept. This template is the guard that stands **in front of** every outbound action — a reusable sub-workflow your other workflows and agents call *before* they send an email, create a charge, book something, or open a ticket.

1. **STEP 1 — Receive the action request** — another workflow calls the webhook (`POST /guard-action`) with a JSON request: `client_id`, `action_type`, `recipient`, `payload`, and `estimated_tokens`. The `CONFIG — Guard Policy` node holds every editable value, and `Code — Normalize Request & Idempotency Key` builds a SHA-256 idempotency key from client + action type + recipient + payload. The same action always produces the same key — so a retry can never execute twice.
2. **STEP 2 — Log + read the ledger** — the request is appended to the `Guard Ledger` Google Sheet as `NEW`, then the whole ledger is read back so the guard checks can see every past decision for this client.
3. **STEP 3 — Four guard checks** — `Code — Check Guard Rules` runs all four, in this order:
   - **Kill switch** — if `kill_switch_enabled` is `true` in CONFIG, everything is blocked instantly (`BLOCKED_KILLSWITCH`).
   - **Idempotency** — if the same key already appears in the ledger (the `NEW` row we just wrote counts once; two or more rows means a replay), the action is blocked as `BLOCKED_DUPLICATE`.
   - **Monthly budget** — the estimated cost (`estimated_tokens` × the per-1k-token rate in CONFIG) is added to this client's spend so far this month (summed from `cost_usd` in the ledger). If it would exceed `monthly_budget_usd`, the action is blocked as `BLOCKED_BUDGET`.
   - **Hourly rate cap** — if this client already ran `max_actions_per_hour` actions in the last hour, the action is blocked as `BLOCKED_RATE`.
   
   Any hit blocks the action immediately — nothing executes, the ledger is updated with the `BLOCKED_*` status, the caller gets `{ "allowed": false }`, and Telegram is alerted.
4. **STEP 4 — AI risk review** — if all four checks pass, an AI Agent (gpt-4o-mini + Structured Output Parser) reviews the action — its type, recipient, payload, cost, and recent activity — and returns a structured verdict (`allow` / `block`, a reason, and a `risk_score` from 0–100). The agent blocks spam, mass sends, duplicates, unapproved charges, and messages to the wrong audience. If the verdict is `block`, or the risk score is at/above `risk_block_threshold` (default 70), the action is blocked as `BLOCKED_AGENT`.
5. **STEP 5 — Execute + log + reply** — allowed actions execute through one generic HTTP Request to your `target_endpoint_url`, with the idempotency key sent as an `Idempotency-Key` header so the target can dedupe too. `Code — Verify Execution` checks the target actually confirmed success — a non-confirming response is `FAILED`, never silently marked done. The ledger flips to `DONE` (or `FAILED`), the webhook replies `{ "allowed": true, "status": "DONE", ... }`, and a Telegram summary closes the run.
6. **STEP 6 — Blocked paths** — every blocked decision, whichever check stopped it, follows the same path: ledger updated with its `BLOCKED_*` status, `{ "allowed": false }` returned to the caller, and a Telegram alert. Nothing executes on a blocked path.

**Status flow in Sheets:** `NEW` → `PROCESSING` → `DONE` / `BLOCKED_DUPLICATE` / `BLOCKED_BUDGET` / `BLOCKED_RATE` / `BLOCKED_KILLSWITCH` / `BLOCKED_AGENT` / `FAILED`

**How to call it from another workflow** — add an HTTP Request node (POST) to this workflow's webhook URL (n8n shows it on the `Webhook — Guard Request` node; in production it ends in `/webhook/guard-action`) with this JSON body:

```json
{
  "client_id": "acme",
  "action_type": "send_email",
  "recipient": "customer@example.com",
  "payload": { "subject": "Your invoice is ready", "body": "Hi — your invoice #1042 is attached." },
  "estimated_tokens": 1200
}
```

The webhook replies with `{"allowed": true/false, "status": "DONE" | "BLOCKED_*", "idempotency_key": "...", "decision_reason": "...", "provider_ref": "..."}`. Your calling workflow should only treat the action as done when `allowed` is `true` — on `false`, do nothing and let the guard's Telegram alert tell you why.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) — [n8n.io](https://n8n.io)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) → API keys
- Google Sheets OAuth2 credentials — n8n Credentials → Google Sheets OAuth2
- A Telegram bot — message [@BotFather](https://t.me/BotFather), send `/newbot`, copy the token; get your chat ID from [@userinfobot](https://t.me/userinfobot)
- A target endpoint that performs the action — your own API, another n8n workflow's webhook, or a service webhook. The endpoint must accept a POST with `{ action_type, recipient, payload, idempotency_key }` and return a JSON success response (e.g. `{ "ok": true, "id": "..." }`).

Steps:

1. **Import the workflow** — in n8n, Workflows → Import from File → select `ai-agent-safety-guard.json`.
2. **CONFIG — Guard Policy** — open the Set node and fill in:
   - `monthly_budget_usd` — max LLM/action spend per client per month (default `100`)
   - `max_actions_per_hour` — max guarded actions per client per hour (default `20`)
   - `kill_switch_enabled` — `false` normally; set to `true` to block everything instantly (see below)
   - `cost_per_1k_tokens_usd` — your model's price per 1,000 tokens (default `0.0006`, the gpt-4o-mini input rate — update it if you change models or want output-token pricing)
   - `guard_sheet_id` — paste your Google Sheet ID (for reference; select the same sheet in every Sheets node)
   - `ledger_sheet` — `Guard Ledger` (the tab name)
   - `telegram_chat_id` — paste your Telegram chat ID
   - `target_endpoint_url` — the URL that actually performs the action (e.g. your email-sending API)
   - `target_api_key` — the API key for that endpoint (**never** a live production key until you have tested)
   - `openai_model` — `gpt-4o-mini`
   - `risk_block_threshold` — risk score at/above which the AI verdict blocks (default `70`)
3. **Create the Google Sheet** — one spreadsheet with a tab named `Guard Ledger` and these exact headers:
   - `timestamp | idempotency_key | client_id | action_type | recipient | status | cost_usd | decision_reason | provider_ref`
   
   Then select your Google Sheets credential in every Sheets node (the spreadsheet is picked by the `guard_sheet_id` in the CONFIG node — select the same sheet in each node).
4. **Credentials** — select your OpenAI credential in `OpenAI Chat Model — Risk Review` and your Telegram credential in `Telegram — Guard Decision Summary` and `Telegram — Guard Blocked Alert`. Leave the credential selects empty in the template until you add your own — never paste keys into node parameters.
5. **Test before you activate** — call the webhook twice with the *identical* payload: the first call should execute (`DONE`), the second must come back `BLOCKED_DUPLICATE` and execute nothing. Then set `kill_switch_enabled` to `true` and call again: it must return `BLOCKED_KILLSWITCH`. Then set `monthly_budget_usd` to `0.0001` and call again: it must return `BLOCKED_BUDGET`. Only after all three tests pass should you point a real workflow at it.
6. **Activate** the workflow, then point your other workflows at its webhook URL. Use the **production** webhook URL (not the test URL) for callers.

## Customize it

- **The kill switch is the whole point in an incident** — if an agent starts misbehaving, set `kill_switch_enabled` to `true` in the CONFIG node and save. Every call is blocked from that second, with the reason logged in the ledger. Fix the caller, then flip it back to `false`. For a faster switch, move the flag into a `Guard Config` sheet and have `Code — Check Guard Rules` read it instead — then you can kill it from your phone by editing a cell.
- **Start with a tiny budget** — `monthly_budget_usd: 5` and `max_actions_per_hour: 5` for the first week. A guard you have never seen block anything is a guard you have not tested. Raise the caps once you trust the verdicts.
- **Per-client budgets** — today one budget applies to every client. If one client needs a bigger cap, add a `Budgets` sheet (`client_id | monthly_budget_usd | max_actions_per_hour`) and have `Code — Check Guard Rules` look the client up before falling back to the CONFIG defaults.
- **Real cost, not estimated cost** — the budget check uses `estimated_tokens` from the caller. If your caller knows the real token count after the LLM call, have it call the guard a second time (or update the ledger row) with the actual count — the estimate is a guardrail, not an invoice.
- **Stricter AI review** — lower `risk_block_threshold` to `50` if the actions are high-stakes (payments, customer-facing messages). Raise it toward `85` only for low-stakes internal actions. You can also extend the agent's system message with your own blocklist (e.g. "never allow sends to more than 10 recipients at once").
- **More action types** — the guard is action-agnostic: `send_email`, `send_slack_message`, `create_charge`, `create_booking`, `open_ticket` all work the same way, because the idempotency key and the AI review only look at the client, type, recipient, and payload. Add new types by teaching your *target endpoint* to handle them — the guard itself needs no changes.
- **Alerting beyond Telegram** — the two Telegram nodes are the only notification step. Swap `Telegram — Guard Blocked Alert` for a Slack or PagerDuty node if a blocked payment or a tripped kill switch should wake someone up.
- **Companion template** — if the action is specifically an invoice payment, pair this guard with our [Invoice Auto-Pay Guardian](/templates/invoice-auto-pay-guardian/), which adds a 3-way invoice/PO/receiving match and per-payment caps on top of the same idempotency idea.
