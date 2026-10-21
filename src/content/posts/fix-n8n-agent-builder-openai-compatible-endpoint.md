---
title: "Fix n8n Agent Builder Failing with Custom OpenAI-Compatible Endpoints (3 Root Causes, 3 Fixes)"
description: "Agent Builder preview fails with a 'get_environment' schema error or gateway rejections on custom OpenAI-compatible endpoints? 3 verified causes, 3 real fixes."
date: 2026-10-21
category: automation
tags: ["n8n", "ai-agents", "error-fix", "openai", "agent-builder"]
draft: false
featured: false
image: "/og/fix-n8n-agent-builder-openai-compatible-endpoint.webp"
---

You point n8n's Agent Builder at a custom OpenAI-compatible endpoint — DeepSeek, a Portkey gateway, OpenRouter, a self-hosted LiteLLM — the credential test says "Connection successful", and then the agent preview fails with a schema validation error or the gateway rejects the request outright. No amount of re-entering the API key fixes it. This is a real, verified bug cluster in n8n's Agents runtime as of October 2026, documented in community.n8n.io thread [321527](https://community.n8n.io/t/321527) and GitHub issue [n8n-io/n8n#39227](https://github.com/n8n-io/n8n/issues/39227) (verified on self-hosted 2.35.7, 2.36.8, and 2.39.10).

Quick definitions: the **Agent Builder** is n8n's newer native agent-creation UI (distinct from the classic LangChain-based **AI Agent node** you wire up in workflows). An **OpenAI-compatible endpoint** is any API that speaks the OpenAI HTTP format but isn't OpenAI itself. A **routing gateway** (Portkey, OpenRouter, LiteLLM) sits in front of several providers and needs to know *which* provider should serve each request — it learns that from the model name string or from custom HTTP headers.

By the end of this article you'll know the three verified causes of these failures, a two-minute diagnostic that tells you which one you have, and three fixes that actually work — ordered from fastest to most structural.

**Prerequisites:** an n8n instance (Agent Builder runs on n8n Cloud and recent self-hosted versions; the defects below are verified on 2.35.7–2.43.x as of October 2026), an OpenAI-compatible credential, and (for the deep diagnostics) access to the gateway's request logs if you use one.

## The symptom: two different failures, same root area

The failure shows up in one of two ways, and it helps to know which one you have:

**Failure A — schema rejection in Agent Builder preview:**
```
Invalid schema for function 'get_environment': [] is not of type 'object'.
```
The agent has no user-added tools at all, the credential test passed, and a trivial test prompt (like a greeting) still fails. `get_environment` is not something you added — it's an internal tool n8n's Agent Builder injects into every agent automatically. Agent Builder does not expose a toggle or schema editor for it, and the credential test only checks the `/models` route, never function calling — so "connection successful" tells you nothing about whether tool schemas will be accepted.

**Failure B — the gateway rejects the request:**
```
Either x-portkey-provider needs to be passed. Or the x-portkey-config header should have a valid config with provider details in it.
```
or simply `No output generated. Check the stream for errors.` This one hits users who route through Portkey, OpenRouter, or LiteLLM-style gateways. Notably, the *classic AI Agent node* handles the exact same credential correctly — so if your workflow agent works but the Agent Builder one doesn't, you're not misconfiguring anything. The two agent implementations disagree with each other.

**How to confirm in one minute:** open Agent Builder, pick the custom OpenAI-compatible credential, type a one-word test prompt, and preview. If you get the `get_environment` schema error (Failure A) or the gateway error (Failure B), you have an Agent Builder compatibility problem, not a bad API key.

## Root cause 1: Agent Builder probes the Responses API first — and never falls back

The OpenAI **Responses API** is OpenAI's newer, stateful agent API (route `/v1/responses`); most OpenAI-compatible providers only implement the older **Chat Completions API** (`/v1/chat/completions`). When Agent Builder talks to a custom OpenAI endpoint, it probes the Responses API first. If the provider rejects the request — for example rejecting the `get_environment` tool schema — that rejection does *not* trigger the fallback to Chat Completions. The agent just fails. This is confirmed behavior in community thread 321527 (October 2026), not a configuration mistake.

## Root cause 2: Agent Builder strips the provider prefix from your model ID

The native Agents runtime treats `provider/model-name` as its own internal addressing scheme: it splits the string on the first `/`, dispatches on the prefix, and passes *only the suffix* to the provider SDK. The relevant code lives in `packages/cli/src/modules/agents/json-config/credential-field-mapping.ts` and the `@n8n/agents` runtime's `model-factory.ts` (`createModel`). So `openai/gpt-5-mini` goes on the wire as plain `gpt-5-mini`.

That's fine for first-party providers, whose native catalogs never contain a `/`. But routing gateways conventionally route on the *full* model string (`openai/gpt-5-mini`, `@OpenAI/gpt-5-mini`, etc.). The gateway receives a model name it can't map to any upstream provider and rejects the request. As a side note, Agent Builder's own model-ID validation requires lowercase `provider/model-name` and rejects the gateway-native `@OpenAI/...` form — so you can't even spell the gateway's preferred string correctly.

## Root cause 3: your credential's custom headers are silently dropped

On top of the prefix stripping, the OpenAI credential mapper in the Agents runtime reduces an `openAiApi` credential to just `{ apiKey, baseURL }` — effectively `(c) => ({ apiKey: c.apiKey, baseURL: c.url })` — and discards the credential's optional header fields. Those headers (`x-portkey-provider`, `x-portkey-config`, and similar) are exactly how routing gateways receive their provider-routing instructions, so dropping them removes the gateway's other routing channel at the same time the model string loses its prefix. Again: the classic AI Agent node passes headers and slashed model names through correctly, so this is an Agents-runtime-only defect.

> **Honest caveat:** there is a fourth, *unconfirmed* possibility. In the NetArz case from thread 321527, the empty-object tool schema n8n sends for `get_environment` (`properties: {}`) may be getting rewritten to `[]` by the provider's side. Treat that as a hypothesis until the full redacted error body identifies the exact field — it's the provider's logs that settle it, not speculation.

## Fix 1 (fastest): isolate the fault in two minutes

Before changing anything, run two isolation checks that pinpoint which root cause you're dealing with:

**Check 1 — official endpoint vs custom endpoint.** Build the same minimal agent (no tools, one greeting prompt) twice: once with OpenAI's official endpoint, once with your custom endpoint. If only the custom endpoint fails, the problem is in compatibility between Agent Builder and the provider (root causes 1–3, or the provider-side rewrite). If *both* fail, the problem is on n8n's side.

**Check 2 — the Chat Completions baseline.** In a classic workflow, wire a Chat Trigger to a Basic LLM Chain with an OpenAI Chat Model pointed at your custom endpoint, and turn the **"Use Responses API" option OFF** (forcing Chat Completions mode). Then, separately, test tool calling with the classic AI Agent node plus a Calculator tool — ask it to use the calculator and confirm a tool execution actually happened. A working chain confirms basic chat works; a working classic agent confirms the model supports tool calling. If Agent Builder still fails where these succeed, you've proven the problem is in Agent Builder's Responses-first probing and its `get_environment` injection — not in your provider.

## Fix 2: use the provider's own endpoint instead of a routing gateway

If Fix 1 shows the failure only happens through a gateway (Portkey/OpenRouter/LiteLLM), the most reliable workaround is to remove the gateway from the path entirely: point the OpenAI-compatible credential's base URL directly at the provider's own endpoint with the exact model ID.

```text
Base URL: https://api.deepseek.com/v1      (the provider's own OpenAI-compatible endpoint)
Model:    deepseek-chat                    (the provider's exact model name — no prefix needed)
```

Why this works: with no gateway in the path, there's nothing that needs the provider prefix or the routing headers that Agent Builder strips. Root causes 2 and 3 both stop mattering. The trade-off is real: you lose the gateway's unified billing, rate-limit pooling, and fallbacks. Use this when you need Agent Builder working *today* and you only need one provider anyway.

> **Warning:** never paste the full chat endpoint into the base URL field. The client appends `/chat/completions` itself, so `https://api.deepseek.com/v1/chat/completions` becomes `…/chat/completions/chat/completions` and 404s. Always stop at `/v1`.

## Fix 3: if you must use a gateway, move the routing server-side

When you can't drop the gateway — because you rely on Portkey's routing, OpenRouter's fallbacks, or LiteLLM's load balancing — the correct move is to configure the routing *inside the gateway* instead of asking n8n to send it per request:

1. **Use virtual keys / named configs.** In Portkey, create a named config (or virtual key) that pins the provider and model; point n8n's base URL at that config's endpoint. The gateway then routes on its own stored config instead of on headers or the model string that Agent Builder mangles.
2. **Pin the model to one upstream.** Configure the gateway route to serve a single model, so the stripped model suffix is unambiguous.
3. **Ask the provider to diff the schema.** Have NetArz (or your provider) compare the `get_environment` tool definition they *received* against what they *forwarded* — specifically whether `properties: {}` became `[]`. Include your n8n version and the full redacted error JSON body; that diff is the only thing that confirms or kills the rewrite hypothesis.

## Verify everything works

Run the Agent Builder preview again with the same one-word test prompt. You should see a normal agent reply instead of the schema or gateway error. For the belt-and-braces check, look at the *gateway's request logs*: confirm the request that arrived carries a resolvable model string and (for Fix 3) that routing resolved to the intended upstream provider. If you changed credential settings, re-run Check 2 from Fix 1 to make sure the baseline still passes — a green Agent Builder preview means nothing if basic chat broke along the way.

## Prevent it next time

- **Watch the upstream issue.** The two wire-format defects are tracked in n8n-io/n8n#39227 (opened 2026-09-22). The suggested fixes — forwarding the model string unstripped when the base URL is custom, and passing credential header fields through to the model factory — are small, but until they're merged and released, treat any custom gateway + Agent Builder combination as experimental and re-test after every n8n upgrade.
- **Pin and note your n8n version.** These defects were verified on 2.35.7, 2.36.8, and 2.39.10; behavior differs between the classic AI Agent node and the native Agents runtime, so "it worked in the workflow" is never evidence that Agent Builder will work.
- **Keep the credential test in perspective.** A passing "Connection successful" only proves `/models` responds — it says nothing about tool schemas or the Responses API path, which is where Agent Builder actually fails.

## FAQ

### Does the classic AI Agent node have the same problem?

No. The classic node is LangChain-based and passes slashed model names and custom headers through correctly. That's exactly why the same credential can work in a workflow and fail in Agent Builder — and why the Fix 1 baseline checks use the classic path.

### Is there a "Use Responses API" toggle inside Agent Builder?

Not exposed. The toggle exists in the OpenAI Chat Model node used by classic workflows, which is why Fix 1 uses it as a baseline test. Agent Builder's Responses-first probing has no user-facing switch; the workarounds above route around it instead of switching it off.

### My provider says tool calling is supported, but Agent Builder still fails. Why?

"Supports tool calling" usually means the provider tested with a standard chat-completions tool schema. Agent Builder's injected `get_environment` tool has an *empty-object* schema, which is the edge case that breaks — so provider tool support and Agent Builder compatibility are two different claims. The Fix 3 schema diff is what settles it.

### Do the `N8N_INSTANCE_AI_MODEL*` environment variables fix this?

No — those configure the in-editor **AI Assistant**, a different feature from the **Agent Builder**. Mixing the two up is a common wrong turn; Agent Builder reads its model and credential from the agent's own UI settings, not from those env vars.

## Key Takeaways

1. **The `get_environment` schema error is an Agent Builder internal** — n8n injects that tool into every agent, exposes no toggle for it, and probes the Responses API first with no Chat Completions fallback.
2. **The native Agents runtime strips the provider prefix from model IDs and drops custom credential headers** — which breaks routing gateways like Portkey and OpenRouter (GitHub n8n-io/n8n#39227).
3. **Isolate before you fix:** same agent against the official vs custom endpoint, plus a classic Basic LLM Chain baseline with "Use Responses API" off.
4. **Fastest workarounds:** use the provider's direct endpoint, or move gateway routing server-side (virtual keys / named configs) so n8n doesn't have to send it.

**Next step:** if your gateway is in the loop, pull one failed request from its logs and check the model string and headers that actually arrived — that single line of evidence tells you which of the three root causes you're dealing with faster than any amount of credential re-typing. And if you hit the schema error, add your details (n8n version, provider, redacted error body) to the [community thread](https://community.n8n.io/t/321527) — more provider data points are what get these wire-format bugs fixed.
