"""FR-5: turn the room's decisions into a timed, staged Story Bible."""
from __future__ import annotations

import brain
from cast import AGENT_BY_ID, AGENT_IDS, AGENTS, EMOTIONS, POSES, SCENE_BEATS

SCHEMA_VERSION = "1.0.0"
WORDS_PER_SEC = 2.6
LINE_GAP_SEC = 0.35
SCENE_PAD_SEC = 1.0
MAX_LINE_WORDS = 22
LINE_ACTIONS = ["move_to", "interact", "look_at", "gesture"]
HUD_FOR_BEAT = {"hook": ("pitch",), "setup": ("pitch",), "conflict": ("pitch",),
                "twist": ("propose_twist", "react_twist"),
                "resolution": ("studio_rule", "vote_ending", "arbitrate"), "cta": ("arbitrate",)}


def script_schema() -> dict:
    line = {"type": "object", "properties": {
        "speaker_agent_id": {"type": "string", "enum": AGENT_IDS},
        "dialogue": {"type": "string"},
        "emotion": {"type": "string", "enum": EMOTIONS},
        "pose": {"type": "string", "enum": POSES},
        "action_type": {"type": "string", "enum": LINE_ACTIONS},
        "target_agent": {"type": "string", "enum": AGENT_IDS + ["none"]},
        "prop": {"type": "string"}},
        "required": ["speaker_agent_id", "dialogue", "emotion", "pose", "action_type",
                     "target_agent", "prop"], "additionalProperties": False}
    scene = {"type": "object", "properties": {
        "beat": {"type": "string", "enum": SCENE_BEATS}, "setting": {"type": "string"},
        "lines": {"type": "array", "items": line}},
        "required": ["beat", "setting", "lines"], "additionalProperties": False}
    return {"type": "object", "properties": {
        "title": {"type": "string"}, "logline": {"type": "string"},
        "scenes": {"type": "array", "items": scene}},
        "required": ["title", "logline", "scenes"], "additionalProperties": False}


def _valid(script: dict) -> bool:
    beats = [s["beat"] for s in script.get("scenes", [])]
    lines = [ln for s in script.get("scenes", []) for ln in s["lines"]]
    words = sum(len(ln["dialogue"].split()) for ln in lines)
    speakers = {ln["speaker_agent_id"] for ln in lines}
    return (5 <= len(beats) <= 6 and "twist" in beats and len(speakers) >= 4
            and 170 <= words <= 290 and all(s["lines"] for s in script["scenes"]))


def write_script(room, outcome: dict) -> tuple[dict, str]:
    decisions = "\n".join(f"{d['decision_id']} R{d['round']} {d['agent_id']} {d['action_type']}: "
                          f"{d['decision_summary']} WHY: {d['reasoning_why']}" for d in room.decisions)
    cast = "\n".join(f"{a['agent_id']}: {a['role']}; {a['personality']} Prop: {a['prop']}." for a in AGENTS)
    system = ("You are the Director, turning a writers' room debate into a tight animated-film script. "
              "Keep every agent in character and keep the conflict; do not invent capabilities the "
              "commit does not show.")
    from room import feature_brief
    user = (f"{feature_brief(room.feature)}\n\nCAST:\n{cast}\n\nDECISION LOG:\n{decisions}\n\n"
            f"LOCKED: twist = {outcome['twist']['label']} ({outcome['twist']['description']}); "
            f"ending = {outcome['ending']['label']} ({outcome['ending']['description']}).\n\n"
            "Write 6 scenes in this beat order: hook, setup, conflict, twist, resolution, cta. "
            "3-4 lines per scene, every line at most 16 words, 200-250 spoken words in total, all four "
            "agents speak. The hook must grab attention in the first line. Every line has a visible "
            "action: move_to (walk toward target_agent or centre), interact (hand/strike a prop with "
            "target_agent), look_at, or gesture. Use each agent's own prop.")
    ctx = {"rng": room.rng, "feature": room.feature, "twist": outcome["twist"], "ending": outcome["ending"]}
    script, used = brain.think("script", system, user, script_schema(), ctx)
    if used == "claude" and not _valid(script):
        print("[staging] Claude script failed structure checks; using offline script template.")
        import stub_brain
        script, used = stub_brain.generate("script", ctx), "offline"
    return script, used


