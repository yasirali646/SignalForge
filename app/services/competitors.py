"""Competitor lifecycle: update metadata/sources and cascade delete."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AgentRun, AlertLog, AlertRule, Competitor, Event, Snapshot, Source
from app.schemas import CompetitorUpdate


def _normalize_domain(domain: str) -> str:
    return domain.lower().removeprefix("https://").removeprefix("http://").rstrip("/")


def update_competitor(db: Session, competitor_id: int, body: CompetitorUpdate) -> Competitor:
    row = db.get(Competitor, competitor_id)
    if not row:
        raise ValueError("Competitor not found")

    domain = _normalize_domain(body.domain)
    if domain != row.domain:
        clash = db.scalar(
            select(Competitor).where(
                Competitor.domain == domain, Competitor.id != competitor_id
            )
        )
        if clash:
            raise ValueError("Competitor domain already exists")

    if body.name != row.name:
        clash = db.scalar(
            select(Competitor).where(
                Competitor.name == body.name, Competitor.id != competitor_id
            )
        )
        if clash:
            raise ValueError("Competitor name already exists")

    row.name = body.name
    row.domain = domain

    sources = db.scalars(
        select(Source).where(Source.competitor_id == competitor_id)
    ).all()
    by_type = {s.source_type: s for s in sources}

    url_map = {
        "pricing": (body.pricing_url, True),
        "homepage": (body.homepage_url, False),
        "careers": (body.careers_url, False),
    }
    for source_type, (url, use_unlocker) in url_map.items():
        if not url:
            continue
        existing = by_type.get(source_type)
        if existing:
            existing.url = url
            if source_type == "pricing":
                existing.use_unlocker = True
        else:
            db.add(
                Source(
                    competitor_id=competitor_id,
                    url=url,
                    source_type=source_type,
                    use_unlocker=use_unlocker,
                )
            )

    news = by_type.get("news")
    news_url = f"serp://{body.name}/news"
    if news:
        news.url = news_url
    else:
        db.add(
            Source(
                competitor_id=competitor_id,
                url=news_url,
                source_type="news",
            )
        )

    db.commit()
    db.refresh(row)
    return row


def delete_competitor(db: Session, competitor_id: int) -> None:
    row = db.get(Competitor, competitor_id)
    if not row:
        raise ValueError("Competitor not found")

    event_ids = list(
        db.scalars(select(Event.id).where(Event.competitor_id == competitor_id)).all()
    )
    if event_ids:
        db.execute(delete(AlertLog).where(AlertLog.event_id.in_(event_ids)))

    db.execute(delete(Event).where(Event.competitor_id == competitor_id))
    db.execute(delete(Snapshot).where(Snapshot.competitor_id == competitor_id))
    db.execute(delete(Source).where(Source.competitor_id == competitor_id))
    db.execute(delete(AgentRun).where(AgentRun.competitor_id == competitor_id))
    db.execute(delete(AlertRule).where(AlertRule.competitor_id == competitor_id))
    db.delete(row)
    db.commit()
