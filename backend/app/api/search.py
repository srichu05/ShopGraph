from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.schemas.product import ProductSummary, ProductFilter
from app.schemas.evidence import EvidenceItem
from app.schemas.query import ExtractedConstraints, QueryIntent, RetrievalStrategy
from app.services.retrieval.hybrid_retriever import hybrid_retriever
from app.db.neo4j.connection import neo4j_client

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Keyword or structured search term")
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResponse(BaseModel):
    query: str
    products: List[ProductSummary]
    total_found: int
    evidence: List[EvidenceItem]
    cypher_query: Optional[str] = None


@router.post("", response_model=SearchResponse)
def search_products(req: SearchRequest):
    """Executes structured or semantic product search with parameter validation."""
    if not neo4j_client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is currently unreachable.",
        )

    constraints = ExtractedConstraints(
        intent=QueryIntent.PRODUCT_SEARCH,
        strategy=RetrievalStrategy.HYBRID,
        category_name=req.category,
        brand_name=req.brand,
        price_min=req.min_price,
        price_max=req.max_price,
        rating_min=req.min_rating,
        raw_query=req.query,
    )

    products, evidence, cypher_used = hybrid_retriever.retrieve(
        constraints=constraints,
        limit=req.limit,
    )

    return SearchResponse(
        query=req.query,
        products=products,
        total_found=len(products),
        evidence=evidence.graph_facts + evidence.vector_evidence,
        cypher_query=cypher_used,
    )


@router.get("", response_model=SearchResponse)
def search_products_get(
    query: str = "*",
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    limit: int = 10,
):
    """Executes structured or semantic product search via GET with query parameters."""
    req = SearchRequest(
        query=query if query.strip() else "*",
        category=category,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        limit=limit,
    )
    return search_products(req)
