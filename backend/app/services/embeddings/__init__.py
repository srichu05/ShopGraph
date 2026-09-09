"""Embeddings module."""
from app.config import settings
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local import local_embeddings, LocalEmbeddingProvider
from app.services.embeddings.gemini import GeminiEmbeddingProvider

def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory returning configured embedding provider."""
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiEmbeddingProvider()
    return local_embeddings

__all__ = [
    "BaseEmbeddingProvider",
    "LocalEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "local_embeddings",
    "get_embedding_provider",
]
