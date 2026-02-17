"""
Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InvoiceLineItemSchema(BaseModel):
    item_code: Optional[str] = None
    description: str
    quantity: float
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: float = 0.0
    tax_amount: float = 0.0
    currency: str = "USD"
    po_reference: Optional[str] = None
    status: str
    invoice_type: str = "STANDARD"
    match_result: str = "PENDING"
    confidence_score: float = 0.0
    discrepancies: Optional[list] = None
    processing_time: Optional[float] = None
    created_at: Optional[datetime] = None
    line_items: list[InvoiceLineItemSchema] = []

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ProcessingResult(BaseModel):
    status: str
    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    total_amount: Optional[float] = None
    po_reference: Optional[str] = None
    match_result: Optional[str] = None
    match_score: Optional[float] = None
    discrepancies: list = []
    processing_time: Optional[float] = None
    error: Optional[str] = None


class DashboardStats(BaseModel):
    total_invoices: int = 0
    matched: int = 0
    partial_match: int = 0
    no_match: int = 0
    pending: int = 0
    failed: int = 0
    total_value: float = 0.0
    avg_processing_time: float = 0.0
    avg_confidence: float = 0.0


class HealthResponse(BaseModel):
    status: str
    orchestrator: str
    vision_ocr: dict
    erp: dict
    timestamp: str


class PurchaseOrderResponse(BaseModel):
    po_number: str
    vendor_name: str
    vendor_id: str
    order_date: str
    total_amount: float
    currency: str = "USD"
    status: str
    items: list


class MatchDetailResponse(BaseModel):
    invoice_id: str
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    total_amount: float = 0.0
    po_reference: Optional[str] = None
    match_result: str
    discrepancies: Optional[list] = None
    po_data: Optional[dict] = None
    grn_data: Optional[dict] = None
