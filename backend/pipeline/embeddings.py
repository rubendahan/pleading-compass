"""Embedding providers and chunk aggregation."""

from __future__ import annotations

import math
import os
from typing import Protocol

from .config import EmbeddingConfig
from .model_providers import _normalize_azure_endpoint


class EmbeddingClient(Protocol):
    provider_name: str
    model_id: str

    def embed_text(self, text: str) -> list[float]:
        """Embed one text value."""


class VertexAIEmbeddingClient:
    provider_name = "vertex_ai"

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        self.model_id = config.model_id
        project_id = os.getenv(config.project_id_env)
        if not project_id:
            raise RuntimeError(
                f"Missing {config.project_id_env}. Set it before running Vertex embeddings."
            )
        try:
            import vertexai  # type: ignore
            from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "Install `google-cloud-aiplatform` to use provider=vertex_ai."
            ) from exc

        vertexai.init(project=project_id, location=config.location)
        self._TextEmbeddingInput = TextEmbeddingInput
        self._model = TextEmbeddingModel.from_pretrained(config.model_id)

    def embed_text(self, text: str) -> list[float]:
        instance = self._TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")
        result = self._model.get_embeddings([instance])[0]
        return [float(value) for value in result.values]


class OpenAIEmbeddingClient:
    provider_name = "openai"

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        self.model_id = config.model_id or "text-embedding-3-small"
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Missing {config.api_key_env}. Set it before running OpenAI embeddings."
            )
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Install the `openai` package to use provider=openai.") from exc

        self._client = OpenAI(api_key=api_key, timeout=120)

    def embed_text(self, text: str) -> list[float]:
        result = self._client.embeddings.create(model=self.model_id, input=text)
        return [float(value) for value in result.data[0].embedding]


class AzureOpenAIEmbeddingClient:
    provider_name = "azure_openai"

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        api_key = os.getenv(config.api_key_env)
        endpoint = os.getenv(config.azure_endpoint_env)
        api_version = os.getenv(config.azure_api_version_env)
        model_id = config.model_id or os.getenv(config.azure_embedding_deployment_env)
        missing = [
            name
            for name, value in [
                (config.api_key_env, api_key),
                (config.azure_endpoint_env, endpoint),
                (config.azure_api_version_env, api_version),
                (
                    f"{config.azure_embedding_deployment_env} or embeddings.model_id",
                    model_id,
                ),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing Azure OpenAI embedding setting(s): " + ", ".join(missing)
            )
        try:
            from openai import AzureOpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "Install the `openai` package to use provider=azure_openai."
            ) from exc

        self.model_id = str(model_id)
        self._client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=_normalize_azure_endpoint(str(endpoint)),
            api_version=str(api_version),
            timeout=120,
        )

    def embed_text(self, text: str) -> list[float]:
        result = self._client.embeddings.create(model=self.model_id, input=text)
        return [float(value) for value in result.data[0].embedding]


class HuggingFaceLocalEmbeddingClient:
    provider_name = "hf_local"

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        self.model_id = config.model_id or "nvidia/llama-nemotron-embed-1b-v2"
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "Install local embedding dependencies with "
                "`python -m pip install -e '.[hf]'` to use provider=hf_local."
            ) from exc

        self._torch = torch
        self._device = _resolve_hf_device(config.hf_device, torch)
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            trust_remote_code=config.hf_trust_remote_code,
        )
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = (
                self._tokenizer.eos_token or self._tokenizer.unk_token
            )

        model_kwargs = {"trust_remote_code": config.hf_trust_remote_code}
        torch_dtype = _resolve_hf_torch_dtype(config.hf_torch_dtype, torch)
        if torch_dtype is not None:
            model_kwargs["torch_dtype"] = torch_dtype

        self._model = AutoModel.from_pretrained(self.model_id, **model_kwargs)
        self._model.eval()
        self._model.to(self._device)

    def embed_text(self, text: str) -> list[float]:
        text = text.strip() or " "
        encoded = self._tokenizer(
            [text],
            padding=True,
            truncation=True,
            max_length=self.config.hf_max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}

        with self._torch.inference_mode():
            outputs = self._model(**encoded)

        embedding = _extract_embedding_tensor(
            outputs,
            encoded.get("attention_mask"),
            self._torch,
        )
        if self.config.hf_normalize:
            embedding = self._torch.nn.functional.normalize(embedding, p=2, dim=-1)
        return [float(value) for value in embedding[0].detach().float().cpu().tolist()]


