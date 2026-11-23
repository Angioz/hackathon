"""Fallback runner: executes the same assets and quality checks as `bruin run`, without Bruin.

Use only when the Bruin CLI is unavailable (dev box without Bruin, or demo failover).
The source of truth is still the Bruin pipeline; this reads the same asset files.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
import hack_common as hc  # noqa: E402

ORDER = ["ingest_feature_payload.py", "seed_agents_and_memory.py", "writers_room_sim.py",
         "story_quality_checks.sql", "export_pipeline_inputs.py"]
CHECK_RE = re.compile(r"-\s*name:\s*(\S+)\s*\n\s*query:\s*(.+?)\n\s*value:\s*(\d+)")


def run_sql_asset(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    header, body = text.split("@bruin */", 1)
    table = re.search(r"name:\s*(\S+)", header).group(1)
    schema = table.split(".")[0]
    con = hc.connect()
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    con.execute(f"CREATE OR REPLACE TABLE {table} AS {body.strip()}")
    failures = []
    for col in ("run_id", "decision_id", "agent_id", "action_type", "decision_summary", "reasoning_why"):
        nulls = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL").fetchone()[0]
        if nulls:
            failures.append(f"not_null({col}) failed on {nulls} rows")
    for name, query, value in CHECK_RE.findall(header):
        got = con.execute(query).fetchone()[0]
        status = "PASS" if int(got) == int(value) else "FAIL"
        print(f"  [check] {status} {name} (got {got}, want {value})")
        if status == "FAIL":
            failures.append(name)
    con.close()
    if failures:
        raise SystemExit(f"Quality checks failed: {failures}. Export held back.")


def main() -> None:
    for name in ORDER:
        path = HERE / "assets" / name
        print(f"==> {name}")
        if name.endswith(".sql"):
            run_sql_asset(path)
        else:
            subprocess.run([sys.executable, str(path)], check=True)
    print("==> pipeline finished")


if __name__ == "__main__":
    main()
