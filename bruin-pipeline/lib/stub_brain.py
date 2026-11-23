"""Offline stand-in brain: template-driven, seeded by the run's RNG.

Used when no API key is set or a Claude call fails, so the pipeline (and a live
demo) never stalls. Every decision it makes is tagged brain='offline' in the log.
"""
from __future__ import annotations

import re

from cast import AGENT_BY_ID, ENDING_BY_ID, TWIST_BY_ID

PITCH = {
    "Dev": ["Lead with what the diff actually changes in {files}.",
            "Show the code path first; the hype can wait.",
            "Open on the before-and-after of {short}."],
    "Growth": ["Open with '{short} changes everything' over a rocket launch.",
               "Hook them with a countdown: ten seconds to the future.",
               "Make the first line a promise: this saves you hours."],
    "Critic": ["Open on a user trying to break {short}.",
               "Start with the bug everyone is afraid of.",
               "Lead with doubt; earn the payoff later."],
    "Director": ["Cold open on the merge button, then cut to the room.",
                 "One shot: all four of us circling the diff.",
                 "Start mid-argument; the audience catches up."],
}
LINES = {
    "pitch": {
        "Dev": "Before anyone says revolutionary, look at {files}.",
        "Growth": "Picture it: {short}, and the whole internet notices!",
        "Critic": "Cute. I give it ten seconds before something breaks.",
        "Director": "Places, everyone. This merge is our opening scene.",
    },
    "react_support": "Fine. That twist is exactly the test we need.",
    "react_oppose": "No. That twist makes us look reckless.",
}


def _short(feature: dict) -> str:
    title = re.sub(r"^\w+(\([^)]*\))?!?:\s*", "", feature.get("title") or "") or "the new feature"
    return " ".join(title.split()[:6]).rstrip(",.;:")


def _files(feature: dict) -> str:
    files = feature.get("changed_files") or []
    return ", ".join(f.split("/")[-1] for f in files[:2]) or "the diff"


def _fmt(text: str, feature: dict) -> str:
    return text.format(short=_short(feature), files=_files(feature))


def _turn(summary, why, dialogue, emotion, target="none", stance="neutral", choice=""):
    return {"decision_summary": summary, "reasoning_why": why, "dialogue": dialogue,
            "emotion": emotion, "target_agent": target, "stance": stance, "choice": choice}


def generate(kind: str, ctx: dict) -> dict:
    rng, feature = ctx["rng"], ctx["feature"]
    agent = ctx.get("agent") or {}
    aid = agent.get("agent_id", "Director")
    if kind == "pitch":
        rival = rng.choice([a for a in AGENT_BY_ID if a != aid])
        return _turn(_fmt(rng.choice(PITCH[aid]), feature),
                     f"{agent['goal']} Memory says: {ctx.get('memory_hint', 'first run')}.",
                     _fmt(LINES["pitch"][aid], feature), rng.choice(["excited", "skeptical", "proud"]),
                     rival, rng.choice(["support", "oppose"]))
    if kind == "propose_twist":
        tid = rng.choice(ctx["options"])
        t = TWIST_BY_ID[tid]
        return _turn(f"Inject twist: {t['label']}.",
                     f"{t['description']} It tests {_short(feature)} where the pitch was weakest.",
                     f"Plot twist: {t['label'].lower()}. Now what?", "amused", "Growth", "oppose", tid)
    if kind == "react_twist":
        stance = rng.choice(["support", "oppose"])
        why = ("It forces the feature to prove itself." if stance == "support"
               else "It distracts from what the code really does.")
        return _turn(f"{stance.title()} the {ctx['twist']['label']} twist.", why,
                     LINES["react_" + stance], "worried" if stance == "oppose" else "excited",
                     "Critic", stance)
    if kind == "vote_ending":
        eid = ctx.get("preferred") or rng.choice(ctx["options"])
        e = ENDING_BY_ID[eid]
        return _turn(f"Vote for ending: {e['label']}.",
                     f"{e['description']} That fits my goal: {agent['goal']}",
                     f"My vote? {e['label']}.", "proud", "Director", "support", eid)
    if kind == "arbitrate":
        eid = ctx["tally_winner"]
        e = ENDING_BY_ID[eid]
        return _turn(f"Final ending: {e['label']}.",
                     f"Weighted vote favoured it ({ctx['tally_text']}) and it differs from last run.",
                     f"Decision made. We end on: {e['label'].lower()}.", "proud",
                     "none", "neutral", eid)
    if kind == "script":
        return _script(ctx)
    raise ValueError(f"unknown kind {kind}")


