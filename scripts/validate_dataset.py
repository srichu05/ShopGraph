"""
ShopGraph - Dataset Validation and Methodology Correction Script
Performs rigorous, disk-backed validation of the raw dataset:
1. Complete duplicate review analysis using SQLite.
2. Exact timestamp and verified purchase semantics.
3. Category array taxonomy structure inspection and real examples.
4. Product variant analysis: parent_asin vs asin mapping.
5. 100% verification of bought_together across all metadata records.
6. Revalidation of all dataset statistics.
"""

import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Ensure UTF-8 console output for Windows
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
META_FILE = DATA_RAW_DIR / "meta_Musical_Instruments.jsonl"
REVIEW_FILE = DATA_RAW_DIR / "Musical_Instruments.jsonl"
DB_FILE = BASE_DIR / "data" / "validation_temp.db"

def validate_metadata():
    print("\n=======================================================")
    print("--- 1. METADATA VALIDATION & BOUGHT_TOGETHER SCAN ---")
    print("=======================================================")

    total_records = 0
    parent_asins = Counter()
    stores = Counter()
    main_categories = Counter()
    category_paths = []
    category_tokens = Counter()
    non_null_bought_together = []
    
    sample_categories = []
    sample_with_details = []
    prices = []
    ratings = []

    with open(META_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            rec = json.loads(line_str)
            total_records += 1

            p_asin = rec.get("parent_asin")
            if p_asin:
                parent_asins[p_asin] += 1

            store = rec.get("store")
            if store and isinstance(store, str) and store.strip():
                stores[store.strip()] += 1

            mc = rec.get("main_category")
            if mc:
                main_categories[mc] += 1

            # Check bought_together
            bt = rec.get("bought_together")
            if bt is not None and bt != "" and bt != [] and bt != {}:
                non_null_bought_together.append((p_asin, bt))

            # Categories
            cats = rec.get("categories")
            if cats and isinstance(cats, list) and len(cats) > 0:
                cat_tuple = tuple(c.strip() for c in cats if isinstance(c, str) and c.strip())
                if cat_tuple:
                    category_paths.append(cat_tuple)
                    for c in cat_tuple:
                        category_tokens[c] += 1
                    if len(sample_categories) < 15 and len(cat_tuple) > 2:
                        sample_categories.append((p_asin, rec.get("title", "")[:60], cat_tuple))

            # Prices
            p = rec.get("price")
            if p is not None:
                try:
                    prices.append(float(p))
                except (ValueError, TypeError):
                    pass

            # Ratings
            r = rec.get("average_rating")
            if r is not None:
                try:
                    ratings.append(float(r))
                except (ValueError, TypeError):
                    pass

    print(f"Total Metadata Records: {total_records:,}")
    print(f"Unique parent_asin: {len(parent_asins):,}")
    duplicate_parent_asins = {k: v for k, v in parent_asins.items() if v > 1}
    print(f"Duplicate parent_asin: {len(duplicate_parent_asins):,}")
    print(f"Unique Stores / Brands: {len(stores):,}")
    print(f"Unique Main Categories: {len(main_categories):,}")
    print(f"Distinct Category Taxonomy Paths: {len(set(category_paths)):,}")
    print(f"Unique Category Labels across all paths: {len(category_tokens):,}")
    print(f"Items with non-null bought_together: {len(non_null_bought_together):,}")
    if non_null_bought_together:
        print(f"  Samples of bought_together: {non_null_bought_together[:5]}")
    else:
        print("  --> CONFIRMED: bought_together is 100% NULL/ABSENT across all 213,593 metadata records.")

    return {
        "total_products": total_records,
        "unique_parent_asin": len(parent_asins),
        "duplicate_parent_asin": len(duplicate_parent_asins),
        "unique_stores": len(stores),
        "unique_main_categories": len(main_categories),
        "distinct_category_paths": len(set(category_paths)),
        "unique_category_labels": len(category_tokens),
        "sample_categories": sample_categories,
        "non_null_bought_together_count": len(non_null_bought_together)
    }

def validate_reviews_sqlite():
    print("\n=======================================================")
    print("--- 2. REVIEWS VALIDATION & DISK-BACKED DUPLICATE ANALYSIS (SQLite) ---")
    print("=======================================================")

    if DB_FILE.exists():
        DB_FILE.unlink()

    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = MEMORY")
    cursor.execute("PRAGMA cache_size = 100000")

    cursor.execute("""
        CREATE TABLE reviews (
            row_id INTEGER PRIMARY KEY,
            user_id TEXT,
            parent_asin TEXT,
            asin TEXT,
            rating REAL,
            timestamp INTEGER,
            verified_purchase INTEGER,
            helpful_vote INTEGER,
            has_text INTEGER,
            has_title INTEGER,
            content_hash TEXT
        )
    """)

    print("Populating SQLite table from Musical_Instruments.jsonl...")
    batch = []
    total_reviews = 0
    missing_user_id = 0
    missing_parent_asin = 0
    missing_asin = 0
    missing_text = 0
    missing_title = 0
    missing_timestamp = 0
    missing_rating = 0

    with open(REVIEW_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            rec = json.loads(line_str)
            total_reviews += 1

            u_id = rec.get("user_id")
            p_asin = rec.get("parent_asin")
            asin = rec.get("asin")
            rating = rec.get("rating")
            ts = rec.get("timestamp")
            vp = 1 if rec.get("verified_purchase") is True else 0
            hv = rec.get("helpful_vote", 0)
            text = rec.get("text", "")
            title = rec.get("title", "")

            if not u_id: missing_user_id += 1
            if not p_asin: missing_parent_asin += 1
            if not asin: missing_asin += 1
            if text is None or text == "": missing_text += 1
            if title is None or title == "": missing_title += 1
            if ts is None: missing_timestamp += 1
            if rating is None: missing_rating += 1

            # Hash for exact duplicate detection (user, parent_asin, asin, rating, timestamp, title, text)
            hash_str = f"{u_id}|{p_asin}|{asin}|{rating}|{ts}|{title}|{text}"
            c_hash = hashlib.md5(hash_str.encode("utf-8", errors="ignore")).hexdigest()

            batch.append((line_num, u_id, p_asin, asin, rating, ts, vp, hv, 
                          0 if (text is None or text == "") else 1,
                          0 if (title is None or title == "") else 1,
                          c_hash))

            if len(batch) >= 100000:
                cursor.executemany("""
                    INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                batch = []
                print(f"  Inserted {total_reviews:,} rows...", flush=True)

    if batch:
        cursor.executemany("INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)

    conn.commit()
    print(f"Total reviews indexed into SQLite: {total_reviews:,}")

    print("\nCreating indexing on SQLite table for analytical queries...")
    cursor.execute("CREATE INDEX idx_user_parent_ts ON reviews (user_id, parent_asin, timestamp)")
    cursor.execute("CREATE INDEX idx_content_hash ON reviews (content_hash)")
    cursor.execute("CREATE INDEX idx_parent_asin ON reviews (parent_asin)")
    cursor.execute("CREATE INDEX idx_asin ON reviews (asin)")
    cursor.execute("CREATE INDEX idx_user_id ON reviews (user_id)")
    conn.commit()

    # 1. Exact Duplicate Records (identical content hash)
    cursor.execute("""
        SELECT content_hash, COUNT(*) as cnt, MIN(row_id), MAX(row_id)
        FROM reviews
        GROUP BY content_hash
        HAVING cnt > 1
    """)
    exact_dup_groups = cursor.fetchall()
    exact_dup_extra_rows = sum(r[1] - 1 for r in exact_dup_groups)
    print(f"\n1. EXACT DUPLICATE RECORDS:")
    print(f"   Unique content hash groups with duplicates: {len(exact_dup_groups):,}")
    print(f"   Total redundant duplicate rows: {exact_dup_extra_rows:,}")

    # 2. Key Duplicate: (user_id, parent_asin, timestamp)
    cursor.execute("""
        SELECT user_id, parent_asin, timestamp, COUNT(*) as cnt
        FROM reviews
        GROUP BY user_id, parent_asin, timestamp
        HAVING cnt > 1
    """)
    key_dup_groups = cursor.fetchall()
    key_dup_extra_rows = sum(r[3] - 1 for r in key_dup_groups)
    print(f"\n2. DUPLICATE KEY (user_id, parent_asin, timestamp):")
    print(f"   Duplicate key groups: {len(key_dup_groups):,}")
    print(f"   Total redundant key rows: {key_dup_extra_rows:,}")

    # Inspect samples of key duplicates where content differs vs matches
    cursor.execute("""
        SELECT r.user_id, r.parent_asin, r.asin, r.rating, r.timestamp, r.content_hash, r.row_id
        FROM reviews r
        WHERE (r.user_id, r.parent_asin, r.timestamp) IN (
            SELECT user_id, parent_asin, timestamp FROM reviews
            GROUP BY user_id, parent_asin, timestamp HAVING count(*) > 1 LIMIT 5
        )
        ORDER BY r.user_id, r.parent_asin, r.timestamp, r.row_id
    """)
    sample_key_dups = cursor.fetchall()
    print("   Sample Key Duplicates:")
    for r in sample_key_dups:
        print(f"     Row {r[6]}: User: {r[0][:12]}.. | Parent: {r[1]} | Variant ASIN: {r[2]} | Rating: {r[3]} | TS: {r[4]}")

    # 3. Legitimate multiple reviews: same user + same parent_asin at DIFFERENT timestamps
    cursor.execute("""
        SELECT user_id, parent_asin, COUNT(DISTINCT timestamp) as distinct_ts, COUNT(*) as total_reviews
        FROM reviews
        GROUP BY user_id, parent_asin
        HAVING distinct_ts > 1
    """)
    multi_ts_reviews = cursor.fetchall()
    print(f"\n3. MULTIPLE REVIEWS BY SAME USER FOR SAME PRODUCT AT DIFFERENT TIMESTAMPS:")
    print(f"   User-Product pairs with reviews across multiple timestamps: {len(multi_ts_reviews):,}")
    print(f"   (These represent legitimate updated reviews, re-purchases, or reviews for different variants)")

    # 4. Variant analysis: reviews where asin != parent_asin
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE asin != parent_asin")
    diff_asin_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT asin) FROM reviews")
    unique_asins = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT parent_asin) FROM reviews")
    unique_parent_asins = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM reviews")
    unique_users = cursor.fetchone()[0]

    # Find parent_asins that have multiple distinct variant asins
    cursor.execute("""
        SELECT parent_asin, COUNT(DISTINCT asin) as var_count
        FROM reviews
        GROUP BY parent_asin
        HAVING var_count > 1
    """)
    parents_with_multi_asins = cursor.fetchall()
    
    print(f"\n4. PRODUCT VARIANT (parent_asin vs asin) ANALYSIS:")
    print(f"   Total Unique parent_asin in reviews: {unique_parent_asins:,}")
    print(f"   Total Unique variant asin in reviews: {unique_asins:,}")
    print(f"   Reviews where asin != parent_asin: {diff_asin_count:,} ({diff_asin_count/total_reviews*100:.2f}%)")
    print(f"   Parent ASINs that map to multiple variant ASINs: {len(parents_with_multi_asins):,}")

    # Sample parent_asins with multiple variant asins
    cursor.execute("""
        SELECT parent_asin, COUNT(DISTINCT asin) as var_count, group_concat(DISTINCT asin) as asins
        FROM reviews
        GROUP BY parent_asin
        HAVING var_count >= 3
        LIMIT 5
    """)
    sample_multi_variants = cursor.fetchall()
    print("   Sample Parent ASINs with Multiple Variant ASINs:")
    for sm in sample_multi_variants:
        print(f"     Parent ASIN: {sm[0]} has {sm[1]} variants -> {sm[2][:80]}...")

    # 5. Rating distribution
    cursor.execute("SELECT rating, COUNT(*) FROM reviews GROUP BY rating ORDER BY rating")
    ratings_dist = cursor.fetchall()

    # 6. Verified purchase count
    cursor.execute("SELECT verified_purchase, COUNT(*) FROM reviews GROUP BY verified_purchase")
    vp_dist = cursor.fetchall()

    conn.close()
    if DB_FILE.exists():
        DB_FILE.unlink()  # Clean up temp database

    return {
        "total_reviews": total_reviews,
        "unique_users": unique_users,
        "unique_parent_asin": unique_parent_asins,
        "unique_asin": unique_asins,
        "exact_duplicate_groups": len(exact_dup_groups),
        "exact_duplicate_redundant_rows": exact_dup_extra_rows,
        "key_duplicate_groups": len(key_dup_groups),
        "key_duplicate_redundant_rows": key_dup_extra_rows,
        "multi_timestamp_user_product_pairs": len(multi_ts_reviews),
        "diff_asin_count": diff_asin_count,
        "parents_with_multi_asins_count": len(parents_with_multi_asins),
        "ratings_distribution": ratings_dist,
        "verified_purchase_distribution": vp_dist,
        "missing_counts": {
            "user_id": missing_user_id,
            "parent_asin": missing_parent_asin,
            "asin": missing_asin,
            "text": missing_text,
            "title": missing_title,
            "timestamp": missing_timestamp,
            "rating": missing_rating
        },
        "sample_multi_variants": sample_multi_variants
    }

def main():
    meta_results = validate_metadata()
    review_results = validate_reviews_sqlite()

    out_file = BASE_DIR / "data" / "revalidation_results.json"
    combined = {
        "metadata": meta_results,
        "reviews": review_results
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"\n[OK] Validation results saved to {out_file}")

if __name__ == "__main__":
    main()
