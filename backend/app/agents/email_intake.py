"""
Agent 1: Email intake — polls an IMAP inbox for invoice attachments.

Attachments are handed to `app.services.intake.receive_document`, which validates, stores and
deduplicates them (by SHA-256, persisted in the database), then queues processing.
"""

import asyncio
import email
import imaplib
import logging
from datetime import UTC, datetime
from email.header import decode_header, make_header
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

SKIP_SENDERS = ("mailer-daemon", "postmaster", "noreply", "no-reply")
INVOICE_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")
SMALL_INLINE_IMAGE = 51_200   # inline images under 50 KB are logos/signatures, not invoices

polling_state: dict[str, Any] = {
    "running": False,
    "last_poll": None,
    "last_error": None,
    "total_polls": 0,
    "total_invoices_found": 0,
}


def mask_email(address: str) -> str:
    if not address or "@" not in address:
        return "(not configured)"
    user, domain = address.split("@", 1)
    return f"{user[:2]}{'•' * max(1, len(user) - 2)}@{domain}"


def _decode(value) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


class EmailIntakeAgent:
    def __init__(self):
        self.host = settings.email_host
        self.port = settings.email_port
        self.user = settings.email_user
        self.password = settings.email_password
        self.use_ssl = settings.email_use_ssl

    @property
    def configured(self) -> bool:
        return bool(self.user and self.password)

    def _connect(self):
        mail = imaplib.IMAP4_SSL(self.host, self.port) if self.use_ssl else imaplib.IMAP4(self.host, self.port)
        mail.login(self.user, self.password)
        return mail

    def check_connection(self) -> tuple[bool, str | None]:
        try:
            mail = self._connect()
            mail.select("INBOX")
            mail.logout()
            return True, None
        except Exception as e:
            return False, str(e)

    def poll_inbox(self, folder: str = "INBOX", max_emails: int = 10) -> list[dict]:
        """Return [{filename, data, sender, subject, date}] for new invoice attachments (blocking)."""
        results: list[dict] = []
        mail = self._connect()
        try:
            mail.select(folder)
            _, numbers = mail.search(None, "UNSEEN")
            for num in numbers[0].split()[:max_emails]:
                _, msg_data = mail.fetch(num, "(BODY.PEEK[])")
                msg = email.message_from_bytes(msg_data[0][1])
                sender = _decode(msg.get("From"))
                if any(s in sender.lower() for s in SKIP_SENDERS):
                    mail.store(num, "+FLAGS", "\\Seen")
                    continue
                found = False
                for part in msg.walk():
                    if part.get_content_maintype() == "multipart":
                        continue
                    filename = _decode(part.get_filename())
                    if not filename or not filename.lower().endswith(INVOICE_EXTENSIONS):
                        continue
                    data = part.get_payload(decode=True)
                    if not data:
                        continue
                    disp = str(part.get("Content-Disposition", "")).lower()
                    inline = part.get("Content-ID") and "inline" in disp and "attachment" not in disp
                    if inline and not filename.lower().endswith(".pdf") and len(data) < SMALL_INLINE_IMAGE:
                        continue
                    results.append({"filename": filename, "data": data, "sender": sender,
                                    "subject": _decode(msg.get("Subject")), "date": msg.get("Date", "")})
                    found = True
                if found:
                    mail.store(num, "+FLAGS", "\\Seen")
        finally:
            try:
                mail.logout()
            except Exception:
                pass
        return results

    async def poll_inbox_async(self, folder: str = "INBOX", max_emails: int = 10) -> list[dict]:
        return await asyncio.to_thread(self.poll_inbox, folder, max_emails)


def mark_poll(found: int, error: str | None = None):
    polling_state["total_polls"] += 1
    polling_state["last_poll"] = datetime.now(UTC).isoformat()
    polling_state["last_error"] = error
    polling_state["total_invoices_found"] += found
