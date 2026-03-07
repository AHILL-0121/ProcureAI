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


# ============================================================================
# ERP Dataset Models (Oracle Migration Dataset)
# ============================================================================

class Vendor(Base):
    """Vendor/Supplier master data from Oracle ERP"""
    __tablename__ = "erp_vendors"

    id = Column(String, primary_key=True, default=generate_uuid)
    supplier_id = Column(String, unique=True, index=True)  # Original SUPPLIER_ID
    supplier_name = Column(String)
    supplier_type = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Material(Base):
    """Material/Item master data from Oracle ERP"""
    __tablename__ = "erp_materials"

    id = Column(String, primary_key=True, default=generate_uuid)
    item_id = Column(String, unique=True, index=True)  # Original ITEM_ID
    description = Column(String)
    category = Column(String, nullable=True)
    uom = Column(String, nullable=True)  # Unit of Measure
    created_at = Column(DateTime, default=datetime.utcnow)


class POHeader(Base):
    """Purchase Order Header from Oracle ERP"""
    __tablename__ = "erp_po_headers"

    id = Column(String, primary_key=True, default=generate_uuid)
    po_header_id = Column(String, unique=True, index=True)  # Original PO_HEADER_ID
    po_number = Column(String, unique=True, index=True)
    supplier_id = Column(String, ForeignKey("erp_vendors.supplier_id"))
    creation_date = Column(String)
    currency = Column(String, default="USD")
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship("POLine", back_populates="header", cascade="all, delete-orphan")


class POLine(Base):
    """Purchase Order Line Item from Oracle ERP"""
    __tablename__ = "erp_po_lines"

    id = Column(String, primary_key=True, default=generate_uuid)
    po_line_id = Column(String, unique=True, index=True)  # Original PO_LINE_ID
    po_header_id = Column(String, ForeignKey("erp_po_headers.po_header_id"))
    line_num = Column(Integer)
    item_id = Column(String, ForeignKey("erp_materials.item_id"))
    quantity = Column(Float)
    unit_price = Column(Float)
    line_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    header = relationship("POHeader", back_populates="lines")


class GoodsReceiptERP(Base):
    """Goods Receipt Note from Oracle ERP"""
    __tablename__ = "erp_goods_receipts"

    id = Column(String, primary_key=True, default=generate_uuid)
    receipt_id = Column(String, unique=True, index=True)  # Original GRN ID
    po_line_id = Column(String, ForeignKey("erp_po_lines.po_line_id"))
    quantity_received = Column(Float)
    receipt_date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    action = Column(String)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
