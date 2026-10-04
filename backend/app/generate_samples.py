"""
Write demo invoices (plain-text) into backend/samples/, built from real ERP purchase orders so
each one exercises a specific matching rule.

    python -m app.generate_samples
"""

import os
from collections import defaultdict

from app.seed_erp import norm_id, read_csv

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "samples")


def load():
    vendors = {norm_id(r["SUPPLIER_ID"]): r for r in read_csv("vendors.csv")}
    materials = {norm_id(r["ITEM_ID"]): r for r in read_csv("materials.csv")}
    headers = {norm_id(r["PO_HEADER_ID"]): r for r in read_csv("po_headers.csv")}
    lines = defaultdict(list)
    for r in read_csv("po_lines.csv"):
        lines[norm_id(r["PO_HEADER_ID"])].append(r)
    received = defaultdict(float)
    for r in read_csv("goods_receipts.csv"):
        received[norm_id(r["PO_LINE_ID"])] += float(r["RECEIVED_QTY"])
    pos = []
    for hid, h in sorted(headers.items(), key=lambda kv: kv[1]["PO_NUMBER"]):
        ls = []
        for ln in lines[hid]:
            mat = materials.get(norm_id(ln["ITEM_ID"]))
            if not mat:
                continue   # a few PO lines have no item; they are not useful for demos
            ls.append({"id": norm_id(ln["PO_LINE_ID"]), "item_number": mat["ITEM_NUMBER"],
                       "description": mat["DESCRIPTION"], "uom": ln["UOM"],
                       "qty": float(ln["QUANTITY"]), "price": float(ln["UNIT_PRICE"]),
                       "received": received.get(norm_id(ln["PO_LINE_ID"]), 0.0)})
        v = vendors.get(norm_id(h["SUPPLIER_ID"]))
        if not v or not ls or len(ls) != len(lines[hid]):
            continue
        pos.append({"po": h["PO_NUMBER"], "currency": h["CURRENCY"], "vendor": v["SUPPLIER_NAME"],
                    "tax": v["TAX_ID"], "terms": v["PAY_TERMS"], "lines": ls})
    return pos, vendors


def render(number, date, vendor, tax, po, currency, items, terms="NET30", note=None):
    rows = []
    subtotal = 0.0
    for it in items:
        total = round(it["qty"] * it["price"], 2)
        subtotal += total
        rows.append(f"{it['item_number']:<10} {it['description']:<26} {it['qty']:>7g} {it['uom']:<4} "
                    f"{it['price']:>10,.2f} {total:>12,.2f}")
    tax_amt = round(subtotal * 0.10, 2)
    lines = [
        "=" * 78, f"{'TAX INVOICE':^78}", "=" * 78,
        vendor, "Unit 4, Industrial Estate", f"Tax ID: {tax}", "",
        f"Invoice Number: {number}", f"Invoice Date:   {date}", f"PO Reference:   {po}", f"Currency:       {currency}",
        f"Payment Terms:  {terms}", "", "Bill To: ProcureAI Demo Corp, Accounts Payable", "-" * 78,
        f"{'ITEM':<10} {'DESCRIPTION':<26} {'QTY':>7} {'UOM':<4} {'UNIT PRICE':>10} {'AMOUNT':>12}", "-" * 78,
        *rows, "-" * 78,
        f"{'Subtotal':>64} {subtotal:>12,.2f}", f"{'Tax (10%)':>64} {tax_amt:>12,.2f}",
        f"{'TOTAL DUE':>64} {subtotal + tax_amt:>12,.2f}", "",
    ]
    if note:
        lines.append(f"Note: {note}")
    return "\n".join(lines) + "\n"


