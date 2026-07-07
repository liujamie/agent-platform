import asyncio
import time
import uuid
from typing import Any

from app.core.workflow.graph import WorkflowGraph
from app.models.common import Context
from app.models.workflow import WorkflowResult, NodeType
from pydantic import BaseModel


class NodeResult(BaseModel):
    node_id: str
    status: str
    output: str = ""
    error: str | None = None
    duration_ms: int = 0


class WorkflowExecutor:
    """Execute a DAG WorkflowGraph: topological sort -> parallel layers -> aggregate."""

    def __init__(self, tool_registry=None):
        self.tool_registry = tool_registry

    async def execute(self, graph: WorkflowGraph) -> WorkflowResult:
        trace_id = str(uuid.uuid4())
        ctx = Context()
        layers = graph.topo_sort()
        all_results: dict[str, NodeResult] = {}

        for layer in layers:
            tasks = [self._run_node(nid, graph, ctx) for nid in layer]
            node_results = await asyncio.gather(*tasks, return_exceptions=True)

            for nid, nr in zip(layer, node_results):
                if isinstance(nr, Exception):
                    all_results[nid] = NodeResult(node_id=nid, status="error", error=str(nr))
                else:
                    all_results[nid] = nr
                    ctx.set(nid, nr.output)

        outputs = {nid: nr.output for nid, nr in all_results.items()}
        return WorkflowResult(status="completed", trace_id=trace_id, outputs=outputs)

    async def _run_node(self, nid: str, graph: WorkflowGraph, ctx: Context) -> NodeResult:
        node = graph.get_node(nid)
        if node is None:
            return NodeResult(node_id=nid, status="error", error=f"Node '{nid}' not found")

        start = time.time()
        try:
            if node.timeout:
                async def execute_with_timeout():
                    return await self._dispatch_node(node, ctx)
                output = await asyncio.wait_for(execute_with_timeout(), timeout=node.timeout)
            else:
                output = await self._dispatch_node(node, ctx)

            duration = int((time.time() - start) * 1000)
            return NodeResult(node_id=nid, status="success", output=str(output), duration_ms=duration)
        except asyncio.TimeoutError:
            return NodeResult(node_id=nid, status="error", error="Timeout", duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return NodeResult(node_id=nid, status="error", error=str(e), duration_ms=int((time.time() - start) * 1000))

    async def _dispatch_node(self, node, ctx) -> Any:
        if node.type == NodeType.transform:
            return _run_transform(node, ctx)
        elif node.type == NodeType.tool:
            return f"tool:{node.config.get('tool', 'unknown')} executed"
        elif node.type == NodeType.agent:
            return f"agent:{node.id} executed"
        else:
            return f"node {node.id} executed"


def _run_transform(node, ctx) -> str:
    transform_type = node.config.get("transform_type", "")
    input_val = ctx.get(node.id, "")
    if transform_type == "upper":
        return str(input_val).upper()
    elif transform_type == "reverse":
        return str(input_val)[::-1]
    return f"transformed({node.id})"
