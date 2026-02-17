"""
Agent 5: Matching & Reconciliation Agent
Performs three-way match: Invoice vs. PO vs. Receipt.
Flags discrepancies with configurable tolerances.
"""

import logging
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

# Matching tolerances (from SRS)
QUANTITY_TOLERANCE = 0.02   # ±2%
PRICE_TOLERANCE = 0.05      # ±5%
DESCRIPTION_THRESHOLD = 0.85 # 85% fuzzy match


class MatchingAgent:
    """Three-way matching engine: Invoice ↔ PO ↔ Goods Receipt."""

    def perform_three_way_match(
        self,
        invoice_data: dict,
        po_data: Optional[dict],
        grn_data: Optional[dict]
    ) -> dict:
        """
        Main matching pipeline:
        1. Invoice → PO match (2-way)
        2. PO → GRN match (delivery verification)
        3. Invoice → GRN match (quantity received)
        4. Aggregate result
        """
        result = {
            "match_result": "PENDING",
            "invoice_po_match": None,
            "po_grn_match": None,
            "invoice_grn_match": None,
            "discrepancies": [],
            "summary": {},
            "score": 0.0,
        }

        if not po_data:
            result["match_result"] = "NO_MATCH"
            result["discrepancies"].append({
                "type": "MISSING_PO",
                "severity": "HIGH",
                "message": f"Purchase Order '{invoice_data.get('po_reference', 'N/A')}' not found in ERP"
            })
            return result

        # 1. Invoice ↔ PO matching
        invoice_po = self._match_invoice_to_po(invoice_data, po_data)
        result["invoice_po_match"] = invoice_po

        # 2. PO ↔ GRN matching
        if grn_data:
            po_grn = self._match_po_to_grn(po_data, grn_data)
            result["po_grn_match"] = po_grn
        else:
            result["discrepancies"].append({
                "type": "MISSING_GRN",
                "severity": "MEDIUM",
                "message": "No Goods Receipt found for this PO - delivery not confirmed"
            })

        # 3. Invoice ↔ GRN matching
        if grn_data:
            invoice_grn = self._match_invoice_to_grn(invoice_data, grn_data)
            result["invoice_grn_match"] = invoice_grn

        # 4. Aggregate discrepancies
        all_discs = result["discrepancies"]
        if invoice_po:
            all_discs.extend(invoice_po.get("discrepancies", []))
        if result.get("po_grn_match"):
            all_discs.extend(result["po_grn_match"].get("discrepancies", []))
        if result.get("invoice_grn_match"):
            all_discs.extend(result["invoice_grn_match"].get("discrepancies", []))

        # Determine overall result
        high_severity = [d for d in all_discs if d.get("severity") == "HIGH"]
        medium_severity = [d for d in all_discs if d.get("severity") == "MEDIUM"]

        if len(high_severity) > 0:
            result["match_result"] = "NO_MATCH"
            result["score"] = max(0, 1.0 - (len(high_severity) * 0.3 + len(medium_severity) * 0.1))
        elif len(medium_severity) > 0:
            result["match_result"] = "PARTIAL_MATCH"
            result["score"] = max(0, 1.0 - len(medium_severity) * 0.1)
        elif len(all_discs) == 0:
            result["match_result"] = "FULL_MATCH"
            result["score"] = 1.0
        else:
            result["match_result"] = "PARTIAL_MATCH"
            result["score"] = 0.85

        result["summary"] = {
            "total_discrepancies": len(all_discs),
            "high_severity": len(high_severity),
            "medium_severity": len(medium_severity),
            "low_severity": len([d for d in all_discs if d.get("severity") == "LOW"]),
        }

        return result

    def _match_invoice_to_po(self, invoice: dict, po: dict) -> dict:
        """Compare invoice line items against PO line items."""
        result = {"match_type": "INVOICE_PO", "discrepancies": [], "matched_items": 0, "total_items": 0}

        inv_items = invoice.get("line_items", [])
        po_items = po.get("items", [])
        result["total_items"] = len(inv_items)

        # Total amount comparison (use subtotal if available, since PO total is pre-tax)
        inv_total = invoice.get("subtotal") or invoice.get("total_amount", 0)
        po_total = po.get("total_amount", 0)
        if po_total > 0:
            variance = abs(inv_total - po_total) / po_total
            if variance > PRICE_TOLERANCE:
                result["discrepancies"].append({
                    "type": "TOTAL_MISMATCH",
                    "severity": "HIGH",
                    "message": f"Invoice total (${inv_total:,.2f}) differs from PO total (${po_total:,.2f}) by {variance*100:.1f}%",
                    "invoice_value": inv_total,
                    "po_value": po_total,
                    "variance_pct": round(variance * 100, 1)
                })

        # Line item matching
        for inv_item in inv_items:
            best_match = self._find_best_item_match(inv_item, po_items)
            if best_match:
                result["matched_items"] += 1
                # Check quantity
                inv_qty = inv_item.get("quantity", 0)
                po_qty = best_match.get("quantity", 0)
                if po_qty > 0:
                    qty_variance = abs(inv_qty - po_qty) / po_qty
                    if qty_variance > QUANTITY_TOLERANCE:
                        result["discrepancies"].append({
                            "type": "QUANTITY_MISMATCH",
                            "severity": "MEDIUM",
                            "message": f"Item '{inv_item.get('description', '')}': Invoice qty ({inv_qty}) vs PO qty ({po_qty})",
                            "invoice_value": inv_qty,
                            "po_value": po_qty,
                        })

                # Check unit price
                inv_price = inv_item.get("unit_price", 0)
                po_price = best_match.get("unit_price", 0)
                if po_price > 0:
                    price_variance = abs(inv_price - po_price) / po_price
                    if price_variance > PRICE_TOLERANCE:
                        result["discrepancies"].append({
                            "type": "PRICE_MISMATCH",
                            "severity": "HIGH",
                            "message": f"Item '{inv_item.get('description', '')}': Invoice price (${inv_price:,.2f}) vs PO price (${po_price:,.2f})",
                            "invoice_value": inv_price,
                            "po_value": po_price,
                        })
            else:
                result["discrepancies"].append({
                    "type": "UNMATCHED_ITEM",
                    "severity": "MEDIUM",
                    "message": f"Invoice item '{inv_item.get('description', '')}' not found in PO"
                })

        return result

    def _match_po_to_grn(self, po: dict, grn: dict) -> dict:
        """Compare PO items against goods received."""
        result = {"match_type": "PO_GRN", "discrepancies": []}

        po_items = po.get("items", [])
        grn_items = grn.get("items", [])

        for po_item in po_items:
            grn_match = self._find_best_item_match(po_item, grn_items)
            if grn_match:
                po_qty = po_item.get("quantity", 0)
                grn_qty = grn_match.get("quantity", 0)
                if po_qty > 0 and abs(po_qty - grn_qty) / po_qty > QUANTITY_TOLERANCE:
                    result["discrepancies"].append({
                        "type": "DELIVERY_SHORTAGE",
                        "severity": "MEDIUM",
                        "message": f"Item '{po_item.get('description', '')}': Ordered {po_qty}, received {grn_qty}",
                        "ordered": po_qty,
                        "received": grn_qty,
                    })
            else:
                result["discrepancies"].append({
                    "type": "NOT_RECEIVED",
                    "severity": "HIGH",
                    "message": f"PO item '{po_item.get('description', '')}' not found in goods receipt"
                })

        return result

    def _match_invoice_to_grn(self, invoice: dict, grn: dict) -> dict:
        """Compare invoice items against goods received."""
        result = {"match_type": "INVOICE_GRN", "discrepancies": []}

        inv_items = invoice.get("line_items", [])
        grn_items = grn.get("items", [])

        for inv_item in inv_items:
            grn_match = self._find_best_item_match(inv_item, grn_items)
            if grn_match:
                inv_qty = inv_item.get("quantity", 0)
                grn_qty = grn_match.get("quantity", 0)
                if grn_qty > 0 and abs(inv_qty - grn_qty) / grn_qty > QUANTITY_TOLERANCE:
                    result["discrepancies"].append({
                        "type": "INVOICE_RECEIPT_QTY",
                        "severity": "MEDIUM",
                        "message": f"Item '{inv_item.get('description', '')}': Invoiced {inv_qty}, received {grn_qty}",
                    })

        return result

    def _find_best_item_match(self, target: dict, candidates: list[dict]) -> Optional[dict]:
        """Find the best matching item using item_code or fuzzy description match."""
        target_code = target.get("item_code", "")
        target_desc = target.get("description", "")

        # Try exact item code match first
        if target_code:
            for candidate in candidates:
                if candidate.get("item_code") == target_code:
                    return candidate

        # Fuzzy description match
        best_score = 0
        best_match = None
        for candidate in candidates:
            cand_desc = candidate.get("description", "")
            score = SequenceMatcher(None, target_desc.lower(), cand_desc.lower()).ratio()
            if score > best_score and score >= DESCRIPTION_THRESHOLD:
                best_score = score
                best_match = candidate

        return best_match
