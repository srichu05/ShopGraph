"""
ShopGraph Context Construction Layer
====================================
Formats fused evidence into token-budgeted, provenance-tagged contexts
for grounded LLM answer synthesis.
"""

from typing import List, Optional
from app.schemas.evidence import UnifiedEvidence, EvidenceType
from app.schemas.product import ProductSummary, ProductDetail


class ContextBuilder:
    """Builds clean, structured evidence contexts for prompt injection."""

    def build_prompt_context(
        self,
        query: str,
        products: List[ProductSummary],
        evidence: UnifiedEvidence,
        details: Optional[List[ProductDetail]] = None,
        max_products: int = 5,
    ) -> str:
        """Constructs markdown evidence context with provenance labels."""
        lines = []
        lines.append("### RETRIEVED PRODUCT & GRAPH EVIDENCE")
        lines.append(f"User Query: \"{query}\"\n")

        if not products and evidence.total_count == 0:
            lines.append("No products or evidence matched the query constraints in the knowledge graph.\n")
            return "\n".join(lines)

        lines.append(f"Total Candidate Products Retrieved: {len(products)}")
        lines.append("Top Relevant Products:")

        # Detail lookup
        detail_map = {d.id: d for d in (details or [])}

        for idx, p in enumerate(products[:max_products], 1):
            p_detail = detail_map.get(p.id)
            lines.append(f"\n{idx}. Product: {p.title} (ID: {p.id})")
            price_str = f"${p.price:.2f}" if p.price is not None else "NULL / Not listed in dataset"
            rating_str = f"{p.average_rating:.1f}/5.0 ({p.rating_count} ratings)" if p.average_rating else "No ratings"
            lines.append(f"   - [OBSERVED GRAPH FACT] Price: {price_str}")
            lines.append(f"   - [OBSERVED GRAPH FACT] Rating: {rating_str}")
            if p.brand_name:
                lines.append(f"   - [OBSERVED GRAPH FACT] Brand: {p.brand_name}")
            if p.category_id:
                lines.append(f"   - [OBSERVED GRAPH FACT] Category Breadcrumb: {p.category_id}")

            if p_detail and p_detail.features:
                top_feats = "; ".join(p_detail.features[:3])
                lines.append(f"   - [OBSERVED GRAPH FACT] Features: {top_feats}")

        # Provenance Evidence Breakdown
        lines.append("\n### SUPPORTING EVIDENCE DETAILS")

        # 1. Graph facts
        if evidence.graph_facts:
            lines.append("\nObserved Knowledge Graph Facts:")
            for ev in evidence.graph_facts[:8]:
                lines.append(f"- [{ev.evidence_type.value}] {ev.description}")

        # 2. Vector similarities
        if evidence.vector_evidence:
            lines.append("\nSemantic Vector Retrieval Signals:")
            for ev in evidence.vector_evidence[:6]:
                lines.append(f"- [{ev.evidence_type.value}] {ev.description}")

        # 3. Review evidence
        if evidence.review_evidence:
            lines.append("\nReviewer Feedback Evidence:")
            for ev in evidence.review_evidence[:6]:
                lines.append(f"- [{ev.evidence_type.value}] {ev.description}")

        lines.append("\n### DATASET BOUNDARY CONSTRAINTS")
        lines.append("1. Review timestamps represent publication dates, NEVER purchase or order dates.")
        lines.append("2. Missing prices are NULL, NEVER assume $0 or free.")
        lines.append("3. Only verified_purchase=True indicates a verified transaction; current possession is unknown.")
        lines.append("4. Answer ONLY from facts listed above. If an aspect is missing, explicitly state it is not recorded in the dataset.")

        return "\n".join(lines)


context_builder = ContextBuilder()