def stage(script: dict, room, outcome: dict) -> dict:
    pos = {a["agent_id"]: {"x": a["home_x"], "y": 0.78, "z": 0.0} for a in AGENTS}
    t, scenes, n = 0.0, [], 0
    for si, sc in enumerate(script["scenes"], start=1):
        start_scene, lines = t, []
        t += SCENE_PAD_SEC / 2
        for ln in sc["lines"]:
            n += 1
            words = ln["dialogue"].split()
            if len(words) > MAX_LINE_WORDS:
                ln["dialogue"] = " ".join(words[:MAX_LINE_WORDS])
            spk, tgt = ln["speaker_agent_id"], ln["target_agent"]
            tgt = tgt if tgt in AGENT_BY_ID and tgt != spk else None
            frm = dict(pos[spk])
            if ln["action_type"] == "move_to":
                to_x = pos[tgt]["x"] + (0.09 if pos[tgt]["x"] < frm["x"] else -0.09) if tgt else 0.5
                pos[spk] = {"x": round(min(0.92, max(0.08, to_x)), 3), "y": 0.78,
                            "z": round(room.rng.uniform(-0.15, 0.15), 3)}
            dur = round(max(1.6, len(ln["dialogue"].split()) / WORDS_PER_SEC), 2)
            lines.append({
                "line_id": f"L{n:02d}", "speaker_agent_id": spk, "dialogue": ln["dialogue"],
                "emotion": ln["emotion"], "pose": ln["pose"],
                "character_action": {"type": ln["action_type"], "target_agent": tgt,
                                     "prop": ln.get("prop") or None,
                                     "from": frm, "to": dict(pos[spk]),
                                     "look_at": tgt or ("camera" if sc["beat"] in ("hook", "cta") else None)},
                "est_start_sec": round(t, 2), "est_duration_sec": dur})
            t += dur + LINE_GAP_SEC
        t += SCENE_PAD_SEC / 2
        hud = [d["decision_id"] for d in room.decisions if d["action_type"] in HUD_FOR_BEAT.get(sc["beat"], ())]
        if sc["beat"] in ("hook", "setup", "conflict"):  # spread the 4 pitches over the opening scenes
            k = ("hook", "setup", "conflict").index(sc["beat"])
            hud = hud[k::3] or hud[:1]
        scenes.append({"scene_id": f"S{si}", "beat": sc["beat"], "setting": sc["setting"],
                       "est_start_sec": round(start_scene, 2), "est_duration_sec": round(t - start_scene, 2),
                       "positions_at_end": {k: dict(v) for k, v in pos.items()},
                       "hud_decision_ids": hud, "lines": lines})
    return {"scenes": scenes, "total": round(t, 2)}


def build_story_bible(room, outcome: dict, script: dict, script_brain: str) -> dict:
    staged = stage(script, room, outcome)
    brains = sorted({d["brain"] for d in room.decisions} | {script_brain})
    return {
        "schema_version": SCHEMA_VERSION, "run_id": room.run_id,
        "commit_sha": room.feature["commit_sha"], "feature_title": room.feature["title"],
        "title": script["title"], "logline": script["logline"],
        "canvas": {"width": 1280, "height": 720, "fps": 30, "layout": "16:9_split_stage",
                   "stage_coords": "x,y normalized 0-1 within the left 70% stage; z depth -1..1"},
        "brain_modes": brains,
        "cast": [{k: a[k] for k in ("agent_id", "display_name", "role", "gender", "voice_profile",
                                     "avatar_rig_id", "color", "prop")} |
                 {"home": {"x": a["home_x"], "y": 0.78, "z": 0.0}} for a in AGENTS],
        "plot_twist": {**outcome["twist"], "proposed_by": "Critic",
                       "decision_id": next(d["decision_id"] for d in room.decisions
                                           if d["action_type"] == "propose_twist")},
        "ending": {**outcome["ending"], "decided_by": "Director",
                   "votes": outcome["votes"], "weighted_tally": outcome["tally"]},
        "total_target_duration_sec": staged["total"],
        "timing_note": "est_* values assume 2.6 words/sec; the Voice Spine's real timestamps override them.",
        "scenes": staged["scenes"],
    }
