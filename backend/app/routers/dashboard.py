from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import String, case, func, select
from sqlalchemy.orm import Session

from app.agents.orchestrator import OrchestratorAgent
from app.database import get_db
from app.models import REVIEW_STATUSES, Invoice, InvoiceStatus, MatchResult, User
from app.schemas import CurrencyTotal, DashboardStats, HealthResponse
from app.security import get_current_user
from app.services.jobs import IN_FLIGHT, jobs

router = APIRouter(prefix="/api", tags=["dashboard"])


def _count(cond):
    return func.coalesce(func.sum(case((cond, 1), else_=0)), 0)


PRIMARY_CURRENCY = "INR"   # always listed first; the rest follow by amount


def _by_currency(db: Session, *conds) -> list[CurrencyTotal]:
    q = (select(Invoice.currency, func.sum(Invoice.total_amount), func.count(Invoice.id))
         .where(*conds).group_by(Invoice.currency)
         .order_by(case((Invoice.currency == PRIMARY_CURRENCY, 0), else_=1), func.sum(Invoice.total_amount).desc()))
    return [CurrencyTotal(currency=c or "—", amount=round(float(a or 0), 2), count=n) for c, a, n in db.execute(q)]


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    s = db.execute(select(
        func.count(Invoice.id),
        _count(Invoice.match_result == MatchResult.FULL_MATCH),
        _count(Invoice.match_result == MatchResult.PARTIAL_MATCH),
        _count(Invoice.match_result == MatchResult.NO_MATCH),
        _count(Invoice.match_result == MatchResult.PENDING),
        _count(Invoice.status == InvoiceStatus.FAILED),
        _count(Invoice.status == InvoiceStatus.DUPLICATE),
        _count(Invoice.status == InvoiceStatus.DISCREPANCY),
        _count(Invoice.status == InvoiceStatus.ON_HOLD),
        _count(Invoice.status == InvoiceStatus.APPROVED),
        _count(Invoice.status == InvoiceStatus.REJECTED),
        _count(Invoice.status.in_(IN_FLIGHT)),
        func.avg(Invoice.processing_time),
        func.avg(case((Invoice.confidence_score > 0, Invoice.confidence_score), else_=None)),
    )).one()
    total, full, partial, nomatch, pending, failed, dup, review, hold, approved, rejected, processing, avg_t, avg_c = s
    decided = full + partial + nomatch

    # Issue types across invoices currently waiting for review
    issues: Counter[str] = Counter()
    vendors: Counter[str] = Counter()
    for discs, vendor in db.execute(select(Invoice.discrepancies, Invoice.vendor_name)
                                    .where(Invoice.status.in_(REVIEW_STATUSES))):
        types = {str(d.get("type")) for d in (discs or []) if isinstance(d, dict) and d.get("severity") in ("HIGH", "MEDIUM")}
        issues.update(types)
        if types:
            vendors[vendor or "Unknown vendor"] += 1

    since = datetime.now(UTC) - timedelta(days=30)
    day = func.date(Invoice.created_at, type_=String)   # works on SQLite and PostgreSQL
    daily = [{"date": str(d), "received": n, "auto_matched": m, "exceptions": e} for d, n, m, e in db.execute(
        select(day, func.count(Invoice.id), _count(Invoice.status == InvoiceStatus.MATCHED),
               _count(Invoice.status.in_(list(REVIEW_STATUSES) + ["REJECTED", "DUPLICATE", "FAILED"])))
        .where(Invoice.created_at >= since).group_by(day).order_by(day))]

    start_today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    t = db.execute(select(
        func.count(Invoice.id),
        _count(Invoice.status == InvoiceStatus.MATCHED),
    ).where(Invoice.created_at >= start_today)).one()
    decided_today = db.execute(select(
        _count(Invoice.status == InvoiceStatus.APPROVED), _count(Invoice.status == InvoiceStatus.REJECTED),
    ).where(Invoice.reviewed_at >= start_today)).one()

    return DashboardStats(
        total_invoices=total, matched=full, partial_match=partial, no_match=nomatch, pending=pending, failed=failed,
        duplicates=dup, in_review=review, on_hold=hold, approved=approved, rejected=rejected, processing=processing,
        auto_match_rate=round(full / decided, 3) if decided else 0.0,
        avg_processing_time=round(float(avg_t or 0), 2), avg_confidence=round(float(avg_c or 0), 2),
        value_by_currency=_by_currency(db),
        cleared_by_currency=_by_currency(db, Invoice.status.in_([InvoiceStatus.MATCHED, InvoiceStatus.APPROVED])),
        held_by_currency=_by_currency(db, Invoice.status.in_(REVIEW_STATUSES)),
        issues_by_type=[{"type": k, "count": v} for k, v in issues.most_common(8)],
        vendors_to_watch=[{"vendor": k, "open_exceptions": v} for k, v in vendors.most_common(5)],
        daily=daily,
        today={"received": t[0], "auto_matched": t[1], "approved": decided_today[0], "rejected": decided_today[1],
               "waiting": review + hold},
    )


@router.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)):
    h = await OrchestratorAgent().get_pipeline_health(db)
    groq = h["vision_ocr"].get("groq_status")
    erp_ok = h["erp"].get("status") == "online"
    overall = "healthy" if groq == "online" and erp_ok else ("degraded" if erp_ok or groq == "online" else "unhealthy")
    return HealthResponse(status=overall, orchestrator=h["orchestrator"], vision_ocr=h["vision_ocr"], erp=h["erp"],
                          queue_depth=jobs.depth, timestamp=h["timestamp"])
