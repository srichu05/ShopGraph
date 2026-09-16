"""
ShopGraph FastAPI Application Entrypoint
========================================
Main application module setting up CORS, lifecycle events,
error handlers, and REST API routing.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.neo4j.connection import neo4j_client
from app.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shopgraph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    # Attempt initial Neo4j connection
    is_connected = neo4j_client.connect()
    if is_connected:
        logger.info("Neo4j database connection established successfully.")
    else:
        logger.warning(
            "Neo4j is currently offline. API will start in degraded mode. "
            "Offline routes and mocks are available."
        )

    yield

    logger.info("Shutting down %s...", settings.APP_NAME)
    neo4j_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Explainable Graph-RAG E-Commerce Intelligence Platform built on Neo4j, Gemini/Groq, and Cypher.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
# In development: allows localhost/127.0.0.1 on ports 3000/5173/8000
# In production: strictly uses explicitly configured CORS_ORIGINS without regex wildcards
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

if settings.APP_ENV == "production":
    prod_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=prod_origins,
        allow_origin_regex=None,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    """Catches unhandled runtime service errors (e.g. database offline)."""
    logger.error("Runtime error handling request %s: %s", request.url, exc)
    detail_msg = "Internal service error occurred." if settings.APP_ENV == "production" else str(exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "Service Unavailable", "detail": detail_msg},
    )


# Register API routers under /api and root health check
app.include_router(api_router, prefix=settings.API_PREFIX)
# Also register health at root /health for simple monitoring
from app.api.health import router as root_health
app.include_router(root_health)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
