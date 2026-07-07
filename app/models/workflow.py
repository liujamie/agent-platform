from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    agent = "agent"
    tool = "tool"
    condition = "condition"
    transform = "transform"


class RetryConfig(BaseModel):
    max_retries: int = 3
    backoff_seconds: float = 1.0


class NodeDef(BaseModel):
    id: str
    type: NodeType
    config: dict[str, Any] = Field(default_factory=dict)
    retry: RetryConfig | None = None
    timeout: int | None = None


class EdgeDef(BaseModel):
    source: str
    target: str
    condition: str | None = None
    data_mapping: dict[str, str] | None = None


class WorkflowDef(BaseModel):
    nodes: list[NodeDef]
    edges: list[EdgeDef]


class WorkflowResult(BaseModel):
    status: str
    trace_id: str = ""
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class WorkflowStatus(BaseModel):
    workflow_id: str
    status: str
    node_statuses: dict[str, str] = Field(default_factory=dict)
