import os
import re
import shutil
import sys
import tempfile

import pytest

# Configure the app for tests BEFORE importing it
_TMP = tempfile.mkdtemp(prefix="procureai-tests-")
os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": f"sqlite:///{os.path.join(_TMP, 'test.db')}",
    "UPLOAD_DIR": os.path.join(_TMP, "uploads"),
    "GROQ_API_KEY": "",
    "JWT_SECRET": "test-secret",
    "EMAIL_USER": "",
    "EMAIL_PASSWORD": "",
    "WORKER_CONCURRENCY": "1",
})
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.vision_ocr import VisionOCRAgent  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import AuditLog, Invoice, InvoiceLineItem, Role, ToleranceRule, User  # noqa: E402
from app.security import hash_password, limiter  # noqa: E402
from app.seed_erp import seed  # noqa: E402

ITEM_RE = re.compile(r"^(\S+)\s+(.+?)\s+([\d.]+)\s+(\w+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$")


def fake_llm_parse(text: str) -> dict:
    """Deterministic stand-in for the LLM that understands the sample invoice layout."""
    def grab(label):
        m = re.search(rf"{label}:\s*(.+)", text)
        return m.group(1).strip() if m else None

    lines = [l.rstrip() for l in text.splitlines()]
    vendor = next((l.strip() for l in lines if l.strip() and not set(l.strip()) <= {"=", "-"}
                   and "TAX INVOICE" not in l), None)
    items = []
    for l in lines:
        m = ITEM_RE.match(l.strip())
        if m and m.group(1) != "ITEM":
            items.append({"item_code": m.group(1), "description": m.group(2).strip(), "quantity": m.group(3),
                          "uom": m.group(4), "unit_price": m.group(5), "total_price": m.group(6)})

    def money(label):
        m = re.search(rf"{label}\s+([\d,]+\.\d{{2}})", text)
        return m.group(1) if m else None

    return {"invoice_number": grab("Invoice Number"), "invoice_date": grab("Invoice Date"), "vendor_name": vendor,
            "vendor_tax_id": grab("Tax ID"), "po_reference": grab("PO Reference"), "currency": grab("Currency"),
            "payment_terms": grab("Payment Terms"), "line_items": items, "subtotal": money("Subtotal"),
            "tax_amount": money(r"Tax \(10%\)"), "total_amount": money("TOTAL DUE"), "notes": grab("Note")}


@pytest.fixture(scope="session", autouse=True)
def database():
    init_db()
    with SessionLocal() as db:
        seed(db, reset=True)
        for email, role in [("admin@test.io", Role.ADMIN), ("approver@test.io", Role.APPROVER),
                            ("clerk@test.io", Role.AP_CLERK), ("viewer@test.io", Role.VIEWER)]:
            db.add(User(email=email, name=email.split("@")[0].title(), password_hash=hash_password("password123"),
                        role=role))
        db.commit()
    yield
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_invoices(monkeypatch):
    async def fake_extract(self, text, extra=""):
        return fake_llm_parse(text)

    monkeypatch.setattr(VisionOCRAgent, "_extract_from_text", fake_extract)
    monkeypatch.setattr(VisionOCRAgent, "configured", property(lambda self: True))
    with SessionLocal() as db:
        db.query(InvoiceLineItem).delete()
        db.query(Invoice).delete()
        db.query(AuditLog).delete()
        db.query(ToleranceRule).delete()
        db.commit()
    limiter.reset()
    yield


@pytest.fixture
def samples_dir():
    from app.generate_samples import SAMPLES_DIR, create_samples

    create_samples()
    return SAMPLES_DIR
