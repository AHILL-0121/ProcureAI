import pytest
from fastapi.testclient import TestClient
from test_api import _exception_invoice, login

from app.database import SessionLocal
from app.main import app
from app.models import POHeader
from app.seed_erp import seed

# PO-999999 is quoted by sample 05 but is not in the ERP: importing it should clear that invoice.
PO_999999 = {
    "po_headers.csv": "PO_HEADER_ID,PO_NUMBER,SUPPLIER_ID,CREATION_DATE,CURRENCY\n99999,PO-999999,3,2026-09-01,GBP\n",
    "po_lines.csv": "PO_LINE_ID,PO_HEADER_ID,ITEM_ID,UOM,QUANTITY,UNIT_PRICE,DELIVERY_DATE\n99001,99999,1015,LTR,5,453.42,2026-09-10\n",
    "goods_receipts.csv": "GR_ID,PO_LINE_ID,ITEM_ID,SUPPLIER_ID,RECEIPT_DATE,RECEIVED_QTY,UOM\n99001,99001,1015,3,2026-09-12,5,LTR\n",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin(client):
    return login(client, "admin@test.io")


@pytest.fixture
def clerk(client):
    return login(client, "clerk@test.io")


@pytest.fixture
def viewer(client):
    return login(client, "viewer@test.io")


@pytest.fixture
def restore_erp():
    yield
    with SessionLocal() as db:
        seed(db, reset=True)


def send(client, headers, files: dict[str, str], **params):
    q = "&".join(f"{k}={str(v).lower()}" for k, v in params.items())
    return client.post(f"/api/erp/import?{q}", headers=headers,
                       files=[("files", (name, body.encode(), "text/csv")) for name, body in files.items()])


def po_count():
    with SessionLocal() as db:
        return db.query(POHeader).count()


def test_status_shows_sample_dataset_and_layouts(client, viewer):
    r = client.get("/api/erp/status", headers=viewer)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "sample" and body["counts"]["po_headers"] == 1000
    po_lines = next(x for x in body["layouts"] if x["name"] == "po_lines")
    assert {"PO_LINE_ID", "PO_HEADER_ID", "QUANTITY", "UNIT_PRICE"} <= set(po_lines["required"])


def test_only_admins_can_import(client, clerk):
    assert send(client, clerk, PO_999999).status_code == 403


def test_preview_reports_counts_and_writes_nothing(client, admin):
    r = send(client, admin, PO_999999, mode="merge", dry_run=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and not body["committed"]
    by = {e["name"]: e for e in body["entities"]}
    assert by["po_headers"]["inserts"] == 1 and by["po_lines"]["inserts"] == 1 and by["goods_receipts"]["inserts"] == 1
    assert po_count() == 1000


def test_invalid_rows_block_the_import_with_row_and_column(client, admin):
    files = {
        "po_headers.csv": "PO_HEADER_ID,PO_NUMBER,SUPPLIER_ID,CURRENCY\n"
                          "99999,PO-999999,404,GBP\n"          # unknown vendor
                          "99998,PO-000001,3,GBP\n"            # PO number already used by another PO
                          "99997,PO-999997,3,Pounds\n",        # not a currency
        "po_lines.csv": "PO_LINE_ID,PO_HEADER_ID,QUANTITY,UNIT_PRICE\n99001,99999,five,1.00\n",
    }
    body = send(client, admin, files, mode="merge", dry_run=False).json()
    assert not body["ok"] and not body["committed"]
    errors = {e["name"]: e["errors"] for e in body["entities"]}
    messages = {(x["row"], x["column"]) for x in errors["po_headers"]}
    assert {(2, "SUPPLIER_ID"), (3, "PO_NUMBER"), (4, "CURRENCY")} <= messages
    assert errors["po_lines"][0]["column"] == "QUANTITY" and errors["po_lines"][0]["row"] == 2
    assert po_count() == 1000


def test_missing_column_and_unknown_layout(client, admin):
    body = send(client, admin, {"po_lines.csv": "PO_LINE_ID,PO_HEADER_ID\n1,2\n"}).json()
    assert "QUANTITY" in body["entities"][0]["errors"][0]["column"]
    r = send(client, admin, {"notes.csv": "A,B\n1,2\n"})
    assert r.status_code == 422 and "doesn't match any ERP layout" in r.json()["detail"]


def test_excel_style_file_is_recognised_by_header(client, admin):
    # semicolons, a BOM, a file name that says nothing, and day-first dates
    body = "﻿PO_HEADER_ID;PO_NUMBER;SUPPLIER_ID;CREATION_DATE;CURRENCY\n99999;PO-999999;3;01/09/2026;GBP\n"
    r = send(client, admin, {"Export (3).csv": body}, dry_run=True).json()
    assert r["ok"] and r["entities"][0]["name"] == "po_headers"


def test_merge_import_rematches_waiting_invoice(client, admin, clerk, samples_dir, restore_erp):
    inv = _exception_invoice(client, clerk, samples_dir, "05_unknown_po")
    assert inv["status"] == "DISCREPANCY"

    r = send(client, admin, PO_999999, mode="merge", dry_run=False)
    body = r.json()
    assert body["committed"] and body["rematching"] >= 1
    assert po_count() == 1001

    after = client.get(f"/api/invoices/{inv['id']}", headers=clerk).json()
    assert after["status"] == "MATCHED", after["discrepancies"]
    status = client.get("/api/erp/status", headers=admin).json()
    assert status["source"] == "import" and status["last_import"]["mode"] == "merge"


def test_merge_updates_existing_rows_without_deleting(client, admin, restore_erp):
    files = {"vendors.csv": "SUPPLIER_ID,SUPPLIER_NAME\n3,Northwind Metals Ltd\n"}
    body = send(client, admin, files, mode="merge", dry_run=False).json()
    assert body["committed"] and body["entities"][0]["updates"] == 1
    vendors = {v["supplier_id"]: v for v in client.get("/api/vendors", headers=admin).json()}
    assert vendors["3"]["name"] == "Northwind Metals Ltd"
    assert vendors["3"]["tax_id"] == "TAX0003"          # column not in the file: left alone
    assert len(vendors) == 10


def test_replace_needs_core_files_then_swaps_the_dataset(client, admin, restore_erp):
    body = send(client, admin, {"vendors.csv": "SUPPLIER_ID,SUPPLIER_NAME\n1,Acme\n"}, mode="replace", dry_run=True).json()
    assert not body["ok"] and "po_headers.csv" in body["problems"][0]

    files = {
        "vendors.csv": "SUPPLIER_ID,SUPPLIER_NAME,TAX_ID,CURRENCY\nV1,Acme Fasteners,GB123,GBP\n",
        "materials.csv": "ITEM_ID,ITEM_NUMBER,DESCRIPTION,UOM\nM1,BOLT-10,Hex bolt M10,EA\n",
        "po_headers.csv": "PO_HEADER_ID,PO_NUMBER,SUPPLIER_ID,CURRENCY\nH1,PO-2026-0001,V1,GBP\n",
        "po_lines.csv": "PO_LINE_ID,PO_HEADER_ID,ITEM_ID,QUANTITY,UNIT_PRICE\nL1,H1,M1,100,0.35\n",
    }
    body = send(client, admin, files, mode="replace", dry_run=False).json()
    assert body["committed"], body
    assert any("goods_receipts" in w for w in body["warnings"])
    status = client.get("/api/erp/status", headers=admin).json()["counts"]
    assert status["po_headers"] == 1 and status["vendors"] == 1 and status["goods_receipts"] == 0
    po = client.get("/api/purchase-orders/PO-2026-0001", headers=admin).json()["purchase_order"]
    assert po["lines"][0]["line_num"] == 1 and po["lines"][0]["line_amount"] == 35.0
