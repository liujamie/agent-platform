from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init core components
    yield
    # Shutdown: cleanup


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


@app.get("/health")
async def health():
    return {"status": "ok"}


def start():
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
