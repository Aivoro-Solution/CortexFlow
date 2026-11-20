---
title: "Anthropic Opened at $111.50 and Closed at $97.17 — What Day One Tells n8n Builders"
description: "ANT's first day on Nasdaq: a 34% pop at the open, a fade to $97.17 at the close, and 813M shares traded. What the tape means for anyone building on Claude."
date: 2026-11-20
category: news
tags: ["anthropic", "claude", "ipo", "n8n"]
draft: false
featured: false
image: "/og/anthropic-ant-first-day-close-97-17-nov-19.webp"
---

Anthropic priced its IPO at $83 a share on Wednesday. By noon on Thursday, the stock was trading at $111.50. By the closing bell, it was $97.17. Same company, same day, a $250 billion swing in what the market thought it was worth — and that swing is the whole story for anyone building on Claude.

Yesterday we covered [the pricing and the first trade](/blog/anthropic-ipo-priced-83-ant-trading-nov-19/). This is the rest of the tape: what actually happened across the full first session, why the pop faded, and the five things worth doing this week now that your model vendor is a public company.

## The full first-day tape

Anthropic sold 980 million shares at $83, raising $81.3 billion — the largest IPO on record, ahead of SpaceX's $75 billion debut in June. Trading began at 11:48 a.m. ET on Thursday, November 19, at $111.50, a 34% premium to the IPO price. At that open, Anthropic was worth about $2 trillion on a fully diluted basis.

It did not stay there. The stock touched about $115 in the first minutes, then slid through the afternoon, dipping below $100 within half an hour and bottoming at $92.72 before recovering into the close.

| First-day tape, ANT (Nov 19, 2026) | |
|---|---|
| IPO price | $83.00 |
| First trade (11:48 a.m. ET) | $111.50 (+34%) |
| Intraday high | ~$115.10 |
| Intraday low | $92.72 |
| Close | $97.17 (+17.07%) |
| Shares traded | 813M+ (Nasdaq) |
| Fully diluted value at close | ~$1.75 trillion |
| After-hours (8 p.m. ET) | $92.60 (-4.7% vs close) |

The close is still a strong debut by any normal measure: up 17% on the IPO price, the biggest IPO ever, and more than 813 million shares changed hands — comfortably beating SpaceX's 522 million on its opening day, according to Nasdaq. Barron's called it a "surprisingly normal first day." But the direction of travel matters. The market paid $111.50 at 11:48 a.m. and $97.17 at 4 p.m. — and kept selling after hours, down to $92.60 by 8 p.m. ET.

![Fig 1 — A ticker-tape press stamping Anthropic's first trading day. The tape enters at the $111.50 open, passes under the lit stamping die, and winds out at the $97.17 close; the dial reads the close inside the day's $92.72–~$115.10 range.](/figures/anthropic-ant-first-day-close-97-17-nov-19-tape-press.svg)

*Fig 1 — The first-day tape, as a machine. The tape enters at the $111.50 open, the press stamps the day's range, and it winds out at the $97.17 close. Watch the dial: the close sits just 20% of the way up from the day's low — most of the session was spent giving the opening pop back.*

Context helps: the broader market fell the same day, with the S&P 500 and the Nasdaq Composite both down about 2%. Anthropic did not fade in a vacuum. Investopedia's verdict on the day was blunt: "The AI trade's biggest test yet is over, and results were mixed."

## Why the pop faded

Three forces were working against the open price.

**First, the open was set by scarcity, not by a full day of trading.** Only a fraction of Anthropic's shares were available to trade on day one — up to roughly 315 million shares, with the rest locked up for about 180 days. A small floating supply meeting enormous demand (the offering was reported roughly six times oversubscribed) pushes the first print up. That is mechanics, not a verdict on the business.

**Second, the numbers underneath are genuinely extreme in both directions.** Revenue was $33.24 billion for the nine months to September 30, 2026, up from $2.55 billion a year earlier, with a run-rate of about $81 billion as of October 31. But Anthropic has also committed roughly $900.9 billion in future compute and infrastructure spending. At the $97.17 close, the market values the company at about $1.75 trillion fully diluted — roughly 21 times that revenue run-rate. A buyer at $111.50 was paying for a future that has to go almost perfectly; a buyer at $97.17 is paying for the same future with a little more room for error.

**Third, the AI trade itself is being questioned.** The stock market has been rattled by growing concern about whether AI-driven gains are sustainable, and Anthropic's debut was treated as a test of that question. A 17% close is a pass. A 34% open fading to 17% is a pass with a warning attached: enthusiasm is real, but it is no longer unconditional.

## What this means if you build on Claude

Nothing about Claude the product changed on Thursday. The API works the same way it did on Wednesday. What changed is the information environment around it — and that is where the builder opportunity sits.

A public Anthropic must now file quarterly reports, hold earnings calls, and disclose material risks in audited documents. That is a free, regularly updated roadmap feed for your stack: revenue mix, compute commitments, customer concentration, and risk factors, all in filings you can read. Yesterday's article made the general point; today the feed is live, and the first filing cycle is the one to watch.

