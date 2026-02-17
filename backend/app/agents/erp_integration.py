"""
Agent 4: ERP Integration Agent (MCP Layer)
Queries ERP data loaded from Oracle Migration Dataset CSVs.
Provides PO lookup, GRN lookup, and search capabilities.
"""

import logging
from typing import Optional

from app.erp_csv_loader import (
    get_purchase_order,
    get_goods_receipt,
    search_purchase_orders,
    get_erp_stats,
)

logger = logging.getLogger(__name__)


class ERPIntegrationAgent:
    """ERP integration agent backed by Oracle Migration Dataset (CSV)."""

    def __init__(self):
        self.cache: dict[str, dict] = {}

    def fetch_purchase_order(self, po_number: str) -> Optional[dict]:
        """Fetch PO details from ERP dataset."""
        cache_key = f"po:{po_number}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for {po_number}")
            return self.cache[cache_key]

        po = get_purchase_order(po_number)
        if po:
            self.cache[cache_key] = po
            logger.info(f"Fetched PO {po_number}: {po['vendor_name']}, ${po['total_amount']:,.2f}")
        else:
            logger.warning(f"PO {po_number} not found in ERP")

        return po

    def fetch_goods_receipt(self, po_number: str) -> Optional[dict]:
        """Fetch Goods Receipt Note for a PO."""
        cache_key = f"grn:{po_number}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        grn = get_goods_receipt(po_number)
        if grn:
            self.cache[cache_key] = grn
            logger.info(f"Fetched GRN for {po_number}: {grn['grn_number']}")
        else:
            logger.warning(f"No goods receipt found for PO {po_number}")

        return grn

    def search_pos(self, vendor_name: str = None, status: str = None) -> list[dict]:
        """Search purchase orders with filters."""
        return search_purchase_orders(vendor_name=vendor_name, status=status)

    def get_erp_stats(self) -> dict:
        """Get statistics about the ERP dataset."""
        stats = get_erp_stats()
        stats["cache_size"] = len(self.cache)
        return stats
