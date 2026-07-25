from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.models import SkillDefinition

router = APIRouter(prefix="/api/v1/admin/skills")


class SkillUpdateMetadataRequest(BaseModel):
    description: str | None = None
    tags: list[str] | None = None


class SkillUpdateContentRequest(BaseModel):
    content: str


# ── helpers ──────────────────────────────────────────

def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _skill_to_dict(s: SkillDefinition) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description or "",
        "tags": s.tags or [],
        "path": s.path,
        "version": s.version or "1.0.0",
        "git_commit_hash": s.git_commit_hash or "",
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# ── CRUD ─────────────────────────────────────────────

@router.get("/")
async def list_skills():
    """List all skill metadata from database."""
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


@router.get("/{skill_id}")
async def get_skill(skill_id: int):
    """Get skill metadata + content (reads prompt.md from filesystem)."""
    from app.main import get_db_session
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(SkillDefinition).where(SkillDefinition.id == skill_id)
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    data = _skill_to_dict(skill)

    # Read prompt.md from filesystem
    root = _get_project_root()
    prompt_path = root / skill.path / "prompt.md"
    if prompt_path.is_file():
        try:
            data["content"] = prompt_path.read_text(encoding="utf-8")
        except Exception:
            data["content"] = ""
    else:
        data["content"] = ""

    # List extension files
    skill_dir = root / skill.path
    ext_files = []
    if skill_dir.is_dir():
        for sub in sorted(skill_dir.iterdir()):
            if sub.is_dir() and not sub.name.startswith("."):
                files = sorted(
                    f.relative_to(skill_dir).as_posix()
                    for f in sub.glob("**/*")
                    if f.is_file() and not f.name.startswith(".")
                )
                if files:
                    ext_files.append({"dir": sub.name, "files": files})
    data["ext_files"] = ext_files

    return data


@router.get("/{skill_id}/content")
async def get_skill_content(skill_id: int):
    """Read prompt.md from filesystem (for the frontend editor)."""
    from app.main import get_db_session
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(SkillDefinition).where(SkillDefinition.id == skill_id)
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    root = _get_project_root()
    prompt_path = root / skill.path / "prompt.md"
    if not prompt_path.is_file():
        return {"content": ""}

    try:
        content = prompt_path.read_text(encoding="utf-8")
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")


@router.put("/{skill_id}/content")
async def update_skill_content(skill_id: int, req: SkillUpdateContentRequest):
    """Write prompt.md to filesystem (no DB change)."""
    from app.main import get_db_session
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await session.execute(
        select(SkillDefinition).where(SkillDefinition.id == skill_id)
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    root = _get_project_root()
    prompt_path = root / skill.path / "prompt.md"
    try:
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(req.content, encoding="utf-8")
        return {"message": "Content saved", "path": str(prompt_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")


@router.put("/{skill_id}")
async def update_skill_metadata(skill_id: int, req: SkillUpdateMetadataRequest):
    """Update skill metadata (description, tags) in DB + skill.yaml."""
    from app.main import get_db_session
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        result = await session.execute(
            select(SkillDefinition).where(SkillDefinition.id == skill_id)
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")

        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(skill, attr_name(key), value)
        skill.updated_at = datetime.now()

        # Also update skill.yaml on filesystem
        root = _get_project_root()
        yaml_path = root / skill.path / "skill.yaml"
        if yaml_path.is_file():
            try:
                import yaml
                with open(yaml_path, encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
                for key, value in update_data.items():
                    yaml_data[key] = value
                with open(yaml_path, "w", encoding="utf-8") as f:
                    yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False)
            except Exception:
                pass  # Don't fail the API if yaml write fails

        await session.commit()
        return _skill_to_dict(skill)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: int):
    """Soft-delete: mark skill as archived (doesn't delete files)."""
    from app.main import get_db_session
    from sqlalchemy import select

    session = get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        result = await session.execute(
            select(SkillDefinition).where(SkillDefinition.id == skill_id)
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")

        skill.status = "archived"
        skill.updated_at = datetime.now()
        await session.commit()
        return {"message": f"Skill '{skill.name}' archived"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ── Sync ─────────────────────────────────────────────

@router.post("/sync")
async def sync_skills_api():
    """Scan skills/ directory and sync metadata into DB."""
    from app.core.skill.sync import sync_skills
    result = await sync_skills()
    return result


# ── helpers ──────────────────────────────────────────

def attr_name(key: str) -> str:
    """Map camelCase API fields to snake_case model fields."""
    mapping = {
        "gitCommitHash": "git_commit_hash",
    }
    return mapping.get(key, key)
