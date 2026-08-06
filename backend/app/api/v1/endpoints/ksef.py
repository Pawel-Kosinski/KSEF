"""Endpoint synchronizacji paczek faktur z KSeF na żądanie."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.schemas.ksef import (
    KsefSyncJobCreatedResponse,
    KsefSyncJobResponse,
    KsefSyncPeriodRequest,
    KsefSyncRequest,
    KsefSyncResponse,
)
from app.services.ksef.exceptions import (
    KsefApiError,
    KsefAuthError,
    KsefSyncError,
    KsefSyncValidationError,
)
from app.services.ksef.sync_job_service import (
    KsefSyncJobService,
    SyncJobNotCancellableError,
    SyncJobNotFoundError,
    job_to_response,
)
from app.services.ksef.sync_service import KsefSyncService

router = APIRouter(prefix="/ksef", tags=["KSeF"])


def _sync_job_service(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> KsefSyncJobService:
    return KsefSyncJobService(session, tenant.tenant_id)


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


@router.post(
    "/sync-period",
    response_model=KsefSyncJobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_ksef_period_async(
    body: KsefSyncPeriodRequest,
    service: KsefSyncJobService = Depends(_sync_job_service),
    session: AsyncSession = Depends(get_rls_session),
) -> KsefSyncJobCreatedResponse:
    """Uruchamia synchronizację kosztów i sprzedaży w tle (nie blokuje HTTP)."""
    job = await service.create_period_sync_job(body.date_from, body.date_to)
    await session.commit()
    return KsefSyncJobCreatedResponse(job_id=job.id, status=job.status)


@router.get("/sync-jobs/{job_id}", response_model=KsefSyncJobResponse)
async def get_ksef_sync_job(
    job_id: UUID,
    service: KsefSyncJobService = Depends(_sync_job_service),
) -> KsefSyncJobResponse:
    job = await service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zadanie synchronizacji nie istnieje",
        )
    return KsefSyncJobResponse(**job_to_response(job))


@router.post("/sync-jobs/{job_id}/cancel", response_model=KsefSyncJobResponse)
async def cancel_ksef_sync_job(
    job_id: UUID,
    service: KsefSyncJobService = Depends(_sync_job_service),
    session: AsyncSession = Depends(get_rls_session),
) -> KsefSyncJobResponse:
    try:
        job = await service.cancel_job(job_id)
        await session.commit()
        return KsefSyncJobResponse(**job_to_response(job))
    except SyncJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zadanie synchronizacji nie istnieje",
        ) from exc
    except SyncJobNotCancellableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nie można przerwać zadania w stanie: {exc.args[0]}",
        ) from exc


@router.post("/sync-period/legacy", response_model=KsefSyncResponse)
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
