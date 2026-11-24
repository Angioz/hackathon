"""Brain for the Launch Studio Agents. Every turn records which brain answered (llm_mode).

HACK_BRAIN=bruin   -> Bruin Cloud agents (bruin_brain.py; uses Bruin credits)
HACK_BRAIN=llm     -> OpenAI-compatible chat API: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
HACK_BRAIN=offline -> template stand-in (stub_brain.py), no network
HACK_BRAIN=auto    -> llm (e.g. Claude via Runware) first, Bruin agents as backup, else offline

Live turns: strict JSON schema, one retry on invalid output, then automatic fallback to
the stub for that turn (recorded as llm_mode='offline_fallback').
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

import bruin_brain
import stub_brain

LLM_TIMEOUT_SEC = 25          # one agent turn
LLM_SCRIPT_TIMEOUT_SEC = 120  # the Director writing the whole script is a much longer answer
LLM_MAX_TOKENS = 4000         # reasoning models (e.g. deepseek-v4-1-flash) need >= 3000 to think and answer
LLM_SCRIPT_MAX_TOKENS = 8000


def mode() -> str:
    wanted = os.environ.get("HACK_BRAIN", "auto").lower()
    if wanted != "auto":
        return wanted
    if llm_configured():
        return "llm"
    if bruin_brain.available():
        return "bruin"
    return "offline"


def llm_configured() -> bool:
    return all(os.environ.get(k) for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))


def model_label() -> str:
    m = mode()
    return {"bruin": "bruin-cloud-agents", "llm": os.environ.get("LLM_MODEL", "?")}.get(m, "stub")


def _llm(system: str, user: str, schema: dict, timeout: float = LLM_TIMEOUT_SEC,
         max_tokens: int = LLM_MAX_TOKENS) -> dict:
    url = os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions"
    body = {
        "model": os.environ["LLM_MODEL"],
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system + " Reply with JSON only. Use plain ASCII punctuation (no em dashes or smart quotes)."},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "turn", "schema": schema, "strict": True}},
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"] or ""
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return clean(json.loads(text))


def clean(value):
    """Replace mangled characters some models emit (U+FFFD) and smart punctuation."""
    if isinstance(value, str):
        for bad, good in (("�", " - "), ("—", " - "), ("–", "-"), ("’", "'"),
                          ("‘", "'"), ("“", '"'), ("”", '"')):
            value = value.replace(bad, good)
        return " ".join(value.split())
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    return value


def conforms(value, schema: dict) -> bool:
    """Minimal JSON-schema check for the subset we use (object/array/string + enum)."""
    t = schema.get("type")
    if t == "object":
        if not isinstance(value, dict):
            return False
        props = schema.get("properties", {})
        if any(k not in value for k in schema.get("required", [])):
            return False
        return all(conforms(value[k], props[k]) for k in value if k in props)
    if t == "array":
        return isinstance(value, list) and all(conforms(v, schema.get("items", {})) for v in value)
    if t == "string":
        return isinstance(value, str) and ("enum" not in schema or value in schema["enum"])
    return True


def think(kind: str, system: str, user: str, schema: dict, stub_ctx: dict,
          agent_id: str | None = None) -> tuple[dict, str]:
    """Return (result, llm_mode): 'bruin' | 'llm' | 'offline' | 'offline_fallback'."""
    current = mode()
    if current == "offline":
        return stub_brain.generate(kind, stub_ctx), "offline"
    chain = [current]
    if current == "llm" and os.environ.get("HACK_BRAIN", "auto").lower() == "auto" and bruin_brain.available():
        chain.append("bruin")  # backup brain
    aid = agent_id or (stub_ctx.get("agent") or {}).get("agent_id") or "Director"
    for live in chain:
        last_err = None
        for _attempt in range(2):  # one retry on invalid output
            try:
                result = (bruin_brain.ask(aid, system, user, schema) if live == "bruin"
                          else _llm(system, user, schema,
                                     LLM_SCRIPT_TIMEOUT_SEC if kind == "script" else LLM_TIMEOUT_SEC,
                                     LLM_SCRIPT_MAX_TOKENS if kind == "script" else LLM_MAX_TOKENS))
                if conforms(result, schema):
                    return result, live
                last_err = "output did not match schema"
            except (json.JSONDecodeError, ValueError) as exc:
                last_err = f"invalid JSON: {exc}"
            except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, KeyError) as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                break  # transport errors: move to the next brain
        print(f"[brain] {live} failed for {aid}/{kind} ({last_err}).", file=sys.stderr)
    return stub_brain.generate(kind, stub_ctx), "offline_fallback"
