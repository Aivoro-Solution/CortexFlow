---
title: "Fix n8n Anthropic Chat Model Failing After Sonnet 4.5 Retires on Nov 30"
description: "Anthropic retires claude-sonnet-4-5 on Nov 30, 2026, and n8n's Anthropic node still defaults to it. Switch models now to avoid 404 errors."
date: 2026-11-28
category: automation
tags: ["n8n", "error-fix", "anthropic", "claude", "ai-agent"]
draft: false
featured: false
image: "/og/fix-n8n-anthropic-sonnet-4-5-model-retires-nov-30.webp"
---

If your n8n workflow uses an Anthropic Chat Model node you added months ago and never touched since, it is about to break. Anthropic retires `claude-sonnet-4-5-20250929` on November 30, 2026 — two days from now — and n8n's Anthropic Chat Model node version 1.3 still ships that exact model as its default. After the retirement date, every request to the retired model fails. By the end of this post you will know how to check whether your workflows are exposed, switch them to the replacement model, and verify the switch before the deadline hits.

Quick definitions: the **Anthropic Chat Model node** is n8n's node for calling Claude models from an AI Agent or chain. A **retired model** is one Anthropic no longer serves at all — unlike a deprecated model, which still works, requests to a retired model fail outright.

## The symptom: a 404 `not_found_error` starting November 30

Nothing is broken yet, which is what makes this dangerous. Your workflows run fine today. On November 30, 2026, Anthropic retires `claude-sonnet-4-5-20250929` (the retirement also covers the undated alias `claude-sonnet-4-5`). Per Anthropic's [model deprecations page](https://platform.claude.com/docs/en/about-claude/model-deprecations), once a model is retired, requests to it fail — on the Claude API, the Messages API returns a 404 `not_found_error`.

So the failure shape to expect is sudden and total: every execution of every workflow whose Anthropic node still points at Sonnet 4.5 starts erroring on the same day, with a 404 from the API rather than anything wrong in your workflow logic. If you run scheduled agents, they will fail on their first run after the retirement.

## The root cause: n8n's node default is the retiring model

