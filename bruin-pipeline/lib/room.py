"""FR-3: the 4-round Writers' Room Simulation with persistent memory."""
from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor

import brain
import live
from cast import (ACTION_TYPES, AGENT_BY_ID, AGENT_IDS, AGENTS, EMOTIONS,
                  ENDING_BY_ID, ENDINGS, TWIST_BY_ID, TWISTS)

STANCES = ["support", "oppose", "neutral"]


def turn_schema(choices: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "decision_summary": {"type": "string", "description": "What you decide, one sentence."},
            "reasoning_why": {"type": "string", "description": "Why, citing your goal, the diff or your memory."},
            "dialogue": {"type": "string", "description": "Your spoken line for the film, max 16 words."},
            "emotion": {"type": "string", "enum": EMOTIONS},
            "target_agent": {"type": "string", "enum": AGENT_IDS + ["none"]},
            "stance": {"type": "string", "enum": STANCES},
            "choice": {"type": "string", "enum": choices or [""]},
        },
        "required": ["decision_summary", "reasoning_why", "dialogue", "emotion",
                     "target_agent", "stance", "choice"],
        "additionalProperties": False,
    }


def persona(agent: dict) -> str:
    return (
        f"You are {agent['display_name']}, the {agent['role']}, in an AI writers' room deciding how "
        "to tell a 75-105 second animated launch film about a real code merge. "
        f"Your goal: {agent['goal']} Your secret goal: {agent['secret_goal']} "
        f"Personality: {agent['personality']} Stay in character. Disagree whenever your goal "
        "demands it; never agree just to be polite. Never claim the feature does anything the "
        "commit and diff below do not show. Keep dialogue punchy, at most 16 words."
    )


def feature_brief(f: dict) -> str:
    files = ", ".join(f.get("changed_files", [])[:12]) or "(not listed)"
    return (f"COMMIT {f['commit_sha'][:7]} by {f.get('author', '?')}\nTITLE: {f['title']}\n"
            f"BODY: {f.get('body') or '-'}\nFILES: {files}\nSTAT: {f.get('diff_summary', '')}\n"
            f"DIFF EXCERPT:\n{(f.get('diff_excerpt') or '')[:7000]}")


def memory_hint(mem: dict) -> str:
    weights = mem["alliance_weights"]
    ally = max(weights, key=weights.get) if weights else "nobody"
    rival = min(weights, key=weights.get) if weights else "nobody"
    return (f"{mem['memory_reflection']} Most trusted: {ally} ({weights.get(ally, 0.5):.2f}). "
            f"Least trusted: {rival} ({weights.get(rival, 0.5):.2f}). "
            f"Past twists: {mem['preferred_twist_history'][-3:]}. Past endings: {mem['ending_history'][-3:]}.")


