from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.brand import SCHEDULER_JOB_ID
from app.config import (
    MAX_SCHEDULER_INTERVAL_HOURS,
    MIN_SCHEDULER_INTERVAL_HOURS,
    SCHEDULER_INTERVAL_PRESETS,
    get_settings,
    reload_settings,
)
from app.scheduler import _scheduler, apply_scheduler_settings, scheduler_job_status
from app.services.runtime_settings import save_overrides

router = APIRouter(prefix="/settings", tags=["settings"])


class SchedulerSettingsOut(BaseModel):
    scheduler_enabled: bool
    scheduler_interval_hours: float
    scheduler_running: bool
    next_run_at: str | None = None
    interval_presets: list[dict[str, str | float]]


class SchedulerSettingsIn(BaseModel):
    scheduler_enabled: bool | None = None
    scheduler_interval_hours: float | None = Field(None, gt=0)


@router.get("/scheduler", response_model=SchedulerSettingsOut)
def get_scheduler_settings():
    s = get_settings()
    job_active = False
    if _scheduler is not None and _scheduler.running:
        job_active = _scheduler.get_job(SCHEDULER_JOB_ID) is not None
    status = scheduler_job_status()
    return SchedulerSettingsOut(
        scheduler_enabled=s.scheduler_enabled,
        scheduler_interval_hours=s.scheduler_interval_hours,
        scheduler_running=job_active,
        next_run_at=status.get("next_run_at"),
        interval_presets=[
            {"label": label, "hours": hours}
            for label, hours in SCHEDULER_INTERVAL_PRESETS
        ],
    )


@router.put("/scheduler", response_model=SchedulerSettingsOut)
def update_scheduler_settings(body: SchedulerSettingsIn):
    if (
        body.scheduler_enabled is None
        and body.scheduler_interval_hours is None
    ):
        raise HTTPException(400, detail="No settings provided")

    updates: dict = {}
    if body.scheduler_enabled is not None:
        updates["scheduler_enabled"] = body.scheduler_enabled

    if body.scheduler_interval_hours is not None:
        hours = body.scheduler_interval_hours
        if hours < MIN_SCHEDULER_INTERVAL_HOURS or hours > MAX_SCHEDULER_INTERVAL_HOURS:
            raise HTTPException(
                400,
                detail=(
                    f"interval must be between {MIN_SCHEDULER_INTERVAL_HOURS} "
                    f"and {MAX_SCHEDULER_INTERVAL_HOURS} hours"
                ),
            )
        updates["scheduler_interval_hours"] = hours

    save_overrides(updates)
    reload_settings()
    apply_scheduler_settings()
    return get_scheduler_settings()
