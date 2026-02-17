"""
Generate sample invoice PDFs for testing the pipeline.
Run: python -m app.generate_samples
"""

import os
import json


SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)


def create_sample_text_invoices():
    """Create simple text-based invoice files for testing with Llama extraction."""

    invoices = [
        {
            "filename": "invoice_acme_001.txt",
            "content": """
=============================================
              INVOICE
=============================================
Acme Industrial Supplies
123 Factory Lane, Detroit, MI 48201
Vendor ID: V-001
---------------------------------------------
Invoice Number: INV-2024-1001
Invoice Date: 2024-02-15
Due Date: 2024-03-15

Bill To: ProcureAI Corp
         456 Tech Blvd, San Francisco, CA

PO Reference: PO-2024-001
---------------------------------------------
ITEM CODE  | DESCRIPTION                      | QTY  | UNIT PRICE | TOTAL
-----------+----------------------------------+------+------------+--------
ACM-001    | Industrial Bearings (Box of 100) |   50 |    $125.00 |  $6,250.00
ACM-002    | Hydraulic Fluid (20L)            |   25 |    $180.00 |  $4,500.00
ACM-003    | Steel Bolts M12 (Pack of 500)    |  100 |     $50.00 |  $5,000.00
---------------------------------------------
                                    Subtotal:   $15,750.00
                                    Tax (9%):    $1,417.50
                                    TOTAL:      $17,167.50

Payment Terms: Net 30
Thank you for your business!
"""
        },
        {
            "filename": "invoice_techvision_002.txt",
            "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TechVision Electronics
  789 Silicon Ave, San Jose, CA 95134
  Vendor ID: V-002
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INVOICE #: INV-2024-2002
Date: 2024-02-20
Due: 2024-03-20

Customer: ProcureAI Corp
PO Number: PO-2024-002

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Items:
1. TV-101  LCD Monitor 27-inch         x40  @$350.00  = $14,000.00
2. TV-102  Wireless Keyboard & Mouse   x80  @$55.00   = $4,400.00
3. TV-103  USB-C Docking Station       x40  @$350.00  = $14,000.00

                              Subtotal: $32,400.00
                              Sales Tax: $2,916.00
                              TOTAL DUE: $35,316.00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Terms: Net 30
"""
        },
        {
            "filename": "invoice_greenleaf_003.txt",
            "content": """
+------------------------------------------+
|        GreenLeaf Office Products          |
|      55 Eco Drive, Portland, OR 97201    |
|           Vendor ID: V-003                |
+------------------------------------------+

INVOICE
Number: INV-2024-3003
Date:   2024-02-25
Due:    2024-03-25

TO: ProcureAI Corp
REF: PO-2024-003

Description              Code     Qty   Price     Amount
---------------------------------------------------------
A4 Copy Paper (5000)     GL-201   100   $28.50   $2,850.00
Printer Toner Cartridge  GL-202    20   $75.00   $1,500.00
Desk Organizer Set       GL-203    10   $50.00     $500.00
---------------------------------------------------------
                              Subtotal: $4,850.00
                              Tax 9%:     $436.50
                              TOTAL:    $5,286.50

Payment: Net 30 days
"""
        },
        {
            "filename": "invoice_safeguard_004.txt",
            "content": """
╔═══════════════════════════════════════╗
║   SafeGuard PPE Co.                   ║
║   321 Safety Rd, Houston, TX 77001    ║
║   Vendor ID: V-004                    ║
╚═══════════════════════════════════════╝

INVOICE NUMBER: INV-2024-4004
DATE ISSUED:    2024-03-01
DATE DUE:       2024-03-31

BILL TO: ProcureAI Corp
PURCHASE ORDER: PO-2024-004

ITEMS ORDERED:
─────────────────────────────────────────
SG-301  Safety Helmet (OSHA Approved)
        Qty: 100 × $35.00 = $3,500.00

SG-302  Hi-Vis Safety Vest
        Qty: 200 × $12.00 = $2,400.00

SG-303  Steel-Toe Boots (Assorted)
        Qty: 50 × $60.00 = $3,000.00
─────────────────────────────────────────
SUBTOTAL:       $8,900.00
TAX (9%):         $801.00
AMOUNT DUE:     $9,701.00

Terms: Net 30
"""
        },
        {
            "filename": "invoice_cleanpro_005.txt",
            "content": """
-------------------------------------------
     CleanPro Janitorial Supplies
     88 Clean Street, Chicago, IL 60601
     Vendor: V-005
-------------------------------------------

Invoice: INV-2024-5005
Issued: 2024-03-05
Due: 2024-04-05

To: ProcureAI Corp
PO#: PO-2024-005

Qty  Code    Description                   Unit$    Total
---  ------  ----------------------------  -------  --------
50   CP-401  Industrial Floor Cleaner 5L   $22.00   $1,100.00
30   CP-402  Microfiber Mop Heads (10pk)   $35.00   $1,050.00
100  CP-403  Disinfectant Spray 500ml      $10.50   $1,050.00

                                 Subtotal: $3,200.00
                                 Tax (9%):   $288.00
                                 TOTAL:    $3,488.00

Payment Terms: Net 30
-------------------------------------------
"""
        },
        # === Invoices with deliberate discrepancies for testing ===
        {
            "filename": "invoice_acme_006_price_mismatch.txt",
            "content": """
=============================================
              INVOICE
=============================================
Acme Industrial Supplies
123 Factory Lane, Detroit, MI 48201
Vendor ID: V-001
---------------------------------------------
Invoice Number: INV-2024-1006
Invoice Date: 2024-03-14
Due Date: 2024-04-14

Bill To: ProcureAI Corp
PO Reference: PO-2024-008
---------------------------------------------
ITEM CODE  | DESCRIPTION                      | QTY  | UNIT PRICE | TOTAL
-----------+----------------------------------+------+------------+--------
ACM-004    | Pneumatic Air Hose 50ft          |   30 |     $72.00 |  $2,160.00
ACM-005    | Conveyor Belt Segment 10ft       |   10 |    $480.00 |  $4,800.00
ACM-001    | Industrial Bearings (Box of 100) |   20 |    $130.00 |  $2,600.00
ACM-006    | Lubricant Grease (5kg)           |   10 |     $90.00 |    $900.00
---------------------------------------------
                                    Subtotal:   $10,460.00
                                    Tax (9%):      $941.40
                                    TOTAL:      $11,401.40

NOTE: Prices adjusted due to raw material cost increase.
"""
        },
        {
            "filename": "invoice_metalworks_007_qty_mismatch.txt",
            "content": """
MetalWorks Fabrication
42 Forge Blvd, Pittsburgh, PA 15201
Vendor ID: V-006

INVOICE #INV-2024-6007
Date: 2024-03-10
Due: 2024-04-10

Ship To: ProcureAI Corp
PO Ref: PO-2024-006

Items:
  MW-501  Custom Steel Brackets (Set of 4)   220 x $85.00  = $18,700.00
  MW-502  Aluminum Sheet 4x8ft               105 x $120.00 = $12,600.00
  MW-503  Welding Rods (50kg Box)              40 x $400.00 = $16,000.00

                                    Subtotal: $47,300.00
                                        Tax:   $4,257.00
                                      TOTAL:  $51,557.00
"""
        },
        {
            "filename": "invoice_unknown_008_no_po.txt",
            "content": """
Global Supplies Inc.
999 International Dr, Miami, FL 33101

INVOICE: INV-2024-9008
Date: 2024-03-20
Due: 2024-04-20

To: ProcureAI Corp

Items:
1. GS-001  Premium Widget Assembly    50 x $120.00 = $6,000.00
2. GS-002  Standard Connector Pack    200 x $15.00 = $3,000.00
3. GS-003  Calibration Tool Kit       10 x $500.00 = $5,000.00

                            Subtotal: $14,000.00
                            Tax (8%):  $1,120.00
                            TOTAL:    $15,120.00
"""
        },
        {
            "filename": "invoice_techvision_009_partial.txt",
            "content": """
TechVision Electronics
789 Silicon Ave, San Jose, CA 95134

Invoice Number: INV-2024-2009
Date: 2024-03-18
Payment Due: 2024-04-18

Bill To: ProcureAI Corp
Purchase Order: PO-2024-009

Item     Description                Qty    Price      Total
------   -------------------------  ----   --------   ---------
TV-104   Server Rack 42U              5   $2,500.00  $12,500.00
TV-105   CAT6 Ethernet Cable 100ft   80   $25.00      $2,000.00
TV-106   Network Switch 48-Port       5   $700.00     $3,500.00

                                   Subtotal: $18,000.00
                                   Tax:       $1,620.00
                                   TOTAL:    $19,620.00

Note: 20 CAT6 cables backordered - will ship separately
"""
        },
        {
            "filename": "invoice_credit_010.txt",
            "content": """
GreenLeaf Office Products
55 Eco Drive, Portland, OR 97201
Vendor ID: V-003

        CREDIT NOTE

Credit Note Number: CN-2024-3010
Original Invoice: INV-2024-3003
Date: 2024-03-10

To: ProcureAI Corp
PO Reference: PO-2024-003

Return Credit:
GL-203  Desk Organizer Set (Defective)  -5 x $50.00 = -$250.00

                        Credit Subtotal: -$250.00
                        Tax Adjustment:   -$22.50
                        TOTAL CREDIT:    -$272.50
"""
        },
    ]

    for inv in invoices:
        filepath = os.path.join(SAMPLES_DIR, inv["filename"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(inv["content"])
        print(f"Created: {filepath}")

    print(f"\nCreated {len(invoices)} sample invoices in {SAMPLES_DIR}")
    return [os.path.join(SAMPLES_DIR, inv["filename"]) for inv in invoices]


if __name__ == "__main__":
    create_sample_text_invoices()
