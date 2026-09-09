"""
ShopGraph — Preprocessing Pipeline (Phase 2 Finalized)
======================================================
Transforms raw Amazon Reviews '23 (Musical Instruments) JSONL files into clean,
normalized, and graph-consistent JSONL files for Neo4j ingestion.

Supported Modes:
  --mode sample : Review-dense, balanced development slice (default: 10,000 products, ~50,000 reviews).
                  Guarantees 100% of sampled products have >= 1 review (targeting >= 3 reviews/product)
                  while preserving broad category and brand diversity.
  --mode full   : Complete 213,593 products and 3,017,439 reviews in a fully streaming pass.

Preserved Semantics:
  - Canonical Product ID: parent_asin
  - Variant ASIN: preserved as Review.variant_asin
  - Review Timestamp: preserved as publication epoch ms (NOT purchase date)
  - Verified Purchase: preserved as boolean (enables derived PURCHASED edge)
  - Category Identity: canonical full breadcrumb path (Category.id)
  - Missing Prices: remain NULL (never 0 or 'free')
  - Duplicate Review Handling: canonical content hash deduplication preserving multi-timestamp reviews
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_META_FILE = RAW_DIR / "meta_Musical_Instruments.jsonl"
RAW_REVIEW_FILE = RAW_DIR / "Musical_Instruments.jsonl"


def normalize_brand(store_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Deterministically normalizes store string into brand_id and clean brand_name.
    Strips 'Visit the ... Store' or 'Brand: ...' patterns.
    """
    if not store_str or not isinstance(store_str, str):
        return None, None

    cleaned = store_str.strip()
    if not cleaned:
        return None, None

    # Pattern: 'Visit the Fender Store' -> 'Fender'
    m_visit = re.match(r"^Visit the\s+(.*?)\s+Store$", cleaned, re.IGNORECASE)
    if m_visit:
        cleaned = m_visit.group(1).strip()

    # Pattern: 'Brand: Shure' -> 'Shure'
    m_brand = re.match(r"^Brand:\s*(.*)$", cleaned, re.IGNORECASE)
    if m_brand:
        cleaned = m_brand.group(1).strip()

    if not cleaned:
        return None, None

    # Deterministic brand slug/id: e.g. "brand_fender"
    slug = re.sub(r"[^\w]+", "_", cleaned.lower()).strip("_")
    if not slug:
        slug = hashlib.md5(cleaned.encode("utf-8")).hexdigest()[:12]
    brand_id = f"brand_{slug}"

    return brand_id, cleaned


