"""Endpoint listy kategorii kosztowych tenanta."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.schemas.invoices import CategoryListResponse
from app.services.tenant_categories import resolve_tenant_categories

router = APIRouter(prefix="/categories", tags=["Kategorie"])


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> CategoryListResponse:
    categories = await resolve_tenant_categories(session, tenant.tenant_id)
    return CategoryListResponse(categories=categories)
