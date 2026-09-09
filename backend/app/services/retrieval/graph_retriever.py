"""
ShopGraph Graph Retriever
=========================
Executes validated Cypher against Neo4j, converting graph results into
typed domain entities (ProductDetail, ReviewItem) and granular EvidenceItems
with strict provenance tracking.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.db.neo4j.connection import neo4j_client
from app.schemas.evidence import EvidenceItem, EvidenceType
from app.schemas.product import ProductSummary, ProductDetail, BrandRef, CategoryRef
from app.schemas.review import ReviewItem
from app.schemas.query import ExtractedConstraints
from app.services.cypher.generator import cypher_generator
from app.services.cypher.validator import cypher_validator
from app.services.cypher.sanitizer import cypher_sanitizer

logger = logging.getLogger("shopgraph.retrieval.graph")


class GraphRetriever:
    """Retrieves structured entities and multi-hop paths from Neo4j."""

    def __init__(self, db_client=None):
        self.client = db_client or neo4j_client

    def search_products(
        self,
        constraints: ExtractedConstraints,
        limit: Optional[int] = None,
    ) -> Tuple[List[ProductSummary], List[EvidenceItem], str]:
        """
        Executes structured search based on constraints and returns summaries + evidence.
        """
        cypher, params = cypher_generator.generate_from_constraints(constraints, limit)
        records = self.client.execute_read(cypher, params)

        products: List[ProductSummary] = []
        evidence: List[EvidenceItem] = []

        for r in records:
            p_id = r.get("id")
            title = r.get("title", "")
            price = r.get("price")
            avg_r = r.get("average_rating")
            r_cnt = r.get("rating_count", 0)
            brand = r.get("brand_name")
            cat_id = r.get("category_id")
            img = r.get("image_url")

            prod = ProductSummary(
                id=p_id,
                title=title,
                price=price,
                average_rating=avg_r,
                rating_count=r_cnt,
                brand_name=brand,
                category_id=cat_id,
                image_url=img,
            )
            products.append(prod)

            # Record granular graph evidence
            if price is not None:
                evidence.append(EvidenceItem(
                    id=f"ev_price_{p_id}",
                    evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
                    source="Product.price",
                    product_id=p_id,
                    value=price,
                    description=f"Listed price: ${price:.2f}",
                ))
            if avg_r is not None:
                evidence.append(EvidenceItem(
                    id=f"ev_rating_{p_id}",
                    evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
                    source="Product.average_rating",
                    product_id=p_id,
                    value=avg_r,
                    description=f"Average rating: {avg_r:.1f} ({r_cnt} ratings)",
                ))
            if brand:
                evidence.append(EvidenceItem(
                    id=f"ev_brand_{p_id}",
                    evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
                    source="Product.brand_name",
                    product_id=p_id,
                    value=brand,
                    description=f"Brand: {brand}",
                ))
            if cat_id:
                evidence.append(EvidenceItem(
                    id=f"ev_cat_{p_id}",
                    evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
                    source="Product.category_id",
                    product_id=p_id,
                    value=cat_id,
                    description=f"Category: {cat_id}",
                ))

        return products, evidence, cypher

    def get_product_by_id(self, product_id: str) -> Optional[ProductDetail]:
        """Retrieves single rich product record with brand and category relationships."""
        cypher = """
        MATCH (p:Product {id: $product_id})
        OPTIONAL MATCH (p)-[:BRANDED_BY]->(b:Brand)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
        RETURN p.id AS id, p.title AS title, p.price AS price, p.average_rating AS average_rating,
               p.rating_count AS rating_count, p.features AS features, p.description AS description,
               p.details AS details, p.image_url AS image_url, p.raw_price AS raw_price,
               p.main_category AS main_category,
               b.id AS brand_id, b.name AS brand_name,
               c.id AS category_id, c.name AS category_name, c.level AS category_level, c.parent_id AS category_parent
        LIMIT 1
        """
        cypher_validator.assert_safe(cypher)
        records = self.client.execute_read(cypher, {"product_id": product_id})
        if not records:
            return None

        r = records[0]
        brand_ref = BrandRef(id=r["brand_id"], name=r["brand_name"]) if r.get("brand_id") else None
        cat_ref = (
            CategoryRef(
                id=r["category_id"],
                name=r["category_name"] or "",
                level=r.get("category_level", 0),
                parent_id=r.get("category_parent"),
            )
            if r.get("category_id")
            else None
        )

        return ProductDetail(
            id=r["id"],
            title=r.get("title") or "",
            price=r.get("price"),
            average_rating=r.get("average_rating"),
            rating_count=r.get("rating_count", 0),
            brand_name=r.get("brand_name"),
            category_id=r.get("category_id"),
            image_url=r.get("image_url"),
            brand=brand_ref,
            category=cat_ref,
            main_category=r.get("main_category"),
            features=r.get("features") or [],
            description=r.get("description") or [],
            details=r.get("details") or {},
            raw_price=r.get("raw_price"),
        )

    def get_reviews_for_product(self, product_id: str, limit: int = 10) -> List[ReviewItem]:
        """Retrieves reviews for a product ordered by helpful votes and recency."""
        cypher = """
        MATCH (p:Product {id: $product_id})<-[:REVIEWS]-(r:Review)
        OPTIONAL MATCH (u:User)-[:WROTE]->(r)
        RETURN r.id AS id, r.rating AS rating, r.title AS title, r.text AS text,
               r.timestamp AS timestamp, r.verified_purchase AS verified_purchase,
               r.helpful_votes AS helpful_votes, r.variant_asin AS variant_asin,
               coalesce(u.id, "anonymous") AS user_id, p.id AS product_id
        ORDER BY r.helpful_votes DESC, r.timestamp DESC
        LIMIT $limit
        """
        cypher_validator.assert_safe(cypher)
        params = {"product_id": product_id, "limit": min(limit, settings.MAX_RETRIEVAL_LIMIT)}
        records = self.client.execute_read(cypher, params)

        reviews = []
        for rec in records:
            reviews.append(ReviewItem(
                id=rec["id"],
                user_id=rec["user_id"],
                product_id=product_id,
                variant_asin=rec.get("variant_asin"),
                rating=float(rec.get("rating", 0.0)),
                title=rec.get("title"),
                text=rec.get("text"),
                timestamp=rec.get("timestamp", 0),
                verified_purchase=bool(rec.get("verified_purchase", False)),
                helpful_votes=int(rec.get("helpful_votes", 0)),
            ))
        return reviews

    def get_shared_verified_purchasers(
        self,
        product_id: str,
        limit: int = 5,
    ) -> List[Tuple[ProductSummary, int, EvidenceItem]]:
        """
        Dynamically traverses (p1)<-[:PURCHASED]-(u)-[:PURCHASED]->(p2).
        Returns list of (product_summary, shared_count, evidence_item).
        """
        cypher = """
        MATCH (p1:Product {id: $product_id})<-[:PURCHASED]-(u:User)-[:PURCHASED]->(p2:Product)
        WHERE p1 <> p2
        WITH p2, count(DISTINCT u) AS shared_purchasers
        OPTIONAL MATCH (p2)-[:BRANDED_BY]->(b:Brand)
        OPTIONAL MATCH (p2)-[:BELONGS_TO]->(c:Category)
        RETURN p2.id AS id, p2.title AS title, p2.price AS price, p2.average_rating AS average_rating,
               p2.rating_count AS rating_count, b.name AS brand_name, c.id AS category_id,
               shared_purchasers, p2.image_url AS image_url
        ORDER BY shared_purchasers DESC, p2.average_rating DESC
        LIMIT $limit
        """
        cypher_validator.assert_safe(cypher)
        params = {"product_id": product_id, "limit": min(limit, settings.MAX_RETRIEVAL_LIMIT)}
        records = self.client.execute_read(cypher, params)

        results = []
        for r in records:
            p2_id = r["id"]
            shared_cnt = int(r["shared_purchasers"])
            prod = ProductSummary(
                id=p2_id,
                title=r.get("title") or "",
                price=r.get("price"),
                average_rating=r.get("average_rating"),
                rating_count=r.get("rating_count", 0),
                brand_name=r.get("brand_name"),
                category_id=r.get("category_id"),
                image_url=r.get("image_url"),
            )
            ev = EvidenceItem(
                id=f"ev_shared_purchaser_{product_id}_{p2_id}",
                evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
                source="User-[:PURCHASED]->Product",
                product_id=p2_id,
                value=shared_cnt,
                description=f"{shared_cnt} verified purchasers reviewed both {product_id} and {p2_id}.",
            )
            results.append((prod, shared_cnt, ev))
        return results

    def get_comparison(self, product_ids: List[str]) -> List[ProductDetail]:
        """Retrieves details for multiple products for comparison."""
        products = []
        for pid in product_ids:
            p = self.get_product_by_id(pid)
            if p:
                products.append(p)
        return products


graph_retriever = GraphRetriever()
