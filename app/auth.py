"""JWT authentication and role-based access."""

from __future__ import annotations

import enum
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)

TOKEN_TYPE = "bearer"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEMO = "demo"


@dataclass(frozen=True)
class CurrentUser:
    username: str
    role: UserRole

    @property
    def can_manage_competitors(self) -> bool:
        return self.role == UserRole.ADMIN


def authenticate(username: str, password: str) -> CurrentUser | None:
    settings = get_settings()
    if secrets.compare_digest(username, settings.auth_username) and secrets.compare_digest(
        password, settings.auth_password
    ):
        return CurrentUser(username=username, role=UserRole.ADMIN)
    if secrets.compare_digest(username, settings.auth_demo_username) and secrets.compare_digest(
        password, settings.auth_demo_password
    ):
        return CurrentUser(username=username, role=UserRole.DEMO)
    return None


def create_access_token(user: CurrentUser) -> tuple[str, int]:
    settings = get_settings()
    expires = timedelta(hours=settings.auth_token_expire_hours)
    expire_at = datetime.now(timezone.utc) + expires
    payload: dict[str, Any] = {
        "sub": user.username,
        "role": user.role.value,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> CurrentUser:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    username = payload.get("sub")
    role_raw = payload.get("role", UserRole.ADMIN.value)
    if not username or not isinstance(username, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        role = UserRole(role_raw)
    except ValueError:
        role = UserRole.ADMIN
    return CurrentUser(username=username, role=role)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    settings = get_settings()
    if not settings.auth_enabled:
        return CurrentUser(username=settings.auth_username, role=UserRole.ADMIN)

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)


def require_admin(user: CurrentUser = Depends(require_user)) -> CurrentUser:
    if not user.can_manage_competitors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo accounts cannot modify competitors",
        )
    return user


def is_public_path(path: str) -> bool:
    if path in ("/", "/docs", "/openapi.json", "/redoc"):
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    public_api = (
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/auth/config",
    )
    return path in public_api
