---
title: "Fix n8n DateTime.diffTo() Silently Returning undefined for weekday, weekNumber, and yearDayNumber"
description: "n8n's DateTime.diffTo() with 'weekday', 'weekNumber', or 'yearDayNumber' silently returns undefined — no error. Here's the cause and the fix."
date: 2026-11-20
category: automation
tags: ["n8n", "error-fix", "expressions", "datetime", "luxon"]
draft: false
featured: false
image: "/og/fix-n8n-datetime-diffto-silent-undefined.webp"
---

Your workflow runs. n8n reports success. And yet a date calculation that should return a number quietly hands you `undefined` — no error, no warning, nothing in the execution log. If you have ever used `DateTime.diffTo()` with the unit `weekday`, `weekNumber`, or `yearDayNumber`, you have probably hit this bug. By the end of this post you will know exactly which three units break, why they pass validation and then vanish, and the workarounds that are verified to work today.

## The symptom: diffTo() returns undefined — but only for three units

The pattern is specific, which is what makes it so hard to spot. Evaluate this expression in any n8n workflow:

```javascript
{{ DateTime.fromISO("2024-03-30T18:49:00Z").diffTo("2024-03-25T18:49:00Z", "weekday") }}
```

The result is `undefined`. The same happens for `weekNumber` and `yearDayNumber`. There is no error, no red banner, no failed execution — the expression simply evaluates to nothing, and whatever downstream node consumes that value gets `undefined` instead of a duration.

What makes it worse is that the function is supposed to catch bad units. Try a genuinely made-up unit and you get the friendly error the designers intended:

```javascript
{{ DateTime.fromISO("2024-03-30T18:49:00Z").diffTo("2024-03-25T18:49:00Z", "fortnight") }}
// Unsupported unit 'fortnight'. Supported: 'milliseconds', ...
```

