"""Feature Payload extraction (FR-1) from a real throwaway git repo, including a merge commit."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bruin-pipeline" / "lib"))
import payload as pl  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_merge_commit_payload(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.name", "Test Author")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    (tmp_path / "page.html").write_text("<p>article</p>")
    _git(tmp_path, "add", "."); _git(tmp_path, "commit", "-q", "-m", "Article")
    _git(tmp_path, "switch", "-q", "-c", "feat/smart-scroll")
    (tmp_path / "page.html").write_text("<p>article</p><nav>map</nav>")
    _git(tmp_path, "commit", "-q", "-am", "Add Smart Scroll")
    _git(tmp_path, "switch", "-q", "main")
    _git(tmp_path, "merge", "-q", "--no-ff", "feat/smart-scroll", "-m", "Merge feat/smart-scroll")

    p = pl.from_git(tmp_path, "HEAD")
    assert len(p["commit_sha"]) == 40 and p["run_id"].startswith("run_")
    assert p["author"] == "Test Author"
    assert p["changed_files"] == ["page.html"]          # merge diff vs first parent, not empty
    assert "Add Smart Scroll" in p["body"]
    assert "<nav>map</nav>" in p["diff_excerpt"]


def test_rejects_non_sha_refs(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        pl.from_git(tmp_path, "main; rm -rf /")
