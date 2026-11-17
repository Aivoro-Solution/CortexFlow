---
title: "Fix n8n SharePoint Node 500 Error on Multi-Choice Columns (GH #44139)"
description: "The n8n SharePoint node fails with a 500 error on multi-select Choice columns. Here's the HTTP Request workaround with the Graph fix."
date: 2026-11-17
category: automation
tags: ["n8n", "microsoft-sharepoint", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-sharepoint-multi-choice-500-error.webp"
---

You build a workflow that logs campaign activities to a SharePoint list. The list has a Choice column called Activities with "Allow multiple selections" turned on. You wire up the Microsoft SharePoint node, Resource **Item**, Operation **Create**, fill in the columns — and the node fails with `Microsoft Graph rejected the request (HTTP 500)`. The error message tells you to check the operation's inputs and the app registration's permissions, so you spend an hour re-checking permissions that were never the problem. The same credential, the same list, the same column work fine when you call Microsoft Graph directly.

This is a confirmed bug in n8n, filed as [GitHub issue #44139](https://github.com/n8n-io/n8n/issues/44139) on November 16, 2026 (team-assigned, still open as of November 17, 2026). The SharePoint node sends a multi-choice column value as a plain string. Microsoft Graph requires that value as an **array of strings, plus a sibling annotation** telling it the value is a collection — and without the annotation Graph answers with a bare 500. By the end of this article you will know how to confirm you have hit this exact bug, route multi-choice writes through the HTTP Request node, and verify the values land in the list.

Quick definitions before we start: a **Choice column** in SharePoint is a dropdown-style column with a fixed set of options; when **"Allow multiple selections"** is on, an item can hold several options at once — that is a **multi-choice column**. The **Microsoft SharePoint node** in n8n talks to SharePoint through the **Microsoft Graph API** (Microsoft's REST API for Microsoft 365 data), using an app registration in Entra ID (formerly Azure AD) for authentication. A column's **internal name** is the name SharePoint stores in its schema — it is not always the same as the display name you see in the list settings, and it is the name Graph expects in request bodies.

## The symptom: a bare 500 on Create and Update, only for multi-choice columns

The failure needs one ingredient: a Choice column with multiple selections enabled, included in the columns you send. A typical setup is a list with a Title column plus an Activities column offering "Workshop", "Webinar", and "Conference", with the SharePoint node set to Resource **Item**, Operation **Create** (or **Update**), and the Activities value sent as a string under Columns to Send. The node fails with:

```
NodeApiError: Microsoft Graph rejected the request (HTTP 500).
Check the operation's inputs and the app registration's permissions.
```

The stack trace in the issue points at the Create operation in `packages/nodes-base/nodes/Microsoft/SharePoint/v2/actions/item/create.operation.ts`, called through the node's Graph transport in `transport/index.ts` — the 500 comes back from Graph itself, not from n8n's own validation.

**How to tell this bug apart from a permissions problem.** The error text points at the app registration, but the reporter verified the same app registration succeeds immediately when the same data is sent through an HTTP Request node pointed directly at Graph. A real permissions failure returns **403**, not 500, and it fails for every column, not just multi-choice ones. The fingerprint of this bug is narrower: single-choice columns and text columns in the same list, through the same node and the same credential, work fine. Only the multi-select Choice column fails — and it fails on both Create and Update.

## The root cause: Graph needs an array plus a type annotation the node never sends

For a single-choice column, a plain string is exactly what Graph expects — `"Activities": "Workshop"` — which is why single-select columns work through the node. For a multi-choice column, Graph expects two things in the `fields` object: the value as an **array of strings**, and a **sibling property** named `<ColumnInternalName>@odata.type` with the value `"Collection(Edm.String)"`:

```json
{
  "fields": {
    "Title": "Q4 campaign retrospective",
    "Activities": ["Workshop", "Webinar"],
    "Activities@odata.type": "Collection(Edm.String)"
  }
}
```

The `@odata.type` annotation is what tells Graph the array is a collection of strings rather than a single value. Without it, Graph cannot interpret the field and answers with a 500 that carries no detail — which is why the failure looks like a server problem instead of a malformed request. The n8n SharePoint node composes the request body from the Columns to Send values without adding that annotation (and without sending an array), so every multi-choice write is malformed before it leaves n8n. The expected behaviour, as the issue puts it, is that the node should "detect that the target column is a multi-choice collection and automatically compose the request" — until it does, the fix is to compose the request yourself.

This pattern is documented outside n8n as well: Microsoft's own Q&A answer for creating a list item with a multi-select Choice column gives the same `@odata.type` annotation, and independent Graph guides show the identical shape for both creating and updating items. The fix below is the reporter's verified workaround, cross-checked against those sources.

## Step 1 - Confirm you have this exact bug

Before rebuilding anything, run the one-minute test so you are not chasing a different SharePoint problem (there are several unrelated ones, from app-registration consent to site permissions).

1. In the same list, create an item through the SharePoint node using only single-choice and text columns — leave the multi-choice column out. It should succeed.
2. Add the multi-choice column back with any value. If the node now fails with the HTTP 500 above, you have this bug.
3. If step 1 also fails, check the app registration first: a 403 means permissions, a 401 means the credential itself. This article's fix will not help those.

If the column is single-choice, you do not have this bug at all — the node handles those correctly. And if your list has no multi-choice column, none of this applies.

## Step 2 - Find the site ID, list ID, and the column's internal name

The direct Graph calls need three identifiers. You can fetch all three with Graph Explorer (Microsoft's browser tool for Graph) or with an HTTP Request node using the same Microsoft SharePoint credential — either way, do this once and store the values.

**Site ID.** For a site at `https://contoso.sharepoint.com/sites/Marketing`:

```http
GET https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/Marketing
```

The response's `id` is the site ID (a long composite string). For the root site, `GET https://graph.microsoft.com/v1.0/sites/root` works instead.

**List ID.** With the site ID in hand:

```http
GET https://graph.microsoft.com/v1.0/sites/{site-id}/lists?$filter=displayName eq 'Your List Name'
```

Take the `id` of the matching list.

**Column internal name.** This is the step people skip, and it is the one that breaks the workaround:

```http
GET https://graph.microsoft.com/v1.0/sites/{site-id}/lists/{list-id}/columns
```

Find your Choice column in the response. Its `name` field is the internal name Graph expects as the JSON key, and its `choice.allowMultipleSelections` field confirms it is a multi-choice column. The internal name is often the same as the display name — `Activities` stays `Activities` — but if the display name contains spaces, SharePoint encodes them: a column displayed as "Project Tags" has the internal name `Project_x0020_Tags`. Using the display name as the key silently writes nothing, or errors, so check the response rather than guessing.

> **Note:** the values you send must be options actually defined on the column. A value that is not one of the column's defined choices is rejected by Graph — check the spelling against the column definition, including case, before blaming the request shape.

## Step 3 - Create items with the HTTP Request node

Replace the SharePoint node with an **HTTP Request** node for every write that includes a multi-choice column. (You can keep the SharePoint node for reads and for writes that touch only text, number, and single-choice columns.)

1. Add an **HTTP Request** node. Set **Method** to `POST` and **URL** to:
   ```
   https://graph.microsoft.com/v1.0/sites/{site-id}/lists/{list-id}/items
   ```
   with your site ID and list ID from Step 2.
2. Set **Authentication** to **Predefined Credential Type**, choose **Microsoft SharePoint OAuth2 API**, and select the same credential the SharePoint node uses. The app registration needs `Sites.ReadWrite.All` (or `Sites.Manage.All`) for writes — if you get a 403 here, that is the one place permissions actually matter.
3. Set **Send Body** on, **Body Content Type** to **JSON**, **Specify Body** to **Using JSON**, and paste a body in this shape:

```json
{
  "fields": {
    "Title": "Q4 campaign retrospective",
    "Activities": ["Workshop", "Webinar"],
    "Activities@odata.type": "Collection(Edm.String)"
  }
}
```

Here is what each part does:

- **`fields`** — the wrapper Graph requires for item creation. Every column value lives inside it.
- **`Title`** — an ordinary text column, sent as a plain string, exactly as the SharePoint node would send it.
- **`Activities`** — the multi-choice column, sent as an **array** of the selected options. Send every selected option, in any order.
- **`Activities@odata.type`** — the sibling annotation, with the column's **internal name** before the `@`. This is the piece the SharePoint node never sends, and the piece that turns the 500 into a 201. The value is always the literal string `Collection(Edm.String)` for a multi-choice text column.

If the values come from upstream items, build the body with an expression instead of hard-coding it. With the HTTP Request node's JSON body set to expression mode:

```js
={{ {
  fields: {
    Title: $json.title,
    Activities: $json.activities,
    "Activities@odata.type": "Collection(Edm.String)"
  }
} }}
```

where `$json.activities` is already an array of option strings (for example `["Workshop", "Webinar"]`). If your upstream data holds a single string, wrap it first — a Code node with `Activities: [ $json.activity ]` — because Graph rejects a bare string for a multi-choice column just as surely as the node's version does.

Run the node. A successful create returns **201 Created** with the new item, including its `id` — save that ID if you later need to update the same item.

> **Warning:** the issue text itself contains a typo in the workaround URL — `https://microsoft.com{site-id}/...` — which is missing the `graph.` subdomain and the `/v1.0/sites/` path. The correct base is `https://graph.microsoft.com/v1.0/sites/{site-id}/lists/{list-id}/items`, as verified against Microsoft's Graph documentation and the independent guides linked below. Copy the URL from Step 3, not from the issue body.

## Step 4 - Update items the same way, with PATCH

Updates use a different endpoint and a slightly different body shape. To change the multi-choice value of an existing item, use **Method** `PATCH` against the item's `fields` endpoint:

```
https://graph.microsoft.com/v1.0/sites/{site-id}/lists/{list-id}/items/{item-id}/fields
```

with the body sent **without** the `fields` wrapper — the endpoint already addresses the field set directly:

```json
{
  "Activities": ["Workshop", "Conference"],
  "Activities@odata.type": "Collection(Edm.String)"
}
```

Two things to know about updates:

- **PATCH replaces the whole multi-choice value.** Options you leave out are removed from the item. Always send the complete set of selected options, not just the one you are adding — read the current value first if you need to append rather than replace.
- **The same annotation is required.** The `/fields` endpoint needs the `@odata.type` sibling just like the create endpoint does; leaving it out produces the same class of failure.

You can keep using the SharePoint node's Update operation for items whose multi-choice columns you are not touching — the bug only fires when a multi-choice value is part of the write.

## Step 5 - Verify the values landed

Do not trust the green checkmark alone: a 201 only proves Graph accepted the request. Confirm the stored value matches what you sent.

1. Read the item back with a GET (same credential, HTTP Request node or Graph Explorer):
   ```
   GET https://graph.microsoft.com/v1.0/sites/{site-id}/lists/{list-id}/items/{item-id}?$expand=fields($select=Title,Activities)
   ```
   The response's `fields.Activities` should be the array you sent.
2. Open the item in the SharePoint list UI and confirm the multi-choice column shows all selected options.
3. For a production workflow, add a one-time assertion after the HTTP Request node: an IF node that checks the create response's `fields.Activities` contains every option you sent, and routes mismatches to a notification instead of letting a half-written item sail through silently.

## Prevent it next time

- **Keep multi-choice writes on the HTTP Request node until the fix ships.** The issue is team-assigned (status:in-linear) with no fixed version yet as of November 17, 2026. Watch [GH #44139](https://github.com/n8n-io/n8n/issues/44139) in the release notes; when a release lists it as fixed, re-test the SharePoint node with a multi-choice column before switching back.
- **Always use the column's internal name in Graph bodies.** Display names with spaces become `_x0020_` internally, and Graph silently ignores a key it does not recognise. The columns GET in Step 2 is the source of truth — run it once per list and keep the mapping with the workflow.
- **Pre-flight the column type.** If a workflow writes to lists you do not control, check `choice.allowMultipleSelections` from the columns GET before choosing the node: multi-choice goes through the HTTP Request node, everything else can stay on the SharePoint node.
- **Treat a bare Graph 500 as a malformed payload until proven otherwise.** Graph's 500 for this bug carries no detail, and n8n's error text points at permissions. When the same credential succeeds against the same list through a direct call, the payload — not the permission — is wrong.

## FAQ

### Which n8n versions are affected?

The bug was reported on n8n 2.45.6 (Node 24, PostgreSQL, self-hosted Docker), and the reporter lists both the v1 and v2 SharePoint nodes as affected. There is no fixed version yet — the issue is team-assigned and still open as of November 17, 2026.

### Is this a permissions problem with my app registration?

No. The reporter confirmed the same app registration succeeds immediately via a direct Graph call, and a real permissions failure returns 403, not 500. Make sure the registration has `Sites.ReadWrite.All` (or `Sites.Manage.All`) for writes, then stop chasing permissions — the payload shape is the problem.

### Does this affect single-choice columns?

No. A single-choice column accepts a plain string, which is what the SharePoint node sends, so those writes work. Only Choice columns with "Allow multiple selections" enabled are affected.

### What about multi-value Person or Lookup columns?

They need the same kind of annotation but a different shape: a multi-value Lookup or Person column is written through its `<InternalName>LookupId` property as an array of integer IDs, annotated with `"Collection(Edm.Int32)"`. Same `@odata.type` idea, different type name — and the same advice applies: send the annotation or Graph will not interpret the value.

### Can I fix this without leaving the SharePoint node?

Not for multi-choice columns. The node composes the request body itself and gives you no way to add the `@odata.type` annotation, so there is no setting or expression inside the node that fixes it. The HTTP Request node is the workaround until the upstream fix ships. If multi-select is not truly needed, changing the column to single-choice in SharePoint list settings is a schema-side alternative — but that changes the list for every user of it, so prefer the HTTP Request route.

## Key Takeaways

1. **The SharePoint node sends multi-choice values as a plain string; Graph needs an array plus `"InternalName@odata.type": "Collection(Edm.String)"`** — without the annotation Graph answers with a bare 500.
2. **A 500 here is not a permissions problem** — the same credential works via a direct Graph call, and real permission failures return 403.
3. **Route multi-choice writes through the HTTP Request node**: POST to `/sites/{site-id}/lists/{list-id}/items` with the `fields` wrapper for creates, PATCH to `/items/{item-id}/fields` without it for updates.
4. **Use the column's internal name, not the display name** — spaces become `_x0020_`, and the columns GET endpoint is the source of truth.
5. **Verify at the destination, not the checkmark** — read the item back with `$expand=fields` and confirm the array stored.

Next: if your workflows hit other Microsoft-node traps, the same "node sends the wrong shape" class of bug bit the Outlook node too — see [Fix n8n Outlook "Add Attachment" Attaching the Wrong File](/blog/fix-n8n-outlook-add-attachment-wrong-binary-field/). And when a release lists GH #44139 as fixed, re-test the SharePoint node with a multi-choice column before moving writes back to it.
