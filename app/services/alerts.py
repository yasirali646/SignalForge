"""Evaluate alert rules against new events."""

from __future__ import annotations

import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AlertLog, AlertRule, Event

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _severity_meets(event_sev: str, min_sev: str) -> bool:
    return SEVERITY_RANK.get(event_sev, 0) >= SEVERITY_RANK.get(min_sev, 0)


def _types_match(rule_types: str, event_type: str) -> bool:
    if not rule_types.strip():
        return True
    allowed = {t.strip() for t in rule_types.split(",") if t.strip()}
    return event_type in allowed


def evaluate_alerts_for_event(db: Session, event: Event) -> list[AlertLog]:
    rules = db.scalars(select(AlertRule).where(AlertRule.enabled.is_(True))).all()
    logs: list[AlertLog] = []

    for rule in rules:
        if rule.competitor_id and rule.competitor_id != event.competitor_id:
            continue
        if not _severity_meets(event.severity, rule.min_severity):
            continue
        if not _types_match(rule.event_types, event.event_type):
            continue

        message = (
            f"[SignalForge] {event.title} ({event.severity}) — "
            f"{event.diff_summary[:200]}"
        )
        log = AlertLog(
            rule_id=rule.id,
            event_id=event.id,
            message=message,
            delivered=False,
        )
        db.add(log)
        logs.append(log)

        if rule.webhook_url:
            try:
                with httpx.Client(timeout=10.0) as client:
                    client.post(
                        rule.webhook_url,
                        json={
                            "rule": rule.name,
                            "event_id": event.id,
                            "competitor_id": event.competitor_id,
                            "severity": event.severity,
                            "event_type": event.event_type,
                            "title": event.title,
                            "summary": event.diff_summary,
                            "evidence_url": event.evidence_url,
                        },
                    )
                log.delivered = True
            except Exception as exc:
                logger.warning("Webhook delivery failed for rule %s: %s", rule.name, exc)

    return logs


def seed_default_alert_rules(db: Session) -> None:
    existing = db.scalar(select(AlertRule).limit(1))
    if existing:
        return
    db.add(
        AlertRule(
            name="High severity competitive changes",
            enabled=True,
            event_types="pricing_change,messaging_change,hiring_change",
            min_severity="high",
        )
    )
    db.add(
        AlertRule(
            name="Agent intelligence briefs",
            enabled=True,
            event_types="agent_intel",
            min_severity="medium",
        )
    )
    db.commit()
