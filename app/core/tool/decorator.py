import functools
from typing import Any

from app.core.tool.registry import ToolRegistry

_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    return _registry


def _to_openai_params(params: dict[str, Any]) -> dict[str, Any]:
    """Convert simple param format {name: {type, description, required?}} to OpenAI JSON Schema."""
    properties = {}
    required = []
    for key, spec in params.items():
        properties[key] = {k: v for k, v in spec.items() if k != "required"}
        if spec.get("required"):
            required.append(key)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def tool(name: str, description: str, parameters: dict[str, Any] | None = None):
    """Decorator that registers an async function as a Tool."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(**kwargs) -> str:
            return await func(**kwargs)

        from app.core.tool.base import BaseTool
        from app.models.tool import ToolResult

        class _DecoratedTool(BaseTool):
            async def execute(self, **kwargs) -> ToolResult:
                try:
                    result = await func(**kwargs)
                    return ToolResult(tool_name=_DecoratedTool.name, output=str(result), success=True)
                except Exception as e:
                    return ToolResult(tool_name=_DecoratedTool.name, output="", success=False, error=str(e))

        _DecoratedTool.name = name
        _DecoratedTool.description = description
        _DecoratedTool.parameters = _to_openai_params(parameters or {})
        instance = _DecoratedTool()
        _registry.register(instance)
        return wrapper
    return decorator
