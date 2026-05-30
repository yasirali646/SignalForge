"""Connect Forge Scout research output to the SignalForge event pipeline."""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy.orm import Session

from app.collectors.runner import collect_competitor
from app.models import AgentRun, Competitor, Event, EventType, Severity
from app.services.alerts import evaluate_alerts_for_event

logger = logging.getLogger(__name__)


def _extract_first_url(text: str, domain: str) -> str:
    urls = re.findall(r"https?://[^\s\)\]>]+", text)
    for u in urls:
        if domain.replace("www.", "") in u:
            return u.rstrip(".,;")
    return f"https://{domain}"


_LC_BLOCK_RE = re.compile(
    r"\{'type':\s*'text'[^}]*\}|\{\"type\":\s*\"text\"[^}]*\}",
    re.IGNORECASE,
)


def _clean_reply_markdown(reply: str) -> str:
    """Strip LangChain message artifacts so feed markdown renders cleanly."""
    text = reply.strip()
    text = _LC_BLOCK_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _brief_excerpt(reply: str, max_len: int = 4000) -> str:
    text = _clean_reply_markdown(reply)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def persist_agent_run(
    db: Session,
    *,
    competitor_id: int | None,
    query: str,
    reply: str,
    tools_available: list[str],
    events_created: int = 0,
    collection_triggered: bool = False,
) -> AgentRun:
    run = AgentRun(
        competitor_id=competitor_id,
        query=query,
        reply_md=reply,
        tools_used=json.dumps(tools_available),
        events_created=events_created,
        collection_triggered=collection_triggered,
    )
    db.add(run)
    db.flush()
    return run


def create_intel_event_from_agent(
    db: Session,
    *,
    competitor_id: int,
    agent_run_id: int,
    reply: str,
    domain: str,
) -> Event:
    """Push agent brief into the change event feed as structured agent intel."""
    title_match = re.search(r"^#+\s*(.+)$", reply, re.MULTILINE)
    title = (
        title_match.group(1).strip()[:200]
        if title_match
        else "Agent competitive intelligence brief"
    )
    event = Event(
        competitor_id=competitor_id,
        agent_run_id=agent_run_id,
        origin="agent",
        event_type=EventType.AGENT_INTEL.value,
        severity=Severity.MEDIUM.value,
        title=title,
        diff_summary=_brief_excerpt(reply),
        evidence_url=_extract_first_url(reply, domain),
    )
    db.add(event)
    db.flush()
    evaluate_alerts_for_event(db, event)
    return event


def connect_agent_to_pipeline(
    db: Session,
    *,
    competitor_id: int | None,
    query: str,
    reply: str,
    tools_available: list[str],
    trigger_collection: bool = True,
) -> dict:
    """
    Persist agent run, create feed event, optionally refresh pipeline snapshots.
    """
    events_created = 0
    collection_triggered = False
    collection_stats = None

    run = persist_agent_run(
        db,
        competitor_id=competitor_id,
        query=query,
        reply=reply,
        tools_available=tools_available,
    )

    if competitor_id:
        comp = db.get(Competitor, competitor_id)
        if comp:
            create_intel_event_from_agent(
                db,
                competitor_id=competitor_id,
                agent_run_id=run.id,
                reply=reply,
                domain=comp.domain,
            )
            events_created = 1
            run.events_created = 1

            if trigger_collection:
                try:
                    collection_stats = collect_competitor(db, competitor_id)
                    collection_triggered = True
                    run.collection_triggered = True
                    pipeline_events = collection_stats.get("events_created", 0)
                    events_created += pipeline_events
                    logger.info(
                        "Post-agent collection for %s: %s",
                        comp.name,
                        collection_stats,
                    )
                except Exception as exc:
                    logger.warning("Post-agent collection failed: %s", exc)

    db.commit()
    db.refresh(run)

    return {
        "agent_run_id": run.id,
        "events_created": events_created,
        "collection_triggered": collection_triggered,
        "collection_stats": collection_stats,
    }