This was filed as [GitHub issue #44398](https://github.com/n8n-io/n8n/issues/44398) on November 18, 2026, from a source review of n8n master. The Anthropic Chat Model node at version 1.3 defaults its model parameter to `claude-sonnet-4-5-20250929`. Any v1.3 node where you accepted the default — or picked Sonnet 4.5 deliberately — is wired to a model with a retirement date of November 30, 2026.

Anthropic announced the retirement on September 30, 2026, with `claude-sonnet-5-5` as the recommended replacement. The issue notes two complications with simply changing the default in n8n itself, which matter for your fix below: on node versions before 1.5, the Enable Thinking setting sends thinking configurations that Sonnet 5.5 rejects with a 400 error, and Sonnet 5.5 thinks by default when no thinking field is sent, so the node's `max_tokens` default of 4096 is worth revisiting. As of this writing the issue is open and no fixed n8n release has changed the v1.3 default — so do not wait for an update to save you. The fix is a two-minute edit in each affected node.

## The fix: move every Sonnet 4.5 node to Sonnet 5.5

### Step 1 - Find every exposed node

Open each workflow that uses Claude and check its Anthropic Chat Model node. You are exposed if the model field shows `claude-sonnet-4-5-20250929` or `claude-sonnet-4-5`. The version 1.3 nodes are the prime suspects because that is the version whose default is the retiring model, but any node on any version where Sonnet 4.5 was selected manually is equally exposed.

For a faster sweep, use Anthropic's own audit: in the Claude Console, open the Usage page, click Export, and review the CSV breakdown by API key and model. Any recent usage of `claude-sonnet-4-5-20250929` under the API key your n8n credential uses confirms live exposure.

### Step 2 - Change the model to `claude-sonnet-5-5`

In each exposed node, set the model to `claude-sonnet-5-5` — Anthropic's recommended replacement, active with no retirement sooner than September 28, 2027. Pick it from the node's model list rather than typing from memory, so a typo does not trade one 404 for another.

If the node is an old version (1.3 or earlier) and the model list does not offer Sonnet 5.5, add a fresh Anthropic Chat Model node instead, select `claude-sonnet-5-5`, reconnect it where the old node sat, and delete the old node. A fresh node also sidesteps the thinking-setting trap in Step 3.

### Step 3 - Check the Enable Thinking setting before you save

This is the step that turns a clean migration into a 400 error. On Anthropic node versions before 1.5, Enable Thinking sends configurations Sonnet 5.5 rejects: turned on, it sends `thinking: {type: "enabled", budget_tokens}`; added but left off, it sends `thinking: {type: "disabled"}`. Sonnet 5.5 rejects both with a 400 — its replacements are adaptive thinking with an effort level, and a `between_tools` mode for turning up-front thinking off.

So: if your v1.3 node has Enable Thinking present in either state, do not just change the model in place. Replace the node with a fresh one (Step 2's fallback) so the thinking options map to something Sonnet 5.5 accepts. If Enable Thinking was never added to the node, no thinking field is sent and the model change alone is safe.

### Step 4 - Revisit Max Tokens

With no thinking field sent, Sonnet 5.5 thinks by default, and thinking consumes output budget. The node's default `max_tokens` is 4096, and Anthropic's migration guide says to revisit it. If your agent produces long outputs — reports, drafts, structured JSON — raise Max Tokens above 4096 and watch the first runs for truncated responses. Short classification or extraction agents can usually keep the default.

### Step 5 - Verify before November 30

Run each migrated workflow once, end to end, today. Success looks like this: the Anthropic node returns a normal response with no 404 and no 400, and the output quality matches what Sonnet 4.5 produced. Then check the Claude Console usage export again after a day of runs — `claude-sonnet-4-5-20250929` usage under your key should drop to zero while `claude-sonnet-5-5` appears. Zero old-model usage before November 30 is the proof the deadline cannot hurt you.

## While you are in there: the older defaults are already dead

The same issue flags that n8n's Anthropic node versions 1, 1.1, and 1.2 default to models that are already retired (`claude-2`, `claude-3-sonnet-20240229`, `claude-3-5-sonnet-20240620`). If any workflow still carries a node that old, it is not waiting for a deadline — it is already broken or one edit away from it. Replace those nodes with fresh ones on `claude-sonnet-5-5` in the same pass.

One scope note: Anthropic's retirement dates apply to Anthropic-operated platforms (the Claude API and its managed variants). Partner-operated platforms such as Amazon Bedrock set their own schedules, so if your n8n credential reaches Claude through Bedrock rather than the Claude API directly, check that platform's model table for its own date.

## Prevent it next time

- **Never leave a model on its node default.** Pick the model explicitly when you build the node. A default you chose is a decision you can revisit; a default you inherited is a surprise with a date on it.
- **Check the deprecations page quarterly.** Anthropic gives at least 60 days' notice before retiring a public model — Sonnet 4.5 was announced September 30 for a November 30 retirement. A quarterly check of the [model deprecations page](https://platform.claude.com/docs/en/about-claude/model-deprecations) catches every retirement with time to spare.
- **Audit by API key, not by memory.** The Console usage export shows exactly which models your keys actually called. Run it whenever a retirement is announced instead of guessing which workflows are exposed.
- **Note the next one now:** `claude-opus-4-5-20251101` retires January 22, 2027, replaced by `claude-opus-5-5`. If any node uses Opus 4.5, schedule that migration today while the pattern is fresh.

## Honest limits

The November 30 retirement date and the `claude-sonnet-5-5` replacement are verified on Anthropic's own deprecations page, and the v1.3 default is verified in n8n's source via issue #44398. What is not verified is your instance: the issue was found by source review, not reproduced on a live instance, and whether n8n stores a parameter that equals its default in saved workflows is an open question in the thread. That uncertainty cuts one way only — if your node shows Sonnet 4.5 in the model field, treat it as exposed regardless of how it got there. Model behavior also shifts between versions; Sonnet 5.5 will not answer identically to 4.5, so the verification run in Step 5 should include an output-quality check, not just a green execution.

## FAQ

### My node shows `claude-sonnet-4-5` without the date. Am I affected?

Yes. Anthropic states the retirement includes `claude-sonnet-4-5`, the same model's ID without a date. Treat both spellings as exposed.

### Will updating n8n fix this automatically?

Not as of November 28, 2026. Issue #44398 is open, and changing the v1.3 default needs the thinking-mapping question settled first. Update n8n for other reasons if you like, but make the model change yourself.

### I changed the model and now get a 400 error. Why?

Almost certainly the Enable Thinking setting on a pre-1.5 node: it sends `enabled` or `disabled` thinking configurations that Sonnet 5.5 rejects. Replace the node with a fresh Anthropic Chat Model node, select `claude-sonnet-5-5`, and reconnect it.

### Does this affect Claude through Amazon Bedrock?

Not on Anthropic's dates. Bedrock is partner-operated and sets its own retirement schedule — check its model table for the date that applies to your deployment.

## Key Takeaways

1. **`claude-sonnet-4-5-20250929` retires November 30, 2026** — after that, requests fail with a 404 `not_found_error` on the Claude API.
2. **n8n's Anthropic Chat Model v1.3 defaults to exactly that model**, so untouched nodes are exposed; issue #44398 tracks it and no fixed release has landed yet.
3. **The fix is explicit**: set the model to `claude-sonnet-5-5`, replace pre-1.5 nodes that carry an Enable Thinking setting, and revisit the 4096 `max_tokens` default.
4. **Verify with the Console usage export** — zero Sonnet 4.5 calls under your API key before November 30 means the deadline cannot break you.

Next step: open your Claude Console usage export now and search it for `claude-sonnet-4-5`. If it appears, you have a short list of nodes to fix and two days to fix them. For the next retirement already on the calendar, Opus 4.5 on January 22, 2027, the same audit-and-swap pattern applies.
