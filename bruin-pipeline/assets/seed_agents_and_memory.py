""" @bruin
name: seed_agents_and_memory
type: python
description: FR-2. Upserts the 4 Launch Studio Agents and makes sure each has a memory row to read at run start.
depends:
  - ingest_feature_payload
@bruin """
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import hack_common as hc  # noqa: E402
from cast import AGENTS, AGENT_IDS  # noqa: E402


def main() -> None:
    hc.load_env()
    con = hc.connect()
    con.execute("""CREATE TABLE IF NOT EXISTS agents (
        agent_id VARCHAR PRIMARY KEY, display_name VARCHAR, role VARCHAR, goal VARCHAR,
        secret_goal VARCHAR, personality VARCHAR, gender VARCHAR, voice_profile VARCHAR,
        avatar_rig_id VARCHAR, color VARCHAR, prop VARCHAR)""")
    con.execute("""CREATE TABLE IF NOT EXISTS agent_memory (
        run_id VARCHAR, agent_id VARCHAR, memory_reflection VARCHAR, alliance_weights JSON,
        preferred_twist_history JSON, ending_history JSON, wins INTEGER, created_at VARCHAR)""")
    for a in AGENTS:
        con.execute("INSERT OR REPLACE INTO agents VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            a["agent_id"], a["display_name"], a["role"], a["goal"], a["secret_goal"],
            a["personality"], a["gender"], a["voice_profile"], a["avatar_rig_id"],
            a["color"], a["prop"]])
        has_memory = con.execute("SELECT COUNT(*) FROM agent_memory WHERE agent_id = ?",
                                 [a["agent_id"]]).fetchone()[0]
        if not has_memory:
            neutral = {other: 0.5 for other in AGENT_IDS if other != a["agent_id"]}
            con.execute("INSERT INTO agent_memory VALUES (?,?,?,?,?,?,?,?)", [
                "genesis", a["agent_id"], "No films made yet. Everything to prove.",
                json.dumps(neutral), "[]", "[]", 0, hc.now_iso()])
    count = con.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    con.close()
    print(f"[seed] agents={count}; memory ready")


main()
