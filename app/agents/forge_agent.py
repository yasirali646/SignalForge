"""Forge Scout agent: Bright Data MCP + LangGraph (no external LLM)."""

from __future__ import annotations

from typing import Any

from app.agents.brightdata_agent import (  # noqa: F401
    research_competitor,
    run_brightdata_agent,
    stream_brightdata_agent,
)

__all__ = [
    "AgentNotConfiguredError",
    "list_mcp_tools",
    "run_forge_agent",
    "stream_forge_agent",
    "research_competitor",
]
from app.agents.mcp_tools import list_tool_names
from app.config import get_settings


class AgentNotConfiguredError(Exception):
    pass


def _ensure_configured() -> None:
    if not get_settings().agent_configured():
        raise AgentNotConfiguredError(
            "Set BRIGHTDATA_MCP or BRIGHTDATA_API_TOKEN for the Bright Data agent."
        )


async def list_mcp_tools() -> list[str]:
    _ensure_configured()
    return await list_tool_names()


async def run_forge_agent(
    user_message: str,
    *,
    system_extra: str = "",
) -> dict[str, Any]:
    _ensure_configured()
    return await run_brightdata_agent(user_message, system_extra=system_extra)


async def stream_forge_agent(
    user_message: str,
    *,
    system_extra: str = "",
):
    _ensure_configured()
    async for chunk in stream_brightdata_agent(user_message, system_extra=system_extra):
        yield chunk
