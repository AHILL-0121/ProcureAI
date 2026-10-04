"""
Agent 6: Orchestrator — runs the pipeline for one invoice.

    Received → Read (OCR/LLM) → Check (validation, vendor, duplicates) → Look up (ERP) → Match

`run()` is synchronous and is executed in a worker thread by `app.services.jobs`, so the server's
event loop never blocks on OCR, the LLM or the database. Progress is pushed to WebSocket clients
through `realtime.manager.publish`, which is thread-safe.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Callable, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.classification import ClassificationAgent
from app.agents.erp_integration import ERPIntegrationAgent, grn_summary
from app.agents.matching import MatchingAgent, tolerance_dict
from app.agents.vision_ocr import ExtractionError, VisionOCRAgent
from app.config import settings
from app.database import SessionLocal
from app.extraction import ExtractedInvoice
from app.models import (
    AuditLog,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    InvoiceType,
    MatchResult,
)
from app.services.realtime import manager
from app.services.tolerances import get_tolerance

logger = logging.getLogger(__name__)

STEPS = ["received", "read", "check", "lookup", "match"]


def _now():
    return datetime.now(UTC)


class OrchestratorAgent:
    def __init__(self, vision: VisionOCRAgent | None = None, notify: Callable[[dict], None] | None = None):
        self.vision = vision or VisionOCRAgent()
        self.erp = ERPIntegrationAgent()
        self.classifier = ClassificationAgent(self.erp)
        self.matcher = MatchingAgent()
        self.notify = notify or manager.publish

    # ------------------------------------------------------------------ helpers
    def _emit(self, event: str, inv: Invoice, **data):
        try:
            self.notify({"event": event, "invoice_id": inv.id, "status": inv.status.value if inv.status else None,
                         "invoice_number": inv.invoice_number, "file": inv.original_filename, **data})
        except Exception as e:   # never let notifications break processing
            logger.debug("notify failed: %s", e)

    def _step(self, inv: Invoice, step: str, status: InvoiceStatus | None = None, **data):
        if status:
            inv.status = status
        self._emit("status_update", inv, step=step, step_index=STEPS.index(step), **data)

    @staticmethod
    def _audit(db: Session, inv_id: str, agent: str, action: str, details: dict | None = None, actor: str | None = None):
        db.add(AuditLog(invoice_id=inv_id, agent=agent, action=action, details=details or {}, actor=actor))

    # ------------------------------------------------------------------ pipeline
    def run(self, invoice_id: str) -> dict:
        db = SessionLocal()
        started = time.perf_counter()
        inv: Optional[Invoice] = None
        try:
            inv = db.get(Invoice, invoice_id)
            if not inv:
                return {"status": "MISSING"}
            self._step(inv, "received")

            # ---- Read
            inv.status = InvoiceStatus.EXTRACTING
            db.commit()
            self._step(inv, "read")
            if not inv.file_path:
                return self._fail(db, inv, "The invoice has no stored document", started)
            try:
                extracted, meta = asyncio.run(self.vision.extract_invoice_data(inv.file_path))
            except ExtractionError as e:
                return self._fail(db, inv, str(e), started, agent="vision_ocr")

            self._apply_extraction(inv, extracted, meta)
            inv.status = InvoiceStatus.EXTRACTED
            self._audit(db, inv.id, "vision_ocr", "EXTRACTION_COMPLETE", meta)
            db.commit()

            # ---- Check
            self._step(inv, "check", InvoiceStatus.VALIDATING)
            result = self._check_and_match(db, inv, extracted, started)
            return result
        except Exception as e:  # unexpected: record and surface a readable reason
            logger.exception("Pipeline error for invoice %s", invoice_id)
            db.rollback()
            if inv is not None:
                return self._fail(db, inv, f"Unexpected processing error: {e.__class__.__name__}", started)
            return {"status": "FAILED", "error": str(e)}
        finally:
            db.close()

    def rematch(self, invoice_id: str, actor: str | None = None) -> dict:
        """Re-run checks and matching from the invoice's current (possibly edited) fields."""
        db = SessionLocal()
        try:
            inv = db.get(Invoice, invoice_id)
            if not inv:
                return {"status": "MISSING"}
            extracted = self.current_fields(inv)
            self._audit(db, inv.id, "user" if actor else "orchestrator", "REMATCH_REQUESTED", {}, actor=actor)
            return self._check_and_match(db, inv, extracted, time.perf_counter(), rematch=True)
        finally:
            db.close()

    @staticmethod
    def current_fields(inv: Invoice) -> ExtractedInvoice:
        return ExtractedInvoice.model_validate({
            "invoice_number": inv.invoice_number, "invoice_date": inv.invoice_date, "due_date": inv.due_date,
            "vendor_name": inv.vendor_name, "vendor_tax_id": inv.vendor_tax_id, "po_reference": inv.po_reference,
            "currency": inv.currency, "subtotal": inv.subtotal, "tax_amount": inv.tax_amount,
            "total_amount": inv.total_amount,
            "notes": (inv.extracted_data or {}).get("notes"),
            "line_items": [{"item_code": li.item_code, "description": li.description, "quantity": li.quantity,
                            "unit_price": li.unit_price, "total_price": li.total_price, "uom": li.uom}
                           for li in inv.line_items],
        })

    def _apply_extraction(self, inv: Invoice, ex: ExtractedInvoice, meta: dict):
        inv.invoice_number = ex.invoice_number
        inv.vendor_name = ex.vendor_name
        inv.vendor_tax_id = ex.vendor_tax_id
        inv.invoice_date = ex.invoice_date
        inv.due_date = ex.due_date
        inv.subtotal = ex.subtotal
        inv.total_amount = ex.total_amount or 0.0
        inv.tax_amount = ex.tax_amount or 0.0
        inv.currency = ex.currency
        inv.po_reference = ex.po_reference
        inv.extracted_data = {**ex.to_json(), "_metadata": meta}
        inv.confidence_score = meta.get("confidence_score", 0.0)
        inv.line_items = [
            InvoiceLineItem(line_no=i, description=ln.description, quantity=ln.quantity or 0.0,
                            unit_price=ln.unit_price or 0.0, total_price=ln.total_price or 0.0,
                            item_code=ln.item_code, uom=ln.uom)
            for i, ln in enumerate(ex.line_items, start=1)
        ]

    def _check_and_match(self, db: Session, inv: Invoice, ex: ExtractedInvoice, started: float, rematch: bool = False) -> dict:
        validation = self.classifier.validate_and_classify(db, ex, inv.id)
        inv.invoice_type = InvoiceType(validation["invoice_type"])
        inv.vendor_id = validation["vendor"]["id"]
        inv.validation = {"errors": validation["errors"], "warnings": validation["warnings"],
                          "vendor_known": validation["vendor"]["known"]}
        self._audit(db, inv.id, "classification", "VALIDATION_COMPLETE",
                    {"valid": validation["valid"], "errors": validation["errors"], "warnings": validation["warnings"],
                     "vendor": validation["vendor"]})

        # Duplicate: store it, link it, never match it
        if validation["duplicate_of"]:
            inv.vendor_key = validation["vendor_key"]
            inv.status = InvoiceStatus.DUPLICATE
            inv.duplicate_of = validation["duplicate_of"]
            inv.match_result = MatchResult.NO_MATCH
            inv.discrepancies = [{"type": "DUPLICATE", "severity": "HIGH",
                                  "message": "This invoice number was already received from this vendor",
                                  "duplicate_of": validation["duplicate_of"]}]
            inv.processing_time = round(time.perf_counter() - started, 2)
            self._audit(db, inv.id, "classification", "DUPLICATE_DETECTED", {"duplicate_of": validation["duplicate_of"]})
            db.commit()
            self._emit("match_complete", inv, match_result="NO_MATCH", duplicate_of=inv.duplicate_of, step="match")
            return {"status": "DUPLICATE", "invoice_id": inv.id, "duplicate_of": inv.duplicate_of}

        inv.vendor_key = validation["vendor_key"]
        inv.status = InvoiceStatus.VALIDATED
        try:
            db.commit()
        except IntegrityError:   # a concurrent twin claimed the (vendor, number) slot first
            db.rollback()
            fresh = db.get(Invoice, inv.id)
            if fresh is None:
                return {"status": "MISSING"}
            inv = fresh
            inv.status = InvoiceStatus.DUPLICATE
            inv.match_result = MatchResult.NO_MATCH
            inv.discrepancies = [{"type": "DUPLICATE", "severity": "HIGH",
                                  "message": "This invoice number was already received from this vendor"}]
            db.commit()
            self._emit("match_complete", inv, match_result="NO_MATCH", step="match")
            return {"status": "DUPLICATE", "invoice_id": inv.id}

        # ---- Look up
        self._step(inv, "lookup", InvoiceStatus.MATCHING)
        po = self.erp.fetch_purchase_order(db, ex.po_reference) if ex.po_reference else None
        billed = self.erp.billed_quantities(db, [ln["po_line_id"] for ln in po["lines"]], inv.id) if po else {}
        tolerance = get_tolerance(db, (po or {}).get("vendor_id") or inv.vendor_id)

        # ---- Match
        self._step(inv, "match")
        payload = {**ex.model_dump(), "resolved_vendor_id": inv.vendor_id, "invoice_type": validation["invoice_type"]}
        result = self.matcher.perform_three_way_match(payload, po, billed, tolerance)

        # Validation errors block auto-approval
        discrepancies = list(result["discrepancies"])
        for err in validation["errors"]:
            discrepancies.insert(0, {"type": "VALIDATION_ERROR", "severity": "HIGH", "message": err})

        confidence = inv.confidence_score or 0.0
        if not rematch:
            confidence = min(1.0, confidence + (0.05 if po else 0) + (0.05 if validation["vendor"]["known"] else 0))
            inv.confidence_score = round(confidence, 2)

        match_result = result["match_result"]
        if validation["errors"]:
            match_result = "NO_MATCH"
        if match_result == "FULL_MATCH" and confidence < settings.review_confidence_threshold and not rematch:
            match_result = "PARTIAL_MATCH"
            discrepancies.append({"type": "LOW_CONFIDENCE", "severity": "MEDIUM",
                                  "message": f"Reading confidence is {confidence:.0%}; confirm the extracted fields"})

        for i, li in enumerate(inv.line_items):
            j = result["pairs"].get(i)
            li.matched_po_line_id = po["lines"][j]["po_line_id"] if (po and j is not None) else None

        inv.match_result = MatchResult(match_result)
        inv.match_score = result["score"]
        inv.match_checks = result["checks"]
        inv.discrepancies = discrepancies
        inv.match_snapshot = {
            "po": po, "grn": grn_summary(po) if po else None, "lines": result["lines"],
            "expected_net": result["expected_net"], "tolerance": tolerance_dict(tolerance), "billed_before": billed,
            "matched_at": _now().isoformat(),
        }
        if match_result == "FULL_MATCH":
            inv.status = InvoiceStatus.MATCHED
        elif result["awaiting_receipt"] and not validation["errors"]:
            inv.status = InvoiceStatus.ON_HOLD
        else:
            inv.status = InvoiceStatus.DISCREPANCY
        inv.error = None
        if not rematch:
            inv.processing_time = round(time.perf_counter() - started, 2)
        self._audit(db, inv.id, "matching", "MATCH_COMPLETE",
                    {"result": match_result, "score": result["score"], "summary": result["summary"],
                     "status": inv.status.value, "rematch": rematch})
        db.commit()
        self._emit("match_complete", inv, match_result=match_result, score=result["score"],
                   processing_time=inv.processing_time, step="match", step_index=4)
        return {"status": "SUCCESS", "invoice_id": inv.id, "match_result": match_result,
                "invoice_status": inv.status.value, "score": result["score"]}

    def _fail(self, db: Session, inv: Invoice, message: str, started: float, agent: str = "orchestrator") -> dict:
        try:
            inv = db.get(Invoice, inv.id) or inv
            inv.status = InvoiceStatus.FAILED
            inv.error = message
            inv.processing_time = round(time.perf_counter() - started, 2)
            self._audit(db, inv.id, agent, "PROCESSING_FAILED", {"error": message})
            db.commit()
        except Exception:
            db.rollback()
        self._emit("processing_error", inv, error=message)
        return {"status": "FAILED", "invoice_id": inv.id, "error": message}

    async def get_pipeline_health(self, db: Session) -> dict:
        return {
            "orchestrator": "healthy",
            "vision_ocr": await self.vision.health_check(),
            "erp": self.erp.get_erp_stats(db),
            "timestamp": _now().isoformat(),
        }
