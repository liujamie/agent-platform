import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.models.workflow import WorkflowDef
from app.core.workflow.graph import WorkflowGraph, CyclicGraphError
from app.core.workflow.executor import WorkflowExecutor

router = APIRouter(prefix="/api/v1/workflow")


class WorkflowRunRequest(BaseModel):
    workflow_id: int
    input_data: dict = {}


# ── Execute ──────────────────────────────────────────

@router.post("/run")
async def workflow_run(wf_def: WorkflowDef):
    """Execute a workflow definition directly (ad-hoc)."""
    from app.main import tool_registry
    graph = _build_graph(wf_def)
    executor = WorkflowExecutor(tool_registry=tool_registry)
    result = await executor.execute(graph)
    return result


@router.post("/run/{workflow_id}")
async def workflow_run_by_id(workflow_id: int, req: WorkflowRunRequest):
    """Execute a workflow by DB ID."""
    from app.main import get_db_session, tool_registry, model_router, mcp_gateway
    from sqlalchemy import select
    from app.infrastructure.models import WorkflowDefinition

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
    )
    wf_def = result.scalar_one_or_none()
    if wf_def is None:
        raise HTTPException(status_code=404, detail=f"Workflow #{workflow_id} not found")

    graph = _build_graph(WorkflowDef(**wf_def.definition))
    executor = WorkflowExecutor(
        tool_registry=tool_registry,
        model_router=model_router,
        mcp_gateway=mcp_gateway,
    )
    result = await executor.execute(graph, input_data=req.input_data, workflow_id=workflow_id)
    return result


# ── Instance management ──────────────────────────────

@router.get("/instances")
async def list_instances(page: int = 1, page_size: int = 20):
    """List workflow execution instances."""
    from app.main import get_db_session
    from sqlalchemy import select, func
    from app.infrastructure.models import WorkflowInstance

    session = get_db_session()
    if session is None:
        return {"instances": [], "total": 0}

    try:
        total_q = await session.execute(select(func.count(WorkflowInstance.id)))
        total = total_q.scalar() or 0
        offset = (page - 1) * page_size
        result = await session.execute(
            select(WorkflowInstance)
            .order_by(WorkflowInstance.created_at.desc())
            .offset(offset).limit(page_size)
        )
        instances = []
        for inst in result.scalars().all():
            instances.append({
                "id": inst.id,
                "workflow_id": inst.workflow_id,
                "trace_id": inst.trace_id,
                "status": inst.status,
                "trigger_type": inst.trigger_type,
                "duration_ms": inst.duration_ms,
                "started_at": inst.started_at.isoformat() if inst.started_at else None,
                "ended_at": inst.ended_at.isoformat() if inst.ended_at else None,
            })
        return {"instances": instances, "total": total}
    except Exception as e:
        return {"instances": [], "total": 0, "error": str(e)}


@router.get("/instances/{trace_id}")
async def get_instance(trace_id: str):
    """Get instance detail with node executions."""
    from app.main import get_db_session
    from sqlalchemy import select
    from app.infrastructure.models import WorkflowInstance, WorkflowNodeExecution

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(WorkflowInstance).where(WorkflowInstance.trace_id == trace_id)
    )
    inst = result.scalar_one_or_none()
    if inst is None:
        raise HTTPException(status_code=404, detail="Instance not found")

    node_result = await session.execute(
        select(WorkflowNodeExecution)
        .where(WorkflowNodeExecution.instance_id == inst.id)
        .order_by(WorkflowNodeExecution.id)
    )
    nodes = []
    for n in node_result.scalars().all():
        nodes.append({
            "node_id": n.node_id,
            "node_type": n.node_type,
            "node_name": n.node_name,
            "status": n.status,
            "error": n.error,
            "retry_count": n.retry_count,
            "duration_ms": n.duration_ms,
            "started_at": n.started_at.isoformat() if n.started_at else None,
        })

    return {
        "id": inst.id,
        "workflow_id": inst.workflow_id,
        "trace_id": inst.trace_id,
        "status": inst.status,
        "trigger_type": inst.trigger_type,
        "input_data": inst.input_data,
        "output_data": inst.output_data,
        "duration_ms": inst.duration_ms,
        "started_at": inst.started_at.isoformat() if inst.started_at else None,
        "ended_at": inst.ended_at.isoformat() if inst.ended_at else None,
        "node_executions": nodes,
    }


# ── Approval ─────────────────────────────────────────

@router.post("/approval/{approval_id}/approve")
async def approve_task(approval_id: int, comment: str = ""):
    """Approve a human-in-the-loop task."""
    from app.main import get_db_session
    from sqlalchemy import select
    from app.infrastructure.models import WorkflowApproval

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(WorkflowApproval).where(WorkflowApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = "approved"
    approval.comment = comment
    approval.handled_at = datetime.now()
    await session.commit()
    return {"message": "Approved"}


@router.post("/approval/{approval_id}/reject")
async def reject_task(approval_id: int, comment: str = ""):
    """Reject a human-in-the-loop task."""
    from app.main import get_db_session
    from sqlalchemy import select
    from app.infrastructure.models import WorkflowApproval

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(WorkflowApproval).where(WorkflowApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = "rejected"
    approval.comment = comment
    approval.handled_at = datetime.now()
    await session.commit()
    return {"message": "Rejected"}


# ── Helpers ──────────────────────────────────────────

def _build_graph(wf_def: WorkflowDef) -> WorkflowGraph:
    graph = WorkflowGraph()
    for node in wf_def.nodes:
        graph.add_node(node)
    for edge in wf_def.edges:
        graph.add_edge(edge.source, edge.target, edge.condition)
    try:
        graph.topo_sort()
    except CyclicGraphError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return graph
