---
title: "Fix 'DOMMatrix is not defined' in n8n's PDF Extraction Node on Docker"
description: "n8n's Extract from File node failing with 'DOMMatrix is not defined' on PDFs after 1.98.0? The @napi-rs/canvas native binding is the fix. Full steps inside."
date: 2026-10-20
category: automation
tags: ["n8n", "pdf", "docker", "self-hosting", "error-fix"]
draft: false
featured: false
image: "/og/fix-n8n-docker-pdf-extraction-canvas.webp"
---

You updated your self-hosted n8n past version 1.98.0, ran a workflow that had been extracting text from PDFs for months, and got slapped with this:

```json
{
  "errorMessage": "DOMMatrix is not defined",
  "nodeName": "Extract from File",
  "nodeType": "n8n-nodes-base.extractFromFile",
  "operation": "pdf"
}
```

No retry helps, no PDF is the culprit (every file fails the same way), and — infuriatingly — the same workflow still runs fine on your older test instance. I dug into the forum threads, the GitHub issue, and the n8n Dockerfile to find the real root cause: a `pdfjs-dist` upgrade that quietly needs a browser API and a native canvas binding your Docker image may not ship. By the end of this article you'll know why it breaks and have four concrete fixes, ordered from "do this right now" to "never worry about it again."

