# ShopGraph — Explainable Graph-RAG E-Commerce Intelligence Platform

ShopGraph transforms an Amazon Musical Instruments review corpus into a connected product knowledge graph in Neo4j, combining structured Cypher graph traversal, dense vector retrieval (`BAAI/bge-base-en-v1.5`), and grounded LLM synthesis to deliver natural-language product discovery, review intelligence, recommendations, comparisons, and explainable evidence.

---

## 1. Why Graph-RAG?

Standard vector RAG systems suffer from three critical weaknesses in e-commerce:
1. **Constraint Blindness**: Vector embeddings cannot reliably enforce hard filters (e.g., price ceiling $\le \$300$, brand exclusions, taxonomy boundaries).
2. **Hallucinated Attributes**: Pure LLMs invent prices, ratings, and specifications not present in the catalog.
3. **Black-Box Recommendations**: Vector similarity cannot explain *why* two products relate or whether verified buyers engaged with both items.

**ShopGraph resolves this through Graph-RAG**:
- **Structured Knowledge Graph**: Stores canonical entities (`Product`, `Brand`, `Category`, `Review`, `User`) and verified relationships (`[:BELONGS_TO]`, `[:BRANDED_BY]`, `[:REVIEWS]`, `[:PURCHASED]`).
- **Dense Vector Search**: 768-dimensional embeddings via `BAAI/bge-base-en-v1.5` for semantic matching on product titles, features, and reviews.
- **Reciprocal Rank Fusion (RRF)**: Merges graph-structured candidates and vector similarity candidates with $k=60$, enforcing strict pre- and post-fusion hard constraints.
- **Traceable Evidence**: Synthesized answers cite verified graph facts, review excerpts, and similarity scores.

```
User Query
    │
    ▼
Natural Language Query Understanding (Intent + Hard Constraints)
    │
    ├── Structured Cypher Traversal ──┐
    │                                 ▼
    └── BGE Vector Search (ANN) ──► Reciprocal Rank Fusion (k=60) + Hard Constraints Barrier
                                      │
                                      ▼
                                Evidence Fusion (Graph Facts + Reviews + Similarities)
                                      │
                                      ▼
                                Grounded LLM Response (Gemini / Groq)
```

---

## 2. Graph Schema & Semantics

### Nodes:
- `(:Product)`: Primary key is canonical `parent_asin`. Contains `title`, `price` (float or null), `average_rating`, `rating_count`, `features`, `embedding` (768d).
- `(:Brand)`: Normalized brand name.
- `(:Category)`: Full hierarchical canonical path (e.g., `"Musical Instruments > Guitars > Electric Guitars > Solid Body"`).
- `(:Review)`: Deterministic review ID. Contains `rating`, `title`, `text`, `timestamp` (publication time), `verified_purchase` (boolean), `variant_asin`.
- `(:User)`: Reviewer ID.

### Relationships:
- `(:Product)-[:BELONGS_TO]->(:Category)`
- `(:Product)-[:BRANDED_BY]->(:Brand)`
- `(:User)-[:WROTE]->(:Review)-[:REVIEWS]->(:Product)`
- `(:User)-[:PURCHASED {verified: true}]->(:Product)`: Created **strictly** when `verified_purchase == true`.
- `(:Category)-[:SUB_CATEGORY_OF]->(:Category)`

> [!IMPORTANT]
> **Strict Semantic Safeguards**:
> - Ongoing physical ownership is not claimed.
> - Combinatorial relationships (`BOUGHT_TOGETHER`, `CO_PURCHASED`, `SIMILAR_TO`) are **never** materialized as static graph edges.
> - Shared verified purchaser relationships are computed dynamically in Cypher and phrased strictly as *"verified purchasers associated with both products"* — never as observed co-purchases.

---

## 3. Known Data Limitations

1. **Unlisted Catalog Prices**: Approximately 18% of products in the public Amazon corpus have null prices. The engine strictly preserves `null` values and displays `"Price unavailable"` — never fabricating `$0.00` or "free".
2. **Source Amazon Taxonomy Contamination**: In the source dataset, accessories vastly outnumber instruments (1,897 guitar accessories vs 64 electric guitars). Naive substring search matches accessories; ShopGraph enforces exact taxonomy hierarchy boundaries (`> Electric Guitars >`) to isolate instruments.
3. **CPU Embedding Latency**: The initial local BGE model execution on CPU requires ~60s cold-start before running warm inference at ~250–450ms.

---

## 4. Multi-Factor Recommendation Methodology

ShopGraph's recommendation engine evaluates 6 distinct transparent factors:
1. **Category Relevance** ($w=0.20$): Taxonomy path matching.
2. **Bayesian-Adjusted Rating** ($w=0.25$): Shrinkage formula $\frac{v \cdot R + m \cdot C}{v + m}$ ($C=4.2$, $m=5$) preventing single-review bias.
3. **Price Fit** ($w=0.15$): Budget ceiling satisfaction.
4. **Brand Reputation** ($w=0.10$): Brand match and presence.
5. **Semantic Similarity** ($w=0.15$): Cosine vector distance from BGE embeddings.
6. **Purchaser Overlap** ($w=0.15$): Shared verified purchaser count on a logarithmic scale.

---

## 5. Local Setup & Quickstart

### Prerequisites:
- Python 3.10+
- Node.js 18+
- Docker Engine (for Neo4j 5.26 Community)

### Step 1: Clone & Configure
```bash
# Copy template environment file
cp .env.example .env
```

### Step 2: Start Neo4j via Docker
```bash
docker compose up -d
# Neo4j runs on bolt://localhost:7687 and http://localhost:7474
```

### Step 3: Start FastAPI Backend
```bash
# Install dependencies
pip install -r backend/requirements.txt  # or: pip install fastapi uvicorn neo4j sentence-transformers google-genai pytest

# Start development server
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
Interactive OpenAPI documentation: `http://127.0.0.1:8000/docs`

### Step 4: Start React / Vite Frontend
```bash
cd frontend
npm install
npm run dev -- --port 3000 --host 127.0.0.1
```
Open `http://127.0.0.1:3000` in your browser.

---

## 6. Systematic Evaluation & Benchmarks

Run the executable evaluation framework across the 15 fixed benchmark queries:
```bash
python scripts/evaluate_system.py
```

### Measured Comparison:

| System Configuration | Avg Latency | Hard Constraint Violations | Avg Evidence Items | Grounding Integrity |
| :--- | :---: | :---: | :---: | :--- |
| **A. LLM-Only Baseline** | ~1,200 ms | Multiple (Hallucinated prices) | 0.0 | Zero Graph Grounding |
| **B. Graph-RAG (Cypher)** | 1,115.7 ms | 0 / 15 | 17.8 | 100% Graph Provenance |
| **C. Hybrid Graph + Vector RAG** | 902.4 ms (warm) | 0 / 15 | 15.9 | Dual Fused Corroboration |

### Local CPU Performance Benchmarks:
```bash
python scripts/benchmark_performance.py
```
- **BGE Model Cold-Start (CPU)**: ~65,000 ms
- **Structured Cypher Search**: p50 = **239.4 ms** | p95 = **437.2 ms**
- **BGE Vector Search (CPU)**: p50 = **250.8 ms** | p95 = **534.2 ms**
- **Hybrid Retrieval (RRF)**: p50 = **822.2 ms** | p95 = **1,477.3 ms**
- **Product Detail Lookup**: p50 = **20.2 ms** | p95 = **43.5 ms**
- **Review Intelligence**: p50 = **20.5 ms** | p95 = **151.8 ms**

---

## 7. Security & Production Hardening

- **Cypher Read-Only Validator**: All untrusted queries are checked against strict mutation regexes (`CREATE`, `MERGE`, `DELETE`, `SET`, `DROP`, `ALTER`), forbidden procedures (`CALL dbms`, `apoc.system`, `LOAD CSV`), and unauthorized labels.
- **Penetration Test Suite**: 38 adversarial security tests passing in `backend/tests/test_adversarial_security.py`.
- **CORS Hardening**: In production (`APP_ENV=production`), origins are strictly restricted to `CORS_ORIGINS` without wildcard regexes.
- **Exception Masking**: Production errors mask internal server paths and database connection strings.

---

## 8. Test Execution

```bash
# Run backend test suite (unit, integration, and adversarial security tests)
python -m pytest backend/tests/ -v

# Run frontend production build
cd frontend && npm run build
```

---

## 9. Production Deployment Guide (Phase 6)

ShopGraph is designed to run in production completely within the free tier of modern cloud platforms:
* **Frontend**: Vercel (Hobby Free Tier)
* **Backend**: Google Cloud Run (Serverless Container with 2GB RAM / 1 vCPU)
* **Graph & Vector Database**: Neo4j AuraDB Free (200k node capacity, vector index support)

### Step 1: Deploy Neo4j AuraDB Free
1. Sign up at [console.neo4j.io](https://console.neo4j.io) and create a **Free AuraDB Instance**.
2. Save your connection URI (`neo4j+s://<instance-id>.databases.neo4j.io`) and password.
3. Migrate the graph and vector embeddings:
   ```bash
   # Option A: Direct cloud sync (recommended)
   python scripts/export_neo4j_dump.py --sync-to-aura --uri neo4j+s://<instance-id>.databases.neo4j.io --password <password>

   # Option B: Export local Docker dump for manual console upload
   python scripts/export_neo4j_dump.py --dump-local
   # In Aura Console: Instance -> '...' -> 'Load Database' -> select data/dumps/neo4j_shopgraph.dump
   ```

### Step 2: Deploy Backend to Google Cloud Run
1. Ensure the Google Cloud SDK is installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project <YOUR_GCP_PROJECT_ID>
   ```
2. Build and deploy the backend container directly from source:
   ```bash
   gcloud run deploy shopgraph-backend \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 1 \
     --min-instances 0 \
     --max-instances 3 \
     --port 8080 \
     --set-env-vars APP_ENV=production,NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io,NEO4J_USERNAME=neo4j,NEO4J_PASSWORD=<password>,LLM_PROVIDER=gemini,GEMINI_API_KEY=<key>,GEMINI_MODEL=gemini-2.5-flash,EMBEDDING_PROVIDER=local,EMBEDDING_MODEL=BAAI/bge-base-en-v1.5,EMBEDDING_DIMENSION=768
   ```
   *(Note: `--memory 2Gi` is mandatory for PyTorch CPU + BGE-base; `--min-instances 0` ensures $0 idle cost).*
3. Verify deployment health:
   ```bash
   curl https://<YOUR-CLOUD-RUN-URL>/health
   ```

### Step 3: Deploy Frontend to Vercel
1. Import the repository into [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set Environment Variable:
   * `VITE_API_BASE_URL` = `https://<YOUR-CLOUD-RUN-URL>`
4. Click **Deploy**.

### Step 4: Finalize CORS Protection
Once the Vercel URL is generated (e.g., `https://shopgraph-app.vercel.app`), update Cloud Run:
```bash
gcloud run services update shopgraph-backend \
  --region us-central1 \
  --update-env-vars CORS_ORIGINS=https://shopgraph-app.vercel.app
```

