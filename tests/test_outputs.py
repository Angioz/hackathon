"""Contract + judging-rule checks on real pipeline output (run_1 and run_2)."""
from conftest import CONTRACT, FILES, load, run_dir


def _keys(obj) -> set:
    return set(obj) if isinstance(obj, dict) else set()


def test_three_output_files_exist(run):
    for name in FILES:
        assert (run["dir"] / f"{name}.json").exists(), name


def test_outputs_match_contract(run):
    sample = {n: load(CONTRACT / f"{n}.json") for n in FILES}
    bible, log, script = run["story_bible"], run["decision_log"], run["rewritten_script"]
    assert _keys(sample["story_bible"]) <= _keys(bible)
    assert _keys(sample["story_bible"]["scenes"][0]) <= _keys(bible["scenes"][0])
    assert _keys(sample["story_bible"]["scenes"][0]["lines"][0]) <= _keys(bible["scenes"][0]["lines"][0])
    assert _keys(sample["decision_log"]["decisions"][0]) <= _keys(log["decisions"][0])
    assert _keys(sample["rewritten_script"]) <= _keys(script)
    assert _keys(sample["rewritten_script"]["lines"][0]) <= _keys(script["lines"][0])
    assert bible["run_id"] == log["run_id"] == script["run_id"]


def test_every_decision_has_a_why(run):
    for d in run["decision_log"]["decisions"]:
        assert (d.get("reasoning_why") or "").strip(), d["decision_id"]
        assert (d.get("decision_summary") or "").strip(), d["decision_id"]


def test_at_least_three_distinct_agents(run):
    assert len({d["agent_id"] for d in run["decision_log"]["decisions"]}) >= 3


def test_at_least_one_plot_twist(run):
    assert any(d["plot_twist_flag"] for d in run["decision_log"]["decisions"])
    assert run["story_bible"]["plot_twist"]["twist_id"]


def test_film_length_60_to_180_seconds(run):
    assert 60 <= run["story_bible"]["total_target_duration_sec"] <= 180
    wav = run["dir"] / "full_script_audio.wav"
    if wav.exists():  # once the voice spine has run, check the real audio too
        import wave
        with wave.open(str(wav)) as w:
            assert 60 <= w.getnframes() / w.getframerate() <= 180


def test_every_script_line_has_a_speaker_and_action(run):
    ids = {c["agent_id"] for c in run["story_bible"]["cast"]}
    for line in run["rewritten_script"]["lines"]:
        assert line["speaker_agent_id"] in ids and line["text"].strip()
        assert line["character_action"]["type"]


def test_run1_and_run2_differ():
    r1, r2 = (load(run_dir(r) / "story_bible.json") for r in ("run_1", "run_2"))
    assert r1["run_id"] != r2["run_id"]
    assert r1["plot_twist"]["twist_id"] != r2["plot_twist"]["twist_id"], "same twist"
    assert r1["ending"]["ending_id"] != r2["ending"]["ending_id"], "same ending"
