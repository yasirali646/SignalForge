"""Track demo account agent request limits."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, UserRole
from app.config import get_settings
from app.models import DemoQuota


def get_agent_quota(db: Session, user: CurrentUser) -> tuple[int, int | None, int | None]:
    """Return (used, limit, remaining). limit/remaining are None for unlimited."""
    if user.role != UserRole.DEMO:
        return 0, None, None

    limit = int(get_settings().demo_agent_request_limit)
    row = db.get(DemoQuota, user.username)
    used = row.agent_requests_used if row else 0
    remaining = max(0, limit - used)
    return used, limit, remaining


def ensure_agent_request_allowed(db: Session, user: CurrentUser) -> None:
    if user.role != UserRole.DEMO:
        return
    used, limit, _ = get_agent_quota(db, user)
    if limit is not None and used >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Demo agent limit reached ({limit} requests). Sign in as admin for full access.",
        )


def record_agent_request(db: Session, user: CurrentUser) -> tuple[int, int | None, int | None]:
    if user.role != UserRole.DEMO:
        return get_agent_quota(db, user)

    row = db.get(DemoQuota, user.username)
    if row is None:
        row = DemoQuota(username=user.username, agent_requests_used=0)
        db.add(row)
    row.agent_requests_used += 1
    db.commit()
    return get_agent_quota(db, user)