The lock-up clock is also now running. About 180 days from November 19 — roughly mid-May 2027 — insiders and early holders can sell. That is a known future event, not a surprise. Put it on a calendar now, and when it arrives you will be reading a scheduled event instead of reacting to a headline.

And the after-hours slide is a small operational lesson on its own: ANT fell another 4.7% after the 4 p.m. close. If your monitoring only runs during business hours, you miss the move. The same applies to status pages and vendor incidents — the check that matters is the one that runs when you are not watching.

## Five things to do this week

**1. Re-run your cost math on the close, not the open.** If you quoted a client or a budget using IPO-week headlines, re-check the numbers against the $97.17 close and the ~$1.75 trillion valuation. The open was a scarcity print; the close is the market's working price.

**2. Build the filing watch.** This is a 30-minute n8n workflow with a real payoff: an HTTP Request node polling SEC EDGAR's company filing feed for Anthropic (CIK lookup, then the submissions JSON), an IF node filtering for 10-Q, 10-K and 8-K filings, and a Slack or Telegram node posting a digest when something new lands. Your model vendor's roadmap will now arrive as audited documents — collect them automatically instead of reading about them second-hand.

**3. Set the lock-up reminder.** Roughly May 18, 2027, the ~180-day lock-up expires. Add the date to your calendar with a note: "ANT lock-up expiry — expect volatility, check Claude pricing/support comms, no action unless the filing says otherwise." Scheduled events should never feel like surprises.

**4. Test your second-model fallback while things are calm.** This is not about the stock — it is about the habit. A vendor whose valuation swings $250 billion in six hours is a reminder that your stack has a single point of failure. Run one real task through your fallback model this week and confirm the output is acceptable. If it is not, fix the prompt now, not during an outage. (Our [Claude outage fallback pattern](/blog/claude-outage-nov-13-n8n-fallback/) covers the wiring.)

**5. Keep the standing money rule.** No agent moves money, places an order, or acts on market news without a human approval gate. ANT's first day is exactly the kind of headline an agent would overreact to — the open said "buy the AI boom," the close said "slow down." Neither is an instruction. The approval gate is what turns market noise into a decision a human made.

## Honest limits

A few things this article does not know yet. The first-day numbers come from the regular session; the after-hours quote ($92.60) is a thin market and moves fast. The fully diluted valuation at close is reported as $1.75–1.77 trillion depending on the source's share count — treat "~$1.75 trillion" as the working figure, not a precise one. The intraday high is reported as $115.10 (Finnhub) and $114.99 (Financial Express) — a rounding-level difference, but it is a difference. And the lock-up expiry is "about 180 days" per the filing summary, not a confirmed calendar date; check the prospectus before you set a hard reminder. Nothing here is investment advice — it is a builder's reading of a market event, not a recommendation to buy or sell anything.

## FAQ

### Did Anthropic's IPO succeed?

By the standard measures, yes: $81.3 billion raised, the largest IPO on record, shares closed 17% above the $83 IPO price, and trading volume beat SpaceX's opening day. The caveat is the fade — the stock opened 34% up and gave back half the gain by the close, then slipped further after hours.

### What was Anthropic worth at the close?

About $1.75 trillion on a fully diluted basis at the $97.17 close, down from about $2 trillion at the $111.50 open. Different outlets report $1.75–1.77 trillion depending on the share count they use.

### Why did the stock fall from its open?

Partly mechanics — only a fraction of shares were available to trade on day one, so the first print reflected scarcity plus roughly 6x oversubscribed demand. Partly valuation — at the open the market was paying about 21 times the revenue run-rate and more, against roughly $900.9 billion in committed future compute spending. And partly the broader market, which fell about 2% the same day.

### Does the IPO change anything about using Claude in n8n?

No, not technically. The API, pricing, and models are unchanged. What changes is transparency: Anthropic must now publish audited quarterly filings and hold earnings calls, which gives builders a regular, reliable source of information about the vendor their workflows depend on.

### When can insiders sell their Anthropic shares?

After a lock-up period of about 180 days from the November 19 listing — roughly mid-May 2027. The exact date is in the prospectus; treat the May estimate as approximate until confirmed.

## Key Takeaways

1. **ANT opened at $111.50 (+34%) and closed at $97.17 (+17%)** — the biggest IPO on record, but the market gave back half the opening gain in six hours, then slipped to $92.60 after hours.
2. **The close is the signal, the open was scarcity** — only a fraction of shares traded on day one against roughly 6x oversubscribed demand.
3. **Your vendor is now a public company** — audited filings and earnings calls become a free roadmap feed; build the EDGAR watch workflow this week.
4. **Set the lock-up reminder for ~May 2027** and test your second-model fallback while things are calm.
5. **No agent moves money on market headlines** — the approval gate stays, whatever the tape says.

Next: the first 10-Q will tell us more about Claude's revenue mix and compute spending than any launch event. If you build the filing watch above, you will read it the day it lands. And if you have not set up a fallback model yet, start with our [Claude outage fallback guide](/blog/claude-outage-nov-13-n8n-fallback/).
