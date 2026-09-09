"""
ShopGraph Review Schemas
========================
Pydantic schemas for review interactions, distributions, and review intelligence.
Guarantees:
- Review.variant_asin preserves child ASIN
- timestamp is publication epoch ms (NOT purchase date)
- verified_purchase enables [:PURCHASED] graph traversal
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewItem(BaseModel):
    id: str
    user_id: str
    product_id: str
    variant_asin: Optional[str] = Field(default=None, description="Child ASIN evaluated in this review")
    rating: float
    title: Optional[str] = None
    text: Optional[str] = None
    timestamp: int = Field(description="Review publication timestamp in Unix epoch milliseconds")
    verified_purchase: bool = Field(description="Whether Amazon marked this review as a verified purchase")
    helpful_votes: int = 0


class RatingDistribution(BaseModel):
    total_reviews: int = 0
    average_rating: float = 0.0
    verified_count: int = 0
    unverified_count: int = 0
    star_counts: Dict[int, int] = Field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})


class AspectSentiment(BaseModel):
    aspect: str = Field(description="Extracted review theme (e.g., 'sound quality', 'build quality', 'ease of use')")
    sentiment: str = Field(description="positive, neutral, or negative")
    mention_count: int = 0
    sample_quotes: List[str] = Field(default_factory=list)


class ReviewIntelligenceReport(BaseModel):
    product_id: str
    distribution: RatingDistribution
    aspects: List[AspectSentiment] = Field(default_factory=list)
    top_positive_snippets: List[str] = Field(default_factory=list)
    top_negative_snippets: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
