"""
ShopGraph Embeddings Provider Interface
=======================================
Defines standard embedding contracts for text and product representation.
"""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """Abstract interface for text embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of strings."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension size."""
        pass
