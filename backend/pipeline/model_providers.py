"""LLM providers for structured extraction and review tasks."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .confidence import candidate_token_sequences, diagnostics_from_label_logprobs
from .config import LLMConfig
from .prompts import PromptTemplate
from .schemas import (
    ClaimExtractionResult,
    ClaimRobustnessReview,
    ConfidenceDiagnostics,
    EvidencePairReview,
)


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class LLMClient(Protocol):
    provider_name: str
    model_id: str

    def extract_claims(
        self,
        *,
        prompt: PromptTemplate,
        pleading_text: str,
        trace_path: Path | None = None,
    ) -> ClaimExtractionResult:
        """Extract structured claims from a pleading."""

    def review_evidence_pair(
        self,
        *,
        prompt: PromptTemplate,
        source_evidence: dict,
        target_evidence: dict,
        trace_path: Path | None = None,
    ) -> EvidencePairReview:
        """Review whether two pieces of evidence support or contradict each other."""

    def review_claim_robustness(
        self,
        *,
        prompt: PromptTemplate,
        claim: dict,
        selected_evidence: list[dict],
        evidence_relationships: dict,
        trace_path: Path | None = None,
    ) -> ClaimRobustnessReview:
        """Review the robustness of one claim against selected graph context."""

    def check_connection(self) -> str:
        """Make a minimal live model call and return the response id."""


class OpenAIResponsesClient:
    provider_name = "openai"

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.model_id = config.model_id
        if not self.model_id:
            raise RuntimeError("Missing llm.model_id for provider=openai.")
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Missing {config.api_key_env}. Set it before running phase 0."
            )
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Install the `openai` package to use provider=openai.") from exc
        self._client = OpenAI(api_key=api_key, timeout=config.timeout_seconds)

    def check_connection(self) -> str:
        response = self._client.responses.create(
            model=self.model_id,
            input="Reply with OK.",
            max_output_tokens=16,
        )
        return str(getattr(response, "id", "ok"))

    def extract_claims(
        self,
        *,
        prompt: PromptTemplate,
        pleading_text: str,
        trace_path: Path | None = None,
    ) -> ClaimExtractionResult:
        rendered = prompt.render({"pleading_text": pleading_text})
        instructions = (
            "You extract claims from English pleadings. Return only the requested "
            "structured data. Do not invent evidence ids."
        )

        kwargs = {
            "model": self.model_id,
            "instructions": instructions,
            "input": rendered,
            "text_format": ClaimExtractionResult,
            "max_output_tokens": self.config.max_output_tokens,
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature

        response = self._client.responses.parse(**kwargs)
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            output_text = getattr(response, "output_text", "")
            parsed = ClaimExtractionResult.model_validate_json(output_text)
        if not isinstance(parsed, ClaimExtractionResult):
            parsed = ClaimExtractionResult.model_validate(parsed)

        if trace_path:
            _append_trace(
                trace_path,
                {
                    "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
                    "provider": self.provider_name,
                    "model": self.model_id,
                    "prompt_id": prompt.prompt_id,
                    "task": "claim_extraction",
                    "input_chars": len(rendered),
                    "response_id": getattr(response, "id", None),
                    "output": parsed.model_dump(),
                },
            )
        return parsed

    def review_evidence_pair(
        self,
        *,
        prompt: PromptTemplate,
        source_evidence: dict,
        target_evidence: dict,
        trace_path: Path | None = None,
    ) -> EvidencePairReview:
        return _review_evidence_pair_with_responses_client(
            client=self._client,
            config=self.config,
            provider_name=self.provider_name,
            model_id=self.model_id,
            prompt=prompt,
            source_evidence=source_evidence,
            target_evidence=target_evidence,
            trace_path=trace_path,
        )

    def review_claim_robustness(
        self,
        *,
        prompt: PromptTemplate,
        claim: dict,
        selected_evidence: list[dict],
        evidence_relationships: dict,
        trace_path: Path | None = None,
    ) -> ClaimRobustnessReview:
        return _review_claim_robustness_with_responses_client(
            client=self._client,
            config=self.config,
            provider_name=self.provider_name,
            model_id=self.model_id,
            prompt=prompt,
            claim=claim,
            selected_evidence=selected_evidence,
            evidence_relationships=evidence_relationships,
            trace_path=trace_path,
        )


class AzureOpenAIResponsesClient:
    provider_name = "azure_openai"

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        api_key = os.getenv(config.api_key_env)
        endpoint = os.getenv(config.azure_endpoint_env)
        api_version = os.getenv(config.azure_api_version_env)
        model_id = (
            config.model_id
            or os.getenv(config.azure_light_deployment_env)
            or os.getenv(config.azure_deployment_env)
        )
        missing = [
            name
            for name, value in [
                (config.api_key_env, api_key),
                (config.azure_endpoint_env, endpoint),
                (config.azure_api_version_env, api_version),
                (
                    f"{config.azure_light_deployment_env} or {config.azure_deployment_env} or llm.model_id",
                    model_id,
                ),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing Azure OpenAI setting(s): " + ", ".join(missing)
            )
        try:
            from openai import AzureOpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Install the `openai` package to use provider=azure_openai.") from exc

        self.model_id = str(model_id)
        self._client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=_normalize_azure_endpoint(str(endpoint)),
            api_version=str(api_version),
            timeout=config.timeout_seconds,
        )

    def check_connection(self) -> str:
        response = self._client.responses.create(
            model=self.model_id,
            input="Reply with OK.",
            max_output_tokens=16,
        )
        return str(getattr(response, "id", "ok"))

    def extract_claims(
        self,
        *,
        prompt: PromptTemplate,
        pleading_text: str,
        trace_path: Path | None = None,
    ) -> ClaimExtractionResult:
        rendered = prompt.render({"pleading_text": pleading_text})
        instructions = (
            "You extract claims from English pleadings. Return only the requested "
            "structured data. Do not invent evidence ids."
        )
        kwargs = {
            "model": self.model_id,
            "instructions": instructions,
            "input": rendered,
            "text_format": ClaimExtractionResult,
            "max_output_tokens": self.config.max_output_tokens,
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature

        response = self._client.responses.parse(**kwargs)
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            output_text = getattr(response, "output_text", "")
            parsed = ClaimExtractionResult.model_validate_json(output_text)
        if not isinstance(parsed, ClaimExtractionResult):
            parsed = ClaimExtractionResult.model_validate(parsed)

        if trace_path:
            _append_trace(
                trace_path,
                {
                    "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
                    "provider": self.provider_name,
                    "model": self.model_id,
                    "prompt_id": prompt.prompt_id,
                    "task": "claim_extraction",
                    "input_chars": len(rendered),
                    "response_id": getattr(response, "id", None),
                    "output": parsed.model_dump(),
                },
            )
        return parsed

    def review_evidence_pair(
        self,
        *,
        prompt: PromptTemplate,
        source_evidence: dict,
        target_evidence: dict,
        trace_path: Path | None = None,
    ) -> EvidencePairReview:
        return _review_evidence_pair_with_responses_client(
            client=self._client,
            config=self.config,
            provider_name=self.provider_name,
            model_id=self.model_id,
            prompt=prompt,
            source_evidence=source_evidence,
            target_evidence=target_evidence,
            trace_path=trace_path,
        )

    def review_claim_robustness(
        self,
        *,
        prompt: PromptTemplate,
        claim: dict,
        selected_evidence: list[dict],
        evidence_relationships: dict,
        trace_path: Path | None = None,
    ) -> ClaimRobustnessReview:
        return _review_claim_robustness_with_responses_client(
            client=self._client,
            config=self.config,
            provider_name=self.provider_name,
            model_id=self.model_id,
            prompt=prompt,
            claim=claim,
            selected_evidence=selected_evidence,
            evidence_relationships=evidence_relationships,
            trace_path=trace_path,
        )


class HfLocalNemotronClient:
    provider_name = "hf_local_nemotron"

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.model_id = (
            os.getenv(config.local_model_id_env)
            or config.model_id
            or "nvidia/Llama-3.1-Nemotron-Nano-8B-v1"
        )
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "Install local LLM dependencies with "
                "`python -m pip install -e '.[hf]'` to use provider=hf_local_nemotron."
            ) from exc

        self._torch = torch
        self._device = _resolve_hf_device(
            os.getenv(config.hf_device_env) or config.hf_device,
            torch,
        )
        torch_dtype = _resolve_hf_torch_dtype(
            os.getenv(config.hf_torch_dtype_env) or config.hf_torch_dtype,
            torch,
        )
        token = os.getenv(config.hf_token_env)
        tokenizer_kwargs = {
            "trust_remote_code": config.hf_trust_remote_code,
            "local_files_only": config.hf_local_files_only,
        }
        model_kwargs = dict(tokenizer_kwargs)
        if token:
            tokenizer_kwargs["token"] = token
            model_kwargs["token"] = token
        if torch_dtype is not None:
            model_kwargs["torch_dtype"] = torch_dtype

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                **tokenizer_kwargs,
            )
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = (
                    self._tokenizer.eos_token or self._tokenizer.unk_token
                )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                **model_kwargs,
            )
            self._model.eval()
            self._model.to(self._device)
        except Exception as exc:  # pragma: no cover - depends on local hardware/model cache
            raise RuntimeError(
                "Failed to load local Nemotron model "
                f"{self.model_id!r} on device {self._device!r}. "
                "Use a smaller model, set LOCAL_NEMOTRON_DEVICE=cpu, or run on a "
                "machine with sufficient memory. No OpenAI fallback was used."
            ) from exc

    def check_connection(self) -> str:
        text = self._generate_text(
            instructions="Reply with OK.",
            user_text="Health check.",
            max_new_tokens=16,
        )
        return "hf-local-ok" if text.strip() else "hf-local-empty"

    def extract_claims(
        self,
        *,
        prompt: PromptTemplate,
        pleading_text: str,
        trace_path: Path | None = None,
    ) -> ClaimExtractionResult:
        rendered = prompt.render({"pleading_text": pleading_text})
        instructions = (
            "You extract claims from English pleadings. Return only JSON matching "
            "the requested schema. Do not invent evidence ids."
        )
        parsed = self._generate_structured_json(
            instructions=instructions,
            user_text=rendered,
            response_model=ClaimExtractionResult,
        )
        if trace_path:
            _append_trace(
                trace_path,
                {
                    "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
                    "provider": self.provider_name,
                    "model": self.model_id,
                    "prompt_id": prompt.prompt_id,
                    "task": "claim_extraction",
                    "input_chars": len(rendered),
                    "response_id": None,
                    "output": parsed.model_dump(),
                },
            )
        return parsed

    def review_evidence_pair(
        self,
        *,
        prompt: PromptTemplate,
        source_evidence: dict,
        target_evidence: dict,
        trace_path: Path | None = None,
    ) -> EvidencePairReview:
        rendered = _render_evidence_pair_prompt(
            prompt=prompt,
            source_evidence=source_evidence,
            target_evidence=target_evidence,
        )
        instructions = (
            "You compare two legal evidence documents. Return only JSON matching "
            "the requested schema. Do not invent facts outside the provided evidence."
        )
        confidence = self._evidence_pair_confidence(rendered)
        user_text = rendered
        if confidence:
            user_text += (
                "\n\nA local logit classifier selected this relation:\n"
                f"- relation: {confidence.selected_value}\n"
                f"- confidence: {confidence.selected_probability:.6f}\n\n"
                "Return JSON with this exact `relation` and `score`. Generate only "
                "the rationale and reasoning_summary around that fixed decision."
            )
        parsed = self._generate_structured_json(
            instructions=instructions,
            user_text=user_text,
            response_model=EvidencePairReview,
        )
        if confidence:
            parsed = parsed.model_copy(
                update={
                    "relation": confidence.selected_value,
                    "score": confidence.selected_probability,
                    "confidence": confidence,
                }
            )
        if trace_path:
            _append_trace(
                trace_path,
                {
                    "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
                    "provider": self.provider_name,
                    "model": self.model_id,
                    "prompt_id": prompt.prompt_id,
                    "task": "evidence_pair_review",
                    "source_evidence_id": source_evidence["id"],
                    "target_evidence_id": target_evidence["id"],
                    "input_chars": len(user_text),
                    "response_id": None,
                    "output": parsed.model_dump(),
                },
            )
            if confidence:
                _append_confidence_trace(
                    trace_path,
                    confidence,
                    {
                        "prompt_id": prompt.prompt_id,
                        "source_evidence_id": source_evidence["id"],
                        "target_evidence_id": target_evidence["id"],
                    },
                )
        return parsed

    def review_claim_robustness(
        self,
        *,
        prompt: PromptTemplate,
        claim: dict,
        selected_evidence: list[dict],
        evidence_relationships: dict,
        trace_path: Path | None = None,
    ) -> ClaimRobustnessReview:
        rendered = _render_claim_robustness_prompt(
            prompt=prompt,
            claim=claim,
            selected_evidence=selected_evidence,
            evidence_relationships=evidence_relationships,
        )
        instructions = (
            "You review the robustness of a pleaded legal claim against provided "
            "evidence context. Return only JSON matching the requested schema."
        )
        confidence = self._claim_verdict_confidence(rendered)
        user_text = rendered
        if confidence:
            user_text += (
                "\n\nA local logit classifier selected this verdict:\n"
                f"- verdict: {confidence.selected_value}\n"
                f"- confidence: {confidence.selected_probability:.6f}\n\n"
                "Return JSON with this exact `verdict`. Keep `robustness_score` "
                "as a legal-strength score from 0 to 100, not as model confidence."
            )
        parsed = self._generate_structured_json(
            instructions=instructions,
            user_text=user_text,
            response_model=ClaimRobustnessReview,
        )
        if confidence:
            parsed = parsed.model_copy(
                update={
                    "verdict": confidence.selected_value,
                    "verdict_confidence": confidence.selected_probability,
                    "confidence": confidence,
                }
            )
        if trace_path:
            _append_trace(
                trace_path,
                {
                    "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
                    "provider": self.provider_name,
                    "model": self.model_id,
                    "prompt_id": prompt.prompt_id,
                    "task": "claim_robustness_review",
                    "claim_id": claim["id"],
                    "selected_evidence_ids": [
                        item["evidence_id"] for item in selected_evidence
                    ],
                    "input_chars": len(user_text),
                    "response_id": None,
                    "output": parsed.model_dump(),
                },
            )
            if confidence:
                _append_confidence_trace(
                    trace_path,
                    confidence,
                    {
                        "prompt_id": prompt.prompt_id,
                        "claim_id": claim["id"],
                    },
                )
        return parsed

    def _evidence_pair_confidence(
        self,
        rendered_prompt: str,
    ) -> ConfidenceDiagnostics | None:
        if not self.config.confidence.enabled:
            return None
        _validate_confidence_method(self.config)
        user_text = (
            f"{rendered_prompt}\n\n"
            "Classify the relationship using exactly one label.\n"
            "A = supports\n"
            "B = contradicts\n"
            "C = unrelated\n"
            "D = unclear\n\n"
            "Reply with one letter only. The next token must be A, B, C, or D.\n"
            "Answer:"
        )
        return self._classify_label_logits(
            task="evidence_pair_relation",
            instructions="Classify the evidence relationship. Reply with one label only.",
            user_text=user_text,
            label_to_value={
                "A": "supports",
                "B": "contradicts",
                "C": "unrelated",
                "D": "unclear",
            },
        )

    def _claim_verdict_confidence(
        self,
        rendered_prompt: str,
    ) -> ConfidenceDiagnostics | None:
        if not self.config.confidence.enabled:
            return None
        _validate_confidence_method(self.config)
        user_text = (
            f"{rendered_prompt}\n\n"
            "Classify the claim verdict using exactly one label.\n"
            "A = strong\n"
            "B = medium\n"
            "C = weak\n"
            "D = unsupported\n\n"
            "Reply with one letter only. The next token must be A, B, C, or D.\n"
            "Answer:"
        )
        return self._classify_label_logits(
            task="claim_verdict",
            instructions="Classify the claim verdict. Reply with one label only.",
            user_text=user_text,
            label_to_value={
                "A": "strong",
                "B": "medium",
                "C": "weak",
                "D": "unsupported",
            },
        )

    def _classify_label_logits(
        self,
        *,
        task: str,
        instructions: str,
        user_text: str,
        label_to_value: dict[str, str],
    ) -> ConfidenceDiagnostics:
        encoded = self._encode_messages(instructions=instructions, user_text=user_text)
        sequences = candidate_token_sequences(self._tokenizer, list(label_to_value))
        candidate_logprobs = {
            label: max(
                self._sequence_logprob(
                    encoded["input_ids"],
                    encoded.get("attention_mask"),
                    token_sequence,
                )
                for token_sequence in token_sequences
            )
            for label, token_sequences in sequences.items()
        }
        return diagnostics_from_label_logprobs(
            task=task,
            model_id=self.model_id,
            label_to_value=label_to_value,
            candidate_logprobs=candidate_logprobs,
        )

    def _sequence_logprob(
        self,
        input_ids,
        attention_mask,
        token_sequence: list[int],
    ) -> float:
        current_ids = input_ids.clone()
        current_attention = (
            attention_mask.clone()
            if attention_mask is not None
            else self._torch.ones_like(current_ids)
        )
        total = 0.0
        with self._torch.inference_mode():
            for token_id in token_sequence:
                outputs = self._model(
                    input_ids=current_ids,
                    attention_mask=current_attention,
                )
                logits = outputs.logits[:, -1, :]
                log_probs = self._torch.log_softmax(logits, dim=-1)
                total += float(log_probs[0, int(token_id)].detach().cpu())
                next_token = self._torch.tensor(
                    [[int(token_id)]],
                    dtype=current_ids.dtype,
                    device=self._device,
                )
                current_ids = self._torch.cat([current_ids, next_token], dim=1)
                current_attention = self._torch.cat(
                    [current_attention, self._torch.ones_like(next_token)],
                    dim=1,
                )
        return total / max(len(token_sequence), 1)

    def _generate_structured_json(
        self,
        *,
        instructions: str,
        user_text: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        output_text = self._generate_text(
            instructions=instructions,
            user_text=user_text,
            max_new_tokens=self.config.max_output_tokens,
        )
        return _parse_json_response(output_text, response_model)

    def _generate_text(
        self,
        *,
        instructions: str,
        user_text: str,
        max_new_tokens: int,
    ) -> str:
        encoded = self._encode_messages(instructions=instructions, user_text=user_text)
        input_length = int(encoded["input_ids"].shape[-1])
        generation_kwargs = {
            **encoded,
            "max_new_tokens": max_new_tokens,
            "pad_token_id": self._tokenizer.pad_token_id,
        }
        temperature = self.config.temperature
        if temperature is not None and temperature > 0:
            generation_kwargs["do_sample"] = True
            generation_kwargs["temperature"] = temperature
        else:
            generation_kwargs["do_sample"] = False

        with self._torch.inference_mode():
            output_ids = self._model.generate(**generation_kwargs)
        new_tokens = output_ids[0, input_length:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True)

    def _encode_messages(self, *, instructions: str, user_text: str) -> dict:
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_text},
        ]
        if getattr(self._tokenizer, "chat_template", None):
            text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            text = f"System:\n{instructions}\n\nUser:\n{user_text}\n\nAssistant:\n"
        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.hf_max_input_tokens,
        )
        return {key: value.to(self._device) for key, value in encoded.items()}


def build_llm_client(config: LLMConfig) -> LLMClient:
    if config.provider == "openai":
        return OpenAIResponsesClient(config)
    if config.provider == "azure_openai":
        return AzureOpenAIResponsesClient(config)
    if config.provider == "hf_local_nemotron":
        return HfLocalNemotronClient(config)
    if config.provider == "nemotron_openai_compatible":
        raise NotImplementedError(
            "Nemotron provider is planned for the same LLMClient interface. "
            "Use provider=openai or provider=azure_openai for the current implementation."
        )
    raise ValueError(f"Unsupported LLM provider: {config.provider}")


def _append_trace(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_confidence_trace(
    trace_path: Path,
    confidence: ConfidenceDiagnostics,
    extra: dict,
) -> None:
    confidence_path = trace_path.parent / "confidence.jsonl"
    _append_trace(
        confidence_path,
        {
            "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
            **extra,
            "confidence": confidence.model_dump(),
        },
    )


def _review_evidence_pair_with_responses_client(
    *,
    client,
    config: LLMConfig,
    provider_name: str,
    model_id: str,
    prompt: PromptTemplate,
    source_evidence: dict,
    target_evidence: dict,
    trace_path: Path | None = None,
) -> EvidencePairReview:
    rendered = _render_evidence_pair_prompt(
        prompt=prompt,
        source_evidence=source_evidence,
        target_evidence=target_evidence,
    )
    instructions = (
        "You compare two legal evidence documents. Return only the requested "
        "structured data. Do not invent facts outside the provided evidence."
    )
    kwargs = {
        "model": model_id,
        "instructions": instructions,
        "input": rendered,
        "text_format": EvidencePairReview,
        "max_output_tokens": config.max_output_tokens,
    }
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature

    response = client.responses.parse(**kwargs)
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        output_text = getattr(response, "output_text", "")
        parsed = EvidencePairReview.model_validate_json(output_text)
    if not isinstance(parsed, EvidencePairReview):
        parsed = EvidencePairReview.model_validate(parsed)

    if trace_path:
        _append_trace(
            trace_path,
            {
                "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "provider": provider_name,
                "model": model_id,
                "prompt_id": prompt.prompt_id,
                "task": "evidence_pair_review",
                "source_evidence_id": source_evidence["id"],
                "target_evidence_id": target_evidence["id"],
                "input_chars": len(rendered),
                "response_id": getattr(response, "id", None),
                "output": parsed.model_dump(),
            },
        )
    return parsed


def _review_claim_robustness_with_responses_client(
    *,
    client,
    config: LLMConfig,
    provider_name: str,
    model_id: str,
    prompt: PromptTemplate,
    claim: dict,
    selected_evidence: list[dict],
    evidence_relationships: dict,
    trace_path: Path | None = None,
) -> ClaimRobustnessReview:
    rendered = _render_claim_robustness_prompt(
        prompt=prompt,
        claim=claim,
        selected_evidence=selected_evidence,
        evidence_relationships=evidence_relationships,
    )
    instructions = (
        "You review the robustness of a pleaded legal claim against provided "
        "evidence context. Return only the requested structured data."
    )
    kwargs = {
        "model": model_id,
        "instructions": instructions,
        "input": rendered,
        "text_format": ClaimRobustnessReview,
        "max_output_tokens": config.max_output_tokens,
    }
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature

    response = client.responses.parse(**kwargs)
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        output_text = getattr(response, "output_text", "")
        parsed = ClaimRobustnessReview.model_validate_json(output_text)
    if not isinstance(parsed, ClaimRobustnessReview):
        parsed = ClaimRobustnessReview.model_validate(parsed)

    if trace_path:
        _append_trace(
            trace_path,
            {
                "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "provider": provider_name,
                "model": model_id,
                "prompt_id": prompt.prompt_id,
                "task": "claim_robustness_review",
                "claim_id": claim["id"],
                "selected_evidence_ids": [
                    item["evidence_id"] for item in selected_evidence
                ],
                "input_chars": len(rendered),
                "response_id": getattr(response, "id", None),
                "output": parsed.model_dump(),
            },
        )
    return parsed


def _evidence_metadata(evidence: dict) -> dict:
    return {
        "id": evidence.get("id"),
        "tab": evidence.get("tab"),
        "type": evidence.get("type"),
        "date": evidence.get("date"),
        "period": evidence.get("period"),
        "path": evidence.get("path"),
    }


def _render_evidence_pair_prompt(
    *,
    prompt: PromptTemplate,
    source_evidence: dict,
    target_evidence: dict,
) -> str:
    return prompt.render(
        {
            "source_evidence_id": source_evidence["id"],
            "target_evidence_id": target_evidence["id"],
            "source_evidence_metadata": json.dumps(
                _evidence_metadata(source_evidence),
                ensure_ascii=False,
                indent=2,
            ),
            "target_evidence_metadata": json.dumps(
                _evidence_metadata(target_evidence),
                ensure_ascii=False,
                indent=2,
            ),
            "source_evidence_text": source_evidence["description"],
            "target_evidence_text": target_evidence["description"],
        }
    )


def _render_claim_robustness_prompt(
    *,
    prompt: PromptTemplate,
    claim: dict,
    selected_evidence: list[dict],
    evidence_relationships: dict,
) -> str:
    return prompt.render(
        {
            "claim_id": claim["id"],
            "claim_text": claim["text"],
            "selected_evidence_json": json.dumps(
                selected_evidence,
                ensure_ascii=False,
                indent=2,
            ),
            "evidence_relationships_json": json.dumps(
                evidence_relationships,
                ensure_ascii=False,
                indent=2,
            ),
        }
    )


def _parse_json_response(
    output_text: str,
    response_model: type[StructuredModel],
) -> StructuredModel:
    json_text = _extract_json_object(output_text)
    return response_model.model_validate_json(json_text)


def _extract_json_object(output_text: str) -> str:
    text = output_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return json.dumps(parsed, ensure_ascii=False)
    raise RuntimeError("Local model response did not contain a valid JSON object.")


def _validate_confidence_method(config: LLMConfig) -> None:
    if config.confidence.method != "label_logits":
        raise RuntimeError(
            "Unsupported local confidence method: "
            f"{config.confidence.method!r}. Only 'label_logits' is implemented."
        )


def _resolve_hf_device(device: str, torch_module) -> str:
    requested = (device or "auto").lower()
    if requested != "auto":
        return requested
    if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
        return "mps"
    if torch_module.cuda.is_available():
        return "cuda"
    return "cpu"


def _resolve_hf_torch_dtype(dtype: str, torch_module):
    requested = (dtype or "auto").lower()
    if requested in {"none", "null", "false"}:
        return None
    if requested == "auto":
        return "auto"
    if requested in {"float16", "fp16", "half"}:
        return torch_module.float16
    if requested in {"bfloat16", "bf16"}:
        return torch_module.bfloat16
    if requested in {"float32", "fp32", "full"}:
        return torch_module.float32
    raise ValueError(f"Unsupported hf_torch_dtype: {dtype}")


def _normalize_azure_endpoint(endpoint: str) -> str:
    """Accept either an Azure resource URL or the full responses endpoint."""

    endpoint = endpoint.strip()
    marker = "/openai/"
    if marker in endpoint:
        endpoint = endpoint.split(marker, 1)[0]
    return endpoint.rstrip("/")
