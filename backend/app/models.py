import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any, Optional

from sqlalchemy import JSON, Date, DateTime, Enum, Float, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

Money = Numeric(14, 2, asdecimal=False)
Qty = Numeric(14, 3, asdecimal=False)
TS = DateTime(timezone=True)


def utcnow() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class InvoiceStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    MATCHING = "MATCHING"
    MATCHED = "MATCHED"          # passed 3-way match automatically
    DISCREPANCY = "DISCREPANCY"  # needs human review
    ON_HOLD = "ON_HOLD"          # waiting on something (goods receipt, supplier)
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


class MatchResult(str, enum.Enum):
    FULL_MATCH = "FULL_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NO_MATCH = "NO_MATCH"
    PENDING = "PENDING"


class InvoiceType(str, enum.Enum):
    STANDARD = "STANDARD"
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"
    PRO_FORMA = "PRO_FORMA"


class Role(str, enum.Enum):
    VIEWER = "viewer"
    AP_CLERK = "ap_clerk"
    APPROVER = "approver"
    ADMIN = "admin"


# Statuses that still count as "live" for duplicate detection
LIVE_STATUSES = ("RECEIVED", "EXTRACTING", "EXTRACTED", "VALIDATING", "VALIDATED", "MATCHING",
                 "MATCHED", "DISCREPANCY", "ON_HOLD", "APPROVED")
REVIEW_STATUSES = ("DISCREPANCY", "ON_HOLD")
_LIVE_WHERE = ("status NOT IN ('DUPLICATE','FAILED','REJECTED') AND vendor_key IS NOT NULL "
               "AND invoice_number IS NOT NULL")

Json = Optional[Any]


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    invoice_number: Mapped[Optional[str]] = mapped_column(String, index=True)
    vendor_name: Mapped[Optional[str]] = mapped_column(String)
    vendor_id: Mapped[Optional[str]] = mapped_column(String, index=True)       # ERP supplier id when resolved
    vendor_key: Mapped[Optional[str]] = mapped_column(String, index=True)      # id or normalised name (duplicates)
    vendor_tax_id: Mapped[Optional[str]] = mapped_column(String)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    subtotal: Mapped[Optional[float]] = mapped_column(Money)
    total_amount: Mapped[Optional[float]] = mapped_column(Money, default=0.0)
    tax_amount: Mapped[Optional[float]] = mapped_column(Money, default=0.0)
    currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD")
    po_reference: Mapped[Optional[str]] = mapped_column(String, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.RECEIVED, index=True,
                                                  nullable=True)
    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), default=InvoiceType.STANDARD, nullable=True)
    match_result: Mapped[MatchResult] = mapped_column(Enum(MatchResult), default=MatchResult.PENDING, index=True,
                                                      nullable=True)
    match_score: Mapped[Optional[float]] = mapped_column(Float)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    extracted_data: Mapped[Json] = mapped_column(JSON)
    validation: Mapped[Json] = mapped_column(JSON)          # {"errors": [...], "warnings": [...]}
    discrepancies: Mapped[Json] = mapped_column(JSON)
    match_checks: Mapped[Json] = mapped_column(JSON)        # per-check results from the matching engine
    match_snapshot: Mapped[Json] = mapped_column(JSON)      # PO + GRN data as seen at match time
    duplicate_of: Mapped[Optional[str]] = mapped_column(String, ForeignKey("invoices.id"))
    source_email: Mapped[Optional[str]] = mapped_column(String)
    original_filename: Mapped[Optional[str]] = mapped_column(String)
    file_path: Mapped[Optional[str]] = mapped_column(String)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    processing_time: Mapped[Optional[float]] = mapped_column(Float)
    error: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(TS)
    review_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow, onupdate=utcnow)

    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceLineItem.line_no")

    __table_args__ = (
        # One live invoice per (vendor, invoice number). Duplicates are stored with status DUPLICATE.
        Index("uq_invoice_vendor_number_live", "vendor_key", "invoice_number", unique=True,
              postgresql_where=text(_LIVE_WHERE), sqlite_where=text(_LIVE_WHERE)),
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    invoice_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("invoices.id"), index=True)
    line_no: Mapped[Optional[int]] = mapped_column(default=0)
    description: Mapped[Optional[str]] = mapped_column(String)
    quantity: Mapped[Optional[float]] = mapped_column(Qty, default=0.0)
    unit_price: Mapped[Optional[float]] = mapped_column(Money, default=0.0)
    total_price: Mapped[Optional[float]] = mapped_column(Money, default=0.0)
    item_code: Mapped[Optional[str]] = mapped_column(String)
    uom: Mapped[Optional[str]] = mapped_column(String)
    matched_po_line_id: Mapped[Optional[str]] = mapped_column(String, index=True)

    invoice: Mapped[Optional[Invoice]] = relationship(back_populates="line_items")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    invoice_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    agent: Mapped[Optional[str]] = mapped_column(String)     # pipeline agent name, or "user"
    actor: Mapped[Optional[str]] = mapped_column(String)     # user email for human actions
    action: Mapped[Optional[str]] = mapped_column(String)
    details: Mapped[Json] = mapped_column(JSON)
    timestamp: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow, index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[Role] = mapped_column(Enum(Role, values_callable=lambda e: [m.value for m in e]), default=Role.VIEWER)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow)


