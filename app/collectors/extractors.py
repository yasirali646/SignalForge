"""Normalize raw HTML/markdown into structured competitive signals."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from bs4 import BeautifulSoup


def content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def extract_from_html(html: str, source_type: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)[:8000]

    title = (soup.title.string or "").strip() if soup.title else ""
    h1 = soup.find("h1")
    headline = h1.get_text(strip=True) if h1 else title

    pricing_snippets = _find_pricing_snippets(soup)
    job_mentions = _count_job_signals(text)

    base: dict[str, Any] = {
        "url": url,
        "source_type": source_type,
        "page_title": title,
        "headline": headline,
        "text_length": len(text),
        "text_sample": text[:1500],
    }

    if source_type == "pricing":
        base["pricing_snippets"] = pricing_snippets
        base["price_tokens"] = _extract_price_tokens(text)
    elif source_type == "homepage":
        base["hero_headline"] = headline
        base["meta_description"] = _meta_description(soup)
    elif source_type == "careers":
        base["job_count_estimate"] = job_mentions
        base["job_keywords"] = _job_keywords_found(text)
    elif source_type == "news":
        base["headline"] = headline

    return base


def parse_mcp_serp_text(raw: str) -> dict[str, Any]:
    """Normalize MCP search_engine text/JSON into organic results list."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "organic" in data:
            return data
    except json.JSONDecodeError:
        pass

    items = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("http"):
            items.append(
                {
                    "title": line[:120],
                    "link": line.split()[0],
                    "description": "",
                }
            )
    return {
        "organic": items[:10],
        "general": {"query": "", "demo_mode": False, "source": "mcp"},
    }


def extract_from_serp(serp: dict[str, Any], competitor_name: str) -> dict[str, Any]:
    organic = serp.get("organic") or []
    items = []
    for row in organic[:8]:
        if isinstance(row, dict):
            items.append(
                {
                    "title": row.get("title", ""),
                    "link": row.get("link", ""),
                    "description": row.get("description", ""),
                }
            )
    return {
        "source_type": "news",
        "competitor": competitor_name,
        "news_items": items,
        "item_count": len(items),
        "query": (serp.get("general") or {}).get("query", competitor_name),
    }


def _meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return str(tag["content"])[:500]
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return str(og["content"])[:500]
    return ""


def _find_pricing_snippets(soup: BeautifulSoup) -> list[str]:
    patterns = re.compile(
        r"\$[\d,]+(?:\.\d{2})?|\d+%\s*off|per\s+month|/mo|enterprise|professional|starter",
        re.I,
    )
    snippets: list[str] = []
    for el in soup.find_all(string=patterns):
        parent = el.parent
        if parent:
            snippet = parent.get_text(" ", strip=True)
            if 10 < len(snippet) < 200 and snippet not in snippets:
                snippets.append(snippet)
        if len(snippets) >= 12:
            break
    return snippets


def _extract_price_tokens(text: str) -> list[str]:
    return sorted(set(re.findall(r"\$[\d,]+(?:\.\d{2})?", text)))[:20]


def _count_job_signals(text: str) -> int:
    keywords = [
        "sales",
        "account executive",
        "sdr",
        "bdr",
        "marketing",
        "revops",
        "customer success",
        "engineer",
    ]
    lower = text.lower()
    return sum(lower.count(kw) for kw in keywords)


def _job_keywords_found(text: str) -> list[str]:
    keywords = [
        "sales",
        "account executive",
        "sdr",
        "bdr",
        "marketing",
        "revops",
        "customer success",
    ]
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]
