"""
Tests for Query Understanding & Intent Parsing
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.query import QueryIntent, RetrievalStrategy
from app.services.query_understanding.parser import query_parser


def test_product_search_with_constraints():
    q = "Find an electric guitar under $300 with at least 4.5 stars"
    res = query_parser.parse(q)
    assert res.intent == QueryIntent.PRODUCT_SEARCH
    assert res.category_name == "Electric Guitars"
    assert res.price_max == 300.0
    assert res.price_min is None
    assert res.rating_min == 4.5
    assert res.strategy == RetrievalStrategy.HYBRID


def test_product_comparison():
    q = "Compare B01MRV9Z1Y and B07NBB4KRS on sound quality"
    res = query_parser.parse(q)
    assert res.intent == QueryIntent.COMPARISON
    assert "B01MRV9Z1Y" in res.product_ids
    assert "B07NBB4KRS" in res.product_ids
    assert "sound quality" in res.review_aspects


def test_review_intelligence():
    q = "What do reviewers like and dislike about Shure microphones?"
    res = query_parser.parse(q)
    assert res.intent == QueryIntent.REVIEW_INTELLIGENCE
    assert res.brand_name == "Shure"
    assert res.category_name == "Microphones"


def test_recommendations():
    q = "Recommend a beginner keyboard under $200 for recording"
    res = query_parser.parse(q)
    assert res.intent == QueryIntent.RECOMMENDATION
    assert res.category_name == "Keyboards & MIDI"
    assert res.price_max == 200.0
    assert "beginner" in res.review_aspects
    assert "recording" in res.review_aspects


def test_product_explanation():
    q = "Why was B01M4HO6RK recommended?"
    res = query_parser.parse(q)
    assert res.intent == QueryIntent.PRODUCT_EXPLANATION
    assert "B01M4HO6RK" in res.product_ids


def test_similarity_search():
    q = "Find products similar to B0002E1O2C"
    res = query_parser.parse(q)
    assert res.intent == QueryIntent.SIMILARITY_SEARCH
    assert "B0002E1O2C" in res.product_ids


def test_category_exploration():
    q = "Which brands have electric guitars?"
    res = query_parser.parse(q)
    assert res.intent == QueryIntent.CATEGORY_EXPLORATION
    assert res.category_name == "Electric Guitars"
    assert res.strategy == RetrievalStrategy.GRAPH_ONLY


if __name__ == "__main__":
    test_product_search_with_constraints()
    test_product_comparison()
    test_review_intelligence()
    test_recommendations()
    test_product_explanation()
    test_similarity_search()
    test_category_exploration()
    print("ALL 7 QUERY UNDERSTANDING TESTS PASSED!")
