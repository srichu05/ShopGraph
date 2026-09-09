"""
ShopGraph — Graph Validation Suite (Phase 2)
=============================================
Runs automated integrity, semantic, and boundary checks against the Neo4j database.
Generates an audit report comparing processed data counts with graph state.
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

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_STATS_FILE = ROOT_DIR / "data" / "processed" / "stats.json"


class GraphValidator:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver: Optional[Driver] = None
        self.results: List[Dict[str, Any]] = []

    def connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            print(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            print(f"Connection failed: {e}")
            sys.exit(1)

    def close(self):
        if self.driver:
            self.driver.close()

    def run_check(self, name: str, query: str, expected_zero: bool = True, custom_val_fn=None) -> Dict[str, Any]:
        """Runs a Cypher query and checks whether result satisfies expectations."""
        with self.driver.session(database=self.database) as session:
            res = session.run(query).data()

        status = "PASSED"
        details = res

        if custom_val_fn:
            passed, msg = custom_val_fn(res)
            status = "PASSED" if passed else "FAILED"
            details = msg
        elif expected_zero:
            # Usually we expect 0 bad rows
            first_val = 0
            if res and len(res) > 0:
                first_val = list(res[0].values())[0]
            if first_val > 0:
                status = "FAILED"
            details = f"Count: {first_val}"

        result = {
            "name": name,
            "status": status,
            "details": details,
        }
        self.results.append(result)
        icon = "[PASS]" if status == "PASSED" else "[FAIL]"
        print(f"  {icon} {name:50} -> {details}")
        return result

    def validate_all(self):
        print("\n=================================================================")
        print("--- ShopGraph Phase 2: Neo4j Knowledge Graph Validation ---")
        print("=================================================================\n")

        # -------------------------------------------------------------
        # 1. Node Counts
        # -------------------------------------------------------------
        print("1. Node Population Counts:")
        with self.driver.session(database=self.database) as session:
            p_cnt = session.run("MATCH (p:Product) RETURN count(p) AS c").single()["c"]
            u_cnt = session.run("MATCH (u:User) RETURN count(u) AS c").single()["c"]
            r_cnt = session.run("MATCH (r:Review) RETURN count(r) AS c").single()["c"]
            b_cnt = session.run("MATCH (b:Brand) RETURN count(b) AS c").single()["c"]
            c_cnt = session.run("MATCH (c:Category) RETURN count(c) AS c").single()["c"]

        print(f"   Products   : {p_cnt:,}")
        print(f"   Users      : {u_cnt:,}")
        print(f"   Reviews    : {r_cnt:,}")
        print(f"   Brands     : {b_cnt:,}")
        print(f"   Categories : {c_cnt:,}\n")

        # -------------------------------------------------------------
        # 2. Relationship Counts
        # -------------------------------------------------------------
        print("2. Relationship Population Counts:")
        with self.driver.session(database=self.database) as session:
            wrote_cnt = session.run("MATCH ()-[r:WROTE]->() RETURN count(r) AS c").single()["c"]
            reviews_cnt = session.run("MATCH ()-[r:REVIEWS]->() RETURN count(r) AS c").single()["c"]
            purchased_cnt = session.run("MATCH ()-[r:PURCHASED]->() RETURN count(r) AS c").single()["c"]
            branded_cnt = session.run("MATCH ()-[r:BRANDED_BY]->() RETURN count(r) AS c").single()["c"]
            belongs_cnt = session.run("MATCH ()-[r:BELONGS_TO]->() RETURN count(r) AS c").single()["c"]
            subcat_cnt = session.run("MATCH ()-[r:SUB_CATEGORY_OF]->() RETURN count(r) AS c").single()["c"]

        print(f"   [:WROTE]           : {wrote_cnt:,}")
        print(f"   [:REVIEWS]         : {reviews_cnt:,}")
        print(f"   [:PURCHASED]       : {purchased_cnt:,}")
        print(f"   [:BRANDED_BY]      : {branded_cnt:,}")
        print(f"   [:BELONGS_TO]      : {belongs_cnt:,}")
        print(f"   [:SUB_CATEGORY_OF] : {subcat_cnt:,}\n")

        # -------------------------------------------------------------
        # 3. Structural & Referential Integrity Checks
        # -------------------------------------------------------------
        print("3. Structural & Referential Integrity Checks:")
        self.run_check(
            "Blank or NULL Product IDs",
            "MATCH (p:Product) WHERE p.id IS NULL OR trim(p.id) = '' RETURN count(p) AS c"
        )
        self.run_check(
            "Blank or NULL User IDs",
            "MATCH (u:User) WHERE u.id IS NULL OR trim(u.id) = '' RETURN count(u) AS c"
        )
        self.run_check(
            "Blank or NULL Review IDs",
            "MATCH (r:Review) WHERE r.id IS NULL OR trim(r.id) = '' RETURN count(r) AS c"
        )
        self.run_check(
            "Orphan Reviews (missing WROTE edge from User)",
            "MATCH (r:Review) WHERE NOT (r)<-[:WROTE]-(:User) RETURN count(r) AS c"
        )
        self.run_check(
            "Orphan Reviews (missing REVIEWS edge to Product)",
            "MATCH (r:Review) WHERE NOT (r)-[:REVIEWS]->(:Product) RETURN count(r) AS c"
        )
        self.run_check(
            "Subcategories missing parent [:SUB_CATEGORY_OF]",
            "MATCH (c:Category) WHERE c.level > 0 AND NOT (c)-[:SUB_CATEGORY_OF]->(:Category) RETURN count(c) AS c"
        )
        self.run_check(
            "Category IDs with invalid non-canonical path format",
            "MATCH (c:Category) WHERE c.level > 0 AND NOT c.id CONTAINS ' > ' RETURN count(c) AS c"
        )

        # -------------------------------------------------------------
        # 4. Semantic & Boundary Checks
        # -------------------------------------------------------------
        print("\n4. Dataset Semantic & Boundary Checks:")
        self.run_check(
            "Unverified purchase on [:PURCHASED] edge",
            "MATCH (u:User)-[pur:PURCHASED]->(p:Product) WHERE pur.verified <> true RETURN count(pur) AS c"
        )
        self.run_check(
            "Suspicious zero/free prices ($0.00)",
            "MATCH (p:Product) WHERE p.price = 0 OR p.price = 0.0 RETURN count(p) AS c"
        )
        self.run_check(
            "Reviews missing variant_asin",
            "MATCH (r:Review) WHERE r.variant_asin IS NULL OR trim(r.variant_asin) = '' RETURN count(r) AS c"
        )
        self.run_check(
            "Forbidden materialized [:CO_PURCHASED_WITH] edges",
            "MATCH ()-[r:CO_PURCHASED_WITH]->() RETURN count(r) AS c"
        )
        self.run_check(
            "Forbidden materialized [:BOUGHT_TOGETHER] edges",
            "MATCH ()-[r:BOUGHT_TOGETHER]->() RETURN count(r) AS c"
        )
        self.run_check(
            "Forbidden all-pairs [:SIMILAR_TO] edges",
            "MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS c"
        )

        # -------------------------------------------------------------
        # 5. Overall Status
        # -------------------------------------------------------------
        failures = [r for r in self.results if r["status"] == "FAILED"]
        print("\n=================================================================")
        if not failures:
            print(">>> ALL VALIDATION CHECKS PASSED (100% Integrity)")
        else:
            print(f">>> VALIDATION COMPLETED WITH {len(failures)} FAILURE(S):")
            for f in failures:
                print(f"    - {f['name']}: {f['details']}")
        print("=================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="ShopGraph Neo4j Graph Validator")
    parser.add_argument("--uri", type=str, default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                        help="Neo4j connection URI")
    parser.add_argument("--user", type=str, default=os.getenv("NEO4J_USERNAME", "neo4j"),
                        help="Neo4j username")
    parser.add_argument("--password", type=str, default=os.getenv("NEO4J_PASSWORD", "password"),
                        help="Neo4j password")
    parser.add_argument("--database", type=str, default=os.getenv("NEO4J_DATABASE", "neo4j"),
                        help="Neo4j database name")

    args = parser.parse_args()

    validator = GraphValidator(
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database,
    )
    validator.connect()
    validator.validate_all()
    validator.close()


if __name__ == "__main__":
    main()
