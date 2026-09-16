"""Natural-language Graph-RAG query endpoint."""

import time
from fastapi import APIRouter, HTTPException, status
from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_understanding.parser import query_parser
from app.services.retrieval.hybrid_retriever import hybrid_retriever
from app.services.llm.grounded_generator import grounded_generator
from app.db.neo4j.connection import neo4j_client

router = APIRouter(prefix="/query", tags=["Graph-RAG"])


@router.post("", response_model=QueryResponse)
def run_natural_language_query(req: QueryRequest):
    """
    Executes the end-to-end Graph-RAG pipeline:
    Query Understanding -> Hybrid Retrieval -> Evidence Fusion -> Grounded Synthesis.
    """
    if not neo4j_client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is currently unreachable. Start Neo4j or configure Aura credentials in .env.",
        )

    t0 = time.perf_counter()

    # 1. Query Understanding
    constraints = query_parser.parse(req.query)
    t_parse = time.perf_counter()

    # 2. Hybrid Retrieval & Evidence Fusion
    products, unified_evidence, cypher_used = hybrid_retriever.retrieve(
        constraints=constraints,
        strategy_override=req.strategy_override,
        limit=req.limit,
    )
    t_retrieve = time.perf_counter()

    # 3. Grounded Answer Synthesis
    answer = grounded_generator.generate_response(
        query=req.query,
        products=products,
        evidence=unified_evidence,
    )
    t_gen = time.perf_counter()

    # Collect any data limitations
    limitations = []
    if any(p.price is None for p in products):
        limitations.append("One or more retrieved products have unlisted (NULL) prices in the catalog.")

    total_evidence = unified_evidence.graph_facts + unified_evidence.vector_evidence + unified_evidence.review_evidence
    latencies = {
        "query_understanding": round((t_parse - t0) * 1000, 2),
        "retrieval": round((t_retrieve - t_parse) * 1000, 2),
        "generation": round((t_gen - t_retrieve) * 1000, 2),
        "total": round((t_gen - t0) * 1000, 2),
    }

    # Lightweight structured observability (zero credentials or keys logged)
    import uuid, json, logging
    obs_logger = logging.getLogger("shopgraph.observability")
    obs_logger.info(
        "QUERY_EVENT: %s",
        json.dumps({
            "query_id": str(uuid.uuid4()),
            "intent": constraints.intent.value,
            "strategy": (req.strategy_override or constraints.strategy).value,
            "candidate_count": len(products),
            "evidence_count": len(total_evidence),
            "latency_ms": latencies,
        }),
    )

    return QueryResponse(
        query=req.query,
        intent=constraints.intent,
        strategy_used=req.strategy_override or constraints.strategy,
        answer=answer,
        products=products,
        evidence=total_evidence,
        cypher_executed=cypher_used,
        explanation=f"Identified intent as '{constraints.intent.value}' using strategy '{constraints.strategy.value}'. Retrieved {len(products)} matching candidate products.",
        limitations=limitations,
        latency_breakdown_ms=latencies,
    )
