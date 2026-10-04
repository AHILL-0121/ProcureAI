import glob
import os
import time

import fitz  # PyMuPDF, used to build a real text PDF
import pytest
from fastapi.testclient import TestClient

from app.main import app

IN_FLIGHT = {"RECEIVED", "EXTRACTING", "EXTRACTED", "VALIDATING", "VALIDATED", "MATCHING"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return login(client, "admin@test.io")


@pytest.fixture
def clerk(client):
    return login(client, "clerk@test.io")


@pytest.fixture
def approver(client):
    return login(client, "approver@test.io")


@pytest.fixture
def viewer(client):
    return login(client, "viewer@test.io")


def pdf_from_text(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=700, height=900)
    page.insert_text((30, 40), text, fontname="cour", fontsize=8)
    data = doc.tobytes()
    doc.close()
    return data


def sample_pdf(samples_dir, prefix):
    path = glob.glob(os.path.join(samples_dir, prefix + "_*.txt"))[0]
    return pdf_from_text(open(path, encoding="utf-8").read())


def wait_done(client, headers, inv_id, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/invoices/{inv_id}", headers=headers)
        if r.json()["status"] not in IN_FLIGHT:
            return r.json()
        time.sleep(0.1)
    raise AssertionError("invoice did not finish processing")


def upload(client, headers, name, data, content_type="application/pdf"):
    return client.post("/api/invoices/upload", headers=headers, files=[("files", (name, data, content_type))])


# ---------------------------------------------------------------- auth
def test_endpoints_require_sign_in(client):
    assert client.get("/api/invoices").status_code == 401
    assert client.get("/api/dashboard/stats").status_code == 401
    assert client.post("/api/invoices/upload").status_code == 401


def test_wrong_password_is_rejected(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.io", "password": "nope"})
    assert r.status_code == 401 and "incorrect" in r.json()["detail"]


def test_login_is_rate_limited(client):
    codes = [client.post("/api/auth/login", json={"email": "x@y.z", "password": "bad"}).status_code for _ in range(12)]
    assert 429 in codes


def test_viewer_cannot_upload_or_change_settings(client, viewer):
    assert upload(client, viewer, "a.pdf", b"%PDF-1.4").status_code == 403
    r = client.put("/api/settings/tolerances", headers=viewer,
                   json={"qty_pct": 0.1, "price_pct": 0.1, "price_abs": 0, "total_abs": 0})
    assert r.status_code == 403


def test_health_is_public_and_reports_erp(client):
    body = client.get("/api/health").json()
    assert body["erp"]["total_purchase_orders"] == 1000


# ---------------------------------------------------------------- upload hardening
def test_upload_rejects_spoofed_file_type(client, clerk):
    r = upload(client, clerk, "invoice.pdf", b"MZ\x90\x00 not really a pdf")
    assert r.status_code == 202
    item = r.json()["items"][0]
    assert item["status"] == "REJECTED" and "Only PDF, PNG and JPEG" in item["error"]


def test_upload_rejects_oversized_file(client, clerk, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "upload_max_bytes", 1000)
    r = upload(client, clerk, "big.pdf", b"%PDF-" + b"0" * 2000)
    assert "larger than" in r.json()["items"][0]["error"]


def test_upload_processes_in_background_and_matches(client, clerk, samples_dir):
    data = sample_pdf(samples_dir, "01_full_match")
    r = upload(client, clerk, "../../etc/passwd.pdf", data)
    assert r.status_code == 202
    item = r.json()["items"][0]
    inv = wait_done(client, clerk, item["invoice_id"])
    assert inv["status"] == "MATCHED", inv
    assert inv["original_filename"] == "passwd.pdf"       # path parts stripped
    assert inv["extraction"]["extraction_method"] == "native_pdf"
    # same bytes again: not reprocessed
    again = upload(client, clerk, "copy.pdf", data).json()["items"][0]
    assert again["duplicate"] is True and again["invoice_id"] == item["invoice_id"]


# ---------------------------------------------------------------- review workflow
def _exception_invoice(client, clerk, samples_dir, prefix="03_price_over_tolerance"):
    item = upload(client, clerk, f"{prefix}.pdf", sample_pdf(samples_dir, prefix)).json()["items"][0]
    return wait_done(client, clerk, item["invoice_id"])


def test_review_queue_lists_exceptions(client, clerk, samples_dir):
    inv = _exception_invoice(client, clerk, samples_dir)
    q = client.get("/api/invoices?queue=review", headers=clerk).json()
    assert inv["id"] in [i["id"] for i in q["items"]]
    row = next(i for i in q["items"] if i["id"] == inv["id"])
    assert row["top_issue_code"] == "PRICE_OVER" and row["top_issue_severity"] == "HIGH"


def test_approving_over_high_issues_needs_a_note_and_approver_role(client, clerk, approver, samples_dir):
    inv = _exception_invoice(client, clerk, samples_dir)
    assert client.post(f"/api/invoices/{inv['id']}/approve", headers=clerk, json={}).status_code == 403
    r = client.post(f"/api/invoices/{inv['id']}/approve", headers=approver, json={})
    assert r.status_code == 422
    r = client.post(f"/api/invoices/{inv['id']}/approve", headers=approver, json={"note": "Price rise agreed by buyer"})
    assert r.status_code == 200 and r.json()["status"] == "APPROVED" and r.json()["reviewed_by"] == "approver@test.io"
    trail = client.get(f"/api/invoices/{inv['id']}/audit", headers=approver).json()
    assert trail[-1]["action"] == "APPROVED_OVERRIDE" and trail[-1]["actor"] == "approver@test.io"
    # final: cannot be edited or approved again
    assert client.patch(f"/api/invoices/{inv['id']}", headers=clerk, json={"currency": "EUR"}).status_code == 409


def test_reject_requires_reason(client, clerk, approver, samples_dir):
    inv = _exception_invoice(client, clerk, samples_dir, "05_unknown_po")
    assert client.post(f"/api/invoices/{inv['id']}/reject", headers=approver, json={"note": " "}).status_code == 422
    r = client.post(f"/api/invoices/{inv['id']}/reject", headers=approver, json={"note": "PO does not exist"})
    assert r.json()["status"] == "REJECTED"


def test_edit_fields_then_rematch(client, clerk, samples_dir):
    inv = _exception_invoice(client, clerk, samples_dir, "11_currency_mismatch")
    po_currency = inv["match_snapshot"]["po"]["currency"]
    r = client.patch(f"/api/invoices/{inv['id']}", headers=clerk, json={"currency": po_currency})
    assert r.status_code == 200 and "currency" in r.json()["validation"]["edited_fields"]
    r = client.post(f"/api/invoices/{inv['id']}/rematch", headers=clerk)
    assert r.json()["match_result"] == "FULL_MATCH" and r.json()["status"] == "MATCHED"


def test_signed_document_link(client, clerk, samples_dir):
    inv = _exception_invoice(client, clerk, samples_dir)
    link = client.get(f"/api/invoices/{inv['id']}/document-link", headers=clerk).json()
    path = link["url"].split("testserver", 1)[1]
    r = client.get(path)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert client.get(f"/api/documents/invoice/{inv['id']}?token=forged").status_code == 401
    other = _exception_invoice(client, clerk, samples_dir, "04_qty_exceeds_received")
    assert client.get(path.replace(inv["id"], other["id"])).status_code == 403


# ---------------------------------------------------------------- read models
def test_dashboard_and_purchase_orders(client, viewer, clerk, samples_dir):
    _exception_invoice(client, clerk, samples_dir)
    stats = client.get("/api/dashboard/stats", headers=viewer).json()
    assert stats["total_invoices"] >= 1 and stats["in_review"] >= 1
    assert any(i["type"] == "PRICE_OVER" for i in stats["issues_by_type"])
    pos = client.get("/api/purchase-orders?page=2&page_size=10", headers=viewer).json()
    assert pos["total"] == 1000 and len(pos["items"]) == 10 and pos["page"] == 2
    detail = client.get(f"/api/purchase-orders/{pos['items'][0]['po_number']}", headers=viewer).json()
    assert "invoiced_qty" in detail["purchase_order"]["lines"][0]


def test_tolerance_override_changes_verdict(client, admin, clerk, samples_dir):
    inv = _exception_invoice(client, clerk, samples_dir)
    vendor = inv["match_snapshot"]["po"]["vendor_id"]
    r = client.put(f"/api/settings/tolerances?vendor_id={vendor}", headers=admin,
                   json={"qty_pct": 0.02, "price_pct": 0.10, "price_abs": 0.05, "total_abs": 1})
    assert r.status_code == 200
    r = client.post(f"/api/invoices/{inv['id']}/rematch", headers=clerk)
    assert r.json()["match_result"] == "FULL_MATCH"
    client.delete(f"/api/settings/tolerances/{vendor}", headers=admin)


def test_admin_manages_users(client, admin):
    r = client.post("/api/users", headers=admin, json={"email": "new@test.io", "name": "New", "role": "ap_clerk"})
    assert r.status_code == 201 and r.json()["temporary_password"]
    assert client.post("/api/users", headers=admin, json={"email": "new@test.io", "name": "x"}).status_code == 409
    assert client.post("/api/users", headers=admin, json={"email": "bad", "name": "x"}).status_code == 422


def test_decision_can_be_undone_by_its_author(client, clerk, approver, samples_dir):
    inv = _exception_invoice(client, clerk, samples_dir, "05_unknown_po")
    client.post(f"/api/invoices/{inv['id']}/reject", headers=approver, json={"note": "Wrong PO"})
    assert client.post(f"/api/invoices/{inv['id']}/reopen", headers=clerk).status_code == 403
    r = client.post(f"/api/invoices/{inv['id']}/reopen", headers=approver)
    assert r.status_code == 200 and r.json()["status"] == "DISCREPANCY" and r.json()["reviewed_by"] is None
    assert client.post(f"/api/invoices/{inv['id']}/reopen", headers=approver).status_code == 409


def test_detail_tolerates_pre_v2_rows(client, viewer):
    """Line items created before v2 have NULL line_no; the detail endpoint must still render."""
    from app.database import SessionLocal
    from app.models import Invoice, InvoiceLineItem, InvoiceStatus

    with SessionLocal() as db:
        inv = Invoice(status=InvoiceStatus.DISCREPANCY, invoice_number="OLD-1", total_amount=None, confidence_score=None)
        db.add(inv)
        db.flush()
        db.add(InvoiceLineItem(invoice_id=inv.id, line_no=None, description="legacy line", quantity=None))
        db.commit()
        inv_id = inv.id
    r = client.get(f"/api/invoices/{inv_id}", headers=viewer)
    assert r.status_code == 200, r.text
    assert r.json()["line_items"][0]["line_no"] == 0 and r.json()["total_amount"] == 0.0


def test_ping_needs_no_auth(client):
    r = client.get("/api/ping")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_inr_is_listed_first_by_currency(client, viewer):
    from app.database import SessionLocal
    from app.models import Invoice, InvoiceStatus

    with SessionLocal() as db:
        db.add_all([Invoice(status=InvoiceStatus.DISCREPANCY, invoice_number="CUR-USD", currency="USD", total_amount=90000),
                    Invoice(status=InvoiceStatus.DISCREPANCY, invoice_number="CUR-EUR", currency="EUR", total_amount=50000),
                    Invoice(status=InvoiceStatus.DISCREPANCY, invoice_number="CUR-INR", currency="INR", total_amount=10)])
        db.commit()
    stats = client.get("/api/dashboard/stats", headers=viewer).json()
    for key in ("value_by_currency", "held_by_currency"):
        assert [c["currency"] for c in stats[key]][:3] == ["INR", "USD", "EUR"], stats[key]
