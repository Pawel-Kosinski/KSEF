from fastapi import APIRouter

from app.api.v1.endpoints import auth, categories, invoices, ksef, settings, stats

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(stats.router)
api_router.include_router(categories.router)
api_router.include_router(invoices.router)
api_router.include_router(ksef.router)
