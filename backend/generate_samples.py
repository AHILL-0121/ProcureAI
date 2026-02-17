"""
Generate sample invoice text files from the Oracle ERP dataset.
Creates invoices covering 8 different matching scenarios:
  1. FULL MATCH       - exact quantities and prices (happy path)
  2. PARTIAL MATCH    - small price variance within tolerance (3.5%)
  3. NO MATCH (PRICE) - major price discrepancy (25% overcharge)
  4. NO MATCH (QTY)   - billing for 2x what was ordered
  5. NO PO FOUND      - invoice references PO-999999 (doesn't exist)
  6. FULL MATCH       - multi-line PO with 18% tax
  7. NO MATCH (EXTRA) - invoice has unauthorized extra items
  8. PARTIAL MATCH    - minor qty shortfall (1.5% under)
"""

import csv
import os
import random
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "erp")
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "uploads", "samples")


def load_csv(f):
    with open(os.path.join(DATA_DIR, f), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def clean_id(val):
    return val.split(".")[0] if "." in val else val


def make_invoice(inv_num, inv_date, due_date, po_num, vendor_name, vendor_id,
                 pay_terms, currency, line_items, tax_rate, scenario_label):
    """Build invoice text from parameters."""
    line_texts = []
    subtotal = 0.0
    for i, item in enumerate(line_items, 1):
        line_total = round(item["qty"] * item["price"], 2)
        subtotal += line_total
        line_texts.append(
            f'  {i}. {item["code"]}  {item["desc"]}  '
            f'Qty: {item["qty"]}  Unit Price: {item["price"]:.2f} {currency}  '
            f'Total: {line_total:.2f} {currency}'
        )

    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    sep = "=" * 60

    return f"""INVOICE
{sep}
Invoice Number: {inv_num}
Invoice Date: {inv_date}
Due Date: {due_date}
PO Reference: {po_num}

VENDOR:
  Name: {vendor_name}
  Vendor ID: {vendor_id}
  Payment Terms: {pay_terms}

BILL TO:
  ProcureAI Corp
  123 Business Park
  London, UK

LINE ITEMS:
{chr(10).join(line_texts)}

{sep}
  Subtotal: {subtotal:.2f} {currency}
  Tax ({tax_rate*100:.0f}%): {tax:.2f} {currency}
  TOTAL DUE: {total:.2f} {currency}
{sep}

[Scenario: {scenario_label}]
"""


def main():
    # Clear old samples
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    for f in os.listdir(SAMPLES_DIR):
        os.remove(os.path.join(SAMPLES_DIR, f))

    vendors = {clean_id(r["SUPPLIER_ID"]): r for r in load_csv("vendors.csv")}
    materials = {clean_id(r["ITEM_ID"]): r for r in load_csv("materials.csv")}

    po_headers = {}
    for r in load_csv("po_headers.csv"):
        hid = clean_id(r["PO_HEADER_ID"])
        r["_hid"] = hid
        po_headers[r["PO_NUMBER"]] = r

    po_lines_by_header = defaultdict(list)
    for r in load_csv("po_lines.csv"):
        lid = clean_id(r["PO_LINE_ID"])
        hid = clean_id(r["PO_HEADER_ID"])
        r["_lid"] = lid
        r["_hid"] = hid
        r["_iid"] = clean_id(r["ITEM_ID"])
        po_lines_by_header[hid].append(r)

    grn_by_pol = defaultdict(list)
    for r in load_csv("goods_receipts.csv"):
        grn_by_pol[clean_id(r["PO_LINE_ID"])].append(r)

    inv_by_pol = defaultdict(list)
    for r in load_csv("invoices.csv"):
        inv_by_pol[clean_id(r["PO_LINE_ID"])].append(r)

    # Categorize POs - find those where ALL lines have GRN + invoice
    full_match_pos = []
    for po_num, header in po_headers.items():
        hid = header["_hid"]
        lines = po_lines_by_header.get(hid, [])
        if not lines:
            continue
        has_grn = [bool(grn_by_pol.get(ln["_lid"])) for ln in lines]
        has_inv = [bool(inv_by_pol.get(ln["_lid"])) for ln in lines]
        if all(has_grn) and all(has_inv):
            full_match_pos.append(po_num)

    random.seed(99)

    def get_po_data(po_num):
        h = po_headers[po_num]
        hid = h["_hid"]
        sid = clean_id(h.get("SUPPLIER_ID", "0"))
        v = vendors.get(sid, {})
        lines = po_lines_by_header.get(hid, [])
        items = []
        for ln in lines:
            iid = ln["_iid"]
            mat = materials.get(iid, {})
            items.append({
                "code": mat.get("ITEM_NUMBER", f"ITEM-{iid}"),
                "desc": mat.get("DESCRIPTION", f"Item {iid}"),
                "qty": float(ln.get("QUANTITY", 0)),
                "price": float(ln.get("UNIT_PRICE", 0)),
                "lid": ln["_lid"],
            })
        return h, sid, v, items

    invoices_created = []
    today = datetime.now()
    sorted_fm = sorted(full_match_pos)

    # ──────────────────────────────────────────────────────────
    # SCENARIO 1: FULL MATCH (exact quantities and prices)
    # ──────────────────────────────────────────────────────────
    po1 = sorted_fm[0]
    h, sid, v, items = get_po_data(po1)
    text = make_invoice(
        "INV-FULL-001", (today - timedelta(days=5)).strftime("%Y-%m-%d"),
        (today + timedelta(days=25)).strftime("%Y-%m-%d"),
        po1, v.get("SUPPLIER_NAME", ""), sid, v.get("PAY_TERMS", "NET30"),
        h["CURRENCY"], items, 0.0,
        "FULL MATCH - Exact qty and price, should auto-approve"
    )
    fname = f"scenario_1_full_match_{po1}.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "FULL_MATCH", po1))
    print(f"  1. {fname}")

    # ──────────────────────────────────────────────────────────
    # SCENARIO 2: PARTIAL MATCH (3.5% price increase - within 5% tol)
    # ──────────────────────────────────────────────────────────
    po2 = sorted_fm[5]
    h, sid, v, items = get_po_data(po2)
    for item in items:
        item["price"] = round(item["price"] * 1.035, 2)
    text = make_invoice(
        "INV-PART-002", (today - timedelta(days=3)).strftime("%Y-%m-%d"),
        (today + timedelta(days=27)).strftime("%Y-%m-%d"),
        po2, v.get("SUPPLIER_NAME", ""), sid, v.get("PAY_TERMS", "NET30"),
        h["CURRENCY"], items, 0.05,
        "PARTIAL MATCH - Prices 3.5% higher than PO (within 5% tolerance)"
    )
    fname = f"scenario_2_partial_match_{po2}.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "PARTIAL_MATCH", po2))
    print(f"  2. {fname}")

    # ──────────────────────────────────────────────────────────
    # SCENARIO 3: NO MATCH - Major price overcharge (25% higher)
    # ──────────────────────────────────────────────────────────
    po3 = sorted_fm[10]
    h, sid, v, items = get_po_data(po3)
    for item in items:
        item["price"] = round(item["price"] * 1.25, 2)
    text = make_invoice(
        "INV-OVER-003", (today - timedelta(days=7)).strftime("%Y-%m-%d"),
        (today + timedelta(days=23)).strftime("%Y-%m-%d"),
        po3, v.get("SUPPLIER_NAME", ""), sid, v.get("PAY_TERMS", "NET30"),
        h["CURRENCY"], items, 0.10,
        "NO MATCH - Prices 25% higher than PO (possible fraud or wrong rate)"
    )
    fname = f"scenario_3_price_mismatch_{po3}.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "NO_MATCH", po3))
    print(f"  3. {fname}")

    # ──────────────────────────────────────────────────────────
    # SCENARIO 4: NO MATCH - Quantity overbilling (2x ordered)
    # ──────────────────────────────────────────────────────────
    po4 = sorted_fm[15]
    h, sid, v, items = get_po_data(po4)
    for item in items:
        item["qty"] = round(item["qty"] * 2.0)
    text = make_invoice(
        "INV-QTYHI-004", (today - timedelta(days=2)).strftime("%Y-%m-%d"),
        (today + timedelta(days=28)).strftime("%Y-%m-%d"),
        po4, v.get("SUPPLIER_NAME", ""), sid, v.get("PAY_TERMS", "NET30"),
        h["CURRENCY"], items, 0.0,
        "NO MATCH - Quantity doubled (billing for 2x what was ordered/received)"
    )
    fname = f"scenario_4_qty_overbill_{po4}.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "NO_MATCH", po4))
    print(f"  4. {fname}")

    # ──────────────────────────────────────────────────────────
    # SCENARIO 5: NO MATCH - PO doesn't exist
    # ──────────────────────────────────────────────────────────
    fake_items = [{"code": "ITEM-007", "desc": "Material Description 7",
                   "qty": 100, "price": 250.00}]
    text = make_invoice(
        "INV-FAKE-005", (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        (today + timedelta(days=29)).strftime("%Y-%m-%d"),
        "PO-999999", "Unknown Vendor Corp", "999", "NET30", "USD",
        fake_items, 0.18,
        "NO MATCH - PO-999999 does not exist in ERP (possible fraud)"
    )
    fname = "scenario_5_fake_po_PO-999999.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "NO_MATCH", "PO-999999"))
    print(f"  5. {fname}")

    # ──────────────────────────────────────────────────────────
    # SCENARIO 6: FULL MATCH - Multi-line PO with 18% tax
    # ──────────────────────────────────────────────────────────
    multi_line_pos = [p for p in full_match_pos
                      if len(po_lines_by_header.get(po_headers[p]["_hid"], [])) >= 3]
    po6 = sorted(multi_line_pos)[0] if multi_line_pos else sorted_fm[20]
    h, sid, v, items = get_po_data(po6)
    text = make_invoice(
        "INV-MULTI-006", (today - timedelta(days=10)).strftime("%Y-%m-%d"),
        (today + timedelta(days=20)).strftime("%Y-%m-%d"),
        po6, v.get("SUPPLIER_NAME", ""), sid, v.get("PAY_TERMS", "NET30"),
        h["CURRENCY"], items, 0.18,
        "FULL MATCH - Multi-line PO with 18% tax, all items correct"
    )
    fname = f"scenario_6_full_match_multiline_{po6}.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "FULL_MATCH", po6))
    print(f"  6. {fname}")

    # ──────────────────────────────────────────────────────────
    # SCENARIO 7: NO MATCH - Extra unauthorized line items
    # ──────────────────────────────────────────────────────────
    po7 = sorted_fm[25]
    h, sid, v, items = get_po_data(po7)
    items.append({"code": "ITEM-099", "desc": "Unauthorized Service Charge",
                  "qty": 1, "price": 5000.00})
    items.append({"code": "ITEM-098", "desc": "Express Shipping Surcharge",
                  "qty": 1, "price": 2500.00})
    text = make_invoice(
        "INV-EXTRA-007", (today - timedelta(days=4)).strftime("%Y-%m-%d"),
        (today + timedelta(days=26)).strftime("%Y-%m-%d"),
        po7, v.get("SUPPLIER_NAME", ""), sid, v.get("PAY_TERMS", "NET30"),
        h["CURRENCY"], items, 0.0,
        "NO MATCH - Invoice has extra items not in PO (unauthorized charges)"
    )
    fname = f"scenario_7_extra_items_{po7}.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "NO_MATCH", po7))
    print(f"  7. {fname}")

    # ──────────────────────────────────────────────────────────
    # SCENARIO 8: PARTIAL MATCH - Minor qty shortfall (1.5% under)
    # ──────────────────────────────────────────────────────────
    po8 = sorted_fm[30]
    h, sid, v, items = get_po_data(po8)
    for item in items:
        item["qty"] = round(item["qty"] * 0.985)
    text = make_invoice(
        "INV-QTYLO-008", (today - timedelta(days=6)).strftime("%Y-%m-%d"),
        (today + timedelta(days=24)).strftime("%Y-%m-%d"),
        po8, v.get("SUPPLIER_NAME", ""), sid, v.get("PAY_TERMS", "NET30"),
        h["CURRENCY"], items, 0.05,
        "PARTIAL MATCH - Qty 1.5% under PO (within 2% tolerance, minor flag)"
    )
    fname = f"scenario_8_minor_qty_diff_{po8}.txt"
    with open(os.path.join(SAMPLES_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    invoices_created.append((fname, "PARTIAL_MATCH", po8))
    print(f"  8. {fname}")

    # ──────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────
    print(f"\nDone! {len(invoices_created)} scenario invoices in {SAMPLES_DIR}\n")
    print("SCENARIO SUMMARY:")
    print("-" * 80)
    for fname, expected, po in invoices_created:
        print(f"  {fname}")
        print(f"    Expected: {expected} | PO: {po}")
    print("-" * 80)


if __name__ == "__main__":
    main()