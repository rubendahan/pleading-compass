"""Pydantic schemas shared by pipeline phases."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClaimExtractionItem(BaseModel):
    claim_id: str = Field(pattern=r"^C\d{3,}$")
    text: str
    source_quote: str
    paragraph_refs: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)


class ClaimExtractionResult(BaseModel):
    claims: list[ClaimExtractionItem]


class ConfidenceDiagnostics(BaseModel):
    method: str
    task: str
    model_id: str
    selected_label: str
    selected_value: str
    selected_probability: float = Field(ge=0.0, le=1.0)
    label_probabilities: dict[str, float] = Field(default_factory=dict)
    value_probabilities: dict[str, float] = Field(default_factory=dict)
    candidate_logprobs: dict[str, float] = Field(default_factory=dict)
    entropy: float = Field(ge=0.0)


class EvidencePairReview(BaseModel):
    source_evidence_id: str
    target_evidence_id: str
    relation: Literal["supports", "contradicts", "unrelated", "unclear"]
    score: float = Field(ge=0.0, le=1.0)
    rationale: str
    reasoning_summary: str
    confidence: ConfidenceDiagnostics | None = None


class ClaimEvidenceFinding(BaseModel):
    evidence_id: str
    summary: str
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class ClaimRobustnessReview(BaseModel):
    claim_id: str
    claim_text: str
    robustness_score: int = Field(ge=0, le=100)
    verdict: Literal["strong", "medium", "weak", "unsupported"]
    verdict_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: ConfidenceDiagnostics | None = None
    supporting_evidence: list[ClaimEvidenceFinding] = Field(default_factory=list)
    challenging_evidence: list[ClaimEvidenceFinding] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    over_extrapolation_risks: list[str] = Field(default_factory=list)
    legal_explanation: str
    recommended_action: str


class Claim(BaseModel):
    id: str
    text: str
    source_quote: str | None = None
    paragraph_refs: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    embedding_model_id: str | None = None


class Evidence(BaseModel):
    id: str
    tab: int | None = None
    path: str
    source_path: str | None = None
    type: str
    format: str
    source_format: str | None = None
    date: str | None = None
    period: str | None = None
    description: str
    description_hint: str | None = None
    raw_text: str
    embedding: list[float] | None = None
    embedding_model_id: str | None = None
    extraction_status: Literal["ok", "unsupported", "failed"] = "ok"
    extraction_error: str | None = None


class Edge(BaseModel):
    source_id: str
    target_id: str
    type: Literal["USES_EVIDENCE", "SIMILAR_TO", "SUPPORTS", "CONTRADICTS"]
    score: float | None = None
    rationale: str | None = None
    prompt_id: str | None = None
    model_id: str | None = None
    embedding_model_id: str | None = None
    review_relation: Literal["supports", "contradicts", "unrelated", "unclear"] | None = None
    review_score: float | None = Field(default=None, ge=0.0, le=1.0)
    review_rationale: str | None = None
    reasoning_summary: str | None = None
    confidence: ConfidenceDiagnostics | None = None
    review_prompt_id: str | None = None
    review_model_id: str | None = None


class GraphNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict


class GraphDocument(BaseModel):
    nodes: list[GraphNode]
    edges: list[Edge]


class CaseManifestEvidence(BaseModel):
    id: str
    tab: int | None = None
    path: str
    source_path: str | None = None
    type: str
    format: str
    source_format: str | None = None
    date: str | None = None
    period: str | None = None
    description_hint: str | None = None
    cited_by_claim_ids: list[str] = Field(default_factory=list)


class CaseManifest(BaseModel):
    case_id: str
    case_name: str | None = None
    court: str | None = None
    claim_number: str | None = None
    pleading: str
    pleading_sources: list[str] = Field(default_factory=list)
    bundle_index: str | None = None
    bundle_dir: str
    source_documents_dir: str | None = None
    evidence: list[CaseManifestEvidence]


class RunMetadata(BaseModel):
    run_id: str
    timestamp: str
    case_id: str
    config_path: str
    prompt_id: str
    llm_provider: str
    llm_model_id: str
    embedding_provider: str
    embedding_model_id: str
    neo4j_enabled: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Phase1RunMetadata(BaseModel):
    run_id: str
    timestamp: str
    case_id: str
    source_phase0_dir: str
    config_path: str
    prompt_id: str
    llm_provider: str
    llm_model_id: str
    embedding_provider: str | None = None
    embedding_model_id: str | None = None
    neo4j_enabled: bool
    claim_evidence_similarity_edges: int
    evidence_evidence_similarity_edges: int
    support_edges: int
    contradict_edges: int
    evidence_pair_reviews: int
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Phase2RunMetadata(BaseModel):
    run_id: str
    timestamp: str
    case_id: str
    source_phase1_dir: str
    config_path: str
    prompt_id: str
    llm_provider: str
    llm_model_id: str
    claim_evidence_top_k: int
    claim_reports: int
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
