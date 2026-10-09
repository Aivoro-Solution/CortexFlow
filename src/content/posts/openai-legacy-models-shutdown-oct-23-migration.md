---
title: "OpenAI Pulls the Plug on 29 Legacy Models on October 23: The n8n Migration Checklist"
description: "OpenAI shuts down 29 legacy models on Oct 23, 2026. Audit your n8n workflows, map each model to its substitute, and migrate before they hard-fail."
date: 2026-10-09
category: news
tags: ["openai", "n8n", "migration", "gpt-4", "api"]
draft: false
featured: false
image: "/og/openai-legacy-models-shutdown-oct-23-migration.webp"
---

On **October 23, 2026** — 14 days from now — OpenAI will switch off 29 legacy model IDs and snapshots in one go. That includes every GPT-4 and GPT-3.5 Turbo name your workflows probably still call: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`, the o-series reasoning models (`o1`, `o1-pro`, `o3-mini`, `o4-mini`), and `gpt-4.1-nano`. There is no graceful degrade: at shutdown time, OpenAI says, the model "will no longer be accessible" — your pinned calls fail outright with an API error.

If your n8n instance has an OpenAI node with the model field set to `gpt-4-0613` or `gpt-3.5-turbo-0125`, that workflow breaks on the 23rd. This guide walks you through a full audit-and-migrate pass: find every dead model string in your workflows, swap in the correct substitute, and verify before the deadline.

**By the end, your n8n instance will have zero references to the October 23 shutdown list, and a test run will prove each changed workflow still works.**

## What dies on October 23

OpenAI announced this wave on April 22, 2026, under the heading "Legacy GPT model snapshots." Every entry below has a shutdown date of 2026-10-23 (verified on OpenAI's deprecations page, via [DigitalMatters](https://digitalmatters.me/artificial-intelligence-ai/openai-october-2026-model-shutoff/) and the [modeldeprecations.dev mirror](https://github.com/mnfst/modeldeprecations.dev/blob/HEAD/snapshots/openai/deprecations.md)):

| Dead model / snapshot | Affected aliases | OpenAI's substitute |
|---|---|---|
| `gpt-3.5-turbo-0125` | `gpt-3.5-turbo`, `-completions` versions | `gpt-5.6-terra` |
| `gpt-4-0613` | `gpt-4`, `-completions` versions | `gpt-5.6-sol` |
| `gpt-4-1106-preview` | — | `gpt-5.6-sol` |
| `gpt-4-turbo` | `gpt-4-turbo-2024-04-09` | `gpt-5.6-sol` |
| `gpt-4.1-nano` | `gpt-4.1-nano-2025-04-14` | `gpt-5.6-luna` |
| `gpt-4o-2024-05-13` | — | `gpt-5.6-sol` |
| `gpt-image-1` | — | `gpt-image-2.5-sunburst` or `-flare` |
| `o1-2024-12-17` | `o1` | `gpt-5.6-sol` |
| `o1-pro-2025-03-19` | `o1-pro` | `gpt-5.6-sol` (reasoning mode pro) |
| `o3-mini-2025-01-31` | `o3-mini` | `gpt-5.6-sol` |
| `o4-mini-2025-04-16` | `o4-mini` | `gpt-5.6-terra` |
| `ft-gpt-3.5-turbo`, `ft-gpt-4`, `ft-gpt-4.1-nano-2025-04-14`, `ft-o4-mini-2025-04-16`, `ft-babbage-002`, `ft-davinci-002` | — | must rebuild on a current base |

Three smaller waves already passed — September 24 (the entire Sora 2 family and Videos API, with *no replacement offered*), September 28 (the last GPT-3-era names), October 1 (`gpt-5.4-cyber`). OpenAI has shown it follows through. This wave has been "deprecated" since April; October 23 is when the models are simply gone.

**Prerequisites**

- A self-hosted or cloud n8n instance with workflows that call OpenAI (the OpenAI node, the AI Agent node with an OpenAI model, or HTTP Request nodes hitting the API directly).
- An OpenAI API key with access to the GPT-5.6 family substitutes listed above.
- `jq` installed if you want the fast audit route, and the ability to export workflows from n8n.

**Example terminology** — replace these placeholders in every command:

- `<dead-models>` — one of the model strings from the table above.
- `<n8n-host>` — your n8n host, e.g. `https://n8n.example.com`.
- `<api-key>` — your OpenAI API key (keep it out of chat logs and version control).

