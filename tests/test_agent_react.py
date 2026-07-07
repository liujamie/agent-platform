"""tests/test_agent_react.py"""
import pytest
from app.models.agent import AgentConfig, AgentEvent, AgentEventType, AgentResult
from app.core.agent.base import BaseAgent
from app.core.agent.react import ReActAgent


class TestReActAgentInit:
    def test_extends_base_agent(self):
        cfg = AgentConfig(name="test", role="helper", model="deepseek-chat")
        agent = ReActAgent(cfg, model_client=None, tool_registry=None)
        assert isinstance(agent, BaseAgent)

    def test_accepts_config(self):
        cfg = AgentConfig(name="test", role="helper", model="deepseek-chat")
        agent = ReActAgent(cfg, model_client=None, tool_registry=None)
        assert agent.config.name == "test"
        assert agent.config.max_iterations == 10

    def test_memory_initialized(self):
        cfg = AgentConfig(name="test", role="helper", model="deepseek-chat")
        agent = ReActAgent(cfg, model_client=None, tool_registry=None)
        assert hasattr(agent, "_messages")
        assert agent._messages == []


class TestReActAgentExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_agent_result(self):
        cfg = AgentConfig(name="test", role="helper", model="deepseek-chat")
        agent = ReActAgent(cfg, model_client=None, tool_registry=None)
        result = await agent.execute("hello", session_id="s1")
        assert isinstance(result, AgentResult)

    @pytest.mark.asyncio
    async def test_execute_error_without_model(self):
        cfg = AgentConfig(name="test", role="helper", model="deepseek-chat")
        agent = ReActAgent(cfg, model_client=None, tool_registry=None)
        result = await agent.execute("hello")
        assert result.error is not None


class TestReActAgentStream:
    @pytest.mark.asyncio
    async def test_stream_yields_error_event_without_model(self):
        cfg = AgentConfig(name="test", role="helper", model="deepseek-chat")
        agent = ReActAgent(cfg, model_client=None, tool_registry=None)
        events = []
        async for event in agent.stream("hello"):
            events.append(event)
        assert len(events) > 0
        assert events[-1].type == AgentEventType.error
