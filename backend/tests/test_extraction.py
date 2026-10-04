from datetime import date

import pytest

from app.agents.vision_ocr import chunk_pages, merge_chunks, parse_json_object, totals_found_in_text
from app.extraction import ExtractedInvoice, parse_date, parse_number


@pytest.mark.parametrize("raw,expected", [
    ("1,234.50", 1234.5), ("$45", 45.0), ("(12.00)", -12.0), ("EUR 7 576,80", 7576.8), ("1.234,56", 1234.56),
    (12, 12.0), (None, None), ("N/A", None), ("", None), (True, None),
])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("2024-01-09", date(2024, 1, 9)), ("09/01/2024", date(2024, 1, 9)), ("Jan 9, 2024", date(2024, 1, 9)),
    ("9 January 2024", date(2024, 1, 9)), ("not a date", None), (None, None),
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("PO#822", "PO-000822"), ("po 000822", "PO-000822"), ("P.O. No. 822", "PO-000822"),
    ("PO-000822", "PO-000822"), ("PO-2024-001", "PO-2024-001"), (None, None), ("null", None),
])
def test_po_reference_normalised(raw, expected):
    assert ExtractedInvoice.model_validate({"po_reference": raw}).po_reference == expected


def test_llm_garbage_does_not_crash_and_is_repaired():
    inv = ExtractedInvoice.model_validate({
        "invoice_number": "INV-1", "vendor_name": "Supplier_5", "currency": "€",
        "line_items": [{"description": "Bolts", "quantity": "10", "unit_price": "2.50", "total_price": None},
                       {"description": "Nuts", "quantity": None, "unit_price": "1.00", "total_price": "5.00"},
                       "not a line"],
        "subtotal": None, "tax_amount": "3.00", "total_amount": None,
    })
    assert inv.currency == "EUR"
    assert inv.line_items[0].total_price == 25.0
    assert inv.line_items[1].quantity == 5.0
    assert inv.subtotal == 30.0 and inv.total_amount == 33.0
    assert len(inv.line_items) == 2
    assert any("computed" in c for c in inv.coercions)
    assert inv.arithmetic_consistency() == 1.0


def test_unknown_currency_is_dropped():
    assert ExtractedInvoice.model_validate({"currency": "XXX"}).currency is None


def test_chunking_and_merge():
    pages = ["a" * 50, "b" * 50, "c" * 120]
    chunks = chunk_pages(pages, 100)
    assert all(len(c) <= 101 for c in chunks) and "".join(chunks).count("c") == 120
    merged = merge_chunks([
        {"invoice_number": "INV-9", "vendor_name": "V", "line_items": [{"description": "x"}]},
        {"invoice_number": None, "line_items": [{"description": "y"}], "total_amount": 10},
    ])
    assert merged["invoice_number"] == "INV-9" and merged["total_amount"] == 10
    assert [l["description"] for l in merged["line_items"]] == ["x", "y"]


def test_parse_json_object_handles_fences():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_totals_cross_check_catches_injected_total():
    inv = ExtractedInvoice.model_validate({"total_amount": 999999.0})
    assert totals_found_in_text(inv, "TOTAL DUE 1,234.00") is False
    inv2 = ExtractedInvoice.model_validate({"total_amount": 1234.0})
    assert totals_found_in_text(inv2, "TOTAL DUE 1,234.00") is True
