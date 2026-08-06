"""Uruchamianie synchronizacji KSeF w tle z persystencją statusu."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import KsefSyncJob
from app.database.session import async_session_factory, set_tenant_context
from app.schemas.ksef import KsefSyncResponse
from app.services.ksef.exceptions import (
    KsefApiError,
    KsefAuthError,
    KsefSyncError,
    KsefSyncValidationError,
)
from app.services.ksef.sync_service import KsefSyncService

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()
_job_tasks: dict[uuid.UUID, asyncio.Task] = {}


class SyncJobNotFoundError(Exception):
    pass


class SyncJobNotCancellableError(Exception):
    pass


def _serialize_result(result) -> str:
    if is_dataclass(result):
        payload = asdict(result)
        for key, value in payload.items():
            if isinstance(value, date):
                payload[key] = value.isoformat()
        return json.dumps(payload)
    return json.dumps(result)


class KsefSyncJobService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self._session = session
        self._tenant_id = tenant_id

    async def create_period_sync_job(
        self,
        date_from: date,
        date_to: date,
    ) -> KsefSyncJob:
        job = KsefSyncJob(
            id=uuid.uuid4(),
            tenant_id=self._tenant_id,
            status="pending",
            date_from=date_from,
            date_to=date_to,
            progress_message="Oczekiwanie na start…",
        )
        self._session.add(job)
        await self._session.flush()
        self._schedule_job(job.id, self._tenant_id)
        return job

    async def get_job(self, job_id: uuid.UUID) -> KsefSyncJob | None:
        result = await self._session.execute(
            select(KsefSyncJob).where(
                KsefSyncJob.id == job_id,
                KsefSyncJob.tenant_id == self._tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def cancel_job(self, job_id: uuid.UUID) -> KsefSyncJob:
        job = await self.get_job(job_id)
        if job is None:
            raise SyncJobNotFoundError(str(job_id))
        if job.status in ("completed", "failed", "cancelled"):
            raise SyncJobNotCancellableError(job.status)

        now = datetime.now(timezone.utc)
        job.status = "cancelled"
        job.progress_message = "Przerwano przez użytkownika"
        job.error_message = "Synchronizacja przerwana przez użytkownika"
        job.completed_at = now
        job.updated_at = now
        await self._session.flush()

        task = _job_tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()

        return job

    @staticmethod
    def _schedule_job(job_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        task = asyncio.create_task(_run_sync_job(job_id, tenant_id))
        _background_tasks.add(task)
        _job_tasks[job_id] = task

        def _cleanup(done_task: asyncio.Task) -> None:
            _background_tasks.discard(done_task)
            _job_tasks.pop(job_id, None)

        task.add_done_callback(_cleanup)


async def _is_job_cancelled(job_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
    async with async_session_factory() as session:
        await session.begin()
        await set_tenant_context(session, tenant_id)
        job = (
            await session.execute(
                select(KsefSyncJob.status).where(
                    KsefSyncJob.id == job_id,
                    KsefSyncJob.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        await session.commit()
        return job == "cancelled"


async def _run_sync_job(job_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    date_from: date
    date_to: date

    async with async_session_factory() as session:
        try:
            await session.begin()
            await set_tenant_context(session, tenant_id)
            job = (
                await session.execute(
                    select(KsefSyncJob).where(
                        KsefSyncJob.id == job_id,
                        KsefSyncJob.tenant_id == tenant_id,
                    )
                )
            ).scalar_one()

            date_from = job.date_from
            date_to = job.date_to
            job.status = "running"
            job.progress_message = "Synchronizacja z KSeF…"
            job.updated_at = datetime.now(timezone.utc)
            await session.flush()
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Nie udało się oznaczyć zadania sync %s jako running", job_id)
            return

    if await _is_job_cancelled(job_id, tenant_id):
        return

    try:
        service = KsefSyncService()
        result = await service.sync_period(tenant_id, date_from, date_to)
        if await _is_job_cancelled(job_id, tenant_id):
            return
        await _finalize_job(job_id, tenant_id, status="completed", result=result)
    except asyncio.CancelledError:
        logger.info("Zadanie sync %s anulowane", job_id)
        raise
    except (KsefSyncValidationError, KsefAuthError, KsefApiError, KsefSyncError) as exc:
        await _finalize_job(job_id, tenant_id, status="failed", error=str(exc))
    except Exception as exc:
        logger.exception("Nieoczekiwany błąd sync job %s", job_id)
        await _finalize_job(job_id, tenant_id, status="failed", error=str(exc))


async def _finalize_job(
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    *,
    status: str,
    result=None,
    error: str | None = None,
) -> None:
    async with async_session_factory() as session:
        await session.begin()
        await set_tenant_context(session, tenant_id)
        job = (
            await session.execute(
                select(KsefSyncJob).where(
                    KsefSyncJob.id == job_id,
                    KsefSyncJob.tenant_id == tenant_id,
                )
            )
        ).scalar_one()
        if job.status in ("completed", "failed", "cancelled"):
            return
        job.status = status
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = job.completed_at
        if result is not None:
            job.result_json = _serialize_result(result)
            job.progress_message = "Zakończono"
        if error:
            job.error_message = error
            job.progress_message = "Błąd synchronizacji"
        if status == "cancelled":
            job.progress_message = "Przerwano przez użytkownika"
        await session.commit()


def job_to_response(job: KsefSyncJob) -> dict:
    result: KsefSyncResponse | None = None
    if job.result_json:
        data = json.loads(job.result_json)
        result = KsefSyncResponse(**data)

    return {
        "id": job.id,
        "status": job.status,
        "date_from": job.date_from,
        "date_to": job.date_to,
        "progress_message": job.progress_message,
        "error_message": job.error_message,
        "result": result,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }
