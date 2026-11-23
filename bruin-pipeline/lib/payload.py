"""FR-1: build a Feature Payload from a local git commit or a GitHub webhook event."""
from __future__ import annotations

import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

MAX_DIFF_CHARS = 4000
SHA_RE = re.compile(r"^[0-9a-fA-F]{4,40}$|^HEAD(~\d+)?$")


def new_run_id(commit_sha: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"run_{stamp}_{commit_sha[:7]}_{uuid.uuid4().hex[:4]}"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


def from_git(repo: Path, ref: str = "HEAD") -> dict:
    if not SHA_RE.match(ref):
        raise ValueError(f"Not a commit SHA or HEAD ref: {ref!r}")
    sha = _git(repo, "rev-parse", ref).strip()
    title = _git(repo, "log", "-1", "--format=%s", sha).strip()
    body = _git(repo, "log", "-1", "--format=%b", sha).strip()
    author = _git(repo, "log", "-1", "--format=%an", sha).strip()
    parents = _git(repo, "rev-list", "--parents", "-n", "1", sha).split()[1:]
    if len(parents) > 1:  # merge commit: describe what the merged branch brought in
        base = parents[0]
        files = [f for f in _git(repo, "diff", "--name-only", base, sha).splitlines() if f]
        stat = _git(repo, "diff", "--stat", base, sha).strip()
        patch = _git(repo, "diff", "--unified=1", base, sha)
        merged = _git(repo, "log", "--format=- %s%n%b", f"{base}..{parents[1]}").strip()
        body = f"{body}\nMerged commits:\n{merged}".strip()
    else:
        files = [f for f in _git(repo, "show", "--name-only", "--format=", sha).splitlines() if f]
        stat = _git(repo, "show", "--stat", "--format=", sha).strip()
        patch = _git(repo, "show", "--format=", "--unified=1", sha)
    return {
        "run_id": new_run_id(sha),
        "source": "git_cli",
        "commit_sha": sha,
        "title": title,
        "body": body[:1000],
        "author": author,
        "changed_files": files,
        "diff_summary": stat.splitlines()[-1] if stat else "",
        "diff_stat": stat[:1500],
        "diff_excerpt": patch[:MAX_DIFF_CHARS],
    }


def from_github_event(event: dict, event_type: str) -> dict | None:
    """Normalize a GitHub push (to main) or merged pull_request event. None = ignore."""
    if event_type == "push":
        if event.get("ref") != "refs/heads/main" or event.get("deleted"):
            return None
        head = event.get("head_commit") or {}
        files = sorted({f for c in event.get("commits", [])
                        for k in ("added", "modified", "removed") for f in c.get(k, [])})
        sha = head.get("id") or event.get("after", "")
        message = head.get("message", "")
        author = (head.get("author") or {}).get("name", "")
    elif event_type == "pull_request":
        pr = event.get("pull_request") or {}
        if event.get("action") != "closed" or not pr.get("merged"):
            return None
        if (pr.get("base") or {}).get("ref") != "main":
            return None
        sha = pr.get("merge_commit_sha") or ""
        message = f"{pr.get('title', '')}\n\n{pr.get('body') or ''}"
        author = (pr.get("user") or {}).get("login", "")
        files = []
    else:
        return None
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha or ""):
        return None
    title, _, body = message.partition("\n")
    return {
        "run_id": new_run_id(sha),
        "source": f"github_{event_type}",
        "commit_sha": sha,
        "title": title.strip()[:200],
        "body": body.strip()[:1000],
        "author": author,
        "changed_files": files,
        "diff_summary": f"{len(files)} files changed" if files else "",
        "diff_stat": "",
        "diff_excerpt": "",
    }
