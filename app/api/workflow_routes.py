import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.workflow import WorkflowDef
from app.core.workflow.graph import WorkflowGraph, CyclicGraphError
from app.core.workflow.executor import WorkflowExecutor

router = APIRouter(prefix="/api/v1/workflow")


@router.post("/run")
async def workflow_run(wf_def: WorkflowDef):
    from app.main import tool_registry

    graph = _build_graph(wf_def)
    executor = WorkflowExecutor(tool_registry=tool_registry)
    result = await executor.execute(graph)
    return result.model_dump()


@router.post("/stream")
async def workflow_stream(wf_def: WorkflowDef):
    from app.main import tool_registry

    graph = _build_graph(wf_def)
    executor = WorkflowExecutor(tool_registry=tool_registry)

    async def event_stream():
        yield "event: start\ndata: {}\n\n"
        result = await executor.execute(graph)
        yield f"event: complete\ndata: {json.dumps(result.model_dump())}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
