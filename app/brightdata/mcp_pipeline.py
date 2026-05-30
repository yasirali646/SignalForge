"""Use Bright Data MCP tools for pipeline collection when REST zones are unavailable."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Coroutine, TypeVar

from app.agents.mcp_tools import mcp_invoke
from app.config import get_settings

T = TypeVar("T")


def mcp_available() -> bool:
    return bool(get_settings().resolved_mcp_url())


def _run_async(coro: Coroutine[object, object, T]) -> T:
    """
    Run an MCP coroutine from sync code.

    Uses asyncio.run when no loop is active; otherwise runs in a worker thread
    so post-agent collection works from FastAPI async handlers.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def mcp_search_sync(query: str) -> str:
    return _run_async(
        mcp_invoke("search_engine", {"query": query, "engine": "google"})
    )


def mcp_scrape_sync(url: str) -> str:
    return _run_async(mcp_invoke("scrape_as_markdown", {"url": url}))
