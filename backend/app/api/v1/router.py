from fastapi import APIRouter

from app.api.v1.endpoints import invoices, ksef, stats

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(stats.router)
api_router.include_router(invoices.router)
api_router.include_router(ksef.router)
