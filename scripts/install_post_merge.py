import argparse, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(); p.add_argument('--repo', default=str(ROOT / 'demo-app' / '.demo-repo')); a = p.parse_args()
repo = pathlib.Path(a.repo).resolve(); hooks = pathlib.Path(subprocess.check_output(['git','-C',str(repo),'rev-parse','--git-path','hooks'], text=True).strip()); hooks = hooks if hooks.is_absolute() else repo / hooks
hooks.mkdir(parents=True, exist_ok=True); hook = hooks / 'post-merge'
if hook.exists(): raise SystemExit('Existing post-merge hook; refusing to overwrite it.')
script = (ROOT / 'run_autonomous_launch.py').as_posix(); rep = repo.as_posix()
hook.write_text('#!/bin/sh\nexec py "' + script + '" --commit HEAD --repo "' + rep + '" --headless\n', encoding='utf-8'); hook.chmod(0o755); print(hook)
