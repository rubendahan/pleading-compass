"""LLM seam — Claude (anthropic) OR OpenAI, with an offline stub.

Provider is picked from the environment: ``ANTHROPIC_API_KEY`` → Claude;
else ``OPENAI_API_KEY`` → OpenAI (``gpt-4o-mini`` by default, structured outputs
via ``response_format`` json_schema strict). ``offline=True`` or no key →
``available()`` is False and callers fall back to the deterministic stub paths.
Keys come from the environment ONLY — never hard-coded. Override the OpenAI model
with ``LLM_MODEL``.

The shared bundle text rides as a system prefix (cached on Claude; auto-prefix-
cached on OpenAI) so the per-claim sweep pays for the bundle once. Structured
output is strict so the model cannot drift the schema (anti-hallucination at the
shape level; the *content* is separately verbatim-checked by the caller).
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

# Default models. Callers pass a Claude name; on OpenAI it is mapped to LLM_MODEL.
MODEL_PER_CLAIM = "claude-haiku-4-5"
MODEL_EXTRACT = "claude-sonnet-4-6"
_OPENAI_DEFAULT = "gpt-4o-mini"


class LLM:
    """Thin LLM wrapper over Claude or OpenAI. ``offline``/missing key disables it."""

    def __init__(self, *, offline: bool = False, bundle_prefix: str = ""):
        self.offline = offline
        self.bundle_prefix = bundle_prefix
        self._client = None
        self.provider: Optional[str] = None
        if offline:
            return
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic  # type: ignore
                self._client = anthropic.Anthropic()
                self.provider = "anthropic"
            except Exception:
                self._client = None
        elif os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI  # type: ignore
                self._client = OpenAI()
                self.provider = "openai"
            except Exception:
                self._client = None

    def available(self) -> bool:
        return self._client is not None

    @property
    def backend(self) -> str:
        return self.provider or "offline-stub"

    def _openai_model(self) -> str:
        return os.getenv("LLM_MODEL", _OPENAI_DEFAULT)

    def structured(self, instruction: str, schema: dict, *, model: str,
                   max_tokens: int = 1024) -> Optional[dict]:
        """One structured call: strict JSON validated against *schema*.

        Returns the parsed object, or ``None`` on any failure (callers then use
        the deterministic stub path).
        """
        if not self.available():
            return None
        if self.provider == "anthropic":
            return self._structured_anthropic(instruction, schema, model=model,
                                              max_tokens=max_tokens)
        return self._structured_openai(instruction, schema, max_tokens=max_tokens)

    # ----------------------------------------------------------------- anthropic
    def _structured_anthropic(self, instruction: str, schema: dict, *, model: str,
                              max_tokens: int) -> Optional[dict]:
        system = []
        if self.bundle_prefix:
            system.append({
                "type": "text",
                "text": self.bundle_prefix,
                "cache_control": {"type": "ephemeral"},
            })
        tool = {"name": "emit", "description": "Emit the structured result.",
                "strict": True, "input_schema": schema}
        try:
            resp = self._client.messages.create(  # type: ignore[union-attr]
                model=model, max_tokens=max_tokens, system=system or None,
                tools=[tool], tool_choice={"type": "tool", "name": "emit"},
                messages=[{"role": "user", "content": instruction}],
            )
        except Exception:
            return None
        for block in getattr(resp, "content", []):
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == "emit":
                return dict(block.input)
        text = "".join(getattr(b, "text", "") for b in getattr(resp, "content", [])
                       if getattr(b, "type", None) == "text")
        return parse_json(text)

    # -------------------------------------------------------------------- openai
    def _structured_openai(self, instruction: str, schema: dict, *,
                           max_tokens: int) -> Optional[dict]:
        messages = []
        if self.bundle_prefix:
            messages.append({"role": "system", "content": self.bundle_prefix})
        messages.append({"role": "user", "content": instruction})
        rf = {"type": "json_schema",
              "json_schema": {"name": "emit", "strict": True, "schema": schema}}
        try:
            resp = self._client.chat.completions.create(  # type: ignore[union-attr]
                model=self._openai_model(), messages=messages,
                response_format=rf, temperature=0, max_tokens=max_tokens,
            )
            return parse_json(resp.choices[0].message.content)
        except Exception:
            return None


def parse_json(text: str):
    """Parse a JSON object/array from model output, tolerating ``` fences/prose."""
    text = (text or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
        return None
