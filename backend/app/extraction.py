"""
Typed schema for data extracted from an invoice by the LLM.

LLM output is untrusted: numbers arrive as "1,200.00", "$45", null or "N/A"; dates arrive in any format.
Everything is coerced here so downstream agents only ever see clean types, and every repair is
recorded in `coercions` so reviewers can see what was guessed.
"""

import re
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

ISO_4217 = {
    "USD", "EUR", "GBP", "INR", "JPY", "CNY", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK", "DKK", "PLN", "CZK",
    "HUF", "SGD", "HKD", "AED", "SAR", "ZAR", "BRL", "MXN", "KRW", "TRY", "ILS", "THB", "MYR", "IDR", "PHP",
}
CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY", "Rs": "INR", "Rs.": "INR"}

_NUM_RE = re.compile(r"-?\d[\d.,\s]*\d|-?\d|-?\.\d+")
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y",
                 "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d", "%d-%b-%Y")


def parse_number(value: Any) -> Optional[float]:
    """'1,234.50' -> 1234.5, '(12.00)' -> -12.0, '$45' -> 45.0, None/'N/A' -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    m = _NUM_RE.search(s.replace(" ", " "))
    if not m:
        return None
    raw = m.group(0).replace(" ", "")
    if "," in raw and "." in raw:
        # the right-most separator is the decimal one: "1,234.56" or "1.234,56"
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        # "7576,80" -> decimal comma; "1,234" / "1,234,567" -> thousands
        raw = raw.replace(",", ".") if re.search(r",\d{1,2}$", raw) else raw.replace(",", "")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    try:
        n = float(raw)
    except ValueError:
        return None
    return -abs(n) if negative else n


def parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s or s.lower() in {"null", "none", "n/a"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_currency(value: Any) -> Optional[str]:
    if not value:
        return None
    s = str(value).strip()
    if s in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[s]
    s = s.upper()[:3]
    return s if s in ISO_4217 else None


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return None if not s or s.lower() in {"null", "none", "n/a", "string"} else s


class ExtractedLine(BaseModel):
    item_code: Optional[str] = None
    description: str = ""
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    uom: Optional[str] = None

    _text = field_validator("item_code", "uom", mode="before")(lambda v: clean_text(v))
    _nums = field_validator("quantity", "unit_price", "total_price", mode="before")(lambda v: parse_number(v))

    @field_validator("description", mode="before")
    @classmethod
    def _desc(cls, v):
        return clean_text(v) or ""


class ExtractedInvoice(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    vendor_address: Optional[str] = None
    bill_to: Optional[str] = None
    po_reference: Optional[str] = None
    currency: Optional[str] = None
    line_items: list[ExtractedLine] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    coercions: list[str] = Field(default_factory=list)

    _text = field_validator("invoice_number", "vendor_name", "vendor_id", "vendor_tax_id", "vendor_address",
                            "bill_to", "payment_terms", "notes", mode="before")(lambda v: clean_text(v))
    _nums = field_validator("subtotal", "tax_amount", "total_amount", mode="before")(lambda v: parse_number(v))
    _dates = field_validator("invoice_date", "due_date", mode="before")(lambda v: parse_date(v))

    @field_validator("currency", mode="before")
    @classmethod
    def _cur(cls, v):
        return parse_currency(v)

    @field_validator("po_reference", mode="before")
    @classmethod
    def _po(cls, v):
        s = clean_text(v)
        if not s:
            return None
        s = re.sub(r"\s+", "", s.upper())
        m = re.fullmatch(r"(?:PO|P\.O\.|PURCHASEORDER)[-#:.]*(?:NO\.?|NUMBER)?[-#:.]*(\d{1,6})", s)
        if m:   # normalise "PO#822", "PO 000822", "P.O. No. 822" -> "PO-000822"
            return f"PO-{int(m.group(1)):06d}"
        return s

    @field_validator("line_items", mode="before")
    @classmethod
    def _lines(cls, v):
        return [x for x in (v or []) if isinstance(x, dict)]

    @model_validator(mode="after")
    def _fill_arithmetic(self):
        """Fill gaps that arithmetic can recover, and record each repair."""
        for i, ln in enumerate(self.line_items, start=1):
            if ln.total_price is None and ln.quantity is not None and ln.unit_price is not None:
                ln.total_price = round(ln.quantity * ln.unit_price, 2)
                self.coercions.append(f"line {i}: total computed from qty × price")
            elif ln.unit_price is None and ln.quantity and ln.total_price is not None:
                ln.unit_price = round(ln.total_price / ln.quantity, 4)
                self.coercions.append(f"line {i}: unit price computed from total ÷ qty")
            elif ln.quantity is None and ln.unit_price and ln.total_price is not None:
                ln.quantity = round(ln.total_price / ln.unit_price, 3)
                self.coercions.append(f"line {i}: quantity computed from total ÷ price")
        line_sum = round(sum(ln.total_price or 0 for ln in self.line_items), 2)
        if self.subtotal is None and self.line_items:
            self.subtotal = line_sum
            self.coercions.append("subtotal computed from line totals")
        if self.total_amount is None and self.subtotal is not None:
            self.total_amount = round(self.subtotal + (self.tax_amount or 0), 2)
            self.coercions.append("total computed from subtotal + tax")
        if self.tax_amount is None and self.total_amount is not None and self.subtotal is not None:
            self.tax_amount = round(self.total_amount - self.subtotal, 2)
        return self

    # ---- consistency signals used by the confidence score ----
    def arithmetic_consistency(self) -> float:
        """Share of arithmetic checks that hold (lines, subtotal, total)."""
        checks: list[bool] = []
        for ln in self.line_items:
            if ln.quantity is not None and ln.unit_price is not None and ln.total_price is not None:
                checks.append(abs(ln.quantity * ln.unit_price - ln.total_price) <= max(0.5, 0.005 * abs(ln.total_price)))
        if self.line_items and self.subtotal is not None:
            checks.append(abs(sum(ln.total_price or 0 for ln in self.line_items) - self.subtotal) <= 1.0)
        if self.subtotal is not None and self.total_amount is not None:
            checks.append(abs(self.subtotal + (self.tax_amount or 0) - self.total_amount) <= 1.0)
        return sum(checks) / len(checks) if checks else 0.0

    def completeness(self) -> float:
        required = [self.invoice_number, self.vendor_name, self.total_amount, self.line_items]
        optional = [self.invoice_date, self.po_reference, self.currency, self.subtotal]
        score = sum(2 for f in required if f) + sum(1 for f in optional if f)
        return score / (2 * len(required) + len(optional))

    def to_json(self) -> dict:
        return self.model_dump(mode="json")
