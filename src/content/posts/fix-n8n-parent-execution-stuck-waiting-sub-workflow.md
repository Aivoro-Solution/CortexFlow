---
title: "Fix n8n Parent Execution Stuck on 'Waiting' Forever After a Sub-Workflow Finishes"
description: "A parent n8n execution stays 'waiting' for hours after its sub-workflow finished. The WaitTracker race, the two log lines that prove it, and the fixes."
date: 2026-11-22
category: automation
tags: ["n8n", "error-fix", "executions", "sub-workflow", "wait-tracker"]
draft: false
featured: false
image: "/og/fix-n8n-parent-execution-stuck-waiting-sub-workflow.webp"
---

Your parent workflow calls a sub-workflow with the Execute Workflow node and waits for it to finish. The child runs, finishes successfully — and the parent never wakes up. Twelve hours later it is still sitting at status `waiting`, with no error anywhere, and the only evidence is two log lines repeating every minute. By the end of this post you will know exactly which race strands the parent, how to confirm it from your logs in thirty seconds, how to unstick a stuck parent, and the two fixes that stop it happening again.

## The symptom: a successful child, a parent that never resumes

The setup is ordinary. A parent workflow calls a sub-workflow through the Execute Workflow node with "Wait for Sub-Workflow Completion" enabled. The sub-workflow contains a Wait node, so it parks and is later resumed by n8n's WaitTracker. The child finishes with status `success`. The parent should resume with the child's result. Instead it stays `waiting` — in the reported case, for about 12 hours, until the reporter stopped it by hand.

What makes this one nasty is the silence. Nothing errors. The child execution looks healthy. The parent execution looks like it is still legitimately waiting. The same workflow ran fine twenty minutes earlier, because the bug is a timing race: it only bites when the child finishes inside a very short window. That is also why it is easy to dismiss as a one-off — until it strands a production chain at 3 a.m.

