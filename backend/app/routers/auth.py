from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User
from app.routers.common import audit
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserOut, UserUpdate
from app.security import (
    client_key,
    create_token,
    get_current_user,
    hash_password,
    limiter,
    random_password,
    require_role,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    limiter.check(client_key(request, "login"), limit=10)
    user = db.scalars(select(User).where(func.lower(User.email) == body.email.strip().lower())).first()
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return TokenResponse(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


def _role(value: str) -> Role:
    try:
        return Role(value)
    except ValueError as e:
        raise HTTPException(422, f"Unknown role '{value}'. Use viewer, ap_clerk, approver or admin.") from e


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_role(Role.ADMIN))):
    return list(db.scalars(select(User).order_by(User.created_at)))


@router.post("/users", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_role(Role.ADMIN))):
    email = body.email.strip().lower()
    if db.scalars(select(User).where(func.lower(User.email) == email)).first():
        raise HTTPException(409, "A user with this email already exists")
    password = body.password or random_password()
    user = User(email=email, name=body.name.strip(), role=_role(body.role), password_hash=hash_password(password))
    db.add(user)
    audit(db, None, "USER_CREATED", admin.email, {"email": email, "role": user.role.value})
    db.commit()
    return {"user": UserOut.model_validate(user), "temporary_password": None if body.password else password}


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate, db: Session = Depends(get_db),
                admin: User = Depends(require_role(Role.ADMIN))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if body.name is not None:
        user.name = body.name.strip()
    if body.role is not None:
        if user.id == admin.id and body.role != Role.ADMIN.value:
            raise HTTPException(400, "You cannot remove your own admin role")
        user.role = _role(body.role)
    if body.active is not None:
        if user.id == admin.id and not body.active:
            raise HTTPException(400, "You cannot deactivate your own account")
        user.active = body.active
    if body.password:
        user.password_hash = hash_password(body.password)
    audit(db, None, "USER_UPDATED", admin.email, {"user": user.email, **body.model_dump(exclude={"password"}, exclude_none=True)})
    db.commit()
    return user
