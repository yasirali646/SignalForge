"""Login and session endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import (
    TOKEN_TYPE,
    CurrentUser,
    UserRole,
    authenticate,
    create_access_token,
    require_user,
)
from app.config import get_settings
from app.database import get_db
from app.services.demo_quota import get_agent_quota

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class UserOut(BaseModel):
    username: str
    role: str
    can_manage_competitors: bool
    agent_requests_used: int = 0
    agent_requests_limit: int | None = None
    agent_requests_remaining: int | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = TOKEN_TYPE
    expires_in: int
    user: UserOut


class AuthConfigOut(BaseModel):
    auth_enabled: bool
    product_name: str
    demo_username: str | None = None


def _user_out(user: CurrentUser, db: Session) -> UserOut:
    used, limit, remaining = get_agent_quota(db, user)
    return UserOut(
        username=user.username,
        role=user.role.value,
        can_manage_competitors=user.can_manage_competitors,
        agent_requests_used=used,
        agent_requests_limit=limit,
        agent_requests_remaining=remaining,
    )


@router.get("/config", response_model=AuthConfigOut)
def auth_config():
    settings = get_settings()
    from app.brand import PRODUCT_NAME

    demo_username = settings.auth_demo_username if settings.auth_enabled else None
    return AuthConfigOut(
        auth_enabled=settings.auth_enabled,
        product_name=PRODUCT_NAME,
        demo_username=demo_username,
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.auth_enabled:
        user = CurrentUser(username=settings.auth_username, role=UserRole.ADMIN)
        token, expires_in = create_access_token(user)
        return LoginResponse(
            access_token=token,
            expires_in=expires_in,
            user=_user_out(user, db),
        )

    user = authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, expires_in = create_access_token(user)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=_user_out(user, db),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(require_user), db: Session = Depends(get_db)):
    return _user_out(user, db)
