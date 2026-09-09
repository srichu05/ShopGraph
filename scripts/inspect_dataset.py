"""
ShopGraph - Dataset Inspection and Quality Assessment
Analyzes raw JSONL dataset files: calculates schemas, statistics, missingness, duplicates, and quality issues.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

# Ensure UTF-8 console output for Windows
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

META_FILE = DATA_RAW_DIR / "meta_Musical_Instruments.jsonl"
REVIEW_FILE = DATA_RAW_DIR / "Musical_Instruments.jsonl"

def inspect_metadata(filepath: Path, sample_limit: int = 5):
    print(f"\n=======================================================")
    print(f"--- 1. INSPECTING METADATA: {filepath.name} ---")
    print(f"=======================================================")
    
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return {}

    file_size_bytes = filepath.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    print(f"Raw File Size: {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")

    total_records = 0
    malformed_records = 0
    seen_parent_asins = set()
    duplicate_products = 0

    field_presence = Counter()
    missing_counts = Counter()
    sample_records = []

    brands = set()
    categories_set = set()
    price_values = []
    ratings = []

    all_keys = set()
    details_keys_counter = Counter()

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line_idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                rec = json.loads(line_str)
            except Exception as e:
                malformed_records += 1
                continue

            total_records += 1
            if len(sample_records) < sample_limit:
                sample_records.append(rec)

            # Product identifier
            p_asin = rec.get("parent_asin")
            if not p_asin:
                missing_counts["parent_asin"] += 1
            else:
                if p_asin in seen_parent_asins:
                    duplicate_products += 1
                else:
                    seen_parent_asins.add(p_asin)

            # Field presence & missingness
            for k in ["main_category", "title", "average_rating", "rating_number", 
                      "features", "description", "price", "images", "videos", 
                      "store", "categories", "details", "parent_asin", "bought_together"]:
                all_keys.add(k)
                val = rec.get(k)
                if val is not None and val != "" and val != [] and val != {}:
                    field_presence[k] += 1
                else:
                    missing_counts[k] += 1

            # Brands / stores
            store = rec.get("store")
            if store and isinstance(store, str) and store.strip():
                brands.add(store.strip())

            # Categories
            cats = rec.get("categories")
            if cats and isinstance(cats, list):
                for c in cats:
                    if c and isinstance(c, str):
                        categories_set.add(c.strip())

            # Details
            details = rec.get("details")
            if isinstance(details, dict):
                for dk in details.keys():
                    details_keys_counter[dk] += 1

            # Prices
            price = rec.get("price")
            if price is not None:
                try:
                    price_float = float(price)
                    price_values.append(price_float)
                except (ValueError, TypeError):
                    pass

            # Ratings
            avg_r = rec.get("average_rating")
            if avg_r is not None:
                try:
                    ratings.append(float(avg_r))
                except (ValueError, TypeError):
                    pass

            if total_records % 50000 == 0:
                print(f"  Processed {total_records:,} metadata records...", flush=True)

    print(f"\nTotal Metadata Records Processed: {total_records:,}")
    print(f"Unique Products (parent_asin): {len(seen_parent_asins):,}")
    print(f"Duplicate Products: {duplicate_products:,}")
    print(f"Malformed Records: {malformed_records:,}")
    print(f"Unique Brands (from 'store'): {len(brands):,}")
    print(f"Unique Category Hierarchy Labels: {len(categories_set):,}")
    
    if ratings:
        print(f"Average Rating Mean: {sum(ratings)/len(ratings):.2f} (min: {min(ratings)}, max: {max(ratings)})")
    if price_values:
        print(f"Numeric Prices: {len(price_values):,} values (min: ${min(price_values):.2f}, max: ${max(price_values):.2f}, avg: ${sum(price_values)/len(price_values):.2f})")

    print("\n--- Field Presence & Missingness in Metadata ---")
    for k in sorted(all_keys):
        present = field_presence[k]
        missing = missing_counts[k]
        pct_missing = (missing / total_records * 100) if total_records else 0
        print(f"  {k:20}: Present: {present:8,d} ({100-pct_missing:5.1f}%) | Missing: {missing:8,d} ({pct_missing:5.1f}%)")

    print(f"\nTop 10 Technical Specification Keys (from 'details'):")
    for dk, count in details_keys_counter.most_common(10):
        print(f"  {dk:35}: {count:8,d} ({count/total_records*100:5.1f}%)")

    return {
        "total_products": total_records,
        "unique_products": len(seen_parent_asins),
        "duplicates": duplicate_products,
        "brands_count": len(brands),
        "categories_count": len(categories_set),
        "missing_counts": dict(missing_counts),
        "field_presence": dict(field_presence),
        "sample_records": sample_records[:2]
    }

def inspect_reviews(filepath: Path, sample_limit: int = 5):
    print(f"\n=======================================================")
    print(f"--- 2. INSPECTING REVIEWS: {filepath.name} ---")
    print(f"=======================================================")

    if not filepath.exists():
        print(f"File not found: {filepath}")
        return {}

    file_size_bytes = filepath.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    print(f"Raw File Size: {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")

    total_reviews = 0
    malformed_records = 0
    unique_users = set()
    unique_parent_asins = set()
    unique_asins = set()
    
    seen_review_keys = set()
    duplicate_reviews = 0

    field_presence = Counter()
    missing_counts = Counter()
    sample_reviews = []

    ratings_dist = Counter()
    verified_count = 0
    helpful_vote_sum = 0
    helpful_vote_max = 0

    review_keys = ["rating", "title", "text", "images", "asin", "parent_asin", 
                   "user_id", "timestamp", "helpful_vote", "verified_purchase"]

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line_idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                rec = json.loads(line_str)
            except Exception as e:
                malformed_records += 1
                continue

            total_reviews += 1
            if len(sample_reviews) < sample_limit:
                sample_reviews.append(rec)

            u_id = rec.get("user_id")
            p_asin = rec.get("parent_asin")
            asin = rec.get("asin")
            ts = rec.get("timestamp")

            if u_id:
                unique_users.add(u_id)
            else:
                missing_counts["user_id"] += 1

            if p_asin:
                unique_parent_asins.add(p_asin)
            else:
                missing_counts["parent_asin"] += 1

            if asin:
                unique_asins.add(asin)
            else:
                missing_counts["asin"] += 1

            # Duplicate review check: same user + same parent_asin + same timestamp
            if u_id and p_asin and ts:
                rev_key = (u_id, p_asin, ts)
                if rev_key in seen_review_keys:
                    duplicate_reviews += 1
                else:
                    # Keep set size bounded if memory becomes an issue
                    if len(seen_review_keys) < 2000000:
                        seen_review_keys.add(rev_key)

            # Field presence
            for k in review_keys:
                val = rec.get(k)
                if val is not None and val != "" and val != []:
                    field_presence[k] += 1
                else:
                    missing_counts[k] += 1

            # Rating distribution
            r = rec.get("rating")
            if r is not None:
                ratings_dist[r] += 1

            # Verified
            if rec.get("verified_purchase") is True:
                verified_count += 1

            # Helpful
            hv = rec.get("helpful_vote", 0)
            if hv:
                helpful_vote_sum += hv
                if hv > helpful_vote_max:
                    helpful_vote_max = hv

            if total_reviews % 200000 == 0:
                print(f"  Processed {total_reviews:,} review records...", flush=True)

    print(f"\nTotal Reviews Processed: {total_reviews:,}")
    print(f"Unique Users: {len(unique_users):,}")
    print(f"Unique Parent ASINs (reviewed products): {len(unique_parent_asins):,}")
    print(f"Unique Variant ASINs: {len(unique_asins):,}")
    print(f"Duplicate Reviews: {duplicate_reviews:,}")
    print(f"Malformed Records: {malformed_records:,}")
    print(f"Verified Purchases: {verified_count:,} ({verified_count/total_reviews*100:5.1f}%)")
    print(f"Max Helpful Votes: {helpful_vote_max:,}")

    print("\n--- Rating Distribution ---")
    for star in sorted(ratings_dist.keys()):
        cnt = ratings_dist[star]
        print(f"  {star} Stars: {cnt:9,d} ({cnt/total_reviews*100:5.1f}%)")

    print("\n--- Field Presence & Missingness in Reviews ---")
    for k in review_keys:
        present = field_presence[k]
        missing = missing_counts[k]
        pct_missing = (missing / total_reviews * 100) if total_reviews else 0
        print(f"  {k:20}: Present: {present:9,d} ({100-pct_missing:5.1f}%) | Missing: {missing:9,d} ({pct_missing:5.1f}%)")

    return {
        "total_reviews": total_reviews,
        "unique_users": len(unique_users),
        "unique_parent_asins": len(unique_parent_asins),
        "duplicate_reviews": duplicate_reviews,
        "verified_purchases": verified_count,
        "ratings_distribution": dict(ratings_dist),
        "missing_counts": dict(missing_counts),
        "field_presence": dict(field_presence),
        "sample_reviews": sample_reviews[:2]
    }

def main():
    meta_stats = inspect_metadata(META_FILE)
    rev_stats = inspect_reviews(REVIEW_FILE)
    
    # Save results as JSON
    results = {
        "category": "Musical_Instruments",
        "metadata": meta_stats,
        "reviews": rev_stats
    }
    out_path = BASE_DIR / "data" / "inspection_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[OK] Inspection summary saved to {out_path}")

if __name__ == "__main__":
    main()
