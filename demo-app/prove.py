"""Smoke-test the demo app against REAL pipeline output (no fixtures).

  py demo-app/prove.py     (needs output/latest from a pipeline run, e.g. after the demo merge)
"""
import json, pathlib, subprocess, sys, time, urllib.request

root = pathlib.Path(__file__).resolve().parents[1]
latest = root / 'output' / 'latest'
if not (latest / 'decision_log.json').exists():
    sys.exit('No real run in output/latest. Run the pipeline first (py launch/run_autonomous_launch.py ...).')
p = subprocess.Popen(['node', 'server.js'], cwd=root / 'demo-app')
try:
    time.sleep(2)
    for url in ['http://localhost:3000/', 'http://localhost:3000/decision-log',
                'http://localhost:3000/api/runs', 'http://localhost:3000/api/run?id=latest']:
        with urllib.request.urlopen(url, timeout=10) as r:
            body = r.read()
            print(url, r.status, len(body), 'bytes')
    data = json.loads(urllib.request.urlopen('http://localhost:3000/api/run?id=latest').read())
    assert 'fixture' not in data['log'] and data['log']['decisions'], 'expected real decisions'
    print('latest run:', data['story']['run_id'], '| twist:', data['story']['plot_twist']['label'],
          '| ending:', data['story']['ending']['label'], '| decisions:', len(data['log']['decisions']))
finally:
    p.terminate(); p.wait()
