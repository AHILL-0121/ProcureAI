"""
Mock ERP data: 50 Purchase Orders and corresponding Goods Receipts.
Used as the simulated ERP backend for the MVP.
"""

MOCK_PURCHASE_ORDERS = [
    {
        "po_number": "PO-2024-001",
        "vendor_name": "Acme Industrial Supplies",
        "vendor_id": "V-001",
        "order_date": "2024-01-15",
        "expected_delivery": "2024-02-15",
        "total_amount": 15750.00,
        "tax_amount": 1417.50,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "ACM-001", "description": "Industrial Bearings (Box of 100)", "quantity": 50, "unit_price": 125.00, "total_price": 6250.00},
            {"item_code": "ACM-002", "description": "Hydraulic Fluid (20L)", "quantity": 25, "unit_price": 180.00, "total_price": 4500.00},
            {"item_code": "ACM-003", "description": "Steel Bolts M12 (Pack of 500)", "quantity": 100, "unit_price": 50.00, "total_price": 5000.00}
        ]
    },
    {
        "po_number": "PO-2024-002",
        "vendor_name": "TechVision Electronics",
        "vendor_id": "V-002",
        "order_date": "2024-01-20",
        "expected_delivery": "2024-02-20",
        "total_amount": 32400.00,
        "tax_amount": 2916.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "TV-101", "description": "LCD Monitor 27-inch", "quantity": 40, "unit_price": 350.00, "total_price": 14000.00},
            {"item_code": "TV-102", "description": "Wireless Keyboard & Mouse Combo", "quantity": 80, "unit_price": 55.00, "total_price": 4400.00},
            {"item_code": "TV-103", "description": "USB-C Docking Station", "quantity": 40, "unit_price": 350.00, "total_price": 14000.00}
        ]
    },
    {
        "po_number": "PO-2024-003",
        "vendor_name": "GreenLeaf Office Products",
        "vendor_id": "V-003",
        "order_date": "2024-01-25",
        "expected_delivery": "2024-02-25",
        "total_amount": 4850.00,
        "tax_amount": 436.50,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "GL-201", "description": "A4 Copy Paper (Box of 5000)", "quantity": 100, "unit_price": 28.50, "total_price": 2850.00},
            {"item_code": "GL-202", "description": "Printer Toner Cartridge", "quantity": 20, "unit_price": 75.00, "total_price": 1500.00},
            {"item_code": "GL-203", "description": "Desk Organizer Set", "quantity": 10, "unit_price": 50.00, "total_price": 500.00}
        ]
    },
    {
        "po_number": "PO-2024-004",
        "vendor_name": "SafeGuard PPE Co.",
        "vendor_id": "V-004",
        "order_date": "2024-02-01",
        "expected_delivery": "2024-03-01",
        "total_amount": 8900.00,
        "tax_amount": 801.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "SG-301", "description": "Safety Helmet (OSHA Approved)", "quantity": 100, "unit_price": 35.00, "total_price": 3500.00},
            {"item_code": "SG-302", "description": "Hi-Vis Safety Vest", "quantity": 200, "unit_price": 12.00, "total_price": 2400.00},
            {"item_code": "SG-303", "description": "Steel-Toe Boots (Assorted Sizes)", "quantity": 50, "unit_price": 60.00, "total_price": 3000.00}
        ]
    },
    {
        "po_number": "PO-2024-005",
        "vendor_name": "CleanPro Janitorial",
        "vendor_id": "V-005",
        "order_date": "2024-02-05",
        "expected_delivery": "2024-03-05",
        "total_amount": 3200.00,
        "tax_amount": 288.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "CP-401", "description": "Industrial Floor Cleaner (5L)", "quantity": 50, "unit_price": 22.00, "total_price": 1100.00},
            {"item_code": "CP-402", "description": "Microfiber Mop Heads (Pack of 10)", "quantity": 30, "unit_price": 35.00, "total_price": 1050.00},
            {"item_code": "CP-403", "description": "Disinfectant Spray (500ml)", "quantity": 100, "unit_price": 10.50, "total_price": 1050.00}
        ]
    },
    {
        "po_number": "PO-2024-006",
        "vendor_name": "MetalWorks Fabrication",
        "vendor_id": "V-006",
        "order_date": "2024-02-10",
        "expected_delivery": "2024-03-10",
        "total_amount": 45000.00,
        "tax_amount": 4050.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "MW-501", "description": "Custom Steel Brackets (Set of 4)", "quantity": 200, "unit_price": 85.00, "total_price": 17000.00},
            {"item_code": "MW-502", "description": "Aluminum Sheet 4x8ft", "quantity": 100, "unit_price": 120.00, "total_price": 12000.00},
            {"item_code": "MW-503", "description": "Welding Rods (50kg Box)", "quantity": 40, "unit_price": 400.00, "total_price": 16000.00}
        ]
    },
    {
        "po_number": "PO-2024-007",
        "vendor_name": "PowerDrive Electric",
        "vendor_id": "V-007",
        "order_date": "2024-02-12",
        "expected_delivery": "2024-03-12",
        "total_amount": 22600.00,
        "tax_amount": 2034.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "PD-601", "description": "Industrial Motor 5HP", "quantity": 10, "unit_price": 1200.00, "total_price": 12000.00},
            {"item_code": "PD-602", "description": "Circuit Breaker Panel", "quantity": 20, "unit_price": 280.00, "total_price": 5600.00},
            {"item_code": "PD-603", "description": "Copper Wire 12AWG (500ft)", "quantity": 10, "unit_price": 500.00, "total_price": 5000.00}
        ]
    },
    {
        "po_number": "PO-2024-008",
        "vendor_name": "Acme Industrial Supplies",
        "vendor_id": "V-001",
        "order_date": "2024-02-14",
        "expected_delivery": "2024-03-14",
        "total_amount": 9800.00,
        "tax_amount": 882.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "ACM-004", "description": "Pneumatic Air Hose 50ft", "quantity": 30, "unit_price": 65.00, "total_price": 1950.00},
            {"item_code": "ACM-005", "description": "Conveyor Belt Segment 10ft", "quantity": 10, "unit_price": 450.00, "total_price": 4500.00},
            {"item_code": "ACM-001", "description": "Industrial Bearings (Box of 100)", "quantity": 20, "unit_price": 125.00, "total_price": 2500.00},
            {"item_code": "ACM-006", "description": "Lubricant Grease (5kg)", "quantity": 10, "unit_price": 85.00, "total_price": 850.00}
        ]
    },
    {
        "po_number": "PO-2024-009",
        "vendor_name": "TechVision Electronics",
        "vendor_id": "V-002",
        "order_date": "2024-02-18",
        "expected_delivery": "2024-03-18",
        "total_amount": 18500.00,
        "tax_amount": 1665.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "TV-104", "description": "Server Rack 42U", "quantity": 5, "unit_price": 2500.00, "total_price": 12500.00},
            {"item_code": "TV-105", "description": "CAT6 Ethernet Cable 100ft", "quantity": 100, "unit_price": 25.00, "total_price": 2500.00},
            {"item_code": "TV-106", "description": "Network Switch 48-Port", "quantity": 5, "unit_price": 700.00, "total_price": 3500.00}
        ]
    },
    {
        "po_number": "PO-2024-010",
        "vendor_name": "BuildRight Construction",
        "vendor_id": "V-008",
        "order_date": "2024-02-20",
        "expected_delivery": "2024-03-20",
        "total_amount": 67500.00,
        "tax_amount": 6075.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "BR-701", "description": "Portland Cement (50kg Bag)", "quantity": 500, "unit_price": 45.00, "total_price": 22500.00},
            {"item_code": "BR-702", "description": "Rebar #5 20ft", "quantity": 300, "unit_price": 80.00, "total_price": 24000.00},
            {"item_code": "BR-703", "description": "Plywood Sheet 4x8ft", "quantity": 200, "unit_price": 55.00, "total_price": 11000.00},
            {"item_code": "BR-704", "description": "Concrete Blocks (Pallet)", "quantity": 20, "unit_price": 500.00, "total_price": 10000.00}
        ]
    },
    # -- POs 11-20 --
    {
        "po_number": "PO-2024-011",
        "vendor_name": "FreshFlow HVAC",
        "vendor_id": "V-009",
        "order_date": "2024-02-22",
        "expected_delivery": "2024-03-22",
        "total_amount": 28000.00,
        "tax_amount": 2520.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "FF-801", "description": "Central AC Unit 5 Ton", "quantity": 4, "unit_price": 5000.00, "total_price": 20000.00},
            {"item_code": "FF-802", "description": "Air Duct Flexible 25ft", "quantity": 40, "unit_price": 200.00, "total_price": 8000.00}
        ]
    },
    {
        "po_number": "PO-2024-012",
        "vendor_name": "GreenLeaf Office Products",
        "vendor_id": "V-003",
        "order_date": "2024-02-25",
        "expected_delivery": "2024-03-25",
        "total_amount": 6750.00,
        "tax_amount": 607.50,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "GL-204", "description": "Ergonomic Office Chair", "quantity": 15, "unit_price": 350.00, "total_price": 5250.00},
            {"item_code": "GL-205", "description": "Standing Desk Converter", "quantity": 5, "unit_price": 300.00, "total_price": 1500.00}
        ]
    },
    {
        "po_number": "PO-2024-013",
        "vendor_name": "SafeGuard PPE Co.",
        "vendor_id": "V-004",
        "order_date": "2024-03-01",
        "expected_delivery": "2024-04-01",
        "total_amount": 5600.00,
        "tax_amount": 504.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "SG-304", "description": "Nitrile Gloves (Box of 100)", "quantity": 200, "unit_price": 12.00, "total_price": 2400.00},
            {"item_code": "SG-305", "description": "Safety Goggles", "quantity": 100, "unit_price": 18.00, "total_price": 1800.00},
            {"item_code": "SG-306", "description": "Ear Protection Muffs", "quantity": 70, "unit_price": 20.00, "total_price": 1400.00}
        ]
    },
    {
        "po_number": "PO-2024-014",
        "vendor_name": "AutoParts Direct",
        "vendor_id": "V-010",
        "order_date": "2024-03-03",
        "expected_delivery": "2024-04-03",
        "total_amount": 12400.00,
        "tax_amount": 1116.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "AP-901", "description": "Engine Oil 10W-40 (20L)", "quantity": 40, "unit_price": 85.00, "total_price": 3400.00},
            {"item_code": "AP-902", "description": "Air Filter Heavy Duty", "quantity": 60, "unit_price": 45.00, "total_price": 2700.00},
            {"item_code": "AP-903", "description": "Brake Pads (Set of 4)", "quantity": 50, "unit_price": 126.00, "total_price": 6300.00}
        ]
    },
    {
        "po_number": "PO-2024-015",
        "vendor_name": "CleanPro Janitorial",
        "vendor_id": "V-005",
        "order_date": "2024-03-05",
        "expected_delivery": "2024-04-05",
        "total_amount": 4100.00,
        "tax_amount": 369.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "CP-404", "description": "Heavy Duty Trash Bags (Roll of 50)", "quantity": 100, "unit_price": 18.00, "total_price": 1800.00},
            {"item_code": "CP-405", "description": "Hand Sanitizer Station", "quantity": 10, "unit_price": 120.00, "total_price": 1200.00},
            {"item_code": "CP-406", "description": "Paper Towel Rolls (Case of 12)", "quantity": 20, "unit_price": 55.00, "total_price": 1100.00}
        ]
    },
    {
        "po_number": "PO-2024-016",
        "vendor_name": "MetalWorks Fabrication",
        "vendor_id": "V-006",
        "order_date": "2024-03-07",
        "expected_delivery": "2024-04-07",
        "total_amount": 31000.00,
        "tax_amount": 2790.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "MW-504", "description": "Stainless Steel Pipe 6inch 10ft", "quantity": 50, "unit_price": 320.00, "total_price": 16000.00},
            {"item_code": "MW-505", "description": "Metal Cutting Blades (Pack of 10)", "quantity": 100, "unit_price": 150.00, "total_price": 15000.00}
        ]
    },
    {
        "po_number": "PO-2024-017",
        "vendor_name": "PowerDrive Electric",
        "vendor_id": "V-007",
        "order_date": "2024-03-10",
        "expected_delivery": "2024-04-10",
        "total_amount": 15800.00,
        "tax_amount": 1422.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "PD-604", "description": "LED High Bay Light 200W", "quantity": 50, "unit_price": 180.00, "total_price": 9000.00},
            {"item_code": "PD-605", "description": "Electrical Conduit EMT 10ft", "quantity": 200, "unit_price": 15.00, "total_price": 3000.00},
            {"item_code": "PD-606", "description": "Junction Box 4x4", "quantity": 100, "unit_price": 38.00, "total_price": 3800.00}
        ]
    },
    {
        "po_number": "PO-2024-018",
        "vendor_name": "BuildRight Construction",
        "vendor_id": "V-008",
        "order_date": "2024-03-12",
        "expected_delivery": "2024-04-12",
        "total_amount": 24000.00,
        "tax_amount": 2160.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "BR-705", "description": "Scaffolding Frame Set", "quantity": 20, "unit_price": 800.00, "total_price": 16000.00},
            {"item_code": "BR-706", "description": "Safety Netting 50ft Roll", "quantity": 10, "unit_price": 800.00, "total_price": 8000.00}
        ]
    },
    {
        "po_number": "PO-2024-019",
        "vendor_name": "FreshFlow HVAC",
        "vendor_id": "V-009",
        "order_date": "2024-03-15",
        "expected_delivery": "2024-04-15",
        "total_amount": 9600.00,
        "tax_amount": 864.00,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "FF-803", "description": "HEPA Air Filter 20x25", "quantity": 60, "unit_price": 80.00, "total_price": 4800.00},
            {"item_code": "FF-804", "description": "Thermostat Smart Wi-Fi", "quantity": 20, "unit_price": 240.00, "total_price": 4800.00}
        ]
    },
    {
        "po_number": "PO-2024-020",
        "vendor_name": "Acme Industrial Supplies",
        "vendor_id": "V-001",
        "order_date": "2024-03-18",
        "expected_delivery": "2024-04-18",
        "total_amount": 7250.00,
        "tax_amount": 652.50,
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": "ACM-007", "description": "Heavy Duty Chain (per meter)", "quantity": 100, "unit_price": 25.00, "total_price": 2500.00},
            {"item_code": "ACM-008", "description": "Industrial Padlock Set", "quantity": 50, "unit_price": 35.00, "total_price": 1750.00},
            {"item_code": "ACM-009", "description": "Wire Rope 3/8inch 100ft", "quantity": 10, "unit_price": 300.00, "total_price": 3000.00}
        ]
    },
] + [
    # -- POs 21-30 --
    {
        "po_number": f"PO-2024-{i:03d}",
        "vendor_name": ["TechVision Electronics", "GreenLeaf Office Products", "SafeGuard PPE Co.", "CleanPro Janitorial",
                        "MetalWorks Fabrication", "PowerDrive Electric", "BuildRight Construction", "FreshFlow HVAC",
                        "AutoParts Direct", "Acme Industrial Supplies"][(i - 21) % 10],
        "vendor_id": f"V-{((i - 21) % 10) + 1:03d}",
        "order_date": f"2024-03-{20 + (i - 21):02d}",
        "expected_delivery": f"2024-04-{20 + (i - 21):02d}",
        "total_amount": round(5000 + (i * 1234.56), 2),
        "tax_amount": round((5000 + (i * 1234.56)) * 0.09, 2),
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": f"ITEM-{i}01", "description": f"Standard Component Part {i}A", "quantity": 10 + i, "unit_price": round(100 + i * 15, 2), "total_price": round((10 + i) * (100 + i * 15), 2)},
            {"item_code": f"ITEM-{i}02", "description": f"Premium Assembly Unit {i}B", "quantity": 5 + i, "unit_price": round(200 + i * 20, 2), "total_price": round((5 + i) * (200 + i * 20), 2)}
        ]
    }
    for i in range(21, 31)
] + [
    # -- POs 31-40 --
    {
        "po_number": f"PO-2024-{i:03d}",
        "vendor_name": ["Acme Industrial Supplies", "TechVision Electronics", "MetalWorks Fabrication",
                        "PowerDrive Electric", "BuildRight Construction", "SafeGuard PPE Co.",
                        "GreenLeaf Office Products", "CleanPro Janitorial", "FreshFlow HVAC", "AutoParts Direct"][(i - 31) % 10],
        "vendor_id": f"V-{((i - 31) % 10) + 1:03d}",
        "order_date": f"2024-04-{(i - 30):02d}",
        "expected_delivery": f"2024-05-{(i - 30):02d}",
        "total_amount": round(8000 + (i * 987.65), 2),
        "tax_amount": round((8000 + (i * 987.65)) * 0.09, 2),
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": f"ITEM-{i}01", "description": f"Bulk Material Type {i}A", "quantity": 20 + i, "unit_price": round(50 + i * 8, 2), "total_price": round((20 + i) * (50 + i * 8), 2)},
            {"item_code": f"ITEM-{i}02", "description": f"Specialty Part {i}B", "quantity": 8 + (i % 5), "unit_price": round(300 + i * 12, 2), "total_price": round((8 + (i % 5)) * (300 + i * 12), 2)}
        ]
    }
    for i in range(31, 41)
] + [
    # -- POs 41-50 --
    {
        "po_number": f"PO-2024-{i:03d}",
        "vendor_name": ["MetalWorks Fabrication", "Acme Industrial Supplies", "TechVision Electronics",
                        "PowerDrive Electric", "FreshFlow HVAC", "BuildRight Construction",
                        "SafeGuard PPE Co.", "CleanPro Janitorial", "GreenLeaf Office Products", "AutoParts Direct"][(i - 41) % 10],
        "vendor_id": f"V-{((i - 41) % 10) + 1:03d}",
        "order_date": f"2024-04-{10 + (i - 41):02d}",
        "expected_delivery": f"2024-05-{10 + (i - 41):02d}",
        "total_amount": round(10000 + (i * 555.55), 2),
        "tax_amount": round((10000 + (i * 555.55)) * 0.09, 2),
        "currency": "USD",
        "status": "OPEN",
        "items": [
            {"item_code": f"ITEM-{i}01", "description": f"Industrial Supply {i}A", "quantity": 15, "unit_price": round(200 + i * 10, 2), "total_price": round(15 * (200 + i * 10), 2)},
            {"item_code": f"ITEM-{i}02", "description": f"Maintenance Kit {i}B", "quantity": 10, "unit_price": round(150 + i * 5, 2), "total_price": round(10 * (150 + i * 5), 2)}
        ]
    }
    for i in range(41, 51)
]

