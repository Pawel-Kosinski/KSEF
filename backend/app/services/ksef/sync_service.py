"""Synchronizacja paczek faktur z KSeF na żądanie (POST /invoices/exports)."""

import asyncio
import io
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone, timedelta
from pathlib import PurePosixPath
from uuid import UUID
from zoneinfo import ZoneInfo

try:
    WARSAW_TZ = ZoneInfo("Europe/Warsaw")
except Exception:  # Windows bez pakietu tzdata
    WARSAW_TZ = timezone(timedelta(hours=1))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.models import Tenant
from app.services.etl_pipeline import EtlPipelineError, InvoiceEtlPipeline
from app.services.ksef.auth import KsefAuthService
from app.services.ksef.client import KsefClient
from app.services.ksef.crypto import (
    ExportEncryptionMaterial,
    build_export_encryption_material,
    decrypt_export_package_in_memory,
)
from app.services.ksef.exceptions import (
    KsefExportTimeoutError,
    KsefSyncError,
    KsefSyncValidationError,
)
from app.services.ksef.models import (
    ExportDateRange,
    ExportEncryptionInfo,
    ExportFilters,
    ExportStatusResponse,
    InvoiceExportRequest,
)
from app.services.invoice_roles import ksef_subject_to_role
from app.services.tenant_categories import fetch_active_category_names

logger = logging.getLogger(__name__)

MAX_SYNC_DATE_RANGE_DAYS = 90
DEFAULT_SYNC_CHUNK_DAYS = 7
MIN_SYNC_CHUNK_DAYS = 1


def iter_date_chunks(
    date_from: date,
    date_to: date,
    chunk_days: int,
) -> list[tuple[date, date]]:
    """Dzieli zakres na podokresy (włącznie z date_from i date_to)."""
    if chunk_days < 1:
        raise ValueError("chunk_days musi być >= 1")
    chunks: list[tuple[date, date]] = []
    current = date_from
    while current <= date_to:
        end = min(current + timedelta(days=chunk_days - 1), date_to)
        chunks.append((current, end))
        current = end + timedelta(days=1)
    return chunks


EXPORT_STATUS_IN_PROGRESS = 100
EXPORT_STATUS_SUCCESS = 200


@dataclass
class KsefSyncResult:
    export_reference_number: str
    date_from: date
    date_to: date
    invoices_processed: int = 0
    invoices_failed: int = 0
    lines_processed: int = 0
    package_invoice_count: int = 0
    is_truncated: bool = False
    chunks_processed: int = 0
    truncated_periods: int = 0
    errors: list[str] = field(default_factory=list)


def merge_sync_results(target: KsefSyncResult, source: KsefSyncResult) -> None:
    target.invoices_processed += source.invoices_processed
    target.invoices_failed += source.invoices_failed
    target.lines_processed += source.lines_processed
    target.package_invoice_count += source.package_invoice_count
    target.chunks_processed += source.chunks_processed
    target.truncated_periods += source.truncated_periods
    target.is_truncated = target.is_truncated or source.is_truncated
    target.errors.extend(source.errors)
    if source.export_reference_number:
        target.export_reference_number = source.export_reference_number


