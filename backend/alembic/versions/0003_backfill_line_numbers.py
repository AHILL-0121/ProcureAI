"""Number invoice lines created before v2 (line_no was added empty by 0002)

Revision ID: 0003_line_no
Revises: 0002_v2
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_line_no"
down_revision = "0002_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, invoice_id FROM invoice_line_items WHERE line_no IS NULL ORDER BY invoice_id, id")).all()
    counters: dict[str, int] = {}
    for line_id, invoice_id in rows:
        start = counters.get(invoice_id)
        if start is None:
            start = bind.execute(sa.text(
                "SELECT COALESCE(MAX(line_no), 0) FROM invoice_line_items WHERE invoice_id = :i"),
                {"i": invoice_id}).scalar() or 0
        counters[invoice_id] = start + 1
        bind.execute(sa.text("UPDATE invoice_line_items SET line_no = :n WHERE id = :id"),
                     {"n": counters[invoice_id], "id": line_id})


def downgrade() -> None:
    pass
