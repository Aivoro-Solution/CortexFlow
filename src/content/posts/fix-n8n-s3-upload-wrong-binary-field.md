---
title: "Fix n8n S3 Node Uploading the Wrong File When Items Use Different Binary Field Names (GH #44299)"
description: "Your n8n S3 node uploads the wrong file when items use different binary field names — it reads the field name from item 0. Here's the fix."
date: 2026-11-18
category: automation
tags: ["n8n", "s3", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-s3-upload-wrong-binary-field.webp"
---

You upload two files to S3 through n8n. The first object lands in the bucket with the right content. The second one either fails with "no binary data property 'data' does not exist on item" — or worse, uploads the *first* file's bytes under the second file's key. You check the field name, you check the binary tab, everything looks correct. Run it again. Same wrong file, same error.

This is a confirmed bug in n8n, filed as [GitHub issue #44299](https://github.com/n8n-io/n8n/issues/44299) on November 17, 2026 (team-assigned, Linear GHC-9802, still open as of November 18, 2026). The S3 node's File Upload operation reads the binary field name from **item 0 for every item**, even when the expression you wrote resolves to a different field name for each item. By the end of this article you will know how to confirm you have hit this exact bug, fix it with a one-node workaround, and verify each object in the bucket is the file it was supposed to be.

Quick definitions before we start: **binary data** in n8n is file content attached to an item, separate from its JSON — each binary file lives under a **binary property name** (a key like `data` or `attachment`). The **S3 node** is n8n's node for S3-compatible storage — MinIO, DigitalOcean Spaces, Wasabi, and any other service that speaks the S3 API. Its **File > Upload** operation with **Binary File** turned on takes an **Input Binary Field** parameter telling it which binary property holds the file to upload, and it accepts an expression such as `{{ $json.field }}` that can resolve to a different name per item. An **item index** is the position of an item in the list the node is processing — item 0 is the first, item 1 the second, and so on.

## The symptom: item 2 uploads item 1's file — or errors

The failure needs two ingredients: more than one input item, and a binary field name that differs between items. A typical setup is a batch that pulls files from different sources — item 1 carries its file under `data`, item 2 under `attachment` — with Input Binary Field set to an expression that picks the right name per item:

```
{{ $json.field }}
```

with `field` equal to `data` on item 1 and `attachment` on item 2. What happens:

- **If item 2 also has a binary property named `data`** (say, a thumbnail or an earlier download), the node silently uploads *that* file to item 2's key. The execution reports success. The wrong bytes go into the bucket, and nothing in the run tells you.
- **If item 2 has no property named `data`**, the node fails with an error along the lines of `no binary data property "data" does not exist on item` — even though the file you wanted is sitting in the input under `attachment`.

**How to tell this bug apart from a misconfigured field name.** If the field name were simply wrong, every item would fail the same way. Here only items after the first misbehave, and the name in the error is always item 1's field name, never the current item's. That pattern — first item fine, later items reading the first item's field — is the fingerprint. If all your items use the *same* binary property name, you do not have this bug: the index-0 lookup and the current-item lookup return the same name.

## The root cause: the field name is hard-coded to index 0

The reporter found this by reading the source on master, in `packages/nodes-base/nodes/S3/S3.node.ts`. The upload branch loops over all input items, but reads the field name with a hard-coded 0:

```ts
this.getNodeParameter('binaryPropertyName', 0)
```

The binary data lookup immediately below it already uses the current item index `i` — `this.helpers.assertBinaryData(i, binaryPropertyName)` and `this.helpers.getBinaryDataBuffer(i, binaryPropertyName)`. So for item 1, the node asks for item 1's binary data, but with item 0's field name. The inconsistency is what makes this a bug rather than a design choice: every other parameter in the same operation (`bucketName`, `fileName`, `binaryData`, `additionalFields`, `tagsUi`, `fileContent`) already uses the current item index, and so does the **Download** operation in the same file. Only the upload's binary field name is stuck on 0.

Two details from the issue narrow the blast radius. First, the separate **AWS S3 node** (`AwsS3V2`) already reads this parameter with the current item index — only the S3-compatible node is affected, so if your bucket is on AWS itself, switching nodes dodges the bug entirely. Second, the reporter verified the defect with a unit test using two items with different binary field names: the test fails without the fix and passes with it. The reporter opened [PR #44302](https://github.com/n8n-io/n8n/pull/44302) the same day — a one-line change plus a regression test in `nodes/S3/__tests__/S3.node.operation.test.ts` (all 10 tests pass with the fix). Until that fix ships in a release you run, the workarounds below are the way through.

<figure class="shot">
  <img src="/figures/fix-n8n-s3-upload-wrong-binary-field-selector-dial.svg" alt="Isometric index-0 selector dial machine: a stamping press whose rotary field-name selector is locked at 0, stamping item 1's label data onto both parcels on a conveyor; item 2's own attachment tag lies unread beside it, and a lit orange lever is the rename fix" loading="lazy" />
  <figcaption>The index-0 selector dial, as a machine. The press's rotary selector is locked at <code>0</code> — the <code>getNodeParameter('binaryPropertyName', 0)</code> call in <code>S3.node.ts</code> — so it stamps item 1's label, <code>data</code>, onto both parcels, even though item 2's own tag reads <code>attachment</code> and lies unread beside it. <strong>Notice:</strong> the orange lever is the fix — rename every item's binary key to one fixed name (<code>attachment</code>) in a Code node before the S3 node, and the stuck-at-0 read no longer matters. The Download operation in the same file and the separate AWS S3 node already read the current item index, which is how you know only this upload read is broken (GH #44299).</figcaption>
</figure>

## Step 1 - Confirm you have this exact bug

Before changing anything, run the two-item test so you are not chasing a different upload problem (S3 upload errors have several unrelated causes, from endpoint and credential issues to bucket policies).

1. Build a minimal workflow: a Code node that emits two items, each with a different binary field name — item 1 with `data`, item 2 with `attachment` — and a `field` JSON value matching each name.
2. Add the S3 node, resource **File**, operation **Upload**, with **Binary File** turned on, Input Binary Field set to `{{ $json.field }}`, and a valid bucket and key per item.
3. Run it. If item 2 errors with `no binary data property "data" does not exist on item`, or uploads the file from `data` instead of `attachment`, you have this bug.

If instead every item fails with the same field name, or the error mentions credentials, endpoints, or access denied, you have a different problem — check the S3 credential and bucket permissions first.

## Step 2 - Fix it: give every item the same binary field name (recommended)

The bug only bites when the field name varies per item. Remove the variation and the index-0 lookup returns the right file for every item. The cleanest way is a Code node set to **Run Once for Each Item** immediately before the S3 node, which renames each item's binary key to one fixed name:

```js
const item = $input.item;

// Rename whatever binary key this item has to one fixed name
const key = Object.keys(item.binary)[0];
item.binary = { attachment: item.binary[key] };

return item;
```

Then set the S3 node's Input Binary Field to the static text `attachment` — no expression. Now the node reads `attachment` for item 0, item 1, item 47: the lookup is identical for every item, so the hard-coded 0 no longer matters.

Two refinements if your items carry more than one binary file:

- Don't blindly take `Object.keys(item.binary)[0]` — pick the key explicitly, for example from a JSON field: `item.binary = { attachment: item.binary[item.json.field] };`
- Guard against items with no binary data at all, or the rename throws: `if (!item.binary || !Object.keys(item.binary).length) return item;` and let a downstream IF node route empty items away from the S3 node.

If you would rather avoid code, the **Edit Fields (Set) node** now supports a binary data type: add a field of type binary, reference the original binary property, and give it the fixed name `attachment`. Same result, no JavaScript — but you still need one rename per upstream source if the names differ before the merge point, so the Code node is usually the shorter path.

## Step 3 - Alternative fix: process one item at a time with SplitInBatches

If renaming feels too invasive, force the node to see only one item per run. Put a **SplitInBatches** node before the S3 node with **Batch Size** set to `1`, and loop its output back through the S3 node. With a single item in each batch, item 0 *is* the current item, and the expression resolves correctly.

This works, but it costs you: one execution per item instead of one execution for the batch, plus the loop wiring. Use it when you cannot touch the binary keys — for example when a later node needs the original names — and use the rename fix when you can.

## Step 4 - Alternative fix: use the AWS S3 node instead

If your bucket is on AWS itself, the simplest fix is to stop using the S3-compatible node altogether. The separate **AWS S3 node** (`AwsS3V2`) reads the binary field name with the current item index already, so the same expression works correctly there with no workaround at all. Swap the node, point it at the same bucket and key, and keep your per-item expression.

This only helps on real AWS. If your bucket is on MinIO, DigitalOcean Spaces, Wasabi, or another S3-compatible service, the AWS S3 node is not an option — use the rename fix in Step 2.

## Step 5 - Verify each object in the bucket is the right file

Don't trust the green checkmark: the silent wrong-file case reports success. Verify at the destination, not in the editor.

1. Re-run the two-item test from Step 1 with the fix in place.
2. Download each object from the bucket (or list it with `aws s3 ls` / your provider's console) and confirm the content matches the file that item was supposed to carry — not item 1's file under both keys.
3. For a production workflow, add a one-time assertion: after the S3 node, an IF node that checks the uploaded object's size or ETag against the expected value from `$json`, and routes mismatches to a notification instead of letting them sail through silently.

Once the upstream fix lands, the regression test in PR #44302 — both items uploading with their own field names — is the definitive check. Until then, the bucket check is yours.

## Prevent it next time

- **Standardize binary property names across a workflow.** Pick one name — `data` is the n8n default — and make every node that produces a file use it. The bug, and a whole family of binary-name mistakes, disappears when names never vary.
- **Never use a per-item expression for Input Binary Field** in the S3 node's Upload operation until the fix ships in a release you run. A static name is immune to this bug.
- **Treat "first item works, later items don't" as an index bug until proven otherwise.** In n8n, any parameter that resolves per item but is read at index 0 will show exactly this shape — and the same class of bug has already bitten the Microsoft Outlook node's Add Attachment operation ([GH #44021](https://github.com/n8n-io/n8n/issues/44021)).
- **Check the sibling operation and the sibling node.** When a node has two operations that do similar things, compare them: here Download was already correct, which told the reporter — and tells you — exactly where the defect lives. And when two nodes do similar things, compare those too: the AWS S3 node was already correct, which is both a diagnostic clue and a ready-made workaround.

## FAQ

### Which n8n versions are affected?

The bug was reported against current master on November 17, 2026, and the S3-compatible node's upload branch is the current code, so every 2.x release carrying it is affected. There is no fixed version yet — the issue is team-assigned (Linear GHC-9802) with PR #44302 open, so watch the release notes for GH #44299.

### Does this affect the AWS S3 node too?

No. The AWS S3 node (`AwsS3V2`) already reads the binary field name with the current item index. Only the S3-compatible node (`S3.node.ts`, used for MinIO, DigitalOcean Spaces, Wasabi, and other S3-API services) is affected.

### Does this affect S3 downloads as well?

No. The Download operation in the same node already reads the field name with the current item index. Only File > Upload with Binary File turned on is affected.

### Why does the execution report success when the wrong file is uploaded?

Because the node did exactly what its code says: it read the field name from item 0 and uploaded the file it found. From the node's point of view nothing failed. The wrongness lives in which file was selected, and n8n has no way to know that was not the file you meant. That is why the verification step checks the object in the bucket, not just the green checkmark.

### Is the Code-node rename safe for the file contents?

Yes — renaming a binary key only changes the dictionary key; the file bytes, MIME type, and filename metadata travel with the value unchanged. You are moving a pointer, not re-encoding the file.

## Conclusion

The S3 node's File Upload operation reads the binary field name from item 0 for every item, so any workflow where the field name varies per item uploads the wrong file or fails outright. Rename every item's binary key to one fixed name before the S3 node — or run items one at a time through SplitInBatches, or switch to the AWS S3 node if your bucket is on AWS — and verify the object in the bucket, not just the green checkmark. The upstream fix is tracked in [GH #44299](https://github.com/n8n-io/n8n/issues/44299); until it ships, a static field name is the durable defence.

Related reading: the same index-0 bug class in another node — [Fix n8n Outlook 'Add Attachment' Attaching the Wrong File](/blog/fix-n8n-outlook-add-attachment-wrong-binary-field/) — and other silent per-item traps in [Fix n8n SplitInBatches Loop Ending Early — Execution Reports "Success" but Items Are Missing](/blog/fix-n8n-splitinbatches-loop-ends-early/).
