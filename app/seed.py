"""Seed demo competitors with monitor sources."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competitor, Source

SEED_COMPETITORS = [
    {
        "name": "Bright Data",
        "domain": "brightdata.com",
        "sources": [
            {
                "url": "https://brightdata.com/pricing",
                "source_type": "pricing",
                "use_unlocker": True,
                "label": "Pricing (Unlocker)",
            },
            {
                "url": "https://brightdata.com/",
                "source_type": "homepage",
                "use_unlocker": False,
                "label": "Homepage",
            },
            {
                "url": "https://brightdata.com/careers",
                "source_type": "careers",
                "use_unlocker": False,
                "label": "Careers",
            },
            {"url": "news://serp", "source_type": "news", "use_unlocker": False, "label": "SERP News"},
        ],
    },
    {
        "name": "Oxylabs",
        "domain": "oxylabs.io",
        "sources": [
            {
                "url": "https://oxylabs.io/pricing",
                "source_type": "pricing",
                "use_unlocker": True,
                "label": "Pricing (Unlocker)",
            },
            {
                "url": "https://oxylabs.io/",
                "source_type": "homepage",
                "use_unlocker": False,
                "label": "Homepage",
            },
            {
                "url": "https://oxylabs.io/careers",
                "source_type": "careers",
                "use_unlocker": False,
                "label": "Careers",
            },
            {"url": "news://serp", "source_type": "news", "use_unlocker": False, "label": "SERP News"},
        ],
    },
    {
        "name": "Zyte",
        "domain": "zyte.com",
        "sources": [
            {
                "url": "https://www.zyte.com/pricing",
                "source_type": "pricing",
                "use_unlocker": True,
                "label": "Pricing (Unlocker)",
            },
            {
                "url": "https://www.zyte.com/",
                "source_type": "homepage",
                "use_unlocker": False,
                "label": "Homepage",
            },
            {
                "url": "https://www.zyte.com/jobs",
                "source_type": "careers",
                "use_unlocker": False,
                "label": "Careers",
            },
            {"url": "news://serp", "source_type": "news", "use_unlocker": False, "label": "SERP News"},
        ],
    },
]


def seed_competitors(db: Session) -> int:
    created = 0
    for item in SEED_COMPETITORS:
        domain = item["domain"]
        existing = db.scalar(select(Competitor).where(Competitor.domain == domain))
        if existing:
            competitor = existing
        else:
            competitor = Competitor(name=item["name"], domain=domain)
            db.add(competitor)
            db.flush()
            created += 1

        for src in item["sources"]:
            url = src["url"]
            if url == "news://serp":
                url = f"serp://{competitor.name}/news"
            exists = db.scalar(
                select(Source).where(
                    Source.competitor_id == competitor.id,
                    Source.source_type == src["source_type"],
                )
            )
            if exists:
                continue
            db.add(
                Source(
                    competitor_id=competitor.id,
                    url=url,
                    source_type=src["source_type"],
                    use_unlocker=src.get("use_unlocker", False),
                    label=src.get("label"),
                )
            )
    db.commit()
    return created
