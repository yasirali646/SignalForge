"""Bright Data MCP client helpers for LangChain tool invocation."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import get_settings

logger = logging.getLogger(__name__)

_TOOL_CACHE: dict[str, Any] = {}


def mcp_client_config() -> dict[str, dict[str, str]]:
    url = get_settings().resolved_mcp_url()
    if not url:
        raise RuntimeError("BRIGHTDATA_MCP or BRIGHTDATA_API_TOKEN not configured")
    return {"bright_data": {"url": url, "transport": "sse"}}


async def get_mcp_tools():
    """
    Fetch available MCP tools from Bright Data.

    We aggressively normalize ExceptionGroup/TaskGroup failures into a readable
    message so the UI can show a useful error (token/config/connectivity).
    """
    try:
        client = MultiServerMCPClient(mcp_client_config())
        return await client.get_tools()
    except Exception as exc:
        # Python 3.11+ sometimes wraps connection failures as ExceptionGroup
        # with an unhelpful "unhandled errors in a TaskGroup" message.
        msg = str(exc)
        if getattr(exc, "exceptions", None):
            try:
                parts = []
                for inner in exc.exceptions:  # type: ignore[attr-defined]
                    parts.append(str(inner))
                msg = "; ".join(p for p in parts if p) or msg
            except Exception:
                pass
        url = ""
        try:
            url = get_settings().resolved_mcp_url()
        except Exception:
            url = ""
        hint = (
            "Unable to connect to Bright Data MCP. "
            "Check BRIGHTDATA_MCP / BRIGHTDATA_API_TOKEN, network access, and token limits."
        )
        preview = ""
        if url:
            preview = url.split("token=")[0] + "token=***" if "token=" in url else url[:80]
        raise RuntimeError(f"{hint} ({msg}) {preview}".strip()) from exc


async def list_tool_names() -> list[str]:
    tools = await get_mcp_tools()
    return sorted(t.name for t in tools)


async def _get_tool(name: str):
    if name in _TOOL_CACHE:
        return _TOOL_CACHE[name]
    tools = await get_mcp_tools()
    for tool in tools:
        _TOOL_CACHE[tool.name] = tool
    if name not in _TOOL_CACHE:
        raise RuntimeError(f"MCP tool '{name}' not found")
    return _TOOL_CACHE[name]


def tool_result_to_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts = []
        for block in result:
            if isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    if isinstance(result, dict):
        return json.dumps(result)
    return str(result)


async def mcp_invoke(tool_name: str, payload: dict[str, Any]) -> str:
    tool = await _get_tool(tool_name)
    try:
        result = await tool.ainvoke(payload)
    except TypeError:
        result = await tool.ainvoke({k: v for k, v in payload.items() if v is not None})
    return tool_result_to_text(result)
