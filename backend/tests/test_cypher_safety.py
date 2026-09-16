"""
Tests for Cypher Safety, Read-Only Enforcement, and Parameterization
"""

import pytest
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.cypher.validator import cypher_validator, CypherValidationError
from app.services.cypher.sanitizer import cypher_sanitizer
from app.services.cypher.generator import cypher_generator
from app.schemas.query import QueryIntent, ExtractedConstraints


def test_safe_read_query_passes():
    query = """
    MATCH (p:Product)-[:BRANDED_BY]->(b:Brand)
    WHERE p.price <= $max_price
    RETURN p.id, p.title, b.name
    LIMIT 10
    """
    is_valid, violations = cypher_validator.validate(query)
    assert is_valid is True
    assert len(violations) == 0


@pytest.mark.parametrize("bad_keyword", [
    "CREATE (p:Product {id: '123'})",
    "MATCH (p:Product) SET p.price = 0",
    "MATCH (p:Product) DELETE p",
    "MATCH (p:Product) DETACH DELETE p",
    "MERGE (b:Brand {id: 'brand_new'})",
    "MATCH (p:Product) REMOVE p.features",
    "DROP CONSTRAINT product_id",
    "CALL dbms.security.createUser('hacker', 'pass')",
])
def test_mutating_keywords_rejected(bad_keyword):
    is_valid, violations = cypher_validator.validate(bad_keyword)
    assert is_valid is False
    with pytest.raises(CypherValidationError):
        cypher_validator.assert_safe(bad_keyword)


@pytest.mark.parametrize("forbidden_rel", [
    "MATCH (p1:Product)-[:BOUGHT_TOGETHER]->(p2:Product) RETURN p1, p2",
    "MATCH (p1:Product)-[:CO_PURCHASED]->(p2:Product) RETURN p1, p2",
    "MATCH (u:User)-[:OWNS]->(p:Product) RETURN u, p",
    "MATCH (p1:Product)-[:SIMILAR_TO]->(p2:Product) RETURN p1, p2",
    "MATCH (r:Review)-[:PURCHASED_ON]->(p:Product) RETURN r, p",
])
def test_forbidden_relationships_rejected(forbidden_rel):
    is_valid, violations = cypher_validator.validate(forbidden_rel)
    assert is_valid is False
    assert any("forbidden" in v.lower() or "unapproved" in v.lower() for v in violations)


def test_unapproved_node_label_rejected():
    query = "MATCH (a:Account)-[:WROTE]->(r:Review) RETURN a, r LIMIT 5"
    is_valid, violations = cypher_validator.validate(query)
    assert is_valid is False
    assert any("forbidden or unknown node label" in v.lower() for v in violations)


def test_unrestricted_full_graph_scan_rejected():
    query = "MATCH (n) RETURN n"
    is_valid, violations = cypher_validator.validate(query)
    assert is_valid is False


def test_limit_enforcement_and_clamping():
    # 1. Appends limit when missing
    q_no_limit = "MATCH (p:Product) RETURN p.id"
    bounded_q, limit_val = cypher_sanitizer.enforce_limit(q_no_limit, requested_limit=15)
    assert "LIMIT $limit" in bounded_q
    assert limit_val == 15

    # 2. Clamps excessive limit
    q_huge = "MATCH (p:Product) RETURN p.id LIMIT 50000"
    bounded_q2, limit_val2 = cypher_sanitizer.enforce_limit(q_huge)
    assert "LIMIT 50" in bounded_q2
    assert limit_val2 == 50


def test_generator_produces_safe_parameterized_query():
    constraints = ExtractedConstraints(
        intent=QueryIntent.PRODUCT_SEARCH,
        category_name="Electric Guitars",
        price_max=350.0,
        rating_min=4.0,
        raw_query="electric guitars under $350 with 4 stars"
    )
    cypher, params = cypher_generator.generate_from_constraints(constraints, limit=12)

    # Must pass validation
    cypher_validator.assert_safe(cypher)

    # Must be properly parameterized
    assert params["max_price"] == 350.0
    assert params["min_rating"] == 4.0
    assert params["limit"] == 12
    assert "$max_price" in cypher
    assert "$min_rating" in cypher
    assert "LIMIT $limit" in cypher


@pytest.mark.parametrize("adversarial_query", [
    "CALL db.labels() YIELD label RETURN label",
    "CALL dbms.components() YIELD name RETURN name",
    "CALL apoc.export.csv.all('export.csv', {}) YIELD file RETURN file",
    "CALL apoc.load.json('file:///data.json') YIELD value RETURN value",
    "CALL apoc.system.execute('cat /etc/passwd') YIELD result RETURN result",
    "LOAD CSV FROM 'file:///data.csv' AS row RETURN row",
    "CALL custom.unsafe.procedure() YIELD x RETURN x",
    "MATCH (p:Product) CALL { WITH p RETURN p } RETURN p",
])
def test_unauthorized_procedures_and_load_csv_rejected(adversarial_query):
    is_valid, violations = cypher_validator.validate(adversarial_query)
    assert is_valid is False
    assert len(violations) > 0
    with pytest.raises(CypherValidationError):
        cypher_validator.assert_safe(adversarial_query)


def test_approved_vector_query_procedure_permitted():
    valid_proc_query = (
        "CALL db.index.vector.queryNodes('product_vector_index', 5, [0.1, 0.2, 0.3]) "
        "YIELD node, score "
        "RETURN node.id AS id, score"
    )
    is_valid, violations = cypher_validator.validate(valid_proc_query)
    assert is_valid is True, f"Expected valid query, got violations: {violations}"
    assert len(violations) == 0
    cypher_validator.assert_safe(valid_proc_query)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
