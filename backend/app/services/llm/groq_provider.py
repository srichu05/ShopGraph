"""
ShopGraph Groq Provider
=======================
Implements LLMProvider using the Groq Python SDK for fast open-weights model inference
(e.g., Llama 3.3 70B, Mixtral).
"""

import logging
from typing import Optional
from app.config import settings
from app.services.llm.base import LLMProvider

logger = logging.getLogger("shopgraph.llm.groq")


class GroqProvider(LLMProvider):
    """Groq LLM provider implementation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model_name = model or settings.GROQ_MODEL
        self._client = None

        if self._api_key:
            try:
                from groq import Groq
                self._client = Groq(api_key=self._api_key)
            except Exception as e:
                logger.error("Failed to initialize Groq client: %s", e)

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        return self._client is not None and bool(self._api_key)

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.is_available():
            raise RuntimeError(
                "Groq provider is not configured. Provide GROQ_API_KEY in .env or switch LLM_PROVIDER."
            )

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_t = max_tokens or settings.LLM_MAX_TOKENS

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        try:
            chat_completion = self._client.chat.completions.create(
                messages=messages,
                model=self._model_name,
                temperature=temp,
                max_tokens=max_t,
            )
            return chat_completion.choices[0].message.content or ""
        except Exception as e:
            logger.error("Groq chat completion failed: %s", e)
            raise RuntimeError(f"Groq API generation error: {e}") from e
