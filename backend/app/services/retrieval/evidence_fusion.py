"""
ShopGraph Evidence Fusion Layer
===============================
Merges, categorizes, and deduplicates evidence from structured Graph queries,
vector ANN searches, and review analyses while maintaining strict provenance.
"""

from collections import defaultdict
from typing import Dict, List, Optional
from app.schemas.evidence import EvidenceItem, EvidenceType, UnifiedEvidence
from app.schemas.product import ProductSummary


class EvidenceFusionEngine:
    """Fuses multi-modal graph and vector evidence into a unified, traceable evidence package."""

    def fuse(
        self,
        query: str,
        graph_facts: Optional[List[EvidenceItem]] = None,
        vector_evidence: Optional[List[EvidenceItem]] = None,
        review_evidence: Optional[List[EvidenceItem]] = None,
        inferred_evidence: Optional[List[EvidenceItem]] = None,
    ) -> UnifiedEvidence:
        """Merges all retrieved evidence streams, removing duplicates by item ID."""
        seen_ids = set()

        deduped_graph = []
        for item in (graph_facts or []):
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                deduped_graph.append(item)

        deduped_vector = []
        for item in (vector_evidence or []):
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                deduped_vector.append(item)

        deduped_review = []
        for item in (review_evidence or []):
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                deduped_review.append(item)

        deduped_inferred = []
        for item in (inferred_evidence or []):
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                deduped_inferred.append(item)

        return UnifiedEvidence(
            query=query,
            graph_facts=deduped_graph,
            vector_evidence=deduped_vector,
            review_evidence=deduped_review,
            inferred_evidence=deduped_inferred,
        )

    def group_by_product(self, evidence: UnifiedEvidence) -> Dict[str, List[EvidenceItem]]:
        """Groups evidence items by canonical product_id (parent_asin)."""
        grouped = defaultdict(list)
        all_items = (
            evidence.graph_facts
            + evidence.vector_evidence
            + evidence.review_evidence
            + evidence.inferred_evidence
        )
        for item in all_items:
            if item.product_id:
                grouped[item.product_id].append(item)
            else:
                grouped["global"].append(item)
        return dict(grouped)


evidence_fusion = EvidenceFusionEngine()
