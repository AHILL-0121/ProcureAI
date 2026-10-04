"""Pydantic request/response models."""

from datetime import date, datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------- auth & users
class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str
    role: str
    active: bool

    @field_validator("role", mode="before")
    @classmethod
    def _role(cls, v):
        return getattr(v, "value", v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    name: str = Field(min_length=1, max_length=120)
    role: str = "viewer"
    password: Optional[str] = Field(default=None, min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)


# ---------------------------------------------------------------- invoices
def _none_to(default):
    return lambda v: default if v is None else v


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    line_no: int = 0
    item_code: Optional[str] = None
    description: Optional[str] = None
    quantity: float = 0.0
    unit_price: float = 0.0
    total_price: float = 0.0
    uom: Optional[str] = None
    matched_po_line_id: Optional[str] = None

    # rows created before v2 can hold NULLs in these columns
    _ints = field_validator("line_no", mode="before")(_none_to(0))
    _nums = field_validator("quantity", "unit_price", "total_price", mode="before")(_none_to(0.0))


def _enum(v):
    return getattr(v, "value", v)


class InvoiceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    po_reference: Optional[str] = None
    total_amount: float = 0.0
    currency: Optional[str] = None
    status: str
    match_result: str = "PENDING"
    match_score: Optional[float] = None
    confidence_score: float = 0.0
    invoice_date: Optional[date] = None
    created_at: Optional[datetime] = None
    processing_time: Optional[float] = None
    original_filename: Optional[str] = None
    source_email: Optional[str] = None
    reviewed_by: Optional[str] = None
    top_issue: Optional[str] = None
    top_issue_code: Optional[str] = None
    top_issue_severity: Optional[str] = None
    issue_count: int = 0

    _status = field_validator("status", mode="before")(lambda v: _enum(v))
    _result = field_validator("match_result", mode="before")(lambda v: _enum(v) if v is not None else "PENDING")
    _nums = field_validator("total_amount", "confidence_score", mode="before")(_none_to(0.0))


class InvoiceDetail(InvoiceSummary):
    due_date: Optional[date] = None
    subtotal: Optional[float] = None
    tax_amount: float = 0.0
    invoice_type: str = "STANDARD"
    vendor_tax_id: Optional[str] = None
    validation: Optional[dict] = None
    discrepancies: Optional[list] = None
    match_checks: Optional[list] = None
    match_snapshot: Optional[dict] = None
    extraction: Optional[dict] = None
    duplicate_of: Optional[str] = None
    error: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    line_items: list[InvoiceLineOut] = []

    _type = field_validator("invoice_type", mode="before")(lambda v: _enum(v) if v is not None else "STANDARD")
    _tax = field_validator("tax_amount", mode="before")(_none_to(0.0))


class LineEdit(BaseModel):
    item_code: Optional[str] = None
    description: str = ""
    quantity: float = 0.0
    unit_price: float = 0.0
    total_price: Optional[float] = None
    uom: Optional[str] = None


class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    po_reference: Optional[str] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    line_items: Optional[list[LineEdit]] = None


class ReviewAction(BaseModel):
    note: Optional[str] = Field(default=None, max_length=2000)


class UploadItem(BaseModel):
    invoice_id: Optional[str] = None
    filename: str
    status: str
    duplicate: bool = False
    error: Optional[str] = None


class UploadResponse(BaseModel):
    accepted: int
    items: list[UploadItem]


class DocumentLink(BaseModel):
    url: str
    media_type: str
    filename: Optional[str] = None
    expires_in: int


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    invoice_id: Optional[str] = None
    agent: str
    actor: Optional[str] = None
    action: str
    details: Optional[Any] = None
    timestamp: Optional[datetime] = None


# ---------------------------------------------------------------- dashboard / health
class CurrencyTotal(BaseModel):
    currency: str
    amount: float
    count: int


class DashboardStats(BaseModel):
    total_invoices: int = 0
    matched: int = 0
    partial_match: int = 0
    no_match: int = 0
    pending: int = 0
    failed: int = 0
    duplicates: int = 0
    in_review: int = 0
    on_hold: int = 0
    approved: int = 0
    rejected: int = 0
    processing: int = 0
    auto_match_rate: float = 0.0
    avg_processing_time: float = 0.0
    avg_confidence: float = 0.0
    value_by_currency: list[CurrencyTotal] = []
    cleared_by_currency: list[CurrencyTotal] = []
    held_by_currency: list[CurrencyTotal] = []
    issues_by_type: list[dict] = []
    vendors_to_watch: list[dict] = []
    daily: list[dict] = []
    today: dict = {}


class HealthResponse(BaseModel):
    status: str
    orchestrator: str
    vision_ocr: dict
    erp: dict
    queue_depth: int = 0
    timestamp: str


# ---------------------------------------------------------------- settings
class ToleranceIn(BaseModel):
    qty_pct: float = Field(ge=0, le=1)
    price_pct: float = Field(ge=0, le=1)
    price_abs: float = Field(ge=0)
    total_abs: float = Field(ge=0)


class ToleranceOut(ToleranceIn):
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
