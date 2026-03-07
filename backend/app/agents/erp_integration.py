"""
Agent 4: ERP Integration Agent
Queries ERP data from PostgreSQL database (Oracle Migration Dataset).
Provides PO lookup, GRN lookup, and search capabilities.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal
from app.models import Vendor, Material, POHeader, POLine, GoodsReceiptERP

logger = logging.getLogger(__name__)


class ERPIntegrationAgent:
    """ERP integration agent backed by PostgreSQL database."""

    def __init__(self):
        self.cache: dict[str, dict] = {}

    def _get_db(self) -> Session:
        """Get database session"""
        return SessionLocal()

    def fetch_purchase_order(self, po_number: str) -> Optional[dict]:
        """Fetch PO details from PostgreSQL database."""
        cache_key = f"po:{po_number}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for {po_number}")
            return self.cache[cache_key]

        db = self._get_db()
        try:
            # Query PO header with lines
            po_header = db.query(POHeader).filter(
                POHeader.po_number == po_number
            ).options(joinedload(POHeader.lines)).first()

            if not po_header:
                logger.warning(f"PO {po_number} not found in database")
                return None

            # Get vendor info
            vendor = db.query(Vendor).filter(
                Vendor.supplier_id == po_header.supplier_id
            ).first()

            # Build items list from PO lines
            items = []
            total_amount = 0.0

            for line in po_header.lines:
                # Get material info
                material = db.query(Material).filter(
                    Material.item_id == line.item_id
                ).first()

                line_total = line.quantity * line.unit_price
                total_amount += line_total

                items.append({
                    "item_code": material.item_id if material else line.item_id,
                    "description": material.description if material else f"Item {line.item_id}",
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "total_price": round(line_total, 2),
                    "uom": material.uom if material else "EA",
                    "_po_line_id": line.po_line_id,
                })

            result = {
                "po_number": po_number,
                "vendor_name": vendor.supplier_name if vendor else f"Supplier {po_header.supplier_id}",
                "vendor_id": po_header.supplier_id,
                "order_date": po_header.creation_date,
                "expected_delivery": "",
                "total_amount": round(total_amount, 2),
                "tax_amount": 0.0,
                "currency": po_header.currency,
                "status": po_header.status,
                "items": items,
            }

            self.cache[cache_key] = result
            logger.info(f"Fetched PO {po_number} from database: {result['vendor_name']}, ${result['total_amount']:,.2f}")
            return result

        finally:
            db.close()

    def fetch_goods_receipt(self, po_number: str) -> Optional[dict]:
        """Fetch Goods Receipt Note for a PO from database."""
        cache_key = f"grn:{po_number}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        db = self._get_db()
        try:
            # Get PO header to find lines
            po_header = db.query(POHeader).filter(
                POHeader.po_number == po_number
            ).options(joinedload(POHeader.lines)).first()

            if not po_header or not po_header.lines:
                logger.warning(f"No PO or lines found for {po_number}")
                return None

            # Get all GRNs for this PO's lines
            po_line_ids = [line.po_line_id for line in po_header.lines]
            grns = db.query(GoodsReceiptERP).filter(
                GoodsReceiptERP.po_line_id.in_(po_line_ids)
            ).all()

            if not grns:
                logger.warning(f"No goods receipt found for PO {po_number}")
                return None

            # Build items list from GRNs
            grn_items = []
            latest_date = ""
            grn_ids = set()

            for grn in grns:
                # Get the corresponding PO line
                po_line = db.query(POLine).filter(
                    POLine.po_line_id == grn.po_line_id
                ).first()

                if po_line:
                    # Get material info
                    material = db.query(Material).filter(
                        Material.item_id == po_line.item_id
                    ).first()

                    grn_items.append({
                        "item_code": material.item_id if material else po_line.item_id,
                        "description": material.description if material else f"Item {po_line.item_id}",
                        "quantity": grn.quantity_received,
                        "uom": material.uom if material else "EA",
                        "condition": "GOOD",
                        "_po_line_id": grn.po_line_id,
                    })

                    grn_ids.add(grn.receipt_id)
                    if grn.receipt_date > latest_date:
                        latest_date = grn.receipt_date

            if not grn_items:
                return None

            result = {
                "grn_number": f"GRN-{min(grn_ids)}" if grn_ids else "GRN-?",
                "po_number": po_number,
                "received_date": latest_date,
                "receiver": "Warehouse",
                "items": grn_items,
            }

            self.cache[cache_key] = result
            logger.info(f"Fetched GRN for {po_number} from database: {result['grn_number']}")
            return result

        finally:
            db.close()

    def search_pos(self, vendor_name: str = None, status: str = None, limit: int = 50) -> list[dict]:
        """Search purchase orders with filters from database."""
        db = self._get_db()
        try:
            query = db.query(POHeader).options(joinedload(POHeader.lines))

            # Apply filters
            if status:
                query = query.filter(POHeader.status == status)

            if vendor_name:
                # Join with vendor and filter by name
                query = query.join(Vendor, POHeader.supplier_id == Vendor.supplier_id)
                query = query.filter(Vendor.supplier_name.ilike(f"%{vendor_name}%"))

            query = query.limit(limit)
            po_headers = query.all()

            results = []
            for po_header in po_headers:
                # Get vendor
                vendor = db.query(Vendor).filter(
                    Vendor.supplier_id == po_header.supplier_id
                ).first()

                # Calculate total from lines
                total = sum(line.line_amount for line in po_header.lines)

                results.append({
                    "po_number": po_header.po_number,
                    "vendor_name": vendor.supplier_name if vendor else f"Supplier {po_header.supplier_id}",
                    "vendor_id": po_header.supplier_id,
                    "order_date": po_header.creation_date,
                    "total_amount": round(total, 2),
                    "currency": po_header.currency,
                    "status": po_header.status,
                    "line_count": len(po_header.lines),
                })

            logger.info(f"Found {len(results)} POs matching filters")
            return results

        finally:
            db.close()

    def get_erp_stats(self) -> dict:
        """Get statistics about the ERP dataset from database (cached for 5 minutes)."""
        import time
        cache_key = "erp_stats"
        cache_duration = 300  # 5 minutes
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < cache_duration:
                return cached_data
        
        # Fetch fresh stats
        db = self._get_db()
        try:
            stats = {
                "total_vendors": db.query(Vendor).count(),
                "total_materials": db.query(Material).count(),
                "total_purchase_orders": db.query(POHeader).count(),
                "total_po_lines": db.query(POLine).count(),
                "total_goods_receipts": db.query(GoodsReceiptERP).count(),
                "unique_vendors": db.query(Vendor).count(),  # Simplified - same as total
                "cache_size": len(self.cache),
                "data_source": "PostgreSQL (Neon)"
            }
            # Cache the result
            self.cache[cache_key] = (stats, time.time())
            return stats
        finally:
            db.close()
