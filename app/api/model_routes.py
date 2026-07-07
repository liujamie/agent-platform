from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/model")


class SwitchRequest(BaseModel):
    model_name: str


@router.get("/list")
async def list_models():
    from app.main import model_router

    if model_router is None:
        return {"models": [], "current": None}
    return {"models": model_router.list_models(), "current": model_router.current}


@router.post("/switch")
async def switch_model(req: SwitchRequest):
    from app.main import model_router

    if model_router is None:
        return {"status": "error", "error": "Model router not initialized"}
    model_router.switch_to(req.model_name)
    return {"status": "ok", "current": model_router.current}
