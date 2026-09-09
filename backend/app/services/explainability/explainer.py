"""
ShopGraph Explainability Service
================================
Constructs transparent, multi-factor explanation reports for recommendations and search results.
Strictly separates:
- OBSERVED_GRAPH_FACT: Grounded Neo4j properties and edges
- VECTOR_SIMILARITY: ANN embedding similarity scores
- REVIEW_EVIDENCE: Customer review text and verified purchase flags
- RECOMMENDATION_INFERENCE: Algorithmic composite score contributions
"""

from typing import Any, Dict, List, Optional
from app.schemas.evidence import EvidenceItem, EvidenceType
from app.schemas.product import ProductSummary, ProductDetail
from app.schemas.explainability import ExplanationReport, FactorContribution, GraphPathStep


class ExplainabilityService:
    """Generates transparent, granular attribution for recommendation rationales."""

    def build_explanation(
        self,
        product: ProductSummary,
        factors: List[FactorContribution],
        detail: Optional[ProductDetail] = None,
        shared_purchasers_count: int = 0,
        semantic_score: Optional[float] = None,
        review_quotes: Optional[List[str]] = None,
    ) -> ExplanationReport:
        """Assembles a full explanation report with factor decomposition and graph paths."""
        observed_facts: List[str] = []
        inferred_aspects: List[str] = []
        limitations: List[str] = []
        graph_paths: List[List[GraphPathStep]] = []

        # 1. Price evidence
        if product.price is not None:
            observed_facts.append(f"Product price is listed at ${product.price:.2f} USD.")
        else:
            limitations.append("Price is unlisted/null in the dataset; cannot filter by budget.")

        # 2. Rating & Volume
        if product.average_rating:
            observed_facts.append(
                f"Customer satisfaction is rated {product.average_rating:.1f}/5.0 based on {product.rating_count} recorded reviews."
            )
        else:
            limitations.append("No ratings recorded for this product.")

        # 3. Brand & Category paths
        if product.brand_name:
            observed_facts.append(f"Branded by {product.brand_name}.")
            graph_paths.append([
                GraphPathStep(
                    start_node=product.id,
                    start_label="Product",
                    relationship="BRANDED_BY",
                    end_node=product.brand_name,
                    end_label="Brand",
                )
            ])

        if product.category_id:
            observed_facts.append(f"Classified under category: {product.category_id}.")
            graph_paths.append([
                GraphPathStep(
                    start_node=product.id,
                    start_label="Product",
                    relationship="BELONGS_TO",
                    end_node=product.category_id,
                    end_label="Category",
                )
            ])

        # 4. Shared Verified Purchasers (Multi-hop graph traversal)
        if shared_purchasers_count > 0:
            observed_facts.append(
                f"Traversed {shared_purchasers_count} shared verified purchasers connecting to this product."
            )
            graph_paths.append([
                GraphPathStep(
                    start_node=product.id,
                    start_label="Product",
                    relationship="PURCHASED",
                    end_node="SharedUsers",
                    end_label="User",
                ),
                GraphPathStep(
                    start_node="SharedUsers",
                    start_label="User",
                    relationship="PURCHASED",
                    end_node="TargetProduct",
                    end_label="Product",
                ),
            ])

        # 5. Semantic similarity
        if semantic_score is not None:
            inferred_aspects.append(
                f"Semantic ANN similarity score of {semantic_score:.2f} against query intent."
            )

        # Build concise summary reason
        top_factors = sorted(factors, key=lambda f: f.weighted_score, reverse=True)[:2]
        factor_reasons = [f.explanation for f in top_factors]
        summary_reason = f"Recommended because {'; '.join(factor_reasons)}." if factor_reasons else "Recommended based on overall catalog ranking."

        return ExplanationReport(
            product_id=product.id,
            product_title=product.title,
            summary_reason=summary_reason,
            factors=factors,
            graph_paths=graph_paths,
            review_evidence_quotes=review_quotes or [],
            observed_facts=observed_facts,
            inferred_aspects=inferred_aspects,
            limitations=limitations,
        )


explainer = ExplainabilityService()
