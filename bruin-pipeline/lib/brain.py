"""LLM brain for the Launch Studio Agents.

HACK_BRAIN=claude  -> always call Claude (fails loudly if the call fails)
HACK_BRAIN=offline -> deterministic-template stand-in, no network (demo failover)
HACK_BRAIN=auto    -> Claude when ANTHROPIC_API_KEY is set, offline stand-in otherwise
                      or when a single Claude call fails (the fallback is logged).
"""
from __future__ import annotations

import json
import os
import sys

import stub_brain

MODEL = os.environ.get("HACK_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("HACK_EFFORT", "low")


def mode() -> str:
    wanted = os.environ.get("HACK_BRAIN", "auto").lower()
    if wanted == "auto":
        return "claude" if os.environ.get("ANTHROPIC_API_KEY") else "offline"
    return wanted


_client = None


def _claude(system: str, user: str, schema: dict) -> dict:
    global _client
    import anthropic

    if _client is None:
        _client = anthropic.Anthropic(max_retries=3, timeout=120)
    response = _client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": EFFORT,
            "format": {"type": "json_schema", "schema": schema},
        },
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined this turn (refusal).")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude output truncated (max_tokens).")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def think(kind: str, system: str, user: str, schema: dict, stub_ctx: dict) -> tuple[dict, str]:
    """Return (result, brain_used). brain_used is 'claude' or 'offline'."""
    current = mode()
    if current == "claude" or (current != "offline" and os.environ.get("ANTHROPIC_API_KEY")):
        try:
            return _claude(system, user, schema), "claude"
        except Exception as exc:  # noqa: BLE001 - zero-HITL: log and fall back
            if os.environ.get("HACK_BRAIN", "auto").lower() == "claude":
                raise
            print(f"[brain] Claude call failed for {kind} ({type(exc).__name__}: {exc}); "
                  "using offline stand-in for this turn.", file=sys.stderr)
    return stub_brain.generate(kind, stub_ctx), "offline"
