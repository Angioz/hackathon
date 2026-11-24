"""FR-10: Auto-Publisher. Dry-run by default; always writes publish_receipt.json.

Live delivery needs ALL of: --mode live, HACK_PUBLISH_ALLOW=1, HACK_PUBLISH_WEBHOOK_URL,
and an existing video file. Channels come from HACK_PUBLISH_CHANNELS (allowlist).
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_CHANNELS = {"x", "linkedin", "youtube", "tiktok", "instagram", "webhook_sink"}


def caption(bible: dict) -> str:
    return (f"{bible['title']}\n\n{bible['logline']}\n\n"
            f"Plot twist chosen by the Critic agent: {bible['plot_twist']['label']}. "
            f"Ending decided by the Director agent: {bible['ending']['label']}.\n"
            f"Commit {bible['commit_sha'][:7]}. Written by 4 AI agents in a Bruin pipeline, zero humans.\n"
            "#BuildInPublic #AIagents #Bruin")


def publish(run_dir: Path, mode: str = "dry-run") -> dict:
    bible = json.loads((run_dir / "story_bible.json").read_text(encoding="utf-8"))
    video = run_dir / "final_video.mp4"
    wanted = [c.strip() for c in os.environ.get("HACK_PUBLISH_CHANNELS", "webhook_sink").split(",") if c.strip()]
    channels = [c for c in wanted if c in ALLOWED_CHANNELS]
    receipt = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": bible["run_id"], "commit_sha": bible["commit_sha"], "mode": mode,
        "target_channels": channels, "rejected_channels": sorted(set(wanted) - set(channels)),
        # relative to the repo (output/<run_id>/...) so receipts never carry a personal home path
        "caption": caption(bible), "video_path": os.path.relpath(video, run_dir.parents[1]).replace("\\", "/"),
        "video_exists": video.exists(),
        "delivery_status": "dry_run", "http_status": None,
    }
    if mode == "live":
        url = os.environ.get("HACK_PUBLISH_WEBHOOK_URL", "")
        if os.environ.get("HACK_PUBLISH_ALLOW") != "1" or not url.startswith("https://"):
            receipt["delivery_status"] = "blocked: set HACK_PUBLISH_ALLOW=1 and an https HACK_PUBLISH_WEBHOOK_URL"
        elif not video.exists():
            receipt["delivery_status"] = "blocked: final_video.mp4 not rendered"
        else:
            body = json.dumps({k: receipt[k] for k in ("run_id", "commit_sha", "target_channels",
                                                       "caption", "video_path")}).encode()
            req = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    receipt["http_status"], receipt["delivery_status"] = resp.status, "delivered"
            except Exception as exc:  # noqa: BLE001 - recorded in the receipt, never raised
                receipt["delivery_status"] = f"failed: {type(exc).__name__}: {exc}"
    (run_dir / "publish_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt
