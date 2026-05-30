"""Demo helpers for hackathon judging when live pages are unchanged."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.extractors import content_hash, extract_from_html
from app.database import get_db
from app.diff.engine import diff_snapshots
from app.models import Competitor, Event, Snapshot, Source
from app.schemas import EventOut

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/simulate-change/{competitor_id}", response_model=list[EventOut])
def simulate_change(competitor_id: int, db: Session = Depends(get_db)):
    """
    Inject a changed pricing snapshot to produce a diff event for demos.
    """
    competitor = db.get(Competitor, competitor_id)
    if not competitor:
        raise HTTPException(404, detail="Competitor not found")

    source = db.scalar(
        select(Source).where(
            Source.competitor_id == competitor_id,
            Source.source_type == "pricing",
        )
    )
    if not source:
        raise HTTPException(404, detail="No pricing source for competitor")

    previous = db.scalar(
        select(Snapshot)
        .where(Snapshot.source_id == source.id)
        .order_by(Snapshot.captured_at.desc())
        .limit(1)
    )
    if not previous:
        raise HTTPException(400, detail="Run collection first to create baseline")

    before = json.loads(previous.extracted_json)
    fixture_path = (
        Path(__file__).resolve().parents[2] / "fixtures" / "pricing_changed.html"
    )
    if not fixture_path.exists():
        fixture_path.write_text(
            """<html><body><h1>Plans & Pricing</h1>
<p>Starter plan $79/mo — limited time offer.</p>
<p>Professional plan $349/mo — includes API access and SSO.</p>
<p>Enterprise — contact sales.</p></body></html>""",
            encoding="utf-8",
        )
    html = fixture_path.read_text(encoding="utf-8")
    after = extract_from_html(html, "pricing", source.url)

    new_hash = content_hash(after)
    snapshot = Snapshot(
        competitor_id=competitor.id,
        source_id=source.id,
        content_hash=new_hash,
        extracted_json=json.dumps(after),
        raw_preview=html[:2000],
        collector="demo_simulate",
    )
    db.add(snapshot)
    db.flush()

    created_events = []
    for evt in diff_snapshots(
        before,
        after,
        source_type="pricing",
        evidence_url=source.url,
    ):
        row = Event(
            competitor_id=competitor.id,
            source_id=source.id,
            event_type=evt["event_type"],
            severity=evt["severity"],
            title=evt["title"],
            diff_summary=evt["diff_summary"],
            evidence_url=evt["evidence_url"],
            before_snapshot_id=previous.id,
            after_snapshot_id=snapshot.id,
        )
        db.add(row)
        db.flush()
        created_events.append(
            EventOut(
                id=row.id,
                competitor_id=row.competitor_id,
                competitor_name=competitor.name,
                source_id=row.source_id,
                event_type=row.event_type,
                severity=row.severity,
                title=row.title,
                diff_summary=row.diff_summary,
                evidence_url=row.evidence_url,
                before_snapshot_id=row.before_snapshot_id,
                after_snapshot_id=row.after_snapshot_id,
                detected_at=row.detected_at,
            )
        )

    db.commit()
    return created_events