class DeterministicEmbeddingClient:
    """Tiny deterministic provider for tests and offline smoke checks."""

    provider_name = "deterministic"

    def __init__(self, model_id: str = "deterministic-test-embedding") -> None:
        self.model_id = model_id

    def embed_text(self, text: str) -> list[float]:
        buckets = [0.0] * 16
        for index, char in enumerate(text):
            buckets[index % len(buckets)] += (ord(char) % 97) / 97.0
        norm = math.sqrt(sum(value * value for value in buckets)) or 1.0
        return [value / norm for value in buckets]


def build_embedding_client(config: EmbeddingConfig) -> EmbeddingClient:
    if config.provider == "hf_local":
        return HuggingFaceLocalEmbeddingClient(config)
    if config.provider == "openai":
        return OpenAIEmbeddingClient(config)
    if config.provider == "azure_openai":
        return AzureOpenAIEmbeddingClient(config)
    if config.provider == "vertex_ai":
        return VertexAIEmbeddingClient(config)
    if config.provider == "deterministic":
        return DeterministicEmbeddingClient(config.model_id)
    raise ValueError(f"Unsupported embedding provider: {config.provider}")


def embed_with_chunk_centroid(
    text: str,
    client: EmbeddingClient,
    *,
    max_chunk_chars: int,
) -> list[float]:
    chunks = chunk_text(text, max_chunk_chars=max_chunk_chars)
    if not chunks:
        return client.embed_text("")
    vectors = [client.embed_text(chunk) for chunk in chunks]
    return mean_vector(vectors)


def chunk_text(text: str, *, max_chunk_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chunk_chars:
        return [text]

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chunk_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                paragraph[start : start + max_chunk_chars]
                for start in range(0, len(paragraph), max_chunk_chars)
            )
            continue
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= max_chunk_chars:
            current = candidate
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    size = len(vectors[0])
    if any(len(vector) != size for vector in vectors):
        raise ValueError("Cannot average embedding vectors with different dimensions.")
    return [sum(vector[i] for vector in vectors) / len(vectors) for i in range(size)]


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


def _extract_embedding_tensor(outputs, attention_mask, torch_module):
    for key in ("sentence_embeddings", "sentence_embedding", "embeddings", "pooler_output"):
        value = _output_value(outputs, key)
        if value is not None:
            if getattr(value, "ndim", 0) == 2:
                return value
            if getattr(value, "ndim", 0) == 3:
                return _mean_pool_tensor(value, attention_mask, torch_module)

    last_hidden_state = _output_value(outputs, "last_hidden_state")
    if last_hidden_state is None and isinstance(outputs, (tuple, list)) and outputs:
        last_hidden_state = outputs[0]
    if last_hidden_state is None:
        raise RuntimeError("Could not find an embedding tensor in the Hugging Face model output.")
    return _mean_pool_tensor(last_hidden_state, attention_mask, torch_module)


def _output_value(outputs, key: str):
    if isinstance(outputs, dict):
        return outputs.get(key)
    return getattr(outputs, key, None)


def _mean_pool_tensor(last_hidden_state, attention_mask, torch_module):
    if attention_mask is None:
        return last_hidden_state.mean(dim=1)
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size())
    mask = mask.to(dtype=last_hidden_state.dtype)
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=torch_module.finfo(last_hidden_state.dtype).eps)
    return summed / counts
