---
title: "Fix n8n HTTP Request Node Turning UTF-8 Accented Text into Garbled Chinese Characters (GB18030 Mojibake, GH #43713)"
description: "n8n's HTTP Request node re-decodes valid UTF-8 JSON as GB18030, turning 'Point d'étape' into 'Point d'茅tape'. One setting fixes it."
date: 2026-11-13
category: automation
tags: ["n8n", "http-request", "encoding", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-http-request-gb18030-mojibake.webp"
---

You call a perfectly normal API with n8n's HTTP Request node. The server answers `200`, the `Content-Type` header says `application/json; charset=utf-8`, and the body is valid UTF-8 French. The execution reports success. Then you open the output and find this:

```json
{"titre": "Point d'茅tape", "corps": "D茅cision : 芦聽茅largir聽禄 le p茅rim猫tre."}
```

The original text was `Point d'étape` and `Décision : « élargir » le périmètre.` — every accented character has been replaced with Chinese characters. This is **mojibake**: text decoded with the wrong character encoding. And the worst part is that nothing failed. The node did not throw, the workflow did not stop, and if the corrupted text flows into a database, a CRM, or an email, you find out from a customer, not from n8n.

This is a real bug, reported in [GitHub issue #43713](https://github.com/n8n-io/n8n/issues/43713) (November 12, 2026, team-assigned, Linear ticket GHC-9752, still open as of November 13, 2026). The reporter reproduced it on n8n 2.46.6, traced it to the exact file and function, and confirmed the workaround on their own instance. By the end of this article you will know exactly which responses trigger it, why it happens, and two fixes that work today — no upstream patch required.

Quick definitions before we start: **UTF-8** is the encoding used by over 98% of the web — it represents accented Latin letters like `é` as two bytes. **GB18030** is a Chinese character encoding; its byte pairs happen to overlap with UTF-8 byte pairs, so UTF-8 bytes can be "successfully" misread as Chinese characters. **Mojibake** is the garbled text that results when bytes are decoded with the wrong encoding. The **HTTP Request node** is n8n's general-purpose node for calling any API; its **Response Format** setting controls how it turns the raw response bytes into JSON, text, or binary data.

## The symptom: correct bytes in, Chinese characters out

The trigger is specific, and that specificity is what makes the bug hard to notice. Feed the HTTP Request node (typeVersion 3 or above) a JSON response like this, with the Response Format left on automatic detection:

```json
{"titre": "Point d'étape", "corps": "Décision : « élargir » le périmètre."}
```

The node returns:

```json
{"titre": "Point d'茅tape", "corps": "D茅cision : 芦聽茅largir聽禄 le p茅rim猫tre."}
```

Note what did *not* happen: no error, no replacement character (`�`), no empty output. The corruption is total — every accented character in every field is wrong, not just the passage that triggered it — and it looks like plausible text, so a quick glance at the output can miss it entirely. The reporter also found stored text with the same corruption pattern written as early as June 2026, which means older n8n releases are very likely affected too.

The treacherous part is the silence. This is the same failure class as the [Firestore node that silently sends tiny decimals as integers](/blog/fix-n8n-firestore-small-decimals-integer-value/) and the [SplitInBatches loop that ends early with status "success"](/blog/fix-n8n-splitinbatches-loop-ends-early/): the execution status tells you nothing about whether the data is right.

> **Note:** the corruption happens at decode time, inside the node — the source API is fine, and the bytes on the wire are correct UTF-8. That is good news for recovery: re-fetching the same endpoint with the fix below returns clean text. It also means the damage is limited to whatever your workflow already stored.

## The root cause: a heuristic that tests the wrong thing

The bug lives in `packages/nodes-base/nodes/HttpRequest/V3/utils/buffer-decoding.ts`, in a function called `binaryToStringWithEncodingDetection`. The reporter traced the failure to three steps in that function:

1. **A declared `charset=utf-8` is not treated as authoritative**, because it equals the function's `DEFAULT_ENCODING`. So even when the server explicitly says "this is UTF-8", the node proceeds to guess anyway.
2. **The body is decoded as UTF-8 — correctly — and then a pattern test runs on the decoded *string*, not on the raw bytes.** The pattern, `HIGH_ASCII_PATTERN` (`/[\x80-\xFF]{3,}/`), looks for three consecutive bytes in the high range. But applied to a decoded string it matches three consecutive *code points* in U+0080–U+00FF — and `«`, a non-breaking space (U+00A0), and `é` are exactly three such code points in a row. A correctly decoded French sentence trips the "this might be a legacy encoding" detector.
3. **The fallback loop tries `gb18030`, `gbk`, and `gb2312`, and keeps the first decoding that produces no replacement character (U+FFFD).** UTF-8 bytes of Latin text very often pair up as valid GB18030, so the corrupted text passes the check and is returned as the answer.

In short: the node decodes the body correctly, decides the correct result looks suspicious, and "fixes" it into garbage. The reporter's proposed upstream fix is to replace the heuristic with a strict decode — `new TextDecoder('utf-8', { fatal: true }).decode(buf)` — which succeeds on any valid UTF-8 body and throws only on genuinely invalid bytes, so the legacy-charset fallback runs only when it should. A commenter on the issue added one important refinement: merely checking for U+FFFD is not enough proof, because a valid UTF-8 body can legitimately contain a literal replacement character — the strict decoder settles that too, since it only throws on invalid byte sequences.

**Which responses trigger it?** The pattern needs three consecutive code points in U+0080–U+00FF after UTF-8 decoding. Plain ASCII never triggers it, and a lone `é` in an otherwise ASCII sentence does not either. French text is the classic trigger — guillemets (`« »`), non-breaking spaces before punctuation, and accented letters cluster together — but any language with accented Latin characters (German, Spanish, Portuguese, Scandinavian languages) can hit it, as can any JSON field that packs several accented words together.

## Step 1 - Confirm you are affected (two minutes)

Before changing anything, check whether your live data is already corrupted. Add a **Code node** immediately after your HTTP Request node and run it in the editor with real input data:

```js
const mojibakePattern = /[一-鿿]/; // CJK Unified Ideographs — should never appear in Latin text

const corrupted = $input.all().filter((item) => {
  return JSON.stringify(item.json).match(mojibakePattern);
});

if (corrupted.length > 0) {
  throw new Error(
    `Encoding bug: ${corrupted.length} item(s) contain CJK characters in text that should be Latin — ` +
    `e.g. ${JSON.stringify(corrupted[0].json).slice(0, 120)}. ` +
    `Apply the Response Format fix in Step 2 and re-fetch.`
  );
}

return $input.all();
```

The check is a heuristic, not a proof — it flags Chinese characters in fields that should be French, German, or English. If it throws, you have the bug in your live data. If it passes, your current responses are clean — but keep the guard in place, because the next API response with a guillemet can trigger it at any time.

To check data already stored, search your database or sheet for the tell-tale characters: `茅` (from `é`), `芦` (from `«`), `聽` (from a non-breaking space), `禄` (from `»`). Those four are the fingerprints of this exact bug — UTF-8 French re-decoded as GB18030.

## Step 2 - Fix A: set the Response Format explicitly to JSON (the confirmed workaround)

This is the workaround the reporter verified on n8n 2.46.6: **set the node's Response Format explicitly to JSON**. When the format is explicit, the body is parsed as JSON directly, and the encoding-detection code never runs.

1. Open the HTTP Request node.
2. Find **Response Format** (under Options / Response in node version 3+).
3. Change it from automatic detection to **JSON**.
4. Execute the node again with the same request.

You should see `{"titre": "Point d'étape", ...}` — the accents intact. That is the whole fix for any endpoint that returns JSON, which covers the large majority of API calls in n8n workflows.

> **Warning:** do not "fix" corrupted text downstream with a find-and-replace on the garbled characters (replacing `茅` with `é`, for example). The mapping from mojibake back to the original text is not one-to-one in general — the same garbled character can come from different originals — and a replace rule will silently mangle the next response that legitimately contains that character. Fix the decode, not the output.

## Step 3 - Fix B: for non-JSON text, fetch as binary and decode strictly

Fix A only works for JSON. If the endpoint returns HTML, CSV, or plain text, there is no JSON parser to bypass the detection — so bypass the detection yourself: fetch the response as raw binary, then decode it with the same strict check the reporter proposed for the upstream fix.

**In the HTTP Request node**, set **Response Format** to **File** (binary). The node now returns the untouched bytes.

**Add a Code node** immediately after it, and decode with a strict UTF-8 decoder that falls back to GB18030 only when the bytes are genuinely not UTF-8:

```js
const buf = Buffer.from($binary.data.data, 'base64');

let text;
try {
  // Strict decode: succeeds on any valid UTF-8, throws on invalid bytes.
  text = new TextDecoder('utf-8', { fatal: true }).decode(buf);
} catch {
  // Only reached when the bytes are genuinely not UTF-8 — e.g. a real GBK page.
  text = new TextDecoder('gb18030').decode(buf);
}

return [{ json: { text } }];
```

Two details matter here. First, `$binary.data.data` is the base64 string of the downloaded body — `Buffer.from(..., 'base64')` turns it back into raw bytes. Second, `{ fatal: true }` is the whole point: a non-strict decoder silently replaces invalid bytes with U+FFFD and never throws, which would hide a genuinely legacy-encoded response instead of routing it to the fallback. This is the same logic the reporter tested against the node's own helpers: valid UTF-8 with non-breaking spaces, accents, and even a literal U+FFFD character is kept as-is, while real Latin-1 and real GBK bytes throw and still reach the fallback, which decodes the GBK correctly.

## Step 4 - Verify the fix worked

Run the workflow once against an endpoint that returns the reporter's fixture text — any endpoint returning `application/json; charset=utf-8` with `« écoute »` in the body will do — and compare the two settings:

| Response Format | Output for `« écoute »` | Verdict |
|---|---|---|
| Automatic detection | `芦聽茅coute聽禄` | Bug reproduced — do not ship this setting |
| JSON (Fix A) / File + strict decode (Fix B) | `« écoute »` | Fixed |

If the output still shows garbled characters after Fix A, the write went through a different node — check that the HTTP Request node was actually changed and that no second HTTP Request node in the workflow still uses automatic detection on the same endpoint. If the output is clean, the fix is confirmed end to end: the bytes left the server correctly *and* n8n decoded them correctly.

For text endpoints, verify with the Code node from Step 3: send it a known UTF-8 body and a known GBK body (if you have one) and confirm the first comes back unchanged and the second still decodes to readable Chinese — the fallback must keep working for genuinely legacy-encoded sources.

## Prevent it next time

- **Never leave Response Format on automatic detection for an endpoint whose format you know.** Set JSON for APIs and File + strict decode for text. Automatic detection is a guess, and this bug is what a wrong guess looks like.
- **Keep the Step 1 guard node after every HTTP Request node that handles non-ASCII text.** It costs one node and it turns silent corruption into a loud, failed execution — which your error workflow can actually alert on.
- **Add `« écoute »` to your workflow's test data.** It is the smallest, most ordinary-looking string that triggers the bug — a guillemet, a non-breaking space, and an accented letter — and it belongs in every HTTP workflow's test fixtures alongside plain ASCII.
- **Watch [issue #43713](https://github.com/n8n-io/n8n/issues/43713) for the upstream fix.** When a release lands with the strict-decoder correction in `buffer-decoding.ts`, you can leave Response Format on automatic detection again — but keep the guard in place for a few releases, in case the fix does not cover every code path.
- **Audit the siblings.** The same "decode, then re-guess" pattern is a trap anywhere a node infers an encoding from content instead of trusting the declared charset. If another node in your stack auto-detects encodings on text, test it with `« écoute »` before you trust it.

## What this fix does not do

The workarounds above fix *your* decoding; they do not fix the node. Data already written with garbled text stays garbled until you rewrite those rows — re-run the affected items through the fixed workflow (the source API still has the clean text; the corruption happened only inside n8n). And the guard only protects responses that pass through a node you added it to: an HTTP Request node in a different workflow hitting the same French endpoint has the same bug, so audit every HTTP Request node that handles accented text, not just the one that bit you.

## FAQ

### Which n8n versions are affected?

The bug was reproduced on n8n 2.46.6 with HTTP Request node typeVersion 3 and above, and the same logic is on `master` as of November 12, 2026. The reporter also found stored text with the same corruption pattern from June 2026, so older releases are very likely affected too. There is no fixed version yet — issue #43713 is open, team-assigned, and tracked internally as Linear GHC-9752.

### Does this affect n8n Cloud too?

Yes — the bug is in the node's `buffer-decoding.ts` conversion, which runs identically on Cloud and self-hosted. Cloud users apply the same fixes; the only difference is that Cloud instances receive the upstream fix automatically once it ships.

### My API returns English only — am I affected?

Only if a response ever contains three consecutive characters in the U+0080–U+00FF range. Pure ASCII is safe, and a single accented character in an otherwise ASCII response does not trigger the pattern. But user-generated content is unpredictable — one French customer name or one `«` in a product description is enough — so set the format explicitly anyway.

### Why does the garbled text look like Chinese specifically?

Because the fallback tries GB18030 first, and UTF-8 byte pairs for accented Latin letters happen to be valid GB18030 byte pairs that map to Chinese characters. GBK and GB2312 are tried after it, but GB18030 usually "succeeds" first — which is why the corruption looks Chinese rather than like random bytes.

### Can I reverse the mojibake back to the original text?

Not reliably in a plain Code node. Reversing it means re-encoding the garbled string as GB18030 bytes and decoding those as UTF-8, which needs an encoding library (like `iconv-lite`) that the default Code node does not provide. The reliable path is to re-fetch from the source with the fixed node — the source data was never corrupted.

## Key Takeaways

1. **n8n's HTTP Request node can turn valid UTF-8 French into Chinese characters** — `Point d'étape` becomes `Point d'茅tape` — because the encoding detector re-decodes an already-correct UTF-8 string as GB18030.
2. **A declared `charset=utf-8` does not protect you** — the detector ignores it (it equals the default encoding) and tests a byte-pattern against the decoded string, where `«`, a non-breaking space, and `é` look like three high bytes in a row.
3. **The execution reports success** — this is silent data corruption, so add the CJK guard (`/[一-鿿]/`) after HTTP Request nodes handling non-ASCII text to turn it into a loud failure.
4. **The reliable fix today is to set Response Format explicitly** — JSON for APIs (reporter-confirmed workaround), or File + a strict `TextDecoder('utf-8', { fatal: true })` decode in a Code node for HTML, CSV, and plain text.
5. **No upstream fix has shipped yet** — issue #43713 is open as of November 13, 2026, team-assigned (Linear GHC-9752); verify with the `« écoute »` fixture and re-fetch any rows corrupted before the fix.

Next: if silent-success bugs are a pattern in your instance, read [Fix n8n Firestore Node Saving Tiny Decimals as Integers (Silent Data Corruption)](/blog/fix-n8n-firestore-small-decimals-integer-value/) — it covers the same failure class from the database side, including the guard-node pattern that catches all of them.
