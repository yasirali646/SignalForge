"""
Bright Data web agent via LangGraph + MCP (no external LLM).

Orchestrates search_engine and scrape_as_markdown per
https://docs.brightdata.com/ai/agents and LangChain MCP integration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.mcp_tools import get_mcp_tools, mcp_invoke
from app.agents.prompts import RESEARCH_COMPETITOR_TEMPLATE
from app.collectors.extractors import parse_mcp_serp_text

logger = logging.getLogger(__name__)

MAX_SEARCHES = 4
MAX_SCRAPES = 4


class AgentState(TypedDict, total=False):
    user_message: str
    system_extra: str
    queries: list[str]
    search_hits: list[dict[str, Any]]
    scrape_hits: list[dict[str, Any]]
    reply: str
    tools_available: list[str]
    tools_used: list[str]
    error: str | None


def _parse_serp(raw: str, query: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        data = json.loads(raw)
        organic = data.get("organic") or data.get("results") or []
        if isinstance(organic, list):
            for row in organic[:8]:
                if isinstance(row, dict):
                    link = row.get("link") or row.get("url") or ""
                    items.append(
                        {
                            "query": query,
                            "title": row.get("title", ""),
                            "link": link,
                            "description": row.get("description") or row.get("snippet", ""),
                        }
                    )
            if items:
                return items
    except json.JSONDecodeError:
        pass

    parsed = parse_mcp_serp_text(raw)
    for row in parsed.get("organic", [])[:8]:
        items.append(
            {
                "query": query,
                "title": row.get("title", ""),
                "link": row.get("link", ""),
                "description": row.get("description", ""),
            }
        )
    return items


def _urls_from_message(text: str) -> list[str]:
    return re.findall(r"https?://[^\s\])>\"']+", text)[:5]


def _pick_scrape_urls(
    search_hits: list[dict[str, Any]],
    extra_urls: list[str],
    domain_hint: str | None,
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(url: str) -> None:
        u = url.rstrip("/")
        if not u.startswith("http") or u in seen:
            return
        seen.add(u)
        ordered.append(u)

    for u in extra_urls:
        add(u)

    if domain_hint:
        base = domain_hint if domain_hint.startswith("http") else f"https://{domain_hint}"
        add(base)
        add(f"{base.rstrip('/')}/pricing")

    for hit in search_hits:
        add(hit.get("link", ""))

    return ordered[:MAX_SCRAPES]


def _plan_queries(state: AgentState) -> AgentState:
    msg = (state.get("user_message") or "").strip()
    extra = (state.get("system_extra") or "").strip()
    queries: list[str] = [msg] if msg else []

    domain = None
    name = None
    if extra:
        m_dom = re.search(r"\(([^)]+)\)", extra)
        m_name = re.search(r"competitor:\s*([^(]+)", extra, re.I)
        if m_name:
            name = m_name.group(1).strip()
        if m_dom:
            domain = m_dom.group(1).strip()

    if name and domain and "Research this competitor" in msg:
        queries = [
            f"{name} product launch OR funding OR partnership news",
            f"{name} pricing plans site:{domain}",
            f"{name} careers sales SDR marketing hiring",
            f"{name} homepage positioning messaging",
        ]
    elif name:
        queries.append(f"{name} competitive intelligence news pricing")
    elif domain:
        queries.append(f"site:{domain} pricing OR plans")

    deduped: list[str] = []
    seen_q: set[str] = set()
    for q in queries:
        q = q.strip()
        if q and q.lower() not in seen_q:
            seen_q.add(q.lower())
            deduped.append(q)

    return {**state, "queries": deduped[:MAX_SEARCHES]}


async def _run_searches(state: AgentState) -> AgentState:
    hits: list[dict[str, Any]] = []
    used = list(state.get("tools_used") or [])
    for query in state.get("queries") or []:
        try:
            raw = await mcp_invoke("search_engine", {"query": query, "engine": "google"})
            hits.extend(_parse_serp(raw, query))
            if "search_engine" not in used:
                used.append("search_engine")
        except Exception as exc:
            logger.warning("search_engine failed for %r: %s", query, exc)
    return {**state, "search_hits": hits, "tools_used": used}


async def _run_scrapes(state: AgentState) -> AgentState:
    extra = _urls_from_message(state.get("user_message", ""))
    domain = None
    extra_sys = state.get("system_extra") or ""
    m = re.search(r"\(([^)]+)\)", extra_sys)
    if m:
        domain = m.group(1).strip()

    urls = _pick_scrape_urls(state.get("search_hits") or [], extra, domain)
    scrapes: list[dict[str, Any]] = []
    used = list(state.get("tools_used") or [])

    for url in urls:
        try:
            md = await mcp_invoke("scrape_as_markdown", {"url": url})
            scrapes.append({"url": url, "content": md[:6000]})
            if "scrape_as_markdown" not in used:
                used.append("scrape_as_markdown")
        except Exception as exc:
            logger.debug("scrape failed %s: %s", url, exc)

    return {**state, "scrape_hits": scrapes, "tools_used": used}


def _compile_brief(state: AgentState) -> AgentState:
    msg = state.get("user_message", "")
    searches = state.get("search_hits") or []
    scrapes = state.get("scrape_hits") or []
    tools_used = state.get("tools_used") or []

    lines = [
        "## Executive summary",
        _executive_summary(msg, searches, scrapes),
        "",
        "## Signals detected",
    ]

    pricing = _pricing_signals(scrapes, searches)
    lines.append(f"- **Pricing:** {pricing}")

    news = _news_signals(searches)
    lines.append(f"- **News / launches:** {news}")

    hiring = _hiring_signals(scrapes, searches)
    lines.append(f"- **Hiring:** {hiring}")

    messaging = _messaging_signals(scrapes)
    lines.append(f"- **Messaging:** {messaging}")

    lines.extend(["", "## Recommended actions", *_recommended_actions(searches, scrapes)])

    lines.extend(["", "## Evidence links"])
    links = _evidence_links(searches, scrapes)
    if links:
        lines.extend(f"- {u}" for u in links)
    else:
        lines.append("- No live URLs captured — retry with a competitor focus or specific URL.")

    lines.extend(
        [
            "",
            "---",
            f"*Powered by Bright Data MCP ({', '.join(tools_used) or 'search + scrape'}) — "
            "no third-party LLM.*",
        ]
    )

    return {**state, "reply": "\n".join(lines)}


def _executive_summary(
    msg: str, searches: list[dict], scrapes: list[dict]
) -> str:
    n_search = len(searches)
    n_scrape = len(scrapes)
    if n_search == 0 and n_scrape == 0:
        return (
            "Bright Data could not retrieve live web signals for this query. "
            "Check MCP token limits or try a more specific competitor question."
        )
    top_titles = [h.get("title") for h in searches[:3] if h.get("title")]
    hint = ""
    if top_titles:
        hint = f" Top surfaced themes: {'; '.join(top_titles[:2])}."
    return (
        f"Live competitive scan completed ({n_search} search hits, {n_scrape} pages scraped) "
        f"for: {msg[:200]}.{hint}"
    )


def _pricing_signals(scrapes: list[dict], searches: list[dict]) -> str:
    prices: list[str] = []
    for s in scrapes:
        text = s.get("content", "")
        prices.extend(re.findall(r"\$[\d,]+(?:\.\d{2})?", text))
    if prices:
        return "Detected price tokens: " + ", ".join(sorted(set(prices))[:8])
    for h in searches:
        blob = f"{h.get('title', '')} {h.get('description', '')}".lower()
        if "pricing" in blob or "plan" in blob:
            return f"Pricing mentioned in SERP — see {h.get('link', 'search results')}"
    return "No clear public pricing on scraped pages; check pricing URL manually."


def _news_signals(searches: list[dict]) -> str:
    if not searches:
        return "No news SERP results."
    bullets = []
    for h in searches[:5]:
        t = h.get("title") or "Untitled"
        bullets.append(f"{t} ({h.get('link', 'n/a')})")
    return "; ".join(bullets[:3])


def _hiring_signals(scrapes: list[dict], searches: list[dict]) -> str:
    kws = ["sales", "sdr", "bdr", "account executive", "revops", "marketing"]
    found: list[str] = []
    for s in scrapes:
        lower = s.get("content", "").lower()
        found.extend(kw for kw in kws if kw in lower)
    if found:
        return "Role keywords on careers/pages: " + ", ".join(sorted(set(found))[:6])
    for h in searches:
        if "career" in (h.get("link") or "").lower() or "job" in (h.get("title") or "").lower():
            return f"Careers signal in search — {h.get('link', '')}"
    return "Limited hiring signals in this pass."


def _messaging_signals(scrapes: list[dict]) -> str:
    for s in scrapes:
        lines = [ln.strip() for ln in s.get("content", "").splitlines() if ln.strip()]
        for ln in lines[:12]:
            if 20 < len(ln) < 200 and not ln.startswith("http"):
                return ln[:180]
    return "Review homepage scrape for headline themes."


def _recommended_actions(searches: list[dict], scrapes: list[dict]) -> list[str]:
    actions = [
        "- Compare pricing/plan changes against your last snapshot in SignalForge.",
        "- Brief sales on top news titles before the next competitive deal.",
    ]
    if scrapes:
        actions.append("- Validate scraped positioning against your battlecard.")
    if not searches and not scrapes:
        actions = ["- Retry research with competitor name + domain selected."]
    return actions


def _evidence_links(searches: list[dict], scrapes: list[dict]) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for h in searches:
        u = h.get("link", "")
        if u.startswith("http") and u not in seen:
            seen.add(u)
            links.append(u)
    for s in scrapes:
        u = s.get("url", "")
        if u.startswith("http") and u not in seen:
            seen.add(u)
            links.append(u)
    return links[:12]


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("plan", _plan_queries)
    graph.add_node("search", _run_searches)
    graph.add_node("scrape", _run_scrapes)
    graph.add_node("compile", _compile_brief)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "scrape")
    graph.add_edge("scrape", "compile")
    graph.add_edge("compile", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


async def run_brightdata_agent(
    user_message: str,
    *,
    system_extra: str = "",
) -> dict[str, Any]:
    try:
        tools = await get_mcp_tools()
        tool_names = [t.name for t in tools]
    except Exception as exc:
        return {
            "reply": f"Bright Data agent error: {exc}",
            "tool_count": 0,
            "tools_available": [],
            "error": True,
        }

    initial: AgentState = {
        "user_message": user_message,
        "system_extra": system_extra,
        "queries": [],
        "search_hits": [],
        "scrape_hits": [],
        "tools_available": tool_names,
        "tools_used": [],
    }

    try:
        final = await get_graph().ainvoke(initial)
    except Exception as exc:
        logger.exception("Bright Data agent graph failed")
        return {
            "reply": f"Bright Data agent error: {exc}",
            "tool_count": len(tool_names),
            "tools_available": tool_names,
            "error": True,
        }

    reply = (final.get("reply") or "").strip()
    if not reply:
        reply = "No brief generated. Try a competitor-specific research request."

    return {
        "reply": reply,
        "tool_count": len(tool_names),
        "tools_available": tool_names,
        "tools_used": final.get("tools_used", []),
        "message_count": len(final.get("queries") or []) + 2,
        "error": bool(final.get("error")),
    }


async def stream_brightdata_agent(
    user_message: str,
    *,
    system_extra: str = "",
):
    """SSE-friendly events: status | token | done | error"""
    try:
        tools = await get_mcp_tools()
        tool_names = [t.name for t in tools]
    except Exception as exc:
        yield {"event": "error", "data": str(exc)}
        return

    yield {"event": "status", "data": "Connecting to Bright Data MCP…"}
    yield {
        "event": "status",
        "data": f"Loaded {len(tool_names)} MCP tools (Bright Data web agent).",
    }

    state: AgentState = {
        "user_message": user_message,
        "system_extra": system_extra,
        "tools_available": tool_names,
    }

    try:
        yield {"event": "status", "data": "Planning research queries…"}
        state = {**state, **_plan_queries(state)}

        yield {"event": "status", "data": "Searching the live web (Bright Data SERP)…"}
        state = {**state, **(await _run_searches(state))}

        yield {"event": "status", "data": "Scraping competitor pages…"}
        state = {**state, **(await _run_scrapes(state))}

        yield {"event": "status", "data": "Compiling intelligence brief…"}
        state = {**state, **_compile_brief(state)}

        reply = state.get("reply", "")
        chunk_size = 400
        for i in range(0, len(reply), chunk_size):
            yield {"event": "token", "data": reply[i : i + chunk_size]}

        yield {
            "event": "done",
            "data": {
                "reply": reply,
                "tool_count": len(tool_names),
                "tools_available": tool_names,
                "tools_used": state.get("tools_used", []),
            },
        }
    except Exception as exc:
        yield {"event": "error", "data": str(exc)[:2000]}


async def research_competitor(name: str, domain: str) -> dict[str, Any]:
    query = RESEARCH_COMPETITOR_TEMPLATE.format(name=name, domain=domain)
    extra = f"Focus on competitor: {name} ({domain})"
    return await run_brightdata_agent(query, system_extra=extra)
