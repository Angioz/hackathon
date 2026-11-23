""" @bruin
name: writers_room_sim
type: python
description: FR-3/FR-4. Runs the 4-round writers' room, writes decision_log, story_bibles and the updated agent_memory.
depends:
  - seed_agents_and_memory
@bruin """
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import brain  # noqa: E402
import bruin_brain  # noqa: E402
import hack_common as hc  # noqa: E402
import room as rm  # noqa: E402
import staging  # noqa: E402


def main() -> None:
    hc.load_env()
    started = time.time()
    con = hc.connect()
    run_id = hc.current_run_id(con)
    feature = json.loads(con.execute(
        "SELECT payload_json FROM raw_feature_payloads WHERE run_id = ?", [run_id]).fetchone()[0])
    print(f"[room] run={run_id} llm_mode={brain.mode()} model={brain.model_label()}")

    room = rm.Room(run_id, feature, rm.load_memory(con))
    outcome = room.simulate()
    script, script_brain = staging.write_script(room, outcome)
    bible = staging.build_story_bible(room, outcome, script, script_brain)

    con.execute("""CREATE TABLE IF NOT EXISTS decision_log (
        decision_id VARCHAR, run_id VARCHAR, round INTEGER, beat_id VARCHAR, agent_id VARCHAR,
        action_type VARCHAR, target_agent VARCHAR, decision_summary VARCHAR, reasoning_why VARCHAR,
        dialogue VARCHAR, emotion VARCHAR, stance VARCHAR, choice VARCHAR, plot_twist_flag BOOLEAN,
        accepted BOOLEAN, llm_mode VARCHAR, memory_refs JSON, created_at VARCHAR)""")
    con.execute("""CREATE TABLE IF NOT EXISTS story_bibles (
        run_id VARCHAR PRIMARY KEY, twist_id VARCHAR, ending_id VARCHAR,
        total_target_duration_sec DOUBLE, story_json JSON, created_at VARCHAR)""")
    cols = ["decision_id", "run_id", "round", "beat_id", "agent_id", "action_type", "target_agent",
            "decision_summary", "reasoning_why", "dialogue", "emotion", "stance", "choice",
            "plot_twist_flag", "accepted", "llm_mode", "memory_refs"]
    now = hc.now_iso()
    for d in room.decisions:
        con.execute(f"INSERT INTO decision_log VALUES ({','.join('?' * (len(cols) + 1))})",
                    [d[c] for c in cols] + [now])
    con.execute("INSERT INTO story_bibles VALUES (?,?,?,?,?,?)", [
        run_id, outcome["twist"]["twist_id"], outcome["ending"]["ending_id"],
        bible["total_target_duration_sec"], json.dumps(bible), now])
    new_memory = room.updated_memory(outcome)
    for m in new_memory:
        con.execute("INSERT INTO agent_memory VALUES (?,?,?,?,?,?,?,?)", [
            m["run_id"], m["agent_id"], m["memory_reflection"], json.dumps(m["alliance_weights"]),
            json.dumps(m["preferred_twist_history"]), json.dumps(m["ending_history"]), m["wins"], now])
    con.close()
    if brain.mode() == "bruin":  # mirror each reflection into the agent's Bruin long-term memory
        for m in new_memory:
            try:
                bruin_brain.remember(m["agent_id"], m["memory_reflection"])
            except Exception as exc:  # noqa: BLE001 - DuckDB memory is the source of truth
                print(f"[room] Bruin memory write failed for {m['agent_id']}: {exc}")
    print(f"[room] decisions={len(room.decisions)} twist={outcome['twist']['twist_id']} "
          f"ending={outcome['ending']['ending_id']} duration~{bible['total_target_duration_sec']}s "
          f"llm_modes={bible['llm_modes']} took={time.time() - started:.1f}s")


main()
