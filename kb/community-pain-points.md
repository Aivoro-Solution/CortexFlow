# Community Pain Points — Blog Topic Research

**Date:** 2026-09-30
**Purpose:** Real problems people struggle with (n8n, AI agents, self-hosting) → blog tutorial ideas for AgentCraft.
**Sources scanned:**
- n8n Community → Questions category (~30 recent topics, Sept 2026) — https://community.n8n.io/c/questions/
- n8n Community → Latest (~30 topics incl. Jobs, Tips & Tricks) — https://community.n8n.io/latest
- GitHub n8n-io/n8n issues: 30 most recent mentioning langchain/AI + 15 most-commented AI-agent issues + 10 most-commented webhook/self-hosted issues (~55 issue titles, API)
- Reddit r/n8n, r/AI_Agents, r/automation: ~10 high-engagement threads (via web search — reddit.com HTML is blocked for direct fetch; re-check via browser task)
- r/selfhosted + self-hosting guides: via web search (gotcha docs, upgrade guides)

**Coverage note:** Reddit direct access was blocked during this scan; Reddit findings below come from indexed thread summaries. Re-verify via a browser session on the weekly re-scan.

---

## Theme 1 — WhatsApp Trigger production webhooks not registering / changing URLs

- **Sources:** n8n Community Questions (3 separate threads on 2026-09-29: "production webhook not registered on n8n Cloud" ×2, "Whatsapp trigger issuse"); GitHub #19037 "Whatsapp Trigger - Production URL is changing after some hours active" (15c), #14290 "WhatsApp Business Cloud AI tool broken — Invalid URL" (26c)
- **Frequency/severity:** HIGH — recurring, production-breaking, asked repeatedly within a single day.
- **Problem:** WhatsApp triggers work in test mode but the production webhook never registers on n8n Cloud, or the production URL silently changes hours after setup. Related gotcha from Reddit: WhatsApp needs a separate `POST /{WABA_ID}/subscribed_apps` step even after webhook verification, which nobody documents in one place.
- **Blog post idea:** "How to Build a WhatsApp AI Chatbot with n8n (Without the Webhook Headaches)" — angle: the free-stack tutorial (Meta Cloud API + n8n AI Agent + RAG) that explicitly covers production-vs-test webhook registration, the subscribed_apps step, and URL-change fixes. (Already on the content plan — bump priority.)
- **Links:** https://community.n8n.io/c/questions/ · https://github.com/n8n-io/n8n/issues/19037 · https://github.com/n8n-io/n8n/issues/14290

## Theme 2 — Webhook duplicates & non-idempotent retries cause duplicate side effects

- **Sources:** n8n Community Questions (2026-09-29: "How to deduplicate Shopify orders/create webhook triggers", "Retry failed n8n workflows without creating duplicate side effects", "Stop duplicate side effects on webhook retries"); GitHub #31837 "Webhook trigger firing multiple times" (18c)
- **Frequency/severity:** HIGH — 4 threads in one day on the forum alone; hits anyone doing e-commerce/payment webhooks.
- **Problem:** Webhooks (Shopify, Stripe, etc.) fire duplicates; n8n retries re-run side effects (double orders, double messages, double charges). Users don't know the dedup/idempotency-key patterns, and "execution says success" while the downstream system got hit twice.
- **Blog post idea:** "How to Deduplicate Webhooks in n8n (Idempotency Patterns That Actually Work)" — angle: dedup table pattern (Data Tables/Postgres), idempotency keys, and safe retry design with a downloadable workflow.
- **Links:** https://community.n8n.io/c/questions/ · https://github.com/n8n-io/n8n/issues/31837

## Theme 3 — AI Agent memory: lost context, polluted memory, provider-specific bugs

- **Sources:** GitHub #14361 "AI Agent doesn't store the Tool usages in memory" (56c — the most-commented AI issue), #22112 "AI Agent v3.0 stores full intermediate tool outputs in Redis Chat Memory (memory pollution)" (15c), #20335 "Claude 4.5 failing due to Postgres AI Memory Bug (Empty AI Message)" (15c)
- **Frequency/severity:** VERY HIGH — the #1 most-discussed AI-agent issue; memory is the single most confusing AI concept in n8n.
- **Problem:** Agents forget tool results between turns; v3 dumps entire tool outputs into memory blowing up context/cost; Postgres memory backend breaks Claude with empty messages. Users can't tell which memory backend to use or why their agent "forgets".
- **Blog post idea:** "n8n AI Agent Memory Explained: Window Buffer vs Redis vs Postgres (and 3 Bugs to Avoid)" — angle: plain-English memory guide with per-backend setup, the tool-usage memory gap workaround, and memory-pollution cost control.
- **Links:** https://github.com/n8n-io/n8n/issues/14361 · https://github.com/n8n-io/n8n/issues/22112 · https://github.com/n8n-io/n8n/issues/20335

