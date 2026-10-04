"""v2: review workflow, auth, tolerances, typed money/dates, rebuilt ERP tables

- invoices: review fields, match snapshot/checks, file hash, vendor key, Date/Numeric types,
  timezone-aware timestamps, indexes, and a partial unique index for duplicate protection
- invoice_line_items: line_no, uom, matched PO line
- audit_logs: actor
- new: users, tolerance_rules, erp_invoices, erp_pr_headers, erp_pr_lines
- ERP tables are rebuilt with the v2 layout. **Reload them afterwards:** `python -m app.seed_erp --reset`
- legacy purchase_orders / goods_receipts tables (unused mock data) are dropped

Revision ID: 0002_v2
Revises: 0001_legacy
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from alembic import op

from app.extraction import parse_date

revision = "0002_v2"
down_revision = "0001_legacy"
branch_labels = None
depends_on = None

MONEY = sa.Numeric(14, 2, asdecimal=False)
QTY = sa.Numeric(14, 3, asdecimal=False)
TS = sa.DateTime(timezone=True)
NEW_STATUSES = ("ON_HOLD", "APPROVED", "REJECTED", "DUPLICATE")
LIVE_WHERE = ("status NOT IN ('DUPLICATE','FAILED','REJECTED') AND vendor_key IS NOT NULL "
              "AND invoice_number IS NOT NULL")


def _is_pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_erp_tables():
    op.create_table(
        "erp_vendors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("supplier_name", sa.String(), nullable=True),
        sa.Column("tax_id", sa.String(), nullable=True),
        sa.Column("pay_terms", sa.String(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("created_at", TS, nullable=True),
    )
    op.create_index("ix_erp_vendors_supplier_id", "erp_vendors", ["supplier_id"], unique=True)
    op.create_index("ix_erp_vendors_supplier_name", "erp_vendors", ["supplier_name"])
    op.create_index("ix_erp_vendors_tax_id", "erp_vendors", ["tax_id"])

    op.create_table(
        "erp_materials",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("item_number", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("uom", sa.String(), nullable=True),
        sa.Column("created_at", TS, nullable=True),
    )
    op.create_index("ix_erp_materials_item_id", "erp_materials", ["item_id"], unique=True)
    op.create_index("ix_erp_materials_item_number", "erp_materials", ["item_number"])

    op.create_table(
        "erp_po_headers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("po_header_id", sa.String(), nullable=True),
        sa.Column("po_number", sa.String(), nullable=True),
        sa.Column("supplier_id", sa.String(), sa.ForeignKey("erp_vendors.supplier_id"), nullable=True),
        sa.Column("creation_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", TS, nullable=True),
    )
    op.create_index("ix_erp_po_headers_po_header_id", "erp_po_headers", ["po_header_id"], unique=True)
    op.create_index("ix_erp_po_headers_po_number", "erp_po_headers", ["po_number"], unique=True)
    op.create_index("ix_erp_po_headers_supplier_id", "erp_po_headers", ["supplier_id"])

    op.create_table(
        "erp_po_lines",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("po_line_id", sa.String(), nullable=True),
        sa.Column("po_header_id", sa.String(), sa.ForeignKey("erp_po_headers.po_header_id"), nullable=True),
        sa.Column("line_num", sa.Integer(), nullable=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("erp_materials.item_id"), nullable=True),
        sa.Column("uom", sa.String(), nullable=True),
        sa.Column("quantity", QTY, nullable=True),
        sa.Column("unit_price", MONEY, nullable=True),
        sa.Column("line_amount", MONEY, nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("created_at", TS, nullable=True),
    )
    op.create_index("ix_erp_po_lines_po_line_id", "erp_po_lines", ["po_line_id"], unique=True)
    op.create_index("ix_erp_po_lines_po_header_id", "erp_po_lines", ["po_header_id"])

    op.create_table(
        "erp_goods_receipts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("receipt_id", sa.String(), nullable=True),
        sa.Column("po_line_id", sa.String(), sa.ForeignKey("erp_po_lines.po_line_id"), nullable=True),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("quantity_received", QTY, nullable=True),
        sa.Column("uom", sa.String(), nullable=True),
        sa.Column("receipt_date", sa.Date(), nullable=True),
        sa.Column("created_at", TS, nullable=True),
    )
    op.create_index("ix_erp_goods_receipts_receipt_id", "erp_goods_receipts", ["receipt_id"], unique=True)
    op.create_index("ix_erp_goods_receipts_po_line_id", "erp_goods_receipts", ["po_line_id"])

    op.create_table(
        "erp_invoices",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("erp_invoice_id", sa.String(), nullable=True),
        sa.Column("invoice_number", sa.String(), nullable=True),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("po_line_id", sa.String(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("invoiced_qty", QTY, nullable=True),
        sa.Column("uom", sa.String(), nullable=True),
        sa.Column("unit_price", MONEY, nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("amount", MONEY, nullable=True),
    )
    op.create_index("ix_erp_invoices_erp_invoice_id", "erp_invoices", ["erp_invoice_id"], unique=True)
    op.create_index("ix_erp_invoices_invoice_number", "erp_invoices", ["invoice_number"])
    op.create_index("ix_erp_invoices_supplier_id", "erp_invoices", ["supplier_id"])
    op.create_index("ix_erp_invoices_po_line_id", "erp_invoices", ["po_line_id"])

    op.create_table(
        "erp_pr_headers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("pr_header_id", sa.String(), nullable=True),
        sa.Column("pr_number", sa.String(), nullable=True),
        sa.Column("requester_id", sa.String(), nullable=True),
        sa.Column("creation_date", sa.Date(), nullable=True),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
    )
    op.create_index("ix_erp_pr_headers_pr_header_id", "erp_pr_headers", ["pr_header_id"], unique=True)
    op.create_index("ix_erp_pr_headers_pr_number", "erp_pr_headers", ["pr_number"], unique=True)

    op.create_table(
        "erp_pr_lines",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("pr_line_id", sa.String(), nullable=True),
        sa.Column("pr_header_id", sa.String(), nullable=True),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("uom", sa.String(), nullable=True),
        sa.Column("quantity", QTY, nullable=True),
        sa.Column("required_date", sa.Date(), nullable=True),
        sa.Column("est_unit_price", MONEY, nullable=True),
    )
    op.create_index("ix_erp_pr_lines_pr_line_id", "erp_pr_lines", ["pr_line_id"], unique=True)
    op.create_index("ix_erp_pr_lines_pr_header_id", "erp_pr_lines", ["pr_header_id"])


def _convert_dates(table: str, columns: list[str]):
    """String → Date columns, parsing whatever format the old LLM output used."""
    bind = op.get_bind()
    with op.batch_alter_table(table) as b:
        for c in columns:
            b.add_column(sa.Column(f"{c}__new", sa.Date(), nullable=True))
    t = sa.table(table, sa.column("id", sa.String()), *[sa.column(c, sa.String()) for c in columns],
                 *[sa.column(f"{c}__new", sa.Date()) for c in columns])
    rows = bind.execute(sa.select(t.c.id, *[t.c[c] for c in columns])).all()
    for row in rows:
        values = {f"{c}__new": parse_date(row[i + 1]) for i, c in enumerate(columns)}
        bind.execute(t.update().where(t.c.id == row[0]).values(**values))
    with op.batch_alter_table(table) as b:
        for c in columns:
            b.drop_column(c)
    with op.batch_alter_table(table) as b:
        for c in columns:
            b.alter_column(f"{c}__new", new_column_name=c)


def upgrade() -> None:
    pg = _is_pg()
    if pg:
        with op.get_context().autocommit_block():
            for s in NEW_STATUSES:
                op.execute(f"ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS '{s}'")

    # ---- legacy mock tables and old ERP layout
    for t in ("purchase_orders", "goods_receipts", "erp_goods_receipts", "erp_po_lines", "erp_po_headers",
              "erp_materials", "erp_vendors"):
        op.drop_table(t)
    _create_erp_tables()

    # ---- invoices
    with op.batch_alter_table("invoices") as b:
        b.add_column(sa.Column("vendor_key", sa.String(), nullable=True))
        b.add_column(sa.Column("vendor_tax_id", sa.String(), nullable=True))
        b.add_column(sa.Column("subtotal", MONEY, nullable=True))
        b.add_column(sa.Column("match_score", sa.Float(), nullable=True))
        b.add_column(sa.Column("validation", sa.JSON(), nullable=True))
        b.add_column(sa.Column("match_checks", sa.JSON(), nullable=True))
        b.add_column(sa.Column("match_snapshot", sa.JSON(), nullable=True))
        b.add_column(sa.Column("duplicate_of", sa.String(), nullable=True))
        b.add_column(sa.Column("original_filename", sa.String(), nullable=True))
        b.add_column(sa.Column("file_hash", sa.String(64), nullable=True))
        b.add_column(sa.Column("error", sa.Text(), nullable=True))
        b.add_column(sa.Column("reviewed_by", sa.String(), nullable=True))
        b.add_column(sa.Column("reviewed_at", TS, nullable=True))
        b.add_column(sa.Column("review_note", sa.Text(), nullable=True))
        b.alter_column("total_amount", type_=MONEY, existing_type=sa.Float())
        b.alter_column("tax_amount", type_=MONEY, existing_type=sa.Float())
        b.alter_column("currency", type_=sa.String(3), existing_type=sa.String())
        if pg:
            b.alter_column("created_at", type_=TS, existing_type=sa.DateTime(),
                           postgresql_using="created_at AT TIME ZONE 'UTC'")
            b.alter_column("updated_at", type_=TS, existing_type=sa.DateTime(),
                           postgresql_using="updated_at AT TIME ZONE 'UTC'")
        else:
            b.alter_column("created_at", type_=TS, existing_type=sa.DateTime())
            b.alter_column("updated_at", type_=TS, existing_type=sa.DateTime())
        b.create_foreign_key("fk_invoices_duplicate_of", "invoices", ["duplicate_of"], ["id"])
    _convert_dates("invoices", ["invoice_date", "due_date"])
    for col in ("vendor_id", "vendor_key", "status", "match_result", "file_hash", "created_at"):
        op.create_index(f"ix_invoices_{col}", "invoices", [col])
    op.create_index("uq_invoice_vendor_number_live", "invoices", ["vendor_key", "invoice_number"], unique=True,
                    postgresql_where=sa.text(LIVE_WHERE), sqlite_where=sa.text(LIVE_WHERE))

    # ---- invoice lines
    with op.batch_alter_table("invoice_line_items") as b:
        b.add_column(sa.Column("line_no", sa.Integer(), nullable=True))
        b.add_column(sa.Column("uom", sa.String(), nullable=True))
        b.add_column(sa.Column("matched_po_line_id", sa.String(), nullable=True))
        b.alter_column("quantity", type_=QTY, existing_type=sa.Float())
        b.alter_column("unit_price", type_=MONEY, existing_type=sa.Float())
        b.alter_column("total_price", type_=MONEY, existing_type=sa.Float())
    op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])
    op.create_index("ix_invoice_line_items_matched_po_line_id", "invoice_line_items", ["matched_po_line_id"])

    # ---- audit
    with op.batch_alter_table("audit_logs") as b:
        b.add_column(sa.Column("actor", sa.String(), nullable=True))
        if pg:
            b.alter_column("timestamp", type_=TS, existing_type=sa.DateTime(),
                           postgresql_using="\"timestamp\" AT TIME ZONE 'UTC'")
        else:
            b.alter_column("timestamp", type_=TS, existing_type=sa.DateTime())
    op.create_index("ix_audit_logs_invoice_id", "audit_logs", ["invoice_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # ---- auth & settings
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.Enum("viewer", "ap_clerk", "approver", "admin", name="role"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", TS, nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "tolerance_rules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("vendor_id", sa.String(), nullable=True, unique=True),
        sa.Column("qty_pct", sa.Float(), nullable=False),
        sa.Column("price_pct", sa.Float(), nullable=False),
        sa.Column("price_abs", sa.Float(), nullable=False),
        sa.Column("total_abs", sa.Float(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", TS, nullable=True),
    )


def downgrade() -> None:
    raise NotImplementedError("v2 → v1 is not supported; restore a backup instead")
