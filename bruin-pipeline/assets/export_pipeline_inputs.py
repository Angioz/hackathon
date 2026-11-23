""" @bruin
name: export_pipeline_inputs
type: python
description: FR-5. Emits story_bible.json, decision_log.json and rewritten_script.json for the renderer. No human gate.
depends:
  - hack.story_quality_checks
@bruin """
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import hack_common as hc  # noqa: E402

LOG_COLS = ["decision_id", "run_id", "round", "beat_id", "agent_id", "action_type", "target_agent",
            "decision_summary", "reasoning_why", "dialogue", "emotion", "stance", "choice",
            "plot_twist_flag", "accepted", "llm_mode", "memory_refs", "created_at"]


def rewritten_script(bible: dict) -> dict:
    voices = {c["agent_id"]: c["voice_profile"] for c in bible["cast"]}
    lines = [{"line_id": ln["line_id"], "scene_id": sc["scene_id"], "beat": sc["beat"],
              "speaker_agent_id": ln["speaker_agent_id"],
              "voice_profile": voices[ln["speaker_agent_id"]], "text": ln["dialogue"],
              "emotion": ln["emotion"], "character_action": ln["character_action"]}
             for sc in bible["scenes"] for ln in sc["lines"]]
    return {"schema_version": bible["schema_version"], "run_id": bible["run_id"],
            "title": bible["title"], "source": "bruin-pipeline/export_pipeline_inputs",
            "human_gate": "none (zero-HITL; replaces Stage 18 gate G-3)", "voices": voices,
            "word_count": sum(len(ln["text"].split()) for ln in lines),
            "full_text": "\n".join(f"{ln['speaker_agent_id']}: {ln['text']}" for ln in lines),
            "lines": lines}


def main() -> None:
    hc.load_env()
    con = hc.connect()
    run_id = hc.current_run_id(con)
    bible = json.loads(con.execute("SELECT story_json FROM story_bibles WHERE run_id = ?",
                                   [run_id]).fetchone()[0])
    rows = con.execute(f"SELECT {', '.join(LOG_COLS)} FROM decision_log WHERE run_id = ? "
                       "ORDER BY decision_id", [run_id]).fetchall()
    log = [dict(zip(LOG_COLS, r)) for r in rows]
    for d in log:
        d["memory_refs"] = json.loads(d["memory_refs"]) if d["memory_refs"] else {}
    out = hc.run_dir(run_id)
    hc.write_json(out / "story_bible.json", bible)
    hc.write_json(out / "decision_log.json", {"run_id": run_id, "decisions": log})
    hc.write_json(out / "rewritten_script.json", rewritten_script(bible))
    con.execute("UPDATE run_state SET status = 'exported' WHERE run_id = ?", [run_id])
    con.close()
    latest = hc.publish_latest(run_id)
    print(f"[export] wrote {out} and mirrored to {latest}")


main()
