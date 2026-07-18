from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.models import ModelConfig
from app.model.openai_client import OpenAIClient
from app.model.dashscope_client import DashScopeClient

router = APIRouter(prefix="/api/v1/admin/models")

# ---------- Encryption helpers ----------

_ENCRYPTION_KEY = None


def _get_encryption_key() -> bytes:
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        from app.config.settings import get_settings
        key = get_settings().model_config_key
        if key:
            # Ensure 32-byte key for Fernet
            import hashlib
            _ENCRYPTION_KEY = hashlib.sha256(key.encode()).digest()
        else:
            _ENCRYPTION_KEY = b""
    return _ENCRYPTION_KEY


def _encrypt(plaintext: str) -> str:
    from cryptography.fernet import Fernet
    key = _get_encryption_key()
    if not key:
        return plaintext  # fallback: store as-is if no key configured
    f = Fernet(Fernet.generate_key())  # placeholder
    # Actually derive from key:
    import base64
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str | None) -> str:
    if not ciphertext:
        return ""
    try:
        from cryptography.fernet import Fernet
        import base64
        key = _get_encryption_key()
        if not key:
            return ciphertext
        f = Fernet(base64.urlsafe_b64encode(key))
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ciphertext


# ---------- Request/Response schemas ----------


class ModelCreateRequest(BaseModel):
    name: str
    provider: str = "openai"
    api_key: str = ""
    base_url: str | None = None
    model: str


class ModelUpdateRequest(BaseModel):
    name: str | None = None
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


# ---------- Live ModelRouter helpers ----------


def _build_client(cfg: ModelConfig) -> Any:
    """Build a ModelClient from a ModelConfig ORM row."""
    api_key = _decrypt(cfg.api_key_encrypted)
    if cfg.provider == "dashscope":
        return DashScopeClient(api_key=api_key, model=cfg.model)
    return OpenAIClient(
        api_key=api_key,
        base_url=cfg.base_url or "https://api.deepseek.com",
        model=cfg.model,
    )


def _register_to_router(cfg: ModelConfig) -> None:
    """Register a single model config into the live ModelRouter."""
    from app.main import model_router

    client = _build_client(cfg)
    model_router.register(cfg.name, client)
    if cfg.is_current:
        model_router.switch_to(cfg.name)


async def reload_all_from_db(session) -> None:
    """Reload all active models from DB into the ModelRouter."""
    from app.main import model_router
    from sqlalchemy import select

    model_router._models.clear()
    model_router._current = None

    result = await session.execute(
        select(ModelConfig).where(ModelConfig.name.isnot(None))
    )
    for row in result.scalars().all():
        _register_to_router(row)


# ---------- CRUD endpoints ----------


@router.get("/")
async def list_models():
    """List all model configs (decrypted API keys NOT returned)."""
    from app.main import get_db_session
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        return {"models": []}
    try:
        result = await session.execute(
            select(ModelConfig).order_by(ModelConfig.created_at.desc())
        )
        models = result.scalars().all()
        return {"models": [_model_to_dict(m) for m in models]}
    except Exception as e:
        return {"models": [], "message": str(e)}


@router.post("/")
async def create_model(req: ModelCreateRequest):
    """Create a new model config and register it live."""
    from app.main import get_db_session

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select

        # Check duplicate name
        existing = await session.execute(
            select(ModelConfig).where(ModelConfig.name == req.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Model '{req.name}' already exists")

        cfg = ModelConfig(
            name=req.name,
            provider=req.provider,
            api_key_encrypted=_encrypt(req.api_key) if req.api_key else None,
            base_url=req.base_url,
            model=req.model,
            is_current=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(cfg)
        await session.commit()
        await session.refresh(cfg)

        # Register into live router
        _register_to_router(cfg)

        return _model_to_dict(cfg)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{model_id}")
async def update_model(model_id: int, req: ModelUpdateRequest):
    """Update a model config and hot-reload it."""
    from app.main import get_db_session
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        result = await session.execute(
            select(ModelConfig).where(ModelConfig.id == model_id)
        )
        cfg = result.scalar_one_or_none()
        if cfg is None:
            raise HTTPException(status_code=404, detail="Model not found")

        update_data = req.model_dump(exclude_unset=True)
        # Handle api_key separately (encrypt before storing)
        if "api_key" in update_data:
            api_key = update_data.pop("api_key")
            if api_key:
                cfg.api_key_encrypted = _encrypt(api_key)

        for key, value in update_data.items():
            if value is not None:
                setattr(cfg, key, value)
        cfg.updated_at = datetime.now()
        await session.commit()
        await session.refresh(cfg)

        # Hot-reload in ModelRouter
        from app.main import model_router
        client = _build_client(cfg)
        model_router.register(cfg.name, client)
        if cfg.is_current:
            model_router.switch_to(cfg.name)

        return _model_to_dict(cfg)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{model_id}")
async def delete_model(model_id: int):
    """Delete a model config and remove it from the live router."""
    from app.main import get_db_session, model_router
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        result = await session.execute(
            select(ModelConfig).where(ModelConfig.id == model_id)
        )
        cfg = result.scalar_one_or_none()
        if cfg is None:
            raise HTTPException(status_code=404, detail="Model not found")

        await session.delete(cfg)
        await session.commit()

        # Remove from live router
        model_router._models.pop(cfg.name, None)
        if model_router._current == cfg.name:
            model_router._current = None

        return {"message": f"Model '{cfg.name}' deleted"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_id}/switch")
async def switch_model(model_id: int):
    """Switch the current active model."""
    from app.main import get_db_session, model_router
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        result = await session.execute(
            select(ModelConfig).where(ModelConfig.id == model_id)
        )
        cfg = result.scalar_one_or_none()
        if cfg is None:
            raise HTTPException(status_code=404, detail="Model not found")

        # Clear current flag on all models
        await session.execute(
            ModelConfig.__table__.update().values(is_current=False)
        )
        # Set new current
        cfg.is_current = True
        await session.commit()

        # Switch in live router
        model_router.switch_to(cfg.name)

        return {"message": f"Switched to '{cfg.name}'", "current": cfg.name}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_models():
    """Reload all models from DB into the ModelRouter (no restart needed)."""
    from app.main import get_db_session

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await reload_all_from_db(session)
        return {"message": "Models reloaded from database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Helpers ----------


def _model_to_dict(m: ModelConfig) -> dict[str, Any]:
    return {
        "id": m.id,
        "name": m.name,
        "provider": m.provider,
        "base_url": m.base_url,
        "model": m.model,
        "is_current": m.is_current,
        "has_api_key": bool(m.api_key_encrypted),
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }
