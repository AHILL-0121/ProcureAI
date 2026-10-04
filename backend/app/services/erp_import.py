"""
ERP Connect, phase 1: load a company's ERP data from CSV files.

The same eight layouts as `backend/data/erp/*.csv` (the sample dataset uses this code too, via `seed_erp`).
Files are recognised by name (`po_lines.csv`) or, failing that, by their header row.

Nothing is written until every row is valid: `build_plan` parses and checks everything and returns a report;
`apply_plan` writes it in one transaction.

Modes:
- merge:   insert new rows and update existing ones by their ERP id. Nothing is deleted.
- replace: empty every ERP table, then load the files. Needs vendors, PO headers and PO lines.
"""

import csv
import io
import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.extraction import ISO_4217, parse_date, parse_number
from app.models import (
    ERPInvoice,
    GoodsReceiptERP,
    Material,
    POHeader,
    POLine,
    PRHeader,
    PRLine,
    Vendor,
    generate_uuid,
)

Mode = Literal["merge", "replace"]
MAX_ERRORS_PER_FILE = 25


@dataclass(frozen=True)
class Column:
    name: str            # CSV header
    attr: str            # model attribute
    kind: str = "text"   # id | text | num | date | currency | upper
    required: bool = False
    positive: bool = False   # numbers that can't be negative


@dataclass(frozen=True)
class Entity:
    name: str            # also the file stem
    label: str
    model: Any
    key: str             # CSV column holding the ERP id
    columns: tuple[Column, ...]
    refs: tuple[tuple[str, str], ...] = ()   # (column, referenced entity); checked when the value is present

    @property
    def key_attr(self) -> str:
        return next(c.attr for c in self.columns if c.name == self.key)

    @property
    def required(self) -> list[str]:
        return [c.name for c in self.columns if c.required]


# Parents before children: this is the insert order. Deletes run in reverse.
ENTITIES: tuple[Entity, ...] = (
    Entity("vendors", "Vendors", Vendor, "SUPPLIER_ID", (
        Column("SUPPLIER_ID", "supplier_id", "id", True),
        Column("SUPPLIER_NAME", "supplier_name", "text", True),
        Column("TAX_ID", "tax_id"),
        Column("PAY_TERMS", "pay_terms"),
        Column("CURRENCY", "currency", "currency"),
    )),
    Entity("materials", "Materials", Material, "ITEM_ID", (
        Column("ITEM_ID", "item_id", "id", True),
        Column("DESCRIPTION", "description", "text", True),
        Column("ITEM_NUMBER", "item_number"),
        Column("UOM", "uom"),
        Column("CATEGORY", "category"),
    )),
    Entity("po_headers", "Purchase orders", POHeader, "PO_HEADER_ID", (
        Column("PO_HEADER_ID", "po_header_id", "id", True),
        Column("PO_NUMBER", "po_number", "text", True),
        Column("SUPPLIER_ID", "supplier_id", "id"),
        Column("CURRENCY", "currency", "currency", True),
        Column("CREATION_DATE", "creation_date", "date"),
        Column("STATUS", "status", "upper"),
    ), refs=(("SUPPLIER_ID", "vendors"),)),
    Entity("po_lines", "PO lines", POLine, "PO_LINE_ID", (
        Column("PO_LINE_ID", "po_line_id", "id", True),
        Column("PO_HEADER_ID", "po_header_id", "id", True),
        Column("QUANTITY", "quantity", "num", True, positive=True),
        Column("UNIT_PRICE", "unit_price", "num", True, positive=True),
        Column("ITEM_ID", "item_id", "id"),
        Column("UOM", "uom"),
        Column("DELIVERY_DATE", "delivery_date", "date"),
        Column("LINE_NUM", "line_num", "num"),
    ), refs=(("PO_HEADER_ID", "po_headers"), ("ITEM_ID", "materials"))),
    Entity("goods_receipts", "Goods receipts", GoodsReceiptERP, "GR_ID", (
        Column("GR_ID", "receipt_id", "id", True),
        Column("PO_LINE_ID", "po_line_id", "id", True),
        Column("RECEIVED_QTY", "quantity_received", "num", True, positive=True),
        Column("RECEIPT_DATE", "receipt_date", "date"),
        Column("ITEM_ID", "item_id", "id"),
        Column("SUPPLIER_ID", "supplier_id", "id"),
        Column("UOM", "uom"),
    ), refs=(("PO_LINE_ID", "po_lines"),)),
    Entity("invoices", "Invoice history", ERPInvoice, "INVOICE_ID", (
        Column("INVOICE_ID", "erp_invoice_id", "id", True),
        Column("INVOICE_NUMBER", "invoice_number", "text", True),
        Column("SUPPLIER_ID", "supplier_id", "id"),
        Column("PO_LINE_ID", "po_line_id", "id"),
        Column("INVOICE_DATE", "invoice_date", "date"),
        Column("INVOICED_QTY", "invoiced_qty", "num"),
        Column("UOM", "uom"),
        Column("UNIT_PRICE", "unit_price", "num"),
        Column("CURRENCY", "currency", "upper"),     # history only: not checked against the ISO list
        Column("AMOUNT", "amount", "num"),
    )),
    Entity("pr_headers", "Purchase requisitions", PRHeader, "PR_HEADER_ID", (
        Column("PR_HEADER_ID", "pr_header_id", "id", True),
        Column("PR_NUMBER", "pr_number", "text", True),
        Column("REQUESTER_ID", "requester_id", "id"),
        Column("CREATION_DATE", "creation_date", "date"),
        Column("DEPARTMENT", "department"),
        Column("CURRENCY", "currency", "currency"),
    )),
    Entity("pr_lines", "Requisition lines", PRLine, "PR_LINE_ID", (
        Column("PR_LINE_ID", "pr_line_id", "id", True),
        Column("PR_HEADER_ID", "pr_header_id", "id", True),
        Column("ITEM_ID", "item_id", "id"),
        Column("UOM", "uom"),
        Column("QUANTITY", "quantity", "num"),
        Column("REQUIRED_DATE", "required_date", "date"),
        Column("EST_UNIT_PRICE", "est_unit_price", "num"),
    ), refs=(("PR_HEADER_ID", "pr_headers"),)),
)
BY_NAME = {e.name: e for e in ENTITIES}
REPLACE_NEEDS = ("vendors", "po_headers", "po_lines")


