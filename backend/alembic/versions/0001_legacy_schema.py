"""Legacy schema (v1, created by Base.metadata.create_all before Alembic existed)

Existing v1 databases: run `alembic stamp 0001_legacy` once, then `alembic upgrade head`.
New databases: `alembic upgrade head` runs this and every later revision.

Revision ID: 0001_legacy
Revises:
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_legacy"
down_revision = None
branch_labels = None
depends_on = None

status_enum = sa.Enum("RECEIVED", "EXTRACTING", "EXTRACTED", "VALIDATING", "VALIDATED", "MATCHING", "MATCHED",
                      "DISCREPANCY", "FAILED", name="invoicestatus")
type_enum = sa.Enum("STANDARD", "CREDIT_NOTE", "DEBIT_NOTE", "PRO_FORMA", name="invoicetype")
result_enum = sa.Enum("FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH", "PENDING", name="matchresult")


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("invoice_number", sa.String(), index=True),
        sa.Column("vendor_name", sa.String()),
        sa.Column("vendor_id", sa.String()),
        sa.Column("invoice_date", sa.String()),
        sa.Column("due_date", sa.String(), nullable=True),
        sa.Column("total_amount", sa.Float()),
        sa.Column("tax_amount", sa.Float()),
        sa.Column("currency", sa.String()),
        sa.Column("po_reference", sa.String(), nullable=True, index=True),
        sa.Column("status", status_enum),
        sa.Column("invoice_type", type_enum),
        sa.Column("match_result", result_enum),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("discrepancies", sa.JSON(), nullable=True),
        sa.Column("source_email", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("processing_time", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("invoice_id", sa.String(), sa.ForeignKey("invoices.id")),
        sa.Column("description", sa.String()),
        sa.Column("quantity", sa.Float()),
        sa.Column("unit_price", sa.Float()),
        sa.Column("total_price", sa.Float()),
        sa.Column("item_code", sa.String(), nullable=True),
    )
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("po_number", sa.String(), unique=True, index=True),
        sa.Column("vendor_name", sa.String()), sa.Column("vendor_id", sa.String()),
        sa.Column("order_date", sa.String()), sa.Column("expected_delivery", sa.String(), nullable=True),
        sa.Column("total_amount", sa.Float()), sa.Column("tax_amount", sa.Float()), sa.Column("currency", sa.String()),
        sa.Column("status", sa.String()), sa.Column("items", sa.JSON()), sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("grn_number", sa.String(), unique=True, index=True), sa.Column("po_number", sa.String(), index=True),
        sa.Column("vendor_name", sa.String()), sa.Column("receipt_date", sa.String()),
        sa.Column("received_by", sa.String(), nullable=True), sa.Column("items", sa.JSON()),
        sa.Column("status", sa.String()), sa.Column("notes", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("invoice_id", sa.String(), nullable=True),
        sa.Column("agent", sa.String()), sa.Column("action", sa.String()),
        sa.Column("details", sa.JSON(), nullable=True), sa.Column("timestamp", sa.DateTime()),
    )
    op.create_table(
        "erp_vendors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("supplier_id", sa.String(), unique=True, index=True),
        sa.Column("supplier_name", sa.String()), sa.Column("supplier_type", sa.String(), nullable=True),
        sa.Column("tax_id", sa.String(), nullable=True), sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "erp_materials",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), unique=True, index=True),
        sa.Column("description", sa.String()), sa.Column("category", sa.String(), nullable=True),
        sa.Column("uom", sa.String(), nullable=True), sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "erp_po_headers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("po_header_id", sa.String(), unique=True, index=True),
        sa.Column("po_number", sa.String(), unique=True, index=True),
        sa.Column("supplier_id", sa.String(), sa.ForeignKey("erp_vendors.supplier_id")),
        sa.Column("creation_date", sa.String()), sa.Column("currency", sa.String()), sa.Column("status", sa.String()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "erp_po_lines",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("po_line_id", sa.String(), unique=True, index=True),
        sa.Column("po_header_id", sa.String(), sa.ForeignKey("erp_po_headers.po_header_id")),
        sa.Column("line_num", sa.Integer()),
        sa.Column("item_id", sa.String(), sa.ForeignKey("erp_materials.item_id")),
        sa.Column("quantity", sa.Float()), sa.Column("unit_price", sa.Float()), sa.Column("line_amount", sa.Float()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "erp_goods_receipts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("receipt_id", sa.String(), unique=True, index=True),
        sa.Column("po_line_id", sa.String(), sa.ForeignKey("erp_po_lines.po_line_id")),
        sa.Column("quantity_received", sa.Float()), sa.Column("receipt_date", sa.String()),
        sa.Column("created_at", sa.DateTime()), sa.Column("action", sa.String()),
        sa.Column("details", sa.JSON(), nullable=True), sa.Column("timestamp", sa.DateTime()),
    )


def downgrade() -> None:
    for t in ("erp_goods_receipts", "erp_po_lines", "erp_po_headers", "erp_materials", "erp_vendors", "audit_logs",
              "goods_receipts", "purchase_orders", "invoice_line_items", "invoices"):
        op.drop_table(t)
    bind = op.get_bind()
    for e in (status_enum, type_enum, result_enum):
        e.drop(bind, checkfirst=True)
