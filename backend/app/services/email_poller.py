"""Background IMAP polling. Runtime state lives here, not in `settings`."""

import asyncio
import logging

from app.agents.email_intake import EmailIntakeAgent, mark_poll, polling_state
from app.config import settings
from app.database import SessionLocal
from app.services.intake import IntakeError, receive_document
from app.services.jobs import jobs

logger = logging.getLogger(__name__)


class EmailPoller:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self.agent = EmailIntakeAgent()
        self.connection_ok: bool | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def ingest(self, attachments: list[dict]) -> list[dict]:
        def save():
            out = []
            with SessionLocal() as db:
                for a in attachments:
                    try:
                        res = receive_document(db, a["data"], a["filename"], source=a["sender"])
                        out.append({"filename": a["filename"], "invoice_id": res.invoice.id, "duplicate": res.duplicate})
                    except IntakeError as e:
                        out.append({"filename": a["filename"], "error": str(e)})
            return out
        results = await asyncio.to_thread(save)
        for r in results:
            if r.get("invoice_id") and not r.get("duplicate"):
                jobs.enqueue(r["invoice_id"])
        return results

    async def poll_once(self) -> list[dict]:
        try:
            attachments = await self.agent.poll_inbox_async()
        except Exception as e:
            mark_poll(0, str(e))
            raise
        results = await self.ingest(attachments)
        mark_poll(len([r for r in results if r.get("invoice_id") and not r.get("duplicate")]))
        return results

    async def _loop(self):
        polling_state["running"] = True
        try:
            while True:
                try:
                    found = await self.poll_once()
                    if found:
                        logger.info("Email poll: %d attachment(s)", len(found))
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning("Email poll failed: %s", e)
                await asyncio.sleep(max(10, settings.email_poll_interval))
        finally:
            polling_state["running"] = False

    async def start(self, check: bool = True) -> bool:
        if self.running or not self.agent.configured:
            return self.running
        if check:
            ok, err = await asyncio.to_thread(self.agent.check_connection)
            self.connection_ok = ok
            if not ok:
                polling_state["last_error"] = err
                logger.error("IMAP check failed, email polling not started: %s", err)
                return False
        self._task = asyncio.create_task(self._loop())
        return True

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        polling_state["running"] = False


poller = EmailPoller()
