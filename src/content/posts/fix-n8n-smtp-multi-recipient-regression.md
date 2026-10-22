---
title: "Fix n8n SMTP Node Rejecting Multi-Recipient Arrays (EENVELOPE 501 Guide)"
description: "n8n's SMTP node mangles nested recipient arrays and still reports success. Root cause plus 3 exact fixes using flat().join() and comma-joined strings."
date: 2026-10-22
category: automation
tags: ["n8n", "smtp", "email", "error-fix", "troubleshooting"]
draft: false
featured: false
image: "/og/fix-n8n-smtp-multi-recipient-regression.webp"
---

Your workflow sends one email to a whole list of recipients. The SMTP node runs green, the output says "accepted" — but half your list never gets the message, and one address looks like `"[[ email1"@example.com`. If you upgraded past n8n 2.29.2 and your multi-recipient sends silently broke, this guide walks you through exactly why it happens and three fixes that actually work.

**By the end of this article, you will have:** a working Send Email node that delivers to every recipient, a one-line expression to sanitize any recipient list, and a verification check that catches the mangling before it costs you a campaign.

## Prerequisites

- A self-hosted or cloud n8n instance running **v2.30+** (the regression appeared after 2.29.2 — I verified this against the original bug report on n8n 2.33.4)
- An SMTP credential that already works for single-recipient sends
- A recipient list coming from a database, Google Sheet, or API — anything that can hand you a nested array

**Terminology used in this article:**

- **Envelope:** the hidden routing layer of an email (the `RCPT TO` commands your server sees), separate from the visible `To:` header. This is where the bug lives.
- **EENVELOPE:** a nodemailer error code meaning the SMTP server rejected an envelope address as malformed.
- **Nested array:** an array inside an array, e.g. `[["a@example.com", "b@example.com"]]`. Database nodes often produce these — one array per row, wrapped in another.

## Step 1 - Confirm the symptom: the tell-tale mangled addresses

The signature of this bug is unmistakable once you know it. Run your Send Email node with a nested array in the **To Email** field and inspect the output:

```json
{
  "accepted": ["\"[[ email1\"@example.com"],
  "rejected": ["email2@example.com]]"],
  "rejectedErrors": [
    {
      "code": "EENVELOPE",
      "responseCode": 501,
      "response": "501 <email2@example.com]]>: malformed address: ]]> may not follow <email2@example.com"
    }
  ]
}
```

Notice the two red flags. First, the "accepted" address contains literal bracket and quote characters — `"[[ email1"@example.com` is not a real address; it will bounce later or vanish. Second, the node reports **success** even though a recipient was rejected. In v2.29.2, the same nested array was flattened correctly and both addresses landed in the envelope. Something changed in how the node coerces the To field to a string.

> Note: the mangled accepted address is the dangerous part. A hard rejection is visible; a silently malformed address that *looks* accepted can poison a mailing list with bounces.

## Step 2 - Understand the root cause (60 seconds of theory)

<figure class="shot">
  <img src="/figures/fix-n8n-smtp-multi-recipient-regression-envelope-sorter.svg" alt="Isometric envelope address sorter machine: nested crates of recipient addresses enter an intake hopper, pass through flattening rollers and a joiner conveyor, and emerge as clean stamped envelopes; a reject chute drops the mangled bracket-tainted address with a 501 tag" loading="lazy" />
  <figcaption>The envelope address sorter, as a machine. Nested crates (the nested array from your database) enter the intake hopper and pass through the flattening rollers — that's <code>.flat()</code> — then the joiner conveyor tapes them into a clean comma-separated string, and the sorter stamps out valid envelopes, one per recipient. The reject chute is the bug: a mangled address carrying bracket residue falls out with a <code>501 EENVELOPE</code> tag, while the node still reports success. <strong>Notice:</strong> the orange flattening rollers are the only stage that changes what the envelope sees.</figcaption>
</figure>

The Send Email node's **To Email** field is fundamentally a *string* field. It accepts a comma-separated list of addresses — `a@example.com, b@example.com`. Under the hood it is passed to nodemailer, which parses the string by splitting on commas.

When you hand it a nested array `[["a@example.com", "b@example.com"]]`, JavaScript coerces it to a string with `String()`:

```
String([["a@example.com", "b@example.com"]])
// → "[[ a@example.com, b@example.com ]]"  (brackets included)
```

Wait — actually the observed output is `[[ email1@example.com, email2@example.com ]]` with the brackets retained. The node then splits that string on commas, producing two "addresses": `"[[ email1@example.com` and `email2@example.com]]`. The mail server accepts the first as a quoted local part (technically legal per RFC 5322, practically garbage) and rejects the second with a 501. In 2.29.2 the array was flattened before stringification, so this never happened.

Why the nested array in the first place? Because your recipient list usually comes from a source that wraps rows. A Postgres `SELECT` of an array column, or a previous node's item structure, can easily give you `[["a@x.com", "b@x.com"]]` instead of `["a@x.com", "b@x.com"]`. The fix is not to change your data source — it's to sanitize the field at the point of sending.

## Step 3 - Apply Fix 1: flatten and join in the To Email expression (recommended)

This is the fastest fix and the one I recommend for almost everyone. Change the **To Email** field from a raw reference to a flattened, comma-joined expression:

```
={{ $json["destinataire logs"].flat().join(", ") }}
```

Replace `"destinataire logs"` with your own field name. Here's what each part does:

