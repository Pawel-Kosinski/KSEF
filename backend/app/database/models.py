import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    """Dzierżawca platformy SaaS (firma MŚP)."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    nip: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    encrypted_ksef_token: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="Token autoryzacyjny KSeF (zaszyfrowany Fernet)",
    )
    ksef_hwm_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="High Water Mark – ostatnia potwierdzona data PermanentStorage",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    invoices: Mapped[list["Invoice"]] = relationship(back_populates="tenant")
    categories: Mapped[list["TenantCategory"]] = relationship(back_populates="tenant")
    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(Base):
    """Konto użytkownika powiązane z tenantem (SaaS)."""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_tenant_id", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")


class TenantCategory(Base):
    """Drzewo kategorii kosztowych definiowane per tenant (SaaS)."""

    __tablename__ = "tenant_categories"
    __table_args__ = (
        Index("idx_tenant_categories_tenant_name", "tenant_id", "name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="categories")


class Invoice(Base):
    """Nagłówek faktury FA(3) – metadane dokumentu."""

    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_tenant_role", "tenant_id", "invoice_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ksef_number: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, comment="P_2")
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, comment="P_1")
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="P_6")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    seller_nip: Mapped[str] = mapped_column(String(10), nullable=False)
    buyer_nip: Mapped[str] = mapped_column(String(10), nullable=False)
    invoice_role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="cost",
        server_default="cost",
        comment="cost = faktura kosztowa (nabywca), sales = sprzedaż (sprzedawca)",
    )
    contractor_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nazwa kontrahenta (sprzedawca dla kosztów, nabywca dla sprzedaży)",
    )
    total_net: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        comment="Suma netto z nagłówka FA (P_13_*)",
    )
    total_vat: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        comment="Suma VAT z nagłówka FA (P_14_*)",
    )
    total_gross: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        comment="Kwota brutto / należność ogółem (P_15)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="invoices")
    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice")


class InvoiceLine(Base):
    """
    Pojedynczy wiersz faktury FA(3) – //tns:Fa/tns:FaWiersz.

    Pola mapowane ze schematu:
    - P_7  → product_name
    - P_8B → quantity
    - P_9A → unit_price (netto)
    - P_11 → line_net_value
  """

    __tablename__ = "invoice_lines"
    __table_args__ = (
        Index("idx_lines_tenant_product", "tenant_id", "product_name"),
        Index("idx_lines_tenant_invoice", "tenant_id", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    product_name: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="P_7 – nazwa towaru/usługi"
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="P_8B – ilość"
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="P_9A – cena jednostkowa netto"
    )
    line_net_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, comment="P_11 – wartość netto wiersza"
    )

    ai_category_main: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_category_sub: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")
