""" @bruin
name: ingest_feature_payload
type: python
description: FR-1. Reads the pending Feature Payload written by the trigger (or builds one from git HEAD) and starts a new run.
@bruin """
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import hack_common as hc  # noqa: E402
import payload as pl  # noqa: E402


def main() -> None:
    hc.load_env()
    if hc.PENDING_PAYLOAD.exists():
        feature = json.loads(hc.PENDING_PAYLOAD.read_text(encoding="utf-8"))
        print(f"[ingest] using pending payload for {feature['commit_sha'][:7]}")
    else:
        feature = pl.from_git(hc.REPO_ROOT, "HEAD")
        print(f"[ingest] no pending payload; built from git HEAD {feature['commit_sha'][:7]}")
    if not feature.get("run_id"):
        feature["run_id"] = pl.new_run_id(feature["commit_sha"])

    con = hc.connect()
    con.execute("""CREATE TABLE IF NOT EXISTS raw_feature_payloads (
        run_id VARCHAR PRIMARY KEY, commit_sha VARCHAR, title VARCHAR, author VARCHAR,
        changed_files JSON, diff_summary VARCHAR, payload_json JSON, created_at VARCHAR)""")
    con.execute("""CREATE TABLE IF NOT EXISTS run_state (
        run_id VARCHAR PRIMARY KEY, commit_sha VARCHAR, started_at VARCHAR, status VARCHAR)""")
    con.execute("INSERT INTO raw_feature_payloads VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        feature["run_id"], feature["commit_sha"], feature["title"], feature.get("author", ""),
        json.dumps(feature.get("changed_files", [])), feature.get("diff_summary", ""),
        json.dumps(feature), hc.now_iso()])
    con.execute("INSERT INTO run_state VALUES (?, ?, ?, 'started')",
                [feature["run_id"], feature["commit_sha"], hc.now_iso()])
    con.close()

    hc.write_json(hc.run_dir(feature["run_id"]) / "feature_payload.json", feature)
    if hc.PENDING_PAYLOAD.exists():
        hc.PENDING_PAYLOAD.unlink()  # consumed; the next run must bring its own payload
    print(f"[ingest] run_id={feature['run_id']}")


main()
