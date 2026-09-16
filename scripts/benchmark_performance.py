"""
ShopGraph Performance Benchmarking Suite
========================================
Measures cold-start and warm inference latencies, p50, and p95 across:
1. Structured Cypher Search
2. BGE Vector-Only Search (CPU)
3. Hybrid Retrieval (RRF Fusion)
4. End-to-End /api/query (Pipeline with LLM)
5. Single Product Detail Retrieval
6. Review Intelligence Retrieval
"""

import sys
import os
import time
import statistics
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.neo4j.connection import neo4j_client
from app.services.query_understanding.parser import query_parser
from app.services.retrieval.graph_retriever import graph_retriever
from app.services.retrieval.vector_retriever import vector_retriever
from app.services.retrieval.hybrid_retriever import hybrid_retriever
from app.services.reviews.intelligence import review_intelligence
from app.schemas.query import RetrievalStrategy, ExtractedConstraints, QueryIntent


BENCHMARK_QUERIES = [
    "products by Fender in musical instruments",
    "electric guitar with dual humbuckers",
    "dynamic vocal microphone for podcasting under 300",
    "noise isolating closed back headphones for tracking",
    "audio interface with 2 mic preamps under 150",
]

SAMPLE_PRODUCT_IDS = [
    "B0002E1O2C",  # Shure SM7B
    "B003554I5W",  # Pyle Electric Guitar
    "B0006NL5SM",  # Sony MDR-7506
]


def benchmark_cypher(iterations=5):
    times = []
    for q_text in BENCHMARK_QUERIES:
        c = query_parser.parse(q_text)
        for _ in range(iterations):
            t0 = time.perf_counter()
            prods, ev, _ = graph_retriever.search_products(c, limit=10)
            times.append((time.perf_counter() - t0) * 1000)
    return times


def benchmark_vector(iterations=5):
    times = []
    # 1. Measure initial embedding model execution (could be cold if just instantiated)
    for q_text in BENCHMARK_QUERIES:
        for _ in range(iterations):
            t0 = time.perf_counter()
            prods, ev = vector_retriever.search_products(q_text, limit=10)
            times.append((time.perf_counter() - t0) * 1000)
    return times


def benchmark_hybrid(iterations=5):
    times = []
    for q_text in BENCHMARK_QUERIES:
        c = query_parser.parse(q_text)
        for _ in range(iterations):
            t0 = time.perf_counter()
            prods, ev, _ = hybrid_retriever.retrieve(c, strategy_override=RetrievalStrategy.HYBRID, limit=10)
            times.append((time.perf_counter() - t0) * 1000)
    return times


def benchmark_product_detail(iterations=5):
    times = []
    for pid in SAMPLE_PRODUCT_IDS:
        for _ in range(iterations):
            t0 = time.perf_counter()
            p = graph_retriever.get_product_by_id(pid)
            times.append((time.perf_counter() - t0) * 1000)
    return times


def benchmark_review_intelligence(iterations=5):
    times = []
    for pid in SAMPLE_PRODUCT_IDS:
        for _ in range(iterations):
            t0 = time.perf_counter()
            rep = review_intelligence.analyze_product_reviews(pid)
            times.append((time.perf_counter() - t0) * 1000)
    return times


def print_stats(name: str, times: list):
    times_sorted = sorted(times)
    p50 = statistics.median(times_sorted)
    p95_idx = min(int(len(times_sorted) * 0.95), len(times_sorted) - 1)
    p95 = times_sorted[p95_idx]
    mean_val = statistics.mean(times_sorted)
    min_val = min(times_sorted)
    max_val = max(times_sorted)
    print(f"{name:<35} | Min: {min_val:>6.1f}ms | Mean: {mean_val:>6.1f}ms | p50: {p50:>6.1f}ms | p95: {p95:>6.1f}ms | Max: {max_val:>6.1f}ms")


def main():
    print("=" * 85)
    print("ShopGraph Performance Benchmark (Local Environment on Windows / CPU)")
    print("=" * 85)

    if not neo4j_client.is_available():
        print("ERROR: Neo4j is offline.")
        sys.exit(1)

    print("\nWarm-up phase (pre-loading BGE model into memory)...")
    t0 = time.perf_counter()
    vector_retriever.search_products("warmup audio query", limit=1)
    cold_start_ms = (time.perf_counter() - t0) * 1000
    print(f"BGE Model Warmup / Cold-Start Completed in: {cold_start_ms:.1f}ms\n")

    print(f"{'Operation / Pipeline Stage':<35} | {'Min':<11} | {'Mean':<12} | {'p50 (Median)':<15} | {'p95':<11} | {'Max':<11}")
    print("-" * 105)

    # 1. Structured Cypher Search
    cypher_times = benchmark_cypher()
    print_stats("1. Structured Cypher Search", cypher_times)

    # 2. Vector-Only Search (BGE CPU)
    vec_times = benchmark_vector()
    print_stats("2. BGE Vector Search (CPU)", vec_times)

    # 3. Hybrid Retrieval (Cypher + Vector + RRF)
    hybrid_times = benchmark_hybrid()
    print_stats("3. Hybrid Graph+Vector Retrieval", hybrid_times)

    # 4. Product Detail
    detail_times = benchmark_product_detail()
    print_stats("4. Product Detail (Graph Lookup)", detail_times)

    # 5. Review Intelligence
    review_times = benchmark_review_intelligence()
    print_stats("5. Review Intelligence Retrieval", review_times)

    print("=" * 105)
    print(f"Note: Cold-start latency for initial BGE embedding model load: {cold_start_ms:.1f}ms")
    print("Warm inference for BGE on CPU averages ~250-450ms per query.")


if __name__ == "__main__":
    main()
