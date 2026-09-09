"""
ShopGraph Explainability Schemas
================================
Structured models for transparent recommendation rationales and graph path explanations.
Enforces strict distinction between:
- OBSERVED GRAPH FACTS (grounded in Neo4j)
- VECTOR SIMILARITY (ANN embedding distances)
- REVIEW EVIDENCE (explicit reviewer feedback)
- RECOMMENDATION INFERENCES (algorithmic composite scoring)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.evidence import EvidenceType


class FactorContribution(BaseModel):
    factor_name: str = Field(description="Scoring dimension (e.g. 'category_match', 'rating_quality', 'price_fit')")
    weight: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)
    weighted_score: float = Field(ge=0.0, le=1.0)
    evidence_type: EvidenceType
    explanation: str


class GraphPathStep(BaseModel):
    start_node: str
    start_label: str
    relationship: str
    end_node: str
    end_label: str


class ExplanationReport(BaseModel):
    product_id: str
    product_title: str
    summary_reason: str
    factors: List[FactorContribution] = Field(default_factory=list)
    graph_paths: List[List[GraphPathStep]] = Field(default_factory=list)
    review_evidence_quotes: List[str] = Field(default_factory=list)
    observed_facts: List[str] = Field(default_factory=list)
    inferred_aspects: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
