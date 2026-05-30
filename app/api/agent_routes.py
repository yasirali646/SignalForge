import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.forge_agent import (
    AgentNotConfiguredError,
    list_mcp_tools,
    research_competitor,
    run_forge_agent,
    stream_forge_agent,
)
from app.agents.pipeline_bridge import connect_agent_to_pipeline
from app.auth import CurrentUser, require_user
from app.config import get_settings
from app.database import get_db
from app.models import AgentRun, Competitor
from app.services.demo_quota import (
    ensure_agent_request_allowed,
    get_agent_quota,
    record_agent_request,
)

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentStatusOut(BaseModel):
    configured: bool
    mcp_configured: bool
    brightdata_agent: bool
    model: str
    agent_mode: str
    mcp_url_preview: str | None = None
    agent_requests_used: int = 0
    agent_requests_limit: int | None = None
    agent_requests_remaining: int | None = None


class AgentChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    competitor_id: int | None = None
    trigger_collection: bool = True


class AgentChatOut(BaseModel):
    reply: str
    tool_count: int
    tools_available: list[str]
    message_count: int | None = None
    error: bool = False
    agent_run_id: int | None = None
    events_created: int = 0
    collection_triggered: bool = False


class AgentRunOut(BaseModel):
    id: int
    competitor_id: int | None
    competitor_name: str | None = None
    query: str
    reply_preview: str
    events_created: int
    collection_triggered: bool
    created_at: str

    model_config = {"from_attributes": True}


def _run_to_out(run: AgentRun, comp: Competitor | None) -> AgentRunOut:
    preview = run.reply_md[:300] + ("…" if len(run.reply_md) > 300 else "")
    return AgentRunOut(
        id=run.id,
        competitor_id=run.competitor_id,
        competitor_name=comp.name if comp else None,
        query=run.query,
        reply_preview=preview,
        events_created=run.events_created,
        collection_triggered=run.collection_triggered,
        created_at=run.created_at.isoformat(),
    )


async def _finalize_agent_result(
    db: Session,
    *,
    competitor_id: int | None,
    query: str,
    result: dict,
    trigger_collection: bool,
) -> AgentChatOut:
    bridge = connect_agent_to_pipeline(
        db,
        competitor_id=competitor_id,
        query=query,
        reply=result["reply"],
        tools_available=result.get("tools_available", []),
        trigger_collection=trigger_collection and competitor_id is not None,
    )
    return AgentChatOut(
        reply=result["reply"],
        tool_count=result.get("tool_count", 0),
        tools_available=result.get("tools_available", []),
        message_count=result.get("message_count"),
        error=result.get("error", False),
        agent_run_id=bridge["agent_run_id"],
        events_created=bridge["events_created"],
        collection_triggered=bridge["collection_triggered"],
    )


@router.get("/status", response_model=AgentStatusOut)
def agent_status(
    user: CurrentUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    s = get_settings()
    mcp = s.resolved_mcp_url()
    preview = None
    if mcp:
        preview = mcp.split("token=")[0] + "token=***" if "token=" in mcp else mcp[:60]
    used, limit, remaining = get_agent_quota(db, user)
    return AgentStatusOut(
        configured=s.agent_configured(),
        mcp_configured=bool(mcp),
        brightdata_agent=True,
        model=s.agent_model_label(),
        agent_mode=s.agent_mode,
        mcp_url_preview=preview,
        agent_requests_used=used,
        agent_requests_limit=limit,
        agent_requests_remaining=remaining,
    )


@router.get("/runs/{run_id}")
def get_agent_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(404, detail="Run not found")
    comp = db.get(Competitor, run.competitor_id) if run.competitor_id else None
    return {
        **_run_to_out(run, comp).model_dump(),
        "reply_md": run.reply_md,
    }


@router.get("/runs", response_model=list[AgentRunOut])
def list_agent_runs(
    competitor_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    q = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
    if competitor_id:
        q = q.where(AgentRun.competitor_id == competitor_id)
    runs = db.scalars(q).all()
    out = []
    for run in runs:
        comp = db.get(Competitor, run.competitor_id) if run.competitor_id else None
        out.append(_run_to_out(run, comp))
    return out


@router.get("/tools")
async def agent_tools():
    try:
        names = await list_mcp_tools()
        return {"tools": names, "count": len(names)}
    except AgentNotConfiguredError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail=f"MCP tools error: {exc}") from exc


@router.post("/chat", response_model=AgentChatOut)
async def agent_chat(
    body: AgentChatIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_user),
):
    if not get_settings().agent_configured():
        raise HTTPException(503, detail="Agent not configured.")
    ensure_agent_request_allowed(db, user)

    extra = ""
    if body.competitor_id:
        comp = db.get(Competitor, body.competitor_id)
        if comp:
            extra = f"Focus on competitor: {comp.name} ({comp.domain})"

    try:
        result = await run_forge_agent(body.message, system_extra=extra)
        out = await _finalize_agent_result(
            db,
            competitor_id=body.competitor_id,
            query=body.message,
            result=result,
            trigger_collection=body.trigger_collection,
        )
        record_agent_request(db, user)
        return out
    except AgentNotConfiguredError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail=f"Agent error: {exc}") from exc


@router.post("/chat/stream")
async def agent_chat_stream(
    body: AgentChatIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_user),
):
    if not get_settings().agent_configured():
        raise HTTPException(503, detail="Agent not configured.")
    ensure_agent_request_allowed(db, user)

    extra = ""
    if body.competitor_id:
        comp = db.get(Competitor, body.competitor_id)
        if comp:
            extra = f"Focus on competitor: {comp.name} ({comp.domain})"

    async def event_generator():
        final_result: dict | None = None
        try:
            async for chunk in stream_forge_agent(body.message, system_extra=extra):
                if chunk["event"] == "done":
                    final_result = chunk["data"]
                yield f"data: {json.dumps(chunk)}\n\n"

            if final_result and final_result.get("reply"):
                bridge = connect_agent_to_pipeline(
                    db,
                    competitor_id=body.competitor_id,
                    query=body.message,
                    reply=final_result["reply"],
                    tools_available=final_result.get("tools_available", []),
                    trigger_collection=body.trigger_collection
                    and body.competitor_id is not None,
                )
                record_agent_request(db, user)
                quota_used, quota_limit, quota_remaining = get_agent_quota(db, user)
                bridge["agent_requests_used"] = quota_used
                bridge["agent_requests_limit"] = quota_limit
                bridge["agent_requests_remaining"] = quota_remaining
                yield f"data: {json.dumps({'event': 'pipeline', 'data': bridge})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'data': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/research/{competitor_id}", response_model=AgentChatOut)
async def agent_research_competitor(
    competitor_id: int,
    trigger_collection: bool = True,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_user),
):
    comp = db.get(Competitor, competitor_id)
    if not comp:
        raise HTTPException(404, detail="Competitor not found")
    if not get_settings().agent_configured():
        raise HTTPException(503, detail="Agent not configured.")
    ensure_agent_request_allowed(db, user)

    try:
        result = await research_competitor(comp.name, comp.domain)
        out = await _finalize_agent_result(
            db,
            competitor_id=competitor_id,
            query=f"Research {comp.name}",
            result=result,
            trigger_collection=trigger_collection,
        )
        record_agent_request(db, user)
        return out
    except AgentNotConfiguredError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail=f"Agent error: {exc}") from exc
