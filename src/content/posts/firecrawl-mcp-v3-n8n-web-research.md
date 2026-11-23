---
title: "Firecrawl MCP v3 Gives Your n8n Agent 3,000+ Tools — the Wiring Pattern (and the Catch)"
description: "Firecrawl MCP v3 is a +300% rising search this week: 3,000+ Alexandria tools, 60x rate limits, a local Rust engine — here's the n8n wiring."
date: 2026-11-23
category: news
tags: ["firecrawl", "mcp", "n8n", "web scraping", "ai agents"]
draft: false
featured: false
image: "/og/firecrawl-mcp-v3-n8n-web-research.webp"
---

Your n8n agent can already call an LLM, read a spreadsheet, and send a Slack message. What it cannot do on its own is go and get fresh facts from the live web — competitor prices, a changelog, a company's funding round — and bring them back as clean data instead of a hallucinated summary. That is the job Firecrawl's MCP server has been doing for a while. This week, n8n builders started searching for it in numbers big enough to notice: "firecrawl mcp server" is a +300% rising related query for "MCP server" in the US over the past 7 days (Google Trends Explore, Nov 16–23, 2026, read Nov 23).

The timing is not a coincidence. Firecrawl shipped MCP v3 on November 12, 2026, then open-sourced a local Rust scraping engine on November 18. By the end of this article you will have a working n8n workflow that gives an AI Agent live web research through Firecrawl's MCP server — and you will know exactly what the "3,000+ tools" headline does and does not mean.

## What Firecrawl MCP v3 actually is

