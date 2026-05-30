from fastapi import APIRouter

from app.config import get_settings
from app.scheduler import _scheduler, start_scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status")
def scheduler_status():
    s = get_settings()
    running = _scheduler is not None and _scheduler.running
    return {
        "enabled": s.scheduler_enabled,
        "running": running,
        "interval_hours": s.scheduler_interval_hours,
    }


@router.post("/start")
def scheduler_start():
    start_scheduler()
    return scheduler_status()
