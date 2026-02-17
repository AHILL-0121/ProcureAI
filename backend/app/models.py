import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Enum, Text, JSON, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from app.database import Base


class InvoiceStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    MATCHING = "MATCHING"
    MATCHED = "MATCHED"
    DISCREPANCY = "DISCREPANCY"
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


def generate_uuid():
    return str(uuid.uuid4())


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=generate_uuid)
    invoice_number = Column(String, index=True)
    vendor_name = Column(String)
    vendor_id = Column(String)
    invoice_date = Column(String)
    due_date = Column(String, nullable=True)
    total_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    po_reference = Column(String, nullable=True, index=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.RECEIVED)
    invoice_type = Column(Enum(InvoiceType), default=InvoiceType.STANDARD)
    match_result = Column(Enum(MatchResult), default=MatchResult.PENDING)
    confidence_score = Column(Float, default=0.0)
    extracted_data = Column(JSON, nullable=True)
    discrepancies = Column(JSON, nullable=True)
    source_email = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    processing_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    invoice_id = Column(String, ForeignKey("invoices.id"))
    description = Column(String)
    quantity = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    item_code = Column(String, nullable=True)

    invoice = relationship("Invoice", back_populates="line_items")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    po_number = Column(String, unique=True, index=True)
    vendor_name = Column(String)
    vendor_id = Column(String)
    order_date = Column(String)
    expected_delivery = Column(String, nullable=True)
    total_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    status = Column(String, default="OPEN")
    items = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id = Column(String, primary_key=True, default=generate_uuid)
    grn_number = Column(String, unique=True, index=True)
    po_number = Column(String, index=True)
    vendor_name = Column(String)
    receipt_date = Column(String)
    received_by = Column(String, nullable=True)
    items = Column(JSON, default=list)
    status = Column(String, default="RECEIVED")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    invoice_id = Column(String, nullable=True)
    agent = Column(String)
    action = Column(String)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
