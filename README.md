# ShopGraph — Explainable Graph-RAG E-Commerce Intelligence Platform

ShopGraph transforms a large-scale Amazon Musical Instruments review corpus into a connected product knowledge graph and combines Neo4j graph traversal, vector retrieval, and LLM reasoning to provide natural-language product discovery, review intelligence, recommendations, comparisons, and explainable answers.

---

## 1. Project Architecture & Components

```
User Query
    │
    ▼
[Phase 4] JavaScript Frontend (Vercel)
    │
    ▼
[Phase 3] FastAPI Python Backend
    │
    ├── Natural Language Query Understanding
    ├── Untrusted Text-to-Cypher Safeguards (Read-Only)
    ├── Neo4j Graph Traversal (Cypher)
    ├── Vector Index / ANN Semantic Search
    └── Evidence Fusion & Grounded LLM Response (Gemini / Groq)
    │
    ▼
[Phase 2] Neo4j Knowledge Graph
    ├── Nodes: (:Product), (:User), (:Review), (:Brand), (:Category)
    └── Edges: [:WROTE], [:REVIEWS], [:PURCHASED], [:BRANDED_BY], [:BELONGS_TO], [:SUB_CATEGORY_OF]
```

---

## 2. Repository Structure

```
ShopGraph/
│
├── data/
│   ├── raw/                             # Immutable source data (GIT-IGNORED)
│   │   ├── meta_Musical_Instruments.jsonl
│   │   └── Musical_Instruments.jsonl
│   ├── processed/                       # Cleaned, normalized graph entities
│   │   ├── products.jsonl               # 10,000 canonical products
│   │   ├── reviews.jsonl                # 50,000 reviews with deterministic IDs
│   │   ├── categories.jsonl             # 541 canonical hierarchy nodes
│   │   ├── brands.jsonl                 # 4,531 normalized brands
│   │   ├── stats.json                   # Preprocessing run statistics
│   │   └── README.md                    # Data dictionary and schemas
│   ├── dataset_validation_report.md     # Phase 1 dataset validation report
│   └── README.md                        # Dataset provenance & statistics
│
├── backend/                             # Phase 3 FastAPI Graph-RAG Engine
│   ├── app/
│   │   ├── main.py                      # FastAPI entrypoint, CORS, and lifespans
│   │   ├── config.py                    # Environment settings (Pydantic BaseSettings)
│   │   ├── api/                         # REST routers (/search, /recommend, /products, /compare, /query)
│   │   ├── db/neo4j/                    # Thread-safe Neo4j driver & session lifecycle
│   │   ├── schemas/                     # Pydantic request/response & evidence models
│   │   └── services/
│   │       ├── query_understanding/     # Intent classification & constraint parser
│   │       ├── cypher/                  # Cypher safety validator, sanitizer, generator
│   │       ├── retrieval/               # Graph, Vector, and Hybrid retrievers
│   │       ├── embeddings/              # Gemini & local fallback embeddings
│   │       ├── llm/                     # Gemini & Groq provider abstraction
│   │       ├── explainability/          # Multi-factor score attribution & graph paths
│   │       ├── reviews/                 # Rating distribution & aspect sentiment
│   │       └── recommendations/         # Multi-factor Bayesian recommendation engine
│   ├── tests/                           # 37 comprehensive unit & integration tests
│   └── README.md                        # Backend documentation & API contracts
│
├── cypher/
│   ├── constraints.cypher               # Uniqueness constraints on primary IDs
│   ├── schema.cypher                    # Supporting search & traversal indexes
│   ├── examples/
│   │   └── multi_hop_queries.cypher     # 10 representative multi-hop Cypher queries
│   └── validation/
│       ├── node_integrity.cypher        # Node count and ID validity queries
│       ├── relationship_integrity.cypher# Referential integrity queries
│       └── semantic_checks.cypher       # Semantic boundary & price nullness checks
│
├── scripts/
│   ├── download_raw.py                  # Automated resumable raw downloader
│   ├── inspect_dataset.py               # Initial streaming inspector
│   ├── validate_dataset.py              # Full SQLite disk-backed duplicate auditor
│   ├── preprocess.py                    # Streaming preprocessor (sample & full modes)
│   ├── ingest_neo4j.py                  # Parameterized batch UNWIND Neo4j loader
│   └── validate_graph.py                # Automated Neo4j graph integrity validator
│
├── .env.example                         # Template configuration
├── .gitignore                           # Git exclusion rules
├── ShopGraph_PRD.md                     # Master Product Requirements Document
└── README.md                            # Project overview & guide
```

---

## 3. Dataset Semantics & Core Rules

- **Canonical Product Identity**: `parent_asin` is the primary `Product.id`.
- **Variant Handling**: Child `asin` referenced by a review is stored on `Review.variant_asin`.
- **Review Timestamp**: `timestamp` represents the review publication timestamp, **never an order or purchase date**.
- **Verified Purchase**: `(:User)-[:PURCHASED]->(:Product)` is created **strictly** when `verified_purchase == true`. Ongoing physical ownership is not claimed.
- **Category Hierarchy**: Category IDs are full canonical paths (`"Musical Instruments > Guitars > Electric Guitars > Solid Body"`) to prevent collapsing the 72 ambiguous category labels occurring under different parent paths.
- **Price Nullness**: Missing prices remain `null` and are **never** converted to `$0` or "free".
- **Combinatorial Safeguards**: Derived (`SHARED_VERIFIED_PURCHASER`, `CO_REVIEWED_WITH`) and semantic (`SIMILAR_TO`) relationships are **not** materialized as unconstrained all-pairs edges; they are computed dynamically via Cypher or vector search.

---

## 4. Quickstart: Preprocessing & Ingestion

### Step 1: Environment Setup
```bash
# Copy template configuration
cp .env.example .env

# Install required Python packages
pip install neo4j python-dotenv
```

### Step 2: Run Preprocessing
```bash
# Review-dense development subset (10,000 products with >= 3 reviews, ~50,000 reviews):
python scripts/preprocess.py --mode sample --sample-products 10000 --sample-reviews 50000

# Or process full dataset (213k products, 3M reviews in memory-optimized streaming pass):
python scripts/preprocess.py --mode full
```

### Step 3: Ingest into Neo4j
Configure your Neo4j credentials in `.env` (or pass via CLI):
```bash
# Ingest processed files into Neo4j
python scripts/ingest_neo4j.py --batch-size 2000

# Or test in dry-run mode:
python scripts/ingest_neo4j.py --dry-run
```

### Step 4: Validate Graph Integrity
```bash
python scripts/validate_graph.py
```

### Step 5: Launch Phase 3 FastAPI Backend
```bash
# Run all 37 backend tests
python -m pytest backend/tests/ -v

# Start FastAPI development server on port 8000
uvicorn app.main:app --app-dir backend --reload --port 8000

# Access interactive Swagger API documentation:
# http://localhost:8000/docs
```
