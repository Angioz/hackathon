"""Merge Webhook receiver (stdlib only).

  GITHUB_WEBHOOK_SECRET=... py launch/webhook_server.py --port 8787

POST /webhook  - GitHub push / pull_request events; HMAC-SHA256 verified; deduped by
                 X-GitHub-Delivery; a merge to main starts run_autonomous_launch.py in the
                 background and returns 202 immediately.
GET  /health   - liveness.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bruin-pipeline" / "lib"))
import hack_common as hc  # noqa: E402
import payload as pl  # noqa: E402

MAX_BODY = 5 * 1024 * 1024
INBOX = hc.OUTPUT_DIR / "webhook_inbox"
SEEN: set[str] = set()


def valid_signature(secret: str, body: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


class Handler(BaseHTTPRequestHandler):
    secret = ""

    def _send(self, code: int, msg: dict) -> None:
        data = json.dumps(msg).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        self._send(200, {"ok": True}) if self.path == "/health" else self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/webhook":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._send(413, {"error": "bad body size"})
        body = self.rfile.read(length)
        if not valid_signature(self.secret, body, self.headers.get("X-Hub-Signature-256", "")):
            return self._send(401, {"error": "bad signature"})
        delivery = self.headers.get("X-GitHub-Delivery", "")
        event_type = self.headers.get("X-GitHub-Event", "")
        if event_type == "ping":
            return self._send(200, {"ok": "pong"})
        if delivery in SEEN:
            return self._send(200, {"ok": "duplicate delivery ignored"})
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            return self._send(400, {"error": "invalid json"})
        if pl.from_github_event(event, event_type) is None:
            return self._send(200, {"ok": "ignored (not a merge to main)"})
        SEEN.add(delivery)
        INBOX.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(c for c in delivery if c.isalnum() or c == "-")[:64] or "nodelivery"
        evt_path = INBOX / f"{safe_id}.json"
        evt_path.write_bytes(body)
        log = open(INBOX / f"{safe_id}.log", "w", encoding="utf-8")  # noqa: SIM115 - child owns it
        subprocess.Popen([sys.executable, str(ROOT / "launch" / "run_autonomous_launch.py"),
                          "--event-json", str(evt_path), "--event-type", event_type],
                         cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        self._send(202, {"ok": "pipeline started", "delivery": safe_id})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    hc.load_env()
    Handler.secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not Handler.secret:
        raise SystemExit("Set GITHUB_WEBHOOK_SECRET (in .env.local) before starting the receiver.")
    print(f"listening on http://{args.host}:{args.port}/webhook")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
