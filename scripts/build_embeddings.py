"""
ShopGraph — Vector Embeddings Generation & Indexing Pipeline (Phase 3)
=====================================================================
Generates real 768-dimensional embeddings for Products and Reviews,
stores them on Neo4j nodes (p.embedding and r.embedding), creates Neo4j
vector indexes, and waits for them to become ONLINE.

Usage:
    python scripts/build_embeddings.py
    python scripts/build_embeddings.py --batch-size 1000
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Set up project root in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

from app.config import settings
from app.db.neo4j.connection import neo4j_client
from app.services.embeddings import get_embedding_provider

DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
PRODUCTS_FILE = PROCESSED_DIR / "products.jsonl"
REVIEWS_FILE = PROCESSED_DIR / "reviews.jsonl"


def get_product_canonical_text(p: Dict[str, Any]) -> str:
    """Extract canonical product text representation for embedding."""
    title = p.get("title") or ""
    features = p.get("features") or []
    if isinstance(features, list):
        feat_text = " ".join(str(f) for f in features if f)
    else:
        feat_text = str(features)
    description = p.get("description") or []
    if isinstance(description, list):
        desc_text = " ".join(str(d) for d in description if d)
    else:
        desc_text = str(description)
    return f"{title} {feat_text} {desc_text}".strip()


def get_review_canonical_text(r: Dict[str, Any]) -> str:
    """Extract canonical review text representation for embedding."""
    title = r.get("title") or ""
    text = r.get("text") or ""
    return f"{title} {text}".strip()


def embed_and_update_products(batch_size: int = 1000) -> int:
    """Generates and writes product embeddings to Neo4j."""
    if not PRODUCTS_FILE.exists():
        raise FileNotFoundError(f"Products file not found: {PRODUCTS_FILE}")

    embedder = get_embedding_provider()
    print(f"\n--- Embedding Products ({PRODUCTS_FILE.name}) ---")
    print(f"Provider: {settings.EMBEDDING_PROVIDER} | Model: {embedder.model_name} | Dimension: {embedder.dimension}")

    total_count = 0
    batch: List[Dict[str, Any]] = []
    t_start = time.perf_counter()

    update_cypher = """
    UNWIND $batch AS item
    MATCH (p:Product {id: item.id})
    SET p.embedding = item.embedding
    """

    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            p_id = record.get("id")
            if not p_id:
                continue

            text = get_product_canonical_text(record)
            emb = embedder.embed_text(text)
            batch.append({"id": p_id, "embedding": emb})

            if len(batch) >= batch_size:
                neo4j_client.execute_write(update_cypher, {"batch": batch}, timeout_ms=120000)
                total_count += len(batch)
                rate = total_count / (time.perf_counter() - t_start)
                print(f"  Products processed: {total_count:,} ({rate:.1f} items/sec)")
                batch = []

    if batch:
        neo4j_client.execute_write(update_cypher, {"batch": batch}, timeout_ms=120000)
        total_count += len(batch)
        print(f"  Products processed: {total_count:,} (final batch written)")

    elapsed = time.perf_counter() - t_start
    print(f"Completed Product embeddings: {total_count:,} items in {elapsed:.1f}s ({total_count/elapsed:.1f} items/sec)")
    return total_count


def embed_and_update_reviews(batch_size: int = 2000) -> int:
    """Generates and writes review embeddings to Neo4j."""
    if not REVIEWS_FILE.exists():
        raise FileNotFoundError(f"Reviews file not found: {REVIEWS_FILE}")

    embedder = get_embedding_provider()
    print(f"\n--- Embedding Reviews ({REVIEWS_FILE.name}) ---")
    print(f"Provider: {settings.EMBEDDING_PROVIDER} | Model: {embedder.model_name} | Dimension: {embedder.dimension}")

    total_count = 0
    batch: List[Dict[str, Any]] = []
    t_start = time.perf_counter()

    update_cypher = """
    UNWIND $batch AS item
    MATCH (r:Review {id: item.id})
    SET r.embedding = item.embedding
    """

    with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            r_id = record.get("id")
            if not r_id:
                continue

            text = get_review_canonical_text(record)
            emb = embedder.embed_text(text)
            batch.append({"id": r_id, "embedding": emb})

            if len(batch) >= batch_size:
                neo4j_client.execute_write(update_cypher, {"batch": batch}, timeout_ms=120000)
                total_count += len(batch)
                rate = total_count / (time.perf_counter() - t_start)
                print(f"  Reviews processed: {total_count:,} ({rate:.1f} items/sec)")
                batch = []

    if batch:
        neo4j_client.execute_write(update_cypher, {"batch": batch}, timeout_ms=120000)
        total_count += len(batch)
        print(f"  Reviews processed: {total_count:,} (final batch written)")

    elapsed = time.perf_counter() - t_start
    print(f"Completed Review embeddings: {total_count:,} items in {elapsed:.1f}s ({total_count/elapsed:.1f} items/sec)")
    return total_count


def create_and_verify_vector_indexes(dimension: int = 768) -> None:
    """Creates Neo4j vector indexes and waits until they are ONLINE."""
    print("\n--- Creating Neo4j Vector Indexes ---")

    product_idx_cypher = f"""
    CREATE VECTOR INDEX product_text_embeddings IF NOT EXISTS
    FOR (p:Product) ON (p.embedding)
    OPTIONS {{indexConfig: {{`vector.dimensions`: {dimension}, `vector.similarity_function`: 'cosine'}}}}
    """

    review_idx_cypher = f"""
    CREATE VECTOR INDEX review_text_embeddings IF NOT EXISTS
    FOR (r:Review) ON (r.embedding)
    OPTIONS {{indexConfig: {{`vector.dimensions`: {dimension}, `vector.similarity_function`: 'cosine'}}}}
    """

    print("Creating index 'product_text_embeddings'...")
    neo4j_client.execute_write(product_idx_cypher, timeout_ms=120000)

    print("Creating index 'review_text_embeddings'...")
    neo4j_client.execute_write(review_idx_cypher, timeout_ms=120000)

    print("Waiting for vector indexes to become ONLINE...")
    max_wait_seconds = 120
    poll_interval = 2
    waited = 0

    target_indexes = {"product_text_embeddings", "review_text_embeddings"}

    while waited < max_wait_seconds:
        status_cypher = """
        SHOW INDEXES
        YIELD name, type, state, populationPercent, labelsOrTypes, properties
        WHERE name IN ['product_text_embeddings', 'review_text_embeddings']
        RETURN name, type, state, populationPercent, labelsOrTypes, properties
        """
        results = neo4j_client.execute_read(status_cypher)
        status_map = {r["name"]: r for r in results}

        all_online = True
        for name in target_indexes:
            idx = status_map.get(name)
            if not idx:
                all_online = False
                print(f"  Index {name} not found yet in SHOW INDEXES...")
                break
            state = idx.get("state")
            pop = idx.get("populationPercent", 0.0)
            print(f"  Index {name}: state={state}, population={pop}%")
            if state != "ONLINE":
                all_online = False

        if all_online:
            print("\nAll Neo4j vector indexes are ONLINE and ready for retrieval!")
            return

        time.sleep(poll_interval)
        waited += poll_interval

    raise TimeoutError(f"Vector indexes failed to reach ONLINE state within {max_wait_seconds} seconds.")


def verify_vector_layer() -> None:
    """Verifies populated embeddings and runs sample queries."""
    print("\n--- Verifying Vector Layer Integrity ---")

    # 1. Product embedding count and dimension check
    p_check = neo4j_client.execute_read("""
    MATCH (p:Product)
    WHERE p.embedding IS NOT NULL
    RETURN count(p) AS count, size(head(collect(p.embedding))) AS sample_dim
    """)[0]
    p_count = p_check["count"]
    p_dim = p_check["sample_dim"]
    print(f"Populated Product embeddings: {p_count:,} (Sample dimension: {p_dim})")

    # 2. Review embedding count and dimension check
    r_check = neo4j_client.execute_read("""
    MATCH (r:Review)
    WHERE r.embedding IS NOT NULL
    RETURN count(r) AS count, size(head(collect(r.embedding))) AS sample_dim
    """)[0]
    r_count = r_check["count"]
    r_dim = r_check["sample_dim"]
    print(f"Populated Review embeddings: {r_count:,} (Sample dimension: {r_dim})")

    # 3. Test Product vector search query
    embedder = get_embedding_provider()
    test_query = "Fender Stratocaster electric guitar sunburst"
    test_vec = embedder.embed_text(test_query)

    print(f"\nTesting Product Vector Search for: '{test_query}'...")
    p_results = neo4j_client.execute_read("""
    CALL db.index.vector.queryNodes('product_text_embeddings', 3, $vec)
    YIELD node, score
    RETURN node.id AS id, node.title AS title, score
    """, {"vec": test_vec})

    for rank, res in enumerate(p_results, 1):
        print(f"  {rank}. [{res['score']:.4f}] {res['id']}: {res['title']}")

    # 4. Test Review vector search query
    print(f"\nTesting Review Vector Search for: 'clear sound and durable cable'...")
    r_vec = embedder.embed_text("clear sound and durable cable")
    r_results = neo4j_client.execute_read("""
    CALL db.index.vector.queryNodes('review_text_embeddings', 3, $vec)
    YIELD node, score
    MATCH (node)-[:REVIEWS]->(p:Product)
    RETURN node.id AS id, node.title AS title, node.text AS text, p.title AS product_title, score
    """, {"vec": r_vec})

    for rank, res in enumerate(r_results, 1):
        title = res.get("title") or "No Title"
        txt = (res.get("text") or "")[:70]
        print(f"  {rank}. [{res['score']:.4f}] Review on '{res['product_title']}': \"{title}\" - {txt}...")


def main():
    parser = argparse.ArgumentParser(description="ShopGraph Phase 3 Vector Embeddings Pipeline")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for writing to Neo4j")
    parser.add_argument("--skip-products", action="store_true", help="Skip embedding products")
    parser.add_argument("--skip-reviews", action="store_true", help="Skip embedding reviews")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing indexes and embeddings")
    args = parser.parse_args()

    print("==================================================================")
    print("ShopGraph Phase 3 Vector Pipeline")
    print("==================================================================")

    if not neo4j_client.connect():
        print(f"Error: Unable to connect to Neo4j at {settings.NEO4J_URI}")
        sys.exit(1)

    if args.verify_only:
        verify_vector_layer()
        return

    # Step 1: Products
    if not args.skip_products:
        embed_and_update_products(batch_size=args.batch_size)

    # Step 2: Reviews
    if not args.skip_reviews:
        embed_and_update_reviews(batch_size=args.batch_size * 2)

    # Step 3: Indexes
    create_and_verify_vector_indexes(dimension=settings.EMBEDDING_DIMENSION)

    # Step 4: Verification
    verify_vector_layer()

    print("\nPhase 3 Vector Layer Generation & Validation Complete!")


if __name__ == "__main__":
    main()