This was reported against n8n 2.46.7 in [GitHub issue #44762](https://github.com/n8n-io/n8n/issues/44762) (opened 2026-11-21, Linear GHC-9832, status `in-linear`, still open as of 2026-11-21). The reporter confirmed the same code path exists in 2.48.7, 2.49.3, 3.3.0 and current master, so this is not a version you can simply upgrade away from yet.

## The root cause: two resume paths, each waiting on the other

When a parent waits on a sub-workflow, n8n has two ways to resume it, and both live in `packages/cli/src/wait-tracker.ts`. The bug is that each path assumes the other one will handle the parent — and under one specific condition, neither does.

**Path 1 — the child finishes and tries to resume the parent.** When the child completes (it had resumed from a Wait node, so it goes through `WaitTracker.startExecution` → `resumeParentExecution`), n8n first writes the child's result into the parent (`patchParent` — this succeeds), then tries to claim the parent for resuming (`claimParent` → `startExecution(parent)`). That claim throws `ExecutionAlreadyResumingError` because the leader's 60-second `resumeParentsOfFinishedSubExecutions` sweep happens to be inspecting that parent at that exact moment — the parent is sitting in the sweep's `this.resuming` set between `this.resuming.add(parentId)` and `this.resuming.delete(parentId)` in `resumeParentIfChildFinished`. `claimParent` does not retry that error. It logs and returns, trusting the sweep to pick the parent up:

```
2026-11-21T05:09:44.981Z Parent execution not claimable: already claimed by another process, or not parked yet
```

**Path 2 — the sweep tries to resume the parent and finds nothing to resume from.** The sub-workflow has `saveDataSuccessExecution: "none"`, so its execution row is deleted as soon as it finishes. When the sweep's `patchParentWithFinishedChild` looks up the parent's `waitingChildExecutionIds`, there is no child row left. It logs and returns without claiming the parent:

```
2026-11-21T05:09:44.992Z Parent execution waits on sub-executions that no longer exist
```

That second line then repeats every minute, forever. The parent is never resumed.

The JSDoc on `claimParent` says a failed claim is picked up by `resumeParentsOfFinishedSubExecutions` on the next tick. That promise only holds when the child's row still exists. With `saveDataSuccessExecution: "none"`, the row is gone before the sweep can use it — and the result `patchParent` already wrote into the parent is never acted on.

Three conditions have to line up for the race to fire:

1. The sub-workflow has **Save Successful Production Executions set to "Don't Save"** (`saveDataSuccessExecution: "none"`), so its row is deleted on completion.
2. The sub-workflow **contains a Wait node** (waits longer than roughly 65 seconds go through the WaitTracker), so the child resumes through `WaitTracker.startExecution`.
3. The child **finishes while the 60-second sweep is inspecting that parent** — a window one database query wide. Most runs finish outside it, which is why the same workflow usually works.

## Diagnose it in thirty seconds

If a parent is stuck on `waiting` and you suspect this race, check two things:

1. **The logs.** Search for the two lines above, within milliseconds of each other, for the same parent. The first line (`Parent execution not claimable`) followed by the repeating `Parent execution waits on sub-executions that no longer exist` is the fingerprint. The second line repeating every minute is the giveaway that the sweep is re-inspecting a parent it can never resolve.
2. **The sub-workflow's settings.** Open the sub-workflow → Settings → Save Data → "Save Successful Production Executions". If it is set to "Don't Save" and the child execution shows `success` while the parent shows `waiting`, you have your match.

> **Note:** A parent can also sit on `waiting` legitimately — for example, while the child is genuinely still running, or while a Wait node is counting down. The race is confirmed only when the child has already finished successfully *and* the two log lines are present. Do not apply the fixes below to a parent that is waiting on a child that has not finished yet.

## Fix 1 — Keep the child's row until the sweep resolves (team workaround)

This is the immediate unblocker suggested by n8n team member grinem in the issue thread. On the **sub-workflow**, set Save Successful Production Executions to "Save All" (`saveDataSuccessExecution: "all"`), and rely on global pruning so the row does not pile up forever:

```bash
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=24
```

`EXECUTIONS_DATA_PRUNE=true` turns on automatic pruning of old execution data, and `EXECUTIONS_DATA_MAX_AGE=24` keeps rows for 24 hours before pruning them — long enough for the 60-second sweep to find the child row and resume the parent, short enough that execution data does not accumulate. Set both in your n8n environment (Docker Compose `environment:` block, or your deployment's env config) and restart n8n.

Why this works: with the child row surviving, the sweep's `patchParentWithFinishedChild` finds the finished child, claims the parent, and resumes it. The race window still exists, but the fallback the code relies on — "the sweep will pick it up" — actually holds.

The trade-off is real, and the reporter hit it: this stores the child's execution data in your database, even briefly. If the sub-workflow's execution data holds a short-lived per-run credential that you do not want persisted in Postgres at all, this fix is not acceptable for that workflow. That is exactly why the reporter needed Fix 2.

## Fix 2 — Decouple the handoff with a resume URL (reporter-verified)

If you cannot store the child's execution data, stop using "Wait for Sub-Workflow Completion" for that chain. The reporter restructured the parent–child handoff so it never touches `claimParent` or `resumeParentIfChildFinished` at all, and the chains have resumed cleanly since the change (2026-11-21):

1. In the **parent**, add a Wait node set to **"On Webhook Call"** where the Execute Workflow node used to wait. The Wait node exposes a resume URL through the `$execution.resumeUrl` expression.
2. Pass `$execution.resumeUrl` into the **sub-workflow** as an input parameter (for example, a `resumeUrl` field on the Execute Workflow node's input, or via the sub-workflow's input schema).
3. In the **parent**, call the sub-workflow with Execute Workflow set to **not** wait for completion (`waitForSubWorkflow: false`).
4. At the end of the **sub-workflow**, add an HTTP Request node that POSTs its result to the `resumeUrl` it received. The parent's Wait node receives the POST and resumes with the result as its output.

This replaces n8n's internal parent–child resume handshake with an explicit webhook callback. The child's execution row can be deleted immediately (`saveDataSuccessExecution: "none"`) because nothing ever needs to look it up again — the result travels in the POST body, not through the database.

> **Warning:** The resume URL is a capability URL — anyone who can POST to it can resume that waiting execution. Treat it like a credential: pass it only to the sub-workflow that needs it, never log it, and never expose it in a response or a shared workflow.

## Fix 3 — Watch for the upstream fix (PR #44765)

Community contributor Arin004joshi opened [PR #44765](https://github.com/n8n-io/n8n/pull/44765), which makes the handoff deterministic: when the child finishes while the sweep is inspecting the parent, `WaitTracker` now waits for the local inspection to release before retrying the parent claim. The retry is limited to `ExecutionAlreadyResumingError` caused by local contention, so cross-process claim behaviour is unchanged.

The reporter tested the PR against 2.46.7 with a toxiproxy harness that stretches the sweep's inspection to a few seconds (500 ms of latency on every Postgres reply) and fires 90 parent/sub-workflow pairs timed to finish inside the window:

| n8n 2.46.7 | Parents finished `success` | Parents still `waiting` 3 min after the last child was due |
| --- | --- | --- |
| Stock | 80 | **10** |
| With PR #44765 | 90 | **0** |

The patched run also logged 18 waits on the sweep's inspection — claims that hit the window and waited it out instead of giving up. As of 2026-11-21 the PR is open and unmerged, so there is no fixed version yet. Watch for a release containing PR #44765, then upgrade and re-enable `saveDataSuccessExecution: "none"` on the child if you had switched it to `"all"` as a stopgap.

Two honest limits from the PR discussion. First, the fix covers local contention only: in multi-main setups, a follower handling the child's resume can still hit a `local: false` claim conflict that is not retried, though the default `N8N_EXECUTIONS_MAX_RESUME_ATTEMPTS=2` usually grants the follower the next attempt. Second, there is a separate edge case outside the PR's scope: if the child finishes before the parent is even parked, and its row is deleted before any result can be patched into the parent, there is no result for the sweep to apply.

## What to do with a parent that is already stuck

A stuck parent will not resume on its own — the sweep logs the same line every minute and moves on. Stop the parent manually from the Executions tab (that is what the reporter did after 12 hours). Be aware that stopping it discards the result `patchParent` already wrote into it: if the downstream work matters, re-run the parent after applying Fix 1 or Fix 2. Then check the logs for the two fingerprint lines — if they are there, you have confirmed the race rather than a genuinely slow child.

## Verify the fix worked

After applying Fix 1 or Fix 2, run the parent–child chain a few times and check three things:

1. The parent reaches `success` within a minute of the child finishing — no parent left on `waiting` after the child shows `success`.
2. The logs show **no** `Parent execution not claimable` line for that parent, and no repeating `Parent execution waits on sub-executions that no longer exist` lines.
3. With Fix 2, the parent's Wait node output contains the result the sub-workflow POSTed — confirm the payload arrives intact before you trust the chain in production.

If you are on a latency-sensitive setup (remote Postgres, slow disk), the race is more likely to fire, because the sweep's inspection lasts longer. That is worth knowing when you decide whether to apply Fix 2 pre-emptively to your most critical chains.

## Prevent it next time

- **Audit your sub-workflows now:** any child with Save Successful Production Executions set to "Don't Save" *and* a Wait node inside it is exposed to this race. Either switch it to "Save All" with pruning on, or convert the chain to the resume-URL pattern.
- **Alert on the log line, not on the status:** a parent stuck on `waiting` looks identical to a parent legitimately waiting. Add a log alert for `Parent execution waits on sub-executions that no longer exist` repeating more than twice — that line should never repeat in a healthy instance.
- **Do not rely on "it worked last time":** the race window is one database query wide. A chain that ran fine twenty minutes earlier can strand the next run. If a chain is business-critical, Fix 2 removes the race entirely instead of narrowing it.

## FAQ

### Does this affect n8n Cloud?

The report is from a self-hosted instance (Docker on Kubernetes, PostgreSQL, main mode). The code path is the same on Cloud, but Cloud instances do not expose the WaitTracker logs, so you would see the symptom — a parent stuck on `waiting` after a successful child — without the fingerprint lines. If you hit that on Cloud, the Fix 2 restructure still applies, and the upstream fix in PR #44765 will reach Cloud automatically when it ships.

### Is "Wait for Sub-Workflow Completion" broken in general?

No. Most runs finish outside the sweep's inspection window and resume normally — the reporter measured 80 out of 90 parents succeeding on stock 2.46.7 even under artificially stretched timing. The bug is a race, not a constant failure. But "usually works" is the wrong reliability bar for a production chain, which is why the fixes above matter.

### I already have EXECUTIONS_DATA_PRUNE on. Am I safe?

Only if the child row survives long enough. Pruning deletes rows older than `EXECUTIONS_DATA_MAX_AGE`; the race needs the row to exist when the sweep inspects the parent, which is within a minute of the child finishing. A short max age (hours, not minutes) is fine. What breaks the fallback is `saveDataSuccessExecution: "none"` on the child, which deletes the row immediately — pruning settings do not help there.

## Key Takeaways

1. **A parent stuck on `waiting` after a successful child is a WaitTracker race, not a slow child** — the child-completion path and the 60-second sweep each assume the other will resume the parent.
2. **The fingerprint is two log lines milliseconds apart** — `Parent execution not claimable` followed by the repeating `Parent execution waits on sub-executions that no longer exist`.
3. **The trigger is `saveDataSuccessExecution: "none"` on a child that contains a Wait node** — the child's row is deleted before the sweep can use it.
4. **The quick fix is "Save All" on the child plus `EXECUTIONS_DATA_PRUNE=true`** with a short `EXECUTIONS_DATA_MAX_AGE` — unless the child's data must never be stored.
5. **The robust fix is a resume-URL callback** — parent waits on a webhook, child POSTs its result to `$execution.resumeUrl`, and the internal handoff is bypassed entirely.
6. **PR #44765 fixes the race upstream** (reporter-tested: 10/90 stuck on stock, 0/90 patched) — watch for a release containing it, and note it does not cover the multi-main `local: false` gap.

Next: if you run parent–child chains in production, audit every sub-workflow for the "Don't Save" + Wait node combination today — the check takes two minutes per workflow, and the next stranded parent will not announce itself any louder than a log line you are not watching.
