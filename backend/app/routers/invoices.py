import os
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.agents.orchestrator import OrchestratorAgent
from app.config import settings
from app.database import get_db
from app.models import (
    REVIEW_STATUSES,
    AuditLog,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    MatchResult,
    Role,
    User,
)
from app.routers.common import audit, get_invoice_or_404, to_detail, to_summary
from app.schemas import (
    AuditEntry,
    DocumentLink,
    InvoiceDetail,
    InvoiceSummary,
    InvoiceUpdate,
    Page,
    ReviewAction,
    UploadItem,
    UploadResponse,
)
from app.security import client_key, create_token, decode_token, get_current_user, limiter, require_role
from app.services.intake import BACKEND_DIR, IntakeError, media_type_for, receive_document
from app.services.jobs import IN_FLIGHT, jobs
from app.services.realtime import manager

router = APIRouter(prefix="/api", tags=["invoices"])

SAMPLES_DIR = os.path.join(BACKEND_DIR, "samples")
FINAL = (InvoiceStatus.APPROVED, InvoiceStatus.REJECTED)
QUEUES = {
    "review": list(REVIEW_STATUSES),
    "processing": [s.value for s in IN_FLIGHT],
    "cleared": ["MATCHED", "APPROVED"],
    "failed": ["FAILED", "DUPLICATE"],
}
SORTS: dict[str, Any] = {
    "-created_at": Invoice.created_at.desc(), "created_at": Invoice.created_at.asc(),
    "-amount": Invoice.total_amount.desc(), "amount": Invoice.total_amount.asc(),
    "invoice_number": Invoice.invoice_number.asc(), "vendor": Invoice.vendor_name.asc(),
}


def _now():
    return datetime.now(UTC)


# ---------------------------------------------------------------- intake
@router.post("/invoices/upload", response_model=UploadResponse, status_code=202)
async def upload_invoices(request: Request, files: list[UploadFile] = File(...), db: Session = Depends(get_db),
                          user: User = Depends(require_role(Role.AP_CLERK))):
    limiter.check(client_key(request, "upload"), limit=settings.upload_rate_per_minute)
    if len(files) > 20:
        raise HTTPException(400, "Upload at most 20 files at a time")
    items: list[UploadItem] = []
    for f in files:
        data = await f.read(settings.upload_max_bytes + 1)
        try:
            res = await run_in_threadpool(receive_document, db, data, f.filename, "upload", user.email)
        except IntakeError as e:
            items.append(UploadItem(filename=f.filename or "file", status="REJECTED", error=str(e)))
            continue
        if not res.duplicate:
            jobs.enqueue(res.invoice.id)
        items.append(UploadItem(invoice_id=res.invoice.id, filename=f.filename or "file", duplicate=res.duplicate,
                                status=res.invoice.status.value,
                                error="This exact file was already received" if res.duplicate else None))
    return UploadResponse(accepted=sum(1 for i in items if i.invoice_id and not i.duplicate), items=items)


@router.post("/invoices/process-demo", response_model=UploadResponse, status_code=202)
def process_demo(db: Session = Depends(get_db), user: User = Depends(require_role(Role.ADMIN))):
    if not os.path.isdir(SAMPLES_DIR):
        raise HTTPException(404, "No sample invoices found. Run `python -m app.generate_samples`.")
    items = []
    for name in sorted(os.listdir(SAMPLES_DIR)):
        if not name.lower().endswith((".txt", ".pdf", ".png", ".jpg", ".jpeg")):
            continue
        with open(os.path.join(SAMPLES_DIR, name), "rb") as fh:
            data = fh.read()
        try:
            res = receive_document(db, data, name, "demo", user.email, allow_text=True)
        except IntakeError as e:
            items.append(UploadItem(filename=name, status="REJECTED", error=str(e)))
            continue
        if not res.duplicate:
            jobs.enqueue(res.invoice.id)
        items.append(UploadItem(invoice_id=res.invoice.id, filename=name, status=res.invoice.status.value,
                                duplicate=res.duplicate))
    return UploadResponse(accepted=sum(1 for i in items if i.invoice_id and not i.duplicate), items=items)


