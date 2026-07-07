from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/tool")


class ToolExecuteRequest(BaseModel):
    tool_name: str
    args: dict = {}


@router.get("/list")
async def list_tools():
    from app.main import tool_registry

    tools = []
    for t in tool_registry.list_tools():
        tools.append({"name": t.name, "description": t.description})
    return {"tools": tools}


@router.post("/execute")
async def execute_tool(req: ToolExecuteRequest):
    from app.main import tool_registry

    result = await tool_registry.execute(req.tool_name, req.args)
    return {
        "tool_name": result.tool_name,
        "output": result.output,
        "success": result.success,
        "error": result.error,
    }
