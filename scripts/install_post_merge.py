"""Install a post-merge hook in the demo repo that runs the single trigger
(launch/run_autonomous_launch.py) on every merge. Refuses to overwrite a foreign hook.

  py scripts/install_post_merge.py [--repo demo-app/.demo-repo]
"""
import argparse
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKER = "# hack-launch-trigger"

p = argparse.ArgumentParser()
p.add_argument("--repo", default=str(ROOT / "demo-app" / ".demo-repo"))
a = p.parse_args()
repo = pathlib.Path(a.repo).resolve()
hooks = pathlib.Path(subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--git-path", "hooks"],
                                             text=True).strip())
hooks = hooks if hooks.is_absolute() else repo / hooks
hooks.mkdir(parents=True, exist_ok=True)
hook = hooks / "post-merge"
if hook.exists() and MARKER not in hook.read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("Existing post-merge hook not created by us; refusing to overwrite it.")
script = (ROOT / "launch" / "run_autonomous_launch.py").as_posix()
hook.write_text(f'#!/bin/sh\n{MARKER}\nexec py "{script}" --commit HEAD --repo "{repo.as_posix()}"\n',
                encoding="utf-8", newline="\n")
hook.chmod(0o755)
print(hook)
