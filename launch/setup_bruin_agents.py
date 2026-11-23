"""Create (once) the 4 Launch Studio Agents as Bruin Cloud agents; writes their ids to
bruin-pipeline/lib/bruin_agents.json. Idempotent: reuses agents that already exist by name.

  py launch/setup_bruin_agents.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bruin-pipeline" / "lib"))
import bruin_brain  # noqa: E402
import hack_common as hc  # noqa: E402
from cast import AGENTS  # noqa: E402
from room import persona  # noqa: E402


def cli(*args: str):
    out = subprocess.run([bruin_brain.bruin_exe(), "cloud", "agents", *args, "-o", "json"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode:
        raise SystemExit(out.stderr or out.stdout)
    return json.loads(out.stdout)


def main() -> None:
    hc.load_env()
    listed = cli("list")
    existing = {a["name"]: a["id"] for a in (listed if isinstance(listed, list) else listed.get("agents", []))}
    ids = {}
    for a in AGENTS:
        name = f"Hack {a['display_name']}"
        if name in existing:
            ids[a["agent_id"]] = existing[name]
            print(f"reuse  {name}: {existing[name]}")
            continue
        made = cli("create", "--name", name, "--description", f"Launch Studio Agent: {a['role']}",
                   "--prompt", persona(a), "--visibility", "team")
        ids[a["agent_id"]] = made.get("id") or made.get("agent", {}).get("id")
        print(f"create {name}: {ids[a['agent_id']]}")
    bruin_brain.AGENTS_FILE.write_text(json.dumps(ids, indent=2), encoding="utf-8")
    print(f"wrote {bruin_brain.AGENTS_FILE}")


if __name__ == "__main__":
    main()