Quick definitions so we're on the same page: the **Extract from File** node is n8n's built-in file-reading node — feed it a binary PDF and it pulls out the text. **pdfjs-dist** is the open-source JavaScript library (from Mozilla's PDF.js project) that actually parses the PDF pages. A **native binding** is a compiled binary module (like `@napi-rs/canvas`) that gives Node.js access to OS-level graphics APIs — Node.js doesn't ship a browser's canvas, so PDF rendering needs one bolted on.

## The symptom

The `Extract from File` node (operation: PDF) fails on every execution with `NodeOperationError: DOMMatrix is not defined`, originating from `pdf.operation.ts` in the n8n-nodes-base package. The failure is total — the node produces no output at all, just the error.

**The break started exactly at n8n 1.98.0**, and it hits self-hosted setups: Docker, npm installs, and (reported on 1.98.1) even n8n Cloud at the time. Versions 1.97.1 and earlier are unaffected. A community member later confirmed the error was gone on **1.100.1**, and the current 2.x Docker images ship the missing piece by default — so the fix you're about to apply is the same one the n8n team converged on.

## The root cause

In n8n 1.98.0, the team upgraded `pdfjs-dist` to a new major version (~5.3.31). That version of pdfjs-dist assumes it's running with browser-native APIs available — specifically `DOMMatrix` and a canvas implementation for page rendering. In a browser that assumption is free. In a server-side Node.js process inside a Docker container, neither exists.

That gap is what `@napi-rs/canvas` fills: it's a prebuilt native module that gives Node.js a working canvas API without a headless browser. n8n's own Docker build (`docker/images/n8n/Dockerfile`) installs it explicitly as "Canvas Support: PDF.js canvas rendering via `@napi-rs/canvas`." When your image predates that dependency — or you're on a version where the pdfjs-dist upgrade landed before the canvas dependency was wired up correctly — the import of `DOMMatrix` happens at module load, the binding isn't there to provide it, and every PDF extraction dies with the same cryptic one-liner.

Why does it surface as `DOMMatrix` rather than a missing-module error? Because pdfjs-dist references the global `DOMMatrix` at load time, and in Node.js an unresolved global throws a `ReferenceError` before you ever get to a meaningful message. The misleading part: nothing about "DOMMatrix" appears in your workflow, your PDF, or your config — it's a library-version mismatch wearing an error-message disguise.

## Prerequisites

- Self-hosted n8n on **Docker** (Compose or `docker run`), running 1.98.0 through 1.99.x where the error appears.
- Terminal access to the Docker host with permission to pull/recreate containers.
- About 10 minutes, and (for Fix 1) a stable internet connection to pull the new image.

## Fix 1 — Upgrade to a version that ships the canvas binding (recommended)

This is the official end state: n8n's newer Docker images install `@napi-rs/canvas` at build time, and a community member verified the error gone on 1.100.1. On 2.x it's bundled by default.

In your `docker-compose.yml`, change the image tag:

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:2.31.0
    # was: docker.n8n.io/n8nio/n8n:1.98.1 (or whatever broke)
```

Why the explicit tag instead of `:latest`? Because `:latest` is exactly how you got here — an unattended pull or a rebuild silently moved you from a working version to a broken one. Pinning the tag makes the version a deliberate decision, which Fix 4 reinforces.

Then recreate the container:

```bash
docker compose pull n8n
docker compose up -d n8n
docker logs n8n --tail 30
```

Why these commands, in order: `pull` fetches the new image, `up -d` recreates the container from it, and `logs --tail 30` confirms n8n booted cleanly ("Editor is now accessible via:" is the line you're looking for). Then run the workflow with a PDF — the Extract from File node should now return text instead of the `DOMMatrix` error.

> **Note:** If you use a custom Docker image that extends `n8nio/n8n` (e.g. one that adds Python/FFmpeg — see our guide on [running Python and FFmpeg inside Dockerized n8n](/blog/run-python-ffmpeg-dockerized-n8n/)), rebuild that image from the new base tag too. A stale custom image keeps the broken layer stack.

## Fix 2 — Pin back to 1.97.1 if you can't upgrade yet

Maybe you're mid-project, a plugin pins you to 1.9x, or you just need the workflows running in the next five minutes. The community-verified workaround is to **downgrade and pin to 1.97.1**, the last version whose older `pdfjs-dist` has no browser-API dependency at all.

```yaml
services:
  n8n:
    image: n8n.io/n8nio/n8n:1.97.1
```

```bash
docker compose pull n8n
docker compose up -d n8n
```

Why it works: 1.97.1's pdfjs-dist is the 3.x line, which was written for Node.js and never touches `DOMMatrix`. The PDF extraction code path in that version is identical for text PDFs, so your workflows behave the same.

> **Warning:** pinning backward re-introduces every bug fixed between 1.97.1 and your current version. One forum user reported their Information Extractor node (an LLM chain node) broke after the downgrade and had to be re-tuned by switching its LLM model. Treat 1.97.1 as a bridge, not a home — schedule the upgrade from Fix 1 as soon as your blockers clear.

## Fix 3 — Add the missing native binding to your own image

If you maintain a custom n8n image (for example, to add Python, FFmpeg, or system fonts), the broken state can persist even after you change the tag — the custom layers were built from an image whose canvas support didn't line up. You can install the binding explicitly.

Create (or extend) your Dockerfile:

```dockerfile
FROM docker.n8n.io/n8nio/n8n:2.31.0

USER root
# Install the native canvas binding pdfjs-dist needs for PDF rendering.
# @napi-rs/canvas ships prebuilt binaries, so no system build tools or
# cairo/pango dev libraries are required — unlike node-canvas.
RUN cd /usr/local/lib/node_modules/n8n \
 && npm install @napi-rs/canvas

USER node
```

Why each line matters: `FROM` must be a version whose image you trust (pin the tag per Fix 1's logic). `cd /usr/local/lib/node_modules/n8n` targets the actual n8n install path inside the container — that's where the `require('@napi-rs/canvas')` resolution happens at runtime. Installing it there means pdfjs-dist finds the binding on its module path. `USER node` switches back to the non-root runtime user the official entrypoint expects; forgetting it is the classic custom-image footgun (file permission errors on `/home/node/.n8n`).

Build and swap:

```bash
docker build -t my-n8n:fixed .
docker compose up -d n8n   # with image: my-n8n:fixed
```

Then verify with Fix 5 below. Note that `@napi-rs/canvas` downloads a prebuilt binary for your platform at install time — on ARM (Raspberry Pi, Graviton) make sure the build platform matches your runtime host, or Docker will fetch the wrong binary.

## Fix 4 — Pin versions in CI/CD so this never returns

The deeper disease: `docker compose up --build` or a deploy script that pulls `:latest` can re-break you on any future dependency bump. Make the version explicit everywhere.

- In `docker-compose.yml`: always a pinned tag, never `:latest`. Add a comment with the reason.
- In deploy scripts: replace `docker pull n8nio/n8n` with the pinned tag, and add a changelog review step — n8n publishes breaking changes at docs.n8n.io/hosting/installation/update.
- In staging: run a canary workflow containing one Extract from File PDF step before promoting an image to production. The failure mode is binary (every PDF fails), so one test file catches it.

## Verify the fix

After applying any of the fixes above, run this check:

1. Open the workflow, run the **Extract from File** node manually on a PDF binary.
2. You should see JSON output with the extracted text in the `text` field — no red error badge, no `DOMMatrix` mention.
3. For good measure, test a second PDF with scanned images vs. one with text: text PDFs extract directly; scanned ones need OCR regardless (that's a different feature, not this bug).

If the error persists after upgrading, you almost certainly have a stale custom image or a leftover container running the old tag — `docker ps` and check the image ID, then `docker image prune` the old one and recreate.

## Prevent it next time

- **Subscribe to the n8n releases page** ([github.com/n8n-io/n8n/releases](https://github.com/n8n-io/n8n/releases)) and skim the dependency-bump entries before upgrading production. This bug was announced as a routine `pdfjs-dist` bump.
- **Keep one regression workflow**: a 3-node flow (read test PDF → extract text → assert output isn't empty). Run it after every n8n update. Five minutes of setup catches this entire class of failure.
- **Watch for the same pattern elsewhere**: any n8n node whose underlying JS library assumes browser globals (`window`, `document`, `DOMMatrix`) can break the same way on Docker. When a node that "used to work" starts throwing `X is not defined` after an upgrade, check the library's changelog first — the answer is usually a version bump, not your workflow.

## FAQ

### Does this bug affect n8n Cloud?

It was reported on n8n Cloud 1.98.1 at the time, but Cloud runs the fixed image now, so current Cloud users aren't affected. This is primarily a self-hosted Docker problem — exactly the audience maintaining their own image tags.

### Is `DOMMatrix is not defined` ever caused by something else?

In n8n, no: every report traces to the pdfjs-dist 5.x upgrade. If you see it outside n8n (a Node.js script using pdfjs-dist directly), the same root cause applies — your pdfjs-dist version expects browser globals. Pin pdfjs-dist below 5.x or install `@napi-rs/canvas` in that project.

### Can I just use an OCR node or convert PDFs to images instead?

You can — some users worked around it by converting PDFs to images and sending them to an LLM — but it's a workaround with real costs: slower, more expensive per page, and worse on tables and multi-column layouts. Fix the binding and keep native text extraction.

### Will pinning to 1.97.1 break my other workflows?

Potentially. Anything added or fixed between 1.97.1 and your version regresses. The Information Extractor LLM node is the known casualty from forum reports. Audit your workflows on the downgraded version before trusting it in production.

## Key Takeaways

1. **`DOMMatrix is not defined` is a library-version mismatch, not a config error** — n8n 1.98.0 upgraded pdfjs-dist to 5.3.31, which needs browser APIs (`DOMMatrix`) and a canvas that don't exist in Node.js Docker containers.
2. **The real fix is the `@napi-rs/canvas` native binding** — present in n8n's newer official Docker images; upgrading to 1.100.1+ or current 2.x (Fix 1) resolves it.
3. **Pinning to 1.97.1 is the verified bridge** when you can't upgrade yet — but it re-opens older bugs, so treat it as temporary.
4. **Custom images need the binding installed at build time** (Fix 3) — `npm install @napi-rs/canvas` in `/usr/local/lib/node_modules/n8n`, and always switch `USER` back to `node`.
5. **Pin your image tags and keep a regression workflow** — `:latest` is how the broken bump reached you in the first place.

Next: if your Dockerized n8n also needs Python or FFmpeg alongside working PDF extraction, our guide on [running Python and FFmpeg inside Dockerized n8n](/blog/run-python-ffmpeg-dockerized-n8n/) shows the custom-Dockerfile pattern (with the `apk`-missing workaround) that pairs well with Fix 3 above.

*Fix verified via the [community.n8n.io thread](https://community.n8n.io/t/solution-workaround-dommatrix-is-not-defined-error-in-extract-from-file-pdf-node-on-n8n-v1-98-0/135568) documenting the 1.98.0 regression and the 1.97.1 workaround, plus the follow-up report confirming the error resolved on 1.100.1, and n8n's own Dockerfile which ships `@napi-rs/canvas` for PDF.js canvas rendering.*

---
*Images: not included — no license-verified copyright-free stock images available for this topic.*
