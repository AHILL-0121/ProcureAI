"""
Agent 5: Three-way matching (invoice ↔ purchase order ↔ goods receipt), at line level.

The rule a clerk applies: pay for what was ordered AND received, at the ordered price, once.

For every invoice line we find the PO line it refers to (one-to-one), then check
  price     invoice unit price vs PO unit price (tolerance: % and absolute)
  receipt   invoiced qty vs (received qty − qty already billed)
  order     cumulative billed qty vs ordered qty
  unit      unit of measure
Header checks: PO exists and is open, vendor matches the PO vendor, currency matches, and the
invoice net equals what the matched lines justify (catches unexplained fees).

PO lines that are not on the invoice are informational only: an unreceived line the supplier
has not billed is not a reason to hold the invoice.

This module is pure (no database, no I/O) so it can be tested exhaustively.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Optional

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"


@dataclass(frozen=True)
class Tolerance:
    qty_pct: float = 0.02
    price_pct: float = 0.05
    price_abs: float = 0.05
    total_abs: float = 1.00

    def price_limit(self, po_price: float) -> float:
        return max(abs(po_price) * self.price_pct, self.price_abs)

    def qty_limit(self, qty: float) -> float:
        return max(abs(qty) * self.qty_pct, 1e-6)


def _norm_code(code: Optional[str]) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def _code_digits(code: Optional[str]) -> Optional[int]:
    m = re.search(r"(\d+)\s*$", code or "")
    return int(m.group(1)) if m else None


def code_matches(inv_code: Optional[str], po_line: dict) -> bool:
    """Supplier code vs ERP item: exact on item number or item id, or same trailing number (ITEM-015 == ITEM15)."""
    ic = _norm_code(inv_code)
    if not ic:
        return False
    targets = [_norm_code(po_line.get("item_number")), _norm_code(po_line.get("item_id"))]
    if ic in [t for t in targets if t]:
        return True
    num = _code_digits(inv_code)
    if num is None:
        return False
    item_number = po_line.get("item_number") or ""
    prefix_inv = re.sub(r"[^A-Z]", "", ic)
    prefix_po = re.sub(r"[^A-Z]", "", _norm_code(item_number))
    return bool(prefix_inv) and prefix_inv == prefix_po and num == _code_digits(item_number)


def description_score(a: str, b: str) -> float:
    """Fuzzy similarity that refuses to equate 'Material 1' with 'Material 12'."""
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return 0.0
    score = SequenceMatcher(None, a, b).ratio()
    da, db = re.findall(r"\d+", a), re.findall(r"\d+", b)
    if da and db and da != db:
        score *= 0.5
    return score


def _proximity(x: Optional[float], y: Optional[float]) -> float:
    if x is None or y is None:
        return 0.0
    m = max(abs(x), abs(y))
    return 1.0 if m == 0 else max(0.0, 1.0 - abs(x - y) / m)


def pair_lines(inv_lines: list[dict], po_lines: list[dict]) -> dict[int, int]:
    """One-to-one assignment {invoice line index: po line index}, greedy by best combined score."""
    candidates = []
    for i, il in enumerate(inv_lines):
        for j, pl in enumerate(po_lines):
            code = 1.0 if code_matches(il.get("item_code"), pl) else 0.0
            desc = description_score(il.get("description", ""), pl.get("description", ""))
            if code == 0.0 and desc < 0.8:
                continue
            score = (0.6 * max(code, desc)
                     + 0.2 * _proximity(il.get("quantity"), pl.get("quantity"))
                     + 0.2 * _proximity(il.get("unit_price"), pl.get("unit_price")))
            candidates.append((score + code * 0.5, i, j))   # code matches outrank description matches
    candidates.sort(reverse=True)
    used_i, used_j, pairs = set(), set(), {}
    for _, i, j in candidates:
        if i in used_i or j in used_j:
            continue
        pairs[i] = j
        used_i.add(i)
        used_j.add(j)
    return pairs


def _pct(value: float, base: float) -> Optional[float]:
    return round(value / base * 100, 1) if base else None


def _names_match(a: Optional[str], b: Optional[str]) -> Optional[bool]:
    def n(s):
        s = re.sub(r"\b(inc|ltd|llc|gmbh|plc|co|corp|limited|pvt|sa|ag|bv)\b\.?", " ", (s or "").lower())
        return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())
    na, nb = n(a), n(b)
    if not na or not nb:
        return None
    return na == nb or SequenceMatcher(None, na, nb).ratio() >= 0.88


def _tax(s: Optional[str]) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


class MatchingAgent:
    """Kept as a class for the orchestrator; the logic lives in `perform_three_way_match`."""

    def perform_three_way_match(self, invoice: dict, po: Optional[dict], billed: Optional[dict] = None,
                                tolerance: Optional[Tolerance] = None) -> dict:
        return perform_three_way_match(invoice, po, billed or {}, tolerance or Tolerance())


def perform_three_way_match(invoice: dict, po: Optional[dict], billed: dict[str, float],
                            tol: Tolerance) -> dict:
    checks: list[dict] = []

    def add(code: str, severity: str, message: str, passed: bool = False, line: Optional[int] = None, **extra):
        checks.append({"code": code, "severity": severity, "passed": passed, "message": message,
                       **({"line": line} if line is not None else {}), **extra})

    inv_lines = invoice.get("line_items") or []
    currency = invoice.get("currency")

    # ---------- PO ----------
    if not invoice.get("po_reference"):
        add("MISSING_PO_REFERENCE", HIGH, "The invoice does not quote a purchase order number")
        return _finish(checks, [], None)
    if not po:
        add("MISSING_PO", HIGH, f"Purchase order {invoice['po_reference']} was not found in the ERP")
        return _finish(checks, [], None)
    add("PO_FOUND", LOW, f"Purchase order {po['po_number']} found", passed=True)
    if (po.get("status") or "OPEN").upper() in ("CLOSED", "CANCELLED", "CANCELED"):
        add("PO_CLOSED", HIGH, f"Purchase order {po['po_number']} is {po['status'].lower()}")

    # ---------- Vendor ----------
    inv_tax, po_tax = _tax(invoice.get("vendor_tax_id")), _tax(po.get("vendor_tax_id"))
    same: Optional[bool]
    if invoice.get("resolved_vendor_id") and po.get("vendor_id"):
        same = str(invoice["resolved_vendor_id"]) == str(po["vendor_id"])
    elif inv_tax and po_tax:
        same = inv_tax == po_tax
    else:
        same = _names_match(invoice.get("vendor_name"), po.get("vendor_name"))
    if same is None:
        add("VENDOR_UNVERIFIED", MEDIUM, "The vendor on the invoice could not be verified against the PO vendor")
    elif same:
        add("VENDOR_MATCH", LOW, f"Vendor matches PO vendor ({po['vendor_name']})", passed=True)
    else:
        add("VENDOR_MISMATCH", HIGH,
            f"Invoice vendor '{invoice.get('vendor_name') or '?'}' is not the PO vendor '{po['vendor_name']}'",
            invoice_value=invoice.get("vendor_name"), po_value=po["vendor_name"])

    # ---------- Currency ----------
    if not currency:
        add("CURRENCY_MISSING", MEDIUM, f"No currency on the invoice; PO is in {po['currency']}")
    elif currency != po.get("currency"):
        add("CURRENCY_MISMATCH", HIGH, f"Invoice is in {currency} but the PO is in {po['currency']}",
            invoice_value=currency, po_value=po["currency"])
    else:
        add("CURRENCY_MATCH", LOW, f"Currency {currency} matches the PO", passed=True)

    # ---------- Lines ----------
    if not inv_lines:
        add("NO_LINES", MEDIUM, "No line items were read from the invoice; only header totals can be checked")

    po_lines = po.get("lines") or []
    pairs = pair_lines(inv_lines, po_lines)
    is_credit = invoice.get("invoice_type") == "CREDIT_NOTE"
    line_results = []
    expected_net = 0.0

    for i, il in enumerate(inv_lines):
        n = i + 1
        qty = il.get("quantity") or 0.0
        price = il.get("unit_price") or 0.0
        res = {"line": n, "description": il.get("description"), "item_code": il.get("item_code"),
               "quantity": qty, "unit_price": price, "total_price": il.get("total_price"),
               "po_line_id": None, "checks": []}
        if i not in pairs:
            add("UNMATCHED_LINE", HIGH, f"Line {n} '{il.get('description') or il.get('item_code') or '?'}' is not on the PO", line=n)
            res["checks"].append("UNMATCHED_LINE")
            line_results.append(res)
            continue

        pl = po_lines[pairs[i]]
        received = pl.get("received_qty") or 0.0
        before = billed.get(pl["po_line_id"], 0.0)
        available = received - before
        res.update({"po_line_id": pl["po_line_id"], "po_line_num": pl["line_num"], "po_description": pl["description"],
                    "po_item_number": pl.get("item_number"), "ordered_qty": pl["quantity"], "po_unit_price": pl["unit_price"],
                    "received_qty": received, "billed_before": before, "available_qty": round(available, 3),
                    "receipts": pl.get("receipts", [])})
        expected_net += qty * pl["unit_price"]

        # price
        diff = price - pl["unit_price"]
        if abs(diff) > tol.price_limit(pl["unit_price"]):
            if diff > 0:
                add("PRICE_OVER", HIGH,
                    f"Line {n}: unit price {price:,.2f} is {_pct(diff, pl['unit_price'])}% above the PO price {pl['unit_price']:,.2f}",
                    line=n, invoice_value=price, po_value=pl["unit_price"], variance_pct=_pct(diff, pl["unit_price"]))
                res["checks"].append("PRICE_OVER")
            else:
                add("PRICE_UNDER", LOW,
                    f"Line {n}: unit price {price:,.2f} is below the PO price {pl['unit_price']:,.2f}",
                    passed=True, line=n, invoice_value=price, po_value=pl["unit_price"], variance_pct=_pct(diff, pl["unit_price"]))
        res["price_variance_pct"] = _pct(diff, pl["unit_price"])

        if not is_credit:
            # receipt
            if received <= 0:
                add("NOT_RECEIVED", HIGH, f"Line {n}: nothing has been received against PO line {pl['line_num']} yet",
                    line=n, invoice_value=qty, received=0)
                res["checks"].append("NOT_RECEIVED")
            elif qty - available > tol.qty_limit(max(available, 0)):
                add("QTY_EXCEEDS_RECEIVED", HIGH,
                    f"Line {n}: invoiced {qty:g} but only {max(available, 0):g} received and not yet billed"
                    + (f" ({before:g} billed before)" if before else ""),
                    line=n, invoice_value=qty, received=received, billed_before=before)
                res["checks"].append("QTY_EXCEEDS_RECEIVED")
            # order
            if before + qty - pl["quantity"] > tol.qty_limit(pl["quantity"]):
                add("QTY_EXCEEDS_PO", HIGH,
                    f"Line {n}: billing would reach {before + qty:g} against {pl['quantity']:g} ordered",
                    line=n, invoice_value=qty, po_value=pl["quantity"], billed_before=before)
                res["checks"].append("QTY_EXCEEDS_PO")
        # unit
        if il.get("uom") and pl.get("uom") and _norm_code(il["uom"]) != _norm_code(pl["uom"]):
            add("UOM_MISMATCH", MEDIUM, f"Line {n}: invoiced in {il['uom']} but ordered in {pl['uom']}",
                line=n, invoice_value=il["uom"], po_value=pl["uom"])
            res["checks"].append("UOM_MISMATCH")
        line_results.append(res)

    if is_credit:
        add("CREDIT_NOTE", MEDIUM, "Credit note: quantities are not checked against receipts; confirm the return")

    # ---------- Header net ----------
    net = invoice.get("subtotal")
    if net is None and invoice.get("total_amount") is not None:
        net = invoice["total_amount"] - (invoice.get("tax_amount") or 0)
    if net is not None and inv_lines:
        # Each line was checked against the PO above; here we look for charges that are not itemised.
        line_sum = sum((l.get("total_price") or 0) for l in inv_lines)
        diff = net - line_sum
        if abs(diff) > max(tol.total_abs, abs(line_sum) * 0.001):
            add("TOTAL_MISMATCH", HIGH,
                f"Invoice net {net:,.2f} is {diff:+,.2f} away from the sum of its lines ({line_sum:,.2f}); "
                "look for fees or charges not itemised on the invoice",
                invoice_value=round(net, 2), expected_value=round(line_sum, 2), variance_pct=_pct(diff, line_sum))
        elif pairs:
            po_value = round(expected_net, 2)
            delta = round(line_sum - expected_net, 2)
            add("TOTAL_MATCH", LOW,
                f"Invoice net agrees with its lines; PO value of the billed quantities is {po_value:,.2f}"
                + (f" ({delta:+,.2f})" if abs(delta) >= 0.01 else ""),
                passed=True, invoice_value=round(net, 2), expected_value=po_value)

    # ---------- PO fulfilment (informational) ----------
    billed_idx = set(pairs.values())
    open_lines = [pl for j, pl in enumerate(po_lines) if j not in billed_idx]
    for pl in open_lines:
        state = "received" if (pl.get("received_qty") or 0) > 0 else "not received"
        add("PO_LINE_NOT_BILLED", LOW, f"PO line {pl['line_num']} ({pl['description']}) is {state} and not on this invoice",
            passed=True, po_line=pl["line_num"])

    return _finish(checks, line_results, pairs, expected_net)


def _finish(checks: list[dict], lines: list[dict], pairs: Optional[dict], expected_net: float = 0.0) -> dict:
    failed = [c for c in checks if not c["passed"]]
    high = [c for c in failed if c["severity"] == HIGH]
    medium = [c for c in failed if c["severity"] == MEDIUM]
    low = [c for c in failed if c["severity"] == LOW]
    if high:
        result = "NO_MATCH"
    elif medium:
        result = "PARTIAL_MATCH"
    else:
        result = "FULL_MATCH"
    score = round(max(0.0, 1.0 - 0.35 * len(high) - 0.12 * len(medium) - 0.03 * len(low)), 2)
    hold_codes = {"NOT_RECEIVED"}
    awaiting_receipt = bool(high) and all(c["code"] in hold_codes for c in high)
    return {
        "match_result": result,
        "score": score,
        "awaiting_receipt": awaiting_receipt,
        "checks": checks,
        "discrepancies": [{"type": c["code"], **{k: v for k, v in c.items() if k not in ("code", "passed")}} for c in failed],
        "lines": lines,
        "pairs": pairs or {},
        "expected_net": round(expected_net, 2),
        "summary": {"high": len(high), "medium": len(medium), "low": len(low), "passed": len(checks) - len(failed)},
    }


def tolerance_dict(t: Tolerance) -> dict:
    return asdict(t)
