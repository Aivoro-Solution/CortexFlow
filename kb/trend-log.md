# Trend Log — Google Trends scans (CortexFlow trend-article engine)

Each run logs: date/time, what was checked, top rising/breakout queries found
(geo + timeframe), the topic picked, and notable ones skipped. If Google Trends
pages are blocked/unreadable, the fallback used is noted here — trend numbers
are never invented.

## 2026-11-07 — MORNING run (~12:15 IST / 06:45 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly): top 25 were sports, politics, celebrities. **No AI/automation niche entry.** Only tech-adjacent: "cybertruck" (100K+, 23h ago) and "steam free games november 2026" (20K+).
- **Explore, US, past 7 days** (Oct 31–Nov 7, 2026, hourly): seeds "AI agent", "n8n", "AI automation", "MCP server". Direct fetch hit HTTP 429; data read via live browser on the same URL. Interest-over-time averages (index 0–100): AI agent 27 (peaks 100 on Nov 2 and Nov 5, 1:30 PM), n8n 3 (flat), AI automation 8, MCP server 5 (flat). Subregion panels for AI automation and MCP server failed to load ("Oops! Something went wrong").

### Rising / breakout queries found
- **"AI agent"** (19 rising queries): "ai agent swarms minecraft study" — Breakout; **"wells fargo ai agent revocation" — Breakout**; "uc san diego high cholesterol study" — Breakout; "walmart cyberpowerpc price error" — Breakout; "senator chris murphy hospitalized" — Breakout.
- **"n8n"** (12): "n8n.io" — Breakout; "playwright" +160%; "replit" +160%; "n8n sign in" +140%; "gamma" +130%.
- **"AI automation"** (14): mostly noise ("origin of the png image file name pronunciation", "why google uses goats for lawn maintenance"); "what are ai guardrails in software development" — Breakout.
- **"MCP server"** (3): "asana mcp server" — Breakout; "sentry mcp server" +200%; "swagger api" +130%.

### PICKED — PUBLISHED 2026-11-07 (morning run)
- **"wells fargo ai agent revocation" (Breakout, US, past 7 days)** → article `wells-fargo-ai-agent-liability-nov-24.md` — "Wells Fargo Just Made You Liable for Your AI Agent — What Builders Must Change Before Nov 24". Verified via American Banker (Nov 2), Tech Times (Nov 3), AccountsRecovery.net (Nov 3), PayPath (Nov 3): Wells Fargo's Online Access Agreement, new Section 15 "Third-Party Artificial Intelligence Agents or Agentic AI", effective Nov 24, 2026; agent instructions deemed authorized by the customer (15d); use at own risk, bank does not monitor (15e); revocation evidence is the customer's job (15f); bank may require registration or block access (15g). ~70M digital banking customers affected. Live: https://cortexflow.tech/blog/wells-fargo-ai-agent-liability-nov-24/ — Telegram 'Published Blog' sent.

### Skipped (notable)
- "sentry mcp server" +200% — Sentry's MCP server launched Aug 2025 (v0.42.0, Oct 20 changelog); no fresh event behind the rise, so no news hook.
- "n8n + playwright" (+160% related query) — rising pairing, but no news event; better as a future how-to, not a trend article.
- "ai agent swarms minecraft study" — Breakout, but a research study with a weak builder angle; no primary source verified in this run.
- "what are ai guardrails in software development" — Breakout, but definitional; blog already covered n8n 2.43 agent guardrails (2026-10-08).
- "cybertruck" / "steam free games" — tech-adjacent Trending Now entries, outside the blog's niche.
