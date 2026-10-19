---
title: "How to Run Python and FFmpeg Inside Dockerized n8n (4 Fixes That Work)"
description: "n8n Docker image ships neither Python nor FFmpeg. Build a custom Dockerfile, re-enable the Execute Command node, and wire up Python task runners."
date: 2026-10-19
category: automation
tags: ["n8n", "self-hosting", "Docker", "python", "ffmpeg", "troubleshooting"]
image: "/og/run-python-ffmpeg-dockerized-n8n.webp"
draft: false
featured: false
---

You drop a Code node set to Python into your n8n workflow, hit "Execute", and n8n tells you `Python 3 is missing from this system` — or the runner fails with `its virtual environment is missing`. Then you try a media step with an Execute Command node running `ffmpeg -i input.mp4 output.webm`, and either the command fails with `ffmpeg: command not found` — or the Execute Command node doesn't exist in the node panel at all.

Both failures have the same root cause: the official n8n Docker image is a slim Alpine-based image that ships neither Python nor FFmpeg, and since n8n v2.0 the Execute Command node is disabled by default as a security hardening measure. This guide walks through the exact fixes, verified against community-accepted solutions: a custom Dockerfile that adds Python and FFmpeg, re-enabling Execute Command, and setting up the Python task runner on newer n8n versions. By the end, both `python3` in Code nodes and `ffmpeg` in Execute Command will run inside your container.

## The symptom

Three different errors, all pointing at the same gap:

1. **Code node in Python mode fails:** `Python runner unavailable: Python 3 is missing from this system` — the official Docker image is Alpine-based and does not include Python at all.
2. **Task-runner error on newer n8n (v2.x):** `Failed to start Python task runner in internal mode. because its virtual environment is missing from this system` — Python exists nowhere, and internal runner mode is debug-only anyway.
3. **Execute Command fails or is missing:** `ffmpeg: command not found` when FFmpeg isn't installed — and on n8n 2.0+, the Execute Command node isn't even in the node selector until you re-enable it.

The trap most people fall into: they try `apk add` via the Execute Command node itself, or they mount binaries into the running container. Both "fixes" evaporate on the next `docker compose up` — the container filesystem is disposable by design. The only durable fix is building the tool into the image.

## The root cause

Two separate decisions by the n8n team combine here:

1. **Slim base image.** The published `n8nio/n8n` Docker image is built on Alpine Linux to stay small. Alpine ships almost nothing: no Python, no FFmpeg, no compilers. That's why the container can't run your Python script or transcode a video out of the box.
2. **Disabled Execute Command in v2.0+.** Since n8n 2.0, the Execute Command and Local File Trigger nodes are disabled by default because they allow arbitrary command execution and filesystem access. They stay off until you explicitly opt back in with the `NODES_EXCLUDE` environment variable.

For Python specifically there's a third layer: newer n8n runs Code nodes through task runners (a separate execution path from the main process). If you're on n8n v2.x, installing Python into the image is necessary but not sufficient — you also need the runner configuration correct.

## Prerequisites

- A running Dockerized n8n setup (docker-compose or plain `docker run`), n8n 1.x or 2.x. Commands below were verified against n8n 2.x tags.
- A terminal on the host with Docker access and permission to rebuild images.
- Basic familiarity with Dockerfiles and `docker-compose.yml`.

**Placeholder:** replace `<tag>` with the n8n version tag you actually run (e.g. `2.39.8`), and `<image-name>` with whatever you name your custom image (e.g. `n8n-custom`).

## Step 1 - Check your n8n version and Alpine base

Newer n8n images changed what's inside: some recent tags (built on Alpine 3.24) don't even ship the `apk` package manager binary, so `RUN apk add` fails at build time. Check first, from the host:

```bash
docker exec <your-n8n-container> cat /etc/os-release
docker exec <your-n8n-container> which apk
```

The first command tells you the Alpine version (match it later). If `which apk` returns nothing, you'll need the Step 2 workaround that copies `apk` back in from a plain Alpine stage of the same version. Also note your n8n tag now — you're going to pin it in the Dockerfile, because the build only survives while the base image stays the same Alpine generation.

> **Note:** Pin the n8n tag (`FROM n8nio/n8n:2.39.8`, not `:latest`). When n8n bumps its Alpine base, your Dockerfile's package list may need rebuilding. Budget a rebuild for every n8n upgrade.

## Step 2 - Write the Dockerfile that adds Python and FFmpeg

Create a `Dockerfile` next to your `docker-compose.yml`. This is the accepted community solution: extend the official image, switch to root, install, switch back:

```dockerfile
ARG tag=<tag>
FROM n8nio/n8n:$tag
USER root
RUN apk add --no-cache python3 py3-pip ffmpeg
USER node
```

