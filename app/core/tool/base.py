from abc import ABC, abstractmethod
from app.models.tool import ToolResult


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict = {}

    @property
    def source(self) -> str:
        """Source identifier, e.g. 'built-in' or an MCP connection name."""
        return "built-in"

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...
