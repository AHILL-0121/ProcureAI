"""Authentication (JWT bearer tokens), role checks, password hashing, and a small rate limiter."""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Role, User

logger = logging.getLogger(__name__)

ROLE_RANK = {Role.VIEWER: 0, Role.AP_CLERK: 1, Role.APPROVER: 2, Role.ADMIN: 3}
_bearer = HTTPBearer(auto_error=False)
DEV_ADMIN_EMAIL = "admin@procureai.local"
DEV_ADMIN_PASSWORD = "procureai-admin"


# ---------------------------------------------------------------- passwords (scrypt, stdlib)
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, dk_b64 = stored.split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
    except ValueError:
        return False
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=len(expected))
    return hmac.compare_digest(dk, expected)


# ---------------------------------------------------------------- tokens
def _secret() -> str:
    if settings.is_production and settings.jwt_secret == "change-me-in-production":
        raise RuntimeError("Set JWT_SECRET in production")
    return settings.jwt_secret


def create_token(user: User, scope: str = "access", minutes: int | None = None, **claims) -> str:
    now = datetime.now(UTC)
    payload = {"sub": user.id, "role": user.role.value, "scope": scope, "iat": now,
               "exp": now + timedelta(minutes=minutes or settings.jwt_expire_minutes), **claims}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str, scope: str = "access") -> dict:
    try:
        data = jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.") from e
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials") from e
    if data.get("scope") != scope:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return data


def user_from_token(db: Session, token: str, scope: str = "access") -> User:
    data = decode_token(token, scope)
    user = db.get(User, data.get("sub"))
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found or disabled")
    return user


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                     db: Session = Depends(get_db)) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required", headers={"WWW-Authenticate": "Bearer"})
    return user_from_token(db, creds.credentials)


def require_role(minimum: Role):
    def dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"This action needs the {minimum.value.replace('_', ' ')} role")
        return user
    return dep


# ---------------------------------------------------------------- rate limiting (per client, in-memory)
class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, limit: int, window: float = 60.0):
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Wait a minute and try again.",
                                headers={"Retry-After": str(int(window))})
        q.append(now)

    def reset(self):
        self._hits.clear()


limiter = RateLimiter()


def client_key(request: Request, suffix: str) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return f"{suffix}:{ip}"


# ---------------------------------------------------------------- bootstrap
def bootstrap_admin(db: Session):
    if db.scalar(select(func.count()).select_from(User)):
        return
    if settings.admin_email and settings.admin_password:
        email, password = settings.admin_email.lower(), settings.admin_password
    elif not settings.is_production:
        email, password = DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD
        logger.warning("No users exist: created development admin %s / %s. Set ADMIN_EMAIL and ADMIN_PASSWORD "
                       "for real deployments.", email, password)
    else:
        logger.error("No users exist and ADMIN_EMAIL/ADMIN_PASSWORD are not set: nobody can sign in.")
        return
    db.add(User(email=email, name="Administrator", password_hash=hash_password(password), role=Role.ADMIN))
    db.commit()


def random_password() -> str:
    return secrets.token_urlsafe(12)
