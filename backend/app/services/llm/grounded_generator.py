"""
ShopGraph Grounded Response Generator
=====================================
Synthesizes verified knowledge graph facts, review intelligence, and semantic signals
into grounded, hallucination-free natural language responses.
"""

import logging
from typing import List, Optional
from app.config import settings
from app.schemas.evidence import UnifiedEvidence
from app.schemas.product import ProductSummary, ProductDetail
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.retrieval.context_builder import context_builder

logger = logging.getLogger("shopgraph.llm.generator")

GROUNDING_SYSTEM_PROMPT = """You are the ShopGraph E-Commerce Intelligence AI.
Your objective is to provide helpful, transparent, and strictly grounded product answers, recommendations, and comparisons based ONLY on the provided Neo4j Knowledge Graph facts and Review evidence.

CRITICAL GROUNDING RULES:
1. ONLY make factual statements supported by the provided evidence. If information (like price, battery life, weight, or availability) is not in the context, explicitly state that it is not recorded in the dataset.
2. MISSING PRICES: If a product's price is listed as NULL or missing, NEVER claim it is $0 or free. State that the price is not available.
3. TIMESTAMPS: The review timestamp is strictly the date the review was PUBLISHED. It is NEVER an order date, shipping date, or purchase date.
4. PURCHASE STATUS: A verified purchase indicates that Amazon validated the transaction for that review. It does NOT prove current physical ownership.
5. RECOMMENDATION EXPLANATION: Clearly explain WHY an item is recommended using the specific evidence (e.g., category match, price budget, rating score, specific review quotes, or shared purchaser overlap).
6. FORMATTING: Structure answers with clear headings, bullet points, and mention product titles and canonical IDs where appropriate.
"""


class GroundedGenerator:
    """Coordinates prompt construction and grounded LLM completion."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = get_llm_provider()
        return self._provider

    def generate_response(
        self,
        query: str,
        products: List[ProductSummary],
        evidence: UnifiedEvidence,
        details: Optional[List[ProductDetail]] = None,
    ) -> str:
        """Generates grounded answer from retrieved graph evidence."""
        context = context_builder.build_prompt_context(
            query=query,
            products=products,
            evidence=evidence,
            details=details,
        )

        user_prompt = f"""User Question: {query}

{context}

Please provide a comprehensive, grounded, and helpful response addressing the user's question.
Explicitly explain your recommendations using the observed evidence."""

        if not self.provider.is_available():
            logger.warning("LLM provider '%s' is not available (no credentials). Returning grounded fallback summary.", self.provider.provider_name)
            return self._build_deterministic_summary(query, products, evidence)

        try:
            return self.provider.generate(
                prompt=user_prompt,
                system_instruction=GROUNDING_SYSTEM_PROMPT,
            )
        except Exception as e:
            logger.error("LLM generation failed: %s. Returning structured summary.", e)
            return self._build_deterministic_summary(query, products, evidence)

    def _build_deterministic_summary(
        self,
        query: str,
        products: List[ProductSummary],
        evidence: UnifiedEvidence,
    ) -> str:
        """Offline / fallback deterministic summary when LLM provider is offline."""
        if not products:
            return f"No products matching \"{query}\" were found in the knowledge graph under the specified constraints."

        lines = [f"Found {len(products)} relevant product(s) in the knowledge graph for \"{query}\":\n"]
        for idx, p in enumerate(products[:5], 1):
            price_str = f"${p.price:.2f}" if p.price is not None else "Price not listed"
            rating_str = f"{p.average_rating:.1f}★ ({p.rating_count} reviews)" if p.average_rating else "No rating"
            brand_str = f" by {p.brand_name}" if p.brand_name else ""
            lines.append(f"{idx}. **{p.title}** (ID: `{p.id}`){brand_str}")
            lines.append(f"   - Price: {price_str} | Rating: {rating_str}")
            if p.category_id:
                lines.append(f"   - Category: {p.category_id}")

        lines.append("\n*Note: LLM provider is currently offline; results are displayed directly from retrieved graph evidence.*")
        return "\n".join(lines)


grounded_generator = GroundedGenerator()
