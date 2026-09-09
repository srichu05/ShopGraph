"""
ShopGraph Multi-Dimensional Recommendation Engine
=================================================
Calculates explainable, multi-factor recommendation scores across:
- Category relevance (w_category)
- Rating quality with Bayesian volume shrinkage (w_rating)
- Price / budget satisfaction (w_price)
- Brand match & reputation (w_brand)
- Semantic relevance (w_semantic)
- Shared verified purchaser graph traversal (w_purchaser_overlap)
"""

import math
from typing import Dict, List, Optional, Tuple
from app.config import settings
from app.schemas.evidence import EvidenceItem, EvidenceType
from app.schemas.product import ProductSummary, ProductDetail
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendedProduct,
)
from app.schemas.explainability import FactorContribution
from app.services.retrieval.graph_retriever import graph_retriever, GraphRetriever
from app.services.retrieval.vector_retriever import vector_retriever, VectorRetriever
from app.services.explainability.explainer import explainer, ExplainabilityService


class RecommendationEngine:
    """Computes transparent, multi-dimensional product recommendations."""

    def __init__(
        self,
        g_retriever: Optional[GraphRetriever] = None,
        v_retriever: Optional[VectorRetriever] = None,
        exp_service: Optional[ExplainabilityService] = None,
    ):
        self.graph = g_retriever or graph_retriever
        self.vector = v_retriever or vector_retriever
        self.explainer = exp_service or explainer

    def recommend(
        self,
        req: RecommendationRequest,
        semantic_scores: Optional[Dict[str, float]] = None,
    ) -> RecommendationResponse:
        """Generates ranked, explainable product recommendations."""
        # 1. Resolve scoring weights (defaults from settings or request override)
        weights = self._resolve_weights(req.custom_weights)

        # Resolve explicit semantic scores mapping (from request payload or explicit argument)
        scores_map: Dict[str, float] = {}
        if req.semantic_scores:
            scores_map.update(req.semantic_scores)
        if semantic_scores:
            scores_map.update(semantic_scores)

        # 2. Gather candidates
        candidates: List[ProductSummary] = []
        shared_purchaser_map: Dict[str, int] = {}
        all_evidence: List[EvidenceItem] = []

        # If base product_id is provided, traverse shared verified purchasers
        if req.product_id:
            try:
                overlap_results = self.graph.get_shared_verified_purchasers(
                    req.product_id, limit=req.limit * 3
                )
                for prod, shared_cnt, ev in overlap_results:
                    candidates.append(prod)
                    shared_purchaser_map[prod.id] = shared_cnt
                    all_evidence.append(ev)
            except Exception:
                pass

        # Also search by category / query
        if req.category_id or req.query or not candidates:
            from app.schemas.query import ExtractedConstraints, QueryIntent
            constraints = ExtractedConstraints(
                intent=QueryIntent.RECOMMENDATION,
                category_name=req.category_id,
                brand_name=req.brand_name,
                price_max=req.max_price,
                rating_min=req.min_rating,
                raw_query=req.query or (f"products in {req.category_id}" if req.category_id else "top products"),
            )
            try:
                search_prods, search_ev, _ = self.graph.search_products(
                    constraints, limit=req.limit * 3
                )
                candidates.extend(search_prods)
                all_evidence.extend(search_ev)
            except Exception:
                pass

        # Deduplicate candidates
        seen_ids = set()
        unique_candidates: List[ProductSummary] = []
        for c in candidates:
            if c.id not in seen_ids and c.id != req.product_id:
                seen_ids.add(c.id)
                unique_candidates.append(c)

        # 3. Score and rank candidates
        scored_products: List[RecommendedProduct] = []

        for prod in unique_candidates:
            cand_sem_score = scores_map.get(prod.id)
            factors, composite_score = self._score_product(
                prod=prod,
                req=req,
                weights=weights,
                shared_purchasers=shared_purchaser_map.get(prod.id, 0),
                semantic_score=cand_sem_score,
            )

            explanation = self.explainer.build_explanation(
                product=prod,
                factors=factors,
                shared_purchasers_count=shared_purchaser_map.get(prod.id, 0),
                semantic_score=cand_sem_score,
            )

            scored_products.append(
                RecommendedProduct(
                    product=prod,
                    composite_score=round(composite_score, 4),
                    explanation=explanation,
                )
            )

        # Sort descending by composite score
        scored_products.sort(key=lambda x: x.composite_score, reverse=True)
        final_recs = scored_products[:req.limit]

        return RecommendationResponse(
            query=req.query,
            target_product_id=req.product_id,
            recommendations=final_recs,
            total_found=len(scored_products),
            weights_applied=weights,
            evidence_items=all_evidence[:15],
        )

    def _resolve_weights(self, custom: Optional[Dict[str, float]]) -> Dict[str, float]:
        base = {
            "category": settings.REC_WEIGHT_CATEGORY,
            "rating": settings.REC_WEIGHT_RATING,
            "price": settings.REC_WEIGHT_PRICE,
            "brand": settings.REC_WEIGHT_BRAND,
            "semantic": settings.REC_WEIGHT_SEMANTIC,
            "purchaser_overlap": settings.REC_WEIGHT_PURCHASER_OVERLAP,
        }
        if custom:
            for k, v in custom.items():
                if k in base and isinstance(v, (int, float)) and v >= 0:
                    base[k] = float(v)

        # Normalize to sum to 1.0
        total = sum(base.values())
        if total > 0:
            return {k: round(v / total, 4) for k, v in base.items()}
        return base

    def _score_product(
        self,
        prod: ProductSummary,
        req: RecommendationRequest,
        weights: Dict[str, float],
        shared_purchasers: int,
        semantic_score: Optional[float] = None,
    ) -> Tuple[List[FactorContribution], float]:
        factors: List[FactorContribution] = []
        composite = 0.0

        # Factor 1: Category match
        cat_score = 0.5
        cat_desc = "Category is in related taxonomy"
        if req.category_id and prod.category_id:
            if req.category_id.lower() in prod.category_id.lower():
                cat_score = 1.0
                cat_desc = f"Matches category '{req.category_id}'"
        f_cat = FactorContribution(
            factor_name="category_match",
            weight=weights["category"],
            score=round(cat_score, 4),
            weighted_score=round(cat_score * weights["category"], 4),
            evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
            explanation=cat_desc,
        )
        factors.append(f_cat)
        composite += f_cat.weighted_score

        # Factor 2: Bayesian-adjusted Rating Score
        # Bayesian shrinkage: (v * R + m * C) / (v + m)
        # C = 4.2 (dataset mean), m = 5 (prior strength)
        C = 4.2
        m = 5
        v = prod.rating_count
        R = prod.average_rating if prod.average_rating is not None else C
        bayesian_r = (v * R + m * C) / (v + m)
        rating_score = min(1.0, max(0.0, bayesian_r / 5.0))
        f_rating = FactorContribution(
            factor_name="rating_quality",
            weight=weights["rating"],
            score=round(rating_score, 4),
            weighted_score=round(rating_score * weights["rating"], 4),
            evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
            explanation=f"Bayesian-adjusted rating of {bayesian_r:.2f}/5.0 based on {v} reviews",
        )
        factors.append(f_rating)
        composite += f_rating.weighted_score

        # Factor 3: Price / Budget fit
        price_score = 0.5
        price_desc = "Price within average market range"
        if prod.price is not None:
            if req.max_price is not None:
                if prod.price <= req.max_price:
                    # Closer to budget ceiling with good value
                    price_score = 0.8 + 0.2 * (1.0 - (prod.price / req.max_price))
                    price_desc = f"Affordable price of ${prod.price:.2f} is well within budget ceiling of ${req.max_price:.2f}"
                else:
                    price_score = max(0.0, 1.0 - ((prod.price - req.max_price) / req.max_price))
                    price_desc = f"Price of ${prod.price:.2f} exceeds budget of ${req.max_price:.2f}"
            else:
                price_score = 0.7
                price_desc = f"Price listed at ${prod.price:.2f}"
        else:
            price_score = 0.4
            price_desc = "Price unlisted in catalog"

        f_price = FactorContribution(
            factor_name="price_fit",
            weight=weights["price"],
            score=round(price_score, 4),
            weighted_score=round(price_score * weights["price"], 4),
            evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
            explanation=price_desc,
        )
        factors.append(f_price)
        composite += f_price.weighted_score

        # Factor 4: Brand match
        brand_score = 0.5
        brand_desc = "Standard brand presence"
        if req.brand_name and prod.brand_name:
            if req.brand_name.lower() in prod.brand_name.lower():
                brand_score = 1.0
                brand_desc = f"Exact match for brand '{req.brand_name}'"
        elif prod.brand_name:
            brand_score = 0.7
            brand_desc = f"Established brand '{prod.brand_name}'"

        f_brand = FactorContribution(
            factor_name="brand_reputation",
            weight=weights["brand"],
            score=round(brand_score, 4),
            weighted_score=round(brand_score * weights["brand"], 4),
            evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
            explanation=brand_desc,
        )
        factors.append(f_brand)
        composite += f_brand.weighted_score

        # Factor 5: Semantic Relevance
        if semantic_score is not None:
            sem_val = max(0.0, min(1.0, float(semantic_score)))
            f_sem = FactorContribution(
                factor_name="semantic_relevance",
                weight=weights["semantic"],
                score=round(sem_val, 4),
                weighted_score=round(sem_val * weights["semantic"], 4),
                evidence_type=EvidenceType.VECTOR_SIMILARITY,
                explanation=f"Semantic vector similarity score: {sem_val:.2f}",
            )
        else:
            # Explicit neutral fallback when no vector score is available - do not fabricate similarity
            neutral_val = 0.5
            f_sem = FactorContribution(
                factor_name="semantic_relevance",
                weight=weights["semantic"],
                score=round(neutral_val, 4),
                weighted_score=round(neutral_val * weights["semantic"], 4),
                evidence_type=EvidenceType.RECOMMENDATION_INFERENCE,
                explanation="Semantic similarity score unavailable; neutral fallback applied",
            )
        factors.append(f_sem)
        composite += f_sem.weighted_score

        # Factor 6: Shared Verified Purchaser Overlap
        overlap_score = 0.0
        overlap_desc = "No shared purchaser overlap observed"
        if shared_purchasers > 0:
            # Diminishing returns log scale
            overlap_score = min(1.0, math.log1p(shared_purchasers) / math.log1p(20))
            overlap_desc = f"{shared_purchasers} verified purchasers associated with both products"

        f_overlap = FactorContribution(
            factor_name="purchaser_overlap",
            weight=weights["purchaser_overlap"],
            score=round(overlap_score, 4),
            weighted_score=round(overlap_score * weights["purchaser_overlap"], 4),
            evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
            explanation=overlap_desc,
        )
        factors.append(f_overlap)
        composite += f_overlap.weighted_score

        return factors, composite


recommendation_engine = RecommendationEngine()
