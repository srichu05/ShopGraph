"""
Comprehensive FastAPI REST API Integration Tests
================================================
Tests request/response validation, error handling, offline degradations,
and mocked end-to-end Graph-RAG endpoints.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.neo4j.connection import neo4j_client
from app.services.llm.factory import MockLLMProvider
from app.services.llm.grounded_generator import grounded_generator

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint returns status and service configurations."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "neo4j" in data["services"]
    assert "llm" in data["services"]


def test_offline_database_error_handling():
    """When Neo4j is offline, API returns graceful 503 rather than crashing."""
    with patch.object(neo4j_client, "is_available", return_value=False):
        res_search = client.post("/api/search", json={"query": "electric guitar"})
        assert res_search.status_code == 503
        assert "unreachable" in res_search.json()["detail"].lower()

        res_prod = client.get("/api/products/B01M4HO6RK")
        assert res_prod.status_code == 503

        res_query = client.post("/api/query", json={"query": "find guitars under $300"})
        assert res_query.status_code == 503


def test_mocked_search_and_query_flow():
    """Tests end-to-end Graph-RAG query execution with mocked Neo4j records."""
    mock_records = [
        {
            "id": "B01M4HO6RK",
            "title": "Pearl Export Lacquer Drum Set",
            "price": 399.0,
            "average_rating": 4.5,
            "rating_count": 48,
            "brand_name": "Pearl",
            "category_id": "Musical Instruments > Drums & Percussion",
            "image_url": "https://example.com/drum.jpg",
            "features": ["P930 Demonator Pedal", "Export 5-piece"],
            "description": ["Popular drum set"],
            "details": {"Manufacturer": "Pearl"},
            "raw_price": "399.0",
            "main_category": "Musical Instruments",
            "brand_id": "brand_pearl",
            "category_name": "Drums & Percussion",
            "category_level": 1,
            "category_parent": "Musical Instruments",
        }
    ]

    mock_reviews = [
        {
            "id": "rev_1",
            "rating": 5.0,
            "title": "Great drum set",
            "text": "The build quality and sound quality are phenomenal!",
            "timestamp": 1640000000000,
            "verified_purchase": True,
            "helpful_votes": 4,
            "variant_asin": "B01M4HO6RK",
            "user_id": "U12345",
        }
    ]

    # Use mock LLM provider for deterministic generation
    grounded_generator._provider = MockLLMProvider()

    with patch.object(neo4j_client, "is_available", return_value=True):
        with patch.object(neo4j_client, "execute_read", return_value=mock_records):
            # 1. Test Search Endpoint
            res_search = client.post("/api/search", json={"query": "drum set under $500", "limit": 5})
            assert res_search.status_code == 200
            data_search = res_search.json()
            assert len(data_search["products"]) == 1
            assert data_search["products"][0]["id"] == "B01M4HO6RK"
            assert data_search["products"][0]["price"] == 399.0
            assert len(data_search["evidence"]) >= 1

            # 2. Test Product Detail Endpoint
            res_prod = client.get("/api/products/B01M4HO6RK")
            assert res_prod.status_code == 200
            data_prod = res_prod.json()
            assert data_prod["id"] == "B01M4HO6RK"
            assert data_prod["brand"]["name"] == "Pearl"

            # 3. Test Recommendations Endpoint
            res_rec = client.post(
                "/api/recommend",
                json={"category_id": "Drums & Percussion", "max_price": 500.0, "limit": 3}
            )
            assert res_rec.status_code == 200
            data_rec = res_rec.json()
            assert len(data_rec["recommendations"]) >= 1
            rec_item = data_rec["recommendations"][0]
            assert "composite_score" in rec_item
            assert "explanation" in rec_item
            assert len(rec_item["explanation"]["factors"]) == 6

            # 4. Test End-to-end Graph-RAG Query Endpoint
            res_query = client.post(
                "/api/query",
                json={"query": "Find the best drum set under $500 for beginner recording", "limit": 5}
            )
            assert res_query.status_code == 200
            data_query = res_query.json()
            assert data_query["intent"] == "recommendation"
            assert "answer" in data_query
            assert len(data_query["products"]) == 1
            assert "latency_breakdown_ms" in data_query
            assert "retrieval" in data_query["latency_breakdown_ms"]


def test_neo4j_query_timeout_forwarded_to_driver():
    """Verify configured timeout is converted to seconds and forwarded to session.run()."""
    from app.config import settings
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.data.return_value = [{"p.id": "test_id"}]

    with patch.object(neo4j_client, "is_available", return_value=True), \
         patch.object(neo4j_client, "_driver", mock_driver):
        # 1. Default timeout from settings
        neo4j_client.execute_read("MATCH (p:Product) RETURN p.id")
        expected_default_sec = float(settings.NEO4J_QUERY_TIMEOUT_MS) / 1000.0
        mock_session.run.assert_called_with(
            "MATCH (p:Product) RETURN p.id", {}, timeout=expected_default_sec
        )

        # 2. Explicit custom timeout
        neo4j_client.execute_read("MATCH (p:Product) RETURN p.id", timeout_ms=3500)
        mock_session.run.assert_called_with(
            "MATCH (p:Product) RETURN p.id", {}, timeout=3.5
        )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
