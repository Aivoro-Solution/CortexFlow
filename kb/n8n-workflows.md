# n8n Workflow Template Library — Research Notes

**Source:** https://n8n.io/workflows
**Researched:** 2026-09-30
**Purpose:** Tutorial material + blog post ideas for the AI agents/automation/chatbots blog.

---

## 1. Library overview

- **Size:** 12,795 community workflows (per homepage title, Sept 2026). New templates published daily.
- **Access:** Free to browse; each template page has "Use workflow" (direct import to n8n Cloud), "Download workflow" (JSON), and "Copy to clipboard" (paste into canvas).
- **URL pattern:** `https://n8n.io/workflows/<id>-<slug>/` — bare ID also resolves: `https://n8n.io/workflows/<id>` (verified pattern).
- **Template page contents:** title, "Last update" age, categories, long-form description (often with architecture, setup steps, business use cases), sometimes embedded YouTube build videos, author contact/upsell.
- **Top-level categories** (from template pages): AI, SecOps, Sales, IT Ops, Marketing, Engineering, DevOps, Building Blocks, Design, Finance, HR, Other, Product, Support.
- **Granular template categories** (examples seen): Sales Automation, Document Generation, AI Business Tools, Lead Generation.
- **Quality variance:** Official/curated templates are polished; community templates range from excellent to stale (watch for outdated model names, e.g. unsupported Gemini models — good "fix-it" content opportunity).
- **Caveat:** Download/view counts were not visible in fetched page text; popularity below is inferred from cross-references (research docs, community mentions, forum threads), not from the library's own sort.

---

## 2. Notable / popular workflows

| # | Title | What it does | Category | URL |
|---|---|---|---|---|
| 5010 | RAG Starter Template | Form trigger → AI Agent with Simple Vector Store; zero-setup RAG demo with OpenAI | AI | https://n8n.io/workflows/5010-rag-starter-template-using-simple-vector-stores-form-trigger-and-openai/ |
| 6270 | Build your first AI agent | Official starter: Chat Trigger → AI Agent + Gemini + weather/RSS tools + memory | AI | https://n8n.io/workflows/6270-build-your-first-ai-agent/ |
| 10450 | LinkedIn posts with Mistral AI | Dual-agent system: conversational frontend agent + backend writer agent, 7 post templates | AI / Marketing | https://n8n.io/workflows/10450-generate-linkedin-posts-with-mistral-ai-using-7-dynamic-content-templates/ |
| 2339 | Study notes from documents (Mistral + Qdrant) | File trigger → extract → vectorize to Qdrant → AI generates study guide/briefing/timeline | AI | https://n8n.io/workflows/2339-breakdown-documents-into-study-notes-using-templating-mistralai-and-qdrant |
| 4804 | AI premium proposal generator | Form → GPT-4 proposal copy → Google Slides/PandaDoc → Gmail; $1.5–5k/client positioning | Sales Automation | https://n8n.io/workflows/4804-ai-premium-proposal-generator-with-openai-google-slides-and-pandadoc/ |
| 3446 | Daily newsletter service | Schedule → Excel subscribers → fetch templates → AI summaries → HTML email via Outlook | AI | https://n8n.io/workflows/3446-daily-newsletter-service-using-excel-outlook-and-ai/ |
| 6552 | Email triage (GPT-4/Gmail/Trello) | AI classifies/routes incoming email to Trello | AI | https://n8n.io/workflows/6552 |
| 11854 | Support ticket triage | AI triages tickets | Support | https://n8n.io/workflows/11854 |
| 10150 | Lead routing | AI routes inbound leads | Sales | https://n8n.io/workflows/10150 |
| 8646 | CV screening | AI screens resumes | HR | https://n8n.io/workflows/8646 |
| 13154 | Content moderation | AI moderation pipeline | SecOps | https://n8n.io/workflows/13154 |
| 11911 | Invoice processing | AI invoice extraction/processing | Finance | https://n8n.io/workflows/11911 |
| 8057 | Meeting notes | AI meeting-notes generation | Productivity | https://n8n.io/workflows/8057 |
| 13139 | Data integrity alerts | AI watches for data anomalies | IT Ops | https://n8n.io/workflows/13139 |
| 7912 | GA4 anomaly detection | Flags Google Analytics anomalies | Marketing | https://n8n.io/workflows/7912 |
| 9503 | Pitch-deck processing | Webhook → validation → Drive/Gmail pipeline, 24 nodes (Lead Generation) | Lead Generation | https://n8n.io/workflows/9503 |

IDs 6552–13139 surfaced as "template evidence" in an independent n8n AI-patterns research doc — treat as notable, re-verify each page before citing details.

---

## 3. AI-agent-focused picks (tutorial gold)

1. **#6270 Build your first AI agent** — the canonical beginner on-ramp; free Gemini key, 2-minute setup. Perfect "your first agent in 10 minutes" post.
2. **#5010 RAG Starter** — simplest possible RAG (Simple Vector Store, no infra). Ideal base for "RAG in n8n explained" + "how to swap in Qdrant/Supabase for production."
3. **#10450 LinkedIn dual-agent** — shows the compound-agent pattern (frontend agent calling a backend workflow as a Tool via Execute Workflow trigger). Great "multi-agent" tutorial.
4. **#2339 Qdrant study-notes** — full ingest→vectorize→generate loop with Mistral; includes an Ollama/local variant link. Ties into the Qdrant version-breakage pain point.
5. **#4804 Proposal generator** — freelancer/agency money workflow; form → LLM → document → email → payment. Strong "sell this as a service" angle.
6. **#6552 Email triage** — the classic AI-agent-meets-inbox pattern (classify → route → Trello).
7. **#10150 Lead routing + #11854 ticket triage** — pair as "AI lead-qualification" content (matches community pain-point research).
8. **#11911 Invoice processing** — vertical AI use case with human-approval gate potential.
9. **#3446 Newsletter service** — scheduled AI digest; easily remixed (swap Outlook→Gmail, Excel→Sheets, templates→any RSS).
10. **#13154 Moderation** — trust/safety automation; timely with 2026 agent-safety news cycle.

