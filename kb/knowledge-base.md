# AI Blog Knowledge Base — Docs Deep-Read

> Built 2026-09-30 from systematic reads of n8n docs, Docker docs, and LangChain docs.
> Versions reflected: **n8n 2.40** (3.0 scheduled Oct 2026) · **Docker Compose spec, v5 era** · **LangChain v1 (~1.3.x)**.
> All concepts paraphrased — this is a reference, not a copy of the docs.
> Re-check these sources weekly; see `weekly-check-instructions.md`.

---

## 1. n8n — Core (docs.n8n.io)

### Workflows & executions
- A workflow is nodes on a canvas. n8n **auto-saves every few seconds**, but nothing goes live until you **Publish**. Production runs (webhooks, schedules, app triggers) use the *published* version, never your latest edits. Publishing is asynchronous — unchanged triggers keep running during a publish.
- **Tutorial gold:** the #1 beginner confusion ("I changed my workflow but the webhook still does the old thing") is answered by the draft-vs-published model.
- Two execution modes: **Manual** (click Execute Workflow on canvas) and **Production** (trigger + published workflow). **Partial executions** ("Execute step" on one node) re-run only that node and its upstream — requires a trigger node on the canvas (Manual Trigger works).
- **Quota counting (paid Cloud/self-hosted):** only *production* executions count. Schedule trigger = 1 per fire regardless of outcome; polling triggers = 1 only when new data found; webhooks = 1 per inbound request; **sub-workflow and error-workflow runs don't count separately**. One agent *turn* = one execution.
- **Dirty nodes** = changed since last execution; affects partial-run behavior. **Debug executions** let you paste a past execution's data into the current workflow for debugging.

### Flow logic
- **Execution order (version gotcha):** pre-1.0 = round-robin level-by-level; **1.0+ = branch-by-branch, topmost-to-bottommost by canvas position**. Order is changeable in workflow settings.
- **Error handling:** set an **error workflow** per workflow in Workflow Settings; it must start with the **Error Trigger** node; one error workflow is reusable across many workflows. Payload includes `execution.id/url`, `error.message`, `lastNodeExecuted`, `workflow.name`. **Stop And Error** node forces failure on purpose.
- If/Switch split branches; **Merge** node rejoins them.

### Expressions & Code node
- Expressions use `{{ }}` (handlebars-ish JavaScript). Key built-ins: `$json` (current item), `$('NodeName')` (other nodes), `$input`, `$fromAI()`. Docs recommend the **Edit Fields (Set) node** over complex inline expressions.
- Multi-statement expressions need an IIFE: `{{(()=>{...})()}}`. Luxon `DateTime` built in. Expressions work inside credential fields too.
- Common beginner errors: "Referenced node is unexecuted" (run the upstream node first), invalid JSON in JSON mode.
- **Code node:** secure-mode task runners default since n8n 2.0. In **3.0**, `N8N_RUNNERS_TASK_TIMEOUT` drops 300s→60s.

### Data pinning
- Freeze a node's output during development so manual runs reuse it — no repeated API calls, no burned rate limits. **Production executions always ignore pinned data** (it never leaks). Limits: single main-output nodes only; **binary data can't be pinned**.
- Mock-data approaches: Code node, Edit Fields node, Customer Datastore node — then pin the result.

