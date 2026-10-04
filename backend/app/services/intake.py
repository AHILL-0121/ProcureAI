"""Receiving documents: validation, safe storage, deduplication by content hash, invoice creation."""

import hashlib
import os
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditLog, Invoice, InvoiceStatus

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_DIR = settings.upload_dir or os.path.join(BACKEND_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# extension -> (magic prefix check, media type)
ALLOWED = {
    ".pdf": ("application/pdf", lambda b: b.startswith(b"%PDF-")),
    ".png": ("image/png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image/jpeg", lambda b: b.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda b: b.startswith(b"\xff\xd8\xff")),
}
SNIFF = [(".pdf", ALLOWED[".pdf"][1]), (".png", ALLOWED[".png"][1]), (".jpg", ALLOWED[".jpg"][1])]


class IntakeError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class IntakeResult:
    invoice: Invoice
    duplicate: bool


def detect_type(data: bytes) -> Optional[str]:
    for ext, check in SNIFF:
        if check(data[:16]):
            return ext
    return None


def media_type_for(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        return "text/plain; charset=utf-8"
    return ALLOWED.get(ext, ("application/octet-stream",))[0]


def safe_display_name(name: str | None) -> str:
    base = os.path.basename((name or "document").replace("\\", "/"))
    base = "".join(c for c in base if c.isprintable())[:150]
    return base or "document"


def receive_document(db: Session, data: bytes, original_name: str | None, source: str,
                     actor: str | None = None, allow_text: bool = False) -> IntakeResult:
    if not data:
        raise IntakeError("The file is empty")
    if len(data) > settings.upload_max_bytes:
        raise IntakeError(f"The file is larger than {settings.upload_max_bytes // (1024 * 1024)} MB", 413)

    ext = detect_type(data)
    if ext is None:
        if allow_text and (original_name or "").lower().endswith(".txt"):
            ext = ".txt"
        else:
            raise IntakeError("Only PDF, PNG and JPEG files are accepted", 415)

    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalars(select(Invoice).where(Invoice.file_hash == digest,
                                                Invoice.status.notin_([InvoiceStatus.FAILED, InvoiceStatus.REJECTED]))
                          .order_by(Invoice.created_at)).first()
    if existing:
        return IntakeResult(existing, duplicate=True)

    stored = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, stored)
    with open(path, "wb") as fh:
        fh.write(data)

    inv = Invoice(status=InvoiceStatus.RECEIVED, source_email=source, original_filename=safe_display_name(original_name),
                  file_path=path, file_hash=digest)
    db.add(inv)
    db.flush()
    db.add(AuditLog(invoice_id=inv.id, agent="intake", action="RECEIVED", actor=actor,
                    details={"source": source, "filename": inv.original_filename, "bytes": len(data)}))
    db.commit()
    return IntakeResult(inv, duplicate=False)