def _script(ctx: dict) -> dict:
    f, twist, ending = ctx["feature"], ctx["twist"], ctx["ending"]
    s, fl = _short(f), _files(f)
    L = lambda spk, txt, emo, pose, act, tgt="none", prop="": {  # noqa: E731
        "speaker_agent_id": spk, "dialogue": txt, "emotion": emo, "pose": pose,
        "action_type": act, "target_agent": tgt, "prop": prop}
    scenes = [
        ("hook", "Launch stage, merge button glowing", [
            L("Growth", f"Stop scrolling. {s} just landed, and it is big.", "excited", "celebrate", "move_to", "none", "megaphone"),
            L("Dev", "It is a merge, not a moon landing. Calm down.", "skeptical", "talk", "look_at", "Growth"),
            L("Director", "Perfect tension. Roll camera, everyone in.", "proud", "debate", "gesture", "none", "clapperboard")]),
        ("setup", "Around the glowing diff cube", [
            L("Dev", f"Here is what changed: {fl}. Clean and tested.", "proud", "inspect_code", "interact", "Critic", "git_diff_cube"),
            L("Critic", "Tested by whom? I have questions.", "skeptical", "debate", "move_to", "Dev"),
            L("Growth", "Questions are engagement. I love questions.", "excited", "talk", "look_at", "Critic"),
            L("Director", "Dev, keep it simple. Growth, keep it honest.", "neutral", "talk", "gesture")]),
        ("conflict", "Split stage, two camps", [
            L("Growth", "Tagline: the feature that changes everything.", "excited", "celebrate", "move_to", "Director"),
            L("Dev", "Changes everything? It changes exactly what the diff says.", "angry", "debate", "interact", "Growth", "git_diff_cube"),
            L("Critic", "And I can break it. Watch.", "amused", "inspect_code", "interact", "Dev", "bug_hammer"),
            L("Director", "Hold that. Critic, show us.", "neutral", "talk", "look_at", "Critic")]),
        ("twist", "Lights flicker red", [
            L("Critic", f"Plot twist: {twist['label'].lower()}.", "amused", "shocked", "interact", "Growth", "bug_hammer"),
            L("Growth", "That was not in the launch plan!", "worried", "shocked", "move_to", "Dev"),
            L("Dev", "Good. Now we find out if the code is real.", "proud", "inspect_code", "interact", "Critic", "git_diff_cube"),
            L("Director", "This is the scene. Nobody leaves.", "excited", "debate", "gesture", "none", "clapperboard")]),
        ("resolution", "Spotlight centre stage", [
            L("Director", f"The room has voted. We end on {ending['label'].lower()}.", "proud", "talk", "move_to"),
            L("Dev", "Then we say what it does, and nothing more.", "neutral", "talk", "look_at", "Director"),
            L("Critic", "Fine. It survived me. Barely.", "amused", "celebrate", "interact", "Dev"),
            L("Growth", "Honest and exciting. I can sell that.", "excited", "celebrate", "interact", "Critic", "megaphone")]),
        ("cta", "All four in frame, logo up", [
            L("Growth", f"{s}. Live today. Go try it.", "excited", "celebrate", "move_to", "none", "megaphone"),
            L("Director", "Cut. That is a wrap.", "proud", "celebrate", "gesture", "none", "clapperboard"),
            L("Dev", "Ship it.", "proud", "celebrate", "look_at", "Growth")]),
    ]
    return {"title": f"{s}: The Launch Room",
            "logline": f"Four agents fight over how to launch {s}, until {twist['label'].lower()} forces the truth.",
            "scenes": [{"beat": b, "setting": st, "lines": ls} for b, st, ls in scenes]}
