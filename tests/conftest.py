import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "bruin-pipeline" / "contracts" / "sample"
FILES = ("story_bible", "decision_log", "rewritten_script")


def run_dir(label: str) -> Path:
    """Prefer this machine's latest local runs; fall back to the committed evidence."""
    for base in (ROOT / "output", ROOT / "docs" / "evidence"):
        if (base / label / "story_bible.json").exists():
            return base / label
    pytest.skip(f"no {label} found in output/ or docs/evidence/")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(params=["run_1", "run_2"])
def run(request):
    d = run_dir(request.param)
    return {name: load(d / f"{name}.json") for name in FILES} | {"dir": d}
