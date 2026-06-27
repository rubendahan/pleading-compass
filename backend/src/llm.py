"""Multi-provider LLM helper (shared by every LLM judge).

Backends, first available wins:
  * Anthropic  (ANTHROPIC_API_KEY, LLM_MODEL default claude-sonnet-4-6) via the
    official `anthropic` SDK.
  * OpenRouter (OPENROUTER_API_KEY, OPENROUTER_MODEL default a free Nemotron),
    base https://openrouter.ai/api/v1, via raw HTTP.
  * No key -> callers fall back to the deterministic offline stub judge.

Keys come from the environment ONLY — never hard-coded.
"""
from __future__ import annotations

import json
import os
import re

DEFAULT_MODEL = "claude-sonnet-4-6"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-nano-9b-v2:free"


def active_backend(force_stub: bool = False) -> str:
    if force_stub:
        return "offline stub"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    return "offline stub"


def chat(system: str, user: str, *, model: str | None = None, max_tokens: int = 1200) -> tuple[str, str]:
    """Return (text, backend_label). Raises if no backend key is configured."""
    backend = active_backend()
    if backend == "anthropic":
        return _anthropic(system, user, model or os.getenv("LLM_MODEL", DEFAULT_MODEL), max_tokens)
    if backend == "openrouter":
        return _openrouter(system, user, model or os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL), max_tokens)
    raise RuntimeError("No LLM backend configured (set ANTHROPIC_API_KEY or OPENROUTER_API_KEY).")


def _anthropic(system: str, user: str, model: str, max_tokens: int) -> tuple[str, str]:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return text, f"anthropic:{model}"


def _openrouter(system: str, user: str, model: str, max_tokens: int) -> tuple[str, str]:
    import requests
    key = os.environ["OPENROUTER_API_KEY"]
    resp = requests.post(
        OPENROUTER_BASE + "/chat/completions",
        headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "HTTP-Referer": "https://hackthelaw.local/cms-pleading-proof",
            "X-Title": "CMS Pleading-to-Proof",
        },
        json={
            "model": model, "max_tokens": max_tokens, "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"], f"openrouter:{model}"


def parse_json(text: str):
    """Parse a JSON object/array from model output, tolerating ``` fences/prose."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            return json.loads(m.group(1))
        raise
