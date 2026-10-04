"""
Agent 3: Checking (validation, classification, vendor resolution, duplicate detection).
"""

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.erp_integration import ERPIntegrationAgent, normalise_name
from app.extraction import ISO_4217, ExtractedInvoice
from app.models import LIVE_STATUSES, Invoice

logger = logging.getLogger(__name__)

HIGH_VALUE_THRESHOLD = 100_000


def vendor_key_for(vendor_id: Optional[str], vendor_name: Optional[str]) -> Optional[str]:
    if vendor_id:
        return f"id:{vendor_id}"
    n = normalise_name(vendor_name)
    return f"name:{n}" if n else None


class ClassificationAgent:
    def __init__(self, erp: ERPIntegrationAgent | None = None):
        self.erp = erp or ERPIntegrationAgent()

    def classify_type(self, inv: ExtractedInvoice) -> str:
        number = (inv.invoice_number or "").lower()
        notes = (inv.notes or "").lower()
        if (inv.total_amount or 0) < 0 or "credit" in number or "credit note" in notes:
            return "CREDIT_NOTE"
        if "debit" in number or "debit note" in notes:
            return "DEBIT_NOTE"
        if "pro forma" in number or "proforma" in number or "proforma" in notes or "pro-forma" in notes:
            return "PRO_FORMA"
        return "STANDARD"

    def validate_and_classify(self, db: Session, inv: ExtractedInvoice, invoice_id: str | None = None) -> dict:
        errors: list[str] = []
        warnings: list[str] = list(f"Filled in automatically: {c}" for c in inv.coercions)

        # Required fields
        if not inv.invoice_number:
            errors.append("Invoice number is missing")
        if not inv.vendor_name and not inv.vendor_tax_id:
            errors.append("Vendor name is missing")
        if inv.total_amount is None:
            errors.append("Total amount is missing")

        invoice_type = self.classify_type(inv)
        if inv.total_amount is not None and inv.total_amount <= 0 and invoice_type != "CREDIT_NOTE":
            errors.append("Total amount must be positive for a standard invoice")
        if invoice_type == "PRO_FORMA":
            warnings.append("Pro-forma invoice: not a request for payment")

        # Currency
        if inv.currency and inv.currency not in ISO_4217:
            errors.append(f"Currency '{inv.currency}' is not a valid ISO 4217 code")
        elif not inv.currency:
            warnings.append("Currency not stated on the invoice")

        # Lines & arithmetic
        if not inv.line_items:
            warnings.append("No line items found")
        for i, ln in enumerate(inv.line_items, start=1):
            if ln.quantity is None or ln.quantity == 0:
                warnings.append(f"Line {i}: quantity missing or zero")
            if ln.unit_price is None or ln.unit_price <= 0:
                warnings.append(f"Line {i}: unit price missing or not positive")
            if ln.quantity is not None and ln.unit_price is not None and ln.total_price is not None:
                expected = round(ln.quantity * ln.unit_price, 2)
                if abs(expected - ln.total_price) > max(0.5, 0.005 * abs(ln.total_price)):
                    warnings.append(f"Line {i}: qty × price = {expected:,.2f} but the line says {ln.total_price:,.2f}")
        if inv.line_items and inv.subtotal is not None:
            s = round(sum(ln.total_price or 0 for ln in inv.line_items), 2)
            if abs(s - inv.subtotal) > 1.0:
                warnings.append(f"Line totals add up to {s:,.2f} but the subtotal is {inv.subtotal:,.2f}")
        if inv.total_amount and inv.total_amount > HIGH_VALUE_THRESHOLD:
            warnings.append(f"High-value invoice ({inv.total_amount:,.2f}): second approval recommended")
        if inv.po_reference and not inv.po_reference.startswith("PO-"):
            warnings.append(f"PO reference '{inv.po_reference}' has an unusual format")

        # Vendor resolution against the ERP vendor master
        vendor = self.erp.resolve_vendor(db, inv.vendor_name, inv.vendor_tax_id)
        vendor_info: dict[str, Any]
        if vendor:
            vendor_info = {"id": vendor.supplier_id, "name": vendor.supplier_name, "tax_id": vendor.tax_id, "known": True}
        else:
            vendor_info = {"id": None, "name": inv.vendor_name, "tax_id": inv.vendor_tax_id, "known": False}
            if inv.vendor_name or inv.vendor_tax_id:
                warnings.append(f"Vendor '{inv.vendor_name or inv.vendor_tax_id}' is not in the vendor master")

        # Duplicate detection (persistent, database-backed)
        vkey = vendor_key_for(vendor_info["id"], inv.vendor_name)
        duplicate_of = None
        if vkey and inv.invoice_number:
            q = (select(Invoice.id).where(Invoice.vendor_key == vkey, Invoice.invoice_number == inv.invoice_number,
                                          Invoice.status.in_(LIVE_STATUSES)))
            if invoice_id:
                q = q.where(Invoice.id != invoice_id)
            duplicate_of = db.scalars(q.order_by(Invoice.created_at)).first()
        if not duplicate_of and vkey and inv.total_amount is not None and inv.invoice_date:
            nq = (select(Invoice.id, Invoice.invoice_number)
                  .where(Invoice.vendor_key == vkey, Invoice.total_amount == inv.total_amount,
                         Invoice.invoice_date == inv.invoice_date, Invoice.status.in_(LIVE_STATUSES)))
            if invoice_id:
                nq = nq.where(Invoice.id != invoice_id)
            near = db.execute(nq).first()
            if near:
                warnings.append(f"Same vendor, date and amount as invoice {near[1] or near[0]}: possible duplicate")

        return {
            "valid": not errors,
            "invoice_type": invoice_type,
            "errors": errors,
            "warnings": warnings,
            "vendor": vendor_info,
            "vendor_key": vkey,
            "duplicate_of": duplicate_of,
        }
