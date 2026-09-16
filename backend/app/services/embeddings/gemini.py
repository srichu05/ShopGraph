"""
ShopGraph Gemini Embedding Provider
===================================
Produces dense semantic embeddings using Google Gemini's embedding models
(e.g., text-embedding-004) via the official Google GenAI SDK.
"""

import logging
from typing import List, Optional
from app.config import settings
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local import local_embeddings

logger = logging.getLogger("shopgraph.embeddings")


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding provider with automatic fallback to local provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIMENSION
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Google GenAI Client: %s. Using local fallback.", e)

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self.model or "text-embedding-004"

    def embed_text(self, text: str) -> List[float]:
        if not self._client:
            # Fallback when key is missing or offline
            return local_embeddings.embed_text(text)

        try:
            response = self._client.models.embed_content(
                model=self.model,
                contents=text,
            )
            # GenAI returns embedding with values list
            if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                return response.embedding.values
            elif hasattr(response, "embeddings") and len(response.embeddings) > 0:
                return response.embeddings[0].values
            return local_embeddings.embed_text(text)
        except Exception as e:
            logger.warning("Gemini embedding API error: %s. Falling back to local embeddings.", e)
            return local_embeddings.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._client:
            return local_embeddings.embed_batch(texts)

        try:
            response = self._client.models.embed_content(
                model=self.model,
                contents=texts,
            )
            if hasattr(response, "embeddings"):
                return [emb.values for emb in response.embeddings]
            return [self.embed_text(t) for t in texts]
        except Exception as e:
            logger.warning("Gemini batch embedding error: %s. Falling back to local.", e)
            return local_embeddings.embed_batch(texts)
