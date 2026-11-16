---
title: "Fix n8n Outlook 'Add Attachment' Attaching the Wrong File (GH #44021)"
description: "Your n8n Outlook node attaches the wrong file when items use different binary field names — it reads the field name from item 0. Here's the fix."
date: 2026-11-16
category: automation
tags: ["n8n", "microsoft-outlook", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-outlook-add-attachment-wrong-binary-field.webp"
---

You send two emails through the Microsoft Outlook node. The first one arrives with the right attachment. The second one arrives with the *first* email's file — or the workflow fails with "No binary data property 'data' does not exist on item" even though the file is right there in the node's input. You check the field name, you check the binary tab, everything looks correct. Run it again. Same wrong file, same error.

This is a confirmed bug in n8n, filed as [GitHub issue #44021](https://github.com/n8n-io/n8n/issues/44021) on November 16, 2026 (team-assigned, Linear GHC-9780, still open as of November 16, 2026). The Outlook node's "Add Attachment" operation reads the binary field name from **item 0 for every item**, even when the expression you wrote resolves to a different field name for each item. By the end of this article you will know how to confirm you have hit this exact bug, fix it with a one-node workaround, and verify each message carries the right file.

Quick definitions before we start: **binary data** in n8n is file content attached to an item, separate from its JSON — each binary file lives under a **binary property name** (a key like `data` or `attachment`). The **Microsoft Outlook node** (v2) can add an attachment to an existing message with the resource **Message Attachment**, operation **Add**. Its **Input Data Field Name** parameter tells the node which binary property holds the file to attach, and it accepts an expression such as `{{ $json.field }}` that can resolve to a different name per item. An **item index** is the position of an item in the list the node is processing — item 0 is the first, item 1 the second, and so on.

## The symptom: item 2 attaches item 1's file — or errors

The failure needs two ingredients: more than one input item, and a binary field name that differs between items. A typical setup is a loop or a batch that downloads files from different sources — item 1 carries its file under `data`, item 2 under `attachment` — with Input Data Field Name set to an expression that picks the right name per item:

```
{{ $json.field }}
```

with `field` equal to `data` on item 1 and `attachment` on item 2. What happens:

- **If item 2 also has a binary property named `data`** (say, a thumbnail or an earlier download), the node silently attaches *that* file to item 2's message. The execution reports success. The wrong file goes out, and nothing in the run tells you.
- **If item 2 has no property named `data`**, the node fails with an error along the lines of `No binary data property "data" does not exist on item` — even though the file you wanted is sitting in the input under `attachment`.

**How to tell this bug apart from a misconfigured field name.** If the field name were simply wrong, every item would fail the same way. Here only items after the first misbehave, and the name in the error is always item 1's field name, never the current item's. That pattern — first item fine, later items reading the first item's field — is the fingerprint. If all your items use the *same* binary property name, you do not have this bug: the index-0 lookup and the current-item lookup return the same name.

## The root cause: the field name is hard-coded to index 0

The reporter traced this to one line in `packages/nodes-base/nodes/Microsoft/Outlook/v2/actions/messageAttachment/add.operation.ts`. In the Add Attachment operation, `messageId` and `options` are read with the current item's index — but `binaryPropertyName` is hard-coded to index 0. The issue's own reproduction makes it concrete: with the expression above, `execute` for index 1 calls `assertBinaryData(1, 'data')` when the field name for index 1 is `attachment`. The node asks for the binary data of item 1, but with item 0's field name.

The inconsistency is what makes this a bug rather than a design choice. The **Download Attachment** operation in the same folder already reads the field name with the current item index. Only Add Attachment is stuck on 0 — and the v1 Outlook node has the same hard-coded 0, so switching node versions does not help. The reporter reproduced it on master `53c9b488ae` (n8n 2.48.0) and supplied a failing regression test for `nodes/Microsoft/Outlook/test/v2/node/messageAttachment/add.test.ts`, offering to open a PR. Until that fix ships, the workarounds below are the way through.

## Step 1 - Confirm you have this exact bug

Before changing anything, run the two-item test so you are not chasing a different attachment problem (Outlook attachment errors have several unrelated causes, from draft-creation deserialization errors to Graph permission issues).

1. Build a minimal workflow: a Code node that emits two items, each with a different binary field name — item 1 with `data`, item 2 with `attachment` — and a `field` JSON value matching each name.
2. Add the Microsoft Outlook node, resource **Message Attachment**, operation **Add**, with Input Data Field Name set to `{{ $json.field }}` and a valid `messageId` per item.
3. Run it. If item 2 errors with `No binary data property "data" does not exist on item`, or attaches the file from `data` instead of `attachment`, you have this bug.

If instead every item fails with the same field name, or the error mentions deserialization (`UnableToDeserializePostBody`), you have a different problem — check the Graph permissions and the message ID first.

## Step 2 - Fix it: give every item the same binary field name (recommended)

The bug only bites when the field name varies per item. Remove the variation and the index-0 lookup returns the right file for every item. The cleanest way is a Code node set to **Run Once for Each Item** immediately before the Outlook node, which renames each item's binary key to one fixed name:

```js
const item = $input.item;

// Rename whatever binary key this item has to one fixed name
const key = Object.keys(item.binary)[0];
item.binary = { attachment: item.binary[key] };

return item;
```

Then set the Outlook node's Input Data Field Name to the static text `attachment` — no expression. Now the node reads `attachment` for item 0, item 1, item 47: the lookup is identical for every item, so the hard-coded 0 no longer matters.

Two refinements if your items carry more than one binary file:

- Don't blindly take `Object.keys(item.binary)[0]` — pick the key explicitly, for example from a JSON field: `item.binary = { attachment: item.binary[item.json.field] };`
- Guard against items with no binary data at all, or the rename throws: `if (!item.binary || !Object.keys(item.binary).length) return item;` and let a downstream IF node route empty items away from the Outlook node.

If you would rather avoid code, the **Edit Fields (Set) node** now supports a binary data type: add a field of type binary, reference the original binary property, and give it the fixed name `attachment`. Same result, no JavaScript — but you still need one rename per upstream source if the names differ before the merge point, so the Code node is usually the shorter path.

## Step 3 - Alternative fix: process one item at a time with SplitInBatches

If renaming feels too invasive, force the node to see only one item per run. Put a **SplitInBatches** node before the Outlook node with **Batch Size** set to `1`, and loop its output back through the Outlook node. With a single item in each batch, item 0 *is* the current item, and the expression resolves correctly.

This works, but it costs you: one execution per item instead of one execution for the batch, plus the loop wiring. Use it when you cannot touch the binary keys — for example when a later node needs the original names — and use the rename fix when you can.

## Step 4 - Verify each message got the right file

Don't trust the green checkmark: the silent wrong-file case reports success. Verify at the destination, not in the editor.

1. Re-run the two-item test from Step 1 with the fix in place.
2. Open each message in Outlook (or Sent Items) and confirm the attachment filename matches the file that item was supposed to carry — not item 1's file on both messages.
3. For a production workflow, add a one-time assertion: after the Outlook node, an IF node that checks the execution output's attachment name against the expected filename from `$json`, and routes mismatches to a notification instead of letting them sail through silently.

Once the upstream fix lands, the regression test in the issue — `assertBinaryData` called as `(1, 'attachment')` for item 1 — is the definitive check. Until then, the Sent Items check is yours.

## Prevent it next time

- **Standardize binary property names across a workflow.** Pick one name — `data` is the n8n default — and make every node that produces a file use it. The bug, and a whole family of binary-name mistakes, disappears when names never vary.
- **Never use a per-item expression for Input Data Field Name** in the Outlook Add Attachment operation until the fix ships in a release you run. A static name is immune to this bug.
- **Treat "first item works, later items don't" as an index bug until proven otherwise.** In n8n, any parameter that resolves per item but is read at index 0 will show exactly this shape — and the same class of bug has bitten other nodes before.
- **Check the sibling operation.** When a node has two operations that do similar things, compare them: here Download Attachment was already correct, which told the reporter — and tells you — exactly where the defect lives.

## FAQ

### Which n8n versions are affected?

The bug was reproduced on master `53c9b488ae` (n8n 2.48.0) and the v2 Add Attachment operation is the current one, so every 2.x release carrying this code is affected. The v1 Outlook node has the same hard-coded 0. There is no fixed version yet — the issue is team-assigned (Linear GHC-9780) with a PR offered by the reporter, so watch the release notes for GH #44021.

### Does this affect sending emails with attachments, or only adding attachments to existing messages?

Only the **Message Attachment → Add** operation, which attaches a file to an existing message by ID. The Send Message operation's attachment handling is a separate code path. If your send-mail attachments misbehave, check the field name and the binary tab first — that is a different problem.

### Why does the execution report success when the wrong file is attached?

Because the node did exactly what its code says: it read the field name from item 0 and attached the file it found. From the node's point of view nothing failed. The wrongness lives in which file was selected, and n8n has no way to know that was not the file you meant. That is why the verification step checks the attachment at the destination.

### Is the Code-node rename safe for the file contents?

Yes — renaming a binary key only changes the dictionary key; the file bytes, MIME type, and filename metadata travel with the value unchanged. You are moving a pointer, not re-encoding the file.

## Conclusion

The Outlook node's Add Attachment operation reads the binary field name from item 0 for every item, so any workflow where the field name varies per item attaches the wrong file or fails outright. Rename every item's binary key to one fixed name before the Outlook node — or run items one at a time through SplitInBatches — and verify the attachment in Sent Items, not just the green checkmark. The upstream fix is tracked in [GH #44021](https://github.com/n8n-io/n8n/issues/44021); until it ships, a static field name is the durable defence.

Related reading: if your workflows hit other silent per-item traps, see [Fix n8n SplitInBatches Loop Ending Early — Execution Reports "Success" but Items Are Missing](/blog/fix-n8n-splitinbatches-loop-ends-early/) and [Fix n8n "Cannot Resolve Paired Item" Errors](/blog/fix-n8n-cannot-resolve-paired-item/).