## Step 1 - Audit every workflow for dead model strings

The model you named in your code is easy to find. What your frameworks chose for you is not: LangChain's `ChatOpenAI()` with no `model=` argument still sends `gpt-3.5-turbo` by default — a request that dies on October 23 even though you never typed the name.

![A laptop showing program code on screen — the kind of place where dead OpenAI model strings hide in your workflow exports](/images/openai-legacy-models-shutdown-oct-23-migration/laptop-code.jpeg)

The fastest reliable audit is a text search over your exported workflow JSON. Export each workflow from the n8n UI (Workflow menu → Export → Download), then run:

```bash
grep -rEo '"model":\s*"[^"]*"' workflows/ | sort | uniq -c | sort -rn
```

This prints every model string your workflows reference, with counts — scan the output against the shutdown table above. In the n8n UI, you can also check each AI Agent node's model selector, but the grep catches what the UI misses: pinned model strings inside credentials, Code nodes, and HTTP Request bodies.

> **Note:** Bare aliases count. If your code says `gpt-4.1-nano` or `o4-mini` rather than the dated snapshot, it is still on this list — OpenAI listed those names as their own rows. And `gpt-4o-2024-05-13` is a GPT-4o snapshot, not GPT-4: if you pinned it in 2024 for reproducibility, you are affected.

**You should see** either zero matches against the shutdown list (you are already safe) or a list of files to fix. Keep that list — it becomes your migration checklist.

## Step 2 - Map each dead model to its substitute

Use the mapping table above, choosing the OpenAI-recommended substitute per row. Two decisions to make consciously:

- **Cost.** The 5.6 family has different pricing than the 2023-era models it replaces — a workflow running millions of `gpt-4-0613` calls per month will not cost the same on `gpt-5.6-sol`. Check OpenAI's current pricing page before migration day and budget for it, rather than discovering the difference on the 24th.
- **Quality.** `gpt-5.6-terra` is OpenAI's suggested replacement for the cheap tier (`3.5-turbo`, `o4-mini`), not a clone of it. Run your changed workflows with real inputs (Step 4) before you trust the swap in production.

Also decide now whether to test `gpt-6` Sol/Luna as well: OpenAI's April guidance pointed to GPT-5.6, but for the newest deprecation waves it points to GPT-6, and GPT-6 pricing was cut at launch. If you are rewriting prompts anyway, one comparison run is cheap.

## Step 3 - Swap the models in n8n

Open each flagged workflow and change the model in the OpenAI node's **Model** field (or the equivalent parameter in a Code/HTTP node). In n8n:

1. Open the workflow, click the AI Agent or OpenAI node.
2. Change **Model** to the substitute from the table.
3. If the node used a model pinned in an expression (e.g. `={{ $json.model }}`), trace where that value comes from and update it at the source.
4. Save and activate.

> **Warning:** Do this even for workflows that are currently turned off. OpenAI applies shutdown to the model, not your usage pattern — a disabled workflow you re-enable on October 24 fails silently at 3 AM. The grep in Step 1 already found them; don't skip them now.

If you use LangChain inside a Code node, add the explicit `model=` parameter rather than relying on the default — the default was the trap to begin with.

## Step 4 - Rebuild any fine-tuned models now — they cannot be converted

