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

    agent = ReActAgent(req.agent_config, model_client=model_client, tool_registry=tool_registry)
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
        temperature=(agent_def.temperature or 70) / 100,
    )

    model_client = model_router.current_client if model_router else None
    agent = ReActAgent(agent_config, model_client=model_client, tool_registry=tool_registry)
    start = time.time()
    result = await agent.execute(req.message)
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

    agent = ReActAgent(req.agent_config, model_client=model_client, tool_registry=tool_registry)

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
        temperature=(agent_def.temperature or 70) / 100,
    )

    model_client = model_router.current_client if model_router else None
    agent = ReActAgent(agent_config, model_client=model_client, tool_registry=tool_registry)

    async def event_stream():
        full_output = ""
        start = time.time()
        async for event in agent.stream(req.message):
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
