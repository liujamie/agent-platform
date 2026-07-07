from typing import AsyncIterator

from app.core.agent.base import BaseAgent
from app.core.agent.state import AgentStateMachine, AgentState
from app.models.agent import AgentConfig, AgentResult, AgentEvent, AgentEventType


class ReActAgent(BaseAgent):
    """
    ReAct Agent implementation.

    Thought -> Action -> Observation -> Thought -> ... -> Final Answer
    """

    def __init__(self, config: AgentConfig, model_client=None, tool_registry=None):
        super().__init__(config)
        self.model_client = model_client
        self.tool_registry = tool_registry
        self._state_machine = AgentStateMachine()
        self._messages: list[dict] = []

    async def execute(self, task_input: str, session_id: str = "") -> AgentResult:
        if self.model_client is None:
            return AgentResult(status="error", output="", error="Model client not configured")

        self._state_machine.reset()
        self._messages = [{"role": "user", "content": task_input}]
        try:
            self._state_machine.transition(AgentState.RUNNING)
            response = await self.model_client.invoke(
                messages=self._messages,
                model=self.config.model,
            )
            output = response.get("content", "") if hasattr(response, 'get') else response.content
            self._state_machine.transition(AgentState.FINISHED)
            return AgentResult(
                status="success",
                output=str(output),
                steps=1,
            )
        except Exception as e:
            self._state_machine.transition(AgentState.ERROR)
            return AgentResult(status="error", error=str(e), steps=0)

    async def stream(self, task_input: str, session_id: str = "") -> AsyncIterator[AgentEvent]:
        if self.model_client is None:
            yield AgentEvent(type=AgentEventType.error, content="Model client not configured")
            return

        self._state_machine.reset()
        self._messages = [{"role": "user", "content": task_input}]

        yield AgentEvent(type=AgentEventType.start, content="Agent started")
        yield AgentEvent(type=AgentEventType.thinking, content="Processing...")

        try:
            self._state_machine.transition(AgentState.RUNNING)
            content = ""
            async for chunk in self.model_client.stream(
                messages=self._messages,
                model=self.config.model,
            ):
                content += chunk
                yield AgentEvent(type=AgentEventType.chunk, content=chunk)

            self._state_machine.transition(AgentState.FINISHED)
            yield AgentEvent(type=AgentEventType.end, content=content)
        except Exception as e:
            self._state_machine.transition(AgentState.ERROR)
            yield AgentEvent(type=AgentEventType.error, content=str(e))
