import os
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

# 2. Model Router (model clients registered in lifespan)
from app.model.router import ModelRouter
model_router = ModelRouter()

# 3. Include API routers (at module level so tests without lifespan work)
from app.api.agent_routes import router as agent_router
from app.api.tool_routes import router as tool_router
from app.api.model_routes import router as model_router_api
from app.api.workflow_routes import router as workflow_router
from app.api.admin_routes import router as admin_router

_db_session = None  # Set after DB init in lifespan


def get_db_session():
    return _db_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_router, _db_session

    # 1. Init Database
    try:
        from app.infrastructure.database import init_db, async_session_maker
        await init_db()
        _db_session = async_session_maker()
        print("[init] Database connected")
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

    # 3. Register model clients
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

    yield

    # Shutdown
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


@app.get("/health")
async def health():
    db_status = "connected" if _db_session is not None else "unavailable"
    return {"status": "ok", "database": db_status}


def start():
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