class ToleranceRule(Base):
    """Matching tolerances. The row with vendor_id NULL is the global default; vendor rows override it."""
    __tablename__ = "tolerance_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    vendor_id: Mapped[Optional[str]] = mapped_column(String, unique=True)
    qty_pct: Mapped[float] = mapped_column(Float)
    price_pct: Mapped[float] = mapped_column(Float)
    price_abs: Mapped[float] = mapped_column(Float)
    total_abs: Mapped[float] = mapped_column(Float)
    updated_by: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow, onupdate=utcnow)


# ============================================================================
# ERP dataset (Oracle migration dataset, loaded by `python -m app.seed_erp`)
# ============================================================================

class Vendor(Base):
    __tablename__ = "erp_vendors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    supplier_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String, index=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    pay_terms: Mapped[Optional[str]] = mapped_column(String)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    created_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow)


class Material(Base):
    __tablename__ = "erp_materials"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    item_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    item_number: Mapped[Optional[str]] = mapped_column(String, index=True)    # printed code, e.g. ITEM-015
    description: Mapped[Optional[str]] = mapped_column(String)
    category: Mapped[Optional[str]] = mapped_column(String)
    uom: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow)


class POHeader(Base):
    __tablename__ = "erp_po_headers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    po_header_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    po_number: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    supplier_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("erp_vendors.supplier_id"), index=True)
    creation_date: Mapped[Optional[date]] = mapped_column(Date)
    currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD")
    status: Mapped[Optional[str]] = mapped_column(String, default="OPEN")    # OPEN | CLOSED | CANCELLED
    created_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow)

    vendor: Mapped[Optional[Vendor]] = relationship(lazy="joined")
    lines: Mapped[list["POLine"]] = relationship(back_populates="header", cascade="all, delete-orphan",
                                                 order_by="POLine.line_num")


class POLine(Base):
    __tablename__ = "erp_po_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    po_line_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    po_header_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("erp_po_headers.po_header_id"), index=True)
    line_num: Mapped[Optional[int]] = mapped_column()
    item_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("erp_materials.item_id"))
    uom: Mapped[Optional[str]] = mapped_column(String)
    quantity: Mapped[Optional[float]] = mapped_column(Qty)
    unit_price: Mapped[Optional[float]] = mapped_column(Money)
    line_amount: Mapped[Optional[float]] = mapped_column(Money)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow)

    header: Mapped[Optional[POHeader]] = relationship(back_populates="lines")
    material: Mapped[Optional[Material]] = relationship(lazy="joined")
    receipts: Mapped[list["GoodsReceiptERP"]] = relationship(back_populates="po_line",
                                                             order_by="GoodsReceiptERP.receipt_date")


class GoodsReceiptERP(Base):
    __tablename__ = "erp_goods_receipts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    receipt_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    po_line_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("erp_po_lines.po_line_id"), index=True)
    item_id: Mapped[Optional[str]] = mapped_column(String)
    supplier_id: Mapped[Optional[str]] = mapped_column(String)
    quantity_received: Mapped[Optional[float]] = mapped_column(Qty)
    uom: Mapped[Optional[str]] = mapped_column(String)
    receipt_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[Optional[datetime]] = mapped_column(TS, default=utcnow)

    po_line: Mapped[Optional[POLine]] = relationship(back_populates="receipts")


class ERPInvoice(Base):
    """Historical invoices from the ERP dataset (reference data, one row per PO line)."""
    __tablename__ = "erp_invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    erp_invoice_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String, index=True)
    supplier_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    po_line_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date)
    invoiced_qty: Mapped[Optional[float]] = mapped_column(Qty)
    uom: Mapped[Optional[str]] = mapped_column(String)
    unit_price: Mapped[Optional[float]] = mapped_column(Money)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    amount: Mapped[Optional[float]] = mapped_column(Money)


class PRHeader(Base):
    __tablename__ = "erp_pr_headers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    pr_header_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    pr_number: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    requester_id: Mapped[Optional[str]] = mapped_column(String)
    creation_date: Mapped[Optional[date]] = mapped_column(Date)
    department: Mapped[Optional[str]] = mapped_column(String)
    currency: Mapped[Optional[str]] = mapped_column(String(3))


class PRLine(Base):
    __tablename__ = "erp_pr_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    pr_line_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    pr_header_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    item_id: Mapped[Optional[str]] = mapped_column(String)
    uom: Mapped[Optional[str]] = mapped_column(String)
    quantity: Mapped[Optional[float]] = mapped_column(Qty)
    required_date: Mapped[Optional[date]] = mapped_column(Date)
    est_unit_price: Mapped[Optional[float]] = mapped_column(Money)