class ERPFileError(ValueError):
    """A file that cannot be read at all (unknown layout, not CSV, duplicate entity)."""


# ---------------------------------------------------------------- reading files
@dataclass
class CsvFile:
    entity: Entity
    filename: str
    headers: list[str]
    rows: list[dict[str, str]]


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ERPFileError("is not a text CSV file")


def read_csv_bytes(filename: str, data: bytes) -> CsvFile:
    text = _decode(data)
    first = text.split("\n", 1)[0]
    delimiter = max((",", ";", "\t"), key=first.count)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header_row = next(reader)
    except StopIteration:
        raise ERPFileError("is empty") from None
    headers = [h.strip().upper() for h in header_row]
    rows = [dict(zip(headers, (v.strip() for v in r), strict=False)) for r in reader if any(v.strip() for v in r)]
    return CsvFile(detect_entity(filename, headers), filename, headers, rows)


def detect_entity(filename: str, headers: list[str]) -> Entity:
    stem = re.sub(r"[^a-z_]", "", os.path.splitext(os.path.basename(filename))[0].lower().replace("-", "_").replace(" ", "_"))
    if stem in BY_NAME:
        return BY_NAME[stem]
    have = set(headers)
    fits = [e for e in ENTITIES if set(e.required) <= have]
    # prefer the layout whose id column is present and that explains the most headers
    fits.sort(key=lambda e: (e.key in have, len(have & {c.name for c in e.columns})), reverse=True)
    if fits and fits[0].key in have:
        return fits[0]
    names = ", ".join(f"{e.name}.csv" for e in ENTITIES)
    raise ERPFileError(f"doesn't match any ERP layout. Name it one of {names}, or use the template's header row")


def read_directory(data_dir: str) -> list[CsvFile]:
    files = []
    for e in ENTITIES:
        path = os.path.join(data_dir, f"{e.name}.csv")
        if os.path.exists(path):
            with open(path, "rb") as fh:
                files.append(read_csv_bytes(os.path.basename(path), fh.read()))
    return files


# ---------------------------------------------------------------- planning
@dataclass
class EntityReport:
    name: str
    label: str
    filename: str | None = None
    rows: int = 0
    inserts: int = 0
    updates: int = 0
    emptied: bool = False
    error_count: int = 0
    errors: list[dict] = field(default_factory=list)

    def error(self, row: int | None, column: str | None, message: str):
        self.error_count += 1
        if len(self.errors) < MAX_ERRORS_PER_FILE:
            self.errors.append({"row": row, "column": column, "message": message})


