"""Build the static GitHub Pages site into _site/ (no server needed).

  py scripts/build_pages.py            then: py -m http.server 8098 -d _site

/                -> site/hack-launch-films (mock website)
/live/           -> demo-app/live.html, replaying the committed golden run
/decision-log/   -> demo-app/decision-log.html, run 1 vs run 2 from committed evidence
/smart-scroll/   -> demo-app/index.html (the demo feature itself)
The demo app's /api endpoints are replaced by static JSON files in /data/.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
EVIDENCE = ROOT / "docs" / "evidence"
RUNS = ["run_1", "run_2"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def swap(text: str, old: str, new: str, where: str) -> str:
    if old not in text:
        raise SystemExit(f"build_pages: expected snippet not found in {where}: {old[:60]!r}")
    return text.replace(old, new)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data").mkdir(parents=True)

    # Mock website at the root
    shutil.copytree(ROOT / "site" / "hack-launch-films", OUT, dirs_exist_ok=True)
    for preview in ("preview-desktop.png", "preview-phone.png"):
        (OUT / preview).unlink(missing_ok=True)

    # Data the demo app normally serves from /api
    events = [json.loads(line) for line in read(EVIDENCE / "golden" / "events.jsonl").splitlines() if line.strip()]
    (OUT / "data" / "events-golden.json").write_text(json.dumps({"total": len(events), "events": events}), encoding="utf-8")
    for run in RUNS:
        payload = {"log": json.loads(read(EVIDENCE / run / "decision_log.json")),
                   "story": json.loads(read(EVIDENCE / run / "story_bible.json"))}
        (OUT / "data" / f"run-{run}.json").write_text(json.dumps(payload), encoding="utf-8")
    (OUT / "data" / "runs.json").write_text(json.dumps(RUNS), encoding="utf-8")

    # /live/: replay the golden run from static JSON
    live = read(ROOT / "demo-app" / "live.html")
    live = swap(live, 'replay=params.get("replay")', 'replay=params.get("replay")||"golden"', "live.html")
    live = swap(live, 'fetch("/api/live?run="+encodeURIComponent(replay))',
                'fetch("../data/events-"+encodeURIComponent(replay)+".json")', "live.html")
    (OUT / "live").mkdir()
    (OUT / "live" / "index.html").write_text(live, encoding="utf-8")

    # /decision-log/: run 1 vs run 2 from static JSON
    log = read(ROOT / "demo-app" / "decision-log.html")
    log = swap(log, "fetch('/api/runs')", "fetch('../data/runs.json')", "decision-log.html")
    log = swap(log, "fetch('/api/run?id='+encodeURIComponent(sel.value))",
               "fetch('../data/run-'+encodeURIComponent(sel.value)+'.json')", "decision-log.html")
    log = swap(log, '<a href="/">← Smart Scroll</a>', '<a href="../">← Back to Hack</a>', "decision-log.html")
    (OUT / "decision-log").mkdir()
    (OUT / "decision-log" / "index.html").write_text(log, encoding="utf-8")

    # /smart-scroll/: the demo feature page
    (OUT / "smart-scroll").mkdir()
    page = swap(read(ROOT / "demo-app" / "index.html"), 'href="/decision-log"', 'href="../decision-log/"', "index.html")
    (OUT / "smart-scroll" / "index.html").write_text(page, encoding="utf-8")

    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    files = sorted(str(p.relative_to(OUT)).replace("\\", "/") for p in OUT.rglob("*") if p.is_file())
    print(f"built {OUT} ({len(files)} files):", *files, sep="\n  ")


if __name__ == "__main__":
    main()
