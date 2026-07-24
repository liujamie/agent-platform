import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings

settings = get_settings()

# --- Initialize core components at module level ---

# 1. Tool Registry (import tools to trigger @tool decorator)
from app.core.tool.decorator import get_registry
import app.tools  # noqa: F401
tool_registry = get_registry()

# 2. MCP Gateway
from app.core.mcp.gateway import MCPGateway
mcp_gateway = MCPGateway(tool_registry)

# 3. Model Router (model clients registered in lifespan)
from app.model.router import ModelRouter
model_router = ModelRouter()

# 3. Include API routers (at module level so tests without lifespan work)
from app.api.agent_routes import router as agent_router
from app.api.tool_routes import router as tool_router
from app.api.model_routes import router as model_router_api
from app.api.workflow_routes import router as workflow_router
from app.api.admin_routes import router as admin_router
from app.api.admin_model_routes import router as admin_model_router
from app.api.admin_mcp_routes import router as admin_mcp_router

_db_session = None  # Set after DB init in lifespan


def get_db_session():
    return _db_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_router, _db_session

    # 1. Init Database
    try:
        from app.infrastructure import database as db_module
        await db_module.init_db()
        _db_session = db_module.async_session_maker()
        print("[init] Database connected")
        # Auto-migrate: add connections column to existing agent_definitions table
        if _db_session is not None:
            try:
                async with _db_session() as s:
                    from sqlalchemy import text
                    await s.execute(text(
                        "ALTER TABLE agent_definitions ADD COLUMN IF NOT EXISTS connections JSON NULL COMMENT '绑定的 MCP 连接列表' AFTER tools"
                    ))
                    await s.commit()
                    print("[init] Schema migration: connections column added")
            except Exception:
                pass  # Column may already exist or MySQL version < 8.0
    except Exception as e:
        print(f"[init] Database unavailable (will work without DB): {e}")
        _db_session = None

    # 2. Init Redis
    try:
        from app.infrastructure.redis_client import init_redis
        await init_redis()
        print("[init] Redis connected")
    except Exception as e:
        print(f"[init] Redis unavailable: {e}")

    # 3. Register model clients — try DB first, fall back to env config
    if _db_session is not None:
        try:
            from app.api.admin_model_routes import reload_all_from_db
            await reload_all_from_db(_db_session)
            if model_router.current:
                print(f"[init] Models loaded from database (current: {model_router.current})")
        except Exception as e:
            print(f"[init] Failed to load models from DB: {e}")
    if model_router.current is None:
        # Fallback: env-based config
        if settings.model_clients:
            from app.model.openai_client import OpenAIClient
            from app.model.dashscope_client import DashScopeClient
            first_name = None
            for cfg in settings.model_clients:
                provider = cfg.get("provider", "openai")
                name = cfg.get("name", provider)
                if provider == "dashscope":
                    client = DashScopeClient(api_key=cfg["api_key"], model=cfg.get("model", "qwen-plus"))
                else:
                    client = OpenAIClient(
                        api_key=cfg["api_key"],
                        base_url=cfg.get("base_url", "https://api.deepseek.com"),
                        model=cfg.get("model", "deepseek-chat"),
                    )
                model_router.register(name, client)
                if first_name is None:
                    first_name = name
            if first_name:
                model_router.switch_to(first_name)
        else:
            if settings.deepseek_api_key:
                from app.model.openai_client import OpenAIClient
                client = OpenAIClient(
                    api_key=settings.deepseek_api_key,
                    base_url=settings.default_model_api_base,
                    model=settings.default_model,
                )
                model_router.register("default", client)
                model_router.switch_to("default")
            if settings.dashscope_api_key:
                from app.model.dashscope_client import DashScopeClient
                ds_client = DashScopeClient(api_key=settings.dashscope_api_key)
                model_router.register("dashscope", ds_client)

    # 4. Auto-reconnect MCP connections from DB
    if _db_session is not None:
        try:
            from sqlalchemy import select
            from app.infrastructure.models import MCPConnection
            result = await _db_session.execute(
                select(MCPConnection).where(MCPConnection.status.in_(["connected", "error"]))
            )
            for mcp_conn in result.scalars().all():
                try:
                    await mcp_gateway.connect(
                        name=mcp_conn.name,
                        connection_type=mcp_conn.connection_type,
                        command=mcp_conn.command,
                        args=mcp_conn.args or [],
                        url=mcp_conn.url,
                        env_vars=mcp_conn.env_vars or {},
                    )
                    mcp_conn.status = "connected"
                    mcp_conn.error_message = None
                except Exception as e:
                    mcp_conn.status = "error"
                    mcp_conn.error_message = str(e)
                mcp_conn.updated_at = datetime.now()
            await _db_session.commit()
            print("[init] MCP connections restored")
        except Exception as e:
            print(f"[init] MCP connections restore skipped: {e}")

    yield

    # Shutdown
    # Disconnect all MCP connections first
    try:
        await mcp_gateway.disconnect_all()
        print("[shutdown] MCP connections closed")
    except Exception as e:
        print(f"[shutdown] MCP connections close error: {e}")

    try:
        from app.infrastructure.database import close_db
        await close_db()
    except Exception:
        pass
    try:
        from app.infrastructure.redis_client import close_redis
        await close_redis()
    except Exception:
        pass


app = FastAPI(
    title="Agent Platform",
    description="Multi-Agent orchestration & scheduling platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(tool_router)
app.include_router(model_router_api)
app.include_router(workflow_router)
app.include_router(admin_router)
app.include_router(admin_model_router)
app.include_router(admin_mcp_router)


@app.get("/health")
async def health():
    db_status = "connected" if _db_session is not None else "unavailable"
    return {"status": "ok", "database": db_status}


def start():
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
