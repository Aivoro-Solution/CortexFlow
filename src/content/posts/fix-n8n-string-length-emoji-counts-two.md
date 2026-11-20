---
title: "Fix n8n String length() Counting Every Emoji as Two Characters"
description: "n8n's String length() counts UTF-16 code units, so one emoji reads as 2 characters. Here's the cause and the Code-node fix that counts real characters."
date: 2026-11-20
category: automation
tags: ["n8n", "error-fix", "expressions", "unicode", "emoji"]
draft: false
featured: false
image: "/og/fix-n8n-string-length-emoji-counts-two.webp"
---

Your workflow runs. n8n reports success. And yet a message-length check that should pass quietly fails — or a "max 100 characters" truncation chops a message short — because one emoji counted as two characters. If you validate, truncate, or display text length anywhere in n8n with `String.length()`, you have probably hit this bug. By the end of this post you will know exactly why the count is wrong, how to prove it in thirty seconds, and the Code-node workaround that counts real characters today.

## The symptom: one emoji, length 2

The pattern is specific, which is what makes it so easy to miss. Evaluate this expression in any n8n workflow, with each string containing exactly one emoji (U+1F600, 😀):

```javascript
{{ "😀".length() }}
{{ "a😀b".length() }}
```

The results are `2` and `4`. The same happens for any character outside the Basic Multilingual Plane — for example CJK Extension B ideographs such as U+20000. Plain ASCII is unaffected: `{{ "String".length() }}` correctly returns `6`, and two BMP (Basic Multilingual Plane) CJK characters still return `2`.

This shows up in ordinary workflows, not edge cases. Text coming from APIs, chat messages, form fields, or CSV files often contains emoji. A user who writes `{{ $json.message.length() }}` in a Set or IF node to validate, truncate, or display text length gets the wrong number — and a comparison such as "the message must be at most one character" is wrong from the start.

