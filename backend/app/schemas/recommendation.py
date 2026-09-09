"""
ShopGraph Recommendation Schemas
================================
Pydantic schemas for explainable recommendation requests and multi-factor score payloads.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.product import ProductSummary
from app.schemas.evidence import EvidenceItem
from app.schemas.explainability import ExplanationReport


class RecommendationRequest(BaseModel):
    product_id: Optional[str] = Field(default=None, description="Base product for item-to-item recommendations")
    category_id: Optional[str] = Field(default=None, description="Category filter breadcrumb")
    query: Optional[str] = Field(default=None, description="Natural language preference context")
    max_price: Optional[float] = Field(default=None, ge=0.0, description="Upper price ceiling")
    min_rating: Optional[float] = Field(default=None, ge=1.0, le=5.0, description="Minimum average rating")
    brand_name: Optional[str] = Field(default=None, description="Brand filter")
    limit: int = Field(default=5, ge=1, le=20)
    custom_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional custom weights for category, rating, price, brand, semantic, purchaser_overlap",
    )
    semantic_scores: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional explicit mapping of Product ID to vector similarity score [0.0, 1.0]",
    )


class RecommendedProduct(BaseModel):
    product: ProductSummary
    composite_score: float = Field(ge=0.0, le=1.0)
    explanation: ExplanationReport


class RecommendationResponse(BaseModel):
    query: Optional[str] = None
    target_product_id: Optional[str] = None
    recommendations: List[RecommendedProduct] = Field(default_factory=list)
    total_found: int
    weights_applied: Dict[str, float]
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
