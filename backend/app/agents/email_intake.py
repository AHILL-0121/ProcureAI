"""
Agent 1: Email Intake Agent
Monitors email inboxes (IMAP), detects invoice attachments, extracts metadata.
For MVP: Also supports manual file upload as fallback.
Supports continuous background polling via asyncio.
"""

import asyncio
import imaplib
import email
import os
import hashlib
import logging
from email.header import decode_header
from datetime import datetime
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory dedup store (use Redis in production)
_seen_hashes: set[str] = set()

# ── Polling state (module-level, shared across the app) ──
polling_state = {
    "running": False,
    "last_poll": None,          # ISO timestamp of last successful poll
    "last_error": None,         # last error message (if any)
    "total_polls": 0,
    "total_invoices_found": 0,
}


class EmailIntakeAgent:
    """Monitors IMAP inbox for invoice attachments."""

    def __init__(self):
        self.host = settings.email_host
        self.port = settings.email_port
        self.user = settings.email_user
        self.password = settings.email_password
        self.use_ssl = settings.email_use_ssl

    def _connect(self) -> imaplib.IMAP4_SSL | imaplib.IMAP4:
        if self.use_ssl:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            mail = imaplib.IMAP4(self.host, self.port)
        mail.login(self.user, self.password)
        return mail

    def _file_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _is_duplicate(self, file_hash: str) -> bool:
        if file_hash in _seen_hashes:
            return True
        _seen_hashes.add(file_hash)
        return False

    def poll_inbox(self, folder: str = "INBOX", max_emails: int = 10) -> list[dict]:
        """Poll inbox for new emails with PDF attachments."""
        results = []
        try:
            mail = self._connect()
            mail.select(folder)
            _, message_numbers = mail.search(None, "UNSEEN")

            for num in message_numbers[0].split()[:max_emails]:
                # Use PEEK so the email stays UNSEEN until we confirm we saved an attachment
                _, msg_data = mail.fetch(num, "(BODY.PEEK[])")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                sender = msg.get("From", "")
                date_str = msg.get("Date", "")

                # ── Skip non-invoice senders ──
                sender_lower = sender.lower()
                if any(skip in sender_lower for skip in (
                    "mailer-daemon", "postmaster", "noreply", "no-reply",
                )):
                    logger.debug(f"Skipped system email from {sender}")
                    # Mark system emails as SEEN so they don't reappear
                    mail.store(num, "+FLAGS", "\\Seen")
                    continue

                # Extract attachments
                saved_from_this_email = False
                for part in msg.walk():
                    if part.get_content_maintype() == "multipart":
                        continue

                    content_disp = str(part.get("Content-Disposition", "")).lower()
                    content_id = part.get("Content-ID")
                    is_explicit_attachment = "attachment" in content_disp

                    filename = part.get_filename()
                    if filename and filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
                        file_data = part.get_payload(decode=True)
                        if not file_data:
                            continue

                        # ── Skip small inline images (<50 KB) — likely icons/logos/signatures ──
                        # Gmail marks pasted images as "inline" with a Content-ID,
                        # but real invoice screenshots are typically >50 KB.
                        is_inline = content_id and "inline" in content_disp and not is_explicit_attachment
                        is_image = filename.lower().endswith((".png", ".jpg", ".jpeg"))
                        if is_inline and is_image and len(file_data) < 51_200:
                            logger.info(f"Skipped small inline image ({len(file_data)} bytes): {filename}")
                            continue

                        logger.info(f"Accepted attachment: {filename} ({len(file_data)} bytes, disp={content_disp[:40]})")
                        file_hash = self._file_hash(file_data)

                        if self._is_duplicate(file_hash):
                            logger.info(f"Duplicate attachment skipped: {filename}")
                            continue

                        # Save file
                        safe_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        file_path = os.path.join(UPLOAD_DIR, safe_name)
                        with open(file_path, "wb") as f:
                            f.write(file_data)

                        results.append({
                            "subject": subject,
                            "sender": sender,
                            "date": date_str,
                            "filename": filename,
                            "file_path": file_path,
                            "file_hash": file_hash,
                            "file_size": len(file_data),
                        })
                        saved_from_this_email = True

                # Mark email as SEEN only if we saved at least one attachment
                if saved_from_this_email:
                    mail.store(num, "+FLAGS", "\\Seen")

            mail.logout()
        except Exception as e:
            logger.error(f"Email polling error: {e}")
            polling_state["last_error"] = str(e)

        return results

    async def poll_inbox_async(self, folder: str = "INBOX", max_emails: int = 10) -> list[dict]:
        """Async wrapper – runs blocking IMAP poll in a thread-pool executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.poll_inbox, folder, max_emails)

    @staticmethod
    def save_uploaded_file(filename: str, file_data: bytes) -> dict:
        """Save a manually uploaded invoice file (MVP fallback)."""
        file_hash = hashlib.sha256(file_data).hexdigest()
        safe_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        with open(file_path, "wb") as f:
            f.write(file_data)

        return {
            "subject": "Manual Upload",
            "sender": "user@local",
            "date": datetime.utcnow().isoformat(),
            "filename": filename,
            "file_path": file_path,
            "file_hash": file_hash,
            "file_size": len(file_data),
        }
