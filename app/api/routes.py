import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import CurrentUser, require_admin
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.runner import collect_all, collect_competitor
from app.database import get_db
from app.models import Competitor, Event, Snapshot, Source
from app.schemas import (
    CollectRunOut,
    CompetitorCreate,
    CompetitorOut,
    CompetitorUpdate,
    DailyBriefOut,
    EventOut,
    SourceCreate,
    SourceOut,
    SnapshotOut,
)
from app.services.competitors import delete_competitor, update_competitor

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "signalforge"}


@router.get("/competitors", response_model=list[CompetitorOut])
def list_competitors(db: Session = Depends(get_db)):
    return db.scalars(select(Competitor).order_by(Competitor.name)).all()


@router.post("/competitors", response_model=CompetitorOut, status_code=201)
def create_competitor(
    body: CompetitorCreate,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    domain = body.domain.lower().removeprefix("https://").removeprefix("http://").rstrip("/")
    existing = db.scalar(select(Competitor).where(Competitor.domain == domain))
    if existing:
        raise HTTPException(409, detail="Competitor domain already exists")
    row = Competitor(name=body.name, domain=domain)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/competitors/{competitor_id}", response_model=CompetitorOut)
def patch_competitor(
    competitor_id: int,
    body: CompetitorUpdate,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    try:
        return update_competitor(db, competitor_id, body)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(404, detail=msg) from exc
        raise HTTPException(409, detail=msg) from exc


@router.delete("/competitors/{competitor_id}", status_code=204)
def remove_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    try:
        delete_competitor(db, competitor_id)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.get("/competitors/{competitor_id}/sources", response_model=list[SourceOut])
def list_sources(competitor_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(Source).where(Source.competitor_id == competitor_id)
    ).all()


@router.post(
    "/competitors/{competitor_id}/sources",
    response_model=SourceOut,
    status_code=201,
)
def add_source(
    competitor_id: int,
    body: SourceCreate,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    if not db.get(Competitor, competitor_id):
        raise HTTPException(404, detail="Competitor not found")
    row = Source(
        competitor_id=competitor_id,
        url=str(body.url),
        source_type=body.source_type,
        use_unlocker=body.use_unlocker,
        label=body.label,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _event_to_out(e: Event, db: Session) -> EventOut:
    comp = db.get(Competitor, e.competitor_id)
    origin = getattr(e, "origin", None) or "pipeline"
    return EventOut(
        id=e.id,
        competitor_id=e.competitor_id,
        competitor_name=comp.name if comp else None,
        source_id=e.source_id,
        origin=origin,
        agent_run_id=getattr(e, "agent_run_id", None),
        event_type=e.event_type,
        severity=e.severity,
        title=e.title,
        diff_summary=e.diff_summary,
        evidence_url=e.evidence_url,
        before_snapshot_id=e.before_snapshot_id,
        after_snapshot_id=e.after_snapshot_id,
        detected_at=e.detected_at,
    )


@router.get("/events", response_model=list[EventOut])
def list_events(
    competitor_id: int | None = None,
    severity: str | None = Query(None, pattern="^(low|medium|high)$"),
    event_type: str | None = None,
    origin: str | None = Query(None, pattern="^(pipeline|agent)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = (
        select(Event)
        .order_by(Event.detected_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if competitor_id:
        q = q.where(Event.competitor_id == competitor_id)
    if severity:
        q = q.where(Event.severity == severity)
    if event_type:
        q = q.where(Event.event_type == event_type)
    if origin:
        q = q.where(Event.origin == origin)
    events = db.scalars(q).all()
    return [_event_to_out(e, db) for e in events]


@router.get("/snapshots", response_model=list[SnapshotOut])
def list_snapshots(
    competitor_id: int | None = None,
    source_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Snapshot).order_by(Snapshot.captured_at.desc()).limit(limit)
    if competitor_id:
        q = q.where(Snapshot.competitor_id == competitor_id)
    if source_id:
        q = q.where(Snapshot.source_id == source_id)
    rows = db.scalars(q).all()
    return [
        SnapshotOut(
            id=s.id,
            competitor_id=s.competitor_id,
            source_id=s.source_id,
            content_hash=s.content_hash,
            extracted=json.loads(s.extracted_json),
            raw_preview=s.raw_preview,
            collector=s.collector,
            captured_at=s.captured_at,
        )
        for s in rows
    ]


@router.post("/collect/{competitor_id}", response_model=CollectRunOut)
def run_collect(competitor_id: int, db: Session = Depends(get_db)):
    if not db.get(Competitor, competitor_id):
        raise HTTPException(404, detail="Competitor not found")
    stats = collect_competitor(db, competitor_id)
    return CollectRunOut(**stats)


@router.post("/collect", response_model=list[CollectRunOut])
def run_collect_all(db: Session = Depends(get_db)):
    results = collect_all(db)
    return [CollectRunOut(**r) for r in results]


@router.get("/brief/daily", response_model=DailyBriefOut)
def daily_brief(db: Session = Depends(get_db)):
    events = db.scalars(select(Event).order_by(Event.detected_at.desc()).limit(25)).all()
    event_out = []
    high = 0
    for e in events:
        comp = db.get(Competitor, e.competitor_id)
        if e.severity == "high":
            high += 1
        event_out.append(_event_to_out(e, db))
    summary = (
        f"Daily SignalForge brief: {len(event_out)} recent signals, {high} high severity."
        if event_out
        else "No change events yet. Run collection to establish baselines."
    )
    return DailyBriefOut(
        generated_at=datetime.now(timezone.utc),
        event_count=len(event_out),
        high_severity_count=high,
        events=event_out,
        summary=summary,
    )
