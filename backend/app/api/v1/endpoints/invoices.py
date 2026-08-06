"""Endpointy listy i szczegółów faktur."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.schemas.invoices import (
    InvoiceCategoryUpdate,
    InvoiceCategoryUpdateResponse,
    InvoiceDetail,
    InvoiceLineCategoryUpdate,
    InvoiceLineCategoryUpdateResponse,
    InvoiceListItem,
)
from app.services.invoice_category import (
    InvalidCategoryError,
    InvoiceCategoryService,
    InvoiceNotFoundError as CategoryInvoiceNotFoundError,
    LineNotFoundError,
)
from app.services.invoice_roles import resolve_contractor_nip
from app.services.invoices import InvoiceNotFoundError, InvoiceService

router = APIRouter(prefix="/invoices", tags=["Faktury"])


def _invoice_service(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> InvoiceService:
    return InvoiceService(session, tenant.tenant_id)


def _invoice_category_service(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> InvoiceCategoryService:
    return InvoiceCategoryService(session, tenant.tenant_id)


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
    category: str | None = Query(
        default=None,
        description="Filtr: faktury z co najmniej jedną pozycją w danej kategorii",
    ),
    service: InvoiceService = Depends(_invoice_service),
) -> list[InvoiceListItem]:
    return await service.list_invoices(
        role=role,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        category=category,
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


@router.patch("/{invoice_id}/category", response_model=InvoiceCategoryUpdateResponse)
async def update_invoice_category(
    invoice_id: UUID,
    body: InvoiceCategoryUpdate,
    service: InvoiceCategoryService = Depends(_invoice_category_service),
) -> InvoiceCategoryUpdateResponse:
    try:
        invoice = await service.update_invoice_category(
            invoice_id,
            body.category_main,
            category_sub=body.category_sub,
        )
        return InvoiceCategoryUpdateResponse(
            id=invoice.id,
            primary_category_main=invoice.primary_category_main,
            primary_category_sub=invoice.primary_category_sub,
            primary_category_source=invoice.primary_category_source,
        )
    except CategoryInvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faktura nie istnieje",
        ) from exc
    except InvalidCategoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{invoice_id}/lines/{line_id}/category",
    response_model=InvoiceLineCategoryUpdateResponse,
)
async def update_invoice_line_category(
    invoice_id: UUID,
    line_id: UUID,
    body: InvoiceLineCategoryUpdate,
    service: InvoiceCategoryService = Depends(_invoice_category_service),
) -> InvoiceLineCategoryUpdateResponse:
    try:
        line, invoice = await service.update_line_category(
            invoice_id,
            line_id,
            body.category_main,
            category_sub=body.category_sub,
            learn_rule=body.learn_rule,
        )
        contractor_nip = None
        if body.learn_rule:
            contractor_nip = resolve_contractor_nip(
                invoice.invoice_role,
                invoice.seller_nip,
                invoice.buyer_nip,
            )
        return InvoiceLineCategoryUpdateResponse(
            id=line.id,
            line_number=line.line_number,
            ai_category_main=line.ai_category_main,
            ai_category_sub=line.ai_category_sub,
            ai_confidence=line.ai_confidence,
            category_source=line.category_source,
            invoice_primary_category_main=invoice.primary_category_main,
            invoice_primary_category_sub=invoice.primary_category_sub,
            invoice_primary_category_source=invoice.primary_category_source,
            rule_saved=body.learn_rule,
            contractor_nip=contractor_nip,
        )
    except CategoryInvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faktura nie istnieje",
        ) from exc
    except LineNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pozycja faktury nie istnieje",
        ) from exc
    except InvalidCategoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
