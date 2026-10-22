---
title: "Fix n8n Postgres Query Parameters Splitting on Commas (GH #40022 Guide)"
description: "n8n's Postgres node splits query parameter values on commas, turning 'Doe, John' into two bind values. Root cause in stringToArray plus 3 exact fixes."
date: 2026-10-22
category: automation
tags: ["n8n", "postgres", "error-fix", "troubleshooting", "database"]
draft: false
featured: false
image: "/og/fix-n8n-postgres-comma-query-parameter.webp"
---

Your webhook collects free-text form input — customer names, addresses, notes. The workflow runs fine for weeks, then one customer named `Doe, John` signs up and the Postgres node explodes with `ERROR: wrong number of parameters for prepared statement`. The data is fine. The query is fine. The node is splitting your single parameter value on its comma — and there is nothing wrong with your input.

**By the end of this article, you will have:** the exact root cause (a comma-split applied *after* expression evaluation in Postgres node v2.5+), three verified fixes including the one-line expression change that keeps every value as exactly one bind parameter, and a verification routine that proves the fix before it touches production.

## Prerequisites

- A self-hosted or cloud n8n instance (bug verified on n8n **2.41.3** and current master; the vulnerable code is byte-identical in both)
- A Postgres node on **typeVersion 2.5+** using the **Execute Query** operation with **Query Parameters** enabled
- The issue tracker reference: [n8n-io/n8n#40022](https://github.com/n8n-io/n8n/issues/40022)

**Terminology used in this article:**

- **Bind value:** a single `$1`, `$2` parameter PostgreSQL actually receives. Your query must supply exactly as many bind values as placeholders.
- **Query Parameters:** the n8n Postgres node field where you enter `={{ $json.name }}`, `={{ $json.note }}` — one expression per bind value.
- **stringToArray:** the n8n helper (`helpers/utils.ts`) that comma-splits a string: `.split(',')` plus trimming and empty filtering.

## Step 1 - Confirm the symptom: "Expected 2 parameters but got 3"

Run your Postgres node with **Execute Query** and **Query Parameters** on:

```sql
SELECT $1::text AS a, $2::text AS b
```

Feed it an item whose first field contains a comma:

```json
{ "name": "Doe, John", "note": "hello" }
```

The node fails with:

```
ERROR: wrong number of parameters for prepared statement "two"
DETAIL: Expected 2 parameters but got 3.
```

Three giveaways that this is the comma bug and not something else:

1. **The error only fires on data-dependent input.** Rows without commas execute fine — which is why this survives testing and blows up on real form data.
2. **The count always overshoots.** You supplied 2 expressions but the node bound 3 values, because `"Doe, John"` was split into `"Doe"` and `"John"`.
3. **The error blames the count, not the comma.** Nothing in the message mentions the comma in your data, so the instinct is to recount your placeholders — which wastes an hour.

The Postgres driver rejects the surplus value outright; it does not drop it, shift the bindings, or write wrong data. So it is always a hard error — never silent corruption (the issue reporter initially feared silent corruption, then corrected it after verifying the binding against a real database).

## Step 2 - Understand the root cause: the split happens after evaluation

The bug lives in `packages/nodes-base/nodes/Postgres/v2/actions/database/executeQuery.operation.ts`, inside the `nodeVersion >= 2.5` branch:

```ts
const evaluatedExpression = evaluateExpression(rawEvaluated);
const evaluatedValues = isJSON(evaluatedExpression)
    ? [evaluatedExpression]
    : stringToArray(evaluatedExpression);
if (evaluatedValues.length) values.push(...evaluatedValues);
```

And `stringToArray` in `helpers/utils.ts`:

```ts
export function stringToArray(str: NodeParameterValueType | undefined) {
    if (str === undefined) return [];
    return String(str)
        .split(',')
        .filter((entry) => entry)
        .map((entry) => entry.trim());
}
```

The crucial detail: `evaluateExpression` returns **plain strings** (via `toString()` — it only JSON-encodes objects). So `isJSON()` saves you only when your *data itself* happens to parse as JSON:

| Evaluated value | `isJSON` | Bind values produced | Correct? |
|---|---|---|---|
| `123` | true | 1 | yes |
| `true` | true | 1 | yes |
| `Doe, John` | **false** | **2** | **no** |
| `hello, world, again` | **false** | **3** | **no** |

Casual testing passes because numeric or boolean-looking values behave correctly while ordinary free text does not. It is data-dependent — the worst shape for a bug in a form/webhook ingestion path.

The older branch (`nodeVersion < 2.5`) splits the **raw** parameter string *before* evaluation, then pushes each evaluated result whole — so commas inside your data are safe there. The hazard exists only in the newer branch, where the split is applied *after* evaluation. A related fix ([PR #31704](https://github.com/n8n-io/n8n/pull/31704), merged 2026-06-04) already made the node spread real arrays correctly; the comma-in-string case is the remaining half of the same problem.

<figure class="shot">
  <img src="/figures/fix-n8n-postgres-comma-query-parameter-tokenizer.svg" alt="Isometric tokenizer press machine: parameter value slugs ride a conveyor toward a splitting blade; the bare slug 'Doe, John' is guillotined at its comma into two tokens while a sleeved slug passes through whole, and a counter dial reads 3 tokens against 2 placeholder slots with a reject flag raised" loading="lazy" />
  <figcaption><strong>Fig 1 — The comma splitter press.</strong> One parameter slug enters the blade housing; on node v2.5+ the comma split fires on the evaluated string, so <code>Doe, John</code> becomes two tokens and the counter reads 3 against 2 placeholder slots. Notice the sleeved slug passing through whole — that sleeve is the true-JS-array fix from Step 3.</figcaption>
</figure>

## Step 3 - Apply the fix (3 verified options)

### Fix A — Pass Query Parameters as a true JS array (recommended, verified by the n8n team)

Instead of entering each parameter on its own line as a string expression, send **one** expression that evaluates to a real JavaScript array. Because PR #31704 made the node spread arrays into individual bind values, commas inside the values are never touched:

```
={{ [$json.name, $json.note] }}
```

This works for any number of parameters:

```
={{ [$json.name, $json.note, $json.city, $json.phone] }}
```

The rule: `{{ $json.name }}` evaluates to the string `"Doe, John"` (which the node then splits), while `{{ [$json.name] }}` evaluates to the array `["Doe, John"]` (which the node binds whole — commas intact). This is the workaround the n8n team themselves verified: *"If you simply send a valid JS array in the 'Query Parameters' field (instead of a string), n8n wouldn't try to split each parameter on the comma and instead use the raw values."* — [community.n8n.io/t/27955/6](https://community.n8n.io/t/postgres-node-errors-inserting-data-using-execute-query-as-well-as-using-upsert/27955/6). The same trick was independently confirmed on MySQL and Postgres nodes by multiple community users across 2023–2025.

### Fix B — Downgrade the Postgres node to typeVersion 2.4

Open the node settings (gear icon) → **Node version** → select **2.4**. The pre-2.5 branch splits the raw string before evaluation and pushes each evaluated result whole, so commas in your data are safe. The issue's own verification table marks the legacy branch **SAFE** for the exact reproduction case.

Trade-offs: 2.4 predates some newer node features and you miss future Execute Query improvements. Use this when you cannot change the Query Parameters format (e.g. a shared template), and plan to move to Fix A once the upstream fix lands.

### Fix C — Restructure to avoid the split path entirely

If neither A nor B fits, sanitize at the source with a Code node that returns the array Fix A needs:

```js
return [{
  json: {
    params: [ $input.first().json.name, $input.first().json.note ]
  }
}];
```

Then set Query Parameters to `={{ $json.params }}` — one array, zero splits. This is the same shape as Fix A; the Code node just makes it reusable across many Postgres nodes.

## Step 4 - Verify the fix worked

Run the node in **Execute once** with the reproduction data (`name: "Doe, John"`, `note: "hello"`). Success means all three of these:

1. **The node returns a row with the comma intact.** Query `SELECT $1::text AS a, $2::text AS b` and check the output item: `a` must equal `Doe, John` exactly — not `Doe`.
2. **No parameter-count error.** The `Expected N but got M` error must be gone.
3. **Spot-check the database.** For writes, query the table directly and confirm the stored value keeps its comma: `SELECT * FROM your_table WHERE id = ...`.

For a permanent guard, add a cheap canary to your ingestion path: a Code node right after the Postgres node that asserts on the expected shape (e.g. `items[0].json.a.includes(',')` when your fixture row contains a comma). If a future n8n update regresses this, the canary fails loudly instead of the data path failing silently at 2 AM.

## Step 5 - Prevent it next time

- **Adopt the true-array convention everywhere.** From now on, always write Query Parameters as `={{ [$json.a, $json.b] }}` in your team templates — it is immune to the split on every node version, and reads clearly.
- **Keep fixtures with commas.** Add rows like `name: "Doe, John"` to your pinned test data. This bug is data-dependent; your test data must include the adversarial cases.
- **Watch the upstream issue.** n8n-io/n8n#40022 proposes the real fix: never split a value that came from an expression (only literal text keeps `stringToArray`). Subscribe to it; once merged, you can revert Fix B downgrades.
- **Prefer column-mapping operations where possible.** For plain INSERT/UPSERT, the Postgres node's Insert/Upsert operations bind fields directly and never hit this code path — reserve Execute Query for genuinely custom SQL.

## FAQ

### Does this affect the MySQL or other database nodes too?

Yes — the same `stringToArray` pattern exists across several database nodes. Community threads confirm comma-splitting on the MySQL node (v2.4) with the same symptom: text before the comma gets bound, the rest vanishes into extra parameters. The true-JS-array fix (Fix A) was first confirmed on MySQL and works the same way there.

### Why not just wrap values in quotes, like `'{{ $json.field2 }}'`?

The quotes become part of the input string — the node does not strip them. Your database then stores `'Doe, John'` with literal quote characters. Do not do this.

### Is this the same as the older "array wrapped as single bind value" bug?

Related but distinct. Issue #30978 was about a JS array being wrapped as *one* bind value (fixed by PR #31704, which made arrays spread). Issue #40022 is the remaining half: a *string* containing a comma being split into *several* bind values. Both come from the node not reliably distinguishing "one string value" from "a comma-separated list of values".

### Which n8n versions are affected?

Any n8n version whose Postgres node runs typeVersion **2.5 or newer** — verified on 2.41.3 and current master with byte-identical code. Node v2.4 and older use the legacy branch, which is safe.

## Conclusion

The Postgres node on v2.5+ comma-splits your evaluated query parameters, so `Doe, John` becomes two bind values and the query dies with a misleading count error. The verified fix: pass Query Parameters as a true JS array — `={{ [$json.name, $json.note] }}` — so every value binds whole, commas intact. If you cannot change the expression format, downgrade the node to 2.4 and watch [n8n-io/n8n#40022](https://github.com/n8n-io/n8n/issues/40022) for the upstream fix. Keep comma-bearing fixtures in your test data, because this bug only shows up when real-world text arrives.

*Images: none — no license-verified stock images were available for this topic, so none were used rather than an unrelated one.*
