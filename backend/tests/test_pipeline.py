import glob
import os

import pytest

from app.agents.orchestrator import OrchestratorAgent
from app.database import SessionLocal
from app.models import Invoice, InvoiceStatus
from app.services.intake import receive_document

EXPECTED = {
    "01_full_match": ("MATCHED", "FULL_MATCH", set()),
    "02_partial_invoice_one_line_FULL_MATCH": ("MATCHED", "FULL_MATCH", set()),
    "03_price_over_tolerance": ("DISCREPANCY", "NO_MATCH", {"PRICE_OVER"}),
    "04_qty_exceeds_received": ("DISCREPANCY", "NO_MATCH", {"QTY_EXCEEDS_RECEIVED"}),
    "05_unknown_po": ("DISCREPANCY", "NO_MATCH", {"MISSING_PO"}),
    "06_multiline_full_match": ("MATCHED", "FULL_MATCH", set()),
    "07_unauthorised_extra_line": ("DISCREPANCY", "NO_MATCH", {"UNMATCHED_LINE"}),
    "08_qty_within_tolerance": ("MATCHED", "FULL_MATCH", set()),
    "09_unreceived_line_not_billed_FULL_MATCH": ("MATCHED", "FULL_MATCH", set()),
    "10_vendor_mismatch": ("DISCREPANCY", "NO_MATCH", {"VENDOR_MISMATCH"}),
    "11_currency_mismatch": ("DISCREPANCY", "NO_MATCH", {"CURRENCY_MISMATCH"}),
    "12_goods_not_received_ON_HOLD": ("ON_HOLD", "NO_MATCH", {"NOT_RECEIVED"}),
}


def ingest(path):
    with SessionLocal() as db, open(path, "rb") as fh:
        res = receive_document(db, fh.read(), os.path.basename(path), "test", allow_text=True)
        return res.invoice.id


def process(path, events=None):
    inv_id = ingest(path)
    OrchestratorAgent(notify=(events.append if events is not None else (lambda e: None))).run(inv_id)
    with SessionLocal() as db:
        inv = db.get(Invoice, inv_id)
        inv.line_items  # load before the session closes
        return inv


def sample(samples_dir, prefix):
    return glob.glob(os.path.join(samples_dir, prefix + "_*.txt"))[0]


@pytest.mark.parametrize("prefix", list(EXPECTED))
def test_sample_scenarios(samples_dir, prefix):
    status, result, must_have = EXPECTED[prefix]
    inv = process(sample(samples_dir, prefix))
    failed = {d["type"] for d in inv.discrepancies or []}
    assert inv.status.value == status, (inv.status, inv.discrepancies, inv.error)
    assert inv.match_result.value == result
    assert must_have <= failed
    if result == "FULL_MATCH":
        assert all(li.matched_po_line_id for li in inv.line_items)
        assert inv.match_snapshot["po"]["po_number"] == inv.po_reference


def test_pipeline_emits_progress_for_every_step(samples_dir):
    events = []
    process(sample(samples_dir, "01_full_match"), events)
    steps = [e.get("step") for e in events if e["event"] == "status_update"]
    assert steps == ["received", "read", "check", "lookup", "match"]
    assert events[-1]["event"] == "match_complete" and events[-1]["match_result"] == "FULL_MATCH"


def test_duplicate_invoice_is_blocked(samples_dir):   # audit M5
    first = process(sample(samples_dir, "01_full_match"))
    dup = process(sample(samples_dir, "13_duplicate_of_01"))
    assert first.status == InvoiceStatus.MATCHED
    assert dup.status == InvoiceStatus.DUPLICATE and dup.duplicate_of == first.id


def test_same_file_twice_is_not_reprocessed(samples_dir):
    path = sample(samples_dir, "01_full_match")
    a, b = ingest(path), ingest(path)
    assert a == b


def test_cumulative_billing_across_invoices(samples_dir):
    first = process(sample(samples_dir, "02_partial_invoice_one_line_FULL_MATCH"))
    assert first.status == InvoiceStatus.MATCHED
    # Same lines again under a new invoice number: quantities were already billed
    text = open(sample(samples_dir, "02_partial_invoice_one_line_FULL_MATCH"), encoding="utf-8").read()
    path = os.path.join(os.path.dirname(sample(samples_dir, "02_partial")), "..", "rebill.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace("INV-DEMO-002", "INV-DEMO-902"))
    try:
        second = process(path)
    finally:
        os.remove(path)
    assert {"QTY_EXCEEDS_RECEIVED"} <= {d["type"] for d in second.discrepancies}


def test_edit_and_rematch_clears_issue(samples_dir):
    inv = process(sample(samples_dir, "11_currency_mismatch"))
    po_currency = inv.match_snapshot["po"]["currency"]
    with SessionLocal() as db:
        row = db.get(Invoice, inv.id)
        row.currency = po_currency
        db.commit()
    OrchestratorAgent(notify=lambda e: None).rematch(inv.id, actor="clerk@test.io")
    with SessionLocal() as db:
        row = db.get(Invoice, inv.id)
        assert row.match_result.value == "FULL_MATCH" and row.status == InvoiceStatus.MATCHED


def test_unreadable_document_fails_with_reason(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("   ")
    inv = process(str(path))
    assert inv.status == InvoiceStatus.FAILED
    assert "No readable text" in inv.error
