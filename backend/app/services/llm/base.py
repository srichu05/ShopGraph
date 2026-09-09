"""
ShopGraph LLM Provider Abstraction
==================================
Defines contracts for LLM providers (Gemini and Groq).
Guarantees provider-agnostic text and chat generation without changing business logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMProvider(ABC):
    """Abstract interface for LLM operations."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generates a text completion given a prompt and optional system instructions."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name identifier of the provider ('gemini' or 'groq')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model identifier string."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured with credentials and ready to execute."""
        pass
