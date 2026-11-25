---
title: "Fix n8n hasField() Returning True for toString and constructor"
description: "n8n's hasField() says every item has a toString field, even empty ones. The in operator is the cause — here is the own-key check that answers correctly."
date: 2026-11-25
category: automation
tags: ["n8n", "error-fix", "expressions", "javascript", "workflows"]
draft: false
featured: false
image: "/og/fix-n8n-hasfield-prototype-names-always-true.webp"
---

You add a guard to an IF node: only continue when the item actually carries a field. The expression preview says `true`, the workflow takes the branch — and the item that just passed has no such field at all. Nothing errored, nothing warned you, and the branch that should have been skipped ran anyway. The cause is a bug in n8n's `hasField()` expression helper: it checks field presence with JavaScript's `in` operator, which also matches names every object inherits from `Object.prototype` — `toString`, `constructor`, `hasOwnProperty`, and friends. For those names, `hasField()` answers `true` for every item, including a completely empty one. By the end of this post you will know exactly which names are affected, how to replace the check with one that only sees real fields, and how to audit your existing workflows for guards that have been silently always-true.

## The symptom: an empty object "has" fields it never had

Open any node's expression editor and evaluate these three expressions:

```text
{{ ({}).hasField('toString') }}
{{ ({}).hasField('constructor') }}
{{ ({}).hasField('hasOwnProperty') }}
```

All three return `true`. The object literal `{}` has no fields at all, yet `hasField()` claims it carries all three. The same happens on real items: `{{ $json.hasField('constructor') }}` returns `true` for every item flowing through the node, whatever the item actually contains.