### Credentials
- Securely stored, testable on save. Types: **Fixed** (same credential every run) vs **End-user credential** (each user's own OAuth). **Allowed HTTP Request Domains** (All / Specific / None) blocks credential leakage when a credential is reused inside a generic HTTP Request node. Use a naming convention for credentials.

### Gateway credits (new, 2.36.0)
- Cloud Starter/Pro only: run AI models/services **without your own API keys** — n8n routes through its own gateway and bills a prepaid balance. Per-node switchable with your own credentials. Tutorial angle: zero-friction on-ramp for AI workflow tutorials.

---

## 2. n8n — AI ("Integrate AI", formerly /advanced-ai/)

> NOTE: `/advanced-ai/` now 404s — content moved to `/build/integrate-ai/`.

### AI Agent node (the flagship)
- One AI Agent node; attach a **chat model sub-node + at least one tool sub-node**. The model decides which tools to call. Loop: setup run → tool call run → evaluate → final answer.
- **Major gotcha:** the old "agent type" setting (Tools, SQL, Conversational, ReAct…) is **deprecated since 1.82.0** — everything is Tools Agent; **non-Tools modes removed in n8n 3.0**. Old SQL Agent use case → Postgres/MySQL tool sub-node + AI Agent node.
- Node v3 adds **"Force Tool Call on First Iteration"** (2.40) — fixes small models (Mistral-Small, Ollama, vLLM) that answer in prose and skip tools.
- **Cluster nodes** = root node (AI Agent, vector store, chain) + sub-nodes attached beneath (chat models, memory, tools, embeddings, retrievers, loaders, splitters, output parsers). Tutorial writers must show the "attach sub-node" UI pattern.
- **Memory sub-nodes attach only to the AI Agent root node, never to chains.**

### Tools
- Built-in tool nodes plus three powerful ones: **Call n8n Workflow Tool** (any workflow becomes a tool — the key "sub-workflows as tools" pattern), **Custom Code Tool**, **HTTP Request Tool**.
- **MCP servers registry:** one-click connect to registry MCP servers, n8n auto-creates an MCP credential; choose tools (all / allowlist / denylist). Choice guide: **built-in tool** = tightly scoped, you pin parameters; **MCP server** = broad action range at the cost of control and context.
- **$fromAI():** `{{ $fromAI('key', 'description', 'type', 'defaultValue') }}` — lets the model fill tool parameters dynamically. Only works for tool sub-nodes on the AI Agent node.

### Memory
- Simple Memory (easiest, fixed-length chat history), Redis/Postgres Chat Memory, Xata; advanced **Chat Memory Manager** node. **Agents (new first-class kind)** have **session memory** (on by default) and **episodic memory** (recalls earlier sessions; needs an OpenAI credential).

### RAG patterns
- Recipe: fetch source data → **Vector Store node (Insert Documents)** + embedding model + **Default Data Loader** with text splitter (**Recursive Character Text Splitter** recommended; 200–500 token chunks for fine-grained retrieval) + optional metadata.
- Query two ways: (1) **vector store as a tool** attached to an agent (same embedding model as ingestion); (2) vector store node directly with **Get Many**. Pro tip: **Vector Store Question Answer tool** in front of the Agent saves tokens on expensive models.
- n8n supports **text embeddings only**. Official **RAG Starter Template** exists (upload + query workflows).

### Evaluations
- Philosophy: LLMs are black boxes — measure, don't reason. **Light evaluation (pre-deployment):** small hand-made dataset, visual comparison, big iteration gains. **Metric-based (post-deployment):** large dataset from production executions, expected outputs + numeric metric, regression-test on every fix.

### Human-in-the-loop
- Per-tool approval: workflow pauses, reviewer approves/denies via **Chat, Slack, Discord, Telegram, Teams, Gmail, WhatsApp Business Cloud, Google Chat, Outlook** (approval channel can differ from the main channel). `$tool.name`/`$tool.parameters` build the review message. **Document the review setup in the agent's system prompt** or it mishandles denials.

### "Build and manage agents" (NEW, in Preview) — first-class agents
- Agent Builder: Model, Instructions (system prompt), Tools (built-in, workflows, custom JSON-schema tools, MCP servers), **Skills** (reusable instruction+tool bundles), Web search (native or Brave/SearXNG fallback), Knowledge base (upload files), Memory (session + episodic), **Sub-agents** (delegate to published agents), Channels (Slack, Telegram, Linear), Schedules (cron).
- Draft/publish model like workflows. **Message an Agent** node for agent-in-workflow or messaging published agents.
- **Gotchas: queue mode not yet supported for agents;** self-hosted needs `N8N_ENABLED_MODULES=agents` (+ `instance-ai` for AI-assisted building, public `WEBHOOK_URL` for channels).

### LangChain mapping & LangSmith
- Chain→root, Agent→root, Language model→sub-node, Memory→sub-node (agent only), Tool/Retriever/Embeddings/Loader/Parser/Splitter→sub-nodes.
- **LangSmith tracing works on self-hosted only** (not Cloud): `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_ENDPOINT`.

---

## 3. n8n — Hosting ("Host n8n", formerly /hosting/)

> NOTE: `/hosting/` moved to `/deploy/host-n8n/`.

### Install options
- One-line: `curl -fsSL https://get.n8n.io | sh`. Docker Compose guide ships the **n8n Assistant sandbox stack** (sandbox-api, privileged sandbox-runner, searxng). **Daytona recommended for production** sandboxes.
- Default DB is SQLite inside the container; **Postgres required for real production**. **Gotcha: Postgres 18 changed its default data dir — must set `PGDATA`**, else the volume misses and the DB starts empty. Major-version upgrades need `pg_dumpall`.
- **npm/npx install deprecated from n8n 3.0** — Docker becomes mandatory.

### Env vars & config (~25 categories)
- Key areas: Executions (timeouts, pruning), Queue mode, Security, SSRF protection, Task runners, Endpoints (webhook paths, base URL), **Deployment (encryption key — share `N8N_ENCRYPTION_KEY` across all workers or credentials become unreadable)**, Database, Logs, OpenTelemetry.
- Security checklist from Compose guide: never expose privileged sandbox-runner, rotate secrets, lock mTLS keys to 0600, firewall only n8n's port.

### Queue mode (scaling)
- Architecture: **main instance** (timers, webhooks, UI/API) → **Redis** (Bull queue) → **worker processes** (`EXECUTIONS_MODE=queue` + Postgres; SQLite unsupported). Separate **webhook processors** (`n8n webhook`) for inbound HTTP scale, behind a load balancer: `/webhook/*` and `/webhook-waiting/*` to the webhook pool, everything else to main; **don't put main in the LB pool**.
- Worker concurrency: `n8n worker --concurrency=N`, default 10 (n8n recommends ≥5; low concurrency × many workers exhausts the DB pool).
- **2.34+ gotcha:** large webhook responses in queue mode travel worker→main inside a Redis message (default cap 64 MiB via `N8N_WEBHOOK_RESPONSE_RELAY_SIZE_MAX`); offload-to-storage option needs shared S3/Azure/filesystem binary storage. **Filesystem binary storage is not supported in queue mode** — use S3.

### Database
- Default SQLite (`~/.n8n/database.sqlite`). Postgres: latest two active majors (17, 18 as of mid-2026) + one compatibility major (16); shifts every November. Aurora = experimental; CockroachDB/YugabyteDB/AlloyDB unsupported.
- Env: `DB_TYPE=postgresdb`, `DB_POSTGRESDB_{HOST,PORT,DATABASE,USER,PASSWORD,SCHEMA}` + SSL options.

### Security
- SSL: **reverse proxy (Traefik/NLB) recommended**, or `N8N_SSL_CERT`/`N8N_SSL_KEY` directly. Also: MFA enforcement, SSO (SAML/OIDC), disable public API, block specific nodes, harden task runners, **SSRF protection (3.0 enlarges the default block list)**, encryption-key rotation (on by default in 3.0), execution-data redaction, telemetry opt-out.

---

## 4. Docker — Core (docs.docker.com)

### What Docker is
- Open platform for developing/shipping/running apps: package an app + everything it needs into a container — a loosely isolated, lightweight environment — so the same artifact runs identically on a laptop, VPS, or cloud.
- **Client–server:** the `docker` CLI is just a client; `dockerd` (daemon) does the work (build/run/distribute) and manages images/containers/networks/volumes over a REST API (UNIX socket or network). The client can drive a **remote** daemon — basis for "deploy from laptop to VPS via `DOCKER_HOST`".
- **Docker Compose** is "another Docker client" for multi-container apps.

### Desktop vs Engine (matters for tutorials)
- **Engine** = core: daemon + CLI + APIs (+ BuildKit, containerd).
- **Desktop** = GUI bundle for Mac/Windows/Linux: Engine + CLI + Compose + Build + Kubernetes + extras. On macOS/Windows, containers run inside a lightweight Linux VM (slower bind-mount I/O, forwarded ports).
- **Tutorial takeaway:** learn on Desktop locally, deploy on Engine on the VPS; the Compose file is identical in both.

### Images
- Standardized, **immutable** packages built from **layers** (each Dockerfile instruction ≈ one layer). Unchanged layers are reused from cache → small images, fast rebuilds.
- Docker Hub is the default registry; "Docker Trusted Content" push: Official Images, **Hardened Images** (minimal, near-zero CVEs), Verified Publishers. Beginner advice: start from Official Images.

### Containers
- Runnable instances of images — isolated processes with own filesystem/network/process space. **When a container is removed, any state changes not in persistent storage disappear** — the entire motivation for volumes. Hammer this in every self-hosting tutorial.

### Dockerfile basics
- Core instructions: `FROM`, `WORKDIR`, `COPY`, `RUN`, `ENV`, `EXPOSE` (declares intent, doesn't publish), `USER`, `CMD`.
- Best practices: **multi-stage builds** (final image = only runtime needs); small trusted bases; **order instructions least-changing-first** (`COPY . .` before dependency install busts cache — copy manifests → install → copy source); **`apt-get update && apt-get install` in a single RUN** (a lone `apt-get update` layer gets cached and installs silently use stale lists); `.dockerignore`; **tags are mutable** — pin by digest for certainty (or Dependabot for docker); **one concern per container**; keep containers ephemeral/stateless.

---

## 5. Docker — Networking

### Bridge driver
- A bridge network = software bridge on the host with its own subnet. Containers on the same bridge talk freely; outside traffic blocked except via **published ports**; outbound uses NAT.
- **The single most important networking gotcha:** there are *two* bridges. The **default `bridge`** (plain `docker run`) gives **no DNS name resolution** — containers reach each other only by IP (unless legacy `--link`). **User-defined bridges give automatic DNS by container name/alias**. Docs flatly call user-defined bridges "superior" and the default "not recommended for production."
- **Port publishing gotcha:** `-p 8080:80` with no host IP binds **all interfaces (0.0.0.0)** — on a VPS this can bypass host firewall expectations. Scope it (`-p 127.0.0.1:8080:80`) or put a reverse proxy in front.
- `host` = shares host's network stack (no port mapping); `none` = no networking; `overlay` = multi-host (Swarm).

### Networking in Compose
- Compose creates **one user-defined bridge network per project** (`<project>_default`); every service joins it. Services reach each other by **name** (e.g. `postgres://db:5432`) with zero config. **Container IPs change on recreate — always use names, never IPs.**
- Inter-service traffic uses the **container** port; the host port is only for outside access (`ports: ["8001:5432"]` → services use `db:5432`, host uses `localhost:8001`). Classic beginner confusion — drill it.
- `networks:` top-level + per-service; `internal: true` = no external gateway (good for isolating a DB); `external: true` = attach to a pre-existing network (must exist before `up` — useful for a shared proxy network).
- `network_mode` and `networks` are **mutually exclusive**; `ports` is a runtime error with `network_mode: host`.
- `extra_hosts` injects `/etc/hosts`; special value `host-gateway` resolves to the host from inside containers (sanctioned way to reach host services).
- `links` is legacy — not needed for name resolution on Compose's default network. Don't teach it to beginners.

---

## 6. Docker — Volumes / Storage

- **Volumes** = Docker-managed persistent stores, outside any container's lifecycle. **Preferred** mechanism: easier to back up/migrate than bind mounts, CLI-manageable, safely shareable between containers, faster than the container writable layer.
- **Named vs anonymous:** named = reusable/shareable/back-up-able; anonymous = random ID, orphans pile up (`docker volume prune` cleans).
- **Gotchas:** (1) mounting a volume over a directory **hides** whatever was in the image at that path; (2) mounting an **empty** volume over a directory with files **copies** the image's files into it (pre-population — disable with `nocopy`); (3) volumes are **not removed automatically** when containers are removed; (4) a volume can mount into multiple containers at once, even mixed `rw`/`ro`; (5) `--mount` preferred over `-v`: explicit, fails loudly on typos; `-v` silently creates directories for mistyped bind paths.
- **Bind mounts** = host path mapped in (dev source-sync, host-owned config); **tmpfs** = RAM-only, gone on stop (secrets/scratch).
- **Tutorial takeaway:** n8n/Postgres data → **named volume** declared in top-level `volumes:`; config files edited on the host → bind mount (preferably `:ro`). Never rely on anonymous volumes or the container filesystem for anything you care about.

---

## 7. Docker Compose File Reference (docs.docker.com/compose/compose-file/)

> Canonical path is now `/reference/compose-file/`; old URL redirects to the same content.

### The spec (version gotcha)
- Legacy `2.x`/`3.x` formats were **merged into one versionless Compose Specification** (Compose v2, 1.27.0+). **Top-level `version:` is obsolete** — informative only, triggers a warning, never selects a schema. Teach `compose.yaml` with **no** `version` key. `compose.yaml` is the canonical filename (`.yml` still works).
- New top-level `name:` sets the project name. Top-level elements: `services` (required), `networks`, `volumes`, `configs`, `secrets`, `models` (Docker Model Runner), `include`, plus Build/Deploy specs.

### services — the fields that matter for self-hosting
- **`image`:** `[registry/][project/]image[:tag|@digest]`. Missing locally → pulls per `pull_policy` (default `missing`) — **but `latest` is always re-pulled even under `missing`**. Tutorial gotcha: with `image: n8nio/n8n:latest`, `docker compose up` won't fetch a newer `latest` unless you `docker compose pull` first. Pin versions (`n8nio/n8n:1.x`) for reproducibility.
- **`ports`:** short syntax `[HOST:]CONTAINER[/PROTOCOL]` — **always quote** (`"8080:80"`) to avoid YAML float parsing. Long syntax: `target`, `published` (string, ranges allowed), `host_ip`, `protocol`, `mode`. **Gotcha:** omitting host IP binds 0.0.0.0 (see §5).
- **`expose`:** declares ports for inter-service visibility only — *not* published to host. Mostly redundant (containers on the same network already see all each other's ports).
- **`environment` / `env_file`** (where n8n config lives):
  - `environment`: map or list; **booleans must be quoted** (`"true"`). Bare key with no value pulls from the shell environment.
  - `env_file`: list of files; relative paths resolve from the Compose file's folder. **Precedence: `environment` overrides `env_file`, even with empty/undefined values.** Files processed top-down; last wins for duplicates.
  - `.env` format rules: `VAR=VAL` or `VAR: VAL`; `#` comments; unquoted and double-quoted values get **interpolation** (`${VAR}` expanded); **single-quoted values are literal**; inline comments need a preceding space; `VAR=` (empty) vs bare `VAR` (unset) differ.
  - Long syntax adds `required: false` and `format: raw` (no interpolation — handy for passwords containing `$`).
  - **Tutorial takeaway:** keep secrets in a gitignored `.env`, reference as `${VAR}`; commit only `.env.example`. Never hardcode credentials.
- **`volumes` (service-level):** short `VOLUME:CONTAINER_PATH[:ACCESS_MODE]` (`rw` default, `ro`, SELinux `z`/`Z`); long syntax with `type: volume|bind|tmpfs`, `source`, `target`, `read_only`, `bind: {create_host_path}`, `volume: {nocopy, subpath}`. Named volumes reused across services **must** be declared under top-level `volumes:`.
- **`depends_on` + `healthcheck` (the readiness gotcha):**
  - Short syntax only orders **container start** — Compose "does not wait until a container is 'ready', only until it's running." An app can boot and fail its first DB connection because Postgres isn't accepting connections yet.
  - Long syntax: `condition: service_started` (default) | `service_healthy` (waits for the dependency's `healthcheck` to pass) | `service_completed_successfully` (one-shot jobs like migrations). Also `restart: true` (restart when the dependency is updated) and `required: false`.
  - **`service_healthy` requires the dependency to define a `healthcheck:`** — pair every long-running dependency (Postgres: `pg_isready`) with one. `healthcheck`: `test` (`CMD`/`CMD-SHELL`/`NONE`), `interval`, `timeout`, `retries`, `start_period`.
- **`restart`:** `no` (default) | `always` | `on-failure[:max-retries]` | `unless-stopped`. **For a VPS, `unless-stopped` (or `always`) is the correct default** — survives reboots and crashes. Distinct from `deploy.restart_policy` (Swarm-oriented; on plain `docker compose up` it falls back to `restart`).
- **`command` vs `entrypoint`:** override Dockerfile `CMD`/`ENTRYPOINT`. Gotcha: unlike Dockerfile `CMD`, Compose `command` does **not** run inside the image's `SHELL` — wrap shell features explicitly (`sh -c "..."`).
- **`secrets`:** better than env vars for credentials — mounted read-only at `/run/secrets/<name>`. Env vars leak via `docker inspect`/logs; secrets don't.
- **`deploy.resources`:** `limits` (hard cap) vs `reservations` (guaranteed minimum) for `cpus`, `memory` (`512M`), plus GPU reservations. Legacy flat keys (`mem_limit`, `cpus`) are superseded. On a small VPS, `deploy.resources.limits.memory` prevents one runaway container from OOMing the host.
- **Logging:** `logging: {driver, options}` — set `max-size`/`max-file` (json-file) on a VPS so logs don't fill the disk.
- **Handy smaller fields:** `container_name` (**prevents scaling** past 1), `init: true` (proper PID 1 signal forwarding — good for Node apps like n8n), `profiles` (opt-in services via `--profile`), `user` (run as non-root), `stop_grace_period`, `platform` (e.g. forcing `linux/amd64`), `read_only`, `extends`, `labels`.

### Compose in production (docs explicitly bless single-server deploys)
- "The easiest way to deploy an application is to run it on a single server, similar to how you would run your development environment."
- Prod checklist: remove dev bind mounts for app code, bind different host ports, set prod env vars (log verbosity), `restart: always`, add log aggregators. Keep overrides in a second file (`compose.production.yaml`) applied with `-f` (only deltas needed).
- Redeploy pattern: `docker compose build web && docker compose up -d --no-deps web`. Remote deploys via `DOCKER_HOST` / `DOCKER_TLS_VERIFY` / `DOCKER_CERT_PATH`.

### Minimal n8n stack (distilled pattern)
2 services (`n8n` + `postgres`) · one named volume for Postgres (and one for `/home/node/.n8n`) · one default network (services reach each other by name — `DB_POSTGRESDB_HOST=db`) · `depends_on: {db: {condition: service_healthy}}` + `pg_isready` healthcheck · `restart: unless-stopped` · secrets via `.env` (never commit) · `127.0.0.1:`-scoped or reverse-proxied port publishing · `deploy.resources.limits` on small VPSes · log rotation via `logging.options`.

---

## 8. LangChain — Concepts (python.langchain.com/docs/concepts/)

> NOTE: the old `python.langchain.com/docs/concepts/*` URLs no longer host concept pages — they render the new overview; concepts moved to the unified **`docs.langchain.com`** (Mintlify). Docs reflect the **LangChain v1 (~1.3.x) era**.

### The mental model: "Agent = Model + Harness"
An **agent** is a model calling tools in a loop until the task is done; a **harness** is everything around that loop — the prompt, the tools, and middleware. `create_agent()` from `langchain.agents` is the one entry point.
**Tutorial angle:** open every LangChain tutorial with the 1-line loop diagram (model call → tool execution → repeat until no more tool calls) — it explains 80% of what readers will debug.

### LangChain vs LangGraph vs Deep Agents (positioning)
- **LangChain (`create_agent`)** — minimal, highly configurable harness; compose only what you need via middleware.
- **Deep Agents** — batteries-included harness *built on* LangChain agents: automatic context compression, virtual filesystem (`ls/read/write/edit/delete/glob/grep/execute`), subagent spawning (`task` tool), long-term memory via AGENTS.md files, opt-in task planning (TodoListMiddleware), prompt caching.
- **LangGraph** — low-level orchestration underneath both; durable execution, human-in-the-loop, persistence/checkpointing. Use when the workflow isn't a plain "loop until done" (routing, fan-out, deterministic steps).
- **LangSmith** — traces, debug, evaluate any of the above.
- **Tutorial note:** "which one should I use?" is evergreen content — readers constantly confuse the three.

### Agents core components
- **Model:** pass `"provider:model"` string (e.g. `"openai:gpt-5.5"`) or an initialized instance.
- **Tools:** any Python callable, LangChain tool, or tool dict.
- **System prompt:** string or SystemMessage; dynamic prompts at runtime via middleware (`@dynamic_prompt`).
- **Structured output:** `response_format=` with a schema; strategies `ToolStrategy` (artificial tool calling) and `ProviderStrategy` (provider-native). **Prompted output (instructing via prompt) was removed in v1 as unreliable.**
- **AgentState:** TypedDict with append-only `messages`; the type signature for middleware hooks. Custom fields → subclass, pass via `state_schema=`.
- **Invocation:** `agent.invoke({"messages": [...]}, config={"configurable": {"thread_id": ...}})`. `thread_id` scopes the *conversation*; `context` (new in v1) carries *per-run* immutable data (user ID, API keys, feature flags), accessed via `runtime.context`.
- **Gotchas:** `create_react_agent` (from `langgraph.prebuilt`) is deprecated → `create_agent`; `prompt=` renamed to `system_prompt=`; pre-bound models (`model.bind_tools(...)`) no longer accepted; state schemas are **TypedDict only** (Pydantic/dataclasses removed); streaming node renamed `"agent"` → `"model"`.

### Middleware (the v1 replacement for callbacks/hooks)
Middleware hooks into the agent loop (`before_model`/`after_model`/`wrap_model_call`/`wrap_tool_call`/…). Prebuilt catalog highlights:
- **ToolError** (exceptions → error ToolMessages so the model self-retries), **ToolRetry/ModelRetry** (exponential backoff), **ModelFallback** (failover across providers), **Summarization** (trigger on token fraction/count; `keep` control), **HumanInTheLoop** (approve/edit/reject before tool calls), **ModelCallLimit/ToolCallLimit**, **PIIMiddleware** (block/redact/mask/hash), **TodoList** (opt-in planning), **LLMToolSelector** (LLM picks relevant tools when you have 10+), **ContextEditing** (clear old tool outputs over a token threshold).
- **Tutorial notes:** middleware is *the* beginner-friendly customization story — "one concern per middleware, compose freely." **HITL + call limits + retries are the three every production tutorial should show.** Old patterns (`InjectedState`, `InjectedStore`, `get_runtime()`) are replaced by the single `ToolRuntime` interface. For **agent behavior customization the docs push middleware instead of callbacks** (callbacks remain the observability surface for tracing/streaming).

### Tools deep concepts
- **`@tool` decorator** is the primary authoring path; **type hints are required** (they become the JSON schema); docstring = the model's usage instructions.
- **Reserved arg names:** `config` and `runtime` can't be tool arguments; use a `runtime: ToolRuntime` parameter instead (hidden from the model's schema). It exposes: **state** (short-term memory), **context** (per-run config), **store** (long-term memory), **stream_writer** (progress updates), **tool_call_id**, etc.
- **Return values:** `str` → ToolMessage; `object` (dict) → structured data for the model; **multimodal content blocks** if the model supports them; `Command` → update agent state *and* return a message; **`return_direct=True`** → short-circuit the loop, return tool output as final answer (gold for "deterministic answer, skip the extra LLM call" tutorials).
- **Dynamic tool selection:** filter registered tools by state/store/context (permissions, feature flags) — solves "too many tools overwhelm the model." Or register tools at runtime (e.g. from MCP) via `wrap_model_call` + `wrap_tool_call`.
- **Headless tools** (new): tool *definition* server-side, *implementation* on the client (browser) after an interrupt/resume handshake — for geolocation, clipboard, IndexedDB.
- **Deep Agents tools/MCP:** full MCP server support; virtual filesystem tools; declarative path permissions (first-match-wins); code execution via sandbox backends or QuickJS interpreter.

### Memory (short-term vs long-term)
- **Short-term = AgentState** for the current thread. Persistence via `checkpointer` at agent creation (`thread_id` per conversation; production = database-backed checkpointer like Postgres).
- **Long conversations:** trim (token-based, `@before_model` middleware), delete (`RemoveMessage`), or **summarize** (`SummarizationMiddleware` — compressed summary persists into state).
- **Long-term = Store** (namespace/key pattern), via `runtime.store`; survives across threads. Deep Agents loads memory from `AGENTS.md` at startup.
- **Skills** (Agent Skills standard, `SKILL.md`): progressive disclosure — frontmatter at startup, full content on demand. Different from memory (always loaded).
- **Tutorial note:** the state/store/context table is the clearest explainer: **Runtime Context** = static config, conversation-scoped; **State** = short-term, conversation-scoped; **Store** = long-term, cross-conversation.

### Context engineering (flagship concept page)
"Providing the right information and tools in the right format so the LLM can accomplish a task — the number one job of AI Engineers." Agent failures are usually *wrong context*, not a weak model. Three control surfaces: **Model context** (system prompt, messages, tools, response format — transient), **Tool context** (state, store, runtime context — persistent), **Life-cycle context** (summarization, guardrails, logging — persistent, via middleware).
**Tutorial note:** the philosophical backbone for "why your agent fails" posts.

### Models/providers
- `init_chat_model("provider:model")` is the universal constructor; provider packages share one interface — "new model names work immediately, no LangChain update required." The portability story: "switch models with one string."
- `invoke` (single), `stream` (AIMessageChunk stream), `astream_events` (typed events), `batch`/`batch_as_completed`. **Auto-streaming:** `invoke()` inside a streaming run auto-switches to streaming internally.
- Connection resilience: default 6 retries with backoff for network/429/5xx (not 401/404); raise `max_retries` to 10–15 for long agent runs.
- **Model profiles** (`model.profile`, powered by models.dev): capabilities like context window, tool calling — used by SummarizationMiddleware; user-overridable.

### RAG / retrieval
- Pipeline: load → split → embed → store in vector store → retrieve. Three architectures: **2-step RAG** (always retrieve-then-generate; simple/predictable; FAQs), **Agentic RAG** (agent decides when/how to retrieve via tools mid-reasoning; research assistants), **Hybrid** (query enhancement + retrieval validation + answer validation).
- **Gotcha:** legacy chains (`RetrievalQA`, `ConversationalRetrievalChain`) moved to `langchain-classic`; the modern path is **agentic RAG** (retriever wrapped as a `@tool`).

### Streaming & evaluation
- Agent-level: `agent.stream(..., stream_mode="values"|"updates"|"messages"|...)`. `stream_mode="messages"` is the token-streaming workhorse for chatbot UIs.
- **Offline evaluation** (datasets + experiments before shipping; catch regressions) vs **Online** (real-time scoring of production traffic). Workflow: dataset (curated, production traces, or synthetic) → experiment → analyze. "Add real traces to a dataset so a failure you saw once becomes a test you run every time." Rubric grading middleware brings LLM-as-judge *into* the agent loop.

### LangChain v1 gotchas cheat-sheet (biggest tutorial hazard)
1. **Namespace shrink:** `langchain` package now only has `agents`, `messages`, `tools`, `chat_models`, `embeddings`. Everything else (chains, retrievers, indexing API) → **`langchain-classic`** (`pip install langchain-classic`, `from langchain_classic.chains import LLMChain`).
2. `create_react_agent` → `create_agent`; `prompt=` → `system_prompt=`; old `initialize_agent`/`AgentExecutor` superseded.
3. **Python 3.10+ required** (3.9 dropped). `message.text()` → `.text` property. Chat model return type fixed to `AIMessage`.
4. `.bind_tools()` pre-bound models not accepted by `create_agent`; `ToolNode` instances not accepted in `tools=`; `response_format` prompted-output removed.
5. **Most old tutorials are pre-v1** — any tutorial using `LLMChain`, `AgentExecutor`, `ConversationBufferMemory` needs the classic package or a rewrite. Strong content angle: "LangChain v1: what still works" migration posts.

---

## 9. n8n 3.0 Breaking Changes (scheduled Oct 2026) — tutorial-critical

Removed nodes with documented replacements:
- **Function/Function Item → Code node** · **Item Lists → Split Out/Aggregate/Sort/Limit/Remove Duplicates/Summarize** · **Cron/Interval → Schedule Trigger** · **HTML Extract → HTML node's Extract HTML Content** · **iCalendar → Convert to File (ICS)** · **Convert to/from binary data → Convert to File / Extract from File** · **Read/Write Binary File → Read/Write Files from Disk** · **Read PDF → Extract from File (PDF)** · **Workflow Trigger → n8n Trigger** · **LangChain Code → removed** · **Manual Chat Trigger → Chat Trigger** · **Chat Messages Retriever → Chat Memory Manager** · doc loaders (Binary/JSON/GitHub Input Loader) → **Default Data Loader** · old vector-store Insert/Load pairs → unified node · **AI Transform → auto-migrated to Code node**.
- **npm/npx install removed** (Docker mandatory). `N8N_DEFAULT_BINARY_DATA_MODE=default` invalid (use filesystem/s3/azure/database); storage dir renamed `binaryData`→`storage`; unverified community packages off by default; `N8N_RUNNERS_TASK_TIMEOUT` 300→60s; Chat Hub off by default (gone in 4.0); `N8N_ENABLED_MODULES=agents` needed for first-class agents.
- **`$getPairedItem` removed → use `pairedItem`/`$("").item`**. Execute Sub-workflow Local File/URL sources removed (use Database/Define Below).

---

## 10. Tutorial Angles & Beginner Traps (cross-source)

**Best tutorial angles surfaced:**
1. n8n AI Agent + Call n8n Workflow Tool (sub-workflows as tools) for compound agents
2. RAG with Simple Vector Store + Recursive Character Text Splitter (official starter template exists)
3. Human-in-the-loop approvals via Telegram/Slack (native HITL, cheap to demo)
4. Gateway credits on Cloud = zero-API-key AI tutorials
5. Error workflow pattern (reusable "Error Handler" workflow, great visual payoff)
6. `create_agent` in 10 lines (weather tool hello-world)
7. "@tool decorator: the only 3 rules" (type hints required, docstring matters, reserved names)
8. Middleware trio: HumanInTheLoop + ModelCallLimit + ToolRetry — "production-ready agent in 15 lines"
9. Short-term vs long-term memory via the state/store/context table
10. Agentic RAG: retriever-as-tool (replaces all legacy RetrievalQA tutorials)
11. Streaming tokens to a UI (`stream_mode="messages"`)
12. LangChain v1 migration guide — huge SEO opportunity since most existing tutorials are stale
13. "n8n 3.0 breaking changes / migration" content (Oct 2026)

**Beginner traps to warn about:**
- Draft vs published: webhook still runs the old version until you publish
- Partial executions need a trigger node on the canvas
- Expressions referencing unexecuted nodes; pinned data silently ignored in production
- Branch execution order = canvas position (1.0+)
- webhook-test URLs (`/webhook-test/*`) vs production URLs
- Queue mode: no filesystem binary storage, no first-class agents yet
- Postgres 18 PGDATA gotcha; self-hosted agents need `N8N_ENABLED_MODULES=agents`
- Compose: `latest` not re-pulled without `docker compose pull`; `depends_on` short syntax doesn't wait for readiness; containers on the default bridge have no DNS; `-p 8080:80` binds 0.0.0.0; volumes not auto-removed
- LangChain: most old tutorials are pre-v1 (LLMChain/AgentExecutor era)
