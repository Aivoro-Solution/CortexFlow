"""SHA-aware push of specific files to a GitHub repo via the Contents API.

Usage: push_sha_aware.py <owner/repo> <branch> <commit-message> <file1> [file2 ...]
File paths are given relative to ~/workspace/blog/.

Unlike gh-push-contents, this fetches each existing file's blob SHA first,
so updating existing files works.
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import (
    add_surrogate_to_request,
    read_json_response,
    read_response_body,
    DynamicCredentialError,
)

API = "https://api.github.com"
ALLOWED = ["api.github.com"]
CREDENTIAL = "custom.github"
ROOT = os.path.expanduser("~/workspace/blog")


def api(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=body, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body:
        req.add_header("Content-Type", "application/json")
    add_surrogate_to_request(
        req, CREDENTIAL, entry_name="access_token", allowed_hosts=ALLOWED
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return read_json_response(resp)
    except urllib.error.HTTPError as exc:
        detail = read_response_body(exc).decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {path}: {detail}")


def get_sha(owner_repo, branch, quoted):
    try:
        info = api("GET", f"/repos/{owner_repo}/contents/{quoted}?ref={branch}")
        return info.get("sha")
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise


def main():
    owner_repo, branch, message = sys.argv[1], sys.argv[2], sys.argv[3]
    rels = sys.argv[4:]
    for i, rel in enumerate(rels, 1):
        full = os.path.join(ROOT, rel)
        with open(full, "rb") as fh:
            content = base64.b64encode(fh.read()).decode("ascii")
        quoted = "/".join(urllib.parse.quote(p) for p in rel.split(os.sep))
        sha = get_sha(owner_repo, branch, quoted)
        payload = {
            "message": message if i == 1 else f"Update {rel}",
            "content": content,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        api("PUT", f"/repos/{owner_repo}/contents/{quoted}", payload)
        print(f"  [{i}/{len(rels)}] {rel} ({'updated' if sha else 'created'})", flush=True)
    print("DONE")


if __name__ == "__main__":
    try:
        main()
    except (DynamicCredentialError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
