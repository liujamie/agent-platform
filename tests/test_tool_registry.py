"""tests/test_tool_registry.py"""
import pytest
from app.core.tool.base import BaseTool
from app.core.tool.registry import ToolRegistry
from app.core.tool.decorator import tool, get_registry
from app.models.tool import ToolResult


class TestBaseTool:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseTool()


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        reg.register(_make_mock_tool("echo", "echo input"))
        retrieved = reg.get("echo")
        assert retrieved is not None
        assert retrieved.name == "echo"

    def test_get_nonexistent(self):
        reg = ToolRegistry()
        assert reg.get("nope") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(_make_mock_tool("a", "tool a"))
        reg.register(_make_mock_tool("b", "tool b"))
        assert len(reg.list_tools()) == 2

    def test_list_tool_schemas(self):
        reg = ToolRegistry()
        reg.register(_make_mock_tool("search", "search web"))
        schemas = reg.list_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "search"

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        reg = ToolRegistry()
        reg.register(_make_mock_tool("echo", "echo", output="hello"))
        result = await reg.execute("echo", {})
        assert result.success is True
        assert result.output == "hello"

    @pytest.mark.asyncio
    async def test_execute_nonexistent(self):
        reg = ToolRegistry()
        result = await reg.execute("nope", {})
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        reg = ToolRegistry()
        reg.register(_make_mock_tool("fail", "failing", should_fail=True))
        result = await reg.execute("fail", {})
        assert result.success is False


class TestToolDecorator:
    def test_decorator_registers_tool(self):
        # Clear and re-register
        import app.core.tool.decorator as d
        d._registry = ToolRegistry()

        @tool(name="greet", description="say hello")
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        registry = get_registry()
        assert registry.get("greet") is not None
        assert registry.get("greet").name == "greet"


# --- helpers ---

def _make_mock_tool(name: str, description: str, output: str = "ok", should_fail: bool = False):
    class MockTool(BaseTool):
        def __init__(self):
            self.name = name
            self.description = description

        async def execute(self, **kwargs) -> ToolResult:
            if should_fail:
                return ToolResult(tool_name=self.name, output="", success=False, error="failed")
            return ToolResult(tool_name=self.name, output=output, success=True)

    return MockTool()
