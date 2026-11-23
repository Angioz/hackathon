import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def main():
    p = argparse.ArgumentParser(); p.add_argument('--run-id', required=True); p.add_argument('--channel', action='append', default=[]); p.add_argument('--caption', default=''); p.add_argument('--video-path'); a = p.parse_args()
    if os.environ.get('PUBLISH_LIVE') == '1': print('Live publishing is not implemented.', file=sys.stderr); return 1
    if not a.run_id or Path(a.run_id).name != a.run_id or a.run_id in ('.','..'): p.error('invalid run id')
    path = ROOT / 'output' / a.run_id / 'publish_receipt.json'; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'channels': a.channel, 'caption': a.caption, 'video_path': a.video_path, 'status':'dry_run'}, indent=2), encoding='utf-8'); print(path); return 0
if __name__ == '__main__': sys.exit(main())
