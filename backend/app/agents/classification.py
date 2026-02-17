"""
Agent 3: Classification & Validation Agent
Validates extracted invoice data, classifies invoice type, enriches with business rules.
"""

import hashlib
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Known vendor database (expanded in production)
KNOWN_VENDORS = {
    "V-001": "Acme Industrial Supplies",
    "V-002": "TechVision Electronics",
    "V-003": "GreenLeaf Office Products",
    "V-004": "SafeGuard PPE Co.",
    "V-005": "CleanPro Janitorial",
    "V-006": "MetalWorks Fabrication",
    "V-007": "PowerDrive Electric",
    "V-008": "BuildRight Construction",
    "V-009": "FreshFlow HVAC",
    "V-010": "AutoParts Direct",
}

# In-memory hash store for deduplication
_invoice_hashes: set[str] = set()


class ClassificationAgent:
    """Validate, classify, and enrich extracted invoice data."""

    def validate_and_classify(self, extracted_data: dict) -> dict:
        """
        Main pipeline:
        1. Schema validation
        2. Invoice type classification
        3. Duplicate detection
        4. Anomaly detection
        5. Vendor enrichment
        """
        result = {
            "valid": True,
            "invoice_type": "STANDARD",
            "validation_errors": [],
            "warnings": [],
            "enriched_data": dict(extracted_data),
            "is_duplicate": False,
        }

        # 1. Schema validation
        self._validate_schema(extracted_data, result)

        # 2. Classify invoice type
        result["invoice_type"] = self._classify_type(extracted_data)

        # 3. Duplicate detection
        invoice_hash = self._compute_hash(extracted_data)
        if invoice_hash in _invoice_hashes:
            result["is_duplicate"] = True
            result["warnings"].append("Potential duplicate invoice detected")
        else:
            _invoice_hashes.add(invoice_hash)

        # 4. Anomaly detection
        self._detect_anomalies(extracted_data, result)

        # 5. Vendor enrichment
        self._enrich_vendor(extracted_data, result)

        # Overall validity
        result["valid"] = len(result["validation_errors"]) == 0

        return result

    def _validate_schema(self, data: dict, result: dict):
        """Check required fields are present and valid."""
        required = ["invoice_number", "vendor_name", "total_amount"]
        for field in required:
            if not data.get(field):
                result["validation_errors"].append(f"Missing required field: {field}")

        # Validate amounts
        total = data.get("total_amount", 0)
        if isinstance(total, (int, float)) and total <= 0:
            result["validation_errors"].append("Total amount must be positive")

        # Validate line items
        items = data.get("line_items", [])
        if not items:
            result["warnings"].append("No line items found")
        else:
            for i, item in enumerate(items):
                qty = item.get("quantity", 0)
                price = item.get("unit_price", 0)
                if qty <= 0:
                    result["warnings"].append(f"Line item {i + 1}: quantity is zero or negative")
                if price <= 0:
                    result["warnings"].append(f"Line item {i + 1}: unit price is zero or negative")

        # Validate PO reference format
        po_ref = data.get("po_reference")
        if po_ref and not po_ref.startswith("PO-"):
            result["warnings"].append(f"PO reference '{po_ref}' has unusual format")

    def _classify_type(self, data: dict) -> str:
        """Classify invoice type based on content analysis."""
        total = data.get("total_amount", 0)
        invoice_num = (data.get("invoice_number") or "").lower()
        notes = (data.get("notes") or "").lower()

        if total < 0 or "credit" in invoice_num or "credit" in notes:
            return "CREDIT_NOTE"
        if "debit" in invoice_num or "debit" in notes:
            return "DEBIT_NOTE"
        if "pro forma" in invoice_num or "proforma" in notes or "pro-forma" in notes:
            return "PRO_FORMA"
        return "STANDARD"

    def _compute_hash(self, data: dict) -> str:
        """Hash key fields to detect duplicates."""
        key_string = f"{data.get('invoice_number', '')}|{data.get('vendor_name', '')}|{data.get('total_amount', 0)}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _detect_anomalies(self, data: dict, result: dict):
        """Flag pricing outliers and suspicious patterns."""
        total = data.get("total_amount", 0)

        # High-value invoice warning
        if isinstance(total, (int, float)) and total > 100000:
            result["warnings"].append(f"High-value invoice: ${total:,.2f} - requires additional review")

        # Check line item math
        items = data.get("line_items", [])
        calculated_subtotal = sum(
            item.get("total_price", 0) for item in items
        )
        declared_subtotal = data.get("subtotal", 0)
        if declared_subtotal and abs(calculated_subtotal - declared_subtotal) > 1.0:
            result["warnings"].append(
                f"Line items total (${calculated_subtotal:,.2f}) doesn't match declared subtotal (${declared_subtotal:,.2f})"
            )

        # Check individual item math
        for i, item in enumerate(items):
            expected = round(item.get("quantity", 0) * item.get("unit_price", 0), 2)
            actual = item.get("total_price", 0)
            if abs(expected - actual) > 0.5:
                result["warnings"].append(
                    f"Line item {i + 1}: qty × price = ${expected:,.2f}, declared = ${actual:,.2f}"
                )

    def _enrich_vendor(self, data: dict, result: dict):
        """Look up vendor in known database and enrich data."""
        vendor_name = data.get("vendor_name", "")
        matched_vendor = None

        # Try exact vendor_id match
        vendor_id = data.get("vendor_id")
        if vendor_id and vendor_id in KNOWN_VENDORS:
            matched_vendor = (vendor_id, KNOWN_VENDORS[vendor_id])
        else:
            # Fuzzy name match
            for vid, vname in KNOWN_VENDORS.items():
                if vendor_name.lower() in vname.lower() or vname.lower() in vendor_name.lower():
                    matched_vendor = (vid, vname)
                    break

        if matched_vendor:
            result["enriched_data"]["vendor_id"] = matched_vendor[0]
            result["enriched_data"]["vendor_name_verified"] = matched_vendor[1]
            result["enriched_data"]["vendor_known"] = True
        else:
            result["enriched_data"]["vendor_known"] = False
            result["warnings"].append(f"Vendor '{vendor_name}' not found in known vendor database")