# ---------------------------------------------------------------- read
@router.get("/invoices", response_model=Page[InvoiceSummary])
def list_invoices(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    queue: Optional[str] = None, status: Optional[str] = None, match_result: Optional[str] = None,
    search: Optional[str] = None, currency: Optional[str] = None, issue: Optional[str] = None,
    sort: str = "-created_at", db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    q = select(Invoice)
    if queue and queue in QUEUES:
        q = q.where(Invoice.status.in_(QUEUES[queue]))
    if status:
        q = q.where(Invoice.status.in_([s.strip().upper() for s in status.split(",") if s.strip()]))
    if match_result:
        q = q.where(Invoice.match_result == match_result.upper())
    if currency:
        q = q.where(Invoice.currency == currency.upper())
    if search:
        like = f"%{search.strip()}%"
        q = q.where(or_(Invoice.invoice_number.ilike(like), Invoice.vendor_name.ilike(like),
                        Invoice.po_reference.ilike(like), Invoice.original_filename.ilike(like)))
    page_rows: list[Invoice]
    if issue:   # discrepancy type filter (JSON column, filtered in Python for portability)
        wanted = {i.strip().upper() for i in issue.split(",")}
        rows = [r for r in db.scalars(q.order_by(SORTS.get(sort, Invoice.created_at.desc()))) if any((d or {}).get("type") in wanted for d in (r.discrepancies or []))]
        total = len(rows)
        page_rows = rows[(page - 1) * page_size: page * page_size]
    else:
        total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
        page_rows = list(db.scalars(q.order_by(SORTS.get(sort, Invoice.created_at.desc()))
                                    .offset((page - 1) * page_size).limit(page_size)))
    return Page(items=[to_summary(i) for i in page_rows], total=total, page=page, page_size=page_size)


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(invoice_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    inv = db.scalars(select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.line_items))).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return to_detail(inv)


