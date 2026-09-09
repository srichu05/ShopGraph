"""Product comparison endpoint."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from app.schemas.comparison import ComparisonRequest, ComparisonResponse, ProductComparisonItem
from app.schemas.evidence import EvidenceItem, EvidenceType
from app.services.retrieval.graph_retriever import graph_retriever
from app.services.reviews.intelligence import review_intelligence
from app.services.llm.grounded_generator import grounded_generator
from app.db.neo4j.connection import neo4j_client

router = APIRouter(prefix="/compare", tags=["Comparison"])


@router.post("", response_model=ComparisonResponse)
def compare_products(req: ComparisonRequest):
    """Generates side-by-side product comparisons, feature matrices, and grounded trade-off analysis."""
    if not neo4j_client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is currently unreachable.",
        )

    products = []
    comparison_items: List[ProductComparisonItem] = []
    matrix: Dict[str, Dict[str, Any]] = {
        "title": {},
        "price": {},
        "rating": {},
        "rating_count": {},
        "brand": {},
        "category": {},
    }
    all_evidence: List[EvidenceItem] = []
    limitations: List[str] = []

    for pid in req.product_ids:
        prod = graph_retriever.get_product_by_id(pid)
        if not prod:
            limitations.append(f"Product '{pid}' could not be found in the catalog.")
            continue

        products.append(prod)
        matrix["title"][pid] = prod.title
        matrix["price"][pid] = f"${prod.price:.2f}" if prod.price is not None else "NULL"
        matrix["rating"][pid] = prod.average_rating
        matrix["rating_count"][pid] = prod.rating_count
        matrix["brand"][pid] = prod.brand_name
        matrix["category"][pid] = prod.category_id

        # Analyze reviews for this product
        rev_report = review_intelligence.analyze_product_reviews(pid, limit=15)

        # Extract top strengths and tradeoffs from aspects
        strengths = [a.aspect for a in rev_report.aspects if a.sentiment == "positive"]
        tradeoffs = [a.aspect for a in rev_report.aspects if a.sentiment == "negative"]

        comparison_items.append(
            ProductComparisonItem(
                product=prod,
                review_intelligence=rev_report,
                strengths=strengths[:3],
                tradeoffs=tradeoffs[:3],
            )
        )

        all_evidence.append(
            EvidenceItem(
                id=f"ev_comp_{pid}",
                evidence_type=EvidenceType.OBSERVED_GRAPH_FACT,
                source="Product",
                product_id=pid,
                value={"price": prod.price, "rating": prod.average_rating},
                description=f"Comparison facts for {prod.title} (ID: {pid})",
            )
        )

    if len(comparison_items) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least two valid products are required for comparison.",
        )

    # Optional grounded LLM synthesis
    from app.schemas.evidence import UnifiedEvidence
    unified = UnifiedEvidence(query=f"Compare {req.product_ids}", graph_facts=all_evidence)
    synthesis = grounded_generator.generate_response(
        query=f"Compare products: {', '.join(req.product_ids)} focusing on {req.focus_aspects or 'key features and value'}",
        products=products,
        evidence=unified,
        details=products,
    )

    return ComparisonResponse(
        products=comparison_items,
        matrix=matrix,
        llm_synthesis=synthesis,
        evidence_items=all_evidence,
        limitations=limitations,
    )
