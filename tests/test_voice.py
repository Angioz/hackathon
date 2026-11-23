"""Voice spine stitching (Task 1) with a fake TTS: no network, no characters spent."""
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "voice"))
import synthesize_voices as sv  # noqa: E402


def fake_tts(voice_id, model, text):
    chars, starts, ends, t = [], [], [], 0.05
    for ch in text:
        d = 0.0 if ch.isspace() else 0.06
        chars.append(ch); starts.append(t); ends.append(t + d); t += d or 0.05
    return {"pcm": b"\x00\x00" * int(sv.RATE * (t + 0.1)), "chars": chars, "starts": starts, "ends": ends}


def test_stitched_timeline_is_contiguous_and_complete(monkeypatch):
    monkeypatch.setattr(sv, "tts", fake_tts)
    script = {"lines": [{"line_id": "L01", "speaker_agent_id": "Dev", "text": "Ship the diff."},
                        {"line_id": "L02", "speaker_agent_id": "Critic", "text": "Not before I break it."}]}
    vmap = {"Dev": {"voice_id": "a"}, "Critic": {"voice_id": "b"}}
    pcm, words, segs = sv.synthesize(script, vmap, "m")
    assert [w["word"] for w in words] == ["Ship", "the", "diff.", "Not", "before", "I", "break", "it."]
    assert all(a["end"] <= b["start"] for a, b in zip(words, words[1:]))
    assert segs[1]["start"] >= segs[0]["end"] + sv.GAP_SEC - 1e-3   # gap kept, nothing overlaps
    assert {w["speaker_agent_id"] for w in words} == {"Dev", "Critic"}
    assert abs(len(pcm) / 2 / sv.RATE - segs[-1]["end"]) < 0.01       # audio length == timeline
