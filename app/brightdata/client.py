"""Bright Data REST client (SERP API, Web Scraper / Unlocker zones)."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class BrightDataError(Exception):
    pass


class BrightDataClient:
    """Unified client for POST https://api.brightdata.com/request."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._token = self.settings.brightdata_api_token.strip()

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise BrightDataError(
                "BRIGHTDATA_API_TOKEN is not set. Configure .env or use COLLECTOR_MODE=local."
            )
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def request(
        self,
        *,
        zone: str,
        url: str,
        format: str = "raw",
        data_format: str | None = "markdown",
        method: str = "GET",
        country: str = "us",
    ) -> str:
        payload: dict[str, Any] = {
            "zone": zone,
            "url": url,
            "format": format,
            "method": method,
            "country": country,
        }
        if data_format:
            payload["data_format"] = data_format

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                self.settings.brightdata_request_url,
                headers=self._headers(),
                json=payload,
            )
        if response.status_code >= 400:
            raise BrightDataError(
                f"Bright Data request failed ({response.status_code}): {response.text[:500]}"
            )
        return response.text

    def serp_search(self, query: str, num_results: int = 10) -> dict[str, Any]:
        """SERP API via Google search URL with brd_json=1."""
        encoded = quote_plus(query)
        url = (
            f"https://www.google.com/search?q={encoded}"
            f"&num={num_results}&hl=en&gl=us&brd_json=1"
        )
        raw = self.request(
            zone=self.settings.brightdata_serp_zone,
            url=url,
            format="raw",
            data_format=None,
        )
        return self._parse_json_response(raw)

    def scrape_page(
        self,
        url: str,
        *,
        use_unlocker: bool = False,
    ) -> tuple[str, str]:
        """Web Scraper API zone, or Web Unlocker for JS-heavy pages."""
        zone = (
            self.settings.brightdata_unlocker_zone
            if use_unlocker
            else self.settings.brightdata_scraper_zone
        )
        collector = "brightdata_unlocker" if use_unlocker else "brightdata_scraper"
        content = self.request(
            zone=zone,
            url=url,
            format="raw",
            data_format="markdown",
        )
        return content, collector

    @staticmethod
    def _parse_json_response(raw: str) -> dict[str, Any]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BrightDataError(f"Invalid JSON from Bright Data: {raw[:200]}") from exc
        if isinstance(data, dict) and "body" in data:
            body = data["body"]
            if isinstance(body, str):
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return {"raw": body}
            return body if isinstance(body, dict) else {"raw": body}
        return data if isinstance(data, dict) else {"raw": raw}


class LocalCollector:
    """Fallback when API token is absent — direct HTTP for local demos."""

    FIXTURE_MAP = {
        "pricing": "pricing_sample.html",
        "homepage": "homepage_sample.html",
        "careers": "careers_sample.html",
    }

    def scrape_page(self, url: str, *, use_unlocker: bool = False) -> tuple[str, str]:
        collector = "local_unlocker_sim" if use_unlocker else "local_http"
        try:
            with httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "SignalForge/1.0"},
            ) as client:
                response = client.get(url)
            if response.status_code >= 400:
                raise BrightDataError(f"HTTP {response.status_code}")
            return response.text, collector
        except Exception as exc:
            settings = get_settings()
            if not settings.demo_use_fixtures:
                raise BrightDataError(f"Local fetch failed: {url}") from exc
            html = self._load_fixture(url)
            return html, f"{collector}_fixture"

    def _load_fixture(self, url: str) -> str:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "fixtures"
        for key, filename in self.FIXTURE_MAP.items():
            if key in url.lower() or key in url:
                path = root / filename
                if path.exists():
                    return path.read_text(encoding="utf-8")
        return (root / "homepage_sample.html").read_text(encoding="utf-8")

    def serp_search(self, query: str, num_results: int = 10) -> dict[str, Any]:
        # Minimal synthetic SERP for offline demo
        return {
            "organic": [
                {
                    "title": f"[Demo] News about {query}",
                    "link": f"https://news.google.com/search?q={quote_plus(query)}",
                    "description": "Enable BRIGHTDATA_API_TOKEN for live SERP results.",
                    "rank": 1,
                }
            ],
            "general": {"query": query, "demo_mode": True},
        }
