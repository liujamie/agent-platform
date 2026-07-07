from typing import Any

from app.core.tool.base import BaseTool
from app.models.tool import ToolResult


class ToolRegistry:
    """Central registry for all tools. Supports register, lookup, and execution."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def list_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for LLM function calling."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                },
            })
        return schemas

    async def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(tool_name=name, output="", success=False, error=f"Tool '{name}' not found")
        return await tool.execute(**args)
