from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.models import AgentDefinition, WorkflowDefinition, RunLog

router = APIRouter(prefix="/api/v1/admin")


# ========== Agent Definition CRUD ==========

class AgentCreateRequest(BaseModel):
    name: str
    role: str
    model_name: str
    tools: list[str] = []
    memory_enabled: bool = True
    temperature: int = 70


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    model_name: str | None = None
    tools: list[str] | None = None
    memory_enabled: bool | None = None
    temperature: int | None = None
    status: str | None = None


@router.get("/agents")
async def list_agents():
    """List all agent definitions."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"agents": [], "message": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(AgentDefinition).order_by(AgentDefinition.created_at.desc())
        )
        agents = result.scalars().all()
        return {"agents": [_agent_to_dict(a) for a in agents]}
    except Exception as e:
        return {"agents": [], "message": str(e)}


@router.post("/agents")
async def create_agent(req: AgentCreateRequest):
    """Create a new agent definition."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        agent = AgentDefinition(
            name=req.name,
            role=req.role,
            model_name=req.model_name,
            tools=req.tools,
            memory_enabled=req.memory_enabled,
            temperature=req.temperature,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        return _agent_to_dict(agent)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: int):
    """Get a single agent definition."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return _agent_to_dict(agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: int, req: AgentUpdateRequest):
    """Update an agent definition."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(agent, key, value)
        agent.updated_at = datetime.now()
        await session.commit()
        await session.refresh(agent)
        return _agent_to_dict(agent)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: int):
    """Archive (soft-delete) an agent definition."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        agent.status = "archived"
        agent.updated_at = datetime.now()
        await session.commit()
        return {"message": "Agent archived"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ========== Workflow Definition CRUD ==========

class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    definition: dict[str, Any]


@router.get("/workflows")
async def list_workflows():
    """List all workflow definitions."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"workflows": [], "message": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(WorkflowDefinition).order_by(WorkflowDefinition.created_at.desc())
        )
        workflows = result.scalars().all()
        return {"workflows": [_workflow_to_dict(w) for w in workflows]}
    except Exception as e:
        return {"workflows": [], "message": str(e)}


@router.post("/workflows")
async def create_workflow(req: WorkflowCreateRequest):
    """Create a new workflow definition."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        wf = WorkflowDefinition(
            name=req.name,
            description=req.description,
            definition=req.definition,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(wf)
        await session.commit()
        await session.refresh(wf)
        return _workflow_to_dict(wf)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{wf_id}")
async def get_workflow(wf_id: int):
    """Get a single workflow definition."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == wf_id)
        )
        wf = result.scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return _workflow_to_dict(wf)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workflows/{wf_id}")
async def delete_workflow(wf_id: int):
    """Archive a workflow definition."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == wf_id)
        )
        wf = result.scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        wf.status = "archived"
        wf.updated_at = datetime.now()
        await session.commit()
        return {"message": "Workflow archived"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ========== Run Logs ==========

@router.get("/logs")
async def list_logs(page: int = 1, page_size: int = 20):
    """List run logs with pagination."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"logs": [], "total": 0, "message": "Database not configured"}
    try:
        from sqlalchemy import select, func
        # Count total
        count_result = await session.execute(select(func.count(RunLog.id)))
        total = count_result.scalar() or 0
        # Fetch page
        offset = (page - 1) * page_size
        result = await session.execute(
            select(RunLog)
            .order_by(RunLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        logs = result.scalars().all()
        return {
            "logs": [_log_to_dict(l) for l in logs],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        return {"logs": [], "total": 0, "message": str(e)}


@router.get("/logs/{trace_id}")
async def get_log_by_trace(trace_id: str):
    """Get a run log by trace ID."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"error": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(RunLog).where(RunLog.trace_id == trace_id)
        )
        log = result.scalar_one_or_none()
        if log is None:
            raise HTTPException(status_code=404, detail="Log not found")
        return _log_to_dict(log)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Stats ==========

@router.get("/stats")
async def get_stats():
    """Get platform statistics."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"agent_count": 0, "workflow_count": 0, "log_count": 0}
    try:
        from sqlalchemy import select, func
        agent_count = (await session.execute(select(func.count(AgentDefinition.id)))).scalar() or 0
        wf_count = (await session.execute(select(func.count(WorkflowDefinition.id)))).scalar() or 0
        log_count = (await session.execute(select(func.count(RunLog.id)))).scalar() or 0
        return {
            "agent_count": agent_count,
            "workflow_count": wf_count,
            "log_count": log_count,
        }
    except Exception as e:
        return {"agent_count": 0, "workflow_count": 0, "log_count": 0, "error": str(e)}


# ========== Helpers ==========

def _agent_to_dict(agent):
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "model_name": agent.model_name,
        "tools": agent.tools or [],
        "memory_enabled": agent.memory_enabled,
        "temperature": agent.temperature,
        "status": agent.status,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


def _workflow_to_dict(wf):
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description or "",
        "definition": wf.definition,
        "status": wf.status,
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
        "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
    }


def _log_to_dict(log):
    return {
        "id": log.id,
        "trace_id": log.trace_id,
        "agent_id": log.agent_id,
        "workflow_id": log.workflow_id,
        "input": log.input,
        "output": log.output,
        "status": log.status,
        "tokens": log.tokens,
        "duration_ms": log.duration_ms,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
