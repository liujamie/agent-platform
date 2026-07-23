from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.models import MCPConnection

router = APIRouter(prefix="/api/v1/admin/mcp-connections")


class MCPCreateRequest(BaseModel):
    name: str
    connection_type: str = "stdio"
    command: str | None = None
    args: list[str] = []
    url: str | None = None
    env_vars: dict[str, str] = {}


class MCPUpdateRequest(BaseModel):
    name: str | None = None
    connection_type: str | None = None
    command: str | None = None
    args: list[str] | None = None
    url: str | None = None
    env_vars: dict[str, str] | None = None


@router.get("/")
async def list_mcp_connections():
    """List all MCP connections with status."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"connections": [], "message": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(MCPConnection).order_by(MCPConnection.created_at.desc())
        )
        connections = result.scalars().all()

        # Merge with live status from MCPGateway
        from app.main import mcp_gateway
        results = []
        for c in connections:
            entry = _conn_to_dict(c)
            # Override status with live gateway status if connected
            live = mcp_gateway.get_connection(c.name)
            if live:
                entry["status"] = live["status"]
                entry["tools"] = live["tools"]
            results.append(entry)
        return {"connections": results}
    except Exception as e:
        return {"connections": [], "message": str(e)}


@router.post("/")
async def create_mcp_connection(req: MCPCreateRequest):
    """Create a new MCP connection config and auto-connect."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        existing = await session.execute(
            select(MCPConnection).where(MCPConnection.name == req.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Connection '{req.name}' already exists")

        conn = MCPConnection(
            name=req.name,
            connection_type=req.connection_type,
            command=req.command,
            args=req.args or [],
            url=req.url,
            env_vars=req.env_vars or {},
            status="disconnected",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(conn)
        await session.commit()
        await session.refresh(conn)

        # Auto-connect via MCPGateway
        from app.main import mcp_gateway
        try:
            await mcp_gateway.connect(
                name=conn.name,
                connection_type=conn.connection_type,
                command=conn.command,
                args=conn.args or [],
                url=conn.url,
                env_vars=conn.env_vars or {},
            )
            conn.status = "connected"
        except Exception as e:
            conn.status = "error"
            conn.error_message = str(e)

        conn.updated_at = datetime.now()
        await session.commit()
        return _conn_to_dict(conn)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conn_id}")
async def update_mcp_connection(conn_id: int, req: MCPUpdateRequest):
    """Update an MCP connection config and reconnect if was connected."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(MCPConnection).where(MCPConnection.id == conn_id)
        )
        conn = result.scalar_one_or_none()
        if conn is None:
            raise HTTPException(status_code=404, detail="MCP connection not found")

        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(conn, key, value)

        # Reconnect if it was connected
        from app.main import mcp_gateway
        was_connected = conn.status == "connected" or mcp_gateway.get_connection(conn.name) is not None
        if was_connected:
            try:
                await mcp_gateway.connect(
                    name=conn.name,
                    connection_type=conn.connection_type,
                    command=conn.command,
                    args=conn.args or [],
                    url=conn.url,
                    env_vars=conn.env_vars or {},
                )
                conn.status = "connected"
                conn.error_message = None
            except Exception as e:
                conn.status = "error"
                conn.error_message = str(e)

        conn.updated_at = datetime.now()
        await session.commit()
        return _conn_to_dict(conn)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conn_id}")
async def delete_mcp_connection(conn_id: int):
    """Delete an MCP connection config and disconnect first."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(MCPConnection).where(MCPConnection.id == conn_id)
        )
        conn = result.scalar_one_or_none()
        if conn is None:
            raise HTTPException(status_code=404, detail="MCP connection not found")

        # Disconnect from gateway first
        from app.main import mcp_gateway
        await mcp_gateway.disconnect(conn.name)

        await session.delete(conn)
        await session.commit()
        return {"message": f"Connection '{conn.name}' deleted"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conn_id}/connect")
async def connect_mcp(conn_id: int):
    """Manually connect an MCP server."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(MCPConnection).where(MCPConnection.id == conn_id)
        )
        conn = result.scalar_one_or_none()
        if conn is None:
            raise HTTPException(status_code=404, detail="MCP connection not found")

        from app.main import mcp_gateway
        try:
            await mcp_gateway.connect(
                name=conn.name,
                connection_type=conn.connection_type,
                command=conn.command,
                args=conn.args or [],
                url=conn.url,
                env_vars=conn.env_vars or {},
            )
            conn.status = "connected"
            conn.error_message = None
        except Exception as e:
            conn.status = "error"
            conn.error_message = str(e)

        conn.updated_at = datetime.now()
        await session.commit()
        return _conn_to_dict(conn)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conn_id}/disconnect")
async def disconnect_mcp(conn_id: int):
    """Manually disconnect an MCP server."""
    from app.main import get_db_session, mcp_gateway
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(MCPConnection).where(MCPConnection.id == conn_id)
        )
        conn = result.scalar_one_or_none()
        if conn is None:
            raise HTTPException(status_code=404, detail="MCP connection not found")

        await mcp_gateway.disconnect(conn.name)
        conn.status = "disconnected"
        conn.error_message = None
        conn.updated_at = datetime.now()
        await session.commit()
        return _conn_to_dict(conn)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conn_id}/tools")
async def list_mcp_tools(conn_id: int):
    """List tools discovered from an MCP connection."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(MCPConnection).where(MCPConnection.id == conn_id)
        )
        conn = result.scalar_one_or_none()
        if conn is None:
            raise HTTPException(status_code=404, detail="MCP connection not found")

        from app.main import mcp_gateway
        live = mcp_gateway.get_connection(conn.name)
        if not live:
            return {"tools": [], "status": conn.status}

        tools_detail = []
        for tool_name in live["tools"]:
            tool = mcp_gateway.get_tool(tool_name)
            if tool:
                tools_detail.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                })
        return {"tools": tools_detail, "status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _conn_to_dict(c: MCPConnection) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "connection_type": c.connection_type,
        "command": c.command,
        "args": c.args or [],
        "url": c.url,
        "env_vars": c.env_vars or {},
        "status": c.status,
        "error_message": c.error_message,
        "tools": [],
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
