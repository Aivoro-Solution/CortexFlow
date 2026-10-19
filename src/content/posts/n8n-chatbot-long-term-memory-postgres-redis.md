---
title: "How to Add Long-Term Memory to n8n Chatbots (Postgres & Redis Guide)"
description: "Stop your n8n chatbot from forgetting everything. Set up Postgres or Redis chat memory with session keys, context windows, TTL and a summarization pattern."
date: 2026-10-19
category: chatbots
tags: ["n8n", "chatbots", "postgres", "redis", "ai-agents", "tutorial"]
draft: false
featured: false
image: "/og/n8n-chatbot-long-term-memory-postgres-redis.webp"
---

Every n8n chatbot has the same embarrassing failure mode: it answers brilliantly in the moment, then forgets everything the moment the next message arrives. A user tells it their name, their order number, their problem — and one message later it's asking for the name again.

This happens because an LLM (Large Language Model — the AI that generates your chatbot's replies) is stateless. Each call to it is independent: it knows only what you send in that one request. If you don't resend the conversation history, the model has no past. In n8n, the fix is a **memory sub-node** attached to the AI Agent node — a small node that reads the last few messages from a store and hands them to the model before it answers, then writes the new exchange back.

By the end of this guide you'll have a working n8n workflow where the AI Agent remembers conversations using either **Postgres** (durable, queryable) or **Redis** (fast, self-expiring), you'll know how to wire the session key so two users never see each other's history, and you'll have a pattern for keeping month-long conversations within the model's context window.

## How n8n memory nodes actually work

Forget the marketing word "memory" for a second. Mechanically, it's just a key-value store with a key problem:

1. When a message arrives, n8n reads the **session key** (a string like the chat's session ID or a Telegram chat ID).
2. The memory node fetches the last N messages stored under that key — N is the **context window length** (the number of previous messages the agent sees; more messages cost more tokens on every reply).
3. Those messages are injected into the model's prompt, the model answers, and the new exchange is appended under the same key.

**Two settings decide whether this works or corrupts everything.** Get the session key wrong and every user shares one conversation — your bot will tell one customer what another ordered. This is the single most common production bug with n8n chatbots. Set the context window too high and you burn tokens on every reply; too low and the bot forgets mid-task.

n8n ships several memory options that plug into the AI Agent node via its `ai_memory` input:

- **Simple Memory** (the old Window Buffer Memory): keeps the last N messages inside the n8n process itself. Lost on restart, not shared between workers in queue mode. Fine for a weekend prototype, wrong for anything real.
- **Postgres Chat Memory**: stores history rows in a Postgres table. Survives restarts, and you can query and audit the history with SQL.
- **Redis Chat Memory**: stores history in Redis, an in-memory data store built for speed. Sub-millisecond reads, plus automatic expiration — old sessions clean themselves up.
- **MongoDB Chat Memory**: same idea for teams already running MongoDB.
- **Motorhead Memory / Zep**: external memory services. I'll cover them briefly at the end — I haven't run either against current n8n versions, so consider them leads, not tested recipes.

Everything below applies to the AI Agent node. Note that AI chains (the older "chain" nodes) can't use memory sub-nodes — if you're still on chains, migrate to the agent node first.

**Prerequisites**

- A running n8n instance (self-hosted 1.x or n8n Cloud; node names below match n8n 1.x — they shift between releases, so check your instance's node panel if a name looks different).
- An AI Agent node with a chat model (OpenAI, Anthropic, or a local model) already working.
- For the Postgres path: any Postgres you can reach from n8n — a local Docker container, Supabase, or Neon all work.
- For the Redis path: any Redis you can reach — a local Docker container, Redis Cloud, or ElastiCache.
- A trigger that identifies the user: the Chat Trigger widget, the Telegram Trigger, or a webhook carrying a user ID.

## Step 1 - Wire the session key before touching any database

The session key is the whole design. Every memory node stores and retrieves history under one key, and if that key isn't unique per user, histories collide.

Which expression you use depends on your trigger:

```javascript
// Chat Trigger (n8n's built-in chat widget) — sessionId arrives automatically:
={{ $json.sessionId }}

// Telegram Trigger — the sender's chat ID:
={{ $('Telegram Trigger').item.json.message.chat.id }}

// WhatsApp / webhook — whatever field identifies your user:
={{ $json.userId }}
```

For testing, a static key like `my_test_session` is fine. But **never ship a static key to production** — one shared key means every visitor reads one shared conversation.

> **Warning:** if you run the same agent behind two triggers (Telegram plus your website widget), the same human is two different IDs and lands in two separate memories. If that matters, normalize both to one customer ID in a Set node before the memory node.

Test this before going live: open two browser sessions, chat as two different users, and ask user A for their name after user B introduced themselves. If A ever hears B's name, your session key is wrong.

## Step 2 - Add Postgres chat memory for durable history

Postgres is the pick when history is an asset: support transcripts you must keep, audit trails, or conversations you want to query later with SQL ("show me every chat where the bot offered a refund").

### 2.1 - Get a Postgres reachable from n8n

If you already run one, skip ahead. Otherwise the fastest local option is Docker:

```bash
docker run -d \
  --name n8n-postgres \
  -e POSTGRES_USER=n8n \
  -e POSTGRES_PASSWORD=<choose-a-strong-password> \
  -e POSTGRES_DB=n8n_memory \
  -p 5432:5432 \
  postgres:16
```

What each part does: `--name` labels the container so you can manage it; the three `-e` flags create the database user, its password, and an empty database; `-p 5432:5432` exposes Postgres on the standard port. Managed options (Supabase, Neon) work identically from n8n's side — you just paste a different host into the credential.

You should see the container running under `docker ps`. If n8n runs in Docker too, make sure both containers share a network — `localhost` inside n8n's container is not your host.

### 2.2 - Create the Postgres credential in n8n

In n8n: **Credentials → New → Postgres**. Fill in host, port, database (`n8n_memory`), user, and password. For Supabase/Neon, use the connection details from their dashboard (their pools usually need SSL enabled — toggle it in the credential).

Click **Test** — n8n connects before saving. If it fails here, it's a network or auth problem, not a memory problem; fix it before continuing.

### 2.3 - Attach the memory node

Add a **Postgres Chat Memory** node and connect it to the AI Agent's `ai_memory` input. Configure:

- **Session Key**: your expression from Step 1 (Chat Trigger users can leave the default binding).
- **Context Window Length**: start with 10–20. Ten messages is plenty for a support bot; more costs tokens on every single reply.

When the workflow runs, the node creates its history table automatically (commonly seen as `n8n_chat_histories`, holding the session ID, the messages as JSON, and a row ID). The database user needs `CREATE TABLE` permission for this first-run setup — a locked-down read-only user will fail here with a warning, so grant table creation once or pre-create the table yourself.

Send two test messages through the workflow, then check the table with a Postgres node or `psql`:

```sql
SELECT session_id, message FROM n8n_chat_histories LIMIT 5;
```

You should see one row per stored message under your test session key. Same session key on the next message → the agent sees the earlier ones. New session key → a blank conversation. That isolation is the whole point.

## Step 3 - Add Redis chat memory for fast, self-expiring sessions

Redis is the pick when sessions are short-lived and speed matters: WhatsApp bots, flash-sale support, anything where a conversation older than a day is dead weight. Redis reads and writes in sub-milliseconds, and its TTL (time-to-live) deletes stale sessions for you.

### 3.1 - Get a Redis reachable from n8n

```bash
docker run -d \
  --name n8n-redis \
  -p 6379:6379 \
  redis:7 --appendonly yes
```

The `--appendonly yes` flag turns on AOF persistence, Redis's append-only log. By default Redis keeps everything in RAM — restart the container and history evaporates. AOF replays the log on boot, so sessions survive restarts. For most chatbots, losing old history on a restart is acceptable; for anything where it isn't, keep this flag (or use RDB snapshots).

`docker ps` should show it running. Same network note as Postgres applies if n8n is containerized.

### 3.2 - Create the Redis credential and attach the node

**Credentials → New → Redis**, host and port (and password if your Redis requires one). Then add a **Redis Chat Memory** node to the AI Agent's `ai_memory` input. The official node exposes exactly three parameters:

- **Session Key**: your per-user expression from Step 1.
- **Session Time To Live**: seconds after which the session expires. `86400` = 24 hours is a sane default for chatbots.
- **Context Window Length**: same trade-off as Postgres — 10–20 to start.

That's the eviction story in one field: set a TTL and old sessions delete themselves with no cleanup workflow. Postgres has no equivalent — stale rows there sit until you delete them, which is a reason to prefer Redis for high-volume, short-lived chats.

One caution from the n8n community worth knowing: the built-in Redis Chat Memory node shares its credential type with the regular Redis operation nodes, so anyone with the credential can `KEYS *` and read other sessions. Don't share the credential broadly; keep it on the workflows that need it.

### 3.3 - Verify it works

Run the same two-message test as Step 2.3: continuity under one session key, isolation under a new one. Then wait out (or temporarily shorten) the TTL and confirm the session is gone — that's your proof the self-cleanup works.

## Postgres vs Redis: the decision table

Neither is "better." They solve different memory problems — durability versus ephemerality:

| | Postgres Chat Memory | Redis Chat Memory |
|---|---|---|
| History survives restarts | Yes | Only with persistence (AOF/RDB) enabled |
| Read/write speed | Milliseconds | Sub-millisecond |
| Old sessions expire automatically | No — you clean them up (SQL or Chat Memory Manager) | Yes — Session Time To Live |
| Queryable history (analytics, audits) | Yes, full SQL | No, key-value only |
| Setup effort | Medium (database + credential + table perms) | Low (container + credential) |
| Cost at small scale | Free self-hosted; managed from ~$5/mo | Free self-hosted; managed from free tiers |
| Best for | Support transcripts, audits, long relationships | WhatsApp bots, high-volume short chats |

**The one-line rule: if the history is an asset you might query, use Postgres. If it's a liability you want to forget, use Redis with a TTL.** For many teams the answer is both — Redis for the live session, a background workflow copying summaries into Postgres (more on that below).

## The summarization pattern for long conversations

The context window is a trap for long relationships. Twenty messages is fine; two thousand will either blow the model's context limit or cost a fortune in tokens per reply. The fix is **summarization**: periodically compress the old history into a short summary and keep only the summary plus recent messages.

The pattern, verified on current n8n:

1. A scheduled workflow (or a counter in your main flow) watches a session's message count — say every 50 messages.
2. It uses the **Chat Memory Manager** node — n8n's node for reading, inserting, and clearing messages in a memory store outside the agent — to read the old messages.
3. An LLM call compresses them: "Summarize this conversation in 10 bullet points, keeping names, preferences, and open issues."
4. The manager node clears the old messages and inserts the summary as a single system message, so the agent keeps the gist without the bulk.

This is a background concern, not a hot-path one: summarize asynchronously so the user's reply never waits on it. As a simpler variant, some teams skip the manager node and write summaries to a separate Postgres table with a SQL node, then inject the summary into the agent's system prompt via an expression. Either way, the agent's memory becomes two layers — a durable summary plus a small rolling window — which is the closest n8n gets to genuine long-term memory without a vector database.

## Testing checklist

Run these before you call it done:

- [ ] **Continuity:** send three messages in one session (introduce a name, change the topic, then ask "what's my name?"). The bot must recall it.
- [ ] **Isolation:** start a second session with a different key and ask the same question. It must not know the first session's name.
- [ ] **Restart survival:** restart n8n (Postgres) or the Redis container with persistence on, then ask a recall question. History must persist.
- [ ] **Expiry:** shorten the TTL to 60 seconds, wait, then check the session is gone (Redis) — or confirm your cleanup query removed it (Postgres).
- [ ] **Queue mode:** if n8n runs with multiple workers, confirm memory is shared. Simple Memory is process-local and fails here; Redis and Postgres are shared backends and pass.

## What I didn't test

Motorhead and Zep both offer dedicated memory services with n8n integrations, and Zep in particular has community reports of "just working" where Postgres needed prompt tuning. I haven't run either against current n8n versions, so I won't prescribe them — treat them as your next experiment if you outgrow the built-in nodes. I also didn't benchmark Redis vs Postgres latency in a real workflow; the speed claims above come from each store's documented characteristics, not my own measurements. And a real caveat for regulated use cases: chat history in either store is stored in cleartext. If you handle health or financial data, encrypt sensitive fields before they reach the memory node, or keep that data out of chat history entirely.

## Key Takeaways

1. **The session key is the design.** A wrong key merges strangers' conversations; a static key in production merges everyone's. Bind it to a real per-user ID before anything else.
2. **Postgres = memory as an asset** (durable, queryable, auditable); **Redis = memory as a liability** (fast, TTL self-cleanup). Pick by what you want the history to *become*.
3. **Start with a context window of 10–20** and raise it only with a measured reason — every extra message costs tokens on every reply.
4. **Summarize, don't just widen.** For long relationships, compress old history into summaries with the Chat Memory Manager instead of growing the window forever.
5. **Test isolation, not just continuity.** Two sessions, one restart, one expiry check — before production.

Next step: if your agent needs to recall *facts* across sessions by meaning rather than recency (a vector database like PGVector or Qdrant wired as a tool), that's the natural sequel to this guide — session memory is *what was said*; semantic memory is *what matters*.

## FAQ

### Does the n8n Chat Trigger provide the session ID automatically?

Yes. The Chat Trigger (n8n's built-in chat widget) includes a `sessionId` in its output, and the memory node's default session-key binding uses it. For Telegram, WhatsApp, or webhooks you must wire the key yourself — a Telegram chat ID or the sender's ID is the standard choice.

### Will Redis chat memory survive a server restart?

Only if you enable persistence. Redis stores data in memory by default, so a restart wipes sessions. Start Redis with `--appendonly yes` (AOF logging) or enable RDB snapshots if continuity matters — or accept the loss for short-lived chats.

### How many messages should the context window hold?

Start with 10–20. That covers most support and qualification conversations. Each additional message is sent to the model on every reply, so the cost scales linearly. For conversations that genuinely run long, use the summarization pattern instead of widening the window.

### Can two users share one memory session by accident?

Only if your session key is wrong — a static key, a hardcoded value, or an expression that resolves identically for everyone. The default Chat Trigger binding is per-session and safe. Always run the two-browser isolation test before going live.

### Postgres or Redis for a WhatsApp bot?

Redis, in most cases. WhatsApp conversations are high-volume and short-lived, so the sub-millisecond reads and automatic TTL expiry are exactly what you want. Add Postgres only if you need durable transcripts for audits or analytics.
