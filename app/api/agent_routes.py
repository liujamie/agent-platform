import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.agent.react import ReActAgent
from app.models.agent import AgentConfig

router = APIRouter(prefix="/api/v1/agent")


class AgentRunRequest(BaseModel):
    message: str
    agent_config: AgentConfig


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