So `fortnight` fails loudly and correctly, while `weekday` — a real, documented Luxon concept — fails silently. The reporter of [GitHub issue #44559](https://github.com/n8n-io/n8n/issues/44559) reproduced it on n8n master at commit `59604870` (2026-11-19), and confirmed it hits **all three expression engines**: the legacy `n8n-workflow` engine and the isolated `@n8n/expression-runtime` engine, both its VM and QuickJS variants.

The real-world damage is silent data corruption, not a crash. A Set node writes `undefined` into a field that should hold a number. An IF node comparing that field takes the wrong branch. A downstream API call sends a null where a duration belongs — and the execution still reports success, so nothing alerts you until a customer or a report surfaces the wrong data days later.

> **Note:** This is not the same bug as the 2.46 error-output regression covered in [Fix n8n $('Node').first() Returning null for a Node's Error Output in Webhook Executions](/blog/fix-n8n-error-output-expression-null-2-46-regression/). That one is about node references resolving to `null` in production webhooks. This one is about a date function swallowing its own error in every engine, in every execution mode.

## Root cause: three extract-only parts sneak past the unit check

`diffTo()` is n8n's own extension on Luxon's `DateTime` — it is not raw Luxon. It accepts a unit, or an array of units, and validates each one against a set built from two lists: `dateParts` and `durationUnits`.

The problem is what `dateParts` contains. Alongside genuine duration units it also holds the three parts that Luxon's `extract()` supports: `weekday`, `weekNumber`, and `yearDayNumber`. These are **get-only parts** — they describe a single date (which weekday it falls on, which ISO week it belongs to, which day of the year it is). They are not durations, and Luxon's `diff()` does not accept them as units.

So the validation passes — `weekday` is in the allowed set — and the value reaches Luxon, which throws an internal `InvalidUnitError`. That is where the silence comes from: n8n's expression sandbox only forwards `ExpressionError` and `ExpressionExtensionError` instances. Luxon's internal error is neither, so it gets swallowed and the expression evaluates to `undefined`.

The two files involved are `packages/workflow/src/extensions/date-extensions.ts` and its mirror in `packages/@n8n/expression-runtime/src/extensions/date-extensions.ts` — the fix has to land in both, because the legacy engine and the isolated engine each carry their own copy. n8n team member grinem confirmed the diagnosis in the issue thread on 2026-11-19, and the reporter has a fix ready with regression tests (a pull request was promised shortly after the report). The issue is tracked internally as Linear GHC-9814 and is still open as of 2026-11-19, with no fixed version yet.

In plain terms: the unit check trusts a list that mixes two different kinds of thing — units you can measure a difference in, and properties you can only read off a single date. Three of the second kind slip through, Luxon rejects them, and the sandbox eats the rejection instead of surfacing it.

## The fix: use a real duration unit, or extract the part you actually want

There are two correct replacements, and which one you need depends on what you were actually trying to compute. Most people reaching for one of these three units want one of the two things below.

### Step 1 - If you want a difference, use a valid duration unit

`diffTo()` only accepts genuine duration units. Use one of these — singular forms work too:

| Unit | What it measures |
|---|---|
| `years`, `quarters`, `months`, `weeks`, `days` | Calendar-scale differences |
| `hours`, `minutes`, `seconds`, `milliseconds` | Clock-scale differences |

For example, to get the whole weeks between two dates:

```javascript
{{ DateTime.fromISO("2024-03-30T18:49:00Z").diffTo("2024-03-25T18:49:00Z", "weeks").weeks }}
// 0.7142857142857143
```

You should see a number, not `undefined`. If you need a whole number, wrap it in `Math.floor()` or `Math.round()` — `diffTo()` returns a Luxon `Duration`, and `.weeks` reads the value out of it.

> **Warning:** `weekNumber` is not the same as `weeks`. `weekNumber` is the ISO week number of a single date (week 13 of the year, say); `weeks` is the length of the gap between two dates. Swapping one for the other changes the answer even when the expression works.

### Step 2 - If you want the weekday, week number, or day of year, use extract()

The three broken units are perfectly valid — just not for `diffTo()`. They belong to `extract()`, which reads a property off one date:

```javascript
{{ DateTime.fromISO("2024-03-30T18:49:00Z").extract("weekday") }}
// 6 (Saturday — Luxon numbers weekdays 1 = Monday through 7 = Sunday)

{{ DateTime.fromISO("2024-03-30T18:49:00Z").extract("weekNumber") }}
// 13

{{ DateTime.fromISO("2024-03-30T18:49:00Z").extract("yearDayNumber") }}
// 90
```

You should see real numbers. If you were diffing two dates to work out "how many weekdays apart are these?" — that is a different calculation entirely: take the difference in `days`, then derive the weekday of each endpoint with `extract("weekday")` and do the arithmetic yourself in a Code node.

### Step 3 - Guard the diffTo() calls you already have

Until a fixed n8n release ships, audit your workflows for the three units — search workflow JSON for `diffTo` combined with `weekday`, `weekNumber`, or `yearDayNumber`. Any hit is silently producing `undefined` today.

For the calls you keep, add a guard so a silent `undefined` can never flow downstream unnoticed. In a Code node after the calculation:

```javascript
const gap = $json.gapInWeeks;
if (gap === undefined) {
  throw new Error('diffTo() returned undefined — check the unit passed to it');
}
return $input.all();
```

That turns the silent failure into a loud one: the execution fails, the Error Trigger fires if you have one, and you find out in minutes instead of days. The same guard belongs in an IF node if you prefer no-code: check whether the field `is empty` before the branch that consumes it.

## Verify it worked

Run the workflow and check the field that used to be `undefined`:

1. The expression `{{ DateTime.fromISO("2024-03-30T18:49:00Z").diffTo("2024-03-25T18:49:00Z", "weeks").weeks }}` returns `0.7142857142857143`.
2. The expression `{{ DateTime.fromISO("2024-03-30T18:49:00Z").extract("weekday") }}` returns `6`.
3. The expression with `"fortnight"` still throws `Unsupported unit 'fortnight'` — that friendly error is the correct behaviour, and the upcoming fix will make `weekday`, `weekNumber`, and `yearDayNumber` throw the same way instead of returning `undefined`.

## Prevent it next time

- **Keep a mental split between duration units and date parts.** Duration units (`days`, `weeks`, `months`, `years`, `hours`, `minutes`, `seconds`, `milliseconds`, `quarters`) measure a gap between two dates. Date parts (`weekday`, `weekNumber`, `yearDayNumber`, `month`, `day`, `hour`) describe one date and belong to `extract()`. If a unit sounds like a property of a single date, it does not belong in `diffTo()`.
- **Treat any `undefined` from a date expression as a bug, not an empty value.** Date math in n8n either returns a Duration or throws — `undefined` means an error was swallowed somewhere. A cheap IF-node check after any `diffTo()` catches the next swallowed error before it reaches your data.
- **Watch for the fix in the n8n changelog.** The reporter has a fix with regression tests ready, and the issue (GH #44559, Linear GHC-9814) is team-confirmed. Once it lands, `diffTo()` with these three units will throw the friendly `Unsupported unit` error instead of returning `undefined` — at which point you can remove the guard in Step 3, but keep the valid-unit replacements: they are the correct code either way.

## FAQ

### Does this affect $now.diff() too?

No — at least not in the way reported. `.diff()` is Luxon's native method, not n8n's `diffTo()` extension, and the issue is specifically about `diffTo()`'s validation list mixing `dateParts` into the allowed units. If you use native `.diff()`, pass it the same genuine duration units (`days`, `weeks`, …) and you are fine.

### Which n8n versions are affected?

The report was verified on master at commit `59604870` (2026-11-19), and the bug lives in the validation code shared by the legacy engine and the isolated VM/QuickJS engines, so it affects current 2.x releases. There is no fixed version yet as of 2026-11-19 — check the [GitHub issue #44559](https://github.com/n8n-io/n8n/issues/44559) for the release that carries the fix.

### Why doesn't the expression editor show an error?

Because the error never reaches the editor. Luxon throws an internal `InvalidUnitError`, and the expression sandbox only forwards `ExpressionError` and `ExpressionExtensionError` — everything else is swallowed and the expression evaluates to `undefined`. The editor cannot display an error it never receives, which is exactly why the failure is silent.

## Key Takeaways

1. **`diffTo()` with `weekday`, `weekNumber`, or `yearDayNumber` silently returns `undefined`** — the units pass validation because they sit in the `dateParts` list, then Luxon rejects them and the sandbox swallows the error.
2. **The three units are extract-only** — use `extract("weekday")`, `extract("weekNumber")`, or `extract("yearDayNumber")` on a single date, and use real duration units (`days`, `weeks`, …) for `diffTo()`.
3. **Silent `undefined` is the dangerous part** — executions report success while downstream data is wrong, so guard `diffTo()` results with an explicit `undefined` check until a fixed release ships.
4. **A fix is coming** — the reporter has a patch with regression tests ready (GH #44559, Linear GHC-9814, team-confirmed), which will make these units throw the friendly `Unsupported unit` error instead.

Next: search your workflows for `diffTo` calls using any of the three units and replace them today — the fix is a one-line change per expression, and the audit takes five minutes.
