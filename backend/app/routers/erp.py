import logging
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.erp_integration import ERPIntegrationAgent, grn_summary, invalidate_cache
from app.config import settings
from app.database import get_db
from app.models import AuditLog, Invoice, InvoiceStatus, Role, User, Vendor
from app.routers.common import audit, to_summary
from app.security import get_current_user, require_role
from app.services import erp_import
from app.services.jobs import jobs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["erp"])
erp = ERPIntegrationAgent()


@router.get("/purchase-orders")
def list_purchase_orders(q: Optional[str] = None, vendor: Optional[str] = None, status: Optional[str] = None,
                         page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                         sort: str = "-order_date", db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return erp.search_pos(db, query=q, vendor=vendor, status=status, page=page, page_size=page_size, sort=sort)


@router.get("/purchase-orders/{po_number}")
def get_purchase_order(po_number: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    po = erp.fetch_purchase_order(db, po_number)
    if not po:
        raise HTTPException(404, f"Purchase order {po_number} not found")
    lines = erp.fulfilment(db, po)
    invoices = db.scalars(select(Invoice).where(Invoice.po_reference == po_number).order_by(Invoice.created_at.desc())).all()
    return {"purchase_order": {**po, "lines": lines}, "goods_receipt": grn_summary(po),
            "invoices": [to_summary(i) for i in invoices]}


@router.get("/vendors")
def list_vendors(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [{"supplier_id": v.supplier_id, "name": v.supplier_name, "tax_id": v.tax_id, "currency": v.currency,
             "pay_terms": v.pay_terms} for v in db.scalars(select(Vendor).order_by(Vendor.supplier_name))]


# ---------------------------------------------------------------- ERP Connect: file import
@router.get("/erp/status")
def erp_status(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    last = db.scalars(select(AuditLog).where(AuditLog.action == "ERP_IMPORTED")
                      .order_by(AuditLog.timestamp.desc()).limit(1)).first()
    counts = erp_import.table_counts(db)
    source = "import" if last else ("sample" if counts["po_headers"] else "empty")
    return {
        "source": source, "counts": counts, "layouts": erp_import.layouts(),
        "last_import": {"at": last.timestamp, "by": last.actor, **(last.details or {})} if last else None,
    }


def _rematch_waiting(ids: list[str]):
    for invoice_id in ids:
        try:
            jobs.orchestrator.rematch(invoice_id, actor=None)
        except Exception:
            logger.exception("Re-match after ERP import failed for %s", invoice_id)


@router.post("/erp/import")
async def erp_import_files(background: BackgroundTasks, files: list[UploadFile] = File(...),
                           mode: Literal["merge", "replace"] = "merge", dry_run: bool = True, rematch: bool = True,
                           db: Session = Depends(get_db), admin: User = Depends(require_role(Role.ADMIN))):
    """Check (dry_run=true) or load CSV files into the ERP tables. All-or-nothing."""
    if len(files) > len(erp_import.ENTITIES):
        raise HTTPException(400, f"Send at most {len(erp_import.ENTITIES)} files, one per ERP layout")
    parsed = []
    for f in files:
        data = await f.read(settings.upload_max_bytes + 1)
        name = f.filename or "file"
        if len(data) > settings.upload_max_bytes:
            raise HTTPException(413, f"{name} is larger than {settings.upload_max_bytes // (1024 * 1024)} MB")
        try:
            parsed.append(erp_import.read_csv_bytes(name, data))
        except erp_import.ERPFileError as e:
            raise HTTPException(422, f"{name} {e}") from e

    plan = erp_import.build_plan(db, parsed, mode)
    result = plan.summary()
    if dry_run or not plan.ok:
        return {**result, "committed": False}

    counts = erp_import.apply_plan(db, plan)
    invalidate_cache()
    waiting = list(db.scalars(select(Invoice.id).where(
        Invoice.status.in_([InvoiceStatus.DISCREPANCY, InvoiceStatus.ON_HOLD])))) if rematch else []
    audit(db, None, "ERP_IMPORTED", admin.email,
          {"mode": mode, "files": [f.filename for f in parsed], "counts": counts, "rematched": len(waiting)},
          agent="erp")
    db.commit()
    if waiting:
        background.add_task(_rematch_waiting, waiting)
    return {**result, "committed": True, "counts": counts, "rematching": len(waiting)}
