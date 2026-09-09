"""API package router registration."""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.api.products import router as products_router
from app.api.recommend import router as recommend_router
from app.api.compare import router as compare_router
from app.api.query import router as query_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(search_router)
api_router.include_router(products_router)
api_router.include_router(recommend_router)
api_router.include_router(compare_router)
api_router.include_router(query_router)

__all__ = ["api_router"]
