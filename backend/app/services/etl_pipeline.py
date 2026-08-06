"""
Potok ETL: XML FA(3) → kategoryzacja AI (P_7) → PostgreSQL (RLS).

Do modelu AI trafia wyłącznie product_name z pola P_7.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models import Invoice, InvoiceLine
from app.database.session import async_session_factory, set_tenant_context
from app.services.ai.categorizer import ProductCategorizer
from app.services.ai.exceptions import AICategorizationError
from app.services.invoice_roles import resolve_contractor_name, resolve_contractor_nip
from app.services.invoice_primary_category import update_invoice_primary_category
from app.services.tenant_categories import resolve_tenant_categories
from app.services.xml.fa3_parser import Fa3XmlParserError, parse_fa3_xml
from app.services.xml.models import Fa3InvoiceLine

logger = logging.getLogger(__name__)


@dataclass
class EtlProcessResult:
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    lines_processed: int
    categories_used: list[str]


class EtlPipelineError(Exception):
    """Błąd przetwarzania potoku ETL."""


class InvoiceEtlPipeline:
    """Orkiestruje parsowanie XML, kategoryzację AI i zapis do invoice_lines."""

    def __init__(self, categorizer: ProductCategorizer | None = None):
        self._categorizer = categorizer or ProductCategorizer()

    async def process_invoice_xml(
        self,
        tenant_id: uuid.UUID,
        xml_content: bytes | str,
        *,
        ksef_number: str | None = None,
        invoice_role: str = "cost",
        session: AsyncSession | None = None,
    ) -> EtlProcessResult:
        """
        Przetwarza pojedynczy dokument FA(3) dla tenanta.

        Gdy session=None, otwiera własną transakcję z SET LOCAL app.current_tenant.
        """
        if session is not None:
            return await self._process_with_session(
                session,
                tenant_id,
                xml_content,
                ksef_number=ksef_number,
                invoice_role=invoice_role,
            )

        async with async_session_factory() as owned_session:
            try:
                await owned_session.begin()
                await set_tenant_context(owned_session, tenant_id)
                result = await self._process_with_session(
                    owned_session,
                    tenant_id,
                    xml_content,
                    ksef_number=ksef_number,
                    invoice_role=invoice_role,
                )
                await owned_session.commit()
                return result
            except Exception:
                await owned_session.rollback()
                raise

    async def _process_with_session(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        xml_content: bytes | str,
        *,
        ksef_number: str | None = None,
        invoice_role: str = "cost",
    ) -> EtlProcessResult:
        try:
            parsed = parse_fa3_xml(xml_content)
        except Fa3XmlParserError as exc:
            raise EtlPipelineError(f"Błąd parsowania XML: {exc}") from exc

        allowed_categories = await resolve_tenant_categories(session, tenant_id)
        contractor_name = resolve_contractor_name(
            invoice_role,
            parsed.header.seller_name,
            parsed.header.buyer_name,
        )

        contractor_nip = resolve_contractor_nip(
            invoice_role,
            parsed.header.seller_nip,
            parsed.header.buyer_nip,
        )

        if ksef_number:
            existing = (
                await session.execute(
                    select(Invoice).where(
                        Invoice.tenant_id == tenant_id,
                        Invoice.ksef_number == ksef_number,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                self._merge_invoice_header(existing, parsed, invoice_role, contractor_name)
                await session.flush()
                existing_line_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(InvoiceLine)
                        .where(InvoiceLine.invoice_id == existing.id)
                    )
                ).scalar_one()
                parsed_line_count = len(parsed.lines)
                if parsed_line_count != existing_line_count:
                    logger.info(
                        "Ponowne przetwarzanie faktury %s: %s linii XML vs %s w bazie",
                        ksef_number,
                        parsed_line_count,
                        existing_line_count,
                    )
                    line_entities = await self._build_classified_lines(
                        session,
                        tenant_id,
                        existing.id,
                        parsed.lines,
                        contractor_nip,
                        allowed_categories,
                    )
                    await session.execute(
                        delete(InvoiceLine).where(
                            InvoiceLine.invoice_id == existing.id,
                            InvoiceLine.tenant_id == tenant_id,
                        )
                    )
                    for entity in line_entities:
                        session.add(entity)
                    update_invoice_primary_category(existing, line_entities)
                    await session.flush()
                    return EtlProcessResult(
                        tenant_id=tenant_id,
                        invoice_id=existing.id,
                        lines_processed=len(line_entities),
                        categories_used=allowed_categories,
                    )
                return EtlProcessResult(
                    tenant_id=tenant_id,
                    invoice_id=existing.id,
                    lines_processed=existing_line_count,
                    categories_used=allowed_categories,
                )

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            ksef_number=ksef_number,
            invoice_number=parsed.header.invoice_number,
            issue_date=parsed.header.issue_date,
            sale_date=parsed.header.sale_date,
            currency_code=parsed.header.currency_code,
            seller_nip=parsed.header.seller_nip,
            buyer_nip=parsed.header.buyer_nip,
            invoice_role=invoice_role,
            contractor_name=contractor_name,
            total_net=parsed.header.total_net,
            total_vat=parsed.header.total_vat,
            total_gross=parsed.header.total_gross,
        )
        session.add(invoice)
        await session.flush()

        line_entities = await self._build_classified_lines(
            session,
            tenant_id,
            invoice.id,
            parsed.lines,
            contractor_nip,
            allowed_categories,
        )
        for entity in line_entities:
            session.add(entity)

        update_invoice_primary_category(invoice, line_entities)
        await session.flush()
        return EtlProcessResult(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            lines_processed=len(parsed.lines),
            categories_used=allowed_categories,
        )

    @staticmethod
    def _merge_invoice_header(
        invoice: Invoice,
        parsed,
        invoice_role: str,
        contractor_name: str | None,
    ) -> None:
        if invoice.invoice_role != invoice_role:
            invoice.invoice_role = invoice_role
        if contractor_name and not invoice.contractor_name:
            invoice.contractor_name = contractor_name
        if parsed.header.total_net is not None and invoice.total_net is None:
            invoice.total_net = parsed.header.total_net
        if parsed.header.total_vat is not None and invoice.total_vat is None:
            invoice.total_vat = parsed.header.total_vat
        if parsed.header.total_gross is not None and invoice.total_gross is None:
            invoice.total_gross = parsed.header.total_gross

    async def _build_classified_lines(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        lines: list[Fa3InvoiceLine],
        contractor_nip: str,
        allowed_categories: list[str],
    ) -> list[InvoiceLine]:
        concurrency = max(1, get_settings().etl_classification_concurrency)
        semaphore = asyncio.Semaphore(concurrency)

        async def classify_one(line: Fa3InvoiceLine):
            async with semaphore:
                classification = await self._classify_line(
                    session,
                    tenant_id,
                    contractor_nip,
                    line.product_name,
                    allowed_categories,
                )
                return line, classification

        results = await asyncio.gather(*(classify_one(line) for line in lines))

        entities: list[InvoiceLine] = []
        for line, classification in results:
            entities.append(
                InvoiceLine(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    invoice_id=invoice_id,
                    line_number=line.line_number,
                    product_name=line.product_name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_net_value=line.line_net_value,
                    ai_category_main=classification.kategoria_glowna,
                    ai_category_sub=classification.kategoria_podrzedna,
                    ai_confidence=classification.pewnosc_klasyfikacji,
                    category_source=classification.source,
                )
            )
        return entities

    async def _classify_line(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        contractor_nip: str,
        product_name: str,
        allowed_categories: list[str],
    ):
        timeout = get_settings().ollama_timeout_sec
        try:
            return await asyncio.wait_for(
                self._categorizer.classify_product_name(
                    product_name,
                    allowed_categories=allowed_categories,
                    session=session,
                    tenant_id=tenant_id,
                    contractor_nip=contractor_nip,
                ),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, AICategorizationError) as exc:
            logger.warning(
                "Kategoryzacja AI pominięta dla %r (timeout=%ss): %s",
                product_name,
                timeout,
                exc,
            )
            return self._fallback_classification(allowed_categories)

    @staticmethod
    def _fallback_classification(_allowed_categories: list[str]):
        from app.services.ai.classification_result import ClassificationResult

        return ClassificationResult(
            kategoria_glowna=None,
            kategoria_podrzedna=None,
            pewnosc_klasyfikacji=0,
            source="fallback",
        )
