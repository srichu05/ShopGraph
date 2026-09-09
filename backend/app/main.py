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

# CORS Middleware (supports local development and Vercel deployments)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    """Catches unhandled runtime service errors (e.g. database offline)."""
    logger.error("Runtime error handling request %s: %s", request.url, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "Service Unavailable", "detail": str(exc)},
    )


# Register API routers under /api and root health check
app.include_router(api_router, prefix=settings.API_PREFIX)
# Also register health at root /health for simple monitoring
from app.api.health import router as root_health
app.include_router(root_health)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