## Theme 4 — AI Agent silently drops / mishandles tool calls

- **Sources:** GitHub #38870 "AI Agent tool responses intermittently return empty even though the tool executed successfully" (16c, team:ai assigned), #38503 "AI Agent V3 can lose canonical tool names and silently drop the next tool call" (8c), #24042 "Tool node errors fail workflow instead of returning error to agent for handling" (17c), #37916 "schema-invalid tool call terminates whole execution" (7c), #37779 "retryOnFail silently wipes tool-call context on Max Iterations" (4c), #37840 "Anthropic silently drops tools when systemMessage is large" (4c)
- **Frequency/severity:** VERY HIGH — a whole cluster of open, team-assigned bugs around tool-call reliability in 2026.
- **Problem:** The agent executes a tool fine, but the observation comes back empty; or a bad tool call kills the entire run instead of letting the model recover; or retries wipe the tool context. Debugging is miserable because executions report "success".
- **Blog post idea:** "Why Your n8n AI Agent Drops Tool Calls (Debugging Guide)" — angle: a systematic debugging checklist (observation empties, schema validation, max-iterations behavior, system-prompt size limits) with workarounds for each known bug.
- **Links:** https://github.com/n8n-io/n8n/issues/38870 · https://github.com/n8n-io/n8n/issues/38503 · https://github.com/n8n-io/n8n/issues/24042

## Theme 5 — MCP in n8n: setup confusion, auth pain, queue-mode breakage

- **Sources:** n8n Community Questions (2026-09-29: "MCP Server Trigger: Access to request headers", "MCP Server Trigger: Requiring re-auth" oauth2); GitHub #32278 "Cannot register local n8n mcp with my claude desktop connector" (12c), #26373 "Sub-agents unable to use MCP Tools due to Engine Request architecture" (15c), #26394 "MCP tool calls fail in queue mode" (13c), #39613 "MCP Server Trigger does not propagate downstream isError to MCP clients", #38232 "MCP Client Tool node ignores the MCP tool title"
- **Frequency/severity:** HIGH — MCP is the hottest 2026 topic and the n8n integration has sharp edges everywhere (auth, headers, queue mode, Claude Desktop).
- **Problem:** Users can't get request headers inside MCP-triggered workflows; OAuth re-auth loops; MCP tools break in queue/scaling mode; can't connect n8n's MCP server to Claude Desktop. Docs cover the happy path only.
- **Blog post idea:** "MCP + n8n: The Complete Troubleshooting Guide" — angle: companion to the "connect MCP server" tutorial — headers access, OAuth re-auth fixes, queue-mode workarounds, Claude Desktop registration, error propagation.
- **Links:** https://community.n8n.io/c/questions/ · https://github.com/n8n-io/n8n/issues/32278 · https://github.com/n8n-io/n8n/issues/26394

## Theme 6 — Qdrant vector store keeps breaking (versions, fetch failures, subpaths)

- **Sources:** GitHub cluster (Sept 2026): #38401 "Qdrant N8N update question" (19c), #38261/#38259/#38253/#38195/#38165 "fetch failed" duplicates, #37907 "bundled @qdrant/js-client-rest outdated vs Qdrant 1.19.x", #38890 "Qdrant URL subpath (reverse-proxy prefix) dropped by createQdrantClient"
- **Frequency/severity:** HIGH — a burst of duplicate issues shows a version-compat landmine; RAG builders hit it constantly.
- **Problem:** n8n upgrades break the Qdrant node ("fetch failed"), the bundled JS client lags Qdrant server versions, and reverse-proxy subpaths get dropped. Users can't tell whether it's their setup or a version mismatch.
- **Blog post idea:** "RAG in n8n: Qdrant vs Supabase vs Pinecone (2026)" — angle: honest vector-DB comparison for n8n RAG with a version-compatibility matrix and the fetch-failed fix checklist. Doubles as affiliate-adjacent content.
- **Links:** https://github.com/n8n-io/n8n/issues/38401 · https://github.com/n8n-io/n8n/issues/37907 · https://github.com/n8n-io/n8n/issues/38890

