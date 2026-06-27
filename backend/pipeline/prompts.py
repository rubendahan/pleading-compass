"""Prompt loading and rendering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .simple_yaml import _FallbackYamlParser


FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: str
    task: str
    required_variables: list[str]
    body: str

    @property
    def prompt_id(self) -> str:
        return f"{self.id}.{self.version}"

    def render(self, variables: dict[str, Any]) -> str:
        missing = [name for name in self.required_variables if name not in variables]
        if missing:
            raise ValueError(
                f"Missing required prompt variable(s) for {self.prompt_id}: "
                + ", ".join(missing)
            )
        rendered = self.body
        for name, value in variables.items():
            rendered = rendered.replace("{{ " + name + " }}", str(value))
            rendered = rendered.replace("{{" + name + "}}", str(value))
        return rendered


def load_prompt(path: str | Path) -> PromptTemplate:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise ValueError(f"Prompt file {path} must start with YAML front matter.")
    metadata_text, body = match.groups()
    metadata = _FallbackYamlParser(metadata_text).parse()
    required = metadata.get("required_variables") or []
    if not isinstance(required, list):
        raise ValueError(f"`required_variables` in {path} must be a list.")
    return PromptTemplate(
        id=str(metadata["id"]),
        version=str(metadata["version"]),
        task=str(metadata.get("task", "")),
        required_variables=[str(item) for item in required],
        body=body.strip(),
    )
