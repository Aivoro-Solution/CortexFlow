---
title: "Fix n8n $('Node').first() Returning null for a Node's Error Output in Webhook Executions (2.46 Regression)"
description: "In n8n 2.46.0+, expressions reading a node's error output return null in production webhook runs — silently. Here's the verified cause and two workarounds."
date: 2026-11-19
category: automation
tags: ["n8n", "error-fix", "webhook", "expressions", "regression"]
draft: false
featured: false
image: "/og/fix-n8n-error-output-expression-null-2-46-regression.webp"
---

Your workflow runs. n8n reports success. And yet a downstream node receives `null` where an error message should be — no error, no warning, nothing in the execution log. If you upgraded to n8n 2.46.0 or later and your error-handling branches suddenly went quiet, you are probably hitting this regression. By the end of this post you will know exactly which expression pattern breaks, why it breaks, and the two workarounds that are verified to work today.

## The symptom: error output reads as null, but only in production webhooks

The pattern is specific, which is what makes it so hard to spot. A node is set to **On Error → Continue (using error output)**. A later node reads the error with an expression like `{{ $('Thrower').first().json.error }}`. On n8n 2.45.0 and earlier, that expression returns the error message. From 2.46.0 onward, in a **production webhook execution**, it returns `null`.

The reporter of [GitHub issue #44333](https://github.com/n8n-io/n8n/issues/44333) reproduced it methodically — 8 to 12 calls per version, identical results every time:

| Version / engine | `$('Thrower').first().json.error` | `$json.error` | try/catch around `$('Thrower').first(1)` |
|---|---|---|---|
| 2.34.5, 2.40.0, 2.44.0, 2.45.0 | `boom` | `boom` | OK |
| 2.46.0, 2.47.5, 2.48.4 (default engine) | **null** | `boom` | `ERR: #<Object> could not be cloned.` |
| 2.47.5, `N8N_EXPRESSION_ENGINE=legacy` | `boom` | `boom` | OK |

Three details from that table matter more than the rest:

- **Only the reference to the node that produced the error output fails.** `$json` in a node downstream of the error branch still carries the error, and a reference to a passthrough node sitting on the error output (`$('Pass').first()`) still works.
- **Only production webhook executions fail.** The same workflow run with `n8n execute` on 2.47.5 passes. Manual runs in the editor are unaffected, which is why this slips past testing.
- **Wrapping the expression in try/catch does not help.** It throws `#<Object> could not be cloned.` instead — a clue that points straight at the root cause.

The real-world damage is silent data corruption, not a crash. In the reporter's case, a Redis node's whole parameter became `null` and the push failed with "Invalid argument type". With other nodes the `null` would have been written downstream as an empty value with no error at all.

> **Note:** This is not the same bug as the 1.123.x Code-node issue covered in [Fix n8n $('Code') Expressions Resolving to null After Upgrading to 1.123.x](/blog/fix-n8n-code-node-expressions-resolve-null/). That one (issue #41588) hit Code nodes with task runners disabled and was fixed in #42249. This one is 2.x, the default `vm` expression engine, error-output branches only, and webhook executions only.

## Root cause: the vm engine cannot clone the error across the isolate boundary

n8n team member grinem diagnosed it in the issue thread: the `# could not be cloned` error points directly at V8 structured cloning failing when the `vm` engine serializes raw `runData` across the isolate boundary for error output branches — the `Error` object's prototype and property descriptors are un-clonable.

In plain terms: when a node fails and n8n routes its output down the error branch, the error data is a live JavaScript `Error` object. The default expression engine in 2.46.0+ evaluates expressions inside an isolated V8 context, and data crossing into that isolate has to be serialized with structured cloning. A raw `Error` does not survive that trip. Instead of throwing a visible error, the lookup silently resolves to `null` — the worst possible failure mode for an error-handling path, because the one branch designed to catch problems is the one that goes blind.

The issue is team-assigned (Linear GHC-9806) and still open as of November 19, 2026. It affects 2.46.0 through the current stable 2.48.4, with no fixed version yet.

## Prerequisites

- A self-hosted n8n instance on 2.46.0 or later (Docker, npm, or any install where you can set environment variables).
- Access to restart n8n after changing environment variables (for Workaround A).
- The failing workflow, with a node set to **On Error → Continue (using error output)** and a downstream expression reading that node's output.

## Step 1 - Confirm you are hitting this bug, not a different null

Before changing anything, prove the diagnosis with the three-way check from the reproduction table. Add a Set node downstream of the error branch with these assignments:

```javascript
// Assignment 1 — the broken pattern
{{ $('Thrower').first().json.error }}

// Assignment 2 — the control that should still work
{{ $json.error }}

// Assignment 3 — the reference via a passthrough node on the error branch
{{ $('Pass').first().json.error }}
```

Replace `Thrower` with the name of your failing node, and `Pass` with a Code node on its error output that simply returns `$input.all()`.

Publish the workflow and call the **production** webhook URL (not the test URL). You should see:

- Assignment 1 returns `null`, assignments 2 and 3 return the error message — you are hitting this regression. Skip to Step 2 or Step 3.
- All three return the error — your null comes from somewhere else (check whether the node actually errored, and whether the expression references the right node name).
- All three return `null` — the error output branch is not running at all. Check the failing node's **On Error** setting is actually "Continue (using error output)" and that the workflow is published, not just saved.

> **Warning:** Do not test this with the editor's "Execute workflow" button or the test webhook URL. Those paths do not reproduce the bug — only a published workflow called on its production webhook URL fails.

## Step 2 - Workaround A: switch to the legacy expression engine

This is the only workaround the reporter verified that restores the broken pattern itself. Set the environment variable:

```bash
N8N_EXPRESSION_ENGINE=legacy
```

In Docker Compose, add it to the n8n service environment and recreate the container:

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:2.47.5
    environment:
      - N8N_EXPRESSION_ENGINE=legacy
```

Then restart n8n and re-run the Step 1 check against the production webhook. `$('Thrower').first().json.error` should return the error message again, and the try/catch variant should return `OK`.

Here is what each part does:

- `N8N_EXPRESSION_ENGINE=legacy` tells n8n to evaluate expressions with the pre-2.46 engine, which does not serialize `runData` across an isolate boundary, so the `Error` object never has to be cloned.
- The restart is required — n8n reads this variable at startup, and changing it in a running container does nothing.

**What does not work:** the reporter also tested `N8N_EXPRESSION_ENGINE_ALLOW_WEBHOOK_ISOLATE_SKIP=false`, `N8N_EXPRESSION_ENGINE_LAZY_ACQUIRE=false`, and `N8N_EXPRESSION_ENGINE_NATIVE_EVALUATION=false` on 2.47.5. None of them changed the result. Do not spend time on those toggles.

**The trade-off, stated plainly:** n8n marks the legacy engine as soon to be deprecated. This workaround buys you working error handling today, but it is not a permanent home. Treat it as a bridge until the fix lands in a 2.4x release, and re-test the default engine after every upgrade. If you cannot accept a deprecated engine even temporarily, use Workaround B instead.

## Step 3 - Workaround B: stop referencing the error node directly

If you would rather not touch the expression engine, restructure the workflow so no expression ever reads the failing node by name. Both of these patterns were verified working in the reproduction table on the affected versions:

**Option 1 — read `$json` downstream of the error branch.** Once an item has travelled down the error output, the error is part of that item's own JSON. Any node after the branch can use `{{ $json.error }}` (or `{{ $json.message }}` depending on the node's error shape) with no node reference at all.

**Option 2 — put a passthrough node on the error output and reference that instead.** A Code node with a single line:

```javascript
return $input.all();
```

wired to the failing node's error output, then reference the passthrough node — `{{ $('Pass').first().json.error }}` — instead of the failing node. The passthrough node's output is plain item data, not a raw `Error`, so it clones across the isolate boundary without trouble.

Option 1 is the smaller change when the error data is only needed one step downstream. Option 2 is better when several later nodes need the error, because they can all reference the one passthrough node by name.

> **Note:** Do not wrap the broken reference in try/catch as a "fix". On affected versions it throws `#<Object> could not be cloned.` — you would be trading a silent null for a loud error in a branch whose whole job is to handle errors gracefully.

## Step 4 - Verify the fix end to end

Re-run the Step 1 check against the production webhook URL after applying your chosen workaround. You should see all three assignments return the error message. Then trigger the real failure path once more — not just the reproduction workflow — and confirm the downstream node receives the actual error text instead of `null`.

If you used Workaround A, also confirm the legacy engine did not change any other expression behaviour in the same workflow: run one normal (non-error) execution and compare its output against the previous version's.

## Prevent it next time

- **Test error branches on the production webhook after every upgrade.** Manual runs and `n8n execute` do not reproduce this class of bug. One call to the production URL with a forced error, checking that the error text arrives downstream, would have caught this before it reached real traffic.
- **Pin your n8n version and read the changelog before upgrading.** If you are on 2.45.0 and your workflows rely on error-output expressions, stay there until a release note mentions GHC-9806 or the fix for issue #44333.
- **Prefer `$json` over `$('Node')` references in error-handling branches.** A downstream node reading its own input is immune to this whole class of cross-node serialization bugs. Use named node references only where the data genuinely lives on another branch.
- **Add a canary to error-handling workflows.** A Set node that writes the error text to a log, or an IF node that alerts when the error field is empty, turns the next silent null into a visible failure instead of corrupted data.

## FAQ

### Does this affect manual runs or the test webhook URL?

No. The reporter confirmed the same workflow passes with `n8n execute` and the bug appears only in production webhook executions. That is exactly why it is dangerous: everything looks fine in the editor.

### Does it affect all `$('Node').first()` references, or only error output?

Only references to the node that produced the error output. References to any other node — including a passthrough node on the same error branch — work normally, as does `$json`.

### Is the legacy engine safe to use?

It is the engine n8n shipped before 2.46.0, and it is the reporter's verified workaround on 2.47.5. The risk is not stability but longevity: n8n marks it as soon to be deprecated, so plan to re-test the default engine after the fix ships rather than settling on legacy permanently.

### What about `N8N_EXPRESSION_ENGINE_ALLOW_WEBHOOK_ISOLATE_SKIP` and the other toggles?

The reporter tested all three on 2.47.5 and none changed the result. They are not workarounds for this bug.

## Key Takeaways

1. **n8n 2.46.0 through 2.48.4 silently null out expressions that read a node's error output in production webhook executions** — `$('Node').first().json.error` returns `null` with no error.
2. **The cause is V8 structured cloning**: the default `vm` engine cannot serialize the raw `Error` object across the isolate boundary for error-output branches (issue #44333, Linear GHC-9806, still open as of November 19, 2026).
3. **Two verified workarounds**: set `N8N_EXPRESSION_ENGINE=legacy` and restart, or stop referencing the failing node directly — read `$json` downstream, or reference a passthrough Code node on the error branch.
4. **Test error branches on the production webhook after every upgrade** — manual runs do not reproduce this bug, and a silent null in an error handler corrupts data instead of failing loudly.

Next: watch [issue #44333](https://github.com/n8n-io/n8n/issues/44333) for the fixed version, then remove the legacy-engine setting and re-run the Step 1 check on the default engine before calling the workaround done.
