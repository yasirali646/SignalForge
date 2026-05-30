"""Compare snapshots and emit structured change events."""

from __future__ import annotations

import json
from typing import Any

from app.models import EventType, Severity, SourceType


def diff_snapshots(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    source_type: str,
    evidence_url: str,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    if source_type == SourceType.PRICING.value:
        events.extend(_diff_pricing(before, after, evidence_url))
    elif source_type == SourceType.HOMEPAGE.value:
        events.extend(_diff_messaging(before, after, evidence_url))
    elif source_type == SourceType.CAREERS.value:
        events.extend(_diff_hiring(before, after, evidence_url))
    elif source_type == SourceType.NEWS.value:
        events.extend(_diff_news(before, after, evidence_url))

    return events


def _diff_pricing(
    before: dict[str, Any], after: dict[str, Any], url: str
) -> list[dict[str, Any]]:
    b_prices = set(before.get("price_tokens") or [])
    a_prices = set(after.get("price_tokens") or [])
    if b_prices == a_prices and before.get("pricing_snippets") == after.get(
        "pricing_snippets"
    ):
        return []

    added = sorted(a_prices - b_prices)
    removed = sorted(b_prices - a_prices)
    summary_parts = []
    if added:
        summary_parts.append(f"New price points: {', '.join(added)}")
    if removed:
        summary_parts.append(f"Removed price points: {', '.join(removed)}")
    if not summary_parts:
        summary_parts.append("Pricing page layout or plan copy changed.")

    severity = Severity.HIGH.value if added or removed else Severity.MEDIUM.value
    return [
        {
            "event_type": EventType.PRICING_CHANGE.value,
            "severity": severity,
            "title": "Competitor pricing page changed",
            "diff_summary": "; ".join(summary_parts),
            "evidence_url": url,
        }
    ]


def _diff_messaging(
    before: dict[str, Any], after: dict[str, Any], url: str
) -> list[dict[str, Any]]:
    b_head = (before.get("hero_headline") or before.get("headline") or "").strip()
    a_head = (after.get("hero_headline") or after.get("headline") or "").strip()
    b_meta = (before.get("meta_description") or "").strip()
    a_meta = (after.get("meta_description") or "").strip()

    if b_head == a_head and b_meta == a_meta:
        return []

    parts = []
    if b_head != a_head:
        parts.append(f"Headline: '{b_head}' → '{a_head}'")
    if b_meta != a_meta:
        parts.append("Meta description updated.")

    return [
        {
            "event_type": EventType.MESSAGING_CHANGE.value,
            "severity": Severity.MEDIUM.value,
            "title": "Homepage messaging shift detected",
            "diff_summary": " ".join(parts),
            "evidence_url": url,
        }
    ]


def _diff_hiring(
    before: dict[str, Any], after: dict[str, Any], url: str
) -> list[dict[str, Any]]:
    b_count = int(before.get("job_count_estimate") or 0)
    a_count = int(after.get("job_count_estimate") or 0)
    b_kw = set(before.get("job_keywords") or [])
    a_kw = set(after.get("job_keywords") or [])
    delta = a_count - b_count
    new_roles = sorted(a_kw - b_kw)

    if delta == 0 and not new_roles and b_count == a_count:
        return []

    severity = Severity.HIGH.value if delta >= 3 or new_roles else Severity.MEDIUM.value
    summary = f"Hiring signal delta: {delta:+d} keyword hits."
    if new_roles:
        summary += f" New role families: {', '.join(new_roles)}."

    return [
        {
            "event_type": EventType.HIRING_CHANGE.value,
            "severity": severity,
            "title": "Careers / hiring footprint changed",
            "diff_summary": summary,
            "evidence_url": url,
        }
    ]


def _diff_news(
    before: dict[str, Any], after: dict[str, Any], url: str
) -> list[dict[str, Any]]:
    b_links = {item.get("link") for item in (before.get("news_items") or [])}
    a_items = after.get("news_items") or []
    new_items = [i for i in a_items if i.get("link") not in b_links]
    if not new_items and before.get("item_count") == after.get("item_count"):
        return []

    titles = [i.get("title", "")[:80] for i in new_items[:3]]
    return [
        {
            "event_type": EventType.NEWS_SIGNAL.value,
            "severity": Severity.LOW.value if len(new_items) < 2 else Severity.MEDIUM.value,
            "title": f"{len(new_items)} new news SERP result(s)",
            "diff_summary": "Recent headlines: " + "; ".join(titles) if titles else "News index refreshed.",
            "evidence_url": new_items[0].get("link", url) if new_items else url,
        }
    ]


def parse_snapshot_json(raw: str) -> dict[str, Any]:
    return json.loads(raw)
