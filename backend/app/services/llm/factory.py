"""
ShopGraph LLM Factory
=====================
Instantiates and configures the active LLM provider (Gemini or Groq)
dynamically based on configuration.
"""

import logging
from typing import Optional
from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.groq_provider import GroqProvider

logger = logging.getLogger("shopgraph.llm.factory")


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider for unit testing and offline development."""

    def __init__(self, name: str = "mock"):
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return "mock-v1"

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        return (
            "Based on the retrieved knowledge graph facts, the recommended product is "
            "grounded in the provided evidence. Missing prices remain unrecorded in the dataset."
        )


def get_llm_provider(force_provider: Optional[str] = None) -> LLMProvider:
    """Returns the configured LLMProvider instance."""
    provider_type = (force_provider or settings.LLM_PROVIDER).lower()

    if provider_type == "gemini":
        return GeminiProvider()
    elif provider_type == "groq":
        return GroqProvider()
    elif provider_type == "mock":
        return MockLLMProvider()
    else:
        logger.warning("Unknown LLM provider '%s'. Defaulting to Gemini.", provider_type)
        return GeminiProvider()
