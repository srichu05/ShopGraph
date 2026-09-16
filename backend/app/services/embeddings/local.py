"""
ShopGraph Local Embedding Providers
===================================
Provides dense semantic embeddings for Graph-RAG retrieval and ranking.
- BGEEmbeddingProvider: Real pretrained 768-dimensional sentence transformer (BAAI/bge-base-en-v1.5)
- LocalHashingEmbeddingProvider: Lightweight deterministic offline hasher for zero-dependency test environments
"""

import hashlib
import logging
import math
import os
from typing import List, Optional
from app.services.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger("shopgraph.embeddings.local")


class LocalHashingEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, zero-dependency offline embedding generator using subword hashing."""

    def __init__(self, dimension: int = 768):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "subword-hashing-768"

    def embed_text(self, text: str) -> List[float]:
        cleaned = text.lower().strip()
        if not cleaned:
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        tokens = cleaned.split()
        ngrams = [cleaned[i:i+3] for i in range(max(0, len(cleaned)-2))]
        all_features = tokens + ngrams

        for feat in all_features:
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if ((h >> 16) & 1) else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class BGEEmbeddingProvider(BaseEmbeddingProvider):
    """
    Pretrained, state-of-the-art 768-dimensional dense semantic embedding provider
    powered by BAAI/bge-base-en-v1.5 via SentenceTransformers.
    """

    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", dimension: int = 768):
        self._model_name = model_name
        self._dim = dimension
        self._model = None
        self._hasher = LocalHashingEmbeddingProvider(dimension=dimension)

    def _get_model(self):
        if self._model is None:
            try:
                import torch
                from sentence_transformers import SentenceTransformer
                torch.set_num_threads(os.cpu_count() or 4)
                logger.info("Loading embedding model %s on CPU...", self._model_name)
                try:
                    self._model = SentenceTransformer(self._model_name, device="cpu", local_files_only=True)
                except Exception:
                    self._model = SentenceTransformer(self._model_name, device="cpu")
                self._model.max_seq_length = 128
            except Exception as e:
                logger.warning(
                    "SentenceTransformer '%s' failed to initialize: %s. Falling back to subword hashing.",
                    self._model_name, e
                )
                self._model = False
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_text(self, text: str) -> List[float]:
        cleaned = text.strip()
        if not cleaned:
            return [0.0] * self._dim

        model = self._get_model()
        if model is False or model is None:
            return self._hasher.embed_text(cleaned)

        try:
            # Format query for asymmetric retrieval per BGE specification
            formatted = f"Represent this sentence for searching relevant passages: {cleaned}"
            emb = model.encode(formatted, normalize_embeddings=True)
            return [float(x) for x in emb]
        except Exception as e:
            logger.warning("BGE embed_text error: %s. Falling back to hashing.", e)
            return self._hasher.embed_text(cleaned)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        model = self._get_model()
        if model is False or model is None:
            return self._hasher.embed_batch(texts)

        try:
            formatted = [t.strip() for t in texts]
            embs = model.encode(formatted, batch_size=128, show_progress_bar=False, normalize_embeddings=True)
            return [[float(x) for x in vec] for vec in embs]
        except Exception as e:
            logger.warning("BGE embed_batch error: %s. Falling back to hashing.", e)
            return self._hasher.embed_batch(texts)


# Primary local semantic embedding provider
bge_embeddings = BGEEmbeddingProvider()
hashing_embeddings = LocalHashingEmbeddingProvider()

# Default alias for compatibility
LocalEmbeddingProvider = BGEEmbeddingProvider
local_embeddings = bge_embeddings