What each line does:
- `ARG tag=<tag>` lets you pass the n8n version at build time, so the Dockerfile stays reusable across upgrades.
- `USER root` — the official image runs as the `node` user; installing system packages needs root. This is the single most common mistake (building without it fails with `permission denied`).
- `RUN apk add --no-cache python3 py3-pip ffmpeg` — installs Python 3, pip, and FFmpeg from Alpine's package repository. `--no-cache` avoids leaving a package cache in the layer.
- `USER node` — drops back to the non-root user before the container starts. Running n8n as root is a security risk; never skip this.

**If your n8n tag lacks `apk`** (checked in Step 1), use the two-stage version that copies `apk` in from a matching plain-Alpine stage:

```dockerfile
FROM alpine:3.24 AS alpine
FROM docker.n8n.io/n8nio/n8n:2.39.8
COPY --from=alpine /sbin/apk /sbin/apk
COPY --from=alpine /usr/lib/libapk.so* /usr/lib/
USER root
RUN apk add --no-cache ffmpeg python3 py3-pip
USER node
```

The first line's Alpine version must match what `/etc/os-release` reported inside the n8n image. A version mismatch here is the #1 reason this workaround fails.

**If you use FFmpeg's `drawtext` or `subtitles` filters**, add fonts too — the n8n image ships no fonts, and `subtitles=` will exit 0 while drawing nothing:

```dockerfile
RUN apk add --no-cache ffmpeg python3 py3-pip fontconfig font-dejavu
```

> **Warning:** Don't install Python/FFmpeg on a running container with `docker exec` and expect it to last. Containers are ephemeral — everything you `exec`-install dies on the next restart. The Dockerfile is the fix; everything else is a demo.

## Step 3 - Build the image and point Compose at it

```bash
docker build --build-arg tag=<tag> -t <image-name>:<tag> .
```

You should see the `apk add` step complete without errors. Then update your `docker-compose.yml` to build (or pull your built image) instead of the stock image:

```yaml
services:
  n8n:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - "tag=<tag>"
    # ... rest of your existing config
```

What changed: Compose now builds your custom image at `docker compose up --build` instead of pulling the stock one. Alternatively, push the built image to a registry and reference `image: <image-name>:<tag>`.

Verify the tools exist in the new container:

```bash
docker compose up -d --build
docker exec <your-n8n-container> python3 --version
docker exec <your-n8n-container> ffmpeg -version
```

You should see a Python 3.x version and the FFmpeg banner. If `ffmpeg -version` fails, the image build step didn't include it — check the build log, not the workflow.

## Step 4 - Re-enable the Execute Command node (n8n 2.0+ only)

On n8n 2.0 and later, the Execute Command node is excluded from the node panel by default. To bring it back, set the `NODES_EXCLUDE` environment variable to an empty array in your compose file:

```yaml
services:
  n8n:
    environment:
      - NODES_EXCLUDE=[]
    # ... rest of your existing config
```

Why this variable and not something else: n8n's default config lists Execute Command in its disabled-node set; `NODES_EXCLUDE="[]"` clears that list. This is the documented, community-verified method — alternatives like `N8N_EXECUTE_COMMAND_ENABLED` or `N8N_NODES_EXCLUDE` do not exist and will silently do nothing. One community thread burned hours on exactly that misspelling.

Restart fully after changing it (`docker compose down && docker compose up -d`), then search the node panel for "Execute Command". If it's still missing, the container didn't pick up the new env — check `docker exec <container> env | grep NODES_EXCLUDE`.

> **Note:** On n8n 1.x this step doesn't exist — Execute Command was never disabled there. And n8n Cloud users are out of luck entirely: you can't install packages or use Execute Command on the hosted platform, so use an HTTP Request node against an external FFmpeg API instead.

## Step 5 - Wire up the Python task runner (n8n 2.x)

On n8n v2.x, Code nodes run through task runners, and the supported production setup is **external mode**. Add these to the n8n service in compose:

```yaml
environment:
  - N8N_RUNNERS_ENABLED=true
  - N8N_RUNNERS_MODE=external
  - N8N_RUNNERS_BROKER_LISTEN_ADDRESS=0.0.0.0
  - N8N_RUNNERS_AUTH_TOKEN=<a-long-random-secret>
```

Each key's job: `N8N_RUNNERS_ENABLED` turns the runner system on; `N8N_RUNNERS_MODE=external` runs Code-node code in the external runner process instead of the debug-only internal mode (this is the actual fix for the `virtual environment is missing` error); `N8N_RUNNERS_BROKER_LISTEN_ADDRESS` lets the runner reach the broker; `N8N_RUNNERS_AUTH_TOKEN` is the shared secret between n8n and the runner — generate something long and random, and never commit a real one to a public repo.

If your Python Code node needs third-party packages (say, `requests` or `pypdf`), installing them isn't enough — there's a separate allowlist gate. Build a custom runners image and allowlist the modules:

```dockerfile
FROM n8nio/runners:<tag>
USER root
RUN cd /opt/runners/task-runner-python && uv pip install pypdf
COPY n8n-task-runners.json /etc/n8n-task-runners.json
USER runner
```

