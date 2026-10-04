from app.agents.matching import Tolerance, code_matches, description_score, pair_lines, perform_three_way_match

TOL = Tolerance()


def po_line(pid, num, item_no, desc, qty, price, received, uom="KG"):
    return {"po_line_id": pid, "line_num": num, "item_id": str(1000 + num), "item_number": item_no, "description": desc,
            "uom": uom, "quantity": qty, "unit_price": price, "line_amount": qty * price, "received_qty": received,
            "receipts": [{"receipt_id": f"R{pid}", "quantity": received, "date": "2026-01-01"}] if received else []}


def make_po(lines, currency="EUR", vendor="Supplier_5", vendor_id="5", status="OPEN"):
    return {"po_number": "PO-000100", "vendor_id": vendor_id, "vendor_name": vendor, "vendor_tax_id": "TAX0005",
            "currency": currency, "status": status, "lines": lines,
            "total_amount": sum(l["line_amount"] for l in lines)}


def inv_line(code, desc, qty, price, uom="KG"):
    return {"item_code": code, "description": desc, "quantity": qty, "unit_price": price,
            "total_price": round(qty * price, 2), "uom": uom}


def invoice(lines, currency="EUR", vendor="Supplier_5", tax="TAX0005", resolved="5", **kw):
    subtotal = round(sum(l["total_price"] for l in lines), 2)
    return {"po_reference": "PO-000100", "vendor_name": vendor, "vendor_tax_id": tax, "resolved_vendor_id": resolved,
            "currency": currency, "line_items": lines, "subtotal": subtotal, "tax_amount": 0.0,
            "total_amount": subtotal, **kw}


def codes(result):
    return {c["code"] for c in result["checks"] if not c["passed"]}


PO3 = make_po([
    po_line("1", 1, "ITEM-005", "Material Description 5", 38, 145.0, 38),
    po_line("2", 2, "ITEM-012", "Material Description 12", 20, 86.43, 20, uom="LTR"),
    po_line("3", 3, "ITEM-003", "Material Description 3", 12, 286.33, 0, uom="EA"),
])


def test_full_match():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0),
                   inv_line("ITEM-012", "Material Description 12", 20, 86.43, "LTR")])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert r["match_result"] == "FULL_MATCH", codes(r)
    assert r["pairs"] == {0: 0, 1: 1}


def test_partial_invoice_of_multiline_po_is_not_a_total_mismatch():   # audit M1
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0)])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert r["match_result"] == "FULL_MATCH", codes(r)


def test_unreceived_line_not_billed_does_not_fail_invoice():   # audit M2
    inv = invoice([inv_line("ITEM-012", "Material Description 12", 20, 86.43, "LTR")])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert r["match_result"] == "FULL_MATCH"
    assert any(c["code"] == "PO_LINE_NOT_BILLED" and c["passed"] for c in r["checks"])


def test_vendor_mismatch_is_high():   # audit M3
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0)], vendor="Supplier_9", tax="TAX0009",
                  resolved="9")
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert r["match_result"] == "NO_MATCH" and "VENDOR_MISMATCH" in codes(r)


def test_vendor_checked_by_name_when_unresolved():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0)], vendor="Supplier 5 Ltd", tax=None,
                  resolved=None)
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert "VENDOR_MISMATCH" not in codes(r)


def test_currency_mismatch_is_high():   # audit M4
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0)], currency="GBP")
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert "CURRENCY_MISMATCH" in codes(r) and r["match_result"] == "NO_MATCH"


def test_price_over_tolerance():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 153.90)])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert "PRICE_OVER" in codes(r)
    price = next(c for c in r["checks"] if c["code"] == "PRICE_OVER")
    assert price["variance_pct"] == 6.1
    # the header difference is explained by the price issue, so no separate TOTAL_MISMATCH
    assert "TOTAL_MISMATCH" not in codes(r)


def test_price_within_percentage_and_under_price_pass():
    r1 = perform_three_way_match(invoice([inv_line("ITEM-005", "Material Description 5", 38, 152.0)]), PO3, {}, TOL)
    r2 = perform_three_way_match(invoice([inv_line("ITEM-005", "Material Description 5", 38, 120.0)]), PO3, {}, TOL)
    assert r1["match_result"] == "FULL_MATCH" and r2["match_result"] == "FULL_MATCH"