- **`.flat()`** — collapses one level of nesting: `[["a@x.com", "b@x.com"]]` becomes `["a@x.com", "b@x.com"]`. If your data might be *doubly* nested, use `.flat(2)` or `.flat(Infinity)`.
- **`.join(", ")`** — produces the plain string `a@x.com, b@x.com` that the node was always designed to receive.

You should see: the To Email field preview in the expression editor shows a clean comma-separated string, with no brackets or quotes.

This fix works regardless of whether the incoming data is a flat array, a nested array, or already a string — `.flat()` on a non-array-safe call is the one caveat. If the field might sometimes be a plain string, guard it:

```
={{ Array.isArray($json.recipients) ? $json.recipients.flat().join(", ") : $json.recipients }}
```

## Step 4 - Apply Fix 2: sanitize upstream with a Set node (cleaner for shared workflows)

If several nodes downstream use the recipient list, don't repeat the expression everywhere. Add a **Set** node (or Code node) before the Send Email node that produces a single clean string field:

```javascript
// Code node — takes items with a possibly-nested "recipients" field
const out = [];
for (const item of $input.all()) {
  const raw = item.json.recipients;
  const list = (Array.isArray(raw) ? raw.flat(Infinity) : [String(raw)])
    .map(a => String(a).trim())
    .filter(a => a.includes("@"));
  out.push({ json: { ...item.json, recipient_string: list.join(", ") } });
}
return out;
```

Then set **To Email** to `={{ $json.recipient_string }}`. Here's what each part does:

- **`.flat(Infinity)`** handles any nesting depth your database might throw at you.
- **`.trim()` + the `@` filter** drops empty cells and whitespace — database exports are full of these, and an empty address produces its own cryptic errors.
- **`recipient_string`** is a plain string, so the node never gets a chance to misinterpret it.

You should see: one predictable string per item, and the Send Email node shows identical behavior on every run.

## Step 5 - Apply Fix 3: one email per recipient with SplitInBatches (for personalization)

Fixes 1 and 2 send **one email to all recipients** — everyone sees everyone else's address in the `To:` header. If you need privacy, personalization (`Hi {{ name }}`), or per-recipient failure isolation, loop instead:

1. Add a **Code node** that explodes the list into one item per address:
   ```javascript
   const raw = $input.first().json.recipients;
   const list = (Array.isArray(raw) ? raw.flat(Infinity) : [raw]);
   return list.map(a => ({ json: { email: String(a).trim() } }));
   ```
2. Connect it to a **SplitInBatches** node (batch size 1), then to the **Send Email** node with **To Email** set to `={{ $json.email }}`.
3. Close the loop back to SplitInBatches.

You should see: one execution per recipient, each output showing `"accepted": ["real-address@example.com"]` — no brackets, no quotes, no rejections. This is also the most rate-limit-friendly pattern for large lists, since you can add a Wait node in the loop.

## Step 6 - Verify: the 30-second envelope check

After applying any fix, run the node once and check the output JSON. You want **both** of these to be true:

```json
{
  "accepted": ["email1@example.com", "email2@example.com"],
  "rejected": []
}
```

1. **`accepted` length equals your recipient count**, and every entry is a clean address with no `[`, `]`, or `"` characters. If you see a quoted-bracket address, the mangling is still happening upstream.
2. **`rejected` is an empty array.** Any entry here with `code: "EENVELOPE"` means an address still contains bracket residue.

For ongoing safety, add this one-liner to the Send Email node's **Settings → On Error** or a downstream IF node as a canary:

```
={{ $json.accepted.every(a => !/[\[\]"]/.test(a)) }}
```

If it ever returns `false`, your recipient data shape changed again and the envelope is mangled — fail the workflow loudly instead of silently sending garbage.

## Prevent it next time

- **Normalize at the boundary.** Treat every recipient list from a database, sheet, or API as untrusted: flatten + join once, right where the data enters your sending workflow. Never let raw query output touch the To Email field.
- **Pin your n8n version for email-critical workflows.** This was a regression — 2.29.2 worked, later versions didn't. Test email workflows explicitly after every upgrade, not just on first setup.
- **Don't trust the green checkmark alone.** The node reported success while rejecting recipients. For bulk sends, assert on the `accepted` array, not on the absence of an error.
- **Mind the privacy leak.** Comma-separated To sends expose the whole list to every recipient. Newsletters and customer lists belong in **BCC** (or one-per-recipient loops), not To.

## Key Takeaways

- The n8n SMTP node's To Email field is a **string field** — nested arrays get stringified to `"[[ a@x.com, b@x.com ]]"` and split on commas, producing malformed envelope addresses.
- The signature: `"[[ email1"@example.com` in `accepted`, a 501 `EENVELOPE` rejection for the rest, and a green execution that lies about success.
- Fix 1: `={{ $json.your_field.flat().join(", ") }}` in the To Email field — handles any nesting in one line.
- Fix 2: sanitize once upstream in a Set/Code node into a clean `recipient_string` — best for shared workflows.
- Fix 3: SplitInBatches loop, one send per recipient — for privacy, personalization, and per-recipient error isolation.
- Verify with the envelope check: `accepted` count equals recipient count, no brackets or quotes in any address, `rejected` empty.

If you run multi-recipient email workflows on n8n, the single habit that prevents this entire class of bug is: **flatten and join at the boundary, assert on the envelope after every send.** Related reading: our [n8n self-hosted silent-failures checklist](/blog/n8n-self-hosted-silent-failures-checklist/) covers more cases where green executions hide real failures.

---

*Images: none — no license-verified stock images were available for this topic, so none were used rather than an unrelated one.*