class Room:
    def __init__(self, run_id: str, feature: dict, memory: dict):
        self.run_id, self.feature, self.memory = run_id, feature, memory
        self.rng = random.Random(run_id)
        self.decisions: list[dict] = []

    def transcript(self) -> str:
        if not self.decisions:
            return "(nothing said yet)"
        return "\n".join(f"R{d['round']} {d['agent_id']} [{d['action_type']}]: {d['decision_summary']} "
                         f"-- \"{d['dialogue']}\"" for d in self.decisions[-12:])

    def ask(self, agent_id: str, kind: str, task: str, choices: list[str], **stub) -> dict:
        agent = AGENT_BY_ID[agent_id]
        user = (f"{feature_brief(self.feature)}\n\nYOUR MEMORY FROM PAST RUNS: "
                f"{memory_hint(self.memory[agent_id])}\n\nROOM SO FAR:\n{self.transcript()}\n\nTASK: {task}")
        ctx = {"rng": self.rng, "feature": self.feature, "agent": agent, "options": choices,
               "memory_hint": self.memory[agent_id]["memory_reflection"], **stub}
        result, used = brain.think(kind, persona(agent), user, turn_schema(choices), ctx, agent_id)
        result["llm_mode"] = used
        return result

    def ask_many(self, jobs: list[tuple]) -> list[dict]:
        """Run independent turns (same round) concurrently when a live brain is used."""
        if brain.mode() == "offline":
            return [self.ask(*j[:4], **(j[4] if len(j) > 4 else {})) for j in jobs]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = [pool.submit(self.ask, *j[:4], **(j[4] if len(j) > 4 else {})) for j in jobs]
            return [f.result() for f in futs]

    def log(self, rnd: int, agent_id: str, action_type: str, r: dict, *, twist=False, accepted=True) -> dict:
        assert action_type in ACTION_TYPES
        d = {"decision_id": f"d{len(self.decisions) + 1:02d}", "run_id": self.run_id, "round": rnd,
             "beat_id": f"r{rnd}_{agent_id.lower()}_{action_type}", "agent_id": agent_id,
             "action_type": action_type, "target_agent": r.get("target_agent", "none"),
             "decision_summary": r["decision_summary"].strip(),
             "reasoning_why": r["reasoning_why"].strip(), "dialogue": r.get("dialogue", "").strip(),
             "emotion": r.get("emotion", "neutral"), "stance": r.get("stance", "neutral"),
             "choice": r.get("choice", ""), "plot_twist_flag": twist, "accepted": accepted,
             "llm_mode": r.get("llm_mode", "rule"),
             "memory_refs": json.dumps({"memory_run": self.memory[agent_id]["run_id"]})}
        self.decisions.append(d)
        live.emit("decision", **{k: d[k] for k in ("decision_id", "round", "agent_id", "action_type",
                  "target_agent", "decision_summary", "reasoning_why", "dialogue", "emotion", "stance",
                  "choice", "plot_twist_flag", "llm_mode")})
        return d

    def simulate(self) -> dict:
        # Round 1 - pitches: each agent argues for a framing.
        live.emit("round", round=1, label="Pitch: how should we launch this?")
        order = AGENT_IDS[:]
        self.rng.shuffle(order)
        task = ("Pitch how the film should open and frame this feature. "
                "Name one agent you support or oppose (target_agent + stance).")
        for aid, r in zip(order, self.ask_many([(aid, "pitch", task, []) for aid in order])):
            self.log(1, aid, "pitch", r)

        # Round 2 - Critic injects a twist; studio memory bans recently used twists.
        live.emit("round", round=2, label="Plot twist: the Critic strikes")
        recent = [t for m in self.memory.values() for t in m["preferred_twist_history"][-2:]]
        twist_opts = [t["twist_id"] for t in TWISTS if t["twist_id"] not in recent] or \
            [t["twist_id"] for t in TWISTS]
        menu = "; ".join(f"{t}: {TWIST_BY_ID[t]['description']}" for t in twist_opts)
        r = self.ask("Critic", "propose_twist", f"Choose the mid-film plot twist from: {menu}. "
                     "Pick the one that best exposes a real weakness of this feature.", twist_opts)
        twist = TWIST_BY_ID[r["choice"] if r["choice"] in twist_opts else twist_opts[0]]
        self.log(2, "Critic", "propose_twist", r, twist=True)
        reactors = [a for a in AGENT_IDS if a != "Critic"]
        task = (f"The Critic proposes the twist '{twist['label']}': "
                f"{twist['description']} Support or oppose it, in character.")
        for aid, r in zip(reactors, self.ask_many([(a, "react_twist", task, [], {"twist": twist})
                                                   for a in reactors])):
            r["stance"] = r["stance"] if r["stance"] in ("support", "oppose") else "support"
            self.log(2, aid, "react_twist", r, twist=True)

        # Studio rule (Director's secret goal): never repeat last run's ending.
        last_endings = self.memory["Director"]["ending_history"][-1:]
        end_opts = [e["ending_id"] for e in ENDINGS if e["ending_id"] not in last_endings]
        if last_endings:
            self.log(3, "Director", "studio_rule", {
                "decision_summary": f"Ban last film's ending ({ENDING_BY_ID[last_endings[0]]['label']}).",
                "reasoning_why": "Agent memory shows we used it last run; repeating it would make "
                                 "this film a rerun.", "dialogue": "", "llm_mode": "rule"})

        # Round 3 - everyone votes on the ending.
        live.emit("round", round=3, label="Vote: how does it end?")
        menu = "; ".join(f"{e}: {ENDING_BY_ID[e]['description']}" for e in end_opts)
        votes = {}
        task = (f"The twist is '{twist['label']}'. Vote for the ending "
                f"from: {menu}. Argue for it in character.")
        for aid, r in zip(AGENT_IDS, self.ask_many([(a, "vote_ending", task, end_opts) for a in AGENT_IDS])):
            votes[aid] = r["choice"] if r["choice"] in end_opts else end_opts[0]
            r["choice"] = votes[aid]
            self.log(3, aid, "vote_ending", r)

        # Round 4 - Director arbitrates; vote weight = 1 + Director's trust in the voter.
        live.emit("round", round=4, label="The Director decides")
        trust = self.memory["Director"]["alliance_weights"]
        tally: dict[str, float] = {}
        for aid, eid in votes.items():
            tally[eid] = tally.get(eid, 0) + 1 + (trust.get(aid, 0.5) if aid != "Director" else 0.5)
        winner = max(sorted(tally), key=tally.get)
        tally_text = ", ".join(f"{e}={w:.2f}" for e, w in sorted(tally.items(), key=lambda x: -x[1]))
        r = self.ask("Director", "arbitrate", f"Weighted vote tally (votes x your trust): {tally_text}. "
                     "Decide the final ending. Your reasoning must cite the tally.", end_opts,
                     tally_winner=winner, tally_text=tally_text)
        ending = ENDING_BY_ID[r["choice"] if r["choice"] in end_opts else winner]
        r["choice"] = ending["ending_id"]
        self.log(4, "Director", "arbitrate", r)
        for d in self.decisions:
            if d["action_type"] == "vote_ending":
                d["accepted"] = d["choice"] == ending["ending_id"]
        return {"twist": twist, "ending": ending, "votes": votes, "tally": tally}

    def updated_memory(self, outcome: dict) -> list[dict]:
        stance = {d["agent_id"]: d["stance"] for d in self.decisions if d["action_type"] == "react_twist"}
        stance["Critic"] = "support"
        rows = []
        for aid in AGENT_IDS:
            m = self.memory[aid]
            w = dict(m["alliance_weights"])
            for other in w:
                delta = 0.10 if stance.get(other) == stance.get(aid) else -0.10
                delta += 0.15 if outcome["votes"][other] == outcome["votes"][aid] else -0.05
                w[other] = round(min(1.0, max(0.0, w[other] + delta)), 3)
            won = outcome["votes"][aid] == outcome["ending"]["ending_id"]
            ally, rival = max(w, key=w.get), min(w, key=w.get)
            reflection = (f"Run {self.run_id[-12:]}: I voted {outcome['votes'][aid]}; the room chose "
                          f"{outcome['ending']['ending_id']} after the {outcome['twist']['twist_id']} twist. "
                          f"{'I won that fight.' if won else 'I lost that fight and will push harder.'} "
                          f"I now trust {ally} most and {rival} least.")
            rows.append({"run_id": self.run_id, "agent_id": aid, "memory_reflection": reflection,
                         "alliance_weights": w,
                         "preferred_twist_history": m["preferred_twist_history"] + [outcome["twist"]["twist_id"]],
                         "ending_history": m["ending_history"] + [outcome["ending"]["ending_id"]],
                         "wins": m["wins"] + int(won)})
        return rows


def load_memory(con) -> dict:
    rows = con.execute("""SELECT run_id, agent_id, memory_reflection, alliance_weights,
        preferred_twist_history, ending_history, wins FROM agent_memory
        QUALIFY ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY created_at DESC, run_id DESC) = 1""").fetchall()
    mem = {}
    for run_id, aid, refl, w, th, eh, wins in rows:
        mem[aid] = {"run_id": run_id, "memory_reflection": refl, "alliance_weights": json.loads(w),
                    "preferred_twist_history": json.loads(th), "ending_history": json.loads(eh),
                    "wins": wins}
    missing = [a["agent_id"] for a in AGENTS if a["agent_id"] not in mem]
    if missing:
        raise RuntimeError(f"No memory for {missing}; run seed_agents_and_memory first.")
    return mem
