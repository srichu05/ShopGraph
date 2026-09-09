"""
ShopGraph Evidence Schemas
==========================
Defines granular evidence items and provenance structures ensuring every fact
retrieved from Neo4j, vector search, or reviews is strictly traceable.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    OBSERVED_GRAPH_FACT = "OBSERVED_GRAPH_FACT"      # Explicit property/edge in Neo4j (e.g., price, rating, brand)
    VECTOR_SIMILARITY = "VECTOR_SIMILARITY"          # Semantic vector search ANN score
    REVIEW_EVIDENCE = "REVIEW_EVIDENCE"              # Raw review text, user rating, verified purchase status
    RECOMMENDATION_INFERENCE = "RECOMMENDATION_INFERENCE" # Algorithmic scoring / LLM synthesis


class EvidenceItem(BaseModel):
    """A discrete unit of evidence with full provenance tracking."""
    id: str = Field(description="Unique identifier of the evidence item")
    evidence_type: EvidenceType = Field(description="Classification of evidence origin")
    source: str = Field(description="Entity or attribute source (e.g. 'Product.average_rating', 'Review.text')")
    product_id: Optional[str] = Field(default=None, description="Associated canonical parent_asin")
    value: Any = Field(description="Raw retrieved value or metric")
    description: str = Field(description="Human-readable explanation of this piece of evidence")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence or similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provenance attributes")


class UnifiedEvidence(BaseModel):
    """Aggregated evidence payload passed to context builder and LLM."""
    query: str
    graph_facts: List[EvidenceItem] = Field(default_factory=list)
    vector_evidence: List[EvidenceItem] = Field(default_factory=list)
    review_evidence: List[EvidenceItem] = Field(default_factory=list)
    inferred_evidence: List[EvidenceItem] = Field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.graph_facts) + len(self.vector_evidence) + len(self.review_evidence) + len(self.inferred_evidence)
