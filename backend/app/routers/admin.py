from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.email_intake import mask_email, polling_state
from app.config import settings
from app.database import get_db
from app.models import AuditLog, Role, ToleranceRule, User, Vendor
from app.routers.common import audit
from app.schemas import AuditEntry, ToleranceIn, ToleranceOut
from app.security import get_current_user, require_role
from app.services.email_poller import poller
from app.services.tolerances import default_tolerance

router = APIRouter(prefix="/api", tags=["settings"])


# ---------------------------------------------------------------- tolerances
def _out(r: ToleranceRule | None, vendors: dict) -> ToleranceOut:
    if r is None:
        d = default_tolerance()
        return ToleranceOut(qty_pct=d.qty_pct, price_pct=d.price_pct, price_abs=d.price_abs, total_abs=d.total_abs)
    return ToleranceOut(qty_pct=r.qty_pct, price_pct=r.price_pct, price_abs=r.price_abs, total_abs=r.total_abs,
                        vendor_id=r.vendor_id, vendor_name=vendors.get(r.vendor_id or ""),
                        updated_by=r.updated_by, updated_at=r.updated_at)


@router.get("/settings/tolerances")
def get_tolerances(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    vendors = {v.supplier_id: v.supplier_name for v in db.scalars(select(Vendor))}
    rules = list(db.scalars(select(ToleranceRule)))
    default = next((r for r in rules if r.vendor_id is None), None)
    return {"default": _out(default, vendors),
            "vendors": [_out(r, vendors) for r in rules if r.vendor_id is not None]}


@router.put("/settings/tolerances", response_model=ToleranceOut)
def set_tolerance(body: ToleranceIn, vendor_id: Optional[str] = Query(None), db: Session = Depends(get_db),
                  admin: User = Depends(require_role(Role.ADMIN))):
    if vendor_id and not db.scalars(select(Vendor).where(Vendor.supplier_id == vendor_id)).first():
        raise HTTPException(404, "Vendor not found")
    q = select(ToleranceRule).where(ToleranceRule.vendor_id == vendor_id if vendor_id else ToleranceRule.vendor_id.is_(None))
    rule = db.scalars(q).first() or ToleranceRule(vendor_id=vendor_id)
    for k, v in body.model_dump().items():
        setattr(rule, k, v)
    rule.updated_by = admin.email
    db.add(rule)
    audit(db, None, "TOLERANCE_UPDATED", admin.email, {"vendor_id": vendor_id, **body.model_dump()})
    db.commit()
    vendors = {v.supplier_id: v.supplier_name for v in db.scalars(select(Vendor))}
    return _out(rule, vendors)


@router.delete("/settings/tolerances/{vendor_id}", status_code=204)
def delete_vendor_tolerance(vendor_id: str, db: Session = Depends(get_db), admin: User = Depends(require_role(Role.ADMIN))):
    rule = db.scalars(select(ToleranceRule).where(ToleranceRule.vendor_id == vendor_id)).first()
    if not rule:
        raise HTTPException(404, "No override for this vendor")
    db.delete(rule)
    audit(db, None, "TOLERANCE_REMOVED", admin.email, {"vendor_id": vendor_id})
    db.commit()


# ---------------------------------------------------------------- email intake
@router.get("/email/poll-status")
def email_poll_status(_: User = Depends(get_current_user)):
    return {**polling_state, "running": poller.running, "configured": poller.agent.configured,
            "interval_seconds": settings.email_poll_interval, "mailbox": mask_email(settings.email_user),
            "connection_ok": poller.connection_ok}


@router.post("/email/poll-now")
async def email_poll_now(admin: User = Depends(require_role(Role.ADMIN))):
    if not poller.agent.configured:
        raise HTTPException(400, "Email intake is not configured (EMAIL_USER / EMAIL_PASSWORD)")
    try:
        results = await poller.poll_once()
    except Exception as e:
        raise HTTPException(502, f"Could not read the mailbox: {e}") from e
    return {"found": len(results), "items": results}


@router.post("/email/poll-start")
async def email_poll_start(admin: User = Depends(require_role(Role.ADMIN))):
    if not poller.agent.configured:
        raise HTTPException(400, "Email intake is not configured (EMAIL_USER / EMAIL_PASSWORD)")
    started = await poller.start(check=True)
    if not started:
        raise HTTPException(502, f"Could not connect to the mailbox: {polling_state.get('last_error')}")
    return {"running": True, "interval_seconds": settings.email_poll_interval}


@router.post("/email/poll-stop")
async def email_poll_stop(admin: User = Depends(require_role(Role.ADMIN))):
    await poller.stop()
    return {"running": False}


# ---------------------------------------------------------------- audit trail
@router.get("/audit-logs", response_model=list[AuditEntry])
def list_audit_logs(invoice_id: Optional[str] = None, limit: int = Query(50, ge=1, le=500),
                    db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = select(AuditLog)
    if invoice_id:
        q = q.where(AuditLog.invoice_id == invoice_id)
    return list(db.scalars(q.order_by(AuditLog.timestamp.desc()).limit(limit)))
