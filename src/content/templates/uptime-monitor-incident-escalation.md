---
title: "Uptime Monitor with Incident Escalation"
description: "Check your sites every 5 minutes, retry on failure, and escalate to Telegram + Slack after 3 straight failures."
date: 2026-10-01
category: "automation"
difficulty: "beginner"
workflow: "/templates/uptime-monitor-incident-escalation.json"
integrations: ["Telegram", "Slack"]
---

## How it works

1. **Every 5 Minutes** — a schedule trigger starts a check cycle.
2. **Site List** — a Set node holding your sites as name + url pairs. Edit this once; everything else follows.
3. **Expand Sites** — turns the site list into one item per site so the check runs for each of them.
4. **Check Site** — sends an HTTP GET with a 10-second timeout. "Never error" is on, so a failure flows into the IF node instead of crashing the run.
5. **Site Down?** — an IF node: anything other than status 200 counts as down. Healthy sites go to *Reset Fail Count*.
6. **Wait 60 Seconds** — pauses a minute before retrying, so a momentary blip doesn't page anyone.
7. **Recheck Site** — fetches the site one more time.
8. **Still Down?** — still failing goes to *Log Incident*; recovered goes to *Reset Fail Count*.
9. **Log Incident** — appends a row (time, url, status) to your incidents sheet.
10. **Read Fail Count / Increment Counter / Update Fail Count** — reads the site's fail_count from your tracking sheet, adds 1, and writes it back. This is the consecutive-failure counter.
11. **Escalate?** — an IF node on fail_count >= 3.
12. **Telegram Escalation + Slack Escalation** — 3 straight failures: "DOWN" alert goes to both Telegram and Slack.
13. **Telegram Warning** — 1-2 failures: a Telegram-only heads-up, no Slack noise.
14. **Reset Fail Count** — any successful check resets the counter to 0, so only truly consecutive failures escalate.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A Google account with a spreadsheet — two tabs: `SiteStatus` (columns: url, fail_count, one row per site) and `Incidents` (columns: time, url, status)
- A Telegram bot token — message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, copy the token. You also need your own chat ID (message [@userinfobot](https://t.me/userinfobot) to get it).
- A Slack workspace where you can add an n8n OAuth app

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Edit your sites** — open *Site List* and replace the example with your own name + url pairs.
4. **Connect Google Sheets** — go to *Credentials → New → Google Sheets OAuth2 API*, sign in, save. Select it in *Log Incident*, *Read Fail Count*, *Update Fail Count*, and *Reset Fail Count*, pointing at your spreadsheet's `SiteStatus` and `Incidents` tabs.
5. **Connect Telegram** — go to *Credentials → New → Telegram API*, paste your bot token, save. Select it in *Telegram Escalation* and *Telegram Warning*, and put your chat ID in both.
6. **Connect Slack** — go to *Credentials → New → Slack OAuth2 API*, authorize, save. Select it in *Slack Escalation* and set your channel (e.g. #incidents).
7. **Activate** the workflow (toggle, top-right). Temporarily add a bogus URL to *Site List* to watch the retry → warn → escalate path fire, then remove it.

## Customize it

- **Change the check interval** — open *Every 5 Minutes* and pick a different cadence.
- **Change the escalation threshold** — open *Escalate?* and edit the 3-failure cutoff.
- **Change the retry delay** — open *Wait 60 Seconds* and adjust the amount.
- **More sites** — just add entries to *Site List*; add matching rows to the `SiteStatus` sheet tab.
- **Add PagerDuty or email** — branch a new node off *Telegram Escalation* for any other alert channel.
