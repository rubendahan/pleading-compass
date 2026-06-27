"""Configuration loading for the phase 0 pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .simple_yaml import load_yaml


class RunConfig(BaseModel):
    name: str = "cms_synthetic"
    fail_on_unsupported_evidence: bool = False


class LLMConfidenceConfig(BaseModel):
    enabled: bool = False
    method: str = "label_logits"


class LLMConfig(BaseModel):
    provider: str = "azure_openai"
    model_id: str = ""
    api_key_env: str = "AZURE_OPENAI_API_KEY"
    azure_endpoint_env: str = "AZURE_OPENAI_ENDPOINT"
    azure_api_version_env: str = "AZURE_OPENAI_API_VERSION"
    azure_deployment_env: str = "AZURE_OPENAI_DEPLOYMENT"
    azure_light_deployment_env: str = "AZURE_OPENAI_LIGHT_DEPLOYMENT"
    local_model_id_env: str = "LOCAL_NEMOTRON_MODEL_ID"
    hf_token_env: str = "HF_TOKEN"
    hf_device: str = "auto"
    hf_device_env: str = "LOCAL_NEMOTRON_DEVICE"
    hf_torch_dtype: str = "auto"
    hf_torch_dtype_env: str = "LOCAL_NEMOTRON_TORCH_DTYPE"
    hf_trust_remote_code: bool = True
    hf_max_input_tokens: int = 12000
    hf_local_files_only: bool = False
    timeout_seconds: float = 120
    max_output_tokens: int = 12000
    temperature: float | None = 0.0
    trace: bool = True
    confidence: LLMConfidenceConfig = Field(default_factory=LLMConfidenceConfig)


class EmbeddingConfig(BaseModel):
    provider: str = "vertex_ai"
    model_id: str = "gemini-embedding-001"
    api_key_env: str = "AZURE_OPENAI_API_KEY"
    azure_endpoint_env: str = "AZURE_OPENAI_ENDPOINT"
    azure_api_version_env: str = "AZURE_OPENAI_API_VERSION"
    azure_embedding_deployment_env: str = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
    project_id_env: str = "GOOGLE_CLOUD_PROJECT"
    location: str = "us-central1"
    hf_device: str = "auto"
    hf_torch_dtype: str = "auto"
    hf_trust_remote_code: bool = True
    hf_max_length: int = 8192
    hf_normalize: bool = True
    max_chunk_chars: int = 12000


class Neo4jConfig(BaseModel):
    enabled: bool = True
    uri_env: str = "NEO4J_URI"
    user_env: str = "NEO4J_USER"
    password_env: str = "NEO4J_PASSWORD"
    database: str | None = None


class Phase2Config(BaseModel):
    claim_evidence_top_k: int = Field(default=5, ge=1)


class OutputConfig(BaseModel):
    include_embeddings_in_json: bool = True
    write_llm_traces: bool = True


class AppConfig(BaseModel):
    run: RunConfig = Field(default_factory=RunConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embeddings: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    phase2: Phase2Config = Field(default_factory=Phase2Config)
    outputs: OutputConfig = Field(default_factory=OutputConfig)


def load_config(path: str | Path) -> AppConfig:
    data: dict[str, Any] = load_yaml(path)
    return AppConfig.model_validate(data)


def load_env_file(path: str | Path = ".env", *, override: bool = False) -> list[str]:
    """Load KEY=VALUE pairs from a local .env file.

    Values already present in the process environment are preserved by default.
    The return value contains the variable names loaded or observed in the file;
    callers should not print values.
    """

    env_path = Path(path)
    if not env_path.exists():
        return []

    loaded: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = _parse_env_value(value.strip())
        if override or key not in os.environ:
            os.environ[key] = value
        loaded.append(key)
    return loaded


def _parse_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value
