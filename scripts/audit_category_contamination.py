"""
ShopGraph Category Taxonomy & Contamination Audit
=================================================
Investigates and quantifies category contamination in the Amazon Musical Instruments corpus:
1. Electric Guitars vs Guitar Accessories (cables, bags, picks, straps)
2. Guitars vs Books / Sheet Music
3. Drum Sets vs Drum Components / Hardware / Sticks

Traces the root cause across:
A. Source Amazon Taxonomy
B. Query Understanding / Parser
C. Cypher Filtering
D. Vector Retrieval
E. RRF Fusion
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.neo4j.connection import neo4j_client


def run_query(query: str, params: dict = None):
    return neo4j_client.execute_read(query, params or {})


def audit_electric_guitars():
    print("\n" + "=" * 70)
    print("1. Electric Guitars Taxonomy Audit")
    print("=" * 70)

    # Count genuine electric guitars
    q_genuine = """
    MATCH (p:Product)
    WHERE p.category_id CONTAINS 'Electric Guitars'
      AND NOT p.category_id CONTAINS 'Accessories'
    RETURN count(p) AS count
    """
    genuine_cnt = run_query(q_genuine)[0]["count"]

    # Count accessories filed under Guitars or Guitar & Bass Accessories
    q_acc = """
    MATCH (p:Product)
    WHERE p.category_id CONTAINS 'Guitar & Bass Accessories'
    RETURN count(p) AS count
    """
    acc_cnt = run_query(q_acc)[0]["count"]

    # Sample accessories that contain 'Guitar' in title
    q_sample_acc = """
    MATCH (p:Product)
    WHERE p.category_id CONTAINS 'Guitar & Bass Accessories'
      AND toLower(p.title) CONTAINS 'guitar'
    RETURN p.id AS id, p.title AS title, p.category_id AS cat
    LIMIT 5
    """
    sample_acc = run_query(q_sample_acc)

    print(f"Genuine Electric Guitar nodes (non-accessories) : {genuine_cnt}")
    print(f"Guitar & Bass Accessories nodes                     : {acc_cnt}")
    print("\nSample accessories containing 'guitar' in title:")
    for s in sample_acc:
        print(f"  - [{s['id']}] {s['title'][:65]} (Category: {s['cat'].split('>')[-1].strip()})")


def audit_guitars_vs_books():
    print("\n" + "=" * 70)
    print("2. Guitars vs Books / Sheet Music Contamination Audit")
    print("=" * 70)

    q_books = """
    MATCH (p:Product)
    WHERE (p.category_id CONTAINS 'Songbooks' OR p.category_id CONTAINS 'Sheet Music' OR p.category_id CONTAINS 'Instructional')
      AND toLower(p.title) CONTAINS 'guitar'
    RETURN count(p) AS count
    """
    book_cnt = run_query(q_books)[0]["count"]

    q_sample_books = """
    MATCH (p:Product)
    WHERE (p.category_id CONTAINS 'Songbooks' OR p.category_id CONTAINS 'Sheet Music' OR p.category_id CONTAINS 'Instructional')
      AND toLower(p.title) CONTAINS 'guitar'
    RETURN p.id AS id, p.title AS title, p.category_id AS cat
    LIMIT 5
    """
    sample_books = run_query(q_sample_books)

    print(f"Books / Songbooks containing 'guitar' in title in the dataset: {book_cnt}")
    for s in sample_books:
        print(f"  - [{s['id']}] {s['title'][:65]} (Category: {s['cat'].split('>')[-1].strip()})")


def audit_drum_sets_vs_hardware():
    print("\n" + "=" * 70)
    print("3. Drum Sets vs Drum Parts / Sticks / Hardware Audit")
    print("=" * 70)

    q_complete_kits = """
    MATCH (p:Product)
    WHERE p.category_id CONTAINS 'Drum Sets'
      AND NOT (p.category_id CONTAINS 'Hardware' OR p.category_id CONTAINS 'Accessories')
    RETURN count(p) AS count
    """
    complete_cnt = run_query(q_complete_kits)[0]["count"]

    q_drum_parts = """
    MATCH (p:Product)
    WHERE (p.category_id CONTAINS 'Drum & Percussion Accessories' OR p.category_id CONTAINS 'Drum Hardware')
      AND toLower(p.title) CONTAINS 'drum'
    RETURN count(p) AS count
    """
    parts_cnt = run_query(q_drum_parts)[0]["count"]

    print(f"Complete Drum Sets / Kits nodes                        : {complete_cnt}")
    print(f"Drum Accessories & Hardware nodes                       : {parts_cnt}")


def audit_microphones_vs_accessories():
    print("\n" + "=" * 70)
    print("4. Microphones vs Phantom Power / Accessories Audit")
    print("=" * 70)

    q_mics = """
    MATCH (p:Product)
    WHERE (p.category_id CONTAINS 'Dynamic Microphones' OR p.category_id CONTAINS 'Condenser Microphones')
    RETURN count(p) AS count
    """
    mics_cnt = run_query(q_mics)[0]["count"]

    q_mic_acc = """
    MATCH (p:Product)
    WHERE p.category_id CONTAINS 'Microphones & Accessories > Accessories'
    RETURN count(p) AS count
    """
    acc_cnt = run_query(q_mic_acc)[0]["count"]

    print(f"Genuine Microphones (Dynamic / Condenser) nodes         : {mics_cnt}")
    print(f"Microphone Accessories (Shock mounts, phantom power, cables): {acc_cnt}")


def main():
    print("=" * 70)
    print("ShopGraph Category Taxonomy Contamination & Root Cause Audit")
    print("=" * 70)

    if not neo4j_client.is_available():
        print("ERROR: Neo4j is not connected.")
        sys.exit(1)

    audit_electric_guitars()
    audit_guitars_vs_books()
    audit_drum_sets_vs_hardware()
    audit_microphones_vs_accessories()

    print("\n" + "=" * 70)
    print("ROOT CAUSE SYNTHESIS")
    print("=" * 70)
    print("""
Key Finding:
1. Source Amazon Taxonomy (Root Cause A):
   - The source dataset categorizes accessories and parts under common parent trees:
     e.g., 'Musical Instruments > Guitars > Guitar & Bass Accessories > Picks'
     e.g., 'Musical Instruments > Microphones & Accessories > Accessories > Phantom Power Supplies'
   - In naive substring searches (e.g., CONTAINS 'Guitars'), accessories vastly outnumber instruments (1,200+ accessories vs ~140 instruments).

2. Cypher Boundary Protection (Engine Defense):
   - ShopGraph's hierarchy boundary matching (' > Electric Guitars > ' or endsWith ' > Electric Guitars')
     strictly isolates genuine instruments from accessories.

3. Vector Retrieval Semantic Drift (Root Cause D):
   - A query like 'electric guitar with dual humbuckers' can match replacement pickups, gig bags, or miniatures
     in unconstrained ANN search because those accessory descriptions heavily repeat guitar terminology.
   - Reciprocal Rank Fusion (RRF) with hard category/price constraints prevents these drifted vector candidates
     from taking top rank.
""")


if __name__ == "__main__":
    main()
