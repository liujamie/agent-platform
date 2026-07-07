from abc import ABC, abstractmethod
from typing import AsyncIterator
from pydantic import BaseModel


class ModelResult(BaseModel):
    content: str
    model: str
    usage: dict = {"input": 0, "output": 0}


class ModelClient(ABC):
    """Abstract client for LLM model providers."""

    @abstractmethod
    async def invoke(self, messages: list[dict], model: str | None = None, tools: list | None = None) -> ModelResult:
        ...

    @abstractmethod
    async def stream(self, messages: list[dict], model: str | None = None, tools: list | None = None) -> AsyncIterator[str]:
        ...
        yield  # pragma: no cover
