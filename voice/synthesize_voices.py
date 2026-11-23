"""Task 1 / FR-6: 4-voice spine from rewritten_script.json via ElevenLabs (free plan).

  py voice/synthesize_voices.py [--script output/latest/rewritten_script.json]

Per line: POST /v1/text-to-speech/{voice_id}/with-timestamps (pcm_24000), cached by
sha256(voice_id|model|text) in voice/.cache so reruns spend no characters.
Lines are stitched in order with a fixed silence gap (no stretching, no cutting).
Writes output/<run_id>/full_script_audio.wav (24 kHz mono 16-bit) and voice_words.json
[{word,start,end,speaker_agent_id,line_id}] on one global timeline; mirrors to output/latest.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
RATE = 24000
GAP_SEC = 0.30
API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=pcm_24000"
MIN_SEC, MAX_SEC = 60.0, 180.0


def load_env() -> None:
    env = ROOT / ".env.local"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def tts(voice_id: str, model: str, text: str) -> dict:
    """Return {'pcm': bytes, 'chars': [...], 'starts': [...], 'ends': [...]} (cached)."""
    key = hashlib.sha256(f"{voice_id}|{model}|{text}".encode()).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise SystemExit("ELEVENLABS_API_KEY missing in .env.local (and line not cached).")
        body = json.dumps({"text": text, "model_id": model}).encode()
        req = urllib.request.Request(API.format(voice_id=voice_id), data=body, method="POST",
                                     headers={"xi-api-key": api_key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"ElevenLabs {exc.code}: {exc.read().decode(errors='replace')[:300]}")
        CACHE.mkdir(exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    al = data.get("alignment") or data.get("normalized_alignment") or {}
    return {"pcm": base64.b64decode(data["audio_base64"]), "chars": al.get("characters", []),
            "starts": al.get("character_start_times_seconds", []),
            "ends": al.get("character_end_times_seconds", [])}


def words_from_alignment(chars, starts, ends) -> list[dict]:
    words, cur, w_start, w_end = [], "", None, None
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append({"word": cur, "start": w_start, "end": w_end})
            cur, w_start = "", None
            continue
        if not cur:
            w_start = s
        cur, w_end = cur + ch, e
    if cur:
        words.append({"word": cur, "start": w_start, "end": w_end})
    return words


def synthesize(script: dict, voice_map: dict, model: str) -> tuple[bytes, list[dict], list[dict]]:
    pcm, words, segments, t = bytearray(), [], [], 0.0
    gap = b"\x00\x00" * int(RATE * GAP_SEC)
    for i, line in enumerate(script["lines"]):
        spk = line["speaker_agent_id"]
        voice = voice_map[spk]["voice_id"]
        r = tts(voice, model, line["text"])
        dur = len(r["pcm"]) / 2 / RATE
        for w in words_from_alignment(r["chars"], r["starts"], r["ends"]):
            words.append({"word": w["word"], "start": round(t + w["start"], 3),
                          "end": round(t + min(w["end"], dur), 3),
                          "speaker_agent_id": spk, "line_id": line["line_id"]})
        segments.append({"line_id": line["line_id"], "speaker_agent_id": spk,
                         "start": round(t, 3), "end": round(t + dur, 3)})
        pcm += r["pcm"]
        t += dur
        if i < len(script["lines"]) - 1:
            pcm += gap
            t += GAP_SEC
    return bytes(pcm), words, segments


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(ROOT / "output" / "latest" / "rewritten_script.json"))
    ap.add_argument("--model", default=os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5"))
    args = ap.parse_args()
    load_env()
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    voice_map = json.loads((HERE / "voice_map.json").read_text(encoding="utf-8"))
    missing = {ln["speaker_agent_id"] for ln in script["lines"]} - set(voice_map)
    if missing:
        raise SystemExit(f"No voice mapped for {sorted(missing)}")

    pcm, words, segments = synthesize(script, voice_map, args.model)
    total = len(pcm) / 2 / RATE
    covered = {s["line_id"] for s in segments}
    uncovered = [ln["line_id"] for ln in script["lines"] if ln["line_id"] not in covered
                 or not any(w["line_id"] == ln["line_id"] for w in words)]

    out = ROOT / "output" / script["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out / "full_script_audio.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm)
    (out / "voice_words.json").write_text(json.dumps(words, indent=1), encoding="utf-8")
    (out / "voice_segments.json").write_text(json.dumps(segments, indent=1), encoding="utf-8")
    latest = ROOT / "output" / "latest"
    if latest.exists() and latest.resolve() != out.resolve():
        for name in ("full_script_audio.wav", "voice_words.json", "voice_segments.json"):
            shutil.copy2(out / name, latest / name)
    print(f"audio {total:.1f}s, {len(words)} words, {len(segments)}/{len(script['lines'])} lines -> {out}")

    if uncovered:
        print(f"GATE FAIL: lines without words: {uncovered}", file=sys.stderr)
        return 1
    if not MIN_SEC <= total <= MAX_SEC:
        print(f"GATE FAIL: duration {total:.1f}s outside {MIN_SEC}-{MAX_SEC}s", file=sys.stderr)
        return 1
    print("GATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