The reporter of [GitHub issue #44587](https://github.com/n8n-io/n8n/issues/44587) (opened 2026-11-20) reproduced it in any expression field, in every execution mode. There is no error, no red banner, no failed execution — the expression simply returns a confident-looking wrong number, and whatever downstream node consumes it acts on bad data.

> **Note:** This is not the same bug as the `DateTime.diffTo()` issue covered in [Fix n8n DateTime.diffTo() Silently Returning undefined](/blog/fix-n8n-datetime-diffto-silent-undefined/). That one swallows an error and returns `undefined`. This one returns a number — the wrong number.

## Root cause: length() counts UTF-16 code units, not characters

n8n's `length()` string extension is documented as "Returns the character count of a string". But its implementation, in both mirrored copies of the string extensions — `packages/workflow/src/extensions/string-extensions.ts` and `packages/@n8n/expression-runtime/src/extensions/string-extensions.ts` — is effectively:

```javascript
return value.length;
```

That is JavaScript's `String.prototype.length`, and JavaScript strings are sequences of UTF-16 code units, not characters. Every character in the Basic Multilingual Plane (U+0000 to U+FFFF — Latin, Cyrillic, most CJK, common symbols) fits in one 16-bit code unit, so `.length` and the character count agree. Anything above U+FFFF does not fit, so UTF-16 stores it as a **surrogate pair**: two code units that together encode one code point.

So for 😀 (U+1F600): 2 code units, 1 code point, 1 thing a human sees. `.length` reports 2 because it counts the lowest layer — the storage boxes, not the characters.

**There are three different things people call "a character", and they give three different answers:**

| Unit | What it is | Counted by | `"😀"` | `"👨‍👩‍👧‍👦"` (family emoji) |
| --- | --- | --- | --- | --- |
| UTF-16 code units | One 16-bit slot of UTF-16 | `str.length` | 2 | 11 |
| Unicode code points | One Unicode scalar value (U+1F600) | `[...str].length` | 1 | 7 |
| Grapheme clusters | One thing a human perceives as a character | `Intl.Segmenter` | 1 | 1 |

The family emoji is the sharpest illustration: it is built from four person emoji joined by three zero-width joiners, so it is 11 code units, 7 code points, and 1 grapheme. n8n's `length()` reports 11. The issue asks for code-point counting (the documented "character count"), which fixes the single-emoji case — but even the fixed version would still report 7 for the family emoji. Keep that distinction in mind when you pick a workaround below.

## Step 1 - Prove the bug in your own workflow

Before changing anything, confirm you are affected. Add a Code node (or a Set node with an expression) and run it:

```javascript
// Code node — paste, run, and read the output
const samples = ["😀", "a😀b", "String", "👨‍👩‍👧‍👦"];

return samples.map((text) => ({
  json: {
    text,
    lengthMethod: text.length,          // what n8n's length() returns today
    codePoints: [...text].length,       // the correct character count
    graphemes: [...new Intl.Segmenter("en", { granularity: "grapheme" }).segment(text)].length,
  },
}));
```

You should see `lengthMethod` of 2, 4, 6, and 11 against `codePoints` of 1, 3, 6, and 7. If your numbers match, the bug is live in your n8n version and every `length()` check on emoji-bearing text is suspect.

> **Warning:** Do not "fix" this by switching to `.split("")`. `"😀".split("")` also returns 2 — it splits on code units, exactly like `.length`. The spread operator and `Array.from()` are the ones that iterate by code point.

## Step 2 - Count real characters with a Code node

The reliable place for the workaround is a Code node, where you have full JavaScript. Add it wherever you currently measure text — before your IF validation, before truncation, or as a field your downstream nodes read instead of `length()`:

```javascript
// Code node — "Run Once for All Items", returns one item per input item
const text = $input.item.json.message ?? "";
const codePointCount = [...text].length;
const graphemeCount = [...new Intl.Segmenter("en", { granularity: "grapheme" }).segment(text)].length;

return {
  json: {
    ...$input.item.json,
    charCount: codePointCount,       // matches the documented behaviour of length()
    graphemeCount,                   // what a human sees — use this for display limits
  },
};
```

Here is what each part does:

- `[...text].length` — the spread operator iterates the string by Unicode code point, so each surrogate pair becomes one element. This is the count `length()` was documented to return, and it is the one the GitHub issue asks n8n to implement.
- `Intl.Segmenter` with `granularity: "grapheme"` — counts user-perceived characters, so a ZWJ family emoji counts as 1 and a flag emoji counts as 1. Use this when the limit is about what a person sees (a chat bubble, a username field, a tweet-length check).
- `$input.item.json.message ?? ""` — guards against a missing or null field. Without it, spreading `undefined` throws and the node fails.

After this node, your IF node compares `{{ $json.charCount }}` (or `{{ $json.graphemeCount }}`) instead of `{{ $json.message.length() }}` — and the comparison is finally correct.

## Step 3 - Truncate without slicing an emoji in half

Length checks are only half the story. The same UTF-16 trap breaks truncation: `"a😀b".slice(0, 2)` returns `"a"` plus a lone high surrogate — a broken character that renders as `�` downstream. If you cap message length anywhere, truncate by code point, not by code unit:

```javascript
// Code node — safe truncation to N characters
const text = $input.item.json.message ?? "";
const maxChars = 100;

const truncated = [...text].slice(0, maxChars).join("");

return {
  json: {
    ...$input.item.json,
    message: truncated,
    wasTruncated: [...text].length > maxChars,
  },
};
```

`[...text]` splits the string into code points first, so `.slice()` can never cut a surrogate pair in half. The `wasTruncated` flag tells downstream nodes whether anything was lost, which the old `.slice(0, 100)` version never did.

## Step 4 - Verify the fix works

Run the Step 1 probe again, but this time read the Code node's `charCount` and `graphemeCount` fields instead of `.length`. You should see:

| Input | `.length()` (broken) | `charCount` (code points) | `graphemeCount` |
| --- | --- | --- | --- |
| `"😀"` | 2 | 1 | 1 |
| `"a😀b"` | 4 | 3 | 3 |
| `"String"` | 6 | 6 | 6 |
| `"👨‍👩‍👧‍👦"` | 11 | 7 | 1 |
| `"é"` (precomposed) | 1 | 1 | 1 |
| `"é"` (e + combining accent) | 2 | 2 | 1 |

I verified these numbers with Node.js (the same JavaScript engine n8n's Code node runs): the spread counts and the `Intl.Segmenter` counts behave exactly as the table shows. Note the last two rows — a combining accent is two code points but one grapheme, so even the code-point count can over-count what a human sees. If your limit is about display width, use `graphemeCount`; if it is about matching the documented `length()`, use `charCount`.

Then run one real workflow end to end with an emoji-bearing message through your IF validation and your truncation step, and confirm the branch taken and the stored text are both correct. A unit test in isolation is not enough — the bug bites at the boundary between nodes, so verify at the boundary.

## Prevent it next time

- **Audit every `length()` call.** Search your exported workflows (`n8n export:workflow --all`, then grep for `.length()`) for any expression that measures user-generated or API-returned text. Any of them can be wrong today if the text contains emoji.
- **Make the Code node a habit.** For any text that can contain emoji, compute `charCount` once, early, and have every downstream node read that field instead of calling `length()` again.
- **Watch the upstream issue.** As of 2026-11-20, [GitHub issue #44587](https://github.com/n8n-io/n8n/issues/44587) is still open with no team reply, no pull request, and no fixed version. When n8n ships the fix (counting code points in both mirrored string-extension files), you can drop the workaround — but keep the Code node until you have upgraded to a release that contains it, and re-run the Step 1 probe after upgrading to confirm.
- **Do not trust `.length` in any JavaScript context for this.** The trap is not n8n-specific: it is JavaScript's `String.prototype.length` behaving exactly as specified. Anywhere you count characters in JS — a Code node, a webhook handler, a validation function — ask which of the three units you actually mean.

## Limits and honest caveats

This workaround counts code points or graphemes, but it cannot make n8n's own `length()` correct — only an upstream fix in the two string-extension files can do that, and none exists yet. The issue was opened on 2026-11-20, so there is no team confirmation and no timeline; treat the workaround as the fix for now, not as a temporary patch with a known expiry date. Also, `Intl.Segmenter` is available in modern Node.js (n8n's Code node runs on Node), but if you run n8n on a very old Node version, verify `Intl.Segmenter` exists before relying on `graphemeCount` — `charCount` via the spread operator works everywhere. Finally, neither count measures display width: a wide CJK character and a narrow Latin letter both count as 1, so do not use either for pixel-width layout.

## FAQ

### Does this affect all n8n versions?

The issue reproduces in any expression field and both string-extension implementations are affected, so yes — every current version that ships this `length()` is affected. There is no fixed version as of 2026-11-20.

### Why not just use `.length` on the string in a Code node?

That is the same trap in a different node. `"😀".length` in a Code node is also 2, because it is the same JavaScript `String.prototype.length`. You need the spread operator or `Array.from()` to iterate by code point.

### Is `[...str].length` the same as what a user sees?

Not always. It counts code points, which fixes single emoji and astral CJK characters. But a ZWJ family emoji is 7 code points and 1 grapheme, and `e` + combining accent is 2 code points and 1 grapheme. For what a user sees, use `Intl.Segmenter` with `granularity: "grapheme"`.

### Does `.length()` break anything else, like `.slice()` or `.substring()`?

Yes, in the same way. Any operation that indexes by code unit — `.slice()`, `.substring()`, `.charAt()`, bracket indexing — can split a surrogate pair. Truncate with `[...text].slice(0, N).join("")` as shown in Step 3.

## Key Takeaways

1. **n8n's `length()` counts UTF-16 code units, not characters** — `"😀".length()` returns 2, `"a😀b".length()` returns 4, despite the docs promising a character count.
2. **The root cause is one line** — `return value.length;` in the mirrored string-extension files — so the bug hits every expression engine and every execution mode.
3. **Count code points with `[...text].length`** in a Code node, and use `Intl.Segmenter` with grapheme granularity when the limit is about what a human sees.
4. **Truncate by code point** with `[...text].slice(0, N).join("")`, never with `.slice()` on the raw string, or you will split emoji in half.
5. **The issue (#44587) is still open with no fixed version** as of 2026-11-20 — keep the Code-node workaround until you upgrade to a release that contains the upstream fix, and re-run the probe after upgrading.

Next: audit your own workflows for `.length()` on user-generated text — the emoji in your users' messages has been miscounting silently, and the fix is one Code node per measurement point.
