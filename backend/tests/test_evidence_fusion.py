"""
Tests for Evidence Fusion, Provenance Tracking, and Context Construction
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.evidence import EvidenceItem, EvidenceType
from app.schemas.product import ProductSummary
from app.services.retrieval.evidence_fusion import evidence_fusion
from app.services.retrieval.context_builder import context_builder


def test_evidence_fusion_and_deduplication():
    ev1 = EvidenceItem(
        id="ev_price_B01M4HO6RK",
        evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
        source="Product.price",
        product_id="B01M4HO6RK",
        value=399.0,
        description="Listed price: $399.00"
    )
    ev2 = EvidenceItem(
        id="ev_vec_B01M4HO6RK",
        evidence_type=EvidenceType.VECTOR_SIMILARITY,
        source="Neo4jVectorIndex.product_text_embeddings",
        product_id="B01M4HO6RK",
        value=0.89,
        description="Semantic similarity: 0.89"
    )
    # Duplicate ID
    ev1_dup = EvidenceItem(
        id="ev_price_B01M4HO6RK",
        evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
        source="Product.price",
        product_id="B01M4HO6RK",
        value=399.0,
        description="Listed price: $399.00"
    )

    unified = evidence_fusion.fuse(
        query="drum sets under $500",
        graph_facts=[ev1, ev1_dup],
        vector_evidence=[ev2]
    )

    assert unified.total_count == 2
    assert len(unified.graph_facts) == 1
    assert len(unified.vector_evidence) == 1
    assert unified.graph_facts[0].id == "ev_price_B01M4HO6RK"


def test_evidence_grouping_by_product():
    ev1 = EvidenceItem(
        id="ev_1", evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
        source="Product.price", product_id="P1", value=100.0, description="P1 price"
    )
    ev2 = EvidenceItem(
        id="ev_2", evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
        source="Product.price", product_id="P2", value=200.0, description="P2 price"
    )
    unified = evidence_fusion.fuse(query="test", graph_facts=[ev1, ev2])
    grouped = evidence_fusion.group_by_product(unified)

    assert "P1" in grouped
    assert "P2" in grouped
    assert len(grouped["P1"]) == 1
    assert grouped["P1"][0].id == "ev_1"


def test_context_construction_preserves_provenance_and_boundaries():
    prod = ProductSummary(
        id="B01M4HO6RK",
        title="Pearl Export Drum Set",
        price=399.0,
        average_rating=4.2,
        rating_count=22,
        brand_name="Pearl",
        category_id="Musical Instruments > Drums & Percussion"
    )
    ev = EvidenceItem(
        id="ev_price_B01M4HO6RK",
        evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
        source="Product.price",
        product_id="B01M4HO6RK",
        value=399.0,
        description="Listed price: $399.00"
    )
    unified = evidence_fusion.fuse(query="drum sets", graph_facts=[ev])

    ctx = context_builder.build_prompt_context(
        query="drum sets",
        products=[prod],
        evidence=unified
    )

    assert "B01M4HO6RK" in ctx
    assert "[OBSERVED GRAPH FACT] Price: $399.00" in ctx
    assert "Review timestamps represent publication dates, NEVER purchase" in ctx
    assert "Missing prices are NULL, NEVER assume $0 or free" in ctx


if __name__ == "__main__":
    import pytest
    pytest.main(["-v", __file__])