## Theme 7 — Self-hosted n8n fails silently (the ops checklist nobody has in one place)

- **Sources:** Reddit r/n8n — "What actually breaks when you run n8n self-hosted for 6+ paying clients on one VPS" (94 pts, 32c): queue mode + Redis fix, Postgres filling to 11GB of execution logs in 2 months (fix: EXECUTIONS_DATA_PRUNE), webhook URLs rotating on container restart (fix: pin N8N_WEBHOOK_URL), encryption keys dying with the server, HTTP node 300s timeout too short for LLM calls; "5 ways self-hosted n8n can fail silently" (20 pts): incomplete SQLite WAL backups, shallow health checks, disk cleanup ordering, lost encryption keys; n8n Community: "How do you catch a workflow that stops triggering entirely (no error, just no executions)?", "When a workflow quietly stopped in your own business, who noticed first?" (15 replies, 180 views)
- **Frequency/severity:** VERY HIGH — the most upvoted operational content in the niche; silent failures are the #1 self-hosting fear.
- **Problem:** Self-hosted instances die in ways that produce no alerts: disk full of execution logs, rotated webhook URLs, dead encryption keys, workflows that simply stop triggering with no error. No single checklist exists.
- **Blog post idea:** "Self-Hosted n8n Production Checklist: 12 Things That Break Silently (and Fixes)" — angle: the definitive ops checklist — pruning, pinned webhook URLs, key backups, health checks that actually check, execution-time monitoring. High-share potential.
- **Links:** https://www.reddit.com/r/n8n/comments/1sr7pni/what_actually_breaks_when_you_run_n8n_selfhosted/ · https://www.reddit.com/r/n8n/comments/1wcd1dv/5_ways_selfhosted_n8n_can_fail_silently_and_how/ · https://community.n8n.io/c/questions/

## Theme 8 — Postgres major-version upgrades break n8n ("database files are incompatible")

- **Sources:** n8n-hosting official README (Postgres 16→18 is breaking: "FATAL: database files are incompatible with server"); self-hosting renovate review (15 Postgres instances blocked on 16/17→18 migration); community: "Connecting to self hosted supabase's postgres db (docker)" (2,769 views)
- **Frequency/severity:** HIGH — every Postgres major release triggers a wave of broken self-hosted instances; PG 18 requires PGDATA env handling.
- **Problem:** Bumping the postgres image tag alone kills the database. Users need dump/restore or pg_upgrade with downtime planning, and n8n must stay offline during it. The official docs bury this.
- **Blog post idea:** "How to Upgrade Postgres for n8n Without Losing Data (16→17→18 Safe Path)" — angle: step-by-step dump/restore runbook with the guard checks, backup verification, and rollback plan.
- **Links:** https://github.com/n8n-io/n8n-hosting/blob/HEAD/docker-compose/withPostgresAndWorker/README.md · https://community.n8n.io/latest

## Theme 9 — N8N_ENCRYPTION_KEY loss = all credentials dead

- **Sources:** Reddit r/n8n threads (key "dies with the server if not backed up externally"); self-hosting gotcha docs: "Mismatching encryption keys" boot failure after one bad first boot, credentials showing `unset` after restart when the key changed; community: "n8n asks you to create an owner again after a redeploy" (database/volume mismatch)
- **Frequency/severity:** HIGH — catastrophic when it hits (total credential loss), and it hits beginners constantly.
- **Problem:** Users don't understand the encryption key is the single point of failure: lose it (or let it regenerate on a fresh volume) and every stored credential becomes undecryptable. First-boot mistakes permanently poison the instance.
- **Blog post idea:** "n8n Encryption Key Explained: Backup, Recovery & the Mistakes That Wipe Your Credentials" — angle: what the key does, where to store it, recovery runbook, and the first-boot trap.
- **Links:** https://github.com/getcolors/skills/blob/HEAD/n8n-single-node/SKILL.md · https://sliplane.io/blog/self-hosting-n8n-with-ai-assistant

## Theme 10 — Docker/Compose first-time setup traps

