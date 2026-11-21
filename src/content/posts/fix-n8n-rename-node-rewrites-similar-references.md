---
title: "Fix n8n Renaming a Node Silently Breaking References to Similarly-Named Nodes"
description: "Renaming a node in n8n rewrites $node references to nodes whose names start with the old one — Code1 becomes Transform1. Here's the cause and the fix."
date: 2026-11-21
category: automation
tags: ["n8n", "error-fix", "expressions", "workflow-editor"]
draft: false
featured: false
image: "/og/fix-n8n-rename-node-rewrites-similar-references.webp"
---

You rename a Code node to something clearer, and n8n helpfully rewrites every expression that referenced it. Except it rewrites one too many. Your `$node.Code1.json.x` — a reference to a *different* node, `Code1` — silently becomes `$node.Transform1.json.x`, a node that does not exist. The workflow keeps running, or fails in a place that looks unrelated, and nothing tells you the rename caused it. By the end of this post you will know exactly which reference syntax is safe, how to audit a workflow after any rename, and how to fix references that are already broken.

## The symptom: a rename rewrites a reference you never touched

The pattern is specific, which is what makes it so easy to miss. Build a workflow with two Code nodes — n8n names them `Code` and `Code1` by default — then add an Edit Fields (Set) node after them with a field whose value is:

```javascript
{{ $node.Code1.json.x }}
```

Now rename the first node from `Code` to `Transform`. Open the Edit Fields node and read the value again:

```javascript
{{ $node.Transform1.json.x }}
```

