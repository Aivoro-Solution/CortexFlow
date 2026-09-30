# Weekly Docs Check — Instructions

> Run once a week. Purpose: keep the blog's knowledge base current by detecting NEW or CHANGED content in the 6 watched doc sources, so new tutorials can be written while topics are fresh.

## 1. Sources to revisit

Read `~/workspace/blog/kb/baseline.json` first — it holds the last-known state for each source.

| # | URL to check | Canonical (use if the first redirects/404s) |
|---|---|---|
| 1 | https://docs.n8n.io | — |
| 2 | https://docs.n8n.io/advanced-ai/ | https://docs.n8n.io/build/integrate-ai/ (the original 404s — check the canonical) |
| 3 | https://docs.n8n.io/hosting/ | https://docs.n8n.io/deploy/host-n8n/ (original moved — check the canonical) |
| 4 | https://docs.docker.com | — (landing is a "What's new" feed; also scan the section families listed in baseline) |
| 5 | https://docs.docker.com/compose/compose-file/ | https://docs.docker.com/reference/compose-file/ (canonical path) |
| 6 | https://python.langchain.com/docs/concepts/ | https://docs.langchain.com (concepts moved here; legacy URL renders the overview) |

## 2. How to check each source

1. Fetch the URL with `browser_open`. Start from the landing/canonical page and scan the **docs navigation / sidebar / sitemap** for section and page titles.
2. Compare against the `sections` list for that source in `baseline.json`:
   - **New pages/sections** in the nav that aren't in the baseline → flag.
   - **Renamed, moved, or removed pages** → flag (note old vs new path).
   - **Version bumps**: check the changelog/release-notes page for each product:
     - n8n: `https://docs.n8n.io/changelog/release-notes.md` — compare latest version/date vs baseline `version`.
     - Docker/Compose: `https://docs.docker.com` "What's new" feed — new entries since last check.
     - LangChain: `https://docs.langchain.com` nav + migration notes — look for v1.x minor bumps or new concept pages.
3. For any flagged change, open the new/changed page and skim it (don't deep-read everything — capture: what it is, why it matters for tutorials, any version gotcha).
4. Watch especially for: **new node/feature pages in n8n AI docs**, **n8n major releases (3.0!) and breaking-change updates**, **new Compose spec fields**, **LangChain v1.x behavior changes**, and **deprecation notices** anywhere (these are tutorial hazards).

## 3. Output format

Produce a short report of **ONLY what's new/changed**. If nothing changed, say exactly: "No changes detected this week." Do not re-summarize the baseline.

Report format:

```
## Weekly docs check — <DATE>
### n8n core
- [NEW] <page title> — <one-line what it is + why it matters>
- [CHANGED] <page title> — <what changed>
### n8n AI (integrate-ai)
- ...
### n8n hosting
- ...
### Docker
- ...
### Compose file reference
- ...
### LangChain
- ...
### Version bumps
- n8n: 2.40 → 2.41 (2026-10-…)
- ...
```

Mark each item `[NEW]`, `[CHANGED]`, or `[REMOVED]`. Keep it to one or two lines per item.

## 4. After reporting

Update `baseline.json`:
- Set `checked` to today's date for every source checked.
- Update `version` where it changed.
- Add new section titles to the `sections` list (keep the existing ones).
- Note removed/renamed pages in the `note` field.

Also append a dated changelog entry to `~/workspace/blog/kb/knowledge-base.md` (a short "## Changelog" section at the bottom if it doesn't exist) describing anything that changes tutorial advice — e.g. a new deprecation, a renamed node, a new recommended pattern. Do NOT rewrite the whole knowledge base; only patch what changed.
