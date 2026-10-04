"""
ProcureAI API — multi-agent three-way invoice matching.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.agents.vision_ocr import VisionOCRAgent
from app.config import settings
from app.database import SessionLocal
from app.migrate import run as run_migrations
from app.routers import admin, auth, dashboard, erp, invoices
from app.security import bootstrap_admin, user_from_token
from app.services.email_poller import poller
from app.services.jobs import jobs
from app.services.realtime import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("procureai")


async def check_models():
    """Log whether the text and vision models actually answer, before the first invoice needs them."""
    result = await VisionOCRAgent().startup_check()
    for role, label in (("text", "text model  "), ("vision", "vision model")):
        r = result.get(role)
        if r is None:
            logger.info("LLM check | %s disabled (GROQ_VISION_MODEL is empty)", label)
            continue
        took = f" ({r['latency_ms']} ms)" if "latency_ms" in r else ""
        if not r["ok"]:
            logger.error("LLM check | %s %s: FAILED, %s%s", label, r["model"], r["detail"], took)
        elif r.get("warning"):
            logger.warning("LLM check | %s %s: %s%s", label, r["model"], r["detail"], took)
        else:
            logger.info("LLM check | %s %s: OK, %s%s", label, r["model"], r["detail"], took)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env != "test":
        # Bring the Neon schema to the latest version and load ERP data if missing (idempotent)
        await asyncio.to_thread(run_migrations)
    with SessionLocal() as db:
        bootstrap_admin(db)
    if settings.llm_startup_check and settings.app_env != "test":
        await check_models()
    manager.bind_loop(asyncio.get_running_loop())
    await jobs.start()
    if settings.email_polling_enabled and poller.agent.configured:
        asyncio.create_task(poller.start(check=True))   # IMAP check runs in a thread; startup is not delayed
    logger.info("ProcureAI ready (env=%s)", settings.app_env)
    yield
    await poller.stop()
    await jobs.stop()


app = FastAPI(title="ProcureAI", description="Multi-agent three-way invoice matching (Tesseract OCR + Groq LLM)",
              version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,          # bearer tokens, no cookies
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

for r in (auth.router, invoices.router, erp.router, dashboard.router, admin.router):
    app.include_router(r)


@app.get("/")
async def root():
    return {"name": "ProcureAI API", "version": app.version, "docs": "/docs", "health": "/api/health"}


@app.get("/api/ping")
def ping():
    """Cheap wake-up call for the frontend: no auth, no LLM, just one round trip to wake Neon too."""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    try:
        with SessionLocal() as db:
            user_from_token(db, token)
    except Exception:
        await websocket.close(code=4401)
        return
    await manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=not settings.is_production)
