"""Health and diagnostic endpoint."""

from fastapi import APIRouter
from app.config import settings
from app.db.neo4j.connection import neo4j_client
from app.services.llm.factory import get_llm_provider

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Returns runtime health, database connectivity, and configured LLM provider."""
    neo4j_online = neo4j_client.is_available()
    llm = get_llm_provider()

    return {
        "status": "healthy" if neo4j_online else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "services": {
            "neo4j": {
                "status": "connected" if neo4j_online else "unavailable",
                "uri": settings.NEO4J_URI,
            },
            "llm": {
                "provider": llm.provider_name,
                "model": llm.model_name,
                "configured": llm.is_available(),
            },
            "embeddings": {
                "provider": settings.EMBEDDING_PROVIDER,
                "model": settings.EMBEDDING_MODEL,
                "dimension": settings.EMBEDDING_DIMENSION,
            },
        },
    }
