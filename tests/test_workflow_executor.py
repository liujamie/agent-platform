"""tests/test_workflow_executor.py"""
import pytest
from app.models.workflow import NodeDef, NodeType, RetryConfig
from app.core.workflow.graph import WorkflowGraph
from app.core.workflow.executor import WorkflowExecutor, NodeResult


class TestNodeResult:
    def test_node_result_creation(self):
        nr = NodeResult(node_id="a", status="success", output="ok")
        assert nr.node_id == "a"
        assert nr.duration_ms >= 0


class TestWorkflowExecutor:
    @pytest.mark.asyncio
    async def test_empty_workflow(self):
        executor = WorkflowExecutor()
        result = await executor.execute(WorkflowGraph())
        assert result.status == "completed"
        assert result.outputs == {}

    @pytest.mark.asyncio
    async def test_single_tool_node(self):
        executor = WorkflowExecutor()
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.tool, config={"tool": "echo"}))
        result = await executor.execute(g)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_linear_transform_workflow(self):
        executor = WorkflowExecutor()
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.transform, config={"transform_type": "upper"}))
        g.add_node(NodeDef(id="b", type=NodeType.transform, config={"transform_type": "reverse"}))
        g.add_edge("a", "b")
        result = await executor.execute(g)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_parallel_nodes(self):
        executor = WorkflowExecutor()
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.transform, config={}))
        g.add_node(NodeDef(id="b", type=NodeType.transform, config={}))
        g.add_node(NodeDef(id="c", type=NodeType.transform, config={}))
        g.add_edge("a", "b")
        g.add_edge("a", "c")
        result = await executor.execute(g)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_trace_id_is_set(self):
        executor = WorkflowExecutor()
        g = WorkflowGraph()
        g.add_node(NodeDef(id="a", type=NodeType.transform, config={}))
        result = await executor.execute(g)
        assert len(result.trace_id) > 0
