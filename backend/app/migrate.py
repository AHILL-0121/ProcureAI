"""
Bring the database to the latest schema and make sure ERP data is present.

    python -m app.migrate

- Runs automatically when the API starts; can also be run by hand.
- Fresh database: runs every migration.
- v1 database created before Alembic (has `invoices` but no `alembic_version`): stamps it as
  `0001_legacy` first, then upgrades.
- Loads the sample ERP CSVs when the ERP tables are empty, unless ERP_SAMPLE_DATA=false.
"""

import logging
import os

from sqlalchemy import inspect

from alembic import command
from alembic.config import Config
from app.config import settings
from app.database import SessionLocal, engine
from app.seed_erp import seed

logger = logging.getLogger(__name__)
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))


def run():
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.attributes["configure_logger"] = False
    tables = set(inspect(engine).get_table_names())
    if "invoices" in tables and "alembic_version" not in tables:
        logger.info("Existing v1 database detected: stamping 0001_legacy")
        command.stamp(cfg, "0001_legacy")
    command.upgrade(cfg, "head")
    if not settings.erp_sample_data:
        logger.info("ERP sample data disabled (ERP_SAMPLE_DATA=false): import your data in Settings")
        return
    with SessionLocal() as db:
        result = seed(db)
    logger.info("ERP data: %s", "already loaded" if result.get("skipped") else result)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()
