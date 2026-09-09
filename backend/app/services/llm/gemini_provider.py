"""
ShopGraph Google Gemini Provider
================================
Implements LLMProvider using the official Google GenAI SDK.
"""

import logging
from typing import Optional
from app.config import settings
from app.services.llm.base import LLMProvider

logger = logging.getLogger("shopgraph.llm.gemini")


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model_name = model or settings.GEMINI_MODEL
        self._client = None

        if self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI client: %s", e)

    @property
    def provider_name(self) -> str:
        return "gemini"

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
                "Gemini provider is not configured. Provide GEMINI_API_KEY in .env or switch LLM_PROVIDER."
            )

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_t = max_tokens or settings.LLM_MAX_TOKENS

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=temp,
                max_output_tokens=max_t,
                system_instruction=system_instruction,
            )

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            logger.error("Gemini content generation failed: %s", e)
            raise RuntimeError(f"Gemini API generation error: {e}") from e