@router.get("/invoices/{invoice_id}/audit", response_model=list[AuditEntry])
def invoice_audit(invoice_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_invoice_or_404(db, invoice_id)
    return list(db.scalars(select(AuditLog).where(AuditLog.invoice_id == invoice_id).order_by(AuditLog.timestamp)))


# ---------------------------------------------------------------- documents (signed, short-lived links)
@router.get("/invoices/{invoice_id}/document-link", response_model=DocumentLink)
def document_link(invoice_id: str, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    inv = get_invoice_or_404(db, invoice_id)
    if not inv.file_path:
        raise HTTPException(404, "This invoice has no stored document")
    token = create_token(user, scope="document", minutes=10, inv=inv.id)
    url = str(request.url_for("view_invoice_document", invoice_id=inv.id)) + f"?token={token}"
    return DocumentLink(url=url, media_type=media_type_for(inv.file_path), filename=inv.original_filename, expires_in=600)


@router.get("/documents/invoice/{invoice_id}", name="view_invoice_document")
def view_invoice_document(invoice_id: str, token: str = Query(...), db: Session = Depends(get_db)):
    claims = decode_token(token, scope="document")
    if claims.get("inv") != invoice_id:
        raise HTTPException(403, "This link is for a different document")
    inv = get_invoice_or_404(db, invoice_id)
    if not inv.file_path or not os.path.exists(inv.file_path):
        raise HTTPException(404, "The document file is no longer available")
    return FileResponse(inv.file_path, media_type=media_type_for(inv.file_path),
                        headers={"Content-Disposition": f'inline; filename="{inv.original_filename or "invoice"}"',
                                 "Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"})


# ---------------------------------------------------------------- review
def _editable(inv: Invoice):
    if inv.status in FINAL:
        raise HTTPException(409, f"Invoice is already {inv.status.value.lower()}")
    if inv.status in IN_FLIGHT:
        raise HTTPException(409, "Invoice is still being processed")


@router.patch("/invoices/{invoice_id}", response_model=InvoiceDetail)
def update_invoice(invoice_id: str, body: InvoiceUpdate, db: Session = Depends(get_db),
                   user: User = Depends(require_role(Role.AP_CLERK))):
    inv = get_invoice_or_404(db, invoice_id)
    _editable(inv)
    changes = {}
    for field, value in body.model_dump(exclude_unset=True, exclude={"line_items"}).items():
        if field == "currency" and value:
            value = value.upper()
        old = getattr(inv, field)
        if old != value:
            changes[field] = {"from": str(old) if old is not None else None, "to": str(value) if value is not None else None}
            setattr(inv, field, value)
    if body.line_items is not None:
        inv.line_items = [
            InvoiceLineItem(line_no=i, item_code=l.item_code, description=l.description, quantity=l.quantity,
                            unit_price=l.unit_price, uom=l.uom,
                            total_price=l.total_price if l.total_price is not None else round(l.quantity * l.unit_price, 2))
            for i, l in enumerate(body.line_items, start=1)
        ]
        changes["line_items"] = {"to": f"{len(body.line_items)} line(s)"}
    if changes:
        edits = dict((inv.validation or {}).get("edited_fields") or {})
        edits.update({k: user.email for k in changes})
        inv.validation = {**(inv.validation or {}), "edited_fields": edits}
        audit(db, inv.id, "FIELDS_EDITED", user.email, changes)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409, "Another live invoice from this vendor already has this invoice number") from e
    db.refresh(inv)
    return to_detail(inv)


@router.post("/invoices/{invoice_id}/rematch", response_model=InvoiceDetail)
async def rematch(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.AP_CLERK))):
    inv = get_invoice_or_404(db, invoice_id)
    if inv.status not in (InvoiceStatus.MATCHED, InvoiceStatus.DISCREPANCY, InvoiceStatus.ON_HOLD):
        raise HTTPException(409, f"Invoices in status {inv.status.value} cannot be re-matched")
    await run_in_threadpool(OrchestratorAgent().rematch, invoice_id, user.email)
    db.expire_all()
    return to_detail(get_invoice_or_404(db, invoice_id))


UNDO_WINDOW = timedelta(minutes=15)


def _decide(db: Session, inv: Invoice, status: InvoiceStatus, user: User, note: Optional[str], action: str):
    previous = inv.status.value
    inv.status = status
    inv.reviewed_by = user.email
    inv.reviewed_at = _now()
    inv.review_note = note
    audit(db, inv.id, action, user.email,
          {"note": note, "match_result": inv.match_result.value, "previous_status": previous})
    db.commit()
    db.refresh(inv)
    manager.publish({"event": "review_update", "invoice_id": inv.id, "status": status.value,
                     "invoice_number": inv.invoice_number, "actor": user.email})
    return to_detail(inv)


@router.post("/invoices/{invoice_id}/reopen", response_model=InvoiceDetail)
def reopen(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.AP_CLERK))):
    """Undo the most recent decision (approve / reject / hold) within 15 minutes."""
    inv = get_invoice_or_404(db, invoice_id)
    last = db.scalars(select(AuditLog).where(AuditLog.invoice_id == invoice_id,
                                             AuditLog.action.in_(["APPROVED", "APPROVED_OVERRIDE", "REJECTED", "HELD",
                                                                  "REOPENED"]))
                      .order_by(AuditLog.timestamp.desc())).first()
    if not last or last.action == "REOPENED" or not (last.details or {}).get("previous_status"):
        raise HTTPException(409, "There is no decision to undo on this invoice")
    if last.actor != user.email and user.role != Role.ADMIN:
        raise HTTPException(403, "Only the person who made the decision can undo it")
    when = last.timestamp
    if when is not None and when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    if when is None or _now() - when > UNDO_WINDOW:
        raise HTTPException(409, "Decisions can only be undone within 15 minutes")
    inv.status = InvoiceStatus((last.details or {})["previous_status"])
    inv.reviewed_by = inv.reviewed_at = inv.review_note = None
    audit(db, inv.id, "REOPENED", user.email, {"undid": last.action})
    db.commit()
    db.refresh(inv)
    manager.publish({"event": "review_update", "invoice_id": inv.id, "status": inv.status.value,
                     "invoice_number": inv.invoice_number, "actor": user.email})
    return to_detail(inv)


