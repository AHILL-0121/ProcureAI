"""
ProcureAI MVP - FastAPI Main Application
Multi-Agent AI System for Three-Way Match Automation
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database import get_db, init_db
from app.models import Invoice, InvoiceStatus, MatchResult, AuditLog
from app.schemas import (
    InvoiceResponse, InvoiceListResponse, ProcessingResult,
    DashboardStats, HealthResponse, PurchaseOrderResponse, MatchDetailResponse
)
from app.agents.orchestrator import OrchestratorAgent
from app.agents.email_intake import EmailIntakeAgent, polling_state
from app.agents.erp_integration import ERPIntegrationAgent
from app.agents.vision_ocr import VisionOCRAgent

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("procureai")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


ws_manager = ConnectionManager()
orchestrator = OrchestratorAgent()
_poll_task: asyncio.Task | None = None       # handle for the background polling loop


async def _email_polling_loop():
    """Background coroutine: continuously polls the IMAP inbox."""
    agent = EmailIntakeAgent()
    interval = settings.email_poll_interval
    polling_state["running"] = True
    logger.info(f"📬 Email polling loop started (every {interval}s)")

    while polling_state["running"]:
        try:
            results = await agent.poll_inbox_async()
            polling_state["total_polls"] += 1
            polling_state["last_poll"] = datetime.utcnow().isoformat()
            polling_state["last_error"] = None

            if results:
                polling_state["total_invoices_found"] += len(results)
                logger.info(f"📨 Email poll found {len(results)} new invoice attachment(s)")

                from app.database import SessionLocal
                for attachment in results:
                    db = SessionLocal()
                    try:
                        result = await orchestrator.process_invoice(
                            file_path=attachment["file_path"],
                            source_email=attachment["sender"],
                            db=db,
                        )
                        logger.info(
                            f"✅ Auto-processed email invoice: {attachment['filename']} → {result.get('status')}"
                        )
                    except Exception as proc_err:
                        logger.error(f"❌ Failed to process email invoice {attachment['filename']}: {proc_err}")
                    finally:
                        db.close()
            else:
                logger.debug("📭 Email poll: no new invoices")

        except asyncio.CancelledError:
            logger.info("📬 Email polling loop cancelled")
            break
        except Exception as e:
            polling_state["last_error"] = str(e)
            logger.error(f"📬 Email poll cycle error: {e}")

        await asyncio.sleep(interval)

    polling_state["running"] = False
    logger.info("📬 Email polling loop stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poll_task
    # Startup
    logger.info("🚀 ProcureAI starting up...")
    init_db()

    # Set WebSocket callback on orchestrator
    async def ws_broadcast(data):
        await ws_manager.broadcast(data)
    orchestrator.set_ws_callback(ws_broadcast)

    # ── IMAP connectivity check ──
    if settings.email_user and settings.email_password:
        try:
            import imaplib
            logger.info(f"📧 Checking IMAP connection to {settings.email_host}:{settings.email_port} ...")
            if settings.email_use_ssl:
                _mail = imaplib.IMAP4_SSL(settings.email_host, settings.email_port)
            else:
                _mail = imaplib.IMAP4(settings.email_host, settings.email_port)
            _status, _caps = _mail.login(settings.email_user, settings.email_password)
            _mail.select("INBOX")
            _mail.logout()
            logger.info(f"✅ IMAP check passed — logged in as {settings.email_user}")
        except Exception as imap_err:
            logger.error(f"❌ IMAP check FAILED: {imap_err}")
            logger.warning("   Email polling will be skipped until credentials are fixed.")
            # Mark polling as not startable so the loop doesn't keep failing
            settings.email_polling_enabled = False
    else:
        logger.warning("📧 IMAP check skipped — EMAIL_USER / EMAIL_PASSWORD not set in .env")

    # ── LLM connectivity check ──
    try:
        logger.info("🤖 Checking Groq API connection...")
        vision_agent = VisionOCRAgent()
        health_status = vision_agent.health_check()
        
        if health_status.get("groq_status") == "online" and health_status.get("model_available"):
            logger.info(f"✅ Groq API ready — text: {health_status.get('model')}, vision: {health_status.get('vision_model')}")
        else:
            logger.error("❌ Groq API check FAILED")
            logger.error(f"   Error: {health_status.get('error', 'Unknown error')}")
            logger.warning("   Invoice processing will fail until Groq API is configured")
    except Exception as llm_err:
        logger.error(f"❌ LLM initialization error: {llm_err}")

    # Start background email polling if credentials are configured
    if settings.email_polling_enabled and settings.email_user:
        _poll_task = asyncio.create_task(_email_polling_loop())
        logger.info("📬 Background email polling scheduled")
    else:
        logger.info("📬 Email polling disabled (no credentials or email_polling_enabled=False)")

    logger.info("✅ Database initialized, agents ready")
    yield
    # Shutdown — cancel polling gracefully
    if _poll_task and not _poll_task.done():
        polling_state["running"] = False
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
    logger.info("👋 ProcureAI shutting down")


app = FastAPI(
    title="ProcureAI",
    description="Multi-Agent AI System for Three-Way Match Automation - Powered by Local Llama 3.1",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────── Root Route ────────────

@app.get("/")
async def root():
    """Root endpoint - basic API info."""
    return {
        "name": "ProcureAI API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health"
    }


# ──────────── WebSocket ────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or handle client messages
            await websocket.send_json({"type": "ack", "message": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ──────────── Health ────────────

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Check system health including Ollama/Llama status."""
    health = orchestrator.get_pipeline_health()
    return HealthResponse(
        status="healthy",
        orchestrator=health["orchestrator"],
        vision_ocr=health["vision_ocr"],
        erp=health["erp"],
        timestamp=health["timestamp"],
    )


