"""
ShopGraph — Neo4j Ingestion Pipeline (Phase 2)
==============================================
Ingests preprocessed JSONL files into Neo4j using parameterized UNWIND batches.
Supports both local Neo4j and cloud-hosted Neo4j Aura.

Ingestion Order:
  1. Uniqueness Constraints & Schema Indexes
  2. Categories (:Category) + [:SUB_CATEGORY_OF] hierarchy
  3. Brands (:Brand)
  4. Products (:Product) + [:BRANDED_BY] + [:BELONGS_TO]
  5. Users (:User), Reviews (:Review), [:WROTE], [:REVIEWS], [:PURCHASED]

Preserved Semantics:
  - Product.id = parent_asin
  - Review.variant_asin = asin
  - Review.timestamp = review publication timestamp (NOT purchase date)
  - [:PURCHASED] edge created strictly when verified_purchase == true
  - Category.id = full canonical breadcrumb path
  - Missing prices remain NULL (never 0)
  - No all-pairs unconstrained derived or similarity edges materialized
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from neo4j import GraphDatabase, Driver
except ImportError:
    print("Error: 'neo4j' package is required. Install via: pip install neo4j")
    sys.exit(1)

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CYPHER_DIR = ROOT_DIR / "cypher"

PRODUCTS_FILE = PROCESSED_DIR / "products.jsonl"
REVIEWS_FILE = PROCESSED_DIR / "reviews.jsonl"
CATEGORIES_FILE = PROCESSED_DIR / "categories.jsonl"
BRANDS_FILE = PROCESSED_DIR / "brands.jsonl"

CONSTRAINTS_FILE = CYPHER_DIR / "constraints.cypher"
SCHEMA_FILE = CYPHER_DIR / "schema.cypher"


class Neo4jIngestor:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j", batch_size: int = 2000):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.batch_size = batch_size
        self.driver: Optional[Driver] = None

    def connect(self):
        print(f"Connecting to Neo4j at {self.uri} (Database: {self.database})...")
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            print("Successfully connected to Neo4j!")
        except Exception as e:
            print(f"Connection failed: {e}")
            print("\nPlease check your credentials in .env or provide them via CLI.")
            print("Variables expected: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE")
            sys.exit(1)

    def close(self):
        if self.driver:
            self.driver.close()

    def execute_cypher_file(self, file_path: Path):
        """Executes non-empty Cypher statements from a file."""
        if not file_path.exists():
            print(f"Warning: {file_path} not found.")
            return

        print(f"\nApplying Cypher definitions from {file_path.name}...")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split on semicolon, ignoring comments and whitespace
        statements = [stmt.strip() for stmt in content.split(";") if stmt.strip()]
        for stmt in statements:
            # Skip comment-only statements
            lines = [line.strip() for line in stmt.split("\n") if line.strip() and not line.strip().startswith("//")]
            if not lines:
                continue
            clean_stmt = "\n".join(lines)
            try:
                with self.driver.session(database=self.database) as session:
                    session.run(clean_stmt)
                    first_line = clean_stmt.split('\n')[0]
                    print(f"  Applied: {first_line[:70]}...")
            except Exception as e:
                print(f"  Notice during statement execution: {e}")

    def ingest_categories(self):
        """Ingests categories and creates [:SUB_CATEGORY_OF] hierarchy."""
        if not CATEGORIES_FILE.exists():
            print(f"Error: {CATEGORIES_FILE} not found. Run preprocess.py first.")
            return

        print(f"\n--- Ingesting Categories from {CATEGORIES_FILE.name} ---")
        query_nodes = """
        UNWIND $batch AS cat
        MERGE (c:Category {id: cat.id})
        SET c.name = cat.name,
            c.level = cat.level,
            c.path = cat.path
        """

        query_hierarchy = """
        UNWIND $batch AS cat
        MATCH (c:Category {id: cat.id})
        MATCH (p:Category {id: cat.parent_id})
        MERGE (c)-[:SUB_CATEGORY_OF]->(p)
        """

        categories = []
        with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    categories.append(json.loads(line_str))

        # 1. Create Category nodes
        with self.driver.session(database=self.database) as session:
            session.run(query_nodes, batch=categories)
        print(f"  Merged {len(categories):,} Category nodes.")

        # 2. Create hierarchy edges for items with parent_id
        with_parent = [c for c in categories if c.get("parent_id")]
        with self.driver.session(database=self.database) as session:
            session.run(query_hierarchy, batch=with_parent)
        print(f"  Merged {len(with_parent):,} [:SUB_CATEGORY_OF] hierarchy relationships.")

    def ingest_brands(self):
        """Ingests brands."""
        if not BRANDS_FILE.exists():
            print(f"Error: {BRANDS_FILE} not found. Run preprocess.py first.")
            return

        print(f"\n--- Ingesting Brands from {BRANDS_FILE.name} ---")
        query = """
        UNWIND $batch AS b
        MERGE (brand:Brand {id: b.id})
        SET brand.name = b.name,
            brand.raw_store = b.raw_store
        """

        brands = []
        with open(BRANDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    brands.append(json.loads(line_str))

        with self.driver.session(database=self.database) as session:
            session.run(query, batch=brands)
        print(f"  Merged {len(brands):,} Brand nodes.")

    def ingest_products(self):
        """Ingests products along with [:BRANDED_BY] and [:BELONGS_TO] edges in batches."""
        if not PRODUCTS_FILE.exists():
            print(f"Error: {PRODUCTS_FILE} not found. Run preprocess.py first.")
            return

        print(f"\n--- Ingesting Products from {PRODUCTS_FILE.name} ---")
        query = """
        UNWIND $batch AS p
        MERGE (prod:Product {id: p.id})
        SET prod.title = p.title,
            prod.average_rating = p.average_rating,
            prod.rating_count = p.rating_count,
            prod.price = p.price,
            prod.price_currency = p.price_currency,
            prod.raw_price = p.raw_price,
            prod.main_category = p.main_category,
            prod.features = p.features,
            prod.description = p.description,
            prod.image_url = p.image_url,
            prod.brand_id = p.brand_id,
            prod.category_id = p.category_id

        WITH prod, p
        FOREACH (_ IN CASE WHEN p.brand_id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (b:Brand {id: p.brand_id})
            MERGE (prod)-[:BRANDED_BY]->(b)
        )
        FOREACH (_ IN CASE WHEN p.category_id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (c:Category {id: p.category_id})
            MERGE (prod)-[:BELONGS_TO]->(c)
        )
        """

        batch = []
        total_products = 0
        start_time = time.time()

        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                batch.append(json.loads(line_str))

                if len(batch) >= self.batch_size:
                    with self.driver.session(database=self.database) as session:
                        session.run(query, batch=batch)
                    total_products += len(batch)
                    elapsed = time.time() - start_time
                    rate = total_products / elapsed if elapsed > 0 else 0
                    print(f"  Ingested {total_products:,} products ({rate:.0f} rec/s)...")
                    batch = []

            if batch:
                with self.driver.session(database=self.database) as session:
                    session.run(query, batch=batch)
                total_products += len(batch)

        print(f"  Finished: Merged {total_products:,} Products and relationships.")

    def ingest_reviews_and_users(self):
        """
        Ingests Users, Reviews, [:WROTE], [:REVIEWS], and [:PURCHASED] edges in batches.
        [:PURCHASED] is created strictly for verified purchases.
        """
        if not REVIEWS_FILE.exists():
            print(f"Error: {REVIEWS_FILE} not found. Run preprocess.py first.")
            return

        print(f"\n--- Ingesting Reviews and Users from {REVIEWS_FILE.name} ---")
        query = """
        UNWIND $batch AS r
        MERGE (u:User {id: r.user_id})
        MERGE (prod:Product {id: r.product_id})
        MERGE (rev:Review {id: r.id})
        SET rev.rating = r.rating,
            rev.title = r.title,
            rev.text = r.text,
            rev.timestamp = r.timestamp,
            rev.variant_asin = r.variant_asin,
            rev.verified_purchase = r.verified_purchase,
            rev.helpful_votes = r.helpful_votes

        MERGE (u)-[w:WROTE]->(rev)
        SET w.timestamp = r.timestamp

        MERGE (rev)-[rel:REVIEWS]->(prod)
        SET rel.variant_asin = r.variant_asin

        WITH u, prod, r
        FOREACH (_ IN CASE WHEN r.verified_purchase = true THEN [1] ELSE [] END |
            MERGE (u)-[pur:PURCHASED]->(prod)
            SET pur.verified = true,
                pur.review_timestamp = r.timestamp
        )
        """

        batch = []
        total_reviews = 0
        start_time = time.time()

        with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                batch.append(json.loads(line_str))

                if len(batch) >= self.batch_size:
                    with self.driver.session(database=self.database) as session:
                        session.run(query, batch=batch)
                    total_reviews += len(batch)
                    elapsed = time.time() - start_time
                    rate = total_reviews / elapsed if elapsed > 0 else 0
                    print(f"  Ingested {total_reviews:,} reviews ({rate:.0f} rec/s)...")
                    batch = []

            if batch:
                with self.driver.session(database=self.database) as session:
                    session.run(query, batch=batch)
                total_reviews += len(batch)

        print(f"  Finished: Merged {total_reviews:,} Reviews and interaction edges.")

    def run_full_ingestion(self):
        start_time = time.time()
        self.connect()

        # Step 1: Constraints & Schema
        self.execute_cypher_file(CONSTRAINTS_FILE)
        self.execute_cypher_file(SCHEMA_FILE)

        # Step 2: Categories
        self.ingest_categories()

        # Step 3: Brands
        self.ingest_brands()

        # Step 4: Products
        self.ingest_products()

        # Step 5: Reviews and Users
        self.ingest_reviews_and_users()

        total_time = round(time.time() - start_time, 2)
        print(f"\n=================================================================")
        print(f"--- Neo4j Ingestion Complete! (Elapsed: {total_time}s) ---")
        print("=================================================================\n")
        self.close()


def main():
    parser = argparse.ArgumentParser(description="ShopGraph Neo4j Ingestion Script")
    parser.add_argument("--uri", type=str, default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                        help="Neo4j connection URI (default: from NEO4J_URI or bolt://localhost:7687)")
    parser.add_argument("--user", type=str, default=os.getenv("NEO4J_USERNAME", "neo4j"),
                        help="Neo4j username (default: from NEO4J_USERNAME or neo4j)")
    parser.add_argument("--password", type=str, default=os.getenv("NEO4J_PASSWORD", "password"),
                        help="Neo4j password (default: from NEO4J_PASSWORD)")
    parser.add_argument("--database", type=str, default=os.getenv("NEO4J_DATABASE", "neo4j"),
                        help="Neo4j database name (default: neo4j)")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("INGEST_BATCH_SIZE", "2000")),
                        help="Batch size for parameterized UNWIND inserts (default: 2000)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Test connection and file readiness without writing to the database")

    args = parser.parse_args()

    ingestor = Neo4jIngestor(
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database,
        batch_size=args.batch_size,
    )

    if args.dry_run:
        print("Running DRY RUN: verifying files and connection...")
        for p in [PRODUCTS_FILE, REVIEWS_FILE, CATEGORIES_FILE, BRANDS_FILE]:
            if p.exists():
                print(f"  [OK] Found {p.name}")
            else:
                print(f"  [MISSING] {p.name}")
        ingestor.connect()
        ingestor.close()
        print("Dry run complete.")
        return

    ingestor.run_full_ingestion()


if __name__ == "__main__":
    main()
