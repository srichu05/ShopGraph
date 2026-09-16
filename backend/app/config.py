"""
ShopGraph Backend Configuration
===============================
Environment-based settings for Neo4j, LLM providers (Gemini & Groq),
embeddings, retrieval boundaries, and recommendation scoring weights.
"""

from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "ShopGraph Intelligence Engine"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = ""  # Comma-separated list of allowed origins in production

    # Neo4j Graph Database
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_LIFETIME: int = 3600
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50
    NEO4J_QUERY_TIMEOUT_MS: int = 10000
    NEO4J_MAX_RESULTS: int = 50

    # LLM Provider Configuration (gemini or groq)
    LLM_PROVIDER: Literal["gemini", "groq"] = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 2048

    # Embedding Configuration
    EMBEDDING_PROVIDER: Literal["gemini", "local"] = "local"
    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
    EMBEDDING_DIMENSION: int = 768

    # Retrieval Safeguards
    DEFAULT_RETRIEVAL_LIMIT: int = 10
    MAX_RETRIEVAL_LIMIT: int = 50
    MAX_REVIEWS_PER_PRODUCT: int = 8
    RRF_K: int = 60  # Reciprocal Rank Fusion constant

    # Explainable Recommendation Scoring Weights (must sum to 1.0)
    REC_WEIGHT_CATEGORY: float = 0.20
    REC_WEIGHT_RATING: float = 0.25
    REC_WEIGHT_PRICE: float = 0.15
    REC_WEIGHT_BRAND: float = 0.10
    REC_WEIGHT_SEMANTIC: float = 0.15
    REC_WEIGHT_PURCHASER_OVERLAP: float = 0.15

    # Data paths (for offline metadata / catalog fallbacks)
    PROCESSED_DATA_DIR: str = str(ROOT_DIR / "data" / "processed")


# Singleton instance
settings = Settings()
