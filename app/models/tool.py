from typing import Any
from pydantic import BaseModel, Field


class ToolParam(BaseModel):
    type: str
    description: str = ""
    required: bool = False


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    output: str
    success: bool
    error: str | None = None
    duration_ms: int = 0
