"""
ShopGraph Phase 3 Hybrid Retrieval Hardening Regression Tests
============================================================
Validates fixes for:
1. Category boundary matching (eliminates phantom power supplies/accessories from microphones).
2. Brand filtering via (p)-[:BRANDED_BY]->(b:Brand) and WITH projection barrier.
3. Hard price ceiling constraint enforcement across hybrid candidate streams.
4. Compound instrument category parsing (guitar cable -> Instrument Cables, drum set -> Drum Sets).
5. 5-star rating tier parsing (5 star -> 4.5+ tier).
6. RRF k=60 preservation and score fusion.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from app.config import settings
from app.schemas.query import QueryIntent, RetrievalStrategy, ExtractedConstraints
from app.schemas.product import ProductSummary
from app.services.query_understanding.parser import query_parser
from app.services.cypher.generator import cypher_generator
from app.services.retrieval.hybrid_retriever import hybrid_retriever


def test_power_module_category_boundary_filtering():
    """Verify exact hierarchy segment matching eliminates accessories like Power Module."""
    c = ExtractedConstraints(
        intent=QueryIntent.PRODUCT_SEARCH,
        strategy=RetrievalStrategy.HYBRID,
        category_name="Microphones",
        price_max=300.0,
        raw_query="dynamic vocal microphone for podcasting under 300",
    )
    cypher, params = cypher_generator.generate_from_constraints(c, limit=20)
    assert "WITH p, b, c" in cypher
    assert 'p.category_id CONTAINS (" > " + $category_name + " > ")' in cypher
    assert 'p.category_id ENDS WITH (" > " + $category_name)' in cypher
    assert params["category_name"] == "Microphones"
    assert params["max_price"] == 300.0


def test_brand_property_and_with_barrier_in_cypher():
    """Verify brand matching uses b.name on Brand node with WITH barrier to avoid row leaking."""
    c = ExtractedConstraints(
        intent=QueryIntent.PRODUCT_SEARCH,
        strategy=RetrievalStrategy.HYBRID,
        category_name="Guitars",
        brand_name="Yamaha",
        raw_query="Yamaha guitar",
    )
    cypher, params = cypher_generator.generate_from_constraints(c, limit=10)
    assert "toLower(b.name) CONTAINS toLower($brand_name)" in cypher
    assert "p.brand_name" not in cypher  # Product nodes do not have brand_name property
    assert "WITH p, b, c" in cypher
    assert params["brand_name"] == "Yamaha"


def test_hard_price_ceiling_enforcement_in_hybrid_retriever():
    """Verify candidate products exceeding max_price or with None price are rejected when ceiling is set."""
    c = ExtractedConstraints(
        intent=QueryIntent.PRODUCT_SEARCH,
        strategy=RetrievalStrategy.HYBRID,
        category_name="Microphones",
        price_max=300.0,
        raw_query="dynamic vocal microphone under 300",
    )

    valid_mic = ProductSummary(
        id="B00KCN83VI",
        title="Electro-Voice RE320",
        price=299.0,
        average_rating=4.7,
        rating_count=212,
        category_id="Musical Instruments > Microphones & Accessories > Microphones > Dynamic Microphones > Vocal",
    )
    overpriced_mic = ProductSummary(
        id="B0002E4Z8M",
        title="Shure SM7B Vocal Dynamic Microphone",
        price=399.0,
        average_rating=4.8,
        rating_count=3500,
        category_id="Musical Instruments > Microphones & Accessories > Microphones > Dynamic Microphones > Vocal",
    )
    unpriced_mic = ProductSummary(
        id="B000IEFJ22",
        title="Coby High Performance Dynamic Microphone",
        price=None,
        average_rating=3.5,
        rating_count=13,
        category_id="Musical Instruments > Microphones & Accessories > Microphones > Dynamic Microphones",
    )

    assert hybrid_retriever._satisfies_constraints(valid_mic, c, strict_category=True) is True
    assert hybrid_retriever._satisfies_constraints(overpriced_mic, c, strict_category=True) is False
    assert hybrid_retriever._satisfies_constraints(unpriced_mic, c, strict_category=True) is False


def test_compound_category_keywords_parsing():
    """Verify compound instrument categories parse correctly without colliding with single-word parents."""
    # Guitar cable -> Instrument Cables, NOT Guitars
    res_cable = query_parser.parse("guitar cable with durable construction")
    assert res_cable.category_name == "Instrument Cables"

    # Drum set -> Drum Sets, NOT general Drums & Percussion
    res_drum = query_parser.parse("drum set with good build quality")
    assert res_drum.category_name == "Drum Sets"

    # Microphone cable -> Microphone Cables
    res_mic_cable = query_parser.parse("microphone cable 10ft")
    assert res_mic_cable.category_name == "Microphone Cables"


def test_five_star_rating_tier_parsing():
    """Verify '5 star' maps to top rating tier (4.5+) while explicit decimals are preserved."""
    res_5star = query_parser.parse("5 star guitar")
    assert res_5star.rating_min == 4.5

    res_decimal = query_parser.parse("guitar with at least 4.8 stars")
    assert res_decimal.rating_min == 4.8


def test_rrf_preserves_k_60_and_fuses():
    """Verify RRF maintains default k=60 and correctly boosts items appearing in both streams."""
    p1 = ProductSummary(id="P1", title="Dual Stream Product", price=150.0)
    p2 = ProductSummary(id="P2", title="Graph Only Product", price=120.0)
    p3 = ProductSummary(id="P3", title="Vector Only Product", price=140.0)

    graph_items = [p1, p2]
    vector_items = [(p1, 0.88), (p3, 0.85)]

    ranked = hybrid_retriever._reciprocal_rank_fusion(
        graph_items=graph_items,
        vector_items=vector_items,
        k=settings.RRF_K,
        limit=5,
    )

    assert settings.RRF_K == 60
    assert len(ranked) == 3
    # P1 is rank 1 in both graph and vector -> gets highest score (1/61 + 1/61 = 0.03278)
    assert ranked[0].id == "P1"
