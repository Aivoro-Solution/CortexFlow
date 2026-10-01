---
title: "Competitor Price Monitoring & Alerts"
description: "Track competitor prices daily: fetch product pages, extract prices, and get a Telegram alert when they change."
date: 2026-10-01
category: "automation"
difficulty: "beginner"
workflow: "/templates/competitor-price-monitoring.json"
integrations: ["Google Sheets", "Telegram"]
---

## How it works

1. **Daily Schedule** — runs once a day at 09:00 and kicks off the price check.
2. **Read Products** — reads your Google Sheet rows: product_name, url, and last_price.
3. **Fetch Product Page** — downloads each product page (n8n automatically runs it once per row).
4. **Extract Price** — pulls the price out of the page HTML with a CSS selector you set per site.
5. **Normalize Price** — strips currency symbols and converts the price text into a plain number.
6. **Price Changed?** — an IF node that compares the live price against last_price from your sheet.
7. **Send Price Alert** — Telegram messages you: "Price changed: X was $A, now $B" with the product link.
8. **Update Last Price** — writes the new price back into the sheet so tomorrow's run compares against it.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Google account with a spreadsheet — columns: product_name, url, last_price
- A Telegram bot token — message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, copy the token. You also need your own chat ID (message [@userinfobot](https://t.me/userinfobot) to get it).

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Connect Google Sheets** — go to *Credentials → New → Google Sheets OAuth2 API*, sign in with Google, save. Then open *Read Products* and *Update Last Price* and select this credential, picking your spreadsheet.
4. **Connect Telegram** — go to *Credentials → New → Telegram API*, paste your bot token, save. Select it in *Send Price Alert* and replace `PASTE_YOUR_CHAT_ID` with your chat ID.
5. **Set the price selector** — open *Extract Price* and change the CSS selector (currently `.price`) to match your competitor's site. Right-click the price in your browser → *Inspect* → copy its selector.
6. **Activate** the workflow (toggle, top-right). Use *Execute workflow* once to test it immediately.

## Customize it

- **Change the schedule** — open *Daily Schedule* and pick a different time or interval.
- **Track more products** — just add rows to the sheet; no workflow changes needed.
- **Alert on drops only** — in *Price Changed?*, replace "not equals" with "smaller than" so you only get pinged on price drops.
- **Respect the sites you monitor** — keep the daily schedule, don't scrape aggressively, and check each site's terms of service and robots.txt before monitoring it.