This is the one step with no shortcut. Fine-tuned variants (`ft-gpt-3.5-turbo`, `ft-gpt-4`, `ft-gpt-4.1-nano-2025-04-14`, `ft-o4-mini-2025-04-16`, `ft-babbage-002`, `ft-davinci-002`) shut down alongside their base models, and OpenAI states that inference on fine-tuned models keeps working only until the base model is deprecated. You must **retrain on a current base** (`gpt-5.6-terra`, `gpt-5.6-sol`, or `gpt-5.6-luna`) — there is no export-and-import path.

If retraining is impossible before October 23, prepare a fallback: point the workflow at the base substitute with few-shot examples in the prompt, and schedule the retrain as debt, not a plan.

## Step 5 - Verify every changed workflow

For each migrated workflow, run one test execution with realistic input and check the result — not just that it completes, but that the output quality matches what the old model produced. Then:

1. Confirm the OpenAI **Usage** dashboard shows calls hitting the new model names.
2. Set a one-time calendar reminder for October 23 to check error logs — you want to find any missed reference that day, not when a customer does.
3. Pin the new model name explicitly everywhere. You have now learned why defaults and bare aliases are a liability.

## Hard cases and limits

- **ChatGPT is not affected** by this shutdown — it applies to the API, not the consumer product. Azure OpenAI has its own retirement timeline; check your Azure portal if you use it.
- **I did not verify substitute pricing or quality myself.** The substitutes are OpenAI's official recommendations, not tested benchmarks — measure before you trust them at scale.
- **The `gpt-image-1` replacement is the vaguest row:** OpenAI lists `gpt-image-2.5-sunburst` or `-flare` in one source and `gpt-image-2` in another. Test image generation outputs before the 23rd if visuals are part of your product.
- This post covers the October 23 wave only. December brings the shutdown of the `gpt-5` August snapshots (`gpt-5-2025-08-07`, mini/nano/pro, `o3-2025-04-16`) — keep the grep from Step 1; you will run it again.

## FAQ

### What happens to a workflow still calling gpt-4 on October 23?

The API call fails — OpenAI removes the model entirely, so there is no graceful degradation and no automatic redirect to a newer model. Every affected n8n workflow errors on its next run.

### Is the bare name `gpt-4` affected, or only dated snapshots like `gpt-4-0613`?

Both. OpenAI listed short names and bare aliases (`gpt-4`, `gpt-4-turbo`, `gpt-4.1-nano`, `o1`, `o1-pro`, `o3-mini`, `o4-mini`, `gpt-3.5-turbo`) as their own rows with the same October 23 shutdown date.

### Do I need to migrate if my workflows only use GPT-5 models?

No. This wave touches legacy GPT-3.5/4, the o-series snapshots, `gpt-4.1-nano`, and `gpt-image-1`. Current GPT-5.6 and GPT-6 models are the safe targets.

### What about my fine-tuned gpt-3.5-turbo model?

It shuts down on October 23 with the base model. You must retrain on a supported base (`gpt-5.6-terra`, `-sol`, or `-luna`); there is no conversion path. Start now — retraining is the longest lead-time item on this checklist.

## Key Takeaways

1. **29 model IDs and snapshots go dark on October 23** — `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`, `gpt-4.1-nano`, the o-series, and all their fine-tunes, plus `gpt-image-1`.
2. **Grep your exported workflow JSON first** — the audit takes minutes and catches the traps: bare aliases, framework defaults, and pinned snapshots.
3. **Swap to OpenAI's listed substitutes** (mostly `gpt-5.6-sol`, `terra` for the cheap tier, `luna` for nano) and test output quality before trusting them.
4. **Fine-tunes must be rebuilt** — there is no migration path, only retraining. This is your longest lead time; start it today.

Next: keep the audit grep in a runbook and re-run it quarterly — the next wave (December, the `gpt-5` August snapshots) is already scheduled. For the bigger picture on keeping self-hosted n8n healthy, read our [n8n October 2026 Security Update](/blog/n8n-october-2026-security-update/).

*Images: Pexels*
