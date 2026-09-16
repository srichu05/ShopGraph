"""
ShopGraph Hybrid Retriever
==========================
Coordinates Graph-only, Vector-only, and Hybrid Graph+Vector retrieval.
Enforces hard structured user constraints (price ceiling/floor, brand, rating, category)
across candidate streams, merges candidate sets using Reciprocal Rank Fusion (RRF),
and fuses multi-modal evidence with strict provenance.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from app.config import settings
from app.schemas.query import ExtractedConstraints, RetrievalStrategy
from app.schemas.product import ProductSummary
from app.schemas.evidence import UnifiedEvidence, EvidenceItem
from app.services.retrieval.graph_retriever import graph_retriever, GraphRetriever
from app.services.retrieval.vector_retriever import vector_retriever, VectorRetriever
from app.services.retrieval.evidence_fusion import evidence_fusion

logger = logging.getLogger("shopgraph.retrieval.hybrid")


class HybridRetriever:
    """Combines structured graph filtering with semantic ANN ranking and hard constraint enforcement."""

    def __init__(
        self,
        g_retriever: Optional[GraphRetriever] = None,
        v_retriever: Optional[VectorRetriever] = None,
    ):
        self.graph = g_retriever or graph_retriever
        self.vector = v_retriever or vector_retriever

    def _satisfies_constraints(
        self,
        p: ProductSummary,
        constraints: ExtractedConstraints,
        strict_category: bool = True,
    ) -> bool:
        """Enforces hard structured constraints (price, brand, rating, category)."""
        # 1. Price ceiling constraint (e.g., 'under 300')
        if constraints.price_max is not None:
            if p.price is None or p.price > constraints.price_max:
                return False

        # 2. Price floor constraint (e.g., 'over 100')
        if constraints.price_min is not None:
            if p.price is None or p.price < constraints.price_min:
                return False

        # 3. Brand constraint (e.g., 'Yamaha')
        if constraints.brand_name:
            if not p.brand_name or constraints.brand_name.lower() not in p.brand_name.lower():
                return False

        # 4. Rating constraint (e.g., 'at least 4.5', '5 star')
        if constraints.rating_min is not None:
            if p.average_rating is None or p.average_rating < constraints.rating_min:
                return False

        # 5. Category constraint (exact hierarchy segment boundary)
        if strict_category and constraints.category_name:
            if not p.category_id:
                return False
            cat = constraints.category_name
            cid = p.category_id
            matched = (
                f" > {cat} > " in cid
                or cid.endswith(f" > {cat}")
                or cid == cat
            )
            if not matched:
                return False

        return True

    def retrieve(
        self,
        constraints: ExtractedConstraints,
        strategy_override: Optional[RetrievalStrategy] = None,
        limit: int = 10,
    ) -> Tuple[List[ProductSummary], UnifiedEvidence, Optional[str]]:
        """
        Executes retrieval according to selected or overridden strategy.
        Returns (ranked_products, unified_evidence, cypher_query_used).
        """
        strategy = strategy_override or constraints.strategy
        target_limit = min(limit, settings.MAX_RETRIEVAL_LIMIT)

        graph_products: List[ProductSummary] = []
        graph_evidence: List[EvidenceItem] = []
        cypher_used: Optional[str] = None

        vector_products: List[Tuple[ProductSummary, float]] = []
        vector_evidence: List[EvidenceItem] = []

        # 1. Execute Graph Retrieval if requested or hybrid
        if strategy in (RetrievalStrategy.GRAPH_ONLY, RetrievalStrategy.HYBRID):
            try:
                graph_products, graph_evidence, cypher_used = self.graph.search_products(
                    constraints, limit=target_limit * 2
                )
            except Exception as e:
                logger.warning("Graph retrieval failed or Neo4j unavailable: %s", e)

        # 2. Execute Vector Retrieval if requested or hybrid
        if strategy in (RetrievalStrategy.VECTOR_ONLY, RetrievalStrategy.HYBRID):
            try:
                vector_products, vector_evidence = self.vector.search_products(
                    constraints.raw_query, limit=target_limit * 2
                )
            except Exception as e:
                logger.warning("Vector retrieval failed or vector index not ready: %s", e)

        # 3. Filter candidates by explicit user constraints before ranking
        filtered_graph = [
            p for p in graph_products
            if self._satisfies_constraints(p, constraints, strict_category=True)
        ]
        filtered_vector = [
            (p, sc) for p, sc in vector_products
            if self._satisfies_constraints(p, constraints, strict_category=True)
        ]

        # If strict category matching eliminated all candidates, fall back to relaxed category matching
        if constraints.category_name and not filtered_graph and not filtered_vector:
            filtered_graph = [
                p for p in graph_products
                if self._satisfies_constraints(p, constraints, strict_category=False)
            ]
            filtered_vector = [
                (p, sc) for p, sc in vector_products
                if self._satisfies_constraints(p, constraints, strict_category=False)
            ]

        # 4. Strategy Resolution & Ranking
        final_products: List[ProductSummary] = []

        if strategy == RetrievalStrategy.GRAPH_ONLY:
            final_products = filtered_graph[:target_limit]
        elif strategy == RetrievalStrategy.VECTOR_ONLY:
            final_products = [p for p, _ in filtered_vector][:target_limit]
        else:
            # HYBRID: Merge using Reciprocal Rank Fusion (RRF)
            final_products = self._reciprocal_rank_fusion(
                filtered_graph, filtered_vector, k=settings.RRF_K, limit=target_limit
            )

        # Post-fusion constraint enforcement (defense-in-depth)
        final_products = [
            p for p in final_products
            if self._satisfies_constraints(p, constraints, strict_category=False)
        ]

        # 5. Fuse all evidence and restrict to returned products
        final_pids = {p.id for p in final_products}
        relevant_graph_ev = [
            ev for ev in graph_evidence
            if ev.product_id is None or ev.product_id in final_pids
        ]
        relevant_vector_ev = [
            ev for ev in vector_evidence
            if ev.product_id is None or ev.product_id in final_pids
        ]

        unified_evidence = evidence_fusion.fuse(
            query=constraints.raw_query,
            graph_facts=relevant_graph_ev,
            vector_evidence=relevant_vector_ev,
        )

        return final_products, unified_evidence, cypher_used

    def _reciprocal_rank_fusion(
        self,
        graph_items: List[ProductSummary],
        vector_items: List[Tuple[ProductSummary, float]],
        k: int = 60,
        limit: int = 10,
    ) -> List[ProductSummary]:
        """
        Applies standard RRF algorithm:
        RRF_score(d) = SUM (1 / (k + rank_i(d)))
        """
        scores = defaultdict(float)
        products_map: Dict[str, ProductSummary] = {}

        # Rank from graph
        for rank, p in enumerate(graph_items, 1):
            scores[p.id] += 1.0 / (k + rank)
            products_map[p.id] = p

        # Rank from vector
        for rank, (p, _) in enumerate(vector_items, 1):
            scores[p.id] += 1.0 / (k + rank)
            if p.id not in products_map:
                products_map[p.id] = p

        # Sort descending by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [products_map[pid] for pid in sorted_ids[:limit]]


hybrid_retriever = HybridRetriever()
