"""Bruin Cloud agents as the Launch Studio Agents' brains (uses Bruin credits, no extra LLM key).

Each character is a Bruin Cloud agent (ids in bruin_agents.json, created by
launch/setup_bruin_agents.py). A turn = `bruin cloud agents send --output-schema`, then
poll `status` until completed; the structured answer comes back in output_message.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

AGENTS_FILE = Path(__file__).with_name("bruin_agents.json")
POLL_SEC = 2.0
MAX_MESSAGE = 9800  # Bruin rejects messages over 10,000 characters
TIMEOUT_SEC = float(os.environ.get("HACK_BRUIN_TIMEOUT", "180"))
GUARD = ("Answer ONLY from the context in this message. Do not query data, open files, "
         "or use tools. Stay in character.\n\n")


def bruin_exe() -> str:
    found = shutil.which("bruin")
    if found:
        return found
    for cand in (Path.home() / ".local/bin/bruin.exe", Path.home() / ".local/bin/bruin"):
        if cand.exists():
            return str(cand)
    raise RuntimeError("Bruin CLI not found")


def agent_ids() -> dict:
    return json.loads(AGENTS_FILE.read_text(encoding="utf-8")) if AGENTS_FILE.exists() else {}


def available() -> bool:
    return bool(os.environ.get("BRUIN_CLOUD_API_KEY")) and bool(agent_ids())


def _cli(*args: str) -> dict:
    out = subprocess.run([bruin_exe(), "cloud", "agents", *args, "-o", "json"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"bruin cloud agents {args[0]} failed: {out.stderr.strip() or out.stdout.strip()}")
    return json.loads(out.stdout)


def ask(agent_id: str, system: str, user: str, schema: dict) -> dict:
    bid = str(agent_ids()[agent_id])
    message = f"{GUARD}{system}\n\n{user}"
    if len(message) > MAX_MESSAGE:  # keep the feature brief (head) and the task (tail)
        head = 2500
        message = message[:head] + "\n[...trimmed...]\n" + message[-(MAX_MESSAGE - head - 20):]
    sent = _cli("send", "--agent-id", bid, "--message", message,
                "--output-schema", json.dumps(schema))
    thread, msg = str(sent["thread_id"]), str(sent["message_pair_id"])
    deadline = time.time() + TIMEOUT_SEC
    while time.time() < deadline:
        time.sleep(POLL_SEC)
        st = _cli("status", "--agent-id", bid, "--thread-id", thread, "--message-id", msg)
        if st.get("status") in ("pending", "processing"):
            continue
        if st.get("status") != "completed":
            raise RuntimeError(f"Bruin agent {agent_id} ended with status {st.get('status')}")
        raw = st.get("structured_output") or st.get("output_message") or ""
        return raw if isinstance(raw, dict) else json.loads(raw)
    raise TimeoutError(f"Bruin agent {agent_id} did not answer within {TIMEOUT_SEC:.0f}s")


def remember(agent_id: str, text: str) -> None:
    """Write the agent's reflection into its Bruin long-term memory (best effort)."""
    bid = str(agent_ids()[agent_id])
    _cli("set-memory", "--agent-id", bid, "--memory", text)
