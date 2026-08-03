"""Endpoint synchronizacji paczek faktur z KSeF na żądanie."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.schemas.ksef import KsefSyncRequest, KsefSyncResponse
from app.services.ksef.exceptions import (
    KsefApiError,
    KsefAuthError,
    KsefSyncError,
    KsefSyncValidationError,
)
from app.services.ksef.sync_service import KsefSyncService

router = APIRouter(prefix="/ksef", tags=["KSeF"])


@router.post("/sync", response_model=KsefSyncResponse)
async def sync_ksef_invoices(
    body: KsefSyncRequest,
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> KsefSyncResponse:
    """
    Ręczna synchronizacja faktur kosztowych z KSeF dla wybranego zakresu dat.

    Wymaga wcześniejszej konfiguracji kategorii kosztowych (tenant_categories).
    Filtry KSeF: subjectType=Subject2 (nabywca), dateType=Issue.
    """
    service = KsefSyncService()
    try:
        result = await service.sync_invoices(
            session,
            tenant.tenant_id,
            body.date_from,
            body.date_to,
            subject_type=body.subject_type,
        )
    except KsefSyncValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except KsefAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Błąd uwierzytelniania KSeF: {exc}",
        ) from exc
    except KsefApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Błąd API KSeF: {exc}",
        ) from exc
    except KsefSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return KsefSyncResponse(
        export_reference_number=result.export_reference_number,
        date_from=result.date_from,
        date_to=result.date_to,
        package_invoice_count=result.package_invoice_count,
        invoices_processed=result.invoices_processed,
        invoices_failed=result.invoices_failed,
        lines_processed=result.lines_processed,
        is_truncated=result.is_truncated,
        chunks_processed=result.chunks_processed,
        truncated_periods=result.truncated_periods,
        errors=result.errors,
    )
