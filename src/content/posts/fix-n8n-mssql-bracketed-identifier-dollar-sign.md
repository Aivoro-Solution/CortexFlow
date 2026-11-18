---
title: "Fix n8n Microsoft SQL Node Treating $123 in a Bracketed Table Name as a Missing Query Parameter (GH #44362)"
description: "n8n v3 rejects bracketed table names like [Company$Table 1$123-456-789] with '$123, but only 0 query parameter(s) are set'. Here's the one-line fix."
date: 2026-11-18
category: automation
tags: ["n8n", "microsoft-sql", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-mssql-bracketed-identifier-dollar-sign.webp"
---

You upgrade n8n to v3 and a workflow that has run for months suddenly fails. The query is unchanged, the credentials are unchanged, and the error makes no sense: `The query references $123, but only 0 query parameter(s) are set`. You set no query parameters — because the query has none. The `$123` it complains about is part of a table name.

This is a confirmed bug in n8n, filed as [GitHub issue #44362](https://github.com/n8n-io/n8n/issues/44362) on November 18, 2026 (team-assigned, Linear GHC-9807, still open as of November 18, 2026). The Microsoft SQL node's v3 placeholder check reads `$` followed by digits inside a **bracketed identifier** as a query parameter reference, even though the text is part of the table name. By the end of this article you will know how to confirm you have hit this exact bug, fix it with a one-line query change, and verify the query runs again.

Quick definitions before we start: a **bracketed identifier** is a SQL Server table or column name wrapped in square brackets, like `[Company$Table 1$123-456-789]` — brackets let a name contain spaces, hyphens, and special characters that would otherwise be invalid. A **query parameter placeholder** in the Microsoft SQL node is `$N` (for example `$1`, `$2`), a marker in the query text that the node replaces with a value from the Query Parameters list before sending the query to the server. **QUOTED_IDENTIFIER** is a SQL Server setting that controls whether double-quoted text like `"My Table"` is treated as an identifier (on) or as a string literal (off). **Microsoft Dynamics NAV / Business Central** is Microsoft's ERP system, whose databases use table names in exactly this shape — `Company$Table 1$123-456-789` — so this bug hits real production databases, not contrived examples.

## The symptom: a table name is mistaken for a missing parameter

The failure needs one ingredient: a query that mentions a bracketed identifier containing `$` followed by digits. The reporter's query was:

```sql
SELECT TOP 1 * FROM [Company$Table 1$123-456-789]
```

Run it in a Microsoft SQL node, operation **Execute Query**, with no Query Parameters set, and the node fails before the query ever reaches the server:

```
The query references $123, but only 0 query parameter(s) are set
```

Note the wording: the query never reaches SQL Server. The node runs a placeholder check first — it scans the query text for anything shaped like `$` followed by digits, and throws if there is no matching entry in the Query Parameters list. The check is new in v3, which is why the same workflow ran fine before the upgrade.

**How to tell this bug apart from a genuinely missing parameter.** If your query really does use a `$1` placeholder and you forgot to add the parameter, the error is correct and the fix is to add it. Here the `$123` sits inside square brackets, as part of a table name, and the query has no placeholders at all. That pattern — a `$` plus digits inside `[...]` with an empty Query Parameters list — is the fingerprint. If the `$` plus digits in your query sits outside any brackets or quotes, you have a different problem: a real unbound placeholder.

## The root cause: the placeholder check does not understand brackets

The reporter traced the bug to the source on master, in `packages/nodes-base/nodes/Microsoft/Sql/GenericFunctions.ts`. The `bindQueryParameters` function runs an unbound-placeholder check before every query. It already knows that `$N` inside single quotes (`'...'`) or double quotes (`"..."`) is not a parameter — it skips those matches with an `isInsideQuotes` helper. What it does not know is that SQL Server bracketed identifiers (`[...]`) are the same kind of delimited text. So `$123` inside `[Company$Table 1$123-456-789]` is read as a reference to a parameter named `$123`, and with zero parameters set, the node throws.

The inconsistency is what makes this a bug rather than a design choice: the check already treats quoted strings as non-parameters, and bracketed identifiers are SQL Server's other delimited-identifier form — [Microsoft's own documentation](https://learn.microsoft.com/en-us/sql/relational-databases/databases/database-identifiers) lists brackets and double quotes side by side as the two ways to write a delimited identifier. The reporter opened [PR #44132](https://github.com/n8n-io/n8n/pull/44132) with the fix — treat bracketed identifiers like quoted text in the placeholder check, with tests — but as of November 18, 2026 it is still open and not merged, so no released version contains the fix yet. Until one does, the workaround below is the way through.

## Step 1 - Confirm you have this exact bug

Before changing the query, run the minimal reproduction so you are not chasing a different SQL error (connection, permission, and syntax errors all look similar at a glance in n8n).

1. Add a Microsoft SQL node, operation **Execute Query**, with no Query Parameters.
2. Set the query to `SELECT TOP 1 * FROM [Company$Table 1$123-456-789]` — or your own table name, as long as it is bracketed and contains `$` followed by digits.
3. Execute the node. If it fails with `The query references $123, but only 0 query parameter(s) are set` (the number after `$` will match the digits in your table name), you have this bug.

If instead the error mentions a login failure, a network timeout, or an invalid object name, you have a different problem — check the credential, the server address, and that the table actually exists under that name first.

## Step 2 - Fix it: quote the identifier with double quotes instead of brackets (recommended)

This is the workaround the reporter verified: write the identifier with double quotes instead of brackets.

```sql
SELECT TOP 1 * FROM "Company$Table 1$123-456-789"
```

That is the whole fix. The placeholder check already skips `$N` inside double quotes, so the node stops seeing a phantom parameter, and SQL Server treats the double-quoted name as the same identifier as the bracketed one.

Why this works: SQL Server accepts two forms of delimited identifier — brackets and double quotes — and they are interchangeable for a name like this one. The double-quoted form is already on the check's skip list, so nothing else in the node needs to change. If the table is schema-qualified, quote each part separately:

```sql
SELECT TOP 1 * FROM dbo."Company$Table 1$123-456-789"
```

> **Note:** double-quoted identifiers only work when `SET QUOTED_IDENTIFIER` is `ON`. That is the default for the driver the n8n node uses, and for almost every SQL Server connection — but if your workflow or server explicitly sets `QUOTED_IDENTIFIER OFF`, double-quoted text is treated as a string literal instead of a name, and the query will fail with a syntax error. If you hit that, re-enable it for the session with `SET QUOTED_IDENTIFIER ON` before the query, or use the alternative in Step 3.

Apply the same swap everywhere the name appears — `JOIN`s, `WHERE` clauses, column references — not just the `FROM`. Any bracketed identifier in the query that contains `$` plus digits will trip the same check.

## Step 3 - Verify the query runs, and check for real placeholders

Re-run the node with the double-quoted query. You should see a successful execution with one row (or the rows your query returns) — and, importantly, the execution should reach SQL Server this time. If the workflow's SQL is generated by an AI node, check the generated text too: the same `$` plus digits pattern can appear in other bracketed names the model emits, and each one needs the same swap.

While you are here, do one sanity check in the other direction. If your query genuinely uses `$1`, `$2`, or similar placeholders, they must still be listed in the node's Query Parameters — the check is real, and a placeholder outside brackets or quotes with no matching parameter will (correctly) throw the same error. The workaround changes how identifiers are written; it does not disable the check.

## What does not fix it

Two things are worth ruling out so you do not waste a debugging cycle on them. First, adding a Query Parameter named `$123` (or a dummy parameter) is the wrong fix: the node would then bind a value where the table name should be, and the query would fail on the server side instead. Second, renaming the table is not a realistic option for a Dynamics NAV / Business Central database — the `$` names are the system's own naming scheme, and renaming breaks the ERP. The double-quote swap is the fix that keeps the database untouched.

One more community suggestion is worth mentioning with a caution: a forum reply suggested escaping the dollar sign as `$$123` inside the query. The reporter did not confirm that, and it is not part of the issue or the PR, so treat it as untested — try the double-quote form first, and only test `$$` escaping in a scratch workflow if double quotes are unavailable to you for some reason.

## Prevent it next time

- **Audit v3-upgraded workflows for `$` inside brackets.** Any Microsoft SQL node query that references a Dynamics NAV / Business Central table — or any table whose name contains `$` followed by digits — will hit this until the fix ships. Search your workflow JSON for `[$` as a quick sweep.
- **Watch PR #44132.** When it merges and lands in a release, bracketed identifiers will be skipped by the placeholder check and you can switch back to brackets if you prefer them. Until then, keep the double-quoted form.
- **Pin your n8n version after an upgrade.** This bug arrived with the v3 upgrade, and it broke workflows that had run for months. Test upgraded nodes against a copy of each production workflow before pointing the live ones at the new version.

## FAQ

### Does this affect other database nodes?

No. This is specific to the Microsoft SQL node's `bindQueryParameters` placeholder check. Other database nodes have their own parameter handling, and the Postgres node, for example, uses a different placeholder style. If you see a similar `$N` error on another node, it is a different bug with a different cause.

### Can I just turn the placeholder check off?

There is no setting for that. The check runs before every query in the Microsoft SQL node on v3. The double-quote workaround is the supported path until PR #44132 ships.

### My table name has a `$` but no digits after it — am I affected?

No. The check looks for `$` followed by digits (`$123`, `$1`). A `$` on its own, or `$` followed by letters, does not match the pattern and will not throw.

### What if my identifier also contains a double quote?

Escape it by doubling it — `"My ""Quoted"" Table"` — which is SQL Server's rule for a double quote inside a double-quoted identifier. Bracketed identifiers escape a `]` the same way, by doubling it (`]]`).

## Key Takeaways

1. **The v3 Microsoft SQL node mistakes `$` plus digits inside `[...]` for a query parameter** — the placeholder check skips quoted strings but not bracketed identifiers (GH #44362).
2. **The fix is one character class away: write the identifier with double quotes** — `"Company$Table 1$123-456-789"` instead of `[Company$Table 1$123-456-789]` — and the check skips it.
3. **Double quotes need `QUOTED_IDENTIFIER ON`**, which is the default for the node's driver; if it is off in your session, turn it on or the quoted name becomes a string literal.
4. **Do not add a dummy `$123` parameter and do not rename the table** — the first breaks the query on the server, the second breaks the ERP that owns the name.
5. **PR #44132 fixes the check properly** (bracketed identifiers treated like quoted text), but it is not merged as of November 18, 2026 — keep the workaround until a release contains it.

Next: if you run Dynamics NAV / Business Central through n8n, sweep your other Microsoft SQL nodes for bracketed `$` names now — every one of them will fail the same way on v3, and the double-quote swap takes seconds per query.