def normalize_price(raw_price: Any) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Normalizes raw price to (numeric_value, currency, raw_string).
    Guarantees: Missing price remains NULL (None). Never converts missing to 0.0.
    """
    if raw_price is None or raw_price == "":
        return None, None, None

    raw_str = str(raw_price).strip()
    if not raw_str:
        return None, None, None

    # Strip currency symbols and commas
    cleaned = raw_str.replace("$", "").replace(",", "").strip()
    try:
        val = float(cleaned)
        if val >= 0:
            return round(val, 2), "USD", raw_str
        return None, None, raw_str
    except ValueError:
        return None, None, raw_str


def parse_categories(raw_cats: Any) -> List[Dict[str, Any]]:
    """
    Parses categories array into hierarchical Category nodes.
    Category.id = canonical full breadcrumb path (e.g. 'Musical Instruments > Guitars')
    """
    if not raw_cats or not isinstance(raw_cats, list):
        return []

    clean_labels = [str(c).strip() for c in raw_cats if c and str(c).strip()]
    if not clean_labels:
        return []

    categories = []
    for i, label in enumerate(clean_labels):
        full_path = " > ".join(clean_labels[: i + 1])
        parent_id = " > ".join(clean_labels[:i]) if i > 0 else None
        categories.append({
            "id": full_path,
            "name": label,
            "level": i,
            "parent_id": parent_id,
            "path": clean_labels[: i + 1],
        })

    return categories


def generate_review_id(user_id: str, parent_asin: str, asin: str, timestamp: int, rating: float) -> str:
    """
    Generates a deterministic Review ID from canonical fields.
    Format: rev_<20-char-sha256-hex>
    """
    raw_key = f"{user_id}|{parent_asin}|{asin}|{timestamp}|{rating}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:20]
    return f"rev_{key_hash}"


def compute_content_hash(user_id: str, parent_asin: str, asin: str, rating: float, 
                         timestamp: int, title: str, text: str) -> bytes:
    """
    Computes 16-byte MD5 digest of canonicalized review fields for exact duplicate filtering.
    """
    hash_str = f"{user_id}|{parent_asin}|{asin}|{rating}|{timestamp}|{title}|{text}"
    return hashlib.md5(hash_str.encode("utf-8", errors="replace")).digest()


class Preprocessor:
    def __init__(self, mode: str = "sample", sample_products: int = 10000, sample_reviews: int = 50000):
        self.mode = mode
        self.sample_products_target = sample_products
        self.sample_reviews_target = sample_reviews
        self.stats: Dict[str, Any] = {
            "mode": mode,
            "sample_products_target": sample_products if mode == "sample" else None,
            "sample_reviews_target": sample_reviews if mode == "sample" else None,
            "raw_products_read": 0,
            "processed_products": 0,
            "raw_reviews_read": 0,
            "processed_reviews": 0,
            "duplicates_removed": 0,
            "malformed_reviews": 0,
            "unique_users": 0,
            "unique_brands": 0,
            "unique_categories": 0,
            "products_with_price": 0,
            "products_with_null_price": 0,
            "zero_price_count": 0,
            "verified_purchases": 0,
            "unverified_reviews": 0,
            "variant_asin_diff_count": 0,
            "products_ge_1_review": 0,
            "products_ge_3_reviews": 0,
            "products_ge_5_reviews": 0,
            "products_zero_reviews": 0,
            "start_time": time.time(),
            "elapsed_seconds": 0.0,
        }

    def run(self):
        print("=================================================================")
        print(f"--- ShopGraph Preprocessing Pipeline (Mode: {self.mode.upper()}) ---")
        print("=================================================================")
        print(f"Raw metadata file : {RAW_META_FILE}")
        print(f"Raw reviews file  : {RAW_REVIEW_FILE}")
        print(f"Output directory  : {PROCESSED_DIR}")

        if not RAW_META_FILE.exists() or not RAW_REVIEW_FILE.exists():
            raise FileNotFoundError(f"Raw data files missing in {RAW_DIR}. Run download_raw.py first.")

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        categories_dict: Dict[str, Dict[str, Any]] = {}
        brands_dict: Dict[str, Dict[str, Any]] = {}
        target_product_ids: Set[str] = set()

        products_out_path = PROCESSED_DIR / "products.jsonl"
        reviews_out_path = PROCESSED_DIR / "reviews.jsonl"
        categories_out_path = PROCESSED_DIR / "categories.jsonl"
        brands_out_path = PROCESSED_DIR / "brands.jsonl"

        # -------------------------------------------------------------
        # STEP 1: Frequency Scan (Sample Mode Only)
        # -------------------------------------------------------------
        review_counts: Counter = Counter()
        if self.mode == "sample":
            print("\n[Step 1/3] Pre-scanning reviews to calculate product review density...")
            t_scan = time.time()
            with open(RAW_REVIEW_FILE, "r", encoding="utf-8", errors="replace") as f_rev:
                for line_idx, line in enumerate(f_rev, 1):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        rec = json.loads(line_str)
                        p_asin = rec.get("parent_asin")
                        if p_asin:
                            review_counts[p_asin] += 1
                    except Exception:
                        continue
                    if line_idx % 1000000 == 0:
                        print(f"  Scanned {line_idx:,} reviews in {time.time()-t_scan:.1f}s...")
            print(f"--> Frequency scan complete ({len(review_counts):,} reviewed products found).")

        # -------------------------------------------------------------
        # STEP 2: Process Product Metadata
        # -------------------------------------------------------------
        print("\n[Step 2/3] Processing Product Metadata...")
        dept_counts = defaultdict(int)
        dept_cap = max(600, self.sample_products_target // 12) if self.mode == "sample" else sys.maxsize

        # In sample mode: Pass 2a - identify target product IDs meeting density & diversity thresholds
        if self.mode == "sample":
            print(f"  Selecting {self.sample_products_target:,} review-dense products (min >= 3 reviews, cap: {dept_cap}/dept)...")
            # Pass 2a: products with >= 3 reviews
            with open(RAW_META_FILE, "r", encoding="utf-8", errors="replace") as f_meta:
                for line in f_meta:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        raw = json.loads(line_str)
                    except Exception:
                        continue
                    p_id = raw.get("parent_asin")
                    if not p_id or not isinstance(p_id, str):
                        continue
                    p_id = p_id.strip()
                    cnt = review_counts.get(p_id, 0)
                    if cnt < 3:
                        continue
                    main_cat = raw.get("main_category") or "General"
                    if dept_counts[main_cat] >= dept_cap:
                        continue
                    target_product_ids.add(p_id)
                    dept_counts[main_cat] += 1
                    if len(target_product_ids) >= self.sample_products_target:
                        break

            # Pass 2b: if needed, fill up to target count from products with >= 2 reviews
            if len(target_product_ids) < self.sample_products_target:
                print(f"  Filling remaining quota (currently {len(target_product_ids):,} products)...")
                with open(RAW_META_FILE, "r", encoding="utf-8", errors="replace") as f_meta:
                    for line in f_meta:
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            raw = json.loads(line_str)
                        except Exception:
                            continue
                        p_id = raw.get("parent_asin")
                        if not p_id or p_id in target_product_ids:
                            continue
                        p_id = p_id.strip()
                        if review_counts.get(p_id, 0) >= 2:
                            target_product_ids.add(p_id)
                            if len(target_product_ids) >= self.sample_products_target:
                                break

            print(f"--> Target products selected: {len(target_product_ids):,} across {len(dept_counts)} departments.")

        # Now write normalized products directly to products.jsonl
        written_products = 0
        with open(products_out_path, "w", encoding="utf-8") as f_prod_out:
            with open(RAW_META_FILE, "r", encoding="utf-8", errors="replace") as f_meta:
                for line_idx, line in enumerate(f_meta, 1):
                    self.stats["raw_products_read"] += 1
                    line_str = line.strip()
                    if not line_str:
                        continue

                    try:
                        raw = json.loads(line_str)
                    except Exception:
                        continue

                    p_id = raw.get("parent_asin")
                    if not p_id or not isinstance(p_id, str) or not p_id.strip():
                        continue
                    p_id = p_id.strip()

                    # Filter in sample mode
                    if self.mode == "sample" and p_id not in target_product_ids:
                        continue

                    title = str(raw.get("title") or "").strip()
                    avg_rating = raw.get("average_rating")
                    if avg_rating is not None:
                        try:
                            avg_rating = round(float(avg_rating), 2)
                        except (ValueError, TypeError):
                            avg_rating = None

                    rating_num = raw.get("rating_number")
                    try:
                        rating_num = int(rating_num) if rating_num is not None else 0
                    except (ValueError, TypeError):
                        rating_num = 0

                    # Categories
                    cat_nodes = parse_categories(raw.get("categories"))
                    leaf_cat_id = cat_nodes[-1]["id"] if cat_nodes else None
                    for c in cat_nodes:
                        categories_dict[c["id"]] = c

                    # Brand / Store
                    b_id, b_name = normalize_brand(raw.get("store"))
                    if b_id and b_name:
                        if b_id not in brands_dict:
                            brands_dict[b_id] = {
                                "id": b_id,
                                "name": b_name,
                                "raw_store": raw.get("store"),
                            }

                    # Price normalization (strictly preserves NULLs)
                    price_val, price_curr, raw_price_str = normalize_price(raw.get("price"))
                    if price_val is not None:
                        self.stats["products_with_price"] += 1
                    else:
                        self.stats["products_with_null_price"] += 1

                    # Images extraction
                    primary_image = None
                    raw_images = raw.get("images")
                    if isinstance(raw_images, list) and raw_images:
                        img0 = raw_images[0]
                        if isinstance(img0, dict):
                            primary_image = img0.get("large") or img0.get("hi_res") or img0.get("thumb")

                    features = raw.get("features")
                    if not isinstance(features, list):
                        features = []
                    features = [str(feat).strip() for feat in features if feat and str(feat).strip()]

                    desc = raw.get("description")
                    if not isinstance(desc, list):
                        desc = [str(desc).strip()] if desc else []
                    desc = [str(d).strip() for d in desc if d and str(d).strip()]

                    details = raw.get("details")
                    if not isinstance(details, dict):
                        details = {}

                    main_cat = raw.get("main_category") or "General"

                    product_record = {
                        "id": p_id,
                        "title": title,
                        "average_rating": avg_rating,
                        "rating_count": rating_num,
                        "price": price_val,
                        "price_currency": price_curr,
                        "raw_price": raw_price_str,
                        "brand_id": b_id,
                        "main_category": main_cat,
                        "category_id": leaf_cat_id,
                        "features": features[:15],
                        "description": desc[:5],
                        "image_url": primary_image,
                        "details": details,
                    }

                    f_prod_out.write(json.dumps(product_record, ensure_ascii=False) + "\n")
                    written_products += 1

                    if self.mode == "full" and written_products % 50000 == 0:
                        print(f"  Products processed: {written_products:,}...")

        self.stats["processed_products"] = written_products
        self.stats["unique_brands"] = len(brands_dict)
        self.stats["unique_categories"] = len(categories_dict)
        print(f"--> Products written: {written_products:,} to {products_out_path.name}")
        print(f"--> Unique Brands: {len(brands_dict):,}")
        print(f"--> Unique Canonical Categories: {len(categories_dict):,}")

        # -------------------------------------------------------------
        # STEP 3: Stream Reviews with Canonical Deduplication
        # -------------------------------------------------------------
        print("\n[Step 3/3] Streaming Reviews with Canonical Duplicate Filtering...")
        seen_content_hashes: Set[bytes] = set()
        user_ids: Set[str] = set()
        reviews_written = 0
        per_prod_rev_counts: Counter = Counter()

        # Dynamic per-product cap: e.g. 50,000 / 10,000 = ~5-6 reviews per product
        per_product_cap = max(3, (self.sample_reviews_target // self.sample_products_target) + 1) if self.mode == "sample" else sys.maxsize

        with open(reviews_out_path, "w", encoding="utf-8") as f_rev_out:
            with open(RAW_REVIEW_FILE, "r", encoding="utf-8", errors="replace") as f_rev_in:
                for line_idx, line in enumerate(f_rev_in, 1):
                    self.stats["raw_reviews_read"] += 1
                    line_str = line.strip()
                    if not line_str:
                        continue

                    try:
                        raw = json.loads(line_str)
                    except Exception:
                        self.stats["malformed_reviews"] += 1
                        continue

                    u_id = raw.get("user_id")
                    p_asin = raw.get("parent_asin")
                    asin = raw.get("asin")
                    rating = raw.get("rating")
                    ts = raw.get("timestamp")

                    # Validate critical fields
                    if not u_id or not p_asin or not asin or rating is None or ts is None:
                        self.stats["malformed_reviews"] += 1
                        continue

                    u_id = str(u_id).strip()
                    p_asin = str(p_asin).strip()
                    asin = str(asin).strip()

                    # In sample mode: only retain reviews for selected products
                    if self.mode == "sample" and p_asin not in target_product_ids:
                        continue

                    # In sample mode: apply per-product cap to distribute reviews evenly
                    if self.mode == "sample" and per_prod_rev_counts[p_asin] >= per_product_cap:
                        continue

                    try:
                        rating = float(rating)
                        ts = int(ts)
                    except (ValueError, TypeError):
                        self.stats["malformed_reviews"] += 1
                        continue

                    title = str(raw.get("title") or "").strip()
                    text = str(raw.get("text") or "").strip()
                    vp = True if raw.get("verified_purchase") is True else False
                    helpful = raw.get("helpful_vote", 0)
                    try:
                        helpful = int(helpful)
                    except (ValueError, TypeError):
                        helpful = 0

                    # Exact canonical duplicate check (Phase 1 verified strategy)
                    c_hash = compute_content_hash(u_id, p_asin, asin, rating, ts, title, text)
                    if c_hash in seen_content_hashes:
                        self.stats["duplicates_removed"] += 1
                        continue
                    seen_content_hashes.add(c_hash)

                    # Variant ASIN tracking
                    if asin != p_asin:
                        self.stats["variant_asin_diff_count"] += 1

                    # Verified purchase tracking
                    if vp:
                        self.stats["verified_purchases"] += 1
                    else:
                        self.stats["unverified_reviews"] += 1

                    user_ids.add(u_id)
                    per_prod_rev_counts[p_asin] += 1

                    # Deterministic Review ID
                    rev_id = generate_review_id(u_id, p_asin, asin, ts, rating)

                    review_record = {
                        "id": rev_id,
                        "user_id": u_id,
                        "product_id": p_asin,
                        "variant_asin": asin,
                        "rating": rating,
                        "title": title,
                        "text": text,
                        "timestamp": ts,  # Review publication time
                        "verified_purchase": vp,
                        "helpful_votes": helpful,
                    }

                    f_rev_out.write(json.dumps(review_record, ensure_ascii=False) + "\n")
                    reviews_written += 1

                    if line_idx % 500000 == 0:
                        print(f"  Reviews scanned: {line_idx:,} | Written: {reviews_written:,} | Dups dropped: {self.stats['duplicates_removed']:,}")

        self.stats["processed_reviews"] = reviews_written
        self.stats["unique_users"] = len(user_ids)

        # Review coverage distribution
        p_ge_1 = sum(1 for c in per_prod_rev_counts.values() if c >= 1)
        p_ge_3 = sum(1 for c in per_prod_rev_counts.values() if c >= 3)
        p_ge_5 = sum(1 for c in per_prod_rev_counts.values() if c >= 5)
        p_zero = written_products - p_ge_1

        self.stats["products_ge_1_review"] = p_ge_1
        self.stats["products_ge_3_reviews"] = p_ge_3
        self.stats["products_ge_5_reviews"] = p_ge_5
        self.stats["products_zero_reviews"] = p_zero

        # -------------------------------------------------------------
        # STEP 4: Write Categories and Brands JSONL
        # -------------------------------------------------------------
        print("\nWriting Categories and Brands JSONL...")
        with open(categories_out_path, "w", encoding="utf-8") as f_out:
            for cat in sorted(categories_dict.values(), key=lambda x: (x["level"], x["id"])):
                f_out.write(json.dumps(cat, ensure_ascii=False) + "\n")
        print(f"--> Saved: {categories_out_path.name} ({len(categories_dict):,} records)")

        with open(brands_out_path, "w", encoding="utf-8") as f_out:
            for b in sorted(brands_dict.values(), key=lambda x: x["name"]):
                f_out.write(json.dumps(b, ensure_ascii=False) + "\n")
        print(f"--> Saved: {brands_out_path.name} ({len(brands_dict):,} records)")

        # Write stats.json
        self.stats["elapsed_seconds"] = round(time.time() - self.stats["start_time"], 2)
        stats_out_path = PROCESSED_DIR / "stats.json"
        with open(stats_out_path, "w", encoding="utf-8") as f_out:
            json.dump(self.stats, f_out, indent=2)
        print(f"--> Saved: {stats_out_path.name}")

        print("\n=================================================================")
        print("--- Preprocessing Complete! ---")
        print("=================================================================")
        print(f"Products Written          : {self.stats['processed_products']:,}")
        print(f"Reviews Written           : {self.stats['processed_reviews']:,}")
        print(f"Products with >= 1 Review : {p_ge_1:,} ({p_ge_1/written_products:.1%})")
        print(f"Products with >= 3 Reviews: {p_ge_3:,} ({p_ge_3/written_products:.1%})")
        print(f"Products with ZERO Reviews: {p_zero:,} ({p_zero/written_products:.1%})")
        print(f"Duplicates Removed        : {self.stats['duplicates_removed']:,}")
        print(f"Unique Users              : {self.stats['unique_users']:,}")
        print(f"Unique Brands             : {self.stats['unique_brands']:,}")
        print(f"Unique Categories         : {self.stats['unique_categories']:,}")
        print(f"Verified Purchases        : {self.stats['verified_purchases']:,}")
        print(f"Elapsed Time              : {self.stats['elapsed_seconds']}s")
        print("=================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShopGraph Dataset Preprocessor")
    parser.add_argument("--mode", choices=["sample", "full"], default="sample",
                        help="Processing mode: 'sample' for review-dense development subset, 'full' for complete dataset")
    parser.add_argument("--sample-products", type=int, default=10000,
                        help="Number of products to sample in sample mode (default: 10000)")
    parser.add_argument("--sample-reviews", type=int, default=50000,
                        help="Maximum reviews to retain in sample mode (default: 50000)")
    args = parser.parse_args()

    preprocessor = Preprocessor(
        mode=args.mode,
        sample_products=args.sample_products,
        sample_reviews=args.sample_reviews,
    )
    preprocessor.run()
