"""Autonomous scheduled collection for all competitors."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.brand import SCHEDULER_JOB_ID
from app.collectors.runner import collect_all
from app.config import get_settings
from app.database import SessionLocal
from app.services.alerts import evaluate_alerts_for_event
from app.models import Event
from sqlalchemy import select

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _scheduled_collect_job() -> None:
    logger.info("Scheduled collection started")
    db = SessionLocal()
    try:
        results = collect_all(db)
        total_events = sum(r.get("events_created", 0) for r in results)
        logger.info("Scheduled collection done: %d new events", total_events)

        if total_events:
            recent = db.scalars(
                select(Event).order_by(Event.detected_at.desc()).limit(total_events + 5)
            ).all()
            for event in recent[:total_events]:
                evaluate_alerts_for_event(db, event)
    except Exception:
        logger.exception("Scheduled collection failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (scheduler_enabled=false)")
        if _scheduler and _scheduler.running:
            try:
                _scheduler.remove_job(SCHEDULER_JOB_ID)
            except Exception:
                pass
        return _scheduler if _scheduler and _scheduler.running else None

    if _scheduler is None or not _scheduler.running:
        _scheduler = BackgroundScheduler()
        _scheduler.start()

    _scheduler.add_job(
        _scheduled_collect_job,
        trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
        id=SCHEDULER_JOB_ID,
        replace_existing=True,
    )
    logger.info(
        "Scheduler started: collect every %s hour(s)",
        settings.scheduler_interval_hours,
    )
    return _scheduler


def apply_scheduler_settings() -> None:
    """Reload config from disk and reschedule the background collect job."""
    from app.config import reload_settings

    reload_settings()
    settings = get_settings()
    global _scheduler

    if not settings.scheduler_enabled:
        if _scheduler and _scheduler.running:
            try:
                _scheduler.remove_job(SCHEDULER_JOB_ID)
            except Exception:
                pass
            logger.info("Scheduled collection disabled via settings")
        return

    if _scheduler is None or not _scheduler.running:
        start_scheduler()
        return

    _scheduler.reschedule_job(
        SCHEDULER_JOB_ID,
        trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
    )
    logger.info(
        "Scheduler rescheduled: collect every %s hour(s)",
        settings.scheduler_interval_hours,
    )


def scheduler_job_status() -> dict:
    """Next run time for the collect job, if scheduled."""
    if _scheduler is None or not _scheduler.running:
        return {"next_run_at": None}
    job = _scheduler.get_job(SCHEDULER_JOB_ID)
    if not job or not job.next_run_time:
        return {"next_run_at": None}
    return {"next_run_at": job.next_run_time.isoformat()}


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None
