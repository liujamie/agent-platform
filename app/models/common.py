from typing import Any
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0
    total: int = 0

    def __init__(self, **data):
        super().__init__(**data)
        if self.total == 0 and (self.input or self.output):
            object.__setattr__(self, 'total', self.input + self.output)


class Task(BaseModel):
    input: str
    session_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Context:
    """Mutable execution context shared across workflow nodes / agent steps."""

    def __init__(self):
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._store)
