import json
from typing import AsyncIterator

from app.core.agent.base import BaseAgent
from app.core.agent.state import AgentStateMachine, AgentState
from app.models.agent import AgentConfig, AgentResult, AgentEvent, AgentEventType


class ReActAgent(BaseAgent):
    """
    ReAct Agent implementation.

    Thought -> Action -> Observation -> Thought -> ... -> Final Answer
    Supports tool calling via OpenAI-compatible function_call API.
    """

    def __init__(self, config: AgentConfig, model_client=None, tool_registry=None, mcp_gateway=None):
        super().__init__(config)
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.mcp_gateway = mcp_gateway
        self._state_machine = AgentStateMachine()
        self._messages: list[dict] = []

    def _get_tool_schemas(self) -> list[dict]:
        """Build OpenAI-compatible tool schemas from config tool names + connections."""
        if not self.tool_registry:
            return []
        tool_names = set(self.config.tools or [])

        # Expand MCP connections into their tool names
        if self.mcp_gateway and self.config.connections:
            for conn_name in self.config.connections:
                conn = self.mcp_gateway.get_connection(conn_name)
                if conn:
                    for t in (conn.get("tools") or []):
                        tool_names.add(t)

        schemas = []
        for name in sorted(tool_names):
            tool = self.tool_registry.get(name)
            if tool:
                func = {"name": tool.name, "description": tool.description}
                if tool.parameters:
                    func["parameters"] = tool.parameters
                schemas.append({"type": "function", "function": func})
        return schemas

    def _build_system_message(self) -> dict:
        """Build system message with role prompt."""
        return {"role": "system", "content": self.config.role}

    async def _load_history(self, session_id: str) -> list[dict]:
        """Load conversation history from Redis."""
        try:
            from app.infrastructure.redis_client import session_get_messages
            return await session_get_messages(session_id)
        except Exception:
            return []

    async def _save_to_history(self, session_id: str, user_msg: str, assistant_msg: str):
        """Save a conversation turn to Redis."""
        try:
            from app.infrastructure.redis_client import session_add_message
            await session_add_message(session_id, {"role": "user", "content": user_msg})
            await session_add_message(session_id, {"role": "assistant", "content": assistant_msg})
        except Exception:
            pass

    async def execute(self, task_input: str, session_id: str = "") -> AgentResult:
        if self.model_client is None:
            return AgentResult(status="error", output="", error="Model client not configured")

        self._state_machine.reset()
        messages = [self._build_system_message()]
        if session_id:
            history = await self._load_history(session_id)
            messages.extend(history)
        messages.append({"role": "user", "content": task_input})
        tool_schemas = self._get_tool_schemas()
        steps = 0

        try:
            self._state_machine.transition(AgentState.RUNNING)
            while steps < self.config.max_iterations:
                response = await self.model_client.invoke(
                    messages=messages,
                    model=self.config.model,
                    tools=tool_schemas or None,
                )
                steps += 1

                if response.tool_calls:
                    self._state_machine.transition(AgentState.TOOL_CALL)
                    assistant_msg: dict = {"role": "assistant", "content": response.content}
                    assistant_msg["tool_calls"] = [
                        {k: v for k, v in tc.items() if k != "index"}
                        for tc in response.tool_calls
                    ]
                    messages.append(assistant_msg)

                    for tc in response.tool_calls:
                        tool_name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                        except json.JSONDecodeError:
                            args = {}

                        result = await self.tool_registry.execute(tool_name, args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result.output,
                        })
                    self._state_machine.transition(AgentState.RUNNING)
                else:
                    self._state_machine.transition(AgentState.FINISHED)
                    if session_id:
                        await self._save_to_history(session_id, task_input, response.content or "")
                    return AgentResult(
                        status="success",
                        output=response.content or "",
                        steps=steps,
                    )

            self._state_machine.transition(AgentState.ERROR)
            return AgentResult(
                status="error",
                output="",
                error=f"Max iterations ({self.config.max_iterations}) reached",
                steps=steps,
            )
        except Exception as e:
            self._state_machine.transition(AgentState.ERROR)
            return AgentResult(status="error", error=str(e), steps=0)

    async def stream(self, task_input: str, session_id: str = "") -> AsyncIterator[AgentEvent]:
        if self.model_client is None:
            yield AgentEvent(type=AgentEventType.error, content="Model client not configured")
            return

        self._state_machine.reset()
        messages = [self._build_system_message()]
        if session_id:
            history = await self._load_history(session_id)
            messages.extend(history)
        messages.append({"role": "user", "content": task_input})
        tool_schemas = self._get_tool_schemas()
        steps = 0

        yield AgentEvent(type=AgentEventType.start, content="Agent started")

        try:
            self._state_machine.transition(AgentState.RUNNING)
            while steps < self.config.max_iterations:
                yield AgentEvent(type=AgentEventType.thinking, content=f"Step {steps + 1}...")
                steps += 1

                response = await self.model_client.invoke(
                    messages=messages,
                    model=self.config.model,
                    tools=tool_schemas or None,
                )

                if response.tool_calls:
                    self._state_machine.transition(AgentState.TOOL_CALL)
                    assistant_msg: dict = {"role": "assistant", "content": response.content}
                    assistant_msg["tool_calls"] = [
                        {k: v for k, v in tc.items() if k != "index"}
                        for tc in response.tool_calls
                    ]
                    messages.append(assistant_msg)

                    for tc in response.tool_calls:
                        tool_name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                        except json.JSONDecodeError:
                            args = {}

                        yield AgentEvent(
                            type=AgentEventType.tool_call,
                            content=f"Calling tool: {tool_name}",
                            tool_name=tool_name,
                            tool_args=args,
                        )

                        result = await self.tool_registry.execute(tool_name, args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result.output,
                        })

                        yield AgentEvent(
                            type=AgentEventType.tool_result,
                            content=result.output,
                            tool_result=result.output,
                        )
                    self._state_machine.transition(AgentState.RUNNING)
                else:
                    self._state_machine.transition(AgentState.FINISHED)
                    output = response.content or ""
                    if session_id:
                        await self._save_to_history(session_id, task_input, output)
                    if output:
                        yield AgentEvent(type=AgentEventType.chunk, content=output)
                    yield AgentEvent(type=AgentEventType.end, content=output)
                    return

            self._state_machine.transition(AgentState.ERROR)
            yield AgentEvent(type=AgentEventType.error, content=f"Max iterations ({self.config.max_iterations}) reached")
        except Exception as e:
            self._state_machine.transition(AgentState.ERROR)
            yield AgentEvent(type=AgentEventType.error, content=str(e))