---

## 4. Architecture notes (from detail pages read)

### #10450 — LinkedIn posts (dual-agent)
Chat Trigger → **AI Agent ("LinkedIn Agent")** + Simple Memory (10 msgs) + Mistral Chat Model + **Tool = Execute Workflow trigger** ("template" tool). The tool invokes a backend flow: Switch node routes template 1–7 → Set nodes hold large structured prompts (tone rules, forbidden phrases) → second **AI Agent ("post generator")** writes the post → returns via tool to chat.
*Pattern to teach: frontend router agent + backend specialist agent as a tool.*

### #5010 — RAG starter
Form Trigger (upload PDF) → **AI Agent** + Simple Vector Store (ingest via Default Data Loader) + Embeddings OpenAI. Zero config; agent answers from the uploaded doc.
*Pattern to teach: minimal RAG; then "productionize" by swapping Simple Vector Store → Qdrant/Supabase/Pinecone.*

### #2339 — Study notes (Qdrant + Mistral)
Local File Trigger watches a folder → extract text → vectorize into **Qdrant** → series of template prompts "research" the KB → export study guide/briefing/timeline to folder. Requires self-hosted n8n + Qdrant + Mistral key; author also ships an Ollama variant.
*Pattern to teach: file-triggered RAG pipelines; local-model variant for $0 cost.*

### #4804 — Proposal generator
Form Trigger (deal fields) → GPT-4 with example-based prompts → duplicate Google Slides template → `{{variable}}` replacement → Gmail delivery; premium branch uses PandaDoc for signature + payment.
*Pattern to teach: AI document assembly; template-variable replacement; proposal→payment in one flow.*

### #3446 — Newsletter service
Schedule Trigger → read Excel subscribers → dedupe categories → HTTP fetch latest n8n templates → AI summarize → HTML node builds email → Outlook sends. Dedupes "seen before" templates per subscriber.
*Pattern to teach: scheduled digests; dedup tables; swapping any source/destination.*

### #6270 — First AI agent
Chat Trigger → **AI Agent** + Gemini model + 2 tools (OpenWeather via HTTP, RSS news reader) + Conversation Memory. Setup = paste one Gemini API key.
*Pattern to teach: agent + tools + memory in 4 nodes; adding Gmail/Calendar tools next.*

---

## 5. Blog post ideas mapped from these workflows

1. **"Your First n8n AI Agent in 10 Minutes (Free Gemini Key)"** — rebuild #6270, add a Gmail tool; beginner on-ramp post.
2. **"RAG in n8n Explained: From the Starter Template to Production"** — start from #5010, swap Simple Vector Store → Qdrant, add chunk-size guidance.
3. **"I Rebuilt n8n's LinkedIn Agent Workflow — Here's the Multi-Agent Pattern Worth Stealing"** — deep-dive #10450's frontend-router + backend-writer tool pattern.
4. **"How to Build a WhatsApp AI Sales Agent in n8n (Lead Scoring 0–100)"** — inspired by #10150 + community WhatsApp pain points; webhook → agent → Sheets/CRM + Slack alert.
5. **"AI Invoice Processing with n8n: Email → OCR → Approval Gate → QuickBooks"** — extend #11911 with human-in-the-loop.
6. **"Self-Hosted RAG for $0: n8n + Ollama + Qdrant (No API Keys)"** — remix #2339's Ollama variant as the free-stack tutorial.
7. **"The n8n Proposal Generator Freelancers Charge $2,000 For"** — rebuild #4804 with cost breakdown; agency-monetization angle.
8. **"AI Email Triage in n8n: Classify, Route, Draft Replies"** — rebuild #6552; pairs with Gmail/Outlook categories.
9. **"Build a Daily AI Newsletter on Autopilot"** — remix #3446 (any RSS/API source → AI summary → email/Telegram).
10. **"10 Copy-Paste n8n Workflows for Freelancers"** — roundup post linking the library templates above, one persona, one use case each.

---

## 6. Weekly re-check procedure (for the Monday scan)

1. Open https://n8n.io/workflows and note the total workflow count in the title (was 12,795 on 2026-09-30) — a jump signals new publishes.
2. Check n8n's official channels for newly featured templates: the n8n blog (blog.n8n.io) "templates" posts and the community forum "Built with n8n" / "Show and tell" categories.
3. Search the library for trending AI topics: `AI agent`, `MCP`, `RAG`, `WhatsApp`, `voice agent` — look for templates with recent "Last update" dates.
4. Watch for newly published templates around breaking changes (e.g. n8n 3.0 node migrations) — these are timely tutorial opportunities.
5. When a promising new template appears: open its detail page, record id/title/category/URL/architecture in section 2/3 format, and append it to this file with the date.
6. Also track the n8n changelog (docs.n8n.io changelog) for new nodes — new nodes usually get demo templates within days.