- **Sources:** n8n Community: "Which n8n Docker image/setup should we use for a new self-hosted deployment?"; guides: `n8nio/n8n` vs `docker.n8n.io/n8nio/n8n` registry confusion, `dnf install docker` not including the Compose v2 plugin (breaks every tutorial on fresh AWS boxes), WEBHOOK_URL deprecated in favor of N8N_WEBHOOK_URL, N8N_PATH trailing-slash 404s, subpath proxy asset 404s
- **Frequency/severity:** HIGH — the #1 beginner funnel; every wrong env var costs hours.
- **Problem:** Too many image registries, renamed env vars, and distro-specific missing plugins. Tutorials go stale fast and none cover the full env-var matrix (N8N_HOST, N8N_PROTOCOL, WEBHOOK_URL, N8N_PATH) in one place.
- **Blog post idea:** "n8n Docker Compose Setup: The 2026 Guide (Postgres + Worker + Redis Queue Mode)" — angle: one verified compose stack with every env var explained, registry guidance, and the 10 most common first-boot errors with fixes.
- **Links:** https://community.n8n.io/c/questions/ · https://github.com/n8n-io/n8n-hosting/blob/HEAD/docker-compose/withPostgresAndWorker/README.md

## Theme 11 — No clean dev → production promotion path

- **Sources:** n8n Community Questions (2026-09-29: "How can we promote a dev workflow to prod?", "How should workflow ownership be transferred when moving a dev workflow to production?"); knowledge-base find: draft-vs-published confusion is n8n's #1 beginner trap (production webhooks run the published version, never latest edits)
- **Frequency/severity:** MEDIUM-HIGH — every team/agency hits this; individuals hit the draft-vs-published variant.
- **Problem:** No built-in environments/promotion flow. Users hand-edit production, lose track of versions, or discover their "fix" never went live because they didn't publish. Ownership transfer between dev/prod instances is manual and error-prone.
- **Blog post idea:** "n8n Dev to Production: Environments, Versioning & Safe Promotion" — angle: practical workflow — export/import discipline, git backup of workflows, staging instance pattern, and the draft-vs-published mental model.
- **Links:** https://community.n8n.io/c/questions/

## Theme 12 — OAuth & credential management pain (scopes, re-auth, sharing)

- **Sources:** n8n Community Questions (2026-09-29: "Connect Salesforce Error — the requested scope is not allowed" oauth2, "How to centrally reuse tenant-scoped Microsoft Graph OAuth credentials across Outlook and Teams workflows?", "MCP Server Trigger: Requiring re-auth"); GitHub #39227 "Agent Builder: OpenAI credentials routed through OpenAI-compatible gateways break — provider prefix stripped"; Reddit: shared API key hitting a cap broke 5 workflows at once
- **Frequency/severity:** HIGH — OAuth threads are evergreen; credential architecture questions show teams scaling up.
- **Problem:** Scope errors with Salesforce/Microsoft, re-auth loops, no clean way to share tenant credentials across workflows, and gateway/proxy setups stripping provider prefixes. Plus blast-radius: one shared key caps out and kills everything.
- **Blog post idea:** "n8n Credentials Deep Dive: OAuth Scopes, Shared Credentials & Re-auth Fixes" — angle: per-provider OAuth troubleshooting (Salesforce, Microsoft Graph), credential sharing patterns, and key blast-radius hygiene.
- **Links:** https://community.n8n.io/c/questions/ · https://github.com/n8n-io/n8n/issues/39227

## Theme 13 — API rate limits & quotas kill production workflows

- **Sources:** n8n Community Questions (2026-09-29: production Google Drive "Quota exceeded for quota metric 'Queries'... drive.googleapis.com" — 239 views, 12 replies); Reddit: reused API key hit usage cap, broke 5 workflows
- **Frequency/severity:** MEDIUM-HIGH — every Google/OpenAI-heavy workflow eventually hits this in production.
- **Problem:** Workflows built on generous dev quotas die in production with cryptic quota errors. Users don't know about batching, backoff, quota projects, or per-key usage dashboards.
- **Blog post idea:** "Handling API Rate Limits in n8n (Google, OpenAI): Batching, Backoff & Quota Dashboards" — angle: production-hardening guide — SplitInBatches pacing, retry-with-backoff, separate quota projects, monitoring usage before it breaks.
- **Links:** https://community.n8n.io/c/questions/

## Theme 14 — No monitoring: failed executions go unnoticed

