"""Confidence helpers for local model logit scoring."""

from __future__ import annotations

import math
from typing import Mapping

from .schemas import ConfidenceDiagnostics


def candidate_token_sequences(tokenizer, labels: list[str]) -> dict[str, list[list[int]]]:
    """Return token-id continuations to try for each short label.

    Chat models differ on whether the next token for a label is encoded as
    ``A``, `` A``, or after a newline. We score all practical variants and use
    the best continuation for each label.
    """

    sequences: dict[str, list[list[int]]] = {}
    for label in labels:
        variants = [label, f" {label}", f"\n{label}"]
        unique: list[list[int]] = []
        for variant in variants:
            token_ids = tokenizer.encode(variant, add_special_tokens=False)
            if token_ids and token_ids not in unique:
                unique.append([int(token_id) for token_id in token_ids])
        if not unique:
            raise RuntimeError(f"Could not tokenize confidence label {label!r}.")
        sequences[label] = unique
    return sequences


def probabilities_from_logprobs(logprobs: Mapping[str, float]) -> dict[str, float]:
    if not logprobs:
        raise ValueError("Cannot normalize an empty logprob mapping.")
    max_logprob = max(logprobs.values())
    exp_values = {
        label: math.exp(logprob - max_logprob) for label, logprob in logprobs.items()
    }
    total = sum(exp_values.values())
    if total <= 0:
        raise ValueError("Cannot normalize logprobs with zero total probability.")
    return {label: value / total for label, value in exp_values.items()}


def probability_entropy(probabilities: Mapping[str, float]) -> float:
    return -sum(value * math.log(value) for value in probabilities.values() if value > 0)


def diagnostics_from_label_logprobs(
    *,
    task: str,
    model_id: str,
    label_to_value: Mapping[str, str],
    candidate_logprobs: Mapping[str, float],
) -> ConfidenceDiagnostics:
    label_probabilities = probabilities_from_logprobs(candidate_logprobs)
    selected_label = max(label_probabilities, key=label_probabilities.get)
    selected_value = label_to_value[selected_label]
    return ConfidenceDiagnostics(
        method="label_logits",
        task=task,
        model_id=model_id,
        selected_label=selected_label,
        selected_value=selected_value,
        selected_probability=label_probabilities[selected_label],
        label_probabilities=dict(label_probabilities),
        value_probabilities={
            label_to_value[label]: probability
            for label, probability in label_probabilities.items()
        },
        candidate_logprobs=dict(candidate_logprobs),
        entropy=probability_entropy(label_probabilities),
    )
