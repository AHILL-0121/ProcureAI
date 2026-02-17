"""
Agent 6: Orchestrator Agent
Coordinates agent workflows, manages state, handles the full invoice processing pipeline.
"""

import logging
import time
from datetime import datetime
from typing import Optional, Callable

from sqlalchemy.orm import Session

from app.models import (
    Invoice, InvoiceLineItem, AuditLog,
    InvoiceStatus, MatchResult, InvoiceType,
    PurchaseOrder, GoodsReceipt
)
from app.agents.email_intake import EmailIntakeAgent
from app.agents.vision_ocr import VisionOCRAgent
from app.agents.classification import ClassificationAgent
from app.agents.erp_integration import ERPIntegrationAgent
from app.agents.matching import MatchingAgent
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Central coordinator for the multi-agent pipeline."""

    def __init__(self):
        self.email_agent = EmailIntakeAgent()
        self.vision_agent = VisionOCRAgent()
        self.classification_agent = ClassificationAgent()
        self.erp_agent = ERPIntegrationAgent()
        self.matching_agent = MatchingAgent()
        self._ws_callback: Optional[Callable] = None

    def set_ws_callback(self, callback: Callable):
        """Set WebSocket broadcast callback for real-time updates."""
        self._ws_callback = callback

    async def _notify(self, event: str, data: dict):
        """Send real-time notification via WebSocket."""
        if self._ws_callback:
            try:
                await self._ws_callback({"event": event, **data})
            except Exception as e:
                logger.error(f"WebSocket notification failed: {e}")

    def _log_audit(self, db: Session, invoice_id: str, agent: str, action: str, details: dict = None):
        """Create audit log entry."""
        log = AuditLog(
            invoice_id=invoice_id,
            agent=agent,
            action=action,
            details=details or {},
        )
        db.add(log)
        db.commit()

    async def process_invoice(self, file_path: str, source_email: str = "manual", db: Session = None) -> dict:
        """
        Full pipeline: Extract → Validate → Match → Store
        Returns processing result with match status.
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        pipeline_start = time.time()
        invoice_id = None

        try:
            # --- Step 1: Create invoice record ---
            invoice = Invoice(
                status=InvoiceStatus.RECEIVED,
                source_email=source_email,
                file_path=file_path,
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            invoice_id = invoice.id

            self._log_audit(db, invoice_id, "orchestrator", "PIPELINE_START", {"file": file_path})
            await self._notify("invoice_received", {"invoice_id": invoice_id, "file": file_path})

            # --- Step 2: Vision/OCR Extraction ---
            invoice.status = InvoiceStatus.EXTRACTING
            db.commit()
            await self._notify("status_update", {"invoice_id": invoice_id, "status": "EXTRACTING"})

            try:
                extracted = self.vision_agent.extract_invoice_data(file_path)
            except Exception as e:
                invoice.status = InvoiceStatus.FAILED
                db.commit()
                self._log_audit(db, invoice_id, "vision_ocr", "EXTRACTION_FAILED", {"error": str(e)})
                await self._notify("processing_error", {"invoice_id": invoice_id, "error": str(e)})
                return {"status": "FAILED", "error": str(e), "invoice_id": invoice_id}

            # Update invoice with extracted data
            invoice.invoice_number = extracted.get("invoice_number")
            invoice.vendor_name = extracted.get("vendor_name")
            invoice.vendor_id = extracted.get("vendor_id")
            invoice.invoice_date = extracted.get("invoice_date")
            invoice.due_date = extracted.get("due_date")
            invoice.total_amount = extracted.get("total_amount", 0)
            invoice.tax_amount = extracted.get("tax_amount", 0)
            invoice.currency = extracted.get("currency", "USD")
            invoice.po_reference = extracted.get("po_reference")
            invoice.extracted_data = extracted
            invoice.confidence_score = extracted.get("_metadata", {}).get("confidence_score", 0)
            invoice.status = InvoiceStatus.EXTRACTED
            db.commit()

            # Add line items
            for item_data in extracted.get("line_items", []):
                line_item = InvoiceLineItem(
                    invoice_id=invoice_id,
                    description=item_data.get("description", ""),
                    quantity=item_data.get("quantity", 0),
                    unit_price=item_data.get("unit_price", 0),
                    total_price=item_data.get("total_price", 0),
                    item_code=item_data.get("item_code"),
                )
                db.add(line_item)
            db.commit()

            self._log_audit(db, invoice_id, "vision_ocr", "EXTRACTION_COMPLETE", {
                "confidence": invoice.confidence_score,
                "fields_extracted": len([k for k, v in extracted.items() if v and k != "_metadata"])
            })
            await self._notify("status_update", {"invoice_id": invoice_id, "status": "EXTRACTED"})

            # --- Step 3: Classification & Validation ---
            invoice.status = InvoiceStatus.VALIDATING
            db.commit()

            validation = self.classification_agent.validate_and_classify(extracted)

            invoice.invoice_type = InvoiceType(validation.get("invoice_type", "STANDARD"))
            invoice.status = InvoiceStatus.VALIDATED
            db.commit()

            self._log_audit(db, invoice_id, "classification", "VALIDATION_COMPLETE", {
                "valid": validation["valid"],
                "type": validation["invoice_type"],
                "warnings": validation["warnings"],
            })
            await self._notify("status_update", {"invoice_id": invoice_id, "status": "VALIDATED"})

            if not validation["valid"]:
                invoice.status = InvoiceStatus.FAILED
                db.commit()
                return {
                    "status": "VALIDATION_FAILED",
                    "invoice_id": invoice_id,
                    "errors": validation["validation_errors"],
                }

            # --- Step 4: ERP Integration (fetch PO + GRN) ---
            invoice.status = InvoiceStatus.MATCHING
            db.commit()

            po_ref = extracted.get("po_reference")
            po_data = None
            grn_data = None

            if po_ref:
                po_data = self.erp_agent.fetch_purchase_order(po_ref)
                if po_data:
                    grn_data = self.erp_agent.fetch_goods_receipt(po_ref)

            # --- Step 5: Three-Way Matching ---
            match_result = self.matching_agent.perform_three_way_match(
                invoice_data=extracted,
                po_data=po_data,
                grn_data=grn_data,
            )

            invoice.match_result = MatchResult(match_result["match_result"])
            invoice.discrepancies = match_result.get("discrepancies")
            invoice.status = (
                InvoiceStatus.MATCHED if match_result["match_result"] == "FULL_MATCH"
                else InvoiceStatus.DISCREPANCY
            )
            invoice.processing_time = round(time.time() - pipeline_start, 2)
            db.commit()

            self._log_audit(db, invoice_id, "matching", "MATCH_COMPLETE", {
                "result": match_result["match_result"],
                "score": match_result["score"],
                "discrepancies": len(match_result.get("discrepancies", [])),
            })

            await self._notify("match_complete", {
                "invoice_id": invoice_id,
                "match_result": match_result["match_result"],
                "score": match_result["score"],
                "processing_time": invoice.processing_time,
            })

            return {
                "status": "SUCCESS",
                "invoice_id": invoice_id,
                "invoice_number": invoice.invoice_number,
                "vendor_name": invoice.vendor_name,
                "total_amount": invoice.total_amount,
                "po_reference": invoice.po_reference,
                "match_result": match_result["match_result"],
                "match_score": match_result["score"],
                "discrepancies": match_result.get("discrepancies", []),
                "processing_time": invoice.processing_time,
                "validation": validation,
            }

        except Exception as e:
            logger.exception(f"Pipeline error for invoice {invoice_id}: {e}")
            if invoice_id:
                try:
                    invoice_obj = db.query(Invoice).filter(Invoice.id == invoice_id).first()
                    if invoice_obj:
                        invoice_obj.status = InvoiceStatus.FAILED
                        db.commit()
                except:
                    pass
            return {"status": "FAILED", "error": str(e), "invoice_id": invoice_id}

        finally:
            if own_session:
                db.close()

    def get_pipeline_health(self) -> dict:
        """Check health of all agents."""
        return {
            "orchestrator": "healthy",
            "vision_ocr": self.vision_agent.health_check(),
            "erp": self.erp_agent.get_erp_stats(),
            "timestamp": datetime.utcnow().isoformat(),
        }