Nobody asked n8n to touch `Code1`. There is no node called `Transform1`, so the expression now points at nothing. The same thing happens with `CodeX` and `Code_old` — anything whose name starts with the old name gets rewritten. The reporter of [GitHub issue #44680](https://github.com/n8n-io/n8n/issues/44680) (opened 2026-11-20) reproduced it by running the exact function the editor calls on rename, `Workflow.renameNodeInParameterValue`, against n8n master (`37ee6b940e`):

```
"={{$node.Node12.data.value1}}"     -> "={{$node.NewName2.data.value1}}"
"={{$node.Node1_old.data.value1}}"  -> "={{$node.NewName_old.data.value1}}"
"={{$node.Node1.data.value1}}"      -> "={{$node.NewName.data.value1}}"   (correct)
```

Only the third line is the rename the user actually requested. The first two are collateral damage.

> **Note:** This is a silent-corruption bug, not a crash. The rename succeeds, the editor shows no warning, and the broken reference only surfaces later — when the expression evaluates to nothing or the execution fails downstream. If you renamed a node recently and a workflow started misbehaving, check this first.

## Root cause: the dot-notation pattern has no boundary after the old name

When you rename a node, the editor calls `useCanvasOperations.renameNode`, which calls `workflow.renameNode`, which rewrites every parameter value through `applyAccessPatterns` in `packages/workflow/src/node-reference-parser-utils.ts`. That function tries four access patterns, one per way of writing a node reference:

| Pattern | Example | Safe from this bug? |
| --- | --- | --- |
| `$('Name')` | `{{ $('Code1').first().json.x }}` | Yes — ends in a quote |
| `$node['Name']` | `{{ $node['Code1'].json.x }}` | Yes — ends in a quote |
| `$node.Name` | `{{ $node.Code1.json.x }}` | **No — this is the broken one** |
| `$items('Name')` | `{{ $items('Code1')[0].json.x }}` | Yes — ends in a quote |

The dot-notation pattern is the problem. In the source it reads:

```typescript
replacePattern: (s) => String.raw`(\$node\.)${s}(\.?)`,
```

Read it as a regular expression: match `$node.`, then the old name, then an optional dot. There is no check on what comes *after* the old name. So when the old name is `Code`, the pattern happily matches the first four characters of `$node.Code1` — the `1` is just an extra character the pattern never looks at — and replaces `Code` with `Transform`, leaving the `1` in place. The result is `Transform1`.

The other three patterns all end in a quote or a closing parenthesis, which acts as a natural boundary: `$('Code')` can only match the exact name `Code`, never `Code1`, because the closing quote has to follow immediately. Only dot notation lacks that boundary, and dot notation is the form n8n's expression editor suggests most often — and the form most people write by hand.

The default names make this easy to hit in real workflows. Two Code nodes are `Code` and `Code1`; two Wait nodes are `Wait` and `Wait1`; two HTTP Request nodes are `HTTP Request` and `HTTP Request1`. Any rename of the first node rewrites references to the second. Team member grinem confirmed the diagnosis in the issue thread (2026-11-20) and proposed the fix: a negative lookahead after the old name that rejects identifier continuations — letters, digits, `_`, and `$` — while still allowing the `.` that separates the node name from the property path. The fix is open as [PR #44681](https://github.com/n8n-io/n8n/pull/44681) ("fix(editor): Rename only exact dot-notation node references"), tracked internally as Linear GHC-9821. As of 2026-11-20 it is not merged and no fixed n8n version exists yet, so the workarounds below are the fix for now.

## Step 1 - Check whether a rename already broke your workflow

Before changing anything, find out if you are affected. The damage is invisible in the editor until you open the exact node, so audit the workflow JSON instead. Export the workflow (top-right menu → Download, or fetch it through the n8n API) and search for the renamed node's name followed by a digit, an underscore, or a letter:

```bash
# Search an exported workflow JSON for suspicious renamed references
# Replace Transform with the name you renamed TO
grep -o '\$node\.Transform[0-9A-Za-z_$]*' workflow.json | sort -u
```

You should see only `$node.Transform` — the node you actually renamed. If you see `$node.Transform1`, `$node.Transform_old`, or anything similar, those references are broken: they point at nodes that do not exist. Repeat the search for every node you have renamed recently.

> **Warning:** A broken reference does not always fail loudly. An expression pointing at a non-existent node can resolve to nothing and let the execution continue with empty data — the same silent-wrong-data shape as the `$('Code')` null bug covered in [Fix n8n $('Code') Expressions Resolving to null After Upgrading to 1.123.x](/blog/fix-n8n-code-node-expressions-resolve-null/). Check the data, not just the execution status.

## Step 2 - Repair the broken references

For each broken reference the search found, open the node that contains it and put the original node name back. In the example above, change `$node.Transform1.json.x` back to `$node.Code1.json.x` — the reference to the node that actually exists. Do this by hand, one expression at a time: a find-and-replace across the JSON risks the same prefix-matching mistake that caused the bug.

If you have many broken references, the safer bulk path is to edit the exported workflow JSON with a script that replaces only the exact broken string, then re-import it as a new workflow (never overwrite the original until you have verified the copy):

```bash
# Replace ONLY the exact broken reference — full string, not a prefix
python3 - <<'EOF'
import json

with open('workflow.json') as f:
    data = json.load(f)

text = json.dumps(data)
# One explicit replacement per broken reference you found in Step 1
text = text.replace('$node.Transform1', "$node.Code1")
data = json.loads(text)

with open('workflow-fixed.json', 'w') as f:
    json.dump(data, f, indent=2)
print('wrote workflow-fixed.json')
EOF
```

The `replace` call above matches the complete string `$node.Transform1`, so it cannot accidentally touch `$node.Transform12` or any other name. Import `workflow-fixed.json` as a new workflow, run it, and only then deactivate the old one.

## Step 3 - Stop it happening again: use the bracket forms

The permanent habit is to stop writing dot-notation node references. The `$('Name')` and `$node['Name']` forms are immune to this bug because their patterns end in a quote, so a rename can only ever match the exact name:

```javascript
// Vulnerable — a rename of "Code" rewrites this too
{{ $node.Code1.json.x }}

// Safe — the closing quote stops the match at the exact name
{{ $('Code1').first().json.x }}
{{ $node['Code1'].json.x }}
```

This is the same advice that applies to the paired-item and null-reference bugs in n8n expressions: `$('Name')` is the most robust way to reference another node, because it is explicit about which node you mean and it survives renames, duplication, and the editor's own rewriting. If you have a workflow full of `$node.Name` references, you do not need to rewrite them all today — but change the ones in workflows you rename often, and use the bracket form for every new reference you write.

Two more habits close the remaining gap. First, give nodes names that are not prefixes of each other: `ParseOrders` and `FormatEmail` can never collide, while `Code` and `Code1` collide by construction. Rename the default `Code1` to something descriptive the moment you add a second node of the same type. Second, after *any* rename, re-run Step 1's grep on the exported workflow before you activate it. Thirty seconds of searching beats an afternoon of debugging a workflow that started returning empty data for no visible reason.

## Verify it worked

Run the workflow end to end after the repair and check two things. First, the execution succeeds — a reference to a non-existent node fails or resolves to nothing, so a clean run with the expected data is the proof. Second, open the node you repaired and confirm the expression reads the original node name (`$node.Code1`, not `$node.Transform1`). If you used the bracket form in Step 3, confirm the expression reads `$('Code1')` or `$node['Code1']` — either form is immune to the next rename.

## What to watch for upstream

The fix itself is a one-line change to the dot-notation pattern — a negative lookahead `(?![a-zA-Z0-9_$])` after the old name, so the match only fires when the name is followed by a dot or the end of the reference. PR #44681 carries that change with a regression test covering the `Code` / `Code1` collision. Until it lands in a release, the bracket-form habit above is the complete defence: the bug lives in the editor's rename path, not in your workflows, so nothing you configure in n8n's settings can work around it. When you upgrade, check the release notes for #44681 — and still run Step 1's grep after your first rename on the new version, because that is the only way to be sure the fix made it into your build.

## FAQ

### Does this affect `$json` references too?

No. `$json` refers to the current node's own input items, not to a named node, so a rename never touches it. Only expressions that name another node — `$node.Name`, `$('Name')`, `$node['Name']`, `$items('Name')` — go through the rename rewriting, and of those only the dot-notation form is affected.

### I renamed a node and nothing broke. Was I lucky?

Probably you renamed a node whose name is not a prefix of any other node's name — for example renaming `SendEmail` when no other node is called `SendEmail1` or `SendEmail_old`. The bug only fires when another node's name starts with the old name. Default sequential names (`Code` / `Code1`, `Wait` / `Wait1`) are the common trigger, which is why the first rename in a workflow built from defaults is the dangerous one.

### Does this happen in n8n Cloud too?

The bug is in `packages/workflow`, the shared expression package used by every n8n build, so it is not specific to self-hosting. The reporter verified it at the package level on master; the editor behaviour is the same on Cloud and self-hosted until PR #44681 ships.

## Key Takeaways

1. **Renaming `Code` also rewrites `$node.Code1`** — the dot-notation rename pattern has no boundary after the old name, so any node whose name starts with it gets silently re-pointed at a node that does not exist.
2. **Audit after every rename** — export the workflow JSON and grep for the new name followed by a digit or underscore; a broken reference can resolve to nothing instead of failing loudly.
3. **Use `$('Name')` or `$node['Name']`** — the bracket forms end in a quote, so a rename can only match the exact name. They are immune to this bug.
4. **Give nodes non-prefix names** — `ParseOrders` and `FormatEmail` can never collide; `Code` and `Code1` collide by construction.
5. **The upstream fix is PR #44681** (Linear GHC-9821), not merged as of 2026-11-20 — until it ships in a release, the bracket-form habit is the defence.

Next: check your most-renamed workflows with the Step 1 grep today — the ones you built from default node names are the ones most likely to already carry a broken reference.
