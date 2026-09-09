"""Product recommendation endpoint."""

from fastapi import APIRouter, HTTPException, status
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendations.engine import recommendation_engine
from app.db.neo4j.connection import neo4j_client

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


@router.post("", response_model=RecommendationResponse)
def get_recommendations(req: RecommendationRequest):
    """Generates explainable product recommendations with multi-factor score breakdowns."""
    if not neo4j_client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is currently unreachable.",
        )

    return recommendation_engine.recommend(req)
