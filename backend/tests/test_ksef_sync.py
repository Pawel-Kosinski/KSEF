"""Testy serwisu synchronizacji KSeF (bez wywołań sieciowych)."""

import io
import uuid
import zipfile
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Tenant, TenantCategory
from app.services.ksef.exceptions import KsefSyncValidationError
from app.services.ksef.models import (
    ExportInitResponse,
    ExportStatusResponse,
    InvoiceMetadataItem,
    InvoiceMetadataQueryResponse,
    InvoicePackage,
    InvoicePackagePart,
    OperationStatusInfo,
)
from app.services.ksef.sync_service import (
    KsefSyncService,
    extract_invoice_xml_from_zip,
    iter_date_chunks,
)


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _build_zip_with_xml(ksef_number: str, xml_content: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{ksef_number}.xml", xml_content)
        archive.writestr("_metadata.json", b"{}")
    return buffer.getvalue()


def test_extract_invoice_xml_from_zip():
    xml = b'<?xml version="1.0"?><Faktura/>'
    zip_bytes = _build_zip_with_xml("KSEF-123", xml)
    docs = extract_invoice_xml_from_zip(zip_bytes)
    assert docs == [("KSEF-123", xml)]


def test_iter_date_chunks_splits_range():
    chunks = iter_date_chunks(date(2026, 1, 1), date(2026, 1, 10), 7)
    assert chunks == [
        (date(2026, 1, 1), date(2026, 1, 7)),
        (date(2026, 1, 8), date(2026, 1, 10)),
    ]


def test_validate_date_range_rejects_too_long():
    with pytest.raises(KsefSyncValidationError, match="90"):
        KsefSyncService.validate_date_range(date(2026, 1, 1), date(2026, 5, 1))


@pytest.mark.asyncio
async def test_ensure_tenant_has_categories_raises_when_empty(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1111111111"))
    await db_session.commit()

    service = KsefSyncService()
    with pytest.raises(KsefSyncValidationError, match="kategorie kosztowe"):
        await service.ensure_tenant_has_categories(db_session, tenant_id)


@pytest.mark.asyncio
async def test_sync_invoices_processes_xml_from_mocked_export(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(
        Tenant(
            id=tenant_id,
            name="Sync Test",
            nip="9998887776",
            encrypted_ksef_token="encrypted-test-token",
        )
    )
    db_session.add(
        TenantCategory(tenant_id=tenant_id, name="Materiały i Surowce", sort_order=1)
    )
    await db_session.commit()

    fixture_path = __file__.replace("test_ksef_sync.py", "fixtures/sample_fa3_invoice.xml")
    with open(fixture_path, "rb") as fh:
        sample_xml = fh.read()

    zip_plain = _build_zip_with_xml("KSEF-SYNC-001", sample_xml)

    from app.services.ksef.crypto import (
        ExportEncryptionMaterial,
        generate_initialization_vector,
        generate_symmetric_key,
    )
    from cryptography.hazmat.primitives import padding as sym_padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    key = generate_symmetric_key()
    iv = generate_initialization_vector()
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(zip_plain) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted_zip = encryptor.update(padded) + encryptor.finalize()

    mock_client = MagicMock()
    mock_client.query_invoice_metadata = AsyncMock(
        return_value=InvoiceMetadataQueryResponse(
            has_more=False,
            is_truncated=False,
            invoices=[InvoiceMetadataItem(ksef_number="KSEF-SYNC-001")],
        )
    )
    mock_client.download_invoice_xml = AsyncMock(return_value=sample_xml)
    mock_client.get_public_key_certificates = AsyncMock(return_value=[])
    mock_client.start_invoice_export = AsyncMock(
        return_value=ExportInitResponse(reference_number="EXP-REF-1")
    )
    mock_client.get_export_status = AsyncMock(
        return_value=ExportStatusResponse(
            status=OperationStatusInfo(code=200, description="OK"),
            package=InvoicePackage(
                invoice_count=1,
                size=len(encrypted_zip),
                is_truncated=False,
                parts=[
                    InvoicePackagePart(
                        ordinal_number=1,
                        part_name="part1.zip.aes",
                        method="GET",
                        url="https://example.test/part1",
                        part_size=len(zip_plain),
                        part_hash="hash",
                        encrypted_part_size=len(encrypted_zip),
                        encrypted_part_hash="ehash",
                        expiration_date="2026-12-31T00:00:00+00:00",
                    )
                ],
            ),
        )
    )
    mock_client.download_export_part = AsyncMock(return_value=encrypted_zip)

    mock_auth = MagicMock()
    mock_auth.authenticate_with_ksef_token = AsyncMock(
        return_value=MagicMock(access_token="access-token")
    )

    mock_categorizer = MagicMock()
    from app.services.ai.classification_result import ClassificationResult

    mock_categorizer.classify_product_name = AsyncMock(
        side_effect=[
            ClassificationResult(
                kategoria_glowna="Materiały i Surowce",
                kategoria_podrzedna="test",
                pewnosc_klasyfikacji=90,
                source="ai",
            ),
            ClassificationResult(
                kategoria_glowna="Paliwa i Transport",
                kategoria_podrzedna="test",
                pewnosc_klasyfikacji=90,
                source="ai",
            ),
        ]
    )

    from app.services.etl_pipeline import InvoiceEtlPipeline

    service = KsefSyncService(
        client=mock_client,
        auth_service=mock_auth,
        etl_pipeline=InvoiceEtlPipeline(categorizer=mock_categorizer),
    )
    service._resolve_tenant_ksef_token = lambda _tenant: "test-ksef-token"

    # Podmień generowanie materiału szyfrującego stałym kluczem z testu
    from app.services.ksef import sync_service as sync_module

    original_build = sync_module.build_export_encryption_material

    sync_module.build_export_encryption_material = lambda _certs: ExportEncryptionMaterial(
        symmetric_key=key,
        iv=iv,
        encrypted_symmetric_key_b64="x",
        initialization_vector_b64="y",
        public_key_id="z",
    )

    try:
        result = await service.sync_invoices(
            tenant_id,
            date(2026, 1, 1),
            date(2026, 1, 31),
            session=db_session,
        )
    finally:
        sync_module.build_export_encryption_material = original_build

    assert result.export_reference_number == "metadata:Issue"
    assert result.invoices_processed == 1
    assert result.lines_processed == 2
    assert result.invoices_failed == 0