```yaml
services:
  n8n:
    environment:
      - N8N_RUNNERS_EXTERNAL_ALLOW=pypdf
  task-runners:
    build:
      context: .
      dockerfile: Dockerfile.runners
    environment:
      - N8N_RUNNERS_AUTH_TOKEN=<same-secret>
      - N8N_RUNNERS_TASK_BROKER_URI=http://n8n:5679
```

The crucial detail the community threads keep rediscovering: the packages must go into `/opt/runners/task-runner-python` — that's the only directory the Code node looks at — and `uv pip install` is the tool the runners image provides. The tag must match your n8n version.

Verify end to end: add a Code node, set language to Python, and run:

```python
import sys
return [{"python": sys.version}]
```

If it returns a version string, the full Python path works. Then test FFmpeg with an Execute Command node running `ffmpeg -version` — you should see the FFmpeg banner, not `command not found`.

## Step 6 - A real workflow: Python + FFmpeg together

Here's the pattern this setup unlocks — Python for logic, FFmpeg for media, in one workflow:

1. **HTTP Request node** — downloads a video file (e.g. from a URL trigger).
2. **Write Binary File / Read/Write Files from Disk** — saves it to `/tmp/input.mp4` inside the container. Use a mounted volume for the folder if you need the files to survive restarts.
3. **Execute Command node** — `ffmpeg -i /tmp/input.mp4 -vf scale=1280:-2 -c:v libx264 -preset fast /tmp/output.mp4`. This downscales and re-encodes the video.
4. **Code node (Python)** — reads the output file's size and decides what to do next:

```python
import os
size = os.path.getsize("/tmp/output.mp4")
return [{"output_mb": round(size / 1024 / 1024, 2)}]
```

5. **Slack / Gmail / HTTP node** — sends the result.

Verification is per-step: the Execute Command node should exit 0 and print FFmpeg's progress to stderr; the Python node should return a number. If Execute Command exits non-zero, paste its stderr — nine times out of ten it's a wrong input path, not a broken install.

## Limits and when NOT to do this

- **n8n Cloud can't do any of this.** No custom images, no Execute Command, no package installs. If you're on Cloud and need video processing, call an external FFmpeg API from an HTTP Request node instead.
- **Video transcoding is heavy.** FFmpeg inside the n8n container shares CPU with your workflows. On a small VPS, a transcode can starve running automations — for production media pipelines, run FFmpeg in a dedicated container or a queue worker, not inside n8n.
- **Every n8n upgrade = a rebuild.** The custom Dockerfile is coupled to n8n's Alpine base. Pin the tag, keep the Dockerfile in version control, and rebuild on every upgrade.
- **Security trade-offs are real.** Re-enabling Execute Command and running as root during the build expand your attack surface. Never expose a container with Execute Command enabled directly to the internet; keep n8n behind authentication and a reverse proxy.

## FAQ

### Do I need Python for the Code node if I only write JavaScript?

No. JavaScript Code nodes run on Node.js, which is already in the image. Python installation is only needed when the Code node's language is set to Python.

### Why does my Python package install disappear after restarting?

Because it was installed into the container filesystem (via `docker exec` or a one-off command) instead of baked into the image. Containers are ephemeral — rebuild the image with the package in the Dockerfile, or use the custom runners image with `uv pip install`.

### Can I use pip install inside the running container for a quick test?

Yes, for testing only: `docker exec -u root <container> pip3 install <package>` works until the next restart. For anything durable, put it in the Dockerfile or the runners image.

### Is there a smaller alternative to installing full FFmpeg?

Yes — a multi-stage Dockerfile can copy static FFmpeg binaries (e.g. from `mwader/static-ffmpeg`) into the n8n image without the Alpine package dependency. It's version-agnostic but roughly twice the layer size of the `apk`-installed package. The community thread that tested this reported it working in production across multiple n8n versions.

## Key Takeaways

1. **The stock n8n Docker image has no Python and no FFmpeg** — it's a slim Alpine image, so `python3: command not found` and `ffmpeg: command not found` are expected, not bugs.
2. **The durable fix is a custom Dockerfile**: `FROM n8nio/n8n`, switch to root, `RUN apk add --no-cache python3 py3-pip ffmpeg`, switch back to the `node` user — and add `fontconfig font-dejavu` if you use drawtext/subtitles.
3. **On n8n 2.0+, re-enable Execute Command** with `NODES_EXCLUDE=[]` (exact name — misspellings silently fail), then restart the container fully.
4. **On n8n 2.x, configure external task runners** (`N8N_RUNNERS_ENABLED=true`, `N8N_RUNNERS_MODE=external`, auth token) and allowlist Python packages separately via `N8N_RUNNERS_EXTERNAL_ALLOW` — installing the package alone isn't enough.
5. **Pin the n8n tag and rebuild on every upgrade** — your Dockerfile is coupled to n8n's Alpine base, and newer tags may not even ship `apk`.

Next: verify your setup with the one-line Python version check and `ffmpeg -version` from Step 3 — if both return version strings, your container is ready for Python and media workflows. For processing at scale, look into running FFmpeg as a dedicated queue worker outside the n8n container.
