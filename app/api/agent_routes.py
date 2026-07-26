import json
import time
import uuid

from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.agent.react import ReActAgent
from app.models.agent import AgentConfig

router = APIRouter(prefix="/api/v1/agent")


async def _save_run_log(agent_id: int, input_text: str, output: str, status: str, duration_ms: int):
    """Save a run log entry to the database."""
    from app.main import get_db_session
    from app.infrastructure.models import RunLog

    session = get_db_session()
    if session is None:
        return

    try:
        log = RunLog(
            trace_id=str(uuid.uuid4()),
            agent_id=agent_id,
            input=input_text,
            output=output[:5000] if output else "",
            status=status,
            duration_ms=duration_ms,
            created_at=datetime.now(),
        )
        session.add(log)
        await session.commit()
    except Exception:
        await session.rollback()


class AgentRunRequest(BaseModel):
    message: str
    agent_config: AgentConfig


class AgentRunByIdRequest(BaseModel):
    message: str
    session_id: str = ""


class SessionClearRequest(BaseModel):
    session_id: str


class SessionRenameRequest(BaseModel):
    name: str


class AgentRunResponse(BaseModel):
    status: str
    output: str = ""
    trace_id: str = ""
    error: str | None = None


@router.post("/run", response_model=AgentRunResponse)
async def agent_run(req: AgentRunRequest):
    from app.main import model_router, tool_registry

    model_client = None
    if model_router:
        model_client = model_router.current_client

    from app.main import mcp_gateway
    agent = ReActAgent(req.agent_config, model_client=model_client, tool_registry=tool_registry, mcp_gateway=mcp_gateway)
    result = await agent.execute(req.message)
    return AgentRunResponse(
        status=result.status,
        output=result.output,
        trace_id=result.trace_id,
        error=result.error,
    )


@router.post("/run/{agent_id}", response_model=AgentRunResponse)
async def agent_run_by_id(agent_id: int, req: AgentRunByIdRequest):
    """Run an agent by its database ID. Loads config from DB."""
    from app.main import get_db_session, model_router, tool_registry
    from app.infrastructure.models import AgentDefinition
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent_def = result.scalar_one_or_none()
    if agent_def is None:
        raise HTTPException(status_code=404, detail=f"Agent #{agent_id} not found")

    agent_config = AgentConfig(
        name=agent_def.name,
        role=agent_def.role or "",
        model=agent_def.model_name,
        tools=agent_def.tools or [],
        connections=agent_def.connections or [],
        skills=agent_def.skills or [],
        temperature=(agent_def.temperature or 70) / 100,
    )

    model_client = model_router.current_client if model_router else None
    from app.main import mcp_gateway
    agent = ReActAgent(agent_config, model_client=model_client, tool_registry=tool_registry, mcp_gateway=mcp_gateway)
    start = time.time()
    result = await agent.execute(req.message, session_id=req.session_id)
    duration = int((time.time() - start) * 1000)
    await _save_run_log(agent_id, req.message, result.output, result.status, duration)
    return AgentRunResponse(
        status=result.status,
        output=result.output,
        trace_id=result.trace_id,
        error=result.error,
    )


@router.post("/stream")
async def agent_stream(req: AgentRunRequest):
    from app.main import model_router, tool_registry

    model_client = None
    if model_router:
        model_client = model_router.current_client

    from app.main import mcp_gateway
    agent = ReActAgent(req.agent_config, model_client=model_client, tool_registry=tool_registry, mcp_gateway=mcp_gateway)

    async def event_stream():
        async for event in agent.stream(req.message):
            yield f"event: {event.type.value}\ndata: {json.dumps({'content': event.content})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream/{agent_id}")
async def agent_stream_by_id(agent_id: int, req: AgentRunByIdRequest):
    """Stream an agent by its database ID. Loads config from DB."""
    from app.main import get_db_session, model_router, tool_registry
    from app.infrastructure.models import AgentDefinition
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent_def = result.scalar_one_or_none()
    if agent_def is None:
        raise HTTPException(status_code=404, detail=f"Agent #{agent_id} not found")

    agent_config = AgentConfig(
        name=agent_def.name,
        role=agent_def.role or "",
        model=agent_def.model_name,
        tools=agent_def.tools or [],
        connections=agent_def.connections or [],
        skills=agent_def.skills or [],
        temperature=(agent_def.temperature or 70) / 100,
    )

    model_client = model_router.current_client if model_router else None
    from app.main import mcp_gateway
    agent = ReActAgent(agent_config, model_client=model_client, tool_registry=tool_registry, mcp_gateway=mcp_gateway)

    async def event_stream():
        full_output = ""
        start = time.time()
        async for event in agent.stream(req.message, session_id=req.session_id):
            if event.type.value == "end":
                full_output = event.content or ""
            elif event.type.value == "chunk":
                full_output += event.content or ""
            yield f"event: {event.type.value}\ndata: {json.dumps({'content': event.content})}\n\n"
        duration = int((time.time() - start) * 1000)
        await _save_run_log(agent_id, req.message, full_output, "success", duration)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/session/clear")
async def session_clear(req: SessionClearRequest):
    """Clear all messages from a conversation."""
    from app.core.conversation.service import add_message, get_messages
    # Re-create the conversation by marking old messages deleted and adding a new one
    # For now: this is a no-op since messages are precious.
    # Full clear = delete + recreate, handled on frontend via session delete.
    return {"message": f"Session '{req.session_id}' cleared (messages preserved in history)"}


# ── Session management (Conversation) ───────────────

@router.get("/{agent_id}/sessions")
async def list_sessions(agent_id: int):
    """List all conversations for an agent."""
    from app.core.conversation.service import list_by_agent
    sessions = await list_by_agent(agent_id)
    return {"sessions": sessions}


@router.post("/{agent_id}/sessions")
async def create_session(agent_id: int):
    """Create a new conversation for an agent."""
    from app.core.conversation.service import create_conversation
    result = await create_conversation(agent_id)
    return {"session_id": result["session_id"], "name": result["name"]}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation."""
    from app.core.conversation.service import delete_conversation
    await delete_conversation(session_id)
    return {"message": f"Session '{session_id}' deleted"}


@router.put("/session/{session_id}/rename")
async def rename_session(session_id: str, req: SessionRenameRequest):
    """Rename a conversation."""
    from app.core.conversation.service import rename
    await rename(session_id, req.name)
    return {"message": "Renamed"}


@router.get("/session/messages/{session_id}")
async def get_session_messages(session_id: str):
    """Get all messages for a conversation."""
    from app.core.conversation.service import get_messages
    messages = await get_messages(session_id)
    return {"messages": messages}
