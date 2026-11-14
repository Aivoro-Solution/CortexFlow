---
title: "Fix n8n OpenAI Image Generation Breaking on December 1, 2026 (gpt-image-1-mini Retires, GH #43892)"
description: "OpenAI retires gpt-image-1-mini on Dec 1, 2026 — the default model of n8n's OpenAI image node. Switch to gpt-image-2.6 before your workflows break."
date: 2026-11-14
category: automation
tags: ["n8n", "openai", "image-generation", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-openai-gpt-image-1-mini-retired.webp"
---

Your image-generation workflow works today. On December 1, 2026, it stops — with no code change on your side, no n8n upgrade, and no warning inside the editor. The reason is not an n8n bug. OpenAI is retiring `gpt-image-1-mini`, and that model is the **default** of the OpenAI node's Generate an Image operation. Every workflow that kept the default will start failing on December 1.

This is the worst kind of breakage: a silent calendar deadline. The workflow will keep running on schedule, the node will call OpenAI, and OpenAI will refuse the request because the model no longer exists. If the workflow has no error handling, the failure shows up as a failed execution — or worse, as a downstream step that silently receives no image.

This is a confirmed, dated retirement, not a rumor. OpenAI's own [deprecations page](https://developers.openai.com/api/docs/deprecations) lists `gpt-image-1-mini` with a shutdown date of December 1, 2026, and the issue was filed against n8n as [GitHub issue #43892](https://github.com/n8n-io/n8n/issues/43892) on November 13, 2026 (team-assigned, still open as of November 14, 2026). By the end of this article you will know how to find every affected workflow, which replacement model to pick, what the switch costs, and how to make sure a model retirement never ambushes you again.

Quick definitions before we start: a **model retirement** (or shutdown) is when an API provider permanently stops serving a model — requests naming it are rejected, usually with a "model does not exist" error. The **OpenAI node** is n8n's built-in node for calling OpenAI; its **Image resource, Generate an Image operation** is the step that turns a text prompt into an image. A **default model** is the value the node ships with — the one you get if you never touch the Model dropdown.

## The symptom: working workflows fail on December 1, nothing changed

The failure looks like this. A workflow that has generated images fine for months — product mockups, social-media art, thumbnails — starts failing on its first run after December 1. The OpenAI node returns an error along the lines of "The model does not exist", and the execution fails at that step. Nothing in your workflow changed. Nothing in your n8n version changed. The only thing that changed is on OpenAI's side: the model is gone.

Based on what happened when `gpt-image-1` shut down on October 23, 2026, the error is expected to read like `The model 'gpt-image-1-mini' does not exist.` — OpenAI returned exactly that phrasing for `gpt-image-1`, and the same message is expected here (it has not been observed yet, because the shutdown has not happened).

**Which workflows are affected?** Any workflow with an OpenAI node set to Resource: Image, Operation: Generate an Image, where the Model field is still the default `gpt-image-1-mini`. That is the default on OpenAI node version 2.2 and later — which means most image workflows built in the last few months. The trap is that "I never chose a model" feels like a safe, neutral state. It is not: the default is a specific model with a specific retirement date.

Workflows on older OpenAI node versions are in worse shape, and they may already be broken:

| Model in your node | Status as of November 14, 2026 |
|---|---|
| `dall-e-2` | Shut down May 12, 2026 — already broken |
| `dall-e-3` | Shut down May 12, 2026 — already broken |
| `gpt-image-1` | Shut down October 23, 2026 — already broken |
| `gpt-image-1-mini` | Shuts down **December 1, 2026** — 17 days left |
| `gpt-image-1.5` | Shuts down **December 1, 2026** — 17 days left |
| `chatgpt-image-latest` | Shuts down **December 1, 2026** — 17 days left |
| `gpt-image-2` | Shuts down February 10, 2027 — do not migrate to this one either |

The older node versions (before 2.2) offer only `dall-e-2`, `dall-e-3`, and `gpt-image-1` — all three are already retired. If your node is on one of those versions, your image step has been failing since October 23 at the latest, and the fix below covers you too.

> **Note:** the December 1 shutdown also catches anyone who "fixed" the October 23 `gpt-image-1` shutdown by switching to `gpt-image-1-mini` or `gpt-image-1.5`. Those were reasonable moves in October. They are not fixes anymore — both models are on the same December 1 list.

## The root cause: a default that points at a retiring model

The issue reporter found the problem by reading n8n's source, not by hitting the error. In `packages/@n8n/nodes-langchain/nodes/vendors/OpenAi/v2/actions/image/generate.operation.ts`, the Model parameter ships with `default: { mode: 'list', value: 'gpt-image-1-mini' }`. n8n sets a sensible default when the node version ships, and then the world moves on: OpenAI announced on June 2, 2026 that the whole GPT Image 1 family would leave the API on December 1, and the n8n default never changed.

That is the entire root cause. There is no misconfiguration on your side and no bug in the node logic — the default simply names a model that is about to stop existing. The n8n team has the issue assigned (Linear ticket, status in-linear), but no n8n release can change what OpenAI serves after December 1. The only fix that works is changing the model in your workflows, which is something you do yourself, today.

OpenAI's listed replacements for all three December 1 models are `gpt-image-2.6-sunburst` or `gpt-image-2.6-flare`. Two things to know about them before you pick:

- **They cost more.** The 2.6 models use roughly 4.2× the image tokens of `gpt-image-1-mini` at low quality — about $0.025 per 1024×1024 low-quality image versus about $0.005 for `gpt-image-1-mini` (same $30-per-million-token rate; the token count is what grows). Budget for the increase, or drop the quality setting (Step 3) to compensate.
- **They default to high complexity when the parameter is left unset**, per the issue report, which can change both cost and speed for existing workflows. Set the quality explicitly instead of leaving it to the default.

OpenAI's own prompting guide says to start with GPT Image 2.6 Flare if response time matters most — so Flare is the latency-sensitive pick; try Sunburst first otherwise, and compare both on a sample of your own prompts, because OpenAI does not document a simple quality mapping between the two.

## Step 1 - Find every affected workflow

Before changing anything, find out how many workflows use a retiring model. Checking nodes one by one in the editor is slow and misses the workflow you forgot about, so audit from the exported JSON instead. This works on any self-hosted instance.

Export all workflows to a folder and grep for every retiring model id:

```bash
docker exec -it <your-n8n-container> n8n export:workflow --all --output=/tmp/workflows
grep -rl "gpt-image-1-mini\|gpt-image-1\.5\|chatgpt-image-latest\|gpt-image-1\"\|dall-e-2\|dall-e-3\|gpt-image-2\"" /tmp/workflows
```

Here's what each part does: `n8n export:workflow --all` dumps every workflow as JSON, and the `grep` lists the files that name any retiring model. Each match is a workflow you must fix. If `grep` prints nothing, your image workflows are already on a supported model — skip to Step 4 and set the prevention guard anyway.

> **Note:** the `\"` after `gpt-image-1` in the pattern matters — without it, the pattern also matches `gpt-image-1-mini` and `gpt-image-1.5`, which you want listed separately so you can see which workflows are already broken versus which break on December 1.

If you run n8n Cloud, there is no shell to run the export in. Open each workflow that generates images, click the OpenAI node, and read the Model field directly. Start with the workflows that run on a schedule — those are the ones that will fail unattended on December 1.

## Step 2 - Switch the model to gpt-image-2.6

Open the OpenAI node in each affected workflow and change one field:

1. Set **Resource** to `Image` and **Operation** to `Generate an Image` (they already are, if the workflow generates images).
2. Click the **Model** field and select — or type, if the list does not offer it yet — `gpt-image-2.6-sunburst`.
3. Save the workflow. If the workflow is active, **publish** it: in n8n 2.x, saving alone does not change what production runs — see [Fix n8n Workflow Changes Not Taking Effect in Production](/blog/fix-n8n-workflow-changes-not-taking-effect/) if that surprises you.

Do not pick `gpt-image-1.5`, `chatgpt-image-latest`, or `gpt-image-2` as the replacement. The first two shut down on the same December 1 date, and `gpt-image-2` shuts down February 10, 2027. Any of those just moves the failure to a later date. The only models OpenAI lists without a shutdown date right now are the 2.6 pair (and the 2.5 pair, which OpenAI lists as the replacement for the already-retired `gpt-image-1` — usable, but 2.6 is the current recommendation).

If you are on an OpenAI node older than version 2.2 — the version field shows in the node settings — upgrade n8n first, then switch the model. The old node versions cannot select a 2.6 model at all, and every model they offer is already retired.

## Step 3 - Set quality explicitly and check the cost

The replacement is not a drop-in on price or speed. Before you call the migration done, set the quality and measure the difference.

In the same OpenAI node, open the options and set **Quality** explicitly — `low` for thumbnails and drafts, `medium` for general use — instead of leaving it unset, where the 2.6 models default to high complexity. Then run the node once with a prompt you have used before and compare: same prompt, new model, and check the output image, the execution time, and the token usage in the execution data.

You should see a successful image and a higher token count than `gpt-image-1-mini` used for the same prompt. At low quality, expect roughly a 5× cost per image (about $0.005 → about $0.025 for 1024×1024). If the workflow generates images in bulk — dozens or hundreds per day — multiply that out before December 1, because the cost change lands on the same day as the deadline. If the new cost is unacceptable, `gpt-image-2.5-sunburst` / `gpt-image-2.5-flare` are the cheaper current-generation alternative (about $0.006 at low quality), with no shutdown date listed — but verify that against OpenAI's deprecations page on the day you switch, because the replacement list has already changed once (2.5 → 2.6) in November.

## Step 4 - Verify the fix end to end

Run one affected workflow manually after the switch and confirm three things:

1. The OpenAI node returns an image (binary output present, no error).
2. The execution data shows the new model id — search the execution for `gpt-image-2.6` to confirm the node actually sent what you selected.
3. The downstream steps still work — if anything downstream reads the image's size, format, or filename, confirm it handles the new model's output the same way.

Then re-run the audit from Step 1. The `grep` should now return zero matches for the retiring models. If it still matches, a workflow was missed — usually one that was inactive, or a sub-workflow called by an Execute Workflow node. Sub-workflows have their own OpenAI nodes; audit them too.

## Prevent it next time: never trust a default model

Model retirements are not rare — OpenAI alone has retired three image models in 2026, with `gpt-image-2` already scheduled for February 10, 2027. Three habits make the next one a non-event:

- **Pin the model explicitly in every node, and record the date.** A default you never chose is a dependency you never reviewed. When you set a model, note its shutdown date in the workflow's name or notes.
- **Monitor retirements programmatically.** OpenAI's List Models endpoint (`GET /v1/models`) returns an optional `shutdown_date` field per model. A small scheduled workflow that fetches that list monthly and alerts you when a model you use gains a shutdown date turns a surprise into a ticket.
- **Check the deprecations page when you upgrade n8n.** A node upgrade can change defaults — and a default can already be retired by the time you adopt it. OpenAI's deprecations page is the source of truth; aggregator "shutdown" lists have repeatedly been wrong about dates.

## FAQ

### Will n8n fix this with an update before December 1?

Maybe — the issue is team-assigned — but an n8n update can only change the default for *new* nodes. It cannot rewrite the model id stored in your existing workflows. Even if a fix ships, you still need to update your existing nodes yourself.

### I switched to gpt-image-1.5 in October. Am I safe?

No. `gpt-image-1.5` is on the same December 1 shutdown list as `gpt-image-1-mini`. Switch again, to a 2.6 model, before December 1.

### Does this affect the Chat Model / text operations?

No. This is only the Image resource's Generate an Image operation. Text models have their own retirement schedule — `gpt-image-1-mini` is an image model, and its shutdown does not touch chat completions.

### What error will I see if I miss the deadline?

Expected: `The model 'gpt-image-1-mini' does not exist.` — the same phrasing OpenAI returned when `gpt-image-1` shut down on October 23, 2026. The exact wording for `gpt-image-1-mini` has not been observed yet, because the shutdown is still in the future.

## Key Takeaways

1. **`gpt-image-1-mini` stops working on December 1, 2026** — and it is the default model of n8n's OpenAI image node (v2.2+), so workflows that never chose a model are the ones that break.
2. **Switch to `gpt-image-2.6-sunburst` or `gpt-image-2.6-flare`** — the replacements OpenAI lists. Never "fix" it with `gpt-image-1.5`, `chatgpt-image-latest` (same December 1 date), or `gpt-image-2` (February 10, 2027).
3. **Budget for the cost change** — about 5× per image at low quality — and set quality explicitly, because the 2.6 models default to high complexity when it is left unset.
4. **Audit first, then verify** — export all workflows and grep for the retiring model ids; after switching, re-run the grep and confirm zero matches.
5. **Pin models and watch shutdown dates** — check `GET /v1/models` monthly, because this is the third image-model retirement of 2026 and it will not be the last.

Next: if your image step feeds an AI Agent, check the agent's memory and tool-call setup too — a failed tool call can kill the whole run silently, as covered in [Fix n8n AI Agent Stopping When a Tool Fails or Returns Empty](/blog/fix-n8n-ai-agent-tool-fail-stop/). And if you hit a different OpenAI error from n8n, [Fix Cloudflare 403 Blocking OpenAI Chat Model via n8n Gateway](/blog/fix-cloudflare-403-n8n-openai-gateway/) covers the gateway-side failure mode.
