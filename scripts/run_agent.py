#!/usr/bin/env python3
"""CLI test for Forge Scout (Bright Data MCP + LangGraph)."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.forge_agent import list_mcp_tools, run_forge_agent
from app.config import get_settings


async def main() -> None:
    s = get_settings()
    if not s.agent_configured():
        print("Configure BRIGHTDATA_MCP or BRIGHTDATA_API_TOKEN in .env")
        sys.exit(1)

    print("Loading MCP tools...")
    tools = await list_mcp_tools()
    print(f"Tools ({len(tools)}):", ", ".join(tools[:8]), "...")

    query = " ".join(sys.argv[1:]) or (
        "Search for latest Bright Data product news and summarize competitive implications."
    )
    print("\nQuery:", query)
    print("-" * 50)
    result = await run_forge_agent(query)
    if result.get("message_count"):
        print(f"(messages in trace: {result['message_count']})")
    print(result["reply"])


if __name__ == "__main__":
    asyncio.run(main())
