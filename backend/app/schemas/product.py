"""
ShopGraph Product Schemas
=========================
Pydantic schemas for canonical products, brands, and categories.
Guarantees:
- Product.id == parent_asin
- Missing prices remain None / null
- Canonical category breadcrumbs preserved
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BrandRef(BaseModel):
    id: str
    name: str


class CategoryRef(BaseModel):
    id: str
    name: str
    level: int
    parent_id: Optional[str] = None


class ProductSummary(BaseModel):
    """Compact product representation for listings, search results, and cards."""
    id: str = Field(description="Canonical product identifier (parent_asin)")
    title: str
    average_rating: Optional[float] = None
    rating_count: int = 0
    price: Optional[float] = Field(default=None, description="Price in USD or null if missing")
    price_currency: Optional[str] = "USD"
    brand_name: Optional[str] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None


class ProductDetail(ProductSummary):
    """Rich product representation with features, descriptions, and technical specifications."""
    brand: Optional[BrandRef] = None
    category: Optional[CategoryRef] = None
    main_category: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    description: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    raw_price: Optional[str] = None


class ProductFilter(BaseModel):
    """Structured constraints for filtering products."""
    category_id: Optional[str] = None
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    min_reviews: Optional[int] = None
    search_term: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)
