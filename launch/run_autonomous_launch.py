"""SM-2: one command, zero prompts: commit -> Bruin writers' room -> render -> publish receipt.

  py launch/run_autonomous_launch.py --commit <sha> [--label run_1]
  py launch/run_autonomous_launch.py --event-json evt.json --event-type push   (used by the webhook)

Rendering is Lane A's: set HACK_RENDER_CMD to a command that reads env HACK_RUN_DIR and writes
$HACK_RUN_DIR/final_video.mp4. If unset, the render step is reported as skipped (never faked).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bruin-pipeline" / "lib"))
import hack_common as hc  # noqa: E402
import live  # noqa: E402
import payload as pl  # noqa: E402
import publisher  # noqa: E402

LOCK = hc.OUTPUT_DIR / ".run.lock"


def find_bruin() -> str | None:
    found = shutil.which("bruin")
    if found:
        return found
    for cand in (Path.home() / ".local/bin/bruin.exe", Path.home() / ".local/bin/bruin"):
        if cand.exists():
            return str(cand)
    return None


BRUIN_LINE = re.compile(r"^\[[\d:]+\]\s+(Running|Finished|Failed):\s+(\S+)")


def run_streamed(cmd: list[str]) -> None:
    """Run the pipeline, echo its output, and turn Bruin's step/check lines into live events."""
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    for line in proc.stdout:
        print(line, end="", flush=True)
        m = BRUIN_LINE.match(line.strip())
        if m:
            status, name = m.group(1).lower(), m.group(2)
            asset, _, check = name.partition(":")
            if check:
                live.emit("check", asset=asset, check=check.replace("custom-check:", ""), status=status)
            else:
                live.emit("step", asset=asset, status=status)
    if proc.wait():
        live.emit("run_failed", reason="bruin run failed")
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def step(name: str, timings: dict):
    class _T:
        def __enter__(self):
            print(f"\n=== {name} ===", flush=True)
            self.t = time.time()

        def __exit__(self, *exc):
            timings[name] = round(time.time() - self.t, 1)
    return _T()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--repo", default=str(ROOT), help="git repo whose merge we film")
    ap.add_argument("--event-json")
    ap.add_argument("--event-type", choices=["push", "pull_request"])
    ap.add_argument("--brain", choices=["auto", "bruin", "llm", "offline"])
    ap.add_argument("--runner", choices=["auto", "bruin", "local"], default="auto")
    ap.add_argument("--publish", choices=["dry-run", "live"], default="dry-run")
    ap.add_argument("--label", help="also copy outputs to output/<label>/ (e.g. run_1, run_2)")
    ap.add_argument("--fresh", action="store_true",
                    help="wipe agent memory + run history (local DuckDB) before this run")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):  # Bruin prints symbols (e.g. a check mark) that cp1252 can't encode
        stream.reconfigure(encoding="utf-8", errors="replace")
    hc.load_env()
    if args.fresh and hc.DB_PATH.suffix == ".duckdb" and hc.DB_PATH.exists():
        hc.DB_PATH.unlink()
        print(f"--fresh: removed {hc.DB_PATH}")
    if args.brain:
        os.environ["HACK_BRAIN"] = args.brain

    hc.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        print(f"Another run holds {LOCK}; refusing to start a parallel run.", file=sys.stderr)
        return 2
    timings: dict = {}
    try:
        with step("1. feature payload", timings):
            if args.event_json:
                event = json.loads(Path(args.event_json).read_text(encoding="utf-8"))
                feature = pl.from_github_event(event, args.event_type or "push")
                if feature is None:
                    print("Event is not a merge to main; nothing to do.")
                    return 0
            else:
                feature = pl.from_git(Path(args.repo), args.commit)
            hc.write_json(hc.PENDING_PAYLOAD, feature)
            live.reset(run_id=feature["run_id"], commit_sha=feature["commit_sha"], title=feature["title"],
                       author=feature.get("author", ""), changed_files=feature.get("changed_files", []),
                       source=feature.get("source", ""))
            print(f"run_id={feature['run_id']} commit={feature['commit_sha'][:7]} title={feature['title']!r}")

        with step("2. bruin pipeline", timings):
            bruin = find_bruin() if args.runner in ("auto", "bruin") else None
            if args.runner == "bruin" and not bruin:
                raise SystemExit("Bruin CLI not found (--runner bruin).")
            cmd = ([bruin, "run", str(ROOT / "bruin-pipeline")] if bruin
                   else [sys.executable, str(ROOT / "bruin-pipeline" / "run_local.py")])
            print("runner:", "bruin" if bruin else "local fallback (Bruin CLI not found)")
            run_streamed(cmd)
        run_dir = hc.run_dir(feature["run_id"])

        with step("3. render", timings):
            render_cmd = os.environ.get("HACK_RENDER_CMD")
            if render_cmd:
                subprocess.run(shlex.split(render_cmd, posix=os.name != "nt"), check=True, cwd=ROOT,
                               env={**os.environ, "HACK_RUN_DIR": str(run_dir)})
            else:
                print("SKIPPED: HACK_RENDER_CMD not set (Lane A renderer not wired yet).")

        with step("4. publish", timings):
            receipt = publisher.publish(run_dir, args.publish)
            print(f"publish: {receipt['delivery_status']} -> {receipt['target_channels']}")

        manifest = {"run_id": feature["run_id"], "commit_sha": feature["commit_sha"],
                    "timings_sec": timings, "render": "done" if (run_dir / "final_video.mp4").exists() else "skipped",
                    "artifacts": sorted(p.name for p in run_dir.iterdir())}
        hc.write_json(run_dir / "run_manifest.json", manifest)
        live.emit("run_done", run_id=feature["run_id"], seconds=round(sum(timings.values()), 1),
                  publish=receipt["delivery_status"])
        live.archive(feature["run_id"])
        hc.publish_latest(feature["run_id"])
        if args.label:
            dst = hc.OUTPUT_DIR / args.label
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(run_dir, dst)
        print(f"\nDONE {feature['run_id']} in {sum(timings.values()):.1f}s -> {run_dir}")
        return 0
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
