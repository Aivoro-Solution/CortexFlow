---
title: "AI Stock Analysis Reports"
description: "Multi-agent stock analysis: weekly AI reports with technicals, fundamentals, news sentiment, optional Alpaca paper trades. Import-ready n8n workflows."
date: 2026-10-02
category: "automation"
difficulty: "advanced"
workflow: "/templates/ai-stock-reports.json"
integrations: ["TwelveData", "Alpha Vantage", "Chart-IMG", "Alpaca", "Google Gemini", "SMTP"]
---

## How it works

A 4-workflow multi-agent system that produces institutional-style stock reports. Download and import **all four** JSON files — they work as a team:

1. **ai-stock-reports.json — Main Orchestrator.** Two triggers start it: a **Schedule Trigger** (every Monday 06:20) loops over a 15-ticker watchlist (`LLY, UNH, JPM, V, XOM, HD, CAT, AAPL, MSFT, NVDA, AMZN, GOOGL, META, AVGO, COST`), and a **form trigger** ("Manual Entry: Stock Analysis") lets you analyze any single ticker on demand. Each ticker is passed to the *Execute Workflow* node, which calls this same workflow's AI agent section.
2. **The AI Agent (Google Gemini)** acts as orchestrator: it **must** call all three sub-workflow tools — `technical_analysis`, then `trends_analysis`, then `fundamental_analysis` — and synthesizes everything into a strict JSON report (recommendation, sentiment counts, chart URL, technical write-up, top articles, hot topics). Window Buffer Memory gives it short-term context.
3. **ai-stock-reports-technical.json — Technical Analysis.** Validates the ticker on NASDAQ/NYSE via TwelveData, then pulls 180 days of price history, Bollinger Bands, MACD, and a TradingView chart image (Chart-IMG). A Code node computes Fibonacci levels plus support/resistance; GPT-4o Vision reads the chart (RSI, trend, candlestick patterns); a senior-analyst prompt merges it all into five sections.
4. **ai-stock-reports-fundamental.json — Fundamental Analysis.** Pulls company Overview, Income Statement, and Balance Sheet from Alpha Vantage (with 12s waits between calls to respect rate limits), then an AI analyst extracts description, key metrics (MarketCap, P/E, EPS), and two-year revenue/net-income trends into clean JSON.
5. **ai-stock-reports-trends.json — Trends & News Analysis.** Fetches Alpha Vantage news sentiment for the ticker, then a Code node counts bullish/neutral/bearish articles, averages the sentiment score, and ranks hot topics.
6. **Back in the main workflow:** if the recommendation title contains "Buy", a $7,000 paper buy order fires on **Alpaca**. The report JSON is rendered into a styled HTML email (sentiment-colored sections) and emailed via SMTP.

## Set up steps

You'll need:

- n8n (self-hosted or cloud)
- A TwelveData API key — [twelvedata.com](https://twelvedata.com) (price/exchange validation + indicators)
- An Alpha Vantage API key — [alphavantage.co](https://www.alphavantage.co) (fundamentals + news sentiment)
- A Chart-IMG API key — [chart-img.com](https://chart-img.com) (TradingView chart images)
- A Google PaLM/Gemini API key — [aistudio.google.com](https://aistudio.google.com) (main orchestrator agent)
- An OpenAI API key — [platform.openai.com](https://platform.openai.com) (vision + analyst prompts; used via OpenRouter-compatible model IDs)
- SMTP credentials for sending the report email
- (Optional) Alpaca paper-trading API keys — [alpaca.markets](https://alpaca.markets) (paper account)

1. **Download all four workflow JSONs** using the download button on this page (main file) plus:
   - `/templates/ai-stock-reports-technical.json`
   - `/templates/ai-stock-reports-fundamental.json`
   - `/templates/ai-stock-reports-trends.json`
2. In n8n, go to *Workflows → ⋯ → Import from file* and import all four files.
3. **Link the three tool nodes** — open the main workflow and, in each of *Technical Analysis Tool*, *Trends Analysis Tool*, and *Fundamental Analysis Tool*, click the workflow field and select the matching imported sub-workflow.
4. **Link the Execute Workflow node** — open *Execute Workflow* in the main workflow and select the **AI Stock Analysis Reports — Main Orchestrator** workflow itself (this is how the loop feeds tickers into the agent section).
5. **Paste API keys into the Set nodes** — open *Set Stock Symbol and API Key* (technical workflow) and paste your TwelveData key; open *Set Variables* (fundamental) and *Set Variables1* (trends) and paste your Alpha Vantage key. Nothing else in these nodes needs changing.
6. **Create credentials** — *Credentials → New*: Google PaLM API (select in *Google Gemini Chat Model*), OpenAI (select in *First Technical Analysis*, *ChatGPT 4o*, *ChatGPT 4o1*), Header Auth named `Chart-IMG API Key` (select in *Get Chart URL*), SMTP (select in *Send Stock Analysis*), and optionally Header Auth named `Alpaca API Key` (select in *Buy in Alpaca*; also paste your key ID/secret into the node's header values).
7. **Email addresses** — open *Send Stock Analysis* and replace `PASTE_YOUR_EMAIL_HERE` in both To and From with your email.
8. **Activate all four workflows** (toggle, top-right of each). The sub-workflows are called as tools, but n8n requires them active to be executed.

## Customize it

- **Your watchlist** — edit the `tickers` array in the *Stock List* node (any NASDAQ/NYSE symbols).
- **Schedule** — open *Schedule Trigger* and change the day/time (currently Monday 06:20).
- **Trade size** — in *Buy in Alpaca*, change `"notional": 7000` to your amount. The URL already points at Alpaca's **paper** API — switch to `https://api.alpaca.markets` only if you truly want live trading.
- **Disable auto-buy** — delete or deactivate the *Buy?* → *Buy in Alpaca* branch to keep it reports-only.
- **Buy threshold** — *Buy?* fires when the recommendation title contains "Buy"; tighten it (e.g. also require `overallSentiment` = Bullish) with an extra condition.
- **Email design** — the *Generate HTML* node holds the full email template; the *Adjust HTML Colors* code node recolors sections by sentiment automatically.
- **Swap the brain** — the main agent uses Google Gemini; point *Google Gemini Chat Model* at any Gemini model, or swap the node for an OpenAI chat model.
