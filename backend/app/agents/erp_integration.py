"""
Agent 4: ERP lookups (PostgreSQL / SQLite ERP tables).

- PO lookups load header, vendor, lines, materials and receipts in one round-trip (eager loading).
- Static PO data is cached with a TTL; billed quantities are always computed fresh.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Any, Optional

from cachetools import TTLCache
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import (
    ERPInvoice,
    GoodsReceiptERP,
    Invoice,
    InvoiceLineItem,
    Material,
    POHeader,
    POLine,
    Vendor,
)

logger = logging.getLogger(__name__)

_po_cache: TTLCache = TTLCache(maxsize=512, ttl=300)
_stats_cache: TTLCache = TTLCache(maxsize=1, ttl=300)

BILLED_STATUSES = ("MATCHED", "APPROVED")
_SUFFIXES = re.compile(r"\b(inc|ltd|llc|gmbh|plc|co|corp|corporation|company|limited|pvt|private|sa|ag|bv)\b\.?")


def invalidate_cache():
    _po_cache.clear()
    _stats_cache.clear()


def normalise_name(name: str | None) -> str:
    s = (name or "").lower()
    s = _SUFFIXES.sub(" ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def normalise_tax_id(tax: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (tax or "").upper())


def _date(d) -> Optional[str]:
    return d.isoformat() if d else None


def po_to_dict(po: POHeader) -> dict:
    lines = []
    total = 0.0
    for ln in po.lines:
        amount = round(float(ln.line_amount if ln.line_amount is not None else (ln.quantity or 0) * (ln.unit_price or 0)), 2)
        total += amount
        receipts: list[dict[str, Any]] = [{"receipt_id": g.receipt_id, "quantity": float(g.quantity_received or 0),
                     "date": _date(g.receipt_date)} for g in ln.receipts]
        lines.append({
            "po_line_id": ln.po_line_id,
            "line_num": ln.line_num,
            "item_id": ln.item_id,
            "item_number": ln.material.item_number if ln.material else None,
            "description": ln.material.description if ln.material else f"Item {ln.item_id}",
            "uom": ln.uom or (ln.material.uom if ln.material else None),
            "quantity": float(ln.quantity or 0),
            "unit_price": float(ln.unit_price or 0),
            "line_amount": amount,
            "delivery_date": _date(ln.delivery_date),
            "received_qty": round(sum(r["quantity"] for r in receipts), 3),
            "receipts": receipts,
        })
    return {
        "po_number": po.po_number,
        "po_header_id": po.po_header_id,
        "vendor_id": po.supplier_id,
        "vendor_name": po.vendor.supplier_name if po.vendor else f"Supplier {po.supplier_id}",
        "vendor_tax_id": po.vendor.tax_id if po.vendor else None,
        "currency": po.currency,
        "status": po.status or "OPEN",
        "order_date": _date(po.creation_date),
        "total_amount": round(total, 2),
        "lines": lines,
    }


def grn_summary(po: dict) -> Optional[dict]:
    """A goods-receipt view of a PO dict (None when nothing has been received)."""
    received = [ln for ln in po["lines"] if ln["receipts"]]
    if not received:
        return None
    ids = sorted({r["receipt_id"] for ln in received for r in ln["receipts"]}, key=lambda x: (len(x), x))
    dates = [r["date"] for ln in received for r in ln["receipts"] if r["date"]]
    return {
        "grn_numbers": [f"GRN-{i}" for i in ids],
        "grn_number": f"GRN-{ids[0]}" if len(ids) == 1 else f"GRN-{ids[0]} +{len(ids) - 1}",
        "po_number": po["po_number"],
        "received_date": max(dates) if dates else None,
        "lines_received": len(received),
        "lines_total": len(po["lines"]),
        "status": "COMPLETE" if len(received) == len(po["lines"]) else "PARTIAL",
        "lines": [{"po_line_id": ln["po_line_id"], "line_num": ln["line_num"], "description": ln["description"],
                   "item_number": ln["item_number"], "quantity": ln["received_qty"], "uom": ln["uom"],
                   "receipts": ln["receipts"]} for ln in received],
    }


class ERPIntegrationAgent:
    def fetch_purchase_order(self, db: Session, po_number: str) -> Optional[dict]:
        if not po_number:
            return None
        cached = _po_cache.get(po_number)
        if cached is not None:
            return cached
        po = db.scalars(
            select(POHeader)
            .where(POHeader.po_number == po_number)
            .options(selectinload(POHeader.lines).selectinload(POLine.receipts))
        ).first()
        if not po:
            return None
        data = po_to_dict(po)
        _po_cache[po_number] = data
        return data

    def billed_quantities(self, db: Session, po_line_ids: list[str], exclude_invoice_id: str | None = None) -> dict[str, float]:
        """Quantity already invoiced per PO line (our matched/approved invoices, plus ERP history if enabled)."""
        if not po_line_ids:
            return {}
        q = (select(InvoiceLineItem.matched_po_line_id, func.coalesce(func.sum(InvoiceLineItem.quantity), 0))
             .join(Invoice, Invoice.id == InvoiceLineItem.invoice_id)
             .where(InvoiceLineItem.matched_po_line_id.in_(po_line_ids))
             .where(Invoice.status.in_(BILLED_STATUSES))
             .group_by(InvoiceLineItem.matched_po_line_id))
        if exclude_invoice_id:
            q = q.where(Invoice.id != exclude_invoice_id)
        billed = {pid: float(qty) for pid, qty in db.execute(q)}
        if settings.match_include_erp_invoice_history:
            hq = (select(ERPInvoice.po_line_id, func.sum(ERPInvoice.invoiced_qty))
                  .where(ERPInvoice.po_line_id.in_(po_line_ids)).group_by(ERPInvoice.po_line_id))
            for pid, qty in db.execute(hq):
                billed[pid] = billed.get(pid, 0.0) + float(qty or 0)
        return billed

    def resolve_vendor(self, db: Session, name: str | None, tax_id: str | None) -> Optional[Vendor]:
        tax = normalise_tax_id(tax_id)
        if tax:
            for v in db.scalars(select(Vendor).where(Vendor.tax_id.is_not(None))):
                if normalise_tax_id(v.tax_id) == tax:
                    return v
        target = normalise_name(name)
        if not target:
            return None
        best, best_score = None, 0.0
        for v in db.scalars(select(Vendor)):
            cand = normalise_name(v.supplier_name)
            score = 1.0 if cand == target else SequenceMatcher(None, target, cand).ratio()
            if score > best_score:
                best, best_score = v, score
        return best if best_score >= 0.9 else None

    def search_pos(self, db: Session, query: str | None = None, vendor: str | None = None, status: str | None = None,
                   page: int = 1, page_size: int = 25, sort: str = "-order_date") -> dict:
        totals = (select(POLine.po_header_id.label("hid"), func.sum(POLine.line_amount).label("total"),
                         func.count(POLine.id).label("n")).group_by(POLine.po_header_id).subquery())
        base = (select(POHeader, Vendor.supplier_name, totals.c.total, totals.c.n)
                .outerjoin(Vendor, Vendor.supplier_id == POHeader.supplier_id)
                .outerjoin(totals, totals.c.hid == POHeader.po_header_id))
        if query:
            like = f"%{query}%"
            base = base.where(or_(POHeader.po_number.ilike(like), Vendor.supplier_name.ilike(like)))
        if vendor:
            base = base.where(Vendor.supplier_name.ilike(f"%{vendor}%"))
        if status:
            base = base.where(POHeader.status == status.upper())
        total = db.scalar(select(func.count()).select_from(base.subquery()))
        order: Any = {
            "order_date": POHeader.creation_date.asc(), "-order_date": POHeader.creation_date.desc(),
            "po_number": POHeader.po_number.asc(), "-po_number": POHeader.po_number.desc(),
            "total": totals.c.total.asc(), "-total": totals.c.total.desc(),
        }.get(sort, POHeader.creation_date.desc())
        rows = db.execute(base.order_by(order, POHeader.po_number).offset((page - 1) * page_size).limit(page_size)).all()
        items = [{
            "po_number": po.po_number, "vendor_name": name or f"Supplier {po.supplier_id}", "vendor_id": po.supplier_id,
            "order_date": _date(po.creation_date), "total_amount": round(float(t or 0), 2), "currency": po.currency,
            "status": po.status or "OPEN", "line_count": int(n or 0),
        } for po, name, t, n in rows]
        return {"items": items, "total": total or 0, "page": page, "page_size": page_size}

    def fulfilment(self, db: Session, po: dict) -> list[dict]:
        billed = self.billed_quantities(db, [ln["po_line_id"] for ln in po["lines"]])
        return [{**ln, "invoiced_qty": round(billed.get(ln["po_line_id"], 0.0), 3)} for ln in po["lines"]]

    def get_erp_stats(self, db: Session) -> dict:
        cached = _stats_cache.get("stats")
        if cached:
            return cached
        stats: dict[str, Any] = {
            "total_vendors": db.scalar(select(func.count()).select_from(Vendor)) or 0,
            "total_materials": db.scalar(select(func.count()).select_from(Material)) or 0,
            "total_purchase_orders": db.scalar(select(func.count()).select_from(POHeader)) or 0,
            "total_po_lines": db.scalar(select(func.count()).select_from(POLine)) or 0,
            "total_goods_receipts": db.scalar(select(func.count()).select_from(GoodsReceiptERP)) or 0,
        }
        stats["status"] = "online" if stats["total_purchase_orders"] else "empty"
        _stats_cache["stats"] = stats
        return stats
