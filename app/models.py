import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SourceType(str, enum.Enum):
    PRICING = "pricing"
    HOMEPAGE = "homepage"
    CAREERS = "careers"
    NEWS = "news"


class EventType(str, enum.Enum):
    PRICING_CHANGE = "pricing_change"
    MESSAGING_CHANGE = "messaging_change"
    HIRING_CHANGE = "hiring_change"
    NEWS_SIGNAL = "news_signal"
    AGENT_INTEL = "agent_intel"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sources: Mapped[list["Source"]] = relationship(back_populates="competitor")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="competitor")
    events: Mapped[list["Event"]] = relationship(back_populates="competitor")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="competitor")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    use_unlocker: Mapped[bool] = mapped_column(default=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)

    competitor: Mapped["Competitor"] = relationship(back_populates="sources")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="source")


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    extracted_json: Mapped[str] = mapped_column(Text)
    raw_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    collector: Mapped[str] = mapped_column(String(64))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    competitor: Mapped["Competitor"] = relationship(back_populates="snapshots")
    source: Mapped["Source"] = relationship(back_populates="snapshots")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitors.id"), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(Text)
    reply_md: Mapped[str] = mapped_column(Text)
    tools_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    events_created: Mapped[int] = mapped_column(Integer, default=0)
    collection_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    competitor: Mapped["Competitor | None"] = relationship(back_populates="agent_runs")
    events: Mapped[list["Event"]] = relationship(back_populates="agent_run")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    agent_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=True, index=True
    )
    origin: Mapped[str] = mapped_column(String(16), default="pipeline", index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(512))
    diff_summary: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str] = mapped_column(String(1024))
    before_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("snapshots.id"), nullable=True
    )
    after_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("snapshots.id"), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    competitor: Mapped["Competitor"] = relationship(back_populates="events")
    agent_run: Mapped["AgentRun | None"] = relationship(back_populates="events")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    event_types: Mapped[str] = mapped_column(String(256), default="")
    min_severity: Mapped[str] = mapped_column(String(16), default="medium")
    competitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitors.id"), nullable=True, index=True
    )
    webhook_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DemoQuota(Base):
    __tablename__ = "demo_quotas"

    username: Mapped[str] = mapped_column(String(128), primary_key=True)
    agent_requests_used: Mapped[int] = mapped_column(Integer, default=0)


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
