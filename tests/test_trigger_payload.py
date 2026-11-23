from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_autonomous_launch as launch

def test_payload_fields(monkeypatch):
    responses = {'rev-parse':'a'*40, 'show': 'Add Smart Scroll', 'diff-tree':'feature.txt'}
    def fake(repo, *args):
        if args[0] == 'show' and '--stat' in args: return 'feature.txt | 1 +'
        if args[0] == 'show' and '--format=%an' in args: return 'Test Author'
        return responses[args[0]]
    monkeypatch.setattr(launch, 'git', fake)
    p = launch.build_payload('.', 'HEAD')
    assert p['title'] == 'Add Smart Scroll' and p['author'] == 'Test Author'
    assert p['changed_files'] == ['feature.txt'] and 'feature.txt' in p['diff_summary'] and len(p['commit_sha']) == 40 and p['run_id']
