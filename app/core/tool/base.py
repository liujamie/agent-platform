from abc import ABC, abstractmethod
from app.models.tool import ToolResult


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...
