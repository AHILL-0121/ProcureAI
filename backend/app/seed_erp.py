"""
Load the Oracle migration dataset (backend/data/erp/*.csv) into the ERP tables.

    python -m app.seed_erp            # load if the ERP tables are empty
    python -m app.seed_erp --reset    # wipe ERP tables and reload

Parsing and validation live in `app/services/erp_import.py`, shared with the ERP Connect import in Settings.
"""

import argparse
import csv
import logging
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import POHeader
from app.services.erp_import import apply_plan, build_plan, norm_id, read_directory

__all__ = ["seed", "norm_id", "read_csv", "DATA_DIR"]

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "erp")


def read_csv(name: str, data_dir: str = DATA_DIR) -> list[dict]:
    """Raw rows of one dataset file (used by generate_samples)."""
    path = os.path.join(data_dir, name)
    if not os.path.exists(path):
        logger.warning("ERP CSV missing: %s", path)
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def seed(db: Session, reset: bool = False, data_dir: str = DATA_DIR) -> dict:
    """Load the CSV dataset through the same validation as an ERP Connect import (mode "replace")."""
    if not reset and db.scalar(select(func.count()).select_from(POHeader)):
        logger.info("ERP tables already populated; use --reset to reload")
        return {"skipped": True}
    plan = build_plan(db, read_directory(data_dir), mode="replace")
    if not plan.ok:
        raise ValueError(f"ERP dataset in {data_dir} has errors: {plan.summary()}")
    counts = apply_plan(db, plan)
    logger.info("ERP dataset loaded: %s", counts)
    return counts


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load the ERP CSV dataset into the database")
    parser.add_argument("--reset", action="store_true", help="delete existing ERP rows first")
    args = parser.parse_args()
    init_db()
    with SessionLocal() as db:
        print(seed(db, reset=args.reset))


if __name__ == "__main__":
    main()
