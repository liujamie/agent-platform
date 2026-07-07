from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.models.agent import AgentConfig, AgentResult, AgentEvent


class BaseAgent(ABC):
    """Abstract base class for all Agent implementations."""

    def __init__(self, config: AgentConfig):
        self.config = config

    @abstractmethod
    async def execute(self, task_input: str, session_id: str = "") -> AgentResult:
        ...

    @abstractmethod
    async def stream(self, task_input: str, session_id: str = "") -> AsyncIterator[AgentEvent]:
        ...
        yield  # pragma: no cover
