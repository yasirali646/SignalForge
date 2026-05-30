"""Orchestrate collection, snapshot storage, and diff-based events."""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brightdata.client import BrightDataClient, BrightDataError, LocalCollector
from app.brightdata.mcp_pipeline import mcp_available, mcp_scrape_sync, mcp_search_sync
from app.collectors.extractors import (
    content_hash,
    extract_from_html,
    extract_from_serp,
    parse_mcp_serp_text,
)
from app.config import get_settings
from app.diff.engine import diff_snapshots, parse_snapshot_json
from app.models import Competitor, Event, Snapshot, Source
from app.services.alerts import evaluate_alerts_for_event

logger = logging.getLogger(__name__)


def _get_collector():
    settings = get_settings()
    if settings.collector_mode == "local":
        return LocalCollector(), "local"
    if settings.brightdata_api_token.strip():
        return BrightDataClient(), "brightdata"
    if mcp_available():
        return None, "brightdata_mcp"
    return LocalCollector(), "local"


def collect_competitor(db: Session, competitor_id: int) -> dict:
    competitor = db.get(Competitor, competitor_id)
    if not competitor:
        raise ValueError(f"Competitor {competitor_id} not found")

    collector, mode = _get_collector()
    sources = db.scalars(
        select(Source).where(Source.competitor_id == competitor_id)
    ).all()

    stats = {
        "competitor_id": competitor_id,
        "sources_processed": 0,
        "snapshots_created": 0,
        "events_created": 0,
        "errors": [],
    }

    for source in sources:
        try:
            created, events = _collect_source(
                db, competitor, source, collector, mode
            )
            stats["sources_processed"] += 1
            stats["snapshots_created"] += created
            stats["events_created"] += events
        except Exception as exc:  # noqa: BLE001
            msg = f"{source.label or source.source_type}: {exc}"
            logger.warning("Collection skipped for %s — %s", source.url, exc)
            stats["errors"].append(msg)

    db.commit()
    return stats


def collect_all(db: Session) -> list[dict]:
    ids = db.scalars(select(Competitor.id)).all()
    return [collect_competitor(db, cid) for cid in ids]


def _collect_source(
    db: Session,
    competitor: Competitor,
    source: Source,
    collector,
    mode: str,
) -> tuple[int, int]:
    if source.source_type == "news":
        extracted, raw_preview, collector_name = _collect_news(
            collector, competitor.name, mode
        )
        evidence_url = extracted.get("news_items", [{}])[0].get("link", source.url)
    else:
        extracted, raw_preview, collector_name = _collect_page(
            collector, source.url, source.source_type, source.use_unlocker, mode
        )
        evidence_url = source.url

    new_hash = content_hash(extracted)
    previous = db.scalars(
        select(Snapshot)
        .where(
            Snapshot.source_id == source.id,
            Snapshot.competitor_id == competitor.id,
        )
        .order_by(Snapshot.captured_at.desc())
        .limit(1)
    ).first()

    if previous and previous.content_hash == new_hash:
        return 0, 0

    snapshot = Snapshot(
        competitor_id=competitor.id,
        source_id=source.id,
        content_hash=new_hash,
        extracted_json=json.dumps(extracted),
        raw_preview=(raw_preview or "")[:4000] or None,
        collector=f"{collector_name}:{mode}",
    )
    db.add(snapshot)
    db.flush()

    events_created = 0
    if previous:
        before = parse_snapshot_json(previous.extracted_json)
        for evt in diff_snapshots(
            before,
            extracted,
            source_type=source.source_type,
            evidence_url=str(evidence_url),
        ):
            row = Event(
                competitor_id=competitor.id,
                source_id=source.id,
                origin="pipeline",
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
            evaluate_alerts_for_event(db, row)
            events_created += 1

    return 1, events_created


def _collect_page(
    collector, url: str, source_type: str, use_unlocker: bool, mode: str
):
    if url.startswith("serp://"):
        raise ValueError("invalid page url")

    html = None
    collector_name = "unknown"

    if collector is not None and isinstance(collector, BrightDataClient):
        try:
            html, collector_name = collector.scrape_page(url, use_unlocker=use_unlocker)
        except (BrightDataError, Exception) as exc:
            logger.debug("REST scrape failed for %s: %s", url, exc)

    if html is None and mcp_available():
        try:
            html = mcp_scrape_sync(url)
            collector_name = "brightdata_mcp_scraper"
        except Exception as exc:
            logger.debug("MCP scrape failed for %s: %s", url, exc)

    if html is None:
        local = LocalCollector()
        html, collector_name = local.scrape_page(url, use_unlocker=use_unlocker)

    extracted = extract_from_html(html, source_type, url)
    return extracted, html[:2000], collector_name


def _collect_news(collector, competitor_name: str, mode: str):
    query = f"{competitor_name} product launch OR funding OR partnership"
    serp_data = None
    collector_name = "local_serp_demo"

    if collector is not None and isinstance(collector, BrightDataClient):
        try:
            serp_data = collector.serp_search(query)
            collector_name = "brightdata_serp"
        except (BrightDataError, Exception) as exc:
            logger.debug("REST SERP failed: %s", exc)

    if serp_data is None and mcp_available():
        try:
            raw = mcp_search_sync(query)
            serp_data = parse_mcp_serp_text(raw)
            collector_name = "brightdata_mcp_serp"
        except Exception as exc:
            logger.debug("MCP SERP failed: %s", exc)

    if serp_data is None:
        serp_data = LocalCollector().serp_search(query)
        collector_name = "local_serp_demo"

    extracted = extract_from_serp(serp_data, competitor_name)
    preview = json.dumps(extracted.get("news_items", [])[:3], indent=2)
    return extracted, preview, collector_name
