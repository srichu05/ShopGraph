"""
ShopGraph Query Understanding & Response Schemas
================================================
Unified request and response models for natural-language Graph-RAG queries.
Ensures frontend receives structured data rather than unparsed LLM text.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.product import ProductSummary
from app.schemas.evidence import EvidenceItem


class QueryIntent(str, Enum):
    PRODUCT_SEARCH = "product_search"
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    REVIEW_INTELLIGENCE = "review_intelligence"
    PRODUCT_EXPLANATION = "product_explanation"
    CATEGORY_EXPLORATION = "category_exploration"
    SIMILARITY_SEARCH = "similarity_search"
    GRAPH_RELATIONSHIP_EXPLORATION = "graph_relationship_exploration"


class RetrievalStrategy(str, Enum):
    GRAPH_ONLY = "GRAPH_ONLY"
    VECTOR_ONLY = "VECTOR_ONLY"
    HYBRID = "HYBRID"


class ExtractedConstraints(BaseModel):
    intent: QueryIntent = QueryIntent.PRODUCT_SEARCH
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    rating_min: Optional[float] = None
    review_aspects: List[str] = Field(default_factory=list)
    product_ids: List[str] = Field(default_factory=list)
    raw_query: str


class QueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500, description="Natural language user query")
    strategy_override: Optional[RetrievalStrategy] = Field(default=None, description="Force a specific retrieval mode")
    limit: int = Field(default=10, ge=1, le=50)


class QueryResponse(BaseModel):
    query: str
    intent: QueryIntent
    strategy_used: RetrievalStrategy
    answer: str = Field(description="Grounded, synthesized natural language answer")
    products: List[ProductSummary] = Field(default_factory=list, description="Structured product cards")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Granular traceable evidence")
    cypher_executed: Optional[str] = Field(default=None, description="Safe read-only Cypher query if executed")
    explanation: Optional[str] = Field(default=None, description="Transparent explanation of retrieval and ranking")
    limitations: List[str] = Field(default_factory=list, description="Dataset boundaries or missing facts")
    latency_breakdown_ms: Dict[str, float] = Field(default_factory=dict)
