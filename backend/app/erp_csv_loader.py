"""
ERP Data Loader - Loads Oracle Migration Dataset CSVs into memory.
Provides lookup functions that return data in the same format
the matching agent expects (compatible with the old mock_erp_data API).

Dataset files (in data/erp/):
  vendors.csv      - 10 suppliers
  materials.csv    - 20 items with descriptions
  po_headers.csv   - 1000 purchase orders
  po_lines.csv     - 1983 PO line items
  goods_receipts.csv - 1388 goods receipt records
  invoices.csv     - 1189 ERP-side invoice records
"""

import csv
import logging
import os
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve path relative to this file -> backend/data/erp/
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "erp")


def _load_csv(filename: str) -> list[dict]:
    """Load a CSV file and return list of row dicts."""
    path = os.path.join(_DATA_DIR, filename)
    if not os.path.exists(path):
        logger.warning(f"ERP CSV not found: {path}")
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class ERPDataStore:
    """In-memory store of the Oracle Migration Dataset, indexed for fast lookup."""

    def __init__(self):
        self._loaded = False
        # Indexed data
        self.vendors: dict[str, dict] = {}           # SUPPLIER_ID -> vendor row
        self.materials: dict[str, dict] = {}          # ITEM_ID -> material row
        self.po_headers: dict[str, dict] = {}         # PO_NUMBER -> header row
        self.po_headers_by_id: dict[str, dict] = {}   # PO_HEADER_ID -> header row
        self.po_lines_by_header: dict[str, list] = defaultdict(list)  # PO_HEADER_ID -> [lines]
        self.po_lines_by_id: dict[str, dict] = {}     # PO_LINE_ID -> line row
        self.grn_by_po_line: dict[str, list] = defaultdict(list)      # PO_LINE_ID -> [GRNs]
        self.erp_invoices_by_po_line: dict[str, list] = defaultdict(list)  # PO_LINE_ID -> [inv rows]
        self._all_po_numbers: list[str] = []

        # Raw counts
        self.count_vendors = 0
        self.count_materials = 0
        self.count_po_headers = 0
        self.count_po_lines = 0
        self.count_grns = 0
        self.count_invoices = 0

    def load(self):
        """Load all CSV files and build indexes."""
        if self._loaded:
            return
        logger.info(f"Loading ERP dataset from {_DATA_DIR}")

        # Vendors
        for row in _load_csv("vendors.csv"):
            sid = row["SUPPLIER_ID"].split(".")[0] if "." in row["SUPPLIER_ID"] else row["SUPPLIER_ID"]
            row["_sid"] = sid
            self.vendors[sid] = row
        self.count_vendors = len(self.vendors)

        # Materials
        for row in _load_csv("materials.csv"):
            mid = row["ITEM_ID"].split(".")[0] if "." in row["ITEM_ID"] else row["ITEM_ID"]
            row["_mid"] = mid
            self.materials[mid] = row
        self.count_materials = len(self.materials)

        # PO headers
        for row in _load_csv("po_headers.csv"):
            hid = row["PO_HEADER_ID"].split(".")[0] if "." in row["PO_HEADER_ID"] else row["PO_HEADER_ID"]
            row["_hid"] = hid
            self.po_headers[row["PO_NUMBER"]] = row
            self.po_headers_by_id[hid] = row
        self.count_po_headers = len(self.po_headers)
        self._all_po_numbers = sorted(self.po_headers.keys())

        # PO lines
        raw_lines = _load_csv("po_lines.csv")
        for row in raw_lines:
            lid = row["PO_LINE_ID"].split(".")[0] if "." in row["PO_LINE_ID"] else row["PO_LINE_ID"]
            hid = row["PO_HEADER_ID"].split(".")[0] if "." in row["PO_HEADER_ID"] else row["PO_HEADER_ID"]
            iid = row["ITEM_ID"].split(".")[0] if "." in row["ITEM_ID"] else row["ITEM_ID"]
            row["_lid"] = lid
            row["_hid"] = hid
            row["_iid"] = iid
            self.po_lines_by_header[hid].append(row)
            self.po_lines_by_id[lid] = row
        self.count_po_lines = len(raw_lines)

        # Goods receipts
        raw_grns = _load_csv("goods_receipts.csv")
        for row in raw_grns:
            pol_id = row["PO_LINE_ID"].split(".")[0] if "." in row["PO_LINE_ID"] else row["PO_LINE_ID"]
            row["_pol_id"] = pol_id
            self.grn_by_po_line[pol_id].append(row)
        self.count_grns = len(raw_grns)

        # ERP invoices (dataset invoices - reference data)
        raw_inv = _load_csv("invoices.csv")
        for row in raw_inv:
            pol_id = row["PO_LINE_ID"].split(".")[0] if "." in row["PO_LINE_ID"] else row["PO_LINE_ID"]
            row["_pol_id"] = pol_id
            self.erp_invoices_by_po_line[pol_id].append(row)
        self.count_invoices = len(raw_inv)

        self._loaded = True
        logger.info(
            f"ERP dataset loaded: {self.count_vendors} vendors, "
            f"{self.count_po_headers} POs, {self.count_po_lines} PO lines, "
            f"{self.count_grns} GRNs, {self.count_invoices} invoices"
        )

    # ── Public query methods ──

    def get_purchase_order(self, po_number: str) -> Optional[dict]:
        """
        Look up a PO by its PO_NUMBER (e.g. 'PO-000042').
        Returns a dict in the format the matching agent expects:
          {po_number, vendor_name, vendor_id, order_date, total_amount, currency, status, items: [...]}
        """
        self.load()
        header = self.po_headers.get(po_number)
        if not header:
            return None

        hid = header["_hid"]
        sid = header.get("SUPPLIER_ID", "").split(".")[0]
        vendor = self.vendors.get(sid, {})

        lines = self.po_lines_by_header.get(hid, [])
        items = []
        total_amount = 0.0
        for ln in lines:
            qty = float(ln.get("QUANTITY", 0))
            price = float(ln.get("UNIT_PRICE", 0))
            line_total = qty * price
            total_amount += line_total

            iid = ln["_iid"]
            mat = self.materials.get(iid, {})

            items.append({
                "item_code": mat.get("ITEM_NUMBER", f"ITEM-{iid}"),
                "description": mat.get("DESCRIPTION", f"Item {iid}"),
                "quantity": qty,
                "unit_price": price,
                "total_price": round(line_total, 2),
                "uom": ln.get("UOM", ""),
                "delivery_date": ln.get("DELIVERY_DATE", ""),
                "_po_line_id": ln["_lid"],
            })

        return {
            "po_number": po_number,
            "vendor_name": vendor.get("SUPPLIER_NAME", f"Supplier {sid}"),
            "vendor_id": sid,
            "order_date": header.get("CREATION_DATE", ""),
            "expected_delivery": lines[0].get("DELIVERY_DATE", "") if lines else "",
            "total_amount": round(total_amount, 2),
            "tax_amount": 0.0,
            "currency": header.get("CURRENCY", "USD"),
            "status": "OPEN",
            "items": items,
        }

    def get_goods_receipt(self, po_number: str) -> Optional[dict]:
        """
        Look up goods receipts for a PO.
        Aggregates all GRN rows for lines belonging to this PO.
        Returns a dict like: {grn_number, po_number, received_date, items: [...]}
        """
        self.load()
        header = self.po_headers.get(po_number)
        if not header:
            return None

        hid = header["_hid"]
        lines = self.po_lines_by_header.get(hid, [])
        if not lines:
            return None

        grn_items = []
        latest_date = ""
        grn_ids = set()

        for ln in lines:
            lid = ln["_lid"]
            grns = self.grn_by_po_line.get(lid, [])
            for g in grns:
                iid = g.get("ITEM_ID", "").split(".")[0]
                mat = self.materials.get(iid, {})
                grn_items.append({
                    "item_code": mat.get("ITEM_NUMBER", f"ITEM-{iid}"),
                    "description": mat.get("DESCRIPTION", f"Item {iid}"),
                    "quantity": float(g.get("RECEIVED_QTY", 0)),
                    "uom": g.get("UOM", ""),
                    "condition": "GOOD",
                    "_po_line_id": lid,
                })
                gid = g.get("GR_ID", "").split(".")[0]
                grn_ids.add(gid)
                rd = g.get("RECEIPT_DATE", "")
                if rd > latest_date:
                    latest_date = rd

        if not grn_items:
            return None

        return {
            "grn_number": f"GRN-{min(grn_ids)}" if grn_ids else "GRN-?",
            "po_number": po_number,
            "received_date": latest_date,
            "receiver": "Warehouse",
            "items": grn_items,
        }

    def search_purchase_orders(
        self,
        vendor_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search POs by vendor name (partial match). Returns summary dicts."""
        self.load()
        results = []
        for po_num in self._all_po_numbers:
            if len(results) >= limit:
                break
            header = self.po_headers[po_num]
            sid = header.get("SUPPLIER_ID", "").split(".")[0]
            vendor = self.vendors.get(sid, {})
            vname = vendor.get("SUPPLIER_NAME", "")

            if vendor_name and vendor_name.lower() not in vname.lower():
                continue

            # Compute total from lines
            hid = header["_hid"]
            lines = self.po_lines_by_header.get(hid, [])
            total = sum(float(l.get("QUANTITY", 0)) * float(l.get("UNIT_PRICE", 0)) for l in lines)

            results.append({
                "po_number": po_num,
                "vendor_name": vname,
                "vendor_id": sid,
                "order_date": header.get("CREATION_DATE", ""),
                "total_amount": round(total, 2),
                "currency": header.get("CURRENCY", "USD"),
                "status": "OPEN",
                "line_count": len(lines),
            })

        return results

    def get_stats(self) -> dict:
        """Return summary statistics."""
        self.load()
        return {
            "total_purchase_orders": self.count_po_headers,
            "total_po_lines": self.count_po_lines,
            "total_goods_receipts": self.count_grns,
            "total_erp_invoices": self.count_invoices,
            "unique_vendors": self.count_vendors,
            "materials": self.count_materials,
        }


# Singleton instance
_store = ERPDataStore()


def get_purchase_order(po_number: str) -> Optional[dict]:
    return _store.get_purchase_order(po_number)


def get_goods_receipt(po_number: str) -> Optional[dict]:
    return _store.get_goods_receipt(po_number)


def search_purchase_orders(vendor_name: str = None, status: str = None) -> list[dict]:
    return _store.search_purchase_orders(vendor_name=vendor_name, status=status)


def get_erp_stats() -> dict:
    return _store.get_stats()