# ──────────── Invoice Upload & Processing ────────────

@app.post("/api/invoices/upload", response_model=ProcessingResult)
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload an invoice PDF/image and process through the full pipeline."""
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only PDF and image files are supported")

    # Save the uploaded file
    file_data = await file.read()
    intake = EmailIntakeAgent.save_uploaded_file(file.filename, file_data)

    # Process through orchestrator
    result = await orchestrator.process_invoice(
        file_path=intake["file_path"],
        source_email="upload",
        db=db,
    )

    return ProcessingResult(**result)


@app.post("/api/invoices/process-demo")
async def process_demo_invoices(db: Session = Depends(get_db)):
    """Process all sample invoices in the uploads/samples directory."""
    samples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "samples")
    if not os.path.exists(samples_dir):
        raise HTTPException(status_code=404, detail="No sample invoices found. Place PDFs in uploads/samples/")

    results = []
    for filename in sorted(os.listdir(samples_dir)):
        if filename.lower().endswith((".pdf", ".png", ".jpg", ".txt")):
            file_path = os.path.join(samples_dir, filename)
            result = await orchestrator.process_invoice(file_path=file_path, source_email="demo", db=db)
            results.append(result)

    return {"processed": len(results), "results": results}


# ──────────── Invoice List & Detail ────────────

@app.get("/api/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    match_result: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all invoices with pagination and filters."""
    query = db.query(Invoice)

    if status:
        query = query.filter(Invoice.status == status)
    if match_result:
        query = query.filter(Invoice.match_result == match_result)
    if search:
        query = query.filter(
            (Invoice.invoice_number.ilike(f"%{search}%")) |
            (Invoice.vendor_name.ilike(f"%{search}%")) |
            (Invoice.po_reference.ilike(f"%{search}%"))
        )

    total = query.count()
    invoices = query.order_by(Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return InvoiceListResponse(
        invoices=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Get invoice details by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceResponse.model_validate(invoice)


# ──────────── Matches ────────────

@app.get("/api/matches")
async def list_matches(
    result: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all invoice match results."""
    query = db.query(Invoice).filter(Invoice.match_result != MatchResult.PENDING)
    if result:
        query = query.filter(Invoice.match_result == result)

    invoices = query.order_by(Invoice.created_at.desc()).all()

    erp = ERPIntegrationAgent()
    matches = []
    for inv in invoices:
        po_data = erp.fetch_purchase_order(inv.po_reference) if inv.po_reference else None
        grn_data = erp.fetch_goods_receipt(inv.po_reference) if inv.po_reference else None
        matches.append(MatchDetailResponse(
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            vendor_name=inv.vendor_name,
            total_amount=inv.total_amount,
            po_reference=inv.po_reference,
            match_result=inv.match_result.value if inv.match_result else "PENDING",
            discrepancies=inv.discrepancies,
            po_data=po_data,
            grn_data=grn_data,
            invoice_file_path=inv.file_path,
        ))

    return {"matches": [m.model_dump() for m in matches], "total": len(matches)}


@app.get("/api/documents/invoice/{invoice_id}")
async def view_invoice_document(invoice_id: str, db: Session = Depends(get_db)):
    """Serve invoice document file for viewing."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if not invoice.file_path or not os.path.exists(invoice.file_path):
        raise HTTPException(status_code=404, detail="Invoice document file not found")
    
    return FileResponse(
        invoice.file_path,
        media_type="application/pdf" if invoice.file_path.endswith(".pdf") else "image/jpeg",
        filename=os.path.basename(invoice.file_path)
    )


# ──────────── Dashboard Stats ────────────

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregated dashboard statistics with a single optimized query."""
    # Single query to get all counts and aggregates
    from sqlalchemy import case
    
    stats = db.query(
        func.count(Invoice.id).label('total'),
        func.sum(case((Invoice.match_result == MatchResult.FULL_MATCH, 1), else_=0)).label('matched'),
        func.sum(case((Invoice.match_result == MatchResult.PARTIAL_MATCH, 1), else_=0)).label('partial'),
        func.sum(case((Invoice.match_result == MatchResult.NO_MATCH, 1), else_=0)).label('no_match'),
        func.sum(case((Invoice.match_result == MatchResult.PENDING, 1), else_=0)).label('pending'),
        func.sum(case((Invoice.status == InvoiceStatus.FAILED, 1), else_=0)).label('failed'),
        func.sum(Invoice.total_amount).label('total_value'),
        func.avg(Invoice.processing_time).label('avg_time'),
        func.avg(case((Invoice.confidence_score > 0, Invoice.confidence_score), else_=None)).label('avg_conf'),
    ).first()

    return DashboardStats(
        total_invoices=stats.total or 0,
        matched=stats.matched or 0,
        partial_match=stats.partial or 0,
        no_match=stats.no_match or 0,
        pending=stats.pending or 0,
        failed=stats.failed or 0,
        total_value=round(stats.total_value or 0.0, 2),
        avg_processing_time=round(stats.avg_time or 0.0, 2),
        avg_confidence=round(stats.avg_conf or 0.0, 2),
    )


# ──────────── Purchase Orders (ERP) ────────────

@app.get("/api/purchase-orders")
async def list_purchase_orders(
    vendor: Optional[str] = None,
    status: Optional[str] = None,
):
    """List purchase orders from mock ERP."""
    erp = ERPIntegrationAgent()
    pos = erp.search_pos(vendor_name=vendor, status=status)
    return {"purchase_orders": pos, "total": len(pos)}


@app.get("/api/purchase-orders/{po_number}")
async def get_purchase_order(po_number: str):
    """Get PO details by number."""
    erp = ERPIntegrationAgent()
    po = erp.fetch_purchase_order(po_number)
    if not po:
        raise HTTPException(status_code=404, detail=f"PO {po_number} not found")
    grn = erp.fetch_goods_receipt(po_number)
    return {"purchase_order": po, "goods_receipt": grn}


# ──────────── Email Polling ────────────

@app.get("/api/email/poll-status")
async def email_poll_status():
    """Return current email polling state."""
    return {
        "running": polling_state["running"],
        "last_poll": polling_state["last_poll"],
        "last_error": polling_state["last_error"],
        "total_polls": polling_state["total_polls"],
        "total_invoices_found": polling_state["total_invoices_found"],
        "interval_seconds": settings.email_poll_interval,
        "email_user": settings.email_user or "(not configured)",
    }


@app.post("/api/email/poll-now")
async def email_poll_now(db: Session = Depends(get_db)):
    """Trigger a one-off inbox poll immediately (regardless of background loop)."""
    agent = EmailIntakeAgent()
    results = await agent.poll_inbox_async()
    processed = []
    for attachment in results:
        try:
            result = await orchestrator.process_invoice(
                file_path=attachment["file_path"],
                source_email=attachment["sender"],
                db=db,
            )
            processed.append({
                "filename": attachment["filename"],
                "sender": attachment["sender"],
                "status": result.get("status"),
            })
        except Exception as e:
            processed.append({
                "filename": attachment["filename"],
                "sender": attachment["sender"],
                "error": str(e),
            })
    return {"found": len(results), "processed": processed}


@app.post("/api/email/poll-start")
async def email_poll_start():
    """Start the background polling loop (if not already running)."""
    global _poll_task
    if polling_state["running"]:
        return {"message": "Polling is already running"}
    if not settings.email_user:
        raise HTTPException(status_code=400, detail="Email credentials not configured")
    _poll_task = asyncio.create_task(_email_polling_loop())
    return {"message": f"Polling started (every {settings.email_poll_interval}s)"}


@app.post("/api/email/poll-stop")
async def email_poll_stop():
    """Stop the background polling loop."""
    global _poll_task
    if not polling_state["running"]:
        return {"message": "Polling is not running"}
    polling_state["running"] = False
    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
    return {"message": "Polling stopped"}


# ──────────── Audit Logs ────────────

@app.get("/api/audit-logs")
async def list_audit_logs(
    invoice_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List audit logs."""
    query = db.query(AuditLog)
    if invoice_id:
        query = query.filter(AuditLog.invoice_id == invoice_id)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return {
        "logs": [
            {
                "id": log.id,
                "invoice_id": log.invoice_id,
                "agent": log.agent,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