- **Sources:** n8n Community: "How do you catch a workflow that stops triggering entirely (no error, just no executions)?" + "When a workflow quietly stopped in your own business, who noticed first?" (180 views); Reddit: "5 ways self-hosted n8n can fail silently" (shallow health checks)
- **Frequency/severity:** HIGH — the "who noticed first?" thread resonated because everyone has lived it.
- **Problem:** n8n's default error handling is per-workflow and easy to miss; a workflow that stops triggering produces zero signal. Users need error workflows, heartbeat checks, and external uptime monitors but don't know the pattern.
- **Blog post idea:** "How to Monitor n8n: Error Workflows, Heartbeats & Alerts That Actually Wake You Up" — angle: the complete monitoring stack — global error workflow, heartbeat/dead-man's-switch pattern, execution pruning vs audit needs, external monitors.
- **Links:** https://community.n8n.io/c/questions/ · https://www.reddit.com/r/n8n/comments/1wcd1dv/5_ways_selfhosted_n8n_can_fail_silently_and_how/

## Theme 15 — AI agent cost blindness (token usage invisible)

- **Sources:** GitHub #38482 "OpenAI Node does not report token usage for image operations"; knowledge-base: n8n Gateway credits enable zero-API-key AI tutorials; community cost threads on execution-time growth ("Execution time grows up 3 times", 15 replies)
- **Frequency/severity:** MEDIUM — growing as agents move to production; cost surprises are a churn driver (ties to the "FinOps reckoning" trend).
- **Problem:** Users can't see what an agent run costs — token usage isn't surfaced per node/operation, image ops report nothing, and memory pollution (Theme 3) silently multiplies cost. Nobody teaches cost instrumentation.
- **Blog post idea:** "How Much Does an n8n AI Agent Really Cost? (Token Tracking Guide)" — angle: instrumenting cost per run — execution data, model pricing math, memory/caching levers, and a cost-per-run calculator template.
- **Links:** https://github.com/n8n-io/n8n/issues/38482

## Theme 16 — Expressions & paired-item errors confuse every beginner

- **Sources:** n8n Community Questions (2026-09-29: "Expression evaluation failed: Cannot resolve paired item after Extract from File", "Stuck on an edit field node"); GitHub #39746 "alwaysOutputData doesn't force output inside splitInBatches — execution silently ends with status success"
- **Frequency/severity:** HIGH for beginners — the paired-item model is n8n's steepest learning curve.
- **Problem:** "Cannot resolve paired item" after file extraction/branching; items disappearing inside loops with execution still reporting success. The mental model (items, pairing, contexts) isn't taught anywhere simply.
- **Blog post idea:** "n8n Items & Expressions: The Mental Model That Fixes 80% of Beginner Errors" — angle: visual explainer of items/pairing/$json/$input with the 5 most common errors and fixes. Evergreen SEO magnet.
- **Links:** https://community.n8n.io/c/questions/ · https://github.com/n8n-io/n8n/issues/39746

## Theme 17 — Community nodes can break core AI nodes (dependency conflicts)

- **Sources:** GitHub-attached report: Photon iMessage community node (n8nnodesimessage@1.0.1) breaks OpenAI Chat Model + AI Agent with "Cannot read properties of undefined (reading 'entries')" — reproducible, fixed only by uninstalling; npm dist-tag confusion (latest → 0.3.6 vs 1.0.1 available)
- **Frequency/severity:** MEDIUM — rare per node, but devastating and nearly undiagnosable when it hits.
- **Problem:** Installing a community node can silently break unrelated core/AI nodes via dependency conflicts. No isolation, confusing npm versioning, and the error message gives zero clue about the culprit.
- **Blog post idea:** "n8n Community Nodes: Safe Install Guide & Conflict Troubleshooting" — angle: vetting checklist, version pinning, the binary-search uninstall debug method, and backup-before-install discipline.
- **Links:** https://github.com/user-attachments/files/29678821/n8n-photon-openai-issue-report.pdf

## Theme 18 — Queue mode / scaling confusion (Redis, workers, runners)

