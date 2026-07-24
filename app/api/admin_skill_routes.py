from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.models import SkillDefinition

router = APIRouter(prefix="/api/v1/admin/skills")


class SkillCreateRequest(BaseModel):
    name: str
    description: str = ""
    content: str


class SkillUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None


@router.get("/")
async def list_skills():
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"skills": [], "message": "Database not configured"}
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(SkillDefinition).order_by(SkillDefinition.created_at.desc())
        )
        return {"skills": [_skill_to_dict(s) for s in result.scalars().all()]}
    except Exception as e:
        return {"skills": [], "message": str(e)}


@router.post("/")
async def create_skill(req: SkillCreateRequest):
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        existing = await session.execute(
            select(SkillDefinition).where(SkillDefinition.name == req.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Skill '{req.name}' already exists")

        skill = SkillDefinition(
            name=req.name,
            description=req.description,
            content=req.content,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(skill)
        await session.commit()
        await session.refresh(skill)
        return _skill_to_dict(skill)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{skill_id}")
async def update_skill(skill_id: int, req: SkillUpdateRequest):
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(SkillDefinition).where(SkillDefinition.id == skill_id)
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")

        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(skill, key, value)
        skill.updated_at = datetime.now()
        await session.commit()
        return _skill_to_dict(skill)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: int):
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(SkillDefinition).where(SkillDefinition.id == skill_id)
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")

        await session.delete(skill)
        await session.commit()
        return {"message": f"Skill '{skill.name}' deleted"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def _skill_to_dict(s: SkillDefinition) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description or "",
        "content": s.content,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
