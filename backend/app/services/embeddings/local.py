"""
ShopGraph Local Embedding Provider
==================================
Lightweight, deterministic offline embedding generator for testing and local operation.
Uses feature hashing with subword n-grams and L2 normalization to project texts
into a dense 768-dimensional space with cosine similarity properties.
"""

import hashlib
import math
from typing import List
from app.services.embeddings.base import BaseEmbeddingProvider


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, zero-dependency offline embedding generator."""

    def __init__(self, dimension: int = 768):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        cleaned = text.lower().strip()
        if not cleaned:
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        # Tokenize words + 3-grams
        tokens = cleaned.split()
        ngrams = [cleaned[i:i+3] for i in range(max(0, len(cleaned)-2))]
        all_features = tokens + ngrams

        for feat in all_features:
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if ((h >> 16) & 1) else -1.0
            vec[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


local_embeddings = LocalEmbeddingProvider()