- **Sources:** Reddit r/n8n: fix for loaded VPS is EXECUTIONS_MODE=queue with Redis; GitHub #26394 "MCP tool calls fail in queue mode"; community: "More than 1 CPU core allocation to runner not working", "Execution time grows up 3 times"
- **Frequency/severity:** MEDIUM-HIGH — everyone outgrows single-main mode eventually; queue mode has its own bug surface.
- **Problem:** Users don't know when they need queue mode, how Redis/workers/runners fit together, or that some features (MCP tools, sub-workflow data) behave differently in queue mode. CPU allocation to runners is opaque.
- **Blog post idea:** "n8n Queue Mode Explained: Redis, Workers & When to Scale (and When Not To)" — angle: decision framework + compose setup + the queue-mode-only bugs to watch for.
- **Links:** https://www.reddit.com/r/n8n/comments/1sr7pni/what_actually_breaks_when_you_run_n8n_selfhosted/ · https://github.com/n8n-io/n8n/issues/26394

## Theme 19 — Hiring demand signal: businesses can't find n8n builders

- **Sources:** n8n Community Jobs (2026-09-29): "Looking for an n8n Freelancer" (84 replies), "n8n developer for RFQ-to-quote prototype" (328 replies, 4,066 views), "Hiring n8n experts ongoing" (62 replies), "AI Automation Engineer" (47), "[HIRING] Multi-Agent B2B Lead Gen System | n8n + LangGraph" (37) — massive, sustained demand
- **Frequency/severity:** Market signal, not a pain point — but validates the niche and opens a content lane.
- **Problem (for readers):** Freelancers don't know how to position; businesses don't know what to ask for or what it costs.
- **Blog post idea:** "How to Get n8n Freelance Clients in 2026 (What Businesses Are Actually Hiring For)" — angle: mined from real job posts — the skills requested, pricing signals, and portfolio patterns. Also validates every tutorial as lead-gen for services.
- **Links:** https://community.n8n.io/latest

---

## Priority ranking (blog order suggestion)

**Write first (high pain × no good tutorial × niche fit):**
1. Theme 7 — Self-hosted n8n production checklist (silent failures)
2. Theme 3 — AI Agent memory explained + bug workarounds
3. Theme 1 — WhatsApp AI chatbot with n8n (webhook headaches included)
4. Theme 4 — AI Agent tool-call debugging guide
5. Theme 2 — Webhook deduplication / idempotency patterns

**Write second (strong SEO, evergreen):**
6. Theme 10 — n8n Docker Compose 2026 setup guide
7. Theme 16 — Items & expressions mental model
8. Theme 5 — MCP + n8n troubleshooting companion
9. Theme 14 — Monitoring/alerting guide
10. Theme 8 — Postgres upgrade runbook

**Write third (depth / authority builders):**
11. Theme 6 — Vector DB comparison for n8n RAG
12. Theme 12 — Credentials/OAuth deep dive
13. Theme 9 — Encryption key backup & recovery
14. Theme 11 — Dev → production promotion
15. Theme 18 — Queue mode explained
16. Theme 13 — Rate limits & quotas
17. Theme 15 — AI agent cost tracking
18. Theme 17 — Community node safety
19. Theme 19 — Freelance clients (audience/monetization post)

---

## How to repeat this scan (weekly re-check)

1. **n8n Community → Questions** (https://community.n8n.io/c/questions/): sort by Latest; scan the last 7 days of topics. Flag: any question asked 2+ times, threads with 8+ replies, anything tagged bug. Also glance at "Help me Build my Workflow" for recurring build patterns.
2. **n8n Community → Latest** (https://community.n8n.io/latest): check Jobs for demand signals (reply counts = market heat) and Tips & Tricks for what the community itself teaches (avoid duplicating; find what's missing).
3. **GitHub issues** (API, no auth needed): `GET https://api.github.com/search/issues?q=repo:n8n-io/n8n+type:issue&per_page=20&sort=created&order=desc` for newest; filter mentally for AI/langchain/MCP/webhook/self-hosted. Also `sort=comments&order=desc` monthly to catch heat. Note: the `label:node-langchain` filter returned no results as of 2026-09-30 — the label doesn't exist; search by keyword instead.
4. **Reddit** (r/n8n, r/selfhosted, r/AI_Agents, r/automation): sort by Top → past week. Direct fetch was policy-blocked on 2026-09-30; use a browser-task session or web-search snippets as fallback, and note the access method each run.
5. **Cluster & diff:** group new threads into the themes above; if 3+ new threads form a new theme, add it as Theme 20+ with date. Update the priority ranking if a theme spikes.
6. **Output:** append a dated "Re-scan YYYY-MM-DD" section at the end of this file with: new threads count, new/strengthened themes, and any priority changes. Keep the original themes intact for trend history.
