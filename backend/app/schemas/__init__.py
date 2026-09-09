"""ShopGraph Schemas Module."""

from app.schemas.evidence import EvidenceItem, EvidenceType, UnifiedEvidence
from app.schemas.product import ProductSummary, ProductDetail, BrandRef, CategoryRef, ProductFilter
from app.schemas.review import ReviewItem, RatingDistribution, AspectSentiment, ReviewIntelligenceReport
from app.schemas.explainability import FactorContribution, GraphPathStep, ExplanationReport
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse, RecommendedProduct
from app.schemas.comparison import ComparisonRequest, ComparisonResponse, ProductComparisonItem
from app.schemas.query import QueryIntent, RetrievalStrategy, ExtractedConstraints, QueryRequest, QueryResponse

__all__ = [
    "EvidenceItem",
    "EvidenceType",
    "UnifiedEvidence",
    "ProductSummary",
    "ProductDetail",
    "BrandRef",
    "CategoryRef",
    "ProductFilter",
    "ReviewItem",
    "RatingDistribution",
    "AspectSentiment",
    "ReviewIntelligenceReport",
    "FactorContribution",
    "GraphPathStep",
    "ExplanationReport",
    "RecommendationRequest",
    "RecommendationResponse",
    "RecommendedProduct",
    "ComparisonRequest",
    "ComparisonResponse",
    "ProductComparisonItem",
    "QueryIntent",
    "RetrievalStrategy",
    "ExtractedConstraints",
    "QueryRequest",
    "QueryResponse",
]
