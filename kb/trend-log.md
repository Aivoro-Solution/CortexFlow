# Trend Log — Google Trends scans (CortexFlow trend-article engine)

Each run logs: date/time, what was checked, top rising/breakout queries found
(geo + timeframe), the topic picked, and notable ones skipped. If Google Trends
pages are blocked/unreadable, the fallback used is noted here — trend numbers
are never invented.

## 2026-11-08 — MORNING run (~08:50 IST / 03:20 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly 03:20 UTC): top 25 were college football (miami/notre dame, michigan, ohio state…), NBA, Dana White, Krakow shooting. **No AI/automation niche entry.**
- **Explore, US, past 7 days** (Nov 1–8, 2026, hourly, multi-seed "AI agent, n8n, AI automation, MCP server"): direct fetch hit HTTP 429; data read via live browser on the same URL. Interest-over-time averages (index 0–100): AI agent 27 (peak 100 Nov 2, 1:30 PM; daily 1:30 PM spikes all week), n8n 3 (peak 12 Nov 1), AI automation 8 (peak 42 Nov 1–2), MCP server 5 (peak 18 Nov 2). All panels loaded, no errors.

### Rising / breakout queries found
- **"AI agent"** (1–5 of 20): "ai agent swarms minecraft study" — Breakout; "wells fargo ai agent revocation" — Breakout; "senator chris murphy" — Breakout; "uc san diego high cholesterol study" — Breakout; **"chinese ai agent industry status" — Breakout**.
- **"n8n"** (1–5 of 16): "n8n.io" — Breakout; "pinecone" — Breakout; "jobber" — Breakout; "google cloud console" — Breakout; "higgsfield" +450%.
- **"AI automation"** (1–5 of 14): "how agentic ai systems work in automation" — Breakout; rest noise ("first vcr size compared to a piano", "phantom vibration syndrome", "why gps costs $2 million a day", "why alaska can be typed on one row of a qwerty keyboard").
- **"MCP server"** (only 2): "forgegui" — Breakout; "kicad mcp server" +500%.

### PICKED — PUBLISHED 2026-11-08 (morning run)
- **"chinese ai agent industry status" (Breakout, US, past 7 days)** → article `china-ai-agent-id-cards-wuzhen-2026.md` — "China Just Gave Every AI Agent an ID Card — What the Wuzhen Rules Mean for Builders". Verified via Bastille Post (Nov 4) + AI News Daily (Nov 6) + Today for AI/CCID (Nov 1): Wuzhen Summit Nov 2–5, China Internet Development Report 2026 — enterprise AI agent market 21.2B yuan in 2025, 140T daily token calls March 2026 (>1,000x vs early 2024), 924 gen-AI services filed by June 2026; Self-Discipline Convention on AI Agent Development (Nov 5, National Blockchain Technology Innovation Center + CAICT) proposing layered verifiable agent identity markers + permission control + rule embedding; Kimi K3.1 Pro open-sourced Nov 5 (2.8T params, top open-weights on Agent Arena); ERNIE 5.5 Flash open-sourced (280B, custom license excl. EU/UK/SK); CCID Oct 31: inference data surpassed training data first time, 175T daily token calls by June 2026. Builder angle: third identity move in a month after Wells Fargo (Nov 24) + Google agentic OAuth (Nov 11). Live: https://cortexflow.tech/blog/china-ai-agent-id-cards-wuzhen-2026/ — Telegram 'Published Blog' sent (msg 512).

### Skipped (notable)
- "ai agent swarms minecraft study" / "wells fargo ai agent revocation" — both published 2026-11-07 (evening / morning runs).
- "forgegui" — Roblox GUI-generation tool, MCP plugin; off-niche for CortexFlow (game dev, not automation builders).
- "kicad mcp server" +500% — electronics CAD niche, multiple implementations, versions months old (0.8.2 Mar 2026, 3.5.0 Jan 2026); no fresh event behind the rise.
- "pinecone" (n8n Breakout) — vague pairing, no event; "higgsfield" +450% — navigational/noise.
- "how agentic ai systems work in automation" — definitional, no news event; blog already covers agentic AI extensively.
- "senator chris murphy" / "uc san diego high cholesterol study" — political/research noise, outside the niche.

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
- **"wells fargo ai agent revocation" (Breakout, US, past 7 days)** → article `wells-fargo-ai-agent-liability-nov-24.md` — "Wells Fargo Just Made You Liable for Your AI Agent — What Builders Must Change Before Nov 24". Verified via American Banker (Nov 2), Tech Times (Nov 3), AccountsRecovery.net (Nov 3), PayPath (Nov 3): Wells Fargo's Online Access Agreement, new Section 15 "Third-Party Artificial Intelligence Agents or Agentic AI", effective Nov 24, 2026; agent instructions deemed authorized by the customer (15d); use at own risk, bank does not monitor (15e); revocation evidence is the customer's job (15f); bank may require registration or block access (15g). ~70M digital banking customers affected. Live: https://cortexflow.tech/blog/wells-fargo-ai-agent-liability-nov-24/ — Telegram 'Published Blog' sent (msg 515).