@router.post("/invoices/{invoice_id}/approve", response_model=InvoiceDetail)
def approve(invoice_id: str, body: ReviewAction, db: Session = Depends(get_db),
            user: User = Depends(require_role(Role.APPROVER))):
    inv = get_invoice_or_404(db, invoice_id)
    if inv.status not in (InvoiceStatus.MATCHED, InvoiceStatus.DISCREPANCY, InvoiceStatus.ON_HOLD):
        raise HTTPException(409, f"An invoice in status {inv.status.value} cannot be approved")
    blocking = [d for d in (inv.discrepancies or []) if d.get("severity") == "HIGH"]
    if blocking and not (body.note and body.note.strip()):
        raise HTTPException(422, "This invoice has unresolved high-severity issues. Add a note explaining the override.")
    return _decide(db, inv, InvoiceStatus.APPROVED, user, body.note, "APPROVED" if not blocking else "APPROVED_OVERRIDE")


@router.post("/invoices/{invoice_id}/reject", response_model=InvoiceDetail)
def reject(invoice_id: str, body: ReviewAction, db: Session = Depends(get_db),
           user: User = Depends(require_role(Role.APPROVER))):
    inv = get_invoice_or_404(db, invoice_id)
    if inv.status in FINAL or inv.status in IN_FLIGHT:
        raise HTTPException(409, f"An invoice in status {inv.status.value} cannot be rejected")
    if not (body.note and body.note.strip()):
        raise HTTPException(422, "Add a reason for the rejection")
    return _decide(db, inv, InvoiceStatus.REJECTED, user, body.note, "REJECTED")


@router.post("/invoices/{invoice_id}/hold", response_model=InvoiceDetail)
def hold(invoice_id: str, body: ReviewAction, db: Session = Depends(get_db),
         user: User = Depends(require_role(Role.AP_CLERK))):
    inv = get_invoice_or_404(db, invoice_id)
    if inv.status not in (InvoiceStatus.MATCHED, InvoiceStatus.DISCREPANCY, InvoiceStatus.ON_HOLD):
        raise HTTPException(409, f"An invoice in status {inv.status.value} cannot be put on hold")
    return _decide(db, inv, InvoiceStatus.ON_HOLD, user, body.note, "HELD")


@router.post("/invoices/{invoice_id}/retry", response_model=InvoiceDetail)
def retry(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.AP_CLERK))):
    inv = get_invoice_or_404(db, invoice_id)
    if inv.status != InvoiceStatus.FAILED:
        raise HTTPException(409, "Only failed invoices can be retried")
    inv.status = InvoiceStatus.RECEIVED
    inv.error = None
    inv.match_result = MatchResult.PENDING
    audit(db, inv.id, "RETRY", user.email)
    db.commit()
    jobs.enqueue(inv.id)
    return to_detail(inv)


@router.get("/matches", response_model=Page[InvoiceSummary])
def list_matches(result: Optional[str] = None, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                 db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Invoices that have a match verdict. Uses the snapshot stored at match time (no ERP round-trips)."""
    q = select(Invoice).where(Invoice.match_result != MatchResult.PENDING)
    if result:
        q = q.where(Invoice.match_result == result.upper())
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[to_summary(i) for i in rows], total=total, page=page, page_size=page_size)
