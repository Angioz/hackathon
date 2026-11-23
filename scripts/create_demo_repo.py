"""Create the demo git repo (demo-app/.demo-repo) for the merge-trigger demo. Idempotent.

  py scripts/create_demo_repo.py [--reset]

main            : the Smart Scroll article without the feature
feat/smart-scroll: adds the reading-progress bar and the section navigation (+ its script)
Then: py scripts/install_post_merge.py  and  git -C demo-app/.demo-repo merge --no-ff feat/smart-scroll
"""
from __future__ import annotations

import argparse
import re
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "demo-app" / ".demo-repo"
FEATURE_HTML = ROOT / "demo-app" / "index.html"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def without_feature(html: str) -> str:
    html = re.sub(r"<header>.*?</header>", "", html, flags=re.S)
    html = re.sub(r"<nav>.*?</nav>", "", html, flags=re.S)
    return re.sub(r"<script>.*?</script>", "", html, flags=re.S)


def _force_remove(func, path, _exc):
    Path(path).chmod(stat.S_IWRITE)  # git object files are read-only on Windows
    func(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete and recreate the demo repo")
    args = ap.parse_args()
    if REPO.exists():
        if not args.reset:
            print(f"{REPO} exists (use --reset to recreate)")
            return
        shutil.rmtree(REPO, onerror=_force_remove)
    REPO.mkdir(parents=True)
    feature = FEATURE_HTML.read_text(encoding="utf-8-sig")
    git("init", "-q", "-b", "main")
    git("config", "user.name", "Demo Dev")
    git("config", "user.email", "demo-dev@example.invalid")
    (REPO / "index.html").write_text(without_feature(feature), encoding="utf-8")
    git("add", "index.html")
    git("commit", "-q", "-m", "Publish the long-read article")
    git("switch", "-q", "-c", "feat/smart-scroll")
    (REPO / "index.html").write_text(feature, encoding="utf-8")
    git("add", "index.html")
    git("commit", "-q", "-m", "Add Smart Scroll: reading progress bar and section navigation",
        "-m", "Readers see how far they are through a long article and can jump to any section.")
    git("switch", "-q", "main")
    print(git("log", "--oneline", "--all", "--graph"))


if __name__ == "__main__":
    main()
