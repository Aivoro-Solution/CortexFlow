---
title: "Fix n8n HTTP Request 'Never Error' Returning 401 Forever When a Credential Token Expires (GH #43839)"
description: "n8n's HTTP Request node with 'Never Error' on returns 401 forever once a short-lived token expires — the refresh never runs. Here's the fix."
date: 2026-11-14
category: automation
tags: ["n8n", "http-request", "authentication", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-http-request-never-error-401-token-refresh.webp"
---

Your scheduled workflow runs fine for an hour. Then, with no change on your side, every run after that starts returning `401 Bad credentials` — and it never recovers on its own. The HTTP Request node is not erroring. It is returning the 401 as data, run after run, forever. The credential is fine. The API is fine. The token just expired, and n8n never refreshed it.

This is a confirmed bug in n8n's execution engine, filed as [GitHub issue #43839](https://github.com/n8n-io/n8n/issues/43839) on November 13, 2026 (team-assigned, Linear ticket GHC-9757, still open as of November 14, 2026, reported against n8n 2.47.5 / 3.2.0). The trigger is a specific combination: an HTTP Request node with **"Never Error" turned on**, plus a credential whose token is fetched in `preAuthentication` and expires quickly — the GitHub App API credential is the named example, its installation token lasts one hour. By the end of this article you will know how to confirm you have hit this exact bug, apply the team-confirmed workaround in two minutes, and make sure no other workflow in your instance is silently stuck on the same trap.

Quick definitions before we start: **"Never Error"** is an HTTP Request node option that tells the node to return any HTTP status — including 4xx and 5xx — as a normal result instead of throwing an error. **preAuthentication** is the step where n8n fetches a fresh short-lived token for a credential before sending the request (the GitHub App credential does this to get an installation token). A **401** is the HTTP status for "unauthorized" — here it means the token the request carried is expired or invalid.

## The symptom: a 401 that never clears, returned as data

The failure looks like this. You have a scheduled workflow — say, every 30 or 60 minutes — that calls the GitHub API through an HTTP Request node with "Never Error" and "Include Response Headers and Status" turned on. The first runs after you set it up work. Then, once the installation token's one-hour lifetime lapses, a run returns this as ordinary output data:

```json
{
  "statusCode": 401,
  "message": "Bad credentials"
}
```

No execution fails. No error workflow fires. Nothing alerts you. And the next run returns the same 401, and the one after that, indefinitely — until a *different* request, one without "Never Error", happens to throw a 401 and trigger a refresh. The reporter put it plainly in the issue: a run every 30 or 60 minutes can refresh the token at the start of one run, and the token then expires during a later run. Scheduled workflows are the easiest way to hit this, because the gap between runs is exactly the gap in which the token dies.

**Which workflows are affected?** Any workflow where an HTTP Request node has "Never Error" on and authenticates with a credential that fetches a short-lived token in `preAuthentication`. The confirmed case is the GitHub App API credential (one-hour installation tokens). Any other credential that mints a short-lived token the same way is exposed to the identical failure. OAuth2 credentials are **not** affected — the OAuth2 path already handles this case, as the root-cause section explains.

## The root cause: the refresh only lives inside a `catch` block that never runs

The reporter diagnosed this by reading n8n's source, and an n8n team member confirmed the diagnosis in the issue thread. Here is the mechanism, in three parts.

**Part 1 — the refresh only happens after a thrown error.** Credentials that fetch a short-lived token in `preAuthentication` are refreshed in `requestWithAuthentication` only in its `catch` block: after an error is thrown, n8n calls `credentialsHelper.preAuthentication(..., true)` to mint a fresh token and resends the request once. That is the normal, working path — a 401 throws, the token is refreshed, the request is retried, and the workflow sees the successful response. The code lives in `packages/core/src/execution-engine/node-execution-context/utils/request-helpers/authentication.ts`.

**Part 2 — "Never Error" stops the error from ever being thrown.** When "Never Error" is on, the HTTP Request node sets `requestOptions.simple = false` (in `HttpRequestV3.node.ts`). With `simple: false`, a 401 does not throw — it resolves as a response. The `catch` block never runs, the expired token stays in the credential, and every subsequent request with "Never Error" returns the 401 to the workflow as data. There is no retry, no refresh, no recovery — the node is doing exactly what "Never Error" asked it to do, and that is precisely the problem.

**Part 3 — the OAuth2 path already fixed this; the preAuthentication path did not.** The OAuth2 flow in `request-helpers/oauth.ts` explicitly handles the case: its `retryWithNewToken` turns a resolved 401 under `simple: false` into its refresh path (the code even carries the comment "resolves with the original response under `simple: false` instead of throwing"). The `preAuthentication` path has no equivalent. Team member grinem confirmed it in the thread: "The discrepancy between `requestOAuth2` (which explicitly handles resolved 401s under `simple: false`) and `requestWithAuthentication` (which strictly encapsulates `credentialsHelper.preAuthentication` in `catch`) is definitely an oversight in the execution engine."

One more scope note from the reporter, verified by reading the code but not run live: `httpRequestWithAuthentication` — the helper other nodes use — has the same shape. It refreshes only in its `catch`, based on `error.response?.status`, so with `ignoreHttpStatusErrors` it should have the same gap. The proposed fix (below) does not cover that helper; a follow-up is planned.

> **Note:** this bug is silent by design. "Never Error" exists so workflows can handle error statuses as data — a legitimate pattern. The trap is that it also disables the one mechanism that keeps short-lived tokens alive. If your workflow treats a 401 as data and retries later, it will retry with the same dead token, forever.

## Step 1 - Confirm you have hit this bug, not a genuinely bad credential

Before changing anything, make sure the 401 is the expired-token trap and not a revoked app or a wrong credential. The distinction matters: a genuinely bad credential will not be fixed by any refresh.

1. Open the last execution and inspect the HTTP Request node's output. You should see `statusCode: 401` with a message like `Bad credentials`, returned as a normal item — the execution itself shows as successful.
2. Check the node: **"Never Error" is on** (Parameters → Options → Never Error, or "Respond" / "Response" settings depending on node version). If it is off and you still get 401s, this is not the bug — your credential is actually invalid.
3. Check the credential: it is a type that mints a short-lived token in `preAuthentication` — the GitHub App API credential is the confirmed one. If you use OAuth2, this bug does not apply.
4. Run the same request once **without** "Never Error" (temporarily toggle it off and execute the node manually). If the request now succeeds after a brief pause, you have confirmed the diagnosis: the thrown 401 triggered the refresh, and the retry went through with the fresh token.

You should see the node return a `200` with real data on that manual run. If it still returns 401 even with "Never Error" off, stop — the token refresh itself is failing, which means the credential (app installation, permissions, private key) is genuinely broken, and no setting in the node will fix it.

## Step 2 - Apply the team-confirmed fix: node-level error handling instead of "Never Error"

The fix is a settings swap, not a code change. Team member grinem gave it directly in the issue thread: handle the failure via the node's generic **Settings → On Error → Continue (using regular output)** rather than the HTTP-level "Never Error". Here is exactly what to do:

1. Open the HTTP Request node and turn **"Never Error" OFF**.
2. Open the node's **Settings** tab (the gear icon at the top of the node panel) and set **On Error** to **Continue (using regular output)**.
3. Save the workflow.

Why this works: with "Never Error" off, a 401 throws inside the node execution, exactly as it does on the normal path. The throw lands in the `catch` block of `requestWithAuthentication`, which refreshes the token and resends the request once — the workflow receives the successful response, and execution continues normally. The node-level "Continue (using regular output)" setting only changes what happens if the node *still* errors after that retry (for example, if the refresh itself fails because the app was revoked): instead of killing the whole workflow, the node outputs the error as a regular item and the workflow keeps running. You get the same "don't die on an error status" behavior "Never Error" gave you, but the token refresh gets to run first.

> **Warning:** do not "fix" this by turning "Never Error" off and leaving On Error at its default (Stop Workflow). That restores the refresh, but it also means any genuine 401 — a revoked GitHub App, a deleted installation — now kills the entire workflow instead of being handled. The node-level Continue setting is what keeps the workflow resilient. The two settings look similar; they are not interchangeable.

## Step 3 - Guard the error branch so a real auth failure is visible

With Step 2 in place, a refreshed retry succeeds transparently on the vast majority of runs. But the one case that still needs handling is a *genuine* auth failure — the refresh fails because the credential itself is broken. In that case the node outputs an error item on its regular output, and a downstream node that blindly reads `$json` fields will fail confusingly or, worse, process garbage.

Add an IF node directly after the HTTP Request node:

```javascript
// IF node condition — route to the "auth failed" branch when true
{{ $json.error !== undefined || $json.statusCode === 401 }}
```

Wire the true branch to a notification — a Slack message, a Telegram message, or an Error Trigger workflow — that says which workflow and credential failed. Wire the false branch to your normal downstream processing. This is a five-minute addition that turns the only remaining silent failure into an alert you will actually see.

You should see the IF node route every normal run down the false branch. To test the true branch, temporarily point the node at a revoked credential (or a wrong installation ID) and execute once — the notification should fire, and nothing downstream should run.

## Step 4 - Audit every other workflow for the same combination

This bug is a configuration pattern, not a one-off. Any HTTP Request node in your instance with "Never Error" on and a short-lived-token credential is a workflow that will go quiet for an hour and then 401 forever. Audit from the exported JSON instead of clicking through workflows one by one:

```bash
# Export all workflows and find every HTTP Request node with "Never Error" on
n8n export:workflow --all --output=/tmp/workflows/

grep -rl '"neverError": true' /tmp/workflows/ | while read f; do
  echo "=== $f ==="
  grep -o '"name": "[^"]*"' "$f" | head -3
done
```

Each match is a workflow to apply Step 2 to. While you are there, check the credential each one uses: if it is a GitHub App API credential, or any credential whose token lifetime is an hour or less, it is in the danger zone. OAuth2 credentials can stay as they are — their refresh path already handles resolved 401s.

Also check nodes that call `httpRequestWithAuthentication` with `ignoreHttpStatusErrors` (the same gap, per the reporter) — if you use community or custom nodes that swallow HTTP errors, treat them as suspect until the follow-up fix lands.

## Step 5 - Verify the fix survives a token expiry

The honest verification takes just over an hour, because that is the GitHub App token's lifetime. It is worth doing once, on one workflow, so you trust the fix everywhere else:

1. Apply Step 2 to a scheduled workflow that calls the GitHub API.
2. Run it once manually and confirm a `200`.
3. Wait at least 61 minutes — past the installation token's one-hour expiry — and let the next scheduled run fire (or run it manually).
4. Confirm the execution returns a `200` with real data, not a 401.

Before the fix, that run would have returned `statusCode: 401` as data. After the fix, the 401 throws internally, the token refreshes, the request is resent once, and the workflow sees the successful response. If you want a faster check, the Step 1 manual test (toggle "Never Error" off, execute, watch it succeed) already proves the refresh path works — the 61-minute test proves it works *unattended*, which is the case that actually matters for scheduled workflows.

## Prevent it next time

- **Default to node-level error handling, not "Never Error", on any node that uses a short-lived-token credential.** "Never Error" is fine for APIs with static keys that never expire. The moment a credential mints tokens, the node-level setting is the correct tool.
- **Keep a short list of your expiring-token credentials.** GitHub App installation tokens last one hour. Any credential you add that fetches tokens in `preAuthentication` belongs on that list, and every HTTP Request node using one gets the Step 2 treatment on the day it is built — not after the first silent 401.
- **Watch for the upstream fix.** The reporter has a tested change following the `requestOAuth2` pattern — a resolved 401 under `simple: false` refreshes the credential and resends the request once — proposed as [PR #43834](https://github.com/n8n-io/n8n/pull/43834), with 7 new tests that fail without the change. As of November 14, 2026 it is not yet in a release, and it does not cover the `httpRequestWithAuthentication` / `ignoreHttpStatusErrors` variant (a follow-up is planned). When a release note mentions GHC-9757 or #43839, you can re-test with "Never Error" on — but the node-level setting from Step 2 remains the safer default even then.
- **Alert on 401s, don't just handle them.** The IF-node guard from Step 3 is the difference between "the workflow handled it" and "nobody knew for a week." A 401 that keeps recurring after the fix means the credential itself is dying, and that is a message you want the same day.

## FAQ

### Does this affect OAuth2 credentials?

No. The OAuth2 path (`requestOAuth2`) already converts a resolved 401 under `simple: false` into its token-refresh path. Only credentials that fetch short-lived tokens in `preAuthentication` — the GitHub App API credential is the confirmed example — hit this bug.

### Does this affect nodes other than HTTP Request?

Possibly. The reporter read the code for `httpRequestWithAuthentication` — the helper other nodes use — and found the same shape: it refreshes only in its `catch`, so with `ignoreHttpStatusErrors` it should have the same gap. That variant is not covered by PR #43834. If you use a node that swallows HTTP errors while authenticating with a short-lived-token credential, treat it as suspect.

### Why did my workflow work for the first hour and then break?

The GitHub App installation token lives for one hour. The first run (or the run that created the credential) minted a fresh token. Every run inside that hour reused it. The first run after expiry got a 401 — and because "Never Error" was on, that 401 never threw, so the refresh never ran, and every later run inherited the same dead token.

### Can I just re-enter the credential or restart n8n instead?

You can, and it will work — once. Restarting or re-saving the credential mints a fresh token, so the next run succeeds. An hour later you are back to 401s. It is a manual workaround for a single run, not a fix. Apply Step 2 instead.

### Is "Never Error" itself broken?

No. It does exactly what it says: it returns error statuses as data instead of throwing. The bug is that the token-refresh mechanism lives exclusively in the error path, so anything that suppresses the error also suppresses the refresh. That is the oversight the n8n team acknowledged, and PR #43834 is the proposed correction.

## Key Takeaways

1. **"Never Error" disables more than the error — it disables the token refresh.** A 401 that resolves instead of throwing never reaches the `catch` block where `preAuthentication` tokens are refreshed.
2. **The team-confirmed fix is a settings swap:** turn "Never Error" off, set node Settings → On Error → Continue (using regular output). The 401 throws, the token refreshes, the request is retried, and the workflow keeps running.
3. **OAuth2 credentials are immune; short-lived-token credentials are not.** GitHub App installation tokens (one-hour lifetime) are the confirmed case.
4. **A 401 returned as data is a silent failure.** Add an IF-node guard after the request so a genuine auth failure alerts you instead of flowing downstream as garbage.
5. **Audit, don't patch one workflow.** Any HTTP Request node with "Never Error" on and an expiring-token credential is the same bug waiting for its hour to run out.

Next: run the export-and-grep audit from Step 4 across your instance today — it takes two minutes and tells you exactly how many workflows are one token expiry away from a silent 401. Then check the sibling failure mode in our guide to [fixing n8n's Google Sheets nodes hanging in n8n Cloud](/blog/fix-n8n-google-sheets-hang-cloud/), where a different "looks stuck, no error" trap has the same shape: the workflow looks alive while nothing is actually happening.

---

*Sources: [GitHub issue #43839](https://github.com/n8n-io/n8n/issues/43839) (bug report, reproduction steps, and team confirmation from grinem, November 13, 2026); [PR #43834](https://github.com/n8n-io/n8n/pull/43834) (proposed fix following the `requestOAuth2` pattern); n8n source paths `packages/core/src/execution-engine/node-execution-context/utils/request-helpers/authentication.ts`, `HttpRequestV3.node.ts`, and `request-helpers/oauth.ts` as cited in the issue. No license-verified in-article stock images were available for this topic, so none are included.*
