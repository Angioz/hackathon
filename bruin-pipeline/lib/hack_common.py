"""Shared paths, env loading and DuckDB helpers for the Hack Bruin pipeline."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_DIR.parent
DB_PATH = Path(os.environ.get("HACK_DB", PIPELINE_DIR / "hack_agents.duckdb"))
OUTPUT_DIR = Path(os.environ.get("HACK_OUTPUT", REPO_ROOT / "output"))
PENDING_PAYLOAD = OUTPUT_DIR / "pending" / "feature_payload.json"


def load_env() -> None:
    """Load KEY=VALUE pairs from .env.local (never committed) without overriding real env."""
    for name in (".env.local", ".env"):
        path = REPO_ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    import duckdb

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def current_run_id(con) -> str:
    row = con.execute(
        "SELECT run_id FROM run_state ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        raise RuntimeError("No run_state row: run ingest_feature_payload first.")
    return row[0]


def run_dir(run_id: str) -> Path:
    path = OUTPUT_DIR / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def publish_latest(run_id: str) -> Path:
    """Mirror a run's artifacts to output/latest/ for the renderer."""
    src = run_dir(run_id)
    dst = OUTPUT_DIR / "latest"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst
