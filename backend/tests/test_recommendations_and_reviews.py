"""
Tests for Recommendation Engine, Explainability, and Review Intelligence
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.evidence import EvidenceType
from app.schemas.product import ProductSummary
from app.schemas.review import ReviewItem
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendations.engine import recommendation_engine
from app.services.reviews.intelligence import review_intelligence
from app.services.explainability.explainer import explainer


def test_review_intelligence_distribution_and_aspects():
    mock_reviews = [
        ReviewItem(
            id="rev_1", user_id="u1", product_id="P1", rating=5.0,
            text="The sound quality is amazing and build quality is sturdy!",
            timestamp=1600000000, verified_purchase=True, helpful_votes=3
        ),
        ReviewItem(
            id="rev_2", user_id="u2", product_id="P1", rating=4.0,
            text="Good sound, but price is slightly high. Easy setup.",
            timestamp=1600001000, verified_purchase=True, helpful_votes=1
        ),
        ReviewItem(
            id="rev_3", user_id="u3", product_id="P1", rating=1.0,
            text="Terrible hiss and broken plastic. Poor durability.",
            timestamp=1600002000, verified_purchase=False, helpful_votes=0
        ),
    ]

    report = review_intelligence.analyze_product_reviews("P1", reviews=mock_reviews)

    assert report.product_id == "P1"
    assert report.distribution.total_reviews == 3
    assert report.distribution.verified_count == 2
    assert report.distribution.unverified_count == 1
    assert report.distribution.star_counts[5] == 1
    assert report.distribution.star_counts[1] == 1
    assert len(report.aspects) > 0

    aspect_names = [a.aspect for a in report.aspects]
    assert "sound quality" in aspect_names


def test_recommendation_scoring_and_explanation():
    p1 = ProductSummary(
        id="P1", title="Fender Stratocaster Electric Guitar", price=299.0,
        average_rating=4.7, rating_count=150, brand_name="Fender",
        category_id="Musical Instruments > Guitars > Electric Guitars"
    )

    req = RecommendationRequest(
        category_id="Electric Guitars",
        max_price=350.0,
        brand_name="Fender",
        limit=5
    )

    factors, score = recommendation_engine._score_product(
        prod=p1, req=req,
        weights=recommendation_engine._resolve_weights(None),
        shared_purchasers=4
    )

    assert score > 0.6
    assert len(factors) == 6

    factor_names = [f.factor_name for f in factors]
    assert "category_match" in factor_names
    assert "rating_quality" in factor_names
    assert "price_fit" in factor_names
    assert "purchaser_overlap" in factor_names

    exp = explainer.build_explanation(p1, factors, shared_purchasers_count=4)
    assert exp.product_id == "P1"
    assert len(exp.observed_facts) >= 3
    assert len(exp.graph_paths) >= 2

    # Verify Fix 4: Terminology consistency
    overlap_factor = next(f for f in factors if f.factor_name == "purchaser_overlap")
    assert "verified purchasers associated with both products" in overlap_factor.explanation
    assert "co-reviewed" not in overlap_factor.explanation.lower()
    assert "co-purchased" not in overlap_factor.explanation.lower()


def test_candidate_higher_semantic_similarity_gets_higher_factor():
    """1. Candidate A with higher semantic similarity gets a higher semantic factor than candidate B."""
    p_a = ProductSummary(id="P_A", title="Guitar A", price=200.0, average_rating=4.5, rating_count=20)
    p_b = ProductSummary(id="P_B", title="Guitar B", price=200.0, average_rating=4.5, rating_count=20)
    req = RecommendationRequest(limit=5)
    weights = recommendation_engine._resolve_weights(None)

    factors_a, _ = recommendation_engine._score_product(p_a, req, weights, shared_purchasers=0, semantic_score=0.92)
    factors_b, _ = recommendation_engine._score_product(p_b, req, weights, shared_purchasers=0, semantic_score=0.35)

    sem_a = next(f for f in factors_a if f.factor_name == "semantic_relevance")
    sem_b = next(f for f in factors_b if f.factor_name == "semantic_relevance")

    assert sem_a.score > sem_b.score
    assert sem_a.weighted_score > sem_b.weighted_score
    assert sem_a.score == 0.92
    assert sem_b.score == 0.35
    assert sem_a.evidence_type == EvidenceType.VECTOR_SIMILARITY
    assert sem_b.evidence_type == EvidenceType.VECTOR_SIMILARITY


def test_missing_semantic_score_does_not_fabricate_similarity_value():
    """2. Missing semantic score does not fabricate a similarity value and applies neutral fallback."""
    p = ProductSummary(id="P_C", title="Guitar C", price=200.0, average_rating=4.5, rating_count=20)
    req = RecommendationRequest(limit=5)
    weights = recommendation_engine._resolve_weights(None)

    factors, _ = recommendation_engine._score_product(p, req, weights, shared_purchasers=0, semantic_score=None)

    sem_factor = next(f for f in factors if f.factor_name == "semantic_relevance")
    # Must NOT claim to be vector similarity
    assert sem_factor.evidence_type == EvidenceType.RECOMMENDATION_INFERENCE
    assert sem_factor.evidence_type != EvidenceType.VECTOR_SIMILARITY
    # Explanation must clearly declare unavailable and neutral fallback
    assert "unavailable" in sem_factor.explanation.lower()
    assert "neutral fallback" in sem_factor.explanation.lower()
    assert sem_factor.score == 0.5


def test_composite_score_changes_appropriately_with_semantic_evidence():
    """3. The final composite score changes appropriately when semantic evidence changes."""
    p = ProductSummary(id="P_D", title="Guitar D", price=200.0, average_rating=4.5, rating_count=20)
    req = RecommendationRequest(limit=5)
    weights = recommendation_engine._resolve_weights(None)

    _, score_high = recommendation_engine._score_product(p, req, weights, shared_purchasers=0, semantic_score=0.90)
    _, score_low = recommendation_engine._score_product(p, req, weights, shared_purchasers=0, semantic_score=0.20)
    _, score_none = recommendation_engine._score_product(p, req, weights, shared_purchasers=0, semantic_score=None)

    assert score_high > score_none > score_low
    # The difference in composite score must reflect the difference in semantic score * weight
    expected_diff = round((0.90 - 0.20) * weights["semantic"], 4)
    assert abs((score_high - score_low) - expected_diff) < 1e-4


def test_explanation_reports_actual_semantic_evidence():
    """4. The explanation reports the actual semantic evidence."""
    p = ProductSummary(id="P_E", title="Guitar E", price=200.0, average_rating=4.5, rating_count=20)
    req = RecommendationRequest(limit=5)
    weights = recommendation_engine._resolve_weights(None)

    # With actual score 0.85
    factors, _ = recommendation_engine._score_product(p, req, weights, shared_purchasers=0, semantic_score=0.85)
    sem_factor = next(f for f in factors if f.factor_name == "semantic_relevance")
    assert "0.85" in sem_factor.explanation

    exp = explainer.build_explanation(p, factors, shared_purchasers_count=0, semantic_score=0.85)
    assert any("0.85" in item for item in exp.inferred_aspects)

    # Without score (None)
    factors_none, _ = recommendation_engine._score_product(p, req, weights, shared_purchasers=0, semantic_score=None)
    sem_factor_none = next(f for f in factors_none if f.factor_name == "semantic_relevance")
    assert "unavailable" in sem_factor_none.explanation.lower()


if __name__ == "__main__":
    import pytest
    pytest.main(["-v", __file__])
