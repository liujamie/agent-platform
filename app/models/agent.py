from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from app.models.common import TokenUsage


class AgentEventType(str, Enum):
    start = "start"
    thinking = "thinking"
    tool_call = "tool_call"
    tool_result = "tool_result"
    chunk = "chunk"
    end = "end"
    error = "error"


class AgentConfig(BaseModel):
    name: str
    role: str
    model: str
    tools: list[str] = Field(default_factory=list)
    max_iterations: int = 10
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = 4096


class AgentEvent(BaseModel):
    type: AgentEventType
    content: str = ""
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: str | None = None


class AgentResult(BaseModel):
    status: str
    output: str = ""
    trace_id: str = ""
    token_usage: TokenUsage | None = None
    steps: int = 0
    error: str | None = None
