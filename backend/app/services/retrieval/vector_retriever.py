"""
ShopGraph Vector & Semantic Retriever
=====================================
Executes approximate nearest neighbor (ANN) retrieval over Neo4j vector indexes
using text embeddings. Generates EvidenceItems classified strictly as
`VECTOR_SIMILARITY` to prevent conflation with observed graph facts.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.db.neo4j.connection import neo4j_client
from app.schemas.evidence import EvidenceItem, EvidenceType
from app.schemas.product import ProductSummary
from app.services.embeddings import get_embedding_provider

logger = logging.getLogger("shopgraph.retrieval.vector")


class VectorRetriever:
    """Retrieves semantically similar products and reviews via vector indexes."""

    def __init__(self, db_client=None, embedding_provider=None):
        self.client = db_client or neo4j_client
        self.embedder = embedding_provider or get_embedding_provider()

    def search_products(
        self,
        query_text: str,
        limit: int = 10,
        index_name: str = "product_text_embeddings",
    ) -> Tuple[List[Tuple[ProductSummary, float]], List[EvidenceItem]]:
        """
        Embeds query text and executes ANN search against Neo4j vector index.
        Returns list of (ProductSummary, similarity_score) and granular EvidenceItems.
        """
        if not self.client.is_available():
            logger.warning("Neo4j vector search unavailable: database unreachable.")
            return [], []

        query_vec = self.embedder.embed_text(query_text)
        cypher = f"""
        CALL db.index.vector.queryNodes('{index_name}', $limit, $query_vector)
        YIELD node AS p, score
        OPTIONAL MATCH (p)-[:BRANDED_BY]->(b:Brand)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
        RETURN p.id AS id, p.title AS title, p.price AS price, p.average_rating AS average_rating,
               p.rating_count AS rating_count, b.name AS brand_name, c.id AS category_id,
               p.image_url AS image_url, score
        ORDER BY score DESC
        """
        params = {
            "limit": min(limit, settings.MAX_RETRIEVAL_LIMIT),
            "query_vector": query_vec,
        }

        try:
            records = self.client.execute_read(cypher, params)
        except Exception as e:
            logger.warning("Vector index '%s' query failed or index not yet created: %s", index_name, e)
            return [], []

        results: List[Tuple[ProductSummary, float]] = []
        evidence: List[EvidenceItem] = []

        for r in records:
            p_id = r["id"]
            score = float(r.get("score", 0.0))
            prod = ProductSummary(
                id=p_id,
                title=r.get("title") or "",
                price=r.get("price"),
                average_rating=r.get("average_rating"),
                rating_count=r.get("rating_count", 0),
                brand_name=r.get("brand_name"),
                category_id=r.get("category_id"),
                image_url=r.get("image_url"),
            )
            results.append((prod, score))

            evidence.append(EvidenceItem(
                id=f"ev_vec_{p_id}",
                evidence_type=EvidenceType.VECTOR_SIMILARITY,
                source="Neo4jVectorIndex.product_text_embeddings",
                product_id=p_id,
                value=round(score, 4),
                description=f"Semantic similarity score: {score:.2f} for query '{query_text}'",
                confidence=score,
            ))

        return results, evidence

    def search_reviews(
        self,
        query_text: str,
        limit: int = 10,
        product_id: Optional[str] = None,
        index_name: str = "review_text_embeddings",
    ) -> List[Tuple[Dict[str, Any], float, EvidenceItem]]:
        """Searches reviews for specific qualitative feedback aspects."""
        if not self.client.is_available():
            return []

        query_vec = self.embedder.embed_text(query_text)
        cypher = f"""
        CALL db.index.vector.queryNodes('{index_name}', $limit, $query_vector)
        YIELD node AS r, score
        MATCH (r)-[:REVIEWS]->(p:Product)
        WHERE ($product_id IS NULL OR p.id = $product_id)
        RETURN r.id AS id, r.text AS text, r.title AS title, r.rating AS rating,
               r.verified_purchase AS verified_purchase, p.id AS product_id, score
        ORDER BY score DESC
        """
        params = {
            "limit": min(limit, settings.MAX_RETRIEVAL_LIMIT),
            "query_vector": query_vec,
            "product_id": product_id,
        }

        try:
            records = self.client.execute_read(cypher, params)
        except Exception as e:
            logger.warning("Review vector query failed: %s", e)
            return []

        results = []
        for r in records:
            score = float(r.get("score", 0.0))
            r_id = r["id"]
            p_id = r["product_id"]
            ev = EvidenceItem(
                id=f"ev_rev_vec_{r_id}",
                evidence_type=EvidenceType.VECTOR_SIMILARITY,
                source="Neo4jVectorIndex.review_text_embeddings",
                product_id=p_id,
                value=round(score, 4),
                description=f"Review snippet matched aspect '{query_text}' (score: {score:.2f})",
                confidence=score,
                metadata={"review_text": r.get("text", "")[:200]},
            )
            results.append((r, score, ev))
        return results


vector_retriever = VectorRetriever()
