"""Product and review details endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.product import ProductDetail
from app.schemas.review import ReviewIntelligenceReport
from app.services.retrieval.graph_retriever import graph_retriever
from app.services.reviews.intelligence import review_intelligence
from app.db.neo4j.connection import neo4j_client

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/{product_id}", response_model=ProductDetail)
def get_product_details(product_id: str):
    """Retrieves canonical product metadata and connected brand/category relationships."""
    if not neo4j_client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is currently unreachable. Start Neo4j or configure Aura credentials in .env.",
        )

    prod = graph_retriever.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found in the knowledge graph.",
        )
    return prod


@router.get("/{product_id}/reviews", response_model=ReviewIntelligenceReport)
def get_product_reviews(
    product_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="Max reviews to analyze"),
):
    """Retrieves and analyzes customer reviews, rating distributions, and aspect sentiment."""
    if not neo4j_client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is currently unreachable.",
        )

    # Check product existence first
    prod = graph_retriever.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found.",
        )

    return review_intelligence.analyze_product_reviews(product_id, limit=limit)
