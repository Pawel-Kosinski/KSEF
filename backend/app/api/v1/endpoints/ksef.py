"""Endpoint synchronizacji paczek faktur z KSeF na żądanie."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.tenant import TenantContext, get_current_tenant
from app.schemas.ksef import KsefSyncPeriodRequest, KsefSyncRequest, KsefSyncResponse
from app.services.ksef.exceptions import (
    KsefApiError,
    KsefAuthError,
    KsefSyncError,
    KsefSyncValidationError,
)
from app.services.ksef.sync_service import KsefSyncService

router = APIRouter(prefix="/ksef", tags=["KSeF"])


def _sync_response(result) -> KsefSyncResponse:
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


@router.post("/sync-period", response_model=KsefSyncResponse)
async def sync_ksef_period(
    body: KsefSyncPeriodRequest,
    tenant: TenantContext = Depends(get_current_tenant),
) -> KsefSyncResponse:
    """Synchronizacja kosztów i sprzedaży jednym tokenem KSeF (szybsza ścieżka)."""
    service = KsefSyncService()
    try:
        result = await service.sync_period(
            tenant.tenant_id,
            body.date_from,
            body.date_to,
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

    return _sync_response(result)


@router.post("/sync", response_model=KsefSyncResponse)
async def sync_ksef_invoices(
    body: KsefSyncRequest,
    tenant: TenantContext = Depends(get_current_tenant),
) -> KsefSyncResponse:
    """
    Ręczna synchronizacja faktur kosztowych z KSeF dla wybranego zakresu dat.

    Wymaga wcześniejszej konfiguracji kategorii kosztowych (tenant_categories).
    Filtry KSeF: subjectType=Subject2 (nabywca), dateType=Issue.
    """
    service = KsefSyncService()
    try:
        result = await service.sync_invoices(
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

    return _sync_response(result)
