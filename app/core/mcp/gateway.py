import contextlib
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.types import Tool as MCPTool

from app.core.tool.base import BaseTool
from app.core.tool.registry import ToolRegistry
from app.models.tool import ToolResult


class MCPToolWrapper(BaseTool):
    """Wraps an MCP tool as a BaseTool for the ToolRegistry."""

    def __init__(self, mcp_tool: MCPTool, connection_name: str, gateway: "MCPGateway"):
        self.name = mcp_tool.name
        self.description = mcp_tool.description or f"MCP tool from {connection_name}"
        self.parameters = mcp_tool.inputSchema or {"type": "object"}
        self._connection_name = connection_name
        self._gateway = gateway
        self._mcp_tool_name = mcp_tool.name

    @property
    def source(self) -> str:
        return self._connection_name

    async def execute(self, **kwargs) -> ToolResult:
        try:
            result = await self._gateway.call_tool(self._connection_name, self._mcp_tool_name, kwargs)
            text_parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_parts.append(item.text)
                elif hasattr(item, "data"):
                    text_parts.append(str(item.data))
            output = "\n".join(text_parts)
            return ToolResult(tool_name=self.name, output=output, success=not result.isError)
        except Exception as e:
            return ToolResult(tool_name=self.name, output="", success=False, error=str(e))


class MCPClientWrapper:
    """Manages a single MCP server connection."""

    def __init__(self, name: str, connection_type: str, command: str | None = None,
                 args: list[str] | None = None, url: str | None = None,
                 env_vars: dict[str, str] | None = None):
        self.name = name
        self.connection_type = connection_type
        self.command = command
        self.args = args or []
        self.url = url
        self.env_vars = env_vars
        self.session: ClientSession | None = None
        self._streams: tuple[Any, Any] | None = None
        self._ctx_stack = contextlib.AsyncExitStack()

    async def connect(self) -> list[dict]:
        """Connect to the MCP server and discover available tools."""
        if self.connection_type == "stdio":
            params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env_vars,
            )
            streams = await self._ctx_stack.enter_async_context(stdio_client(params))
        else:
            streams = await self._ctx_stack.enter_async_context(sse_client(self.url))
        self._streams = streams
        read, write = streams

        self.session = await self._ctx_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

        tools_result = await self.session.list_tools()
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
            for t in tools_result.tools
        ]

    async def disconnect(self):
        """Disconnect from the MCP server."""
        await self._ctx_stack.aclose()
        self.session = None

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        if not self.session:
            raise RuntimeError(f"MCP connection '{self.name}' is not connected")
        return await self.session.call_tool(tool_name, arguments)

    @property
    def is_connected(self) -> bool:
        return self.session is not None


class MCPGateway:
    """Manages all MCP server connections and tool registration."""

    def __init__(self, tool_registry: ToolRegistry):
        self._tool_registry = tool_registry
        self._connections: dict[str, MCPClientWrapper] = {}
        self._wrapped_tools: dict[str, list[str]] = {}  # connection_name -> [tool_name, ...]

    async def connect(self, name: str, connection_type: str, *,
                      command: str | None = None, args: list[str] | None = None,
                      url: str | None = None, env_vars: dict[str, str] | None = None) -> str:
        """Connect to an MCP server and register its tools.

        Raises on connection failure (re-raises the underlying exception).
        """
        # Disconnect first if already connected
        if name in self._connections:
            await self._disconnect_internal(name)

        wrapper = MCPClientWrapper(
            name=name, connection_type=connection_type,
            command=command, args=args, url=url, env_vars=env_vars,
        )

        try:
            tools_meta = await wrapper.connect()
        except Exception:
            with contextlib.suppress(Exception):
                await wrapper.disconnect()
            raise

        self._connections[name] = wrapper
        self._wrapped_tools[name] = []

        # Wrap each MCP tool and register to ToolRegistry
        for t in tools_meta:
            mcp_tool = MCPTool(name=t["name"], description=t.get("description", ""),
                               inputSchema=t.get("inputSchema", {"type": "object"}))
            wrapped = MCPToolWrapper(mcp_tool, name, self)
            self._tool_registry.register(wrapped)
            self._wrapped_tools[name].append(t["name"])

        return "connected"

    async def disconnect(self, name: str):
        """Disconnect from an MCP server and unregister its tools."""
        await self._disconnect_internal(name)
        # Also remove from connections dict
        self._connections.pop(name, None)
        self._wrapped_tools.pop(name, None)

    async def _disconnect_internal(self, name: str):
        """Unregister tools and close connection without removing from dict."""
        wrapper = self._connections.get(name)
        if not wrapper:
            return

        # Unregister tools from ToolRegistry
        tool_names = self._wrapped_tools.get(name, [])
        for tool_name in tool_names:
            self._tool_registry.unregister(tool_name)

        await wrapper.disconnect()

    async def disconnect_all(self):
        """Disconnect all MCP servers (for shutdown)."""
        for name in list(self._connections.keys()):
            await self.disconnect(name)

    def get_connection(self, name: str) -> dict | None:
        """Get connection details with its tools."""
        wrapper = self._connections.get(name)
        if not wrapper:
            return None
        return {
            "name": wrapper.name,
            "connection_type": wrapper.connection_type,
            "status": "connected" if wrapper.is_connected else "disconnected",
            "tools": self._wrapped_tools.get(name, []),
        }

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a registered tool by name."""
        return self._tool_registry.get(tool_name)

    def list_connections(self) -> list[dict]:
        """List all active (in-memory) connections."""
        result = []
        for name, wrapper in self._connections.items():
            result.append({
                "name": name,
                "status": "connected" if wrapper.is_connected else "disconnected",
                "tools": self._wrapped_tools.get(name, []),
            })
        return result

    async def call_tool(self, connection_name: str, tool_name: str, arguments: dict) -> Any:
        """Call a tool on a specific MCP connection."""
        wrapper = self._connections.get(connection_name)
        if not wrapper:
            raise RuntimeError(f"MCP connection '{connection_name}' not found")
        return await wrapper.call_tool(tool_name, arguments)
