"""
Tests for LLM Provider Abstraction and Grounded Generation
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.evidence import UnifiedEvidence, EvidenceItem, EvidenceType
from app.schemas.product import ProductSummary
from app.services.llm.factory import get_llm_provider, MockLLMProvider
from app.services.llm.grounded_generator import GroundedGenerator, GROUNDING_SYSTEM_PROMPT


def test_provider_factory_switching():
    mock_prov = get_llm_provider(force_provider="mock")
    assert isinstance(mock_prov, MockLLMProvider)
    assert mock_prov.provider_name == "mock"
    assert mock_prov.is_available() is True

    gemini_prov = get_llm_provider(force_provider="gemini")
    assert gemini_prov.provider_name == "gemini"

    groq_prov = get_llm_provider(force_provider="groq")
    assert groq_prov.provider_name == "groq"


def test_grounded_generator_with_mock_provider():
    mock_prov = MockLLMProvider()
    generator = GroundedGenerator(provider=mock_prov)

    prod = ProductSummary(
        id="B01M4HO6RK",
        title="Pearl Export Drum Set",
        price=399.0,
        average_rating=4.2,
        rating_count=22
    )
    ev = EvidenceItem(
        id="ev_1",
        evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
        source="Product.price",
        product_id="B01M4HO6RK",
        value=399.0,
        description="Listed price: $399.00"
    )
    unified = UnifiedEvidence(query="drum sets", graph_facts=[ev])

    response = generator.generate_response(
        query="drum sets under $500",
        products=[prod],
        evidence=unified
    )

    assert isinstance(response, str)
    assert len(response) > 20


def test_grounding_system_prompt_rules():
    # Verify core PRD anti-hallucination rules are present in the system prompt
    assert "MISSING PRICES" in GROUNDING_SYSTEM_PROMPT
    assert "TIMESTAMPS" in GROUNDING_SYSTEM_PROMPT
    assert "PURCHASE STATUS" in GROUNDING_SYSTEM_PROMPT
    assert "NEVER an order date" in GROUNDING_SYSTEM_PROMPT


def test_offline_deterministic_fallback():
    # Create an unavailable provider
    class OfflineProvider(MockLLMProvider):
        def is_available(self):
            return False

    generator = GroundedGenerator(provider=OfflineProvider())
    prod = ProductSummary(
        id="B01M4HO6RK",
        title="Pearl Export Drum Set",
        price=399.0,
        average_rating=4.2,
        rating_count=22
    )
    unified = UnifiedEvidence(query="drum sets")

    response = generator.generate_response(
        query="drum sets",
        products=[prod],
        evidence=unified
    )

    # Should gracefully return structured offline summary without throwing
    assert "Pearl Export Drum Set" in response
    assert "$399.00" in response
    assert "LLM provider is currently offline" in response


if __name__ == "__main__":
    import pytest
    pytest.main(["-v", __file__])
