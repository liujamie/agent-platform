import json
import time
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

    def __init__(self, config: AgentConfig, model_client=None, tool_registry=None, mcp_gateway=None, agent_id: int | None = None):
        super().__init__(config)
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.mcp_gateway = mcp_gateway
        self._agent_id = agent_id
        self._state_machine = AgentStateMachine()
        self._messages: list[dict] = []
        self._loaded_skills: set[str] = set()  # track which skills have been loaded

    def _add_skill_schema(self, schemas: list[dict]) -> None:
        """Add the load_skill tool schema if agent has skills configured."""
        if not self.config.skills:
            return
        schemas.append({
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": "加载一个专业技能的内容到你的上下文中。当你需要某个领域的专业知识时调用此功能。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "要加载的技能名称",
                            "enum": list(self.config.skills),
                        }
                    },
                    "required": ["name"],
                },
            },
        })

    async def _load_history(self, session_id: str) -> list[dict]:
        """Load full conversation history from MySQL via ConversationService."""
        from app.core.conversation.service import get_messages
        try:
            return await get_messages(session_id)
        except Exception:
            return []

    async def _save_to_history(self, session_id: str, user_input: str, llm_output: str) -> None:
        """Save user + assistant messages to MySQL via ConversationService.
        Auto-names the session from the first user message.
        """
        from app.core.conversation.service import add_message, get_message_count, rename

        try:
            is_first = await get_message_count(session_id) == 0
            if is_first:
                name = user_input.strip()[:30]
                if len(user_input.strip()) > 30:
                    name += "..."
                await rename(session_id, name)

            await add_message(session_id, "user", user_input)
            if llm_output:
                await add_message(session_id, "assistant", llm_output)
        except Exception:
            pass

    async def _fetch_skill_content(self, name: str) -> str | None:
        """Load a skill's content from the filesystem (skills/{name}/)."""
        from app.core.skill.loader import load_skill_content
        return await load_skill_content(name)

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

        # Add load_skill tool if agent has skills configured
        self._add_skill_schema(schemas)

        return schemas

    def _build_system_message(self) -> dict:
        """Build system message with role prompt."""
        return {"role": "system", "content": self.config.role}

    async def _handle_skill_call(self, messages: list, tool_call_id: str, args: dict) -> str:
        """Handle a load_skill tool call.

        Fetches skill content and injects it as a system message.
        Returns the tool result text for the protocol response.
        """
        skill_name = args.get("name", "")
        if not skill_name:
            return "Error: skill name is required"

        if skill_name in self._loaded_skills:
            return f"Skill '{skill_name}' is already loaded"

        content = await self._fetch_skill_content(skill_name)
        if content is None:
            return f"Error: skill '{skill_name}' not found"

        self._loaded_skills.add(skill_name)
        # Inject as system message so it stays in context for subsequent turns
        messages.append({
            "role": "system",
            "content": f"[Skill: {skill_name}]\n{content}",
        })
        return f"Skill '{skill_name}' loaded ({len(content)} chars)"

    async def execute(self, task_input: str, session_id: str = "") -> AgentResult:
        if self.model_client is None:
            return AgentResult(status="error", output="", error="Model client not configured")

        _t = {}  # timing
        self._state_machine.reset()
        messages = [self._build_system_message()]
        if session_id:
            t0 = time.time()
            history = await self._load_history(session_id)
            _t["load_history"] = round(time.time() - t0, 3)

            t0 = time.time()
            from app.core.memory.manager import build_context
            history = await build_context(
                history,
                max_tokens=self.config.max_tokens * 2,
                model_client=self.model_client,
                agent_id=self._agent_id,
                query=task_input,
            )
            _t["build_memory"] = round(time.time() - t0, 3)
            messages.extend(history)
        messages.append({"role": "user", "content": task_input})
        t0 = time.time()
        tool_schemas = self._get_tool_schemas()
        _t["build_tools"] = round(time.time() - t0, 3)
        steps = 0

        try:
            self._state_machine.transition(AgentState.RUNNING)
            while steps < self.config.max_iterations:
                t0 = time.time()
                response = await self.model_client.invoke(
                    messages=messages,
                    model=self.config.model,
                    tools=tool_schemas or None,
                )
                _t["llm_invoke"] = round(time.time() - t0, 3)
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

                        t0 = time.time()
                        if tool_name == "load_skill":
                            result_text = await self._handle_skill_call(messages, tc["id"], args)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result_text,
                            })
                        else:
                            result = await self.tool_registry.execute(tool_name, args)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result.output,
                            })
                        _t[f"tool_{tool_name}"] = round(time.time() - t0, 3)
                    self._state_machine.transition(AgentState.RUNNING)
                else:
                    self._state_machine.transition(AgentState.FINISHED)
                    if session_id:
                        t0 = time.time()
                        await self._save_to_history(session_id, task_input, response.content or "")
                        _t["save_history"] = round(time.time() - t0, 3)
                    if self._agent_id and session_id:
                        t0 = time.time()
                        from app.core.memory.episodic import extract_and_save
                        await extract_and_save(
                            self._agent_id, session_id,
                            task_input, response.content or "",
                            self.model_client,
                        )
                        _t["extract_episodic"] = round(time.time() - t0, 3)
                    print(f"[timing] {_t}")
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

        _t = {}
        self._state_machine.reset()
        messages = [self._build_system_message()]
        if session_id:
            t0 = time.time()
            history = await self._load_history(session_id)
            _t["load_history"] = round(time.time() - t0, 3)

            t0 = time.time()
            from app.core.memory.manager import build_context
            history = await build_context(
                history,
                max_tokens=self.config.max_tokens * 2,
                model_client=self.model_client,
                agent_id=self._agent_id,
                query=task_input,
            )
            _t["build_memory"] = round(time.time() - t0, 3)
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

                t0 = time.time()
                response = await self.model_client.invoke(
                    messages=messages,
                    model=self.config.model,
                    tools=tool_schemas or None,
                )
                _t["llm_invoke"] = round(time.time() - t0, 3)

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

                        if tool_name == "load_skill":
                            result_text = await self._handle_skill_call(messages, tc["id"], args)
                        else:
                            result = await self.tool_registry.execute(tool_name, args)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result.output,
                            })
                            result_text = result.output

                        yield AgentEvent(
                            type=AgentEventType.tool_result,
                            content=result_text,
                            tool_result=result_text,
                        )
                    self._state_machine.transition(AgentState.RUNNING)
                else:
                    self._state_machine.transition(AgentState.FINISHED)
                    output = response.content or ""
                    if session_id:
                        t0 = time.time()
                        await self._save_to_history(session_id, task_input, output)
                        _t["save_history"] = round(time.time() - t0, 3)
                    if self._agent_id and session_id:
                        t0 = time.time()
                        from app.core.memory.episodic import extract_and_save
                        await extract_and_save(
                            self._agent_id, session_id,
                            task_input, output,
                            self.model_client,
                        )
                        _t["extract_episodic"] = round(time.time() - t0, 3)
                    print(f"[timing] {_t}")
                    if output:
                        yield AgentEvent(type=AgentEventType.chunk, content=output)
                    yield AgentEvent(type=AgentEventType.end, content=output)
                    return

            self._state_machine.transition(AgentState.ERROR)
            yield AgentEvent(type=AgentEventType.error, content=f"Max iterations ({self.config.max_iterations}) reached")
        except Exception as e:
            self._state_machine.transition(AgentState.ERROR)
            yield AgentEvent(type=AgentEventType.error, content=str(e))
