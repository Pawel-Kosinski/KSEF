from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.config import get_settings
from app.database.models import InvoiceLine
from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    description="MVP Wirtualny CFO – integracja KSeF API 2.0",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


class InvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    line_number: int
    product_name: str
    quantity: float
    unit_price: float
    line_net_value: float
    ai_category_main: str | None = None
    ai_category_sub: str | None = None
    ai_confidence: int | None = None


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/v1/invoice-lines", response_model=list[InvoiceLineRead])
async def list_invoice_lines(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
):
    """Lista wierszy faktur – filtrowana przez RLS na poziomie PostgreSQL."""
    result = await session.execute(
        select(InvoiceLine).order_by(InvoiceLine.created_at.desc()).limit(100)
    )
    return result.scalars().all()


@app.get("/api/v1/me")
async def get_me(tenant: TenantContext = Depends(get_current_tenant)):
    return {"tenant_id": str(tenant.tenant_id), "sub": tenant.sub}
