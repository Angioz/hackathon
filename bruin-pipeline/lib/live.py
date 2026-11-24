"""Live event feed for the demo screen (demo-app /live).

Events are JSON lines in output/live/events.jsonl for the run in progress; at the end the
trigger copies the file into output/<run_id>/events.jsonl so any run can be replayed.
Best effort: a failure to write an event never breaks the pipeline.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import hack_common as hc

LIVE_DIR = hc.OUTPUT_DIR / "live"
EVENTS = LIVE_DIR / "events.jsonl"


def reset(**info) -> None:
    try:
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        EVENTS.write_text("", encoding="utf-8")
        emit("run_start", **info)
    except OSError:
        pass


def emit(kind: str, **data) -> None:
    try:
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        with EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": round(time.time(), 3), "type": kind, **data},
                                ensure_ascii=False) + "\n")
    except OSError:
        pass


def archive(run_id: str) -> Path | None:
    try:
        dst = hc.run_dir(run_id) / "events.jsonl"
        dst.write_text(EVENTS.read_text(encoding="utf-8"), encoding="utf-8")
        return dst
    except OSError:
        return None
