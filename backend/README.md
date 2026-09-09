# ShopGraph Backend — Graph-RAG & Intelligence Engine

The ShopGraph backend is a production-grade FastAPI application powering natural-language product discovery, review intelligence, and explainable recommendations. It bridges the Neo4j Knowledge Graph with Gemini/Groq LLMs, vector ANN retrieval, and multi-hop Cypher traversals.

---

## 1. Architecture & Request Pipeline

```
User Query
    │
    ▼
FastAPI Application (`backend/app/main.py`)
    │
    ▼
Query Understanding (`app/services/query_understanding/`)
    ├── Classifies Intent: product_search, recommendation, comparison, review_intelligence, etc.
    ├── Extracts Constraints: category, brand, price min/max, rating min, review aspects
    └── Selects Strategy: GRAPH_ONLY, VECTOR_ONLY, HYBRID
    │
    ├───────────────────────────────┬───────────────────────────────┐
    ▼                               ▼                               ▼
Structured Graph Retrieval      Vector / Semantic Retrieval      Review Intelligence
(`services/retrieval/graph`)    (`services/retrieval/vector`)    (`services/reviews/`)
    │                               │                               │
    ├── Parameterized Cypher        ├── Neo4j Vector Index ANN      ├── Rating Histogram
    ├── Read-Only Safety Validator  └── Dense Embeddings            ├── Verified / Unverified Ratio
    └── Strict LIMIT Enforcement        (Gemini / Local)            └── Aspect-based Sentiment
    │                               │                               │
    └───────────────────────────────┴───────────────────────────────┘
                                    │
                                    ▼
                    Evidence Fusion (`services/retrieval/evidence_fusion.py`)
                    ├── Unifies Graph Facts, Vector Similarities, and Review Snippets
                    └── Preserves Full Provenance on Every Retrieved Fact
                                    │
                                    ▼
                    Context Construction (`services/retrieval/context_builder.py`)
                    ├── Enforces Token Budgets & Bounded Contexts
                    └── Injects Strict Anti-Hallucination Grounding Rules
                                    │
                                    ▼
                    LLM Provider Layer (`services/llm/`)
                    ├── Dynamic Provider: Google Gemini (`google.genai`) or Groq (`groq`)
                    └── Grounded Generator (`grounded_generator.py`)
                                    │
                                    ▼
                    Explainability Layer (`services/explainability/`)
                    ├── Graph Path Traversal Attribution
                    └── Distinguishes: [OBSERVED FACT] vs [VECTOR SIMILARITY] vs [RECOMMENDATION INFERENCE]
                                    │
                                    ▼
                    FastAPI REST Response (Structured JSON)
```

---

## 2. API Endpoints

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | System health, Neo4j connectivity, and active LLM provider |
| `POST` | `/api/search` | Structured & semantic product search with price/rating filters |
| `POST` | `/api/recommend` | Multi-dimensional explainable recommendations |
| `GET` | `/api/products/{id}` | Canonical product details with brand/category relationships |
| `GET` | `/api/products/{id}/reviews` | Review intelligence, rating distribution, and aspect sentiment |
| `POST` | `/api/compare` | Side-by-side comparison matrix and grounded trade-off analysis |
| `POST` | `/api/query` | End-to-end natural-language Graph-RAG retrieval and answer synthesis |

Interactive documentation is available at `/docs` (Swagger UI) and `/redoc`.

---

## 3. Cypher Safety & Security Controls

Every generated or executed Cypher query is strictly checked before database interaction:
- **Read-Only Enforcement**: Mutation keywords (`CREATE`, `MERGE`, `DELETE`, `DETACH`, `SET`, `REMOVE`, `DROP`, `ALTER`) are rejected with `CypherValidationError`.
- **Schema Allowlist**:
  - Allowed Nodes: `Product`, `User`, `Review`, `Brand`, `Category`.
  - Allowed Relationships: `WROTE`, `REVIEWS`, `PURCHASED`, `BRANDED_BY`, `BELONGS_TO`, `SUB_CATEGORY_OF`.
- **Forbidden Fabricated Edges**: Rejects `BOUGHT_TOGETHER`, `CO_PURCHASED`, `OWNS`, `PURCHASED_ON`, and materialized `SIMILAR_TO`.
- **Parameterization**: User values are bound as parameters (`$max_price`, `$category_name`), preventing Cypher injection.
- **LIMIT Enforcement**: Queries without a limit are automatically clamped to `settings.NEO4J_MAX_RESULTS` (default: 50).

---

## 4. Multi-Factor Recommendation Scoring

Recommendations are calculated across 6 normalized dimensions (weights sum to 1.0):

$$\text{Composite Score} = w_{\text{cat}} S_{\text{cat}} + w_{\text{rate}} S_{\text{rate}} + w_{\text{price}} S_{\text{price}} + w_{\text{brand}} S_{\text{brand}} + w_{\text{sem}} S_{\text{sem}} + w_{\text{overlap}} S_{\text{overlap}}$$

1. **Category Match ($w_1 = 0.20$)**: Taxonomy breadcrumb overlap.
2. **Rating Quality with Bayesian Shrinkage ($w_2 = 0.25$)**:
   $$R_{\text{adj}} = \frac{v \cdot R + m \cdot C}{v + m}$$
   where $C = 4.2$ (dataset mean), $m = 5$ (shrinkage prior), $v = \text{review count}$.
3. **Price / Budget Fit ($w_3 = 0.15$)**: Satisfaction of user price ceilings.
4. **Brand Reputation ($w_4 = 0.10$)**: Brand catalog presence and matching.
5. **Semantic Relevance ($w_5 = 0.15$)**: Vector ANN similarity against user intent.
6. **Shared Verified Purchaser Overlap ($w_6 = 0.15$)**:
   Traverses $(P_1)\leftarrow[:\text{PURCHASED}]-(U)-[:\text{PURCHASED}]\rightarrow(P_2)$.

---

## 5. Running the Backend

```bash
# Set up environment variables
cp .env.example .env

# Run FastAPI development server
uvicorn app.main:app --app-dir backend --reload --port 8000
```

---

## 6. Running Tests

```bash
# Run all 37 unit and integration tests
python -m pytest backend/tests/ -v
```
