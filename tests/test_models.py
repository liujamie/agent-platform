"""tests/test_models.py"""
import pytest
from pydantic import ValidationError

from app.models.common import TokenUsage, Context, Task
from app.models.agent import AgentConfig, AgentResult, AgentEvent, AgentEventType
from app.models.tool import ToolSchema, ToolResult, ToolParam
from app.models.workflow import WorkflowDef, NodeDef, EdgeDef, WorkflowResult, WorkflowStatus, NodeType


class TestCommonModels:
    def test_token_usage(self):
        t = TokenUsage(input=100, output=50, total=150)
        assert t.input == 100
        assert t.total == 150

    def test_token_usage_defaults(self):
        t = TokenUsage()
        assert t.input == 0
        assert t.output == 0
        assert t.total == 0

    def test_context_store_and_get(self):
        ctx = Context()
        ctx.set("key1", "value1")
        assert ctx.get("key1") == "value1"
        assert ctx.get("nonexistent") is None

    def test_task_creation(self):
        task = Task(input="hello", session_id="s1")
        assert task.input == "hello"
        assert task.session_id == "s1"
        assert task.metadata == {}


class TestAgentModels:
    def test_agent_config_minimal(self):
        cfg = AgentConfig(name="test", role="helper", model="deepseek")
        assert cfg.name == "test"
        assert cfg.tools == []
        assert cfg.max_iterations == 10

    def test_agent_config_defaults(self):
        cfg = AgentConfig(name="a", role="r", model="m")
        assert cfg.max_iterations == 10
        assert cfg.temperature == 0.7

    def test_agent_result(self):
        r = AgentResult(status="success", output="done", trace_id="t1")
        assert r.status == "success"
        assert r.trace_id == "t1"

    def test_agent_events(self):
        e = AgentEvent(type=AgentEventType.chunk, content="hello")
        assert e.type == AgentEventType.chunk
        assert e.content == "hello"

    def test_agent_event_tool_call(self):
        e = AgentEvent(type=AgentEventType.tool_call, tool_name="search", tool_args={"q": "test"})
        assert e.type == AgentEventType.tool_call
        assert e.tool_name == "search"

    def test_invalid_agent_config_missing_required(self):
        with pytest.raises(ValidationError):
            AgentConfig(name="test", role="helper")  # missing model

    def test_invalid_agent_config_negative_temperature(self):
        with pytest.raises(ValidationError):
            AgentConfig(name="test", role="helper", model="m", temperature=-1)


class TestToolModels:
    def test_tool_param(self):
        p = ToolParam(type="string", description="a query", required=True)
        assert p.type == "string"
        assert p.required is True

    def test_tool_schema(self):
        s = ToolSchema(
            name="search",
            description="search web",
            parameters={
                "query": {"type": "string", "description": "search keyword"}
            },
        )
        assert s.name == "search"
        assert "query" in s.parameters

    def test_tool_result(self):
        r = ToolResult(tool_name="search", output="results", success=True)
        assert r.success is True


class TestWorkflowModels:
    def test_node_def_minimal(self):
        n = NodeDef(id="n1", type=NodeType.agent, config={"agent_type": "planner"})
        assert n.id == "n1"

    def test_edge_def(self):
        e = EdgeDef(source="a", target="b")
        assert e.source == "a"
        assert e.condition is None

    def test_edge_def_with_condition(self):
        e = EdgeDef(source="a", target="b", condition="result.status == 'success'")
        assert e.condition is not None

    def test_workflow_def(self):
        w = WorkflowDef(
            nodes=[
                NodeDef(id="a", type=NodeType.agent, config={}),
                NodeDef(id="b", type=NodeType.tool, config={"tool": "search"}),
            ],
            edges=[EdgeDef(source="a", target="b")],
        )
        assert len(w.nodes) == 2
        assert w.edges[0].source == "a"

    def test_workflow_result(self):
        r = WorkflowResult(status="completed", trace_id="t1", outputs={"a": "ok"})
        assert r.status == "completed"
        assert r.outputs == {"a": "ok"}

    def test_workflow_status(self):
        ws = WorkflowStatus(workflow_id="wf1", status="running", node_statuses={"a": "running"})
        assert ws.workflow_id == "wf1"
