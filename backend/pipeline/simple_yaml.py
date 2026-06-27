"""Small YAML reader for this repo's simple config and manifest files.

PyYAML is preferred when installed. This fallback supports the subset used in
`configs/*.yaml` and `cases/*/manifest.yaml`: nested mappings, lists, strings,
numbers, booleans, and nulls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SimpleYamlError(ValueError):
    """Raised when the fallback parser cannot parse a YAML file."""


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return _FallbackYamlParser(path.read_text(encoding="utf-8")).parse()

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SimpleYamlError(f"Expected a mapping at the root of {path}.")
    return data


class _FallbackYamlParser:
    def __init__(self, text: str) -> None:
        self.lines = self._prepare(text)

    def parse(self) -> dict[str, Any]:
        if not self.lines:
            return {}
        value, index = self._parse_block(0, self.lines[0][0])
        if index != len(self.lines):
            raise SimpleYamlError("Could not consume the complete YAML document.")
        if not isinstance(value, dict):
            raise SimpleYamlError("Expected YAML document root to be a mapping.")
        return value

    @staticmethod
    def _prepare(text: str) -> list[tuple[int, str]]:
        prepared: list[tuple[int, str]] = []
        for raw in text.splitlines():
            line = raw.rstrip()
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent % 2 != 0:
                raise SimpleYamlError(f"Unsupported odd indentation: {raw!r}")
            prepared.append((indent, line.strip()))
        return prepared

    def _parse_block(self, index: int, indent: int) -> tuple[Any, int]:
        if self.lines[index][1].startswith("- "):
            return self._parse_list(index, indent)
        return self._parse_mapping(index, indent)

    def _parse_mapping(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while index < len(self.lines):
            current_indent, content = self.lines[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise SimpleYamlError(f"Unexpected indentation near: {content!r}")
            if content.startswith("- "):
                break
            key, value_text = self._split_key_value(content)
            if value_text == "":
                if index + 1 >= len(self.lines) or self.lines[index + 1][0] <= indent:
                    result[key] = None
                    index += 1
                else:
                    result[key], index = self._parse_block(index + 1, self.lines[index + 1][0])
            else:
                result[key] = self._parse_scalar(value_text)
                index += 1
        return result, index

    def _parse_list(self, index: int, indent: int) -> tuple[list[Any], int]:
        result: list[Any] = []
        while index < len(self.lines):
            current_indent, content = self.lines[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise SimpleYamlError(f"Unexpected indentation near: {content!r}")
            if not content.startswith("- "):
                break

            item_text = content[2:].strip()
            if item_text == "":
                if index + 1 >= len(self.lines):
                    result.append(None)
                    index += 1
                else:
                    item, index = self._parse_block(index + 1, self.lines[index + 1][0])
                    result.append(item)
            elif ":" in item_text and not item_text.startswith(("'", '"')):
                key, value_text = self._split_key_value(item_text)
                item: dict[str, Any] = {}
                if value_text == "":
                    if index + 1 >= len(self.lines) or self.lines[index + 1][0] <= current_indent:
                        item[key] = None
                        index += 1
                    else:
                        item[key], index = self._parse_block(index + 1, self.lines[index + 1][0])
                else:
                    item[key] = self._parse_scalar(value_text)
                    index += 1

                while index < len(self.lines):
                    next_indent, next_content = self.lines[index]
                    if next_indent <= current_indent:
                        break
                    if next_indent != current_indent + 2 or next_content.startswith("- "):
                        raise SimpleYamlError(f"Unsupported nested list item near: {next_content!r}")
                    nested_key, nested_value_text = self._split_key_value(next_content)
                    if nested_value_text == "":
                        if index + 1 >= len(self.lines) or self.lines[index + 1][0] <= next_indent:
                            item[nested_key] = None
                            index += 1
                        else:
                            item[nested_key], index = self._parse_block(index + 1, self.lines[index + 1][0])
                    else:
                        item[nested_key] = self._parse_scalar(nested_value_text)
                        index += 1
                result.append(item)
            else:
                result.append(self._parse_scalar(item_text))
                index += 1
        return result, index

    @staticmethod
    def _split_key_value(content: str) -> tuple[str, str]:
        if ":" not in content:
            raise SimpleYamlError(f"Expected key/value pair: {content!r}")
        key, value = content.split(":", 1)
        key = key.strip()
        if not key:
            raise SimpleYamlError(f"Missing key in: {content!r}")
        return key, value.strip()

    @staticmethod
    def _parse_scalar(value: str) -> Any:
        if value in {"null", "Null", "NULL", "~"}:
            return None
        if value in {"true", "True", "TRUE"}:
            return True
        if value in {"false", "False", "FALSE"}:
            return False
        if value == "[]":
            return []
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        try:
            if "." not in value:
                return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            return value