# Generate Goods Receipts for the first 30 POs (some match, some don't for demo)
MOCK_GOODS_RECEIPTS = [
    {
        "grn_number": f"GRN-2024-{i:03d}",
        "po_number": f"PO-2024-{i:03d}",
        "vendor_name": po["vendor_name"],
        "receipt_date": po["expected_delivery"],
        "received_by": "Warehouse Team A",
        "items": po["items"],  # Full receipt (quantities match PO)
        "status": "RECEIVED",
        "notes": "All items received in good condition"
    }
    for i, po in enumerate(MOCK_PURCHASE_ORDERS[:30], start=1)
] + [
    # POs 31-35: Partial receipts (quantity discrepancies for testing)
    {
        "grn_number": f"GRN-2024-{i:03d}",
        "po_number": f"PO-2024-{i:03d}",
        "vendor_name": MOCK_PURCHASE_ORDERS[i - 1]["vendor_name"],
        "receipt_date": MOCK_PURCHASE_ORDERS[i - 1]["expected_delivery"],
        "received_by": "Warehouse Team B",
        "items": [
            {**item, "quantity": max(1, item["quantity"] - 3), "total_price": round((item["quantity"] - 3) * item["unit_price"], 2)}
            for item in MOCK_PURCHASE_ORDERS[i - 1]["items"]
        ],
        "status": "PARTIAL",
        "notes": "Partial delivery received - some items short"
    }
    for i in range(31, 36)
]
# POs 36-50: No receipt yet (for NO_MATCH testing)


def get_purchase_order(po_number: str) -> dict | None:
    """Look up a PO by number."""
    for po in MOCK_PURCHASE_ORDERS:
        if po["po_number"] == po_number:
            return po
    return None


def get_goods_receipt(po_number: str) -> dict | None:
    """Look up a GRN by PO reference."""
    for grn in MOCK_GOODS_RECEIPTS:
        if grn["po_number"] == po_number:
            return grn
    return None


def search_purchase_orders(vendor_name: str = None, status: str = None) -> list[dict]:
    """Search POs with filters."""
    results = MOCK_PURCHASE_ORDERS
    if vendor_name:
        results = [po for po in results if vendor_name.lower() in po["vendor_name"].lower()]
    if status:
        results = [po for po in results if po["status"] == status]
    return results
