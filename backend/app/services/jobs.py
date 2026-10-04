"""
In-process job queue.

Uploads and emails create an Invoice row (status RECEIVED) and enqueue its id. Workers run the
blocking pipeline in threads, so HTTP requests return immediately and WebSocket progress flows
while invoices are processed. On startup, invoices left mid-pipeline by a restart are re-queued.
A periodic task re-matches invoices on hold for a goods receipt.
"""

import asyncio
import logging

from sqlalchemy import select

from app.agents.erp_integration import invalidate_cache
from app.agents.orchestrator import OrchestratorAgent
from app.config import settings
from app.database import SessionLocal
from app.models import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)

IN_FLIGHT = (InvoiceStatus.RECEIVED, InvoiceStatus.EXTRACTING, InvoiceStatus.EXTRACTED,
             InvoiceStatus.VALIDATING, InvoiceStatus.VALIDATED, InvoiceStatus.MATCHING)
HOLD_RECHECK_SECONDS = 600


class JobQueue:
    def __init__(self, orchestrator: OrchestratorAgent | None = None):
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.queue: asyncio.Queue[str] | None = None
        self._tasks: list[asyncio.Task] = []
        self._queued: set[str] = set()

    @property
    def depth(self) -> int:
        return self.queue.qsize() if self.queue else 0

    async def start(self):
        self.queue = asyncio.Queue()
        for n in range(max(1, settings.worker_concurrency)):
            self._tasks.append(asyncio.create_task(self._worker(n)))
        self._tasks.append(asyncio.create_task(self._hold_rechecker()))
        await self._recover()

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    def enqueue(self, invoice_id: str):
        if self.queue is None:
            raise RuntimeError("Job queue not started")
        if invoice_id in self._queued:
            return
        self._queued.add(invoice_id)
        self.queue.put_nowait(invoice_id)

    async def _worker(self, n: int):
        assert self.queue is not None
        while True:
            invoice_id = await self.queue.get()
            try:
                await asyncio.to_thread(self.orchestrator.run, invoice_id)
            except Exception:
                logger.exception("Worker %s failed on %s", n, invoice_id)
            finally:
                self._queued.discard(invoice_id)
                self.queue.task_done()

    async def _recover(self):
        def stuck_ids():
            with SessionLocal() as db:
                return list(db.scalars(select(Invoice.id).where(Invoice.status.in_(IN_FLIGHT))
                                       .order_by(Invoice.created_at)))
        ids = await asyncio.to_thread(stuck_ids)
        for i in ids:
            self.enqueue(i)
        if ids:
            logger.info("Re-queued %d invoice(s) interrupted by a restart", len(ids))

    async def _hold_rechecker(self):
        while True:
            await asyncio.sleep(HOLD_RECHECK_SECONDS)
            try:
                await asyncio.to_thread(self.recheck_holds)
            except Exception:
                logger.exception("Hold re-check failed")

    def recheck_holds(self) -> int:
        invalidate_cache()   # pick up goods receipts posted since the last look
        with SessionLocal() as db:
            ids = list(db.scalars(select(Invoice.id).where(Invoice.status == InvoiceStatus.ON_HOLD)))
        for i in ids:
            self.orchestrator.rematch(i, actor=None)
        return len(ids)


jobs = JobQueue()
