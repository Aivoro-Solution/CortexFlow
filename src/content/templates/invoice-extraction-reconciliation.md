---
title: "Invoice Extraction & Reconciliation Pipeline"
description: "Extract vendor, amount and date from invoice emails with AI, log to Sheets, and hold big invoices for approval."
date: 2026-10-01
category: "automation"
difficulty: "intermediate"
workflow: "/templates/invoice-extraction-reconciliation.json"
integrations: ["Gmail","OpenAI","Google Sheets"]
---

## How it works

1. **Gmail Trigger: Invoice Email** — fires on new messages whose subject contains "invoice" and that have an attachment.
2. **Gmail: Download Attachment** — downloads the invoice attachment from the email.
3. **OpenAI: Extract Invoice Data** — reads the attachment and extracts the vendor name, amount, date, and invoice number as JSON.
4. **Set: Normalize Fields** — cleans the extracted values into consistent fields and stamps the row `status = pending`.
5. **Google Sheets: Log Invoice** — appends a row (date, vendor, amount, invoice number, status) to your spreadsheet.
6. **IF: Amount > 1000** — routes invoices over your approval threshold to a human gate; smaller invoices skip it.
7. **Gmail: Approval Request** — emails finance the invoice details plus an approval link; the workflow pauses until finance responds.
8. **Wait: Finance Approval** — finance opens the approval link and submits Approve or Reject on the form.
9. **IF: Finance Approved?** — routes approved invoices to "reconciled" and rejected ones to "rejected".
10. **Google Sheets: Mark Reconciled** — updates the row's status to `reconciled` for approved invoices.
11. **Google Sheets: Mark Rejected** — updates the row's status to `rejected` when finance rejects it.
12. **Google Sheets: Mark Auto-Reconciled** — for invoices under the threshold, updates the row's status to `auto-reconciled`.
13. **Slack: Notify** — posts a message confirming the invoice was auto-reconciled without human review.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Gmail account — connect via OAuth in n8n
- An OpenAI account — get an API key at platform.openai.com → API keys
- A Google account with a spreadsheet — connect via OAuth in n8n
- A Slack workspace — connect via OAuth in n8n

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your Gmail credential** — in n8n go to *Credentials → New → Gmail OAuth2*, complete the OAuth flow, save. Open *Gmail Trigger: Invoice Email*, *Gmail: Download Attachment*, and *Gmail: Approval Request*, and select the credential.
4. **Create your OpenAI credential** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save. Open *OpenAI: Extract Invoice Data* and select your credential.
5. **Create your Google Sheets credential** — in n8n go to *Credentials → New → Google Sheets OAuth2*, complete the OAuth flow, save. Open the three Google Sheets nodes, select the credential, pick your spreadsheet, and set the sheet name (the template uses columns: date, vendor, amount, invoice_number, status — create these as the header row).
6. **Create your Slack credential** — in n8n go to *Credentials → New → Slack OAuth2*, complete the OAuth flow, save. Open *Slack: Notify*, select the credential, and set the channel (e.g., `#finance`).
7. **Set your finance email** — open *Gmail: Approval Request* and change the recipient to your finance team's email address.
8. **Set your approval threshold** — open *IF: Amount > 1000* and change `1000` to whatever amount should require human approval.
9. **Activate** the workflow (toggle, top-right), then send yourself a test invoice email.

The approval email contains a link built from `{{$execution.resumeUrl}}`. Clicking it opens an Approve/Reject form — submitting the form resumes the workflow exactly where it paused.

## Customize it

- **Change the email filter** — open *Gmail Trigger: Invoice Email* and edit the `q` filter (e.g., `from:vendor@example.com has:attachment`) to match how your invoices arrive.
- **Handle PDFs** — if your invoices arrive as PDFs, add an *Extract from File* node between *Gmail: Download Attachment* and *OpenAI: Extract Invoice Data* so the AI reads the PDF text.
- **Change the threshold currency** — the template compares a plain number; make sure the amount the AI extracts is in your base currency, or add a conversion step in *Set: Normalize Fields*.
- **Add a receipt for rejected invoices** — connect a Gmail send node after *Google Sheets: Mark Rejected* to notify the vendor.