Firecrawl is a web-data API: give it a URL and it returns the page as clean Markdown or structured JSON, handling JavaScript rendering for you. Its MCP server (Model Context Protocol — Anthropic's open standard for exposing tools to AI models) exposes that API as tools an agent can call: search the web, scrape a URL, crawl a site, map every URL on a domain, extract data with a schema, interact with pages, and run deep research with an autonomous agent.

MCP v3, announced November 12, 2026 on Firecrawl's own changelog, is the headline version of that server. Firecrawl's claims, in its own words:

- **3,000+ tools** with automatic provider waterfalls
- **60x higher rate limits**
- **4x more usage** through the MCP
- **Parallel subtasks** — the agent can spawn background work while the main task continues
- **Available now for every harness** — Claude, ChatGPT, Cursor, and any other MCP client

The tools come from Alexandria, Firecrawl's data catalogue, announced September 22, 2026 alongside a $75M Series B. Alexandria is a catalogue of structured-data providers — company data, people data, research, government records — reachable through one Firecrawl connection. One independent count of the public catalogue found 3,294 capabilities across 574 providers in 36 categories (Sulat AI, Nov 13, 2026). The company graph alone now covers 75M+ companies, returning headcount, revenue, funding, and tech stack in roughly half a second, per Firecrawl's November 13 changelog entry.

## What's new in November — and why the searches spiked

MCP v3 was not the only Firecrawl launch in the last ten days. The week stacked up like this:

| Date | Launch | What changed |
|---|---|---|
| Nov 12, 2026 | **Firecrawl MCP v3** | 3,000+ Alexandria tools, provider waterfalls, 60x rate limits, 4x usage, parallel subtasks. npm package `firecrawl-mcp` 3.40.0. |
| Nov 13, 2026 | **Alexandria company data expansion** | 75M+ companies with headcount, revenue, funding, tech stack in ~0.5s. |
| Nov 17, 2026 | **UltraSearch** | Paid agent search over 250M+ people, 75M companies, 150,000 stocks with live pricing. |
| Nov 18, 2026 | **Firecrawl Local** | Open-source Rust binary (AGPL-3.0) that scrapes and crawls on your own machine and works as an MCP server. |

Firecrawl Local deserves a paragraph of its own, because it changes the cost and privacy math. It is a single binary — `cargo install firecrawl-local`, no database, no queue, no container — that turns pages into clean Markdown using the same cleaning code the Firecrawl API uses, renders JavaScript-heavy pages in the Chrome already installed locally, and serves the Firecrawl v2 API on `localhost:3002`, so existing SDK code works by changing the API URL. Firecrawl claims it scrapes 37x faster than the self-hosted version with 230x less memory (11 MB idle) — vendor figures, no independent benchmark published. `firecrawl-local init` wires the MCP server into Claude Code, Claude Desktop, Cursor, Windsurf, Gemini CLI, and Codex, backing up each config first.

## The honest catch: what "3,000+ tools" really means

Before you wire anything up, read the headline carefully, because the number is real but easy to misunderstand.

**The 3,000 tools are catalogue providers, not tools in your agent's list.** The hosted MCP server's full profile lists 33 tools. The thousands sit behind two library tools — `alexandria_library_search` and `alexandria_library_read` — which treat the catalogue like a read-only library of provider contracts. Your agent discovers a provider, then runs it. That is a better design than stuffing 3,000 tool definitions into the model's context window, but it is not the same as having 3,000 tools one call away.

**"MCP v3" is a launch name, not a new version you install.** The npm package `firecrawl-mcp` has been on a 3.x line since tag v3.0.0 (September 11). The hosted endpoint still carries a `/v2/` path — `https://mcp.firecrawl.dev/v2/mcp` — and neither the README nor the MCP docs say "v3". If you already run the hosted MCP, there is nothing to change. If you run it locally with npx or Docker, move to `firecrawl-mcp` 3.40.0 and re-check any prompts that ask for the JSON scrape format or name one enrichment provider.

**The 60x rate-limit claim has no published baseline.** Firecrawl does not say what the old limit was, so plan around the published per-plan API limits instead of the multiplier. And the bill: finding and checking tools in Alexandria is free; running one costs the credits listed on it. A plain scrape costs 1 credit per page, a search 2 credits per 10 results. Every plan includes free MCP usage that refreshes daily, per Firecrawl — and there is a keyless free tier on the hosted server if you have no API key at all.

None of this makes v3 a non-event. The concrete change in 3.40.0 is the provider waterfall: the people and company enrichment tools now run Firecrawl's enrichment waterfall instead of taking a block per provider, so when the first source returns nothing, the system moves to the next one until it finds the record. For a research agent, "keep trying sources until one answers" is the difference between a dead end and a delivered answer.

## How to wire Firecrawl MCP into n8n

Firecrawl documents an n8n route for its MCP server, and it also ships its own verified n8n node. You have two doors into the same building — pick one.

**Prerequisites:** an n8n instance (Cloud or self-hosted, any recent version), a Firecrawl API key from firecrawl.dev/app/api-keys (or no key at all for the keyless free tier), and an AI Agent node with a chat model attached. As of November 23, 2026.

### Route A — MCP Client Tool (the flexible route)

This is the route to take if you want the agent to choose between search, scrape, crawl, map, extract, and research on its own.

**Step 1 - Add an AI Agent node and attach the MCP Client Tool.** In your workflow, add an **AI Agent** node. In the agent configuration, add a new **Tool** and select **MCP Client Tool** as the tool type.

**Step 2 - Point it at Firecrawl's hosted MCP server.** Enter the MCP server endpoint:

```
https://mcp.firecrawl.dev/v2/mcp
```

Set **Server Transport** to **HTTP Streamable** and **Authentication** to **Bearer**, pasting your Firecrawl API key — or leave authentication as **None** to use the keyless free tier. For **Tools to include**, select **All** to expose the Firecrawl tools (scrape, crawl, map, search, extract, and the rest), or **Selected** if you want to cap what the agent can reach. Fewer tools means a smaller attack surface and a cheaper context window — start with Selected and add tools as you need them.

**Step 3 - Tell the agent what "good research" means.** A bare "research this" prompt sends the agent scraping at random. Give it a system prompt with a shape: what to search for, what counts as a source, and what the output must look like. For example: "Search for the company's latest funding round. Return the amount, the date, and the source URL. If two sources disagree, say so and cite both. Never invent a number."

**Step 4 - Verify with a question you already know the answer to.** Ask the agent something verifiable — "What is Firecrawl MCP v3's release date?" — and check that it returns November 12, 2026 with a source. If it answers from memory instead of the tool, your prompt is not forcing tool use: add "Use the Firecrawl tools for every fact" to the system prompt.

> **Warning:** an agent that can browse the live web can also be steered by it. A page it scrapes can contain hidden instructions — prompt injection — telling it to exfiltrate data or call another tool. Never let a research agent write to production systems, and keep the approval gate in the next section on every workflow that acts on what it finds. If you run Firecrawl Local, register it as `firecrawl-local mcp --public-only` when the agent browses untrusted sites, per Firecrawl's own docs — that flag keeps it from reaching internal addresses.

### Route B — Firecrawl's verified n8n node (the deterministic route)

Firecrawl ships its own n8n node, `@mendable/n8n-nodes-firecrawl`, maintained by Firecrawl and verified by n8n — which matters, because n8n Cloud only installs verified community nodes. It covers Firecrawl `/search`, `/scrape`, `/interact`, `/crawl`, `/map`, and `/agent`, with resources for Scraping, Crawling, Map & Search, Agent, Interact, Browser, Account, and Extract.

On n8n Cloud, connecting creates an n8n-linked Firecrawl team with 10,000 free credits. On self-hosted n8n, an admin installs the node once from the nodes panel and every member can use it with a Firecrawl API key. The `/agent` operation — "Extract Data With AI Agent" — waits up to 300 seconds by default (600 at most); for longer jobs, use the async operation plus Get Agent Status.

> **Note:** if your Firecrawl credentials point at `https://api.firecrawl.dev/v1`, the Agent and Interact operations will break. Set the Base URL to `https://api.firecrawl.dev/v2`. The HTTP Request node still has a job here: it reaches API parameters the node does not expose, and it imports cURL commands straight from the Firecrawl API reference.

### Route C — Firecrawl Local (the private route)

If the data you research is sensitive — or you just do not want per-page credits — run Firecrawl Local on the same machine as n8n:

```bash
cargo install firecrawl-local
firecrawl-local init
```

`init` adds the MCP server to your coding tools' configs. For n8n, run the server with HTTP transport and point the MCP Client Tool at `http://localhost:3000/v2/mcp` (or at the Local v2 API on `localhost:3002` from an HTTP Request node). You need Rust and a C compiler to install it, and the AGPL-3.0 license applies to the engine itself — fine for internal use, check with your team before embedding it in a product you sell.

| | Hosted MCP | Verified n8n node | Firecrawl Local |
|---|---|---|---|
| Setup | Endpoint + API key, 2 minutes | Install node, connect account | `cargo install`, local binary |
| Cost | Credits per call; keyless free tier | 10,000 free credits on Cloud connect | Free (AGPL-3.0); you pay for the machine |
| Agent chooses tools? | Yes — full MCP toolset | No — you pick the operation per node | Yes — MCP server, same as hosted |
| Best for | Research agents that need the Alexandria catalogue | Deterministic scrape/crawl steps in a fixed workflow | Private or high-volume scraping |

## The 5-part pattern: give your agent a research desk, not a blank cheque

The same pattern this blog has used for every MCP wiring holds here, because the failure modes are the same:

1. **One tool, one job.** Give the agent the smallest Firecrawl toolset that answers the question — search + scrape for fact-finding, add crawl and map only when it must explore a whole site. Every extra tool is context the model pays for and an action it can misuse.
2. **Demand sources, not summaries.** The system prompt should require a source URL per fact and a flag when sources disagree. A research agent that cannot cite is a rumor machine with an API key.
3. **Cap the spend per run.** Set `max_credits` on Alexandria calls, and put a credit ceiling in the workflow — an IF node that stops the run when the Firecrawl account balance drops below a threshold. The waterfall is exactly the feature that can quietly burn credits: each provider it tries is a call.
4. **Human approval before anything irreversible.** Research is read-only; acting on research is not. Route every write — a Slack post, a CRM update, a price change — through a human approval gate (the Wait node in n8n, or a Slack interactive message). The agent researches; you decide.
5. **Log every lookup.** Append each query, source URL, and credit cost to a sheet or a database. When a number in a report looks wrong a week later, the log is the only thing that tells you whether the agent found it or invented it.

![Fig 1 — The Firecrawl research press: an n8n agent feeds a question into the MCP server, which runs it through the Alexandria provider waterfall until one source answers, then delivers clean Markdown — with the approval lever locked until a human pulls it.](/figures/firecrawl-mcp-v3-n8n-web-research-scraper-press.svg)

*Fig 1 — The Firecrawl scraper press. The n8n AI Agent console (left) drops a research request into its hopper; the Alexandria catalogue drum holds the 3,000+ tool index across 574 providers and the provider waterfall — three stacked cylinders — tries providers in turn until one answers, each feeding the MCP press down a cable. The die stamps clean Markdown onto the card in the output tray. The rate-limit gauge reads the 60x headroom, the approval-log drum keeps the paper trail, and the irreversible-action chute stays gated behind the lit orange APPROVE lever: nothing moves without approval. Readout: Nov 12, 2026 · 3,000+ tools · 60x limits · 4x usage · 75M+ companies · 0 without approval.*

## Limits and trade-offs

- **Pattern-verified, not live-tested.** The n8n wiring above follows Firecrawl's own docs; I did not run a live n8n workflow against the hosted MCP for this article. Treat the endpoint, transport, and auth settings as documented, and run the Step 4 verification before trusting the workflow.
- **Vendor numbers throughout.** 3,000+ tools, 60x rate limits, 4x usage, 37x faster, 230x less memory, 0.5-second company lookups — all Firecrawl's claims, none independently benchmarked. The 60x figure has no published baseline at all.
- **The waterfall costs credits.** "Keep trying providers until one answers" is great for recall and bad for your bill if you do not cap it. Set `max_credits` on every Alexandria call.
- **Scraping is not a right.** Firecrawl turns pages into Markdown, but the target site's terms of service and robots rules still apply to you. Research your own properties and public data; do not use a research agent to strip-mine a competitor's paywalled content.
- **Firecrawl Local is new.** Announced November 18, five days before this article. Expect rough edges, and check the repo's changelog before depending on it in production.

## FAQ

### Do I need to change anything if I already use Firecrawl's MCP server?

No, if you use the hosted server — there is no new URL, and scrape and search cost what they did. If you run it locally with npx or Docker, move to `firecrawl-mcp` 3.40.0 and re-check prompts that ask for the JSON scrape format or name one enrichment provider.

### What is the difference between Firecrawl MCP v3 and Firecrawl Local?

MCP v3 is the hosted/cloud offering: one connection to the Alexandria catalogue with 3,000+ provider tools, waterfalls, and higher limits. Firecrawl Local is an open-source Rust binary you run on your own machine — no credits, no cloud, but no Alexandria catalogue either. They solve different problems: v3 is for breadth, Local is for privacy and volume.

### Can I use Firecrawl MCP without an API key?

Yes. Connect to `https://mcp.firecrawl.dev/v2/mcp` and you get the keyless free tier. For real workloads, get a key — the free tier is for trying things out, not for production research.

### Is the verified n8n node better than the MCP Client Tool?

Neither is better in general. The node is deterministic: you pick the operation, the agent never improvises a scrape. The MCP route is flexible: the agent picks the right tool for a question you did not anticipate. Use the node for fixed pipelines (daily competitor price check), the MCP route for open-ended research (answer this question, whatever it takes).

### How many credits does a research run cost?

A plain scrape is 1 credit per page, a search is 2 credits per 10 results. Alexandria provider runs cost the credits listed on each provider — finding and checking tools is free. Budget a research run like a taxi ride with the meter running: cap it, or the waterfall will.

## Key Takeaways

1. **"firecrawl mcp server" is up +300% in US searches this week** because Firecrawl shipped MCP v3 on Nov 12 (3,000+ Alexandria tools, provider waterfalls, 60x rate limits, 4x usage, parallel subtasks) and open-sourced Firecrawl Local on Nov 18.
2. **The 3,000 tools are catalogue providers behind two library tools** — the hosted server itself lists 33 tools. The real upgrade is the waterfall: keep trying sources until one answers.
3. **Wire it into n8n in minutes**: MCP Client Tool → `https://mcp.firecrawl.dev/v2/mcp`, HTTP Streamable, Bearer auth or keyless — or use Firecrawl's verified node `@mendable/n8n-nodes-firecrawl` for deterministic steps.
4. **Cap the spend and gate the actions.** Set `max_credits` on Alexandria calls, and never let a research agent write anywhere without a human approval gate.
5. **Firecrawl Local is the private option**: one Rust binary, AGPL-3.0, v2 API on `localhost:3002`, no per-page credits — but five days old at time of writing, so verify before depending on it.

Next: if you want the full MCP wiring reference, read [how to connect an MCP server to n8n](/blog/how-to-connect-mcp-server-n8n/) and the [n8n MCP troubleshooting guide](/blog/mcp-n8n-troubleshooting/). If you are building a whole agent stack, the [n8n 2.43 agent guardrails](/blog/n8n-2430-agent-guardrails-release/) are the other half of this pattern — research in, approval out.