This was reported in [GitHub issue #43964](https://github.com/n8n-io/n8n/issues/43964) (opened 2026-11-16, reproduced on current master in expression evaluation, self-hosted, SQLite), still open as of 2026-11-25 with no fixed version yet — so the replacement checks below are the fix for now. Note what the bug is *not*: ordinary field names work correctly. `{{ $json.hasField('email') }}` answers `true` only when the item really has an `email` key. The false positives are confined to a specific set of names, which is exactly what makes the bug easy to miss — your guard works in testing with normal field names and only misbehaves when the name being checked collides with the inherited set, or when the field name comes from upstream data instead of being typed by you.

## The root cause: `in` walks the prototype chain

An expression in n8n is a small piece of JavaScript inside `{{ }}`, and `$json` is the current item's data as a plain object. `hasField()` is one of n8n's object extension methods — helpers n8n adds to objects inside expressions, alongside `keys()`, `values()`, and `removeField()`. The documentation describes `hasField()` as checking the object's top-level keys: it should answer whether *this item* carries that field.

The implementation, per the issue, uses the `in` operator. In JavaScript, `'toString' in {}` is `true`, because `in` does not stop at the object's own keys — it walks the prototype chain, and every plain object inherits `toString`, `constructor`, `hasOwnProperty`, `valueOf`, and several more names from `Object.prototype`. So the check answers a different question than the one you asked: not "does this item have the field?" but "does this name exist anywhere on the object, inherited or not?" For inherited names the answer is always yes, so any guard, IF condition, or validation built on `hasField()` with one of those names is permanently stuck on `true`.

The dangerous shape is the dynamic one. A hard-coded `hasField('toString')` is rare, but `hasField($json.fieldName)` — where the field name arrives from a form, an API response, or a mapping table — can hit the inherited set at runtime without anyone typing it. The workflow then takes the "field present" branch for an item that does not have the field, and downstream nodes read a value that was never there.

## The fix: check own keys, not the prototype chain

The correct question is whether the name is one of the object's *own* keys. JavaScript answers that with `Object.hasOwn()`, `Object.prototype.hasOwnProperty.call()`, or by listing the own keys and testing membership. All three return `false` for `toString` on an empty object and `true` when the item genuinely carries a `toString` field of its own — verified with Node.js: `'toString' in {}` is `true`, while `Object.hasOwn({}, 'toString')` and `Object.keys({}).includes('toString')` are both `false`, and `Object.hasOwn({ toString: 'custom' }, 'toString')` is `true`.

### Step 1 - Replace the expression check with a keys-membership test

In any expression field, swap `hasField()` for a membership test against the item's own keys. n8n's `keys()` extension returns the object's own top-level keys as an array, so:

```text
{{ $json.keys().includes('email') }}
```

`keys()` only ever lists keys the item actually carries — inherited names never appear in it — so `includes()` answers the question `hasField()` was supposed to answer. The dynamic form works the same way:

```text
{{ $json.keys().includes($json.fieldName) }}
```

Here is what each part does: `$json.keys()` builds the array of the item's real field names, and `.includes(...)` returns `true` only when the name you pass is in that array. A field name of `toString` arriving from upstream data now correctly returns `false` unless the item truly has a `toString` key. You should see the expression preview flip to `false` for items missing the field, where `hasField()` showed `true`.

> **Note:** Do not substitute a value check like `{{ $json.email !== undefined }}` and call it equivalent. A field that is present but set to `undefined` — or, with a looser check, `null`, `0`, or `''` — is still a field the item carries, and presence checks in validation logic usually need to distinguish "absent" from "present but empty". The keys-membership test preserves that distinction; a value comparison does not.

### Step 2 - Use an own-property check inside Code nodes

In a Code node you have full JavaScript, so use the direct own-property test:

```javascript
const hasOwnField = (obj, field) => Object.hasOwn(obj, field);

return $input.all().map((item) => ({
  json: {
    ...item.json,
    hasEmail: hasOwnField(item.json, 'email'),
  },
}));
```

`Object.hasOwn(obj, field)` returns `true` only when `field` is an own property of `obj` — inherited names return `false`. It is the modern replacement for `Object.prototype.hasOwnProperty.call(obj, field)`, which does the same job and works in older runtimes; either is correct here. Write the helper once at the top of the Code node and reuse it for every presence check in that node, so the next person editing the workflow does not reintroduce the `in` operator by habit.

### Step 3 - Audit existing workflows for always-true guards

Any workflow that already uses `hasField()` with a literal inherited name — or with a dynamic argument — has a guard that has been answering `true` unconditionally. Export the workflow JSON (Workflow menu → Download, or `GET /api/v1/workflows/<id>` with your API key) and search it:

```bash
grep -o "hasField([^)]*)" workflow.json | sort | uniq -c
```

Every match with a literal argument of `toString`, `constructor`, `hasOwnProperty`, `valueOf`, `toLocaleString`, `isPrototypeOf`, or `propertyIsEnumerable` is a broken guard — replace it using Step 1 or Step 2. Every match with a non-literal argument (a variable, `$json.something`, a template) is a guard that breaks whenever the runtime value lands on one of those names — replace those too; the keys-membership test costs nothing and is correct for all names, inherited or not. Matches with ordinary literal names like `hasField('email')` are answering correctly today, but swapping them to the same pattern keeps the workflow safe if the field name is ever made dynamic later.

## Verify it worked

Run three checks in the expression editor of any node. First, the empty-object case that exposed the bug:

```text
{{ ({}).keys().includes('toString') }}
```

You should see `false` — where `hasField('toString')` returned `true`. Second, the genuine-field case, which must still answer `true`:

```text
{{ ({ toString: 'custom' }).keys().includes('toString') }}
```

Third, a real item from your workflow: pick an execution where the guarded field is absent and confirm the expression preview shows `false` and the IF node now takes the false branch. If all three behave, the guard is reading the item's real fields again. One more sanity check worth doing: an item whose field is present with a falsy value — `count: 0` or `email: ''` — should still return `true` from the keys test, because the field exists. That is the behavior a presence check owes you, and it is the behavior `hasField()` promised.

## Prevent it next time

Treat `hasField()` as unsafe for any name you do not control, and prefer the own-keys pattern as the default presence check in new workflows: `$json.keys().includes('name')` in expressions, `Object.hasOwn()` in Code nodes. The pattern is immune to the whole class of prototype-chain surprises, not just the names listed here — including `__proto__` and the `__defineGetter__` family, which `in` also matches. When the upstream fix lands (the issue is open with no fixed version as of 2026-11-25), `hasField()` should become safe again, but there is no reason to switch back: the own-keys check says exactly what it means. If you maintain shared workflow templates or a team style guide, add one line to it — presence checks test own keys, never `in` — and the bug class stays closed even as new people copy old expressions into new workflows.

## Key Takeaways

1. **n8n's `hasField()` uses the `in` operator**, so it returns `true` for inherited names — `toString`, `constructor`, `hasOwnProperty` — on every item, even empty ones (GitHub #43964, open as of 2026-11-25).
2. **Ordinary field names are unaffected**; the false positives hit literal inherited names and, more dangerously, dynamic field names arriving from upstream data.
3. **Replace it with an own-keys test**: `{{ $json.keys().includes('email') }}` in expressions, `Object.hasOwn(obj, field)` in Code nodes — both verified to answer `false` for inherited names and `true` for real fields, including falsy-valued ones.
4. **Audit what you already shipped**: export workflow JSON and grep for `hasField(` — inherited literals and dynamic arguments are guards that have been silently always-true.

Next: if your guards have been taking the wrong branch, check what those executions actually did downstream before you move on — a presence check stuck on `true` often means records were written, messages sent, or approvals granted for items that should have been skipped. For the broader set of silent-failure patterns in self-hosted n8n, see our [self-hosted silent failures checklist](/blog/n8n-self-hosted-silent-failures-checklist/).
