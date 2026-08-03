"""Endpointy listy i szczegółów faktur."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.schemas.invoices import InvoiceDetail, InvoiceListItem
from app.services.invoices import InvoiceNotFoundError, InvoiceService

router = APIRouter(prefix="/invoices", tags=["Faktury"])


def _invoice_service(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> InvoiceService:
    return InvoiceService(session, tenant.tenant_id)


@router.get("", response_model=list[InvoiceListItem])
async def list_invoices(
    role: str | None = Query(
        default=None,
        description="Filtr: cost (kosztowe) lub sales (sprzedaż)",
        pattern="^(cost|sales)$",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    date_from: date | None = Query(default=None, description="Początek zakresu (P_1)"),
    date_to: date | None = Query(default=None, description="Koniec zakresu (P_1)"),
    service: InvoiceService = Depends(_invoice_service),
) -> list[InvoiceListItem]:
    return await service.list_invoices(
        role=role,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(
    invoice_id: UUID,
    _: TenantContext = Depends(get_current_tenant),
    service: InvoiceService = Depends(_invoice_service),
) -> InvoiceDetail:
    try:
        return await service.get_invoice(invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faktura nie istnieje",
        ) from exc