def test_absolute_price_slack_for_cheap_items():
    po = make_po([po_line("1", 1, "ITEM-001", "Washer", 1000, 0.30, 1000)])
    r = perform_three_way_match(invoice([inv_line("ITEM-001", "Washer", 1000, 0.32)]), po, {}, TOL)
    assert r["match_result"] == "FULL_MATCH", codes(r)


def test_qty_exceeds_received():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 48, 145.0)])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert "QTY_EXCEEDS_RECEIVED" in codes(r)


def test_qty_within_tolerance():
    po = make_po([po_line("1", 1, "ITEM-005", "Material Description 5", 200, 10.0, 200)])
    r = perform_three_way_match(invoice([inv_line("ITEM-005", "Material Description 5", 202, 10.0)]), po, {}, TOL)
    assert "QTY_EXCEEDS_RECEIVED" not in codes(r)


def test_cumulative_billing_is_enforced():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 20, 145.0)])
    r = perform_three_way_match(inv, PO3, {"1": 30.0}, TOL)   # 30 of 38 already billed
    assert "QTY_EXCEEDS_RECEIVED" in codes(r) and "QTY_EXCEEDS_PO" in codes(r)


def test_billing_unreceived_line_puts_invoice_on_hold():   # audit M6
    inv = invoice([inv_line("ITEM-003", "Material Description 3", 12, 286.33, "EA")])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert codes(r) == {"NOT_RECEIVED"} and r["awaiting_receipt"] is True


def test_unmatched_extra_line():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0),
                   inv_line("SVC-900", "Expedited freight surcharge", 1, 450.0, "EA")])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert "UNMATCHED_LINE" in codes(r)


def test_hidden_fee_in_header_total():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0)])
    inv["subtotal"] += 300.0   # fee not itemised
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert "TOTAL_MISMATCH" in codes(r)


def test_missing_and_closed_po():
    r = perform_three_way_match(invoice([]), None, {}, TOL)
    assert codes(r) == {"MISSING_PO"}
    r2 = perform_three_way_match({**invoice([]), "po_reference": None}, None, {}, TOL)
    assert codes(r2) == {"MISSING_PO_REFERENCE"}
    closed = make_po(PO3["lines"], status="CLOSED")
    r3 = perform_three_way_match(invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0)]), closed, {}, TOL)
    assert "PO_CLOSED" in codes(r3)


def test_same_item_on_two_lines_is_paired_one_to_one():   # audit M7
    po = make_po([po_line("1", 1, "ITEM-004", "Material Description 4", 100, 50.0, 100),
                  po_line("2", 2, "ITEM-004", "Material Description 4", 40, 55.0, 40)])
    inv = invoice([inv_line("ITEM-004", "Material Description 4", 40, 55.0),
                   inv_line("ITEM-004", "Material Description 4", 100, 50.0)])
    r = perform_three_way_match(inv, po, {}, TOL)
    assert r["pairs"] == {0: 1, 1: 0}
    assert r["match_result"] == "FULL_MATCH", codes(r)


def test_description_digits_are_not_confused():
    assert description_score("Material Description 1", "Material Description 12") < 0.8
    assert pair_lines([{"description": "Material Description 1"}],
                      [{"description": "Material Description 12", "item_number": "ITEM-012"}]) == {}


def test_code_variants():
    line = {"item_number": "ITEM-015", "item_id": "1015"}
    assert code_matches("ITEM-015", line) and code_matches("item015", line) and code_matches("1015", line)
    assert code_matches("ITEM-15", line)
    assert not code_matches("ITEM-016", line) and not code_matches(None, line) and not code_matches("PART-015", line)


def test_uom_mismatch_is_medium():
    inv = invoice([inv_line("ITEM-005", "Material Description 5", 38, 145.0, "EA")])
    r = perform_three_way_match(inv, PO3, {}, TOL)
    assert r["match_result"] == "PARTIAL_MATCH" and "UOM_MISMATCH" in codes(r)