@dataclass
class Plan:
    mode: Mode
    reports: dict[str, EntityReport]
    problems: list[str] = field(default_factory=list)      # errors not tied to one file
    warnings: list[str] = field(default_factory=list)
    inserts: dict[str, list[dict]] = field(default_factory=dict)
    updates: dict[str, list[dict]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.problems and not any(r.error_count for r in self.reports.values())

    def summary(self) -> dict:
        return {
            "mode": self.mode, "ok": self.ok, "problems": self.problems, "warnings": self.warnings,
            "entities": [vars(r) for r in self.reports.values() if r.filename or r.emptied],
        }


def norm_id(value: str | None) -> str | None:
    """IDs are sometimes exported as floats ("3.0"); store them as plain strings."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[:-2] if value.endswith(".0") else value


def _convert(col: Column, raw: str, report: EntityReport, row_no: int) -> tuple[bool, Any]:
    """Return (ok, value). Blank optional values become None."""
    if raw == "":
        if col.required:
            report.error(row_no, col.name, "is empty")
            return False, None
        return True, None
    if col.kind == "id":
        return True, norm_id(raw)
    if col.kind == "num":
        n = None if re.search(r"[A-Za-z]", raw) else parse_number(raw)
        if n is None:
            report.error(row_no, col.name, f"'{raw}' is not a number")
            return False, None
        if n < 0 and col.positive:
            report.error(row_no, col.name, f"{raw} can't be negative")
            return False, None
        return True, n
    if col.kind == "date":
        d = parse_date(raw)
        if d is None:
            report.error(row_no, col.name, f"'{raw}' is not a date (use YYYY-MM-DD)")
            return False, None
        return True, d
    if col.kind == "currency":
        c = raw.upper()
        if c not in ISO_4217:
            report.error(row_no, col.name, f"'{raw}' is not a supported ISO currency code")
            return False, None
        return True, c
    if col.kind == "upper":
        return True, raw.upper()[:3] if col.attr == "currency" else raw.upper()
    return True, raw


def _existing_keys(db: Session, entity: Entity) -> dict[str, str]:
    """ERP id -> row primary key, for every row of this entity already in the database."""
    key_col = getattr(entity.model, entity.key_attr)
    return {k: pk for k, pk in db.execute(select(key_col, entity.model.id)) if k is not None}


def build_plan(db: Session, files: list[CsvFile], mode: Mode) -> Plan:
    plan = Plan(mode, {e.name: EntityReport(e.name, e.label) for e in ENTITIES})
    by_entity: dict[str, CsvFile] = {}
    for f in files:
        if f.entity.name in by_entity:
            plan.problems.append(f"{f.filename} and {by_entity[f.entity.name].filename} are both {f.entity.label.lower()} files")
            continue
        by_entity[f.entity.name] = f

    if mode == "replace":
        missing = [f"{n}.csv" for n in REPLACE_NEEDS if n not in by_entity]
        if missing:
            plan.problems.append(f"Replace all needs {', '.join(missing)}; otherwise every PO would be deleted")
        for e in ENTITIES:
            if e.name not in by_entity:
                plan.reports[e.name].emptied = True
        if "goods_receipts" not in by_entity:
            plan.warnings.append("No goods_receipts.csv: every PO line will count as not received, so invoices will go on hold")

    # Keys that already exist (merge only; replace starts from empty tables)
    existing: dict[str, dict[str, str]] = {e.name: (_existing_keys(db, e) if mode == "merge" else {}) for e in ENTITIES}
    known: dict[str, set[str]] = {n: set(k) for n, k in existing.items()}
    parsed: dict[str, list[tuple[int, dict]]] = {}

    for e in ENTITIES:
        if e.name not in by_entity:
            continue
        f = by_entity[e.name]
        rep = plan.reports[e.name]
        rep.filename, rep.rows = f.filename, len(f.rows)
        missing_cols = [c for c in e.required if c not in f.headers]
        if missing_cols:
            rep.error(1, ", ".join(missing_cols), "required column is missing from the header row")
            continue
        present = [c for c in e.columns if c.name in f.headers]
        seen: dict[str, int] = {}
        rows: list[tuple[int, dict]] = []
        for i, raw in enumerate(f.rows, start=2):          # row 1 is the header
            values: dict[str, Any] = {}
            good = True
            for col in present:
                ok, v = _convert(col, raw.get(col.name, ""), rep, i)
                good &= ok
                values[col.attr] = v
            key = values.get(e.key_attr)
            if key is not None:
                if key in seen:
                    rep.error(i, e.key, f"{key} is repeated (first on row {seen[key]})")
                    good = False
                else:
                    seen[key] = i
            if good:
                rows.append((i, values))
        parsed[e.name] = rows
        known[e.name] |= set(seen)

    _check_unique_numbers(db, plan, parsed, "po_headers", POHeader, "po_number", "po_header_id", "PO_NUMBER", mode)
    _check_unique_numbers(db, plan, parsed, "pr_headers", PRHeader, "pr_number", "pr_header_id", "PR_NUMBER", mode)

    # References
    for e in ENTITIES:
        rep = plan.reports[e.name]
        for col_name, target in e.refs:
            attr = next(c.attr for c in e.columns if c.name == col_name)
            for row_no, values in parsed.get(e.name, []):
                v = values.get(attr)
                if v is not None and v not in known[target]:
                    rep.error(row_no, col_name, f"{v} is not in {BY_NAME[target].label.lower()}")

    if not plan.ok:
        return plan

    _derive_po_lines(db, parsed, existing, mode)
    for e in ENTITIES:
        ins, upd = [], []
        for _, values in parsed.get(e.name, []):
            pk = existing[e.name].get(values[e.key_attr])
            if pk:
                upd.append({"id": pk, **values})
            else:
                ins.append({"id": generate_uuid(), **values})
        plan.inserts[e.name], plan.updates[e.name] = ins, upd
        plan.reports[e.name].inserts, plan.reports[e.name].updates = len(ins), len(upd)
    return plan


def _check_unique_numbers(db: Session, plan: Plan, parsed: dict, entity: str, model: Any, num_attr: str,
                          key_attr: str, col: str, mode: Mode):
    rep = plan.reports[entity]
    owner: dict[str, str] = {}
    if mode == "merge":
        owner = {n: k for n, k in db.execute(select(getattr(model, num_attr), getattr(model, key_attr))) if n}
    first_row: dict[str, int] = {}
    for row_no, values in parsed.get(entity, []):
        num, key = values.get(num_attr), values.get(key_attr)
        if num in first_row:
            rep.error(row_no, col, f"{num} is repeated (first on row {first_row[num]})")
            continue
        first_row[num] = row_no
        if num in owner and owner[num] != key:
            rep.error(row_no, col, f"{num} already belongs to ERP id {owner[num]}")


def _derive_po_lines(db: Session, parsed: dict, existing: dict, mode: Mode):
    """Compute line_amount, and a line number when the file has none (next free number on its PO)."""
    rows = parsed.get("po_lines", [])
    next_num: dict[str, int] = {}
    if mode == "merge" and rows:
        next_num = {h: int(n or 0) for h, n in db.execute(
            select(POLine.po_header_id, func.max(POLine.line_num)).group_by(POLine.po_header_id)) if h}
    for _, v in rows:
        v["line_amount"] = round((v.get("quantity") or 0.0) * (v.get("unit_price") or 0.0), 2)
        if v.get("line_num") is not None:
            v["line_num"] = int(v["line_num"])
        elif v["po_line_id"] in existing["po_lines"]:
            v.pop("line_num", None)                  # keep the number it already has
        else:
            hid = v["po_header_id"]
            next_num[hid] = next_num.get(hid, 0) + 1
            v["line_num"] = next_num[hid]
    for _, v in parsed.get("po_headers", []):
        if not v.get("status"):
            if v["po_header_id"] in existing["po_headers"]:
                v.pop("status", None)                # keep the status it already has
            else:
                v["status"] = "OPEN"


def apply_plan(db: Session, plan: Plan) -> dict[str, int]:
    if not plan.ok:
        raise ValueError("The import has errors; nothing was written")
    if plan.mode == "replace":
        for e in reversed(ENTITIES):
            db.execute(delete(e.model))
    counts: dict[str, int] = {}
    for e in ENTITIES:
        if plan.inserts.get(e.name):
            db.bulk_insert_mappings(e.model, plan.inserts[e.name])
        if plan.updates.get(e.name):
            db.bulk_update_mappings(e.model, plan.updates[e.name])
        counts[e.name] = len(plan.inserts.get(e.name, [])) + len(plan.updates.get(e.name, []))
    db.commit()
    return counts


# ---------------------------------------------------------------- status
def table_counts(db: Session) -> dict[str, int]:
    return {e.name: db.scalar(select(func.count()).select_from(e.model)) or 0 for e in ENTITIES}


def layouts() -> list[dict]:
    return [{"name": e.name, "label": e.label, "file": f"{e.name}.csv", "key": e.key,
             "required": e.required, "optional": [c.name for c in e.columns if not c.required]} for e in ENTITIES]