class KsefSyncService:
    """
    Koordynuje: auth → eksport → polling → pobranie → deszyfracja → ETL.

    Wymaga sesji DB z aktywnym RLS (SET LOCAL app.current_tenant).
  """

    def __init__(
        self,
        client: KsefClient | None = None,
        auth_service: KsefAuthService | None = None,
        etl_pipeline: InvoiceEtlPipeline | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._client = client or KsefClient(settings=self._settings)
        self._auth = auth_service or KsefAuthService(client=self._client, settings=self._settings)
        self._etl = etl_pipeline or InvoiceEtlPipeline()

    @staticmethod
    def validate_date_range(date_from: date, date_to: date) -> None:
        if date_to < date_from:
            raise KsefSyncValidationError("date_to nie może być wcześniejsza niż date_from")
        if (date_to - date_from).days > MAX_SYNC_DATE_RANGE_DAYS:
            raise KsefSyncValidationError(
                f"Zakres dat nie może przekraczać {MAX_SYNC_DATE_RANGE_DAYS} dni"
            )

    async def ensure_tenant_has_categories(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> list[str]:
        categories = await fetch_active_category_names(session, tenant_id)
        if not categories:
            raise KsefSyncValidationError(
                "Przed pobraniem faktur z KSeF należy zdefiniować kategorie kosztowe "
                "(tabela tenant_categories)."
            )
        return categories

    async def sync_invoices(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        date_from: date,
        date_to: date,
        subject_type: str = "Subject2",
    ) -> KsefSyncResult:
        self.validate_date_range(date_from, date_to)
        return await self._sync_with_truncation_handling(
            session,
            tenant_id,
            date_from,
            date_to,
            subject_type,
        )

    async def _sync_with_truncation_handling(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        date_from: date,
        date_to: date,
        subject_type: str,
    ) -> KsefSyncResult:
        result = await self._sync_single_export(
            session,
            tenant_id,
            date_from,
            date_to,
            subject_type,
        )
        result.chunks_processed = 1

        if not result.is_truncated:
            return result

        span_days = (date_to - date_from).days
        if span_days < 1:
            result.truncated_periods = 1
            result.errors.append(
                f"Paczka KSeF obcięta dla {date_from.isoformat()} — "
                "za dużo faktur w jednym dniu; zmniejsz zakres lub użyj HWM (worker)."
            )
            return result

        logger.warning(
            "Eksport KSeF obcięty dla %s–%s (%s), dzielę na dni",
            date_from,
            date_to,
            subject_type,
        )

        aggregated = KsefSyncResult(
            export_reference_number=result.export_reference_number,
            date_from=date_from,
            date_to=date_to,
        )

        for day_from, day_to in iter_date_chunks(date_from, date_to, MIN_SYNC_CHUNK_DAYS):
            day_result = await self._sync_single_export(
                session,
                tenant_id,
                day_from,
                day_to,
                subject_type,
            )
            day_result.chunks_processed = 1
            if day_result.is_truncated:
                day_result.truncated_periods = 1
                day_result.errors.append(
                    f"Paczka obcięta dla {day_from.isoformat()} — "
                    "za dużo faktur w jednym dniu."
                )
            merge_sync_results(aggregated, day_result)

        return aggregated

    async def _sync_single_export(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        date_from: date,
        date_to: date,
        subject_type: str = "Subject2",
    ) -> KsefSyncResult:
        await self.ensure_tenant_has_categories(session, tenant_id)
        invoice_role = ksef_subject_to_role(subject_type)

        tenant = await self._load_tenant(session, tenant_id)
        tokens = await self._auth.authenticate_with_ksef_token(nip=tenant.nip)

        certificates = await self._client.get_public_key_certificates()
        encryption_material = build_export_encryption_material(certificates)
        export_request = self._build_export_request(
            encryption_material, date_from, date_to, subject_type
        )

        init = await self._client.start_invoice_export(
            tokens.access_token,
            export_request,
        )
        export_ref = init.reference_number

        status = await self._wait_for_export_ready(export_ref, tokens.access_token)
        package = status.package
        if package is None:
            raise KsefSyncError("Eksport zakończony, ale brak danych paczki w odpowiedzi KSeF")

        result = KsefSyncResult(
            export_reference_number=export_ref,
            date_from=date_from,
            date_to=date_to,
            package_invoice_count=package.invoice_count,
            is_truncated=package.is_truncated,
        )

        if package.invoice_count == 0 or not package.parts:
            return result

        xml_documents: list[tuple[str, bytes]] = []
        for part in package.parts:
            encrypted = await self._client.download_export_part(part.url, part.method)
            zip_bytes = decrypt_export_package_in_memory(
                encrypted,
                encryption_material,
            )
            del encrypted
            part_xml = extract_invoice_xml_from_zip(zip_bytes)
            del zip_bytes
            xml_documents.extend(part_xml)

        for ksef_number, xml_bytes in xml_documents:
            try:
                etl_result = await self._etl.process_invoice_xml(
                    tenant_id,
                    xml_bytes,
                    ksef_number=ksef_number,
                    invoice_role=invoice_role,
                    session=session,
                )
                result.invoices_processed += 1
                result.lines_processed += etl_result.lines_processed
            except (EtlPipelineError, Exception) as exc:
                result.invoices_failed += 1
                message = f"{ksef_number}: {exc}"
                result.errors.append(message)
                logger.warning("ETL nieudany dla %s: %s", ksef_number, exc)

        return result

    async def _load_tenant(self, session: AsyncSession, tenant_id: UUID) -> Tenant:
        row = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = row.scalar_one_or_none()
        if tenant is None:
            raise KsefSyncError(f"Nie znaleziono tenanta: {tenant_id}")
        return tenant

    def _build_export_request(
        self,
        material: ExportEncryptionMaterial,
        date_from: date,
        date_to: date,
        subject_type: str = "Subject2",
    ) -> InvoiceExportRequest:
        start = datetime.combine(date_from, time.min, tzinfo=WARSAW_TZ)
        end = datetime.combine(date_to, time(23, 59, 59), tzinfo=WARSAW_TZ)
        return InvoiceExportRequest(
            encryption=ExportEncryptionInfo(
                encrypted_symmetric_key=material.encrypted_symmetric_key_b64,
                initialization_vector=material.initialization_vector_b64,
                public_key_id=material.public_key_id,
            ),
            filters=ExportFilters(
                subject_type=subject_type,
                date_range=ExportDateRange(
                    date_type="Issue",
                    from_=start.isoformat(),
                    to=end.isoformat(),
                ),
            ),
            only_metadata=False,
        )

    async def _wait_for_export_ready(
        self,
        reference_number: str,
        access_token: str,
    ) -> ExportStatusResponse:
        interval = self._settings.ksef_export_poll_interval_sec
        max_attempts = self._settings.ksef_export_poll_max_attempts

        for attempt in range(1, max_attempts + 1):
            status = await self._client.get_export_status(reference_number, access_token)
            code = status.status.code

            if code == EXPORT_STATUS_SUCCESS:
                return status
            if code != EXPORT_STATUS_IN_PROGRESS:
                details = status.status.details or []
                detail_text = "; ".join(details) if details else status.status.description
                raise KsefSyncError(
                    f"Eksport KSeF nieudany: [{code}] {status.status.description}. {detail_text}"
                )

            if attempt < max_attempts:
                await asyncio.sleep(interval)

        raise KsefExportTimeoutError(
            f"Przekroczono czas oczekiwania na eksport ({max_attempts} prób)"
        )


def extract_invoice_xml_from_zip(zip_bytes: bytes) -> list[tuple[str, bytes]]:
    """
    Wyciąga pliki {ksefNumber}.xml z odszyfrowanej paczki ZIP w RAM (io.BytesIO).

    Pomija _metadata.json i inne pliki niebędące fakturami XML.
    Żadne pliki nie są zapisywane na dysk serwera.
    """
    documents: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            if name.startswith("__MACOSX/"):
                continue
            path = PurePosixPath(name)
            if path.name.startswith("_") or path.suffix.lower() != ".xml":
                continue
            ksef_number = path.stem
            if not ksef_number:
                continue
            documents.append((ksef_number, archive.read(name)))
    return documents