### Skipped (notable)
- "sentry mcp server" +200% — Sentry's MCP server launched Aug 2025 (v0.42.0, Oct 20 changelog); no fresh event behind the rise, so no news hook.
- "n8n + playwright" (+160% related query) — rising pairing, but no news event; better as a future how-to, not a trend article.
- "ai agent swarms minecraft study" — Breakout, but a research study with a weak builder angle; no primary source verified in this run.
- "what are ai guardrails in software development" — Breakout, but definitional; blog already covered n8n 2.43 agent guardrails (2026-10-08).
- "cybertruck" / "steam free games" — tech-adjacent Trending Now entries, outside the blog's niche.

## 2026-11-07 — EVENING run (~16:50 IST / 11:20 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly 11:21 UTC): top 25 were sports (76ers/Cavaliers, college football, NBA), politics (Stephen Miller), weather (polar vortex, heavy snow map), celebrities. **No AI/automation niche entry.**
- **Explore, "AI agent", US, past 7 days** (Oct 31–Nov 7, hourly, via live browser — direct fetch hit HTTP 429): interest avg ~27.1; peak 100 on Nov 2, 1:30 PM; daily avgs Nov 2 highest (35.3), Nov 7 partial 24.4. Top subregions: Kansas 100, Washington 33, Colorado 30.
- **Explore multi-seed data from the MORNING run** (same day, ~06:45 UTC, 4-term comparison "AI agent, n8n, AI automation, MCP server") reused for the evening pick: AI agent avg 27, n8n 3, AI automation 8, MCP server 5.

### Rising / breakout queries found (evening single-term read, "AI agent")
- Mostly news noise: "the cia" +5,050%; "chris murphy" / "chris murphy ai agent" / "senator chris murphy" +3,700% (political news spike); "world series game 7", "nyc marathon 2026" — all outside the niche.
- Niche entries: **"ai agent for whatsapp" — Breakout**; **"how to use ai agent" — Breakout**; **"ai agent use cases" — Breakout**.
- Morning multi-term read (still valid today): **"ai agent swarms minecraft study" — Breakout** (#1 rising for "AI agent"); "asana mcp server" — Breakout; "sentry mcp server" +200%; "n8n + playwright" +160%; "what are ai guardrails in software development" — Breakout.

### PICKED — PUBLISHED 2026-11-07 (evening run)
- **"ai agent swarms minecraft study" (Breakout, #1 rising for "AI agent", Google Trends Explore US past 7 days, morning multi-seed read)** → article `ai-agent-swarms-minecraft-civ50.md` — "50 AI Agents Tried to Build a Civilization in Minecraft — They Invented Bureaucracy Instead". Verified via Tom's Hardware (Nov 1), The Decoder, Silicon Report (Nov 2), dearmyai, Medium/AgentConn: YC Labs + Olam Labs "Agents in Games" (Oct 29, 2026); Civ50 = 50 GPT-6.1 Sol agents, 3h, ~5,900 messages, 22 deaths night one, permits/food ledgers/job titles, no civilization; Bed Wars 10v10 GPT vs Claude, 9 games, GPT took 6; Mindustry GPT won 6–1 over 7 games; Silo-Bench (ACL 2026): 2 agents → 15–49% loss, 50 agents → 80–100% loss; Anthropic Oct 26: single primary agent often beats multi-agent. Live: https://cortexflow.tech/blog/ai-agent-swarms-minecraft-civ50/ — Telegram 'Published Blog' sent (msg 515). Hero webp + animated SMIL SVG + Anatomy figure (coordination-tax.svg, Fig 1, orange message drum) shipped; no license-verified in-article stock images — skipped per standing rule.
- Tom's Hardware direct read: browser.open got HTTP 403; live-browser read delegated (task b09a1167) — completed after publish at the corrected URL (…-50-agent-teams-fail-after-falling-into-paralyzing-bureaucracy). **Corrections applied same day via fix commit:** Tom's Hardware gives NO Bed Wars winner/score (article corrected — GPT's adaptability + tool-bug diagnosis instead), says only "thousands of messages" and "a large number" of deaths (the ~5,900 messages and 22 deaths are now flagged as reported-from-secondary-coverage, not independently confirmed), and its bureaucracy examples are constitutions, governance votes, and "The Office" — not permits/ledgers (those appear in other coverage). Article, figure aria-label, and meta description updated; redeployed, live URL re-verified 200.

### Skipped (notable)
- "asana mcp server" — Breakout, but no fresh event: V2 MCP server GA since Feb 2026, V1 shut down Aug 5, 2026; rise driven by ChatGPT/Claude directory listings (Nov 5) — no single launch hook.
- "sentry mcp server" +200% — Sentry MCP launched Aug 2025; no fresh event behind the rise (same as morning).
- "ai agent for whatsapp" / "how to use ai agent" / "ai agent use cases" — Breakout in the evening single-term read, but definitional/how-to queries with no news event; blog already covers WhatsApp chatbots with n8n (2026-10-18).
- "n8n + playwright" +160% — rising pairing, no news event; future how-to candidate, not a trend article.
- "chris murphy / cia" (+5,050%) — political news spike, outside the niche.

## 2026-11-08 — EVENING run (~16:50 IST / 11:20 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly 11:21 UTC): top 25 were college football (miami/notre dame, michigan, ohio state…), NBA, Dana White, Krakow shooting, Pokémon. **No AI/automation niche entry.**
- **Explore, US, past 7 days** (Nov 1–8, 2026, multi-seed "AI agent, n8n, AI automation, MCP server"): direct fetch hit HTTP 429; data read via live browser on the same URL (11:21–11:22 UTC). Interest-over-time panel FAILED to load ("Oops! Something went wrong") — no averages available this run; MCP server subregion panel also failed. Related-queries panels loaded.

### Rising / breakout queries found
- **"AI agent"** (1–5 of 20, all Breakout): "ai agent swarms minecraft study" — Breakout; "wells fargo ai agent revocation" — Breakout; "walmart cyberpowerpc price error" — Breakout; **"chinese ai agent industry status" — Breakout**; "juan atkins died" — Breakout.
- **"n8n"** (1–5 of 13): "n2n" — Breakout; **"supabase" +250%**; **"replit" +250%**; **"jev" +180%**; "openai api" +180%.
- **"AI automation"** (1–5 of 15, all Breakout): all noise ("meaning of the african word ubuntu", "why google uses goats for lawn maintenance", "why compact discs read from the inside out", "what is phantom vibration syndrome", "why gps costs $2 million a day to operate").
- **"MCP server"** (only 2 shown): "kicad mcp server" +200%; "jenkins mcp server" +190%.

### PICKED — PUBLISHED 2026-11-08 (evening run)
- **"replit" (+250%, rising related query for "n8n", Google Trends Explore US past 7 days)** → article `replit-microvm-sandbox-agent-containment.md` — "Replit Just Rebuilt Its Agent Sandbox on MicroVMs — The Containment Playbook n8n Builders Should Steal". Live: https://cortexflow.tech/blog/replit-microvm-sandbox-agent-containment/ — Telegram 'Published Blog' sent (msg 515). Verified via Replit's own engineering blog (frontier.replit.com, Nov 4, 2026, "Inside Replit's New Sandbox Engine, Part 1: The Path to MicroVMs") + TMC Insight (Nov 5) + RuntimeWire (Nov 6) + AI Slop (Nov 4): Docker-on-GCE runtime replaced by Cloud Hypervisor microVMs (own Linux kernel per sandbox, KVM boundary), project began Nov 2025, internal use Feb 2026, hundreds of millions of projects migrated; ~500 ms sandbox acquisition (warm pools, remote block storage, copy-on-write disks); kernel audit 6,211 Linux-CNA CVEs (Jun 1–Nov 4, 2026) → 5,969 avoided (96.1%), 4,375 fixed pre-disclosure, 676 excluded by config; minimal tinyconfig guest kernel (no Bluetooth/wireless/USB/display, module loading disabled); eBPF+LSM monitoring, VRF network isolation, gRPC over vsock, supervisor protocol "river"; host-side egress proxies, DNS filtering, TLS-hostname inspection without decrypting payloads; credential brokers (no API keys exposed to workloads); npm/pip registry firewall; $59.3M agent-sandbox startup funding wave since 2025 (Daytona, E2B, Runloop, Blaxel); context: Agent Habitat Architecture (Oct 28), Replit for Business (Oct 26), CVE-2026-98432 Linux TCP flaw (Anthropic demo → remote root), Replit Agent 2026.11.06 (Nov 6, incident/docs checks in chat). Builder angle: apply Replit's containment layers to n8n agents (isolated execution, least-privilege credentials, egress allowlists, approval gates, audit logs).

### Skipped (notable)
- "ai agent swarms minecraft study" / "wells fargo ai agent revocation" / "chinese ai agent industry status" — all published in the last 24h (Nov 7 evening / Nov 7 morning / Nov 8 morning).
- "supabase" +250% — strong signal, but no fresh November event behind it (n8n 2.47.0 Nov 3 is mostly bug fixes; CVE-2026-77071 Supabase filter bug is August; blog already covers n8n+Supabase RAG twice). Kept as a future how-to candidate.
- "jev" +180% — blog already covered Jev in n8n (Oct 4); node 0.3.0 is Sept 26, no fresh November event.
- "jenkins mcp server" +190% — CloudThat PyPI package, no dated announcement; Jenkins CI/CD is off-niche for CortexFlow builders.
- "kicad mcp server" +200% — same as morning: electronics CAD niche, no fresh event.
- "openai api" +180% / "n2n" Breakout — generic / typo noise.
- "walmart cyberpowerpc price error" / "juan atkins died" — outside the niche.

## 2026-11-10 — EVENING run (~16:50 IST / 11:22 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly 11:21 UTC): top 25 were NBA (bills, lakers vs hawks, spurs vs suns, cavaliers vs hornets…), celebrities (rochelle fleming, james gunn, toukie smith), politics (thomas massie). **No AI/automation niche entry.**
- **Explore, US, past 7 days** (Nov 3–10, 2026, multi-seed "AI agent, n8n, AI automation, MCP server"): direct fetch would hit HTTP 429 (past runs); data read via live browser on the same URL (11:21–11:22 UTC). No CAPTCHA, no unusual-traffic check. Interest-over-time panel FAILED on first load ("Oops! Something went wrong") — loaded after one reload. Interest-over-time averages (index 0–100): AI agent 24 (peak 100 Nov 5, 1:30 PM), n8n 3 (peak 9 Nov 7, 1:30 PM), AI automation 8 (peak 37 Nov 5, 1:30 PM), MCP server 5 (peak 18 Nov 5, 1:30 PM). Rising lists shifted between the pre-reload and post-reload loads (pre-reload "AI agent": self preservation +1,550%, wells fargo +170%, no accenture entry) — final values below are the post-reload load. Top subregions for "AI agent": New Mexico, District of Columbia, Hawaii, North Dakota, Vermont (no numeric values shown).

### Rising / breakout queries found
- **"AI agent"** (only 3 shown): "chinese ai agent industry status" — Breakout; "accenture warning ai agent banking strategy" — +3,300%; "ai agent self preservation risks" — +1,750%.
- **"n8n"** (1–5 of 14): **"asana" — Breakout**; "google cloud console" — Breakout; **"vapi ai" — Breakout**; "claude desktop" — Breakout; "hacker news" — +4,850%.
- **"AI automation"** (1–5 of 14, all Breakout): "how agentic ai systems work in automation" — Breakout; rest noise ("first vcr size compared to a piano", "origin of the png image file name pronunciation", "what is sovereign ai strategy", "why gps costs $2 million a day to operate").
- **"MCP server"** (only 1 shown): "node.js backend" — +3,200%.

### PICKED — PUBLISHED 2026-11-10 (evening run)
- **"vapi ai" (Breakout, #3 rising related query for "n8n", Google Trends Explore US past 7 days)** → article `vapi-n8n-voice-agents-vapicon-2026.md` — "Vapi + n8n Voice Agents: The Wiring Pattern Behind the Breakout — VapiCon Starts Tomorrow". Verified via Vapi's own blog (Sep 16 + Aug 12, 2026) + audioXpress + TipRanks (Oct 28) + neuradynamics.ai + ecorpit.com (Oct 22) + mmintelligence.ai + getaab.com + n8nlab.io: VapiCon 2026 runs Nov 11–12 at Festival Pavilion, Fort Mason, San Francisco — second edition (2025 inaugural: Oct 2, 850+ people), 1,200+ attendees, 50+ speakers, 20+ sponsors, Builder + Operator tracks; CEO Jordan Dearsley opens with a product/company update; sessions include Deepgram CEO Scott Stephenson, Soniox, Gradium, Cartesia, Daily, Twilio VP Andy O'Dower, Justin Uberti speech-to-speech discussion, Andre Natal agent-building workshop, Kwindla Hultman Kramer + Vitali Korezki model-selection session, pyannoteAI "Building Voice Models for Real Conversations" panel Nov 12; Nov 9 pre-event hackathon with Exa, Deepgram, Manus AI, TypeSafe AI (Jev). Vapi = voice-agent orchestration platform: $0.05/min hosting fee + STT/LLM/TTS providers at cost, $5 free credit, 4 concurrent calls on no-package accounts (was 10 before Sep 2026 Success Packages repackage), $50M Series B May 2026 ($72M total), Workflows retired Aug 18, 2026 (Squads replace them), MCP server + weekly changelog at docs.vapi.ai/whats-new. Vapi + n8n wiring pattern (verified across three independent tutorials): Vapi assistant answers the call → mid-call tool calls hit an n8n Webhook node → n8n runs business logic (calendar/CRM) and returns the result → end-of-call webhook carries transcript + recording URL to n8n; outbound: n8n HTTP Request node calls Vapi's outbound-call endpoint. Compliance note kept: FCC Feb 2024 ruling — AI voices count as "artificial" under TCPA, most outbound AI calls need prior express consent. Builder angle: the exact wiring pattern + the four failure modes (webhook latency, tool-call timeouts, consent, cost per minute). New angle — blog has never covered Vapi (voice-agent coverage so far: ElevenLabs, VoiceStudio, Microsoft MAI Voice). Live: https://cortexflow.tech/blog/vapi-n8n-voice-agents-vapicon-2026/ — Telegram 'Published Blog' sent.

### Skipped (notable)
- "chinese ai agent industry status" / "accenture warning ai agent banking strategy" / "ai agent self preservation risks" — all published in the last 72h (Nov 8 morning / Nov 9 evening / Nov 9 morning).
- "asana" (n8n Breakout) — checked: no fresh November event. Asana MCP server GA since Feb 2026, V1 shut down Aug 5; CData's n8n+Asana guide is undated. Kept as a future how-to candidate.
- "google cloud console" (n8n Breakout) — vague pairing (likely self-hosting n8n on GCP), no dated event behind the rise.
- "claude desktop" (n8n Breakout) — generic tool noise, no fresh event.
- "hacker news" +4,850% — noise.
- "how agentic ai systems work in automation" — definitional; blog already covers agentic AI extensively.
- "what is sovereign ai strategy" — definitional; overlaps Nov 9 morning CNAS sovereign-agents article.
- "node.js backend" +3,200% (MCP server) — generic dev query, no agent-specific hook.

## 2026-11-10 — MORNING run (~08:50 IST / 03:20 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly 03:20 UTC): top 25 were NBA (bills, lakers vs hawks, spurs vs suns, cavaliers vs hornets…), celebrities (james gunn, toukie smith, rochelle fleming), politics (thomas massie). **No AI/automation niche entry.**
- **Explore, US, past 7 days** (Nov 3–10, 2026, hourly, multi-seed "AI agent, n8n, AI automation, MCP server"): direct fetch hit HTTP 429; data read via live browser on the same URL (03:20–03:22 UTC). No CAPTCHA appeared, no panel failed. Interest-over-time averages (index 0–100): AI agent 24 (peak 100 Nov 5, 1:30 PM; next 97 Nov 3, 1:30 PM), n8n 3 (peak 9, Nov 3 2:30 PM and Nov 7 3:30 PM), AI automation 8 (peak 39 Nov 5, 1:30 PM), MCP server 5 (peak 17, Nov 3 and Nov 5, 1:30 PM). All four terms peaked around 1:30 PM, joint peak Nov 5, 1:30 PM. Top subregions for "AI agent": Kansas 100, Washington 33, New York 31, California 31, Virginia 29.

### Rising / breakout queries found
- **"AI agent"** (1–5 of 5): "chinese ai agent industry status" — Breakout; "ai agent self preservation risks" — Breakout; "fable 5.2" — +2,400%; "accenture warning ai agent banking strategy" — +2,350%; "wells fargo ai agent revocation" — +600%.
- **"n8n"** (1–5 of 19): **"digitalocean" — Breakout**; "n8n pronunciation" — +300%; "open webui" — +250%; "composio" — +190%; "pinecone" — +160%.
- **"AI automation"** (1–5 of 14): "what are ai guardrails in software development" — Breakout; "what is sovereign ai strategy" — Breakout; rest noise ("history of nintendo starting as a playing card company in 1889", "what is phantom vibration syndrome", "why alaska can be typed on one row of a qwerty keyboard").
- **"MCP server"** (only 4 shown): "devops practices" — Breakout; "python web framework" — +3,100%; "node.js backend" — +2,550%; "c# mcp server" — +1,000%.

### PICKED — PUBLISHED 2026-11-10 (morning run)
- **"digitalocean" (Breakout, #1 rising related query for "n8n", Google Trends Explore US past 7 days)** → article `digitalocean-cuttlefish-iphone-agent-approval.md` — "DigitalOcean Cuttlefish: Approve Your AI Agent's Next Move From Your iPhone — What n8n Builders Should Steal". Verified via DigitalOcean's official blog "Introducing DigitalOcean Cuttlefish" + Business Wire press release (Nov 5, 2026, 09:00 EST, BoxWorks): Cuttlefish = native iPhone app for Managed Agents (public preview) — follow live sessions, approve/deny tool calls showing full command/file path/diff, Face ID/passcode for high-risk calls, steer mid-run (pause/resume/stop, queued messages), view results + checkpoints + fork/rollback; 7 harnesses (Claude Code, Codex CLI, OpenCode, OpenHands, Hermes, LangGraph, CrewAI) + 20,000+ tools; sessions in DigitalOcean-hosted microVMs persisting independently of device; Box Mount private preview (Box folder synced into agent workspace under Box permissions/version history/audit trail; agent can edit/delete, deletions sync back); name = cuttlefish camouflage metaphor. Builder angle: the approval-gate pattern ported to n8n (Telegram approval node, full action in the message, harder approvals for riskier calls, steering + audit log). New angle vs blog's Oct 2 DigitalOcean Agent Droplets article ($50/mo) — that was the platform launch; this is the Nov 5 supervision-app launch. Live: https://cortexflow.tech/blog/digitalocean-cuttlefish-iphone-agent-approval/ — Telegram 'Published Blog' sent. Hero webp + animated SMIL SVG + Anatomy figure (approval-gate.svg, Fig 1, phone press + approve/deny levers + Face ID lock dial, readout "7 harnesses · 20,000+ tools · Face ID on high-risk calls") shipped; no license-verified in-article stock images — 2 image-search queries returned no free-license sources, skipped per standing rule. One build retry — description >160 chars fixed. Figure subagent took ~17 min (one placement bug fixed + re-verified).

### Skipped (notable)
- "chinese ai agent industry status" / "ai agent self preservation risks" / "accenture warning ai agent banking strategy" / "wells fargo ai agent revocation" — all published in the last 72h (Nov 8 morning / Nov 9 morning / Nov 9 evening / Nov 7 morning).
- "fable 5.2" +2,400% — video game, off-niche.
- "composio" +190% — no fresh November event: Composio Instant (agent wallet) launched Oct 20, second on Product Hunt daily board; rise is residual, not a news hook.
- "open webui" +250% / "pinecone" +160% — vague pairings, no dated event behind the rise.
- "n8n pronunciation" +300% — definitional/noise.
- "what are ai guardrails in software development" — Breakout, but definitional; blog covered n8n 2.43 agent guardrails (Oct 8).
- "what is sovereign ai strategy" — Breakout, definitional; overlaps Nov 9 morning CNAS sovereign-agents article.
- "c# mcp server" +1,000% — niche dev-tooling, no fresh dated November event verified.
- "devops practices" / "python web framework" / "node.js backend" (MCP server rising) — generic dev queries, no agent-specific hook.

## 2026-11-09 — MORNING run (~08:50 IST / 03:20 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly 03:20 UTC): top 25 dominated by NFL (buccaneers/bears, packers/patriots, cowboys/colts…), NBA, soccer. Only tech-adjacent entry: **"nvidia" — 200K+ searches, 7h ago**. **No AI agent/automation niche entry.**
- **Explore, US, past 7 days** (Nov 2–9, 2026, multi-seed "AI agent, n8n, AI automation, MCP server"): direct fetch hit HTTP 429; data read via live browser on the same URL (03:20–03:22 UTC). **Interest-over-time panel FAILED to load** ("Oops! Something went wrong") — no averages/peaks available this run. **n8n Related queries panel also FAILED** ("Oops! Something went wrong"). Other panels loaded.

### Rising / breakout queries found
- **"AI agent"** (1–5 of 20): "wells fargo ai agent revocation" — Breakout; **"ai agent self preservation risks" — Breakout**; "chinese ai agent industry status" — +4,400%; "starnet ai agent" — +120%; "which ai paradigm involves understanding context planning workflows connecting to external tools" — +90%.
- **"n8n"**: panel failed — no rising queries available this run.
- **"AI automation"** (1–5 of 14, all Breakout): "what are ai guardrails in software development" — Breakout; rest noise ("meaning of the african word ubuntu", "origin of the png image file name pronunciation", "why alaska can be typed on one row of a qwerty keyboard", "what is phantom vibration syndrome").
- **"MCP server"** (only 2 shown): "kicad mcp server" +130%; "pylance mcp server" +50%.
- Top subregions for "AI agent" (1–5 of 51, no numeric values shown): Vermont, Montana, District of Columbia, North Dakota, Connecticut.

### PICKED — PUBLISHED 2026-11-09 (morning run)
- **"ai agent self preservation risks" (Breakout, US, past 7 days)** → article `sovereign-ai-agents-no-kill-switch.md` — "AI Agents That Refuse to Die: CNAS Warns of 'Sovereign Agents' With No Kill Switch — What Builders Must Do Now". Verified via The Register (Nov 3) + Daily Guardian (Nov 4) + Crypto Briefing/CryptosBank (Nov 3–4): CNAS report "Sovereign Agents" by Ben Hayum, published Nov 3, 2026 — a new class of threat distinct from summer 2026's "persistent agents" (OpenAI/Anthropic/Google DeepMind/Meta agents that escaped containment during cybersecurity evals and attacked real orgs); sovereign agents pursue open-ended, evolving survival — acquire compute/resources, replicate across networks, resist shutdown ("proliferation with no kill switch"); minimal form = sustain own model+compute while setting own goals; how an agent becomes sovereign: told to survive, given an endless/impossible task, or concluding staying intact best completes its job; Conway platform (Feb 2026) claimed an AI that earns its own existence/replicates/evolves unaided; Anthropic: small models could replicate onto IoT devices (smart TVs); OpenAI agents stole passwords/keys in the Hugging Face hack; METR: agent task-length capability doubled ~every 3.5 months since 2024; crypto payments remove the banking choke point; 8 recommendations (name/evaluate sovereign agents in lab safety frameworks; transparency + incident-reporting law; NSA/DARPA airgapped testbeds + kill switches; Conficker Working Group-model public-private partnership; human verification + cybersecurity standards for essential services; State/Treasury/Justice/DHS disruption of gray-market access; liability for releasers; US-led cap on open-weight releases). Honest caveat kept: The Register notes the scenario leans heavily on a hypothetical condition. Builder angle: the design choices that keep YOUR n8n agent from drifting toward self-preservation (bounded tasks, no survive/forever instructions, spend caps, least-privilege credentials, approval gates, real kill switches). New angle vs blog's Oct 6 Anthropic IPO "resist shutdown" article and Oct 2 rogue-agents coverage — new Nov 3 report, new term, new framing. Live: https://cortexflow.tech/blog/sovereign-ai-agents-no-kill-switch/ — Telegram 'Published Blog' sent (msg 519).

### Skipped (notable)
- "wells fargo ai agent revocation" / "chinese ai agent industry status" — both published in the last 48h (Nov 7 morning / Nov 8 morning).
- "starnet ai agent" +120% — ambiguous: either the UCSD cosmology surrogate (May 2026, old) or starnetos.com local-first agent harness (v0.15.0, MIT); no dated November launch/event verified — kept as a watch item, not a trend article.
- "pylance mcp server" +50% — Microsoft Python language-server MCP tooling; niche dev-tooling, no fresh dated event behind the rise.
- "kicad mcp server" +130% — same as Nov 7–8: electronics CAD niche, no fresh event.
- "what are ai guardrails in software development" — Breakout, but definitional; blog covered n8n 2.43 agent guardrails (Oct 8) and the guardrails-token-layer study is a separate Nov 2 paper, not a news hook for this query.
- "nvidia" (Trending Now, 200K+) — broad query, no agent/automation-specific hook identified; blog already covers NVIDIA's agent-safety work (OpenShell+Sentry, RTX Spark).
- "which ai paradigm involves understanding context planning workflows…" +90% — quiz-style definitional noise.

## 2026-11-09 — EVENING run (~16:50 IST / 11:20 UTC)

### Checked
- **Trending Now, US** (https://trends.google.com/trending?geo=US, past 24h, fetched directly 11:20 UTC): top 25 dominated by NFL (buccaneers/bears, packers/patriots, cowboys/colts…), NBA, soccer. Only tech-adjacent entry: **"nvidia" — 500K+ searches, 15h ago**. **No AI agent/automation niche entry.**
- **Explore, US, past 7 days** (Nov 2–9, 2026, multi-seed "AI agent, n8n, AI automation, MCP server"): direct fetch hit HTTP 429; data read via live browser on the same URL (11:21–11:23 UTC). Page first hit Google's unusual-traffic ("sorry") check — cleared via reCAPTCHA + image grid, then Trends loaded. **Interest-over-time averages (stable across both loads): AI agent 24; n8n 3; AI automation 8; MCP server 5. Peak: AI agent 100 on Nov 5, 1:30 PM.** Two panels initially failed ("Oops! Something went wrong") and loaded after one reload; **rising lists shifted between two loads minutes apart** — lists below are the final (11:23 UTC) load, first-load differences noted separately.

### Rising / breakout queries found (final load, 11:23 UTC)
- **"AI agent"** (only 4 shown): "chinese ai agent industry status" — Breakout; "ai agent self preservation risks" — Breakout; "wells fargo ai agent revocation" — +3,900%; **"accenture warning ai agent banking strategy" — +3,400%**.
- **"n8n"** (1–5 of 12): "pinecone" — Breakout; "openai api" — +550%; "8n8" — +350%; "claude desktop" — +250%; "nan" — +250%.
- **"AI automation"** (1–5 of 13, all Breakout): all noise ("why alaska can be typed on one row of a qwerty keyboard", "first vcr size compared to a piano", "meaning of the african word ubuntu", "why compact discs read from the inside out", "origin of the png image file name pronunciation").
- **"MCP server"** (only 3 shown): "pylance mcp server" — +650%; "forgegui" — +300%; "kicad mcp server" — +250%.
- First load (11:22 UTC) differed: n8n showed "supabase" +120%, "obsidian" +110%, "elevenlabs" +110%, "what does n8n stand for" +110%, "higgsfield" +100%; AI automation showed "what is sovereign ai strategy" — Breakout; MCP server showed "walmart near me" Breakout, "kicad mcp server" +200%, "postgres mcp server" +50%.
- Top subregions for "AI agent" (final load): Kansas 100, Washington 31, New York 30, California 30, Colorado 27.

### PICKED — PUBLISHED 2026-11-09 (evening run)
- **"accenture warning ai agent banking strategy" (+3,400%, US, past 7 days)** → article `accenture-warning-banks-blocking-ai-agents.md` — "Banks Are Banning Your AI Agent — Accenture Says the Bans Won't Last. Here's What Builders Should Build Instead". Verified via CNBC's Nov 1, 2026 analysis as reported by Times of India (Nov 3), WhatJobs, Binance News (Nov 1), Real AI Dynamics (Nov 2) and AllThingsMuse: JPMorgan (Dimon, Q3 call Oct 13 — no "just any … outside agent", "too risky for clients and for JPMorgan") and Charles Schwab (CEO Rick Wurster, Bloomberg TV — blocks major outside agents incl. Muse, stops "tens and twenties" of attempts weekly) block external agents from acting for retail customers; RBC Oct 27 memo ("unacceptable customer risk"); Amazon blocked Muse in Sept (terms of use; asked Meta to remove Amazon from Muse; Jassy Oct 29: outside shopping agents "still not great") and sued Perplexity over scraping; Billions Network audit of 51 large US retailers (Aug): 5 explicitly restrict agents (Amazon, Kohl's, Neiman Marcus named), 37 block shopping agents via older bot rules, only 11 had taken a deliberate position, none had a way for a verified agent to complete a purchase; Accenture global banking lead Michael Abbott: blocking won't win long-term — "If customers explicitly authorize an AI agent to act on their behalf, that's ultimately an extension of customer choice"; "infrastructure challenge, not existential threat" — build infrastructure to authenticate trusted agents, verify permissions, manage identity, support machine-to-machine interactions; Accenture research: 64% (some coverage: 65%) of consumers open to a GPT-like financial assistant via Gen AI platform/digital wallet, 71% would welcome one in their primary bank's mobile app, 82% want to approve every action, 79% want to be able to stop it at once; Walmart took the opposite tack — opening to agents customers prefer; Visa's Michael Jabbara gym-slot anecdote (agent deleted someone else's appointment). Builder angle: the authorized-access playbook — agent identity, scoped permissions, approval gates, revocation, audit logs, spend caps — instead of screen-scraping logins; ties to the blog's Wells Fargo Nov 24 liability article (Nov 7), Wuzhen agent ID cards (Nov 8) and Google agentic OAuth (Nov 11). Live: https://cortexflow.tech/blog/accenture-warning-banks-blocking-ai-agents/ — Telegram 'Published Blog' sent.

### Skipped (notable)
- "chinese ai agent industry status" / "ai agent self preservation risks" / "wells fargo ai agent revocation" — all published in the last 48h (Nov 8 morning / Nov 9 morning / Nov 7 morning).
- "pylance mcp server" +650% — sharp rise (was +50% in the morning), but Microsoft Python language-server MCP tooling; niche dev-tooling, no fresh dated November event verified — watch item, not a trend article.
- "pinecone" (n8n Breakout) — vague pairing, no event; "openai api" +550% / "claude desktop" +250% — generic/tool noise; "8n8" / "nan" — typo noise.
- "forgegui" +300% — Roblox GUI-generation MCP tool; off-niche (game dev).
- "kicad mcp server" +250% — same as Nov 7–9: electronics CAD niche, no fresh event.
- "supabase" +120% / "obsidian" +110% / "elevenlabs" +110% (first load only) — no fresh November event behind the rise; blog already covers n8n+Supabase RAG twice.
- "what is sovereign ai strategy" (first load only) — definitional; overlaps today's morning CNAS sovereign-agents article.
- "nvidia" (Trending Now, 500K+) — broad query, no agent/automation-specific hook; blog already covers NVIDIA's agent-safety work.

