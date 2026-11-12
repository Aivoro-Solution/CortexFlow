---
title: "Fix n8n Firestore Node Saving Tiny Decimals as Integers (Silent Data Corruption, GH #40249)"
description: "n8n's Firestore node writes 0.0000001 as integerValue instead of doubleValue — silent corruption, no error. One toString() check is the cause; here is the fix."
date: 2026-11-12
category: automation
tags: ["n8n", "firestore", "google-cloud", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-firestore-small-decimals-integer-value.webp"
---

You sync sensor readings into Firestore with n8n, and everything looks fine. The execution reports success. The document exists. But the value `0.0000001` did not arrive as a decimal — the Firestore node sent it as `{"integerValue": 1e-7}`, which is not a valid integer at all. There is no error, no failed execution, nothing in the logs. Your data is quietly wrong, and the only way you find out is when a downstream app reads the field and gets something it cannot use.

This is a real bug, reported in [GitHub issue #40249](https://github.com/n8n-io/n8n/issues/40249) (October 5, 2026, still open as of November 12, 2026). The reporter verified the outgoing request bodies with a mocked transport and traced the defect to a single line in the node's source. It affects the Google Cloud Firestore node (version 1.1) in both **Create** and **Create or Update** (upsert) operations. By the end of this article you will know exactly which values are affected, how to catch them before they reach Firestore, and three fixes that work today — no upstream patch required.

Quick definitions before we start: **Firestore** is Google Cloud's NoSQL document database. Every value it stores carries an explicit type — `integerValue`, `doubleValue`, `stringValue`, and so on — defined by the [Firestore Value contract](https://cloud.google.com/firestore/docs/reference/rest/v1/Value). **n8n's Firestore node** converts your workflow's JSON into that typed format with an internal function called `jsonToDocument()`. A **scientific-notation number** is how JavaScript prints very small or very large numbers: `0.0000001` becomes `1e-7`. That formatting quirk is the whole bug.

## The symptom: success on screen, wrong type in the database

Feed the Firestore node one input item:

```json
{ "id": "fixture", "value": 0.0000001 }
```

Use Resource **Document**, Operation **Create**, Columns `value`. The execution succeeds. But the request body the node actually sends is:

```json
{ "fields": { "value": { "integerValue": 1e-7 } } }
```

It should be `{"doubleValue": 1e-7}`. The same wrong type appears in the upsert path, at `writes[0].update.fields.value`. The value `-0.0000001` is misclassified the same way.

The treacherous part is the silence. The Firestore node reports success, the workflow moves on, and your error workflow never fires — because nothing failed from n8n's point of view. This is the same failure class as the [SplitInBatches loop that ends early with status "success"](/blog/fix-n8n-splitinbatches-loop-ends-early/) and the [Data Table lookup that throws "Multiple matches found" only in production](/blog/fix-n8n-data-table-multiple-matches-found/): the execution status tells you nothing about whether the data is right.

> **Note:** the reporter verified the outgoing request bodies, not a live server response — so what Firestore's server does with `{"integerValue": 1e-7}` (reject it, or store it wrong) is not part of the report. What is certain is that the request violates the Value contract: `integerValue` must be an integer, and `1e-7` is not one. Either outcome is bad — a rejected write you never notice, or a stored value your app cannot trust. Do not wait for an error to tell you this happened; check the type, as Step 1 shows.

## The root cause: one toString() check decides integer vs double

The node's `jsonToDocument()` function decides the Firestore type by string inspection. Simplified, the logic is:

```js
if (value.toString().indexOf('.') === -1) {
  // no decimal point → treat as integer
  return { integerValue: value };
}
return { doubleValue: value };
```

That works for ordinary numbers: `(42).toString()` is `"42"` (no dot, integer — correct), and `(0.5).toString()` is `"0.5"` (dot, double — correct). It breaks for small fractions because JavaScript switches to scientific notation for numbers with an absolute value below `1e-6`:

| Input | `toString()` | Has a dot? | Sent as | Correct type |
|---|---|---|---|---|
| `1e-7` (0.0000001) | `"1e-7"` | No | `integerValue` | `doubleValue` |
| `-1e-7` | `"-1e-7"` | No | `integerValue` | `doubleValue` |
| `1e-8` | `"1e-8"` | No | `integerValue` | `doubleValue` |
| `1.25e-7` | `"1.25e-7"` | Yes | `doubleValue` | `doubleValue` |
| `1e-6` (0.000001) | `"0.000001"` | Yes | `doubleValue` | `doubleValue` |
| `0.5` | `"0.5"` | Yes | `doubleValue` | `doubleValue` |
| `42`, `0` | `"42"`, `"0"` | No | `integerValue` | `integerValue` |

The pattern is narrow and that is what makes it dangerous: **only fractional numbers below `1e-6` whose mantissa is a single digit are affected** — `1e-7`, `2e-7`, … `9e-7`, `1e-8`, and so on. `1.25e-7` escapes because its mantissa carries a decimal point, and `0.000001` escapes because JavaScript still prints it in decimal form. So a sensor stream or a currency conversion that occasionally produces a tiny single-digit value corrupts exactly the rows you least expect, while 99% of your data looks perfect.

The correct check, which the reporter proposed, is `Number.isInteger(value)` — a value is an integer if and only if it has no fractional part, regardless of how `toString()` formats it. The reporter offered a focused community PR with regression coverage for the Create and Upsert request bodies, pending explicit team approval. As of November 12, 2026, no fixed n8n version exists yet.

## Step 1 - Confirm you are affected (two minutes)

Before changing anything, check whether your data actually contains an affected value. Add a **Code node** immediately before your Firestore node and run it in the editor with real input data:

```js
const affected = $input.all().filter((item) => {
  const v = item.json.value;
  return typeof v === 'number' && !Number.isInteger(v) && !String(v).includes('.');
});

if (affected.length > 0) {
  throw new Error(
    `Firestore type bug: ${affected.length} fractional value(s) would be sent as integerValue — e.g. ${affected[0].json.value}. ` +
    `Route them through the HTTP Request fix in Step 3.`
  );
}

return $input.all();
```

The guard catches exactly the affected set: a number, not an integer, whose string form has no decimal point. If it throws, you have the bug in your live data. If it passes, your current values are safe — but keep the guard in place, because the next batch of sensor data can produce a `1e-7` at any time.

To check data already written, read a suspect document back through the Firestore REST API (or the Firestore console's raw view) and look at the field's type key: `doubleValue` means correct, `integerValue` on a fractional number means it was corrupted on the way in. The Firestore console's table view will not show you this — you need the raw typed response.

> **Warning:** do not "fix" this by rounding tiny values to zero or by adding a small epsilon to force a decimal point (turning `1e-7` into `0.00000010000000001` just to get a dot in the string). Both change the data. The fixes below preserve the exact value.

## Step 2 - Decide which fix fits your workflow

| Fix | When to use it | What changes |
|---|---|---|
| **A. HTTP Request node with explicit `doubleValue`** | You must keep the exact decimal in Firestore | One node swap; the value arrives with the right type |
| **B. Scale and store** | You control the schema and read the value back yourself | Values stored as integers with a scale field; readers divide back |
| **C. Store as a string** | The value is an identifier, a measurement for display, or read by code you control | Type preserved as text; readers parse it back to a number |

Fix A is the only one that stores the value as a real Firestore double. Use it unless you have a specific reason to change the schema. Fixes B and C are pragmatic fallbacks for bulk pipelines where swapping nodes is expensive.

## Step 3 - Fix A: call the Firestore REST API with an explicit doubleValue

Replace the Firestore node with an **HTTP Request node** that calls the Firestore REST API directly, so *you* choose the type instead of `jsonToDocument()`.

**For Create** — a new document in a collection:

- Method: `POST`
- URL: `https://firestore.googleapis.com/v1/projects/<project-id>/databases/(default)/documents/<collection>`
- Authentication: Predefined Credential Type → **Google Cloud Firestore OAuth2 API**, and select the same credential your Firestore node already uses. No new OAuth setup is needed.
- Send Body: `Using JSON`, with this body (replace the placeholders):

```json
{
  "fields": {
    "value": { "doubleValue": "0.0000001" }
  }
}
```

Two details matter here. First, `doubleValue` is written as a **string** (`"0.0000001"`, not `0.0000001`) — that is how Firestore's REST API encodes 64-bit doubles in JSON, per Google's standard JSON mapping for floating-point values. Second, build the value from your input with an expression so it stays dynamic:

```json
{
  "fields": {
    "value": { "doubleValue": "{{ String($json.value) }}" }
  }
}
```

`String(0.0000001)` is `"1e-7"`, and Firestore accepts that as a double — the string form is exact, so no precision is lost in the conversion.

**For Create or Update (upsert)** — the same document, created if missing:

- Method: `PATCH`
- URL: `https://firestore.googleapis.com/v1/projects/<project-id>/databases/(default)/documents/<collection>/{{ $json.id }}?updateMask.fieldPaths=value`
- Authentication and body: same as above. A PATCH against Firestore creates the document when it does not exist, so it behaves like the node's Create or Update operation for a single field. Add more field paths to `updateMask.fieldPaths` (comma-separated) for each extra field in the body.

You should see a `200` response whose body echoes your field back as `{"doubleValue": "1e-7"}`. That echo is the verification — the server is telling you the stored type.

## Step 4 - Fix B: scale the value and store an integer (schema you control)

If your pipeline writes thousands of rows and you would rather not swap nodes, change what you store: multiply the tiny decimal into integer range before the Firestore node, and record the scale alongside it.

In a **Code node** before the Firestore node:

```js
return $input.all().map((item) => {
  const v = item.json.value;
  if (typeof v === 'number' && !Number.isInteger(v) && !String(v).includes('.')) {
    item.json.value_scaled = Math.round(v * 1e7); // 0.0000001 → 1
    item.json.value_scale = 10000000;
  }
  return item;
});
```

Then map the Firestore node's Columns to `value_scaled` and `value_scale` instead of `value`. Readers divide `value_scaled / value_scale` to recover the exact decimal. This works because integers are never misclassified — the bug only touches fractional numbers. Pick the scale factor from your data's smallest magnitude: `1e7` covers values down to `1e-7`; if you can see `1e-9`, use `1e9` (still safely inside JavaScript's integer range).

The trade-off is real: every reader of this collection must know about the scale field, and Firestore queries or ordering on the raw field will not behave like ordering on the decimal. Use Fix A if any reader you do not control touches this collection.

## Step 5 - Fix C: store the value as a string (when the type does not matter)

When the value is only ever read back by your own code — a sensor reading displayed in a dashboard, a rate stored for reference — the simplest escape is to stop sending a number at all. In a **Set node** before the Firestore node, set the field to the expression `{{ String($json.value) }}`. The current node code stores strings as `stringValue`, so `"0.0000001"` arrives intact and no type inference runs on it. Parse it back with `parseFloat()` at read time.

Do not use this for values you query with Firestore range filters or order by — string ordering (`"0.0000001"` vs `"0.0000002"`) is lexicographic, not numeric, and range queries will return wrong results.

## Step 6 - Verify the fix worked

Run the workflow once with the known-bad value `0.0000001`, then read the document back through the REST API:

```bash
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://firestore.googleapis.com/v1/projects/<project-id>/databases/(default)/documents/<collection>/fixture"
```

You should see:

```json
{ "fields": { "value": { "doubleValue": "1e-7" } } }
```

If the response still shows `integerValue`, the write went through the old Firestore node — check that the node was actually replaced and that no second Firestore node in the workflow still writes the same field. If it shows `doubleValue`, the fix is confirmed end to end: the value left n8n correctly *and* Firestore stored it with the right type.

## Prevent it next time

- **Keep the Step 1 guard node in front of every Firestore node that handles decimals.** It costs one node and it turns a silent corruption into a loud, failed execution — which your error workflow can actually alert on.
- **Add `0.0000001` to your workflow's test data.** It is the smallest, most ordinary-looking value that triggers the bug, and it belongs in every Firestore workflow's test fixtures alongside `0.5` and `42`.
- **Watch [issue #40249](https://github.com/n8n-io/n8n/issues/40249) for the upstream fix.** When a release lands with the `Number.isInteger` correction in `jsonToDocument()`, you can swap the HTTP Request node back to the Firestore node — but leave the guard in place for a few releases, in case the fix does not cover the upsert path.
- **Audit the siblings.** The same `toString().indexOf('.')` pattern is a trap anywhere a node infers a type from a formatted number. If another Google node in your stack writes numeric fields, test it with `1e-7` before you trust it.

## What this fix does not do

The workarounds above fix *your* writes; they do not fix the node. Data already written with the wrong type stays wrong until you rewrite those documents — re-run the affected rows through Fix A after deploying it. And the guard only protects values that pass through a node you added it to: a Firestore node in a different workflow with the same tiny-decimal data has the same bug, so audit every Firestore node, not just the one that bit you.

## FAQ

### Which values are affected, exactly?

Fractional numbers with an absolute value below `1e-6` whose mantissa is a single digit: `1e-7`, `2e-7`, … `9e-7`, `1e-8`, `-1e-7`, and so on. `1.25e-7` is safe (its mantissa has a decimal point), `0.000001` is safe (JavaScript still prints it as `0.000001`), and all integers are safe.

### Why doesn't n8n just check Number.isInteger()?

That is exactly the fix the reporter proposed, and they offered a community PR with regression tests for both Create and Upsert. The PR is waiting on explicit team approval, and as of November 12, 2026, no fixed version has shipped. Until it does, the HTTP Request workaround is the reliable path.

### Is this the same as the "phone number stored as a number" Firestore complaint?

No, that is a different type-inference quirk (numeric strings being coerced), discussed in an older community thread. This bug is narrower and worse: a value that is unambiguously a number in your workflow arrives in Firestore with the wrong *numeric* type, and the request body itself is invalid under the Firestore Value contract.

### Does this affect n8n Cloud too?

Yes — the bug is in the node's `jsonToDocument()` conversion, which runs identically on Cloud and self-hosted. Cloud users apply the same fixes; the only difference is that Cloud instances receive the upstream fix automatically once it ships.

### My values are currency amounts like 19.99 — am I affected?

No. `19.99` formats as `"19.99"`, which contains a decimal point, so it is correctly sent as `doubleValue`. The bug only bites below `1e-6`. That said, storing money as a double is its own problem — for currency, store integer cents (Fix B's pattern) regardless of this bug.

## Key Takeaways

1. **n8n's Firestore node sends `0.0000001` as `integerValue`, not `doubleValue`** — `jsonToDocument()` checks for a decimal point in `toString()`, and `(1e-7).toString()` is `"1e-7"`, which has none.
2. **Only single-digit-mantissa fractions below `1e-6` are affected** — `1e-7` breaks, `1.25e-7` and `0.000001` do not, which is why the corruption is easy to miss.
3. **The execution reports success** — this is silent data corruption, so add the Code-node guard (`!Number.isInteger(v) && !String(v).includes('.')`) to turn it into a loud failure.
4. **The reliable fix today is the Firestore REST API via the HTTP Request node** — send `{"doubleValue": "0.0000001"}` explicitly (string-encoded, per Google's JSON mapping) for Create, and PATCH with `updateMask.fieldPaths` for upsert.
5. **No upstream fix has shipped yet** — issue #40249 is open as of November 12, 2026, with a community PR offered; verify with a read-back (`doubleValue` in the response) and re-write any rows corrupted before the fix.

Next: if silent-success bugs are a pattern in your instance, read [Fix n8n SplitInBatches Loop Ending Early — Execution Reports "Success" but Items Are Missing](/blog/fix-n8n-splitinbatches-loop-ends-early/) — it covers the same failure class from the loop side, including the guard-node pattern that catches all of them.
