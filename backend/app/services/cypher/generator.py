"""
ShopGraph Controlled Cypher Generator
=====================================
Generates parameterized, safe Cypher queries tailored to user intents and constraints.
Provides vetted high-performance templates and optional LLM-assisted generation with
mandatory safety validation and fallback.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.schemas.query import QueryIntent, ExtractedConstraints
from app.services.cypher.validator import cypher_validator
from app.services.cypher.sanitizer import cypher_sanitizer


class CypherGenerator:
    """Produces vetted parameterized Cypher queries for the retrieval engine."""

    def generate_from_constraints(
        self,
        constraints: ExtractedConstraints,
        limit: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Maps structured query constraints to a safe, parameterized Cypher query and params.
        """
        intent = constraints.intent
        params: Dict[str, Any] = {}

        if intent == QueryIntent.COMPARISON and constraints.product_ids:
            query, params = self._build_comparison_query(constraints.product_ids)
        elif intent == QueryIntent.REVIEW_INTELLIGENCE and constraints.product_ids:
            query, params = self._build_review_query(constraints.product_ids[0])
        elif intent == QueryIntent.GRAPH_RELATIONSHIP_EXPLORATION and constraints.product_ids:
            query, params = self._build_shared_purchaser_query(constraints.product_ids[0])
        elif intent == QueryIntent.CATEGORY_EXPLORATION:
            query, params = self._build_category_query(constraints.category_name)
        else:
            # Default to structured / hybrid product search
            query, params = self._build_product_search_query(constraints)

        # Enforce limits and sanitize parameters
        bounded_query, final_limit = cypher_sanitizer.enforce_limit(query, limit)
        safe_params = cypher_sanitizer.build_safe_params(params, final_limit)

        # Validate with safety rules
        cypher_validator.assert_safe(bounded_query)

        return bounded_query, safe_params

    def _build_product_search_query(self, c: ExtractedConstraints) -> Tuple[str, Dict[str, Any]]:
        params: Dict[str, Any] = {
            "category_name": c.category_name,
            "brand_name": c.brand_name,
            "min_price": c.price_min,
            "max_price": c.price_max,
            "min_rating": c.rating_min,
        }

        query = """MATCH (p:Product)
OPTIONAL MATCH (p)-[:BRANDED_BY]->(b:Brand)
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
WITH p, b, c
WHERE ($category_name IS NULL OR p.category_id CONTAINS (" > " + $category_name + " > ") OR p.category_id ENDS WITH (" > " + $category_name) OR p.category_id = $category_name)
  AND ($brand_name IS NULL OR toLower(b.name) CONTAINS toLower($brand_name))
  AND ($max_price IS NULL OR p.price <= $max_price)
  AND ($min_price IS NULL OR p.price >= $min_price)
  AND ($min_rating IS NULL OR p.average_rating >= $min_rating)
RETURN p.id AS id, p.title AS title, p.price AS price, p.average_rating AS average_rating,
       p.rating_count AS rating_count, b.name AS brand_name, c.id AS category_id, p.image_url AS image_url
ORDER BY p.rating_count DESC, p.average_rating DESC"""
        return query, params

    def _build_comparison_query(self, product_ids: List[str]) -> Tuple[str, Dict[str, Any]]:
        params = {"product_ids": product_ids}
        query = """MATCH (p:Product)
WHERE p.id IN $product_ids
OPTIONAL MATCH (p)-[:BRANDED_BY]->(b:Brand)
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
RETURN p.id AS id, p.title AS title, p.price AS price, p.average_rating AS average_rating,
       p.rating_count AS rating_count, p.features AS features, p.description AS description,
       p.details AS details, b.name AS brand_name, c.id AS category_id, p.image_url AS image_url"""
        return query, params

    def _build_review_query(self, product_id: str) -> Tuple[str, Dict[str, Any]]:
        params = {"product_id": product_id}
        query = """MATCH (p:Product {id: $product_id})<-[:REVIEWS]-(r:Review)
OPTIONAL MATCH (u:User)-[:WROTE]->(r)
RETURN r.id AS id, r.rating AS rating, r.title AS title, r.text AS text,
       r.timestamp AS timestamp, r.verified_purchase AS verified_purchase,
       r.helpful_votes AS helpful_votes, r.variant_asin AS variant_asin, u.id AS user_id
ORDER BY r.helpful_votes DESC, r.timestamp DESC"""
        return query, params

    def _build_shared_purchaser_query(self, product_id: str) -> Tuple[str, Dict[str, Any]]:
        params = {"product_id": product_id}
        query = """MATCH (p1:Product {id: $product_id})<-[:PURCHASED]-(u:User)-[:PURCHASED]->(p2:Product)
WHERE p1 <> p2
WITH p2, count(DISTINCT u) AS shared_purchasers
OPTIONAL MATCH (p2)-[:BRANDED_BY]->(b:Brand)
OPTIONAL MATCH (p2)-[:BELONGS_TO]->(c:Category)
RETURN p2.id AS id, p2.title AS title, p2.price AS price, p2.average_rating AS average_rating,
       p2.rating_count AS rating_count, b.name AS brand_name, c.id AS category_id,
       shared_purchasers, p2.image_url AS image_url
ORDER BY shared_purchasers DESC, p2.average_rating DESC"""
        return query, params

    def _build_category_query(self, category_name: Optional[str]) -> Tuple[str, Dict[str, Any]]:
        params = {"category_name": category_name}
        query = """MATCH (c:Category)
WHERE ($category_name IS NULL OR toLower(c.name) CONTAINS toLower($category_name))
MATCH (p:Product)-[:BELONGS_TO]->(c)
OPTIONAL MATCH (p)-[:BRANDED_BY]->(b:Brand)
RETURN c.id AS category_id, c.name AS category_name, count(DISTINCT p) AS product_count,
       collect(DISTINCT b.name)[..10] AS top_brands
ORDER BY product_count DESC"""
        return query, params


cypher_generator = CypherGenerator()
