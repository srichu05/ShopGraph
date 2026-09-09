"""
ShopGraph Hybrid Retriever
==========================
Coordinates Graph-only, Vector-only, and Hybrid Graph+Vector retrieval.
Merges candidate sets using Reciprocal Rank Fusion (RRF) and fuses evidence.
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
    """Combines structured graph filtering with semantic ANN ranking."""

    def __init__(
        self,
        g_retriever: Optional[GraphRetriever] = None,
        v_retriever: Optional[VectorRetriever] = None,
    ):
        self.graph = g_retriever or graph_retriever
        self.vector = v_retriever or vector_retriever

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

        # 3. Strategy Resolution & Ranking
        final_products: List[ProductSummary] = []

        if strategy == RetrievalStrategy.GRAPH_ONLY:
            final_products = graph_products[:target_limit]
        elif strategy == RetrievalStrategy.VECTOR_ONLY:
            final_products = [p for p, _ in vector_products][:target_limit]
        else:
            # HYBRID: Merge using Reciprocal Rank Fusion (RRF)
            final_products = self._reciprocal_rank_fusion(
                graph_products, vector_products, k=settings.RRF_K, limit=target_limit
            )

        # 4. Fuse all evidence
        unified_evidence = evidence_fusion.fuse(
            query=constraints.raw_query,
            graph_facts=graph_evidence,
            vector_evidence=vector_evidence,
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