def build():
    pos, vendors = load()

    def pick(pred, skip=()):
        for p in pos:
            if p["po"] not in skip and pred(p):
                return p
        raise RuntimeError("no PO matches scenario")

    def billable(ln, qty=None, price=None):
        return {**ln, "qty": ln["received"] if qty is None else qty, "price": ln["price"] if price is None else price}

    used = set()
    s = []

    p = pick(lambda p: len(p["lines"]) == 1 and p["lines"][0]["received"] == p["lines"][0]["qty"])

    used.add(p["po"])
    s.append(("01_full_match", p, [billable(p["lines"][0])], {}))
    dup_of = (p, [billable(p["lines"][0])])

    p = pick(lambda p: len(p["lines"]) >= 2 and all(l["received"] > 0 for l in p["lines"]), used)

    used.add(p["po"])
    s.append(("02_partial_invoice_one_line_FULL_MATCH", p, [billable(p["lines"][0])], {}))

    p = pick(lambda p: len(p["lines"]) == 1 and p["lines"][0]["received"] > 0, used)

    used.add(p["po"])
    s.append(("03_price_over_tolerance", p, [billable(p["lines"][0], price=round(p["lines"][0]["price"] * 1.08, 2))], {}))

    p = pick(lambda p: len(p["lines"]) == 1 and 10 < p["lines"][0]["received"], used)

    used.add(p["po"])
    s.append(("04_qty_exceeds_received", p, [billable(p["lines"][0], qty=p["lines"][0]["received"] + 10)], {}))

    fake = {**pos[0], "po": "PO-999999"}
    s.append(("05_unknown_po", fake, [billable(pos[0]["lines"][0], qty=5)], {}))

    p = pick(lambda p: len(p["lines"]) >= 3 and all(l["received"] > 0 for l in p["lines"]), used)

    used.add(p["po"])
    s.append(("06_multiline_full_match", p, [billable(l) for l in p["lines"]], {}))

    p = pick(lambda p: len(p["lines"]) == 1 and p["lines"][0]["received"] > 0, used)

    used.add(p["po"])
    extra = {"item_number": "SVC-900", "description": "Expedited freight surcharge", "uom": "EA", "qty": 1, "price": 450.0}
    s.append(("07_unauthorised_extra_line", p, [billable(p["lines"][0]), extra], {}))

    p = pick(lambda p: len(p["lines"]) == 1 and p["lines"][0]["received"] >= 100, used)

    used.add(p["po"])
    s.append(("08_qty_within_tolerance", p, [billable(p["lines"][0], qty=round(p["lines"][0]["received"] * 1.01))], {}))

    p = pick(lambda p: len(p["lines"]) >= 2 and p["lines"][0]["received"] > 0 and any(l["received"] == 0 for l in p["lines"][1:]), used)

    used.add(p["po"])
    s.append(("09_unreceived_line_not_billed_FULL_MATCH", p, [billable(p["lines"][0])], {}))

    p = pick(lambda p: len(p["lines"]) == 1 and p["lines"][0]["received"] > 0, used)

    used.add(p["po"])
    other = next(v for v in vendors.values() if v["SUPPLIER_NAME"] != p["vendor"])
    s.append(("10_vendor_mismatch", p, [billable(p["lines"][0])], {"vendor": other["SUPPLIER_NAME"], "tax": other["TAX_ID"]}))

    p = pick(lambda p: len(p["lines"]) == 1 and p["lines"][0]["received"] > 0, used)

    used.add(p["po"])
    wrong = "USD" if p["currency"] != "USD" else "EUR"
    s.append(("11_currency_mismatch", p, [billable(p["lines"][0])], {"currency": wrong}))

    p = pick(lambda p: len(p["lines"]) == 1 and p["lines"][0]["received"] == 0, used)

    used.add(p["po"])
    s.append(("12_goods_not_received_ON_HOLD", p, [billable(p["lines"][0], qty=p["lines"][0]["qty"])], {}))

    s.append(("13_duplicate_of_01", dup_of[0], dup_of[1], {"note": "Resent copy"}))
    return s


def create_samples() -> list[str]:
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    paths = []
    for i, (name, p, items, over) in enumerate(build(), start=1):
        number = "INV-DEMO-001" if name.startswith("13_") else f"INV-DEMO-{i:03d}"
        text = render(number, "2026-09-14", over.get("vendor", p["vendor"]), over.get("tax", p["tax"]), p["po"],
                      over.get("currency", p["currency"]), items, p.get("terms", "NET30"), over.get("note"))
        path = os.path.join(SAMPLES_DIR, f"{name}_{p['po']}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        paths.append(path)
    return paths


if __name__ == "__main__":
    for path in create_samples():
        print("wrote", os.path.relpath(path))
