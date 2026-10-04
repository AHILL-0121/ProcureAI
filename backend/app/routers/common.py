from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AuditLog, Invoice
from app.schemas import InvoiceDetail, InvoiceSummary

SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def top_issue(inv: Invoice) -> tuple[str | None, str | None, str | None, int]:
    items = [d for d in (inv.discrepancies or []) if isinstance(d, dict)]
    if not items:
        if inv.error:
            return inv.error, "FAILED", "HIGH", 1
        return None, None, None, 0
    items.sort(key=lambda d: SEVERITY_RANK.get(str(d.get("severity")), 3))
    d = items[0]
    return d.get("message"), d.get("type"), d.get("severity"), len(items)


def to_summary(inv: Invoice) -> InvoiceSummary:
    s = InvoiceSummary.model_validate(inv)
    s.top_issue, s.top_issue_code, s.top_issue_severity, s.issue_count = top_issue(inv)
    return s


def to_detail(inv: Invoice) -> InvoiceDetail:
    d = InvoiceDetail.model_validate(inv)
    d.top_issue, d.top_issue_code, d.top_issue_severity, d.issue_count = top_issue(inv)
    d.extraction = (inv.extracted_data or {}).get("_metadata")
    return d


def get_invoice_or_404(db: Session, invoice_id: str) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return inv


def audit(db: Session, invoice_id: str | None, action: str, actor: str | None, details: dict | None = None,
          agent: str = "user"):
    db.add(AuditLog(invoice_id=invoice_id, agent=agent, actor=actor, action=action, details=details or {}))
