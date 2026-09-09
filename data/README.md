# ShopGraph Dataset Documentation

## 1. Overview & Dataset Source
- **Dataset Name**: Amazon Reviews '23
- **Primary Source / Authors**: Julian McAuley Lab, University of California San Diego (UCSD)
- **Authoritative Hosting**: [Hugging Face Datasets: McAuley-Lab/Amazon-Reviews-2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
- **Official Project Website**: [https://amazon-reviews-2023.github.io/](https://amazon-reviews-2023.github.io/)
- **Associated Publication**:
  > Y. Hou, J. Li, Z. He, A. Yan, X. Chen, J. McAuley. *Bridging Language and Items for Retrieval and Recommendation*. arXiv:2403.03952 (2024).

---

## 2. Selected Subset & Rationale
- **Category Selected**: `Musical_Instruments`
- **Candidate Evaluated**: `Electronics` (initial candidate from project specification) vs. `Musical_Instruments` vs. `Appliances` vs. `All_Beauty`.
- **Why `Electronics` Was Not Chosen as Full Raw Download**:
  - `Electronics` metadata is 5.0 GB (`meta_Electronics.jsonl`) with 1,610,012 products.
  - `Electronics` reviews is 21.6 GB (`Electronics.jsonl`) with ~44,000,000 reviews.
  - Total raw size is **26.6 GB**, taking ~3.5 hours to download at standard speeds and requiring massive memory/disk overhead that exceeds the feasibility of a normal developer machine.
- **Why `Musical_Instruments` Was Chosen**:
  1. **Domain Parity with Electronics**: Like electronics, musical gear features dense technical specifications (inputs/outputs, analog/digital, wattage, impedance, materials, dimensions, connectivity) and prominent brands (Fender, Gibson, Yamaha, Shure, Behringer, Boss, Roland, Audio-Technica, Sennheiser, Korg).
  2. **Superior Graph Connectivity**: Unlike replacement-part domains (e.g. Appliances, which lacks a dense 5-core interaction benchmark), musical instrument buyers exhibit strong cross-category co-purchase behavior (instruments -> amplifiers -> pedals -> audio interfaces -> studio microphones -> cables -> headphones).
  3. **High Interaction Density**: The 5-core interaction benchmark contains 29.7 MB of dense multi-interaction graphs, providing rich multi-hop querying and explainability.
  4. **Local Feasibility**: Total raw download is 2.09 GB (602.6 MB metadata + 1.48 GB reviews), allowing complete local development and fast reproducible ingestion.

---

## 3. License & Usage Information
- **Source License**: The Amazon Reviews '23 dataset is released for academic, research, and non-commercial educational purposes by the UCSD McAuley Lab.
- **Data Privacy**: Reviewer IDs and identities are anonymized hashes (`user_id`). No direct personally identifiable information (PII) is exposed.
- **Terms**: Compliant with Amazon data access policies for academic/research benchmarking.

---

## 4. File Structure & Descriptions

```
data/
├── raw/                               # Raw immutable source data (GIT IGNORED)
│   ├── meta_Musical_Instruments.jsonl # 602.61 MB (213,593 product metadata records)
│   └── Musical_Instruments.jsonl      # 1,485.68 MB (3,017,439 user review records)
├── processed/                         # Filtered/curated subsets for graph ingestion
├── inspection_results.json            # Machine-readable output from inspect_dataset.py
└── README.md                          # This documentation file
```

> **IMPORTANT GIT NOTE**:
> Raw dataset files (`data/raw/*`, `*.jsonl`, `*.parquet`) are **NOT** committed to Git. A root `.gitignore` enforces this rule. Raw datasets must be acquired via the reproducible ingestion script described below.

---

## 5. Download Instructions & Reproducibility
The dataset can be automatically and reproducibly downloaded at any time using the project download script:

```bash
# Run from repository root:
python scripts/download_raw.py
```

The script supports:
- Automatic directory creation (`data/raw/`)
- Content-Length verification
- HTTP Range resume capability if interrupted
- Progress and throughput monitoring

---

## 6. Discovered Schema & Field Details

### Product Metadata Schema (`meta_Musical_Instruments.jsonl`)
| Field Name | Type | Description | % Present | Neo4j Proposed Role |
| :--- | :--- | :--- | :--- | :--- |
| `parent_asin` | String | Unique product identifier (canonical item ID) | 100.0% | `Product.id` (Unique Index) |
| `title` | String | Product display name | 100.0% | `Product.title` (Text Search Index) |
| `average_rating` | Float | Cumulative average rating (1.0 - 5.0) | 100.0% | `Product.average_rating` |
| `rating_number` | Integer | Total count of ratings | 100.0% | `Product.rating_count` |
| `store` | String | Brand / Manufacturer storefront name | 98.3% | `(:Product)-[:BRANDED_BY]->(:Brand)` |
| `main_category` | String | High-level primary department | 98.4% | `Product.main_category` |
| `categories` | List[String]| Hierarchical taxonomy breadcrumbs | 91.1% | `(:Product)-[:BELONGS_TO]->(:Category)` |
| `features` | List[String]| Bullet points highlighting key features | 82.9% | `Product.features` (Embedding target) |
| `description` | List[String]| Detailed textual description | 71.5% | `Product.description` (Embedding target) |
| `price` | String/Float| Retail price in USD | 39.8% | `Product.price` |
| `images` | List[Dict]  | Image objects (`thumb`, `large`, `hi_res` URLs)| 100.0% | `Product.image_url` |
| `videos` | List[Dict]  | Video titles and playback URLs | 29.1% | `Product.videos` |
| `details` | Dict/String | Technical specifications & metadata dictionary | 98.5% | Structured specs (`weight`, `dimensions`, etc.) |
| `bought_together`| Null | Direct co-purchase link | 0.0% | **Absent in raw dataset (0 non-null values across 213,593 records)** |

### Review Interaction Schema (`Musical_Instruments.jsonl`)
| Field Name | Type | Description | % Present | Neo4j Proposed Role |
| :--- | :--- | :--- | :--- | :--- |
| `user_id` | String | Unique anonymized reviewer ID | 100.0% | `User.id` (Unique Index) |
| `parent_asin` | String | Item identifier matching metadata | 100.0% | Target `Product.id` |
| `asin` | String | Specific purchased variant ASIN | 100.0% | Interaction property `variant_asin` |
| `rating` | Float | Given star rating (1.0 to 5.0) | 100.0% | `Review.rating` |
| `title` | String | Review headline / subject line | 100.0% | `Review.title` |
| `text` | String | Full review commentary text | 99.99% | `Review.text` (Embedding / Graph-RAG target) |
| `timestamp` | Int64 | Review publication timestamp in ms epoch | 100.0% | `Review.timestamp` (NOT order/purchase date) |
| `helpful_vote`| Integer| Number of upvotes from other users | 100.0% | `Review.helpful_votes` |
| `verified_purchase` | Boolean | Confirmation of Amazon verified purchase | 100.0% | Enables derived `(:User)-[:PURCHASED]->(:Product)` |
| `images` | List[Dict] | User-submitted photos | 5.5% | `Review.images` |

---

## 7. Dataset Statistics (Empirically Validated via 100% SQLite Audit)

### Raw Files
- `meta_Musical_Instruments.jsonl`: **602.61 MB** (631,877,970 bytes)
- `Musical_Instruments.jsonl`: **1,485.68 MB** (1,557,845,107 bytes)
- Total Raw Disk Footprint: **2,088.29 MB (~2.09 GB)**

### Core Metadata Entity Counts
- **Total Metadata Records**: 213,593
- **Unique Products (`parent_asin`)**: 213,593 (100.0% unique; 0 duplicate IDs)
- **Unique Brands / Stores**: 26,284
- **Distinct Taxonomy Paths**: 727
- **Unique Category Taxonomy Nodes**: 575 (72 labels occur under multiple parent paths, requiring full-path canonical identities)
- **Non-null `bought_together` Count**: 0 (0.00% present)
- **Products with Technical Specs (`details`)**: 210,339 (98.48%)
- **Products with Populated Price**: 84,916 (39.76%)

### Review Interaction Counts
- **Total Reviews**: 3,017,439
- **Unique Users**: 1,762,679
- **Unique Reviewed Parent Products**: 213,571 (99.99% catalog coverage)
- **Unique Variant ASINs (`asin`)**: 259,791
- **Reviews with `asin != parent_asin`**: 1,505,952 (49.91% of reviews represent child variants)
- **Parent Products with Multiple Child ASINs**: 16,613
- **Verified Purchases**: 2,780,515 (**92.15%**)
- **Unverified Reviews**: 236,924 (7.85%)
- **Identical Canonicalized Review Content**: 33,658 redundant rows across 28,240 duplicate groups (1.12%, matching on parsed core fields)
- **Duplicate Keys `(user_id, parent_asin, timestamp)`**: 33,659 redundant rows across 28,241 groups
- **Legitimate Multi-Timestamp Reviews**: 7,117 user-product pairs (reviews submitted across multiple dates)
- **Missing Required Fields**: 0 (`user_id`, `parent_asin`, `asin`, `timestamp`, `rating`, `title` all 100% present)
- **Missing Review Text**: 217 (0.007%)
- **Average Rating Mean**: 4.19 / 5.0

### Rating Distribution
- **5 Stars**: 2,024,128 (67.08%)
- **4 Stars**: 400,387 (13.27%)
- **3 Stars**: 197,131 (6.53%)
- **2 Stars**: 131,441 (4.36%)
- **1 Stars**: 264,352 (8.76%)

---

## 8. Graph Relationship Taxonomy & Materialization Guidelines

To maintain semantic honesty and prevent combinatorial explosion in Neo4j:

### 8.1 Observed / Data-Derived (Permanently Materialized in Neo4j)
*Directly supported by raw dataset fields; scales linearly $O(N)$:*
- `(:User)-[:WROTE {timestamp}]->(:Review)`
- `(:Review)-[:REVIEWS {variant_asin}]->(:Product)`
- `(:User)-[:PURCHASED {verified: true, review_timestamp}]->(:Product)` *(Only when `verified_purchase == true`)*
- `(:Product)-[:BRANDED_BY]->(:Brand)`
- `(:Product)-[:BELONGS_TO]->(:Category)` *(via leaf node of canonical breadcrumb path)*
- `(:Category)-[:SUB_CATEGORY_OF]->(:Category)` *(canonical breadcrumb path hierarchy)*

### 8.2 Derived / Projection (Do NOT Fully Materialize)
*Computed via graph algorithms or runtime queries:*
- `(:Product)-[:SHARED_VERIFIED_PURCHASER {shared_purchaser_count}]->(:Product)`
  *(Number of users with verified purchases associated with both products; computed at runtime via 2-hop Cypher or pre-materialized only for top-K with $\ge 3$ support)*
- `(:Product)-[:CO_REVIEWED_WITH {shared_reviewer_count}]->(:Product)`
  *(Shared reviewer engagement)*
- `(:Product)-[:INFERRED_CO_PURCHASE {confidence, support}]->(:Product)`
  *(Proxy model only; explicitly distinguished from observed checkout co-purchase)*

### 8.3 Semantic (Dynamic Vector Retrieval over Static Edge Proliferation)
- Store vector embeddings as node properties (`Product.embedding`).
- Use Neo4j Vector Indexes (HNSW) for dynamic runtime ANN retrieval instead of materializing billions of static `SIMILAR_TO` edges.
- If static `SIMILAR_TO` edges are materialized for graph algorithms, strictly prune to top-5 nearest neighbors with cosine similarity $\ge 0.85$.

