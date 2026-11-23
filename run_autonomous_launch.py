import argparse, json, os, subprocess, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, encoding='utf-8', errors='replace').strip()

def build_payload(repo, commit):
    sha = git(repo, 'rev-parse', '--verify', commit + '^{commit}')
    return {'run_id': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8], 'commit_sha': sha, 'title': git(repo, 'show', '-s', '--format=%s', sha), 'author': git(repo, 'show', '-s', '--format=%an', sha), 'changed_files': git(repo, 'diff-tree', '--root', '--no-commit-id', '--name-only', '-r', '-m', sha).splitlines(), 'diff_summary': git(repo, 'show', '--format=', '--stat', '--oneline', '-m', sha)}

def main():
    p = argparse.ArgumentParser(); p.add_argument('--commit', required=True); p.add_argument('--repo', default=str(ROOT / 'demo-app' / '.demo-repo')); p.add_argument('--headless', action='store_true'); a = p.parse_args()
    try: payload = build_payload(a.repo, a.commit)
    except (subprocess.CalledProcessError, OSError) as e: print(f'Could not read commit: {e}', file=sys.stderr); return 1
    path = Path(os.environ.get('FEATURE_PAYLOAD', ROOT / 'output' / 'feature_payload.json')).resolve(); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    env = os.environ.copy(); env['FEATURE_PAYLOAD'] = str(path)
    try: result = subprocess.run([env.get('BRUIN_BIN', 'bruin'), 'run', 'bruin-pipeline'], cwd=ROOT, env=env)
    except OSError as e: print(f'Could not start pipeline: {e}', file=sys.stderr); return 1
    if result.returncode: return result.returncode
    out = ROOT / 'output' / payload['run_id']; paths = {name: str(out / (name + '.json')) for name in ('story_bible','decision_log','rewritten_script')}
    for name, value in paths.items(): print(f'{name}: {value}')
    receipt = {'run_id': payload['run_id'], 'commit_sha': payload['commit_sha'], 'feature_payload': str(path), 'outputs': paths, 'status': 'pipeline_succeeded'}
    (ROOT / 'output' / 'launch_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8'); return 0
if __name__ == '__main__': sys.exit(main())
