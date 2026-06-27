"""Answer-key registry — makes the labelled GOLD source pluggable.

Two keys ship:
  * ``selftest``  — the synthetic Bates-anchored mini-bundle (validates the scorer).
  * ``bundle``    — the DRAFT key over the real CMS Post Office witness statements
                    (``data/bundle_gold.py``), built for the offline demo + bake-off
                    oracle. Labelled from the public record; flagged for legal review.

A key bundles everything the harness needs to score a judge: the propositions,
the per-proposition GOLD verdict/evidence, and where each proposition is pleaded.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import Proposition


@dataclass
class AnswerKey:
    name: str
    bundle_dir: str
    propositions: list[Proposition]
    gold: dict
    pleaded_at: dict


_ROOT = Path(__file__).resolve().parents[1]


def selftest_key() -> AnswerKey:
    from data.selftest.propositions import PROPOSITIONS, GOLD, PLEADED_AT
    return AnswerKey("selftest", str(_ROOT / "data" / "selftest" / "bundle"),
                     list(PROPOSITIONS), GOLD, PLEADED_AT)


def bundle_key() -> AnswerKey:
    """The real CMS bundle DRAFT key (raises if ``data/bundle_gold.py`` is absent)."""
    from data.bundle_gold import PROPOSITIONS, GOLD, PLEADED_AT
    return AnswerKey("bundle", str(_ROOT / "data" / "bundle"),
                     list(PROPOSITIONS), GOLD, PLEADED_AT)


def get_key(name: Optional[str]) -> AnswerKey:
    if name in (None, "selftest"):
        return selftest_key()
    if name == "bundle":
        return bundle_key()
    raise KeyError(f"unknown answer key '{name}' (have: selftest, bundle)")
