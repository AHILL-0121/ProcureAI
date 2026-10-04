from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.matching import Tolerance
from app.config import settings
from app.models import ToleranceRule


def default_tolerance() -> Tolerance:
    return Tolerance(qty_pct=settings.tolerance_qty_pct, price_pct=settings.tolerance_price_pct,
                     price_abs=settings.tolerance_price_abs, total_abs=settings.tolerance_total_abs)


def _from_rule(r: ToleranceRule) -> Tolerance:
    return Tolerance(qty_pct=r.qty_pct, price_pct=r.price_pct, price_abs=r.price_abs, total_abs=r.total_abs)


def get_tolerance(db: Session, vendor_id: Optional[str]) -> Tolerance:
    """Vendor-specific rule, else the global rule, else configured defaults."""
    if vendor_id:
        r = db.scalars(select(ToleranceRule).where(ToleranceRule.vendor_id == str(vendor_id))).first()
        if r:
            return _from_rule(r)
    r = db.scalars(select(ToleranceRule).where(ToleranceRule.vendor_id.is_(None))).first()
    return _from_rule(r) if r else default_tolerance()
