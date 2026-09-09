"""
ShopGraph Product Comparison Schemas
====================================
Schemas for side-by-side product comparison, specification matrices, and grounded trade-off analysis.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.product import ProductDetail
from app.schemas.review import ReviewIntelligenceReport
from app.schemas.evidence import EvidenceItem


class ComparisonRequest(BaseModel):
    product_ids: List[str] = Field(min_length=2, max_length=5, description="List of 2 to 5 product IDs (parent_asin)")
    focus_aspects: Optional[List[str]] = Field(
        default=None,
        description="Optional aspects to compare (e.g. 'sound quality', 'price', 'durability')",
    )


class ProductComparisonItem(BaseModel):
    product: ProductDetail
    review_intelligence: Optional[ReviewIntelligenceReport] = None
    strengths: List[str] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)


class ComparisonResponse(BaseModel):
    products: List[ProductComparisonItem]
    matrix: Dict[str, Dict[str, Any]] = Field(description="Aspect -> {product_id: value}")
    llm_synthesis: Optional[str] = Field(default=None, description="Grounded trade-off analysis from LLM")
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
