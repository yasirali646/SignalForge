from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    domain: str = Field(..., min_length=3, max_length=256)


class CompetitorUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    domain: str = Field(..., min_length=3, max_length=256)
    pricing_url: str | None = None
    homepage_url: str | None = None
    careers_url: str | None = None


class SourceCreate(BaseModel):
    url: HttpUrl | str
    source_type: str = Field(..., pattern="^(pricing|homepage|careers|news)$")
    use_unlocker: bool = False
    label: str | None = None


class CompetitorOut(BaseModel):
    id: int
    name: str
    domain: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    id: int
    competitor_id: int
    url: str
    source_type: str
    use_unlocker: bool
    label: str | None

    model_config = {"from_attributes": True}


class SnapshotOut(BaseModel):
    id: int
    competitor_id: int
    source_id: int
    content_hash: str
    extracted: dict[str, Any]
    raw_preview: str | None
    collector: str
    captured_at: datetime

    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    id: int
    competitor_id: int
    competitor_name: str | None = None
    source_id: int | None
    origin: str = "pipeline"
    agent_run_id: int | None = None
    event_type: str
    severity: str
    title: str
    diff_summary: str
    evidence_url: str
    before_snapshot_id: int | None
    after_snapshot_id: int | None
    detected_at: datetime

    model_config = {"from_attributes": True}


class CollectRunOut(BaseModel):
    competitor_id: int
    sources_processed: int
    snapshots_created: int
    events_created: int
    errors: list[str] = []


class DailyBriefOut(BaseModel):
    generated_at: datetime
    event_count: int
    high_severity_count: int
    events: list[EventOut]
    summary: str
